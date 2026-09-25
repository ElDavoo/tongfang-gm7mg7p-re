#!/usr/bin/env python3
"""Measure which of a page's figures a check actually holds, and say which.

`docs/findings/xdata-census-rederivation-checklist.md` §2b told a re-deriver
which of its figures to redo by hand. Issue #849 found the split was the wrong
way round: the block said eight were unpinned, and of its eighteen figures the
cheap gate turns red on seven. The damage runs both ways — a reader is sent to
redo work the tree already does, and the eleven that really were unpinned
(`9320`, `390`, `50` and §6a's eight per-subset sums) are left looking like
company. `9320` was the sharpest case, because it was
`OWNERSHIP["main_refs"]` and a value in a constant is a pin-shaped thing; the
key was read by no check at all.

So a figure's being *written down* is not evidence of anything, and this tool
does the measuring rather than the reader. Every numeric figure in a named
section's tables is resolved to one of four verdicts and printed with the
`file:line` that resolved it:

  * `held-by-assertion` — the literal is a value in a module-level dict in
    `ec/tools/*.py` **and** that key is subscripted outside the constant's own
    span, preferring a subscription inside a `check()`/`assert*` call. This is
    the `OWNERSHIP["main_refs"]` case: a value with no reader is a promise
    wearing the costume of a pin, so a dict entry only counts once something
    reads it. *Reads* rather than *compares* is the weaker half, and the
    reported line is the one that compares where there is one — the difference
    between `ORACLE["extmem_pd_distinct"]` in the `extmem_both` sum and the same
    key inside the `check()` that holds it to the census.
  * `held-by-check-literal` — the literal is an int constant inside a `check()`
    call or a numeric `assertEqual`/`assertGreater` family call, or the row
    names a line of a committed CSV that `xdata_register_map.py --check`
    regenerates and compares cell for cell **and a cell on that line is the
    figure**. That last clause is what makes the CSV source safe to use: a
    439-row `refs` column is full of small integers, so searching it for "any
    cell equal to 50" finds a `50` that is a different cluster's count and calls
    the pd-image cluster count pinned. The row's own `file:line` is the
    disambiguator, and it is the one the document already writes down — this is
    how `4,966` is held, as the `refs` cell of `main-ec-003` at
    `xdata-clusters.csv:4`.
  * `unheld` — no oracle entry, no literal inside a check, no cited committed
    cell.
  * `not read by this method` — a shape the reader declines, counted and printed
    with its reason, and **never** failing the run.

**Every `unheld` is "not found by this method", never "absent"** — the caveat
`ec/annotations/registers.yaml` and `check_cluster_citations.py` both carry, and
here it is the load-bearing half of the tool rather than a decoration. The
verdict on `390` and `50` is "no occurrence in the committed tool sources and no
committed cell carries it". That is a statement about a search over text. It is
not a statement that nothing holds those figures, and the reader who finds a
fourth pin is expected to add it here rather than to discount this.

**What the reader accepts as a figure.** The first cell of a table row, and
nothing else — a figure in prose, a heading or a bullet is not read at all, so
this is a checker for tables, not for pages. Within that cell, hex addresses
(`0x06C6`), section and figure references (`§2b`, `#849`) and file paths are
removed before any number is read, so a `file:line` beside a figure is never
mistaken for the figure. A decimal (`0.5`) is not a census figure and is not
read as one. A cell left with no figure is a decline rather than an `unheld`: the
`set(off) == set(on)` row of §2a is a relation, and reading nothing from it is
the right answer, not a miss.

**What the row claims, and what has to back it up.** A table declares itself a
verdict table by having a column headed `verdict`, and every figure row of one
has to put exactly one of `held`, `unheld` or `not read by this method` in that
column. The column is named rather than inferred, and a table without one is
skipped — which is what lets a page quote its own superseded classification in a
correction block without the tool auditing the wrong version. A row of a verdict
table that marks nothing is a disagreement, and so is a section with no verdict
table in it at all: **a table that stops declaring its verdicts would otherwise
return a page to the state before this tool existed and report a clean run**,
which is the one outcome a checker for held-versus-unheld cannot produce.

A `held` row must then name a pin, and the pin has to hold up three ways — the
file exists, the line is one it has, and the file it names is the file the
measurement resolved to. An `unheld` row naming a `file:line` is a disagreement
the other way, because a citation claims that something there holds the figure,
which is what `unheld` denies. That is the one thing in this tree that validates
a `file:line` citation at all, and it is here because these citations move: the
line numbers in this page's own family have already moved under a page that cited
them.

**And the limit worth naming on the other side.** The `.py` searches are over
every tool module, so a figure that happens to equal an unrelated assertion's
literal reads as held. That direction is the safe one to get wrong — the report
prints the exact `file:line` for the reader to see which assertion it is, and a
row's own pin has to agree with it — but it is a search and not a proof that
*this* figure is what *that* check is about.

**And what this tool is not.** It is not in `.github/scripts/agent-gates.sh`, and
cannot be until a human adds it there with a token that has `workflow` scope;
`.github/` is out of this repository's agent reach by construction. It runs by
hand, which is exactly where `check_cluster_citations.py` stands today. A checker
nobody runs is the shape of defect issue #819 was, so that standing is stated
here rather than left for a reader to assume a gate exists.

Usage:
    python3 ec/tools/check_doc_figure_pins.py \\
        docs/findings/xdata-census-rederivation-checklist.md --section 2b
    python3 ec/tools/check_doc_figure_pins.py <doc.md> --section 3 --verbose
"""
import argparse
import ast
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
TOOLS = os.path.join(EC, "tools")


def tool_path(name):
    """`ec/tools/<name>`, the spelling a document cites a tool by.

    The report and the row it is checking have to name the same file the same
    way, or "the pin is in the wrong file" fires on a bare module name against a
    repo-relative one and the rule is a false positive rather than a check.
    """
    return os.path.relpath(os.path.join(TOOLS, name), REPO)


# The three marks the verdicts are written with. A row's cell has to be exactly
# one of these: a sentence that happens to contain the word "held" is prose, and
# reading a verdict out of prose is how a document and a checker end up
# disagreeing about what they were both talking about.
HELD, UNHELD, DECLINED = "held", "unheld", "not read by this method"
VERDICTS = (HELD, UNHELD, DECLINED)
BY_ASSERTION = "held-by-assertion"
BY_LITERAL = "held-by-check-literal"
# What the two `held-by-*` verdicts have in common: a check compares against the
# figure. The document marks a row with the single word `held` and does not
# distinguish how, so agreeing with it means asking this and not the name.
HELD_VERDICTS = (BY_ASSERTION, BY_LITERAL)

# Calls whose int constants are assertions. `check()` is this census tool's own;
# the rest are the numeric half of unittest, deliberately excluding `assertIn`
# and friends, whose first argument is a container and a figure inside one is a
# membership claim rather than an equality. A literal in one of these is a pin
# because something compares against it.
ASSERTING = {"check", "assertEqual", "assertNotEqual", "assertGreater",
             "assertGreaterEqual", "assertLess", "assertLessEqual",
             "assertAlmostEqual"}

# A module-level dict is a candidate oracle: name and all-caps, because that is
# the convention every constant in `ec/tools/` follows and because a lowercase
# dict is nearly always a local working table. The limit is in the docstring — a
# dict that is really a data table would make its values look pinned — so the
# report prints the definition it resolved to and the reader can see the shape.
ORACLE_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")

# This tool's own two modules are not evidence about anything, and including
# them makes the tool grade its own homework: every figure the page lists has to
# appear in the suite that measures it, so `390` and `50` would both measure
# held-by-check-literal the moment a case named them. Excluded by name because
# nothing mechanical can tell a test that pins a figure against the census from
# one that pins it against this tool's verdict about the census -- they are the
# same call shape, and only the second is circular. That is the general limit of
# the literal search and it is worth knowing: a figure this tool reports unheld
# can be "held" by a test somewhere, and this tool will not have seen it.
SELF_MODULES = ("check_doc_figure_pins.py", "test_check_doc_figure_pins.py")

# Removed from a cell before any number is read out of it. None of these can
# reintroduce a digit, and the hex form has to go before the bare-number pass.
NOT_A_FIGURE = re.compile(
    r"0[xX][0-9A-Fa-f]+"          # an address
    r"|§[0-9]+[a-z]?"             # §2b, §6a
    r"|#[0-9]+"                   # #849
    r"|\bissue[s]?\s+#?[0-9]+"    # "issue #849", "issues 849"
    r"|[\w./-]+\.(?:py|md|csv|ya?ml|sh|json|txt|asm|c|yml)\b"
)

# A census figure: a bare decimal, thousands commas the way this corpus writes
# them. The guards are the three ways a digit run here is not a count — inside a
# longer number, a decimal (`0.5`, which is a threshold), or abutting an
# identifier that owns it.
FIGURE = re.compile(r"(?<![0-9A-Za-z_.])(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)"
                    r"(?![0-9])(?!\.[0-9])")

# A citation, in the two spellings this corpus uses: `path.py:1234` and the
# shorthand `:1234` a page uses once the file is named in the paragraph above.
# Only the qualified spelling carries a path, so only it can be resolved to a
# file; the shorthand is the page's own prose and is not this tool's to check.
CITATION = re.compile(r"(?P<path>[\w./-]+\.(?:py|md|csv|ya?ml)):"
                      r"(?P<line>[0-9]+)(?:-(?P<last>[0-9]+))?")

HEADING = re.compile(r"^(#{2,6})\s+(.*)$")
DELIMITER = re.compile(r"^\|[\s:|-]+\|$")
MARKUP = re.compile(r"[`*]")


def tool_names(exclude_self=False):
    """Every module in `ec/tools/`, sorted, so a report is reproducible.

    `exclude_self` drops this tool's own two modules; see `SELF_MODULES` for
    why a measurement of the measurement is not evidence about the census.
    """
    return sorted(n for n in os.listdir(TOOLS)
                  if n.endswith(".py") and not n.startswith("_")
                  and not (exclude_self and n in SELF_MODULES))


def source(name):
    """The text of one `ec/tools/*.py`, or '' if it cannot be read.

    Read as text rather than imported. Importing the census tool would run its
    module-level work, and a checker that costs a second to start is a checker a
    person stops running; parsing it answers every question asked of it here.
    """
    try:
        with open(os.path.join(TOOLS, name), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def tree_of(text):
    """The parse of one source text, or None where it does not parse."""
    try:
        return ast.parse(text)
    except SyntaxError:
        return None


def oracles(texts):
    """((module, table) -> (keys, lo, hi)) for every module-level int dict.

    A dict is read at its own assignment node, so the span is that node's and a
    key's own definition line is inside it -- which is what lets `reads()` tell
    a subscription from the literal that defines one.
    """
    found = {}
    for name in sorted(texts):
        tree = tree_of(texts[name])
        if tree is None:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
                continue
            target = node.targets[0]
            if not (isinstance(target, ast.Name) and ORACLE_NAME.match(target.id)):
                continue
            keys = {}
            for k, v in zip(node.value.keys, node.value.values):
                if (isinstance(k, ast.Constant) and isinstance(k.value, str)
                        and isinstance(v, ast.Constant)
                        and isinstance(v.value, int) and not isinstance(v.value, bool)):
                    keys[k.value] = (v.value, tool_path(name), v.lineno)
            if keys:
                found[(name, target.id)] = (keys, node.lineno, node.end_lineno)
    return found


def asserting_spans(tree):
    """[(lineno, end_lineno)] of every `check()`/numeric-`assert*` call.

    The span, not just the first line, because a call written over eight lines is
    the normal shape in this corpus and the constant being read is often on the
    last one.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = (func.id if isinstance(func, ast.Name)
                  else func.attr if isinstance(func, ast.Attribute) else None)
        if called in ASSERTING:
            yield (node.lineno, node.end_lineno or node.lineno)


def asserted_lines(texts):
    """{module: {lineno: (lo, hi)}} for every line inside an asserting call.

    What separates a read that *checks* a constant from one that merely
    *computes* with it. `ORACLE["extmem_pd_distinct"]` is first read at the
    `extmem_both` sum, which is arithmetic; the read that holds it to the census
    is a line lower, inside the `check()`. Reporting the first would send a
    reader to an assignment and call it a pin -- the same "looks pinned and is
    not" defect this tool exists to measure, one level down.

    The span is kept rather than collapsed to a line because the line the
    comparison lands on is not the line the subscription lands on: a `check()`
    written over eight lines names the constant in its message three lines above
    the `==` that uses it. A reader verifying the pin wants the whole call, and
    "asserted at 3250-3277" says it in five characters that "asserted at 3263"
    does not.
    """
    out = {}
    for name, text in texts.items():
        tree = tree_of(text)
        if tree is None:
            continue
        lines = {at: (lo, hi) for lo, hi in asserting_spans(tree)
                 for at in range(lo, hi + 1)}
        if lines:
            out[name] = lines
    return out


def reads(module, table, key, lo, hi, texts, asserted):
    """(file, lineno, span) of the subscription to `key` that pins it, or None.

    "Pins" rather than "is read", and that is why the search prefers a read
    inside an asserting call: a read is what makes a constant held, and the line
    worth printing to a reader is the one where something compares against it.

    The third element is the asserting call's span where there was one, so the
    caller can cite the check rather than the line inside it -- see
    `asserted_lines`.

    Two spellings count, and the split between them is what keeps two modules'
    same-named constants apart. An unqualified `TABLE["key"]` counts only inside
    the module that defines it -- `counter_sweep_entry.ORACLE` and
    `xdata_register_map.ORACLE` are different dictionaries that happen to share
    a name, and crediting one's reader to the other's value would pin a figure
    on the strength of an unrelated file. A `module.TABLE["key"]` counts
    anywhere, because that spelling says which one it means.
    """
    quoted = re.escape(key) + r"['\"]\s*\]"
    qualified = re.compile(r"\b" + re.escape(module) + r"\." + re.escape(table)
                           + r"\[\s*['\"]" + quoted)
    bare = re.compile(r"(?<![\w.])" + re.escape(table) + r"\[\s*['\"]" + quoted)
    fallback = None
    for name in sorted(texts):
        text = texts[name]
        for hit in qualified.finditer(text):
            at = text.count("\n", 0, hit.start()) + 1
            return (tool_path(name), at, asserted.get(name, {}).get(at, (at, at)))
        if name != module:
            continue
        for hit in bare.finditer(text):
            at = text.count("\n", 0, hit.start()) + 1
            if lo <= at <= hi:
                continue
            span = asserted.get(name, {}).get(at)
            if span:
                return (tool_path(name), at, span)
            fallback = fallback or (tool_path(name), at, (at, at))
    return fallback


def check_literals(texts):
    """{literal: (file, lineno)} for every int inside an asserting call.

    Read off the parse tree rather than off the text, so a number inside a
    message string is not a pin: `check("... at 0x0843 ...")` must not pin 1323
    just because the prose names an address.
    """
    found = {}
    for name in sorted(texts):
        tree = tree_of(texts[name])
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = (func.id if isinstance(func, ast.Name)
                      else func.attr if isinstance(func, ast.Attribute) else None)
            if called not in ASSERTING:
                continue
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Constant) and isinstance(sub.value, int)
                        and not isinstance(sub.value, bool)):
                    found.setdefault(sub.value, (tool_path(name), sub.lineno))
    return found


def census_csvs(texts):
    """The CSVs `xdata_register_map.py --check` regenerates, by reading its own.

    Derived from `OUT_REGISTERS`/`OUT_CLUSTERS` rather than named here, so a
    census that grows a third generated file is covered without this file
    knowing about it. An unparseable module yields no paths, which is a decline
    rather than a silent zero: every CSV-held figure then measures `unheld`,
    which is the honest reading of a search that found no CSV to search.
    """
    tree = tree_of(texts.get("xdata_register_map.py", ""))
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        target = node.targets[0]
        if not (isinstance(target, ast.Name)
                and target.id in ("OUT_REGISTERS", "OUT_CLUSTERS")):
            continue
        parts = [a.value for a in node.value.args if isinstance(a, ast.Constant)]
        if parts:
            out.append(os.path.join(EC, *parts))
    return sorted(out)


def csv_cells(paths):
    """{path: {lineno: {value, ...}}} for the given CSVs, one pass each.

    Keyed by file and line rather than by value, because the verdict is
    resolved against a `file:line` the row itself cites: a 439-row `refs`
    column is full of small integers and "any cell equal to 50" would find a
    `50` belonging to a different cluster. A cell is read whole -- the number's
    own optional thousands commas and nothing else in it -- so a digit run
    inside a hex address in another column is not a figure.
    """
    found = {}
    for path in paths:
        if not os.path.exists(path):
            continue
        rows = {}
        with open(path, newline="", encoding="utf-8") as f:
            for lineno, row in enumerate(csv.reader(f), 1):
                values = set()
                for cell in row:
                    text = cell.strip()
                    if FIGURE.fullmatch(text):
                        values.add(int(text.replace(",", "")))
                rows[lineno] = values
        found[os.path.relpath(path, REPO)] = rows
    return found


def index():
    """The one parse of the tree every measurement reads, built once.

    `measure()` is called once per figure and the tree is not small, so the
    sources, the constants, the check literals and the CSV cells are resolved
    here in a single pass rather than per lookup.
    """
    texts = {n: source(n) for n in tool_names(exclude_self=True)}
    return {"texts": texts, "oracles": oracles(texts),
            "literals": check_literals(texts),
            "asserted": asserted_lines(texts),
            "cells": csv_cells(census_csvs(texts))}


def cited_cell(value, pins, found):
    """(file, lineno) of a cited CSV line carrying `value`, or None.

    Only the lines the row cites, and only in a CSV `--check` regenerates. A row
    that cites nothing is not given a cell by this: the pin is the disambiguator
    that makes a search over 439 rows mean anything, and inventing one would
    undo that.
    """
    for name, line in pins:
        if value in found["cells"].get(name, {}).get(line, ()):
            return (name, line)
    return None


def where(read):
    """`file:line`, or `file:lo-hi` for a call the line sits inside.

    The span is what a reader verifying a pin actually wants: the `check()` that
    holds a constant is written over several lines, and the subscription is
    usually in its message rather than in the comparison below it.
    """
    name, at, (lo, hi) = read
    return f"{name}:{lo}-{hi}" if lo != hi else f"{name}:{at}"


def measure(value, pins, found):
    """(verdict, detail) for one figure, and the `file:line` that decided it.

    The order is not arbitrary. An oracle entry that something reads is the
    strongest pin there is, because the reader is an assertion; a literal inside
    a check is the same thing written inline; a cited committed cell is held only
    because a whole-file comparison would fail on it. Anything the search did
    not find is `unheld`, and `unheld` is a fact about this search.
    """
    for (module, table), (keys, lo, hi) in sorted(found["oracles"].items()):
        for key, (held, file, at) in keys.items():
            if held != value:
                continue
            read = reads(module, table, key, lo, hi, found["texts"],
                         found["asserted"])
            if read:
                return (BY_ASSERTION, f"{table}[\"{key}\"] @ {file}:{at}, "
                                     f"asserted at {where(read)}")
    hit = cited_cell(value, pins, found)
    if hit:
        return (BY_LITERAL, f"cell {value} of {hit[0]}:{hit[1]}, compared "
                            f"whole-file by --check")
    hit = found["literals"].get(value)
    if hit:
        return (BY_LITERAL, f"literal inside a check() at {hit[0]}:{hit[1]}")
    return (UNHELD, "no occurrence in ec/tools/*.py and no committed cell")


def section(text, token):
    """(lineno, level, body lines) for the heading `token` names, or raises.

    The section runs to the next heading of the same or a lower level, so a
    `###` stops at the next `##` and a `##` takes everything under it. An
    ambiguous or absent token is refused rather than guessed: a checker that
    quietly reads §2a when it was asked for §2b is a green run over the wrong
    text, which is the failure this whole tool exists to stop.
    """
    lines = text.split("\n")
    hits = []
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if not m:
            continue
        if re.search(r"(?<![0-9A-Za-z])" + re.escape(token) + r"(?![0-9A-Za-z])",
                     m.group(2)):
            hits.append((i, len(m.group(1)), m.group(2)))
    if not hits:
        raise ValueError(f"no heading in the file names {token!r}")
    if len(hits) > 1:
        raise ValueError(f"{token!r} names {len(hits)} headings -- "
                         + "; ".join(f"line {i + 1}: {t}" for i, _l, t in hits)
                         + " -- so the section is ambiguous and none was read")
    start, level, _title = hits[0]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        m = HEADING.match(lines[i])
        if m and len(m.group(1)) <= level:
            end = i
            break
    return start + 1, level, lines[start + 1:end]


def cells(unit):
    """(the cells of a markdown table row) or () if the unit is not one."""
    if not (unit.startswith("|") and unit.endswith("|")):
        return ()
    return [c.strip() for c in unit[1:-1].split("|")]


def verdict_column(header):
    """The index of the `verdict` column, or None if the table has none.

    Named, not inferred. A cell that happens to read `held` in a table about
    held things is not a marking, and a row whose figures live in a table with no
    such column is not a claim this tool may compare against anything — which is
    also what lets a correction block quote a superseded classification verbatim
    without the tool auditing the wrong version.
    """
    for i, cell in enumerate(header):
        if MARKUP.sub("", cell).strip().lower() == "verdict":
            return i
    return None


def marking(row, column):
    """(verdict, pin citations) for a row of a verdict table.

    The verdict is the cell at the declared column and nothing else, so a row
    that leaves it blank is reported rather than rescued from a neighbouring
    cell. The pins are every qualified `file:line` anywhere in the row, because a
    pin may sit in its own column or in the prose beside the figure.
    """
    text = MARKUP.sub("", row[column]).strip() if column < len(row) else ""
    pins = [(m.group("path"), int(m.group("line")))
            for cell in row for m in CITATION.finditer(cell) if m.group("path")]
    return (text if text in VERDICTS else None), pins


def figures(cell):
    """(the figure cell's numbers, the reason it is not read, or None).

    The first cell only, because that is where this corpus puts the figure and
    bounding the reader is what keeps a prose cell's "1,169 addresses" out of a
    count it was never making.
    """
    text = NOT_A_FIGURE.sub(" ", MARKUP.sub("", cell))
    found = [int(m.group(0).replace(",", "")) for m in FIGURE.finditer(text)]
    if not found:
        return ([], "no figure in the first cell")
    return (found, None)


def broken_pins(pins, figure_cell, claimed, resolved):
    """(problems) for the `file:line`s a row's own marking commits it to.

    Four rules. A cited file has to exist and the line has to be one it has —
    these citations move, and the line numbers under this very page have already
    moved once. A `held` row has to cite something, or "held" is a claim with
    nothing behind it. A `held` row's citation has to name the file the
    measurement resolved to, so a pin that has drifted onto the wrong module is
    caught rather than counted. And an `unheld` row citing anything is a
    disagreement the other way: a citation claims that something there holds the
    figure, which is exactly what `unheld` denies.
    """
    problems = []
    for name, line in pins:
        path = os.path.join(REPO, name)
        if not os.path.exists(path):
            problems.append(f"the row for {figure_cell} names {name}:{line}, and "
                            f"{name} is not in the tree")
            continue
        with open(path, encoding="utf-8") as f:
            total = sum(1 for _ in f)
        if not 1 <= line <= total:
            problems.append(f"the row for {figure_cell} names {name}:{line}, and "
                            f"{name} has {total} line(s)")
    if claimed == DECLINED:
        return problems
    if not resolved:
        if pins and claimed == HELD:
            # Measured unheld and the row cited something: the citation is the
            # claim, and the measurement is what disagrees with it.
            problems.append(f"the row for {figure_cell} is marked {HELD!r} and "
                            f"cites a pin, but nothing in the tree holds the "
                            f"figure")
        elif claimed != HELD and pins:
            problems.append(f"the row for {figure_cell} is marked {claimed!r} but "
                            f"names a pin")
        return problems
    if claimed != HELD:
        return problems
    if not pins:
        return problems + [f"the row for {figure_cell} is marked {HELD!r} but "
                           f"names no `file:line` to pin it with"]
    cited = {name for name, _line in pins}
    for name in sorted(resolved - cited):
        problems.append(
            f"the held row for {figure_cell} cites "
            + ", ".join(f"{n}:{l}" for n, l in pins)
            + f", but the pin that measures it is in {name}")
    return problems


def tables(body):
    """[(header, [(lineno, row)])] for every markdown table in the body.

    A table is a header row, a delimiter row, then body rows, and anything else
    ends it -- which is how markdown itself decides, and why the prose between
    two tables and the blockquote of a correction block are both skipped without
    either being special-cased. The delimiter is required: two adjacent rows
    with no rule between them are not a table and are not read as one.
    """
    out, run = [], []

    def flush():
        if len(run) >= 2 and DELIMITER.match(run[1][1]):
            out.append((run[0][1], [(offset, row) for offset, _s, row in run[2:]]))
        run.clear()

    for offset, unit in enumerate(body):
        stripped = unit.strip()
        row = cells(stripped)
        if len(row) < 2:
            flush()
            continue
        run.append((offset, stripped, row))
    flush()
    return out


def audit(body, found):
    """(results, declined, problems) for one section's body.

    A result is `(figure, claimed, verdict, detail)` per figure, in the order the
    document lists them, so the report and the exit code read the same walk.
    Declined rows are `(cell, reason)`: counted and printed, never a failure.
    """
    results, declined, problems, marked = [], [], [], 0
    for header, rows in tables(body):
        column = verdict_column(cells(header))
        if column is None:
            continue
        marked += 1
        for offset, row in rows:
            claimed, pins = marking(row, column)
            values, _why = figures(row[0])
            if claimed is None:
                problems.append(f"line {offset + 1}: a row of a table with a "
                                f"verdict column marks nothing; every figure row "
                                f"of one has to say {HELD!r}, {UNHELD!r} or "
                                f"{DECLINED!r}")
                continue
            if not values:
                declined.append((MARKUP.sub("", row[0]).strip(),
                                  "no figure in the first cell"))
                continue
            resolved = set()
            for value in values:
                verdict, detail = measure(value, pins, found)
                results.append((value, claimed, verdict, detail))
                hit = re.search(r"([\w./-]+\.(?:py|md|csv|ya?ml)):\d+", detail)
                if hit:
                    resolved.add(hit.group(1))
            problems += broken_pins(
                pins, MARKUP.sub("", row[0]).strip(), claimed, resolved)
    if not marked:
        problems.append("no table in this section has a column headed 'verdict', "
                        "so no figure in it was measured -- a section that stops "
                        "declaring its held/unheld split would otherwise report a "
                        "clean run")
    return results, declined, problems


def disagreements(results):
    """(problems) for every result whose measured verdict is not the marked one.

    A `not read by this method` row is never compared: it is the row saying the
    figure is out of this method's reach, and the measurement cannot disagree
    with a row that agrees it has nothing to say.
    """
    problems = []
    for value, claimed, verdict, detail in results:
        if claimed == DECLINED:
            continue
        if (verdict in HELD_VERDICTS) != (claimed == HELD):
            problems.append(f"the row marks {value} {claimed!r}; measured "
                            f"{verdict!r} ({detail})")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc", help="the markdown file to read a section out of")
    ap.add_argument("--section", required=True,
                    help="the section to measure, as the heading writes it -- "
                         "`2b` for the `### 2b.` heading. Refused rather than "
                         "guessed if the token names more than one heading")
    ap.add_argument("--verbose", action="store_true",
                    help="name every constant and CSV cell the search covered, "
                         "so a reader can see how wide 'unheld' was measured over")
    args = ap.parse_args()

    path = args.doc if os.path.exists(args.doc) else os.path.join(REPO, args.doc)
    if not os.path.exists(path):
        print(f"{args.doc} is not a file in this tree", file=sys.stderr)
        return 2
    try:
        with open(path, encoding="utf-8") as f:
            _lineno, _level, body = section(f.read(), args.section)
    except (ValueError, SyntaxError) as e:
        print(f"{os.path.relpath(path, REPO)}: {e}", file=sys.stderr)
        return 2

    found = index()
    where = f"{os.path.relpath(path, REPO)} §{args.section}"
    results, declined, structural = audit(body, found)
    problems = structural + disagreements(results)

    for value, claimed, verdict, detail in results:
        print(f"  {value:>6}  {verdict:<22} {detail}  [marked {claimed}]")
    for cell, why in declined:
        print(f"  {cell[:44]:<44} {DECLINED:<22} {why}  [not compared]")

    seen = results
    held = sum(1 for r in seen if r[2] in HELD_VERDICTS)
    print(f"{where}: {len(seen)} figure(s), {held} measured held, "
          f"{len(seen) - held} measured unheld, {len(declined)} not read by this "
          f"method (searched {len(found['oracles'])} module-level constant(s), "
          f"{len(found['literals'])} literal(s) inside a check, and the cited lines "
          f"of {len(found['cells'])} committed CSV(s))")
    if args.verbose:
        for (module, table), (keys, lo, hi) in sorted(found["oracles"].items()):
            print(f"  constant {table} @ {tool_path(module)}:{lo}-{hi} -- "
                  + ", ".join(f"{k}={v}" for k, (v, _f, _l) in sorted(keys.items())))
        print(f"  csv read: {', '.join(sorted(found['cells'])) or 'none found'}")

    for line in problems:
        print(f"{where}: {line}", file=sys.stderr)
    if problems:
        print(f"{where}: the section's own marking disagrees with the measurement "
              f"on {len(problems)} point(s)", file=sys.stderr)
        return 1
    print(f"{where}: the section's own marking agrees with the measurement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
