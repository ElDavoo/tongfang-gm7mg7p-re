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
# The two captures of one fixed-load run, as §3 now takes them: the duty bytes
# arrive in the 0x0700-0x07FF one, the temperatures in the 0x0400-0x045F one,
# and both record a mark for every action.
FIXED_LOAD = (str(HERE / 'testdata'
                  / '0751-isolation-example-fixed-load-0700-07ff.csv'),
              str(HERE / 'testdata'
                  / '0751-isolation-example-fixed-load-0400-045f.csv'))
# The same duty capture against a temperature capture whose CPU_TEMP moves more
# than once inside a window, so the window summary's first->last and its change
# count disagree. Marked to pair with the file above.
MULTI_MOVE = (str(HERE / 'testdata'
                  / '0751-isolation-example-fixed-load-0700-07ff.csv'),
              str(HERE / 'testdata'
                  / '0751-isolation-example-multi-move-0400-045f.csv'))

# §6 of the procedure, reconstructed. The one command line §6 gives a reader
# to run, in §6's own order -- three captures, then the before-dump, then the
# after-dump, then what the block wrote -- over the ten files that section
# names, which testdata/0751-isolation-run/ holds under exactly those names.
RUN = HERE / 'testdata' / '0751-isolation-run'
RUN_CAPTURES = (str(RUN / '2026-01-01-0751-isolation-0700-07ff.csv'),
                str(RUN / '2026-01-01-0751-isolation-0f00-0f5f.csv'),
                str(RUN / '2026-01-01-0751-isolation-0400-045f.csv'))
RUN_BEFORE = str(RUN / '2026-01-01-0751-isolation-a0-before-0700.txt')
RUN_AFTER = str(RUN / '2026-01-01-0751-isolation-a0-after-0700.txt')
# The other pair §3's steps 0 and 6 take, for the fan-table range. These are
# the two dumps §6 listed and nothing read, which is what issue #161 is
# about: they are byte for byte identical by construction, so they exercise
# the whole-block read's "unchanged" branch and its "not covered by this
# pair" lines for §4.1 and §4.3.
RUN_BEFORE_0F00 = str(RUN / '2026-01-01-0751-isolation-a0-before-0f00.txt')
RUN_AFTER_0F00 = str(RUN / '2026-01-01-0751-isolation-a0-after-0f00.txt')
# The third pair, for the temperature range, so that §4.5's two confirmed
# bytes have a whole-block read of their own rather than being named as out
# of reach of every pair. It differs only where the temperature capture
# records movement, so it also covers §4.5's "not covered by this pair" for
# the fan duty and all of §4.1-§4.3.
RUN_BEFORE_0400 = str(RUN / '2026-01-01-0751-isolation-a0-before-0400.txt')
RUN_AFTER_0400 = str(RUN / '2026-01-01-0751-isolation-a0-after-0400.txt')
# The runbook, whose §6 is the list these fixtures are named from.
RUNBOOK = (HERE.resolve().parents[1] / 'docs' / 'hardware-tests'
           / 'manual-fan-ctrl-0751-isolation.md')


def concrete(text):
    """§6's two placeholders, resolved to the fixture's own values.

    Shared by both §6 readers so the fence of names and the fence of the
    command line are read with one spelling of the substitution and not
    two, and applied to the runbook's text rather than to a fixture name --
    it is §6 that carries the placeholders.
    """
    return (text.replace("<date>", "2026-01-01")
                .replace("<value>", "a0"))


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
    names = {concrete(line.strip())
             for line in fence.group(1).splitlines() if line.strip()}
    if not names:
        raise AssertionError("§6's fenced block is empty")
    return names


def section6_command(doc):
    """§6's fenced console block -- whichever fence holds the command line.

    Found by what is in it, not by being the first fence, because §6 also
    fences the ten file names and `section6_file_list` reads that one
    first. A block added above the file names must not be able to take its
    place unnoticed.
    """
    if "\n## 6. " not in doc:
        raise AssertionError("no §6 in the runbook; the command line to "
                             "check has moved or gone")
    section = doc.split("\n## 6. ", 1)[1].split("\n## 7. ", 1)[0]
    # The info string is matched because the command line's fence is tagged
    # `console` and the file names' is not; a fence without one has to be
    # found here too or this walks past the block it is looking for.
    for fence in re.finditer(r"```[a-z]*\n(.*?)```", section, re.S):
        if "grade_0751_isolation.py" in fence.group(1):
            return fence.group(1)
    raise AssertionError("§6 has no fenced command line any more")


# A differing-address line as the report prints it, in the WATCHED and
# CONTEXT buckets. The section cannot simply be swept for every `0xNNNN` it
# holds: WATCHED's own §4.3 label names 0x07C6 whether or not it moved.
VALUE_LINE = re.compile(r'(0x[0-9A-F]{4})  0x[0-9A-F]{2} -> 0x[0-9A-F]{2}')


def differing_addresses(section):
    """The addresses a whole-block section shows as differing, as printed.

    Both buckets that name an address, because they do not print it the
    same way: the graded and context bytes get a value line each, the
    generic "other addresses" bucket gets a flat list on one line.
    """
    lines = section.splitlines()
    found = set(VALUE_LINE.findall(section))
    for i, line in enumerate(lines):
        if line.lstrip().startswith('other addresses that differ'):
            found |= set(re.findall(r'0x[0-9A-F]{4}', lines[i + 1]))
    return found


def dumped_change_addresses():
    """The addresses the captures record moving that a dump actually covers.

    Read out of the three CSVs and the six dumps rather than hardcoded, so
    that editing a fixture on either side has to fail this. The
    intersection is deliberate: §3 dumps one range per pair, so an address
    a capture records moving is in the report only if one of the pairs
    happens to cover it -- the captures are the windowed read, the dumps
    the whole-block one, and neither covers everything on its own.
    """
    moved = set()
    for path in RUN_CAPTURES:
        _, changes = grade.read_capture(path)
        moved |= {c.addr for c in changes}
    covered = set()
    for path in (RUN_BEFORE, RUN_AFTER, RUN_BEFORE_0F00, RUN_AFTER_0F00,
                 RUN_BEFORE_0400, RUN_AFTER_0400):
        covered |= set(grade.read_dump(path))
    return {f"0x{a:04X}" for a in moved & covered}


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
        # No duty or temperature byte moves here, so there is no section for it.
        self.assertNotIn('fan duty / temperature bytes', out)
        self.assertNotIn('window delta', out)

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
        # The window starts at the earliest mark, so the duty change that
        # follows the last press is still timed from the first one.
        self.assertIn('0x075B  0x64 -> 0x66   (+2.4s)', out)

    def test_context_section_names_duty_and_temperature_bytes(self):
        _, out, _ = run(*FIXED_LOAD)
        self.assertIn('fan duty / temperature bytes (§4.4/§4.5)', out)
        self.assertIn('fan duty 0x075B/0x075C -- MAIN_FAN_L/R_DUTY', out)
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

    def test_window_delta_tells_the_control_arm_from_the_write(self):
        _, out, _ = run(*FIXED_LOAD)
        # §4.4's deciding number, one per arm: under the no-op the candidate
        # Duty netted 2, under the write it netted 3. Read off the change rows
        # that is subtraction across two terminal windows; here it is two
        # lines. The sign is there too, on the temperature that comes back
        # down in the restore window.
        self.assertIn('window delta  0x075B  0x64 -> 0x66  net +2  (1 change)',
                      out)
        self.assertIn('window delta  0x075B  0x66 -> 0x69  net +3  (1 change)',
                      out)
        self.assertIn('window delta  0x043E  0x36 -> 0x35  net -1  (1 change)',
                      out)

    def test_window_delta_counts_a_byte_that_moves_repeatedly(self):
        _, out, _ = run(*MULTI_MOVE)
        # In the control window CPU_TEMP goes up twice and back down, so its
        # net (+1 over 3 changes) does not stand for how much it moved; in
        # the write window it climbs three times for +3. Both are printed
        # because a reader comparing the two arms needs the count as well as
        # the endpoints.
        self.assertIn('window delta  0x043E  0x33 -> 0x34  net +1  (3 changes)',
                      out)
        self.assertIn('window delta  0x043E  0x34 -> 0x37  net +3  (3 changes)',
                      out)

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

    # The intersection rule, on the branch §3's own pairs cannot reach: two
    # dumps of one range are the same length, so no fixture has one reaching
    # past the other. `read_dump` returns only what it saw, so comparing the
    # union would call every address past the shorter dump a change -- and
    # 0x0751 sits exactly where a truncated after-dump stops covering it.
    def test_a_truncated_pair_is_a_coverage_gap_not_a_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = Path(tmp) / 'before-0700.txt'
            before.write_text('0750: 00 a0 02 03 04 05 06 07\n')
            after = Path(tmp) / 'after-0700.txt'
            after.write_text('0750: 00 a0 02 03\n')
            _, out, _ = run(QUIET, '--dump-pair', str(before), str(after))
        section = out.split('=== whole-block dump pairs (§4.1-§4.3) ===')[1]
        # Four addresses on both sides, and the four only the before dump
        # has are named as a gap rather than reported as four differences.
        self.assertIn('4 address(es) compared', section)
        self.assertIn('before dump only: 0x0754 0x0755 0x0756 0x0757',
                      section)
        self.assertIn('after dump only:  none', section)
        # None of §4.1-§4.3 and neither §4.4/§4.5 context group is in this
        # dump at all, so all five are named as not covered rather than
        # passing as "unchanged" or dropping out of the section's heading.
        self.assertEqual(section.count('not covered by this pair'), 5)
        self.assertNotIn('unchanged across the block', section)

    # §6's whole-block read, over the same §6 set: what the CSV windows
    # cannot see is a byte that moves between the last mark and the
    # after-dump, or moves and returns inside one sweep, and the three dump
    # pairs §3 takes are the bracket for that.
    def test_dump_pairs_read_the_whole_block(self):
        rc, out, _ = run(*RUN_CAPTURES,
                         '--dump', RUN_BEFORE, '--dump', RUN_AFTER,
                         '--dump-pair', RUN_BEFORE, RUN_AFTER,
                         '--dump-pair', RUN_BEFORE_0F00, RUN_AFTER_0F00,
                         '--dump-pair', RUN_BEFORE_0400, RUN_AFTER_0400,
                         '--wrote', '0xA0')
        self.assertEqual(rc, 0)
        section = out.split('=== whole-block dump pairs (§4.1-§4.3) ===')[1]
        section = section.split('=== what this does and does not settle')[0]

        # The 0F00 pair is byte for byte identical by construction, which is
        # §4.2's prediction in the one form a machine can hold: the fan
        # table is unchanged across the whole block. §4.1 and §4.3 are not
        # in a 0x0F00 dump at all, and are named as not covered rather than
        # passed over in silence -- a range that was never read and a range
        # that was read and did not move are different answers.
        self.assertIn('96 address(es) compared', section)
        self.assertIn('fan table (§4.2): unchanged across the block', section)
        self.assertIn('PL1/PL2/PL4 (§4.1): not covered by this pair', section)
        self.assertIn('fan-table bracket byte 0x07C6 (§4.3): not covered by '
                      'this pair', section)

        # The 0700 pair, the other way round: it covers §4.1 and §4.3 and not
        # §4.2, and holds both of those unchanged across the block.
        self.assertIn('256 address(es) compared', section)
        self.assertIn('PL1/PL2/PL4 (§4.1): unchanged across the block',
                      section)
        self.assertIn('fan-table bracket byte 0x07C6 (§4.3): unchanged across '
                      'the block', section)
        self.assertIn('fan table (§4.2): not covered by this pair', section)

        # Issue #189's criterion, on both context groups. The 0400 pair is
        # 96 bytes like the 0F00 one, so two of the three blocks compare 96
        # addresses and the 0x0700 pair is the odd 256.
        self.assertEqual(section.count('96 address(es) compared'), 2)
        self.assertEqual(section.count('256 address(es) compared'), 1)
        # It reaches §4.5's two temperatures, which no other pair can, and
        # names both of the groups it cannot reach -- the fan duty, and
        # all of §4.1-§4.3 -- rather than dropping them under a heading that
        # promises them. Every pair therefore names both context groups, as
        # a value pair or as *not covered by this pair*.
        self.assertIn('0x043E  0x32 -> 0x37', section)
        self.assertIn('0x044F  0x30 -> 0x32', section)
        self.assertIn('CPU_TEMP 0x043E / GPU_TEMP 0x044F -- confirmed (§4.5): '
                      'not covered by this pair', section)
        self.assertIn('fan duty 0x075B/0x075C -- MAIN_FAN_L/R_DUTY '
                      '(§4.4): not covered by this pair', section)

        # The issue's other criterion: across all three pairs the report
        # shows exactly the addresses the captures record moving -- 0x0751
        # and the sensor-looking 0x0796 in the "other" bucket, 0x0402 from
        # the temperature range, the §4.4 duty pair and the §4.5
        # temperatures under their own heading, printed and not graded.
        # Checked against the captures and the dumps rather than a literal
        # list, so a fixture edit on either side of this fails.
        self.assertEqual(differing_addresses(section),
                         dumped_change_addresses())
        self.assertEqual(differing_addresses(section),
                         {'0x0751', '0x075B', '0x075C', '0x0796',
                          '0x0402', '0x043E', '0x044F'})
        self.assertIn('fan duty 0x075B/0x075C -- MAIN_FAN_L/R_DUTY '
                      '(§4.4)', section)
        self.assertIn('other addresses that differ (2), not graded here',
                      section)
        self.assertIn('other addresses that differ (1), not graded here',
                      section)

        # A wider bracket, not a stronger one, and not a verdict. The
        # closing line is what keeps "unchanged" from being read as "did not
        # move", and the whole-block read stays out of §7's vocabulary.
        self.assertIn('not a claim that it did not move inside the block',
                      section)
        self.assertIn('complementary to the windowed CSV read above, not a '
                      'stronger one', section)
        self.assertNotIn('confirmed-working', section)
        self.assertNotIn('confirmed-inert', section)

    # §6 end to end, over the ten files §6 names and by the command line §6
    # gives. Everything a reader of that command line would take from its
    # output, asserted here, because nothing in the repository had been
    # through the whole of §6 before.
    def test_section6_command_line_over_section6s_file_set(self):
        rc, out, _ = run(*RUN_CAPTURES,
                         '--dump', RUN_BEFORE, '--dump', RUN_AFTER,
                         '--dump-pair', RUN_BEFORE, RUN_AFTER,
                         '--dump-pair', RUN_BEFORE_0F00, RUN_AFTER_0F00,
                         '--dump-pair', RUN_BEFORE_0400, RUN_AFTER_0400,
                         '--wrote', '0xA0')
        self.assertEqual(rc, 0)
        # Three actions, nine MARK rows: each is marked in all three
        # watchers seconds apart, which is what the merge is for.
        self.assertIn('=== 3 window(s), one per mark ===', out)
        self.assertEqual(out.count('no watched byte moved in this window'), 3)
        # §4.4's deciding pair, and it reads ambiguous: the fan duty
        # netted 3 under the no-op and 2 under the write, so the write's
        # movement is inside the control's spread. CPU_TEMP is up across both.
        self.assertIn('window delta  0x075B  0x64 -> 0x67  net +3  (2 changes)',
                      out)
        self.assertIn('window delta  0x075B  0x67 -> 0x69  net +2  (1 change)',
                      out)
        self.assertIn('window delta  0x043E  0x33 -> 0x35  net +2  (1 change)',
                      out)
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
        # The three --dump-pair flags do not disturb that: --dump keeps its own
        # meaning and the readback is still taken from the last of those.
        self.assertIn('2026-01-01-0751-isolation-a0-before-0700.txt: '
                      '0x0751 = 0x10', out)
        self.assertIn('the last dump still holds the written 0xA0', out)
        self.assertIn('that is a readback, not evidence', out)
        self.assertIn('not the call itself', out)
        # And the whole-block read §6's command now also produces, with
        # §4.5's temperatures on the block's two ends -- the one thing the
        # 0x0700 and 0x0F00 pairs could not show at all, and named as out of
        # reach under each of them rather than left out of the section.
        self.assertIn('=== whole-block dump pairs (§4.1-§4.3) ===', out)
        self.assertIn('The whole-block dump pairs above were read as a '
                      'second, wider bracket', out)
        self.assertIn('0x043E  0x32 -> 0x37', out)
        self.assertIn('0x044F  0x30 -> 0x32', out)
        self.assertIn('CPU_TEMP 0x043E / GPU_TEMP 0x044F -- confirmed (§4.5): '
                      'not covered by this pair', out)

    # §6's list and the fixture set are the same set. Equality, not existence:
    # a name changed on one side and not the other, and a stray file, both have
    # to fail rather than quietly pass on a subset.
    def test_section6s_file_list_is_the_fixture_set(self):
        doc = RUNBOOK.read_text(encoding="utf-8")
        listed = {Path(n).name for n in section6_file_list(doc)}
        on_disk = {p.name for p in RUN.iterdir() if p.is_file()}
        self.assertEqual(listed, on_disk)

    # The defect issue #161 was opened for: §6 named the two 0F00 dumps in
    # its file list and nothing in the tool read them. `section6_file_list`
    # takes §6's *first* fence, so a file-role block placed above the file
    # names would take that fence's place and fail the set equality above --
    # but the runbook must not be able to drift back to listing six dumps
    # and handing two of them to nothing, either. So the command block is
    # found by what is in it, and has to name every dump §6 lists.
    def test_section6s_command_reads_every_dump_it_lists(self):
        block = concrete(section6_command(RUNBOOK.read_text(encoding="utf-8")))
        for path in (RUN_BEFORE, RUN_AFTER, RUN_BEFORE_0F00, RUN_AFTER_0F00,
                     RUN_BEFORE_0400, RUN_AFTER_0400):
            self.assertIn(Path(path).name, block)


if __name__ == '__main__':
    unittest.main()
