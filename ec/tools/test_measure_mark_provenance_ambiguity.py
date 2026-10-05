#!/usr/bin/env python3
"""How `measure_mark_provenance.py` decided which line a citation means, and
what it does with an answer it had to guess.

`test_measure_mark_provenance_citations.py` stands in for the citation check
being *right*: every pin resolves, and the row-site join closes both ways. This
file stands in for the question one step earlier -- **when several lines carry
the quoted text and the recorded number names none of them, which one is the
claim about?** `resolve()` answers by nearest line and returns a single number,
so a citation that had been resolved into the wrong function was indistinguishable
from one that had been resolved into the right one, and the tool printed `ok` on
both. Two pins on `grade_0751_isolation.py` were in exactly that state, and the
page's central architectural claim rested on them.

The four cases below are built into a temp file rather than read off the
committed table, for the reason that file's docstring gives: a case built the
way `main` builds its input cannot disagree with whichever side of the defect it
was written to catch. `gone` is a fourth answer and not a fifth way of saying
`ambiguous` -- "no line of this file carries the text" is a statement about a
search over a file, "several lines carry it and the number cannot say which" is
a statement about a pin, and collapsing the two would let a citation whose text
*was* found be reported as a broken one.

What is deliberately **not** pinned: how many citations are ambiguous, how many
carry their text in a docstring, how many pins the table holds. Every one of
those moves on any merge that re-anchors a pin or adds a reader, and a test
holding one is the line every such merge has to edit. The committed-tree case
below asserts the *claim* -- that no citation whose subject names a function
resolves into a different one -- which holds whatever the census is.
"""
import importlib.util
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'measure_mark_provenance', HERE / 'measure_mark_provenance.py')
mmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mmp)


# What the temp files below spell. Spelled rather than built from the tool's own
# constants so a case cannot pass because both sides drifted together, and short
# enough that adding a line to one of them is visibly a change to the fixture.
CARRIED = "    if skippable_row(row):"


def a_capture(tmp: str, hits) -> str:
    """A temp file carrying `CARRIED` at the lines in `hits`, 1-based.

    Built by padding rather than by writing a fixed body, because what the four
    cases differ on is *where* the text sits and nothing else: the point is that
    two files differing only in which number the pin recorded resolve differently.
    """
    path = os.path.join(tmp, "f.py")
    with open(path, "w", encoding="utf-8") as f:
        for n in range(1, max(hits) + 2):
            f.write((CARRIED if n in hits else f"    pass  # {n}") + "\n")
    return path


def enclosing_def(lines, lineno):
    """The module-level `def` a line is inside, or None.

    Module-level only, and that is deliberate rather than a simplification: a
    `def` nested inside another is a local, and a claim naming one is a claim
    about a scope this file has no other way to resolve. A citation into a
    nested function is therefore not checked here, which is a blind side and not
    a coverage claim.
    """
    found = None
    for n, text in enumerate(lines, 1):
        match = re.match(r'^def\s+(\w+)\s*\(', text)
        if match and n <= lineno and (found is None or n > found[1]):
            found = (match.group(1), n)
    return found[0] if found else None


def subject_of(what, defined):
    """The function a claim's *subject* names, or None.

    Only a function named where the sentence starts counts. A `what` that
    mentions a function anywhere -- "the rule this tool's section 2 census and
    `grade_0751_isolation.read_capture` share" names two, and neither is what
    the sentence is about -- is a claim about something else that happens to
    contain the name, and holding it to the enclosing function would be a
    checker over prose rather than over the table. The section prefixes are
    dropped because every entry in the table opens with one.
    """
    rest = re.sub(r'^(?:[a-z_]+:\s*)?(?:the\s+|a\s+|an\s+)?', "", what)
    for name in defined:
        if re.match(re.escape(name) + r'\b', rest):
            return name
    return None


class ResolutionHowTests(unittest.TestCase):
    """The four answers, each built so the question is actually asked."""

    def test_two_carrying_lines_and_a_number_naming_neither_is_ambiguous(self):
        # The defect's own shape. The number is equidistant-ish from neither
        # line, so `resolve` picks by proximity and the pin is silently about
        # whichever line happened to be nearer.
        with tempfile.TemporaryDirectory() as tmp:
            path = a_capture(tmp, hits=(3, 9))
            how, found, hits = mmp.resolve_how(path, 5, CARRIED)
        self.assertEqual(how, "ambiguous")
        self.assertEqual(hits, [3, 9])
        # Both candidates are named, because a reader cannot choose between two
        # lines it has not been shown.
        self.assertIn(found, hits)

    def test_a_number_naming_one_of_them_is_not_ambiguous(self):
        # The same two lines, the number moved onto the second. The tie-break
        # still runs and still has to, but the pin now says which line it means,
        # so the answer is checked rather than guessed -- and it is `exact`,
        # not `moved`, because the number is itself a carrying line.
        with tempfile.TemporaryDirectory() as tmp:
            path = a_capture(tmp, hits=(3, 9))
            how, found, _hits = mmp.resolve_how(path, 9, CARRIED)
        self.assertEqual(how, "exact")
        self.assertEqual(found, 9)

    def test_one_carrying_line_is_reported_moved_whatever_the_number_says(self):
        # A pin whose text is gone from the recorded line and found one further
        # on. This is the ordinary state of most pins after any merge that grows
        # a cited file above them, and it must not read as a problem: the text
        # is present and it named its own line.
        with tempfile.TemporaryDirectory() as tmp:
            path = a_capture(tmp, hits=(9,))
            how, found, hits = mmp.resolve_how(path, 3, CARRIED)
        self.assertEqual(how, "moved")
        self.assertEqual((found, hits), (9, [9]))

    def test_text_no_line_carries_is_gone_and_not_ambiguous(self):
        # The distinct fourth answer. Folding it into `ambiguous` would report a
        # citation whose claim is broken as one whose number is stale, which is
        # the overclaim `check_doc_figure_pins.py` refuses in its own vocabulary.
        with tempfile.TemporaryDirectory() as tmp:
            path = a_capture(tmp, hits=(3, 9))
            how, found, hits = mmp.resolve_how(path, 5, "a line carries neither")
        self.assertEqual(how, "gone")
        self.assertIsNone(found)
        self.assertEqual(hits, [])

    def test_resolve_agrees_with_the_line_resolve_how_reports(self):
        # `resolve` is the one-liner the rest of the tool calls, and this is the
        # relation between it and the answer it does not expose. A divergence
        # would mean the section-5 rows and the ambiguity report disagree about
        # the same pin, which is the failure mode of splitting the two.
        with tempfile.TemporaryDirectory() as tmp:
            for hits in ([3], [3, 9], [1, 2, 20]):
                path = a_capture(tmp, hits=tuple(hits))
                for lineno in (1, 3, 9, 20):
                    _how, found, _ = mmp.resolve_how(path, lineno, CARRIED)
                    self.assertEqual(mmp.resolve(path, lineno, CARRIED), found,
                                     f"resolve and resolve_how disagreed at "
                                     f"{lineno} over {hits}")

    def test_a_number_past_the_end_of_the_file_is_moved_not_an_error(self):
        # `line_of`'s reason, reached through the other door: a citation whose
        # file has since shrunk under it must still resolve by its text rather
        # than raising an IndexError out of the middle of section 5.
        with tempfile.TemporaryDirectory() as tmp:
            path = a_capture(tmp, hits=(3,))
            self.assertEqual(mmp.resolve_how(path, 9999, CARRIED),
                             ("moved", 3, [3]))


class AmbiguityIsReportedNotFailedTests(unittest.TestCase):
    """An ambiguous citation is reported and the run still exits clean.

    The distinction the issue asks for, and it is a real one rather than a
    matter of taste: the tool's text is present, which has been its whole check
    since 2026-10-03, and the number is a hint. Failing an ambiguous citation
    would redden every merge that grew a cited file above it -- the churn
    `check_citation_lines.py`'s Rule 3 was rewritten to stop, arriving by the
    citation table instead of by the CSV rows.
    """

    def test_an_ambiguous_citation_is_listed_and_contributes_no_problem(self):
        original = mmp.CITATIONS
        try:
            mmp.CITATIONS = [("ec/tools/grade_0751_isolation.py", 5,
                              CARRIED, "a synthetic pin whose number names "
                                      "neither carrying line")]
            reported = mmp.ambiguous_citations()
            # The scan is empty, so nothing joins against it either way and the
            # only thing `check_citations` could report is the row-site join --
            # which a pin with no row literal never joins.
            problems = mmp.check_citations(set())
        finally:
            mmp.CITATIONS = original
        self.assertEqual(len(reported), 1)
        self.assertEqual(problems, [],
                         "an ambiguous citation became a failure; the run would "
                         "go red on any merge that grows a cited file")

    def test_a_pin_whose_text_is_gone_is_still_a_failure(self):
        # The other half of the pair. Were this also demoted, the tool would
        # report nothing at all for a table whose claims no longer hold, and
        # "reported" would have become "ignored".
        original = mmp.CITATIONS
        try:
            mmp.CITATIONS = [("ec/tools/grade_0751_isolation.py", 1,
                              "no line of the grader carries this", "synthetic")]
            self.assertEqual(mmp.ambiguous_citations(), [])
            problems = mmp.check_citations(set())
        finally:
            mmp.CITATIONS = original
        self.assertEqual(len(problems), 1)
        self.assertIn("carries it any more", problems[0])


class CommittedTreeTests(unittest.TestCase):
    """The claim the tool could not make about itself, made here.

    `resolve()` returns one number and the tool printed `ok`, so a pin resolved
    into the wrong function was indistinguishable from one resolved into the
    right one. This asks the question the return value cannot: does the line a
    citation resolved into sit inside the function its claim is about? It is
    what `ambiguous` means in practice, and asserting it is what keeps the
    `what` column honest rather than decorative.
    """

    def citations_about_a_function(self):
        """(path, recorded, resolved, claimed, enclosing) for every pin whose
        claim is about a function, over the committed tree."""
        out = []
        for path, lineno, want, what in mmp.CITATIONS:
            full = os.path.join(mmp.REPO, path)
            found = mmp.resolve(full, lineno, want)
            if found is None:
                continue
            with open(full, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            defined = {re.match(r'^def\s+(\w+)\s*\(', text).group(1)
                       for text in lines if re.match(r'^def\s+\w+\s*\(', text)}
            claimed = subject_of(what, defined)
            if claimed is None:
                continue
            out.append((path, lineno, found, claimed, enclosing_def(lines, found)))
        return out

    def test_no_citation_resolves_into_a_function_its_claim_does_not_name(self):
        # The defect, as an assertion rather than a correction somebody has to
        # remember to make: a pin whose `what` names a function resolves into a
        # different one. The tool printed `ok` on two of them on the tree before
        # this file existed; recover them by running this rule over that tree's
        # citation table (`git show
        # origin/main:ec/tools/measure_mark_provenance.py`):
        #
        #   recorded :1436  the skip-rule pin, claiming `mark_labels_of`
        #                -> :1383, inside `read_capture`
        #   recorded :1413  the length-test pin, claiming `read_capture`
        #                -> :1554, inside `take_capture_row`
        #
        # The write-up's table of wrong rows names the *other* skip-rule pin,
        # recorded :1531, which does resolve into `mark_labels_of` and is a real
        # mis-resolution -- but its `what` opens "and so does the partition",
        # names no function where the sentence starts, and `subject_of` skips it
        # before any comparison. So this case reproduces one of that table's two
        # rows, not both, and the blind side is stated rather than papered over:
        # `docs/findings/0769-citation-ambiguity-and-what-a-red-means.md`.
        wrong = [f"{path}:{lineno} -> {found}, in {enclosing!r}, claiming "
                 f"{claimed!r}"
                 for path, lineno, found, claimed, enclosing
                 in self.citations_about_a_function()
                 if enclosing is not None and enclosing != claimed]
        self.assertEqual(
            wrong, [],
            "a citation names one function and resolves into another, so the "
            "text found its line and the claim is about a different one. The "
            "quoted text has to carry its function with it:\n  "
            + "\n  ".join(wrong))

    def test_the_citations_are_read_from_the_table_and_not_handed_over(self):
        # Otherwise the case above passes on an empty list and proves nothing --
        # the failure `test_measure_mark_provenance_citations.py` records for a
        # join whose two sets are both empty.
        about = self.citations_about_a_function()
        self.assertTrue(about, "no citation's claim names a function, so the "
                               "case above would pass on nothing")
        # And the ones it did read resolved to a real line of a real file.
        for path, _lineno, found, _claimed, _enclosing in about:
            self.assertIsNotNone(found, f"{path} resolved to nothing")
            self.assertGreater(found, 0)


if __name__ == '__main__':
    unittest.main()