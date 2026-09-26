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
from pathlib import Path
import sys
import tempfile
import unittest

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


class SkipsDeliberately(unittest.TestCase):
    """Every rule that makes the tool conservative, as a case saying so."""

    def test_denial_is_skipped(self):
        # The rule that keeps the corrected tree green, and the one with a
        # known blind side: a stale denial is not caught.
        text = '`0x07D4` did not move in ' + POWER + '.\n'
        self.assertEqual(drifted(text), (0, None))

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
        # A .txt capture has no row-per-change shape to count, so it is out of
        # the oracle -- but it says so on stderr rather than looking like
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
        # The committed summary opens with three `#` lines. A reader that does
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
    unit granularity deliberately: the corpus is 27,032 units, so a per-unit
    line is not a `--verbose` anyone runs, and the invisibility the issue
    names is a property of the file, not of the sentence.
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
