#!/usr/bin/env python3
r"""Map the Setup IFR's form graph: which `Ref` reaches which form, and under
exactly what conditions.

Input is committed text -- `bios/ifr/Setup.en-US.ifr.txt`, ifrextractor 1.6.1's
verbose dump of the `Setup` driver's HII forms -- read through `ifr_census`'s
parser rather than a second one. No ROM, no UEFIExtract, no ifrextractor: this
tool exists to answer questions about a dump that is already in review.

    python3 bios/tools/ifr_refgraph.py --form 0x2718    who reaches Advanced
    python3 bios/tools/ifr_refgraph.py --form 0x2710    the stock tab list
    python3 bios/tools/ifr_refgraph.py --question 0xE9F  one question, both ways
    python3 bios/tools/ifr_refgraph.py --roots           forms no Ref reaches
    python3 bios/tools/ifr_refgraph.py --orphans         ... minus the root
    python3 bios/tools/ifr_refgraph.py --check           the reader against the dump
    python3 bios/tools/ifr_refgraph.py --self-test       known answers, fixture IFR

Why this is not another mode on `ifr_census.py`. That tool answers *forward*
from a question: given a `QuestionId`, where does it live and what hides it.
This one answers *backward* from a form: given a `FormId`, what reaches it. The
two directions need different inputs (a question's own block versus the whole
statement stream) and are asked by different readers, and `ifr_census` is a
committed shared file that several write-ups already cite. So the parser is
imported -- `read_statements`, `varstores`, `block_spans`, `condition_expr`,
`CONDITION_BLOCKS`, `BYTE_BLOCK` -- and there stays exactly one reader of the
verbose format. The suite pins that import, because a rename that split the two
would leave two answers to one question with nothing failing.

**A `Ref`'s target is read from the opcode bytes, not the rendered field.**
`split_fields` strips the `{ ... }` block from every field it reads, so the
rendered `FormId:` is available without the bytes and the bytes without the
fields. This tool decodes the target from the bytes and prints the rendered
field beside it, because a reachability claim that rests only on the rendered
text cannot tell a reformat from a re-extraction. The offset is documented at
`REF_FORMID_OFFSET` and `--check` fails if any `Ref` in the dump disagrees.

**A condition that resolves to nothing is printed as nothing.** A bare
`SuppressIf` states no condition at all, and `condition_expr` returns `None` for
it. Printing `TRUE` there would be a claim the IFR does not make, so the tool
prints `no condition stated` and the suite holds that wording.

**Nesting comes from block spans, never from indentation.** The dump's
condition stream is flat: the `SuppressIf` at one line, the `EqIdValList` under
it and the `Ref` it gates are at three different depths, and reading the tree by
indentation gets it wrong. A referrer therefore carries a *stack* of enclosing
condition blocks, outermost first, which is what a `SuppressIf` inside a
`GrayOutIf` inside a `Form` produces.

`--check` is the reader against the committed dump, and it is honest in both
directions: a missing dump is a failure rather than an empty result, and a dump
whose `Ref` opcodes disagree with their rendered fields is a failure too. There
is no `--write` and no derived file. `ifr_census.py` has a CSV because its
charge table is a thing worth keeping in a diff; a full ref graph of 207 forms
is a lookup, not a document, and committing one would put a file in review that
every future extraction invalidates. `--check` holds this tool to the same
reproducibility `ifr_census.py --check` documents, without the artefact.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ifr_census  # noqa: E402  (the path insert above is what makes this work)
from ifr_census import (CONDITION_BLOCKS, DEFAULT_IFR, REPO,  # noqa: E402
                        block_spans, condition_expr, form_chain, read_dump,
                        read_statements, varstores)

# The opcode ifrextractor prints for a `Ref`, and the offset of the target
# `FormId` inside the block it appends. Measured, not assumed: every `Ref` in
# the committed Setup dump has its opcode byte here and its `FormId` at this
# offset, in both block shapes the dump uses, and `--check` re-derives that on
# whichever dump it is pointed at.
#
#   15 bytes, a Ref within this form set:
#     0     0x0F          EFI_IFR_OPCODE_REF
#     1     0x0F          ref type, no FormSetGuid follows
#     2-5                 the prompt and help string ids ifrextractor resolved
#     6-7                 QuestionId
#     8-9                 VarStoreId
#     10-11               VarStoreInfo
#     12                  QuestionFlags
#     13-14               FormId, little-endian          <- the target
#
#   33 bytes, a Ref into another form set, with the same first 15 and then:
#     15-16               RefQuestionId
#     17-32               FormSetGuid
#
# The offset is a property of the layout above, not of the length: a Ref with a
# FormSetGuid is 18 bytes longer, so "the last two bytes" reads the tail of a
# GUID on those and the target on the rest. `RawRefError` is raised rather than
# guessed at, so a block this table does not describe is reported instead of
# decoded into a plausible wrong form.
REF_OPCODE = 0x0F
REF_FORMID_OFFSET = 13

# The block shapes above, by total length. Used to tell a `Ref` whose bytes are
# laid out as documented from one whose are not.
REF_BLOCK_LENGTHS = (15, 33)


class RawRefError(Exception):
    """A `Ref` whose opcode block this tool does not decode."""


# --------------------------------------------------------------------------
# Reading a Ref's target from its bytes
# --------------------------------------------------------------------------

def opcode_bytes(stmt):
    """The `{ ... }` block ifrextractor appends to `stmt`, as a bytes object.

    `Statement.body` keeps the block; `Statement.fields` has had it stripped.
    Reached through the sibling's own `BYTE_BLOCK` so the two readers agree on
    what a byte block is -- in particular that a help string may end in a brace
    of its own and must not be mistaken for one.
    """
    m = ifr_census.BYTE_BLOCK.search(stmt.body)
    if not m:
        return b""
    return bytes(int(x, 16) for x in m.group(0).strip().strip("{}").split())


def ref_target(stmt):
    """The `FormId` a `Ref` targets, read from its opcode bytes.

    Raises `RawRefError` rather than returning a guess. A `Ref` whose block
    does not start with the opcode, is not one of the two documented shapes, or
    is too short to hold the field, is a shape this tool has not seen -- and
    returning a number for it would put a fabricated form in a reachability
    table, which is the one failure this tool exists to rule out.
    """
    raw = opcode_bytes(stmt)
    if not raw:
        raise RawRefError("no opcode block")
    if raw[0] != REF_OPCODE:
        raise RawRefError("opcode byte 0x%02X is not EFI_IFR_OPCODE_REF" % raw[0])
    if len(raw) not in REF_BLOCK_LENGTHS:
        raise RawRefError("opcode block is %d bytes, not one of %s"
                          % (len(raw), " or ".join(str(n) for n in REF_BLOCK_LENGTHS)))
    return int.from_bytes(raw[REF_FORMID_OFFSET:REF_FORMID_OFFSET + 2], "little")


# --------------------------------------------------------------------------
# The graph
# --------------------------------------------------------------------------

class Referrer(object):
    """One `Ref` that reaches a form, with the conditions that gate it.

    `stack` is the chain of condition blocks enclosing the `Ref`, outermost
    first, each a `(opcode, line, expr)`. `expr` is `None` where the block
    states no condition, which is not the same as a condition that evaluates
    true.
    """

    __slots__ = ("stmt", "index", "form", "stack", "raw", "raw_error")

    def __init__(self, stmt, index, form, stack):
        self.stmt = stmt
        self.index = index
        self.form = form          # (FormId, title, line) of the enclosing form
        self.stack = stack
        try:
            self.raw = ref_target(stmt)
        except RawRefError as exc:
            self.raw = None
            self.raw_error = str(exc)
        else:
            self.raw_error = None

    def rendered(self):
        """The `FormId:` field as the dump prints it, or '' when absent."""
        return self.stmt.field("FormId")

    def agrees(self):
        """True when the bytes and the rendered field name the same form.

        The two are read from different halves of one line, so disagreement
        means the dump is not what this tool reads -- which `--check` fails on
        and a referrer line marks, rather than letting one silently win.
        """
        if self.raw is None or not self.rendered():
            return False
        try:
            return int(self.rendered(), 0) == self.raw
        except ValueError:
            return False

    def gated(self):
        """True when some enclosing block states a condition.

        A `Ref` under a bare `SuppressIf` is not gated: the block states
        nothing, so this reports False for it and the stack still says which
        block it was under.
        """
        return any(expr is not None for _, _, expr in self.stack)

    def question_ids(self):
        """Every QuestionId named by a condition in the stack, in order."""
        out = []
        for _, _, expr in self.stack:
            if expr is None:
                continue
            for qid in expr.question_ids:
                if qid not in out:
                    out.append(qid)
        return out


def condition_stack(statements, spans, index):
    """The condition blocks enclosing statement `index`, outermost first.

    Collected by span rather than by a depth comparison, for the reason
    `ifr_census.census` collects a question's the same way: a `SuppressIf` at a
    shallower depth that some intervening block has already closed is not an
    ancestor, and only the span knows that.

    Ordered by depth ascending, and index within a depth, so the list reads
    from the outermost block inwards. The sibling sorts the reverse way and
    collects for a question's `suppress`/`gray` lists, which are only ever
    concatenated; here the order is printed and a reader has to be able to see
    which block contains which, so it is stated rather than left incidental.
    """
    enclosing = [(statements[j].depth, j) for j in range(index)
                 if statements[j].opcode in CONDITION_BLOCKS
                 and j < spans[j] and index < spans[j]]
    enclosing.sort()
    return [(statements[j].opcode, statements[j].line,
             condition_expr(statements, j)) for _, j in enclosing]


def enclosing_form(statements, spans, index):
    """`(FormId, title, line)` of the form `index` sits inside, or None.

    Nearest preceding `Form`, not "the `Form` at depth 1": forms nest, and
    0x2718's own `Ref`s are in it rather than in the root that contains it.
    """
    for j in range(index - 1, -1, -1):
        stmt = statements[j]
        if stmt.opcode == "Form" and j < spans[j] and index < spans[j]:
            return stmt.field("FormId"), stmt.quoted("Title"), stmt.line
    return None


def formset_title(statements):
    """The `FormSet` title, which is what a root form is expected to repeat."""
    for stmt in statements:
        if stmt.opcode == "FormSet":
            return stmt.quoted("Title")
    return ""


def ref_statements(statements):
    """Indices of the `Ref` statements that name a form, in dump order."""
    return [i for i, s in enumerate(statements)
            if s.opcode == "Ref" and s.field("FormId")]


def referrers(statements, spans, form_id):
    """Every `Ref` targeting `form_id`, in dump order.

    Matched on the opcode bytes, not the rendered field, and the two are
    compared on the way through: a referrer whose bytes and field disagree is
    still listed, marked, because dropping it would hide the disagreement
    rather than report it.
    """
    want = normalise_form_id(form_id)
    out = []
    for i in ref_statements(statements):
        ref = Referrer(statements[i], i, enclosing_form(statements, spans, i),
                       condition_stack(statements, spans, i))
        if ref.raw is not None and normalise_form_id(ref.raw) == want:
            out.append(ref)
        elif ref.raw is None and normalise_form_id(ref.rendered()) == want:
            out.append(ref)
    return out


def normalise_form_id(value):
    """`0x2718`, `2718` and the int 10008 all name the same form.

    The dump writes every `FormId` as `0xNNNN` and a `Ref`'s opcode bytes give
    an int, so the two spellings have to meet. A bare `2718` is read as hex for
    the same reason: the dump's own notation is hex, so a user typing the digits
    they just read out of it means the hex value, and reading them as decimal
    would answer `--form 2718` about a form nobody has heard of without saying
    so. A value that is neither raises rather than passing through, so a
    malformed `FormId` cannot become a key that silently matches nothing.
    """
    if isinstance(value, int):
        return "0x%04X" % value
    text = str(value).strip().lower()
    if not text:
        raise ValueError("empty FormId")
    if text.startswith("0x"):
        return "0x%04X" % int(text[2:], 16)
    if all(c in "0123456789abcdef" for c in text):
        return "0x%04X" % int(text, 16)
    raise ValueError("not a FormId: %r" % value)


def form_indices(statements):
    """Statement index of every `Form`, keyed by its normalised FormId."""
    out = {}
    for i, stmt in enumerate(statements):
        if stmt.opcode == "Form":
            out[normalise_form_id(stmt.field("FormId"))] = i
    return out


def targets(statements):
    """Every form id some `Ref` names, from the bytes where they decode."""
    out = set()
    for i in ref_statements(statements):
        try:
            out.add(normalise_form_id(ref_target(statements[i])))
        except RawRefError:
            rendered = statements[i].field("FormId")
            if rendered:
                out.add(normalise_form_id(rendered))
    return out


def roots(statements):
    """Forms no `Ref` in this dump reaches, in dump order.

    A statement about incoming `Ref`s and nothing else. "No incoming `Ref`" is
    what a TSE-opened root form looks like, and it is also what an orphaned page
    looks like, and this dump contains both -- so `--orphans` prints the set
    without `0x2710` and the two modes together are how a reader tells them
    apart, rather than either label being a verdict.
    """
    named = targets(statements)
    return [(normalise_form_id(s.field("FormId")), s.quoted("Title"), s.line)
            for s in statements
            if s.opcode == "Form" and normalise_form_id(s.field("FormId")) not in named]


def root_form(statements):
    """The root whose title repeats the form set's own title, or None.

    This is the calibration the `--roots` note rests on. Many forms in this
    dump have no incoming `Ref`, so the property is not distinguishing on its
    own; repeating the `FormSet` title is. It is still an IFR-shaped
    observation and not a statement that the TSE opens that form -- only
    `AMITSE` can settle that, and it is not decompiled.
    """
    title = formset_title(statements)
    if not title:
        return None
    for form_id, form_title_, line in roots(statements):
        if form_title_ == title:
            return form_id, form_title_, line
    return None


# --------------------------------------------------------------------------
# Questions, in the reverse direction
# --------------------------------------------------------------------------

def declaring_questions(statements, spans, qid):
    """Every store question declaring `qid`, in dump order.

    A `Ref` carries a `QuestionId` too and is not a question -- it links to one
    in another form rather than addressing a byte of a store -- so this filters
    on the sibling's `STORE_QUESTIONS` rather than on having the field.
    """
    want = qid.lower()
    return [(i, s) for i, s in enumerate(statements)
            if s.opcode in ifr_census.STORE_QUESTIONS
            and s.field("VarOffset")
            and s.question_id().lower() == want]


def mentions(statements, spans, qid):
    """Every condition block whose resolved expression names `qid`.

    Scoped to the conditions this tool resolved, which is the whole condition
    grammar in this dump: an opcode the model does not cover renders as
    `?(...)` and is counted on every run rather than passed off as read, so a
    question that went unseen would come with a non-zero count beside it.
    """
    want = qid.lower()
    out = []
    for i, stmt in enumerate(statements):
        if stmt.opcode not in CONDITION_BLOCKS or i >= spans[i]:
            continue
        expr = condition_expr(statements, i)
        if expr is None:
            continue
        if any(q.lower() == want for q in expr.question_ids):
            out.append((i, stmt, expr))
    return out


def unresolved_blocks(statements, spans):
    """Every condition this tool could not read in full, for the run's count."""
    out = []
    for i, stmt in enumerate(statements):
        if stmt.opcode not in CONDITION_BLOCKS or i >= spans[i]:
            continue
        expr = condition_expr(statements, i)
        if expr is not None and expr.unmodelled():
            out.append((stmt.line, stmt.opcode, expr.text))
    return out


# --------------------------------------------------------------------------
# Printing
# --------------------------------------------------------------------------

def store_of(statements, stores, qid):
    """`(name, guid, size, offset, prompt)` for a question id, or None."""
    for _, stmt in declaring_questions(statements, None, qid):
        store_id = int(stmt.field("VarStoreId") or "0", 0)
        name, guid, size = stores.get(store_id, ("", "", ""))
        return name, guid, size, stmt.field("VarOffset"), stmt.quoted("Prompt")
    return None


def print_stack(ref, stores, statements, indent="      "):
    """One referrer's enclosing condition stack, with the stores behind it."""
    if not ref.stack:
        print("%sno enclosing condition block" % indent)
        return
    for opcode, line, expr in ref.stack:
        text = expr.text if expr is not None else "no condition stated"
        print("%s%s at line %d: %s" % (indent, opcode, line, text))
        if expr is None:
            continue
        for qid in expr.question_ids:
            found = store_of(statements, stores, qid)
            if found is None:
                print("%s  reads %s, which this dump does not declare"
                      % (indent, qid))
            else:
                name, guid, size, offset, _ = found
                print("%s  reads %s = %s[%s]  %s  %s bytes"
                      % (indent, qid, name or "?", offset or "?", guid or "?",
                         size or "?"))


def print_referrer(ref, stores, statements):
    form = ("%s \"%s\"" % (ref.form[0], ref.form[1])) if ref.form else "no enclosing form"
    print()
    print("  line %d  %s  Qid %s  prompt %r  in %s"
          % (ref.stmt.line, ref.stmt.opcode, ref.stmt.question_id() or "-",
             ref.stmt.quoted("Prompt"), form))
    print("    target     %s   (rendered FormId: %s)"
          % ("0x%04X" % ref.raw if ref.raw is not None else "undecoded: %s"
             % ref.raw_error, ref.rendered() or "-"))
    if ref.raw is not None and not ref.agrees():
        print("    WARNING    the opcode bytes and the rendered field disagree")
    print("    gated      %s" % ("yes" if ref.gated() else "no"))


def print_form(args, statements, stores, spans):
    want = normalise_form_id(args.form)
    index = form_indices(statements).get(want)
    if index is None:
        print("No form with FormId %s in this dump." % args.form)
        print("  `grep -n 'Form FormId:' %s` shows what is there."
              % os.path.relpath(args.ifr, REPO))
        return 0
    stmt = statements[index]
    refs = referrers(statements, spans, want)
    print("Form %s \"%s\" at line %d -- %d Ref(s) in this dump reach it."
          % (want, stmt.quoted("Title"), stmt.line, len(refs)))
    if not refs:
        print("  Nothing in this dump names it. That is what a search of this "
              "form set found, not a claim about how the firmware reaches it: "
              "the form that opens a page is chosen by TSE code, which is not "
              "in the IFR.")
    for ref in refs:
        print_referrer(ref, stores, statements)
        print_stack(ref, stores, statements)
    report_conditions(statements, spans)
    return 0


def print_question(args, statements, stores, spans):
    want = args.question
    declared = declaring_questions(statements, spans, want)
    if not declared:
        print("No question with id %s in this dump." % args.question)
        return 0
    for i, stmt in declared:
        store_id = int(stmt.field("VarStoreId") or "0", 0)
        name, guid, size = stores.get(store_id, ("", "", ""))
        print("QuestionId %s at line %d" % (stmt.question_id(), stmt.line))
        print("  kind     %s   prompt %r" % (stmt.opcode, stmt.quoted("Prompt")))
        print("  store    %s  %s  VarStoreId %s  %s bytes"
              % (name or "?", guid or "?", stmt.field("VarStoreId") or "?",
                 size or "?"))
        print("  offset   %s   size %s bits   flags %s"
              % (stmt.field("VarOffset") or "?", stmt.field("Size") or "?",
                 stmt.field("Flags") or "?"))
        print("  form     %s" % (form_chain(statements, i) or "?"))
        stack = condition_stack(statements, spans, i)
        if not stack:
            print("  enclosing conditions  none")
        for opcode, line, expr in stack:
            text = expr.text if expr is not None else "no condition stated"
            print("  enclosing  %s at line %d: %s" % (opcode, line, text))
    hits = mentions(statements, spans, want)
    print()
    print("  read by %d condition(s) in this dump:" % len(hits))
    if not hits:
        print("    None. That is what this method found against this file, not "
              "a claim that no condition anywhere reads it.")
    for i, stmt, expr in hits:
        form = enclosing_form(statements, spans, i)
        where = ("%s \"%s\"" % (form[0], form[1])) if form else "no enclosing form"
        print("    %s at line %d, in %s" % (stmt.opcode, stmt.line, where))
        print("      %s" % expr.text)
        block_stack = condition_stack(statements, spans, i)
        if len(block_stack) > 1:
            print("      under:")
            for opcode, line, outer in block_stack[:-1]:
                text = outer.text if outer is not None else "no condition stated"
                print("        %s at line %d: %s" % (opcode, line, text))
    report_conditions(statements, spans)
    return 0


def print_roots(args, statements, stores):
    found = roots(statements)
    titled = root_form(statements)
    print("FormSet title: %r" % formset_title(statements))
    print("%d form(s) in this dump are named by no Ref:" % len(found))
    for form_id, title, line in found:
        mark = "  <- title repeats the form set's" if titled and (
            form_id, title, line) == titled else ""
        print("  %s  %-44s line %d%s" % (form_id, repr(title), line, mark))
    print()
    print("  No incoming Ref is a statement about this dump. It is what a")
    print("  TSE-opened root form looks like, and it is also what an orphaned")
    print("  page looks like; this set contains both, so neither label is a")
    print("  verdict. --orphans is this set without the titled root.")
    print("  Which form the TSE opens is not in the IFR at all.")
    return 0


def print_orphans(args, statements, stores):
    titled = root_form(statements)
    kept = [r for r in roots(statements) if not titled or r[0] != titled[0]]
    print("%d form(s) are named by no Ref and are not the root whose title "
          "repeats the form set's:" % len(kept))
    for form_id, title, line in kept:
        print("  %s  %-44s line %d" % (form_id, repr(title), line))
    print()
    print("  Not reachable by any Ref in this form set. Not dead: the form may")
    print("  still be opened by TSE code, by another form set, or by a caller")
    print("  this dump does not contain.")
    return 0


def report_conditions(statements, spans):
    """Every run says how many conditions it could not read, and how many there were.

    A `?(...)` node is an opcode this tool does not model. Printing the count
    on every run is what keeps a partly-read condition from reading as a
    fully-read one.
    """
    bare = sum(1 for i, s in enumerate(statements)
               if s.opcode in CONDITION_BLOCKS and i < spans[i]
               and condition_expr(statements, i) is None)
    left = unresolved_blocks(statements, spans)
    print()
    if left:
        print("%d condition(s) carry an opcode this tool does not model and are "
              "shown as ?(...):" % len(left))
        for line, opcode, text in left:
            print("  line %d  %s  %s" % (line, opcode, text))
    else:
        print("every condition this run resolved was read in full.")
    print("%d block(s) state no condition at all; those print as "
          "\"no condition stated\"." % bare)


# --------------------------------------------------------------------------
# --check
# --------------------------------------------------------------------------

def check(args):
    """The reader against the committed dump. Fails in both directions.

    There is no derived artefact here, so the two failure directions are the
    input's: a missing dump is a hole rather than an empty result, and a dump
    whose `Ref` opcodes disagree with their rendered fields means this reader
    and the committed file have diverged. Either would silently change every
    reachability claim built on it.
    """
    path = os.path.abspath(args.ifr)
    if not os.path.isfile(path):
        print("error: no %s. It is the committed dump; regenerate it with "
              "bios/tools/bios_extract.py --extract." % os.path.relpath(path, REPO))
        return 1
    statements = read_dump(path)
    spans = block_spans(statements)
    refs = ref_statements(statements)
    problems, disagree, undecoded = [], 0, 0
    for i in refs:
        ref = Referrer(statements[i], i, enclosing_form(statements, spans, i),
                       ())
        if ref.raw is None:
            undecoded += 1
            problems.append("line %d: %s" % (statements[i].line, ref.raw_error))
        elif not ref.agrees():
            disagree += 1
            problems.append(
                "line %d: bytes name 0x%04X, the rendered field says %s"
                % (statements[i].line, ref.raw, ref.rendered() or "(none)"))
    forms = form_indices(statements)
    named = targets(statements)
    # Distinct *targets*, not `Ref` statements: 0x0001 alone is named four
    # times over. The count and the list beside it are the same set, and the
    # sentence below says "distinct" so the two cannot be read as a count of
    # the statements.
    dangling = sorted(set(named) - set(forms))
    print("%s: %d statement(s), %d form(s), %d Ref(s)"
          % (os.path.relpath(path, REPO), len(statements), len(forms), len(refs)))
    print("every Ref's FormId decoded from its opcode bytes at offset %d: %s"
          % (REF_FORMID_OFFSET, "yes" if not problems else "no"))
    if dangling:
        print("  %d distinct form(s) this dump does not declare are named by a "
              "Ref: %s" % (len(dangling), ", ".join(dangling)))
        print("  That is a Ref into another form set, which the dump may not "
              "contain, and is not a failure of the reader.")
    for line in problems:
        print("  %s" % line)
    if problems:
        print("  If the layout in this tool's docstring is what the dump holds, "
              "the offsets here are what to correct.")
        return 1
    print("reader and dump agree; %d distinct dangling Ref target(s) noted above."
          % len(dangling))
    return 0


# --------------------------------------------------------------------------
# The self-test
# --------------------------------------------------------------------------

# A hand-built IFR holding one case per thing the tool has to get right, in the
# two shapes the committed dump uses. The 15-byte `Ref` is a link within the
# form set; the 33-byte one carries a FormSetGuid after the same first fifteen
# bytes, and its target is at the *same offset*, which is the whole reason the
# offset is a constant rather than "the last two bytes". Between them: a bare
# `SuppressIf` that states no condition, a `SuppressIf` inside a `GrayOutIf`
# around a `Ref` (the shape 0x2712 carries), a `Default ... Value: Other` whose
# own expression sits inside the `SuppressIf` that gates the question it belongs
# to, a `Ref` whose prompt wraps over a CR, and a question two forms reference.
FIXTURE = "\n".join([
    'Program version: 1.6.1, Extraction mode: UEFI, SHA256: 0000',
    '0x100: FormSet Guid: 11111111-1111-1111-1111-111111111111, Title: "Setup", Help: "Setup" { 01 }',
    '0x110: \tVarStore Guid: 22222222-2222-2222-2222-222222222222, VarStoreId: 0x1, Size: 0x10, Name: "Setup" { 02 }',
    '0x120: \tVarStore Guid: 33333333-3333-3333-3333-333333333333, VarStoreId: 0x33, Size: 0x2, Name: "DynamicPageCount" { 03 }',
    '0x130: \tForm FormId: 0x2710, Title: "Setup" { 04 }',
    '0x140: \t\tRef Prompt: "Main", Help: "", QuestionFlags: 0x0, QuestionId: 0x1, VarStoreId: 0x0, VarStoreInfo: 0xFFFF, FormId: 0x2717 { 0F 0F 09 00 02 00 01 00 00 00 FF FF 00 17 27 }',
    '0x150: \t\tRef Prompt: "Advanced", Help: "", QuestionFlags: 0x0, QuestionId: 0x2, VarStoreId: 0x0, VarStoreInfo: 0xFFFF, FormId: 0x2718 { 0F 0F 1E 00 02 00 02 00 00 00 FF FF 00 18 27 }',
    '0x160: \tEnd  { 05 }',
    '0x170: \tForm FormId: 0x2711, Title: "Advanced" { 06 }',
    '0x180: \t\tGrayOutIf  { 0B 82 }',
    '0x190: \t\t\tEqIdVal QuestionId: 0xD81, Value: 0x1 { 07 86 81 0D 01 00 }',
    '0x1A0: \t\t\tSuppressIf  { 08 82 }',
    '0x1B0: \t\t\t\tEqIdValList QuestionId: 0xE9F, Values: [65535] { 09 92 9F 0E FF FF }',
    '0x1C0: \t\t\t\tRef Prompt: "", Help: "", QuestionFlags: 0x0, QuestionId: 0xE, VarStoreId: 0x0, VarStoreInfo: 0xFFFF, FormId: 0x2711 { 0F 0F 02 00 02 00 0E 00 00 00 FF FF 00 11 27 }',
    '0x1D0: \t\t\tEnd  { 0B 02 }',
    '0x1E0: \t\tEnd  { 0C 02 }',
    '0x1F0: \tEnd  { 0D 02 }',
    '0x200: \tForm FormId: 0x2717, Title: "Main" { 0E }',
    '0x210: \t\tSuppressIf  { 0A 82 }',
    '0x218: \t\t\tEqIdValList QuestionId: 0xD81, Values: [1, 2] { 0F 92 81 0D 01 02 }',
    '0x220: \t\t\tNumeric Prompt: "", Help: "", QuestionFlags: 0x0, QuestionId: 0xE9F, VarStoreId: 0x33, VarOffset: 0x0, Flags: 0x11, Size: 16, Min: 0x0, Max: 0xFFFF, Step: 0x0 { 0F 94 9F 0E 00 00 33 00 00 00 11 00 00 00 00 00 00 00 00 00 00 00 00 }',
    '0x230: \t\t\t\tDefault DefaultId: 0x0 Value: Other { 10 5B 85 }',
    '0x240: \t\t\t\t\tValue  { 11 5A 82 }',
    '0x250: \t\t\t\t\t\tEqIdValList QuestionId: 0xD81, Values: [1, 2, 3] { 12 92 81 0D 01 02 03 }',
    '0x260: \t\t\t\t\t\tUint16 Value: 0x1 { 13 0C 01 00 }',
    '0x270: \t\t\t\t\tConditional  { 14 43 }',
    '0x280: \t\t\t\tEnd  { 15 02 }',
    '0x290: \t\t\tEnd  { 16 02 }',
    '0x2A0: \t\t\tRef Prompt: "Key Management", Help: "Enables expert users to modify Secure Boot policy',
    'variables without full authentication", QuestionFlags: 0x4, QuestionId: 0x29F3, VarStoreId: 0x0, VarStoreInfo: 0xFFFF, FormId: 0x29FA { 0F 0F B3 19 B4 19 F3 29 00 00 FF FF 04 FA 29 }',
    '0x2B0: \tEnd  { 17 02 }',
    '0x2C0: \tForm FormId: 0x2718, Title: "Elsewhere" { 18 86 18 27 1E 00 }',
    '0x2D0: \t\tRef Prompt: "Acoustic", Help: "", QuestionFlags: 0x0, QuestionId: 0x3C, VarStoreId: 0x0, VarStoreInfo: 0xFFFF, FormId: 0x1, RefQuestionId: 0x0, FormSetGuid: C48AA1AC-F870-418D-A6EF-C1DD89C1CE19 { 0F 21 44 18 45 18 3C 00 00 00 FF FF 00 01 00 00 00 AC A1 8A C4 70 F8 8D 41 A6 EF C1 DD 89 C1 CE 19 }',
    '0x2E0: \t\tSuppressIf  { 19 82 }',
    '0x2F0: \t\t\tEqIdVal QuestionId: 0x1, Value: 0x2 { 1A 86 01 00 02 00 }',
    '0x300: \t\t\tOneOf Prompt: "Unconditional", Help: "", QuestionFlags: 0x0, QuestionId: 0x902, VarStoreId: 0x1, VarOffset: 0x11 { 1B 91 02 09 01 00 11 00 }',
    '0x310: \t\t\tEnd  { 1C 02 }',
    '0x320: \t\tSuppressIf  { 1D 82 }',
    '0x330: \t\t\tNumeric Prompt: "Bare", Help: "", QuestionFlags: 0x0, QuestionId: 0x903, VarStoreId: 0x1, VarOffset: 0x12 { 1E 94 03 09 01 00 12 00 }',
    '0x340: \t\t\tEnd  { 1F 02 }',
    '0x350: \tEnd  { 20 02 }',
    '0x360: \tForm FormId: 0x2740, Title: "Unreferenced" { 21 86 40 27 00 00 }',
    '0x370: \t\tSubtitle Prompt: "Nothing links here", Help: "", Flags: 0x0 { 22 87 00 00 00 00 00 }',
    '0x380: \tEnd  { 23 02 }',
    '0x390: End  { 24 02 }',
    '',
])


# The fixture's left column is ifrextractor's byte offset into the HII package,
# not a line number, so it cannot be used to look a statement up directly. This
# maps it to the file line `read_statements` will number that statement with,
# using the sibling's own address pattern, so a case can say `at(0x1C0)` and
# mean the statement whose body it wrote.
_FIXTURE_LINE = {}
for _n, _text in enumerate(FIXTURE.split("\n"), 1):
    _m = ifr_census.STATEMENT.match(_text.replace("\r", " "))
    if _m:
        _FIXTURE_LINE[int(_m.group(1), 16)] = _n


def self_test():
    statements = read_statements(FIXTURE.split("\n"))
    spans = block_spans(statements)
    stores = varstores(statements)

    def at(address):
        """The one fixture statement whose address column is `address`."""
        line = _FIXTURE_LINE[address]
        hits = [s for s in statements if s.line == line]
        if len(hits) != 1:
            raise AssertionError("fixture address 0x%X is %d statement(s)"
                                 % (address, len(hits)))
        return hits[0]

    def index_of(address):
        return statements.index(at(address))

    problems = []

    def want(cond, message):
        if not cond:
            problems.append(message)

    # The offset, in both block shapes, against the rendered field. This is the
    # case that fails if someone "simplifies" the decode to the last two bytes:
    # the 33-byte Ref then reads the tail of a GUID and reports 0xC48AA1AC.
    for address, want_form in ((0x140, 0x2717), (0x150, 0x2718),
                                (0x1C0, 0x2711), (0x2A0, 0x29FA),
                                (0x2D0, 0x0001)):
        stmt = at(address)
        got = ref_target(stmt)
        want(got == want_form,
             "the Ref at fixture 0x%X should decode to 0x%04X from its opcode "
             "bytes, got 0x%04X" % (address, want_form, got))
        want(normalise_form_id(stmt.field("FormId")) ==
             normalise_form_id(want_form),
             "the Ref at fixture 0x%X renders FormId %s, which should be 0x%04X"
             % (address, stmt.field("FormId"), want_form))

    # A block this tool does not decode is reported, not guessed at. The
    # fixture's own 15-byte and 33-byte shapes are the two it does.
    for body, why in (
            ("Ref Prompt: \"x\", FormId: 0x2717 { 05 01 02 }", "wrong opcode"),
            ("Ref Prompt: \"x\", FormId: 0x2717 { 0F 01 02 03 }", "unknown length"),
            ("Ref Prompt: \"x\", FormId: 0x2717", "no opcode block")):
        try:
            ref_target(ifr_census.Statement(1, 1, body))
        except RawRefError:
            pass
        else:
            problems.append("a Ref with %s should raise RawRefError" % why)
    try:
        normalise_form_id("not a form")
    except ValueError:
        pass
    else:
        problems.append("a FormId that is not a number should be refused")

    # The wrapped Ref: its prompt runs over a CR, so the FormId sits on the
    # statement's continuation line. `read_statements` joins it; a reader that
    # parsed the fields before joining would lose the target, and this Ref would
    # then silently vanish from the referrer list of whatever it points at.
    wrapped = [i for i in ref_statements(statements)
               if statements[i].line == at(0x2A0).line]
    want(len(wrapped) == 1,
         "the Ref whose prompt wraps over a CR should be one statement, got %d"
         % len(wrapped))
    want(wrapped and normalise_form_id(
        statements[wrapped[0]].field("FormId")) == "0x29FA",
        "the wrapped Ref lost its FormId")
    want([r.stmt.line for r in referrers(statements, spans, "0x29FA")] ==
         [at(0x2A0).line],
         "the wrapped Ref should be a referrer of 0x29FA")

    # 0x2718 is reached once here, from the root, under no condition at all.
    refs = referrers(statements, spans, "0x2718")
    want([r.stmt.line for r in refs] == [at(0x150).line],
         "0x2718 should be reached by the fixture's one Ref at 0x150, got %r"
         % [r.stmt.line for r in refs])
    if refs:
        want(not refs[0].gated(),
             "the Ref at fixture 0x150 is under no condition block and should "
             "not be gated")
        want(refs[0].stack == [],
             "the ungated Ref should carry an empty stack, got %r" % (refs[0].stack,))
        want(refs[0].agrees(),
             "the referrer's opcode bytes and rendered FormId should agree")
    for spelling, how in (("0x2718", "hex"), ("2718", "bare hex"),
                          (10008, "an int")):
        want([r.stmt.line for r in referrers(statements, spans, spelling)] ==
             [at(0x150).line],
             "--form should accept %s (%s) as the form 0x2718"
             % (spelling, how))

    # The nested stack: a SuppressIf inside a GrayOutIf around a Ref, which is
    # the shape the vendor's own 0x2712 carries. It resolves as a stack of two,
    # not a tree read off the indentation, and the outer block is not lost.
    nested = referrers(statements, spans, "0x2711")
    want([r.stmt.line for r in nested] == [at(0x1C0).line],
         "0x2711 should be reached by the fixture's self-Ref at 0x1C0, got %r"
         % [r.stmt.line for r in nested])
    if nested:
        stack = nested[0].stack
        want([op for op, _, _ in stack] == ["GrayOutIf", "SuppressIf"],
             "the self-Ref's enclosing stack should be GrayOutIf then "
             "SuppressIf, outermost first, got %r" % [op for op, _, _ in stack])
        want([line for _, line, _ in stack] == [at(0x180).line, at(0x1A0).line],
             "the stack should name the GrayOutIf then the SuppressIf, got %r"
             % [line for _, line, _ in stack])
        want([e.text for _, _, e in stack] ==
             ["EqIdVal QuestionId: 0xD81, Value: 0x1",
              "EqIdValList QuestionId: 0xE9F, Values: [65535]"],
             "the two blocks should resolve to their own conditions, got %r"
             % [e.text for _, _, e in stack])
        want(nested[0].gated(), "a Ref under two stated conditions is gated")
        want(nested[0].question_ids() == ["0xD81", "0xE9F"],
             "the stack names 0xD81 then 0xE9F, got %r" % nested[0].question_ids())

    # A bare SuppressIf states no condition, and the tool says so rather than
    # printing TRUE. The question under it is still reported as sitting under
    # that block, with the condition absent rather than invented.
    bare = index_of(0x320)
    want(condition_expr(statements, bare) is None,
         "the fixture's bare SuppressIf should state no condition")
    stack = condition_stack(statements, spans, index_of(0x330))
    want([(op, line, expr) for op, line, expr in stack] ==
         [("SuppressIf", at(0x320).line, None)],
         "the question under a bare SuppressIf should carry that block with no "
         "condition, got %r" % ([(o, l, e) for o, l, e in stack],))

    # The question direction: 0xE9F is declared once, on the store the fixture
    # names, and read by the one condition that names it.
    declared = declaring_questions(statements, spans, "0xE9F")
    want([s.line for _, s in declared] == [at(0x220).line],
         "0xE9F should be declared once in the fixture, got %r"
         % [s.line for _, s in declared])
    want(stores.get(0x33, ("",))[0] == "DynamicPageCount",
         "VarStoreId 0x33 should resolve to DynamicPageCount, got %r"
         % (stores.get(0x33),))
    hits = mentions(statements, spans, "0xE9F")
    want([s.line for _, s, _ in hits] == [at(0x1A0).line],
         "0xE9F should be read by one condition in the fixture, got %r"
         % [s.line for _, s, _ in hits])

    # ... and the Default's own expression, nested inside the `SuppressIf` that
    # gates the question it belongs to, does not fold into that question's
    # visibility condition. The Default tests `0xD81` against a *different*
    # value list, so a leak shows up as a wrong answer rather than as a
    # duplicated one.
    stack = condition_stack(statements, spans, index_of(0x220))
    want([(op, e.text if e is not None else None) for op, _, e in stack] ==
         [("SuppressIf", "EqIdValList QuestionId: 0xD81, Values: [1, 2]")],
         "0xE9F should sit under the one SuppressIf and no other; its Default's "
         "own expression leaked into it: %r"
         % [(op, e.text if e is not None else None) for op, _, e in stack])

    # The roots calibration: two forms in the fixture are named by no Ref, only
    # one of them repeats the form set's title, and neither fact is a claim
    # about what the TSE opens.
    want([f[0] for f in roots(statements)] == ["0x2710", "0x2740"],
         "the fixture's unreferenced forms are 0x2710 and 0x2740, got %r"
         % [f[0] for f in roots(statements)])
    titled = root_form(statements)
    want(titled is not None and titled[0] == "0x2710",
         "the only root repeating the form set's title should be 0x2710, got %r"
         % (titled,))

    # A Ref into a form set this dump does not hold (0x2718 names one) is
    # reported as a referrer, not an error, and its target is read from the
    # same offset as every other Ref rather than off the GUID behind it.
    want(not unresolved_blocks(statements, spans),
         "every fixture condition should resolve; %d did not"
         % len(unresolved_blocks(statements, spans)))

    for problem in problems:
        print("  FAIL %s" % problem)
    if problems:
        return 1
    print("  self-test: %d form(s), %d Ref(s), %d read by conditions, every "
          "condition read in full" % (len(form_indices(statements)),
                                      len(ref_statements(statements)), len(hits)))
    return 0


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ifr", default=DEFAULT_IFR,
                    help="an ifrextractor verbose dump to read (default "
                         "bios/ifr/Setup.en-US.ifr.txt)")
    ap.add_argument("--form", metavar="FORMID",
                    help="print every Ref that reaches this form, with the "
                         "conditions that gate each one")
    ap.add_argument("--question", metavar="QID",
                    help="print this question -- where it is stored, and every "
                         "condition in the dump that reads it")
    ap.add_argument("--roots", action="store_true",
                    help="print the forms no Ref in this dump names")
    ap.add_argument("--orphans", action="store_true",
                    help="print those forms without the one whose title "
                         "repeats the form set's")
    ap.add_argument("--check", action="store_true",
                    help="fail if this reader and the committed dump disagree; "
                         "needs neither the ROM nor ifrextractor")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions against a hand-built fixture")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    # `--check` reads the dump through `check`, which reports a missing one as a
    # failed check rather than as a usage error. Both exit non-zero; the
    # difference is which message a reader gets, and the check mode's own
    # contract is the more useful place for it.
    if args.check:
        return check(args)
    if not os.path.isfile(args.ifr):
        raise SystemExit("error: no %s. Pass --ifr, or regenerate the committed "
                         "dump with bios/tools/bios_extract.py --extract."
                         % os.path.relpath(os.path.abspath(args.ifr), REPO))
    statements = read_dump(args.ifr)
    spans = block_spans(statements)
    stores = varstores(statements)
    if args.form:
        return print_form(args, statements, stores, spans)
    if args.question:
        return print_question(args, statements, stores, spans)
    if args.roots:
        return print_roots(args, statements, stores)
    if args.orphans:
        return print_orphans(args, statements, stores)
    ap.print_help()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # `--roots | head` is a documented shape of reading this, and the
        # interpreter's own flush of stdout against a closed pipe would
        # otherwise turn it into a traceback. The write did not land, so this
        # is not reported as success.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
