#!/usr/bin/env python3
"""Offline checks for check_source_citations.py: the committed tree and a
scratch one.

The tool's failure mode is silence, and here it is a specific one. A `:NNN` in a
`docs/findings/` page or an `ec/annotations/` note that has drifted onto a
different construct produces no error at all: the sentence reads exactly as well
with one number as with another, nothing in the tree is red, and the figure a
reader would re-derive is wrong. So what is pinned here is the *whole*
mechanism and then each way it can stop working.

Three classes, in the order a reader needs them:

  * **The committed tree agrees** -- every declared citation still names code
    the target has, and the run prints a held count, a declined count and a
    skipped count that are all non-zero. The last part matters most: a checker
    that located nothing must say so rather than exit 0, because "checked
    nothing" and "found nothing" read alike from the exit code.
  * **The four verdicts each reject what they should.** A span check whose
    boundaries were loosened would pass a citation pointing outside the
    construct; one that held the line exactly would redden every branch that
    grows the target. Both directions are asserted below, because the tool's
    whole argument is the span between them.
  * **A reworded citation is reported, not passed.** The declared list holds a
    locator -- a regular expression over the citing file's own prose -- precisely
    so that a sentence which stops naming the code stops matching. A checker
    that fell back to "no citation found, nothing to check" would report that
    page clean.

The scratch tree is built by copying the committed files, because the fixtures
worth having are the real sentences: a paraphrase that happened to keep the
right number would be a control passing for the wrong reason.

Every case derives the numbers it needs from the committed tree rather than
spelling them, so a case that grows stale fails as the thing it is about rather
than as an arithmetic difference. No case asserts a count of the repository.
"""
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

HERE = Path(__file__).parent
REPO = HERE.parent.parent
spec = importlib.util.spec_from_file_location(
    'check_source_citations', HERE / 'check_source_citations.py')
csc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(csc)


def run_main(argv) -> tuple:
    """(exit code, stdout, stderr) with `argv` in place and both streams
    captured, the way a reader would run it -- the return code and the lines it
    prints are the tool's whole output surface."""
    err, out, saved = io.StringIO(), io.StringIO(), sys.argv
    sys.argv = argv
    try:
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            rc = csc.main()
    finally:
        sys.argv = saved
    return rc, out.getvalue(), err.getvalue()


def run_check(repo) -> tuple:
    """(problems, resolved, held, noted, declined, skipped, report) with the
    report captured.

    The report goes to a buffer rather than to the runner's stdout, so a case
    reads the numbers the tool derived rather than parsing its own fixture.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = csc.check(repo, stream=buf)
    return result + (buf.getvalue(),)


def scratch_tree(mutate=None) -> str:
    """A throwaway copy of the target and the declaring files.

    `mutate` is called with `(relpath, text)` per file and may return a new text.
    Only the files the tool reads are copied, which is the tool's own scope made
    literal: a scratch tree this small cannot pass by carrying a copy of
    something the checker does not look at.
    """
    root = tempfile.mkdtemp(prefix="source-citations-")
    targets = sorted({target for target, _, _, _ in csc.ANCHORS})
    for rel in targets + [name for name, _ in csc.CITATIONS]:
        target = os.path.join(root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        text = Path(REPO, rel).read_text(encoding="utf-8")
        if mutate is not None:
            text = mutate(rel, text)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
    return root


def anchor_span(key) -> tuple:
    """(first, last) of `key`'s span in the committed target, read by the tool.

    A hardcoded copy in this file would go stale silently the next time the
    target grows, and the cases that use it are about the tool's *relationships*
    between anchors and spans -- which numbers they are is the tool's business.
    """
    needle = next(n for _, k, _, n in csc.ANCHORS if k == key)
    target = next(t for t, k, _, _ in csc.ANCHORS if k == key)
    first, last = csc.resolve(csc.read(Path(REPO, target)), needle)
    assert first is not None, f"the committed target does not hold {key}"
    return first, last


class TheCommittedTree(unittest.TestCase):
    """The real thing: the committed prose and the committed tool agree.

    It no longer goes red when an edit to the target moves an anchor's line:
    what it holds is that each citation still names a construct the target has,
    uniquely, and that the sentence still says which construct.
    """

    def test_the_committed_citations_hold(self):
        rc, out, err = run_main(['check_source_citations.py'])
        self.assertEqual(rc, 0, err)
        self.assertIn('name an anchor the target still has', out)

    def test_every_anchor_resolves_and_is_printed_with_its_span(self):
        # The report leads with the derived table, so a reader can see what each
        # citation is held *to* before reading any verdict. Every anchor in the
        # declared list, not a sample of them.
        _, resolved, _, _, _, _, out = run_check(REPO)
        self.assertEqual(resolved, len(csc.ANCHORS))
        for _, key, what, _ in csc.ANCHORS:
            with self.subTest(anchor=key):
                first, last = anchor_span(key)
                self.assertIn(f"  {key}: ", out)
                self.assertIn(f":{first}-{last}  {what}", out)

    def test_the_run_says_what_it_held_declined_and_skipped(self):
        # Without this a rule that stopped looking and a tree with nothing to
        # look at print the same thing, and "checked nothing" would read from
        # the exit code exactly like "found nothing". All three counts are
        # asserted non-zero rather than pinned: they move with every re-point,
        # and a figure to re-point is a figure this repository should not carry.
        _, out, _ = run_main(['check_source_citations.py'])
        match = re.search(r'(\d+) citation\(s\) name an anchor the target still '
                          r'has, \d+ inside a span rather than on its opening '
                          r'line, (\d+) declined as not this tool\'s, (\d+) '
                          r'skipped as superseded', out)
        self.assertIsNotNone(match, out)
        for figure in match.groups():
            self.assertGreater(int(figure), 0)

    def test_the_skip_is_counted_rather_than_silent(self):
        # The #249 quoted predecessors on the dispatch page are quoted material,
        # so their three pins are passed over. A skip that is not announced
        # anywhere is a skip that looks like a check.
        _, _, _, _, _, skipped, out = run_check(REPO)
        self.assertGreater(skipped, 0)
        self.assertIn('skip (quoted material)', out)

    def test_a_file_the_list_declares_no_citation_for_still_reports(self):
        # One declaring file holds no live citation this tool claims. A file
        # with nothing to check must still say what it declined, or "no citation
        # here" and "no check ran" read alike.
        _, _, held, _, _, _, out = run_check(REPO)
        self.assertGreater(held, 0)
        page = "docs/findings/xdata-census-rederivation-checklist.md"
        self.assertIn(f"  {page}: 0 declared citation(s) read, ", out)
        self.assertIn(f"declined {page}:", out)


class ACitationOutsideTheSpan(unittest.TestCase):
    """The defect itself: a number that names a line outside the construct the
    sentence gives it to. #868's own live sentence was the extreme case, where
    the subject was gone; this is the ordinary shape."""

    def recite(self, rel, key, line):
        """A `mutate` that makes `rel`'s first `key` citation cite `:line`.

        The number is found by the declared locator rather than spelled here:
        the prose is not held to today's line, so the committed number may
        already differ from the anchor's. The locator is matched over the raw
        text with its spaces widened to any whitespace, because the prose wraps
        where the collapsed text the tool reads does not.
        """
        locator = next(loc for f, declared in csc.CITATIONS if f == rel
                       for k, loc in declared if k == key)
        pattern = re.compile(locator.replace(" ", r"\s+"))

        def mutate(path, text):
            if path != rel:
                return text
            match = pattern.search(text)
            assert match, f"{rel} carries no {key} citation to move"
            return text[:match.start(1)] + str(line) + text[match.end(1):]
        return mutate

    def test_a_line_outside_the_anchors_span_is_reported(self):
        # One line above the construct's opening line. This is what a rule that
        # accepted "any line in the file" would pass, and what the `:770` case
        # looked like from the reader's side.
        first, _ = anchor_span("map_columns")
        rel = "docs/findings/xdata-4-4-identity-rederivation.md"
        root = scratch_tree(self.recite(rel, "map_columns", first - 1))
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn(f"cites :{first - 1} for map_columns, whose span is", err)
        self.assertIn('names a line outside the construct', err)

    def test_the_report_names_the_anchors_current_line(self):
        # Both halves of the failure: the number the prose cites, and the span
        # it should have been in, so a reader following the prose is not sent
        # back to `grep`. A failure goes to stderr, the way `main` writes it.
        first, last = anchor_span("corpus_wide_invariant")
        rel = "ec/annotations/xdata-086x-dispatch.md"
        root = scratch_tree(self.recite(rel, "corpus_wide_invariant", first - 1))
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn(f"cites :{first - 1} for corpus_wide_invariant, whose span is "
                      f":{first}-{last}", err)

    def test_a_line_inside_the_span_but_off_its_opening_line_is_noted(self):
        # The region claim. The sentence says the invariant holds the buckets,
        # not that it opens on one line, so this is a note and the run stays
        # green -- reddening it would be the line rule again in a span's
        # clothing, which is the failure this design exists to avoid.
        first, last = anchor_span("corpus_wide_invariant")
        inside = first + 1 if last > first else first
        rel = "ec/annotations/xdata-086x-dispatch.md"
        root = scratch_tree(self.recite(rel, "corpus_wide_invariant", inside))
        self.addCleanup(shutil.rmtree, root)
        rc, out, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 0, err)
        self.assertIn(f"note {rel}", out)
        self.assertIn("inside that anchor's span", out)
        self.assertIn("the sentence claims a region", out)


class ThePreFixPage(unittest.TestCase):
    """The page as it read before this change's correction, which is the tree
    #868 was opened against.

    `AGoneAnchor` proves the gone-anchor verdict on a scratch target whose anchor
    string is mutated. That is the mechanism, but it is a synthetic scenario, and
    asserting "the fourth verdict catches this sentence" on the strength of it
    would be the overclaim a previous round of review caught: on the real pre-fix
    page the `:770` cell is **declined**, because `HAND_CHECKED` was never a
    declared anchor, so that verdict has nothing to fire on. What does fire is
    the reworded-citation verdict, since the corrected prose no longer matches the
    locators written against it. Both are asserted here against the real
    sentence, so the write-up's account of this page is demonstrated rather than
    asserted.
    """

    # The pre-fix paragraph, verbatim from `origin/main`'s dispatch page. Kept as
    # text rather than as a number the tool is asked to find, because the point
    # of the case is what happens to a sentence whose subject is gone -- not that
    # a line moved.
    PREFIX = "The row is not the tool's own sum: `HAND_CHECKED[\"0x0860\"]` at\n" \
             "`ec/tools/xdata_register_map.py:770` pins exactly those buckets, and the\n" \
             "self-test's \"hand-checked direction oracle\" assertion at `:2250-2256` fails\n" \
             "loudly if a generated row ever parts company with it.\n"

    def pre_fix_tree(self) -> str:
        """A scratch tree carrying the pre-fix sentence in place of the corrected one.

        The corrected paragraph is dropped and the pre-fix text put in its place,
        so the tree is the live page with the sentence #868 was about. Every other
        file is the committed one, which is what makes the run's verdict about the
        sentence rather than about a stale fixture.
        """
        rel = "ec/annotations/xdata-086x-dispatch.md"

        def swap(path, text):
            if path != rel:
                return text
            # The corrected paragraph is the one naming `CLASSIFIER_SHAPE`'s
            # snippets; drop from there to the paragraph's end and put the
            # pre-fix sentence where it stood.
            at = text.index("The direction rule is held instead by")
            start = text.rindex("\n\n", 0, at) + 2
            stop = text.index("\n\n", at)
            return text[:start] + self.PREFIX + text[stop:]

        root = scratch_tree(swap)
        self.addCleanup(shutil.rmtree, root)
        return root

    def test_the_gone_subject_cell_is_declined_not_failed(self):
        # `:770` names `HAND_CHECKED`, which no declared locator claims. The
        # correct reading of that cell is "not this tool's declared list", and a
        # tool that failed it would be claiming a verdict it has no anchor for.
        # Both halves are asserted: nothing fails on that number, and it is
        # reported by name rather than silently dropped.
        root = self.pre_fix_tree()
        problems, _, _, _, _, _, out = run_check(root)
        self.assertFalse([p for p in problems if ':770' in p],
                         "the :770 cell is failed without a declared anchor to "
                         f"fail it against: {problems}")
        self.assertIn('declined ec/annotations/xdata-086x-dispatch.md:', out)
        self.assertIn('cites :770', out)

    def test_the_reworded_citation_verdict_is_what_actually_fires(self):
        # The corrected prose's locators do not match the pre-fix sentence, so
        # the run reports those as reworded. This is the branch that reports this
        # page, and it is a different one from the gone-anchor verdict.
        root = self.pre_fix_tree()
        problems, _, _, _, _, _ = run_check(root)[:6]
        reworded = [p for p in problems if 'is not found by this method' in p]
        self.assertTrue(reworded, problems)
        self.assertTrue(any('hand_oracle_removed' in p for p in reworded),
                        reworded)

    def test_no_declared_anchor_names_a_subject_the_target_lacks(self):
        # Why the fourth verdict cannot reach this page: every declared needle
        # resolves exactly once in its own target today, so none of them is
        # `HAND_CHECKED`. An anchor declared for a subject the tree has already
        # retracted would redden the committed tree for good, which is the
        # opposite of what a gate is for -- so the decision is pinned here, with
        # the target read per anchor rather than one file assumed.
        for target, key, _, needle in csc.ANCHORS:
            with self.subTest(anchor=key):
                text = Path(REPO, target).read_text(encoding="utf-8")
                self.assertEqual(text.count(needle), 1)


class AGoneAnchor(unittest.TestCase):
    """The case #868 was opened for: the subject of the sentence does not exist
    in the file the sentence names.

    This is the mechanism, on a scratch target. The page the issue was actually
    opened against is `ThePreFixPage`, and the two do not agree about which
    verdict fires -- which is why that class exists rather than this one being
    read as the demonstration.
    """

    def test_an_anchor_the_target_no_longer_holds_is_reported(self):
        # `CLASSIFIER_SHAPE` going away is a real change to the classifier. What
        # must not happen is the checker reading it as "nothing to check" and
        # exiting 0. Never "absent" -- CLAUDE.md's rule, and
        # `ec/annotations/registers.yaml`'s own caveat on the same point.
        def rewrite(rel, text):
            return text.replace("CLASSIFIER_SHAPE = (", "CLASSIFIER_RENAMED = (", 1) \
                if rel.endswith("xdata_register_map.py") else text

        root = scratch_tree(rewrite)
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn("is not found by this method", err)
        self.assertIn("not an absence", err)

    def test_a_gone_anchor_takes_its_citations_down_with_it(self):
        # The citations naming the gone anchor must not be reported as *passed*
        # in the meantime. A checker that skipped them because their anchor was
        # missing would go green on the exact tree this issue is about.
        def rewrite(rel, text):
            return text.replace("CLASSIFIER_SHAPE = (", "CLASSIFIER_RENAMED = (", 1) \
                if rel.endswith("xdata_register_map.py") else text

        root = scratch_tree(rewrite)
        self.addCleanup(shutil.rmtree, root)
        problems, resolved, held, _, _, _ = run_check(root)[:6]
        self.assertTrue(problems)
        self.assertLess(resolved, len(csc.ANCHORS))

    def test_an_anchor_that_became_ambiguous_is_reported(self):
        # Two matches is not a first match. A needle that grew a second copy is
        # a declaration that has itself gone stale, and the failure has to say so
        # rather than pick one.
        def clone(rel, text):
            return text + '\nCLASSIFIER_SHAPE = (\n' \
                if rel.endswith("xdata_register_map.py") else text

        root = scratch_tree(clone)
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn("no longer unique", err)

    def test_a_target_the_tool_cannot_read_is_reported_not_passed(self):
        root = scratch_tree()
        self.addCleanup(shutil.rmtree, root)
        os.remove(os.path.join(root, sorted({t for t, _, _, _ in csc.ANCHORS})[0]))
        rc, _, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn("a broken check, not an empty one", err)

    def test_a_declaring_file_the_tool_cannot_read_is_reported(self):
        root = scratch_tree()
        self.addCleanup(shutil.rmtree, root)
        os.remove(os.path.join(root, csc.CITATIONS[0][0]))
        rc, _, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn("a broken check, not a clean file", err)


class ARewordedCitation(unittest.TestCase):
    """The declared list holds prose, so prose that changes is itself a change
    this tool must notice rather than quietly stop checking."""

    def test_a_citation_reworded_out_of_shape_is_reported(self):
        def strip_code(rel, text):
            # The sentence keeps its number and loses the construct it was citing
            # -- the drift back to a bare `:NNN` that the whole mechanism exists
            # to prevent, and the one a number-only checker cannot see.
            return text.replace("`MAP_COLUMNS` at `xdata_register_map.py:",
                                "the map table at `xdata_register_map.py:", 1) \
                if rel.endswith("xdata-4-4-identity-rederivation.md") else text

        root = scratch_tree(strip_code)
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn("a declared map_columns citation is not found by this "
                      "method", err)

    def test_a_citation_no_locator_matched_is_declined_not_passed(self):
        # A target citation in a scoped file that the declared list says nothing
        # about. Declining it is what makes the count mean something: a checker
        # that silently ignored unclaimed sites would report the same file clean.
        def add_site(rel, text):
            return text + "\nA new claim, citing `xdata_register_map.py:999`.\n" \
                if rel.endswith("xdata-4-4-identity-rederivation.md") else text

        root = scratch_tree(add_site)
        self.addCleanup(shutil.rmtree, root)
        rel = "docs/findings/xdata-4-4-identity-rederivation.md"
        _, _, held, _, declined, _, out = run_check(root)[:7]
        self.assertGreater(held, 0)
        self.assertIn(f"declined {rel}:", out)
        self.assertIn("cites :999", out)
        # The declared citation in the same file is still held, so the decline
        # is reported alongside work done rather than instead of it.
        self.assertGreater(declined, 0)

    def test_the_rest_of_the_run_is_still_reported(self):
        # One defect does not stop the report. Every other anchor still resolves
        # and every other citation is still read, held and counted.
        def rewrite(rel, text):
            return text.replace("CLASSIFIER_SHAPE = (", "CLASSIFIER_RENAMED = (", 1) \
                if rel.endswith("xdata_register_map.py") else text

        root = scratch_tree(rewrite)
        self.addCleanup(shutil.rmtree, root)
        _, resolved, held, _, declined, skipped = run_check(root)[:6]
        self.assertGreater(resolved, 0)
        self.assertLess(resolved, len(csc.ANCHORS))
        self.assertGreater(held, 0)
        self.assertGreater(declined, 0)
        self.assertGreater(skipped, 0)

    def test_a_run_that_located_nothing_is_reported_rather_than_passing(self):
        # Every locator reworded out of shape at once: the tool must still say
        # it read no citation, not exit 0 on a tree it checked nothing in.
        def strip_all(rel, text):
            for _, declared in csc.CITATIONS:
                for key, locator in declared:
                    text = re.sub(locator, "nothing matches this", text)
            return text

        root = scratch_tree(strip_all)
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn("is not found by this method", err)


class TheDeclaredList(unittest.TestCase):
    """The list's own shape, so a new entry cannot be added half-formed."""

    def test_every_anchor_is_held_by_at_least_one_declared_citation(self):
        # An anchor nothing cites is a declaration with no consumer, and a
        # consumer is what keeps its needle from rotting unnoticed.
        cited = {key for _, declared in csc.CITATIONS for key, _ in declared}
        for _, key, _, _ in csc.ANCHORS:
            with self.subTest(anchor=key):
                self.assertIn(key, cited)

    def test_every_declared_locator_captures_exactly_one_group(self):
        # The number is group 1 by construction, and a locator added with a
        # non-capturing group in front of it would read the wrong digits
        # without failing here.
        for rel, declared in csc.CITATIONS:
            for key, locator in declared:
                with self.subTest(file=rel, anchor=key):
                    self.assertEqual(re.compile(locator).groups, 1)

    def test_every_declared_citation_resolves_in_the_committed_tree(self):
        # A locator that matches nothing today is a declaration that has already
        # gone stale, and the run says so -- this holds the same property from
        # the other side, where a fix made it true again.
        for rel, declared in csc.CITATIONS:
            text = csc.read(Path(REPO, rel))
            collapsed, _ = csc.flat(text)
            for key, locator in declared:
                with self.subTest(file=rel, anchor=key):
                    self.assertTrue(re.compile(locator).search(collapsed),
                                    f"{rel} declares {key} but the locator does "
                                    f"not match it")

    def test_the_anchor_targets_are_the_files_the_pointer_scans(self):
        # `pointer()` is built from `ANCHORS`' own targets, so a target added to
        # the anchor list without a corresponding pointer edit would leave its
        # citations invisible. This holds the two in step.
        names = sorted({os.path.basename(t) for t, _, _, _ in csc.ANCHORS})
        pattern = csc.pointer([t for t, _, _, _ in csc.ANCHORS])
        for name in names:
            with self.subTest(target=name):
                self.assertTrue(pattern.search(f"see {name}:123 here"))

    def test_a_span_runs_from_the_anchor_to_the_end_of_its_construct(self):
        # The mechanism the four verdicts rest on. Read from the target rather
        # than spelled, so a construct that grew is not a stale expectation.
        for _, key, _, _ in csc.ANCHORS:
            with self.subTest(anchor=key):
                first, last = anchor_span(key)
                self.assertGreaterEqual(last, first)

    def test_the_supersession_vocabulary_is_copied_not_imported(self):
        # A tool reaching into a sibling for its vocabulary is a tool whose
        # subject is the sibling. Asserted as a fact about this module's globals
        # because the alternative -- importing `check_citation_lines` -- would
        # couple the two tools and is the thing being refused.
        for name in ("QUOTE", "MARKERS", "ANNOUNCES"):
            with self.subTest(name=name):
                self.assertIn(name, vars(csc))

    def test_the_failure_text_names_the_tree_it_actually_read(self):
        # The report must not carry a provenance claim it cannot support. This
        # tool's numbers are reads of whatever tree `--repo` names, so a constant
        # naming a commit in the failure text is a claim about a tree the run may
        # not have read at all -- a scratch run would then report another
        # revision's figures as its own. The named path is the only provenance
        # here that is true of every run.
        root = scratch_tree(lambda rel, text: text.replace(
            "CLASSIFIER_SHAPE = (", "CLASSIFIER_RENAMED = (", 1)
            if rel.endswith("xdata_register_map.py") else text)
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_source_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn(root, err)
        self.assertNotIn('measured on', err)


class TheCensus(unittest.TestCase):
    """`--census` prints the class census, which the write-up does not record.

    The point of these is that the census is *printed* rather than written down
    as a figure: a count of the repository's own prose is out of date at the
    next merge, which is CLAUDE.md's rule and the reason this mode exists at
    all. So nothing here pins a number -- what is held is that every class is
    reported, that the classes partition the sites, and that a file walked by
    the census is named with its own row.
    """

    def census_out(self) -> str:
        rc, out, err = run_main(['check_source_citations.py', '--census'])
        self.assertEqual(rc, 0, err)
        return out

    def test_every_class_is_reported(self):
        # A census that printed only the class it found most of would read as
        # the others being empty.
        out = self.census_out()
        for name in ("live", "quoted-superseded", "declines to attribute"):
            with self.subTest(cls=name):
                self.assertRegex(out, rf"(?m)^\s+\d+\s+{re.escape(name)}$")

    def test_the_census_names_a_declaring_file_with_its_own_row(self):
        # The walk covers the tree, not just `CITATIONS`, which is what makes
        # the held count in a normal run mean something.
        out = self.census_out()
        for rel, _ in csc.CITATIONS:
            with self.subTest(file=rel):
                self.assertIn(f"  {rel}: ", out)

    def test_a_quoted_citation_is_censused_as_quoted_not_live(self):
        # The dispatch page's #249 predecessors are in blockquotes and meant to
        # stay wrong. A census that counted them as live would send a reader to
        # repoint figures §4a-4d wants left visible. What "not live" means for
        # them is a non-zero quoted-superseded count, so that is what is held --
        # the live figure is not asserted, being a number this repository should
        # not carry.
        out = self.census_out()
        rel = "ec/annotations/xdata-086x-dispatch.md"
        row = next(line for line in out.splitlines() if line.startswith(f"  {rel}: "))
        quoted = re.search(r"(\d+) quoted-superseded", row)
        self.assertIsNotNone(quoted, row)
        self.assertGreater(int(quoted.group(1)), 0)

    def test_a_target_citation_is_never_also_counted_as_a_bare_one(self):
        # The two walks must partition the sites. The bare pattern's lookbehind
        # is what keeps them apart -- a `:` preceded by a `.py` is the tail of
        # an explicit citation, not an unattributable number -- so a loosened
        # lookbehind would silently count every explicit cell twice and make
        # the classes sum to more than the population.
        pattern = csc.pointer(sorted({t for t, _, _, _ in csc.ANCHORS}))
        bare = re.compile(r"(?<![\w./-]):(\d+)(?:-(\d+))?(?![\w/])")
        for rel, _ in csc.CITATIONS:
            collapsed, _ = csc.flat(csc.read(Path(REPO, rel)))
            explicit = [(m.start(), m.end()) for m in pattern.finditer(collapsed)]
            bare_spans = [m.span() for m in bare.finditer(collapsed)]
            with self.subTest(file=rel):
                # A citation is "explicit" from its first character to its last,
                # and a bare number inside that range would be the same site
                # counted twice. `finditer` positions are compared rather than
                # the text, because two citations can spell the same number.
                for start, end in explicit:
                    self.assertFalse(
                        [span for span in bare_spans if start <= span[0] < end],
                        f"a site in {rel} is counted as both an explicit and a "
                        f"bare citation: {collapsed[start:end]!r}")

    def test_the_census_classes_partition_the_sites(self):
        # Two readings of one tree, and the relation between them is the point:
        # the census is the whole population, the check is a declared scope
        # inside it. So what the check holds and declines together must be no
        # larger than what the census calls live -- a scope that reported more
        # live cells than the tree has would be describing a different
        # population.
        out = self.census_out()
        census_live = int(re.search(r"(?m)^\s+(\d+)\s+live$", out).group(1))
        _, _, held, _, declined, skipped, _ = run_check(REPO)[:7]
        self.assertGreater(held, 0)
        self.assertGreater(declined, 0)
        self.assertGreater(skipped, 0)
        self.assertLessEqual(held + declined, census_live)


if __name__ == '__main__':
    unittest.main()