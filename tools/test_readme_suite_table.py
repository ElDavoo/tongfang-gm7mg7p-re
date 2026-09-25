#!/usr/bin/env python3
"""Offline checks for tools/README.md's suite table: the *set*, not the counts.

`run-tests.sh` discovers suites by `find`, so a suite is picked up by having
its file committed and nothing else. The README table is the only place that
inventory is written down, and a table with no check on it loses a row the
quiet way: the suite keeps running, the counts it quotes keep printing, and
nothing says the index is behind. Two rows were missing that way, and the
thing that noticed was a person reading the tree rather than a run of it.

So this compares the discovered set against the table's first column, in both
directions. A discovered suite with no row and a row for a suite that is gone
are different mistakes and the failure names which. The counts are never
compared: an expected count turns every added test into a failure, which is
the wrong trade, and the same reason `run-tests.sh` reports its totals rather
than asserting them.

The descriptions are not checked. They are prose -- what a suite stands in
for -- and the runner has no reason to know any of it, so those stay by hand.
"""
import re
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
README = HERE / 'README.md'

# A table row's first cell is one backticked path and nothing else, so
# fullmatch on the cell is enough and a half-written row reads as no row
# rather than as a wrong one. The header cell is ` suite ` and the separator
# is dashes; neither matches, which is how the two are skipped without a
# special case for either.
ROW_PATH = re.compile(r'`([^`]+)`')


def discover():
    """The suites `run-tests.sh` finds, by the runner's own rule.

    The same `test_*.py` pattern and the same `.git` exclusion as the
    runner's find, copied rather than reinvented: a suite the runner runs and
    this check has never heard of is a suite with no row, and that is the
    half that broke. Recomputed per call rather than cached at import, so a
    case can point it at a scratch tree.
    """
    found = set()
    for path in REPO.rglob('test_*.py'):
        rel = path.relative_to(REPO)
        if rel.parts[0] == '.git':
            continue
        found.add(rel.as_posix())
    return found


def table_rows(text):
    """The backticked path in the first column of every row of the table.

    Only the first column, and only lines that open with `|`. The intro
    paragraph and the `ecrw_fake.py` note name a great many `test_*.py`
    files in prose, most of them already rows, and a whole-file scan would
    collect that prose as if it were the table.
    """
    rows = []
    for line in text.splitlines():
        if not line.startswith('|'):
            continue
        cells = line.split('|')
        match = ROW_PATH.fullmatch(cells[1].strip()) if len(cells) > 2 else None
        if match:
            rows.append(match.group(1))
    return rows


def readme_rows():
    """What tools/README.md's table lists right now, on disk."""
    return table_rows(README.read_text())


class ParseTests(unittest.TestCase):
    """The parse itself, on inline tables.

    Without these the set comparison below is one bad regex away from passing
    vacuously -- an empty parse matches an empty discovery, which is the
    §14b defect the runner's empty-discovery guard exists for.
    """

    def test_the_first_column_is_read_and_the_rest_is_not(self):
        text = '\n'.join([
            'prose naming `ec/tools/test_walk_branch_arms.py` in passing',
            '',
            '| suite | what it stands in for |',
            '|---|---|',
            '| `ec/tools/test_group_functions.py` | a `|` free description |',
            '',
            'after the table, `ec/tools/test_export_ownership.py` again',
        ])
        self.assertEqual(table_rows(text),
                         ['ec/tools/test_group_functions.py'])

    def test_the_header_and_the_separator_are_not_rows(self):
        text = '\n'.join([
            '| suite | what it stands in for |',
            '|---|---|',
            '| `ec/tools/test_citation_frames.py` | a description |',
        ])
        self.assertEqual(table_rows(text), ['ec/tools/test_citation_frames.py'])

    def test_a_first_column_that_is_not_one_path_is_not_a_row(self):
        # A row rewritten into prose, or a second backticked path in the
        # first cell, is not something this can half-believe: it reads as
        # absent, and the comparison below says which suite is missing.
        text = '\n'.join([
            '|---|---|',
            '| `a.py` and `b.py` | two paths in one cell |',
            '| a.py | unbackticked |',
        ])
        self.assertFalse(table_rows(text))


class SuiteTableTests(unittest.TestCase):
    """The invariant itself, against the committed tree."""

    def test_discovery_finds_something(self):
        # The runner treats an empty discovery as a failure rather than a
        # silent pass, and a comparison against an empty set is exactly that
        # failure wearing a pass's clothes.
        self.assertTrue(
            discover(),
            'no test_*.py under the repository root. If this suite is the '
            'only one left, the discovery rule is wrong, not the tree.')

    def test_every_discovered_suite_has_a_row(self):
        missing = sorted(discover() - set(readme_rows()))
        self.assertFalse(
            missing,
            f'tools/README.md lists no row for {len(missing)} discovered '
            f'suite(s):\n  ' + '\n  '.join(missing) +
            '\nThe runner picks a new suite up silently by find. The row is '
            'the one step it cannot do, and the description beside it -- '
            'what the suite stands in for -- is prose it has no reason to '
            'know. Add both.')

    def test_every_row_names_a_discovered_suite(self):
        stale = sorted(set(readme_rows()) - discover())
        self.assertFalse(
            stale,
            f'tools/README.md has {len(stale)} row(s) for a suite that is '
            f'not on disk:\n  ' + '\n  '.join(stale) +
            '\nEither the file was renamed or moved, or the row outlived it.')


if __name__ == '__main__':
    unittest.main()
