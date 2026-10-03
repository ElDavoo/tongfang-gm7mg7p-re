#!/usr/bin/env python3
"""Offline checks for check_capture_claims.py: committed files only.

The tool is a pointer-checker, so its failure mode is silence rather than a
crash. Loosen a regex and it stops catching drift while still exiting 0, and
the only thing that notices is a reader who has already been misled -- which
is how issue #265 and the `0x07D4` clause issue #270 retracted were both
found. So what is pinned here is the line between what the tool claims and
what it skips: each rule that makes it conservative gets a case saying so,
because a skip that is not deliberate is the bug.

The fixtures are small enough to write inline, which keeps each case readable
as the sentence it is about rather than as a diff against a stored file, and
that is why the negative case is a quoted sentence rather than a committed
`.md`: a prose file under `ec/` that names a capture and claims a movement is
exactly what the tool flags, so checking one in would make the committed-tree
case red by construction. The captures it is checked *against* are real files
in `testdata/`, read by the real `read_capture()`, so the parse is exercised
rather than stubbed. The last case is the real thing, and it is what says the
tree's prose currently agrees with the captures beside it.
"""
import contextlib
import importlib.util
import io
import os
import re
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).parent
# check_capture_claims imports its walker from check_cluster_citations, the
# way check_register_counts imports trace_xdata_refs; loading it by path is
# no different from running it, and the directory is the same sys.path entry.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_capture_claims', HERE / 'check_capture_claims.py')
ccc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccc)

POWER = 'ec/tools/testdata/capture-claims-example-power-mode-cycle-0700-07ff.csv'
SWEEP = 'ec/tools/testdata/capture-claims-example-ac-plugin-sweep-summary.csv'

# The fixtures, read by the tool's own reader. 0x07C4 has two rows in both and
# no 0x07D4 row in either, which is the shape the pre-#270 sentence contradicts.
INDEX = {name: ccc.read_capture(os.path.join(ccc.REPO, name))
         for name in (POWER, SWEEP)}

# The one committed capture whose counts these cases are argued about: 0x0449
# has 238 rows and 0x044C has 247, which is the pair the count rule has to
# tell apart.
PROFILE = 'evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv'
REAL_INDEX = {PROFILE: ccc.read_capture(os.path.join(ccc.REPO, PROFILE))}

# The committed capture whose *name* states a window: `-0700-07ff`. It is what
# the out-of-window case is argued about, because an address above that window
# is a denial the capture has no opinion about and one below it is not.
POWER_CYCLE = 'evidence/ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv'
CYCLE_INDEX = {POWER_CYCLE: ccc.read_capture(os.path.join(ccc.REPO, POWER_CYCLE))}

# A committed capture whose *name* states no window -- no `-XXXX-YYYY` span
# before `.csv` -- which is what the empty-window case is argued about. Most
# committed captures are like this, so a rule that skipped denials for want of
# a window would skip most of the corpus. `0x06D6` has 602 rows in it and
# `0x0751` none, which is the pair the two empty-window cases turn on.
NO_WINDOW_CAPTURE = 'evidence/ec-watch/2026-09-24-06d9-hold-linux.csv'
NO_WINDOW_INDEX = {NO_WINDOW_CAPTURE: ccc.read_capture(
    os.path.join(ccc.REPO, NO_WINDOW_CAPTURE))}


def claims(text, index=None, suffix='.md'):
    """(problems, claims checked) the tool reports for one piece of prose."""
    with tempfile.NamedTemporaryFile('w', suffix=suffix, delete=False) as f:
        f.write(text)
        path = f.name
    try:
        problems, _, checked = ccc.check(path, index or INDEX, False)
    finally:
        os.unlink(path)
    return problems, checked


def drifted(text, index=None):
    """(count, address) for the first disagreement, for the compact cases."""
    problems, _ = claims(text, index)
    return len(problems), problems[0][3] if problems else None


# A row of the docstring's surface table. Anchored on the pipe, so a bullet or
# a sentence mentioning a file with a number beside it cannot become a row.
SURFACE_ROW = re.compile(
    r"^\|\s*`(?P<path>[^`]+)`\s*\|\s*(?P<claims>\d+)\s*\|\s*"
    r"(?P<presence>\d+)\s*\|\s*(?P<count>\d+)\s*\|\s*$")

# The `--verbose` line for a file that yielded a claim. The other self-report
# line ends in the same words, so the count is matched before that phrase
# rather than the line being filtered on it afterwards.
VERBOSE_CLAIMING = re.compile(r"^\s*(?P<path>\S+):\s*(?P<claims>\d+)\s+claim")

# A pattern that matches nothing, so patching it over `ccc.COUNT` makes the
# count rule's `finditer` yield nothing while the presence rule stands, which
# is what separates the two figures in `derives_presence_split`.
NEVER = re.compile(r"(?!x)x")


# Every capture under `evidence/ec-watch/`, as `main()` builds it. The two
# index constants above are the fixtures and the one capture the count cases
# are argued about; the docstring's table is about the real corpus, so it
# needs the real one.
def committed_index():
    """{path: (per-address, rows, distinct)} for every committed capture."""
    watch = os.path.join(ccc.REPO, ccc.WATCH)
    return {ccc.WATCH + '/' + name: ccc.read_capture(os.path.join(watch, name))
            for name in sorted(os.listdir(watch)) if name.endswith('.csv')}


def docstring_surface():
    """{path: (claims, presence, count)} from the docstring's own table.

    A table is a hand-kept figure like any other, and a regex that matches
    nothing and asserts nothing is exactly the "checker that passes by
    checking nothing" failure this suite's own docstring opens on: the
    membership and per-file cases below would go green against an empty dict.
    So an empty parse raises here, at the one place that knows the table is
    supposed to be there.
    """
    named = {m.group('path'): (int(m.group('claims')), int(m.group('presence')),
                                int(m.group('count')))
             for m in (SURFACE_ROW.match(line)
                       for line in (ccc.__doc__ or '').splitlines()) if m}
    if not named:
        raise AssertionError("the docstring's surface table parsed as no rows")
    return named


def verbose_surface(verbose_output):
    """{path: claims} from a `--verbose` run.

    Only the total, because the total is all `--verbose` prints: the split
    between the two rules is not in the output, and `derives_presence_split`
    is how this suite gets it rather than reading it back off the same line.

    The empty parse raises for the same reason `docstring_surface()` raises on
    one: a run that printed no claiming file at all is a tool that has stopped
    reporting, and returning `{}` would let every membership case read as a
    docstring that names nothing the run confirms.
    """
    surface = {m.group('path'): int(m.group('claims'))
               for m in (VERBOSE_CLAIMING.match(line)
                         for line in verbose_output.splitlines()) if m}
    if not surface:
        raise AssertionError("a --verbose run parsed as no claiming file")
    return surface


def derives_presence_split(path, index):
    """(presence, count) for one file, by dropping the count rule in turn.

    `COUNT` is a module global looked up at call time inside `check()`, so
    neutering it takes the count rule out and leaves the presence rule
    standing: the second total is the presence claims, and the difference is
    the row counts. Which is the only way to get the split without counting
    it off the sentences, and the sentences are the thing under suspicion.
    """
    full = os.path.join(ccc.REPO, path)
    _, _, total = ccc.check(full, index, False)
    with mock.patch.object(ccc, "COUNT", NEVER):
        _, _, without = ccc.check(full, index, False)
    return without, total - without


class ReportsRealDrift(unittest.TestCase):
    """The shape issue #270 retracted, and the numbers it turns on."""

    def test_pre_270_sentence_fails_and_names_the_address(self):
        # The pre-#270 claim, as the note made it: 0x07D4 named as moved in the
        # 2026-09-23 power-mode capture. The capture has no row for it, and
        # this is the case that proves the tool can fail on the bug it was
        # written for rather than only agreeing with the tree.
        text = ('0x07D4 moved at the AC plug-in in ' + POWER + ', the same\n'
                'window in which 0x07C4 and 0x07C6 moved.\n')
        n, addr = drifted(text)
        self.assertEqual((n, addr), (1, '0x07D4'))

    def test_the_true_half_of_that_sentence_is_silent(self):
        # Same sentence, the address that really does have two rows. A checker
        # that only ever fails is not calibrated either.
        text = ('0x07C4 moved at the AC plug-in in ' + POWER + ', the same\n'
                'window in which 0x07C6 moved.\n')
        self.assertEqual(drifted(text), (0, None))

    def test_wrong_row_count_fails(self):
        text = '`0x07C6` moved 17 times in ' + SWEEP + '.\n'
        n, addr = drifted(text)
        self.assertEqual((n, addr), (1, '0x07C6'))

    def test_right_row_count_is_silent(self):
        text = '`0x07C6` moved 18 times in ' + SWEEP + '.\n'
        self.assertEqual(drifted(text), (0, None))

    def test_the_failure_says_the_real_count_and_the_capture(self):
        text = '`0x07C6` moved 17 times in ' + SWEEP + '.\n'
        problems, _ = claims(text)
        self.assertEqual(problems[0][4:], ('count', 17, 18))
        self.assertEqual(problems[0][2], SWEEP)

    def test_the_report_names_the_path_it_is_given(self):
        # `check()` hands back a repository-relative path, so `report()` joins
        # it rather than resolving it again: a relpath over a relative path
        # resolves against the working directory, and on any run from outside
        # the repository root that turns `ec/annotations/registers.yaml` into
        # a chain of `../..`. A report nobody can paste into an editor is a
        # report nobody opens.
        problem = [('ec/annotations/registers.yaml', 1106, SWEEP, '0x07C6',
                    'count', 17, 18)]
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ccc.report(problem), 1)
        line = err.getvalue().splitlines()[0]
        self.assertTrue(line.startswith('ec/annotations/registers.yaml:1106:'), line)
        self.assertNotIn('..', line)
        self.assertIn('0x07C6', line)
        self.assertIn('17', line)
        self.assertIn('18', line)

    def test_wrapped_attribution_is_still_seen(self):
        # The shape the captures' own prose is written in: the capture and the
        # address it is wrong about are not on the same line, and a line-based
        # scan misses it.
        text = ('0x07D4 moved in the same window as 0x07C6, in\n'
                f'`{POWER}`,\n'
                'at the plug-in.\n')
        n, addr = drifted(text)
        self.assertEqual((n, addr), (1, '0x07D4'))

    def test_reported_line_is_the_address_line_not_the_unit_start(self):
        text = ('A sentence that opens here and names no address, and goes on.\n'
                '0x07D4 moved in ' + POWER + '.\n')
        problems, _ = claims(text)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0][1], 2)


class ChecksDenials(unittest.TestCase):
    """A denial is a claim, and it is checked with the polarity inverted.

    A denial is the only shape a retraction takes: #265 and the `0x07D4`
    clause issue #270 withdrew were both written as "this did not happen",
    and while the tool skipped denials a checker that could only see
    attributions would not have noticed either of them coming back. So the
    fixture below is the same pair the presence cases argue about --
    `0x07C4` with two rows and `0x07D4` with none in both committed example
    captures -- read the other way round, which is why no new `.csv` is
    needed for the negative case.
    """

    # findings.md §4g's shape: a swept window, a capture, and three addresses
    # said to have stood still.
    SWEEP_SENTENCE = (
        'Over a sweep of the whole `0x0000-0x07FF` space — 32499 recorded byte\n'
        'changes (' + SWEEP + ') — `0x07B9`, `0x07D0` and `0x07D1` did not\n'
        'change once.\n')

    # findings.md §4g's other shape, and the reason the split exists at all.
    MIXED = (
        '`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv` has\n'
        '`0x0436` moving 4 times — `0x70 -> 0x84 -> 0x98` — with no scatter\n'
        'and `0x0437` never moving — and `0x0438` moving exactly **once**.\n')

    def test_a_false_denial_fails_and_names_the_address(self):
        # The issue's required negative fixture: §4g's sentence with one half
        # false. `0x07C4` really does carry two rows, so saying it never moved
        # is the disagreement, and it has to be reported against that address
        # rather than passing because the sentence also carries two true
        # denials.
        text = '`0x07C4` never moved in ' + POWER + '.\n'
        n, addr = drifted(text)
        self.assertEqual((n, addr), (1, '0x07C4'))

    def test_the_false_denial_names_the_real_row_count(self):
        text = '`0x07C4` never moved in ' + POWER + '.\n'
        problems, _ = claims(text)
        self.assertEqual(problems[0][4:], ('denial', None,
                                           f'{INDEX[POWER][1]} rows, '
                                           f'{INDEX[POWER][2]} distinct addresses'))
        self.assertEqual(problems[0][2], POWER)

    def test_a_true_denial_is_silent(self):
        # The same sentence with the address that really has no row. A
        # checker that only ever fails is not calibrated either.
        text = '`0x07D4` did not move in ' + POWER + '.\n'
        self.assertEqual(drifted(text), (0, None))

    def test_the_sweep_summary_absence_is_checked_and_silent(self):
        # §4g's `0x07B9`/`0x07D0`/`0x07D1`, against the capture it names.
        # The window in the sentence is what puts them in scope: the capture's
        # own name carries none, so without it these would be skipped as
        # unwatched and the finding the section rests on would go unchecked.
        problems, checked = claims(self.SWEEP_SENTENCE)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 3, "one checked denial per named address")

    def test_one_of_those_three_gaining_a_row_would_go_red(self):
        # Sharpness for the case above, and the whole reason to check it: a
        # later capture that gave `0x07D1` a row turns §4g's sentence red.
        text = self.SWEEP_SENTENCE.replace('`0x07D1` did not', '`0x07C6` did not')
        n, addr = drifted(text)
        self.assertEqual((n, addr), (1, '0x07C6'))

    def test_the_pre_265_sentence_still_fails(self):
        # The shape the #265 correction withdrew, and the bug the tool was
        # written for: `0x07D4` attributed to a capture that has no row for
        # it. Gaining the denial rule must not have cost the presence one --
        # a checker that stopped catching this is not calibrated.
        text = ('0x07D4 moved at the AC plug-in in ' + POWER + ', the same\n'
                'window in which 0x07C4 and 0x07C6 moved.\n')
        n, addr = drifted(text)
        self.assertEqual((n, addr), (1, '0x07D4'))

    def test_the_mixed_sentence_reads_both_halves(self):
        problems, checked = claims(self.MIXED, REAL_INDEX)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 4, "0x0436, 0x0437, 0x0438 and the row count")

    def test_the_affirmative_half_is_not_skipped_with_the_denial(self):
        # The other half of the mixed case: `0x0436`'s 4 is a real count and
        # it is the number the #265 correction turns on, so a split that read
        # the denial and dropped the attribution would lose it silently.
        problems, _ = claims(self.MIXED.replace('moving 4 times',
                                                'moving 5 times'), REAL_INDEX)
        self.assertEqual([(p[3], p[4], p[5], p[6]) for p in problems],
                         [('0x0436', 'count', 5, 4)])

    def test_a_denial_outside_the_watched_window_is_a_named_skip(self):
        # The `XDATA_09EB` shape. The capture's own name says `-0700-07ff` and
        # the note says so itself -- "the capture watched 0x0700-0x07FF and
        # never saw 0x09EB" -- so this is a statement about coverage rather
        # than about movement, and reading it as the second is how "not
        # covered" turns into "absent".
        text = (f'Byte {POWER_CYCLE} watched 0x0700-0x07FF and never saw '
                '0x09EB.\n')
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
            f.write(text)
            path = f.name
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                problems, _, checked = ccc.check(path, CYCLE_INDEX, True)
        finally:
            os.unlink(path)
        self.assertEqual((problems, checked), ([], 0), "neither a problem nor a check")
        self.assertIn('denial outside the watched window', err.getvalue())
        self.assertIn('0x09EB', err.getvalue())

    def test_the_window_skip_is_not_a_way_for_a_false_denial_through(self):
        # Sharpness. The same sentence about a byte the capture *did* watch is
        # checked, and `0x07C4` has two rows in that file, so it fails: the
        # skip is scoped to coverage and does not swallow the rule.
        text = (f'Byte {POWER_CYCLE} watched 0x0700-0x07FF and never saw '
                '0x07C4.\n')
        n, addr = drifted(text, CYCLE_INDEX)
        self.assertEqual((n, addr), (1, '0x07C4'))

    def test_a_movement_after_a_bare_connective_is_not_bound_by_the_denial(self):
        # "X did not move in C and Y moved" is one clause carrying both
        # polarities, and `Y` is the subject of the second. A walk that
        # carried the denial over the `and` would judge it by the inverted
        # rule -- and `0x07D5` has no row in that capture, so the presence
        # rule is what has to catch it, as it does on the sentence alone.
        text = (f'`0x07D4` did not move in {POWER_CYCLE} and `0x07D5` moved.\n')
        n, addr = drifted(text, CYCLE_INDEX)
        self.assertEqual((n, addr), (1, '0x07D5'),
                         "the attribution, not the true denial beside it")

    def test_a_true_movement_after_a_bare_connective_is_not_reported(self):
        # The mirror of the case above, and the direction that matters: the
        # sentence is right, and `0x07C4` has two rows in that file. Bound to
        # the denial it would be reported as one the capture contradicts,
        # which is a false positive about a sentence that agrees.
        text = (f'`0x07D4` did not move in {POWER_CYCLE} and `0x07C4` moved.\n')
        self.assertEqual(drifted(text, CYCLE_INDEX), (0, None))

    def test_a_movement_before_a_bare_comma_is_not_bound_by_the_denial(self):
        # The mirror of the two above, and the direction nothing caught: the
        # movement comes first, so the gap out of the cue is a backtick and
        # the *continuation* is what would cross into the clause before it.
        # "`0x07D5` moved, `0x07D4` never moved" has both polarities in one
        # clause and `0x07D5` is the subject of the first, so a walk that
        # carried the denial backwards over the comma would judge it by the
        # inverted rule -- and it has no row in that capture either, so the
        # attribution is what has to catch it, as it does on the sentence.
        text = (f'`0x07D5` moved, `0x07D4` never moved in {POWER_CYCLE}.\n')
        n, addr = drifted(text, CYCLE_INDEX)
        self.assertEqual((n, addr), (1, '0x07D5'),
                         "the attribution, not the true denial beside it")

    def test_a_true_movement_before_a_bare_comma_is_not_reported(self):
        # The true-prose twin, and the false positive the backward walk used
        # to produce: `0x07C4` has two rows in that file and the sentence says
        # it moved, so binding it to the denial reports a sentence that agrees
        # with the capture as one it contradicts.
        text = (f'`0x07C4` moved, `0x07D4` never moved in {POWER_CYCLE}.\n')
        self.assertEqual(drifted(text, CYCLE_INDEX), (0, None))

    def test_the_em_dash_form_was_never_in_the_denial_walk(self):
        # The negative half of the case above, and the reason it is worth
        # keeping: `CLAUSE` splits an em or en dash, so this shape has always
        # put the movement in a clause of its own and the gap the continuation
        # would have crossed is not one the walk sees. It holds for a boundary
        # the splitter makes rather than for a rule in the walk, which is
        # exactly the difference the bare comma above does not get.
        text = (f'`0x07D5` moved — `0x07D4` never moved in {POWER_CYCLE}.\n')
        n, addr = drifted(text, CYCLE_INDEX)
        self.assertEqual((n, addr), (1, '0x07D5'))

    def test_a_coordinated_subject_still_binds_across_its_connective(self):
        # Sharpness for the two above: the connective has to stop the *first*
        # hop, not the walk. "`0x07B9`, `0x07D0` and `0x07D1` did not change
        # once" is one coordinated subject of three, and reading only the
        # nearest of them would check one address where the prose is about
        # three.
        text = ('Over a sweep of the whole `0x0000-0x07FF` space — 32499 '
                f'recorded byte changes ({SWEEP}) — `0x07B9`, `0x07D0` and '
                '`0x07D1` did not change once.\n')
        problems, checked = claims(text)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 3, "one checked denial per coordinated address")

    def test_a_denial_in_a_capture_with_no_window_is_checked_not_skipped(self):
        # A capture whose name carries no span and whose unit names no range
        # is not windowed at all, so there is no address it is said not to
        # have watched and the denial is checked like any other. `0x06D6` has
        # 602 rows in that file, so it fails: an empty window is not a way
        # through, and not being windowed is not an excuse.
        text = f'`0x06D6` never moved in {NO_WINDOW_CAPTURE}.\n'
        n, addr = drifted(text, NO_WINDOW_INDEX)
        self.assertEqual((n, addr), (1, '0x06D6'))

    def test_a_true_denial_in_a_capture_with_no_window_is_silent(self):
        # The other half of the pair above: the same capture, an address it
        # really has no row for, checked rather than passed over. Skipping it
        # left a skip line standing where a check belonged.
        text = f'`0x0751` never moved in {NO_WINDOW_CAPTURE}.\n'
        self.assertEqual(drifted(text, NO_WINDOW_INDEX), (0, None))

    def test_verbose_reports_a_denial_as_checked_rather_than_skipped(self):
        # The inventory line. While denials were skipped this read
        # `skip (denies movement)`, and a reader auditing what is covered had
        # no way to tell a checked denial from an unchecked one.
        text = '`0x07D4` did not move in ' + POWER + '.\n'
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
            f.write(text)
            path = f.name
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                problems, _, checked = ccc.check(path, INDEX, True)
        finally:
            os.unlink(path)
        self.assertEqual((problems, checked), ([], 1))
        self.assertIn('1 claim(s) checked', err.getvalue())
        self.assertNotIn('denies movement', err.getvalue())


class SkipsDeliberately(unittest.TestCase):
    """Every rule that makes the tool conservative, as a case saying so."""

    def test_range_bound_is_skipped(self):
        # 0x0700-0x07FF names the watched window, not two bytes that moved in
        # it, and neither bound has a row in any committed capture.
        text = ('Sweeping `0x0700-0x07FF` in ' + POWER + ' changed exactly one\n'
                'non-sensor byte, `0x07A6`, once per switch.\n')
        self.assertEqual(drifted(text), (0, None))

    def test_address_beside_a_filename_is_not_a_claim(self):
        # The door procedure's own preamble shape: two captures named so
        # nobody mistakes them for a run, with a block address beside them.
        text = ('The committed captures are not a run of this: ' + POWER + '\n'
                'and ' + SWEEP + '. `0x07C0`-`0x07D7` is the block.\n')
        self.assertEqual(drifted(text), (0, None))

    def test_txt_capture_is_reported_not_passed_over(self):
        # A .txt capture is out of the oracle -- `main()` indexes the .csv
        # files and this one is not among them, so there is no row set to hold
        # a claim against -- but it says so on stderr rather than looking like
        # nothing to check.
        text = ('`0x07A6` moved in '
                'evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt.\n')
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
            f.write(text)
            path = f.name
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                problems, _, _ = ccc.check(path, INDEX, True)
        finally:
            os.unlink(path)
        self.assertEqual(problems, [])
        self.assertIn('not a .csv', err.getvalue())

    def test_derived_counts_are_not_row_counts(self):
        # All three are true, and none is a row count for a named address:
        # 32499 is the full log the committed summary was derived from, and
        # 102/449/297 are paired-sample figures over a derived set.
        for stated in ('32499 recorded byte changes', '102 of 449 paired samples',
                       '297 paired samples'):
            text = (f'`0x07C6` appears in {SWEEP} over {stated}.\n')
            self.assertEqual(drifted(text), (0, None), stated)

    def test_a_count_with_no_address_near_it_is_not_checked(self):
        # Prose outside a YAML entry has no entry to carry the subject down
        # from, and an address more than COUNT_WINDOW away is not one to guess
        # at: 238 is 0x0449's real count in one committed capture and 0x07C6's
        # in neither, so binding it to the wrong one would be a disagreement
        # invented here rather than found in the prose.
        text = f'The sweep recorded 238 changes in {SWEEP} over the plug-in.\n'
        self.assertEqual(drifted(text), (0, None))

    def test_word_numerals_are_not_read_as_counts(self):
        # "changed exactly one non-sensor byte, this one, once per switch" is
        # three rows of 0x07A6 in the committed capture, and reading the `one`
        # as a count would report a disagreement that does not exist.
        text = (f'Cycling the three battery modes changed exactly one non-sensor\n'
                f'byte, `0x07A6`, once per switch in {POWER}.\n')
        problems, checked = claims(text)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 1, "presence is still checked; only the count is not")

    def test_capture_not_in_the_tree_is_skipped(self):
        # A prose path that resolves nowhere cannot be counted, and reporting
        # it as a disagreement would be reporting the checker, not the prose.
        text = '`0x07A6` moved in evidence/ec-watch/2026-01-01-not-here.csv.\n'
        self.assertEqual(drifted(text), (0, None))

    def test_addr_key_is_a_declaration_not_a_claim(self):
        # The entry's own `addr:` line says which address the entry is about;
        # it does not say that address moved in a capture. Without the rule,
        # an entry for a byte that never moved is reported on the strength of
        # its own header. The distinction has to be per line and not per file,
        # so the note's own 0x07C4 -- which is also a declared address in its
        # own right, in a different entry -- is still checked.
        text = ('  - name: XDATA_07D4\n'
                '    addr: 0x07D4\n'
                '    status: present-untested\n'
                '    note: >\n'
                f'      0x07C4 moved at the AC plug-in in {POWER}.\n')
        problems, checked = claims(text)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 1, "the note's 0x07C4, and not the header's 0x07D4")

    def test_address_in_either_named_capture_passes(self):
        # The weaker sense the docstring promises: a unit naming two captures
        # is satisfied if the address is in one of them.
        text = (f'`0x0449` moved 238 times in evidence/ec-watch/'
                f'2026-09-18-profile-switch-0400-07ff.csv and {SWEEP}.\n')
        index = dict(INDEX)
        index['evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv'] = \
            ccc.read_capture(os.path.join(
                ccc.REPO, 'evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv'))
        self.assertEqual(drifted(text, index), (0, None))


class SubjectResolution(unittest.TestCase):
    """Which address a stated count is about, which is the easy thing to get
    backwards and the reason the count rule keys on the entry rather than on
    proximity."""

    def yaml(self, addr_line, note):
        return (f'  - name: XDATA_0449\n{addr_line}    static_refs: 4\n'
                f'    status: present-untested\n    note: >\n'
                + "".join(f"      {line}\n" for line in note.split("\n")))

    NOTE = ('Moved 238 times in '
            'evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv, the\n'
            'second-busiest byte on the page after 0x044C.')

    def test_count_binds_to_the_entry_addr_not_the_comparison(self):
        # 0x044C is nearer in the text than anything else, and it is the
        # comparison, not the subject. Binding to it compares 238 with 247 and
        # reports a disagreement that does not exist.
        self.assertEqual(drifted(self.yaml('    addr: 0x0449\n', self.NOTE),
                                 REAL_INDEX), (0, None))

    def test_a_wrong_count_is_reported_against_the_entry_addr(self):
        note = self.NOTE.replace('238 times', '300 times')
        problems, _ = claims(self.yaml('    addr: 0x0449\n', note), REAL_INDEX)
        self.assertEqual([(p[3], p[4], p[5], p[6]) for p in problems],
                         [('0x0449', 'count', 300, 238)])

    def test_list_addr_entry_has_no_subject(self):
        # "the entry" is then two addresses, and picking one of them is the
        # guess this tool exists to stop making. The sharpness is that the
        # note still names 0x044C: had the list `addr:` fallen through to the
        # proximity rule, the 238 would have bound to it and been compared
        # against its real 247.
        text = self.yaml('    addr: [0x0436, 0x0437]\n', self.NOTE)
        problems, checked = claims(text, REAL_INDEX)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 1, "0x044C's presence, and not the 238")

    def test_prose_without_an_entry_uses_the_nearest_address(self):
        # The system-id-0456-bit6-divisor.md shape, where there is no entry to
        # carry down and the count's own subject is the address beside it.
        text = ('The one capture covering the byte,\n'
                '`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv`,\n'
                'has `0x0449` across `0x22`-`0x5A` over 238 changes.\n')
        self.assertEqual(drifted(text, REAL_INDEX), (0, None))

    def test_a_two_digit_range_bound_is_not_an_address(self):
        # `0x22`-`0x5A` is the span 0x0449 took, not two XDATA addresses, and a
        # two-digit token must not be widened into one.
        text = ('`0x07D4` moved in ' + POWER + ' across 0x22-0x5A over 238 changes.\n')
        n, addr = drifted(text)
        self.assertEqual((n, addr), (1, '0x07D4'), "238 is not 0x07D4's count either")


class CaptureParsing(unittest.TestCase):
    """The CSV read, so a change to the tool's idea of a capture is caught."""

    def test_sweep_summary_comment_lines_are_dropped_before_the_header(self):
        # The committed summary opens with a `#` block. A reader that does
        # not drop them first takes a comment as the fieldnames and finds no
        # addr column -- which reads as "the file has no rows", not as a parser
        # that skipped what it should not have.
        per, rows, distinct = ccc.read_capture(os.path.join(
            ccc.REPO, 'evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv'))
        self.assertEqual((rows, distinct), (205, 205))
        self.assertEqual(per['0x07C4'], 2)

    def test_derived_summary_counts_changes_not_rows(self):
        # One row per address, so a row tally would report 1 for an address
        # the full log changed 18 times.
        self.assertEqual(INDEX[SWEEP][0]['0x07C6'], 18)
        self.assertEqual(INDEX[SWEEP][0]['0x07A6'], 3)

    def test_row_tally_capture_counts_rows(self):
        self.assertEqual(INDEX[POWER][0]['0x07C4'], 2)
        self.assertEqual(INDEX[POWER][0]['0x07A6'], 1)
        self.assertNotIn('0x07D4', INDEX[POWER][0])

    def test_address_case_does_not_silently_match_nothing(self):
        # `0X0449` in prose and `0x0449` in a file are one address. A `.upper()`
        # applied before matching makes every capture look empty, and the
        # checker that ships that way passes by checking nothing.
        self.assertEqual(ccc.normalise('0X0449'), '0x0449')
        text = ('`0X0449` moved 238 times in evidence/ec-watch/'
                '2026-09-18-profile-switch-0400-07ff.csv.\n')
        self.assertEqual(drifted(text, REAL_INDEX), (0, None))


class TheFileLevelSelfReport(unittest.TestCase):
    """A file read in full that names no claim is named and counted.

    #975's second half. `if not captures: continue` was the one skip in
    `check()` that printed nothing, so a file walked end to end and finding
    no claim looked exactly like a file nobody opened -- which is most of the
    corpus, and how a whole column of claims stayed invisible to a reader who
    had every reason to look. The count is at **file** granularity and not at
    unit granularity deliberately: a line per unit would name every unit in
    `ROOTS` that yields no claim, which is not a `--verbose` anyone runs, and
    the invisibility the issue names is a property of the file, not of the
    sentence.
    """

    NO_CLAIM = 'A paragraph that names no capture at all.\n'

    def verbose_check(self, text, index=None):
        """(problems, checked, the `--verbose` lines) for one piece of prose."""
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
            f.write(text)
            path = f.name
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                problems, _, checked = ccc.check(path, index or INDEX, True)
        finally:
            os.unlink(path)
        return problems, checked, err.getvalue()

    def test_a_file_naming_no_claim_says_so_in_verbose(self):
        problems, checked, err = self.verbose_check(self.NO_CLAIM)
        self.assertEqual((problems, checked), ([], 0))
        self.assertIn('read in full, no claim to check', err)

    def test_a_file_naming_a_claim_is_counted_instead_of_reported_empty(self):
        # The other half: the new line is an `else`, not an addition. A file
        # that *does* yield a claim keeps the count it always had and is not
        # also reported as one that found nothing.
        text = f'`0x07C4` moved at the AC plug-in in {POWER}.\n'
        problems, checked, err = self.verbose_check(text)
        self.assertEqual((problems, checked), ([], 1))
        self.assertIn('1 claim(s) checked', err)
        self.assertNotIn('no claim to check', err)

    def test_the_summary_count_decomposes_the_file_total(self):
        # The number is worth having only if a reader can take it apart, and
        # this is what takes it apart: the two `--verbose` lines partition the
        # files the summary counts, and the two partition sums to it. Nothing
        # here is a floor -- the point is the arithmetic, not the figures.
        out, err = io.StringIO(), io.StringIO()
        argv = sys.argv
        sys.argv = ['check_capture_claims.py', '--check', '--verbose']
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = ccc.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, err.getvalue())
        verbose = err.getvalue().splitlines()
        claiming = sum(1 for line in verbose if 'claim(s) checked' in line)
        empty = sum(1 for line in verbose if 'no claim to check' in line)
        summary = [line for line in out.getvalue().splitlines()
                   if ' files / ' in line]
        self.assertEqual(len(summary), 1, "the summary line moved or split")
        total = int(summary[0].split(' files / ')[0])
        self.assertEqual(claiming + empty, total)
        counted = [line for line in out.getvalue().splitlines()
                   if 'no capture claim' in line]
        self.assertEqual(len(counted), 1)
        self.assertEqual(int(counted[0].split(' ')[0]), empty,
                         "the summary's own count disagrees with the lines "
                         "`--verbose` printed for the same run")

    def test_the_new_line_is_not_the_one_the_suite_parses(self):
        # `test_committed_prose_matches_committed_captures` reads the claim
        # count by splitting the summary on `' lines / '`, so the new count
        # has to be a line of its own rather than something appended to that
        # one. This is the constraint written down, and it is a constraint on
        # the shape of the output rather than on its wording.
        out = io.StringIO()
        argv = sys.argv
        sys.argv = ['check_capture_claims.py', '--check']
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                ccc.main()
        finally:
            sys.argv = argv
        text = out.getvalue()
        head, _, tail = text.partition('\n')
        self.assertNotIn(' lines / ', tail,
                         "the new count must be a line of its own")
        # The suite's own parse, unchanged: the claim count is still the first
        # number after ` lines / ` on the line that has always held it.
        checked = int(head.split(' lines / ')[1].split(' ')[0])
        self.assertIn(f'{checked} capture claims checked', head)


class TheDocstringSurface(unittest.TestCase):
    """The docstring's own table, held to what a run prints on the same tree.

    The tool reports on itself at file granularity (the class above), and the
    docstring quotes that self-report back. That makes the same surface read
    twice, and the two reads had drifted: the paragraph named five presence
    claims and two row counts in two files where the run reports nine claims
    in three. Issue #991 corrected the paragraph; this class is what stops the
    correction going stale in the other direction.

    **Subset, not equality, and the direction is the whole argument.** A file
    is named in that table because a claim in it was checked, so membership is
    a real invariant and equality is not -- the next capture a human commits
    into the prose adds a row to the run and to nobody's table. And a stale
    docstring has only ever drifted by *gaining* a file it does not name,
    which is the same direction a run then confirms and the table does not.
    So a fourth claiming file in the output, unnamed in the docstring, is a
    green case here and the case below says so on purpose.

    A floor would be the wrong shape for the same reason the row-claim suite
    asserts a decomposition rather than a figure: an expected total turns
    every added capture into a red suite.

    The per-file figures are held as well, because a file can stay named and
    go wrong, and the presence/count split is re-derived from the walk rather
    than read off the sentences -- the sentences being the thing under
    suspicion. Three of the cases are synthetic and doctored deliberately: an
    assertion nobody has seen fail is not evidence of anything.
    """

    @classmethod
    def setUpClass(cls):
        # One real run, shared by the class. `--verbose` is the only thing
        # that prints a per-file count, and it is a whole-corpus walk; three
        # cases reading the same output do not need three walks, and the run
        # is the tree's, so there is nothing to keep fresh between them.
        out, err = io.StringIO(), io.StringIO()
        argv = sys.argv
        sys.argv = ['check_capture_claims.py', '--check', '--verbose']
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                cls.rc = ccc.main()
        finally:
            sys.argv = argv
        cls.claimed = verbose_surface(err.getvalue())
        cls.named = docstring_surface()
        cls.index = committed_index()

    def assert_named_files_yield_claims(self, named, run, why):
        """Every file the docstring names is one a run reports a claim for."""
        for path in sorted(named):
            self.assertIn(path, run,
                          f"{why}: {path} is named and no run confirms it")
            self.assertGreaterEqual(run[path], 1,
                                    f"{why}: {path} is named and yields no claim")

    def assert_quoted_figures_match(self, named, run, why):
        """Each total the docstring quotes is the one the run prints."""
        for path, (claims, _presence, _count) in sorted(named.items()):
            self.assertEqual(run.get(path), claims, f"{why}: {path}")

    def test_every_file_the_docstring_names_yields_a_claim(self):
        self.assert_named_files_yield_claims(self.named, self.claimed, "docstring")

    def test_each_figure_the_docstring_quotes_is_the_one_the_run_prints(self):
        self.assert_quoted_figures_match(self.named, self.claimed, "docstring")

    def test_the_split_is_the_one_the_walk_derives(self):
        # Re-derived rather than read off the sentences, because the sentence
        # is what went wrong: the old paragraph said five presence claims for
        # `registers.yaml` where the walk finds four, its `XDATA_0449` note
        # yielding both a count and a presence claim for the `0x044C` it names.
        for path, (_claims, presence, count) in sorted(self.named.items()):
            self.assertEqual(derives_presence_split(path, self.index),
                             (presence, count), path)

    def test_neutering_the_count_rule_is_what_moves_the_split(self):
        # The sibling suite's drop-it-in-turn, inverted: loosening the count
        # rule checks *fewer* claims, which is the direction the split moves.
        # A derivation answering the same way under both walks would make every
        # row count above zero by accident, and this is what says they are
        # measured rather than read back.
        for path, (_claims, presence, _count) in sorted(self.named.items()):
            full = os.path.join(ccc.REPO, path)
            without, _delta = derives_presence_split(path, self.index)
            self.assertEqual(without, presence, path)
            self.assertLess(without, ccc.check(full, self.index, False)[2], path)

    def test_the_membership_case_fails_on_a_file_no_run_confirms(self):
        # Sharpness. The same assertion that is green against the tree above,
        # given a file the run says nothing about.
        named = dict(self.named)
        named['docs/hardware-tests/never-opened-by-this-tool.md'] = (1, 1, 0)
        with self.assertRaises(AssertionError):
            self.assert_named_files_yield_claims(named, self.claimed, "synthetic")

    def test_the_figure_case_fails_on_a_total_the_run_disagrees_with(self):
        # Sharpness the other way: the file is real and named, and the figure
        # beside it is not the one the run prints.
        named = dict(self.named)
        path = sorted(self.named)[0]
        claims, presence, count = self.named[path]
        named[path] = (claims + 1, presence, count)
        with self.assertRaises(AssertionError):
            self.assert_quoted_figures_match(named, self.claimed, "synthetic")

    def test_a_claiming_file_the_docstring_does_not_name_still_passes(self):
        # The direction a stale docstring has always drifted, held green. A
        # new capture committed into the prose lands here first and in the
        # table only when somebody writes it down, and nothing in this case
        # makes that somebody's failure.
        run = dict(self.claimed)
        run['docs/hardware-tests/a-capture-committed-after-this-table.md'] = 3
        self.assert_named_files_yield_claims(self.named, run, "synthetic")
        self.assert_quoted_figures_match(self.named, run, "synthetic")


class TheCommittedTree(unittest.TestCase):
    """The real thing: the prose and the captures beside it currently agree.

    This is the assertion that would have caught the `0x07D4` clause, and it
    is the one that goes red on any future edit that drifts a claim, which is
    the point of having the tool in the tree at all. The #270 correction bought
    it: the checker passing *now* is the evidence it is calibrated to the tree
    rather than to the bug.
    """

    def test_committed_prose_matches_committed_captures(self):
        # A run that reports 0 claims checked and 0 problems is green for the
        # wrong reason, and the count it prints is the only way to tell -- so
        # the surface is asserted non-empty here rather than taken on trust.
        # This is not a floor on coverage: nothing says the number has to stay
        # at whatever it is today, only that a run reaching nothing fails.
        err = io.StringIO()
        out = io.StringIO()
        argv = sys.argv
        sys.argv = ['check_capture_claims.py', '--check']
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = ccc.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, err.getvalue())
        self.assertIn('capture claims checked', out.getvalue())
        checked = int(out.getvalue().split(' lines / ')[1].split(' ')[0])
        self.assertGreater(checked, 0)


if __name__ == '__main__':
    unittest.main()
