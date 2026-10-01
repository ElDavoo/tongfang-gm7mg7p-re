#!/usr/bin/env python3
"""Offline checks for measure_mark_provenance.py's citation machinery.

The tool's job in section 5 is a claim it makes about itself: every pin
resolves at the line quoted, and the row-site join closes in both directions.
Two things can make that claim false while the tool still exits 0, and both
are worth a case rather than a paragraph:

  * **the join being walked at the wrong width.** `check_citations` ends in two
    set differences, both unpacked as `(path, lineno)`. A `scan` carrying the
    text column is walked fine until the loop reaches it, and then the run
    ends in a `ValueError` from a for-loop -- a traceback in the middle of
    section 5 that names a tuple rather than the width that is wrong or the
    site that carries it. That is the shape issue #762 was opened for, and
    the named error is what replaced it;
  * **the closure passing because it compares nothing.** A join whose two
    sets are empty is `named == scan` in the strict sense and says nothing
    about the tree. The cases below therefore build both sides rather than
    asserting a property of an empty pair.

What is deliberately **not** pinned here is a count: how many pins there are,
how many had drifted, how many the scan finds. Every one of those is a value
that moves on every merge that adds a reader or re-anchors a pin, and a test
holding one is a line every merge has to edit. The committed-tree case asserts
the claim -- every citation resolves and the join closes both ways -- which is
what holds whatever the numbers happen to be.
"""
import importlib.util
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'measure_mark_provenance', HERE / 'measure_mark_provenance.py')
mmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mmp)


# The row literal, spelled rather than written: a line of this file carrying
# the tool's ROW_LITERAL verbatim is a `ts,MARK,,label` site to `row_sites()`,
# so quoting it here would add four sites to the census these cases assert
# closes, and redden the very run they hold. The tree spells it `MARK` or
# builds it everywhere it is not the subject, for the same reason.
MARK_BRANCH = 'if addr == ' + chr(34) + 'MARK' + chr(34) + ':'


def scan_of(sites):
    """What `main` builds: the `(path, lineno)` set the two loops walk.

    `row_sites()` returns `(writers, readers)` and `main` concatenates them
    before narrowing, so this takes the pair the way `main` takes it -- the
    narrowing is the step under test elsewhere in this file, and doing it
    here too would make a case built this way agree with whichever side was
    wrong.
    """
    writers, readers = sites
    return {(path, lineno) for path, lineno, _text in writers + readers}


class ArityTests(unittest.TestCase):
    """The width check, at each width it is there to catch.

    The 3-wide case is the one the issue reproduces, and it is written by hand
    rather than produced by `row_sites()` on purpose: the defect was that
    `main` narrowed a 3-wide row set to 2 and one of the loops did not, so a
    case built the way `main` builds it would agree with whichever side was
    wrong. Hand-built is the only version of this case that can fail.
    """

    def test_a_three_wide_scan_raises_the_named_error(self):
        # `row_sites()` yields (path, lineno, text). This is the set as it is
        # before `main`'s narrowing, and the width the issue reported.
        wide = {("ec/tools/grade_0751_isolation.py", 1477,
                 MARK_BRANCH)}
        with self.assertRaises(ValueError) as caught:
            mmp.check_citations(wide)
        message = str(caught.exception)
        self.assertIn("scan", message)
        self.assertIn("width 3", message)
        # The site is named, not just the width: a reader who cannot see which
        # element was wrong is left re-deriving it.
        self.assertIn("grade_0751_isolation.py", message)

    def test_the_named_error_says_what_the_right_hand_side_is(self):
        # The error is only useful if it says what the set should have been.
        with self.assertRaises(ValueError) as caught:
            mmp.site_arity({("a.py", 1, "text")}, "scan")
        self.assertIn("(path, lineno)", str(caught.exception))

    def test_a_narrower_element_is_refused_too(self):
        # The other direction the issue did not report. A set built by
        # unpacking the wrong end of a row is one wide, and it fails the same
        # way; only testing the reported direction would leave this one to a
        # reader.
        with self.assertRaises(ValueError) as caught:
            mmp.site_arity({("a.py",)}, "scan")
        self.assertIn("width 1", str(caught.exception))

    def test_a_non_tuple_element_names_its_type_rather_than_a_width(self):
        # A string site is iterable and has a length, so reporting "width 6"
        # for one would be a number that reads as a measurement. The type is
        # the fact.
        with self.assertRaises(ValueError) as caught:
            mmp.site_arity({"a.py:1"}, "scan")
        message = str(caught.exception)
        self.assertIn("str", message)
        self.assertNotIn("width 6", message)

    def test_the_error_names_the_set_it_was_looking_at(self):
        # `scan` and `named` are walked by different loops and a reader told
        # only "width 3" cannot tell which of the two was wrong.
        with self.assertRaises(ValueError) as caught:
            mmp.site_arity({("a.py", 1, "t")}, "named")
        self.assertIn("named", str(caught.exception))

    def test_a_pair_set_is_accepted(self):
        # The guard must not be the thing that goes red on a correct tree:
        # this is the shape `main` actually builds.
        mmp.site_arity({("a.py", 1), ("b.py", 2)}, "scan")

    def test_an_empty_set_is_accepted(self):
        # An empty scan is what a tree with no writers would produce. It
        # proves nothing about the join, so it must not raise -- that is the
        # committed-tree case's job, not the guard's.
        mmp.site_arity(set(), "scan")


class JoinTests(unittest.TestCase):
    """Both directions of the join, built so each has something to close."""

    def test_a_site_no_citation_names_is_reported(self):
        # `scan - named`: the page's census would be a hand-typed list, which
        # is the whole failure the join exists to catch. The committed table
        # is patched so the scan's site is one nothing cites, which is the
        # only way to make this direction say something on its own.
        original = mmp.CITATIONS
        try:
            mmp.CITATIONS = [("ec/tools/grade_0751_isolation.py", 1477,
                              "a line carrying no row literal", "synthetic")]
            problems = mmp.check_citations(
                {("ec/tools/grade_0751_isolation.py", 1477)})
        finally:
            mmp.CITATIONS = original
        self.assertTrue(
            any("1477" in p and "no citation names" in p for p in problems),
            f'the scan found a site nothing cites and it was not said: '
            f'{problems}')

    def test_a_citation_the_scan_no_longer_finds_is_reported(self):
        # `named - scan`: the other direction, which a one-sided check misses.
        # Built by patching CITATIONS so the pair really does carry the row
        # literal rather than asserting against the committed table.
        original = mmp.CITATIONS
        try:
            mmp.CITATIONS = [("ec/tools/grade_0751_isolation.py", 1,
                              MARK_BRANCH, "a synthetic pin")]
            problems = mmp.check_citations(set())
        finally:
            mmp.CITATIONS = original
        self.assertTrue(
            any("no longer finds one there" in p for p in problems),
            f'a cited row site the scan dropped was not said: {problems}')

    def test_a_join_that_closes_reports_nothing(self):
        # The pass condition, built rather than read off the committed tree:
        # a pin carrying the literal, a scan holding exactly that site.
        original = mmp.CITATIONS
        try:
            mmp.CITATIONS = [("ec/tools/grade_0751_isolation.py", 1477,
                              MARK_BRANCH, "a synthetic pin")]
            problems = mmp.check_citations(
                {("ec/tools/grade_0751_isolation.py", 1477)})
        finally:
            mmp.CITATIONS = original
        self.assertEqual(problems, [])

    def test_the_width_is_checked_before_the_join_runs(self):
        # Order, not decoration: a wrong width has to be refused before the
        # set differences, or the run ends in the for-loop ValueError this
        # guard exists to replace.
        wide = {("ec/tools/grade_0751_isolation.py", 1477,
                 MARK_BRANCH)}
        with self.assertRaises(ValueError) as caught:
            mmp.check_citations(wide)
        self.assertIn("width", str(caught.exception))


class CommittedTreeTests(unittest.TestCase):
    """The tool's own claim, against the tree it ships in.

    The assertion is the claim and not the census: that every citation's
    quoted text is at the line quoted, and that the row-site join closes both
    ways. Both are properties of the tree that survive a pin being added or
    moved; the number of pins is not, so nothing here counts them.
    """

    def test_every_citation_resolves_at_the_line_it_quotes(self):
        drifted = []
        for path, lineno, want, what in mmp.CITATIONS:
            got = mmp.line_of(os.path.join(mmp.REPO, path), lineno).strip()
            if want not in got:
                drifted.append(f"{path}:{lineno} ({what})")
        self.assertEqual(
            drifted, [],
            f'{len(drifted)} citation(s) name a line that does not carry '
            'their quoted text. A pin is re-anchored by re-reading its own '
            'text in the file, and where the `what` no longer describes the '
            'line it is the `what` that is wrong -- see '
            'docs/findings/0762-provenance-citation-reanchor.md.')

    def test_the_row_site_join_closes_in_both_directions(self):
        scan = scan_of(mmp.row_sites())
        named = {(path, lineno) for path, lineno, want, _what in mmp.CITATIONS
                 if mmp.ROW_LITERAL in want}
        self.assertTrue(scan, "the scan found no row site at all, so a "
                              "closed join over it would prove nothing")
        self.assertEqual(
            sorted(scan - named), [],
            "a scanned row site no citation names, so the page's census is a "
            "hand-typed list rather than this scan")
        self.assertEqual(
            sorted(named - scan), [],
            "a cited row site the scan no longer finds, so the citation and "
            "the scan disagree about what the sites are")

    def test_the_join_the_tool_reports_is_the_join_it_has(self):
        # `check_citations` is called by `main` with the narrowed set; this is
        # the same call, so a `main` that narrowed differently would show up
        # here rather than only in a hand-run.
        self.assertEqual(mmp.check_citations(scan_of(mmp.row_sites())), [])


if __name__ == '__main__':
    unittest.main()
