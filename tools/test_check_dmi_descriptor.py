#!/usr/bin/env python3
"""Offline checks for the prepared GM7MG7P DMI entry in `linux/patches/gm7mg7p-dmi-entry/`.

`check_dmi_descriptor.py` holds the rules. This suite is what keeps the rules
*run* and the map from drifting under them, and it runs with no network, no EC
and no laptop -- like everything else here, it is a check on the shape of a
claim and never on whether the claim is right.

**What is checked here rather than in the checker.** The checker validates the
map against `ec/annotations/registers.yaml` on every run; duplicating that as
assertions would only re-state it. What lives here is the set of things a
*future edit* could break that a re-run of the checker would not catch:

  * the map still covers every feature issue #10 asked about. A row deleted to
    tidy the table would leave the checker perfectly green -- it has no opinion
    about which features *should* be considered -- while an exclusion and its
    cited reason quietly stopped existing. The set is held here for the reason
    `test_agent_gates_patches.py` holds its `PATCHES` list.
  * the checker's own `--self-test` still refuses. A suite that drives a
    self-test as a nested run, the way `ec/tools/test_pd_image_census.py`
    drives `disasm8051.py --self-test`, so a rule that has stopped refusing
    is a red suite rather than a checker that looks healthy.
  * `--check` refuses *exactly* the missing patch, and nothing else. This is
    what makes the current red meaningful: it is one known, named gap, not a
    general failure someone should learn to ignore. A second refusal appearing
    here is a real claim this repository cannot back.

**The current state is one refusal, and the suite pins that.** The prepared
patch is the one deliverable in that directory which needs the network, and it
is not committed. `check_dmi_descriptor.py --check` exits 1 because of it and
because of nothing else, and the cases below are what make that statement
checkable rather than a claim in a README.
"""
import subprocess
import sys
import unittest
from pathlib import Path

import check_dmi_descriptor as chk

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CHECKER = HERE / 'check_dmi_descriptor.py'

# The features issue #10 asked the descriptor to resolve or drop, and the ones
# it listed as confirmed working. Held here rather than derived from the map,
# because the map is the thing under test: read the set out of the artifact it
# polices and a row deleted from that artifact deletes its own coverage check
# with it. A row leaving this list is a deliberate change and should fail here
# with a reason, not pass quietly.
ISSUE_FEATURES = {
    'BATTERY_CHARGE_LIMIT', 'AC_AUTO_BOOT', 'USB_POWERSHARE',
    'USB_C_POWER_PRIORITY', 'NVIDIA_CTGP_CONTROL', 'TOUCHPAD_TOGGLE',
    'LIGHTBAR', 'CPU_TEMP', 'GPU_TEMP', 'PRIMARY_FAN', 'SECONDARY_FAN',
    'FN_LOCK', 'SUPER_KEY', 'KEYBOARD_BACKLIGHT', 'BATTERY_CHARGE_MODES',
}

MAP_ROWS = chk.read_map()


def run_checker(*flags):
    done = subprocess.run([sys.executable, str(CHECKER), *flags],
                          capture_output=True, text=True, cwd=REPO)
    return done.returncode, done.stdout, done.stderr


class MapShapeTests(unittest.TestCase):
    """The map is parseable, complete, and every row says why."""

    def test_the_map_parses_and_has_rows(self):
        # An empty parse matches an empty set of everything below, which is
        # the vacuous pass `tools/run-tests.sh`'s empty-discovery guard exists
        # for, one level down.
        self.assertTrue(MAP_ROWS,
                        f'{chk.MAP} parsed to no rows. If the file is the one '
                        'this suite is about, the CSV shape has changed and '
                        'the checker has to change with it.')

    def test_the_header_is_the_one_the_checker_expects(self):
        path = REPO / chk.MAP
        header = path.read_text(encoding='utf-8').splitlines()[0]
        self.assertEqual(header.split(','), list(chk.COLUMNS))

    def test_every_row_carries_a_reason(self):
        # An exclusion with no written reason is a decision nobody recorded,
        # and it is the failure this whole artifact exists to prevent. The
        # reason is the only column no check can verify for *truth*, so
        # requiring one on every row -- included or not -- is the floor.
        for row in MAP_ROWS:
            with self.subTest(feature=row['repo_feature']):
                self.assertTrue(
                    row['reason'].strip(),
                    f"{row['repo_feature']} has an empty reason column. Every "
                    "row states the finding that justifies its verdict, "
                    "including the ones that are included.")

    def test_every_excluded_row_cites_a_committed_file(self):
        # A reason that names no file is an assertion. The charge rows and the
        # status rows can all point at something; a row that cannot is one
        # whose verdict nobody recorded.
        for row in MAP_ROWS:
            if row['in_descriptor'] == 'yes':
                continue
            with self.subTest(feature=row['repo_feature']):
                self.assertTrue(
                    any(token in row['reason'] for token in
                        ('.md', '.csv', '.yaml', 'docs/findings.md',
                         'registers.yaml', 'static-refs-audit.md')),
                    f"{row['repo_feature']} is excluded and its reason names no "
                    "committed file. An exclusion has to say what was checked "
                    "and where the check is recorded.")

    def test_the_map_covers_every_feature_the_issue_raised(self):
        covered = {row['repo_feature'] for row in MAP_ROWS}
        missing = sorted(ISSUE_FEATURES - covered)
        self.assertFalse(
            missing,
            f'the map has no row for {len(missing)} feature(s) issue #10 '
            f'raised:\n  ' + '\n  '.join(missing) +
            '\nA feature the issue asked to "resolve or drop" has to appear '
            'as a row with a verdict, even when the verdict is that it needs '
            'the driver source. Dropping the row drops the reason with it.')

    def test_no_feature_is_listed_twice(self):
        names = [row['repo_feature'] for row in MAP_ROWS]
        self.assertEqual(sorted(names), sorted(set(names)),
                         'two rows for one feature, which is a disagreement '
                         'the checker would report as a bit mismatch instead')


class CommittedEvidenceTests(unittest.TestCase):
    """The map agrees with `registers.yaml`, and with itself about it."""

    def setUp(self):
        self.statuses = chk.registers_index()
        self.values, self.suffixes = chk.declared_statuses()

    def test_every_status_is_a_declared_value(self):
        # Same rule the checker applies, asserted here so a map edit that
        # broke it is a suite failure naming the row rather than a checker
        # failure buried in a --check run nobody reads.
        self.assertFalse(chk.rule_vocabulary(MAP_ROWS, self.values,
                                             self.suffixes))

    def test_every_address_is_real_and_every_status_agrees(self):
        self.assertFalse(chk.rule_addresses(MAP_ROWS, self.statuses,
                                            self.suffixes))

    def test_the_base_commit_and_the_nix_recipe_agree(self):
        # Rule 3's first two legs. The third needs the patch, which is the
        # one thing this directory does not have yet.
        self.assertFalse(chk.rule_base_commit(None))

    def test_inclusion_needs_a_confirmed_status_an_address_and_a_source(self):
        self.assertFalse(chk.rule_include(MAP_ROWS, (self.values,
                                                     self.suffixes)))

    def test_every_bit_spelling_is_sourced(self):
        # With no patch committed there is no `upstream@<rev>` route, so this
        # is the rule that keeps the map to the two spellings a committed
        # file actually quotes.
        self.assertFalse(
            chk.rule_bit_sourcing(MAP_ROWS, set(), chk.base_rev()))

    def test_the_pr_body_carries_the_board_identity(self):
        self.assertFalse(chk.rule_pr_body(
            (REPO / chk.PR_BODY).read_text(encoding='utf-8'), MAP_ROWS))

    def test_the_exactly_one_included_feature_is_the_charge_modes(self):
        # Pinned rather than derived, because "one bit, and it is the charge
        # modes" is the finding this artifact records. A second row flipping
        # to yes is a real change with real evidence behind it, and it should
        # arrive as a deliberate edit here rather than as a quiet diff.
        included = sorted(row['repo_feature'] for row in MAP_ROWS
                          if row['in_descriptor'] == 'yes')
        self.assertEqual(included, ['BATTERY_CHARGE_MODES'])


class RefusalSetTests(unittest.TestCase):
    """`--check` refuses the missing patch and nothing else.

    The artifact is incomplete, and the current refusal is one named gap rather
    than a general red. That is a claim worth pinning: a second refusal here
    is a claim this repository cannot back, and it would arrive as a suite
    failure naming the checker's own message.
    """

    def test_check_exits_nonzero(self):
        rc, _out, _err = run_checker('--check')
        self.assertNotEqual(rc, 0)

    def test_the_only_refusal_is_the_missing_patch(self):
        _rc, _out, err = run_checker('--check')
        refusals = [ln for ln in err.splitlines() if 'REFUSED' in ln]
        self.assertEqual(
            len(refusals), 1,
            'the prepared entry refuses ' + str(len(refusals)) + ' thing(s); '
            'it should refuse exactly the one this suite documents:\n  '
            + '\n  '.join(refusals))
        self.assertIn(chk.PATCH, refusals[0])

    def test_the_missing_patch_is_reported_not_swallowed(self):
        # A run that found nothing must not read as a run that passed. The
        # banner and the refusal are the same fact in two places on purpose:
        # one for a person reading the output top to bottom, one for anything
        # reading the exit code.
        _rc, out, err = run_checker('--check')
        self.assertIn('INCOMPLETE', out)
        self.assertIn('curl', out,
                      'the banner has to say how to close the gap, not only '
                      'that there is one')
        self.assertIn(chk.PATCH, err)

    def test_the_map_level_rules_ran_despite_the_missing_patch(self):
        # The point of skipping rules rather than bailing: the rules that do
        # not need the patch still have something to say, and a checker that
        # returned early would make every one of them silently vacuous. The
        # refusal set above is the other half -- it says they ran *and* that
        # they found nothing, which an early return would also satisfy.
        _rc, out, err = run_checker('--check')
        self.assertIn('feature rows', out)
        self.assertIn('include rule', out)
        self.assertNotIn(
            'feature-map.csv', err,
            'a refusal naming a map row means a row failed a rule, rather '
            'than the patch being the only gap')


class SelfTestTests(unittest.TestCase):
    """The checker's own `--self-test` still passes, and still pins every rule.

    Driven as a nested run rather than imported, so it is the same entry point
    a maintainer types. A rule that has quietly stopped refusing leaves the
    checker looking healthy and this red.
    """

    def test_self_test_passes(self):
        rc, out, err = run_checker('--self-test')
        self.assertEqual(rc, 0, f'--self-test failed:\n{out}\n{err}')
        self.assertIn('self-test passed', out)

    def test_every_rule_is_pinned_by_the_self_test(self):
        # `--self-test` is *the refusals themselves* -- that is what
        # `check_status_vocabulary.py` says of its own, and a rule added
        # without a case pinning it is a rule nothing has ever seen refuse.
        # Read the rule set off the module and the self-test's source, and
        # require the second to mention every name in the first.
        import inspect
        rules = {name for name, obj in vars(chk).items()
                 if name.startswith('rule_') and inspect.isfunction(obj)}
        self.assertTrue(rules, 'no rule_* functions found on the checker; the '
                               'name convention is what this test keys on')
        source = inspect.getsource(chk.self_test)
        unpinned = sorted(name for name in rules if name not in source)
        self.assertFalse(
            unpinned,
            f'{len(unpinned)} rule(s) are never exercised by --self-test:\n  '
            + '\n  '.join(unpinned) +
            '\nA rule with no case pinning it is a rule nothing has watched '
            'refuse, which is the same as a check that has stopped checking.')


if __name__ == '__main__':
    unittest.main()
