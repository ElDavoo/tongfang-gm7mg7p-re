#!/usr/bin/env python3
r"""Census the Setup IFR: every question's store, offset, default, options, and
the conditions that hide it.

Input is committed text -- `bios/ifr/Setup.en-US.ifr.txt`, ifrextractor 1.6.1's
verbose dump of the `Setup` driver's HII forms. No ROM, no UEFIExtract, no
ifrextractor: `bios/tools/bios_extract.py --extract` produces that file and
this tool only reads it. `--ifr <path>` points it at a different dump, which is
how the same code reads a dump taken in a scratch work directory.

    python3 bios/tools/ifr_census.py                       the charge/battery census
    python3 bios/tools/ifr_census.py --match turbo         questions matching a term
    python3 bios/tools/ifr_census.py --list-excluded       the near-misses it declined
    python3 bios/tools/ifr_census.py --offset Setup:0x4F3  one offset
    python3 bios/tools/ifr_census.py --question 0x2A6      one question id
    python3 bios/tools/ifr_census.py --write               regenerate the CSV
    python3 bios/tools/ifr_census.py --check               the committed CSV is current
    python3 bios/tools/ifr_census.py --self-test           known answers, fixture IFR

Why a table of charge questions, and why this shape. `Setup`, `CpuSetup` and
the rest are boot-services-only on this machine (docs/findings.md §6), so the
IFR is the only map of what the setup offers. The part worth mapping is the
hiding: a `SuppressIf` is how a firmware keeps an option out of sight, and this
tool resolves each one to a readable expression so a row can say what has to be
true for the question to be there at all.

Three decisions, each of which the output is auditable against:

**Which rows are charge questions.** A committed phrase list, not a judgement
call. `CHARGE_TERMS` holds the phrases; a row matches when one of them appears
inside a word of the prompt, the help, or an option label -- all three, because
`Light Bar Effect` is only recognisable from its help and `Boot performance
mode` only from one of its option values. `matched_term` and `matched_field`
say which, per row. `--list-excluded` prints what a looser probe would have
caught and this list declined, so the exclusion is a decision a reader can
overturn rather than a silence.

**A default is the IFR's, not the machine's.** The two `default` columns carry
the `Default` statement (DefaultId 0x0 normal, 0x1 manufacturing), falling back
to the `OneOfOption` flagged `Default`/`MfgDefault` for the questions that state
it there instead. That is a statement about the IFR. The ROM's factory values
live in an NVAR `StdDefaults` store which is deliberately not committed
(bios/README.md, "Default values"), and nothing here reads it.

**A condition is a reading of the condition tree, not a measurement.** The
IFR's condition buffer is a flat stream evaluated on a stack -- `EqIdVal` and
its relatives push, `Not` pops one, `And`/`Or` pop two, and the single value
left is the condition -- so the tool evaluates it that way and prints the tree.
Indentation would get it wrong: in the dump the two `Not`s and the `And` that
combine them all sit at the same depth. An opcode the tool does not model
renders as `?(...)`, and every run prints how many expressions it could not
resolve rather than passing them off as read.

The CSV this writes is derived from a committed input, which is what makes
`--check` a real gate: it re-derives the file and fails on any difference, so a
hand-edited table cannot survive. A census of all 3,659 store questions is
deliberately not committed -- that is a lookup, and `--ifr` with `--match` and
`--offset` serves the lookup without a large derived file in review.
"""
import argparse
import csv
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_IFR = os.path.join(REPO, "bios", "ifr", "Setup.en-US.ifr.txt")
DEFAULT_CSV = os.path.join(REPO, "bios", "ifr", "charge-questions.csv")

# --------------------------------------------------------------------------
# The vocabulary, and what it is not
# --------------------------------------------------------------------------

# A phrase matches when it appears inside a word of the prompt, the help or an
# option label, case-insensitively -- so `charg` is one stem that catches charge,
# charger and charging, and `ac brick` is two words that have to be adjacent.
# The alternative, a bare `ac`, matches thousands of lines of noise (see
# --list-excluded), and the point of a committed list is that a reader can see
# what was asked for rather than having to trust a substring.
CHARGE_TERMS = ("battery", "charg", "flexicharge", "ac brick", "ac power")

# The looser probe behind --list-excluded. It is not the matcher; it exists so
# the rows this tool declined stay printable. A row that trips one of these and
# not CHARGE_TERMS is a question whose prompt, help or option names an AC, a
# power, an adapter or a battery that the phrase list does not.
NEAR_MISS_PROBE = ("ac", "pow", "adapter", "batter", "charg")

# Rows the phrase list matches that are not charge controls. Named here rather
# than left to the reader to sort, because the write-up gives them their own
# section and a split that exists only in prose cannot be checked. Keyed by
# question id, which is unique within one dump; another dump is another key
# space and these two names are re-read per run.
#
# `Boot performance mode` matches on the option label "Max Battery", a
# performance state the firmware picks at reset. `DeepSx Power Policies` matches
# on the option "Enabled in S4-S5/Battery", a deep-sleep policy for the S4-S5
# states. Both contain a charge word and neither controls charging.
NOT_CHARGE = {
    "0xFA": "performance-state option label, not a charge control",
    "0x705": "S4-S5 deep-sleep policy option label, not a charge control",
}

CSV_COLUMNS = [
    "question_id", "kind", "prompt", "help", "form_chain",
    "varstore", "varstore_guid", "varstore_id", "offset", "size_bits",
    "default_normal", "default_mfg", "options",
    "suppress_if", "gray_out_if", "condition_question_ids",
    "matched_term", "matched_field", "verdict", "ifr_line",
]

# --------------------------------------------------------------------------
# Reading ifrextractor's verbose output
# --------------------------------------------------------------------------

# "0x2D498: <tab>FormSet ...". The address prefix is what separates a statement
# from a continuation, because a help string may contain bare CRs and
# ifrextractor breaks the line across them. Indentation is tabs; the space after
# the colon is not one of them, hence `[ ]*` before the tab run.
STATEMENT = re.compile(r"^(0x[0-9A-F]+):[ ]*((?:\t)*)(.*)$")

# A quoted field, with the backslash escapes the format uses. The dump's help
# strings contain embedded CRs and quotes, so a naive `"([^"]*)"` truncates at
# the wrong place on several hundred lines.
QUOTED = r'"((?:[^"\\]|\\.)*)"'

# `Name: value` at the start of a field. Anchored there rather than searched
# for, because a help string is free to contain the words another field uses.
FIELD_HEAD = re.compile(r"([A-Za-z][A-Za-z0-9_]*):[ ]*")

# The byte block ifrextractor appends to every statement, and only ever at the
# end. Stripped from each field's value so `Value: 0x1 { 12 86 17 0E 01 00 }`
# reads as `0x1`. The pattern insists on pairs of hex digits, because a help
# string may legitimately end in a brace.
BYTE_BLOCK = re.compile(r"[ ]*\{[ ]*(?:[0-9A-Fa-f]{2}[ ]*)+\}[ ]*$")


def split_fields(body):
    """`Opcode K: v, K: v, ... { bytes }` as a dict of name to raw value.

    Split on the `, ` that separates fields, skipping the ones inside a quoted
    string. Several hundred help strings in this dump contain a comma of their
    own, so `body.split(", ")` truncates them; a plain `re.search` for
    `Prompt: ` fails the other way, because a prompt is the first field after
    the opcode and no comma separates it from the opcode.

    A chunk that carries no `Name:` is dropped rather than guessed at, which is
    what makes the trailing `, Default, MfgDefault` of a `OneOfOption` safe to
    pass over here: `OPTION` reads that line separately, because its
    `Option:`/`Value:` share one comma-run and this split cannot separate them.
    """
    parts = body.split(" ", 1)
    rest = parts[1] if len(parts) > 1 else ""
    commas, depth, in_quotes, i = [], 0, False, 0
    while i < len(rest):
        ch = rest[i]
        if ch == '"' and rest[i - 1:i] != "\\":
            in_quotes = not in_quotes
        elif in_quotes:
            pass
        elif ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        elif ch == "," and depth == 0 and rest[i + 1:i + 2] == " ":
            # depth, not just quoting: `EqIdValList ... Values: [1, 2]` carries
            # a comma of its own inside the brackets, and splitting there would
            # leave the value reading `[1`.
            commas.append(i)
        i += 1
    out = {}
    for start, end in zip([0] + [c + 2 for c in commas], commas + [len(rest)]):
        chunk = rest[start:end]
        m = FIELD_HEAD.match(chunk)
        if m:
            out[m.group(1)] = BYTE_BLOCK.sub("", chunk[m.end():]).strip()
    return out


# The statement kinds that carry a `QuestionId` and a `VarOffset` -- a question
# that reads or writes a byte of a variable store. `Ref` has a QuestionId and a
# FormId and no VarOffset: it links to a question in another form rather than
# addressing a variable of its own.
STORE_QUESTIONS = ("OneOf", "Numeric", "Text", "CheckBox", "Uint8", "Uint16",
                   "Uint64", "Password", "Subtitle")

# The blocks a question's visibility is decided by. `DisableIf` and
# `InconsistentIf` disable rather than hide, and `WarningIf` is a message, but
# they are the same grammar in the same nesting, so one rule reads all five.
CONDITION_BLOCKS = ("SuppressIf", "GrayOutIf", "DisableIf", "InconsistentIf",
                    "WarningIf")

# Condition-buffer opcodes. The buffer is a stack machine, not a tree: each
# pusher appends a value, `Not` pops one, the binary operators pop two, and
# what is left is the condition. The comparators are binary operators in the
# same sense `And` is -- EFI_IFR_OPCODE_LESSTHAN consumes the two values below
# it -- so they are modelled the same way and render with their own name.
CONDITION_PUSHERS = {
    "True": "TRUE",
    "False": "FALSE",
    "EqIdVal": "EqIdVal QuestionId: {qid}, Value: {val}",
    "EqIdValList": "EqIdValList QuestionId: {qid}, Values: {vals}",
    "EqIdId": "EqIdId QuestionId: {qid}, OtherQuestionId: {other}",
    "QuestionRef1": "QuestionRef1 QuestionId: {qid}",
    "StringRef1": "StringRef1 String: {s}",
}
CONDITION_UNARY = {"Not": "NOT"}
CONDITION_BINARY = {"And": "AND", "Or": "OR", "Equal": "EQUAL",
                    "LessThan": "LESS THAN", "LessEqual": "LESS EQUAL",
                    "GreaterEqual": "GREATER EQUAL", "Match": "MATCH"}
CONDITION_OPS = frozenset(list(CONDITION_PUSHERS) + list(CONDITION_UNARY) +
                          list(CONDITION_BINARY))


class Statement(object):
    """One ifrextractor line, its continuations joined and its parts read.

    `line` is the 1-based number the statement starts on as `grep -n` counts
    it. The dump is read with newline translation off for that reason: 7 of its
    lines end in a bare CR inside a help string, and Python's default text mode
    turns each of those into a line break as well, so a reader in that mode
    numbers every citation past `grep` line 8441 seven lower than this does.
    """

    __slots__ = ("line", "depth", "body", "opcode", "fields")

    def __init__(self, line, depth, parts):
        self.line = line
        self.depth = depth
        self.body = "".join(parts)
        self.opcode = self.body.split(" ", 1)[0].split(":", 1)[0]
        # After the join, never before: 400 questions in the Setup dump have a
        # help string that wraps onto the next line, and every field of theirs
        # sits after the wrap.
        self.fields = split_fields(self.body)

    def field(self, name):
        """A `Name: value` scalar, e.g. `VarOffset: 0x4F3`. '' when absent."""
        return self.fields.get(name, "")

    def quoted(self, name):
        """A `Name: "..."` string, with the format's escapes left as written."""
        m = re.search(QUOTED, self.fields.get(name, ""))
        return m.group(1) if m else ""

    def question_id(self):
        return self.fields.get("QuestionId", "")


def read_statements(lines):
    """Statements from the dump's lines, continuations joined onto their head.

    A line that starts with an address is a statement; one that does not is the
    tail of the statement above it, which is what a help string wrapped over a
    CR looks like once it is in the file.

    Every CR becomes a space, once, here. 1,717 of the 1,724 CRs in the Setup
    dump are the first half of a CRLF, and 7 are a bare CR that ifrextractor
    wrote inside a help string; the space keeps the two halves of a wrapped
    sentence apart when they are joined, and keeps a CR out of the committed
    CSV's help column.
    """
    out, head = [], None
    for n, line in enumerate(lines, 1):
        line = line.replace("\r", " ")
        m = STATEMENT.match(line)
        if m:
            if head is not None:
                out.append(Statement(*head))
            head = (n, len(m.group(2)), [m.group(3)])
        elif head is not None:
            head[2].append(line)
    if head is not None:
        out.append(Statement(*head))
    return out


def read_dump(path):
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        return read_statements(f.read().split("\n"))


def varstores(statements):
    """VarStoreId -> (name, guid, size), from the `VarStore` lines."""
    out = {}
    for s in statements:
        if s.opcode != "VarStore":
            continue
        out[int(s.field("VarStoreId") or "0", 0)] = (s.quoted("Name"),
                                                     s.field("Guid"),
                                                     s.field("Size"))
    return out


def block_spans(statements):
    """(start, end) statement index for every block that opens with a brace.

    The end is the first statement at the opener's own depth or shallower. The
    dump's `End` lines are not the arbiter: on this ROM there are 6,992 of them
    against 7,189 block openers, so they do not balance and the depth is what
    decides. A `SuppressIf` inside a `SuppressIf` therefore gets both, and a
    question inside the inner one is inside the outer one too.
    """
    spans = {}
    for i, stmt in enumerate(statements):
        j = i + 1
        while j < len(statements) and statements[j].depth > stmt.depth:
            j += 1
        spans[i] = j
    return spans


# --------------------------------------------------------------------------
# The condition buffer
# --------------------------------------------------------------------------

class Expr(object):
    """One resolved condition: its text, and the QuestionIds it refers to.

    `resolved` is False when any opcode in the stream was one this tool does not
    model, and the text then carries a `?(...)` node naming it. The flag is
    counted and printed on every run, so a partially-read condition cannot read
    as a fully-read one.
    """

    __slots__ = ("text", "question_ids", "resolved")

    def __init__(self, text, question_ids, resolved):
        self.text = text
        self.question_ids = question_ids
        self.resolved = resolved

    def unmodelled(self):
        return "?" in self.text


def pusher_text(stmt):
    """The readable form of one pusher, or None when it is not a pusher."""
    template = CONDITION_PUSHERS.get(stmt.opcode)
    if template is None:
        return None, []
    if stmt.opcode in ("True", "False"):
        return template, []
    qid = stmt.question_id()
    if stmt.opcode == "EqIdValList":
        return (template.format(qid=qid, vals=stmt.field("Values")),
                [qid] if qid else [])
    if stmt.opcode == "EqIdId":
        other = stmt.field("OtherQuestionId")
        return template.format(qid=qid, other=other), [x for x in (qid, other) if x]
    if stmt.opcode == "StringRef1":
        return template.format(s=stmt.quoted("String")), []
    if stmt.opcode == "QuestionRef1":
        return template.format(qid=qid), [qid] if qid else []
    return template.format(qid=qid, val=stmt.field("Value")), [qid] if qid else []


def condition_expr(statements, start):
    """The condition of the block opening at `start`, or None.

    The buffer is the *contiguous run* of condition opcodes after the opener.
    Contiguity is what makes it right, and it is load-bearing rather than a
    shortcut: a question's own `Default ... Value: Other` can carry a second
    expression, nested inside a `SuppressIf` that gates that very question, and
    a scan that kept descending by depth would fold the default's operands into
    the visibility condition. The run ends at the first statement that is not a
    condition opcode, which is the question.
    """
    stack = []
    for stmt in statements[start + 1:]:
        if stmt.opcode not in CONDITION_OPS:
            break
        if stmt.opcode in CONDITION_UNARY:
            if not stack:
                return Expr("?(unresolved: %s with an empty stack)"
                            % stmt.opcode, [], False)
            operand = stack.pop()
            stack.append(Expr("%s (%s)" % (CONDITION_UNARY[stmt.opcode],
                                           operand.text),
                              operand.question_ids, operand.resolved))
        elif stmt.opcode in CONDITION_BINARY:
            if len(stack) < 2:
                return Expr("?(unresolved: %s with %d value(s) on the stack)"
                            % (stmt.opcode, len(stack)), [], False)
            right, left = stack.pop(), stack.pop()
            stack.append(Expr("(%s %s %s)" % (left.text,
                                              CONDITION_BINARY[stmt.opcode],
                                              right.text),
                              left.question_ids + right.question_ids,
                              left.resolved and right.resolved))
        else:
            text, qids = pusher_text(stmt)
            stack.append(Expr(text, qids, True))
    if not stack:
        # An unconditional SuppressIf does appear in the dump. Returning None
        # says "this block states no condition", which is what it states;
        # printing TRUE would be a claim it does not make.
        return None
    if len(stack) > 1:
        return Expr("?(unresolved: %d values left on the stack)" % len(stack),
                    [], False)
    return stack[0]


# --------------------------------------------------------------------------
# Questions
# --------------------------------------------------------------------------

class Question(object):
    """One question that reads or writes a byte of a variable store."""

    __slots__ = ("stmt", "index", "options", "defaults", "suppress", "gray",
                 "form_chain", "terms", "verdict", "condition_ids")

    def __init__(self, stmt, index):
        self.stmt = stmt
        self.index = index
        self.options = []       # (label, value, is_default, is_mfg)
        self.defaults = {}      # DefaultId -> value, from `Default` statements
        self.suppress = []      # enclosing and nested, outermost first
        self.gray = []
        self.form_chain = ""
        self.terms = []         # (phrase, field) for each CHARGE_TERMS hit
        self.verdict = ""
        self.condition_ids = []

    def text_fields(self):
        """(field, text) for everything a phrase is matched against."""
        return ([("prompt", self.stmt.quoted("Prompt")),
                 ("help", self.stmt.quoted("Help"))]
                + [("option", label) for label, _, _, _ in self.options])

    def row(self, stores):
        """The CSV row. Every column is derived; none is typed in by hand."""
        store_id = int(self.stmt.field("VarStoreId") or "0", 0)
        name, guid, _ = stores.get(store_id, ("", "", ""))
        default_normal = str(self.defaults[0]) if 0 in self.defaults else ""
        default_mfg = str(self.defaults[1]) if 1 in self.defaults else ""
        for _, value, is_default, is_mfg in self.options:
            # A OneOf states its default on the option rather than in a `Default`
            # statement of its own, so the fallback is where most of this
            # column's values come from.
            if is_default and not default_normal:
                default_normal = str(value)
            if is_mfg and not default_mfg:
                default_mfg = str(value)
        terms = self.terms[0] if self.terms else ("", "")
        return {
            "question_id": self.stmt.question_id(),
            "kind": self.stmt.opcode,
            "prompt": self.stmt.quoted("Prompt"),
            "help": self.stmt.quoted("Help"),
            "form_chain": self.form_chain,
            "varstore": name,
            "varstore_guid": guid,
            "varstore_id": self.stmt.field("VarStoreId"),
            "offset": self.stmt.field("VarOffset"),
            "size_bits": self.stmt.field("Size"),
            "default_normal": default_normal,
            "default_mfg": default_mfg,
            "options": "; ".join(
                "%s=%d%s%s" % (label, value, " [default]" if is_default else "",
                               " [mfg]" if is_mfg else "")
                for label, value, is_default, is_mfg in self.options),
            "suppress_if": "; ".join(e.text for e in self.suppress),
            "gray_out_if": "; ".join(e.text for e in self.gray),
            "condition_question_ids": "; ".join(self.condition_ids),
            "matched_term": terms[0],
            "matched_field": terms[1],
            "verdict": self.verdict,
            "ifr_line": str(self.stmt.line),
        }


OPTION = re.compile(r"^OneOfOption Option: %s Value: (\d+)(.*)$" % QUOTED)

# `Default DefaultId: 0x0 Value: 8` -- no comma between the two fields, so the
# comma-split above reads `DefaultId` as "0x0 Value: 8". One of the two shapes
# in the format that is not comma-separated; `OneOfOption` is the other, and
# OPTION above is its half.
DEFAULT = re.compile(r"^Default DefaultId: (0x[0-9A-F]+) Value: (\S+)")


def default_of(stmt):
    """(DefaultId, Value) from a `Default` statement, or None.

    `Value: Other` means the default is the expression in the statements that
    follow rather than a number, and the CSV's default columns are numbers, so
    that case is reported as no value at all rather than as the word "Other".
    """
    m = DEFAULT.match(stmt.body)
    if not m or m.group(2) == "Other":
        return None
    return m.group(1), m.group(2)


def phrase_in(text, phrase):
    """True when `phrase` appears inside a word of `text`, case-insensitively."""
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase), text or "",
                     re.I) is not None


def census(statements):
    """(varstores, questions) for one dump.

    A question collects three things: its own block (options, `Default`
    statements, and any condition nested between it and one of its options), the
    condition blocks that enclose it, and the form chain it sits under. The
    enclosing conditions are gathered by span rather than by a "current block"
    cursor, because a `SuppressIf` inside a `SuppressIf` has to give the
    question both and a single cursor would give it one.
    """
    stores = varstores(statements)
    spans = block_spans(statements)
    questions = []
    for i, stmt in enumerate(statements):
        if stmt.opcode not in STORE_QUESTIONS or not stmt.field("VarOffset"):
            continue
        q = Question(stmt, i)
        for j in range(i + 1, spans[i]):
            child = statements[j]
            m = OPTION.match(child.body)
            if m:
                flags = m.group(3)
                q.options.append((m.group(1), int(m.group(2)),
                                  "Default" in flags, "MfgDefault" in flags))
            elif child.opcode == "Default":
                given = default_of(child)
                if given is not None:
                    q.defaults[int(given[0], 0)] = int(given[1], 0)
            elif child.opcode in CONDITION_BLOCKS:
                expr = condition_expr(statements, j)
                if expr is not None:
                    (q.gray if child.opcode == "GrayOutIf" else
                     q.suppress).append(expr)
                    q.condition_ids.extend(expr.question_ids)
        # Enclosing conditions, outermost first, from the block spans rather
        # than from a depth comparison alone: a `SuppressIf` at a shallower
        # depth that some intervening block has already closed is not an
        # ancestor, and only the span knows that.
        enclosing = [(statements[j].depth, j) for j in range(i)
                     if statements[j].opcode in CONDITION_BLOCKS
                     and j < spans[j] and i < spans[j]]
        enclosing.sort(reverse=True)
        for _, j in enclosing:
            expr = condition_expr(statements, j)
            if expr is None or expr in q.suppress or expr in q.gray:
                continue
            (q.gray if statements[j].opcode == "GrayOutIf" else
             q.suppress).append(expr)
            q.condition_ids.extend(expr.question_ids)
        q.form_chain = form_chain(statements, i)
        q.terms = [(phrase, field) for phrase in CHARGE_TERMS
                   for field, text in q.text_fields() if phrase_in(text, phrase)]
        q.verdict = ("matched-not-a-charge-option" if q.terms and
                     q.stmt.question_id() in NOT_CHARGE else
                     "charge-option" if q.terms else "")
        questions.append(q)
    return stores, questions


def form_chain(statements, index):
    """`FormSet title / Form title`, the menu path a question sits under."""
    forms = []
    for j in range(index - 1, -1, -1):
        stmt = statements[j]
        if stmt.opcode == "Form" and stmt.depth == 1 and not forms:
            forms.append("%s (FormId 0x%s)" % (stmt.quoted("Title"),
                                               stmt.field("FormId")[2:]))
        if stmt.opcode == "FormSet":
            return " / ".join([stmt.quoted("Title")] + forms)
    return ""


def charge_rows(questions):
    """The rows the CSV is: every question the phrase list matched."""
    return [q for q in questions if q.terms]


def unresolved(questions):
    """Every condition text carrying a `?(...)` node, for the run's count."""
    out = []
    for q in questions:
        for expr in q.suppress + q.gray:
            if expr.unmodelled() and expr not in out:
                out.append(expr)
    return out


# --------------------------------------------------------------------------
# The committed census
# --------------------------------------------------------------------------

def render_csv(rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def derive(args):
    stores, questions = census(read_dump(args.ifr))
    return stores, questions, render_csv(
        [q.row(stores) for q in charge_rows(questions)])


def write(args):
    _, _, text = derive(args)
    path = os.path.abspath(args.csv)
    with open(path, "w", newline="") as f:
        f.write(text)
    print("wrote %s: %d row(s)"
          % (os.path.relpath(path, REPO), len(text.splitlines()) - 1))
    return 0


def check(args):
    """The `--check` half: the committed CSV is what this tool derives.

    A missing file is a failure rather than a "would create", because the file
    is derived from a committed input and its absence is a hole in the tree, not
    a state a verification run should repair.
    """
    path = os.path.abspath(args.csv)
    if not os.path.isfile(path):
        print("error: no %s. It is derived from %s; run --write."
              % (os.path.relpath(path, REPO), os.path.relpath(args.ifr, REPO)))
        return 1
    _, _, text = derive(args)
    with open(path, newline="") as f:
        on_disk = f.read()
    if on_disk == text:
        print("%s: %d row(s), unchanged"
              % (os.path.relpath(path, REPO), len(text.splitlines()) - 1))
        return 0
    want, have = text.splitlines(), on_disk.splitlines()
    print("error: %s is not what %s derives."
          % (os.path.relpath(path, REPO), os.path.basename(args.ifr)))
    for n, (a, b) in enumerate(zip(have, want)):
        if a != b:
            print("  line %d\n    committed: %s\n    derived:   %s"
                  % (n + 1, a, b))
            break
    if len(have) != len(want):
        print("  %d committed line(s), %d derived" % (len(have), len(want)))
    print("  If the derivation is the one that should stand, run --write.")
    return 1


# --------------------------------------------------------------------------
# Printing
# --------------------------------------------------------------------------

def print_census(args, statements, stores, questions):
    rows = charge_rows(questions)
    print("%s" % os.path.relpath(args.ifr, REPO))
    print("%d statement(s), %d form(s), %d store question(s), %d link(s), "
          "%d varstore(s)" % (len(statements),
                              sum(1 for s in statements if s.opcode == "Form"),
                              len(questions),
                              sum(1 for s in statements
                                  if s.opcode == "Ref" and s.question_id()),
                              len(stores)))
    print("%d matched %s" % (len(rows), " or ".join(CHARGE_TERMS)))
    if not rows:
        print()
        print("No question's prompt, help or option label matched the phrase "
              "list. That is what this list found against this file, not a "
              "claim that the dump holds no such question: widen CHARGE_TERMS, "
              "or use --match.")
        return 0
    for q in rows:
        print_row(q, stores)
    report_conditions(questions)
    return 0


def report_conditions(questions):
    left = unresolved(questions)
    print()
    if left:
        print("%d condition expression(s) carry an opcode this tool does not "
              "model and are shown as ?(...):" % len(left))
        for expr in left:
            print("  %s" % expr.text)
    else:
        print("every condition this run resolved was read in full.")


def print_row(q, stores):
    row = q.row(stores)
    print()
    print("  %s" % (row["prompt"] or "(no prompt)"))
    print("    Qid %s  %s  %s[%s]  %s-bit  line %s"
          % (row["question_id"], row["kind"], row["varstore"] or "?",
             row["offset"], row["size_bits"], row["ifr_line"]))
    print("    form      %s" % (row["form_chain"] or "?"))
    print("    store     %s  %s  id %s"
          % (row["varstore"], row["varstore_guid"], row["varstore_id"]))
    # `== ""` rather than `or`: a default of 0 is a default, and `0 or "-"`
    # printed the dash for every question whose IFR default is zero.
    print("    IFR default  normal %s, mfg %s"
          % (row["default_normal"] if row["default_normal"] != "" else "-",
             row["default_mfg"] if row["default_mfg"] != "" else "-"))
    for label, value, is_default, is_mfg in q.options:
        print("      option  %-28s = %d%s%s"
              % (label, value, "  [default]" if is_default else "",
                 "  [mfg]" if is_mfg else ""))
    for expr in q.suppress:
        print("    SuppressIf  %s" % expr.text)
    for expr in q.gray:
        print("    GrayOutIf   %s" % expr.text)
    if row["condition_question_ids"]:
        print("    condition reads  %s" % row["condition_question_ids"])
    if q.terms:
        print("    matched    %r in the %s"
              % (q.terms[0][0], q.terms[0][1]))
    print("    verdict    %s" % (q.verdict or "-"))
    if q.stmt.question_id() in NOT_CHARGE:
        print("    note       %s" % NOT_CHARGE[q.stmt.question_id()])


def print_excluded(args, questions):
    """The rows a looser probe would have caught and CHARGE_TERMS declined.

    Printed rather than counted, because the exclusion is the part of a
    committed vocabulary most worth arguing with and a count is not arguable.
    """
    declined = []
    for q in questions:
        if q.terms:
            continue
        hit = [(probe, field) for probe in NEAR_MISS_PROBE
               for field, text in q.text_fields() if phrase_in(text, probe)]
        if hit:
            declined.append((q, hit))
    print("%d question(s) trip %s and none of %s."
          % (len(declined), " / ".join(repr(p) for p in NEAR_MISS_PROBE),
             " / ".join(CHARGE_TERMS)))
    for q, hit in declined:
        print("  %-7s %-44s %s"
              % (q.stmt.question_id(),
                 (q.stmt.quoted("Prompt") or "(no prompt)")[:44],
                 ", ".join("%r in %s" % (p, f) for p, f in hit[:4])))
    return 0


def print_match(args, stores, questions):
    pattern = re.compile(args.match, re.I)
    hits = [q for q in questions
            if any(pattern.search(text) for _, text in q.text_fields())]
    print("%d question(s) matching /%s/" % (len(hits), args.match))
    for q in hits:
        print_row(q, stores)
    if not hits:
        print("Nothing in this dump matched. That is what the pattern found "
              "against this file, not a claim about any other.")
    return 0


def print_offset(args, stores, questions):
    if ":" not in args.offset:
        raise SystemExit("error: --offset wants <varstore>:<offset>, e.g. "
                         "Setup:0x4F3. Got %r." % args.offset)
    name, _, want = args.offset.rpartition(":")
    hits = [q for q in questions
            if q.row(stores)["varstore"].lower() == name.lower()
            and q.row(stores)["offset"].lower() == want.lower()]
    if not hits:
        print("No question in this dump writes %s. `grep -n 'QuestionId: "
              "0x…, VarStoreId' %s` shows what is there."
              % (args.offset, os.path.relpath(args.ifr, REPO)))
        return 0
    for q in hits:
        print_row(q, stores)
    return 0


def print_question(args, stores, questions):
    want = args.question.lower()
    hits = [q for q in questions if q.stmt.question_id().lower() == want]
    if not hits:
        print("No question with id %s in this dump." % args.question)
        return 0
    for q in hits:
        print_row(q, stores)
    return 0


# --------------------------------------------------------------------------
# The self-test
# --------------------------------------------------------------------------

# A hand-built IFR holding one case per thing the tool has to get right: a
# question under a `SuppressIf` whose condition is a stack expression rather
# than a tree; a question under a `GrayOutIf`, which is a different visibility
# rule and must not be reported as suppressed; a question whose only charge word
# is in its help; a question whose only charge word is in an option label, and
# which the committed exclusion therefore rules out of the charge count; a
# `Default ... Value: Other` nested inside the very `SuppressIf` that gates its
# question, which a depth-walking scan would fold into the visibility condition;
# the near-misses the vocabulary has to decline; and the hidden empty-prompt
# numeric the `EqIdVal` conditions point at.
FIXTURE = "\n".join([
    'Program version: 1.6.1, Extraction mode: UEFI, SHA256: 0000',
    '0x100: FormSet Guid: 11111111-1111-1111-1111-111111111111, Title: "Setup", Help: "Setup" { 01 }',
    '0x110: \tVarStore Guid: 22222222-2222-2222-2222-222222222222, VarStoreId: 0x1, Size: 0x10, Name: "Setup" { 02 }',
    '0x120: \tVarStore Guid: 33333333-3333-3333-3333-333333333333, VarStoreId: 0x37, Size: 0x8, Name: "SetupVolatileData" { 03 }',
    '0x130: \tForm FormId: 0x2791, Title: "Platform Settings" { 04 }',
    '0x140: \t\tNumeric Prompt: "", Help: "", QuestionFlags: 0x0, QuestionId: 0xE17, VarStoreId: 0x37, VarOffset: 0x4, Flags: 0x10, Size: 8, Min: 0x0, Max: 0xFF, Step: 0x0 { 05 }',
    '0x150: \t\t\tDefault DefaultId: 0x0 Value: 1 { 06 }',
    '0x160: \t\tEnd  { 07 }',
    '0x170: \t\tSuppressIf  { 08 }',
    '0x180: \t\t\tEqIdVal QuestionId: 0xE17, Value: 0x1 { 09 }',
    '0x190: \t\t\t\tNot  { 0A }',
    '0x1A0: \t\t\t\tEqIdVal QuestionId: 0xE17, Value: 0x5 { 0B }',
    '0x1B0: \t\t\t\tNot  { 0C }',
    '0x1C0: \t\t\t\tAnd  { 0D }',
    '0x1D0: \t\t\tEnd  { 0E }',
    '0x1E0: \t\t\tOneOf Prompt: "Charging Method", Help: "Select charging method as Normal Charging or Fast Charging.", QuestionFlags: 0x10, QuestionId: 0x2A6, VarStoreId: 0x1, VarOffset: 0x4F3, Flags: 0x10, Size: 8, Min: 0x0, Max: 0x1, Step: 0x0 { 0F }',
    '0x1F0: \t\t\t\tOneOfOption Option: "Normal Charging" Value: 0, Default, MfgDefault { 10 }',
    '0x200: \t\t\t\tOneOfOption Option: "Fast Charging" Value: 1 { 11 }',
    '0x210: \t\t\tEnd  { 12 }',
    '0x220: \t\tEnd  { 13 }',
    '0x230: \tGrayOutIf  { 14 }',
    '0x240: \t\t\tEqIdValList QuestionId: 0xE17, Values: [1, 2] { 15 }',
    '0x250: \t\tOneOf Prompt: "Light Bar Effect", Help: "If remove AC power, USB light Bar will be disabled", QuestionFlags: 0x14, QuestionId: 0x29E9, VarStoreId: 0x1, VarOffset: 0x740, Flags: 0x10, Size: 8, Min: 0x0, Max: 0x1, Step: 0x0 { 16 }',
    '0x260: \t\t\tOneOfOption Option: "Off" Value: 0, Default { 17 }',
    '0x270: \t\t\tOneOfOption Option: "Steady" Value: 1 { 18 }',
    '0x280: \t\tEnd  { 19 }',
    '0x290: \tEnd  { 1A }',
    '0x2A0: \tForm FormId: 0x2743, Title: "CPU - Power Management Control" { 1B }',
    '0x2B0: \t\tOneOf Prompt: "Boot performance mode", Help: "Select the performance state.", QuestionFlags: 0x10, QuestionId: 0xFA, VarStoreId: 0x1, VarOffset: 0xE, Flags: 0x10, Size: 8, Min: 0x0, Max: 0x1, Step: 0x0 { 1C }',
    '0x2C0: \t\t\tOneOfOption Option: "Max Power" Value: 0, Default { 1D }',
    '0x2D0: \t\t\tOneOfOption Option: "Max Battery" Value: 1 { 1E }',
    '0x2E0: \t\tEnd  { 1F }',
    '0x2F0: \t\tOneOf Prompt: "  AC Loadline Time", Help: "A VR setting.", QuestionFlags: 0x10, QuestionId: 0x901, VarStoreId: 0x1, VarOffset: 0x10, Flags: 0x10, Size: 8, Min: 0x0, Max: 0x1, Step: 0x0 { 20 }',
    '0x300: \t\t\tOneOfOption Option: "Disabled" Value: 0, Default { 21 }',
    '0x310: \t\t\tOneOfOption Option: "Enabled" Value: 1 { 22 }',
    '0x320: \t\tEnd  { 23 }',
    '0x330: \t\tOneOf Prompt: "PCIe Adapter D0/F1", Help: "A constraint.", QuestionFlags: 0x10, QuestionId: 0x903, VarStoreId: 0x1, VarOffset: 0x12, Flags: 0x10, Size: 8, Min: 0x0, Max: 0x1, Step: 0x0 { 24 }',
    '0x340: \t\t\tOneOfOption Option: "Disabled" Value: 0, Default { 25 }',
    '0x350: \t\t\tOneOfOption Option: "Enabled" Value: 1 { 26 }',
    '0x360: \t\tEnd  { 27 }',
    '0x370: \tEnd  { 28 }',
    '0x380: \tSuppressIf  { 29 }',
    '0x390: \t\tEqIdVal QuestionId: 0xE17, Value: 0x2 { 2A }',
    '0x3A0: \t\tOneOf Prompt: "  ACPI Thermal Trip Point", Help: "A trip point.", QuestionFlags: 0x10, QuestionId: 0x902, VarStoreId: 0x1, VarOffset: 0x11, Flags: 0x10, Size: 8, Min: 0x0, Max: 0x1, Step: 0x0 { 2B }',
    '0x3B0: \t\t\tDefault DefaultId: 0x0 Value: Other { 2C }',
    '0x3C0: \t\t\t\tValue  { 2D }',
    '0x3D0: \t\t\t\t\tEqIdValList QuestionId: 0xE17, Values: [1, 2] { 2E }',
    '0x3E0: \t\t\t\t\tUint64 Value: 0x0 { 2F }',
    '0x3F0: \t\t\t\t\tUint64 Value: 0x1 { 30 }',
    '0x400: \t\t\t\t\tConditional  { 31 }',
    '0x410: \t\t\t\tEnd  { 32 }',
    '0x420: \t\t\tEnd  { 33 }',
    '0x430: \t\tEnd  { 34 }',
    '',
])


def self_test():
    stores, questions = census(read_statements(FIXTURE.split("\n")))
    by_id = dict((q.stmt.question_id(), q) for q in questions)
    problems = []

    def want(cond, message):
        if not cond:
            problems.append(message)

    want(len(questions) == 7,
         "the fixture should yield 7 store questions, got %d" % len(questions))
    want(stores.get(0x1, ("",))[0] == "Setup",
         "VarStoreId 0x1 should resolve to Setup, got %r" % (stores.get(0x1),))
    want(stores.get(0x37, ("",))[0] == "SetupVolatileData",
         "VarStoreId 0x37 should resolve to SetupVolatileData, got %r"
         % (stores.get(0x37),))

    charging = by_id.get("0x2A6")
    want(charging is not None, "the fixture's Charging Method did not parse")
    if charging:
        row = charging.row(stores)
        want(row["offset"] == "0x4F3" and row["varstore"] == "Setup",
             "Charging Method should be Setup[0x4F3], got %s[%s]"
             % (row["varstore"], row["offset"]))
        want(row["default_normal"] == "0" and row["default_mfg"] == "0",
             "Charging Method's default should come from the option flagged "
             "Default/MfgDefault, got normal %r mfg %r"
             % (row["default_normal"], row["default_mfg"]))
        # The stack reading: EqIdVal, Not, EqIdVal, Not, And leaves one value
        # that is NOT(0xE17==1) AND NOT(0xE17==5). Read as a tree by
        # indentation the two `Not`s come out as siblings and the And binds
        # nothing, which is the mistake this tool exists not to make.
        want(len(charging.suppress) == 1,
             "Charging Method should sit under exactly 1 SuppressIf, got %d"
             % len(charging.suppress))
        want(charging.suppress and charging.suppress[0].text ==
             "(NOT (EqIdVal QuestionId: 0xE17, Value: 0x1) AND "
             "NOT (EqIdVal QuestionId: 0xE17, Value: 0x5))",
             "Charging Method's condition resolved to %r"
             % (charging.suppress[0].text if charging.suppress else None))
        want(charging.condition_ids == ["0xE17", "0xE17"],
             "the condition should name 0xE17 twice, got %r"
             % charging.condition_ids)
        want(charging.verdict == "charge-option",
             "Charging Method's verdict should be charge-option, got %r"
             % charging.verdict)
        want(charging.terms == [("charg", "prompt"), ("charg", "help"),
                                ("charg", "option"), ("charg", "option")],
             "Charging Method should match 'charg' in prompt, help and both "
             "options, got %r" % charging.terms)

    # ... and 0xE17 is the hidden empty-prompt numeric at SetupVolatileData 0x4,
    # which is what the first row of the committed census turns on.
    hidden = by_id.get("0xE17")
    want(hidden is not None and hidden.stmt.quoted("Prompt") == ""
         and hidden.row(stores)["varstore"] == "SetupVolatileData"
         and hidden.row(stores)["offset"] == "0x4",
         "the hidden empty-prompt numeric at SetupVolatileData 0x4 did not "
         "resolve")

    lightbar = by_id.get("0x29E9")
    want(lightbar is not None, "the fixture's Light Bar Effect did not parse")
    if lightbar:
        want(lightbar.terms == [("ac power", "help")],
             "Light Bar Effect should match 'ac power' in its help, got %r"
             % lightbar.terms)
        want(len(lightbar.gray) == 1 and not lightbar.suppress,
             "Light Bar Effect is under a GrayOutIf and nothing else; got %d "
             "gray, %d suppress" % (len(lightbar.gray), len(lightbar.suppress)))
        want(lightbar.gray and lightbar.gray[0].text ==
             "EqIdValList QuestionId: 0xE17, Values: [1, 2]",
             "the GrayOutIf resolved to %r"
             % (lightbar.gray[0].text if lightbar.gray else None))
        want(lightbar.verdict == "charge-option",
             "Light Bar Effect's verdict should be charge-option, got %r"
             % lightbar.verdict)

    # The option-label match, and the exclusion that goes with it: a question
    # whose only charge word is in an option value matches, and `Max Battery` is
    # a performance state rather than a charge control.
    boot = by_id.get("0xFA")
    want(boot is not None, "the fixture's Boot performance mode did not parse")
    if boot:
        want(boot.terms == [("battery", "option")],
             "Boot performance mode should match 'battery' in an option, got %r"
             % boot.terms)
        want(boot.verdict == "matched-not-a-charge-option",
             "Boot performance mode is named in NOT_CHARGE and its verdict "
             "should say so, got %r" % boot.verdict)

    # A `Default ... Value: Other` carries its own expression, nested inside the
    # `SuppressIf` that gates the very question it belongs to. A scan that
    # descended by depth would read that expression as part of the visibility
    # condition; the contiguous run stops at the question.
    acpi = by_id.get("0x902")
    want(acpi is not None, "the fixture's ACPI question did not parse")
    if acpi:
        want(acpi.suppress and acpi.suppress[0].text ==
             "EqIdVal QuestionId: 0xE17, Value: 0x2",
             "the ACPI question's SuppressIf resolved to %r -- the Default's "
             "own expression leaked into it"
             % (acpi.suppress[0].text if acpi.suppress else None))
        want(acpi.row(stores)["default_normal"] == "",
             "a `Value: Other` default is an expression, not a number, so the "
             "default column should be empty, got %r"
             % acpi.row(stores)["default_normal"])

    matched = [q.stmt.question_id() for q in charge_rows(questions)]
    want(matched == ["0x2A6", "0x29E9", "0xFA"],
         "the fixture should match exactly 0x2A6, 0x29E9 and 0xFA, in the "
         "order they appear in the dump, got %r" % matched)

    # The near-misses, each declined for its own reason: a VR loadline and a
    # SATA constraint that say AC, and an ACPI setting that says ACPI.
    for qid, label in (("0x901", "AC Loadline"), ("0x902", "ACPI"),
                       ("0x903", "Adapter D0/F1")):
        q = by_id.get(qid)
        want(q is not None, "the fixture's %s did not parse" % label)
        want(q is not None and not q.terms,
             "%s should match no phrase, got %r"
             % (label, q.terms if q else None))
        want(q is not None and any(phrase_in(q.stmt.quoted("Prompt"), probe)
                                   for probe in NEAR_MISS_PROBE),
             "%s should still be visible to --list-excluded, or the exclusion "
             "is invisible" % label)

    text = render_csv([q.row(stores) for q in charge_rows(questions)])
    lines = text.splitlines()
    want(lines[0] == ",".join(CSV_COLUMNS),
         "the CSV header should be this tool's column list")
    want(len(lines) == 4,
         "the fixture CSV should have a header and three rows, got %d line(s)"
         % len(lines))
    want(not unresolved(questions),
         "every fixture condition should resolve; %d did not"
         % len(unresolved(questions)))

    for problem in problems:
        print("  FAIL %s" % problem)
    if problems:
        return 1
    print("  self-test: %d question(s) from the fixture, %d matched %s, "
          "%d condition(s) read in full"
          % (len(questions), len(charge_rows(questions)),
             "/".join(CHARGE_TERMS),
             sum(len(q.suppress) + len(q.gray) for q in questions)))
    return 0


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ifr", default=DEFAULT_IFR,
                    help="an ifrextractor verbose dump to read (default "
                         "bios/ifr/Setup.en-US.ifr.txt)")
    ap.add_argument("--csv", default=DEFAULT_CSV,
                    help="the derived census (default "
                         "bios/ifr/charge-questions.csv)")
    ap.add_argument("--match", metavar="REGEX",
                    help="print every question whose prompt, help or option "
                         "label matches REGEX, not only the charge list")
    ap.add_argument("--list-excluded", action="store_true",
                    help="print the questions a looser probe would have caught "
                         "and CHARGE_TERMS declined")
    ap.add_argument("--offset", metavar="VARSTORE:OFFSET",
                    help="print the question at one offset, e.g. Setup:0x4F3")
    ap.add_argument("--question", metavar="QID",
                    help="print the question with this QuestionId")
    ap.add_argument("--write", action="store_true",
                    help="regenerate the committed CSV from the dump")
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed CSV is not what this tool "
                         "derives; needs neither the ROM nor ifrextractor")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions against a hand-built fixture")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not os.path.isfile(args.ifr):
        raise SystemExit("error: no %s. Pass --ifr, or regenerate the committed "
                         "dump with bios/tools/bios_extract.py --extract."
                         % os.path.relpath(os.path.abspath(args.ifr), REPO))
    # --write first of the two modes that touch the committed CSV: it is the one
    # that writes it, and it is refused alongside --check for the same reason
    # bios_extract.py refuses it there -- a run that both re-blessed the file and
    # compared against it would exit green on anything.
    if args.check and args.write:
        raise SystemExit("error: --write regenerates %s from the current dump; "
                         "it cannot be combined with --check, which compares "
                         "against it." % os.path.relpath(DEFAULT_CSV, REPO))
    if args.check:
        return check(args)
    if args.write:
        return write(args)
    statements = read_dump(args.ifr)
    stores, questions = census(statements)
    if args.list_excluded:
        return print_excluded(args, questions)
    if args.match:
        return print_match(args, stores, questions)
    if args.offset:
        return print_offset(args, stores, questions)
    if args.question:
        return print_question(args, stores, questions)
    return print_census(args, statements, stores, questions)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # `--list-excluded | head -6` is a documented invocation, and the
        # interpreter's own flush of stdout against a closed pipe would
        # otherwise turn it into a traceback. The write did not land, so this
        # is not reported as success; the dup2 keeps the shutdown flush quiet.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
