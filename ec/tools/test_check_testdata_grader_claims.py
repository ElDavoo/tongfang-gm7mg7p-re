#!/usr/bin/env python3
"""Offline checks for check_testdata_grader_claims.py: committed files only.

The tool's failure mode is silence rather than a crash, and silence here is the
specific defect issue #978 measured: `check_testdata_row_claims.py` reported 0
`missing` over the pre-repair tree at each of the index's hand-repairs because
those rows spell no backticked addresses, so nothing was reading the kind of
claim they are written in. So what is pinned here is the line between what this
tool reads and what it declines to read, from both sides -- each shape it
decides, each entry of the closed decline list, and then **each rule dropped in
turn** and asserted to change the answer. A rule that stops changing the answer
has stopped mattering, whichever way the answer moves, and a suite that does not
notice has the same defect as a check that does not fire.

**The scratch cases check against real fixtures on disk**, copied out of the
committed tree rather than written as text: the tool's whole oracle is the
grader's output over a fixture set, and a case that handed the grader a
synthetic capture would be testing a reader no run ever uses. The descriptions
are inline rather than stored beside the tree, for the reason the sibling suite
keeps its prose inline -- a committed `.md` under `ec/` naming a fixture and
claiming what it grades is exactly what these tools read, so committing one
would make the committed-tree case red by construction.

**Nothing here asserts a figure.** Where the committed tree is checked, the
assertions are that the run reached something, that every row is accounted for,
and that nothing disagrees -- not how many rows, claims or shapes there are. A
count of the tree is a value every merge has to edit, and a fixture row added to
the index later must not break any of these.
"""
import collections
import contextlib
import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).parent
# The tool imports its readers from three siblings; loading it by path is no
# different from running it, and the directory is the same sys.path entry.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_testdata_grader_claims', HERE / 'check_testdata_grader_claims.py')
ctgc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctgc)

# The header a scratch index needs to be read as the `File` table, and the
# `Feeds` cell every scratch row carries. The `Feeds` column is
# `check_testdata_index.py`'s; it is written here because the tool reads it to
# decide whether the row is this grader's, which is the `not this grader's row`
# decline.
HEADER = '| File | Feeds | What it constructs |\n| --- | --- | --- |\n'
FEEDS = '`../grade_0751_isolation.py`'

# The three committed fixture sets this suite copies in. Each is a *shape* the
# grader's own report can be asked about, and choosing them is choosing the
# right-hand side: `unplaced-window/` is the only committed set that reaches the
# `graded_unplaced` branch, `unread-window/` the only one that withholds a
# window and grades an unattributed one at once, and `redone-block/` the only
# one holding two blocks under one value with one of them void.
UNPLACED = '0751-isolation-run-unplaced-window'
UNREAD = '0751-isolation-run-unread-window'
MOVED = '0751-isolation-run-3blocks-moved'
MISSING = '0751-isolation-run-missing-mark'
REDONE = '0751-isolation-run-redone-block'


def committed(name):
    """The committed CSVs of a fixture set, as (basename, text) pairs."""
    directory = HERE / 'testdata' / name
    return [(path.name, path.read_text(encoding='utf-8'))
            for path in sorted(directory.glob('*.csv'))]


def docstring_bullets(heading, ends):
    """The names the module docstring's bullet list under `heading` opens with.

    Both closed lists are restated in prose and the suite holds the two copies
    to each other by name, so an entry added to one and not the other is named
    rather than showing up as a changed count. The section is bounded at `ends`
    because one split is not enough: the shapes and the declines are both
    ``  * `name` -- `` openers, so an unbounded read would find the declines
    under the shapes too and every comparison would pass for the wrong reason.

    The opener pattern is anchored on the backticked name because the docstring
    has other bullet lists that open ``  * *italic* `` instead, and a looser
    pattern would read prose that is not claiming to be an entry in either list.
    """
    body = ctgc.__doc__.split(heading, 1)[1].split(ends, 1)[0]
    return re.findall(r"^  \* `([^`]+)`(?: --|\b)", body, re.M)


class ScratchIndex:
    """A throwaway `testdata/` holding real fixtures and an index over them.

    One cell per row, because a case here is about a sentence and a second row
    would only be a second thing to keep true. `note` is the third column
    verbatim, which is the point: the cell is the unit under test and not a
    paraphrase of it.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.testdata = os.path.join(self.root, "testdata")
        os.mkdir(self.testdata)
        self.rows = []

    def fixtures(self, name):
        """Copy a committed fixture set into the scratch tree and return its
        glob token."""
        for base, text in committed(name):
            path = os.path.join(self.testdata, name, base)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        return f"{name}/*.csv"

    def row(self, cell, note, feeds=FEEDS):
        """Add one table row naming `cell` and describing it with `note`."""
        self.rows.append(f'| `{cell}` | {feeds} | {note} |')
        return self

    def write(self, rel, text):
        """Create `rel` under the scratch `testdata/`, parents and all."""
        path = os.path.join(self.testdata, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def check(self):
        """The tool's `Result` for this scratch tree.

        The index is written to disk rather than handed in, because the tool
        reads it from `testdata/README.md` and a case that bypassed that would
        be testing a reader no run ever uses.
        """
        self.write("README.md", HEADER + "".join(r + "\n" for r in self.rows))
        return ctgc.check(self.testdata)

    def verdicts(self):
        """[(shape, verdict)] for this scratch tree, in reading order.

        A list rather than a dict because a row carrying two claims of the same
        shape is a real case -- row 34 states two block verdicts in one cell --
        and a dict would collapse them into one and hide which of the two was
        the disagreement.
        """
        return [(c.shape, c.verdict) for c in self.check().claims]

    def shapes(self):
        """The shapes read, in reading order."""
        return [shape for shape, _ in self.verdicts()]

    def reasons(self):
        """The decline reasons this scratch tree produced, in reading order."""
        return [reason for _, reason, _, _ in self.check().declines]


class ReadsTheReport(ScratchIndex, unittest.TestCase):
    """The shapes, each with a case that decides it against a real run."""

    def test_a_note_constant_is_formatted_with_the_numbers_the_row_states(self):
        self.row(self.fixtures(UNPLACED),
                 "the only committed run that reaches the "
                 "`elif graded_unplaced:` branch, and so the only one to print "
                 "`UNPLACED_GRADED_NOTE` at `2 of the 8`.")
        self.assertEqual(self.verdicts(), [("note printed", "resolved")])

    def test_a_note_constant_at_the_wrong_numbers_is_missing(self):
        # The whole of the shape, and the failure it exists for: the note
        # *text* is printed, so a rule that tested the token rather than the
        # formatted constant would stay green. `grade.UNPLACED_GRADED_NOTE` is
        # the right-hand side and the row's numbers fill it.
        self.row(self.fixtures(UNPLACED),
                 "the only one to print `UNPLACED_GRADED_NOTE` at `5 of the 8`.")
        self.assertEqual(self.verdicts(), [("note printed", "missing")])

    def test_a_withheld_note_must_be_absent_from_a_scoped_run(self):
        # Row 29's own claim, and the direction that makes it worth holding: the
        # note is printed over the unscoped run and unreachable under `--block`,
        # so the same constant is `note printed` in one run and `note withheld`
        # in the other. The scope is carried forward from the `--block 0xA0` the
        # sentence opens with, which is what lets one row make both statements.
        self.row(self.fixtures(UNPLACED),
                 "a `--block 0xA0` run over it is what shows why: the per-block "
                 "sentence prints, the count line and `UNREAD_MARK_NOTE` do not, "
                 "exit 0.")
        result = self.check()
        shapes = [c.shape for c in result.claims]
        self.assertIn("note withheld", shapes)
        withheld = next(c for c in result.claims if c.shape == "note withheld")
        self.assertEqual(withheld.verdict, "resolved")

    def test_a_withheld_note_is_decided_against_the_run_its_sentence_names(self):
        # **The false green this scope rule exists to close**, and it is a
        # mutation of the run rather than of the rule: `UNREAD_MARK_NOTE` is
        # absent from the whole-capture run over `unplaced-window/` too, because
        # that run reaches the `graded_unplaced` branch. So reading the claim
        # against the *unscoped* run finds it absent, records `resolved`, and the
        # `--block 0xA0` run the sentence names is never made at all.
        #
        # **Only the scoped run is given the note**, which is what makes this a
        # test of the scope and not of the absence: injecting it into every run
        # would flip the claim under the old reading too, so the case would pass
        # for a reason that has nothing to do with which run was graded.
        self.row(self.fixtures(UNPLACED),
                 "a `--block 0xA0` run over it is what shows why: the per-block "
                 "sentence prints, the count line and `UNREAD_MARK_NOTE` do not, "
                 "exit 0.")
        real = ctgc.run_grader

        def printing_note(paths, block=None):
            code, out = real(paths, block)
            if block is None:
                return code, out
            return code, out + "\n" + ctgc.grade.UNREAD_MARK_NOTE

        with mock.patch.object(ctgc, 'run_grader', printing_note):
            result = self.check()
        withheld = next(c for c in result.claims if c.shape == "note withheld")
        self.assertEqual(withheld.verdict, "missing")

    def test_a_scope_named_earlier_in_the_sentence_reaches_the_claims_behind_it(self):
        # The same defect on row 30, whose `intact` and `exits 1` sit behind a
        # `--block 0xA0` the sentence names once. Both are decidable and both
        # were read against the whole-capture run, so the `--block` run was never
        # made over this set either. Changing what that run prints must move
        # them.
        self.row(self.fixtures(UNREAD),
                 "so a `--block 0xA0` run of this set prints that block's three "
                 "windows, `intact`, and exits 1.")
        real = ctgc.run_grader

        def different(paths, block=None):
            code, out = real(paths, block)
            if block is not None:
                return 7, out.replace("intact", "VOID")
            return code, out

        with mock.patch.object(ctgc, 'run_grader', different):
            result = self.check()
        verdicts = {c.shape: c.verdict for c in result.claims}
        self.assertEqual(verdicts["exit code"], "missing")
        self.assertEqual(verdicts["block verdict"], "missing")

    def test_a_scope_is_not_carried_across_a_sentence_that_names_none(self):
        # The other side of carrying a scope forward, and what keeps it from
        # becoming a row-wide default: a sentence naming no `--block` value is
        # about what a *whole-capture* run prints, so its counts are read
        # unscoped. **Two sentences in one cell, the first scoped and the second
        # not**, which is the shape that separates carrying a scope forward
        # *within* a sentence from carrying it across the row -- and row 30's own
        # cell is exactly this. The scope is per sentence because `claims_in()`
        # is handed one sentence at a time, so the boundary is structural; what
        # this pins is that the counts behind the unscoped sentence are still
        # **decided** rather than left undecided, which is what reading them
        # against the previous sentence's scoped run would do -- `withheld_pair()`
        # cannot read a scoped banner at all.
        self.row(self.fixtures(UNREAD),
                 "a `--block 0xA0` run of this set prints that block's three "
                 "windows. The withheld banner's `1 of the 8` against the count "
                 "line's `1 of the 7`.")
        result = self.check()
        counts = {c.shape: c.verdict for c in result.claims
                  if c.shape in ("withheld banner count", "unplaced note count")}
        self.assertEqual(counts, {"withheld banner count": "resolved",
                                  "unplaced note count": "resolved"})
        self.assertNotIn("unresolved", [c.verdict for c in result.claims])

    def test_a_withheld_note_that_the_run_prints_is_missing(self):
        # The other direction, and the only one that can be wrong on a row that
        # reads correctly: the same sentence with no scope reads an unscoped run,
        # which prints the note, so claiming it absent has to be red.
        self.row(self.fixtures(UNREAD),
                 "the per-block sentence prints, the count line and "
                 "`UNREAD_MARK_NOTE` do not.")
        self.assertEqual(self.verdicts(), [("note withheld", "missing")])

    def test_a_withheld_banner_count_is_read_off_the_banner_line(self):
        # `2 withheld of 8` is not the tool's spelling, so the right-hand side
        # is the counts the run printed in front of `grade.WITHHELD_REASON`
        # rather than a substring of the sentence. Row 31's own.
        self.row(self.fixtures(MOVED),
                 "so the 2 withheld of 8 are the strays and nothing else.")
        self.assertEqual(self.verdicts(), [("withheld banner count", "resolved")])

    def test_a_withheld_banner_count_at_the_wrong_numbers_is_missing(self):
        self.row(self.fixtures(UNREAD),
                 "so the 3 withheld of 8 are the strays and nothing else.")
        self.assertEqual(self.verdicts(), [("withheld banner count", "missing")])

    def test_two_counts_in_one_sentence_are_read_for_two_contexts(self):
        # The issue's condition on the whole direction, and the reason the
        # context is the closed entry rather than the number: row 30 writes both
        # counts in one sentence, "the withheld banner's `1 of the 8` against the
        # count line's `1 of the 7`", and **the two denominators differ**. A rule
        # that read one `N of the M` stem for both would find the same pair in
        # both claims and pass the sentence it was written to make
        # disqualifiable.
        self.row(self.fixtures(UNREAD),
                 "the only one whose two counts are taken over different "
                 "denominators — the withheld banner's `1 of the 8` against the "
                 "count line's `1 of the 7`.")
        self.assertEqual(self.verdicts(),
                         [("withheld banner count", "resolved"),
                          ("unplaced note count", "resolved")])

    def test_an_exit_code_is_read_from_the_return_not_from_the_report(self):
        self.row(self.fixtures(UNREAD),
                 "a `--block 0xA0` run of this set prints that block's three "
                 "windows, `intact`, and exits 1.")
        self.assertIn(("exit code", "resolved"), self.verdicts())

    def test_an_exit_code_the_run_does_not_return_is_missing(self):
        # `unplaced-window/` is the same day byte for byte with one label made
        # readable and exits 0, so the same sentence over the other set is the
        # disagreement -- and it is a claim about the grader, which is the whole
        # of what this tool reads.
        self.row(self.fixtures(UNPLACED),
                 "a `--block 0xA0` run of this set prints that block's three "
                 "windows, `intact`, and exits 1.")
        self.assertIn(("exit code", "missing"), self.verdicts())

    def test_a_block_verdict_is_matched_case_insensitively(self):
        # The index writes `(void)` where the tool prints `VOID`. A case
        # difference held as a disagreement would be a spelling failure dressed
        # up as a claim about the grader, so both sides are folded.
        self.row(self.fixtures(REDONE),
                 "one value is the value under test of two blocks: `0x00`, in "
                 "`block 2 of 4` (void) and `block 4 of 4` (intact).")
        self.assertEqual(self.verdicts(),
                         [("block verdict", "resolved"),
                          ("block verdict", "resolved")])

    def test_a_block_verdict_the_run_prints_differently_is_missing(self):
        self.row(self.fixtures(REDONE),
                 "`0x00`, in `block 2 of 4` (intact) and `block 4 of 4` (intact).")
        self.assertEqual(self.verdicts(),
                         [("block verdict", "missing"),
                          ("block verdict", "resolved")])

    def test_a_window_count_is_read_from_the_headers_a_run_printed(self):
        # Row 30's own, and the reason the verb is inside the token: this row
        # also says "the two windows in no block", which is about the fixture.
        self.row(self.fixtures(UNREAD),
                 "so a `--block 0xA0` run of this set prints that block's three "
                 "windows.")
        self.assertEqual(self.verdicts(), [("window count", "resolved")])

    def test_a_window_count_the_run_did_not_print_is_missing(self):
        self.row(self.fixtures(UNREAD),
                 "so a `--block 0xA0` run of this set prints that block's five "
                 "windows.")
        self.assertEqual(self.verdicts(), [("window count", "missing")])

    def test_a_count_written_against_a_note_constant_is_not_a_second_claim(self):
        # "`UNPLACED_GRADED_NOTE` at `2 of the 8`" is one claim under two
        # tokens. Reading the count separately would check the sentence twice
        # and report a second answer for it, and against the banner rather than
        # against the note the numbers belong to. **The decline list is asserted
        # empty as well as the shapes**, because the count's clause is " at " and
        # it names neither context: without this rule it would land in the
        # census as a `no closed shape` on a sentence that was read in full.
        self.row(self.fixtures(UNPLACED),
                 "the only one to print `UNPLACED_GRADED_NOTE` at `2 of the 8`.")
        result = self.check()
        self.assertEqual(self.shapes(), ["note printed"])
        self.assertEqual(result.declines, [])

    def test_a_token_after_a_note_is_still_a_claim(self):
        # **The silent drop this is the other side of.** Dropping whatever
        # followed a note took the `exit 0` out of row 29's own sentence --
        # "`UNREAD_MARK_NOTE` do not, exit 0" -- with it: an `exit code` claim,
        # decidable, whose right-hand side is the run's own return code. It
        # reached neither `claims` nor `declines`, so the census gave a reader no
        # way to know a supported claim was never looked at. The rule is now
        # narrowed to the count it was written for, and every other shape after a
        # note is read.
        self.row(self.fixtures(UNPLACED),
                 "a `--block 0xA0` run over it is what shows why: the per-block "
                 "sentence prints, the count line and `UNREAD_MARK_NOTE` do not, "
                 "exit 0.")
        shapes = self.shapes()
        self.assertIn("exit code", shapes)
        result = self.check()
        exit_claims = [c for c in result.claims if c.shape == "exit code"]
        self.assertEqual([c.verdict for c in exit_claims], ["resolved"])
        # And the exit code the sentence states is load-bearing, not merely
        # emitted: the same sentence against a set that exits 1 disagrees.
        self.row(self.fixtures(UNREAD),
                 "the count line and `UNREAD_MARK_NOTE` do not, exit 0.")
        self.assertIn(("exit code", "missing"), self.verdicts())

    def test_a_count_after_a_note_is_the_only_shape_dropped(self):
        # The rule as narrowed, stated as a census of the shapes it touches
        # rather than as the behaviour of one sentence: of the tokens in a cell
        # naming a note, the `N of the M` beside it is read as the note's own
        # numbers and nothing else goes.
        cell = ("the only one to print `UNPLACED_GRADED_NOTE` at `2 of the 8`, "
                "and it exits 0.")
        shapes = [shape for shape, _, _, _ in ctgc.claims_in(cell)]
        self.assertEqual(shapes, ["note", "exit"])

    def test_a_count_about_another_line_behind_a_note_is_still_read(self):
        # **The direction the adjacency rule got wrong.** Naming a note and then
        # stating a *different* counted line's count is one row, two claims, and
        # the count is the second of them: "the withheld banner's `1 of the 8`"
        # is the banner's to be decided against whatever note the sentence
        # mentioned earlier. Read as adjacency the count went unread, and
        # `nearest_count()` then formatted the note with the banner's numbers --
        # so the row reported a disagreement against a sentence that was
        # correct, on an ordinary reword and with no fixture touched.
        self.row(self.fixtures(UNREAD),
                 "a run of this set prints `UNREAD_MARK_NOTE`, and the withheld "
                 "banner's `1 of the 8` is what this one prints.")
        self.assertEqual(self.verdicts(),
                         [("note printed", "resolved"),
                          ("withheld banner count", "resolved")])

    def test_a_note_is_not_formatted_with_another_claims_count(self):
        # The other half of the same rule, and the one that made the row above
        # red rather than merely unread. The note and the count are separate
        # claims, so the note cannot borrow the count's numbers: formatted with
        # `1 of the 8` the note is looked for in a spelling the run never
        # printed, which is a disagreement invented out of a true row. With no
        # count written against it the note is undecided, and undecided is what
        # "not checked, not absent" is for.
        sentence = ("`UNREAD_MARK_NOTE` is named here, and the withheld "
                    "banner's `1 of the 8` is what this one prints.")
        note = next(row for row in ctgc.claims_in(sentence) if row[0] == "note")
        self.assertIsNone(ctgc.nearest_count(note[2], note[3], sentence))

    def test_a_count_naming_no_line_but_following_no_note_is_still_its_own_claim(self):
        # The other half of the other half. A count that names no counted line
        # is the note's numbers *only when a note is written beside it*; with
        # no note, it is a claim of its own and declines as `no closed shape`
        # rather than being read as some note's numbers.
        cell = "a run of this set states `2 of the 8` and nothing else."
        self.row(self.fixtures(UNPLACED), cell)
        self.assertEqual(self.shapes(), [])
        self.assertEqual(self.reasons(), ["no closed shape"])

    def test_a_note_constant_given_a_count_it_has_no_field_for_is_undecided(self):
        # `UNREAD_MARK_NOTE` takes no numbers, so a row that states one beside it
        # is a claim this tool cannot read -- `unresolved`, not a `KeyError` out
        # of `str.format` and not a claim checked against the wrong text.
        self.row(self.fixtures(UNREAD),
                 "the only one to print `UNREAD_MARK_NOTE` at `2 of the 8`.")
        self.assertEqual(self.verdicts(), [("note printed", "unresolved")])


class DeclinesRatherThanGuesses(ScratchIndex, unittest.TestCase):
    """Every entry of the closed decline list, each with the case that is it.

    None of these fails the run, which is the sibling's own discipline: a
    checker that reported its own parser's blind spot as a broken index would be
    pushed to grow a rule for whatever it could not read. What each case pins is
    that the claim is *named* rather than silently passed over or decided
    wrongly.
    """

    def test_a_claim_about_another_rows_fixture_is_declined(self):
        # Row 30's "exits 0", which is about `unplaced-window/`. The reference
        # sits in front of the claim and the claim is about the other set.
        self.row(self.fixtures(UNREAD),
                 "a `--block 0xA0` run of this set prints `intact` and exits 1 "
                 "— and `unplaced-window/`, the same day byte for byte with one "
                 "label made readable, exits 0.")
        # One claim read and one declined: the `exits 1` is about this row's set
        # and the `exits 0` is about `unplaced-window/`, and what tells them
        # apart is the reference sitting in front of the second.
        self.assertEqual(self.reasons(), ["another row's fixture"])
        self.assertEqual(self.shapes(), ["block verdict", "exit code"])

    def test_a_reference_in_an_earlier_clause_does_not_reach_the_claim(self):
        # The other side of the same rule, and the coverage it protects: a
        # whole-sentence test would decline this claim too, because the sentence
        # names another set. `clause_of()` is what tells the two apart.
        self.row(self.fixtures(MOVED),
                 "`3blocks/` above prints the same banner and takes the "
                 "withheld branch above it instead: the 2 withheld of 8 are the "
                 "strays and nothing else.")
        self.assertEqual(self.verdicts(),
                         [("withheld banner count", "resolved")])

    def test_a_row_fed_to_another_grader_is_declined(self):
        self.row(self.fixtures(UNREAD),
                 "a `--block 0xA0` run of this set exits 1.",
                 feeds='`../grade_gpu_door.py`')
        self.assertEqual(self.reasons(), ["not this grader's row"])

    def test_a_row_naming_no_capture_is_declined(self):
        self.write("pair/before.txt", "0780: 10\n")
        self.row("pair/before.txt", "a `--block 0xA0` run over it exits 1.")
        self.assertEqual(self.reasons(), ["no capture in the row's file set"])

    def test_a_withheld_count_in_a_scoped_run_is_declined(self):
        # A `--block` run spells the banner with three numbers and a different
        # question, so a count against it is declined rather than read against a
        # substring that would answer something else.
        self.row(self.fixtures(UNREAD),
                 "a `--block 0xA0` run of this set has 1 withheld of 8.")
        self.assertEqual(self.reasons(),
                         ["withheld count not in whole-capture spelling"])

    def test_a_count_against_the_movement_line_is_declined(self):
        # No module constant identifies that line, so deciding it would mean
        # re-deriving the grader's prose here and holding the copy to it.
        self.row(self.fixtures(UNREAD),
                 "one of the 6 that were graded moved.")
        self.assertEqual(self.reasons(), ["movement restatement"])

    def test_a_count_whose_context_names_neither_line_is_declined(self):
        # The entry that makes the closed list closed: without it a count the
        # tool cannot place would be reported under a token name that is not a
        # decline, which is the shape of a silent cap.
        self.row(self.fixtures(UNREAD), "the `2 of the 8` figure, for the record.")
        self.assertEqual(self.reasons(), ["no closed shape"])

    def test_a_note_claim_about_another_rows_fixture_is_declined_not_decided(self):
        # The two orders the tool could resolve these in, told apart by a claim
        # that is both. Asking the shape first would read this as `note
        # withheld` and then grade *this* row's set for it, which finds the note
        # present and records a `missing` against a sentence that is true about
        # `unplaced-window/`. The declines run first for that reason, and this is
        # the case that holds them there.
        self.row(self.fixtures(UNREAD),
                 "and `unplaced-window/` below prints `UNREAD_MARK_NOTE` where "
                 "this run does not.")
        result = self.check()
        self.assertEqual(self.reasons(), ["another row's fixture"])
        self.assertEqual(result.claims, [])

    def test_a_scoped_runs_banner_answers_no_whole_capture_count(self):
        # `withheld_pair()` reads only the whole-capture spelling, and what makes
        # that unambiguous is the "above were not graded" the scoped spelling does
        # not carry -- it prints "of this block (N of the capture's K window(s))"
        # instead, which is three numbers and a different question. Widening the
        # pattern to `N of the M window(s)` would make a scoped run answer a
        # whole-capture question, so the reading is pinned here rather than
        # through a claim: the `withheld count not in whole-capture spelling`
        # decline stops a scoped claim before it ever reaches this function, and
        # a pinned reader is the only way the pattern itself is held.
        #
        # `missing-mark/` is the set that withholds every window, so its scoped
        # run does print the banner; `unread-window/` withholds one window that a
        # `--block` run does not show, and would not exercise the pattern at all.
        for name, expected in ((UNREAD, (1, 8)), (MISSING, (3, 3))):
            paths = [os.path.join(HERE, 'testdata', name, base)
                     for base, _ in committed(name)]
            self.assertEqual(ctgc.withheld_pair(ctgc.run_grader(paths)[1]),
                             expected, name)
            self.assertIsNone(
                ctgc.withheld_pair(ctgc.run_grader(paths, '0xA0')[1]), name)

    def test_a_note_constant_and_a_count_that_cannot_fill_it_are_undecided(self):
        # `note_text()`'s contract, pinned directly rather than through a claim,
        # because the corpus cannot reach the mismatch: `COUNT_PAIR` always
        # yields two numbers and `UNPLACED_GRADED_NOTE` is the only constant with
        # fields, so the arity check is defensive. What it protects is that a
        # wrong-arity pair is `None` -- a `KeyError` out of `str.format` would
        # take the whole census down over one sentence.
        self.assertIsNone(ctgc.note_text("UNPLACED_GRADED_NOTE", (2,)))
        self.assertIsNone(ctgc.note_text("UNPLACED_GRADED_NOTE"))
        # And the other way round: a constant with no fields cannot take a count
        # at all, so one stated beside it is undecided rather than read against
        # the constant's bare text.
        self.assertIsNone(ctgc.note_text("UNREAD_MARK_NOTE", (2, 8)))
        self.assertEqual(ctgc.note_text("UNREAD_MARK_NOTE"),
                         ctgc.grade.UNREAD_MARK_NOTE)

    def test_every_decline_leaves_the_run_green(self):
        self.row(self.fixtures(UNREAD), "one of the 6 that were graded moved.")
        result = self.check()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ctgc.report(result), 0)


class TheRefusalClauseIsNeverAClaim(ScratchIndex, unittest.TestCase):
    """The exclusion, kept apart from the declines.

    A rule that reached one of these clauses would turn the run red by
    construction -- a different failure from a row this tool cannot read, which
    is why the two are counted on separate lines. **A row need not carry one at
    all**, and a row may carry two: the clauses and the rows are two independent
    counts that agree only where the tree happens to make them, so nothing here
    asserts the distribution or the total. What is asserted is the property that
    is true of any tree -- a clause that is there is never read, and a row
    carrying none is not an error.
    """

    def test_a_count_inside_a_refusal_clause_is_not_read(self):
        self.row(self.fixtures(UNREAD),
                 "A capture in which nothing moves. It is *not* a prediction "
                 "that the withheld banner reads `7 of the 9`.")
        result = self.check()
        self.assertEqual(result.claims, [])
        self.assertEqual(result.declines, [])
        self.assertEqual(result.stripped, 1)

    def test_the_clause_is_cut_and_what_precedes_it_is_kept(self):
        # Row 23 keeps going after its refusal, and the sentence before it is
        # not a refusal -- so the cut is at the clause and not at the sentence.
        self.row(self.fixtures(UNREAD),
                 "Both blocks come out `intact`. It is *not* a prediction "
                 "that a re-run produces it.")
        result = self.check()
        self.assertEqual([c.shape for c in result.claims], ["block verdict"])
        self.assertEqual(result.stripped, 1)

    def test_the_counted_refusals_are_not_claims_either(self):
        # Every row's clause counted, and none of them reaches a rule: this is
        # the assertion that the exclusion is what keeps the run green, not the
        # absence of a matching shape.
        result = ctgc.check()
        self.assertGreater(result.stripped, 0)
        self.assertEqual(result.missing, 0)

    def test_a_row_carrying_no_refusal_clause_is_not_an_error(self):
        # **The "red by construction" argument does not hold row-wide**, and this
        # is what that means: a row carrying no refusal clause has nothing for a
        # rule to reach, so it was never what kept the run green. It is a row
        # like any other, and the census counts what was stripped rather than
        # asserting one per row.
        self.row(self.fixtures(UNREAD),
                 "the withheld banner's `1 of the 8` against the count line's "
                 "`1 of the 7`.")
        result = self.check()
        self.assertEqual(result.stripped, 0)
        self.assertTrue(result.claims)
        self.assertEqual(result.missing, 0)

    def test_a_row_carrying_two_refusal_clauses_counts_both(self):
        # The other end of the distribution, and why the total is not a row
        # count: `strip_refusal()` cuts at the clause so a row that keeps going
        # after its refusal has both halves read, and a row carrying a second
        # refusal in a sentence of its own is counted twice. What is counted is
        # sentences carrying one, which is what makes the sum independent of the
        # row count.
        self.row(self.fixtures(UNREAD),
                 "It is *not* a prediction that `intact` holds. It is *not* a "
                 "prediction that a re-run prints `7 of the 9`.")
        result = self.check()
        self.assertEqual(result.stripped, 2)
        self.assertEqual(result.claims, [])
        self.assertEqual(result.declines, [])

    def test_the_clause_count_is_not_a_row_count(self):
        # What stops the two census figures being read as one number: the
        # stripped count is a **sum taken over rows**, so every cell has to read
        # before it can be added up at all. Both totals are printed beside each
        # other for exactly this reason, and neither is a floor this tool holds
        # itself to.
        #
        # `refusal_count()` is pinned against cells this case writes, with the
        # answer in the sentence: it counts clauses, so a row carrying none and
        # a row carrying two are both correct answers and a function returning
        # `0` for everything would pass a truthiness assertion over the index.
        # What the committed tree's rows carry is **not** asserted -- that is a
        # property of this tree, and a reword that moved a clause would break a
        # property of the *index* rather than of the tool.
        # `docs/findings/testdata-grader-claims.md` is where the measurement
        # over the committed tree is recorded, next to the command that prints
        # it, for the reason nothing in the tool or its suite asserts it.
        self.assertEqual(ctgc.refusal_count(
            "a first sentence. a second sentence."), 0)
        self.assertEqual(ctgc.refusal_count(
            "it holds. It is *not* a prediction that it slips."), 1)
        self.assertEqual(ctgc.refusal_count(
            "one refusal here. It is *not* a prediction that it slips. "
            "another there. It is *not* a prediction that the other does "
            "either."), 2)


class TheClosedListsHoldTheDocstring(unittest.TestCase):
    """Both closed lists, and the two prose copies of them.

    An entry in the constant and not in the docstring is a limit the tool has
    that a reader cannot see; an entry in the docstring and not the constant is
    prose claiming to be a shape that no rule reaches. Neither shows up as a
    changed count, which is why the comparison is by name in both directions.
    """

    def test_every_shape_is_the_docstrings_bullet(self):
        self.assertEqual(
            set(docstring_bullets("Shapes -- read and decided",
                                  "Declines -- counted")),
            set(ctgc.SHAPES),
            "a shape in the constant and not in the docstring, or the other way "
            "around")

    def test_every_decline_is_the_docstrings_bullet(self):
        self.assertEqual(
            set(docstring_bullets("Declines -- counted", "Usage:")),
            set(ctgc.DECLINES),
            "a decline in the constant and not in the docstring, or the other "
            "way around")

    def test_every_note_is_the_graders_own(self):
        # The closed list is what stops the tool reading any all-caps token as a
        # claim, and it can only do that if every name in it is still a string on
        # the grader. A rename there would otherwise leave this tool quietly
        # reading nothing -- a green run, a claim no longer checked -- which is
        # the failure mode the suite exists for, one level down from the one
        # issue #978 measured.
        for name in ctgc.NOTES:
            self.assertIsInstance(getattr(ctgc.grade, name, None), str,
                                  f"{name} is not a module-level string on "
                                  f"the grader")

    def test_the_committed_tree_exercises_every_shape(self):
        # Each shape has an instance in the committed index, so none of the list
        # is an entry the tool has rather than one it has reached.
        reached = {claim.shape for claim in ctgc.check().claims}
        self.assertEqual(set(ctgc.SHAPES) - reached, set(),
                         "these shapes have no instance in the committed index")


class TheCommittedTree(ScratchIndex, unittest.TestCase):
    """The last class is the committed tree itself, and it asserts nothing about
    how big it is."""

    def test_the_committed_index_agrees_with_the_grader(self):
        # The run that proves the tool is useful today, and the one the write-up
        # quotes: every claim the third column makes about the grader's own
        # output agrees with what the tool printed. A disagreement here is a
        # defect in the index's prose and not a reason to change a fixture or to
        # loosen a rule.
        result = ctgc.check()
        self.assertEqual(result.missing, 0,
                         "\n".join(ctgc.claim_line(c) for c in result.claims
                                   if c.verdict == "missing"))

    def test_the_run_reached_something(self):
        # Non-emptiness, never a floor: a row that gains no claim and a fixture
        # set that gains a row both have to leave this green, because a count of
        # the tree is a value every merge has to edit.
        self.assertTrue(ctgc.check().claims)

    def test_the_census_names_every_row(self):
        # Every row of the index is either carrying a claim or not, and the
        # report says which -- the repository's rule against silent caps, and
        # the half a reader needs because the answer is a mix.
        result = ctgc.check()
        carrying = {claim.row for claim in result.claims}
        self.assertTrue(carrying)
        self.assertTrue(all(1 <= row <= result.rows for row in carrying))
        self.assertEqual(len(carrying), result.claiming_rows)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ctgc.decline_report(result)
        text = out.getvalue()
        for shape in ctgc.SHAPES:
            self.assertIn(shape, text)
        for reason in ctgc.DECLINES:
            self.assertIn(reason, text)

    def test_a_row_with_no_claim_does_not_fail(self):
        # The no-red-by-construction case: a row whose description says nothing
        # about what the grader prints is not an error, and a run that turned
        # one red would have to be edited every time a row was reworded.
        self.row(self.fixtures(UNPLACED), "A quiet capture, for a reader to "
                                          "grade by hand.")
        result = self.check()
        self.assertEqual(result.claims, [])
        self.assertEqual(result.missing, 0)

    def test_a_new_row_does_not_fail(self):
        self.row(self.fixtures(UNREAD), "A second set, described in prose.")
        self.row(self.fixtures(UNPLACED), "A third set, described in prose.")
        self.assertEqual(self.check().missing, 0)

    def test_the_run_is_independent_of_the_order_it_is_driven_in(self):
        # The grader is driven in-process once per claim, so grading the same
        # set twice has to give the same answer -- and reading the rows in a
        # different order has to give the same answers too. That is the one
        # property that makes the in-process choice correct, so it is pinned
        # rather than assumed.
        #
        # The reversal moves **every column of the row together**, so each keeps
        # its own fixture set and its own `Feeds` cell: reversing the
        # descriptions alone would re-pair them and test something else.
        once = ctgc.check()
        twice = ctgc.check()
        self.assertEqual([(c.row, c.shape, c.verdict) for c in once.claims],
                         [(c.row, c.shape, c.verdict) for c in twice.claims])

        original = ctgc.table_cells

        def reversed_rows(index, column=1):
            found = original(index, column)
            return list(reversed(found))

        with mock.patch.object(ctgc, 'table_cells', reversed_rows):
            flipped = ctgc.check()
        self.assertEqual(sorted((c.shape, c.verdict) for c in flipped.claims),
                         sorted((c.shape, c.verdict) for c in once.claims))
        self.assertEqual(flipped.stripped, once.stripped)
        self.assertEqual(flipped.missing, once.missing)

    def test_the_grader_binds_no_module_name_while_it_runs(self):
        # What makes the repetition above safe, read off the module rather than
        # asserted about it: no `global` statement anywhere in the grader, so
        # grading a set cannot rebind a module-level name and make the next run
        # answer differently. `GROUP_NOTE` is the one module-level mapping it
        # reads, and this is the case that would go red if a caller ever wrote
        # to it.
        source = (HERE / 'grade_0751_isolation.py').read_text(encoding='utf-8')
        self.assertIsNone(re.search(r"^\s*global\s", source, re.M))
        self.assertIn("note = GROUP_NOTE.get(name)", source)

    def test_the_closing_line_names_the_index_the_run_read(self):
        result = ctgc.check()
        self.assertIn(os.path.join('ec', 'tools', 'testdata', 'README.md'),
                      ctgc.closing_line(result))
        # The root is carried on the `Result` rather than read off a module
        # constant, so a scratch run cannot print the committed path for a tree
        # it never opened.
        self.assertNotIn(ctgc.closing_line(result),
                         ctgc.closing_line(self._scratch_result()))

    def _scratch_result(self):
        self.row(self.fixtures(UNPLACED), "the only one to print "
                                          "`UNREAD_MARK_NOTE`, and it does not.")
        return self.check()

    def test_a_run_that_refused_agrees_with_nothing(self):
        # A refusal prints almost nothing, so a `note withheld` claim over one
        # would otherwise find its constant absent and record a green no
        # capture set earned. This is the case that rule exists for.
        self.row(self.fixtures(UNREAD),
                 "`UNREAD_MARK_NOTE` does not print.")
        with mock.patch.object(ctgc, 'run_grader',
                               return_value=(1, "--block '`' is not a value")):
            result = self.check()
        self.assertEqual([c.verdict for c in result.claims], ["unresolved"])
        self.assertEqual(result.missing, 0)


class EachRuleIsLoadBearing(unittest.TestCase):
    """Each of the rules below, dropped in turn, against the committed tree.

    A rule that stops changing the answer has stopped mattering, and a suite
    that does not notice has the same defect as a check that does not fire. Each
    loosening is asserted to change the run and is asserted against the run as
    shipped rather than against a figure, so a fixture row added to the index
    later does not break any of them.

    **Several of the declines have no instance in the committed tree**, and
    saying so is part of this class: an entry nothing exercises is a limit the
    tool has rather than a shape it has reached, which is what the census line
    prints and what `test_the_committed_tree_exercises_every_shape` is the
    shapes-side of. Those are pinned in `DeclinesRatherThanGuesses` above, and
    the one exception is the declines this class does drop, where the committed
    tree has an instance to move.

    **This is not every rule the tool has, and the scope is named rather than
    implied.** The cases here loosen `clause_of()`, `UNPLACED_CONTEXT`,
    `nearest_count()`, `note_text()`, the refused-run guard, `scope_of()` and
    `scope_for()`, and each needs a committed-tree instance to move for the
    loosening to show. `WINDOW_HEADER`, `MOVEMENT`, `NEGATED`, `CLAUSE_BREAK`,
    `BLOCK_OF` and `numeral()` are loosened where they are load-bearing rather
    than here: `MOVEMENT` in `DeclinesRatherThanGuesses`; the window header, the
    block-verdict case fold and the numeral in `ReadsTheReport`; and the clause
    breaks and the negation in `TheRefusalClauseIsNeverAClaim` and
    `TheCommittedTree`. A rule with no case of its own is one whose removal this
    class would not notice, so those classes are the rest of the coverage and
    this one is not the whole of it.
    """

    def assert_the_rule_is_load_bearing(self, why, before, **patches):
        with mock.patch.multiple(ctgc, **patches):
            after = ctgc.check()
        self.assertNotEqual(
            [(c.row, c.shape, c.verdict) for c in after.claims]
            + [(n, r) for n, r, _, _ in after.declines],
            [(c.row, c.shape, c.verdict) for c in before.claims]
            + [(n, r) for n, r, _, _ in before.declines], why)

    def test_the_clause_the_claim_sits_in(self):
        # Without `clause_of()` every claim is read with the whole sentence
        # before it, which puts row 30's `exits 0` and its `exits 1` in one
        # unit and declines both -- or decides neither.
        before = ctgc.check()
        self.assert_the_rule_is_load_bearing(
            "reading a claim's whole prefix rather than its clause changes "
            "which claims are about another row's fixture",
            before, clause_of=lambda text: text)

    def test_the_context_the_two_counted_lines_are_told_apart_by(self):
        # `UNPLACED_CONTEXT` is what keeps "the count line's `1 of the 7` a
        # second count rather than a second reading of the first. Dropping it
        # sends row 30's `1 of the 7` to the withheld banner, where it
        # disagrees.
        before = ctgc.check()
        self.assert_the_rule_is_load_bearing(
            "one context regex for both counted lines cannot tell row 30's two "
            "denominators apart",
            before, UNPLACED_CONTEXT=ctgc.WITHHELD_CONTEXT)

    def test_a_count_against_a_note_constant_is_read_once(self):
        before = ctgc.check()
        with mock.patch.object(ctgc, 'nearest_count',
                               side_effect=lambda *a: (9, 9)):
            after = ctgc.check()
        self.assertNotEqual(
            [(c.row, c.shape, c.verdict) for c in after.claims],
            [(c.row, c.shape, c.verdict) for c in before.claims],
            "formatting every note constant with the same numbers changes no "
            "claim, so the number the row states is not load-bearing")

    def test_the_note_constants_are_the_graders_own(self):
        # The right-hand side is the grader's text rather than a copy of it, so
        # a note formatted from anything other than the constant stops being
        # checkable at all.
        before = ctgc.check()
        self.assert_the_rule_is_load_bearing(
            "a note constant read from anywhere but the grader module cannot "
            "agree with what the grader printed",
            before, note_text=lambda name, numbers=None: "a note")

    def test_the_refused_run_guard(self):
        # Without it a run that refused reads as one that printed nothing the
        # claim needed, which is a green no capture set earned.
        before = ctgc.check()
        self.assert_the_rule_is_load_bearing(
            "a refused run has to answer every claim `unresolved`",
            before, CENSUS=ctgc.re.compile("never printed"))

    def test_the_scope_a_claim_is_read_at(self):
        # `scope_of()` is what lets one row make a statement about an unscoped
        # run and another about a `--block` run. Without it every claim reads
        # the whole-capture report and row 29's `UNREAD_MARK_NOTE` claim flips.
        before = ctgc.check()
        self.assert_the_rule_is_load_bearing(
            "a claim about a scoped run has to be graded scoped",
            before, scope_of=lambda text: None)

    def test_the_scope_carried_forward_to_the_claims_behind_it(self):
        # `scope_for()` is what carries a `--block V` named earlier in the
        # sentence forward to the claims behind it, and what makes the decline
        # and the decision agree about which run a claim is about -- resolving it
        # twice let `decline_for()` read the clause and `check()` read the
        # window. Without it a claim whose own clause lost the scope at a `:` or
        # a `,` is read unscoped: for row 29's `UNREAD_MARK_NOTE` that is a green
        # no run earned, and for row 30's `intact` and `exits 1` it means the
        # scoped run is never made at all. The two cases in `ReadsTheReport`
        # above are this rule failing the other way.
        before = ctgc.check()
        self.assert_the_rule_is_load_bearing(
            "a `--block V` named earlier in the sentence has to reach the claims "
            "behind it, and the decline and the decision have to read it alike",
            before, scope_for=lambda body, match, after: None)