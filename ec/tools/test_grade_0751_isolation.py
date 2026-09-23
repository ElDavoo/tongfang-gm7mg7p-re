#!/usr/bin/env python3
"""Offline checks against the constructed captures in testdata/; no hardware
and no real capture is involved."""
import contextlib
import importlib.util
import io
from pathlib import Path
import re
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    'grade', HERE / 'grade_0751_isolation.py')
grade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grade)

QUIET = str(HERE / 'testdata' / '0751-isolation-example-quiet.csv')
ACTIVE = str(HERE / 'testdata' / '0751-isolation-example-active.csv')
# The two captures of one fixed-load run, as §3 now takes them: the PWM bytes
# arrive in the 0x0700-0x07FF one, the temperatures in the 0x0400-0x045F one,
# and both record a mark for every action.
FIXED_LOAD = (str(HERE / 'testdata'
                  / '0751-isolation-example-fixed-load-0700-07ff.csv'),
              str(HERE / 'testdata'
                  / '0751-isolation-example-fixed-load-0400-045f.csv'))


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = grade.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


class GradeTests(unittest.TestCase):
    def test_quiet_capture_reports_nothing_moved(self):
        rc, out, _ = run(QUIET)
        self.assertEqual(rc, 0)
        self.assertEqual(out.count('no watched byte moved in this window'), 2)
        self.assertIn('None of the §4.1-§4.3 bytes moved', out)
        # The sensor-looking addresses are context, not a graded result.
        self.assertIn('0x0796 0x079A', out)
        # No PWM or temperature byte moves here, so there is no section for it.
        self.assertNotIn('candidate PWM / temperature bytes', out)

    def test_active_capture_names_the_byte_and_its_offset(self):
        rc, out, _ = run(ACTIVE)
        self.assertEqual(rc, 0)
        self.assertIn('0x0784  0x50 -> 0x28   (+0.4s)', out)
        self.assertIn('0x07C6  0x00 -> 0x01', out)
        self.assertIn('At least one of the §4.1-§4.3 bytes moved', out)
        self.assertNotIn('no watched byte moved', out)

    def test_one_action_marked_in_every_watcher_is_one_window(self):
        rc, out, _ = run(*FIXED_LOAD)
        self.assertEqual(rc, 0)
        # Six MARK rows across the two captures, but three actions: the marks
        # of one action are seconds apart and open a single window.
        self.assertIn('=== 3 window(s), one per mark ===', out)
        self.assertEqual(out.count('no watched byte moved in this window'), 3)
        # The window starts at the earliest mark, so the PWM change that
        # follows the last press is still timed from the first one.
        self.assertIn('0x075B  0x64 -> 0x66   (+2.4s)', out)

    def test_context_section_names_pwm_and_temperature_bytes(self):
        _, out, _ = run(*FIXED_LOAD)
        self.assertIn('candidate PWM / temperature bytes (§4.4/§4.5)', out)
        self.assertIn('candidate fan PWM 0x075B/0x075C -- unconfirmed', out)
        self.assertIn('CPU_TEMP 0x043E / GPU_TEMP 0x044F -- confirmed', out)
        # Both arms, so the no-op control and the write under test are
        # comparable line for line: 0x075B +2 in the control, +3 under the
        # write, and CPU_TEMP still climbing across both.
        self.assertIn('0x075B  0x66 -> 0x69   (+2.8s)', out)
        self.assertIn('0x043E  0x33 -> 0x35   (+9.0s)', out)
        self.assertIn('0x044F  0x30 -> 0x31   (+4.0s)', out)

    def test_pwm_and_temperature_movement_is_not_a_graded_result(self):
        _, out, _ = run(*FIXED_LOAD)
        # Every window moves PWM and a temperature, none moves §4.1-§4.3.
        self.assertIn('None of the §4.1-§4.3 bytes moved', out)
        self.assertNotIn('At least one of the §4.1-§4.3 bytes moved', out)

    def test_context_addresses_leave_the_other_addresses_bucket(self):
        _, out, _ = run(*FIXED_LOAD)
        lines = out.splitlines()
        i = next(i for i, l in enumerate(lines)
                 if l.lstrip().startswith('other addresses that moved'))
        # 0x0402 is in the temperature capture but is neither of the two
        # confirmed bytes; 0x075B/0x043E have their own section above.
        self.assertEqual(re.findall(r'0x[0-9A-F]{4}', lines[i + 1]), ['0x0402'])

    def test_no_capture_claims_a_status(self):
        for argv in ([QUIET], [ACTIVE], list(FIXED_LOAD)):
            _, out, _ = run(*argv)
            # §7's verdicts may only be quoted as what this output is *not*.
            self.assertIn('not the call itself', out)
            self.assertIn('context, not a result', out)
            self.assertIn('CPU package power (§4.5) is in no EC sweep', out)

    def test_changes_before_the_first_mark_belong_to_no_window(self):
        _, out, _ = run(QUIET)
        # 0x0796 moves at 12:00:02, eight seconds before the first mark.
        self.assertNotIn('(+-', out)
        self.assertEqual(out.count('0x0796'), 2)

    def test_capture_without_marks_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'nomarks.csv'
            p.write_text('ts,addr,old,new\n'
                         '2026-01-01T12:00:02.000+01:00,0x0784,0x50,0x28\n')
            rc, _, err = run(str(p))
        self.assertEqual(rc, 1)
        self.assertIn('no MARK rows', err)

    def test_dump_readback_is_not_reported_as_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            after = Path(tmp) / 'after-0700.txt'
            after.write_text('0750: 00 a0 02 03 04 05 06 07\n')
            rc, out, _ = run(QUIET, '--dump', str(after), '--wrote', '0xA0')
        self.assertEqual(rc, 0)
        self.assertIn('0x0751 = 0xA0', out)
        self.assertIn('that is a readback, not evidence', out)

    def test_dump_disagreeing_with_the_written_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            after = Path(tmp) / 'after-0700.txt'
            after.write_text('0750: 00 00\n')
            _, out, _ = run(QUIET, '--dump', str(after), '--wrote', '0xA0')
        self.assertIn('something put it back', out)


if __name__ == '__main__':
    unittest.main()
