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
# The same PWM capture against a temperature capture whose CPU_TEMP moves more
# than once inside a window, so the window summary's first->last and its change
# count disagree. Marked to pair with the file above.
MULTI_MOVE = (str(HERE / 'testdata'
                  / '0751-isolation-example-fixed-load-0700-07ff.csv'),
              str(HERE / 'testdata'
                  / '0751-isolation-example-multi-move-0400-045f.csv'))

# §6 of the procedure, reconstructed. The one command line §6 gives a reader
# to run, in §6's own order -- three captures, then the before-dump, then the
# after-dump, then what the block wrote -- over the eight files that section
# names, which testdata/0751-isolation-run/ holds under exactly those names.
RUN = HERE / 'testdata' / '0751-isolation-run'
RUN_CAPTURES = (str(RUN / '2026-01-01-0751-isolation-0700-07ff.csv'),
                str(RUN / '2026-01-01-0751-isolation-0f00-0f5f.csv'),
                str(RUN / '2026-01-01-0751-isolation-0400-045f.csv'))
RUN_BEFORE = str(RUN / '2026-01-01-0751-isolation-a0-before-0700.txt')
RUN_AFTER = str(RUN / '2026-01-01-0751-isolation-a0-after-0700.txt')
# The runbook, whose §6 is the list these fixtures are named from.
RUNBOOK = (HERE.resolve().parents[1] / 'docs' / 'hardware-tests'
           / 'manual-fan-ctrl-0751-isolation.md')


def section6_file_list(doc):
    """The file names §6 lists, with the two placeholders substituted.

    Read out of the runbook rather than restated, because §6 is the contract
    the fixtures are named from: a rename on either side has to be a change
    to both or a failing test, not a silent disagreement. Raises rather than
    returning nothing if the section or its fenced list cannot be found, so a
    restructure cannot turn this into a test that passes on an empty set.
    """
    if "\n## 6. " not in doc:
        raise AssertionError("no §6 in the runbook; the file list to check "
                             "the fixtures against has moved or gone")
    section = doc.split("\n## 6. ", 1)[1].split("\n## 7. ", 1)[0]
    fence = re.search(r"```\n(.*?)```", section, re.S)
    if fence is None:
        raise AssertionError("§6 has no fenced file list any more")
    names = {line.strip().replace("<date>", "2026-01-01").replace("<value>", "a0")
             for line in fence.group(1).splitlines() if line.strip()}
    if not names:
        raise AssertionError("§6's fenced block is empty")
    return names


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
        # No PWM or temperature byte moves here either, but the section is
        # printed anyway; the zero lines it carries are the subject of
        # test_a_byte_that_held_still_is_a_zero_and_not_a_missing_line below.

    # The blind spot #168 is about. A context byte that did not move used to
    # get no line at all, so "the no-op arm moved 0x075B and the write arm
    # shows nothing" read as missing data rather than as the strongest negative
    # result the procedure can produce -- and "no line" is the shape a correct
    # `confirmed-inert` answer takes, so the absence was self-cancelling.
    def test_a_byte_that_held_still_is_a_zero_and_not_a_missing_line(self):
        rc, out, _ = run(QUIET)
        self.assertEqual(rc, 0)
        # Both windows, both groups, all four bytes.
        self.assertEqual(out.count('candidate PWM / temperature bytes'), 2)
        self.assertEqual(out.count('window delta'), 8)
        # No context byte appears anywhere in this capture, so its level is
        # genuinely not in evidence and the line has to say so rather than fill
        # something in. The zero figures are still correct: a change-row
        # capture records transitions, so a byte that never appears did not
        # move, and that is the claim being made about it.
        for addr in ('0x075B', '0x075C', '0x043E', '0x044F'):
            self.assertIn(f'window delta  {addr}  ???? -> ????  net +0  '
                          'total 0  max 0  '
                          '(0 changes, level not in these captures)', out)

    def test_a_byte_that_held_still_carries_its_level_forward(self):
        _, out, _ = run(*MULTI_MOVE)
        # CPU_TEMP climbs three times in the write window and holds in the
        # restore window after it. The level the restore window opened on is
        # the one the write window left it at, which build_windows knows only
        # because it tracks the last value through the windows rather than
        # re-deriving each one from its own change rows -- and from the
        # settling change the captures carry before the first mark, which
        # belong to no window but still establish the byte's level.
        self.assertIn('window delta  0x043E  0x37 -> 0x37  net +0  '
                      'total 0  max 0  (0 changes)', out)
        self.assertNotIn('window delta  0x043E  ????', out)
        # 0x044F never appears in either capture, so the same window cannot
        # claim to know its level: known-to-be-still and level-in-evidence
        # are two separate facts and the line keeps them apart.
        self.assertIn('window delta  0x044F  ???? -> ????  net +0  '
                      'total 0  max 0  '
                      '(0 changes, level not in these captures)', out)

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
        # Every byte in every window, not only the ones that moved: three
        # windows x two groups x two addresses. A section that went missing
        # where a byte held still is the ambiguity #168 is about, and it is
        # the shape a correct `confirmed-inert` answer takes, so it has to
        # fail here rather than read as a result.
        self.assertEqual(out.count('window delta'), 12)
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

    def test_window_delta_tells_the_control_arm_from_the_write(self):
        _, out, _ = run(*FIXED_LOAD)
        # One line per arm, so the comparison is two lines rather than two
        # terminals of subtraction. On this fixture 0x075B takes a single
        # monotonic step in each arm, so net, total and max are the same
        # number and the choice between them changes nothing here -- which is
        # the point: the step-response figure is not the deciding one, it just
        # happens to agree with the others when the response is a clean step.
        # The sign is there too, on the temperature that comes back down in
        # the restore window, where the three figures part company: net -1,
        # total 1, max 1.
        self.assertIn('window delta  0x075B  0x64 -> 0x66  net +2  total 2  '
                      'max 2  (1 change)', out)
        self.assertIn('window delta  0x075B  0x66 -> 0x69  net +3  total 3  '
                      'max 3  (1 change)', out)
        self.assertIn('window delta  0x043E  0x36 -> 0x35  net -1  total 1  '
                      'max 1  (1 change)', out)

    def test_window_delta_counts_a_byte_that_moves_repeatedly(self):
        _, out, _ = run(*MULTI_MOVE)
        # The fixture the statistic is argued from, on the byte whose two
        # statistics disagree: in the control window CPU_TEMP goes up twice
        # and back down, so its net (+1) is a third of the movement behind it
        # (total 3), while in the write window it climbs three times and all
        # three figures are 3. Read as nets, the two arms look like the write
        # moved three times as far as the control. Read as total movement --
        # which is what §4.4 keys the control-vs-write comparison on -- they
        # moved identically, and the threefold net is an artefact of where the
        # byte happened to end up.
        self.assertIn('window delta  0x043E  0x33 -> 0x34  net +1  total 3  '
                      'max 2  (3 changes)', out)
        self.assertIn('window delta  0x043E  0x34 -> 0x37  net +3  total 3  '
                      'max 3  (3 changes)', out)

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

    def test_a_dump_header_comment_is_skipped(self):
        # §6 tells the operator to annotate what they hand in, and
        # read_capture has always let them. A comment carrying a colon is the
        # case that shows whether read_dump skips them too -- without the skip
        # it reaches int() and raises instead of reading the dump.
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / 'plain-0700.txt'
            plain.write_text('0750: 00 a0 02 03\n')
            annotated = Path(tmp) / 'annotated-0700.txt'
            annotated.write_text('# ecrw.py dump 0x0700 0x0100: before, a0 block\n'
                                 '0750: 00 a0 02 03\n')
            self.assertEqual(grade.read_dump(str(plain))[0x0751], 0xA0)
            self.assertEqual(grade.read_dump(str(annotated)),
                             grade.read_dump(str(plain)))
            _, out, _ = run(QUIET, '--dump', str(annotated), '--wrote', '0xA0')
        self.assertIn('0x0751 = 0xA0', out)

    # §6 end to end, over the eight files §6 names and by the command line §6
    # gives. Everything a reader of that command line would take from its
    # output, asserted here, because nothing in the repository had been
    # through the whole of §6 before.
    def test_section6_command_line_over_section6s_file_set(self):
        rc, out, _ = run(*RUN_CAPTURES,
                         '--dump', RUN_BEFORE, '--dump', RUN_AFTER,
                         '--wrote', '0xA0')
        self.assertEqual(rc, 0)
        # Three actions, nine MARK rows: each is marked in all three
        # watchers seconds apart, which is what the merge is for.
        self.assertIn('=== 3 window(s), one per mark ===', out)
        self.assertEqual(out.count('no watched byte moved in this window'), 3)
        # §4.4's comparison, and it reads ambiguous: the candidate PWM moved
        # 3 under the no-op and 2 under the write, so the write's movement is
        # inside the control's spread. Both figures agree here -- the no-op
        # 0x075B climbs monotonically over two changes, so net, total and max
        # are all 3, against the write arm's all-2 over one -- so the
        # statistic §4.4 now keys on does not change what this capture says.
        # CPU_TEMP is up across both, which is why the drift reads as
        # thermal.
        self.assertIn('window delta  0x075B  0x64 -> 0x67  net +3  total 3  '
                      'max 3  (2 changes)', out)
        self.assertIn('window delta  0x075B  0x67 -> 0x69  net +2  total 2  '
                      'max 2  (1 change)', out)
        self.assertIn('window delta  0x043E  0x33 -> 0x35  net +2  total 2  '
                      'max 2  (1 change)', out)
        # §4.1-§4.3, the half the script does apply, and the half the dumps
        # then confirm: nothing the prediction named moved in any window.
        self.assertIn('None of the §4.1-§4.3 bytes moved', out)
        self.assertNotIn('At least one of the §4.1-§4.3 bytes moved', out)
        # The fan-table capture contributes its three marks and no change
        # rows at all -- §4.2's prediction as the grader sees it.
        self.assertIn('2026-01-01-0751-isolation-0f00-0f5f.csv: 3 mark(s), '
                      '0 change row(s)', out)
        # §4.6: the after-dump is the last --dump, which is why §6 says to put
        # it last -- and holding the written value is a readback, not a result.
        self.assertIn('2026-01-01-0751-isolation-a0-before-0700.txt: '
                      '0x0751 = 0x10', out)
        self.assertIn('the last dump still holds the written 0xA0', out)
        self.assertIn('that is a readback, not evidence', out)
        self.assertIn('not the call itself', out)

    # §6's list and the fixture set are the same set. Equality, not existence:
    # a name changed on one side and not the other, and a stray file, both have
    # to fail rather than quietly pass on a subset.
    def test_section6s_file_list_is_the_fixture_set(self):
        doc = RUNBOOK.read_text(encoding="utf-8")
        listed = {Path(n).name for n in section6_file_list(doc)}
        on_disk = {p.name for p in RUN.iterdir() if p.is_file()}
        self.assertEqual(listed, on_disk)


if __name__ == '__main__':
    unittest.main()
