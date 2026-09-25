#!/usr/bin/env python3
"""Offline checks against the constructed captures in testdata/; no hardware
and no real capture is involved."""
import contextlib
import importlib.util
import io
import os
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
# `unplaced-window/` with the first of its two block-less restores relabelled
# to a form §6 does not fix, in all three captures. Nothing else differs, so
# the label is the whole variable between the two strays: the 12:04 one still
# parses and is graded as `block: unplaced`, the 12:00 one is refused. It
# withholds 1 window of 8 and grades 7, against `3blocks/`'s 2 withheld of 8
# -- the other reason a run can be partly graded, reached by no other
# committed fixture, and the one whose withheld window is in no block at all.
UNREAD_WINDOW = _set('unread-window')
# `3blocks/` with one `0x0784` row added inside block 1's write window, which
# is the address and the step `0751-isolation-example-active.csv` records, so
# the two agree. The marks are untouched, so the block structure and the void
# block 2 are that set verbatim: the same 2 withheld of 8, and now one of the
# 6 that were graded moved. It is here because that combination had no
# committed fixture at all -- the three refused sets withhold every window and
# the two clean ones move nothing -- so the `moved_groups` branch was reached
# only over runs with no withheld window anywhere in the chain.
BLOCK_CAPTURES_MOVED = _set('3blocks-moved')
# §6's per-block dumps for the two-value day, and the only ones of the four
# that carry a <value> a reader could confuse: both pairs read the same two
# bytes in the opposite order, so a §4.6 verdict filed under the wrong block
# would read as a perfectly good answer.
MULTI = HERE / 'testdata' / '0751-isolation-run-multi-block'
MULTI_A0_DUMPS = (str(MULTI / '2026-01-01-0751-isolation-a0-before-0700.txt'),
                  str(MULTI / '2026-01-01-0751-isolation-a0-after-0700.txt'))
MULTI_10_DUMPS = (str(MULTI / '2026-01-01-0751-isolation-10-before-0700.txt'),
                  str(MULTI / '2026-01-01-0751-isolation-10-after-0700.txt'))

# The void one-block set with dumps of its own: `void-block/` byte for byte,
# and `multi-block/`'s `a0` pair under that file's own name so the `<value>`
# in it still says 0xA0. It is the case the two clean sets cannot reach --
# `run/` and `multi-block/` both grade every window, so neither has a
# `--dump` read for a block whose windows the run refused, which is what
# issue #499 is about. Copied rather than composed from the two directories
# in the test, for the reason the other derived sets here are: a failure
# names its own case, and an edit to `multi-block/`'s dumps cannot move this
# set's block under it.
VOID_BLOCK_WITH_DUMPS = _set('void-block-with-dumps')
VOID_DUMPS = HERE / 'testdata' / '0751-isolation-run-void-block-with-dumps'
VOID_A0_DUMPS = (
    str(VOID_DUMPS / '2026-01-01-0751-isolation-a0-before-0700.txt'),
    str(VOID_DUMPS / '2026-01-01-0751-isolation-a0-after-0700.txt'))

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


def as_main_reads(paths):
    """The captures, windows and blocks `main` builds from a list of paths.

    The same walk `main` does, from `read_capture` through `build_windows` to
    `assign_blocks`, so a change to how a capture is read or a block found has
    to be made here too rather than quietly leaving a test asserting the old
    one. `main` refuses a repeated capture before this point, so the list the
    callers hold through `run()` is always the distinct one -- the tests that
    build the list themselves are the ones that reach the readers directly.
    """
    captures, marks, changes = [], [], []
    for path in paths:
        m, c = grade.read_capture(path)
        captures.append((path, m))
        marks += m
        changes += c
    windows = grade.build_windows(marks, changes)
    blocks, unplaced = grade.assign_blocks(windows)
    return captures, windows, blocks, unplaced


def fixture_block_ends():
    """Each block's last mark, as the label and whether it is a restore.

    Taken from the fixture rather than written out here, so a mark edited in
    it fails the tests below instead of leaving them asserting a block
    structure the CSVs no longer have. Read through the same walk main does,
    so a change to how a block is found has to be made here too rather than
    quietly leaving this asserting the old one.
    """
    _, _, blocks, _ = as_main_reads(BLOCK_CAPTURES)
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

    # The same blind spot the pair above has, on the flag that decides how many
    # consoles the cross-console checks run over. One capture listed twice
    # satisfies every one of those checks with a file agreeing with itself, and
    # the one-capture notice that exists to say the checks did not run is
    # suppressed -- so a fat-fingered duplicate reads as a passing
    # cross-console comparison. Refused, before anything is read, and named.
    def test_a_capture_given_twice_is_refused(self):
        rc, out, err = run(*RUN_CAPTURES, RUN_CAPTURES[0])
        self.assertEqual(rc, 1)
        self.assertIn(f'{RUN_CAPTURES[0]!r} is given twice', err)
        self.assertIn('A capture given twice is one console and not two', err)
        # Refused before a single mark is read, so there is no report to be
        # half-right: no per-file mark counts, no census, no windows.
        for absent in ('mark(s),', '=== mark census', 'capture(s),',
                       ', one label each', 'window(s), one per mark',
                       'no watched byte moved'):
            self.assertNotIn(absent, out)
        # One file is one console however many times it is listed, and that
        # holds for the single-capture form as much as for §6's three.
        rc, out, err = run(QUIET, QUIET)
        self.assertEqual(rc, 1)
        self.assertIn('is given twice', err)
        self.assertNotIn('one capture:', out)

        # Identity is by resolved path, not by the string: `./x.csv` and
        # `x.csv` are one file, and so is a symlink to it. Copied into a
        # temporary directory rather than spelled inside the fixture tree,
        # which §6's file list is held equal to and must not gain a name.
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / Path(QUIET).name
            copy.write_bytes(Path(QUIET).read_bytes())
            dotted = os.path.join(tmp, '.', copy.name)
            rc, out, err = run(str(copy), dotted)
            self.assertEqual(rc, 1)
            # Both spellings, and the one file they are, so the operator can
            # see which of the two their command line dropped.
            self.assertIn(f'{dotted!r} and {str(copy)!r}', err)
            self.assertIn(os.path.realpath(copy), err)
            self.assertNotIn('=== mark census', out)
            os.symlink(copy, Path(tmp) / 'linked.csv')
            rc, out, err = run(str(copy), str(Path(tmp) / 'linked.csv'))
            self.assertEqual(rc, 1)
            self.assertIn('linked.csv', err)
            self.assertIn(os.path.realpath(copy), err)
            self.assertNotIn('=== mark census', out)

        # And the same command line without the repeat is the graded run it
        # would have been: the refusal is pinned to the duplicate, not to this
        # invocation.
        rc, out, _ = run(*RUN_CAPTURES)
        self.assertEqual(rc, 0)
        self.assertIn('3 capture(s)', out)
        self.assertNotIn('one capture:', out)

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

    # The clean case, pinned. Nothing in the repository asserted this before:
    # the three `assertIn('None of the §4.1-§4.3 bytes moved', out)` lines
    # elsewhere are on the opening words, and over the committed tree the
    # phrase 'consistent with the static prediction' was in the tool and
    # nowhere else -- so the strongest claim this tool makes could be dropped
    # or reworded off every clean run and no test would fail. It is the third
    # case, and the two in MarkSetTests cover the halves that were broken.
    def test_a_clean_multi_block_run_still_gets_the_prediction_sentence(self):
        rc, out, _ = run(*MULTI_BLOCK)
        self.assertEqual(rc, 0)
        self.assertIn('None of the §4.1-§4.3 bytes moved in any window: '
                      'consistent with the static prediction', out)
        # §5's caveat is the other half of what makes this a scoped claim
        # rather than a verdict: a byte that held still inside the window may
        # still move at the next suspend, AC transition or EC reset. Dropped
        # here it would leave the sentence unqualified in the other direction.
        self.assertIn("for this capture's window only (§5: a byte that does "
                      'not move inside the window may still move at the next '
                      'suspend, AC transition or EC reset)', out)
        # And a run with nothing withheld reaches neither of the two partly
        # shapes: the banner is a fact about this input that is not there.
        self.assertNotIn('were not graded', out)
        self.assertNotIn('No window in this run was graded', out)

    # The same sentence, on a run that read one value of a day. §6's own
    # command line passes `--block` and asks for it once per value, and a
    # clean block is graded whole -- `withheld == 0`, `graded == len(shown)` --
    # so none of the branches above fired and the whole-capture sentence was
    # printed over 3 of the day's 8 windows, on a run whose header, integrity
    # check and closing window had already said it read one block of three.
    def test_a_clean_per_block_run_does_not_claim_the_whole_capture(self):
        rc, out, _ = run(*BLOCK_CAPTURES, '--block', '0xA0')
        self.assertEqual(rc, 0)
        # The movement fact is still reported, and over what carries it: the
        # block, the value under test, and the count the run graded. Dropping
        # the number would make the claim unreadable rather than safe.
        self.assertIn('None of the §4.1-§4.3 bytes moved in any of the 3 '
                      'window(s) in block 1 of 3, value under test 0xA0', out)
        # And the capture-level comparison is declined, by the withheld
        # branch's own words and for its reason: the prediction is about the
        # whole capture, and the same CSVs read unscoped is what would make it.
        self.assertIn('The static prediction is a claim about the whole '
                      'capture, and this output does not make it over one '
                      'block of them', out)
        self.assertIn('the same CSVs graded without --block is what would',
                      out)
        self.assertNotIn('consistent with the static prediction', out)
        # Neither of the other two shapes, either. This run withheld nothing,
        # and reaching for the banner would report a block that graded clean
        # as one this tool could not read.
        self.assertNotIn('were not graded', out)
        self.assertNotIn('No window in this run was graded', out)
        # The blocks it did not read are still named as unchecked by the
        # integrity check above the summary, so the sentence and the section
        # it closes are saying one thing about the denominator.
        self.assertIn('the other 2 block(s) were not checked in this run', out)

    # The same scoping one branch up, where the claim is the stronger of the
    # two rather than the weaker: a `--block` run over `3blocks-moved/` moved a
    # PL inside its own write window and withheld nothing, so the movement line
    # and the `That contradicts ...` attribution under it printed with nothing
    # between them, and the attribution read as a statement about the day.
    def test_a_per_block_movement_is_scoped_before_the_attribution(self):
        rc, out, _ = run(*BLOCK_CAPTURES_MOVED, '--block', '0xA0')
        self.assertEqual(rc, 0)
        self.assertIn('At least one of the §4.1-§4.3 bytes moved after a '
                      'mark: PL1/PL2/PL4 (§4.1).', out)
        # The scope sits where the withheld branch puts it -- between the
        # movement and the attribution -- and declines the same thing: the
        # blocks this run did not read, and what they would have shown.
        self.assertIn('That is block 1 of 3, value under test 0xA0, over its '
                      '3 window(s). The other 2 block(s) were not checked in '
                      'this run', out)
        self.assertIn('what they would have shown is not reported here', out)
        # The attribution itself is unchanged, and scoping is not retracting:
        # a PL that moved inside a window is still the more interesting
        # outcome, and this run really did see it. What is gone is the
        # unqualified reading, because it now has the block in front of it.
        self.assertIn('That contradicts the static prediction', out)
        self.assertNotIn('host-written reload mailbox', out)
        self.assertNotIn('were not graded', out)
        self.assertNotIn('No window in this run was graded', out)

    # What the `len(blocks) > 1` in the guard above is for, and the only
    # thing that holds it. §6's own set is a one-block capture, so a
    # `--block` run over it selects a block that *is* the whole capture: its
    # windows are the whole mark stream, and the whole-capture comparison is
    # exactly the claim that run can support. Scoping it there would decline a
    # comparison that is true, which trades one overclaim for another. Green
    # before this change and green after it -- it pins the guard rather than
    # the fix, and fails the day someone drops the second clause.
    def test_a_block_run_over_a_one_block_capture_still_compares(self):
        rc, out, _ = run(*RUN_CAPTURES, '--block', '0xA0')
        self.assertEqual(rc, 0)
        self.assertIn('None of the §4.1-§4.3 bytes moved in any window: '
                      'consistent with the static prediction', out)
        self.assertIn("for this capture's window only", out)
        # And not the per-block sentence, which would be declining over a
        # set of blocks that is empty.
        self.assertNotIn('is a claim about the whole capture', out)


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

    # The other way a run can end up with little to say, and the one the
    # line above does not cover: some of its windows graded and some not. The
    # withheld banner is right in that case, but the sentence under it is a
    # claim about the capture, and over 6 of its 8 windows it is a claim about
    # 6 wearing the whole capture's wording. Nothing moves here, so the
    # sentence under test is the one that says so.
    def test_a_partly_withheld_run_says_what_its_graded_windows_show(self):
        rc, out, _ = run(*BLOCK_CAPTURES)
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        # The banner is unchanged and still carries its own count.
        self.assertIn('2 of the 8 window(s) above were not graded', flat)
        # And the line under it now names the same split from the other side,
        # with both numbers: 6 graded is the subset the movement fact is a
        # fact about, 2 withheld is what it says nothing about. Written out
        # rather than derived, so a change in either count fails here.
        self.assertIn('None of the §4.1-§4.3 bytes moved in any of the 6 '
                      'window(s) that were graded', flat)
        self.assertIn('the 2 window(s) withheld above are not part of it', flat)
        # The comparison to the prediction is not made over a run the report
        # read part of. This is the sentence the issue is about: it used to be
        # printed here, unqualified, under the banner that says two of these
        # windows were never looked at.
        self.assertNotIn('consistent with the static prediction', out)
        # Nor is this the all-withheld line. Three cases now, and the partial
        # one may not reach for either of the other two's wording.
        self.assertNotIn('No window in this run was graded', out)
        # §7's call is named as out of reach rather than left to be inferred
        # from the banner: a window this run refused to read is one it cannot
        # speak for, so this is not the three-value read `confirmed-inert`
        # needs, and the paragraph below already says so. Named as a window
        # and not as a block, because the other withholding path has no block
        # to name -- see the `unreads` test below.
        self.assertIn('`confirmed-inert` needs all three values, and a window '
                      'this report refused to read is one this run cannot '
                      'speak for', flat)

    # The same split reached the other way, and the reason the clause above is
    # worded about a window rather than a block. A window is withheld either
    # because the block it falls in has a mark set that does not hold, or
    # because its own label is a form §6 does not fix -- and the second path's
    # window is in *no* block, which this run's own census says in the same
    # breath ("a mark this cannot read is a mark no block can be attributed
    # to"). So a closing sentence about a block this report refused to read
    # is a §7 fact the run denies, and it is the sentence the whole branch is
    # for. Withheld 1 of 8 here against the 2 of 8 on the mark-set path, so the
    # counts are the fixture's rather than shared.
    def test_a_withheld_window_in_no_block_claims_no_block_was_refused(self):
        rc, out, _ = run(*UNREAD_WINDOW)
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        # The same split, from the label rather than the mark set: 1 withheld,
        # 7 graded, and the refusal to compare with the prediction is
        # unchanged. This branch is reached either way.
        self.assertIn('1 of the 8 window(s) above were not graded', flat)
        self.assertIn('None of the §4.1-§4.3 bytes moved in any of the 7 '
                      'window(s) that were graded', flat)
        self.assertIn('the 1 window(s) withheld above are not part of it', flat)
        self.assertNotIn('consistent with the static prediction', out)
        # What is withheld, and the reason, are both named at the window: the
        # header says which block it is in, and here that is `unplaced`.
        self.assertIn('block: unplaced -- NOT GRADED', out)
        self.assertIn('a mark this cannot read is a mark no block can be '
                      'attributed to', flat)
        # The two strays differ in nothing but the label, and the output
        # treats them differently: the 12:04 one parses, so it is graded
        # under the same `unplaced` header without the refusal.
        self.assertEqual(out.count('block: unplaced -- NOT GRADED'), 1)
        self.assertEqual(out.count('block: unplaced'), 2)
        # And the clause the issue is about, which now holds on both paths
        # because it names neither: the run cannot speak for the window it
        # refused, and it does not claim a block was refused, because on this
        # path none was.
        self.assertIn('`confirmed-inert` needs all three values, and a window '
                      'this report refused to read is one this run cannot '
                      'speak for', flat)
        self.assertIn('whether it sits in a block of its own is not something '
                      'this output can say', flat)
        self.assertNotIn('a block this report refused to read', out)

    # The same split with something having moved, which no committed fixture
    # reached before this one: the sets above withhold every window, and the
    # clean ones move nothing. So the `moved_groups` branch was printed over
    # a partly-graded run with no withheld window anywhere in the chain, and
    # the attribution underneath it read as covering the whole run.
    def test_a_movement_in_the_graded_windows_of_a_partly_withheld_run_is_scoped(
            self):
        rc, out, _ = run(*BLOCK_CAPTURES_MOVED)
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        # The movement is named exactly as a clean run names it: 0x0784 steps
        # inside block 1's write window and nothing else in the day moves.
        self.assertIn('At least one of the §4.1-§4.3 bytes moved after a '
                      'mark: PL1/PL2/PL4 (§4.1).', out)
        # And it is scoped before the attribution, not by the banner above it:
        # the graded count, the withheld count, and the same refusal to report
        # what the withheld windows would have shown.
        self.assertIn('That is the 6 window(s) that were graded. The 2 '
                      'window(s) withheld above are not part of it', flat)
        self.assertIn('what they would have shown is not reported here', flat)
        # §5's attribution is still the sentence printed -- this is a PL move
        # and not a mailbox poke -- and it now reads as a claim about those 6
        # rather than about the run of 8.
        self.assertIn('That contradicts the static prediction', out)
        self.assertNotIn('host-written reload mailbox', out)
        # Scoping a movement is not the same as declining to report it. The
        # all-withheld line would be the wrong thing to reach for here: 6
        # windows were graded, and one of them moved.
        self.assertNotIn('No window in this run was graded', out)

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

    # The same attribution, one section over. A whole-block bracket is wider
    # than a window and answers the same question, so a pair filed under the
    # wrong block is a result about the wrong bytes rather than a redundant
    # reading -- and the heading is unchanged either way, so the group line
    # above the bracket is the whole of what says whose it is.
    def test_a_dump_pair_is_read_from_the_block_being_graded(self):
        rc, out, _ = run(*MULTI_BLOCK, '--block', '0xA0', '--wrote', '0xA0',
                         '--dump-pair', *MULTI_A0_DUMPS)
        self.assertEqual(rc, 0)
        section = whole_block(out)
        self.assertIn("block 0xA0, from the <value> in these files' §6 names",
                      section)
        self.assertIn('16 address(es) compared', section)
        # 0x0751 is the one address the two pages of this pair disagree on,
        # and it lands in the "other" bucket as an address: the section says
        # which addresses differ, not what they hold. The values are in the
        # §4.6 readback, which is a different section about a different
        # question.
        self.assertIn('other addresses that differ (1), not graded here',
                      section)
        self.assertIn('0x0751', section)
        # And the closing summary reports the read, because one was taken.
        self.assertIn('The whole-block dump pairs above were read', out)

        # The other block's pair, under this block. The pair is named rather
        # than dropped, the refusal says whose it is, and the whole-block
        # read for the block under test is reported as not taken -- the §4.6
        # section's own wording for the same mistake.
        rc, out, _ = run(*MULTI_BLOCK, '--block', '0x10', '--wrote', '0x10',
                         '--dump-pair', *MULTI_A0_DUMPS)
        self.assertEqual(rc, 0)
        section = whole_block(out)
        self.assertIn('belongs to block 0xA0, not the block under test '
                      '(0x10) -- not read for §4.1-§4.3 here', section)
        self.assertIn('no --dump-pair was given for block 0x10', section)
        # Nothing under that heading is compared, so no count is printed and
        # no bucket is there to read as a result. Asserted on the absence
        # rather than on a value: the two fixtures' brackets are identical
        # apart from which block filed them, which is the next test.
        self.assertNotIn('address(es) compared', section)
        self.assertNotIn('other addresses that differ', section)
        # And the closing summary does not claim a whole-block read for a
        # run that took none.
        self.assertNotIn('The whole-block dump pairs above were read', out)

    # Why the refusal rather than a corrected label: the two pairs read the
    # same two bytes in the opposite order, so their brackets come out
    # byte-identical. There is no difference in a mis-filed bracket's body for
    # a reader to notice -- the group line above it is the whole of the
    # attribution, which is why the scoping case above asserts on the label
    # and on what is absent rather than on a value.
    def test_both_blocks_pairs_are_grouped_in_one_unscoped_run(self):
        rc, out, _ = run(*MULTI_BLOCK,
                         '--dump-pair', *MULTI_A0_DUMPS,
                         '--dump-pair', *MULTI_10_DUMPS)
        self.assertEqual(rc, 0)
        section = whole_block(out).split("\n  Every `unchanged` above", 1)[0]
        # One group per block, in the order the pairs were given.
        self.assertEqual(section.count("from the <value> in these files' §6 "
                                       'names'), 2)
        self.assertLess(section.index('block 0xA0'), section.index('block 0x10'))
        # Both read, each as its own bracket.
        self.assertEqual(section.count('16 address(es) compared'), 2)
        self.assertEqual(section.count('other addresses that differ (1)'), 2)
        # And the two bodies are the same reading, bar the <value> in the two
        # file names -- asserted here so the property the refusal rests on is
        # pinned rather than assumed.
        bodies = re.split(r'^  block 0x[0-9A-F]{2}, .*\n', section, flags=re.M)
        self.assertEqual(len(bodies), 3)
        self.assertEqual(bodies[1].replace('-a0-', '-<value>-'),
                         bodies[2].replace('-10-', '-<value>-'))

    # The one input error a pair can carry that its own flags cannot see: two
    # file names naming two different blocks. A pair is one block's before and
    # after, so there is no whole-block read to take from it, and picking
    # either file's block would file a bracket over the wrong bytes. Named,
    # not compared, and not fatal -- the same handling the same-file-twice
    # pair gets, because the window report and the §4.6 readback the operator
    # also needs still get printed.
    def test_a_dump_pair_whose_names_disagree_is_not_read(self):
        rc, out, _ = run(*MULTI_BLOCK, '--dump-pair', MULTI_A0_DUMPS[0],
                         MULTI_10_DUMPS[1])
        self.assertEqual(rc, 0)
        section = whole_block(out)
        self.assertIn('the two file names name different blocks', section)
        self.assertIn('the before side names block 0xA0 and the after side '
                      '0x10', section)
        # Named rather than dropped, so the operator can see which pair was
        # not read instead of finding a missing bracket and guessing.
        self.assertIn(f'{MULTI_A0_DUMPS[0]} -> {MULTI_10_DUMPS[1]}', section)
        # No whole-block read for it, and none claimed in the summary.
        self.assertNotIn('16 address(es) compared', section)
        self.assertNotIn('The whole-block dump pairs above were read', out)
        # The rest of the run is whole: six windows, both blocks intact.
        self.assertIn('=== 6 window(s), one per mark ===', out)
        self.assertEqual(len(marked_windows(out)), 6)
        self.assertEqual(out.count('-- NOT GRADED'), 0)

    # One name and a silent other side is that block's: the name is the more
    # specific of the two statements, which is the reading `report_readback`
    # already gives a name against `--wrote`. The group line says which of the
    # two it was, because "these files' §6 names" would be false for the half
    # that carries none.
    def test_a_dump_pair_named_by_one_of_its_two_files_is_that_blocks(self):
        rc, out, _ = run(*MULTI_BLOCK, '--dump-pair', MULTI_A0_DUMPS[0],
                         PL2_PAIR[1])
        self.assertEqual(rc, 0)
        section = whole_block(out)
        self.assertIn('block 0xA0, from the <value> in one of these two file '
                      'names; the other carries none', section)
        # Read, and read under the block the one name gives it -- the
        # unnamed file is not re-filed under a flag it has no name for.
        self.assertIn('16 address(es) compared', section)
        self.assertNotIn('belongs to block', section)
        # The same pair under the other block, and the one name is enough to
        # keep it out of it: the fallback is only for a pair that names
        # nothing at all.
        rc, out, _ = run(*MULTI_BLOCK, '--block', '0x10', '--wrote', '0x10',
                         '--dump-pair', MULTI_A0_DUMPS[0], PL2_PAIR[1])
        self.assertEqual(rc, 0)
        section = whole_block(out)
        self.assertIn('belongs to block 0xA0, not the block under test '
                      '(0x10) -- not read for §4.1-§4.3 here', section)
        self.assertNotIn('address(es) compared', section)

    # A pair whose two file names carry no `<value>` at all. §6 stamps every
    # dump, so this is a hand-written command line rather than the procedure's
    # own -- which is what the fallback is for, and the group line says the
    # flag is what filed it, so a bracket read under a block no file claimed
    # is not read as one the files named.
    def test_a_dump_pair_that_names_no_block_falls_back_to_the_flag(self):
        rc, out, _ = run(*MULTI_BLOCK, '--block', '0xA0', '--wrote', '0xA0',
                         '--dump-pair', *PL2_PAIR)
        self.assertEqual(rc, 0)
        section = whole_block(out)
        self.assertIn('block 0xA0, from --block/--wrote; these files carry no '
                      '<value> of their own', section)
        self.assertIn('256 address(es) compared', section)
        # The same two files under the other block read as that block's,
        # which is the whole of what a flag-entered value is worth.
        rc, out, _ = run(*MULTI_BLOCK, '--block', '0x10', '--wrote', '0x10',
                         '--dump-pair', *PL2_PAIR)
        self.assertEqual(rc, 0)
        section = whole_block(out)
        self.assertIn('block 0x10, from --block/--wrote; these files carry no '
                      '<value> of their own', section)
        self.assertIn('256 address(es) compared', section)
        # And with no flag there is nothing to fall back to, which the §4.6
        # section already says for a dump.
        rc, out, _ = run(*MULTI_BLOCK, '--dump-pair', *PL2_PAIR)
        self.assertEqual(rc, 0)
        section = whole_block(out)
        self.assertIn('no block named: these files carry no §6 <value> and '
                      'neither --block nor --wrote was given', section)
        self.assertIn('256 address(es) compared', section)

    # Issue #499: the block section knew the block was void and the two file
    # sections were not told, so a §4.6 readback and a whole-block bracket
    # were read and printed for a block whose windows the run had already
    # refused -- in §6's own per-block command form, which is the form
    # #380's run produces. The read itself stays: a void block says the
    # capture is short a mark, not that these two files agree or disagree
    # about anything. What changes is that the group line now carries the
    # verdict, so neither can read as a result for a block the run refused.
    def test_a_dump_pair_for_a_void_block_carries_the_blocks_verdict(self):
        rc, out, _ = run(*VOID_BLOCK_WITH_DUMPS, '--block', '0xA0',
                         '--wrote', '0xA0', '--dump-pair', *VOID_A0_DUMPS)
        # Still 1, for the reason it already was: the block is void.
        self.assertEqual(rc, 1)
        section = whole_block(out)
        line = [l for l in section.splitlines()
                if l.startswith("  block 0xA0, from the <value>")][0]
        # Which block, and what this run did with it -- on the one line that
        # is the whole of the attribution, since the bracket body below
        # cannot show either.
        self.assertIn('block 0xA0', line)
        self.assertIn('VOID', line)
        self.assertIn('its windows were withheld above', line)
        # The bracket is still read and still says what it says. 0x0751 is
        # the one address this pair's two pages disagree on, and it lands in
        # the "other" bucket as an address -- the section names which
        # addresses differ, not what they hold.
        self.assertIn('16 address(es) compared', section)
        self.assertIn('other addresses that differ (1), not graded here',
                      section)
        self.assertIn('0x0751', section)
        # And it is otherwise byte-identical to the same read over the same
        # two files on the two-value day, which is what "the marker is the
        # only change" has to mean -- asserted by comparing the two bodies
        # rather than by picking lines out of one of them. The group line
        # is above both and is the only thing that differs.
        _, intact, _ = run(*MULTI_BLOCK, '--block', '0xA0', '--wrote', '0xA0',
                           '--dump-pair', *MULTI_A0_DUMPS)
        bodies = [re.split(r'^  block 0x[0-9A-F]{2}, .*\n', s, flags=re.M)[1]
                  for s in (section, whole_block(intact))]
        self.assertEqual(bodies[0].replace('void-block-with-dumps', '<set>'),
                         bodies[1].replace('multi-block', '<set>'))

    # The §4.6 half of the same judgement, pinned on its own because it is the
    # half a later change would most easily get wrong in either direction.
    # "The last dump still holds the written 0xA0" is a claim about two files
    # on disk and is true whatever the CSV mark set did, so withdrawing it
    # would throw away a fact the operator can use. What must not survive is
    # the unmarked version: the sentence alone sits under a group line that
    # names no verdict, which is exactly what it read as a result before.
    def test_the_readback_for_a_void_block_is_still_taken_and_says_so(self):
        rc, out, _ = run(*VOID_BLOCK_WITH_DUMPS, '--block', '0xA0',
                         '--wrote', '0xA0', *dumps(*VOID_A0_DUMPS))
        self.assertEqual(rc, 1)
        section = dumps_section(out)
        # Taken, and unchanged in what it says.
        self.assertIn('the last dump still holds the written 0xA0', section)
        self.assertIn('that is a readback, not evidence', section)
        self.assertIn('2026-01-01-0751-isolation-a0-after-0700.txt: '
                      '0x0751 = 0xA0', section)
        # And scoped: the group line carries the verdict, and the sentence
        # below says what kind of read it is, naming the block whose windows
        # are not being read.
        self.assertIn("block 0xA0, from the <value> in these files' §6 names "
                      "-- VOID, its windows were withheld above", section)
        self.assertIn("That is a read of these files and not of block 0xA0's "
                      "windows", section)
        self.assertIn('it says nothing about §4.1-§4.3 for that block',
                      section)
        # Not a register verdict, and not a claim the block was quiet.
        self.assertNotIn('confirmed-', section)
        self.assertNotIn('nothing happened', section)

    # The closing sentence is the third half, and the only one that could read
    # as a counterweight: it sits directly under "No window in this run was
    # graded, so this output says nothing about §4.1-§4.3 for it", and before
    # the fix it answered that with a flat claim that the pairs were read as
    # a bracket on the same bytes. The pair *was* compared, so the count and
    # the sentence both stand; what the withheld block adds is the scope.
    def test_the_closing_summary_does_not_claim_a_whole_block_read_for_a_refused_block(
            self):
        rc, out, _ = run(*VOID_BLOCK_WITH_DUMPS, '--block', '0xA0',
                         '--wrote', '0xA0', '--dump-pair', *VOID_A0_DUMPS)
        self.assertEqual(rc, 1)
        # The read is still reported, because one was taken.
        self.assertIn('The whole-block dump pairs above were read', out)
        # And scoped to the block whose windows were refused. The companion
        # is the second sentence, so a reader who reads only the first --
        # which is the case the withheld banner above makes -- still meets
        # it a line later rather than nowhere.
        self.assertIn('Those pairs are a read of two dump files, and not a '
                      'statement about §4.1-§4.3 for block 0xA0', out)
        self.assertIn('whose windows this run refused to print above', out)
        # And the run really did grade nothing, so the sentence it scopes is
        # not contradicting anything.
        self.assertIn('No window in this run was graded', out)

        # The negative that keeps it from being a sentence bolted onto every
        # run: over the two-value day every window is graded, both blocks are
        # intact, and there is nothing to scope.
        rc, out, _ = run(*MULTI_BLOCK, '--dump-pair', *MULTI_A0_DUMPS)
        self.assertEqual(rc, 0)
        self.assertIn('The whole-block dump pairs above were read', out)
        self.assertNotIn('Those pairs are a read of two dump files', out)
        self.assertNotIn('windows this run refused to print above', out)

    # The regression guard on the other side. The marker exists for a block
    # whose windows were withheld, so an intact block's group line has nothing
    # to carry and must come out exactly as it did before the marker existed --
    # a marker on the common path would be noise on every run, and the line is
    # the one the attribution tests cut on.
    def test_an_intact_block_still_reads_with_no_verdict_marker(self):
        rc, out, _ = run(*RUN_CAPTURES, '--wrote', '0xA0',
                         *dumps(*(RUN_BEFORE, RUN_AFTER)),
                         '--dump-pair', *(RUN_BEFORE, RUN_AFTER))
        self.assertEqual(rc, 0)
        for section in (dumps_section(out), whole_block(out)):
            lines = [l for l in section.splitlines()
                     if l.startswith("  block 0xA0, from the <value>")]
            self.assertEqual(lines,
                             ["  block 0xA0, from the <value> in these "
                              "files' §6 names"])
            self.assertNotIn('VOID', section)
            self.assertNotIn('windows were withheld', section)
        # The scoping line in §4.6 is keyed on the same marker, so it is
        # absent here too rather than firing with nothing to say.
        self.assertNotIn('That is a read of these files and not of block', out)
        self.assertNotIn('Those pairs are a read of two dump files', out)

    # The same silence one step further out: a `--dump` naming a value that is
    # in no block of this run prints as a normal result today, and `verdicts`
    # being empty for it is not the same as a verdict. Said here, where the
    # index exists and the answer is free.
    def test_a_group_naming_a_value_in_no_block_says_no_verdict_is_carried(self):
        # 0xB0 is a value no block under test in `multi-block/` carries, and
        # the PL2 example pair carries no `<value>` of its own, so the flag
        # is the only thing filing it under 0xB0.
        rc, out, _ = run(*MULTI_BLOCK, '--wrote', '0xB0',
                         *dumps(*(PL2_PAIR[0],)), '--dump-pair', *PL2_PAIR)
        self.assertEqual(rc, 0)
        said = ('no block under test 0xB0 is in this run, so no verdict is '
                'carried on this read')
        for section in (dumps_section(out), whole_block(out)):
            self.assertIn(said, " ".join(section.split()))
            self.assertNotIn('VOID', section)
        # Both sections are still read -- this is a read of two files, and the
        # scope of it is what the sentence is about.
        self.assertIn('256 address(es) compared', whole_block(out))
        self.assertIn('0x0784  0x50 -> 0x28', whole_block(out))

    # `verdicts_for` mirrors `report_blocks`' scoping, and the mirror is the
    # load-bearing part: on a `--block 0xA0` run over `3blocks/`, the capture
    # holds a genuinely void block 2 (0x00) and an intact block 3 (0x10), and
    # this run checked neither. An index built over all of them would print
    # "0x00 is VOID" about a block the report says it did not look at -- the
    # defect this fixes, one step removed.
    #
    # Two guards stand between that and the output and both are pinned, so
    # neither can be deleted as redundant: the readers pass `None` rather
    # than the index for a group that is not the block under test, which is
    # what this case asserts against, and `verdicts_for` itself scopes to
    # `selected`, which `test_two_blocks_with_one_value_name_both_verdicts`
    # asserts on directly -- an unscoped index would also mis-report which
    # blocks the closing summary names as refused.
    def test_an_unchecked_block_is_given_no_verdict(self):
        rc, out, _ = run(*BLOCK_CAPTURES, '--block', '0xA0', '--wrote', '0xA0',
                         *dumps(*MULTI_10_DUMPS),
                         '--dump-pair', *MULTI_10_DUMPS)
        # 0, and not 1: 0x00 is void but this run did not check it, and the
        # exit code is about the block that was asked for.
        self.assertEqual(rc, 0)
        self.assertIn('the other 2 block(s) were not checked in this run', out)
        for section, what in ((dumps_section(out), '§4.6'),
                              (whole_block(out), '§4.1-§4.3')):
            # The existing refusal, byte-unchanged.
            self.assertIn('belongs to block 0x10, not the block under test '
                          '(0xA0) -- not read for ' + what + ' here', section)
            # And no verdict about it, or about the void block this run never
            # looked at, in either section.
            self.assertNotIn('VOID', section)
            self.assertNotIn('is intact', section)
            self.assertNotIn('no verdict is carried', section)
        # The block section did print 0xA0's own verdict -- checked and
        # intact, so the run is the clean one it says it is.
        self.assertIn('block 1/3: intact', out)
        self.assertNotIn('block 2/3: VOID', out)

    # The mark set is a precondition of the windows and is checked as one, so
    # "its windows were withheld" has two reasons and not one. `void-block/`
    # is the restore missing; `missing-mark/` and `disagreeing-marks/` are an
    # action missing or spelled two ways *inside* a block that does hold its
    # restore, and `block_verdict` calls those blocks `intact`. A marker keyed
    # on the restore alone would print nothing for them, which is this issue's
    # defect reached by the other road: a read taken for a block whose windows
    # the run refused. Neither of those sets carries a dump, so this is pinned
    # on the builder against the real `problems` lists, and end to end by
    # handing one of them the copied `0xA0` dumps.
    def test_a_refused_mark_set_is_marked_as_well_as_a_void_restore(self):
        for captures, kind in ((MISSING_MARK, 'missing'),
                               (DISAGREEING, 'labels')):
            reads, _, blocks, _ = as_main_reads(captures)
            for b in blocks:
                b.problems = grade.check_block_marks(b, reads)
            block = blocks[0]
            # The two facts `report_blocks` prints as two, and the marker
            # keys on the one that withheld the windows.
            self.assertEqual(grade.block_verdict(block), 'intact')
            self.assertEqual([k for k, _, _ in block.problems], [kind])
            self.assertEqual(grade.block_marker(block),
                             'its mark set does not hold, its windows were '
                             'withheld above')
        # A block with no problems has nothing to mark, which is what keeps
        # the common path byte-identical.
        _, _, blocks, _ = as_main_reads(MULTI_BLOCK)
        self.assertEqual(blocks[0].problems, [])
        self.assertEqual(grade.block_marker(blocks[0]), '')

        # And the same case end to end. Neither set carries a dump of its own,
        # so the two are handed together: the `0xA0` dumps name `0xA0`, which
        # is the one value under test in both, and the read is over the dumps
        # either way -- which is the whole claim. Composed rather than built
        # as a seventh directory for the reason `void-block-with-dumps/` is a
        # copy is not: nothing here is a case a failure has to name, and the
        # dumps are the ones already copied, so an edit to `multi-block/`
        # cannot reach it.
        rc, out, _ = run(*MISSING_MARK, '--wrote', '0xA0',
                         *dumps(*VOID_A0_DUMPS), '--dump-pair', *VOID_A0_DUMPS)
        self.assertEqual(rc, 1)
        # The block section calls it intact and withholds its windows, which
        # is the pair of facts the marker has to sit between.
        self.assertIn("block 1/1: intact -- last mark 'restored 0x0751=0x10' "
                      "is the restore", out)
        self.assertIn('-- NOT GRADED, its windows are not printed', out)
        for section in (dumps_section(out), whole_block(out)):
            self.assertIn("block 0xA0, from the <value> in these files' §6 "
                          "names -- its mark set does not hold, its windows "
                          "were withheld above", section)
        # Still read, still counted, still scoped.
        self.assertIn('16 address(es) compared', whole_block(out))
        self.assertIn('That is a read of these files and not of block', out)
        self.assertIn('Those pairs are a read of two dump files', out)
        # Not a void block, so the void wording is not what is claimed.
        self.assertNotIn('VOID', out)

    # The same two blocks under one value, which no committed capture has: §3's
    # blocks are opened by their write mark, so the same value written twice in
    # a day is two blocks under one name. `Block.index` is what tells them
    # apart, and a marker naming only one of them would be a half-truth in
    # whichever direction it picked -- a read under that value spans both.
    # Asserted on the builder rather than on a run, because a fixture for it
    # is a third block structure this tree does not otherwise carry.
    def test_two_blocks_with_one_value_name_both_verdicts(self):
        at = grade.parse_ts('2026-01-01T12:00:40+01:00')
        printed = grade.Block(0xA0, [grade.Window(at, 'restored 0x0751=0xA0',
                                                  'x.csv')])
        void = grade.Block(0xA0, [grade.Window(at, 'wrote 0x0751=0xA0',
                                               'x.csv')])
        void.problems = [('void', void.windows[-1], 'short its restore')]
        self.assertEqual(grade.verdict_marker([void]),
                         'VOID, its windows were withheld above')
        self.assertEqual(grade.verdict_marker([printed]), '')
        # Both named, in block order, so a read under this value cannot be
        # taken for the one block whose windows were printed.
        self.assertEqual(
            grade.verdict_marker([printed, void]),
            'block 1 of 2 is intact, its windows were printed; block 2 of 2 '
            'is VOID, its windows were withheld above')
        self.assertEqual(grade.verdict_marker([void, void]),
                         'block 1 of 2 is VOID, its windows were withheld '
                         'above; block 2 of 2 is VOID, its windows were '
                         'withheld above')
        # And the index collapses the value to one entry, not two.
        self.assertEqual(grade.verdicts_for([printed, void], None),
                         {0xA0: 'block 1 of 2 is intact, its windows were '
                                'printed; block 2 of 2 is VOID, its windows '
                                'were withheld above'})
        # A `--block` run's index is over the selected block alone, which is
        # the scoping `test_an_unchecked_block_is_given_no_verdict` pins from
        # the outside.
        self.assertEqual(grade.verdicts_for([printed, void], void),
                         {0xA0: 'VOID, its windows were withheld above'})
        self.assertEqual(grade.verdicts_for([printed, void], printed),
                         {0xA0: ''})

    # A label the block walk cannot place is fatal, and the message quotes the
    # three forms §6 fixes rather than describing the problem. The operator
    # cannot fix an unplaceable mark from "this label is malformed"; the three
    # forms are the whole of what has to change. The `mark 3` row below is a
    # hand-written fixture of that shape, and a capture carrying one is still
    # fatal for the whole run however it got there. `ec_watch.py`'s mark
    # prompt used to write it -- `Marker._loop` stamped an empty line as
    # `mark N` -- and stopped on 2026-09-25 (#474): it now refuses a blank
    # press and records nothing, so a capture of that tool's own cannot
    # produce this row any more -- though windows/tools/system_id_probe.py
    # still substitutes the same label, and writes the same shape of row. The
    # fixture and every assertion below stand; see
    # windows/tools/ec_watch-marks.md.
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
        # And a duplicate is not a way to reach the threshold. It is refused
        # rather than counted up to two, so what a duplicate would have
        # suppressed -- the notice that the cross-console checks did not run
        # -- is a line in no report at all rather than a line a reader has to
        # notice is missing.
        rc, out, err = run(QUIET, QUIET)
        self.assertEqual(rc, 1)
        self.assertIn('is given twice', err)
        self.assertNotIn('the cross-console checks did not run', out)
        self.assertNotIn('one capture:', out)

    # The refusal is in `main`, in front of the census, so the half of the fix
    # that keys the count on the distinct captures is not observable through
    # `run()`. Reached directly the readers hold the same line for themselves:
    # one file in the list twice is one capture, so nothing is a missing mark,
    # the census says the cross-console checks did not run, and a void block
    # is reported once rather than once per copy of the file.
    def test_the_readers_count_a_capture_given_twice_as_one_capture(self):
        captures, windows, blocks, unplaced = as_main_reads([QUIET, QUIET])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            problems = [p for b in blocks
                        for p in grade.check_block_marks(b, captures)]
            grade.report_census(captures, windows, blocks, unplaced, {}, None)
        printed = out.getvalue()
        # A mark is not missing from a console that is not there, and the one
        # file's labels agree with themselves, so nothing is withheld.
        self.assertEqual(problems, [])
        self.assertIn('1 capture(s), 2 mark row(s), 2 action(s)', printed)
        self.assertIn('one capture: the cross-console checks did not run',
                      printed)
        # The agreement sentence is reached on the file's own marks and says
        # so: one of one capture, not one of the two the list was holding.
        self.assertIn("'wrote 0x0751=0xA0' in 1 of 1 capture(s), one label each",
                      printed)
        # And the capture is listed once, not under two identical headings.
        heading = '0751-isolation-example-quiet.csv (2 mark(s)):'
        self.assertEqual(printed.count(heading), 1)
        # Three copies rather than two, against the per-capture void check: a
        # filter that dropped only one repeat would leave two reports of the
        # same capture's void block.
        captures, _, blocks, _ = as_main_reads([VOID_BLOCK[0]] * 3)
        problems = [p for b in blocks
                    for p in grade.check_block_marks(b, captures)]
        self.assertEqual([kind for kind, _, _ in problems], ['void'])
        self.assertIn('ends this block on', problems[0][2])


if __name__ == '__main__':
    unittest.main()
