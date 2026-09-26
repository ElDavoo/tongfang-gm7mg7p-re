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
literal plus the five shapes and the two dated refusals below.

**The search is across the files a row's first column resolves to, never per
file.** `0x075B` occurs 16 times in one of `0751-isolation-run-staged/`'s
three CSVs and in neither of the other two, while the row names
`0751-isolation-run-staged/*.csv`. A per-file reading fails a row that is true
today, which is the issue's own condition on the whole direction.

**A bare date in prose is a file set, and never the row's own as well.** The
index writes a *file* in backticks and a *capture* in running prose, and only
the second is somewhere else: a sentence that says what the 2026-09-23
power-mode-cycle capture shows is about that capture, and the fixtures the row
names are not it. So `captures_for()` resolves such a date against
`evidence/ec-watch/<date>-*` and the sentence's literals are held to *those*
files -- **or** to the row's own where there is no such date, never to both.
A union would let row 7 pass on its own after-dump, which covers
`0x0F00-0x0F5F`, and that is the misattribution the sentence's date is there
to prevent. `evidence/ec-watch/` is flat and every capture in it is dated in
its own filename, so the glob is a glob and not a guess, and it is taken over
the whole date -- all six files of `2026-09-23-*` -- rather than narrowed by a
word in the prose, which would be the parser guessing. **The cost of the union
over the date is one address in any of a date's files satisfying a claim about
that date**, and it is written here rather than designed away. **A sentence
naming two or more bare dates is refused whole rather than read from either of
them.** Which of the two a literal belongs to is not a thing the prose says, so
reading the first is how the run came to report `missing` on a sentence that is
true, or `resolved` against a day the sentence never named. The refusal is a
count of matches and never a choice among them, and it is the seventh entry of
the list below.

**The five shapes and the two dated refusals, which are the whole of the
conservative half.** They are counted, printed with the reason, and do not
fail the run -- a checker that reported its own parser's blind spot as a broken
index would be pushed to grow a rule for whatever it could not read, and would
end up inventing the thing it is checking. The list is closed and each entry
has a case in `test_check_testdata_row_claims.py`; an eighth entry appearing in
the tree is a change to this docstring, not an invitation to add a regex:

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
  * *a dated capture that resolved to nothing* -- a bare date whose
    `<date>-*` glob is empty. There is no file set to hold the sentence's
    literals to, and the honest answer is the one the other five give: not
    checked by this method, never absent. It is printed with the glob that was
    searched, so a reader can see which date failed to resolve rather than
    only that a sentence did. This is the whole of what is left of the
    `another capture's address` exemption issue #794 removed, and the commit
    that removed it is where the before is written down;
  * *two dated captures in one sentence* -- a sentence naming two or more bare
    dates, refused whole. Its literals come off `checked` and onto this line
    rather than being read against the first of the globs, and **every** glob
    the sentence named is printed beside them, so a reader sees which dates
    were skipped rather than only that a sentence was. **The union of two days
    is declined rather than taken**, and not as a matter of taste: on this tree
    `2026-09-23-*` is the power-mode-cycle set and `2026-09-24-*` is a plug-in
    sweep, so a sentence about one of them held to both is handed a
    twelve-file set of two unrelated families -- the same misattribution the
    date exists to prevent, along a second axis. **No such sentence is in the
    committed index**, so what pins this is scratch cases, as the sixth
    entry's are.

**What this does not check, which is as much of the point:**

  * *Whether a fixture is what its row says it is.* This asks whether an
    address the row names occurs in a file the row names -- or, where the
    sentence names a capture in prose, whether it occurs in a file that
    capture's date resolves to. It does not ask whether the file constructs
    the shape described, and a green run is not a claim that it does.
  * *That the address has a row in a particular column.* Presence over a
    **fixture** is textual: does the file carry `0xNNNN` anywhere, in any
    case. A mark label (`restored 0x0751=0x0a`) and a dump line (`0780:`) are
    both how a fixture carries an address, and a mark label is precisely what
    rows 20, 22 and 25 claim. A fixture that mentions an address in a comment
    therefore satisfies the rule. ~~The narrower question -- is there a row
    with this in the `addr` column -- is `check_capture_claims.py`'s, over real
    captures.~~ **That sentence was false and is corrected here rather than
    deleted, per `docs/findings.md` §4a.** The question had no owner:
    `check_capture_claims.py` resolves captures out of a path the unit names,
    and a bare date is not a path, so it never saw one. **It is this tool's,
    for a dated claim** -- a date that resolved means the sentence is about a
    real capture, where the `.csv` schema is `ts,addr,old,new` and the column
    *is* the question, so the claim is held to the `addr` column of the date's
    `.csv` members and a hex token in a `#` header block or a comment does not
    satisfy it. Every other claim keeps the textual read above, and a date
    resolving to `.txt` dumps alone has no column to ask, which is the row 6
    and row 8 shape and is reported beside the file count rather than passed
    over. **A claim about a fixture is textual; a claim about a capture is
    columnar, and the date in the sentence is what tells them apart.**
  * *Row counts, timestamps and mark values.* Row 18's `0x0F0A` row *at*
    12:00:08.500 is a count-and-timestamp claim, decidable in principle and
    deliberately not here: it is a different invariant with a different owner,
    and the issue this answers asks for presence.
  * *`MOVEMENT`, and the rest of the sibling's vocabulary.* No claim has to
    say something changed before it is held to the capture, and no sentence
    has to name the file -- it comes from the row, or from a bare date the
    sentence happens to carry.
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
  * ~~*A whole sentence that names a capture in prose.* That is what the
    other-capture shape is, and it is the widest exemption here: none of a
    sentence's literals is checked once it names a dated capture in running
    text. Row 7's is the only one today, and it is right there, but the rule
    buys one correct row at the price of not checking that sentence at
    all.~~ **That entry described a rule which no longer exists, and it is
    left as it was rather than deleted, per `docs/findings.md` §4a.** Issue
    #794 removed it: a bare date is resolved against
    `evidence/ec-watch/<date>-*` and the sentence's literals are held to
    those files, so row 7's `0x0F58`/`0x0F5C` are checked against the six
    2026-09-23 captures and both are present in one of them. What survives of
    it is the dated capture that *resolves to nothing*, which is the sixth
    entry of the shape list above, is counted and printed with the glob it
    searched, and does not fail the run. The cost that replaced the old
    exemption -- one address in any file of a date satisfies a claim about
    that date -- is in the paragraph above and in
    `docs/findings/testdata-row-claims-dated-capture.md`. **The seventh entry
    is a later decision** (issue #979, in
    `docs/findings/testdata-row-claims-multi-date-sentence.md`) and is about a
    *second* date in one sentence rather than about a first that resolved to
    nothing.

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

# The capture root is the sibling's own spelling of where a real capture
# lives, imported rather than written out a second time for the same reason
# `units()` is imported: one place decides, and a second copy is a second
# thing to fall out of date. It is the one constant of that tool this borrows
# rather than a second reader of its job. `read_capture()` comes on the same
# line for the same reason and is the whole of the columnar read below: it
# already drops `#` header blocks before the header is read and already knows
# the `change_count` schema, so borrowing it is what keeps this tool from
# growing a second parser that has to learn both of those separately.
from check_capture_claims import WATCH, read_capture

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

# Where a sentence's bare date is resolved, absolute because the row's own
# root is: `captures_for()` is handed a scratch directory by the suite and the
# committed one by everything else, exactly as `check()`'s `root` is.
CAPTURES = os.path.normpath(os.path.join(EC, os.pardir, WATCH))

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
# their spelling rather than by a count of how far away they are. The look
# around the token is therefore the whole of the rule and it has not changed:
# what changed is what a match *does*. It was the reason a sentence's literals
# were not checked at all, and it is now the selector of the file set they are
# checked against -- see `captures_for()`. **A second match in one sentence is
# not a second file set**: it is the seventh entry of the docstring's shape
# list, and what decides it is the count of the matches rather than what any of
# them resolves to.
DATED_CAPTURE = re.compile(r"(?<!`)\b20\d\d-\d\d-\d\d\b(?!`)")

# The three answers, kept as strings because they are what a report prints and
# a test asserts against. Only `missing` fails. The names are the sibling's,
# so a reader who has met one has met the other. `files` is what the claim was
# held against -- the row's own `File` cell, or the `<date>-*` glob where the
# sentence named a capture in prose, or **every** such glob where it named more
# than one -- so a report line says which, and a dated claim cannot be read as
# one about the row's fixtures.
Claim = collections.namedtuple("Claim", "row files address token reason verdict")

# What one run found: the three verdicts, the tallies a caller prints, and
# the lists it prints them from. A run that reached nothing and a run that
# found nothing look the same from the exit code alone, so the counts are the
# output. There is no floor on any of them, for the reason
# `docs/agent-pipeline.md` records about gates -- an expected count turns
# every added fixture into a failure -- and the suite asserts non-emptiness
# instead, which is the assertion that is true of the tree rather than of the
# tool. `dated` is the per-date breakdown the issue asks for: (glob, the files
# it resolved to, the claims that date carried), in reading order, one entry
# per date a sentence named -- which for a refused two-date sentence is two
# entries carrying the same literals as `unresolved`.
Result = collections.namedtuple(
    "Result", "rows literal_rows literals resolved missing unresolved checked "
    "claiming_rows claims shapes dated")


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


def captures_for(sentence: str, root: str):
    """(verdict, sorted paths, the dates) for the bare dates in one sentence.

    `files_for()`'s answer with a third field, and over the same two verdicts:
    the glob matched something, or it matched nothing, with `unresolved` for a
    sentence that names no date at all, which is neither. `<date>-*` is a glob
    rather than a lookup because `evidence/ec-watch/` is flat and dates every
    capture in its own filename; the glob is returned beside the paths because
    a claim has to name what it was checked against, and on the two halves the
    two answers differ: a resolved date's claims name the glob they were held
    to, and an unresolved one's name the glob that came back empty.

    The third field is one `(glob, files)` pair per bare date the sentence
    carries, in reading order, because a sentence naming two of them has two
    answers and one string could carry neither: every one of them names a date
    the sentence skipped, and the per-date breakdown is keyed by each on its
    own. A sentence naming two or more is `unresolved` with **no** paths,
    whatever its globs resolve to -- the tool declines to pick a file set rather
    than picking one badly -- and its verdict is a function of how many dates
    are written, never of what any of them finds.
    """
    patterns = [f"{found.group(0)}-*"
                for found in DATED_CAPTURE.finditer(sentence)]
    if not patterns:
        return UNRESOLVED, [], []
    dates = [(pattern, sorted(glob.glob(os.path.join(root, pattern))))
             for pattern in patterns]
    if len(dates) > 1:
        return UNRESOLVED, [], dates
    pattern, paths = dates[0]
    return (RESOLVED if paths else MISSING), paths, dates


def literals(sentence: str):
    """(address, token, offset) for each backticked address, in reading order.

    The token and the offset travel with the address because some of the shapes
    are decided by the token the literal is written in -- a range is one token,
    a set is two, a command is a token that names a tool -- and because the
    report has to say which spelling it read.
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


def reason_for(address, token, sentence, offset, code, capture):
    """Why this literal is not checked, or None when it is a claim.

    The seven in a fixed order, cheapest and least committal first. Six of
    them are a property of how the sentence is written, so the same sentence
    is classified the same way whether or not the row's fixtures happen to
    carry the address; the seventh is the one that reads the file set, and only
    its emptiness -- `capture` is the `<date>-*` glob when that date resolved
    to nothing, and `None` when it resolved, which is not a reason at all.

    The multi-date refusal is first because it is a property of the sentence
    as a whole rather than of one literal, so every literal of such a sentence
    reads as the same refusal, and because it precedes the one reason it
    genuinely competes with: a sentence naming two dates of which one resolves
    to nothing is still unread, and the glob that came back empty is named
    beside the one that did not rather than swallowed by it.
    """
    if len(DATED_CAPTURE.findall(sentence)) > 1:
        return "two dated captures in one sentence"
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
    if capture is not None:
        return "dated capture not found"
    return None


def carried_by(address: str, paths):
    """Whether any of `paths` carries the address, in any case.

    Textual, and for a **fixture** that is the whole of the question: a mark
    label, a dump line and a change row are three ways a fixture carries an
    address, and this column claims all three. ~~It is not the sibling's
    question -- is there a row for it in the `addr` column -- which is a
    different tool over a different corpus with a different owner.~~ **That
    sentence named an owner that had no way to reach the question, and
    #975 gave it one: the columnar read below.** It is a different question
    for a different corpus, and the corpus is what tells them apart -- see
    `carried_by_column()`.
    """
    for path in paths:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            if re.search(r"0x" + address[2:] + r"\b", f.read(), re.IGNORECASE):
                return True
    return False


def carried_by_column(address: str, paths):
    """Whether a `.csv` of `paths` has a row with the address in `addr`.

    The other question from `carried_by()`, and it is asked only of a date's
    captures because a capture is not a fixture. A capture is a change log
    whose schema is `ts,addr,old,new`, so the column *is* the question: the
    claim is that the address has a row there, and a hex token in a `#`
    header block, a filename or a comment is not a row. Over a fixture that
    reasoning is backwards -- rows 20, 22 and 25 claim mark labels, which are
    a comment-shaped way of carrying an address and have no `addr` column at
    all -- which is why this is a second reader beside the first rather than a
    change to it. **A claim about a fixture is textual; a claim about a
    capture is columnar, and the bare date in the sentence is what tells them
    apart.**

    `read_capture()` is the sibling's, imported at the top rather than
    re-derived: it is already the reader that drops `#` lines before the
    header is read, which is the whole of what makes a `#`-header mention not
    count, and a second parser here would have to learn that separately.
    """
    for path in paths:
        if not path.endswith(".csv") or not os.path.isfile(path):
            continue
        if read_capture(path)[0].get(address):
            return True
    return False


def with_column(paths):
    """How many of `paths` have an `addr` column to read a claim against.

    A date can resolve to `.txt` dumps alone -- `ecrw.py dump` output, with no
    column at all -- and then the columnar read has nothing to ask. That is
    the row 6 and row 8 shape and it is a fact about the *file set* rather
    than about any literal's spelling, so it is reported in the dated block
    beside the file count rather than added to the closed shape list, whose
    docstring says an eighth entry appearing in the tree is a change to that
    docstring and not an invitation to add a regex.
    """
    return sum(1 for path in paths
               if path.endswith(".csv") and os.path.isfile(path))


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


def check(root=TESTDATA, functions=FUNCTIONS, registers=REGISTERS,
          captures=CAPTURES):
    """A `Result` for one testdata tree.

    The index is read from `root/README.md`, so a caller cannot point the
    check at one file's table and another file's tree, and the whole tree is
    walked at once rather than per row: the `unplaced-window` row is only
    decidable in the company of the rows it cross-references.

    The file set is chosen **per sentence** rather than per row, because a row
    is a cell of prose and a date names one sentence's capture: a row whose
    first sentence is about a capture and whose second is about its own
    fixture is two claims over two file sets, and reading the row's own files
    for both would be the misattribution the date is there to prevent.
    """
    index_path = os.path.join(root, "README.md")
    with open(index_path, encoding="utf-8") as f:
        index = f.read()

    files = table_cells(index)
    descriptions = table_cells(index, column=3)
    code = code_addresses(functions, registers)

    claims, shapes, dated = [], [], collections.OrderedDict()
    per_row = collections.Counter()
    literal_rows = set()
    for number, cell in enumerate(descriptions, 1):
        named = files[number - 1] if number <= len(files) else ""
        paths = row_files(named, root)
        for _, sentence in units(cell):
            found, captures_of, dates = captures_for(sentence, captures)
            # `or`, never a union: a date that resolves redirects the sentence
            # away from the row's own fixtures, so a claim about a capture
            # cannot be satisfied by a row that names the byte in its after-dump.
            about_capture = found == RESOLVED
            held = captures_of if about_capture else paths
            for address, token, offset in literals(sentence):
                literal_rows.add(number)
                reason = reason_for(address, token, sentence, offset, code,
                                    dates[0][0] if found == MISSING else None)
                # Every glob the sentence named, never only its first, so a
                # reader of a refused sentence's report line sees which dates
                # were skipped -- and a dated claim still cannot be read as one
                # about the row's own cell.
                against = ", ".join(pattern for pattern, _ in dates) or named
                if reason:
                    shapes.append((number, address, reason))
                    claims.append(Claim(number, against, address, token, reason,
                                        UNRESOLVED))
                else:
                    per_row[number] += 1
                    # Which reader, and it is the corpus rather than a flag:
                    # a date that resolved means the sentence is about a real
                    # capture, and a capture's `addr` column is the question.
                    # Every other claim is about a fixture, where a mark label
                    # is a real way to carry an address and there is no column
                    # to read.
                    carried = (carried_by_column(address, held)
                               if about_capture
                               else carried_by(address, held))
                    claims.append(Claim(number, against, address, token, None,
                                        RESOLVED if carried else MISSING))
                # One entry per date the sentence named, each keyed by its own
                # glob with its own files, so a refused two-date sentence's
                # literals are listed under both dates and a date nobody could
                # read is visible in the block rather than only on stderr.
                for pattern, matched in dates:
                    dated.setdefault(pattern, [matched, []])[1].append(
                        claims[-1])

    resolved = sum(1 for c in claims if c.verdict == RESOLVED)
    missing = sum(1 for c in claims if c.verdict == MISSING)
    return Result(len(files), len(literal_rows), len(claims), resolved, missing,
                  len(claims) - resolved - missing, resolved + missing,
                  len(per_row), claims, shapes,
                  [(pattern, where[0], where[1]) for pattern, where in dated.items()])


def report(result):
    """Print each disagreement and each skipped literal, and return the misses.

    `unresolved` is printed on stderr so a reader can see *why* a literal was
    not checked -- and the sentence says "not checked, not absent", because
    a pointer-checker that reported its own blind spot as a broken index is
    the failure mode the sibling's docstring spends a page on. The bracketed
    file set is the one the claim was held against, so a dated claim reads as
    the glob it resolved rather than as a cell the reader cannot parse.

    The `missing` line is the sibling's wording, kept rather than given a
    second phrasing for a dated claim: a disagreement is a defect in the
    index's prose about a fixture either way, and whether that fixture is one
    the row names or one a date in the sentence names, a reader is sent to the
    same place -- the sentence.
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


def dated_report(result):
    """Print each dated claim with the file set it was checked against.

    The issue asks for the literals of a sentence naming a capture to be
    reported one by one against the files that date resolved to, and neither
    the tallies nor `report()` can say it: both count, and a reader asking
    *which* capture a claim about a capture was resolved to needs the answer
    per literal. The block is on stdout, because nothing here is a finding, and
    it is printed whenever there is a dated sentence rather than whenever there
    is a dated disagreement -- an empty block would otherwise be
    indistinguishable from a run that read no dates at all, which is the
    failure mode the counts exist to prevent.

    The `N with an addr column` clause sits on the file-count line rather than
    in the shape list, and that is where a fact about a *file set* belongs: a
    date resolving to `.txt` dumps alone has no column for the columnar read to
    ask, and a reader seeing a claim `resolved` has no other way to learn that
    the other files of the date carried no column to consult.
    """
    if not result.dated:
        return
    print("dated-capture claims, each held to the captures its date names and "
          "never to the row's own fixtures:")
    for pattern, paths, dated in result.dated:
        print(f"  {pattern} ({len(paths)} capture(s) under "
              f"{repo_path(CAPTURES)}, {with_column(paths)} with an addr "
              f"column): " + ", ".join(
                  f"row {c.row} {c.address} {c.verdict}" for c in dated))


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

    result = check(captures=CAPTURES)
    if report(result):
        return 1
    by_shape = collections.Counter(reason for _, _, reason in result.shapes)
    print(f"{result.rows} table row(s), {result.literal_rows} literal-bearing: "
          f"{result.literals} literal(s), {result.resolved} resolved, "
          f"{result.missing} missing, {result.unresolved} unresolved")
    print(f"{result.checked} claim(s) checked, {result.claiming_rows} claiming "
          f"row(s), {len(result.shapes)} passed over under the five shapes and "
          "the two dated refusals, each of them: not checked, not absent")
    # Five, not seven: the two dated refusals are the other two entries of the
    # docstring's list, and the one dated sentence in the committed index names
    # one date and resolves. The `shapes:` line below is where the instances
    # are, and a reader who wants the list is one line further down.
    print("shapes: " + ", ".join(
        f"{reason} {count}" for reason, count
        in sorted(by_shape.items(), key=lambda kv: (-kv[1], kv[0]))))
    dated_report(result)
    print(f"{repo_path(INDEX)}: every address claim in the third column agrees "
          "with the fixtures its row names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
