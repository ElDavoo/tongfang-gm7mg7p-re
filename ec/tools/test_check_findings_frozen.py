#!/usr/bin/env python3
"""Cases for `check_findings_frozen.py`.

The tool is a count and an ordering rule over `docs/findings.md`, so the cases
are a committed tree and three scratch trees that each break one of the three
things it holds. A freeze that has never been seen to fail is not a freeze.
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

import check_findings_frozen as frozen  # noqa: E402


def scratch_with(contents):
    """A throwaway repo root whose `docs/findings.md` is `contents`."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "docs"))
    with open(os.path.join(root, "docs", "findings.md"), "w",
              encoding="utf-8") as handle:
        handle.write(contents)
    return root


MINIMAL = "# Findings\n\n## 1. one\n\nbody\n\n## 2. two\n\nbody\n"


class TheCommittedTree(unittest.TestCase):
    def test_the_committed_file_is_at_or_under_the_ceiling(self):
        self.assertEqual(frozen.check(REPO), 0)

    def test_the_ceiling_is_not_below_what_the_file_carries(self):
        # A ceiling under the real count would make the committed tree red and
        # train everyone to ignore the tool, which is how a gate stops gating.
        found = frozen.sections(
            open(os.path.join(REPO, "docs", "findings.md"),
                 encoding="utf-8").read())
        self.assertGreaterEqual(frozen.FROZEN_SECTIONS, len(found))
        self.assertEqual(len(found), 97)

    def test_the_file_says_it_is_frozen(self):
        # The rule and the check are two things and the rule is the one a
        # reader meets first, so its absence is its own defect.
        head = open(os.path.join(REPO, "docs", "findings.md"),
                    encoding="utf-8").read()[:4000]
        self.assertIn("frozen", head)
        self.assertIn("check_findings_frozen.py", head)


class WhatItCatches(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            shutil.rmtree(root, ignore_errors=True)

    def root(self, contents):
        root = scratch_with(contents)
        self.roots.append(root)
        return root

    def test_one_section_past_the_ceiling_fails(self):
        saved = frozen.FROZEN_SECTIONS
        frozen.FROZEN_SECTIONS = 2
        try:
            self.assertEqual(frozen.check(self.root(MINIMAL + "## 3. three\n")), 1)
        finally:
            frozen.FROZEN_SECTIONS = saved

    def test_the_new_section_is_named_in_the_report(self):
        saved = frozen.FROZEN_SECTIONS
        frozen.FROZEN_SECTIONS = 2
        try:
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                frozen.check(self.root(MINIMAL + "## 3. the added one\n"))
            out = buf.getvalue()
        finally:
            frozen.FROZEN_SECTIONS = saved
        self.assertIn("the added one", out)

    def test_exactly_at_the_ceiling_passes(self):
        saved = frozen.FROZEN_SECTIONS
        frozen.FROZEN_SECTIONS = 2
        try:
            self.assertEqual(frozen.check(self.root(MINIMAL)), 0)
        finally:
            frozen.FROZEN_SECTIONS = saved

    def test_a_deleted_section_fails(self):
        # A ceiling alone would not catch this -- the file is one *fewer*, which
        # is what a file that was always that short also looks like -- and every
        # §N above the gap now names the wrong section. Hence the frozen count is
        # a floor as well as a ceiling.
        saved = frozen.FROZEN_SECTIONS
        frozen.FROZEN_SECTIONS = 2
        try:
            self.assertEqual(frozen.check(self.root("# Findings\n\n## 1. one\n")), 1)
        finally:
            frozen.FROZEN_SECTIONS = saved

    def test_a_renumbered_section_fails(self):
        # The failure mode a mid-file insert causes for every citation of §2.
        self.assertEqual(
            frozen.check(self.root("# Findings\n\n## 1. one\n\n## 3. two\n")), 1)

    def test_a_reused_section_number_fails(self):
        self.assertEqual(
            frozen.check(
                self.root("# Findings\n\n## 1. one\n\n## 1. again\n")), 1)

    def test_a_missing_file_fails_rather_than_passing(self):
        root = tempfile.mkdtemp()
        self.roots.append(root)
        self.assertEqual(frozen.check(root), 1)

    def test_prose_mentioning_sections_is_not_a_section(self):
        # "§92" and "## 92." are different things, and only one of them moves
        # the counter. A walk that matched both would fail on a correction.
        text = MINIMAL + "\nsee §2 and ## 2 is the one\n"
        saved = frozen.FROZEN_SECTIONS
        frozen.FROZEN_SECTIONS = 2
        try:
            self.assertEqual(frozen.check(self.root(text)), 0)
        finally:
            frozen.FROZEN_SECTIONS = saved


if __name__ == "__main__":
    unittest.main()
