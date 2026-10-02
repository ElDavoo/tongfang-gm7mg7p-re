#!/usr/bin/env python3
"""Offline checks that every suite describes itself, and that tools/README.md does not.

`run-tests.sh` discovers suites by `find`, so a suite is picked up by having
its file committed and nothing else. What a suite stands in for is its module
docstring: `python3 tools/list_suites.py` prints every suite with the first
line of it.

Until 2026-10-02 the description was a hand-written row in a table in
tools/README.md, and this file held the table to the discovered set. Every
pull request that added a suite added a row to that one table, so it was in
about half of main's commits and was a merge conflict between any two branches
whose rows landed next to each other. The rows mostly restated the docstrings.
So the description now lives in the suite's own file, which no other branch
edits. This checks that every discovered suite has a docstring, and that the
README has not grown the table back.

The counts are never compared: an expected count turns every added test into a
failure, which is the wrong trade, and the same reason `run-tests.sh` reports
its totals rather than asserting them.
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
    """Suite rows tools/README.md carries right now, on disk -- none, by design."""
    return [p for p in table_rows(README.read_text())
            if posixpath.basename(p).startswith('test_')]


def docstring_of(rel):
    """The module docstring of one suite, or '' when it has none."""
    import ast
    source = (REPO / rel).read_text(encoding='utf-8')
    return ast.get_docstring(ast.parse(source)) or ''


def readme_lead(text):
    """The prose above the first table line, or the whole file when it has none.

    The counter this file used to carry lived in the lead, so the lead is where
    a total is a mistake. A table further down may say how many cases its own
    subject has, which is documentation rather than a claim about the
    repository, so the scan stops at the first one.
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

    def test_every_discovered_suite_describes_itself(self):
        bare = sorted(rel for rel in discover() if not docstring_of(rel).strip())
        self.assertFalse(
            bare,
            f'{len(bare)} discovered suite(s) have no module docstring:\n  ' +
            '\n  '.join(bare) +
            '\nThe docstring is where a suite says what it stands in for; '
            '`python3 tools/list_suites.py` is how a reader finds it. Write one '
            'at the top of the file.')

    def test_the_readme_does_not_grow_a_suite_table_back(self):
        rows = readme_rows()
        self.assertFalse(
            rows,
            f'tools/README.md carries {len(rows)} suite row(s) again:\n  ' +
            '\n  '.join(rows) +
            '\nA suite describes itself in its own docstring. A shared table that '
            'every branch adding a suite edits is a merge conflict, which is why '
            'it was removed. Move the description into the suite\'s docstring.')

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
            f'per-suite counts in a suite\'s own docstring are fine and are not what '
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
