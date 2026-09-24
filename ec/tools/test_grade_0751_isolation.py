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
# A three-value day: the same three CSVs §6 names, with all three blocks'
# marks in one set the way §3 takes them, one block per value, and block 2's
# restore mark absent. That is what a mark typed after that watcher had
# exited looks like in a capture -- printed by ec_watch.py, written to
# nothing -- and it is the case §3's per-block check and --block are read
# against: two intact blocks around one void one.
BLOCK_CAPTURES = tuple(
    str(HERE / 'testdata' / '0751-isolation-run-3blocks'
        / f'2026-01-01-0751-isolation-{r}.csv')
    for r in ('0700-07ff', '0f00-0f5f', '0400-045f'))

# The mark-set checks' own fixtures, one directory per case so a failure names
# the case. Three are §6's three captures with one thing wrong with the marks;
# `multi-block/` is the same procedure with nothing wrong, and is the half the
# other three are compared against -- the same 0xA0 block, the same duty
# drift, the same climb, so the only thing that differs between a graded run
# and a refused one is the mark set. The values under test are 0xA0 and 0x10,
# and -- unlike `3blocks/`, whose middle block is void -- every mark is in
# every capture and every capture spells it the same way.
def _set(name):
    return tuple(str(HERE / 'testdata' / f'0751-isolation-run-{name}'
                     / f'2026-01-01-0751-isolation-{r}.csv')
                 for r in ('0700-07ff', '0f00-0f5f', '0400-045f'))


MISSING_MARK = _set('missing-mark')
DISAGREEING = _set('disagreeing-marks')
VOID_BLOCK = _set('void-block')
MULTI_BLOCK = _set('multi-block')
# The same two-value day as `multi-block/`, with one `restore` in no block
# ahead of the first block and one between the two. Every mark is in every
# capture and both blocks are intact, so this set is not about the mark
# checks refusing anything: it is about `--block` selecting a block's own
# windows when a window in no block comes first. The two positions cover
# both directions a count would be wrong in -- the leftover ahead of both
# blocks, and the one between them.
UNPLACED_WINDOW = _set('unplaced-window')
# §6's per-block dumps for the two-value day, and the only ones of the four
# that carry a <value> a reader could confuse: both pairs read the same two
# bytes in the opposite order, so a §4.6 verdict filed under the wrong block
# would read as a perfectly good answer.
MULTI = HERE / 'testdata' / '0751-isolation-run-multi-block'
MULTI_A0_DUMPS = (str(MULTI / '2026-01-01-0751-isolation-a0-before-0700.txt'),
                  str(MULTI / '2026-01-01-0751-isolation-a0-after-0700.txt'))
MULTI_10_DUMPS = (str(MULTI / '2026-01-01-0751-isolation-10-before-0700.txt'),
                  str(MULTI / '2026-01-01-0751-isolation-10-after-0700.txt'))

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


# A window header as the report prints it: the mark's place in the whole
# stream, its timestamp, the label in the repr the header puts it in, and the
# captures it was recorded in.
MARK_HEADER = re.compile(r"^--- mark (\d+)/(\d+): \S+  '(.+?)' \(", re.M)


def marked_windows(out):
    """The (number, label) of every window a report printed.

    Read off the headers rather than asserted as substrings of the labels,
    because §3's labels share their tails -- `wrote 0x0751=0x10` is inside
    `no-op wrote 0x0751=0x10`, and both are in the capture -- so an
    `assertIn` on one of them matches a window in another block. The number
    is kept because `--block` leaves each window where it was in the whole
    mark stream.
    """
    return [(int(n), label) for n, _, label in MARK_HEADER.findall(out)]


def fixture_block_ends():
    """Each block's last mark, as the label and whether it is a restore.

    Taken from the fixture rather than written out here, so a mark edited in
    it fails the tests below instead of leaving them asserting a block
    structure the CSVs no longer have. Read through the same walk main does,
    so a change to how a block is found has to be made here too rather than
    quietly leaving this asserting the old one.
    """
    marks = []
    for path in BLOCK_CAPTURES:
        m, _ = grade.read_capture(path)
        marks += m
    blocks, _ = grade.assign_blocks(grade.coalesce_marks(marks))
    return [(b.windows[-1].label,
             grade.parse_mark(b.windows[-1].label)[0] == 'restore')
            for b in blocks]


def census(out):
    """The mark census section, and nothing after it.

    One spelling of the split: the census is the first section printed and
    four tests each want a different end of it.
    """
    return out.split('=== mark census (§3/§6) ===', 1)[1].split('\n=== ', 1)[0]


def dumps_section(out):
    """The §4.6 section, and nothing after it."""
    return out.split('=== 0x0751 across the dumps (§4.6) ===', 1)[1] \
               .split('=== whole-block dump pairs', 1)[0]


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


def dumps(*paths):
    """`--dump` repeated per file, as §6's command line writes it.

    `--dump` takes one file per flag, so a `--dump a b` pair is a bare
    positional to argparse and not a second dump -- a call that reads like
    the two files is one pair of flags or it is an error.
    """
    return [flag for path in paths for flag in ('--dump', path)]


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
        # No duty or temperature byte moves here either, but the section is
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
        self.assertEqual(out.count('fan duty / temperature bytes'), 2)
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
        # The window starts at the earliest mark, so the duty change that
        # follows the last press is still timed from the first one.
        self.assertIn('0x075B  0x64 -> 0x66   (+2.4s)', out)

    def test_context_section_names_duty_and_temperature_bytes(self):
        _, out, _ = run(*FIXED_LOAD)
        self.assertIn('fan duty / temperature bytes (§4.4/§4.5)', out)
        self.assertIn('fan duty 0x075B/0x075C -- MAIN_FAN_L/R_DUTY', out)
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
        # The four mark-set sets are here as well as the three passing ones:
        # a refusal message is exactly where a status claim would creep in,
        # and the census, the three failure messages and the withheld-window
        # lines are all new text over a new code path.
        for argv in ([QUIET], [ACTIVE], list(FIXED_LOAD), list(MULTI_BLOCK),
                     list(MISSING_MARK), list(DISAGREEING), list(VOID_BLOCK)):
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
        # None of §4.1-§4.3 (four watched groups, counting the reload trigger)
        # and neither §4.4/§4.5 context group is in this dump at all, so all
        # six are named as not covered rather than passing as "unchanged" or
        # dropping out of the section's heading.
        self.assertEqual(section.count('not covered by this pair'), 6)
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
        # §4.4's comparison, and it reads ambiguous: the fan duty moved
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

    # The one input error --dump-pair cannot detect on its own: both paths the
    # same file. Every address is then equal by construction, so "unchanged
    # across the block" is a true statement about nothing -- a bracket that is
    # not a bracket. Flagged loudly, and the pair contributes no whole-block
    # read at all.
    def test_a_dump_pair_of_one_file_with_itself_is_not_a_whole_block(self):
        rc, out, _ = run(*RUN_CAPTURES,
                         '--dump-pair', RUN_BEFORE, RUN_BEFORE)
        self.assertEqual(rc, 0)
        section = out.split('=== whole-block dump pairs (§4.1-§4.3) ===')[1]
        section = section.split('=== what this does and does not settle')[0]
        # Named and flagged, so the operator can see which pair was dropped
        # rather than finding a missing bucket and guessing.
        self.assertIn(f'{RUN_BEFORE} -> {RUN_BEFORE}', section)
        self.assertIn('both sides are the same file', section)
        # No per-bucket output for that pair: not a compared count, and not
        # one "unchanged" line a reader could take for §4.1 or §4.3.
        self.assertNotIn('address(es) compared', section)
        self.assertNotIn('unchanged across the block', section)
        self.assertNotIn('not covered by this pair', section)
        # And the closing summary does not report a read that was not taken.
        self.assertNotIn('The whole-block dump pairs above were read', out)

        # Per pair, not a refusal: the real 0F00 pair in the same run is
        # graded exactly as before. Checked in its own run, because a
        # notIn over this one would trip on the genuine pair.
        rc, out, _ = run(*RUN_CAPTURES,
                         '--dump-pair', RUN_BEFORE, RUN_BEFORE,
                         '--dump-pair', RUN_BEFORE_0F00, RUN_AFTER_0F00)
        self.assertEqual(rc, 0)
        self.assertIn('both sides are the same file', out)
        self.assertIn('96 address(es) compared', out)
        self.assertIn('fan table (§4.2): unchanged across the block', out)
        self.assertIn('The whole-block dump pairs above were read', out)

    # §6's own `rem` says the 0x0700 after-dump has to stay the last --dump,
    # and says why: the 0x0F00 range does not cover 0x0751. Putting those two
    # files there instead is a tidy mistake, and the section used to end after
    # two "not covered by this dump" lines -- indistinguishable in shape from a
    # run where the readback was taken and the answer held.
    def test_readback_is_not_taken_when_the_last_dump_covers_no_0751(self):
        rc, out, _ = run(*RUN_CAPTURES,
                         '--dump', RUN_BEFORE_0F00, '--dump', RUN_AFTER_0F00,
                         '--dump-pair', RUN_BEFORE, RUN_AFTER,
                         '--dump-pair', RUN_BEFORE_0F00, RUN_AFTER_0F00,
                         '--wrote', '0xA0')
        self.assertEqual(rc, 0)
        section = out.split('=== 0x0751 across the dumps (§4.6) ===')[1]
        section = section.split('=== whole-block dump pairs')[0]
        self.assertIn('§4.6 readback was not taken', section)
        # The tool is already holding a pair that covers the address, and says
        # which file of it to pass -- §6's ordering rule, now enforced rather
        # than only written down in a comment the operator has to read right.
        self.assertIn(f'{RUN_BEFORE} -> {RUN_AFTER}', section)
        self.assertIn(f'pass the after file as the last --dump', section)
        self.assertIn(RUN_AFTER, section)
        # No answer is reported for a readback that never happened.
        self.assertNotIn('the last dump still holds the written 0xA0', section)
        self.assertNotIn('the last dump holds', section)

    # The branch past the ordering mistake: nothing in the run covers 0x0751,
    # so there is no pair to name. The notice is a coverage fact and fires on
    # the dumps alone -- no --wrote, no --dump-pair, same line.
    def test_readback_not_taken_when_nothing_here_covers_0751(self):
        rc, out, _ = run(*RUN_CAPTURES,
                         '--dump', RUN_BEFORE_0F00, '--dump', RUN_AFTER_0F00)
        self.assertEqual(rc, 0)
        section = out.split('=== 0x0751 across the dumps (§4.6) ===')[1]
        section = section.split('=== whole-block dump pairs')[0]
        self.assertIn('§4.6 readback was not taken', section)
        self.assertNotIn('a --dump-pair does cover it', section)

    # A pair whose before-dump alone reaches 0x0751 is not named. The readback
    # is taken from a --dump and the after file is the one that can become
    # one, so naming that pair would point at a byte the operator's last
    # --dump cannot hold. Same intersection report_dump_pairs compares under,
    # on a shape no §6 pair has: each of those is one range, both dumps the
    # same length.
    def test_a_pair_whose_before_alone_covers_0751_is_not_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = Path(tmp) / 'before-0700.txt'
            before.write_text('0750: 00 a0 02 03 04 05 06 07\n')
            after = Path(tmp) / 'after-0f00.txt'
            after.write_text('0f00: 00 01 02 03\n')
            rc, out, _ = run(QUIET, '--dump', str(after),
                             '--dump-pair', str(before), str(after))
        self.assertEqual(rc, 0)
        section = out.split('=== 0x0751 across the dumps (§4.6) ===')[1]
        section = section.split('=== whole-block dump pairs')[0]
        # The readback is still reported as not taken; only the "here is the
        # pair to use" clause is withheld, because no pair here can be one.
        self.assertIn('§4.6 readback was not taken', section)
        self.assertNotIn('a --dump-pair does cover it', section)

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

    # §3's per-block integrity check, on the capture shape it exists for. A
    # block whose last mark is not the restore cannot show the byte being put
    # back, and used to be graded exactly like one that could -- which is the
    # "status moving with nothing behind it" shape issue #167 names as not
    # done, one level up: the window report is the same either way, so the
    # difference has to be somewhere else or nowhere.
    def test_a_block_whose_last_mark_is_not_a_restore_is_void(self):
        rc, out, _ = run(*BLOCK_CAPTURES)
        self.assertEqual(rc, 1)
        self.assertEqual(fixture_block_ends(),
                         [('restored 0x0751=0x10', True),
                          ('wrote 0x0751=0x00', False),
                          ('restored 0x0751=0x00', True)])
        self.assertIn('=== 3 block(s), one per no-op control arm (§3) ===', out)
        # Three verdicts, and the void one names the label the block did end
        # on: "void" on its own does not say which block or which mark, and
        # the operator's next move is to go back to the terminals.
        self.assertIn("block 1/3: intact -- last mark 'restored 0x0751=0x10' "
                      "is the restore", out)
        self.assertIn("block 2/3: VOID -- last mark is 'wrote 0x0751=0x00', "
                      "not the restore", out)
        self.assertIn("block 3/3: intact -- last mark 'restored 0x0751=0x00' "
                      "is the restore", out)
        # The two intact blocks say intact in their own right. A check that
        # only speaks when it fails is a check a fold-in reader cannot tell
        # from one that never ran.
        self.assertEqual(out.count(': intact -- last mark'), 2)
        # The note, on the two things that make this check a CSV check rather
        # than a by-eye one: what a void block is short, and why the mark
        # `ec_watch.py` printed at stop may not be in the capture at all.
        section = out.split('=== 3 block(s), one per no-op control arm')[1] \
                   .split('=== 0x0751 across the dumps')[0]
        flat = " ".join(section.split())
        self.assertIn('short the restore mark §3\'s step 5 makes', flat)
        self.assertIn('printed in its `marks:` list and recorded nowhere else',
                      flat)
        self.assertIn('Redo the void block per §3', flat)
        # The other two thirds of the day are still graded, and the void
        # block's marks are still locatable -- every window header prints,
        # numbered where it is in the whole mark stream, so this run reads
        # side by side with the `--block` one. What a void block's windows
        # are not is printed: its last window runs on to the end of the
        # capture because nothing in it ever closed, and issue #169 is the
        # other half of the same hole -- a mark set that cannot support the
        # windows taken over it is not something to print in the usual format
        # and let a fold-in quote.
        self.assertEqual(len(marked_windows(out)), 8)
        self.assertEqual(out.count('block: 0x00 (block 2 of 3) -- NOT GRADED'),
                         2)
        self.assertEqual(out.count('no watched byte moved in this window'), 6)
        # "this block is void" and "this byte is inert" are different
        # sentences, and this section is where they are most likely to be
        # read as one.
        self.assertNotIn('confirmed-working', section)
        self.assertNotIn('confirmed-inert', section)

    # The passing case, over §6's own file set: one block, intact, still 0.
    # The §6 end-to-end test above covers the exit code; this pins the
    # verdict and the sentence that keeps it from being read as a result.
    def test_an_intact_capture_says_so_rather_than_being_silent(self):
        rc, out, _ = run(*RUN_CAPTURES)
        self.assertEqual(rc, 0)
        self.assertIn('=== 1 block(s), one per no-op control arm (§3) ===', out)
        self.assertIn("block 1/1: intact -- last mark 'restored 0x0751=0x10' "
                      "is the restore", out)
        section = out.split('=== 1 block(s), one per no-op control arm')[1] \
                   .split('=== 0x0751 across the dumps')[0]
        flat = " ".join(section.split())
        self.assertIn('a statement about what was captured and not about what '
                      'the EC did', flat)

    # The issue asks for the grader to be run per block and its output
    # attached, and §6's three CSVs are one set for the whole run -- so
    # without --block every invocation prints every block's windows and the
    # three attachments differ only in the dump section. The selector is the
    # value under test rather than a position in the mark stream, because the
    # value is what §6 stamps the dumps with and the only thing a window, a
    # dump and a §4.6 verdict can all be named by.
    def test_block_one_of_a_three_block_capture_is_its_windows_alone(self):
        rc, out, _ = run(*BLOCK_CAPTURES, '--block', '0xA0')
        self.assertEqual(rc, 0)
        self.assertIn('=== block 1 of 3, value under test 0xA0, '
                      '3 window(s) in it ===', out)
        self.assertEqual(marked_windows(out),
                         [(1, 'no-op wrote 0x0751=0x10'),
                          (2, 'wrote 0x0751=0xA0'),
                          (3, 'restored 0x0751=0x10')])
        # Numbered where they are in the whole mark stream, so this run is a
        # subset of the whole-capture one and the two read side by side. And
        # the window that ends the block says the block ended, rather than
        # claiming the capture did: the one false sentence a per-block read
        # could otherwise print.
        self.assertIn('window runs to the end of block 1 of 3', out)
        self.assertNotIn('the end of the capture', out)
        self.assertIn('block 1/3: intact', out)
        # Only this block's verdict. Reporting the other two would put a
        # second block's worth of meaning on an attachment made per block,
        # and a reader could not tell which of them this run was about.
        self.assertIn('the other 2 block(s) were not checked in this run', out)
        self.assertNotIn('block 2/3', out)
        self.assertNotIn('block 3/3', out)
        # The census is printed whole, so the scoping is visible rather than
        # inferred: the two blocks this run did not grade are named, by
        # value, as not selected. It is the only place a per-block run says
        # what it left out, and it has to say so without handing back their
        # verdicts -- which is why it reads `block 2 of 3` where the verdict
        # section reads `block 2/3`.
        self.assertIn('block 2 of 3: value under test 0x00', out)
        self.assertIn('block 3 of 3: value under test 0x10', out)
        self.assertEqual(census(out).count('-- not selected in this run'), 2)

    # The same contract on the void block, which is the case a per-block run
    # exists to be able to say out loud on its own.
    def test_a_void_block_is_graded_on_its_own_and_says_so(self):
        rc, out, _ = run(*BLOCK_CAPTURES, '--block', '0x00')
        self.assertEqual(rc, 1)
        self.assertIn('=== block 2 of 3, value under test 0x00, '
                      '2 window(s) in it ===', out)
        # The marks are still locatable -- the headers and the numbering are
        # the graded run's -- and the bodies are not, because a block short
        # its restore has a last window that never closes and nothing in the
        # capture to close it with. What the withheld windows would have
        # shown is not reported here and is not to be quoted from this run.
        self.assertEqual(marked_windows(out),
                         [(4, 'no-op wrote 0x0751=0xA0'),
                          (5, 'wrote 0x0751=0x00')])
        self.assertEqual(
            out.count('block: 0x00 (block 2 of 3) -- NOT GRADED'), 2)
        self.assertIn("block 2/3: VOID -- last mark is 'wrote 0x0751=0x00', "
                      "not the restore", out)
        self.assertEqual(out.count(': intact -- last mark'), 0)

    def test_the_last_block_of_a_capture_is_graded_on_its_own(self):
        rc, out, _ = run(*BLOCK_CAPTURES, '--block', '10')
        self.assertEqual(rc, 0)
        self.assertIn('=== block 3 of 3, value under test 0x10, '
                      '3 window(s) in it ===', out)
        self.assertEqual(marked_windows(out),
                         [(6, 'no-op wrote 0x0751=0x00'),
                          (7, 'wrote 0x0751=0x10'),
                          (8, 'restored 0x0751=0x00')])
        self.assertIn('block 3/3: intact', out)

    # A block's windows are the ones that belong to it, which is not the same
    # as the ones that sit between where the blocks before it ended and where
    # it ended. `assign_blocks` leaves a window it could not place in the same
    # list, so a `--block` run that took a range of the length the blocks
    # before it add up to would run short by however many of those came
    # first: it would print a window in no block in place of this block's own
    # restore and still call the block `intact`. That is the mis-attribution
    # this tool exists to remove, reached through the scoping path rather than
    # the mark one, so both directions of it are held here -- the leftover
    # ahead of both blocks, and the one between them.
    def test_a_block_is_its_own_windows_over_one_in_no_block(self):
        for value, index, marks in (
                ('0xA0', 1, [(2, 'no-op wrote 0x0751=0x10'),
                             (3, 'wrote 0x0751=0xA0'),
                             (4, 'restored 0x0751=0x10')]),
                ('0x10', 2, [(6, 'no-op wrote 0x0751=0x00'),
                             (7, 'wrote 0x0751=0x10'),
                             (8, 'restored 0x0751=0x00')])):
            with self.subTest(block=value):
                rc, out, _ = run(*UNPLACED_WINDOW, '--block', value)
                self.assertEqual(rc, 0)
                self.assertIn(f'=== block {index} of 2, value under test '
                              f'{value}, 3 window(s) in it ===', out)
                # The block's own three, still numbered where they sit in
                # the whole mark stream. The two 0x99 restores are marks 1
                # and 5: a range that had counted the blocks before this one
                # would have printed one of them here and dropped mark 4 or
                # mark 8 -- this block's restore -- instead.
                self.assertEqual(marked_windows(out), marks)
                # Which is the window the §3 verdict names, so the two read
                # as one run rather than as two unrelated attachments.
                self.assertIn('block %d/2: intact' % index, out)
                self.assertIn('window runs to the end of block', out)
                # The census is printed whole, and it promises of each of
                # these that `--block` cannot select it. A window section
                # that printed one anyway would contradict the line above it
                # in the same run, so the promise is checked against the
                # windows as well as against itself.
                self.assertEqual(census(out).count('`--block` cannot select '
                                                   'it'), 2)

    # A value that is no block's is an input error, not a quiet one. An empty
    # report would be the strongest negative result the procedure can
    # produce, and the last thing a mistyped --block may look like. The
    # message lists the values that are in the capture, because "not a block"
    # on its own sends the operator back to the terminals to work out what
    # was there instead.
    def test_a_block_that_is_not_in_the_capture_is_an_error(self):
        for n in ('0xFF', '01', 'zz'):
            rc, out, err = run(*BLOCK_CAPTURES, '--block', n)
            self.assertEqual(rc, 1)
            if n == 'zz':
                self.assertIn("'zz' is not a value", err)
            else:
                self.assertIn(f'--block {n!r} is not a block in these captures',
                              err)
                self.assertIn('the values under test are 0xA0, 0x00, 0x10',
                              err)
            self.assertNotIn('window(s), one per mark', out)
            self.assertNotIn('no watched byte moved', out)
            self.assertNotIn('block(s), one per no-op control arm', out)

    # `--block` and `--wrote` both name the value under test, so passing two
    # different ones is a wrong command line rather than something to
    # reconcile. A run that graded block 0xA0's windows and took its readback
    # against a write of 0x10 would report the other block's answer for this
    # one, in the same confident format as a real result.
    def test_a_block_that_disagrees_with_wrote_is_an_error(self):
        rc, out, err = run(*BLOCK_CAPTURES, '--block', '0xA0',
                           '--wrote', '0x10')
        self.assertEqual(rc, 1)
        self.assertIn('--block 0xA0 and --wrote 0x10 name different values',
                      err)
        self.assertIn('one of them is a wrong command line', err)
        self.assertNotIn('window(s), one per mark', out)
        self.assertNotIn('no watched byte moved', out)

    # §6 spells the value `a0` in a file name and `0xA0` in a mark label, and
    # §6's own command line now passes the same `<value>` to both flags. Two
    # flags that name the same byte have to read it the same way, or the
    # runbook's command line raises on the value it documents.
    def test_block_and_wrote_take_the_same_spellings_of_a_value(self):
        for value in ('0xA0', 'A0', 'a0', '0xa0'):
            rc, out, _ = run(*BLOCK_CAPTURES, '--block', value,
                             '--wrote', value)
            self.assertEqual(rc, 0, f'--block/--wrote {value!r} was refused')
            self.assertIn('value under test 0xA0', out)
        # And one that is not a value is refused in as many words, rather
        # than reaching int() and raising out of main.
        for flag in ('--block', '--wrote'):
            rc, _, err = run(*BLOCK_CAPTURES, flag, 'zz')
            self.assertEqual(rc, 1)
            self.assertIn(f'{flag} \'zz\' is not a value', err)
            self.assertIn('hex, with or without the 0x', err)


class MarkSetTests(unittest.TestCase):
    """§6's "the marks in all three CSVs must carry the same labels", checked.

    Four cases over four constructed sets, and the four are the same §3 0xA0
    block with the marks changed and nothing else -- same duty drift, same
    climb, same quiet fan table. So what separates a passing run from a
    refused one here is the mark set and not the bytes, which is the only way
    a test of the mark set can say it is the mark set that failed.
    """

    def test_the_census_names_every_capture_s_label_and_role(self):
        rc, out, _ = run(*RUN_CAPTURES)
        self.assertEqual(rc, 0)
        head = census(out)
        # Per capture, every mark with the role the parse gave it and the
        # block it fell in. Without the role column a label's role is
        # something only the tool knows, and without the block column a
        # window list and a dump list still cannot be tied together.
        for capture in ('0700-07ff', '0f00-0f5f', '0400-045f'):
            self.assertIn(f'2026-01-01-0751-isolation-{capture}.csv '
                          f'(3 mark(s)):', head)
        self.assertIn("2026-01-01 12:00:10+01:00  control     0xA0       "
                      "'no-op wrote 0x0751=0x10'", head)
        self.assertIn("2026-01-01 12:00:40+01:00  write       0xA0       "
                      "'wrote 0x0751=0xA0'", head)
        self.assertIn("2026-01-01 12:01:10+01:00  restore     0xA0       "
                      "'restored 0x0751=0x10'", head)
        # Per action, the agreement §6 asks for: nine mark rows over three
        # actions, every one of them in all three captures and spelled the
        # same way in all of them. The passing case is printed as well as the
        # failing one, for the reason the intact-block verdict is: silence
        # about a check that ran is the same shape as one that never did.
        self.assertIn('3 capture(s), 9 mark row(s), 3 action(s) after the '
                      'merge', head)
        self.assertEqual(head.count(', one label each'), 3)
        self.assertIn('block 1 of 1: value under test 0xA0, roles control, '
                      'write, restore', head)
        self.assertNotIn('NOT GRADED', head)

    # The defect issue #169 is about. A mark one console never recorded is
    # not an error to any part of the reader: that console's rows are filed
    # under whichever window their timestamps fall in, and the other two
    # consoles' marks usually cover for it, so nothing in the result ties
    # them to the arm whose mark went missing. On this fixture the control
    # arm's fan-table movement lands before the first mark of the set, so the
    # control window over the other two captures would read "no watched byte
    # moved" -- quiet for want of a mark.
    def test_a_mark_one_capture_never_recorded_stops_the_windows(self):
        rc, out, _ = run(*MISSING_MARK)
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        # Names which capture, which action, and what the consequence is. All
        # three, or the operator is left reading "something is wrong" and
        # guessing which of the eight mark rows to go and look at.
        self.assertIn('recorded in 2 of 3 capture(s), absent from '
                      '2026-01-01-0751-isolation-0f00-0f5f.csv', flat)
        self.assertIn('nothing in the result ties them to the arm whose mark '
                      'is gone', flat)
        self.assertIn('read quiet for want of a mark rather than because '
                      'nothing moved', flat)
        # The census names the two-mark capture as such and the one-mark
        # action as the one that is short, so the two facts meet in one place
        # rather than one being inferred from the other.
        self.assertIn('2026-01-01-0751-isolation-0f00-0f5f.csv (2 mark(s)):',
                      out)
        self.assertIn("'no-op wrote 0x0751=0x10' in 2 of 3 capture(s):", out)
        self.assertIn('-- did not record it', out)
        # And the block's windows are not printed. The headers and the
        # numbering are, so the mark is locatable and this run reads side by
        # side with a graded one; the bodies are not, because they are
        # arithmetic over a mark set that does not say which action they
        # belong to, and printing them in the usual format is the defect.
        self.assertEqual(len(marked_windows(out)), 3)
        self.assertEqual(out.count('block: 0xA0 (block 1 of 1) -- NOT GRADED'),
                         3)
        for line in ('no watched byte moved in this window', 'window delta',
                     'other addresses that moved'):
            self.assertNotIn(line, out)
        # The block is intact and not graded, which are two different facts:
        # the restore is there, and an action before it is missing from a
        # capture. Printed as two, because only the second withholds anything.
        self.assertIn("block 1/1: intact -- last mark 'restored 0x0751=0x10' "
                      "is the restore", out)
        self.assertIn('NOT GRADED, its windows are not printed', out)
        self.assertIn('A block whose mark set does not hold has no windows '
                      'worth printing', flat)
        # And the closing summary says the movement claim covers nothing,
        # rather than reporting a quiet capture off a mark set that never
        # established what the control arm did.
        self.assertIn('No window in this run was graded, so this output says '
                      'nothing about §4.1-§4.3 for it', flat)

    # The other half of the same hole, found one step earlier: two consoles
    # that disagree about what an action was. A mistyped digit in one of three
    # labels is invisible to the merge -- the three labels join into
    # `wrote 0x0751=0xA0 / wrote 0x0751=0x10` and the window opens on that --
    # and invisible to the timestamps, because the write did happen between
    # the two marks. The label is the only thing that can catch it.
    def test_captures_that_disagree_about_an_action_stop_the_windows(self):
        rc, out, _ = run(*DISAGREEING)
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        # Both spellings and every capture, so the reader is not left to work
        # out which of the three is the odd one out.
        self.assertIn("2026-01-01-0751-isolation-0400-045f.csv: "
                      "'wrote 0x0751=0x10'", flat)
        self.assertIn("2026-01-01-0751-isolation-0700-07ff.csv: "
                      "'wrote 0x0751=0xA0'", flat)
        self.assertIn("2026-01-01-0751-isolation-0f00-0f5f.csv: "
                      "'wrote 0x0751=0xA0'", flat)
        self.assertIn('the window it opens is not the action any of them '
                      'recorded', flat)
        # The census prints the joined label the window really opened on, and
        # the window that would have been graded says which action it is not.
        self.assertIn("'wrote 0x0751=0xA0 / wrote 0x0751=0x10'", out)
        self.assertEqual(out.count('block: 0xA0 (block 1 of 1) -- NOT GRADED'),
                         3)
        self.assertNotIn('window delta', out)

    # §3's per-block integrity check, derived from the CSVs rather than read
    # off a terminal, and the one case the 3blocks fixture cannot reach: there
    # the middle block's restore is missing in all three captures, here in
    # every capture at once. Per block *and* per capture, so a capture that
    # recorded only one block would not make every block in the day look
    # complete.
    def test_a_block_that_ends_on_its_write_is_short_of_its_restore(self):
        rc, out, _ = run(*VOID_BLOCK)
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        self.assertIn("block 1/1: VOID -- last mark is 'wrote 0x0751=0xA0', "
                      "not the restore", out)
        # Every capture is named: the check is per capture, and "the block is
        # void" without saying which console's mark is missing is the same
        # hole the check was opened for.
        for capture in ('0700-07ff', '0f00-0f5f', '0400-045f'):
            self.assertIn(f'2026-01-01-0751-isolation-{capture}.csv ends this '
                          f"block on 'wrote 0x0751=0xA0', not the restore",
                          flat)
        self.assertEqual(out.count('block: 0xA0 (block 1 of 1) -- NOT GRADED'),
                         2)
        self.assertNotIn('window delta', out)
        self.assertIn('Redo the void block per §3', flat)

    # Block labelling, on a two-value day with nothing wrong with it: the
    # passing case for everything the three above refuse. Every window says
    # which block it is in, so an unscoped run over §6's one-CSV-set describes
    # the same blocks a per-block invocation does.
    def test_every_window_is_labelled_with_the_block_it_falls_in(self):
        rc, out, _ = run(*MULTI_BLOCK)
        self.assertEqual(rc, 0)
        self.assertIn('=== 6 window(s), one per mark ===', out)
        self.assertEqual(out.count('block: 0xA0 (block 1 of 2)'), 3)
        self.assertEqual(out.count('block: 0x10 (block 2 of 2)'), 3)
        # No block's windows under another's heading, and not by coincidence
        # of ordering either: the labels here share their tails, so the
        # `block:` line is the only thing that tells window 2 from window 5.
        # `marked_windows` is read for the position of each label in the
        # stream, which is what a window is a window of.
        self.assertEqual(
            marked_windows(out),
            [(1, 'no-op wrote 0x0751=0x10'),
             (2, 'wrote 0x0751=0xA0'),
             (3, 'restored 0x0751=0x10'),
             (4, 'no-op wrote 0x0751=0x00'),
             (5, 'wrote 0x0751=0x10'),
             (6, 'restored 0x0751=0x00')])
        # Scoped to either block, the same run prints the same windows under
        # the same block names, so an unscoped run and a per-block attachment
        # agree about which windows are in which block.
        for value, first, last in (('0xA0', 1, 3), ('0x10', 4, 6)):
            _, scoped, _ = run(*MULTI_BLOCK, '--block', value)
            self.assertEqual([n for n, _ in marked_windows(scoped)],
                             list(range(first, last + 1)))
            self.assertEqual(scoped.count(f'block: {value} (block '
                                          f'{first // 3 + 1} of 2)'), 3)
        # And the census names both blocks with their value under test, so a
        # reader of an unscoped run can tell which `--block` to pass.
        self.assertIn('block 1 of 2: value under test 0xA0', out)
        self.assertIn('block 2 of 2: value under test 0x10', out)

    # The issue's headline: a `--dump` pair and a window list have to
    # describe the same block. Both dump pairs here read the same two bytes
    # in the opposite order -- the `0xA0` after-dump holds 0xA0 and the
    # `0x10` after-dump holds 0x10 -- so a verdict filed under the wrong
    # block would be a true sentence about the other block's byte.
    def test_the_readback_is_taken_from_the_dumps_of_the_block_being_graded(self):
        rc, out, _ = run(*MULTI_BLOCK, '--block', '0xA0',
                         *dumps(*MULTI_A0_DUMPS), '--wrote', '0xA0')
        self.assertEqual(rc, 0)
        section = dumps_section(out)
        self.assertIn("block 0xA0, from the <value> in these files' §6 names",
                      section)
        self.assertIn('2026-01-01-0751-isolation-a0-after-0700.txt: '
                      '0x0751 = 0xA0', section)
        self.assertIn('the last dump still holds the written 0xA0', section)
        # Only this block's dumps. The before-dump legitimately holds 0x10 --
        # the mode this block started in -- so the check is on which files
        # were read, not on the value any of them holds.
        self.assertNotIn('isolation-10-', section)

        # The same value under test, the other block's dumps: the section says
        # whose they are and takes no readback from them, rather than
        # reporting the 0xA0 block's byte as this block's answer.
        rc, out, _ = run(*MULTI_BLOCK, '--block', '0x10',
                         *dumps(*MULTI_A0_DUMPS), '--wrote', '0x10')
        self.assertEqual(rc, 0)
        section = dumps_section(out)
        self.assertIn('belongs to block 0xA0, not the block under test '
                      '(0x10) -- not read for §4.6 here', section)
        self.assertIn('no dump was given for block 0x10', section)
        self.assertNotIn('the last dump still holds', section)

        # Both pairs in one unscoped run, each read against its own block. One
        # `--wrote` cannot be the written value of both, so the disagreement
        # is printed and the readback follows the file name.
        rc, out, _ = run(*MULTI_BLOCK, *dumps(*MULTI_A0_DUMPS, *MULTI_10_DUMPS),
                         '--wrote', '0xA0')
        self.assertEqual(rc, 0)
        section = dumps_section(out)
        self.assertEqual(section.count("from the <value> in these files' §6 "
                                       'names'), 2)
        self.assertIn('2026-01-01-0751-isolation-10-after-0700.txt: '
                      '0x0751 = 0x10', section)
        self.assertIn('these dumps are named for block 0x10 but --wrote says '
                      '0xA0', section)
        self.assertEqual(section.count('that is a readback, not evidence'), 2)

    # A label the block walk cannot place is fatal, and the message quotes the
    # three forms §6 fixes rather than describing the problem. The operator
    # cannot fix an unplaceable mark from "this label is malformed"; the three
    # forms are the whole of what has to change. `ec_watch.py` stamps an
    # empty line as `mark N`, which is how this shape arises at the machine
    # (windows/tools/ec_watch.py:119).
    def test_a_mark_that_is_not_one_of_the_three_forms_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'unread.csv'
            p.write_text('ts,addr,old,new\n'
                         '2026-01-01T12:00:10.000+01:00,MARK,,wrote 0x0751=0xA0\n'
                         '2026-01-01T12:00:40.000+01:00,MARK,,no-op wrote '
                         '0x0751=0xA0\n'
                         '2026-01-01T12:01:10.000+01:00,MARK,,mark 3\n')
            rc, out, _ = run(str(p))
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        self.assertIn("'mark 3' is not one of the three forms §6 fixes", flat)
        for form in grade.REQUIRED_LABEL_FORMS:
            self.assertIn(repr(form), flat)
        self.assertIn('a mark this cannot read is a mark no block can be '
                      'attributed to', flat)
        # Named per capture and per mark, and the window it opened carries no
        # body either: a window whose opening mark cannot be placed is a
        # window the tool cannot say what it is a window of. The mark between
        # -- a control arm whose write never came -- is a different case and
        # is graded, under `unplaced`: its rows are real and there is no
        # other arm to mis-file them under.
        self.assertIn('unread.csv at 2026-01-01 12:01:10+01:00', flat)
        self.assertIn('UNREADABLE  unplaced', out)
        self.assertEqual(out.count('block: unplaced'), 2)
        self.assertEqual(out.count('block: unplaced -- NOT GRADED'), 1)
        self.assertIn('window delta', out)

    # The narrowing that keeps the cross-console checks off a single capture,
    # pinned. One capture is the grader's own documented form and the
    # `quiet`/`active` examples are single-CSV, and with one there is no other
    # console for a mark to be missing from and no second spelling to
    # disagree with it -- so "the captures agree" has nothing to be true of,
    # and a run that printed nothing about it would read as a check that
    # passed. The census says so in as many words, and this test fails if that
    # line is ever dropped or the threshold is quietly widened.
    def test_a_single_capture_says_the_cross_console_checks_did_not_run(self):
        for argv in ([QUIET], [ACTIVE]):
            rc, out, _ = run(*argv)
            self.assertEqual(rc, 0)
            self.assertIn('one capture: the cross-console checks did not run',
                          out)
            self.assertIn('a mark cannot be missing from another console that '
                          'is not there', out)
            self.assertIn('The void check and the label parse did run', out)
        # Two captures is the threshold, and the line is gone at it: the
        # fixed-load pair is §3's two-watcher form with a control arm and
        # agreeing labels, so there is a check here to run and it holds.
        rc, out, _ = run(*FIXED_LOAD)
        self.assertEqual(rc, 0)
        self.assertNotIn('the cross-console checks did not run', out)
        self.assertNotIn('one capture:', out)


if __name__ == '__main__':
    unittest.main()
