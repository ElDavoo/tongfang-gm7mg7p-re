#!/usr/bin/env python3
"""Offline checks for check_capture_names.py: committed files and a temp root.

The tool holds two properties of `evidence/ec-watch/` that nothing else on the
tree reads, and both were true on the day the dated-capture merge sized the
`<date>-*` glob by hand: every file in the root is dated in its own filename,
and the root is flat. A refusal nothing checks is a refusal with no teeth, so
the tripwires below are asserted on the committed root -- and they are
**tripwires, not floors**: a future capture that arrives unprefixed turns them
red, which is the point, and no count of files is asserted anywhere, so the
corpus is free to grow.

What is pinned on a scratch root is the half the committed tree cannot show,
because nothing in it is non-conforming today: both refusals firing, the two
vocabularies staying apart in the output as well as in the code, and the cost
each one carries -- stated as a demonstration against `captures_for()` and
`carried_by()` themselves rather than asserted in prose, so "this is a real
blind spot" is something a run shows rather than something a comment claims.

**The distinction this suite has to keep from blurring** is the one the
write-up's census turns on: how many files the run *reached* (6 of 15, because
it globs the dates the index names) is a different question from how many are
*reachable* (0 of 15, because a name with no prefix is out of every glob's
reach). A conforming capture no dated sentence mentions is reachable and
unreached, which is normal, and the second case below says so -- otherwise the
refusal's figure reads as an alarm about nine files and the tool gets widened
to "fix" a number that was never wrong.
"""
import contextlib
import glob
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).parent
# Loaded by path for the same reason `test_check_testdata_row_claims.py` loads
# its tool the same way, and the directory is the sys.path entry the tool's own
# `from check_capture_claims import WATCH` resolves against.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_capture_names', HERE / 'check_capture_names.py')
ccn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccn)

# The two readers of the dated-capture rule. The first is what the refusal is
# taken from; the second is what `check_testdata_row_claims.py` globs, loaded so
# the case below can ask whether a name and the glob that resolves it agree
# rather than asserting that they must.
spec = importlib.util.spec_from_file_location(
    'check_testdata_row_claims', HERE / 'check_testdata_row_claims.py')
ctrc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctrc)

# A file the glob can reach, and one it cannot. Spelled as the difference
# rather than as a list of good names, so a case that adds a third file has to
# say which side of the line it is on.
DATED = "2026-09-23-power-mode-cycle-0f00-0f5f.csv"
UNDATED = "power-mode-cycle-0f00-0f5f.csv"


class ScratchRoot(unittest.TestCase):
    """A throwaway capture root, and the census taken over it."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def capture(self, name, text=""):
        """A file at `name` under the scratch root, empty unless `text`."""
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as f:
            f.write(text)
        return self.root

    def directory(self, name):
        """A subdirectory at `name` -- the second premise, made by hand."""
        os.mkdir(os.path.join(self.root, name))
        return self.root

    def census(self):
        return ccn.census(self.root)

    def refused(self, where="scratch"):
        """The refusal list `report()` produces, with its output swallowed.

        The output is the point of the tool, so every case that wants the
        return value has to put the printing somewhere; doing it once here
        keeps each case from repeating the redirect and from having to care.
        """
        with contextlib.redirect_stderr(io.StringIO()) as err:
            problems = ccn.report(self.census(), where)
        return problems, err.getvalue()


class BothRefusals(ScratchRoot):
    """The two properties, each refused, and each refused in its own words."""

    def test_a_name_with_no_date_prefix_is_refused(self):
        self.capture(UNDATED)
        self.assertEqual(self.census().undated, [UNDATED])

    def test_a_subdirectory_in_the_root_is_refused(self):
        self.directory("2026-09-24-nested")
        self.assertEqual(self.census().directories, ["2026-09-24-nested"])

    def test_a_dated_name_and_a_flat_root_are_refused_for_nothing(self):
        self.capture(DATED)
        found = self.census()
        self.assertEqual((found.undated, found.directories), ([], []))

    def test_the_two_refusals_are_reported_in_separate_vocabularies(self):
        # The reason there are two loops in `report()` rather than one over a
        # merged list. A reader told only "2 problems" cannot tell which
        # premise stopped holding, and the two fixes are different: rename the
        # file, or move the directory's contents up beside their siblings.
        self.capture(UNDATED)
        self.directory("2026-09-24-nested")
        problems, err = self.refused()
        self.assertEqual(problems, [UNDATED, "2026-09-24-nested"])
        self.assertIn(f"scratch/{UNDATED}: carries no", err)
        self.assertIn(f"scratch/2026-09-24-nested: is not a file", err)
        # And neither message is the other's: the word a refusal is named by
        # appears in its own line and nowhere else, so a reader can grep for
        # one kind without finding the other.
        name_line, dir_line = err.splitlines()[0], err.splitlines()[1]
        self.assertNotIn("not a file", name_line)
        self.assertNotIn("prefix", dir_line)

    def test_each_refusal_names_what_it_costs_and_which_fix(self):
        # The useful half of "this is non-conforming" is not the rule but the
        # consequence, so both messages have to carry one. The second also has
        # to refuse the wrong fix by name: widening `captures_for()` to look
        # inside a directory is the change this exists to avoid. The first
        # refusal is spelled over the *prefix* and the second over the
        # `isfile` predicate `carried_by()` itself uses, which is why they can
        # be told apart by a single noun.
        self.capture(UNDATED)
        self.directory("2026-09-24-nested")
        _, err = self.refused()
        self.assertIn("no `<date>-*` glob reaches it", err)
        self.assertIn("Rename it to the day it was captured", err)
        self.assertIn("`carried_by()` skips it", err)
        self.assertIn("not a reason to widen `captures_for()`", err)

    def test_a_trailing_date_is_not_a_prefix(self):
        # The alternative this branch declined, pinned as a refusal rather than
        # left as prose. `captures_for()` builds `f"{date}-*"` and globs it, so
        # a file whose date is at the *end* of its name is out of its reach
        # exactly as an undated one is. Accepting a date in any position would
        # be a different rule, on a corpus where two dates in one filename are
        # ambiguous, and it belongs in its own issue with its own census.
        self.capture("power-mode-cycle-0f00-0f5f-2026-09-23.csv")
        self.assertEqual(self.census().undated,
                         ["power-mode-cycle-0f00-0f5f-2026-09-23.csv"])

    def test_a_lookalike_year_is_not_a_date(self):
        # The four-digit year is a shape, not a calendar, and the docstring
        # says so: `2026-99-99-` conforms. A checker that went on to decide
        # whether a named day exists would be answering a different question
        # from the one that keeps the glob honest, and would be the first thing
        # to break on a corpus carrying a hand-typed date.
        self.capture("2026-99-99-typo.csv")
        self.assertEqual(self.census().undated, [])

    def test_the_prefix_and_the_dated_glob_agree_in_both_directions(self):
        # The one case that needs both tools. `PREFIX` is the rule the refusal
        # is taken from and `captures_for()`'s `<date>-*` is what the premise
        # is for, so a drift between them would leave a file both reachable
        # and refused, or neither. Asserted as agreement over a scratch root's
        # two files rather than as a spelling, so it survives a reworded
        # pattern as long as the two still say the same thing.
        self.capture(DATED)
        self.capture(UNDATED)
        reached = ctrc.captures_for("the 2026-09-23 capture", self.root)
        self.assertEqual([os.path.basename(p) for p in reached[1]], [DATED])
        self.assertEqual(self.census().files, [DATED, UNDATED])
        self.assertEqual(self.census().undated, [UNDATED])


class WhatEachRefusalCosts(ScratchRoot):
    """The two failure modes, demonstrated rather than asserted.

    The issue's claim is that both premises are real and both are unchecked.
    That is a claim about what the neighbouring code *does*, so it is shown by
    running it: a run that stays green while checking less, and a run that goes
    red for a reason that has nothing to do with the prose. Neither is a
    hypothetical, and neither is a hardware or live claim -- the captures here
    are empty files and the only thing read is a name.
    """

    def test_a_capture_no_date_can_reach_is_one_the_run_never_checks(self):
        # The silent direction, and the reason the refusal is a refusal rather
        # than a warning. With the date's only capture unprefixed the glob
        # comes back empty, `captures_for()` reports `missing`, and the tool's
        # own vocabulary makes that `unresolved` -- "not checked by this
        # method, not absent" -- so the run stays green while covering strictly
        # less than it did. `check_testdata_row_claims.py`'s denominator line
        # is what makes that visible; this is the state it is visible in.
        self.capture(UNDATED)
        verdict, paths, dates = ctrc.captures_for(
            "the 2026-09-23 power-mode-cycle capture shows", self.root)
        # The third field is one `(glob, files)` pair per bare date the
        # sentence carries, rather than the single glob it was on the tree this
        # suite was written against: #979's two-date refusal reads all of them
        # so a skipped date is visible in the per-date block, and a sentence
        # naming one date is unaffected. The one date here is still keyed by
        # its own glob, which is the premise being demonstrated.
        self.assertEqual(dates, [("2026-09-23-*", [])])
        self.assertEqual(paths, [])
        self.assertEqual(verdict, ctrc.MISSING)
        self.assertEqual(self.census().undated, [UNDATED])

    def test_a_subdirectory_is_matched_by_the_glob_and_skipped_by_the_reader(self):
        # The red direction, and the sharper of the two, because it is the one
        # that produces a *disagreement* out of a directory. `glob.glob()`
        # returns a directory, so the date resolves; `carried_by()` skips
        # anything that is not a file, so nothing is read from the set it
        # resolved to; and the sentence's literal comes back `missing` -- a
        # verdict whose message sends a reader to fix the index's prose, which
        # is the wrong thing to go and fix.
        #
        # The address is written into a real file beside the directory, so the
        # case fails for the reason it claims: the claim is unsatisfiable
        # because the glob resolved to the wrong kind of thing, not because
        # there is no such address on disk. That is what separates this from
        # the unprefixed file above, where the correct answer is `unresolved`.
        self.directory("2026-09-23-power-mode-cycle")
        self.capture(UNDATED, "2026-01-01T12:02:00,0x0F58,0x00,0x01\n")
        verdict, paths, _ = ctrc.captures_for(
            "the 2026-09-23 capture shows `0x0F58`", self.root)
        self.assertEqual(verdict, ctrc.RESOLVED)
        self.assertEqual([os.path.basename(p) for p in paths],
                         ["2026-09-23-power-mode-cycle"])
        self.assertTrue(os.path.isdir(paths[0]))
        # The one file carrying the address, and the one the date resolved to.
        # The same reader over the same address, so the `False` below is
        # decidable as the glob having resolved to the wrong kind of thing and
        # not as the address being absent from the corpus.
        self.assertTrue(
            ctrc.carried_by("0x0F58", [os.path.join(self.root, UNDATED)]))
        self.assertFalse(ctrc.carried_by("0x0F58", paths))
        self.assertEqual(self.census().directories,
                         ["2026-09-23-power-mode-cycle"])


class TheCommittedRoot(unittest.TestCase):
    """The real thing: the capture root is flat and every file in it is dated.

    The two tripwires. **They assert emptiness, not a figure** -- no count of
    captures appears in either, so adding a capture does not turn a case red,
    while adding one that loses its date prefix does. That asymmetry is the
    cost written down rather than designed away: the second is a refusal, and
    a refusal that nothing can fail is not one.
    """

    def setUp(self):
        self.census = ccn.census(ccn.ROOT)

    def test_the_root_could_be_listed_at_all(self):
        # The vacuity guard, and the reason `census()` answers `None` rather
        # than three empty lists. "0 undated, 0 subdirectories" over a root
        # nobody read is a checker that passed by checking nothing, which is
        # the §14b defect `run-tests.sh` guards at the suite level.
        self.assertIsNotNone(self.census)
        self.assertTrue(self.census.files,
                        f"{ccn.WATCH}/ listed no capture at all. That is a "
                        f"broken census, not an empty one.")

    def test_every_capture_in_the_root_is_dated_in_its_filename(self):
        self.assertEqual(self.census.undated, [])

    def test_the_root_is_flat(self):
        self.assertEqual(self.census.directories, [])

    def test_every_capture_carries_its_own_date_back_to_a_glob_that_reaches_it(self):
        # The premise stated as a property of the tree rather than of the
        # pattern: for each file, the date its name starts with produces a glob
        # that matches the file itself. Read over the listing rather than
        # asserted as a count, so the corpus grows without breaking it.
        for name in self.census.files:
            with self.subTest(capture=name):
                self.assertTrue(ccn.PREFIX.match(name), name)
                reached = glob.glob(
                    os.path.join(ccn.ROOT, f"{name[:10]}-*"))
                self.assertIn(os.path.join(ccn.ROOT, name), reached, name)


class TheCommandLine(unittest.TestCase):
    """`--check` and the default run, over a scratch root.

    The tool is both a census and a refusal and the two have different
    standing, so the exit code is part of what it says: read by hand the run
    prints the census and the refusals and exits 0, and only `--check` makes a
    refusal the verdict. Pinned here because that asymmetry is a decision
    rather than an accident, and an exit code nobody looks at is one nobody
    relies on.
    """

    def run_main(self, root, *argv):
        """(exit code, stdout, stderr) for `main()` over a scratch root."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(ccn, 'ROOT', root), \
                mock.patch.object(sys, 'argv', ['check_capture_names.py', *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return ccn.main(), out.getvalue(), err.getvalue()

    def test_check_fails_on_an_undated_capture(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        open(os.path.join(root, UNDATED), "w").close()
        rc, _, err = self.run_main(root, "--check")
        self.assertEqual(rc, 1)
        self.assertIn("carries no", err)

    def test_check_fails_on_a_root_that_is_not_flat(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        os.mkdir(os.path.join(root, "2026-09-24-nested"))
        rc, _, err = self.run_main(root, "--check")
        self.assertEqual(rc, 1)
        self.assertIn("is not a file", err)

    def test_check_passes_over_the_committed_root(self):
        rc, out, err = self.run_main(ccn.ROOT, "--check")
        self.assertEqual(rc, 0, err)
        self.assertIn("every capture in the root is dated", out)

    def test_the_default_run_prints_the_census_and_exits_zero(self):
        # The standing, in both halves: a refusal it has printed is still not
        # the verdict unless `--check` asked for it, so the tool is useful read
        # by hand -- which is what the write-up's own numbers are read off.
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        open(os.path.join(root, UNDATED), "w").close()
        rc, out, err = self.run_main(root)
        self.assertEqual(rc, 0)
        self.assertIn("1 capture(s)", out)
        self.assertIn("1 without a date prefix", out)
        self.assertIn("carries no", err)

    def test_a_root_that_cannot_be_listed_is_refused_and_not_passed(self):
        # `census()` answers `None` here and `main()` turns that into a broken
        # census rather than three empty lists, so a capture root that moved
        # cannot read as a capture root that is perfectly conformant.
        missing = os.path.join(tempfile.mkdtemp(), "ec-watch")
        self.addCleanup(shutil.rmtree, os.path.dirname(missing))
        self.assertIsNone(ccn.census(missing))
        rc, _, err = self.run_main(missing, "--check")
        self.assertEqual(rc, 1)
        self.assertIn("broken census, not an empty one", err)


if __name__ == '__main__':
    unittest.main()
