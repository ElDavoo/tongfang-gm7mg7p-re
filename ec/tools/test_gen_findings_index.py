#!/usr/bin/env python3
"""Offline checks for gen_findings_index.py: the index is printed, not committed.

`docs/findings/INDEX.md` used to be this tool's output checked into the tree.
Every write-up added a line to it, so it was touched by nearly every pull
request and conflicted more than any other file in the agent pipeline's
conflict runs; it was removed on 2026-10-04. These cases hold that it stays
removed (`--check` fails while the file exists, which is what stops an agent
regenerating it out of habit), that `--check` still holds the one property the
index needs from a write-up -- a `# ` title -- and that the tool still prints a
row per write-up for whoever wants the listing.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
_spec = importlib.util.spec_from_file_location(
    "gen_findings_index", HERE / "gen_findings_index.py")
gfi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gfi)


def run(repo, *argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = gfi.main(["--repo", str(repo), *argv])
    return rc, out.getvalue()


def scratch(files):
    root = Path(tempfile.mkdtemp(prefix="findings-index-"))
    findings = root / "docs" / "findings"
    findings.mkdir(parents=True)
    for name, text in files.items():
        (findings / name).write_text(text, encoding="utf-8")
    return root


class TheCommittedTree(unittest.TestCase):

    def test_the_index_is_not_committed(self):
        self.assertFalse((REPO / "docs" / "findings" / "INDEX.md").exists())

    def test_check_passes(self):
        rc, out = run(REPO, "--check")
        self.assertEqual(rc, 0, out)

    def test_the_listing_names_every_write_up(self):
        _rc, out = run(REPO)
        names = {p.name for p in (REPO / "docs" / "findings").glob("*.md")}
        listed = {name for name in names if f"[`{name}`]" in out}
        self.assertEqual(names - listed - gfi.SKIP, set())


class TheCheck(unittest.TestCase):

    def test_a_committed_index_fails(self):
        root = scratch({"a.md": "# A\n", "INDEX.md": "# Findings index\n"})
        rc, out = run(root, "--check")
        self.assertEqual(rc, 1)
        self.assertIn("INDEX.md is committed again", out)

    def test_an_untitled_write_up_fails_and_is_named(self):
        root = scratch({"a.md": "# A\n", "b.md": "no heading here\n"})
        rc, out = run(root, "--check")
        self.assertEqual(rc, 1)
        self.assertIn("b.md", out)

    def test_a_titled_tree_passes(self):
        rc, _ = run(scratch({"a.md": "# A\n", "b.md": "\n# B\n"}), "--check")
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
