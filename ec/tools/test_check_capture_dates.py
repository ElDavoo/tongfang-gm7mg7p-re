#!/usr/bin/env python3
"""Offline checks for check_capture_dates.py: the committed root and a temp one.

The tool holds the filename's ten characters to the dates the file itself
carries, and reports three populations. **The committed root can show the
third and cannot show the second** -- every capture that states a day agrees
with its own prefix, and `2026-09-23-power-mode-cycle-0f00-final.txt` states
none -- so the refusal that matters is fired on a scratch root instead, the
reason `test_check_capture_names.py` gives for its own two. A case over a
conformant tree proves the tool runs; it cannot prove the tool refuses.

**The three populations partition the root, and that is asserted as a
relation** rather than as three counts. A checker that reports everything
agreeing satisfies every positive case at once, and the only thing that stops
it is a case over a tree holding one of each, checked so that every file is in
exactly one bucket. The bucket that is a line rather than a verdict gets the
same treatment from the other side: the case that adds a day to an uncheckable
capture and watches the bucket shrink while nothing turns red, because that is
what a human closing the gap on `0f00-final.txt` will see.

**No case pins a count of the tree.** `15`, `14` and `1` are figures of the
tree this was written against and every capture a human commits moves them. The
committed-root cases assert the *emptiness* of the disagreement set -- the
tripwire -- and that the denominator is non-zero, which is `captures_for()`'s
own reasoning about a floor: see `docs/agent-pipeline.md`, and `CLAUDE.md`'s
rule that a test asserting a count of the tree is a value every merge has to
edit.
"""
import contextlib
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
# Loaded by path for the same reason `test_check_capture_names.py` loads its
# tool the same way, and the directory is the sys.path entry the tool's own
# `from check_capture_claims import WATCH` resolves against.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_capture_dates', HERE / 'check_capture_dates.py')
ccd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccd)

# `PREFIX` is imported rather than spelled, and the case below asks the two
# spellings of a prefix whether they agree rather than asserting a string, so
# a reworded pattern cannot quietly change what this tool reads a name as
# without a case going red here.
spec = importlib.util.spec_from_file_location(
    'check_capture_names', HERE / 'check_capture_names.py')
ccn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccn)

# A capture that states the day its own name claims, one that states a
# different one, and one that states none. Spelled as three files rather than
# as a list of good names, so a case that adds a fourth has to say which
# population it is on the line of.
AGREES = "2026-09-23-power-mode-cycle-0f00-0f5f.csv"
DISAGREES = "2026-09-24-power-mode-cycle-0f00-0f5f.csv"
UNDATED = "2026-09-23-power-mode-cycle-0f00-final.txt"

AGREEING_TEXT = "ts,addr,old,new\n2026-09-23T17:52:03+02:00,0x0F00,0x35,0x39\n"
# The disagreement is a capture named for the 24th whose own rows are the
# 23rd's, which is the shape the refusal is about: two committed facts about
# one day, and no way to tell from the corpus which of them moved.
DISAGREEING_TEXT = "ts,addr,old,new\n2026-09-23T17:52:03+02:00,0x0F00,0x35,0x39\n"
# What `ec_watch.py --dump` writes: a hex page, and no header. This is the
# committed shape of `0f00-final.txt` and the reason the third population has a
# member at all, so the fixture is that shape rather than an empty file -- an
# empty file would pass for "the read came back empty" and prove nothing.
HEX_PAGE = "0F00: 35 39 3b 3d 3f 41 43 4b 50 53 ff ff ff ff ff ff\n"


class ScratchRoot(unittest.TestCase):
    """A throwaway capture root, and the walk taken over it."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def capture(self, name, text=""):
        """A file at `name` under the scratch root, `text` unless it is bytes."""
        mode, payload = ("wb", text) if isinstance(text, bytes) else ("w", text)
        with open(os.path.join(self.root, name), mode) as f:
            f.write(payload)
        return self.root

    def found(self):
        """The `Checked` list, and the three buckets, over the scratch root."""
        found = ccd.census(self.root)
        self.assertIsNotNone(found)
        return found, ccd.partition(found)

    def reported(self, buckets, where="scratch"):
        """(disagreements, stdout, stderr) from `report()`, output captured."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            problems = ccd.report(buckets, where)
        return problems, out.getvalue(), err.getvalue()


class TheThreePopulations(ScratchRoot):
    """One file of each population, and the properties that make them three."""

    def test_the_three_populations_partition_the_root(self):
        # The case that stops an implementation reporting everything agreeing:
        # every file is in exactly one bucket, and the buckets together are
        # every file the listing gave. `population` is one field, so a file
        # cannot be in two, and the names are compared to the listing rather
        # than to a count -- a root that grows must not need this edited.
        self.capture(AGREES, AGREEING_TEXT)
        self.capture(DISAGREES, DISAGREEING_TEXT)
        self.capture(UNDATED, HEX_PAGE)
        self.capture("power-mode-cycle-undated.csv", AGREEING_TEXT)
        found, buckets = self.found()
        self.assertEqual(len(found), 4)
        self.assertEqual([c.name for c in buckets["agrees"]], [AGREES])
        self.assertEqual([c.name for c in buckets["disagrees"]], [DISAGREES])
        self.assertEqual(sorted(c.name for c in buckets["unchecked"]),
                         sorted([UNDATED, "power-mode-cycle-undated.csv"]))
        for population in ccd.POPULATIONS:
            self.assertTrue(buckets[population], population)
            with self.subTest(population=population):
                self.assertEqual(
                    len(buckets[population]),
                    sum(1 for c in found if c.population == population))

    def test_a_file_naming_a_sibling_is_not_a_disagreement(self):
        # Set membership, which is the decision. This corpus already names
        # siblings -- `2026-09-23-power-mode-snapshot-dc.txt:2` says "just
        # before the power-mode capture in `2026-09-23-power-mode-cycle-*`" --
        # so requiring *every* date in a file to equal the prefix would refuse
        # a capture for naming its neighbour correctly.
        #
        # The sibling is dated the **21st** and the file the 23rd on purpose.
        # The corpus's own sibling line names a sibling of the *same* day, so
        # the two readings give the same answer there, and a fixture built from
        # it would pass under either -- which is how the first version of this
        # case passed with the rule inverted. A decision is only held by a
        # fixture on which the decision bites.
        self.capture(
            AGREES,
            "# taken 2026-09-23, the day after 2026-09-21-power-mode-cycle-*\n"
            + AGREEING_TEXT)
        _, buckets = self.found()
        self.assertEqual([c.name for c in buckets["agrees"]], [AGREES])
        self.assertEqual(buckets["disagrees"], [])

    def test_a_file_stating_only_its_siblings_day_is_a_disagreement(self):
        # The other side of the same case, and the one that says set
        # membership is not so lax that any date at all passes. The one date
        # here is not this file's own, and that is what the prefix is about.
        self.capture(
            AGREES,
            "# a run from 2026-09-24-power-mode-cycle-0700-07ff.csv\n"
            "0x0F00 = 0x35\n")
        _, buckets = self.found()
        self.assertEqual([c.name for c in buckets["disagrees"]], [AGREES])
        self.assertEqual(buckets["agrees"], [])

    def test_an_undecodable_file_is_uncheckable_with_its_own_reason(self):
        # A fourth reason in one population, not a fourth population: a
        # capture no reader takes is a file the run cannot say anything about,
        # which is the same fact as a file that states no day, and the reason
        # names `check_capture_encoding.py` because a capture is defined to be
        # utf-8 and that is the tool that owns the refusal.
        self.capture(AGREES, b"# 2026-09-23\n\xff\xfe not utf-8\n")
        _, buckets = self.found()
        self.assertEqual([c.name for c in buckets["unchecked"]], [AGREES])
        self.assertEqual(buckets["agrees"], [])
        out = self.stdout_of(buckets)
        self.assertIn("is not utf-8-decodable", out)
        self.assertIn("check_capture_encoding.py", out)

    def test_a_prefix_less_file_is_uncheckable_and_not_a_second_refusal(self):
        # `check_capture_names.py`'s refusal, landed here without a second
        # vocabulary: the file is counted and named, and nothing on stderr
        # says `--check` should fail. Two tools reporting one mistake in two
        # vocabularies is the blurring the sibling's own docstring refuses.
        self.capture("power-mode-cycle-undated.csv", AGREEING_TEXT)
        found, buckets = self.found()
        self.assertEqual([c.name for c in buckets["unchecked"]],
                         ["power-mode-cycle-undated.csv"])
        problems, out, err = self.reported(buckets)
        self.assertEqual(problems, [])
        self.assertIn("carries no", out)
        self.assertIn("the cross-check has no claim to run it against", out)
        self.assertEqual(err, "")

    def test_a_lookalike_date_conforms(self):
        # A cross-check, not a calendar: `20\d\d-\d\d-\d\d` is the shape, and
        # this half of the rule is `check_capture_names.py`'s. A checker that
        # went on to decide whether a named day exists would be answering a
        # different question, and would be the first thing to break on a
        # hand-typed date in a capture header.
        self.capture("2026-99-99-typo.csv",
                     "ts,addr,old,new\n2026-99-99T00:00:00+02:00,0x0F00,0x35,0x39\n")
        _, buckets = self.found()
        self.assertEqual([c.name for c in buckets["agrees"]],
                         ["2026-99-99-typo.csv"])

    def test_dates_are_read_from_the_text_and_not_by_file_type(self):
        # One rule for every capture, not one per extension: a `ts` column in
        # a `.txt` and a `#` header in a `.csv` are both a date in the text,
        # and a per-type reader would be a second rule to keep in step with
        # the corpus's file types. Pinned both ways, so re-deriving the
        # extraction from the extension is red here whichever way it is wrong.
        self.capture("2026-09-23-snapshot.txt",
                     "state                         0x0743\n"
                     "2026-09-23T16:39:20Z         0x10\n")
        self.capture("2026-09-24-sweep.csv",
                     "# Issue #8, taken 2026-09-24, GT7MG7P on AC\n"
                     "ts,addr,old,new\n2026-09-24T12:00:00+02:00,0x0743,0x10,0x20\n")
        _, buckets = self.found()
        self.assertEqual([c.name for c in buckets["agrees"]],
                         ["2026-09-23-snapshot.txt", "2026-09-24-sweep.csv"])
        self.assertEqual(buckets["disagrees"], [])

    def test_a_file_that_cannot_be_opened_is_named_rather_than_crashed_on(self):
        # A census is a walk of a live directory, so a file that goes between
        # the listing and the read is reachable in principle, and a traceback
        # is the one answer that helps nobody. Driven through `inspect()`
        # rather than through a root, because a `chmod` that makes a file
        # unreadable does not stop a root from opening it and a case that
        # passed on this machine and failed in CI would be worth nothing.
        found = ccd.inspect(AGREES, os.path.join(self.root, "gone.csv"))
        self.assertEqual(found.population, "unchecked")
        self.assertIn("could not be read", found.reason)

    def test_a_subdirectory_in_the_root_is_never_read(self):
        # Never seen, because the listing is `check_capture_names.census()`'s
        # and that tool owns the subdirectory refusal. Asserted as absence
        # rather than as a count so a root that grows keeps it: a directory
        # here is not this tool's refusal, and a read attempted on one would
        # put a second vocabulary on a mistake that already has an owner.
        self.capture(AGREES, AGREEING_TEXT)
        os.mkdir(os.path.join(self.root, "2026-09-24-nested"))
        found, buckets = self.found()
        self.assertEqual(len(found), 1)
        self.assertEqual([c.name for c in found], [AGREES])
        for population in ccd.POPULATIONS:
            self.assertNotIn("2026-09-24-nested",
                             [c.name for c in buckets[population]])

    def stdout_of(self, buckets):
        """`report()`'s stdout alone, for a case that wants only that stream."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            ccd.report(buckets, "scratch")
        return out.getvalue()


class WhatTheThirdPopulationIsWorth(ScratchRoot):
    """It is a line, and closing the gap turns nothing red.

    The claim the design exists for, stated as a demonstration rather than as
    prose: a human adding a `#` header to `0f00-final.txt` shrinks the third
    population from one to none and the run stays green, while a capture that
    actually disagrees is red the moment it lands. Both halves are the same
    walk over the same root, so they cannot disagree about which is which.
    """

    def test_adding_a_day_shrinks_the_bucket_and_turns_nothing_red(self):
        self.capture(AGREES, AGREEING_TEXT)
        self.capture(UNDATED, HEX_PAGE)
        _, before = self.found()
        problems, out, _ = self.reported(before)
        self.assertEqual(problems, [])
        self.assertIn("1  prefix cannot be checked", out)
        self.assertIn(UNDATED, out)

        self.capture(UNDATED, "# ec_watch.py --dump, 2026-09-23, fan table\n"
                     + HEX_PAGE)
        _, after = self.found()
        problems, out, _ = self.reported(after)
        self.assertEqual(problems, [])
        self.assertIn("0  prefix cannot be checked", out)
        self.assertEqual([c.name for c in after["agrees"]], [AGREES, UNDATED])
        self.assertIn("no capture under scratch/ has a date prefix its own "
                      "contents contradict", out)

    def test_every_member_of_the_third_population_is_named_on_every_run(self):
        # A count nobody reads is the failure mode the whole third population
        # is for, so the claim is over the *relation*: each member is named in
        # the output, whatever the count happens to be. Read over the members
        # rather than against a figure, so a corpus that grows one unchecked
        # capture is a green run and this case is still the thing that fails
        # if the naming stops.
        for day in ("2026-09-23", "2026-09-24", "2026-09-18"):
            self.capture(f"{day}-dump.txt", HEX_PAGE)
        _, buckets = self.found()
        _, out, _ = self.reported(buckets)
        for c in buckets["unchecked"]:
            with self.subTest(capture=c.name):
                self.assertIn(f"scratch/{c.name}: {c.reason}", out)

    def test_the_uncheckable_line_says_it_is_not_a_verdict(self):
        # The standing, said in the output rather than only in the docstring:
        # a reader who runs this over a root and reads one line has to be told
        # that the line is a count and not a pass.
        self.capture(UNDATED, HEX_PAGE)
        _, buckets = self.found()
        problems, out, _ = self.reported(buckets)
        self.assertEqual(problems, [])
        self.assertIn("`--check` does not fail on it", out)


class TheCommandLine(ScratchRoot):
    """`--check` and the default run, over a scratch root.

    `--check` adds exactly one thing to the default run, and the suite holds
    it rather than the docstring: an uncheckable capture is a line either way,
    and a disagreement is a failure only when asked for. Read by hand the run
    is the measurement the write-up quotes, so its exit code is not a claim
    until something asks.
    """

    def run_main(self, root, *argv):
        """(exit code, stdout, stderr) for `main()` over a scratch root."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(ccd, 'ROOT', root), \
                mock.patch.object(sys, 'argv', ['check_capture_dates.py', *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return ccd.main(), out.getvalue(), err.getvalue()

    def test_check_fails_on_a_disagreement_and_says_which(self):
        self.capture(DISAGREES, DISAGREEING_TEXT)
        rc, _, err = self.run_main(self.root, "--check")
        self.assertEqual(rc, 1)
        # The message has to carry all three of what disagrees, what the name
        # says, and what the file says -- a refusal that named only the file
        # would send a reader back to the listing to work out which of two
        # committed facts had moved. The root is the one the run was handed,
        # and `shown()` is why a scratch tree is not named `evidence/ec-watch/`.
        self.assertIn(os.path.join(self.root, DISAGREES), err)
        self.assertIn("the name says `2026-09-24`", err)
        self.assertIn("the file itself carries 2026-09-23", err)
        self.assertIn(f"1 capture(s) under {self.root}/", err)

    def test_the_default_run_exits_zero_and_still_names_the_uncheckable(self):
        # The same tree, without the flag. The refusal is printed and the run
        # is green, which is what makes the tool a measurement as well as a
        # check: the write-up's own figures are read off a default run.
        self.capture(UNDATED, HEX_PAGE)
        rc, out, err = self.run_main(self.root)
        self.assertEqual(rc, 0, err)
        self.assertIn("1  prefix cannot be checked", out)
        self.assertIn(os.path.join(self.root, UNDATED), out)
        self.assertEqual(err, "")

    def test_check_does_not_fail_on_a_capture_it_cannot_check(self):
        # The refusal that is not one. This is the whole of the third
        # population's standing and it is the case that would go red the day
        # someone made the tool fail on a file with no date in it.
        self.capture(UNDATED, HEX_PAGE)
        rc, out, err = self.run_main(self.root, "--check")
        self.assertEqual(rc, 0, err)
        self.assertIn("carries no date to check", out)

    def test_check_passes_over_the_committed_root(self):
        rc, out, err = self.run_main(ccd.ROOT, "--check")
        self.assertEqual(rc, 0, err)
        self.assertIn("prefix cannot be checked", out)

    def test_a_root_that_cannot_be_listed_is_refused_and_not_passed(self):
        # `census()` answers `None` and `main()` turns that into a broken
        # census rather than three zero populations, so a capture root that
        # moved cannot read as a corpus in which every capture agrees with
        # its own name. The vacuity guard, one level above the sibling's.
        missing = os.path.join(tempfile.mkdtemp(), "ec-watch")
        self.addCleanup(shutil.rmtree, os.path.dirname(missing))
        self.assertIsNone(ccd.census(missing))
        for argv in ([], ["--check"]):
            with self.subTest(argv=argv):
                rc, _, err = self.run_main(missing, *argv)
                self.assertEqual(rc, 1)
                self.assertIn("broken census, not an empty one", err)


class TheCommittedRoot(unittest.TestCase):
    """The real corpus: a tripwire, and a denominator that is not a figure."""

    def setUp(self):
        found = ccd.census(ccd.ROOT)
        self.assertIsNotNone(found)
        self.found = found
        self.buckets = ccd.partition(found)

    def test_the_root_could_be_listed_at_all(self):
        # The vacuity guard, and the reason `census()` answers `None` rather
        # than an empty list: "0 disagreeing, 0 unchecked" over a root nobody
        # read is a checker that passed by checking nothing.
        self.assertTrue(self.found,
                        f"{ccd.WATCH}/ listed no capture at all. That is a "
                        f"broken census, not an empty one.")

    def test_the_denominator_is_a_denominator(self):
        # Asserted as non-zero and never as a figure. `15` is a claim about the
        # tree this suite was written against and every capture a human commits
        # moves it; a floor would also be a claim, and the one that keeps
        # being raised to defeat a future capture is the mistake. What has to
        # hold is that the walk reaches something.
        total = sum(len(self.buckets[p]) for p in ccd.POPULATIONS)
        self.assertTrue(total, "no capture reached any population")

    def test_no_capture_disagrees_with_a_date_it_carries(self):
        # The tripwire, and it asserts **emptiness, not a figure**. Every one
        # of the captures that states a day states its own; a capture that
        # arrives disagreeing turns this red, which is exactly what a refusal
        # is for, and one that arrives agreeing does not.
        self.assertEqual([c.name for c in self.buckets["disagrees"]], [])

    def test_every_capture_is_in_exactly_one_population(self):
        # The same partition the scratch root carries, over the real corpus:
        # a capture cannot be counted twice, and a fourth population that
        # `partition()` did not know about would show up as a file missing
        # from all three rather than as a count that added up.
        for name in [c.name for c in self.found]:
            with self.subTest(capture=name):
                here = [p for p in ccd.POPULATIONS
                        if name in [c.name for c in self.buckets[p]]]
                self.assertEqual(len(here), 1, name)

    def test_the_extracted_prefix_is_the_ten_characters_PREFIX_matches(self):
        # The two readers of the rule, held to each other and not to a
        # spelling. `prefix_of()` drops `PREFIX`'s trailing hyphen and this
        # case takes ten characters, so a pattern that grew a second separator
        # is red here rather than quietly changing what a prefix is.
        names = [c.name for c in self.found] + [
            AGREES, DISAGREES, "2026-99-99-typo.csv", "power-mode-undated.csv"]
        for name in names:
            with self.subTest(capture=name):
                self.assertEqual(ccd.prefix_of(name),
                                 ccn.PREFIX.match(name).group(0)[:10]
                                 if ccn.PREFIX.match(name) else None)


if __name__ == '__main__':
    unittest.main()
