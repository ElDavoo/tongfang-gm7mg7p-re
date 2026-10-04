#!/usr/bin/env python3
"""Offline checks for check_eq_guard_citations.py: the committed tree and a
scratch one.

The tool's failure mode is silence, and here it is a specific one. A `:NNN` in
a `docs/findings/` page that has drifted onto a different flag or a different
refusal produces no error at all: the sentence reads exactly as well with
`:4985` as with `:4976`, nothing in the tree is red, and the figure a reader
would re-derive is wrong. So what is pinned here is the *whole* mechanism and
then each way it can stop working.

Four classes, in the order a reader needs them:

  * **The committed tree agrees** -- every declared citation still names code
    the tool has, all nine anchors resolve, and the run prints a held count and
    a declined count that are both non-zero. The last part is the one that
    matters most: a checker that located nothing must say so rather than exit 0,
    because "checked nothing" and "found nothing" read alike from the exit
    code.
  * **The two wrong-code sites stay distinguishable.** #873's finding was not
    that a number was off, it was that a number resolved to *a different thing*.
    So the `--reconcile` help tail and the committed-output refusal are each
    asserted to resolve to a line no other anchor claims, and the two refusals
    to resolve to different lines from each other. A checker that held the two
    refusals to one shared number would pass every other case here.
  * **A moved number is a note, not a failure** (2026-10-04). One cited number
    moved by one line in a scratch copy of a real page, and the run is asserted
    to stay green *and* to print the anchor's current line beside the cited one.
    Holding the number to today's line made every branch that grew the tool
    re-point five write-ups it had not touched; the anchors and the locators
    are what is held, and their own negative cases are the class after.
  * **A reworded citation is reported, not passed.** The declared list holds a
    locator -- a string of the citing file's own prose -- precisely so that a
    sentence which stops naming the code stops matching. A checker that fell
    back to "no citation found, nothing to check" would report that page clean.

The scratch tree is built by copying the committed files, because the fixtures
worth having are the real sentences: a paraphrase of `xdata-4-4`'s refusal
citation that happened to keep the right number would be a control passing for
the wrong reason.
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
    'check_eq_guard_citations', HERE / 'check_eq_guard_citations.py')
cge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cge)


def run_main(argv) -> tuple:
    """(exit code, stdout, stderr) with `argv` in place and both streams
    captured, the way a reader would run it -- the return code and the lines it
    prints are the tool's whole output surface."""
    err, out, saved = io.StringIO(), io.StringIO(), sys.argv
    sys.argv = argv
    try:
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            rc = cge.main()
    finally:
        sys.argv = saved
    return rc, out.getvalue(), err.getvalue()


def run_check(repo) -> tuple:
    """(problems, resolved, held, declined, skipped) with the report captured.

    The report goes to a buffer rather than to the runner's stdout, so a case
    reads the numbers the tool derived rather than parsing its own fixture.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = cge.check(repo, stream=buf)
    return result + (buf.getvalue(),)


def scratch_tree(mutate=None) -> str:
    """A throwaway copy of the tool and the five declaring files.

    `mutate` is called with `(relpath, text)` per file and may return a new text.
    Only the files the tool reads are copied, which is the tool's own scope made
    literal: a scratch tree this small cannot pass by carrying a copy of
    something the checker does not look at.
    """
    root = tempfile.mkdtemp(prefix="eq-guard-citations-")
    for rel in [cge.TOOL] + [name for name, _ in cge.CITATIONS]:
        target = os.path.join(root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        text = Path(REPO, rel).read_text(encoding="utf-8")
        if mutate is not None:
            text = mutate(rel, text)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
    return root


def anchor_line(key) -> int:
    """The line `key` resolves to in the committed tool, read by the tool.

    A hardcoded copy in this file would go stale silently the next time the tool
    grows, and the cases that use it are about the tool's *relationships*
    between anchors -- which numbers they are is the tool's business.
    """
    needle = next(n for k, _, n in cge.ANCHORS if k == key)
    line = cge.resolve(cge.read(Path(REPO, cge.TOOL)), needle)
    assert line is not None, f"the committed tool does not hold {key}"
    return line


class TheCommittedTree(unittest.TestCase):
    """The real thing: the committed prose and the committed tool agree.

    It no longer goes red when an edit to `xdata_register_map.py` moves an
    anchor's line: what it holds is that each citation still names code the
    tool has, uniquely, and that the sentence still says which code.
    """

    def test_the_committed_citations_hold(self):
        rc, out, err = run_main(['check_eq_guard_citations.py'])
        self.assertEqual(rc, 0, err)
        self.assertIn('name code the tool still has', out)

    def test_every_anchor_resolves_and_is_printed_with_its_line(self):
        # The report leads with the derived table, so a reader can see what each
        # citation is held *to* before reading any verdict. Every anchor in the
        # declared list, not a sample of them.
        _, resolved, _, _, _, out = run_check(REPO)
        self.assertEqual(resolved, len(cge.ANCHORS))
        for key, _, _ in cge.ANCHORS:
            with self.subTest(anchor=key):
                self.assertIn(f"  {key}: {cge.TOOL}:{anchor_line(key)}  ", out)

    def test_the_run_says_how_many_it_held_and_how_many_it_declined(self):
        # Without this a rule that stopped looking and a tree with nothing to
        # look at print the same thing, and "checked nothing" would read from
        # the exit code exactly like "found nothing".
        _, out, _ = run_main(['check_eq_guard_citations.py'])
        match = re.search(r'(\d+) citation\(s\) name code the tool still has, '
                          r'(\d+) declined', out)
        self.assertIsNotNone(match, out)
        self.assertGreater(int(match.group(1)), 0)
        # Non-zero on the real tree: the five files carry sixteen
        # `xdata_register_map.py:NNN` pins the tool declines -- fourteen of them
        # for other claims (`OUT_CLUSTERS`, `MAP_COLUMNS`, the `--self-test`
        # span) and two in §97's own restatements of the superseded numbers -- and
        # a rule that reported zero declines on a tree full of them would be
        # declining for a reason nobody wrote down. Sixteen is what
        # `check_eq_guard_citations.py` prints on this tree; the assertion above
        # checks it is non-zero rather than pinning it, because the count moves
        # with every re-point and a pinned figure here would be a figure to
        # re-point.
        self.assertGreater(int(match.group(2)), 0)

    def test_the_skip_is_counted_rather_than_silent(self):
        # The #254 correction block in `docs/findings.md` is quoted material, so
        # its three pins are passed over. A skip that is not announced anywhere
        # is a skip that looks like a check.
        _, _, _, _, skipped, out = run_check(REPO)
        self.assertGreater(skipped, 0)
        self.assertIn('skip (quoted material)', out)


class TheWrongCodeSites(unittest.TestCase):
    """#873's two findings were not "a number is off" but "a number is a
    different thing", and that is the property these hold."""

    def test_the_reconcile_help_tail_is_no_anchors_line(self):
        # `:4457` named the tail of `--reconcile`'s help while three files
        # claimed `--no-eq-guard`. A checker that resolved the flag by "the
        # nearest `--no-eq-guard`" would have kept passing on that.
        self.assertNotEqual(anchor_line("reconcile_help"),
                            anchor_line("no_eq_guard_flag"))

    def test_the_two_refusals_resolve_to_different_lines(self):
        # `:4495-4499` claimed the committed-output refusal and resolved to the
        # `--check`/`--self-test` one. Holding both to one number would hide it.
        self.assertNotEqual(anchor_line("check_refusal"),
                            anchor_line("committed_output_refusal"))

    def test_the_committed_output_refusal_is_below_the_check_refusal(self):
        # The order is a fact about the tool, not an invariant to enforce, so
        # this asserts the *current* relationship rather than a rule: what a
        # report has to be able to tell a reader is which of the two is which.
        self.assertLess(anchor_line("check_refusal"),
                        anchor_line("committed_output_refusal"))

    def test_the_flag_and_the_committed_output_refusal_are_far_apart(self):
        # `:4457` and `:4606-4611` were 149 apart in the tree #873 measured and
        # are 38 apart now; the point is that they are two anchors, not one
        # number that drifted.
        self.assertNotEqual(anchor_line("no_eq_guard_flag"),
                            anchor_line("committed_output_refusal"))


class ADriftedNumber(unittest.TestCase):
    """A moved number, on a copy of a real page: reported, and not a failure."""

    def test_a_cited_number_moved_by_one_is_noted_with_the_current_line(self):
        # The line is read from the tool rather than spelled here (2026-10-01).
        # Spelled as `:4985`/`:4984`, this case went red the moment the tool
        # grew, and it did not do the job it exists for: it failed on the
        # committed tree instead of on the nudge.
        line = anchor_line("committed_output_refusal")

        def nudge(rel, text):
            # The `xdata-4-4` page's committed-output refusal, moved up one
            # line -- the exact shape a commit inserting a line above it
            # produces, and the shape that reads correctly in the prose.
            return text.replace(
                f'OUT_REGISTERS` at `ec/tools/xdata_register_map.py:{line}`',
                f'OUT_REGISTERS` at `ec/tools/xdata_register_map.py:{line - 1}`', 1) \
                if rel.endswith("xdata-4-4-identity-rederivation.md") else text

        root = scratch_tree(nudge)
        self.addCleanup(shutil.rmtree, root)
        rc, out, err = run_main(['check_eq_guard_citations.py', '--repo', root])
        self.assertEqual(rc, 0, err)
        # Both halves of the note: the cited number, and the line the anchor is
        # on now, so a reader following the prose is not sent back to `grep`.
        self.assertIn(
            f"moved docs/findings/xdata-4-4-identity-rederivation.md", out)
        self.assertIn(
            f"cites :{line - 1} for committed_output_refusal, which is "
            f"{cge.TOOL}:{line}", out)

    def test_the_rest_of_the_run_is_still_reported(self):
        # A red run that stops reporting is not a better report. Every other
        # citation is still resolved, held and counted.
        line = anchor_line('flip')  # read, not spelled; see the case above

        def nudge(rel, text):
            return text.replace(f'at `:{line}`', f'at `:{line - 1}`', 1) \
                if rel.endswith("xdata-no-eq-guard-refusal-contract.md") else text

        root = scratch_tree(nudge)
        self.addCleanup(shutil.rmtree, root)
        problems, resolved, held, declined, skipped, out = run_check(root)
        self.assertEqual(problems, [])
        self.assertIn(f"cites :{line - 1} for flip, which is "
                      f"{cge.TOOL}:{anchor_line('flip')}", out)
        self.assertEqual(resolved, len(cge.ANCHORS))
        self.assertGreater(held, 0)
        self.assertGreater(declined, 0)
        self.assertGreater(skipped, 0)


class ARewordedCitation(unittest.TestCase):
    """The declared list holds prose, so prose that changes is itself a change
    this tool must notice rather than quietly stop checking."""

    def test_a_citation_reworded_out_of_shape_is_reported(self):
        def strip_code(rel, text):
            # The sentence keeps its number and loses the code it was citing --
            # the drift back to a bare `:NNN` that the whole mechanism exists to
            # prevent, and the one a number-only checker cannot see.
            return text.replace('`if eq_guard and stripped.startswith("==")` at',
                                'the guard at', 1) \
                if rel.endswith("xdata-4-4-identity-rederivation.md") else text

        root = scratch_tree(strip_code)
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_eq_guard_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn('a declared eq_guard_reject citation is not found by this '
                      'method', err)

    def test_a_tool_whose_anchor_is_gone_is_reported_not_passed(self):
        # The tool losing `if eq_guard and stripped.startswith("==")` is a real
        # change to the classifier; what must not happen is the checker reading
        # it as "nothing to check" and exiting 0. Never "absent" -- CLAUDE.md's
        # rule, and `ec/annotations/registers.yaml`'s own caveat.
        def rewrite_tool(rel, text):
            return text.replace('if eq_guard and stripped.startswith("=="):',
                                'if stripped.startswith("=="):', 1) \
                if rel == cge.TOOL else text

        root = scratch_tree(rewrite_tool)
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_eq_guard_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn('is not found by this method', err)
        self.assertIn('not an absence', err)

    def test_an_anchor_that_became_ambiguous_is_reported(self):
        # Two matches is not a first match. `args.out_registers ==
        # OUT_REGISTERS` already spells two refusals today, which is why the
        # declared anchor carries the `--no-eq-guard` conjunct; a needle that
        # grew a second match is a declaration that has itself gone stale.
        def clone_tool(rel, text):
            return text + '\nif args.no_eq_guard and (args.out_registers == OUT_REGISTERS\n' \
                if rel == cge.TOOL else text

        root = scratch_tree(clone_tool)
        self.addCleanup(shutil.rmtree, root)
        rc, _, err = run_main(['check_eq_guard_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn('the committed-output refusal is not found by this method',
                      err)

    def test_a_tree_the_tool_cannot_read_is_reported_not_passed(self):
        root = scratch_tree()
        self.addCleanup(shutil.rmtree, root)
        os.remove(os.path.join(root, cge.TOOL))
        rc, _, err = run_main(['check_eq_guard_citations.py', '--repo', root])
        self.assertEqual(rc, 1)
        self.assertIn('a broken check, not an empty one', err)


class TheDeclaredList(unittest.TestCase):
    """The list's own shape, so a new entry cannot be added half-formed."""

    def test_every_anchor_is_held_by_at_least_one_declared_citation(self):
        # An anchor nothing cites is a declaration with no consumer. The one
        # exception this file had to make is `reconcile_help`, which is held by
        # `docs/findings.md` §97 and asserted below; the assertion is here so
        # that the next anchor added without a citation is caught.
        cited = {key for _, declared in cge.CITATIONS for key, _ in declared}
        for key, _, _ in cge.ANCHORS:
            with self.subTest(anchor=key):
                self.assertIn(key, cited)

    def test_every_declared_locator_captures_exactly_one_group(self):
        # The number is group 1 by construction, and a locator added with a
        # non-capturing group in front of it would read the wrong digits
        # without failing here.
        for rel, declared in cge.CITATIONS:
            for key, locator in declared:
                with self.subTest(file=rel, anchor=key):
                    self.assertEqual(re.compile(locator).groups, 1)

    def test_the_declaring_files_are_the_five_the_write_up_names(self):
        self.assertEqual(
            sorted(rel for rel, _ in cge.CITATIONS),
            sorted(["docs/findings/xdata-no-eq-guard-refusal-contract.md",
                    "docs/findings/xdata-no-eq-guard-measured-state-correction.md",
                    "ec/annotations/xdata-register-map.md",
                    "docs/findings/xdata-4-4-identity-rederivation.md",
                    "docs/findings.md"]))

    def test_a_file_the_list_declares_no_citation_for_still_reports(self):
        # `xdata-no-eq-guard-measured-state-correction.md` holds no live tool
        # citation -- its two are a record of a past tree, and they are declined
        # rather than held. A file with nothing to check must still say what it
        # declined, or "no citation here" and "no check ran" read alike.
        _, _, held, _, _, out = run_check(REPO)
        self.assertGreater(held, 0)
        page = "docs/findings/xdata-no-eq-guard-measured-state-correction.md"
        self.assertIn(f"  {page}: 0 declared citation(s) read, 1 declined", out)
        self.assertIn(f"declined {page}:", out)


if __name__ == '__main__':
    unittest.main()
