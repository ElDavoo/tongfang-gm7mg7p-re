#!/usr/bin/env python3
"""Cases for `check_no_conflict_markers.py`.

The tool is three regexes over committed text, so the cases are scratch trees
that each grow one shape. What matters more here than the positives is the
negative: a `=======` is a markdown setext heading, this repository's own rule
about the tool is written in backticks in two files, and the write-up about the
tool has to quote a real conflict block. A rule that fires on any of those is a
rule that gets deleted, and #1089's markers sat in the tree for weeks precisely
because nothing was watching -- not because the detection was hard.
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, "ec", "tools"))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import check_no_conflict_markers as markers  # noqa: E402

# The block as `tools/README.md` carried it from #1089 until #1163, abridged
# to the two table rows it stood between. Both halves matter: the incoming side
# had dropped a row the outgoing side kept.
THE_1089_BLOCK = (
    "| `ec/tools/test_walk_branch_arms.py` | the direction classification |\n"
    "<<<<<<< HEAD\n"
    "| `ec/tools/test_walk_budget_census.py` | the terminator-guard census |\n"
    "| `ec/tools/test_walk_flow_follow.py` | the `--follow-flow` mode |\n"
    "=======\n"
    "| `ec/tools/test_walk_budget_census.py` | the terminator-guard census, "
    "corrected |\n"
    ">>>>>>> ba050412 (fix round 1 (review))\n"
    "| `ec/tools/test_xdata_carry_notice.py` | which census a carry line is a "
    "claim about |\n"
)


def scratch(files):
    """A throwaway repo root holding `files` -- {relative path: contents}."""
    root = tempfile.mkdtemp()
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        kwargs = {} if isinstance(content, bytes) else {"encoding": "utf-8"}
        with open(path, mode, **kwargs) as handle:
            handle.write(content)
    return root


class TheCommittedTree(unittest.TestCase):
    def test_the_committed_tree_carries_no_marker(self):
        self.assertEqual(markers.check(REPO, quiet=True), 0)

    def test_the_file_it_exists_for_is_the_one_that_carried_one(self):
        # The tool's claim is that #1089's markers sat in `tools/README.md`
        # until #1163. If the file is renamed or the claim is stale, this is
        # the docstring that is wrong, which is the failure this repository
        # keeps making.
        for rel in ("tools/README.md",):
            self.assertTrue(os.path.exists(os.path.join(REPO, rel)), rel)
        with open(os.path.join(TOOLS, "check_no_conflict_markers.py"),
                  encoding="utf-8") as handle:
            head = handle.read()
        self.assertIn("tools/README.md", head)
        self.assertIn("90287fec", head)
        self.assertIn("#1163", head)


class Markers(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            shutil.rmtree(root, ignore_errors=True)

    def check(self, files):
        root = scratch(files)
        self.roots.append(root)
        return markers.check(root, quiet=True)

    def test_the_block_1089_committed_is_caught(self):
        self.assertEqual(
            self.check({"tools/README.md": "# Tools\n\n" + THE_1089_BLOCK}), 1)

    def test_a_start_marker_on_its_own_is_caught(self):
        # A half-resolved file that kept only the opening marker is still a
        # conflict, and the two outer markers are the unambiguous pair.
        self.assertEqual(
            self.check({"a.py": "x = 1\n<<<<<<< HEAD\ny = 2\n"}), 1)

    def test_an_end_marker_on_its_own_is_caught(self):
        self.assertEqual(
            self.check({"a.py": "y = 2\n>>>>>>> ba050412 (fix round 1)\n"}), 1)

    def test_the_offending_line_is_named_with_its_file_and_line(self):
        import io
        from contextlib import redirect_stdout
        root = scratch({"tools/README.md": "# Tools\n\n" + THE_1089_BLOCK})
        self.roots.append(root)
        buf = io.StringIO()
        with redirect_stdout(buf):
            markers.check(root)
        out = buf.getvalue()
        # Line 4, the `<<<<<<<`, and the count of all three markers, so a
        # person reading a red run does not have to go looking.
        self.assertIn("tools/README.md:4", out)
        self.assertIn("3 committed conflict marker(s) found.", out)

    def test_a_python_file_is_caught_too(self):
        # Not a markdown-only rule: #1089's was prose, and the next one could
        # be a tool that two branches both rewrote.
        self.assertEqual(self.check({"ec/tools/x.py": "<<<<<<< HEAD\n"}), 1)

    def test_a_longer_separator_still_counts(self):
        # `merge.conflictStyle` and `conflict-marker-size` both exist, and a
        # marker that is longer is still a marker.
        self.assertEqual(
            self.check({"a.py": "<<<<<<< HEAD\n===========\n>>>>>>> abc\n"}), 1)


class WhatItMustNotFireOn(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            shutil.rmtree(root, ignore_errors=True)

    def check(self, files):
        root = scratch(files)
        self.roots.append(root)
        return markers.check(root, quiet=True)

    def test_a_setext_heading_is_not_a_separator(self):
        # The boundary the tool has to hold, and the reason the bare `=======`
        # is not checked on its own: markdown spells a heading as a line of `=`
        # under its title, and this repository is full of prose that could
        # start using it tomorrow.
        for title in ("Tools", "A rather long heading than seven equals signs",
                      "Short"):
            underline = "=" * len(title)
            self.assertEqual(
                self.check({"a.md": "%s\n%s\n\ntext\n" % (title, underline)}),
                0, title)

    def test_a_seven_equal_setext_heading_is_still_a_heading(self):
        # The awkward one: a title exactly seven characters long produces a
        # seven-`=` underline, which is byte-identical to git's separator. It
        # is only saved by the pairing rule, so this case is the rule.
        self.assertEqual(
            self.check({"a.md": "Exactly\n=======\n\ntext\n"}), 0)

    def test_naming_the_marker_in_backticks_is_not_carrying_one(self):
        # `CLAUDE.md` and this tool's own docstring both name the pattern in
        # code spans. Without this the rule fails on the two places that state
        # it, which is the fastest route to a check everybody disables.
        for rel in ("CLAUDE.md", "ec/tools/check_no_conflict_markers.py"):
            self.assertEqual(
                self.check({rel: "# T\n\nA `<<<<<<< HEAD` line is the "
                                  "thing.\n"}), 0, rel)

    def test_quoting_a_real_conflict_block_in_a_fence_is_not_carrying_one(self):
        # The write-up about this tool has to be able to show the block, and
        # #1089's own history is the example worth showing.
        doc = ("# A write-up\n\nWhat #1089 committed:\n\n```\n"
               + THE_1089_BLOCK + "```\n\nAnd that is the whole of it.\n")
        self.assertEqual(self.check({"docs/findings/page.md": doc}), 0)

    def test_a_binary_file_is_not_decoded_and_searched(self):
        # A firmware image or a `.png` under `evidence/` must not be run
        # through `errors="ignore"` and then searched for three ASCII runs.
        blob = b"\x89PNG\r\n\x1a\n" + b"<<<<<<< HEAD\n" * 40
        self.assertEqual(self.check({"evidence/thing.png": blob}), 0)

    def test_a_worktree_inside_the_tree_is_not_counted(self):
        # The same pruning the runner, the suite table and the append-log check
        # carry: a `git worktree add` under `.claude/` is a second copy of
        # every file, and a marker in it is not a marker in this tree.
        self.assertEqual(self.check({
            "docs/findings/page.md": "# T\n\nfine\n",
            ".claude/worktrees/x/tools/README.md": THE_1089_BLOCK,
        }), 0)

    def test_vendor_is_not_scanned(self):
        self.assertEqual(self.check({
            "docs/findings/page.md": "# T\n\nfine\n",
            "vendor/thing/README.md": THE_1089_BLOCK,
        }), 0)

    def test_a_line_of_angle_brackets_that_is_not_seven_is_not_a_marker(self):
        # `<<<<<` in a diagram, and a `>>>>>`-shaped arrow in ASCII art, are
        # both things a person writes on purpose.
        self.assertEqual(
            self.check({"a.md": "flow: a <<<<< b >>> c\n<<<<<< six\n"}), 0)


if __name__ == "__main__":
    unittest.main()
