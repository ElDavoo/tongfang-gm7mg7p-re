#!/usr/bin/env python3
"""Cases for `check_reach_deferrals.py`.

The rule is one regex pair over the same prose `check_cluster_citations.py`
walks, so the cases are scratch trees that each grow one shape. What matters
more here than the positive is the negative and the empty: a document quoting
the sentence this rule is about is not making it, a sentence pointing at the
docstring one sentence later has still asserted the reach flatly, and a tree
where the wording has been reworded out from under the rule must fail rather
than pass by finding nothing. A rule that fires on the text stating it, or one
that stops firing and says so by being silent, is a rule that gets turned off.
"""

import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, "ec", "tools"))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import check_reach_deferrals as deferrals  # noqa: E402

# The wording the rule replaced, kept here because a suite that can only see
# the sentence as it is now cannot tell a reworded rule from a working one.
BEFORE = ("`../tools/check_cluster_citations.py` is what holds the rest of the "
          "tree to the census.")

# The wording it became, in the two shapes the committed sites use: the
# `ec/`-rooted path and the page-relative one, wrapped the way this corpus
# wraps.
AFTER_REL = ("`../tools/check_cluster_citations.py` holds the rest of the tree "
             "to the census, within the limits its docstring states.")
AFTER_ROOT = ("`ec/tools/check_cluster_citations.py` holds the rest of the tree "
              "to the census\nwithin the limits its own docstring states.")


def scratch(files):
    """A throwaway repo root holding `files` -- {relative path: contents}."""
    root = tempfile.mkdtemp()
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
    return root


class Tree(unittest.TestCase):
    """A scratch repo, cleaned up, with the check's exit code as the result."""

    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            shutil.rmtree(root, ignore_errors=True)

    def check(self, files):
        root = scratch(files)
        self.roots.append(root)
        return deferrals.check(root, quiet=True)

    def report(self, files):
        root = scratch(files)
        self.roots.append(root)
        buf = io.StringIO()
        with redirect_stdout(buf):
            deferrals.check(root)
        return buf.getvalue()

    def page(self, body, rel="docs/findings/page.md"):
        """The exit code over one scratch page carrying `body`."""
        return self.check({rel: "# A page\n\n" + body + "\n"})


class TheRule(Tree):
    def test_a_claim_with_no_pointer_to_the_docstring_is_reported(self):
        self.assertEqual(self.page(BEFORE), 1)

    def test_a_claim_that_defers_is_not_reported(self):
        self.assertEqual(self.page(AFTER_REL), 0)

    def test_a_deferral_is_read_across_a_rewrap(self):
        # This corpus wraps sentences across lines and `units()` joins them, so
        # the rule cannot be a line-based one: a claim rewrapped by a merge must
        # not stop being a claim, and a rewrapped deferral must not stop being
        # one either.
        self.assertEqual(self.page(AFTER_ROOT), 0)

    def test_a_pointer_in_the_next_sentence_is_not_a_pointer_in_this_one(self):
        # The rule is per sentence, deliberately. A paragraph that asserts the
        # reach flatly and then explains the limits in the sentence after is how
        # the flat assertion reaches a reader first, and the deferral has to be
        # where the claim is.
        self.assertEqual(
            self.page(BEFORE + " See its docstring for what it does not check."),
            1)

    def test_a_claim_written_inside_a_fence_is_still_a_claim(self):
        # The asymmetry the tool's docstring states, and the reason the
        # exemption is the inline code span rather than the fence: a sentence in
        # a block is still a sentence the document makes, and a rule that let
        # one escape by being written in a fence would be a hole in the only
        # thing this enforces. Pinned because "strip fences, the way the
        # conflict-marker check does" is the obvious wrong fix and it reads like
        # tidying.
        self.assertEqual(self.page("```\n" + BEFORE + "\n```"), 1)

    def test_a_code_span_around_only_the_path_leaves_the_claim_asserted(self):
        # The sharp edge beside the previous case, and the one any document
        # quoting this sentence hits first. Backticks pair, so the path's own
        # span does not sit inside the sentence's: the path is quoted and the
        # rest is running text, which is a claim. Correct -- the claim really is
        # in running prose there -- and worth pinning so the next reader does
        # not file it as a false positive and widen the exemption to match.
        self.assertEqual(
            self.page("`../tools/check_cluster_citations.py` is what holds the "
                      "rest of the tree to the census` and it now defers."), 1)

    def test_a_fourth_site_in_a_document_nobody_watched_is_caught(self):
        # The case the rule is for. The committed sites were found by a grep a
        # human ran; this is what makes the next one a red run instead.
        self.assertEqual(self.check({
            "docs/findings.md": "# Findings\n\nProse.\n",
            "ec/annotations/xdata-something-else.md": "# A page\n\n" + BEFORE + "\n",
        }), 1)

    def test_the_report_names_the_file_and_line(self):
        # So a person reading a red run does not have to go looking for which of
        # several sentences in the page it was.
        out = self.report({"docs/findings/page.md": "# A page\n\n" + BEFORE + "\n"})
        self.assertIn("docs/findings/page.md:3", out)


class TheEmptyCase(Tree):
    def test_a_tree_naming_no_claim_fails_rather_than_passing_vacuously(self):
        # The hole every corpus-shaped rule has: the subject gets reworded or
        # renamed, the rule matches nothing, and the run is green because an
        # empty set of problems is an empty set of problems. Reported as a
        # failure on purpose.
        files = {"docs/findings/page.md": "# A page\n\nNo claim here.\n"}
        self.assertEqual(self.check(files), 1)
        self.assertIn("no unit in the tree credits", self.report(files))

    def test_a_tree_naming_another_tool_is_the_empty_case_too(self):
        # The pre-filter reads the file's own text, so a corpus describing
        # plenty of checks and not this one is the empty case rather than a
        # pass -- which is what it is.
        self.assertEqual(self.page(
            "`check_register_counts.py` holds the rest of the tree to the "
            "counts."), 1)


class WhatItMustNotFireOn(Tree):
    # Every case here pairs the text that must stay quiet with a real deferring
    # claim on the same page. Without that second sentence the run fails the
    # empty-corpus guard instead, which would make these cases turn on something
    # other than the text under test.
    PAGE = "# A page\n\n" + AFTER_REL + "\n\n"

    def test_quoting_the_wording_it_replaced_is_not_making_the_claim(self):
        # The write-up about this rule has to show the sentence before and
        # after, and it quotes in backticks rather than in a fence -- the
        # tool's docstring says why, and the two fence cases in `TheRule` say
        # what a wider exemption would cost. The path's own code span comes out
        # so the sentence quotes as one span, which is the only shape in which
        # the backticks pair the way this reads.
        self.assertEqual(self.check({"docs/findings/page.md": self.PAGE + (
            "The wording this replaced was `../tools/"
            "check_cluster_citations.py is what holds the rest of the tree to "
            "the census` and it now defers.\n")}), 0)

    def test_naming_the_wording_in_a_code_span_is_not_making_the_claim(self):
        # The same thing in a document quoting a rule back at the reader rather
        # than showing what it replaced.
        self.assertEqual(self.check({"docs/findings/page.md": self.PAGE + (
            "`check_cluster_citations.py is what holds the rest of the tree to "
            "the census`, in the words this replaced.\n")}), 0)

    def test_this_tools_own_docstring_describes_the_claim_without_making_it(self):
        # The exemption above is for documents that *quote* the sentence. This
        # file's docstring states the rule without asserting the reach, so it
        # needs no exemption at all -- and that is worth pinning, because the
        # natural next edit is to start quoting the sentence in the docstring
        # too, which is the shape `CODE_SPAN` was widened for. If that happens
        # this case goes red and the docstring gets rewritten rather than the
        # rule getting another exception.
        with open(os.path.join(TOOLS, "check_reach_deferrals.py"),
                  encoding="utf-8") as handle:
            docstring = handle.read().split('"""')[1]
        self.assertIsNone(deferrals.CLAIM.search(
            deferrals.CODE_SPAN.sub("", docstring)))

    def test_a_worktree_inside_the_tree_is_not_counted(self):
        # The pruning the runner, the suite table and the conflict-marker check
        # all carry: `git worktree add` under `.claude/` is a second copy of
        # every document, and a sentence in it is not a sentence in this tree.
        self.assertEqual(self.check({
            "docs/findings/page.md": "# A page\n\n" + AFTER_REL + "\n",
            ".claude/worktrees/x/docs/findings/other.md":
                "# A page\n\n" + BEFORE + "\n",
        }), 0)

    def test_a_document_outside_the_roots_is_not_read(self):
        # The roots are imported from the cluster check so the two cannot drift
        # into reading different corpora, and `CLAUDE.md` is at the top of the
        # tree rather than under one of them. This says so: if a root is ever
        # widened to the top level, the rule still has to hold on the file that
        # describes how this repository works.
        self.assertEqual(self.check({
            "CLAUDE.md": "# Project\n\nA `check_cluster_citations.py` is what "
                         "holds the rest of the tree to the census.\n",
            "docs/findings/page.md": "# A page\n\n" + AFTER_REL + "\n",
        }), 0)


class TheCommittedTree(unittest.TestCase):
    def test_every_committed_claim_defers(self):
        self.assertEqual(deferrals.check(REPO, quiet=True), 0)

    def test_the_sites_the_issue_named_still_carry_the_claim(self):
        # The tool asserts a property and names no file, which is what keeps a
        # fourth document from being one more row here. This is the other half:
        # the files the issue was about are still the ones making the claim, so
        # a rename or a move shows up as a failure rather than as a rule that
        # has quietly stopped applying to the sentence it was written for. A
        # site added later is not this test's business -- the tool catches it.
        for rel in ("docs/findings.md",
                    "ec/annotations/xdata-06c2-06db-timers.md",
                    "ec/annotations/xdata-086x-dispatch.md"):
            self.assertTrue(os.path.exists(os.path.join(REPO, rel)), rel)
            with open(os.path.join(REPO, rel), encoding="utf-8") as handle:
                self.assertIn(deferrals.TOOL, handle.read(), rel)


if __name__ == "__main__":
    unittest.main()
