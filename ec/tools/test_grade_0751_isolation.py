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
# The other pair §3's steps 0 and 6 take, for the fan-table range. These are
# the two dumps §6 listed and nothing read, which is what issue #161 is
# about: they are byte for byte identical by construction, so they exercise
# the whole-block read's "unchanged" branch and its "not covered by this
# pair" lines for §4.1 and §4.3.
RUN_BEFORE_0F00 = str(RUN / '2026-01-01-0751-isolation-a0-before-0f00.txt')
RUN_AFTER_0F00 = str(RUN / '2026-01-01-0751-isolation-a0-after-0f00.txt')

# Three constructed dump pairs, each a copy of the corresponding `RUN` page
# with the smallest edit that reaches a branch §3's own fixtures cannot: the
# `RUN` pairs differ only where the captures record movement, and the 0F00
# pair is byte-for-byte identical, so the whole-block read's value line -- the
# `else` that prints `0xNNNN 0xXX -> 0xXX` under a heading -- had no fixture
# to run it. They sit beside the CSV examples and not in `0751-isolation-run/`,
# which is the set §6's file list is held equal to.
EXAMPLE = HERE / 'testdata'
PL2_PAIR = (str(EXAMPLE / '0751-isolation-example-moved-pl2-before-0700.txt'),
            str(EXAMPLE / '0751-isolation-example-moved-pl2-after-0700.txt'))
FAN_PAIR = (str(EXAMPLE / '0751-isolation-example-moved-fan-before-0f00.txt'),
            str(EXAMPLE / '0751-isolation-example-moved-fan-after-0f00.txt'))
MAILBOX_PAIR = (
    str(EXAMPLE / '0751-isolation-example-moved-mailbox-before-0f00.txt'),
    str(EXAMPLE / '0751-isolation-example-moved-mailbox-after-0f00.txt'))
# The same mailbox poke as a change row rather than as a dump difference, for
# the windowed reader: `report_window` files the group the same way and its
# closing paragraph has to keep the difference between the two apart.
MAILBOX_CSV = str(EXAMPLE / '0751-isolation-example-mailbox-poke.csv')

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
    fences the eight file names and `section6_file_list` reads that one
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


def whole_block(out):
    """The whole-block dump-pair section, and nothing after it.

    One spelling of the two splits, which two tests each carried inline: a
    section that later grew a header of its own would then be found by
    whichever of the two had been updated.
    """
    return out.split('=== whole-block dump pairs (§4.1-§4.3) ===')[1] \
               .split('=== what this does and does not settle')[0]


def group_body(section, name):
    """The lines under a `    {name}:` heading, up to the next one.

    Cut by heading rather than searched for as a substring, so "reported
    under its own §4.x heading" is an assertion about where a line sits and
    not merely that the line is in the section somewhere. A note printed
    under a group comes back with its value lines, which is the point: the
    explanation and the bytes it explains are read together.
    """
    heading = f"    {name}:"
    if heading not in section:
        raise AssertionError(f"no {name!r} heading in the section; a watched "
                             "group's heading is what this reads")
    body = []
    for line in section.split(heading, 1)[1].splitlines()[1:]:
        # A group body is indented six spaces. The next group heading, the
        # coverage-gap notice and the "other addresses" bucket are at four,
        # and the section's closing paragraph at two, so all three end the
        # body; blank lines are kept so a value line's spacing survives.
        if line.strip() and not line.startswith("      "):
            break
        body.append(line)
    return "\n".join(body)


def value_lines(text):
    """The differing-address lines in a group body, as printed."""
    return [l for l in text.splitlines() if VALUE_LINE.search(l)]


def dumped_change_addresses():
    """The addresses the captures record moving that a dump actually covers.

    Read out of the three CSVs and the four dumps rather than hardcoded, so
    that editing a fixture on either side has to fail this. The
    intersection is deliberate: the 0x0400-0x045F capture has change rows
    and §3 takes no dump of that range, so no pair can be expected to show
    them -- the captures are the windowed read, the dumps the whole-block
    one, and neither covers everything.
    """
    moved = set()
    for path in RUN_CAPTURES:
        _, changes = grade.read_capture(path)
        moved |= {c.addr for c in changes}
    covered = set()
    for path in (RUN_BEFORE, RUN_AFTER, RUN_BEFORE_0F00, RUN_AFTER_0F00):
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
        # No PWM or temperature byte moves here, so there is no section for it.
        self.assertNotIn('candidate PWM / temperature bytes', out)
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

    def test_window_delta_tells_the_control_arm_from_the_write(self):
        _, out, _ = run(*FIXED_LOAD)
        # §4.4's deciding number, one per arm: under the no-op the candidate
        # PWM netted 2, under the write it netted 3. Read off the change rows
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
        section = whole_block(out)
        # Four addresses on both sides, and the four only the before dump
        # has are named as a gap rather than reported as four differences.
        self.assertIn('4 address(es) compared', section)
        self.assertIn('before dump only: 0x0754 0x0755 0x0756 0x0757',
                      section)
        self.assertIn('after dump only:  none', section)
        # None of §4.1-§4.3 is in this dump at all, so all four watched
        # groups are named as not covered rather than passing as "unchanged".
        self.assertEqual(section.count('not covered by this pair'), 4)
        self.assertNotIn('unchanged across the block', section)

    # §6's whole-block read, over the same §6 set: what the CSV windows
    # cannot see is a byte that moves between the last mark and the
    # after-dump, or moves and returns inside one sweep, and the two dump
    # pairs §3 takes are the bracket for that.
    def test_dump_pairs_read_the_whole_block(self):
        rc, out, _ = run(*RUN_CAPTURES,
                         '--dump', RUN_BEFORE, '--dump', RUN_AFTER,
                         '--dump-pair', RUN_BEFORE, RUN_AFTER,
                         '--dump-pair', RUN_BEFORE_0F00, RUN_AFTER_0F00,
                         '--wrote', '0xA0')
        self.assertEqual(rc, 0)
        section = whole_block(out)

        # The 0F00 pair is byte for byte identical by construction, which is
        # §4.2's prediction in the one form a machine can hold: the fan
        # table is unchanged across the whole block. §4.1 and §4.3 are not
        # in a 0x0F00 dump at all, and are named as not covered rather than
        # passed over in silence -- a range that was never read and a range
        # that was read and did not move are different answers. The reload
        # trigger is in a 0x0F00 dump, and gets the read-and-did-not-move
        # answer: the split put it in a bucket of its own, not in a gap.
        self.assertIn('96 address(es) compared', section)
        self.assertIn('fan table (§4.2): unchanged across the block', section)
        self.assertIn('PL1/PL2/PL4 (§4.1): not covered by this pair', section)
        self.assertIn('fan-table bracket byte 0x07C6 (§4.3): not covered by '
                      'this pair', section)
        self.assertIn(f'{grade.TRIGGER_GROUP}: unchanged across the block',
                      section)

        # The 0700 pair, the other way round: it covers §4.1 and §4.3 and not
        # §4.2, and holds both of those unchanged across the block.
        self.assertIn('256 address(es) compared', section)
        self.assertIn('PL1/PL2/PL4 (§4.1): unchanged across the block',
                      section)
        self.assertIn('fan-table bracket byte 0x07C6 (§4.3): unchanged across '
                      'the block', section)
        self.assertIn('fan table (§4.2): not covered by this pair', section)

        # The issue's criterion: across both pairs the report shows exactly
        # the addresses the captures record moving -- 0x0751 and the
        # sensor-looking 0x0796 in the "other" bucket, the §4.4 candidate
        # PWM pair under its own heading, printed and not graded. Checked
        # against the captures rather than a literal list, so a fixture
        # edit on either side of this fails.
        self.assertEqual(differing_addresses(section),
                         dumped_change_addresses())
        self.assertEqual(differing_addresses(section),
                         {'0x0751', '0x075B', '0x075C', '0x0796'})
        self.assertIn('candidate fan PWM 0x075B/0x075C -- unconfirmed '
                      '(§4.4)', section)
        self.assertIn('other addresses that differ (2), not graded here',
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

    # The whole-block read's value line -- the `else` that prints
    # `0xNNNN  0xXX -> 0xXX` under a heading -- had no fixture to run it: the
    # §6 pairs differ only at addresses WATCHED does not name. These three
    # cover it per group, and the two fan-table ones cover the split.
    def test_dump_pair_reports_a_pl_that_moved(self):
        rc, out, _ = run(QUIET, '--dump-pair', *PL2_PAIR)
        self.assertEqual(rc, 0)
        section = whole_block(out)
        self.assertIn('0x0784  0x50 -> 0x28',
                      group_body(section, 'PL1/PL2/PL4 (§4.1)'))
        # A 0x0700 dump holds no §4.2 byte and none of the trigger, so both
        # are named as not covered. §4.3's byte is in range and did not move,
        # so it reads unchanged -- a group is answered per group, not per
        # dump.
        self.assertIn('fan table (§4.2): not covered by this pair', section)
        self.assertIn(f'{grade.TRIGGER_GROUP}: not covered by this pair',
                      section)
        self.assertIn('fan-table bracket byte 0x07C6 (§4.3): unchanged across '
                      'the block', section)
        self.assertNotIn('confirmed-working', section)
        self.assertNotIn('confirmed-inert', section)

    def test_dump_pair_reports_a_fan_table_byte_that_moved(self):
        rc, out, _ = run(QUIET, '--dump-pair', *FAN_PAIR)
        self.assertEqual(rc, 0)
        section = whole_block(out)
        body = group_body(section, 'fan table (§4.2)')
        # The table byte is filed under §4.2 and the mailbox tail is not, even
        # though this pair moves both -- which is the whole point of the
        # split, and the only thing it can be checked by.
        self.assertIn('0x0F0A  0x52 -> 0x56', body)
        self.assertEqual(value_lines(body), ['      0x0F0A  0x52 -> 0x56'])
        self.assertEqual(value_lines(group_body(section, grade.TRIGGER_GROUP)),
                         ['      0x0F5D  0xB8 -> 0x6E',
                          '      0x0F5E  0xC4 -> 0x6E',
                          '      0x0F5F  0xD0 -> 0x6E'])
        # §4.2's own named next step, which the section used not to have: the
        # tool and the three inputs it already requires. Read off the printed
        # lines with the wrapping undone, so the check is on the sentence and
        # not on where the 72-column wrap happened to break it.
        flat = " ".join(body.split())
        self.assertIn('replay it with windows/tools/fan_table_replay.py', flat)
        self.assertIn('MQTT capture (--csv --final --mqtt, all three are '
                      'required)', flat)
        self.assertNotIn('confirmed-working', section)
        self.assertNotIn('confirmed-inert', section)

    # The false-positive direction. §3's main arm runs with the vendor service
    # up, which is the one that writes the mailbox, so a difference there must
    # not read as the EC reloading its own table: that is the one result §4.2
    # exists to look for.
    def test_a_mailbox_change_is_not_reported_as_a_fan_table_reload(self):
        rc, out, _ = run(QUIET, '--dump-pair', *MAILBOX_PAIR)
        self.assertEqual(rc, 0)
        section = whole_block(out)
        # §4.2 read the table and it did not change, while the three bytes
        # after it did. The magic and selector go in as they arrive, so the
        # three lines read as the write §6 decodes rather than as table
        # content.
        self.assertIn('fan table (§4.2): unchanged across the block', section)
        trigger = group_body(section, grade.TRIGGER_GROUP)
        self.assertEqual(value_lines(trigger),
                         ['      0x0F5D  0xB8 -> 0xFD',
                          '      0x0F5E  0xC4 -> 0xC9',
                          '      0x0F5F  0xD0 -> 0x02'])
        # And they are in neither of the two places they would still read as
        # a table move: under §4.2, or in the bucket for addresses no watched
        # group claims. The heading names the address range, so this is a
        # statement about the bucketing and not a coincidence of wording.
        self.assertNotRegex(group_body(section, 'fan table (§4.2)'),
                            r'0x0F5[DEF]  0x[0-9A-F]{2} -> 0x[0-9A-F]{2}')
        self.assertNotIn('other addresses that differ', section)
        # The note is what the heading's "see below" points at, and it has to
        # say the annotation and that this is not §4.2's answer. Unwrapped,
        # for the same reason as the next step above.
        flat = " ".join(trigger.split())
        self.assertIn('ec/annotations/manual-fan-ctrl-0751.md §6 decodes at '
                      '0x888D', flat)
        self.assertIn("A change here is not §4.2's answer", flat)
        # The two readings are both named, because a note claiming only one
        # would be its own overclaim: §6 says host-written, and
        # windows/vendor-ec-map.md says the last three GPU duty slots.
        self.assertIn('written by the host to ask the EC to copy a table',
                      flat)
        self.assertIn('the last three GPU duty slots', flat)
        self.assertNotIn('confirmed-working', section)
        self.assertNotIn('confirmed-inert', section)

    # The same split in the windowed reader, which files the group the same
    # way -- `report_dump_pairs` says so as its "no third category"
    # invariant -- and whose closing paragraph used to report only that
    # "at least one of §4.1-§4.3 moved". That would have put a host mailbox
    # poke in the sentence about the EC contradicting the static prediction,
    # in the arm where the service is by definition allowed to be writing it.
    def test_a_mailbox_change_in_a_capture_is_not_a_fan_table_reload(self):
        rc, out, _ = run(MAILBOX_CSV)
        self.assertEqual(rc, 0)
        self.assertIn('0x0F5D  0xB8 -> 0xFD   (+0.4s)', out)
        # The group is named, and the note comes back with its value lines.
        self.assertIn(f'    {grade.TRIGGER_GROUP}:', out)
        # The opening words are unchanged, so a reader who greps for them
        # still finds them; what follows them is the attribution.
        self.assertIn(f'At least one of the §4.1-§4.3 bytes moved after a '
                      f'mark: {grade.TRIGGER_GROUP}.', out)
        self.assertIn('That is the host-written reload mailbox, not a §4.2 '
                      'result', out)
        self.assertIn('reads the selector from 0x0F5F and never from 0x0751',
                      out)
        # The §4.2 sentence is the one about contradicting the prediction, and
        # no table byte moved here, so it must not be the sentence printed.
        self.assertNotIn('contradicts the static prediction', out)
        self.assertNotIn('None of the §4.1-§4.3 bytes moved', out)
        # And a §4.1 move still gets the sentence it always got.
        _, out, _ = run(ACTIVE)
        self.assertIn('contradicts the static prediction', out)
        self.assertIn(f'mark: PL1/PL2/PL4 (§4.1), '
                      f'fan-table bracket byte 0x07C6 (§4.3).', out)
        self.assertNotIn('host-written reload mailbox', out)

    # §6 end to end, over the eight files §6 names and by the command line §6
    # gives. Everything a reader of that command line would take from its
    # output, asserted here, because nothing in the repository had been
    # through the whole of §6 before.
    def test_section6_command_line_over_section6s_file_set(self):
        rc, out, _ = run(*RUN_CAPTURES,
                         '--dump', RUN_BEFORE, '--dump', RUN_AFTER,
                         '--dump-pair', RUN_BEFORE, RUN_AFTER,
                         '--dump-pair', RUN_BEFORE_0F00, RUN_AFTER_0F00,
                         '--wrote', '0xA0')
        self.assertEqual(rc, 0)
        # Three actions, nine MARK rows: each is marked in all three
        # watchers seconds apart, which is what the merge is for.
        self.assertIn('=== 3 window(s), one per mark ===', out)
        self.assertEqual(out.count('no watched byte moved in this window'), 3)
        # §4.4's deciding pair, and it reads ambiguous: the candidate PWM
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
        # The two --dump-pair flags do not disturb that: --dump keeps its own
        # meaning and the readback is still taken from the last of those.
        self.assertIn('2026-01-01-0751-isolation-a0-before-0700.txt: '
                      '0x0751 = 0x10', out)
        self.assertIn('the last dump still holds the written 0xA0', out)
        self.assertIn('that is a readback, not evidence', out)
        self.assertIn('not the call itself', out)
        # And the whole-block read §6's command now also produces.
        self.assertIn('=== whole-block dump pairs (§4.1-§4.3) ===', out)
        self.assertIn('The whole-block dump pairs above were read as a '
                      'second, wider bracket', out)

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
    # but the runbook must not be able to drift back to collecting all four
    # dumps and handing two of them to nothing, either. So the command block
    # is found by what is in it, and has to name every dump §6 lists.
    def test_section6s_command_reads_every_dump_it_lists(self):
        block = concrete(section6_command(RUNBOOK.read_text(encoding="utf-8")))
        for path in (RUN_BEFORE, RUN_AFTER, RUN_BEFORE_0F00, RUN_AFTER_0F00):
            self.assertIn(Path(path).name, block)


if __name__ == '__main__':
    unittest.main()
