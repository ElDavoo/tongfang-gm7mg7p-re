#!/usr/bin/env python3
"""Hold each testdata index row's address claims to the files that row names.

`check_testdata_index.py` holds `ec/tools/testdata/README.md` and the tree
under it to each other: a directory no index names is a gap, a path a cell
names that is not on disk is a miss. It reads the **first** column, the
`Feeds` column and the nested tables. It does not read the third -- the
description -- and the third column is the one the index has needed a human to
repair, twice, in #502 and #720, both times in a description of a row whose
file was already named correctly. So every check on the index would have been
green through both.

**This is a new file, not a mode on `check_capture_claims.py`.** That tool's
docstring records why the reuse is not free: `units()` and the sentence
splitter are shared deliberately -- and are shared here too, by import, so a
fix to the splitting logic (issue #273) lands once for all three tools -- but
its scope is `registers.yaml` notes against real captures under
`evidence/ec-watch/`, and it asks a question of a sentence about a file that
sentence names. Here the file comes from a *different column of the same
table*, and the prose is a fixture's description rather than a note about a
capture. What carries over is the invariant, in its own words: an address a
unit attributes to the capture has to have a row in it. What does not is the
`MOVEMENT` predicate -- 18 of the 54 literals in this column sit in a sentence
carrying none of its verbs, and most of those are genuine claims, so gating on
it would skip two thirds of the column. The predicate here is a backticked
literal plus the six shapes below.

**The search is across the files a row's first column resolves to, never per
file.** `0x075B` occurs 16 times in one of `0751-isolation-run-staged/`'s
three CSVs and in neither of the other two, while the row names
`0751-isolation-run-staged/*.csv`. A per-file reading fails a row that is true
today, which is the issue's own condition on the whole direction.

**The six shapes, which are the whole of the conservative half.** They are
counted, printed with the reason, and do not fail the run -- a checker that
reported its own parser's blind spot as a broken index would be pushed to grow
a rule for whatever it could not read, and would end up inventing the thing it
is checking. The list is closed and each entry has a case in
`test_check_testdata_row_claims.py`; a seventh shape appearing in the tree is
a change to this docstring, not an invitation to add a regex:

  * *a capture or window bound* -- a page-aligned literal naming the swept
    page rather than a byte in it, spelled either as a range whose start is
    page-aligned (`0x0700-0x07FF`) or as a bare page-aligned address the
    sentence calls a capture or a page (the `0x0700` and `0x0400` captures);
  * *a watched-set span* -- `` `0x07C4`-`0x07D7` ``, two separately
    backticked bounds. The corpus writes a byte range as one token and a set as
    two, and a set the grader watches is not a byte the fixture holds;
  * *a denial* -- `no row at all for` and `not by a committed run`, both
    saying where an address is **not**;
  * *a dump-command argument* -- `0x0750`/`0x0010` in `` `ecrw.py dump ...` ``;
  * *a firmware code address* -- `0x888D`, which is in
    `ec/annotations/ghidra-functions.csv` and is a handler in the EC image
    rather than a byte in a capture. Filtered against that census **minus**
    `xdata-registers.csv`, because on this firmware the same 4-digit token is
    often both a function entry and an XDATA byte -- `0x07D0` is
    `FUN_CODE_07d0` in the annotation index and a door byte in the register
    map, and it is a claim in two rows. A threshold invented here would have
    got one of those two wrong;
  * *another capture's address* -- an address the sentence attributes to a
    dated capture this row does not name. The index writes a *file* in
    backticks and a *capture* in running prose, and only the second is
    somewhere else, so the whole sentence's literals are read as that
    capture's. That is the one shape with a real cost: a false claim in such a
    sentence is passed over, and the cost is written here rather than left for
    a reader of the tallies to infer.

**What this does not check, which is as much of the point:**

  * *Whether a fixture is what its row says it is.* This asks whether an
    address the row names occurs in a file the row names. It does not ask
    whether the capture constructs the shape described, and a green run is not
    a claim that it does.
  * *That the address has a row in a particular column.* Presence here is
    textual: does the file carry `0xNNNN` anywhere, in any case. A mark label
    (`restored 0x0751=0x0a`) and a dump line (`0780:`) are both how a fixture
    carries an address, and a mark label is precisely what rows 20, 22 and 25
    claim. A fixture that mentions an address in a comment therefore satisfies
    the rule, and the narrower question -- is there a row with this in the
    `addr` column -- is `check_capture_claims.py`'s, over real captures.
  * *Row counts, timestamps and mark values.* Row 18's `0x0F0A` row *at*
    12:00:08.500 is a count-and-timestamp claim, decidable in principle and
    deliberately not here: it is a different invariant with a different owner,
    and the issue this answers asks for presence.
  * *`MOVEMENT`, and the rest of the sibling's vocabulary.* No claim has to
    say something changed before it is held to the capture, and no sentence
    has to name the file -- the file comes from the row.
  * *Row counts, directory reachability, `Feeds`, nested tables.* Those are
    `check_testdata_index.py`'s, in both directions, and this tool reads
    neither a directory listing nor a `Feeds` cell.
  * *The prose below the table, the `Feeds` column, and
    `call-graph/README.md`'s own table.* A nested index of a different shape
    is its own piece of work.
  * *The `0x888D` filter's blind side.* It reads the committed function
    census, so a code address with no annotation row is not filtered by it.
    Every one of those is a literal this tool cannot place, and each is
    reported with the reason rather than passed over in silence.
  * *A whole sentence that names a capture in prose.* That is what the
    other-capture shape is, and it is the widest exemption here: none of a
    sentence's literals is checked once it names a dated capture in running
    text. Row 7's is the only one today, and it is right there, but the rule
    buys one correct row at the price of not checking that sentence at all.

**Not claimed: that this would have caught #502 or #720.** What those two
repairs changed is in the issues, not in the tree, and neither has been read
back as a diff this tool could have been run over. What it holds is the tree as
it stands: the surface is asserted non-empty, and every rule that makes it
conservative has a case.

Usage:
    python3 ec/tools/check_testdata_row_claims.py [--check]
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

# The walker, not a copy of it, the same import `check_capture_claims.py`
# makes. It is handed one *cell* rather than a whole file: a markdown table
# row is a unit of its own to `units()`, so handing it the index would fuse
# all three columns into one unit and the third column would stop being
# separate. A bare cell is prose, so it takes the sentence path.
from check_cluster_citations import REGISTERS, units

# The index checker is imported for what it got right, and re-implemented for
# the one thing it does not expose. `resolve()` returns `(verdict, note)` and
# throws the paths away; this tool needs the file *set*, which is the whole of
# the union rule. Changing it would mean editing a tool that is not at fault
# along with its suite, so `files_for()` follows the same branches and the
# suite asserts the two agree on the committed tree.
from check_testdata_index import (INDEX, MISSING, RESOLVED, TESTDATA,
                                  UNRESOLVED, as_address, below, names_a_file,
                                  repo_path, table_cells)

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)

# The census of firmware code addresses. A literal in it names a routine in
# the EC image, never a byte in a capture, and reading it out of the
# annotations rather than out of a threshold keeps the filter honest: the
# repository already keeps this list, and a cutoff invented here would be a
# claim about the address map that nothing else in the tree supports.
FUNCTIONS = os.path.join(EC, "annotations", "ghidra-functions.csv")

# Four hex digits and a boundary, for the same reason the sibling writes it
# that way: a case-insensitive prefix, and a width. The width is what keeps
# `0x50 -> 0x28`, `0xFD`/`0xC9` and `0xA0`/`0x10` out -- they are the values
# the dumps and the mark labels carry, and widening this to `\w*` would make
# the committed tree red on the day it landed.
ADDRESS = re.compile(r"0[xX]([0-9A-Fa-f]{4})\b")

# A literal is a candidate only where it is written in backticks, which is how
# the index writes an address it means. Running prose is not a claim, and
# reading one would be a parser guessing.
BACKTICKED = re.compile(r"`([^`]+)`")

# A byte range, written as one token. The corpus uses this for both the
# pages it sweeps and the byte runs inside them, and the two are told apart by
# whether the start is page-aligned -- see `page_bounds()`.
RANGE = re.compile(r"(0x[0-9A-Fa-f]{4})\s*(?:-|–|—|to)\s*(0x[0-9A-Fa-f]{4})")

# A watched set, written as two tokens. The backticks between the bounds are
# what makes it a set rather than a range, and they are in the sentence
# between the two literals rather than inside either one's token.
SPAN = re.compile(r"0x[0-9A-Fa-f]{4}`\s*[-–—]\s*`0x[0-9A-Fa-f]{4}")

# The words that turn a page-aligned address into the name of a capture rather
# than a byte in one. `capture`/`page` only, and not `pair`/`log`: those two
# also describe the dump fixtures, and `pair` sits close enough to a genuine
# claim in this column ("...the same shape the `...-moved-mailbox-` pair below
# has...") that reading them would drop real coverage.
PAGE_WORD = re.compile(r"\b(?:captures?|pages?)\b", re.IGNORECASE)

# How far *after* a page-aligned address the word naming it a capture may sit.
# Wide enough for "the `0x0700` and `0x0400` captures", where the word is behind
# the second address rather than its own, and no wider: the next address in a
# list of five must not reach a `capture` that is not about it.
WINDOW = 40

# A denial says where an address is *not*, and the two committed spellings
# differ in what they take. `no row at all for ...` takes the literals as its
# object; `not by a committed run` is a trailing adjunct that denies the clause
# in front of it. Both name the artifact -- a row, a run, a file -- and that
# is what separates them from the column's "not a prediction" disclaimers,
# which are about the future and say nothing about the fixture. The two are
# separate patterns because `denied()` reads the direction off which one
# matched, and that is what keeps row 9's `0x0746` a claim.
DENIAL_OBJECT = re.compile(r"\bno\s+rows?\b[^.;]{0,20}?\bfor\b", re.IGNORECASE)
DENIAL_ADJUNCT = re.compile(
    r"\bnot\s+(?:by|in|on|as|to|into|over|of)\s+(?:a\s+|the\s+)?"
    r"(?:committed\s+)?(?:rows?|runs?|files?|fixtures?|captures?|commits?)\b",
    re.IGNORECASE)

# A tool invoked on the command line. The backticked token has to name one and
# have arguments, so `restored 0x0751=0x0a` -- a mark label, which is a real
# claim about a real fixture -- is not read as a command.
COMMAND = re.compile(r"\S+\.py\b")

# A dated capture named in running prose. The index writes a *file* in
# backticks -- the `2026-09-23` in row 9, drawn on for comparison -- and a
# *capture* in prose, and only the second is somewhere else: a sentence that
# says what the 2026-09-23 power-mode-cycle capture shows is about that
# capture, and the fixtures the row names are not it. Backticked, the same
# date is a file the comparison is drawn from and the sentence's literals are
# still about the row's own fixture, which is why the two are told apart by
# their spelling rather than by a count of how far away they are.
DATED_CAPTURE = re.compile(r"(?<!`)\b20\d\d-\d\d-\d\d\b(?!`)")

# The three answers, kept as strings because they are what a report prints and
# a test asserts against. Only `missing` fails. The names are the sibling's,
# so a reader who has met one has met the other.
Claim = collections.namedtuple("Claim", "row files address token reason verdict")

# What one run found: the three verdicts, the tallies a caller prints, and
# the two lists it prints them from. A run that reached nothing and a run that
# found nothing look the same from the exit code alone, so the counts are the
# output. There is no floor on any of them, for the reason
# `docs/agent-pipeline.md` records about gates -- an expected count turns
# every added fixture into a failure -- and the suite asserts non-emptiness
# instead, which is the assertion that is true of the tree rather than of the
# tool.
Result = collections.namedtuple(
    "Result", "rows literal_rows literals resolved missing unresolved checked "
    "claiming_rows claims shapes")


def normalise(address: str) -> str:
    """`0x0449` and `0X0449` are one address; the file's spelling is not."""
    return "0x" + address[2:].upper()


def page_aligned(address: str) -> bool:
    """Whether the address is the first byte of a 256-byte page."""
    return as_address(address) % 0x100 == 0


def files_for(token: str, root: str):
    """(verdict, sorted paths) for one backticked token of the `File` column.

    The same six branches `check_testdata_index.resolve()` reads, in its
    order, because a `...` abbreviation and a bare `*` glob are the index's
    own shorthands and a second reader of them would be a second thing to
    fall out of date. What is different is only the return: the paths, not a
    note saying which rule matched. `test_check_testdata_row_claims.py`
    asserts the two verdicts agree on every token of the committed table.
    """
    if token.startswith("..."):
        found = below(root, "*" + token[3:])
    elif "/" in token:
        directory, _, pattern = token.rpartition("/")
        path = os.path.join(root, directory)
        if not os.path.isdir(path):
            return MISSING, []
        # A bare `<dir>/` names the directory, and the files under it are the
        # row's to name in its own tokens.
        found = [path] if not pattern else glob.glob(os.path.join(path, pattern))
    elif any(c in token for c in "*?["):
        found = below(root, token)
    elif names_a_file(token):
        path = os.path.join(root, token)
        found = [path] if os.path.exists(path) else []
    else:
        return UNRESOLVED, []
    found = sorted(found)
    return (RESOLVED if found else MISSING), found


def row_files(cell: str, root: str):
    """The sorted paths a whole `File` cell resolves to, unioned over tokens.

    The union is the issue's own example and the reason a per-file reading is
    wrong: `0x075B` is in one of `0751-isolation-run-staged/`'s three CSVs,
    and the row names the directory. A token that resolves to nothing adds
    nothing, which is what leaves a broken row to `check_testdata_index.py`'s
    own four directions rather than reported twice here.
    """
    paths = set()
    for token in BACKTICKED.findall(cell):
        paths.update(files_for(token, root)[1])
    return sorted(paths)


def literals(sentence: str):
    """(address, token, offset) for each backticked address, in reading order.

    The token and the offset travel with the address because two of the six
    shapes are decided by the token the literal is written in -- a range is
    one token, a set is two, a command is a token that names a tool -- and
    because the report has to say which spelling it read.
    """
    out = []
    for token in BACKTICKED.finditer(sentence):
        for found in ADDRESS.finditer(token.group(1)):
            out.append((normalise(found.group(0)), token.group(1),
                        token.start() + found.start()))
    return out


def page_bounds(sentence: str):
    """The bounds of every one-token range that starts on a page boundary.

    The corpus names its three sweep ranges by their page start --
    `0x0700-0x07FF`, `0x0400-0x045F`, `0x0F00-0x0F5F` -- and the narrow runs
    it names *inside* the page by their first byte: `0x0F5D-0x0F5F` and
    `0x0F58-0x0F5C` are both mid-page, and one of those two is a claim. The
    page boundary is therefore what separates a page this tool cannot read
    rows from a set of bytes it can, and it is a property of the address the
    index already writes rather than a word list.
    """
    bounds = set()
    for token in BACKTICKED.finditer(sentence):
        found = RANGE.fullmatch(token.group(1).strip())
        if found and page_aligned(found.group(1)):
            bounds |= {normalise(found.group(1)), normalise(found.group(2))}
    return bounds


def span_bounds(sentence: str):
    """The bounds of every two-token span, which is a set and not a range."""
    bounds = set()
    for found in SPAN.finditer(sentence):
        for address in ADDRESS.finditer(found.group(0)):
            bounds.add(normalise(address.group(0)))
    return bounds


def denied(address: str, sentence: str, offset: int) -> bool:
    """Whether a denial phrase is talking about this literal.

    A denial names what is absent, and the column writes that two ways, and
    which one it is decides the direction. `no row at all for 0x07D4 or
    0x07D5` takes the literals as its object, so the phrase governs what
    follows it; `...one 0x0784 row added, not by a committed run` is a
    trailing adjunct, so it governs the clause in front of it. A bare
    proximity window would not do: "no row" is 38 characters after the last
    address of the inventory that precedes it in row 9, so a window wide
    enough to reach backwards to the trailing denial also reaches forward
    over 0x0746 and drops a claim that is true today.
    """
    for phrase, forwards in ((DENIAL_OBJECT, True), (DENIAL_ADJUNCT, False)):
        found = phrase.search(sentence)
        if not found:
            continue
        if forwards and found.end() <= offset:
            return True
        if not forwards and found.start() >= offset + len(address):
            return True
    return False


def reason_for(address, token, sentence, offset, code):
    """Why this literal is not checked, or None when it is a claim.

    The six in a fixed order, cheapest and least committal first. None of them
    needs the file set, and that is deliberate: a shape is a property of how
    the sentence is written, so the same sentence is classified the same way
    whether or not the row's fixtures happen to carry the address.
    """
    if address in page_bounds(sentence):
        return "capture/window bound"
    if page_aligned(address) and PAGE_WORD.search(
            sentence, offset + len(address), offset + len(address) + WINDOW):
        return "capture/window bound"
    if address in span_bounds(sentence):
        return "watched-set span"
    if denied(address, sentence, offset):
        return "denial"
    if " " in token and COMMAND.search(token):
        return "dump-command argument"
    if as_address(address) in code:
        return "firmware code address"
    if DATED_CAPTURE.search(sentence):
        return "another capture's address"
    return None


def carried_by(address: str, paths):
    """Whether any of `paths` carries the address, in any case.

    Textual, and that is the whole of the question: a mark label, a dump
    line and a change row are three ways a fixture carries an address, and
    this column claims all three. It is not the sibling's question -- is
    there a row for it in the `addr` column -- which is a different tool over
    a different corpus with a different owner.
    """
    for path in paths:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            if re.search(r"0x" + address[2:] + r"\b", f.read(), re.IGNORECASE):
                return True
    return False


def code_addresses(functions=FUNCTIONS, registers=REGISTERS):
    """The addresses the repository knows as firmware code and not as data.

    `ghidra-functions.csv` alone is the wrong filter, and the repository says
    so: on this firmware the same 4-digit token is often both a function entry
    and an XDATA byte -- `0x07D0` is `FUN_CODE_07d0` in the annotation index
    and `DBD1` in the register map -- which is the collision
    `citation_frames.py` exists to adjudicate. Filtering on
    `ghidra-functions.csv` minus `xdata-registers.csv` keeps the door byte as
    a claim (it has rows in the fixtures rows 12 and 15 name) and still reads
    `0x888D` as the handler in the image that it is.

    Both files are read as integers because the annotation index writes an
    address both ways, `0EA2` and `0x888D`, and `as_address()` is the reader
    for that. A row existing at the address is what counts; the scope, the
    bank and the name are not this tool's business.
    """
    found = set()
    with open(functions, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            value = as_address(row.get("addr", ""))
            if value is not None:
                found.add(value)
    with open(registers, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            value = as_address(row.get("addr", ""))
            found.discard(value)
    return found


def check(root=TESTDATA, functions=FUNCTIONS, registers=REGISTERS):
    """A `Result` for one testdata tree.

    The index is read from `root/README.md`, so a caller cannot point the
    check at one file's table and another file's tree, and the whole tree is
    walked at once rather than per row: the `unplaced-window` row is only
    decidable in the company of the rows it cross-references.
    """
    index_path = os.path.join(root, "README.md")
    with open(index_path, encoding="utf-8") as f:
        index = f.read()

    files = table_cells(index)
    descriptions = table_cells(index, column=3)
    code = code_addresses(functions, registers)

    claims, shapes = [], []
    per_row = collections.Counter()
    literal_rows = set()
    for number, cell in enumerate(descriptions, 1):
        named = files[number - 1] if number <= len(files) else ""
        paths = row_files(named, root)
        for _, sentence in units(cell):
            for address, token, offset in literals(sentence):
                literal_rows.add(number)
                reason = reason_for(address, token, sentence, offset, code)
                carried = carried_by(address, paths)
                if reason:
                    shapes.append((number, address, reason))
                    claims.append(Claim(number, named, address, token, reason,
                                        UNRESOLVED))
                    continue
                per_row[number] += 1
                claims.append(Claim(number, named, address, token, None,
                                    RESOLVED if carried else MISSING))

    resolved = sum(1 for c in claims if c.verdict == RESOLVED)
    missing = sum(1 for c in claims if c.verdict == MISSING)
    return Result(len(files), len(literal_rows), len(claims), resolved, missing,
                  len(claims) - resolved - missing, resolved + missing,
                  len(per_row), claims, shapes)


def report(result):
    """Print each disagreement and each skipped literal, and return the misses.

    `unresolved` is printed on stderr so a reader can see *why* a literal was
    not checked -- and the sentence says "not checked, not absent", because
    a pointer-checker that reported its own blind spot as a broken index is
    the failure mode the sibling's docstring spends a page on.
    """
    for claim in result.claims:
        if claim.verdict == UNRESOLVED:
            print(f"row {claim.row} ({claim.files}): {claim.address} is not "
                  f"checked -- {claim.reason}; not absent", file=sys.stderr)
    for claim in result.claims:
        if claim.verdict == MISSING:
            print(f"row {claim.row} ({claim.files}): {claim.address} is "
                  f"attributed to a fixture this row names, and no file it "
                  f"resolves to carries it", file=sys.stderr)
    if result.missing:
        print(f"{result.missing} testdata index row claim(s) disagree with the "
              f"fixtures they name", file=sys.stderr)
        print("A disagreement here is a defect in the index. It is not a "
              "reason to change a fixture.", file=sys.stderr)
    return result.missing


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Accepted and not branched on, the same spelling `check_testdata_index.py`
    # takes: the check is the whole of what this tool does, so --check is the
    # default and the flag is the gate's entry point.
    ap.add_argument("--check", action="store_true",
                    help="check the committed index's address claims against "
                         "the fixtures it names (the default, and the gate's "
                         "entry point)")
    ap.parse_args()

    result = check()
    if report(result):
        return 1
    by_shape = collections.Counter(reason for _, _, reason in result.shapes)
    print(f"{result.rows} table row(s), {result.literal_rows} literal-bearing: "
          f"{result.literals} literal(s), {result.resolved} resolved, "
          f"{result.missing} missing, {result.unresolved} unresolved")
    print(f"{result.checked} claim(s) checked, {result.claiming_rows} claiming "
          f"row(s), {len(result.shapes)} passed over under the six shapes, "
          "each of them: not checked, not absent")
    print("shapes: " + ", ".join(
        f"{reason} {count}" for reason, count
        in sorted(by_shape.items(), key=lambda kv: (-kv[1], kv[0]))))
    print(f"{repo_path(INDEX)}: every address claim in the third column agrees "
          "with the fixtures its row names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
