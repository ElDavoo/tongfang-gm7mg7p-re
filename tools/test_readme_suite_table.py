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
import posixpath
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


# Trees a `find` from the repository root walks into but the committed tree does
# not contain. `.claude/` is the one that bites: `git worktree add` under
# `.claude/worktrees/` puts a whole second checkout inside this one, so a
# developer with any worktree open counts three suites CI cannot see and a
# developer with none does not -- the same figures, reproducible on one machine
# and not the other. `vendor/` holds binaries, not suites. This is the pruning
# `ec/tools/census_test_line_pins.py` already carries for the same reason; the
# two lists should be read together, because a suite set that is well defined in
# one tool and not the other is two answers to one question.
PRUNED = ('.git', '.claude', 'vendor')


def discover():
    """The suites `run-tests.sh` finds, by the runner's own rule.

    The same `test_*.py` pattern and the same `.git` exclusion as the
    runner's find, copied rather than reinvented: a suite the runner runs and
    this check has never heard of is a suite with no row, and that is the
    half that broke. Recomputed per call rather than cached at import, so a
    case can point it at a scratch tree.

    `PRUNED` is walked out of the top of the relative path, so a checkout
    nested at any depth is skipped rather than only one at the root.
    """
    found = set()
    for path in REPO.rglob('test_*.py'):
        rel = path.relative_to(REPO)
        if rel.parts[0] in PRUNED:
            continue
        found.add(rel.as_posix())
    return found


def is_suite_row(path):
    """Whether a table row is about a suite, as opposed to a plain tool.

    The table documents checkers as well as suites -- `check_findings_frozen.py`
    and `gen_findings_index.py` are rows here and have no `test_` suite of
    their own, because a checker with no suite is exactly the thing this table
    exists to make visible. So the "a row outlived its file" direction applies
    to rows that name a `test_*.py`, and a row naming any other tool is
    documentation the reverse check has no opinion about. Without this the
    check is red on a correct table, which is how a gate teaches everyone to
    ignore it.
    """
    return posixpath.basename(path).startswith('test_')


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


def readme_lead(text):
    """The prose above the table: everything before the first table line.

    Scoped deliberately. The counter this file used to carry lived in the lead,
    so the lead is where a total is a mistake -- but a *row* is allowed to say
    how many cases its own suite has, and `at 36 cases` or `twenty-four tests`
    is documentation, not a claim about the repository. A whole-file rule would
    go red on that and teach everyone to ignore this suite, which is the same
    failure `is_suite_row` exists to avoid.
    """
    for line in text.splitlines():
        if line.startswith('|'):
            break
        yield line


# A number immediately followed by `suite`/`test`. Digits only, not the spelled
# words: "Three suites that landed in parallel with it" is prose about three
# named suites and is not a total, and a rule that reddened on it would be a rule
# nobody keeps. Every historical instance is digits -- `1561 tests in all`,
# `48 suites`, `1740 tests` -- so digits lose nothing and cost no false positive.
# Measured on the pre-2026-09-27 file: 214 matches, against 0 in the current one.
TOTAL_SHAPED = re.compile(r'\d[\d,]*\s+(?:suite|test)s?\b', re.I)

# The other half of the same disease, and the reason the numbers were corrected
# in place rather than edited: a correction *chain*. Twenty-two of these were
# appended to one sentence, all in the same spot, which is what made the file a
# merge conflict as well as a stale one.
SUPERSESSION_NOTE = re.compile(r'\*\(Superseded\b')


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

    def test_every_suite_row_names_a_discovered_suite(self):
        # Suite rows only. A row for a checker with no suite of its own is a
        # correct row; see `is_suite_row`.
        stale = sorted(p for p in set(readme_rows())
                       if is_suite_row(p) and p not in discover())
        self.assertFalse(
            stale,
            f'tools/README.md has {len(stale)} row(s) for a suite that is '
            f'not on disk:\n  ' + '\n  '.join(stale) +
            '\nEither the file was renamed or moved, or the row outlived it.')

    def test_the_lead_states_no_total(self):
        # The whole point. This file carried "There are forty-nine today, 1561
        # tests in all" for long enough to collect 3,522 lines of correction
        # under it, every one appended at the same spot by a branch that had
        # added a suite. The total is the runner's last line and belongs there.
        lead = '\n'.join(readme_lead(README.read_text()))
        found = TOTAL_SHAPED.findall(lead)
        self.assertFalse(
            found,
            f'tools/README.md\'s lead states {len(found)} total-shaped figure(s): '
            f'{found}\nA number of suites or tests written here is a claim about a '
            f'tree that stops being true the moment a suite lands, and correcting '
            f'it in place is what grew this section to 3,522 lines. Run '
            f'`bash tools/run-tests.sh` and read its last line; if the lead needs '
            f'to say how big this is, point at that instead of restating it. The '
            f'per-suite counts in the table rows below are fine and are not what '
            f'this reads.')

    def test_the_lead_carries_no_correction_chain(self):
        # The other half. Even with the total gone there is nothing to supersede,
        # so a chain here means one was reintroduced by another route.
        lead = '\n'.join(readme_lead(README.read_text()))
        found = SUPERSESSION_NOTE.findall(lead)
        self.assertFalse(
            found,
            f'tools/README.md\'s lead carries {len(found)} supersession note(s). '
            f'A correction to this file belongs in a `docs/findings/` write-up -- '
            f'the twenty-two that were here are preserved verbatim in '
            f'`docs/findings/tools-readme-totals.md` -- not appended to a '
            f'paragraph in the file they correct.')


if __name__ == '__main__':
    unittest.main()
