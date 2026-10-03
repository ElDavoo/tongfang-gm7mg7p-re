#!/usr/bin/env python3
r"""Hold the `DBD1`/`DBD2` census: two names, two hits each, both accounted for.

`docs/findings.md` 3d and `ec/annotations/ec-0x07d1-sites.md` 6 both say the
DSDT declares `0x07D0`/`0x07D1` as two independent 8-bit fields while the PD
firmware handles them as halves of a 16-bit quantity. The second half of that
sentence was never measured; this is what measures it, and what keeps it
measured.

**Four censuses, all derived from committed inputs, none transcribed.**

  1. *Name census.* For `DBD1`, `DBD2` and `ECMG`: every occurrence in
     `evidence/acpi/dsdt.dsl`, each classified as a store or as a declaration,
     and every one asserted to fall inside a span this tool derives rather than
     a line range it carries. The two spans are the `T1WR` `Arg0 == 0x1173`
     arm (brace-matched from its `ElseIf`) and the `ECMG` declaration (from its
     `OperationRegion` through the closing brace of its `Field` list). A reader
     added anywhere else in the file lands outside both and fails; a reader
     added *inside* the arm keeps its span and fails on the count, which is why
     both checks exist and neither is the load-bearing one alone.
  2. *Route census.* Every `SystemMemory` `OperationRegion` in the file whose
     base is not a literal, the method each sits in, whether that method is
     called, and what the base resolves to. Derived from the file rather than
     carried as a list of names, because the file has dozens of these and no
     hand-written list of three is the file's set -- see `computed_base_routes`
     for what that changes and `UNBOUNDED` for the limit it leaves.
  3. *Coverage census.* What fraction of the `ECMG` window the field list
     declares at all, so "leaves `0x07D2` unnamed" can be stated as what it is
     -- a property of the list, not a hole cut around one byte.
  4. *Reconciliation.* Census 3's bit total against the `width` column of the
     committed `ec/annotations/dsdt-ecmg-fields.csv`, so a `Field` edit that
     moves a figure is caught in both places at once.

**What the trailing comma is about, since it cost a figure.** The element
pattern's last element is the one iasl does not put a comma after: `MGOF,   8`
carries none, where every element above it carries one. The pattern that
requires it (`...,\s*$`) therefore drops `MGOF` silently, and the census it
feeds reads 759 bits instead of 767 -- a shortfall of exactly the eight bits
that element declares. Nothing failed; the number was just wrong, which is the
worse outcome. So the comma is optional here, and `--self-test` pins a fixture
whose last element has no comma so this cannot be reintroduced by a well-
meaning "tidy the pattern" edit.

**Calibration, which is most of what this file is for.** Every claim is scoped
to the ASL, and that scope is load-bearing: a DSDT that declares two bytes and
never reads them says nothing about what the EC firmware does with them, and
`0x07D0`/`0x07D1` keep `unknown-not-absent-DO-NOT-WRITE-BLIND`. The one place
this tool would be tempted to overclaim is census 2's denominator -- 65 536 is
the window's length, and a byte inside the window that no field list names is
*undeclared*, not free and not absent. Nothing here opens an EC image, so no
figure below is evidence about the EC, and no zero here is ever a verdict.

**Why a new file and not a mode on `dsdt_ec_fields.py`.** That tool already
parses this field list, but it is a different question -- it joins each element
to a `MOV DPTR` census and opens the firmware image to do it. This one opens
no image, so it can sit in a cheap gate beside `check_status_vocabulary.py`
and `call_graph.py`, and adding a mode there would put a no-image check behind
an argument that requires one. `dsdt_ec_fields.py --check` still proves the
committed CSV byte for byte; this reconciles against it rather than replacing
it.

Usage:
    python3 ec/tools/check_dsdt_ecmg_pair.py --check
    python3 ec/tools/check_dsdt_ecmg_pair.py --self-test
"""

import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
DEFAULT_DSDT = os.path.join(REPO, "evidence", "acpi", "dsdt.dsl")
DEFAULT_CSV = os.path.join(REPO, "ec", "annotations", "dsdt-ecmg-fields.csv")

# The window `OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)`
# declares, read as its length rather than transcribed: a census that divides
# by a number carried here would quietly mean something else if the region
# changed. Parsed out of the declaration itself, so the denominator and the
# numerator come from the same commit.
LENGTH_RE = re.compile(r"^\s*OperationRegion\s*\(\s*ECMG\s*,[^,]+,\s*"
                       r"(0x[0-9A-Fa-f]+|\d+)\s*,\s*"
                       r"(0x[0-9A-Fa-f]+|\d+)\s*\)\s*$")

REGION_RE = re.compile(r"^\s*OperationRegion\s*\(\s*ECMG\s*,")
FIELD_RE = re.compile(r"^\s*Field\s*\(\s*ECMG\s*,")
OFFSET_RE = re.compile(r"^\s*Offset\s*\(\s*(0x[0-9A-Fa-f]+|\d+)\s*\)")
# The name is `*` rather than the `{0,4}` the issue's parse used. Every name
# this list happens to declare is short enough that the bound never bit here --
# which is exactly why it is a trap: a fifth character would drop the line
# from the census with nothing to say so. Reconciliation against the committed
# CSV is the backstop that catches it, and it fails on its own if a longer name
# ever appears. The trailing comma is optional; see the docstring. The
# pattern is a named string so `--self-test` can put the comma back and then
# put the real one back without either copy drifting.
ELEMENT_PATTERN = r"^\s*([A-Za-z0-9_]*)\s*,\s*(\d+)\s*,?\s*$"
ELEMENT_RE = re.compile(ELEMENT_PATTERN)

# The writer under examination. Named by the argument value rather than by a
# line, so a DSDT revision that moves the arm is followed instead of missed.
WRITER_ARG = "0x1173"
ARM_RE = re.compile(r"^\s*ElseIf\s*\(\s*\(\s*Arg0\s*==\s*" + WRITER_ARG +
                    r"\s*\)\s*\)\s*$")

# **The other routes to this window, and why no list of names can be the
# file's set of them.**
#
# `ECRR` and `ECRW` hardcode the base `ECMG` itself declares -- `Local0 =
# (0xFE410000 + Arg0)` -- and then read or write that byte through the
# `OperationRegion (MMNM, SystemMemory, Arg0, 0x04)` that `MMRW` builds at
# dsdt.dsl:50423. `ECRR` is a *reader*: `ECRR (0x07D0)` reads the `DBD1` byte
# with no field name anywhere in the path, so `DBD1`'s two hits do not by
# themselves show that no reader exists.
#
# Naming `ECRR`, `ECRW` and `SMRW` and calling that the file's computed-base
# methods was wrong, and not by a small margin. The file declares far more
# `OperationRegion`s at a non-literal base than that, in methods that *are*
# called -- so a claim resting on "none of the three is invoked" was resting
# on a three-element list that a fourth entry would have invalidated
# silently, leaving `--check` green. `computed_base_routes` therefore derives
# the set from the file; these three are kept below only as the ones a
# document names, not as an exhaustive enumeration.
ACCESSORS = ("ECRR", "ECRW", "SMRW")

# What the derived census cannot answer, stated here because it is the reason
# the conclusion is scoped rather than absolute. Most of the file's
# computed-base regions take their base from a runtime value -- an argument, a
# local computed from one, or a method's return -- so *which window they reach
# is not a property of the committed source*. One of them builds its base from
# `XBAS`, which is declared `External` at dsdt.dsl:335 and defined nowhere in
# this file, so no committed input bounds it at all. A route the scan cannot
# place is reported as unbounded rather than counted as safe, and no document
# may read "the scan found nothing" as "there is nothing".
UNBOUNDED = "unresolved-base"


def method_re(name):
    """The `Method (NAME, ...)` declaration line for `name`."""
    return re.compile(r"^\s*Method\s*\(\s*" + re.escape(name) + r"\s*,")


def call_re(name):
    """An invocation of `name`: the name followed by `(`, and nothing else.

    That is the form iasl writes a method call in -- `MMRW (Local0, Zero, Zero,
    Zero)` at dsdt.dsl:50500 is inside `ECRR`'s own body -- and it excludes
    the declaration, where `NAME` is followed by a comma. Counting whole-word
    mentions instead would not do, for a reason worth carrying: `ECRW` is
    *also* the name of a `CreateBitField` over `BUF0` in an unrelated scope,
    at dsdt.dsl:4437-4438. One spelling, two objects, three occurrences, and
    only the parenthesised form is a call, so a mention count would report a
    caller that is not one and refuse a file that is correct.
    """
    return re.compile(r"\b" + re.escape(name) + r"\s*\(")

# The census this file exists to hold. Two hits per name, each accounted for:
# `DBD1` and `DBD2` are each one store and one declaration, and `ECMG` is
# declared twice over (`OperationRegion` and `Field`) and used nowhere else.
EXPECTED = {
    "DBD1": {"store": 1, "declaration": 1},
    "DBD2": {"store": 1, "declaration": 1},
    "ECMG": {"store": 0, "declaration": 2},
}

# Census 2's expected figures, for the same reason. Every one is a property of
# the committed `dsdt.dsl` -- a vendor input no change to this repository can
# move -- so asserting them is asserting a measurement rather than a fact about
# this repository's own prose.
EXPECTED_ANCHORS = 28
EXPECTED_BITS = 767
EXPECTED_NAMED_BITS = 751
EXPECTED_UNNAMED_BITS = 16
EXPECTED_GAPS = 23


def _number(text):
    """The int `text` is written as, hex or decimal -- iasl emits both."""
    return int(text, 16) if text.lower().startswith("0x") else int(text)


def read_lines(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read().split("\n")


def block_end(lines, start):
    """The line index of the `}` closing the brace opened at or after `start`.

    Brace-matched rather than "first line starting with `}`", because the field
    list has no nesting today and a pattern that depends on that is a pattern
    that breaks quietly on the first nested one.
    """
    depth = 0
    opened = False
    for index in range(start, len(lines)):
        depth += lines[index].count("{") - lines[index].count("}")
        if "{" in lines[index]:
            opened = True
        if opened and depth <= 0:
            return index
    return None


def find_span(lines, pattern):
    """(first, last) line index of the block `pattern` opens.

    Starting the match on the `OperationRegion` line is deliberate and needs
    no second step: that line opens no brace of its own, so the brace matcher
    runs on to the first `{` -- the `Field` list's -- and closes on that
    list's last element. The span therefore covers the region declaration and
    its field list together, which is what makes two `ECMG` hits rather than
    one inside it; a span covering only one of them would put a correct file
    into the "outside every span" failure.
    """
    for index, line in enumerate(lines):
        if pattern.match(line):
            end = block_end(lines, index)
            return None if end is None else (index, end)
    return None


def in_spans(index, pair):
    """Whether line index `index` sits inside any span in `pair`."""
    return any(span is not None and span[0] <= index <= span[1]
               for span in pair)


def spans(lines):
    """(ecmg, field, writer) line spans, or a reason one could not be found.

    Returned as data rather than asserted inline so the suite can hand this a
    fixture with a brace removed and see the refusal name which span went.
    """
    region = find_span(lines, REGION_RE)
    field = find_span(lines, FIELD_RE)
    writer = find_span(lines, ARM_RE)
    missing = [name for name, span in (("ECMG region", region),
                                       ("ECMG field list", field),
                                       ("T1WR Arg0 == %s arm" % WRITER_ARG,
                                        writer)) if span is None]
    if missing:
        return (region, field, writer), "no %s in the file" % ", no ".join(missing)
    return (region, field, writer), None


def classify(line, name):
    """How `line` uses `name`: a store, a declaration, or neither.

    A store is a name on the left of an `=`, which is the only ASL form that
    writes a field. Anything else that mentions the name is a declaration or a
    load, and the two are told apart by whether the name is an element of a
    field list. This is what catches a reader added *inside* the writer arm:
    the span check cannot see it, because it is legitimately inside a named
    span, and the classification can.
    """
    stripped = line.split("//", 1)[0]
    if re.search(re.escape(name) + r"\s*=(?!=)", stripped):
        return "store"
    element = ELEMENT_RE.match(stripped)
    if (element and element.group(1) == name) or REGION_RE.match(stripped) \
            or FIELD_RE.match(stripped):
        return "declaration"
    return "other"


def name_census(lines, name, span):
    """(entry, problems) for `name` -- every occurrence, classified and sited."""
    region, _field, writer = span
    hits, tally, problems = [], {"store": 0, "declaration": 0}, []
    for index, line in enumerate(lines):
        # A whole-word occurrence, qualified or bare: the store is written
        # `^^PCI0.LPCB.EC0.DBD1`, so a guard that drops anything preceded by a
        # dot drops the store and leaves only the declaration. A qualified
        # occurrence of *another region's* same-spelled name outside the spans
        # is refused by name and with its line printed rather than skipped,
        # which is the right way for it to show up -- an exact total means a
        # false positive is a refusal a maintainer can read, not a wrong
        # number nobody notices.
        if not re.search(r"\b" + re.escape(name) + r"\b", line):
            continue
        hits.append(index + 1)
        kind = classify(line, name)
        if kind in tally:
            tally[kind] += 1
        if kind == "other":
            problems.append(
                "%s: %d mentions %s in a form that is neither a store nor a "
                "declaration:\n    %s\n"
                "    A reader has been added, or a third form has. Either way "
                "the two-hits claim no longer describes the file." %
                (name, index + 1, name, line.strip()))
        if not in_spans(index, (region, writer)):
            problems.append(
                "%s: %d is outside both the %s and the ECMG field list:\n"
                "    %s\n"
                "    Every occurrence has to be one of the two things this "
                "census counts. A hit anywhere else is a third site, and the "
                "claim is about there being two." %
                (name, index + 1,
                 "T1WR Arg0 == %s arm" % WRITER_ARG, line.strip()))
    return {"name": name, "lines": hits, "tally": tally}, problems


def accessor_census(lines, names=ACCESSORS):
    """{name: {"declarations": [line], "calls": [(line, text)]}} for `names`.

    Retained because these three are the ones the documents name, and the
    refusal below has to speak about the route a reader would actually take
    (`ECRR (0x07D0)`) rather than about an index into a list. It is *not* the
    file's set of computed-base methods -- `computed_base_routes` is.
    """
    out = {}
    for name in names:
        declared, calls = method_re(name), call_re(name)
        out[name] = {"declarations": [], "calls": []}
        for index, line in enumerate(lines):
            code = line.split("//", 1)[0]
            if declared.match(code):
                out[name]["declarations"].append(index + 1)
            elif calls.search(code):
                out[name]["calls"].append((index + 1, line.strip()))
    return out


# The `OperationRegion` form whose base this census keys on. Anchored on
# `SystemMemory` because that is the address space `ECMG` itself uses: a
# `PCI_Config` or `SystemIO` region cannot reach an XDATA byte, so including
# those would inflate the route count with things that are not routes to this
# window. The base is captured whole rather than pattern-matched for a literal,
# because "is not a literal" is the whole test.
COMPUTED_REGION_RE = re.compile(
    r"^\s*OperationRegion\s*\(\s*(\w+)\s*,\s*SystemMemory\s*,\s*(.+?)\s*,"
    r"\s*(0x[0-9A-Fa-f]+|\d+)\s*\)")
LITERAL_BASE_RE = re.compile(r"^(0x[0-9A-Fa-f]+|\d+)$")

METHOD_DECL_RE = re.compile(r"^\s*Method\s*\(\s*(\w+)\s*,")


def enclosing_methods(lines):
    """[innermost enclosing Method name or None] for each line.

    A reader with no caller is only a route if something calls it, and what
    something calls is a *method* -- so the question "is this region's method
    invoked" needs the method each region sits in. Brace-matched rather than
    scoped by indentation, for the reason `block_end` gives: the field list has
    no nesting today and a pattern that depends on that breaks quietly on the
    first nested one.

    The declaration and the brace it opens are usually on *separate* lines
    (`Method (X, 2, NotSerialized)` then `{`), so a pending declaration is
    carried to the next brace rather than pushed where it is seen. Associating
    the two wrongly -- pushing a placeholder on the brace line -- attributes
    every region in the file to whichever scope opened last, which is how this
    reported every one of them as uncalled.
    """
    stack, out, pending = [], [], None
    for line in lines:
        out.append(next((name for kind, name in stack if kind == "method"),
                        None))
        code = line.split("//", 1)[0]
        opens, closes = code.count("{"), code.count("}")
        declaration = METHOD_DECL_RE.match(code)
        if declaration:
            pending = declaration.group(1)
        if opens:
            stack.append(("method", pending) if pending else ("other", None))
            pending = None
        for _ in range(closes):
            if stack:
                stack.pop()
    return out


def literal_names(lines):
    """{name: value} for every `Name (X, 0x...)` declared in the file.

    Needed because a computed base is often a *named* constant rather than an
    expression, and `EMPB`'s kind of name has to resolve to something before
    the scan can say where it points. Names declared `External` are absent by
    construction, which is exactly why a base built from one is unbounded.
    """
    out = {}
    for line in lines:
        match = re.match(r"^\s*Name\s*\(\s*(\w+)\s*,\s*"
                         r"(0x[0-9A-Fa-f]+|\d+)\s*\)", line)
        if match:
            out[match.group(1)] = int(match.group(2), 16)
    return out


def resolve_base(expression, names):
    """The constant an `OperationRegion` base evaluates to, or `None`.

    Returns `None` rather than guessing whenever any part of the expression is
    a runtime value -- an `Arg`, a `Local`, or a method call. That is the
    honest answer and it is what most of this file's computed bases produce:
    a base the scan cannot place is a base it cannot clear, and reporting it
    as safe is the failure mode this function exists to prevent.
    """
    text = expression.strip()
    if LITERAL_BASE_RE.match(text):
        return int(text, 16)
    if re.search(r"\w+\s*\(", text):        # a method call: opaque
        return None
    # Substitute the names we can resolve, then refuse anything still holding
    # a bare identifier: an unresolved token is an unknown value, and folding
    # around it would invent a number.
    def substitute(match):
        token = match.group(0)
        return hex(names[token]) if token in names else None
    folded = re.sub(r"\b[A-Za-z_]\w*\b", substitute, text)
    if re.search(r"\b[A-Za-z_]\w*\b", folded):
        return None
    folded = folded.replace("<<", " << ").replace(">>", " >> ")
    try:
        value = eval(folded, {"__builtins__": {}}, {})  # noqa: S307
    except Exception:
        return None
    return value if isinstance(value, int) else None


def computed_base_routes(lines, window_base, window_length):
    """Every `SystemMemory` region at a non-literal base, and where it reaches.

    Returns `{"invoked": [...], "uncalled": [...], "unbounded": [...]}`,
    each entry naming the region, its line, the method that contains it, and
    -- where the base folds to a constant -- whether that constant overlaps the
    window at all.

    This is the census that replaces a hard-coded accessor list, and the
    division it reports is the finding. Three outcomes, and the third is the
    one a name list could never produce:

      * **invoked** -- the region's method is called *and* the base folds to a
        constant outside the window. This is a route to somewhere else, and it
        is the only category that can be cleared.
      * **uncalled** -- the region's method is never called. `ECRR` and
        `ECRW` are here, which is what makes the conclusion survive: they are
        genuine readers of `0x07D0` that nothing in the file ever reaches.
      * **unbounded** -- the base is a runtime value. The scan cannot say
        where it points, so it is reported rather than counted either way. A
        DSDT revision that turns one of these into a constant is caught; one
        that leaves it a runtime value is not, and no document may claim
        otherwise.
    """
    names = literal_names(lines)
    enclosing = enclosing_methods(lines)
    invoked, uncalled, unbounded = [], [], []
    for index, line in enumerate(lines):
        match = COMPUTED_REGION_RE.match(line.split("//", 1)[0])
        if not match:
            continue
        region, base = match.group(1), match.group(2).strip()
        length = int(match.group(3), 16)
        method = enclosing[index]
        entry = {"region": region, "line": index + 1, "base": base,
                 "length": length, "method": method}
        if method is None:
            entry["state"] = UNBOUNDED
            unbounded.append(entry)
            continue
        declared = call_re(method)
        callers = [i + 1 for i, other in enumerate(lines)
                   if declared.search(other.split("//", 1)[0])
                   and not other.split("//", 1)[0].strip().startswith("Method")]
        entry["callers"] = callers
        if not callers:
            entry["state"] = "uncalled"
            uncalled.append(entry)
            continue
        value = resolve_base(base, names)
        if value is None:
            # Reached, but not placeable: reported, never counted as clear.
            entry["state"] = UNBOUNDED
            unbounded.append(entry)
            continue
        entry["resolves"] = value
        # A route is only *cleared* by a constant that lands outside the
        # window. One that lands inside it is a reader, with no field name
        # anywhere in the path, and no count of `DBD1` occurrences can see it.
        overlaps = value < window_base + window_length and \
            value + length > window_base
        entry["state"] = "invoked-into-window" if overlaps else "invoked"
        invoked.append(entry)
    return {"invoked": invoked, "uncalled": uncalled,
            "unbounded": unbounded}


def region_length(lines, span):
    """The byte length the `ECMG` `OperationRegion` declares."""
    region = span[0]
    for index in range(region[0], region[1] + 1):
        match = LENGTH_RE.match(lines[index])
        if match:
            return _number(match.group(2))
    return None


def window_bounds(lines, span):
    """`(base, length)` of the `ECMG` window, read off its own declaration.

    Parsed rather than carried, so the route census compares against the same
    commit that declared the region. A route that lands inside *these* bounds
    is a reader of this window; one compared against a number typed here would
    quietly mean something else if the vendor moved the region.
    """
    region = span[0]
    for index in range(region[0], region[1] + 1):
        match = LENGTH_RE.match(lines[index])
        if match:
            return _number(match.group(1)), _number(match.group(2))
    return 0, 0


def element_positions(lines, span):
    """{name: (anchor offset, first bit, width)} for the field list.

    This is what makes "two independent 8-bit fields" a measurement rather
    than a restatement. Walking the list gives each name the byte it sits at
    and the bit it starts on, so "both 8 bits, under one anchor, the second
    starting where the first ends" is something the census reports instead of
    something the sentence asserting it carries.

    What it deliberately does not check is whether two fields *overlap*; see
    the comment at the call site for why that rule cannot fire.
    """
    _region, field, _writer = span
    anchor, bit = None, 0
    positions = {}
    for index in range(field[0], field[1] + 1):
        line = lines[index]
        match = OFFSET_RE.match(line)
        if match:
            anchor, bit = _number(match.group(1)), 0
            continue
        match = ELEMENT_RE.match(line)
        if not match:
            continue
        width = int(match.group(2))
        if match.group(1) and anchor is not None:
            positions[match.group(1)] = (anchor, bit, width)
        bit += width
    return positions


def declared_widths(lines, span):
    """{name: width} for every named element in the ECMG field list.

    A projection of `element_positions`, so the widths the check asserts and
    the widths the printout shows come from one walk and cannot disagree.
    """
    return {name: width for name, (_a, _b, width) in
            element_positions(lines, span).items()}


def allocated_bytes(lines, span):
    """The byte offsets every element of the ECMG field list allocates.

    Walking the list the way ASL lays it out gives each element the byte its
    bits actually land in, which is not always the anchor: `Offset (0x7D4)`
    allocates `0x07D4` through `0x07D7` for `CPUA`, `DBAP`, `DBSP` and
    `CGCT`. That carry is the whole reason the undeclared stretches have to be
    derived by expanding the list to absolute addresses rather than by
    measuring the distance between anchors -- an anchor-to-anchor gap is not a
    gap between declared bytes, and reading it as one puts `0x07D5`-`0x07D7`
    inside an undeclared stretch that four elements fill.
    """
    _region, field, _writer = span
    allocated, anchor, bit = set(), None, 0
    for index in range(field[0], field[1] + 1):
        line = lines[index].split("//", 1)[0]
        match = OFFSET_RE.match(line)
        if match:
            anchor, bit = _number(match.group(1)), 0
            continue
        match = ELEMENT_RE.match(line)
        if not match or anchor is None:
            continue
        width = int(match.group(2))
        allocated.update(anchor + offset // 8 for offset in range(bit, bit + width))
        bit += width
    return allocated


def contiguous(values):
    """The `[start, end]` runs in an ascending list of offsets."""
    runs = []
    for value in values:
        if runs and runs[-1][1] == value - 1:
            runs[-1][1] = value
        else:
            runs.append([value, value])
    return [tuple(run) for run in runs]


def undeclared_between_anchors(lines, span):
    """What the list does not cover, measured as bytes rather than as gaps.

    Two figures, both defined where they are printed because either is
    meaningless without its definition:

      * `count` -- offsets between the first and last anchor that no element
        allocates. This is the complement of the allocated set, so a
        multi-byte element's continuation bytes are excluded rather than
        counted twice, which is what summing the anchor-to-anchor gaps would
        do.
      * `longest` -- the largest contiguous run of those. A run's endpoints
        matter as much as its length: `Offset (0x7D4)` covers four whole
        bytes, so the stretch that follows it starts one byte later than the
        anchor suggests.

    Returns `(count, longest_run, first_anchor, last_anchor)`, and a `longest`
    of `None` when the list allocates everything between its two anchors.
    """
    allocated = allocated_bytes(lines, span)
    _region, field, _writer = span
    anchors = [_number(OFFSET_RE.match(lines[i]).group(1))
               for i in range(field[0], field[1] + 1)
               if OFFSET_RE.match(lines[i])]
    if not anchors:
        return None, None, None, None
    first, last = anchors[0], anchors[-1]
    gaps = contiguous(b for b in range(first, last + 1) if b not in allocated)
    longest = max(gaps, key=lambda run: run[1] - run[0]) if gaps else None
    return sum(end - start + 1 for start, end in gaps), longest, first, last


def coverage_census(lines, span):
    """The field list measured: anchors, bits, bytes, named split, gaps.

    Every figure is counted, none carried. `gaps` is *consecutive anchors more
    than one byte apart*, and the definition is stated where the number is
    printed because a gap count means nothing without one -- `gap_pairs` is
    carried beside the count so the definition can be checked against it
    rather than taken on trust. That count is not an undeclared-byte count and
    is not used as one; `undeclared_*` below is, and it is measured by
    expanding the list rather than by adding up the gaps.
    """
    region, field, _writer = span
    anchors, bits, named, unnamed, elements = [], 0, 0, 0, 0
    unnamed_count = 0
    for index in range(field[0], field[1] + 1):
        line = lines[index]
        match = OFFSET_RE.match(line)
        if match:
            anchors.append((_number(match.group(1)), index + 1))
            continue
        match = ELEMENT_RE.match(line)
        if match:
            width = int(match.group(2))
            bits += width
            elements += 1
            if match.group(1):
                named += width
            else:
                unnamed += width
                unnamed_count += 1
    gaps = [(a[0], b[0]) for a, b in zip(anchors, anchors[1:])
            if b[0] - a[0] > 1]
    undeclared, longest, first, last = undeclared_between_anchors(lines, span)
    return {
        "anchors": len(anchors),
        "bits": bits,
        "elements": elements,
        "unnamed_elements": unnamed_count,
        "named_bits": named,
        "unnamed_bits": unnamed,
        # A field list does not have to fill whole bytes -- `0x07D3` declares
        # seven of its eight and the next `Offset` moves on. `whole_bytes` is
        # the figure the issue's parse printed (`bits // 8`) and `spare_bits`
        # is what that division rounds away, so no reader takes 95 to mean
        # "95 bytes, exactly".
        "whole_bytes": bits // 8,
        "spare_bits": bits % 8,
        "gaps": len(gaps),
        "gap_pairs": gaps,
        "undeclared_bytes": undeclared,
        "longest_undeclared_run": longest,
        "first_anchor": first,
        "last_anchor": last,
        "region_bytes": region_length(lines, span),
        "region_line": region[0] + 1,
        "field_line": field[0] + 1,
        "span": span,
    }


def undeclared_bits(lines, span, offset):
    """(declared, present) bit count in the byte at `offset`, from the list.

    `present` is how many of the byte's eight bits an `Offset` element claims
    by position, which is 8 for any anchor in the list -- iasl keeps the bit
    cursor running until the next `Offset` even when the sum is short. The gap
    between the two is a bit the list skips over, and `0x07D3` is where it
    happens: four unnamed bits, `GFID`'s three, then straight to `Offset
    (0x7D4)`.
    """
    _region, field, _writer = span
    declared = 0
    inside = False
    for index in range(field[0], field[1] + 1):
        line = lines[index]
        match = OFFSET_RE.match(line)
        if match:
            if inside:
                break
            if _number(match.group(1)) == offset:
                inside = True
            continue
        if inside:
            match = ELEMENT_RE.match(line)
            if match:
                declared += int(match.group(2))
    return declared, 8


def csv_widths(path):
    """The `width` column of the committed CSV, and its row count."""
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return sum(int(row["width"]) for row in rows), len(rows)


def census(dsdt, fields_csv):
    """(problems, census) for the pair of files named.

    Everything here is derived from those two files, so the same call answers
    the same question about a fixture as about the committed tree. That is the
    split from `expectations`: a cut-down field list is not the committed
    `dsdt.dsl` and cannot satisfy its figures, so a caller that wants to know
    whether a *fixture* parses cleanly must not be handed the question of
    whether it is the right size.
    """
    lines = read_lines(dsdt)
    span, missing = spans(lines)
    if missing:
        return [missing], None

    problems, out = [], {"span": span}
    out["widths"] = declared_widths(lines, span)
    for name in ("DBD1", "DBD2", "ECMG"):
        entry, found = name_census(lines, name, span)
        problems.extend(found)
        out[name] = entry
        want = EXPECTED[name]
        if entry["tally"] != want:
            problems.append(
                "%s: %d occurrences, %d store(s) and %d declaration(s); "
                "expected %s.\n"
                "    The whole claim is that this name appears exactly twice "
                "and that both hits are accounted for. A count that moved is "
                "the DSDT changing under a document that still cites it." %
                (name, len(entry["lines"]), entry["tally"]["store"],
                 entry["tally"]["declaration"],
                 ", ".join("%d %s" % (v, k) for k, v in sorted(want.items()))))

    out["coverage"] = cover = coverage_census(lines, span)
    if cover["region_bytes"] is None:
        problems.append("the ECMG OperationRegion declares no length, so the "
                        "coverage denominator would be a number from nowhere")

    out["07d3"] = undeclared_bits(lines, span, 0x07D3)
    out["positions"] = positions = element_positions(lines, span)
    for name in ("DBD1", "DBD2"):
        if name not in positions:
            problems.append("%s is not an element of the ECMG field list, so "
                            "the 'two independent 8-bit fields' claim has "
                            "nothing to be about" % name)
    if "DBD1" in positions and "DBD2" in positions:
        first, second = positions["DBD1"], positions["DBD2"]
        if first[2] != 8 or second[2] != 8:
            problems.append("DBD1/DBD2 are declared %d and %d bits wide; the "
                            "claim says 8 and 8" % (first[2], second[2]))
        if first[0] != second[0]:
            problems.append("DBD1 sits at anchor 0x%X and DBD2 at 0x%X, so "
                            "they are not the pair the claim describes"
                            % (first[0], second[0]))
        # Whether the two *overlap* is deliberately not checked, and the
        # reason is worth more than the check would be. An ASL element list
        # assigns bit ranges sequentially, so two elements under one anchor
        # cannot overlap however the list is edited -- the only way to make
        # them share a bit is to delete the element between them, and the
        # ranges stay disjoint when you do. Disjointness is therefore a
        # property of ASL's grammar rather than of this DSDT, and a rule that
        # cannot fire reads as a guarantee it does not make. What can move is
        # the two widths and the two anchors, and those are checked.

    out["accessors"] = accessors = accessor_census(lines)
    for name, entry in accessors.items():
        for line, text in entry["calls"]:
            problems.append(
                "%s is invoked at %d:\n    %s\n"
                "    %s is one of the file's computed-base methods, so a call "
                "reaches the window at a base no field name appears in -- for "
                "ECRR and ECRW that base is the 0xFE410000 ECMG itself "
                "declares, and the read reaches 0x07D0/0x07D1 with no field "
                "name in the path at all. The claim that the DSDT never reads "
                "these bytes is the claim that no AML invokes this; a caller "
                "makes it false." %
                (name, line, text, name))

    # The derived route census. This is what a hard-coded accessor list cannot
    # do: it finds every `SystemMemory` region at a non-literal base, so a
    # computed-base method added anywhere in the file is seen whether or not
    # anyone thought to name it here. Only a region whose base *resolves into
    # the window* is a refusal -- a route the scan cannot place is reported
    # and counted as unbounded, never cleared.
    window_base, window_length = window_bounds(lines, span)
    out["routes"] = routes = computed_base_routes(lines, window_base,
                                                   window_length)
    for entry in routes.get("invoked", []):
        if entry["state"] != "invoked-into-window":
            continue
        problems.append(
            "%s at %d is a computed-base region inside an invoked method, and "
            "its base %s resolves to 0x%08X, which overlaps the ECMG window "
            "(0x%08X, %d bytes):\n"
            "    %s\n"
            "    This is a route into 0x07D0/0x07D1 that no field name "
            "appears in, so the name census above stays green while the claim "
            "it carries dies. It is derived from the file rather than from a "
            "list of accessor names, which is the point: a fourth "
            "computed-base method is found here even though nothing names it." %
            (entry["region"], entry["line"], entry["base"],
             entry["resolves"], window_base, window_length,
             "method %s, called at %s" % (entry["method"],
                                          ", ".join(str(c)
                                                    for c in entry["callers"]))))

    try:
        widths, rows = csv_widths(fields_csv)
    except (OSError, ValueError, KeyError) as exc:
        problems.append("cannot read the width column of %s: %s" %
                        (fields_csv, exc))
    else:
        out["csv"] = {"widths": widths, "rows": rows}
        if widths + cover["unnamed_bits"] != cover["bits"]:
            problems.append(
                "%s declares %d bits; its %d rows' widths plus the %d "
                "unnamed ones come to %d.\n"
                "    One of the two parses has stopped seeing an element. The "
                "trailing-comma bug this file's docstring names dropped MGOF "
                "from the DSDT side while the CSV kept it, and the shortfall "
                "was exactly its width -- so this is the check that turns that "
                "back red rather than a number that quietly moved." %
                ("the ECMG field list", cover["bits"], rows,
                 cover["unnamed_bits"], widths + cover["unnamed_bits"]))
    return problems, out


def expectations(census):
    """The figures this file holds the *committed* `dsdt.dsl` to.

    Split out from `census` because these are properties of one vendor input
    and not of the parsing. They live in one place and are written once, and
    `--self-test` and the suite both go through `census` instead so a
    three-anchor fixture is judged on whether it parses rather than on whether
    it is the size of the real thing.
    """
    if not census:
        return []
    cover = census["coverage"]
    problems = []
    for label, got, want in (("anchors", cover["anchors"], EXPECTED_ANCHORS),
                             ("bits", cover["bits"], EXPECTED_BITS),
                             ("named bits", cover["named_bits"],
                              EXPECTED_NAMED_BITS),
                             ("unnamed bits", cover["unnamed_bits"],
                              EXPECTED_UNNAMED_BITS),
                             ("gaps between consecutive anchors", cover["gaps"],
                              EXPECTED_GAPS)):
        if got != want:
            problems.append("the ECMG field list declares %d %s; expected %d"
                            % (got, label, want))
    if census["07d3"][0] != 7:
        problems.append("0x07D3: the field list declares %d of its 8 bits; "
                        "expected 7, with bit 7 undeclared" % census["07d3"][0])
    return problems


def report(dsdt, fields_csv, verbose=False):
    """Every problem the committed pair has: the census, then its figures.

    Returns the problems and the census, so `--check` can exit on the former
    while the tests assert on the latter without a second parse.
    """
    found, walked = census(dsdt, fields_csv)
    if verbose and walked:
        print_census(walked)
    return found + expectations(walked), walked


def print_census(census):
    """The sweep, in the shape a reader of the write-up will want it."""
    widths = census["widths"]
    for name in ("DBD1", "DBD2", "ECMG"):
        entry = census[name]
        print("%-5s %d hit(s): %s" %
              (name, len(entry["lines"]),
               ", ".join("%d %s (%s)" % (entry["tally"][k], k, v)
                         for k, v in sorted(entry["tally"].items()) if v)))
    if widths.get("DBD1") and widths.get("DBD1") == widths.get("DBD2"):
        positions = census.get("positions") or {}
        first = positions.get("DBD1")
        second = positions.get("DBD2")
        if first and second:
            print("declared side by side under Offset (0x%X): DBD1 bits "
                  "%d-%d, DBD2 bits %d-%d -- disjoint ranges, so two scalars"
                  % (first[0], first[1], first[1] + first[2] - 1,
                     second[1], second[1] + second[2] - 1))
        else:
            print("declared at %s bits each, of a window %s bytes long" %
                  (widths["DBD1"], census["coverage"]["region_bytes"]))
    print("the named computed-base accessors, and whether anything calls them:")
    for name, entry in census.get("accessors", {}).items():
        print("  %-5s %d call(s); declared at %s" %
              (name, len(entry["calls"]),
               ", ".join("dsdt.dsl:%d" % line for line in entry["declarations"])
               or "nowhere in the file"))
    routes = census.get("routes")
    if routes:
        # The three states, not a single total: the point of deriving this from
        # the file is that the answer is not one number, and collapsing it to
        # one is how the earlier version of this claim came to sound exhaustive.
        print("every SystemMemory region at a non-literal base, from the file:")
        print("  %d in a method nothing calls; %d in a called method whose "
              "base resolves elsewhere; %d whose base this scan cannot place"
              % (len(routes["uncalled"]), len(routes["invoked"]),
                 len(routes["unbounded"])))
        for entry in routes["unbounded"]:
            if entry.get("method"):
                print("    unbounded: %s at dsdt.dsl:%d, base %s, method %s"
                      % (entry["region"], entry["line"], entry["base"],
                         entry["method"]))
    cover = census["coverage"]
    print("ECMG field list (dsdt.dsl:%d-%d, from dsdt.dsl:%d):" %
          (cover["field_line"], cover["span"][1][1], cover["region_line"]))
    print("  %d anchors, %d bits = %d whole bytes and %d spare of %d" %
          (cover["anchors"], cover["bits"], cover["whole_bytes"],
           cover["spare_bits"], cover["region_bytes"]))
    print("  %d named bits plus %d unnamed-but-allocated; %d gaps between "
          "consecutive anchors more than one byte apart" %
          (cover["named_bits"], cover["unnamed_bits"], cover["gaps"]))
    print("  0x07D3 declares %d of its 8 bits" % census["07d3"][0])
    if cover["undeclared_bytes"] is not None:
        run = cover["longest_undeclared_run"]
        stretch = ("none: every byte between them is allocated" if run is None
                   else "longest such stretch 0x%04X-0x%04X, %d bytes"
                        % (run[0], run[1], run[1] - run[0] + 1))
        print("  %d bytes between the first anchor (0x%04X) and the last "
              "(0x%04X) that no element allocates; %s" %
              (cover["undeclared_bytes"], cover["first_anchor"],
               cover["last_anchor"], stretch))
    if "csv" in census:
        print("  reconciles with %s: %d rows, %d bits + %d unnamed" %
              ("dsdt-ecmg-fields.csv", census["csv"]["rows"],
               census["csv"]["widths"], cover["unnamed_bits"]))


# --- fixtures for --self-test -------------------------------------------
#
# A check that has quietly stopped refusing looks exactly like a check that is
# working, so the refusals are what gets pinned. These are cut-down field
# lists -- three anchors is enough to move a gap, a store, or a width, and a
# fixture small enough to read is a fixture whose failure can be seen.

FIXTURE = r"""\
DefinitionBlock ("", "DSDT", 2, "TEST", "TEST", 0x00000001)
{
    Scope (\_SB)
    {
        Device (INOU)
        {
            Method (MMRW, 4, NotSerialized)
            {
                Local0 = Arg0
                Return (Local0)
            }
            Method (ECRR, 1, NotSerialized)
            {
                Local0 = (0xFE410000 + Arg0)
                Local1 = MMRW (Local0, Zero, Zero, Zero)
                Return (Local1)
            }
            Method (ECRW, 2, NotSerialized)
            {
                Local0 = (0xFE410000 + Arg0)
                MMRW (Local0, One, Zero, Arg1)
            }
        }
        Device (EC0)
        {
            Method (T1WR, 4, NotSerialized)
            {
                If (Arg0 == 0x1172)
                {
                    Store (Arg1, DBAC)
                }
                ElseIf ((Arg0 == 0x1173))
                {
                    Local0 = (Arg1 * 0x08)
                    Local1 = (Arg2 * 0x08)
                    ^^PCI0.LPCB.EC0.DBD1 = Local0
                    ^^PCI0.LPCB.EC0.DBD2 = Local1
                }
            }
            OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)
            Field (ECMG, AnyAcc, NoLock, Preserve)
            {
                Offset (0x7D0),
                DBD1,   8,
                DBD2,   8,
                Offset (0x7D3),
                    ,   4,
                GFID,   3,
                Offset (0x7D4),
                LASTF,   8
            }
        }
    }
}
"""

# What `FIXTURE` declares: two named elements at 8, one unnamed at 4, `GFID` at
# 3, and `LASTF` at 8 over three anchors. Written out rather than recomputed
# from the census under test, which is the whole point of the negative cases --
# a figure the tool produced cannot also be the figure that catches the tool.
FIXTURE_BITS = 31
FIXTURE_ANCHORS = 3


def _scratch(text):
    import tempfile
    handle, path = tempfile.mkstemp(suffix=".dsl", text=True)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    return path


def self_test():
    """Pin the refusals. Each case is a way this check must go red."""
    failures = []

    def check(label, cond, detail=""):
        if cond:
            print("  ok    %s" % label)
        else:
            failures.append("%s (%s)" % (label, detail))
            print("  FAIL  %s\n        %s" % (label, detail))

    def widths_csv(spec):
        """A scratch `dsdt-ecmg-fields.csv` whose width column is `spec`."""
        rows = ["region,addr,bit,width,name,dsdt_line,static_refs,"
                "static_refs_main_ec,static_refs_pd_image,in_registers,grade,"
                "asl_refs,asl_sites"]
        for name, width in spec:
            rows.append("ECMG,0x0000,0,%d,%s,0,0,0,0,,present-untested,0," %
                        (width, name))
        return _scratch("\n".join(rows) + "\n")

    scratch_paths = []

    def on_fixture(text, spec):
        """`census()` on `text` against a CSV declaring `spec`.

        The committed-tree figures are deliberately not applied: a
        three-anchor fixture is judged on whether it parses into the shape the
        check expects, not on whether it is the size of the real `dsdt.dsl`,
        which no fixture can be.
        """
        dsl = _scratch(text)
        fields = widths_csv(spec)
        scratch_paths.extend((dsl, fields))
        return census(dsl, fields)

    FIXTURE_WIDTHS = (("DBD1", 8), ("DBD2", 8), ("GFID", 3), ("LASTF", 8))

    def problems_for(text, spec=FIXTURE_WIDTHS):
        return on_fixture(text, spec)[0]

    clean, walked = on_fixture(FIXTURE, FIXTURE_WIDTHS)
    check("the fixture itself is clean, so every case below is the change "
          "under test and nothing else",
          not clean, "the clean fixture reported: %s" % (clean or ""))
    if not clean:
        cover = walked.get("coverage", {})
        check("the last element is counted despite carrying no trailing comma",
              cover.get("bits") == FIXTURE_BITS and
              cover.get("anchors") == FIXTURE_ANCHORS,
              "read %r bits over %r anchors where the fixture declares %d "
              "over %d; LASTF is the element the issue's pattern dropped" %
              (cover.get("bits"), cover.get("anchors"), FIXTURE_BITS,
               FIXTURE_ANCHORS))

    # 1. A reader, inside the writer arm -- the case a span check cannot see.
    reader = FIXTURE.replace(
        "                    ^^PCI0.LPCB.EC0.DBD1 = Local0\n",
        "                    ^^PCI0.LPCB.EC0.DBD1 = Local0\n"
        "                    If (^^PCI0.LPCB.EC0.DBD2 == 0x00)\n"
        "                    {\n"
        "                        Local2 = 1\n"
        "                    }\n")
    found = problems_for(reader)
    check("a reader added inside the writer arm is refused",
          any("neither a store nor a declaration" in p for p in found),
          "the third hit stays inside the named span, so only the "
          "classification can see this one: %s" % (found or "nothing reported"))

    # 2. A third site, in a neighbouring T1WR arm -- outside both spans, and
    #    in a form (a store) the classification accepts, so only the span
    #    check can see it.
    elsewhere = FIXTURE.replace(
        "                    Store (Arg1, DBAC)\n",
        "                    Store (Arg1, DBAC)\n"
        "                    ^^PCI0.LPCB.EC0.DBD2 = Arg2\n")
    found = problems_for(elsewhere)
    check("a hit outside both spans is refused",
          any("outside both" in p for p in found),
          "found: %s" % (found or "nothing reported"))

    # 3. A store where the census says there is one.
    nostore = FIXTURE.replace(
        "                    ^^PCI0.LPCB.EC0.DBD2 = Local1\n", "")
    found = problems_for(nostore)
    check("a missing store is refused on the tally",
          any("expected" in p for p in found),
          "found: %s" % (found or "nothing reported"))

    # 4. The trailing comma required again -- the regression the docstring
    #    names, reproduced so the fix cannot be quietly reverted by a
    #    well-meaning tidy of the pattern.
    globals()["ELEMENT_RE"] = re.compile(
        r"^\s*([A-Za-z0-9_]*)\s*,\s*(\d+)\s*,\s*$")
    try:
        _, regressed = on_fixture(FIXTURE, FIXTURE_WIDTHS)
        check("a pattern that requires the trailing comma drops the last "
              "element",
              regressed["coverage"]["bits"] == FIXTURE_BITS - 8,
              "read %r bits where the clean fixture reads %d, and the "
              "shortfall is exactly LASTF's width" %
              (regressed["coverage"]["bits"], FIXTURE_BITS))
    finally:
        globals()["ELEMENT_RE"] = re.compile(ELEMENT_PATTERN)

    # 5. A gap that closes when two anchors are pulled together.
    _, tight = on_fixture(FIXTURE.replace("Offset (0x7D3),",
                                           "Offset (0x7D1),"), FIXTURE_WIDTHS)
    check("moving an anchor moves the gap count the census reports",
          tight["coverage"]["gaps"] == 1,
          "read %r gaps; Offset (0x7D1) sits next to Offset (0x7D0) and "
          "closes two of the three" % tight["coverage"]["gaps"])

    # 6. A file with the writer arm renamed is a missing span, not a crash.
    armless = FIXTURE.replace("ElseIf ((Arg0 == 0x1173))",
                              "ElseIf ((Arg0 == 0x1174))")
    found = problems_for(armless)
    check("a file with no writer arm is reported as a missing span",
          any("no T1WR Arg0 == %s arm" % WRITER_ARG in p for p in found),
          "found: %s" % (found or "nothing reported"))

    # 7. The width-column disagreement, which is the reconciliation's refusal.
    found = on_fixture(FIXTURE, (("DBD1", 8), ("DBD2", 8), ("GFID", 3),
                                 ("LASTF", 7)))[0]
    check("a width column that disagrees with the parse is refused",
          any("come to" in p for p in found),
          "LASTF is 7 in the CSV and 8 in the DSDT, which is exactly the "
          "shape the trailing-comma bug had: found %s" %
          (found or "nothing reported"))

    # 8. The pair's widths are the claim's, so moving one is refused.
    found = on_fixture(
        FIXTURE.replace("                DBD2,   8,\n",
                       "                DBD2,   16,\n"),
        (("DBD1", 8), ("DBD2", 16), ("GFID", 3), ("LASTF", 8)))[0]
    check("a field that is no longer 8 bits wide is refused",
          any("bits wide" in p for p in found),
          "DBD2 at 16 bits is the opposite of the claim; found: %s" %
          (found or "nothing reported"))

    # 9. A caller for the computed-base accessor. This is the refusal that
    #    replaces the one the false premise would have needed: a file that
    #    still declares DBD1 twice and writes it twice, and that also reads
    #    the byte through `ECRR`, is a file where the DSDT *does* read the
    #    pair -- with no field name anywhere in the path, so the name census
    #    above stays perfectly green while the claim it was carrying dies.
    called = FIXTURE.replace(
        "                    Local0 = (Arg1 * 0x08)\n",
        "                    Local3 = ECRR (0x07D0)\n"
        "                    Local0 = (Arg1 * 0x08)\n")
    found = problems_for(called)
    check("a caller for the computed-base accessor is refused",
          any("ECRR is invoked" in p for p in found),
          "DBD1 and DBD2 are still one store and one declaration each, so "
          "only the accessor census can see this one; found: %s" %
          (found or "nothing reported"))

    # 10. The accessor census's own positive control: the fixture declares
    #     both accessors and calls neither, so the case above turned red on
    #     the call and not on the declaration. A census that counted
    #     declarations as calls would refuse the clean fixture too, which is
    #     the other way for it to stop working.
    check("a method declaration is not counted as a call to itself",
          accessor_census(FIXTURE.split("\n"))["ECRR"]["calls"] == [],
          "ECRR is declared in the fixture and must not read as its own "
          "caller")

    # 11. The refusal that a hard-coded accessor list could not produce. The
    #     fourth computed-base method is one no document names: nothing in
    #     `ACCESSORS` is `WIDR`, so under the old census this file was clean
    #     while `WIDR` sat inside the window. This is the case the finding was
    #     about -- a reader that arrives by a route the name list does not
    #     have -- so it has to go red for the derived census to be worth
    #     anything.
    fourth = FIXTURE.replace(
        "            Method (ECRW, 2, NotSerialized)\n",
        "            Method (WIDR, 1, NotSerialized)\n"
        "            {\n"
        "                OperationRegion (WIDG, SystemMemory, 0xFE4107D0, 0x02)\n"
        "                Field (WIDG, ByteAcc, NoLock, Preserve)\n"
        "                {\n"
        "                    WID0,   8\n"
        "                }\n"
        "                Local2 = WID0\n"
        "                Return (Local2)\n"
        "            }\n"
        "            Method (ECRW, 2, NotSerialized)\n")
    found = problems_for(
        fourth.replace("                    Local0 = (Arg1 * 0x08)\n",
                       "                    Local3 = WIDR ()\n"
                       "                    Local0 = (Arg1 * 0x08)\n"))
    check("a computed-base method nothing names, landing in the window and "
          "called, is refused",
          any("invoked-into-window" in p or "resolves to 0x%08X"
              % 0xFE4107D0 in p for p in found),
          "WIDR is absent from ACCESSORS by construction, which is the point: "
          "found %s" % (found or "nothing reported"))

    # 12. The positive control for that refusal: the same region in a method
    #     nothing calls is a reader with no route, and is reported as uncalled
    #     rather than refused. Without this the case above could pass on a rule
    #     that refuses every computed-base region regardless of reachability.
    idle = problems_for(fourth)
    check("the same computed-base region in an uncalled method is not refused",
          not any("invoked-into-window" in p for p in idle),
          "found: %s" % (idle or "nothing reported"))

    # 13. A runtime base is reported as unbounded, never cleared. `EMPB` in the
    #     committed file is built from `XBAS`, which is `External`; a base the
    #     scan cannot resolve must not be counted as a route that misses.
    _, walked_routes = on_fixture(FIXTURE, FIXTURE_WIDTHS)
    check("the route census reports a computed-base region in the fixture",
          walked_routes.get("routes", {}).get("uncalled") is not None,
          "the fixture's MMRW builds MMNM at Arg0 and nothing calls it, so it "
          "belongs in the uncalled half")

    for path in scratch_paths:
        try:
            os.unlink(path)
        except OSError:
            pass

    # 11. The positive control: the committed CSV reconciles and the committed
    #     file's accessors go uncalled, so the refusals above are
    #     disagreements and not a rule that refuses everything.
    fields_csv = os.path.join(REPO, "ec", "annotations",
                              "dsdt-ecmg-fields.csv")
    if os.path.exists(fields_csv) and os.path.exists(DEFAULT_DSDT):
        found, real = report(DEFAULT_DSDT, fields_csv)
        check("the committed pair is clean",
              not found, "found: %s" % (found or ""))
        if not found and real.get("coverage"):
            cover = real["coverage"]
            check("the committed field list reconciles with its CSV",
                  real["csv"]["widths"] + cover["unnamed_bits"] ==
                  cover["bits"],
                  "%d + %d != %d" % (real["csv"]["widths"],
                                     cover["unnamed_bits"], cover["bits"]))
    else:
        print("  skip  the committed pair (dsdt.dsl or the CSV is absent here)")

    if failures:
        for failure in failures:
            print("  FAILURES ABOVE: %s" % failure)
        return 1
    print("  self-test passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail on a name census that has moved, a coverage "
                         "figure that has moved, or a width column that "
                         "disagrees with the parse (the gate's entry point)")
    ap.add_argument("--print", action="store_true",
                    help="print the census as well as checking it")
    ap.add_argument("--dsdt", default=DEFAULT_DSDT,
                    help="evidence/acpi/dsdt.dsl to read (default: the "
                         "committed one; a path is taken so the self-test "
                         "can run against fixtures without editing it)")
    ap.add_argument("--fields-csv", default=DEFAULT_CSV,
                    help="ec/annotations/dsdt-ecmg-fields.csv, whose width "
                         "column this reconciles against")
    ap.add_argument("--self-test", action="store_true",
                    help="pin the refusals against constructed fixtures")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    try:
        problems, _census = report(args.dsdt, args.fields_csv,
                                   verbose=args.print)
    except OSError as exc:
        print("cannot read the inputs: %s" % exc, file=sys.stderr)
        return 1
    for problem in problems:
        print(problem)
    if problems:
        print("%d problem(s) in the DBD1/DBD2 census." % len(problems))
        return 1 if args.check else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
