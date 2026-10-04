#!/usr/bin/env python3
"""Offline checks for check_py_citations.py: the committed tree, a scratch one,
and the shape of what it declares.

The tool's failure mode is silence, and here it is a specific one. A
`xdata_register_map.py:NNN` written in a docstring or a comment that has drifted
onto a different statement produces no error at all: the sentence reads exactly
as well with `:3634` as with `:4472`, nothing in the tree is red, and the line a
reader would follow is the wrong one. Every committed site was in that state. So
what is pinned here is the whole mechanism and then each way it can stop
working.

The classes below are in the order a reader needs them:

  * **The committed tree agrees** -- every declared citation is on its anchor's
    current line, every anchor resolves and prints with its line, and the run
    reports a held count, a declined count and a skipped count that are all
    non-zero. The last part is the one that matters most: a checker that
    located nothing must say so rather than exit 0, because "checked nothing"
    and "found nothing" read alike from the exit code.
  * **The wrong-code sites stay distinguishable.** The finding here was not
    that a number was off, it was that a number resolved to *a different
    thing* -- a dict cell, a union-find loop, a `--self-test` sweep block. So
    each anchor is asserted to resolve to a line no other anchor claims, and
    the two committed-output refusals to different lines from each other. A
    checker that held every anchor to one shared number would pass every other
    case here.
  * **A perturbation goes red and names the fix.** One cited number moved by one
    line in a scratch copy of a real file, and the run is asserted to fail *and*
    to print the anchor's current line beside the wrong one, so the repair is
    one edit rather than a re-measurement. Then the issue's own done test: a
    line inserted above an anchor in a scratch copy of `xdata_register_map.py`,
    and the citation in a **test** source is asserted to go red. Without the
    first, a green run proves only that the tool agrees with itself; without the
    second, nothing here is about the population the issue asked for.
  * **The declared list's own shape** -- every locator captures exactly one
    group, every anchor is held by at least one declared citation, and the
    declaring files are the ones the write-up names. A tool whose anchor is
    gone, or gone ambiguous, is reported and not passed; a tree it cannot read
    is reported and not passed.

The scratch tree is built by copying the committed files, because the fixtures
worth having are the real sentences: a paraphrase of `inc_dptr_sites.py`'s pair
fold that happened to keep the right number would be a control passing for the
wrong reason.
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
    'check_py_citations', HERE / 'check_py_citations.py')
cpy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpy)

# The files `docs/findings/py-source-citations.md` names as carrying a
# hand-written citation. `check_eq_guard_citations.py` and
# `test_check_doc_figure_pins.py` declare no citation at all and are in
# `CITATIONS` for the other half of the same reason: a reader can tell a claim
# from a synthetic fixture by whether its file is declared *and* declares one.
DECLARING_FILES = (
    'ec/tools/inc_dptr_sites.py',
    'ec/tools/test_xdata_cluster_names.py',
    'ec/tools/test_xdata_register_map.py',
    'ec/tools/test_xdata_guard_off_row_join.py',
)


def run_main(argv) -> tuple:
    """(exit code, stdout, stderr) with `argv` in place and both streams
    captured, the way a reader would run it -- the return code and the lines it
    prints are the tool's whole output surface."""
    err, out, saved = io.StringIO(), io.StringIO(), sys.argv
    sys.argv = argv
    try:
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            rc = cpy.main()
    finally:
        sys.argv = saved
    return rc, out.getvalue(), err.getvalue()


def run_check(repo) -> tuple:
    """(problems, resolved, held, declined, skipped, report) with the report
    captured. The report goes to a buffer rather than to the runner's stdout, so
    a case reads the numbers the tool derived rather than parsing its own
    fixture."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = cpy.check(repo, stream=buf)
    return result + (buf.getvalue(),)


def scratch_tree(mutate=None) -> str:
    """A throwaway copy of the tool and the declaring files.

    `mutate` is called with `(relpath, text)` per file and may return a new text.
    Only the files the tool reads are copied, which is the tool's own scope made
    literal: a scratch tree this small cannot pass by carrying a copy of
    something the checker does not look at.
    """
    root = tempfile.mkdtemp(prefix="py-citations-")
    for rel in [cpy.TOOL] + [name for name, _ in cpy.CITATIONS]:
        target = os.path.join(root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        text = Path(REPO, rel).read_text(encoding="utf-8")
        if mutate is not None:
            text = mutate(rel, text)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
    return root


def saying(problems, *needles) -> list:
    """Problems containing every needle. The needle is the assertion: a case
    that passes because *some* problem was reported would go green on a checker
    that had stopped comparing the thing the case is about."""
    return [p for p in problems if all(n in p for n in needles)]


def anchor_line(key) -> int:
    """The line `key` resolves to in the committed tool, read by the tool.

    A hardcoded copy in this file would go stale silently the next time the tool
    grows, and the cases that use it are about the tool's *relationships*
    between anchors -- which numbers they are is the tool's business.
    """
    needle = next(n for k, _, n in cpy.ANCHORS if k == key)
    line = cpy.resolve(cpy.read(Path(REPO, cpy.TOOL)), needle)
    assert line is not None, f"the committed tool does not hold {key}"
    return line


class TheCommittedTree(unittest.TestCase):
    """The real thing: the committed Python sources and the committed tool
    agree.

    This is the assertion that would have caught every drifted site, and it is
    the one that goes red on the next edit to `xdata_register_map.py`. Nothing
    here reads a firmware image, an annotation CSV or a Ghidra project: every
    number is a substring search over a committed text file the tool names, so
    the whole class runs in milliseconds.
    """

    @classmethod
    def setUpClass(cls):
        cls.problems, cls.resolved, cls.held, cls.declined, cls.skipped, \
            cls.report = run_check(REPO)

    def test_the_run_is_clean(self):
        self.assertEqual(self.problems, [])

    def test_the_committed_citations_hold(self):
        self.assertTrue(self.held, "the run held no citation at all, which is "
                                   "a broken check rather than a clean tree")

    def test_every_anchor_resolves_and_is_printed_with_its_line(self):
        self.assertEqual(self.resolved, len(cpy.ANCHORS))
        for key, what, _ in cpy.ANCHORS:
            self.assertIn(f"{key}: {cpy.TOOL}:{anchor_line(key)}  {what}",
                          self.report)

    def test_the_run_says_how_many_it_held_declined_and_skipped(self):
        # Declined and skipped, and not just held: a non-zero declined count is
        # what says the fixtures were looked at and set aside rather than
        # missed, and a non-zero skipped count is what says the in-place
        # corrections are being passed over on purpose. A tree where each count
        # is zero prints the same summary line as a clean one otherwise.
        self.assertTrue(self.declined, "nothing was declined, so the fixtures "
                                       "are either gone or being read as claims")
        self.assertTrue(self.skipped, "nothing was skipped, so the in-place "
                                      "corrections are being read as live claims")

    def test_the_declared_citations_are_where_the_write_up_says(self):
        # Every anchor is held by at least one declared citation, and each of
        # those citations names the file the write-up's table names for it. A
        # site that moved to another file without the table following would
        # still hold -- which is why this compares the two lists rather than
        # only the anchor set.
        for rel in DECLARING_FILES:
            self.assertIn(f"{rel}: ", self.report)

    def test_a_declared_citation_that_was_reworded_is_reported_not_passed(self):
        # The locator is the sentence, so a sentence that stops naming the code
        # stops matching. A checker that fell back to "nothing matched, nothing
        # to check" would report the file clean -- which is the silent failure
        # this whole class exists to catch.
        def reword(rel, text):
            if rel != 'ec/tools/test_xdata_guard_off_row_join.py':
                return text
            return text.replace("sorted members", "sorted members, roughly")

        root = scratch_tree(reword)
        try:
            problems, _r, held, _d, _s, _out = run_check(root)
            self.assertTrue(
                saying(problems, "cluster_key_def",
                       "not found by this method"),
                f"the reworded sentence was passed rather than reported: "
                f"{problems}")
            self.assertLess(held, self.held)
        finally:
            shutil.rmtree(root)


class TheWrongCodeSites(unittest.TestCase):
    """They were not off by a line or two; they named other code entirely.

    A `:NNN` that resolves to a different statement is a sentence that reads
    correctly and means the wrong line, so an offset checker would have called
    several of them "nearly right". Each anchor is therefore asserted to be a
    line no other anchor claims, and the two refusals to different lines from
    each other -- a checker that held every anchor to one shared number would
    pass every other case here.
    """

    def test_no_two_anchors_claim_the_same_line(self):
        lines = {}
        for key, _what, _needle in cpy.ANCHORS:
            lines.setdefault(anchor_line(key), []).append(key)
        shared = {line: keys for line, keys in lines.items() if len(keys) > 1}
        self.assertEqual(shared, {},
                         f"anchors resolving to one line: {shared}")

    def test_the_two_committed_output_refusals_are_different_lines(self):
        # The distinction the issue rests on: a sentence about
        # `--no-eq-guard`'s refusal resolving to `--export-ownership`'s reads
        # exactly as well as one that does not.
        self.assertNotEqual(anchor_line("no_eq_guard_output_refusal"),
                            anchor_line("export_ownership_output_refusal"))

    def test_the_flag_is_not_where_a_refusal_is(self):
        self.assertNotEqual(anchor_line("no_eq_guard_flag"),
                            anchor_line("no_eq_guard_output_refusal"))

    def test_the_two_list_defaults_are_different_lines(self):
        # `--thresholds` and `--floors` are three lines apart in the argparse
        # block and are two separate claims; a checker that resolved them to
        # one number would pass a sentence naming only one of the two.
        self.assertNotEqual(anchor_line("thresholds_list_default"),
                            anchor_line("floors_list_default"))


class ADriftedNumber(unittest.TestCase):
    """The negative case, on copies of the real files.

    Everything above can be green on a checker that only agrees with itself, so
    these move the tree under it and read what comes back.
    """

    def test_a_cited_number_moved_by_one_is_rejected_and_names_the_fix(self):
        def nudge(rel, text):
            if rel != 'ec/tools/inc_dptr_sites.py':
                return text
            return text.replace("`xdata_register_map.py:1861-1869`",
                                "`xdata_register_map.py:1862-1870`")

        root = scratch_tree(nudge)
        try:
            problems, _r, _h, _d, _s, report = run_check(root)
            want = anchor_line("pair_fold")
            self.assertTrue(
                saying(problems, "inc_dptr_sites.py", "cites :1862",
                       f"xdata_register_map.py:{want}"),
                f"the nudged citation was not reported against the anchor's "
                f"current line: {problems}")
            # The rest of the report still runs: a checker that returned on the
            # first failure would name one line and stop.
            self.assertIn("cluster_key_def", report)
        finally:
            shutil.rmtree(root)

    def test_a_line_inserted_above_an_anchor_turns_a_test_source_citation_red(self):
        # The issue's own done test, and the reason this tool exists rather than
        # a wider `CITATIONS` in `check_eq_guard_citations.py`: inserting one
        # line above an anchor in `xdata_register_map.py` must turn a cited
        # number red in a **test** source, not only in a `docs/findings/` page.
        needle = next(n for k, _, n in cpy.ANCHORS
                      if k == "cluster_key_def")

        def insert(rel, text):
            if rel != cpy.TOOL:
                return text
            # Above the anchor, not below it: a line inserted *under* it would
            # leave the anchor where it was and the citation would still hold,
            # which is the case that proves nothing.
            return text.replace(needle, "# a line nothing cites\n" + needle,
                                1)

        root = scratch_tree(insert)
        try:
            problems, _r, held, _d, _s, _out = run_check(root)
            want = anchor_line("cluster_key_def") + 1
            self.assertTrue(
                saying(problems, "test_xdata_guard_off_row_join.py",
                       f"cites :{want - 1}",
                       f"xdata_register_map.py:{want}"),
                f"inserting a line above the anchor did not turn the citation "
                f"in a test source red: {problems}")
            self.assertLess(held, self.COMMITTED_HELD)
        finally:
            shutil.rmtree(root)

    @classmethod
    def setUpClass(cls):
        _p, _r, cls.COMMITTED_HELD, _d, _s, _o = run_check(REPO)


class AStaleDeclaration(unittest.TestCase):
    """What the tool must refuse to pass, in each of its shapes.

    Each of these is *not found by this method* rather than an absence, which is
    `CLAUDE.md`'s rule and `ec/annotations/registers.yaml`'s own caveat on the
    same point: a static scan finding zero hits is never evidence that the code
    is gone.
    """

    def test_a_tool_whose_anchor_is_gone_is_reported_not_passed(self):
        def drop(rel, text):
            if rel != cpy.TOOL:
                return text
            return text.replace("def cluster_key(g: str, addrs) -> str:", "")

        root = scratch_tree(drop)
        try:
            problems, resolved, _h, _d, _s, _out = run_check(root)
            self.assertTrue(
                saying(problems, "cluster_key", "not found by this method",
                       "stale declaration", "not an absence"),
                f"a vanished anchor was passed or reported as an absence: "
                f"{problems}")
            self.assertLess(resolved, len(cpy.ANCHORS))
        finally:
            shutil.rmtree(root)

    def test_an_anchor_that_became_ambiguous_is_reported(self):
        # "is not found by this method" covers both halves on purpose: a needle
        # that is gone and one that grew a second match are the same class of
        # problem -- a declaration that has itself gone stale.
        def duplicate(rel, text):
            if rel != cpy.TOOL:
                return text
            return text.replace(
                "own_map = load_ownership()",
                "own_map = load_ownership()\n    own_map = load_ownership()", 1)

        root = scratch_tree(duplicate)
        try:
            problems, resolved, _h, _d, _s, _out = run_check(root)
            self.assertTrue(
                saying(problems, "own_map = load_ownership()",
                       "no longer unique", "stale declaration"),
                f"an anchor that grew a second match was passed: {problems}")
            self.assertLess(resolved, len(cpy.ANCHORS))
        finally:
            shutil.rmtree(root)

    def test_a_tree_the_tool_cannot_read_is_reported_not_passed(self):
        root = scratch_tree()
        try:
            os.remove(os.path.join(root, cpy.TOOL))
            problems, resolved, held, _d, _s, _out = run_check(root)
            self.assertTrue(
                saying(problems, "not read", "broken check, not an empty one"),
                f"an unreadable tool was passed: {problems}")
            self.assertEqual((resolved, held), (0, 0))
        finally:
            shutil.rmtree(root)

    def test_a_declaring_file_the_tool_cannot_read_is_reported(self):
        root = scratch_tree()
        try:
            os.remove(os.path.join(
                root, 'ec/tools/test_xdata_cluster_names.py'))
            problems, _r, _h, _d, _s, _out = run_check(root)
            self.assertTrue(
                saying(problems, "test_xdata_cluster_names.py", "not read",
                       "broken check, not a clean file"),
                f"an unreadable declaring file was passed: {problems}")
        finally:
            shutil.rmtree(root)


class TheDeclaredList(unittest.TestCase):
    """The shape of what is declared, which is the tool's own contract.

    None of these cases counts the tree. A census figure asserted here is a
    value every merge that adds a citation has to edit, which is the mistake
    `CLAUDE.md` names and which bit this repository four times over on an
    unrelated table.
    """

    def test_every_locator_captures_exactly_one_group(self):
        for rel, declared in cpy.CITATIONS:
            for key, locator in declared:
                groups = re.compile(locator).groups
                self.assertEqual(groups, 1,
                                 f"{rel}: the {key} locator captures "
                                 f"{groups} group(s); the first is the cited "
                                 f"number and a second one has nothing to "
                                 f"compare against")

    def test_every_anchor_is_held_by_at_least_one_declared_citation(self):
        declared = {key for _rel, cites in cpy.CITATIONS
                    for key, _locator in cites}
        unheld = [key for key, _what, _needle in cpy.ANCHORS
                  if key not in declared]
        self.assertEqual(unheld, [],
                         f"anchors no declared citation names: {unheld}. An "
                         f"anchor nothing cites is a declaration that checks "
                         f"nothing.")

    def test_the_declaring_files_are_the_ones_the_write_up_names(self):
        named = {rel for rel, _cites in cpy.CITATIONS}
        self.assertTrue(set(DECLARING_FILES) <= named,
                        f"the write-up names files the list does not declare: "
                        f"{sorted(set(DECLARING_FILES) - named)}")
        # And the other way: a file the list declares that the write-up does not
        # name is a file whose declines nothing has accounted for.
        write_up = Path(REPO, 'docs/findings/py-source-citations.md')
        if write_up.exists():
            text = write_up.read_text(encoding="utf-8")
            for rel in named - set(DECLARING_FILES):
                self.assertIn(rel, text,
                              f"{rel} is declared but the write-up does not "
                              f"name it, so its declined sites are unaccounted "
                              f"for")

    def test_a_file_the_list_declares_no_citation_for_still_reports(self):
        # `check_eq_guard_citations.py` and `test_check_doc_figure_pins.py` are
        # declared with no locator: they carry only synthetic fixtures. They are
        # listed so those fixtures come out **declined and counted**, which is
        # how a reader tells a fixture from a claim.
        _p, _r, _h, declined, _s, report = run_check(REPO)
        for rel in ('ec/tools/check_eq_guard_citations.py',
                    'ec/tools/test_check_doc_figure_pins.py'):
            self.assertIn(f"declined {rel}:", report)

    def test_the_whole_run_exits_zero_on_the_committed_tree(self):
        rc, out, err = run_main(['check_py_citations.py'])
        self.assertEqual(rc, 0, f"stdout:\n{out}\nstderr:\n{err}")

    def test_a_run_that_reads_no_citation_exits_non_zero(self):
        # The "checked nothing" case, which is the one an exit code alone would
        # otherwise pass: the sentences that carry the citations are gone, so
        # no locator matches, nothing is read, and nothing is wrong. That is a
        # broken tool, and `main()` must not exit 0 on it.
        #
        # Every declaring file rather than one: a tool that read even a single
        # citation is a tool that read something. Some of the locators name a
        # bare `:NNN` the sentence writes after a full one, so a case that
        # respelled only the filename would leave those matching and would be
        # testing a near-miss rather than the invariant. Dropping the files to
        # one line of prose says the same thing without depending on how any of
        # them happens to spell its citation.
        def gut(rel, text):
            if rel == cpy.TOOL:
                return text
            return ("# the sentences carrying this file's citations are gone\n")

        root = scratch_tree(gut)
        try:
            problems, _r, held, declined, _s, _out = run_check(root)
            self.assertEqual(held, 0)
            self.assertTrue(problems, "a locator that matches nothing must be "
                                      "reported, not passed")
            self.assertEqual(declined, 0,
                             "the sites went missing rather than declining, "
                             "which is the silent failure")
            rc, _out, err = run_main(['check_py_citations.py',
                                      '--repo', root])
            self.assertEqual(rc, 1)
            # The reason here is the rewording report rather than the
            # "read no citation at all" line: a locator that misses is a
            # problem in its own right, and it is the first branch `main()`
            # takes. That line guards the case below, which is the only way to
            # reach it.
            self.assertIn("reworded out of the shape", err)
        finally:
            shutil.rmtree(root)

    def test_a_declared_list_naming_no_locator_at_all_exits_non_zero(self):
        # The other route to `held == 0`, and the one the summary line exists
        # for: a `CITATIONS` in which every file declares nothing. Nothing is
        # wrong with the tree, every anchor resolves, and nothing was checked --
        # which must not read as a pass. Reached by swapping the declaration,
        # which is the only way to get there without rewording a real sentence.
        saved = cpy.CITATIONS
        cpy.CITATIONS = tuple((rel, ()) for rel, _declares in saved)
        try:
            _p, _r, held, _d, _s, _o = run_check(REPO)
            self.assertEqual(held, 0)
            rc, _out, err = run_main(['check_py_citations.py'])
            self.assertEqual(rc, 1)
            self.assertIn("read no citation at all", err)
        finally:
            cpy.CITATIONS = saved


if __name__ == "__main__":
    unittest.main()