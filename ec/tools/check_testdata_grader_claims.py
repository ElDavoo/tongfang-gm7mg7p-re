#!/usr/bin/env python3
"""Hold each testdata index row's claims about the grader's own output to it.

`check_testdata_index.py` holds `ec/tools/testdata/README.md` and the tree
under it to each other. `check_testdata_row_claims.py` reads the **third**
column for one kind of claim -- an address a row attributes to a file that row
names -- and holds it to those files. It reads nothing else in that column, and
issue #978 measured what that costs: run over the pre-repair tree at each of the
index's hand-repairs it reported 0 `missing` every time, because the rows those
repairs touched spell **zero** backticked addresses. `docs/findings/
testdata-row-claims-repair-measurement.md` calls that "a recorded blind spot
with the reason it missed" and names this as the follow-up: those rows are about
mark labels, block membership and **where a count is taken**, and no address
question can reach any of them.

That gap is between the index's prose and `grade_0751_isolation.py`, and it is
decidable offline from committed inputs: the third column states what the grader
prints over a fixture set, the fixture set is committed, and the grader takes it
as arguments. So this reads the same column for that kind of claim and decides
it by **running the grader over the set the row's first column resolves to**.
No capture is opened, no EC is read, and no laptop or Windows machine is
involved.

**This is a new file, not a mode on `check_testdata_row_claims.py`.** That
tool's docstring records why: it reads a *fixture's bytes* through an address a
sentence attributes to them, and a sentence saying "prints `2 of the 8` here"
attributes nothing to any file -- it is a claim about a tool, which is a
different oracle over a different question. What carries over is the invariant
in its own words, and both tools import the same readers rather than writing
them out a second time: `row_files` resolves the first column with the index's
own `...`/`*` shorthands, `table_cells` returns the third by position, and
`units()` is the shared sentence splitter (issue #273), handed one *cell* rather
than the index so the three columns do not fuse into one unit.

**The right-hand side is the grader's own text, imported -- never re-derived.**
The index writes a note constant's *name* (`` `UNPLACED_GRADED_NOTE` ``), not the
prose of the note, so the check is `grade.UNPLACED_GRADED_NOTE.format(...)`
appearing in what the run printed, with the numbers the row states. A rule that
re-spelled the note would be a second copy of a string that lives in one place,
and it would go red the day the wording changed without the meaning changing.
The same holds for the withheld banner, which is located by
`grade.WITHHELD_REASON` being on the line rather than by the tool's
`f"{withheld} of the {scope} were not graded: "` spelling being written out here.

**The `N of the M` stem is printed in three grammatical places**, and a bare
substring test would be wrong on two of them, so the *context* is the closed
entry and not the number: the withheld banner and the count line are read, and
the movement line's own restatement is declined by name because no module
constant identifies that line. Each claim is read with the text between it and
the claim before it, cut at a clause boundary, which is what tells "the withheld
banner's `1 of the 8`" from "the count line's `1 of the 7`" in one sentence --
two claims, two contexts, and the split is between them rather than guessed at
from the whole cell.

**The trailing `It is *not* a prediction that ...` clause is stripped before any
claim is read.** Where a row carries one it is a deliberate refusal about the
future, and a rule that reached it would turn the run red by construction, which
is a different failure from a row this tool cannot read. It is an **exclusion**,
not a decline reason, and the two are reported on separate lines so a reader can
tell a sentence this tool refused to look at from a claim it could not decide.

**The "every row carries one" reading is wrong and is not asserted here.** The
clauses and the rows are two independent counts, and they agree only where the
tree happens to make them: a row may carry none -- so there is nothing for a rule
to reach and the "red by construction" argument does not apply to it -- and a row
may carry two, because `strip_refusal()` cuts at the clause rather than at the
sentence precisely so a row that keeps going after its refusal has both halves
read. The census therefore prints the clause count beside the row count rather
than the two being read as one number, and the per-row distribution over a given
tree is `refusal_count()`'s, printed by the write-up's command and not kept
here. The issue this answers said the clauses were "present on all 27 rows";
that was the issue's own figure and nothing in this tool rests on it.

**Nothing here is a claim about the machine.** This tool is two steps from the
hardware: the index's sentence is about the grader's output, and the grader's
output is itself a claim about a capture no live run has produced since the
fixture was written. A green run says the two agree -- it does not say a fixture
*demonstrates* what its row says about the EC, which is the sibling's own
"what this does not check", one step closer to the hardware.

**The closed shape list, which is the whole of the conservative half.** They are
counted, printed with the reason, and do not fail the run -- a checker that
reported its own parser's blind spot as a broken index would be pushed to grow a
rule for whatever it could not read, and would end up inventing the thing it is
checking. `SHAPES` and `DECLINES` are the one place each list is written down as
a value; the bullets below restate each entry in prose and open with the string
the constant gives it, and the suite holds the two to each other by name, so an
entry appearing in the tree that the lists do not name is a change to this
docstring and to the constant rather than an invitation to add a regex. Each
entry has a case in
`test_check_testdata_grader_claims.py`, including the entries with no instance
in the committed index -- those are pinned by scratch cases, because the run
cannot show them.

  Shapes -- read and decided, by running the grader:

  * `note printed` -- a note constant's name in backticks. The constant is
    resolved off the grader module by name and its text -- with the claim's
    `N of the M` filling the format fields, where it has any -- has to be in
    what the run printed. Row 29's `UNPLACED_GRADED_NOTE` at `2 of the 8` is
    the committed instance.
  * `note withheld` -- the same token where the words between it and the claim
    before it negate it ("do not", "cannot reach"), so the constant's text has
    to be **absent**. Row 29's `UNREAD_MARK_NOTE` over a `--block 0xA0` run is
    the committed instance, and it is the shape that can be wrong without the
    index being interestingly wrong: `graded_unplaced` is structurally zero
    under `--block`, so this holds the index's sentence to that structure
    rather than to the note's wording. **The run it is decided at is the scoped
    one the sentence names**, which is what `scope_for()` is for -- decided
    against the whole-capture run the note is absent for an unrelated reason
    (that run reaches the `graded_unplaced` branch), so the claim would be a
    green no run earned.
  * `withheld banner count` -- `N withheld of M`, or a `N of the M` whose
    context names withholding. The right-hand side is the line carrying
    `grade.WITHHELD_REASON`, read as a `(withheld, windows)` pair -- the counts
    in front of it, rather than the tool's f-string spelling written out here.
    Rows 24 and 31's "the 2 withheld of 8" and row 30's "the withheld
    banner's `1 of the 8`" are the committed instances, and the first two are
    the reason a bare `N of the M` test would be wrong here: neither row writes
    the stem.
  * `unplaced note count` -- a `N of the M` whose context names the count line
    or the constant. The right-hand side is
    `grade.UNPLACED_GRADED_NOTE.format(unplaced=N, graded=M)`. **Row 30 is the
    committed instance and it is the one that earns this shape**: its two
    denominators differ, `1 of the 8` against `1 of the 7`, which is what the
    index says makes that run the one able to tell where a count is taken. Row
    29 writes the same note at `2 of the 8`, but it is **not** a second
    instance -- the pair there is written against the constant and is read as
    the note's own numbers, under `note printed` above, which is why the
    context matters: the same `2 of the 8` on row 29 has two denominators
    that coincide and would print the same whichever way the count was taken.
  * `exit code` -- "exit N" / "exits N". The run's own return code, which is
    `main()`'s return rather than a line of its output, so this is the one
    shape read from the call and not from the text.
  * `block verdict` -- a verdict word, backticked or in parentheses, beside a
    `block K of M` or with no block named at all. The right-hand side is the
    grader's own `block K/M: VERDICT` line, matched case-insensitively because
    the index writes `(void)` where the tool prints `VOID` -- a case difference
    would be a spelling failure dressed up as a claim one.
  * `window count` -- a window count the sentence says a run **prints**. The
    verb is part of the token rather than a gate on a bare count, and that is
    what keeps row 30's "the two windows in no block differ in exactly that" out
    of the run: it is about the fixture's own shape, and holding it to a count
    of printed headers would be the misattribution the sibling's dated-capture
    rule exists to stop. The right-hand side is the number of the grader's
    `--- mark N/M:` headers, and a count spelled as a word is read through
    `WORDS` imported from `check_testdata_row_claims.py` rather than through a
    second numeral table written here.

  Every shape above is answered `unresolved` -- not agreed, not disagreed --
  when the run it names **refused** rather than graded. A refusal prints almost
  nothing, so a `note withheld` claim over a run refused for a bad `--block`
  value would otherwise find its constant absent and record a green no capture
  set earned; the census line the grader opens a graded run with is what tells
  the two apart.

  Declines -- counted, printed with the reason, and never failing the run:

  * `another row's fixture` -- the clause a claim sits in names a fixture set
    this row does not. Row 30's "`unplaced-window/`, the same day byte for byte
    with that one label made readable, exits 0" is the committed instance, and
    it is the sentence's own construction that decides it: that `exits 0` is
    about the other set is stated by the reference sitting in front of it, and
    the `exits 1` and `intact` two clauses earlier are about this row because
    nothing in front of *them* names another set. **Row 24's "the same 2
    withheld of 8" is read rather than declined**, because the reference it
    would have to resolve -- `3blocks/` -- is in a clause of its own and this
    row's own set prints the same `2 of the 8`; a rule that reached past the
    clause to find it would be the parser guessing, which is the failure
    `clause_of()` exists to prevent.
  * `not this grader's row` -- the row's `Feeds` cell names another tool. The
    `gpu-door-*` and `sweep-summary-*` rows feed `grade_gpu_door.py` and
    `grade_sweep_summary.py`; one grader is this tool's whole scope, and a row
    fed to another is a named decline rather than a silently skipped row.
  * `no capture in the row's file set` -- the first column resolves to no
    `.csv`. The `...-before-0700.txt` / `...-after-0700.txt` rows are
    `ecrw.py dump` output read through `--dump-pair`, which is a pair of flags
    rather than a capture.
  * `withheld count not in whole-capture spelling` -- a withheld count in a
    claim that also names `--block`. That run spells the banner
    `N of the M window(s) of this block (N of the capture's K window(s))`,
    which is three numbers and a different question; no row states a claim
    against it, so one that did is declined rather than read against a
    substring that would answer something else.
  * `movement restatement` -- a claim about the movement line's own "That is
    the N window(s) that were graded", which row 24 writes as "one of the 6 that
    were graded moved". Declined for the reason the shapes above are not:
    **no module constant identifies that line**, so deciding it would mean
    re-deriving the grader's prose here and holding the copy to it. The
    `2 withheld of 8` in the same sentence is still read, which is what the
    phrase being its own claim rather than a clause rule is for.
  * `no closed shape` -- a `N of the M` whose clause names neither counted
    context. The stem is printed in three grammatical places and only two of
    them are in `SHAPES`; a count belonging to the third is declined here
    rather than guessed at. **This is the entry that makes the closed list
    closed**: without it a count the tool cannot place would be reported under
    a token name that is not a decline, which is the shape of a silent cap.

  **A count spelled as a word is read, not declined.** "prints that block's
  three windows" is row 30's own sentence and it is decidable -- the run's
  `--- mark N/M:` headers are countable -- so the numeral is read through
  `WORDS` imported from `check_testdata_row_claims.py` rather than through a
  second table written here. What keeps the same row's "the two windows in no
  block differ in exactly that" out of the run is the verb inside the token,
  not the numeral: that one is about the fixture's own shape, and holding it to
  a count of printed headers is the misattribution the sibling's dated-capture
  rule exists to stop.

Usage:
    python3 ec/tools/check_testdata_grader_claims.py [--check]
"""
import argparse
import collections
import contextlib
import importlib.util
import io
import os
import re
import sys

# The readers, all imported rather than re-derived, each for the reason its own
# module documents. `row_files` resolves the first column with the index's own
# shorthands, so a fixture set is the same set three tools agree on;
# `table_cells` returns a column by position off a header the reader recognises,
# so an edit above the table cannot move the scan off it and leave a green run
# that read no rows at all.
from check_cluster_citations import units
from check_testdata_index import MISSING, RESOLVED, TESTDATA, UNRESOLVED, \
    repo_path, table_cells
from check_testdata_row_claims import BACKTICKED, WORDS, row_files

HERE = os.path.dirname(os.path.abspath(__file__))

# The grader, loaded by path rather than by name and for the reason
# `test_grade_0751_isolation.py` opens its own two lines the same way (#548): it
# is run from a directory it is not a package in, and it is this tool's **oracle**
# rather than a dependency -- a second copy of its constants, however it were
# imported, would be a second thing to fall out of date.
GRADER = os.path.join(HERE, "grade_0751_isolation.py")

_spec = importlib.util.spec_from_file_location("grade", GRADER)
grade = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grade)

# The index file's name inside whichever root a run was handed, the sibling's own
# constant for the same reason: `check()` opens it and `closing_line()` names it,
# and one place decides where the index is.
INDEX_NAME = "README.md"

# The note constants a claim may name, and the one place that list is written
# down. Membership is a closed list rather than "any all-caps string on the
# module" so a rename in the grader reads as `unknown note constant` -- a
# decline this tool prints -- rather than as a sentence it silently had no
# opinion about. `test_every_note_is_the_graders_own` holds each one to a
# module-level string, so a typo here fails instead of printing.
NOTES = (
    "UNPLACED_GRADED_NOTE",
    "UNREAD_MARK_NOTE",
    "WITHHELD_REASON",
)

# What this tool reads and decides. The one place the list is written down as a
# value: `claim_shape()` returns a name from it or `None`, and `decline_report()`
# prints every entry with its own count -- **including the entries with none**,
# which is the half that matters, because a list entry no instance is a limit the
# tool has rather than a shape it has reached. The docstring's bullets restate
# each name in prose and open with it, and the suite holds the two to each other,
# so an entry in one and not the other is named rather than counted.
SHAPES = (
    "note printed",
    "note withheld",
    "exit code",
    "block verdict",
    "withheld banner count",
    "unplaced note count",
    "window count",
)

# The declines, in `decline_for()`'s order, first match wins, each with a case in
# the suite. `another row's fixture` is first because it is a property of the
# claim's context rather than of the row, the same precedence
# `check_testdata_row_claims.py` gives its multi-date refusal.
DECLINES = (
    "another row's fixture",
    "not this grader's row",
    "no capture in the row's file set",
    "withheld count not in whole-capture spelling",
    "movement restatement",
    "no closed shape",
)

# The claim tokens, one per thing the index writes that this tool can decide.
# They are found by reading position and the gap between one and the next is what
# says what each is about, which is `claims_in()`'s whole job.
NOTE_TOKEN = re.compile(r"`(" + "|".join(NOTES) + r")`")
COUNT_PAIR = re.compile(r"`(\d+) of the (\d+)`")
WITHHELD_PAIR = re.compile(r"\b(\d+)\s+withheld\s+of\s+(\d+)\b")
EXIT_CODE = re.compile(r"\bexits?\s+(?:code\s+is\s+)?(\d+)\b", re.IGNORECASE)
VERDICT_WORD = re.compile(r"`(intact|VOID|PARTIAL)`|\((intact|void|partial)\)",
                          re.IGNORECASE)
BLOCK_OF = re.compile(r"\bblock\s+(\d+)\s+(?:of|/)\s+(\d+)\b", re.IGNORECASE)

# A window count, and **the verb that makes it a claim about what a run printed
# rather than about the fixture's own shape**. Row 30 writes both sorts in one
# row -- "the two windows in no block differ in exactly that" is about the
# fixture, and "a `--block 0xA0` run of this set prints that block's three
# windows" is about the report -- and the verb is inside the token rather than a
# gate applied to a bare count. Gating it afterwards would emit a claim for every
# window the index mentions and then decline most of them, which is a census of
# sentences this tool was never asked to read. Holding a fixture sentence to a
# count of printed headers is the misattribution the sibling's dated-capture
# rule exists to stop, and this is where it is stopped.
WINDOW_CLAIM = re.compile(
    r"\bprints?\b[^.]{0,40}?\b(\d+|one|two|three|four|five|six|seven|eight|nine)"
    r"\s+windows?\b", re.IGNORECASE)

# The window header the grader prints per graded window, and the number of them
# a run's output carries. The header is the tool's own
# `f"\n--- mark {n}/{total}: ..."` opening rather than a copy of its text.
WINDOW_HEADER = re.compile(r"^--- mark \d+/\d+:", re.MULTILINE)

# The census line the grader opens a graded run with, and which is how a run that
# **refused** is told from one that graded. It matters because a refusal prints
# almost nothing: a `note withheld` claim over a run refused for a bad `--block`
# value would otherwise find its constant absent and record a green that no
# capture set earned.
CENSUS = re.compile(r"capture\(s\), \d+ mark row\(s\)")

# The two counted lines of the report, matched where the grader prints them.
# `WITHHELD_LINE` reads the counts in front of `grade.WITHHELD_REASON` rather
# than re-spelling the tool's f-string, so the sentence it identifies is the one
# the constant is on and the numbers come off the run rather than off a copy
# written here. The unplaced count has no such line pattern because its
# right-hand side is the constant itself, formatted.
WITHHELD_LINE = re.compile(r"^\s*(\d+) of the (\d+) window\(s\) above were "
                           r"not graded")
BLOCK_LINE = re.compile(r"^\s*block\s+(\d+)/(\d+):\s*(\w+)")

# The words that say which context a bare count is about, read off the clause the
# count sits in. `unplaced` first because row 30 names "the count line" *and*
# row 29 names the constant, and a count whose own clause says "in no block" is
# the count line's whatever came before it.
UNPLACED_CONTEXT = re.compile(r"UNPLACED_GRADED_NOTE|\bcount line\b|\bin no "
                              r"block\b|\bgraded window", re.IGNORECASE)
WITHHELD_CONTEXT = re.compile(r"\bwithheld\b|\bnot graded\b|\bwithhold",
                              re.IGNORECASE)

# The movement line's own restatement of the graded count, which is a **claim
# token** rather than something scanned for inside another claim's clause. It is
# recognised so it can be declined by name: no module constant identifies that
# line, so holding a claim to it would mean re-deriving the grader's prose here
# and holding the copy to it, and a claim this tool cannot read has to say so
# rather than pass over silently. Row 24's "one of the 6 that were graded moved"
# is the committed instance, and the `2 withheld of 8` in the same sentence is
# still read -- which is the whole point of the token being its own claim rather
# than a clause rule that would take the other one with it.
MOVEMENT = re.compile(r"\b(?:that|which)\s+(?:were|was)\s+graded\b",
                      re.IGNORECASE)

# The refusal clause. Three spellings occur in the corpus and they are one thing:
# `*not* a prediction`, `**not** a prediction`, and row 23's "is not a
# prediction that". The emphasis markers are optional rather than enumerated so a
# row that bolds the word differently is still cut.
REFUSAL = re.compile(r"\*+not\*+\s+a prediction|\bis not a prediction that\b",
                     re.IGNORECASE)

# A fixture set another row names, and the negation that flips a note claim from
# printed to withheld.
FIXTURE_REF = re.compile(r"`([^`]+/)`")
NEGATED = re.compile(r"\b(?:do(?:es)? not|do no|cannot|can not|never|without)\b",
                     re.IGNORECASE)

# The clause boundaries a claim's context is cut at. **Strong marks only, and
# not the comma**: row 30 writes its two counts as "the withheld banner's `1 of
# the 8` against the count line's `1 of the 7`", where the comma is the joiner
# inside one clause, and cutting at it would put both counts in a clause holding
# neither context. The em-dash is what separates them, and it is what separates
# row 30's `exits 0` -- which is about `unplaced-window/` -- from the `exits 1`
# two clauses earlier that is about this row.
CLAUSE_BREAK = (";", ":", ".", "—", "–")

# The `--block V` a claim is scoped to, and the `Feeds` cell's tool. Scoped per
# claim rather than per row because one row states claims about two different
# runs -- row 29 says what the unscoped run prints and what a `--block 0xA0` run
# does not -- and a scope read off the row would silently re-scope one of them.
# A bare `--block` with no value beside it is prose about scoping in general and
# matches nothing, which is what keeps row 29's `--block` selecting a block's own
# windows from scoping a claim the same sentence calls unscoped.
BLOCK_FLAG = re.compile(r"`?--block\s+(\S+?)`?(?=\s|,|\.|$)", re.IGNORECASE)
FEEDS_TOOL = re.compile(r"`\.\./([^`]+?\.py)`")

# One claim found in the prose, and what a run found. `verdict` is the sibling's
# vocabulary so a reader who has met one has met the other, and only `MISSING`
# fails: a claim this tool could not decide is `UNRESOLVED`, which prints as
# "not checked, not absent". `detail` is the claim as the index wrote it and
# `expected` the grader's own text, so a disagreement names both rather than only
# saying that one happened.
Claim = collections.namedtuple("Claim", "row shape detail expected verdict")

Result = collections.namedtuple(
    "Result", "rows claiming_rows claims missing declines stripped reasons root")


def strip_refusal(sentence):
    """The sentence with its trailing "not a prediction" clause removed.

    Cut at the clause and not at the sentence, because row 23 keeps going after
    its refusal -- "...it is *not* a prediction that a run will lose a mark, and
    `0x0F0A` is not a prediction that a fan-table byte moves" -- and both halves
    are refusals while the sentence before them is not. The trailing
    conjunction is left with the cut rather than tidied off, so what remains
    reads as the fragment it is and a reader of a report line can see that a
    claim was found in a sentence the refusal was taken out of.
    """
    found = REFUSAL.search(sentence)
    return sentence[:found.start()].rstrip(" ,;") if found else sentence


def refusal_count(cell):
    """How many of `cell`'s sentences carried a refusal clause.

    Reported on its own line and counted apart from the declines, because it is
    an exclusion rather than a shape this tool cannot read: a rule reaching one of
    these clauses would turn the run red by construction, which is a different
    failure from a row nothing could be said about, and a reader told the two are
    one number would draw the wrong conclusion from either.

    **A count of clauses, not a count of rows, and not a claim that there is one
    per row.** Summing it over a cell gives that row's distribution and summing
    that over the index gives a total that agrees with the row count only where
    the tree happens to make it -- which is why the census prints both beside
    each other and a reader of this number is told nothing about rows carrying
    none or more than one.
    """
    return sum(1 for _, sentence in units(cell)
               if strip_refusal(sentence) != sentence)


def feeds_tool(cell):
    """The tool a `Feeds` cell names, or `None` where it names no `.py`."""
    found = FEEDS_TOOL.search(cell)
    return found.group(1) if found else None


def scope_of(text):
    """The `--block V` this text names, or `None` for a whole-capture run.

    **The nearest mention at or before the claim**, rather than the one in the
    claim's own clause: a sentence names its run once and the claims after it
    inherit it, and reading the clause alone loses that. Row 29 states "a
    `--block 0xA0` run over it is what shows why: the per-block sentence prints,
    the count line and `UNREAD_MARK_NOTE` do not, exit 0" -- the `:` cuts the
    clause, so `UNREAD_MARK_NOTE` and the `exit 0` behind it saw no scope and
    were decided against the **whole-capture** run instead. That is a green no
    run earned: the whole-capture run over `unplaced-window/` reaches the
    `graded_unplaced` branch and so prints no `UNREAD_MARK_NOTE` for a reason that
    has nothing to do with the one the row states, and the `--block 0xA0` run the
    sentence names was never made at all.

    Carried forward from the nearest preceding mention **within the sentence**
    rather than the cell: a sentence that names no `--block` value makes no claim
    about a scoped run, and row 30's other sentence is exactly that case -- it is
    about the two counts a whole-capture banner and a count line print.

    The **last** mention in the claim's window rather than the first, so a
    sentence that re-scopes mid-way is read at the scope its later claims sit
    under.
    """
    found = None
    for mention in BLOCK_FLAG.finditer(text):
        found = mention
    return found.group(1) if found else None


def scope_for(body, match, after):
    """The `--block V` a claim is read at, or `None` for a whole-capture run.

    `scope_of()` over the claim's **whole window** -- the sentence from its
    start up to the next claim -- rather than over the claim's own clause, so a
    scope named earlier in the sentence carries forward to the claims behind it.
    The old reading cut at the clause boundary and lost it; this is the fix, and
    the window still ends where the next claim begins so one claim's scope
    cannot reach the next one's.
    """
    return scope_of(body[:match.end() + len(after)])


def note_text(name, numbers=None):
    """The grader's own note constant, formatted with `numbers` where it needs.

    A constant with format fields is filled from the `N of the M` the index
    states, in the order the constant declares its fields -- which for
    `UNPLACED_GRADED_NOTE` is `{unplaced}` then `{graded}`, and which the index
    spells in that order as the smaller number first. A constant with no fields is
    its own text, and that is what `UNREAD_MARK_NOTE` and `WITHHELD_REASON` are.

    `None` rather than a raised `KeyError` where the field count and the count
    pair disagree: this tool's answer to a claim it cannot read is to say so and
    move on, and a formatting failure here would take the whole census down over
    one sentence.
    """
    text = getattr(grade, name, None)
    if not isinstance(text, str):
        return None
    fields = re.findall(r"\{(\w+)\}", text)
    if not fields:
        return text if numbers is None else None
    if numbers is None or len(numbers) != len(fields):
        return None
    return text.format(**dict(zip(fields, numbers)))


def run_grader(paths, block=None):
    """(exit code, output) for one grading of `paths`, in this process.

    In-process through `grade.main(argv)` rather than a subprocess, for the two
    reasons `test_grade_0751_isolation.py` gives at its own `redirect_stdout`
    case: an interpreter start per run is not what a cheap gate should cost, and
    half of these claims' right-hand sides are the module's own string constants,
    which a subprocess boundary would have to re-read from disk to get.

    stdout and stderr are captured together, because a claim about what a run
    prints is about the report a reader is shown rather than about which of the
    two streams a line arrived on -- the grader prints its refusal text on both.

    `SystemExit` is caught rather than let through: `main()` refuses a bad command
    line by raising, and a refusal is an answer this tool has to print rather than
    a crash that takes the census down with it.
    """
    argv = [str(path) for path in paths]
    if block is not None:
        argv += ["--block", block]
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = grade.main(argv)
        except SystemExit as refused:
            code = refused.code
    return (code if isinstance(code, int) else 1), out.getvalue() + err.getvalue()


def claims_in(sentence):
    """Every claim in `sentence`, in reading order, each with its window.

    A claim's window is the text between the claim before it and the claim after
    it -- so `before` is what the claim is attached to and `after` is what it is
    attached to *it* -- and it is what decides three separate things: which
    context a bare `N of the M` count belongs to (row 30's "the withheld
    banner's `1 of the 8`" against "the count line's `1 of the 7`" is one
    sentence and two contexts), whether a note constant is claimed as printed or
    as withheld (row 29's "`UNREAD_MARK_NOTE` do not" puts the negation *after*
    the token), and whether the claim is about a fixture set this row does not
    name.

    **The gap between claims rather than the whole sentence**, because the whole
    sentence is what puts row 30's `exits 0` -- which is about `unplaced-window/`
    -- in the same unit as the `exits 1` two clauses earlier that is about this
    row. A whole-sentence rule would decline both or neither.

    A claim is `(shape, match, before, after)`. The shape is resolved in
    `claim_shape()` rather than here, because deciding it needs the window and the
    counts together.

    **A `N of the M` written against a note constant is not a second claim**, and
    that is the *only* shape dropped this way. Row 29 writes "`UNPLACED_GRADED_NOTE`
    at `2 of the 8`", the note is formatted with that pair, and the pair has
    therefore been read already; emitting the count separately would check the same
    sentence twice and report a second answer for one claim. It is dropped rather
    than declined, because it is not something this tool cannot read -- it is the
    same claim under another token.

    **What makes the count the note's own is what the count's own clause names,
    not the token in front of it.** A count whose clause names a counted line is
    that line's claim and is read; one whose clause names none can only be the
    numbers the note is formatted with, which is the case this rule is written
    for. Reading the drop as adjacency instead took a row's real count with it:
    naming a note earlier in a sentence and then stating a different line's count
    dropped the count, and the note was then formatted with the dropped count's
    numbers -- so a true row went missing against a sentence that was correct,
    on an ordinary reword and with no fixture touched. `claim_shape()` already
    answers "does this count name a counted line" from the same clause every
    other count is read with, so the two cannot answer it differently.

    **Every other shape after a note is read normally.** Dropping whatever
    followed a note took row 29's "the count line and `UNREAD_MARK_NOTE` do not,
    exit 0" at its `exit 0` as well as its count: an `exit code` claim, decidable,
    whose right-hand side is the run's own return code. A supported claim read by
    nobody is the silent cap this tool's own write-up argues against -- a census
    that counted neither the claim nor a decline for it gives a reader no way to
    know it was never looked at. So the rule is narrowed to the one shape it was
    written for, and a shape this tool cannot decide belongs in `DECLINES` with a
    printed count rather than in a silent `continue` here.
    """
    found = tokens(sentence)

    out = []
    for index, (shape, start, end, match) in enumerate(found):
        if count_is_a_notes_own(found, index, sentence):
            continue
        before = sentence[found[index - 1][2] if index else 0:start]
        after = (sentence[end:found[index + 1][1]]
                 if index + 1 < len(found) else sentence[end:])
        out.append((shape, match, before, after))
    return out


def tokens(sentence):
    """Every claim-shaped token in `sentence`, in reading order.

    One scan shared by `claims_in()` and `note_own_count()`, because both are
    asking about the same tokens and a second reader of the same seven patterns
    would be a second answer to which count a note is written with -- which is
    the disagreement this pair exists to prevent.
    """
    found = []
    for shape, pattern in (("note", NOTE_TOKEN),
                           ("count", COUNT_PAIR),
                           ("withheld", WITHHELD_PAIR),
                           ("exit", EXIT_CODE),
                           ("verdict", VERDICT_WORD),
                           ("windows", WINDOW_CLAIM),
                           ("movement", MOVEMENT)):
        for match in pattern.finditer(sentence):
            found.append((shape, match.start(), match.end(), match))
    found.sort(key=lambda item: (item[1], item[2]))
    return found


def clause_of(before):
    """The clause of `before` a claim is attached to.

    **Bounded at the last clause boundary rather than read whole**, and this is
    what makes row 30's sentence decidable: it opens "a withheld window and a
    graded window in no block hold at once" -- both contexts in one sentence,
    describing the run rather than any one count in it -- and its two counts sit
    at opposite ends of a long sentence with "the withheld banner's" and "the
    count line's" immediately beside them respectively. Reading the whole prefix
    would answer both counts from the opening clause and get one of them wrong.

    The boundary is punctuation the index already uses to end a clause, and it is
    the same rule the sentence splitter `units()` applies for the same reason.
    An em-dash is in it because row 24's own count sits behind one.
    """
    cut = max((before.rfind(mark) for mark in CLAUSE_BREAK), default=-1)
    return before[cut + 1:] if cut >= 0 else before


def claim_shape(shape, before, after):
    """The closed-list entry a claim belongs to, or `None` when it names none.

    `SHAPES`' order and first match wins. The note constants are asked before
    the bare counts because a note and a count can be one claim in the index's
    prose -- row 29 writes "`UNPLACED_GRADED_NOTE` at `2 of the 8`" -- and
    `UNPLACED_GRADED_NOTE` has format fields the count pair fills, so reading the
    count on its own would ask the banner a question the sentence is not asking.
    """
    if shape == "note":
        return "note withheld" if NEGATED.search(before + after) \
            else "note printed"
    if shape == "withheld":
        return "withheld banner count"
    if shape == "exit":
        return "exit code"
    if shape == "verdict":
        return "block verdict"
    if shape == "windows":
        return "window count"
    if shape == "count":
        clause = clause_of(before)
        if UNPLACED_CONTEXT.search(clause):
            return "unplaced note count"
        if WITHHELD_CONTEXT.search(clause):
            return "withheld banner count"
        return None
    return None


def pair_of(match):
    """A count match as a pair of ints, or `None` where it is not one.

    Every pattern this is called with captures two groups -- `COUNT_PAIR`'s
    `` `N of the M` `` and `WITHHELD_PAIR`'s "N withheld of M" -- so the answer
    is the same shape either way and which of the two matched is not the
    question. `None` rather than a raised `ValueError`, for the reason
    `note_text()` gives: a claim this tool cannot read is one it says so about.
    """
    try:
        return int(match.group(1)), int(match.group(2))
    except (TypeError, ValueError):
        return None


def numeral(text):
    """A count the index wrote as digits or as one of `WORDS`, or `None`.

    `WORDS` is `check_testdata_row_claims.py`'s own zero-to-eight vocabulary,
    imported rather than written out a second time: it is already the list of
    numerals this repository's checkers spell, and a second copy here would be a
    second thing to fall out of date. **A numeral it does not cover reads as
    `None` and the claim as undecided**, which is where `nine` and above land --
    the list stops at `eight`, and widening it is a change to that tool's
    vocabulary rather than a threshold invented here.
    """
    text = text.lower()
    if text.isdigit():
        return int(text)
    return WORDS.index(text) if text in WORDS else None


def withheld_pair(output):
    """The `(withheld, windows)` a run's whole-capture banner states, or `None`.

    Only the whole-capture spelling is read, and only because it is the one that
    carries both numbers in the order the index writes them. A `--block` run
    prints `N of the M window(s) of this block (N of the capture's K
    window(s))`, which is three numbers and a different question; a claim
    against that spelling is declined rather than read against a substring that
    would answer something else.
    """
    for line in output.splitlines():
        found = WITHHELD_LINE.match(line)
        if found:
            return int(found.group(1)), int(found.group(2))
    return None


def block_lines(output):
    """The `(index, total, verdict)` triples the run printed, verdict lower-cased.

    The grader's own `block K/M: VERDICT` line. The verdict is folded to lower
    case because the index writes `(void)` where the tool prints `VOID`, and a
    case difference held as a disagreement would be a spelling failure dressed up
    as a claim about the grader.
    """
    out = []
    for line in output.splitlines():
        found = BLOCK_LINE.match(line)
        if found:
            out.append((int(found.group(1)), int(found.group(2)),
                        found.group(3).lower()))
    return out


def decide(shape, match, before, after, body, run):
    """(expected, verdict) for one claim, given the run it is about.

    `run` is `(code, output)` for the claim's own `(fixture set, scope)`, which
    `check()` caches: a row states several claims about one run and grading it
    again per claim would make this tool's cost a multiple of the corpus's rather
    than of its own. The cache key carries the scope, so a `--block` claim never
    reads a whole-capture run's output -- the difference between two runs that
    print different things and would otherwise read as one.

    **Each shape reads the grader's own text**, never a copy of it written out
    here: the note constants formatted from the claim's own numbers, the banner
    located by the leading counts on the line carrying `WITHHELD_REASON`, and the
    block verdicts read off the tool's `block K/M:` line. Only the exit code is
    read from the call rather than the output, because it is `main()`'s return.
    """
    code, output = run
    if not CENSUS.search(output):
        # The run refused rather than graded, so it printed no report for any
        # claim to agree or disagree with. Every shape answers `UNRESOLVED`
        # rather than reading a short output as a report -- the refusal is
        # about which files and flags were handed in, and none of these
        # claims is about that.
        return "the run refused and printed no report", UNRESOLVED
    if shape in ("note printed", "note withheld"):
        name = match.group(1)
        pair = nearest_count(before, after, body)
        expected = note_text(name, pair)
        if expected is None:
            return name, UNRESOLVED
        present = expected in output
        return (expected, RESOLVED if present == (shape == "note printed")
                else MISSING)
    if shape == "exit code":
        stated = int(match.group(1))
        return str(stated), RESOLVED if code == stated else MISSING
    if shape == "block verdict":
        stated = next((g for g in match.groups() if g), "").lower()
        block = BLOCK_OF.search(before) or BLOCK_OF.search(body)
        printed = block_lines(output)
        if block:
            wanted = (int(block.group(1)), int(block.group(2)))
            verdicts = [verdict for index, total, verdict in printed
                        if (index, total) == wanted]
        else:
            verdicts = [verdict for _, _, verdict in printed]
        if not verdicts:
            return stated, UNRESOLVED
        # A block named but not printed at all is `UNRESOLVED` above; one
        # printed with a different verdict is a disagreement, and the names of
        # the verdicts it did print are what a reader needs to see it.
        return ("block verdicts " + ", ".join(sorted(set(verdicts))),
                RESOLVED if set(verdicts) == {stated} else MISSING)
    if shape == "withheld banner count":
        pair = pair_of(match)
        actual = withheld_pair(output)
        if pair is None:
            return None, UNRESOLVED
        if actual is None:
            return f"{pair[0]} of the {pair[1]}", UNRESOLVED
        return (f"{pair[0]} of the {pair[1]}",
                RESOLVED if actual == pair else MISSING)
    if shape == "window count":
        stated = numeral(match.group(1))
        if stated is None:
            return match.group(1), UNRESOLVED
        printed = len(WINDOW_HEADER.findall(output))
        return (f"{printed} window(s) printed",
                RESOLVED if printed == stated else MISSING)
    if shape == "unplaced note count":
        pair = pair_of(match)
        expected = note_text("UNPLACED_GRADED_NOTE", pair)
        if expected is None:
            return None, UNRESOLVED
        return expected, RESOLVED if expected in output else MISSING
    return None, UNRESOLVED


def nearest_count(before, after, body):
    """The count pair a note constant's own clause states, or `None`.

    A note constant with format fields is formatted from the numbers the index
    wrote beside it, and row 29 writes them as "`UNPLACED_GRADED_NOTE` at `2 of
    the 8`" -- so the pair is the one **the note is written with**, which is
    what `note_own_count()` finds.

    `before` and `after` are searched first, in that order, so a pair written
    right beside the token is read from beside it. **Neither side carries a
    count on this corpus**, because any count is itself a token and the windows
    stop at the next token's start; both sides are kept because they are the
    narrow reading and the fallback below is not, and a reworded row that put
    the numbers beside the token would read them here rather than by the
    sentence-level rule.

    **A count belonging to a different claim is not the note's**, and neither is
    the sentence as a whole. Taking the first `N of the M` anywhere in the
    sentence formatted a note with another claim's numbers whenever a row named
    a note and then stated a different counted line's count: the note was then
    looked for in a spelling the run never printed, and the count that *was*
    the row's went unread behind the drop. Falling through to the first count
    the note owns is the same rule `claims_in()` drops on, so the pair a note
    is decided against and the count dropped as its second reading cannot be two
    different counts.
    """
    for text in (before, after):
        found = COUNT_PAIR.search(text)
        if found:
            return pair_of(found)
    return note_own_count(body)


def note_own_count(body):
    """The `N of the M` in `body` a note constant is written with, or `None`.

    **A count that names a counted line is that line's claim, not the note's.**
    A row may name a note and then state the withheld banner's count in the same
    sentence -- "the withheld banner's `1 of the 8` is what this one prints" --
    and that pair is the banner's to be decided against. A count whose own
    clause names no counted line can only be the numbers the note is formatted
    with, which is the count this returns.

    **The count the note is written with, not any count in the sentence.** A
    sentence can carry a third `N of the M` that belongs to a claim of its own --
    about another row's fixture, say -- and naming it here would format the note
    with a pair no run printed and put a true row in the census as a
    disagreement. The count has to be one a note is written beside, which is the
    same condition `claims_in()` drops on, so the pair a note is decided against
    and the count dropped as its second reading cannot be two different counts.
    """
    found = tokens(body)
    for index, (shape, _start, _end, match) in enumerate(found):
        if shape == "count" and count_is_a_notes_own(found, index, body):
            return pair_of(match)
    return None


def count_is_a_notes_own(found, index, sentence):
    """Whether the count at `found[index]` is one a note is written with.

    **Both halves are needed, and neither is sufficient alone.** A count behind
    a note that names a counted line is that line's claim -- the count the
    adjacency rule used to drop, taking a row's real count with it. A count that
    names no counted line but follows no note is a claim of its own, and reading
    it as the note's numbers would format the note with a pair belonging to
    whatever else the sentence says. `claims_in()` drops on this and
    `note_own_count()` resolves on it, so the two cannot disagree about which
    count the note is written with.
    """
    shape, start, end, _match = found[index]
    if shape != "count" or not index or found[index - 1][0] != "note":
        return False
    before = sentence[found[index - 1][2]:start]
    after = (sentence[end:found[index + 1][1]]
             if index + 1 < len(found) else sentence[end:])
    return claim_shape("count", before, after) is None


def decline_for(shape, before, paths, tool, own, scope):
    """Why this claim is not read, or `None` when it is a claim to decide.

    `DECLINES`' order and first match wins. Every entry here is a property of the
    claim or of the row -- never of what the run printed -- so the same sentence
    is classified the same way whatever the fixtures happen to hold, and a claim
    this tool cannot read is the same set of reasons on every tree. `scope` is
    the claim's own `--block` scope, resolved once by `scope_for()` and handed
    in rather than re-derived.

    **Every entry below reads `clause_of(before)` and not `after`,** and that is
    what makes row 30's sentence decidable rather than uniformly declined. It is
    about `unplaced-window/` and about this row in the same breath: the `exits 0`
    is the claim about the other set and sits *after* a reference to it, while
    the `exits 1` and `intact` are claims about this row and sit before it.
    Reading what follows a claim would attach the next claim's reference to this
    one, which is the same parser-guessing failure `clause_of()` exists to avoid.

    The scope is **passed in rather than read here**, so the decline and the
    decision below it cannot answer "is this claim about a scoped run?"
    differently. Reading it off the clause alone once made a withheld count
    behind a `--block V` mention it was meant to be declined for read as a
    whole-capture one, which `withheld_pair()` cannot answer at all.
    """
    clause = clause_of(before)
    foreign = [token for token in FIXTURE_REF.findall(clause)
               if token.strip("/") not in own
               and "evidence" not in token and not token.startswith("..")]
    if foreign:
        return "another row's fixture", foreign[0].strip("/")
    if tool is not None and tool != os.path.basename(GRADER):
        return "not this grader's row", tool
    if not paths:
        return "no capture in the row's file set", None
    if shape == "movement":
        return "movement restatement", None
    if shape == "withheld" and scope:
        return "withheld count not in whole-capture spelling", None
    return None, None


def check(root=TESTDATA):
    """A `Result` for one testdata tree.

    The index is read from `root/README.md`, so a caller cannot point the check
    at one file's table and another file's tree.

    **Each row is graded against its own file set, and a run is cached per
    `(set, scope)`.** The rows cross-refer, and a claim about one row's set is
    *not* graded over another row's: a sentence naming another fixture set is
    declined by `decline_for()` rather than resolved, because which set a claim
    is about is the sentence's own business and reading it out of the prose is
    the parser guessing. Caching by scope matters for the same reason -- a
    `--block` run and a whole-capture run print different things, and a shared
    key would let one answer the other's claim.

    **The root is carried on the `Result`** rather than left to the report to read
    off a module constant, because the suite points runs at scratch trees: a
    closing line naming the committed index for a run that read another one is a
    sentence with nothing behind it, and that is the same class of mistake issue
    #1022 recorded against the sibling.
    """
    with open(os.path.join(root, INDEX_NAME), encoding="utf-8") as f:
        index = f.read()

    files = table_cells(index)
    feeders = table_cells(index, column=2)
    descriptions = table_cells(index, column=3)

    cache = {}
    claims, declines = [], []
    stripped = 0
    claiming = set()

    def run_for(paths, block):
        key = (tuple(paths), block)
        if key not in cache:
            cache[key] = run_grader(paths, block)
        return cache[key]

    for number, cell in enumerate(descriptions, 1):
        named = files[number - 1] if number <= len(files) else ""
        tool = feeds_tool(feeders[number - 1]) if number <= len(feeders) \
            else None
        paths = [path for path in row_files(named, root) if path.endswith(".csv")]
        own = {os.path.basename(path) for path in paths}

        for _, sentence in units(cell):
            if strip_refusal(sentence) != sentence:
                stripped += 1
            body = strip_refusal(sentence)
            if not body.strip():
                continue

            for shape, match, before, after in claims_in(body):
                # The scope is resolved **once, here**, and handed to both the
                # decline and the decision. Resolving it twice let the two
                # disagree about which run a claim is about -- the decline read
                # the claim's clause and the decision read the claim's window, so
                # a claim whose `--block V` sat earlier in its sentence was read
                # at a scope neither of them agreed on.
                scope = scope_for(body, match, after)
                # The declines run **before** the shape is resolved, and the
                # order matters: a claim about a fixture set this row does not
                # name is not a claim about this row's output at all, so asking
                # which counted context it belongs to first would put a token
                # where a set name belongs and report `no closed shape` for a
                # sentence whose problem is that it is about another row.
                reason, detail = decline_for(shape, before, paths, tool, own,
                                             scope)
                if reason:
                    declines.append((number, reason, body, detail))
                    continue
                resolved = claim_shape(shape, before, after)
                if resolved is None:
                    declines.append((number, "no closed shape", body, shape))
                    continue
                expected, verdict = decide(
                    resolved, match, before, after, body,
                    run_for(paths, scope))
                claims.append(Claim(number, resolved, body, expected, verdict))
                claiming.add(number)

    reasons = collections.Counter(reason for _, reason, _, _ in declines)
    missing = sum(1 for claim in claims if claim.verdict == MISSING)
    return Result(len(files), len(claiming), claims, missing, declines,
                  stripped, reasons, root)


def claim_line(claim):
    """`row N <shape>: <expected>` with the verdict, for one claim.

    `expected` is the grader's own text rather than a paraphrase of it, so a
    disagreement report can be read against what the tool printed without
    re-running anything -- which is the property that makes the report worth
    printing at all, and the reason the note constants are imported rather than
    re-spelled. A long note is elided to its first line and its length is named,
    because a reader who needs the whole thing has the constant and the row to
    read it from.
    """
    shown = " ".join(str(claim.expected).split())
    if len(shown) > 60:
        shown = f"{shown[:57]}..."
    return (f"row {claim.row} {claim.shape}: expected {shown} -- "
            f"{claim.verdict}")


def report(result):
    """Print each disagreement and each undecided claim; return the misses.

    `unresolved` goes to stderr with the sibling's wording, "not checked, not
    absent", because a checker that reported its own blind spot as a broken index
    is the failure mode the sibling's docstring spends a page on. A `missing`
    line carries the sibling's other sentence -- a disagreement here is a defect
    in the index's prose, and it is not a reason to change a fixture -- because
    the fix is the same either way and the fixture is the thing that must not be
    edited to go green.
    """
    for claim in result.claims:
        if claim.verdict == UNRESOLVED:
            print(f"row {claim.row} ({claim.shape}) is not checked: "
                  f"{claim.detail} -- not absent", file=sys.stderr)
    for claim in result.claims:
        if claim.verdict == MISSING:
            print(claim_line(claim), file=sys.stderr)
    if result.missing:
        print(f"{result.missing} testdata grader claim(s) disagree with "
              f"grade_0751_isolation.py", file=sys.stderr)
        print("A disagreement here is a defect in the index. It is not a "
              "reason to change a fixture or to loosen a rule.", file=sys.stderr)
    return result.missing


def decline_report(result):
    """Print every declined claim with its reason, and the refusals left out.

    **The census is the output**, and this is the half of it that is about what
    the tool did not read. `check_testdata_row_claims.py` argues the same way
    about its own shape list and the repository's rule against silent caps is
    what decides it: the answer here is a mix, and a reader who cannot tell a
    declined claim from a clean row cannot tell whether the run covered
    anything.

    A declined claim is printed one per line with its reason and the sentence it
    came from, so a reader can go and look at the row rather than take a tally
    on trust. **The refusals are counted on a line of their own** because they
    are an exclusion rather than a decline, and a reader told the two were one
    number would draw the wrong conclusion from either.
    """
    print(f"{result.rows} row(s) read, {result.claiming_rows} carrying at least "
          f"one claim: {len(result.claims)} claim(s) checked, "
          f"{result.missing} disagreeing")
    print(f"{result.stripped} sentence(s) carried a trailing "
          f"'not a prediction' clause, stripped before any claim was read")
    for number, reason, detail, note in result.declines:
        print(f"  declined row {number} {reason}"
              + (f" ({note})" if note else "") + f": {detail[:150]}")
    # Both closed lists printed whole, entries with no instance included. A list
    # of only the entries a run reached cannot be told from a shorter list, and
    # the difference between "this shape has no instance in the committed tree"
    # and "this shape does not exist" is the whole of what the list is for. The
    # shape line carries no ordinal for the reason the sibling's does not: the
    # order is `SHAPES`' but a reader may transcribe the line and must not read a
    # neighbour off it.
    print("shapes: " + ", ".join(
        f"{shape} {sum(1 for c in result.claims if c.shape == shape)}"
        for shape in SHAPES))
    print("declines: " + ", ".join(
        f"{reason} {result.reasons.get(reason, 0)}" for reason in DECLINES))


def closing_line(result) -> str:
    """The run's last line: what was held to what.

    The index it names is the one `check()` read, off `Result.root`, so a
    scratch run cannot print the committed path for a tree it never opened.

    **Nothing here is a floor.** The three figures it carries are what this run
    did, not what a future run must: a row that gains no claim and a fixture set
    that gains a row both have to leave the run green, because a count of the
    tree is a value every merge has to edit. The suite asserts non-emptiness
    instead.
    """
    return (f"{repo_path(os.path.join(result.root, INDEX_NAME))}: every claim "
            f"the third column makes about grade_0751_isolation.py's own output "
            f"agrees with what the tool printed -- {len(result.claims)} read, "
            f"{len(result.declines)} declined by name, "
            f"{result.stripped} refusal clauses stripped")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Accepted and not branched on, the same spelling `check_testdata_index.py`
    # and `check_testdata_row_claims.py` take: the check is the whole of what this
    # tool does, so --check is the default and the flag is the gate's entry point.
    ap.add_argument("--check", action="store_true",
                    help="check the committed index's claims about the "
                         "grader's output against the fixtures each row names "
                         "(the default, and the gate's entry point)")
    ap.parse_args()

    result = check()
    if report(result):
        return 1
    decline_report(result)
    print(closing_line(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())