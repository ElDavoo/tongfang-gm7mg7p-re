#!/usr/bin/env python3
"""Cases for `check_no_append_logs.py`.

The tool is a shape test over headings and one marker, so the cases are a
committed tree and scratch trees that each grow one of the two shapes. A rule
that has never been seen to fail is not a rule, and a rule that fires on the
text which *states* it is worse than no rule — so the negative cases matter at
least as much as the positive ones.
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

import check_no_append_logs as appendlog  # noqa: E402


def scratch(files):
    """A throwaway repo root holding `files` -- {relative path: contents}."""
    root = tempfile.mkdtemp()
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    return root


class TheCommittedTree(unittest.TestCase):
    def test_the_committed_tree_has_no_append_log(self):
        self.assertEqual(appendlog.check(REPO, quiet=True), 0)

    def test_the_three_files_it_exists_for_are_the_three_it_names(self):
        # The tool's claim is that this has happened three times. If a fourth
        # file has grown one and this still says three, the docstring is the
        # stale part, which is the failure this repository keeps making.
        for rel in ("docs/findings.md", "tools/README.md",
                    "docs/findings/test-line-pin-census.md"):
            self.assertTrue(os.path.exists(os.path.join(REPO, rel)), rel)
        head = open(os.path.join(REPO, "ec", "tools", "check_no_append_logs.py"),
                    encoding="utf-8").read()
        for rel in ("docs/findings.md", "tools/README.md",
                    "docs/findings/test-line-pin-census.md"):
            self.assertIn(rel, head)


class MergeHeadings(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            shutil.rmtree(root, ignore_errors=True)

    def check(self, text, rel="docs/findings/page.md"):
        root = scratch({rel: text})
        self.roots.append(root)
        return appendlog.check(root, quiet=True)

    def test_a_dated_merge_heading_fails(self):
        self.assertEqual(self.check("# T\n\n## The `#929` merge, 2026-09-26\n\nx\n"), 1)

    def test_a_bare_merged_tree_note_fails(self):
        self.assertEqual(self.check("# T\n\n## Merged-tree note (2026-09-25)\n\nx\n"), 1)

    def test_the_offending_heading_is_named(self):
        import io
        from contextlib import redirect_stdout
        root = scratch({"docs/findings/page.md":
                        "# T\n\n## The `#929` merge, 2026-09-26\n\nx\n"})
        self.roots.append(root)
        buf = io.StringIO()
        with redirect_stdout(buf):
            appendlog.check(root)
        out = buf.getvalue()
        # Named, with its file and line, so a person reading a red run knows
        # which heading to retitle without going looking for it.
        self.assertIn("docs/findings/page.md:3", out)
        self.assertIn("`#929` merge", out)

    def test_a_heading_about_the_finding_is_fine(self):
        # The boundary the tool has to hold: a section may *cite* a merge while
        # being about something else, and most sections in this repository do.
        for title in ("## Why no checker",
                      "## What the merge moved, and what it did not",
                      "## The measurement",
                      "## What this does not check"):
            self.assertEqual(self.check("# T\n\n%s\n\nx\n" % title), 0, title)

    def test_prose_mentioning_a_merge_is_not_a_heading(self):
        self.assertEqual(
            self.check("# T\n\nThe #929 merge moved four anchors, and here is "
                       "why that mattered.\n"), 0)


class SupersessionNotes(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            shutil.rmtree(root, ignore_errors=True)

    def check(self, text, rel="tools/README.md"):
        root = scratch({rel: text})
        self.roots.append(root)
        return appendlog.check(root, quiet=True)

    def test_a_supersession_note_in_a_shared_doc_fails(self):
        self.assertEqual(
            self.check("# T\n\n*(Superseded a third time, by #1034.)*\n"), 1)

    def test_a_supersession_note_in_a_findings_file_is_fine(self):
        # §4a-4d is a real rule and a findings file is where it belongs.
        self.assertEqual(
            self.check("# T\n\n*(Superseded a third time.)*\n",
                       rel="docs/findings/page.md"), 0)

    def test_writing_the_marker_in_backticks_is_not_writing_one(self):
        # `CLAUDE.md` and this tool's own docstring both name the pattern in
        # code spans. A rule that fires there is a rule that gets disabled.
        for rel in ("CLAUDE.md", "ec/tools/check_no_append_logs.py"):
            self.assertEqual(
                self.check("# T\n\nA `*(Superseded ...)*` note reappears.\n",
                           rel=rel), 0, rel)

    def test_a_supersession_note_is_still_caught_when_the_line_has_prose(self):
        self.assertEqual(
            self.check("# T\n\nSome prose, then *(Superseded again, by #929.)*\n"), 1)


class WhatItSkips(unittest.TestCase):
    def test_a_gitignored_checkout_inside_the_tree_is_not_counted(self):
        # The same pruning the runner and the suite table now carry: a
        # `git worktree add` under `.claude/` is a second copy of every
        # document, and counting it is how a figure stops being a measurement.
        root = scratch({
            "docs/findings/page.md": "# T\n\nfine\n",
            ".claude/worktrees/x/docs/findings/page.md":
                "# T\n\n## The `#929` merge, 2026-09-26\n\nx\n",
        })
        try:
            self.assertEqual(appendlog.check(root, quiet=True), 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_vendor_is_not_scanned(self):
        root = scratch({
            "docs/findings/page.md": "# T\n\nfine\n",
            "vendor/thing/README.md": "## The `#929` merge, 2026-09-26\n",
        })
        try:
            self.assertEqual(appendlog.check(root, quiet=True), 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
