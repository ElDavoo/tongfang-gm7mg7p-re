#!/usr/bin/env python3
"""Offline checks against the constructed captures in testdata/; no hardware
and no real capture is involved."""
import builtins
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

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
# `unplaced-window/` with one thing wrong with each of its two block-less
# restores, so the two strays are refused for the two *different* reasons a
# window in no block can be: the 12:00 one is in all three captures and
# disagrees about the value, the 12:04 one is in two of the three. Both labels
# still parse, so neither is an `unreads` case and the shape is the one
# `unread-window/` below cannot reach -- a stray that is refused for what the
# captures said rather than for what the parse could not read. The six block
# windows and both blocks are that set verbatim, so the only thing that
# withholds a window here is a stray, and the same bytes with both labels
# fixed -- `unplaced-window/` itself -- must not be withheld at all.
UNPLACED_FAILURES = _set('unplaced-window-failures')
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

# §3's command block as it prints it: the same two-value day, with all six of
# its mark rounds per block rather than the three the grader could read before
# #472. The three stage boundaries are here because §3 asks the operator for
# them, and the day is otherwise `multi-block/`'s -- same 0xA0 and 0x10 blocks,
# same duty drift, same climb, nothing §4.1-§4.3 moving. The one thing that is
# not `multi-block/`'s is where the 0x075B rows sit around the `watch over`
# mark, which is the property the boundary exists for and the reason the two
# windows have to be checkable apart.
STAGED_CAPTURES = _set('staged')

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
    """The runbook's four placeholders, resolved to one day's values.

    Shared by all three section readers so the fence of names, the fence of the
    command line and §3's mark rounds are read with one spelling of the
    substitution and not three, and applied to the runbook's text rather than
    to a fixture name -- it is the runbook that carries the placeholders.

    `<current>` and `<original>` are the mode the §3 block starts in, and
    they are the same one: the control arm writes the value already there back
    to itself and the restore puts that value back, so `10` is what both read
    as over the `0xA0` block §3's command line writes. §3 spells them without
    a `0x` because the `0x` is already in the command (`0x0751=0x<current>`),
    so the substitution carries the bare byte rather than a second prefix.
    Adding them here is safe for the two §6 readers, whose text contains
    neither -- which is what the file-list test below would otherwise have to
    check.
    """
    return (text.replace("<date>", "2026-01-01")
                .replace("<value>", "a0")
                .replace("<current>", "10")
                .replace("<original>", "10"))


def section3_command(doc):
    """§3's fenced console block -- the procedure's own command list.

    Cut on §3 and on `### 3a.`, not on the first fence in the file, for the
    reason `section6_command` gives: a fence added above it must not be able
    to take its place unnoticed. Found by its info string as well as by what
    is in it, because §3's block is the `console` fence that runs the
    watchers -- a `console` fence holding something else must not be read as
    the one that fixes the mark labels.
    """
    if "\n## 3. " not in doc:
        raise AssertionError("no §3 in the runbook; the block that fixes the "
                             "mark labels has moved or gone")
    section = doc.split("\n## 3. ", 1)[1].split("\n### 3a. ", 1)[0]
    for fence in re.finditer(r"```[a-z]*\n(.*?)```", section, re.S):
        if "ec_watch.py" in fence.group(1):
            return fence.group(1)
    raise AssertionError("§3 has no fenced console block any more")


# A §3 mark round, as the console block names it: the `rem` line under that
# round, carrying the exact string the operator types into all three consoles.
# Read by the prefix rather than by line number, so a runbook that renames,
# reorders, adds or drops a round changes this list and the case below it
# fails, which is the whole point of reading §3 rather than restating it.
SECTION3_MARK = re.compile(r"^rem  mark each console: (.+)$", re.M)


def section3_marks(doc):
    """§3's six mark-round labels, in the order the console block prints them.

    The `concrete()` placeholders resolved, because `<current>` and
    `<original>` are the two the round labels carry and a label is not a label
    the grader can read until they are the values that block writes.
    """
    block = section3_command(doc)
    labels = [concrete(m) for m in SECTION3_MARK.findall(block)]
    if not labels:
        raise AssertionError("§3's console block names no mark rounds; the "
                             "`rem  mark each console:` lines are what this "
                             "reads, and one of them is missing")
    return labels


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


def window_body(out, number):
    """One window's printed body, up to the next window's header.

    Cut on the mark number rather than searched for in the whole output,
    because the stages a staged capture adds are windows over the *same*
    addresses: a duty byte's `window delta` line reads alike whichever window
    it is in, and the change rows under it print as an offset from that
    window's own mark, so a row at the same distance after two different marks
    is the same text. Which window a line sits in is the assertion, and only
    the cut can make it.
    """
    match = re.search(rf"^--- mark {number}/\d+:.*?(?=^--- mark |\Z)", out,
                      re.M | re.S)
    if match is None:
        raise AssertionError(f"no mark {number} window in the report")
    return match.group(0)


def staged_copies(tmp, edits):
    """`staged/`'s three CSVs, copied into `tmp` with `edits` applied.

    `edits` maps a capture's range -- `0700-07ff.csv`, `0f00-0f5f.csv`,
    `0400-045f.csv`, the suffixes `_set` spells them by -- to a function over
    that capture's text, and a capture the map does not name is copied
    unchanged. A case that a stage boundary fails is a property of the
    boundary rather than a second shape of the day, so it is written beside
    the fixture in a temporary directory instead of taking a directory of its
    own: the alternative is three more rows in `testdata/README.md` to learn
    that the same two checks reach a `watch over` as reach a `wrote`.
    """
    out = []
    for path in STAGED_CAPTURES:
        text = Path(path).read_text(encoding="utf-8")
        edit = edits.get(Path(path).name.rsplit("-0751-isolation-", 1)[1])
        copy = Path(tmp) / Path(path).name
        copy.write_text(edit(text) if edit else text, encoding="utf-8")
        out.append(str(copy))
    return out


def copies_of(tmp, captures, edits=None):
    """`captures` copied into `tmp`, with `edits` applied per file name.

    The arrangement `staged_copies` uses and the reason it uses it: a case
    that is about one row in one capture is a property of that row rather than
    a second shape of the day, so it is written beside the fixture in a
    temporary directory rather than taking a directory of its own in
    `ec/tools/testdata/`. `edits` is keyed on the file's name --
    `staged_copies` keys on the range, which is the same file -- and a capture
    the map does not name is copied unchanged.
    """
    out = []
    for path in captures:
        text = Path(path).read_text(encoding="utf-8")
        edit = (edits or {}).get(Path(path).name)
        copy = Path(tmp) / Path(path).name
        copy.write_text(edit(text) if edit else text, encoding="utf-8")
        out.append(str(copy))
    return out


def insert_after(ts, line):
    """A rewrite of one capture's text: `line` inserted below the row at `ts`.

    The timestamp-keyed cut `edit_mark` makes, for the same reason: one row of
    a capture is named rather than counted, so an edit cannot reach a second
    row that reads alike -- in a two-value day block 2's marks carry the same
    shape as block 1's, and a test that reached both would be testing two
    blocks at once.
    """
    def rewrite(text):
        out = []
        for row in text.splitlines(keepends=True):
            out.append(row)
            if row.startswith(ts):
                out.append(line if line.endswith("\n") else line + "\n")
        return "".join(out)
    return rewrite


def early_exit_row(ts, reason="manual_fan_ctrl_probe: RuntimeError: "
                              "observation failed mid-run"):
    """The row the probe's `except BaseException` handler writes, as text.

    Two CSV fields after the header row is what the tool writes, the tag first
    and the reason in the second, and the tag is the grader's own constant
    rather than a third spelling kept in this file: what these cases are about
    is what the reader makes of the row, not that a test holds its own copy of
    the phrase. The probe's own suite pins the two spellings equal.
    """
    return f"{grade.EARLY_EXIT_TAG} {ts},{reason}"


def edit_mark(ts, label=None):
    """A rewrite of one capture's text: the mark at `ts` gone or respelled.

    Cut by the row's timestamp rather than by its label, because §3's block
    has one `watch over` round *per block* and a case that withholds the
    first block's has to leave the second one's alone -- an edit that reached
    both would be testing two blocks at once and the per-block half of the
    assertion below would have nothing left to say. `ts` is the row's leading
    timestamp, so it can only ever name one row. `label=None` drops the row,
    which is the shape a mark typed after a watcher exited leaves behind in
    the other two captures.
    """
    def rewrite(text):
        out = []
        for line in text.splitlines(keepends=True):
            if not line.startswith(ts):
                out.append(line)
            elif label is not None:
                out.append(line.split(",MARK,,")[0] + f",MARK,,{label}\n")
        return "".join(out)
    return rewrite


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
        flat = " ".join(out.split())
        self.assertIn('=== block 2 of 3, value under test 0x00, '
                      '2 window(s) in it ===', out)
        # The marks are still locatable -- the headers and the numbering are
        # the graded run's -- and the bodies are not, because a block short
        # its restore has a last window that never closes and nothing in the
        # capture to close it with. What the withheld windows would have
        # shown is not reported here and is not to be quoted from this run.
        #
        # This is the one run in the suite that holds all three denominators
        # of a `--block` read at once: the section header's 2 above, the
        # headers' /8, and the banner's own pair below. The first two are
        # asserted already and neither is renumbered to match the third --
        # the whole-stream numbering is what makes a `--block` run a subset
        # of the whole-capture run, which is how §6's one-attachment-per-value
        # workflow reads the two side by side.
        self.assertEqual(marked_windows(out),
                         [(4, 'no-op wrote 0x0751=0xA0'),
                          (5, 'wrote 0x0751=0x00')])
        # So the banner names both of its own rather than picking one. The
        # withheld count is written out on each half, so a change to the
        # number the loop counted, to the block's window count, or to the
        # capture's fails here rather than reading as a still-correct pair.
        self.assertIn('2 of the 2 window(s) of this block', flat)
        self.assertIn("2 of the capture's 8 window(s)", flat)
        # And the defect is pinned, not merely reworded: "of the 2 window(s)
        # above" was false about the two windows printed directly above a
        # line that numbered them 4/8 and 5/8, and no phrasing of that same
        # single denominator may come back.
        self.assertNotIn('2 of the 2 window(s) above were not graded', flat)
        # The refusal is the load-bearing half and it survives the rewrite, on
        # this path as on the whole-capture one: what the withheld windows
        # would have shown is still not quotable from this run.
        self.assertIn('What they would have shown is not reported here and is '
                      'not to be quoted from this run', flat)
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

    # An unreadable label refuses the run whichever block `--block` selected,
    # and the closing section has to say so where the exit code is read from.
    # The two fixtures below are one day byte for byte with a single mark's
    # label differing, so the whole variable between exit 0 and exit 1 is that
    # label -- and over a `--block` run of the refused one the block reads
    # `intact`, no window is withheld, and the movement line below is the
    # clean sentence. So the exit code had no reason printed next to it, which
    # is the shape this test holds shut: the note, and only the note, is what
    # joins the 1 to something the reader can act on.
    def test_an_unreadable_mark_refuses_a_block_run_and_says_why(self):
        rc, out, _ = run(*UNREAD_WINDOW, '--block', '0xA0')
        self.assertEqual(rc, 1)
        section = out.split('=== what this does and does not settle ===')[1]
        flat = " ".join(section.split())
        self.assertIn('A mark this cannot read is a mark no block can be '
                      'attributed to', flat)
        # The scoping clause and the exit code, so a note that stopped saying
        # either of the two things this issue is about would fail here rather
        # than pass on the fact that it printed at all.
        self.assertIn('--block narrows what is graded, not what is known, and '
                      'this refusal holds for the whole run whichever block '
                      'was selected', flat)
        self.assertIn('The exit code is 1 until they do', flat)
        # The two facts that made this a mystery, pinned as still true: the
        # block is intact and nothing was withheld, so the note is not a
        # restatement of the banner above it.
        self.assertIn('block 1/2: intact', out)
        self.assertNotIn('were not graded', section)
        self.assertNotIn('NOT GRADED', out)
        # And the census line the note points at is the one that is there: the
        # refused window is in `unreads`, so it never gets the `unplaced:`
        # line, and a note pointing there would send the reader after a line
        # this run does not print.
        self.assertIn('UNREADABLE  unplaced', out)
        self.assertEqual(census(out).count('`--block` cannot select it'), 1)

        # The other direction, over the same bytes with that one label
        # readable: a window in no block whose label parses is graded as
        # `unplaced` and does not refuse the run, so the note is absent and
        # the exit code is 0. This is what makes "the note is printed
        # exactly when this refusal fires" a property of the tool rather than
        # a fact about one fixture.
        rc, out, _ = run(*UNPLACED_WINDOW, '--block', '0xA0')
        self.assertEqual(rc, 0)
        self.assertNotIn('A mark this cannot read', out)
        self.assertIn('block 1/2: intact', out)
        # Both strays get the census line here, because both of their labels
        # parse, which is the other half of the pair: the line the note points
        # at counts one in the first run and two in this one.
        self.assertEqual(census(out).count('`--block` cannot select it'), 2)

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
    # counts are the fixture's rather than shared. It is also the only committed
    # fixture where this branch's *other* reason fires at the same time: 1 of
    # its 7 graded windows is in no block, so the movement is stated over the 6
    # that are a window of a value under test (#530).
    def test_a_withheld_window_in_no_block_claims_no_block_was_refused(self):
        rc, out, _ = run(*UNREAD_WINDOW)
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        # The same split, from the label rather than the mark set: 1 withheld,
        # 7 graded, and the refusal to compare with the prediction is
        # unchanged. This branch is reached either way.
        self.assertIn('1 of the 8 window(s) above were not graded', flat)
        # Over the 6 of those 7 that are a window of a value under test, and
        # with *both* kinds of excluded window named: the 1 withheld and the
        # 1 graded in no block. Claiming all 7 here is the overclaim #530 is
        # about -- the count line directly above says 1 of the 7 is in no
        # block, so a sentence claiming the 7 contradicts the disclosure
        # printed beside it.
        self.assertIn('None of the §4.1-§4.3 bytes moved in any of the 6 '
                      'window(s) that were graded and belong to a value under '
                      'test', flat)
        self.assertIn('neither the 1 window(s) withheld above nor the 1 graded '
                      'window(s) in no block are part of it', flat)
        # And the graded set as a whole is never the claim's denominator here:
        # 7 is the count's figure, and a sentence over all 7 is the one this
        # run must not make.
        self.assertNotIn('in any of the 7 window(s)', flat)
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
        # path none was. The window in no block is named alongside it, because
        # this run read that one and still cannot speak for it; and the
        # "sits in a block of its own" caveat is about the *refused* window,
        # since which block that one sits in is exactly what this output
        # cannot say -- and is not a question a window in no block raises.
        self.assertIn('`confirmed-inert` needs all three values, and a window '
                      'in no block, or one this report refused to read, is one '
                      'this run cannot speak for', flat)
        self.assertIn('whether the refused one sits in a block of its own is '
                      'not something this output can say', flat)
        self.assertNotIn('a block this report refused to read', out)

    # The case that is not a refusal at all, and was the only one of the four
    # the closing section did not name. Nothing is withheld here and nothing
    # needs to be: the 12:00 and 12:04 strays' labels both parse, so both
    # windows are read, their rows are real, and the run graded all 8. But
    # neither window is a window of any value under test -- a label is the only
    # thing that attributes a window, and these two name 0x99, which is no
    # block's -- so the run reached the bare `else` and printed the
    # whole-capture sentence over a set that is not the whole capture's
    # windows of anything. Exit 0 either way, which is what made it quiet.
    def test_a_graded_window_in_no_block_is_scoped_where_the_prediction_is_read_from(
            self):
        rc, out, _ = run(*UNPLACED_WINDOW)
        self.assertEqual(rc, 0)
        section = out.split('=== what this does and does not settle ===')[1]
        flat = " ".join(section.split())
        # The count, in the section that already carries the withheld banner
        # and the unreadable-mark note, and over the graded denominator rather
        # than the shown one: 8 here, against 7 in the partly-withheld pair
        # below. Written out rather than derived, so a change in either
        # figure fails here.
        self.assertIn('2 of the 8 graded window(s) above are in no block', flat)
        # And the count is the whole of the note: it ends at the census. The
        # note is printed above the whole branch chain, so which sentence
        # follows it is not its to decide -- on a run that also withheld a
        # window, the sentence below claims over a different set than the one
        # this run's chain does, and a "the claim below is over the other 6"
        # tacked onto the count would be asserting a scope the next sentence
        # does not carry. Each branch states its own; the count is bare.
        self.assertNotIn('The claim below is therefore over the other', out)
        self.assertNotIn('rather than over the day', out)
        # The movement is stated over the windows the count leaves, and the
        # windows it leaves are named as outside it -- the withheld branch's
        # own shape, one step over.
        self.assertIn('None of the §4.1-§4.3 bytes moved in any of the 6 '
                      'window(s) that belong to a value under test', flat)
        self.assertIn('the 2 graded window(s) in no block above are not part '
                      'of it', flat)
        # The comparison itself is declined, and for the count's reason rather
        # than the withheld branch's: this run read every window, so "a run
        # it only read part of" would be false, and the sentence says the
        # narrower thing instead.
        self.assertIn('this output does not make it over a run in which 2 of '
                      'its 8 graded window(s) are in no block', flat)
        self.assertNotIn('consistent with the static prediction', section)
        self.assertNotIn('a run it only read part of', section)
        # Nor either of the two refusal shapes: this run refused nothing, and
        # reaching for one of their sentences would report a day that graded
        # clean as one this tool could not read.
        self.assertNotIn('were not graded', out)
        self.assertNotIn('No window in this run was graded', out)
        # The two facts that made this a mystery, pinned as still true, so a
        # note that quietly changed a block verdict fails here rather than
        # passing a test that only reads prose. Both blocks are intact, the
        # capture is complete, and the census still says of each stray that
        # `--block` cannot select it -- a fact about selection, which is why
        # the note had to be a second thing.
        self.assertIn('block 1/2: intact', out)
        self.assertIn('block 2/2: intact', out)
        self.assertEqual(census(out).count('`--block` cannot select it'), 2)

        # The composition, and the reason the count is structurally zero there
        # rather than guarded to be: a `--block` run's `shown` is that block's
        # own windows and a window in no block is in none of them, so the
        # count cannot fire and cannot compete with the selected-block branch.
        # Over the same bytes and the same marks, the run is still the
        # per-block one, and still says nothing about a mark it could not read.
        rc, out, _ = run(*UNPLACED_WINDOW, '--block', '0xA0')
        self.assertEqual(rc, 0)
        section = out.split('=== what this does and does not settle ===')[1]
        self.assertIn('None of the §4.1-§4.3 bytes moved in any of the 3 '
                      'window(s) in block 1 of 2, value under test 0xA0',
                      section)
        self.assertNotIn('graded window(s) above are in no block', section)
        self.assertNotIn('A mark this cannot read', out)

    # The two figures are over disjoint sets, and that is a property of where
    # each is counted rather than a fact about this fixture. A window can be
    # both in no block and withheld -- the 12:00 stray in this set is exactly
    # that, and the banner above names it as refused -- so a count taken over
    # `shown` rather than over the windows actually printed would read 2 of the
    # 8 here and put the same window in both figures. Pinned on this fixture
    # rather than only on the cleaner one above for that reason: there the two
    # counts coincide, and a count of the wrong set would print 2 of the 8
    # there too and only this is where the two denominators differ.
    def test_an_unreadable_mark_does_not_count_twice_in_the_graded_unplaced_line(
            self):
        rc, out, _ = run(*UNREAD_WINDOW)
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        # The banner is unchanged and still over the shown denominator.
        self.assertIn('1 of the 8 window(s) above were not graded', flat)
        # And the count is over the graded one, one lower, naming the other
        # stray: 12:00 is refused, 12:04 is read.
        self.assertIn('1 of the 7 graded window(s) above are in no block', flat)
        # The note about a mark that could not be read is still printed, and
        # the withheld branch is still the one that carries the sentence --
        # this run withheld, so the count line is beside its reason rather than
        # a replacement for it.
        self.assertIn('A mark this cannot read is a mark no block can be '
                      'attributed to', flat)
        # And the branch's own sentence states the same scope the count
        # describes. This is the pairing the count cannot leave alone: the
        # count says 1 of the 7 graded is in no block, so a sentence claiming
        # the movement over all 7 would claim it over the one the count just
        # excluded. The withheld branch narrows to the 6 that are a window of
        # a value under test and names both excluded windows, so the two
        # figures agree -- 6, not 6 and 7 in the same section.
        self.assertIn('None of the §4.1-§4.3 bytes moved in any of the 6 '
                      'window(s) that were graded and belong to a value under '
                      'test', flat)
        self.assertIn('neither the 1 window(s) withheld above nor the 1 graded '
                      'window(s) in no block are part of it', flat)
        self.assertNotIn('in any of the 7 window(s)', flat)
        self.assertNotIn('consistent with the static prediction', out)
        # And the 12:00 window is named as refused exactly once, which is the
        # user-visible half of "counted at the print point": the count does not
        # print a window header, so anything beyond these two figures would be
        # a second claim about the same mark.
        self.assertEqual(out.count('block: unplaced -- NOT GRADED'), 1)
        self.assertEqual(out.count('block: unplaced'), 2)

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

    # The same movement half with nothing withheld, which is a combination no
    # committed fixture reaches: `unplaced-window/` reads every window it is
    # shown, `3blocks-moved/` is the only set that moves, and the two do not
    # meet. The count is over the windows and not over the arms, so one
    # `0x0784` row is all it takes to put them together -- in either of the
    # two placements the count does not distinguish. Copies rather than a
    # directory of their own, for the reason `copies_of`'s docstring gives.
    def test_a_movement_in_the_graded_windows_of_a_partly_unplaced_run_is_scoped(
            self):
        # `3blocks-moved/`'s row is this address and this step, and both
        # anchors are named rather than counted, so a mark that moves in the
        # fixture cannot quietly change which window this row is in.
        def moved_copy(tmp, anchor, ts):
            return copies_of(tmp, UNPLACED_WINDOW, {
                '2026-01-01-0751-isolation-0700-07ff.csv':
                insert_after(anchor, f'{ts},0x0784,0x50,0x28')})

        with tempfile.TemporaryDirectory() as tmp:
            paths = moved_copy(
                tmp, '2026-01-01T12:00:40.000+01:00,MARK,,wrote 0x0751=0xA0',
                '2026-01-01T12:00:43.000+01:00')
            rc, out, err = run(*paths)
        self.assertEqual(rc, 0, err)
        section = out.split('=== what this does and does not settle ===')[1]
        flat = " ".join(section.split())
        # The count is #530's and is still only a count: what follows it is
        # the branch's own sentence, so the two now say the same thing about
        # the same set rather than the count disclaiming the claim below it.
        self.assertIn('2 of the 8 graded window(s) above are in no block', flat)
        # The movement line is the run's own and names the group the row
        # belongs to: a PL move and not a mailbox poke, so the attribution
        # underneath is the static-prediction one, and scoping is not
        # retracting -- a PL that moved is still the more interesting outcome
        # whatever this run can say about where.
        self.assertIn('At least one of the §4.1-§4.3 bytes moved after a '
                      'mark: PL1/PL2/PL4 (§4.1).', out)
        self.assertIn('That contradicts the static prediction', out)
        self.assertNotIn('host-written reload mailbox', out)
        # And between them, the scope: the whole graded set rather than a
        # subset of it, with the unattributed windows named as *part* of that
        # set. That is the claim `moved_groups` supports -- it is a union of
        # group names over `shown` and carries no window identity -- so no
        # narrower one is available, and the sentence says why rather than
        # leaving the reader to work out that a window in no block was in it.
        self.assertIn('That is the 8 window(s) that were graded. The 2 in no '
                      'block are part of it, and this run cannot say which arm '
                      'they are a window of.', flat)
        # The capture-level comparison is declined for the attribution reason,
        # in the no-movement arm's own words and not the withheld arm's: this
        # run read every window it was shown, so "a run it only read part of"
        # would be false here in a way it is not there.
        self.assertIn('this output does not make it over a run in which 2 of '
                      'its 8 graded window(s) are in no block', flat)
        self.assertNotIn('a run it only read part of', section)
        # And none of the four siblings came with it. Nothing was withheld and
        # no block was selected, so the first two are out of reach here, and a
        # run that moves must not pick up the no-movement chain's narrowing
        # either -- there is a movement to scope, not a `None ... moved` to
        # place.
        self.assertNotIn('were not graded', out)
        self.assertNotIn('That is the 6 window(s) that were graded', out)
        self.assertNotIn('That is block', out)
        self.assertNotIn('No window in this run was graded', out)
        self.assertNotIn('belong to a value under test: that is what those 6 '
                         'windows show', flat)

        # The same run with the same row inside the 12:00 stray rather than
        # inside block 1's write window: same marks, same block structure, same
        # `moved_groups`, same count, and `--block` cannot reach either
        # placement. Pinned as an equality over the closing section rather than
        # as a restatement of it, because the two placements are what decide
        # the wording -- "that is the 6 window(s) that belong to a value under
        # test" is true of the first and false of the second, and a sentence
        # that cannot tell them apart is the defect.
        with tempfile.TemporaryDirectory() as tmp:
            paths = moved_copy(
                tmp, '2026-01-01T12:00:02.000+01:00,MARK,,restored 0x0751=0x99',
                '2026-01-01T12:00:05.000+01:00')
            rc, out, err = run(*paths)
        self.assertEqual(rc, 0, err)
        self.assertEqual(
            out.split('=== what this does and does not settle ===')[1],
            section)

        # And the arm cannot reach a `--block` run, structurally rather than by
        # a guard: that run's `shown` is the block's own windows, and a window
        # in no block cannot be one of them. The same bytes are still the
        # per-block run, still over its own three windows.
        with tempfile.TemporaryDirectory() as tmp:
            paths = moved_copy(
                tmp, '2026-01-01T12:00:40.000+01:00,MARK,,wrote 0x0751=0xA0',
                '2026-01-01T12:00:43.000+01:00')
            rc, out, err = run(*paths, '--block', '0xA0')
        self.assertEqual(rc, 0, err)
        section = out.split('=== what this does and does not settle ===')[1]
        self.assertIn('That is block 1 of 2, value under test 0xA0, over its 3 '
                      'window(s).', " ".join(section.split()))
        self.assertNotIn('That is the 3 window(s) that were graded', section)
        self.assertNotIn('graded window(s) above are in no block', section)

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
    # forms §6 fixes rather than describing the problem. The operator cannot
    # fix an unplaceable mark from "this label is malformed"; the forms are
    # the whole of what has to change. It used to say "the three forms" and
    # quote three; it now quotes all six -- the three stage boundaries as well
    # as the three actions -- and takes the count from the tuple rather than
    # from a word in the sentence, so the two cannot disagree. The `mark 3`
    # row below is a hand-written fixture of that shape, and a capture
    # carrying one is still fatal for the whole run however it got there.
    # `ec_watch.py`'s mark prompt used to write it -- `Marker._loop` stamped
    # an empty line as `mark N` -- and stopped on 2026-09-25 (#474): it now
    # refuses a blank press and records nothing, so a capture of that tool's
    # own cannot produce this row any more -- though
    # windows/tools/system_id_probe.py still substitutes the same label, and
    # writes the same shape of row. The fixture and every assertion below
    # stand; see windows/tools/ec_watch-marks.md.
    def test_a_mark_that_is_not_one_of_the_forms_is_an_error(self):
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
        self.assertIn("'mark 3' is not one of the forms §6 fixes", flat)
        # All six, from the tuple and not from a copy: a stage boundary the
        # message did not quote is a boundary an operator who mistyped one
        # cannot see the right spelling of.
        self.assertEqual(len(grade.REQUIRED_LABEL_FORMS), 6)
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

    # The per-window agreement checks are properties of the marks, not of the
    # block a window falls in, and a window the block walk could not place was
    # reaching neither of them: `main` handed `check_block_marks` the blocks
    # and `unplaceable_marks` the strays, and a stray whose label parses and
    # that one console spelled two ways or did not record was passed to nobody
    # and graded in full. The census named both defects on the run before it;
    # nothing withheld the window or moved the exit code.
    #
    # The two strays are refused for the two different reasons rather than
    # being one case, because the tool checks them separately and a one-sided
    # fix would then have nothing to fail against: `labels` on the 12:00 one,
    # `missing` on the 12:04. Both blocks are intact and all six of their
    # windows print, so what withholds the two is the strays' own marks and
    # not a block's.
    def test_a_window_in_no_block_fails_the_same_agreement_checks(self):
        rc, out, _ = run(*UNPLACED_FAILURES)
        self.assertEqual(rc, 1)
        # Two strays, two refusals, and no third window caught up in them.
        self.assertEqual(out.count('block: unplaced -- NOT GRADED'), 2)
        # Each refusal carries the problem that produced it, under the window
        # it is about, in the window's own place in the mark stream. The
        # 12:00 stray is the disagreement: all three consoles recorded it and
        # one typed a different value, so the census's own per-capture list
        # is what the refusal has to name.
        disagree = out.split('\n--- mark 1/8:')[1].split('\n--- mark 2/8:')[0]
        flat = " ".join(disagree.split())
        self.assertIn('block: unplaced -- NOT GRADED', disagree)
        self.assertIn('not graded -- the captures spell this action '
                      'differently', flat)
        self.assertIn("2026-01-01-0751-isolation-0700-07ff.csv: "
                      "'restored 0x0751=0x0a'", flat)
        # And the 12:04 one is the missing mark, naming the console that did
        # not record it rather than the label it did record.
        absent = out.split('\n--- mark 5/8:')[1].split('\n--- mark 6/8:')[0]
        flat = " ".join(absent.split())
        self.assertIn('block: unplaced -- NOT GRADED', absent)
        self.assertIn('not graded -- recorded in 2 of 3 capture(s)', flat)
        self.assertIn('absent from 2026-01-01-0751-isolation-0f00-0f5f.csv',
                      flat)
        # Neither refusal is a block's: both blocks still hold their restore
        # and are called intact, and the six windows between them are printed
        # in the usual format rather than refused. Counted on the `block:`
        # line rather than on `marked_windows`, which finds a header for a
        # withheld window too -- that is what the header is for, so the mark
        # stays locatable in a report that will not print its rows.
        self.assertIn('block 1/2: intact', out)
        self.assertIn('block 2/2: intact', out)
        self.assertEqual(out.count('\n    block: 0xA0 (block 1 of 2)\n'), 3)
        self.assertEqual(out.count('\n    block: 0x10 (block 2 of 2)\n'), 3)
        # Every `unplaced` line in the window section is a refusal, and there
        # is no plain one: the clean half below is the case where two of them
        # are graded, and this is not that case.
        self.assertNotIn('\n    block: unplaced\n', out)
        self.assertEqual(marked_windows(out), [
            (1, 'restored 0x0751=0x0a / restored 0x0751=0x99'),
            (2, 'no-op wrote 0x0751=0x10'), (3, 'wrote 0x0751=0xA0'),
            (4, 'restored 0x0751=0x10'), (5, 'restored 0x0751=0x99'),
            (6, 'no-op wrote 0x0751=0x00'), (7, 'wrote 0x0751=0x10'),
            (8, 'restored 0x0751=0x00')])
        self.assertIn('2 of the 8 window(s) above were not graded', out)
        self.assertIn('6 window(s) that were graded', out)
        # The banner has to name the reason, or it is a count an operator
        # cannot act on. Its second clause is the one this case reaches, and
        # the "no label could be read" half of it must not be the only
        # answer: both labels here parse.
        flat = " ".join(out.split('=== what this does and does not settle '
                                  '===')[1].split())
        self.assertIn('the captures disagree about the action it opened', flat)
        # And the census, which prints whole, still names both strays and
        # still says what the agreement checks now reach and what they do not.
        self.assertEqual(census(out).count('`--block` cannot select it'), 2)
        self.assertEqual(census(out).count('the void check cannot'), 2)

    # The clean half, which is the half this could have broken. A check that
    # has quietly started refusing everything looks exactly like a check that
    # is working, and `unplaced-window/` is the same day byte for byte with
    # both stray labels whole: every mark in all three captures, all three
    # spelling it the same way, both blocks intact. Nothing in the tree
    # asserted `NOT GRADED` is *absent* over it before this -- the clean half
    # of the unreadable-mark test stands on rc 0 plus a census count -- so a
    # check that fired on a stray whose marks agree would not have failed
    # anything.
    def test_a_window_in_no_block_whose_marks_agree_is_not_refused(self):
        rc, out, _ = run(*UNPLACED_WINDOW)
        self.assertEqual(rc, 0)
        self.assertNotIn('NOT GRADED', out)
        self.assertNotIn('were not graded', out)
        # Both strays graded, and the census still promises what it always
        # did about them: `--block` cannot select either one.
        self.assertEqual(marked_windows(out), [
            (1, 'restored 0x0751=0x99'), (2, 'no-op wrote 0x0751=0x10'),
            (3, 'wrote 0x0751=0xA0'), (4, 'restored 0x0751=0x10'),
            (5, 'restored 0x0751=0x99'), (6, 'no-op wrote 0x0751=0x00'),
            (7, 'wrote 0x0751=0x10'), (8, 'restored 0x0751=0x00')])
        self.assertEqual(out.count('block: unplaced'), 2)
        # And the run is the clean one the census said it was: every window
        # graded and nothing refused. It was written here to pin the
        # whole-capture sentence as the one a fully-graded run reaches, and
        # #530 changed that half of it -- on this very fixture, because "every
        # window graded" is not "every graded window a window of a value under
        # test" and the two strays are not one. The bare `else` is now reached
        # only when both hold, so what this case pins is that *grading* is
        # untouched by the refusal checks: the count of graded windows in no
        # block is a disclosure, not a refusal (`were not graded` above, and
        # `NOT GRADED` never), and the sentence under it is #530's, scoped to
        # the 6 of the 8 that are a window of a value under test. #530's own
        # test on this fixture
        # (`test_a_graded_window_in_no_block_is_scoped_...`) is the one that
        # pins that sentence in full.
        flat = " ".join(out.split('=== what this does and does not settle '
                                  '===')[1].split())
        self.assertNotIn('consistent with the static prediction', flat)
        self.assertIn('None of the §4.1-§4.3 bytes moved in any of the 6 '
                      'window(s) that belong to a value under test', flat)
        self.assertIn('the 2 graded window(s) in no block above are not part '
                      'of it', flat)
        self.assertIn('block 1/2: intact', out)
        self.assertIn('block 2/2: intact', out)

        # And the refusal that was there before this one still is, and still
        # reaches only its own window. `unread-window/` is this same day with
        # the 12:00 stray's label made unreadable in all three captures, so it
        # is refused for `unreads` rather than for a disagreement, and the
        # 12:04 one -- whose label is the one this case's fixture edits and
        # that one leaves alone -- is still graded. A new check that swallowed
        # the old one would refuse both and print 2 of the same marker.
        rc, out, _ = run(*UNREAD_WINDOW)
        self.assertEqual(rc, 1)
        self.assertEqual(out.count('block: unplaced -- NOT GRADED'), 1)
        self.assertIn('1 of the 8 window(s) above were not graded', out)
        # The 7 that were graded is still the run's graded figure, and #530
        # moved where the closing sentence reads it from: the count line
        # carries it, over the graded denominator, while the sentence under it
        # states the movement over the 6 of those 7 that are a window of a
        # value under test. What this case is about is unchanged -- the 12:00
        # stray is refused once, the 12:04 one is read -- and the narrower
        # sentence is #530's, pinned in full by the two tests it added.
        self.assertIn('1 of the 7 graded window(s) above are in no block', out)
        self.assertIn('not one of the forms §6 fixes',
                      " ".join(out.split()))

    # The function on its own, reached directly the way the other per-window
    # and per-block readers are, so that what the two strays are refused for
    # is pinned as the kinds rather than only as the sentences the kinds
    # happen to print. `labels` on the 12:00 window and `missing` on the 12:04,
    # one each: a stray can fail both at once and nothing in the report would
    # then say which, so a change that made the second problem crowd out the
    # first would print the same words.
    def test_the_unplaced_window_problems_name_their_kind_per_window(self):
        captures, windows, blocks, unplaced = as_main_reads(UNPLACED_FAILURES)
        self.assertEqual(len(unplaced), 2)
        problems = grade.unplaced_window_problems(unplaced, captures)
        # One entry per failing window, and it is the window that is the key
        # -- `main` prints each refusal in its own window's place.
        self.assertEqual(set(problems), set(unplaced))
        for w, texts in problems.items():
            self.assertEqual(len(texts), 1, f'{w.label!r}')
        # The kinds, in mark order, and each window's own text carrying the
        # fact that named it.
        names, _ = grade.distinct_captures(path for path, _ in captures)
        self.assertEqual(
            [kind for w in unplaced for kind, _, _
             in grade.window_mark_problems(w, names, set(names))],
            ['labels', 'missing'])
        disagree, absent = (problems[w][0] for w in unplaced)
        self.assertIn('the captures spell this action differently', disagree)
        self.assertIn('2026-01-01-0751-isolation-0f00-0f5f.csv', absent)
        # The empty half, and it is the one that fails if the check has
        # started refusing everything: the same day with both strays' labels
        # whole is not a single problem.
        captures, windows, blocks, unplaced = as_main_reads(UNPLACED_WINDOW)
        self.assertEqual(len(unplaced), 2)
        self.assertEqual(
            grade.unplaced_window_problems(unplaced, captures), {})


class StageBoundaryTests(unittest.TestCase):
    """§3's six mark rounds, and the three of them that are not writes.

    Before #472 the settle, the hold and the end of the watch were rounds
    §3's own command block asked for and the grader could not read: a label
    outside the three action forms returned `(None, None)`, the window went
    to `unplaced`, and `unplaceable_marks` refused the whole run -- over the
    day below, six of twelve windows withheld and exit 1, the boundary halves
    of every block ungraded. A boundary is now a role of its own, so the block
    the procedure prints is one the block model can name.

    The cases below are the two ends of that. The first reads the runbook and
    the grader against each other, so a rename, a reorder, an added round or
    a dropped one is a failing test rather than a human's day. The rest say
    what the new class of mark does once it is in the block: it closes a
    window, it is scoped by `--block`, and it fails the same checks any other
    mark does.
    """

    # The contract the issue is really about. §3, §6 and `parse_mark` are one
    # list of forms, and a disagreement between any two of them has to be a
    # red test rather than a day's capture. Read out of the runbook rather
    # than restated, for the reason `section6_file_list` gives.
    def test_section3s_six_rounds_are_the_forms_the_grader_reads(self):
        doc = RUNBOOK.read_text(encoding="utf-8")
        labels = section3_marks(doc)
        # Exactly six, and each one parses to the role the block model gives
        # it -- so the round the operator is told to type and the window the
        # grader opens for it are the same thing.
        self.assertEqual(
            [grade.parse_mark(label) for label in labels],
            [("settle", None), ("control", 0x10), ("hold", None),
             ("write", 0xA0), ("watch", None), ("restore", 0x10)])
        # The three boundaries carry no value and the three actions do, which
        # is the whole of the difference between them and the reason the form
        # table has a flag for it.
        self.assertEqual(grade.BOUNDARY_ROLES, ("settle", "hold", "watch"))
        # And the roles §3's six rounds produce are exactly the roles the six
        # forms the refusal message quotes produce: a role added to the grader
        # without a round to type it, or a round added without a form to read
        # it, fails here rather than at a mark prompt.
        self.assertEqual(set(grade.parse_mark(l)[0] for l in labels),
                         {grade.parse_mark(f)[0]
                          for f in grade.REQUIRED_LABEL_FORMS})
        # The three stage words are in the tuple by name, so the prompt's
        # notice and `unplaceable_marks`' message quote a string the operator
        # can type verbatim.
        for word in ("settled", "held", "watch over"):
            self.assertIn(word, grade.REQUIRED_LABEL_FORMS)
        # §6 names the same six, and the three actions in it are the three it
        # has always named: a §6 that listed the actions and dropped the
        # boundaries would leave the operator reading a list the prompt
        # refuses half of.
        section6 = doc.split("\n## 6. ", 1)[1].split("\n## 7. ", 1)[0]
        for word in ("settled", "held", "watch over"):
            self.assertIn(word, section6)
        for form in grade.REQUIRED_LABEL_FORMS[:3]:
            self.assertIn(form, section6)

    # The defect, measured. §3's block as printed is now a capture the grader
    # grades rather than refuses: twelve windows, two intact blocks, no
    # withheld and nothing unreadable.
    def test_a_staged_six_round_run_is_graded_rather_than_refused(self):
        rc, out, _ = run(*STAGED_CAPTURES)
        self.assertEqual(rc, 0)
        self.assertNotIn('UNREADABLE', out)
        self.assertNotIn('NOT GRADED', out)
        self.assertNotIn('were not graded', out)
        # Every window of both blocks printed, in the block's own order, and
        # the roles line is the six §3 asks for rather than the three the
        # model had room for.
        self.assertEqual(
            marked_windows(out),
            [(1, 'settled'), (2, 'no-op wrote 0x0751=0x10'), (3, 'held'),
             (4, 'wrote 0x0751=0xA0'), (5, 'watch over'),
             (6, 'restored 0x0751=0x10'), (7, 'settled'),
             (8, 'no-op wrote 0x0751=0x00'), (9, 'held'),
             (10, 'wrote 0x0751=0x10'), (11, 'watch over'),
             (12, 'restored 0x0751=0x00')])
        for block, value in ((1, '0xA0'), (2, '0x10')):
            self.assertIn(f"block {block}/2: intact -- last mark", out)
            self.assertIn(f"value under test {value}; roles settle, control, "
                          "hold, write, watch, restore", out)
        # The last-mark-is-the-restore check reaches the boundary windows and
        # is unaffected by them: `watch over` is not a restore, and a block
        # that ended on one would be void.
        self.assertEqual(out.count(': intact -- last mark'), 2)
        self.assertNotIn('VOID', out)

    # The substantive claim, and the reason the fixture puts a 0x075B row on
    # each side of the `watch over` mark. §4.4's control-vs-write comparison
    # is taken over the write's window, so that window has to stop at the end
    # of the watch rather than run on into the restore.
    def test_the_end_of_watch_round_closes_the_write_window(self):
        rc, out, _ = run(*STAGED_CAPTURES)
        self.assertEqual(rc, 0)
        write, watch, restore = (window_body(out, n) for n in (4, 5, 6))
        # The two duty rows on either side of the boundary are in different
        # windows, and each says so by its own figures: two changes inside
        # the write's, one in the window the boundary opened. Merged -- the
        # shape a capture without a `watch over` mark has -- the write's
        # window reads `0x68 -> 0x6D` over three changes, and the restore's
        # own 0x0751 write is inside the same bracket as the observation.
        self.assertIn('window delta  0x075B  0x68 -> 0x6B  net +3  total 3  '
                      'max 3  (2 changes)', write)
        self.assertIn('window delta  0x075B  0x6B -> 0x6D  net +2  total 2  '
                      'max 2  (1 change)', watch)
        self.assertNotIn('0x6D', write)
        self.assertNotIn('0x68', watch)
        # `0x0751` itself is in neither watched nor context group, so the
        # report names it among "other addresses that moved" without printing
        # the two values -- which is why the fixture moves the duty byte
        # around the boundary rather than the byte under test. The restore's
        # own 0x0751 write is after the 12:03:00 row, so it is in the restore
        # window and the split above already says it is not in the write's.
        self.assertIn('0x0751', write)
        self.assertIn('0x0751', restore)
        # The same boundary in the temperature capture, so the property is
        # not one address's accident: CPU_TEMP moves in the write window and
        # again in the one the boundary opened.
        self.assertIn('window delta  0x043E  0x37 -> 0x3B', write)
        self.assertIn('window delta  0x043E  0x3B -> 0x3C', watch)

    # A boundary is one mark like any other to the agreement checks, which is
    # the point of making it one. Both failure kinds, because they are
    # different checks and a fix that reached only one of them would leave a
    # `watch over` half-checked: a stage round a console missed is as much a
    # hole in the record as a `write` it missed.
    def test_a_stage_boundary_is_checked_like_any_other_mark(self):
        # `staged/`'s 0f00 capture records a round a second after the 0700
        # capture's and its 0400 one two seconds after, so block 1's
        # `watch over` is the `12:02:4x` row in each case below. The label
        # the two consoles disagree on is `watched over`: it reads as the
        # stage it is and the merge still parses it, so the case is the
        # disagreement check and not the unplaceable one.
        cases = [
            ('0f00-0f5f.csv', '2026-01-01T12:02:41', None, 'missing',
             'recorded in 2 of 3 capture(s), absent from '
             '2026-01-01-0751-isolation-0f00-0f5f.csv',
             'read quiet for want of a mark rather than because nothing '
             'moved'),
            ('0400-045f.csv', '2026-01-01T12:02:42', 'watched over', 'labels',
             'the captures spell this action differently',
             'the window it opens is not the action any of them recorded'),
        ]
        for capture, ts, respelt, kind, refused, cost in cases:
            with tempfile.TemporaryDirectory() as tmp:
                rc, out, _ = run(*staged_copies(
                    tmp, {capture: edit_mark(ts, respelt)}))
            self.assertEqual(rc, 1, kind)
            flat = " ".join(out.split())
            # Named per capture and with the consequence that check states,
            # which is a different sentence for each of the two.
            self.assertIn(refused, flat, kind)
            self.assertIn(cost, flat, kind)
            # The whole block is withheld, its boundary windows included: the
            # check is over the block's mark set, so a block that fails it
            # loses all six windows and not the four after the bad one.
            self.assertEqual(
                out.count('block: 0xA0 (block 1 of 2) -- NOT GRADED'), 6,
                kind)
            self.assertIn(f'1 problem(s): {kind}', flat, kind)
            # Block 2 never saw the edit and is unaffected, which is what
            # makes this a per-block check rather than a run-wide one -- and
            # the only thing the edit had to be cut by timestamp to show.
            self.assertIn('block 2/2: intact', out, kind)
            self.assertEqual(out.count('block: 0x10 (block 2 of 2) -- '
                                      'NOT GRADED'), 0, kind)
            self.assertEqual(out.count('no watched byte moved in this '
                                      'window'), 6, kind)

    # `--block` selects the windows a boundary opened, not the three an older
    # capture of the same block carries. A scoping that silently dropped them
    # would print a clean per-block attachment whose write window was the
    # `settle` window's, which is the mis-attribution the block model exists
    # to stop.
    def test_block_selects_all_six_windows_of_a_staged_block(self):
        rc, out, _ = run(*STAGED_CAPTURES, '--block', '0xA0')
        self.assertEqual(rc, 0)
        self.assertIn('=== block 1 of 2, value under test 0xA0, '
                      '6 window(s) in it ===', out)
        self.assertEqual(
            marked_windows(out),
            [(1, 'settled'), (2, 'no-op wrote 0x0751=0x10'), (3, 'held'),
             (4, 'wrote 0x0751=0xA0'), (5, 'watch over'),
             (6, 'restored 0x0751=0x10')])
        # Numbered where they are in the whole mark stream, so the two reads
        # sit side by side, and the block's own last window still says the
        # block ended rather than the capture.
        self.assertIn('window runs to the end of block 1 of 2', out)
        self.assertNotIn('the end of the capture', out)
        self.assertIn('block 1/2: intact', out)
        # And the scoping declined is the capture-level comparison, as it is
        # over any block: a boundary does not turn one block into the day.
        self.assertIn('The other 1 block(s) are not part of it', out)
        self.assertNotIn('consistent with the static prediction', out)

    # The scoping choice, pinned. Boundaries are a new class of mark the
    # procedure asks for; making one mandatory would refuse every capture this
    # tool grades today, which is the one thing the issue did not ask for and
    # the reason these three sets are still here unchanged.
    def test_a_capture_with_no_boundaries_still_grades_as_it_did(self):
        for captures, roles, exit_code in (
                (RUN_CAPTURES, [['control', 'write', 'restore']], 0),
                (MULTI_BLOCK, [['control', 'write', 'restore']] * 2, 0),
                # The void block ends on its write and so has one role
                # fewer, and a boundary is not a restore: giving it one
                # would have made the void check pass over a block that
                # never closed. `fixture_block_ends` is what says the second
                # half of that in the tool's own predicate.
                (BLOCK_CAPTURES,
                 [['control', 'write', 'restore'], ['control', 'write'],
                  ['control', 'write', 'restore']], 1)):
            rc, out, _ = run(*captures)
            self.assertEqual(rc, exit_code, f"{len(roles)} block(s)")
            # The three action roles and no more: nothing here invents a
            # window the capture did not record. Read off `Block.roles`
            # through the same walk `main` does rather than counted in the
            # printed census, which prints each block's roles twice and
            # appends `-- NOT GRADED` to the line of one that fails a check.
            _, _, blocks, _ = as_main_reads(captures)
            self.assertEqual([b.roles for b in blocks], roles)
            # And none of the three boundary labels is in the report at all,
            # quoted so the closing section's own "what this does and does
            # not settle" is not what fails the assertion.
            for boundary in ("'settled'", "'held'", "'watch over'"):
                self.assertNotIn(boundary, out, boundary)
        # `3blocks/`'s void block is still void, which is the one exit code in
        # the three that is not 0 and the one thing a boundary must not have
        # changed: it is still short its restore, and still exit 1.
        self.assertEqual(fixture_block_ends()[1],
                         ('wrote 0x0751=0x00', False))


class EarlyExitTests(unittest.TestCase):
    # The one `#` row this tool reads rather than skips: the one
    # `windows/tools/manual_fan_ctrl_probe.py` writes when a run stops part
    # way through. Every case is over a temp copy of `multi-block/` -- §6's
    # shape, two values, every mark in every capture -- with one row added to
    # one capture, so the only thing that differs between a graded run and a
    # refused one is that row. Two blocks rather than one because the decision
    # is per block and a one-block capture cannot show what it does to the
    # rest of the day.
    ANCHOR = '2026-01-01T12:00:55.000+01:00'  # inside block 1's write window
    CRASHED_TS = '2026-01-01T12:00:57.000+01:00'
    CAPTURE = '2026-01-01-0751-isolation-0700-07ff.csv'

    def crashed(self, tmp, line, anchor=None):
        """`multi-block/`'s three captures, `line` added to one of them."""
        return copies_of(tmp, MULTI_BLOCK,
                         {self.CAPTURE: insert_after(anchor or self.ANCHOR,
                                                      line)})

    # The decision: a row that places is charged to the block whose window it
    # fell in, that block's windows are withheld and the exit code is 1. The
    # block stays *intact* -- the restore is there, the `finally` puts it back
    # whether or not the arm got to its hold -- which is why this case is
    # worth a fixture of its own rather than a line in the void check's case:
    # the void check has nothing to say here, and before this the report said
    # so in the only words it had.
    def test_an_early_exit_row_withholds_the_block_it_falls_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.crashed(tmp, early_exit_row(self.CRASHED_TS))
            # The a0 pair with it, as `test_a_refused_mark_set_is_marked...`
            # does: a withheld block's marker rides on the two file sections'
            # group lines, and that is where a reader of a fold-in meets it.
            rc, out, err = run(*paths, '--wrote', '0xA0',
                               *dumps(*MULTI_A0_DUMPS),
                               '--dump-pair', *MULTI_A0_DUMPS)
        flat = " ".join(out.split())
        self.assertEqual(rc, 1, err)
        # Counted on the read line, which is the last line a run with no MARK
        # rows is refused after.
        self.assertIn('2026-01-01-0751-isolation-0700-07ff.csv: 6 mark(s), '
                      '15 change row(s), 1 early-exit row(s)', out)
        # The census names the kind, so a reader can see at a glance that this
        # is not a mark-set problem, and the block section calls the block
        # intact and withheld anyway: two facts, printed as two.
        self.assertIn('block 1 of 2: value under test 0xA0, roles control, '
                      'write, restore -- NOT GRADED, 1 problem(s): early-exit',
                      census(out))
        self.assertIn('block 1/2: intact', out)
        self.assertIn('NOT GRADED, its windows are not printed', out)
        # The section above the windows: which row, which capture, where it
        # fell and what it said. Whole, and not scoped -- this run grades
        # both blocks, so "whole" is the census's own rule rather than a
        # stretch, and the reason is in the block's own window below.
        self.assertIn('=== early-exit rows (a run that did not reach its '
                      'hold) ===', out)
        self.assertIn('2026-01-01-0751-isolation-0700-07ff.csv '
                      '(1 row(s)):', out)
        self.assertIn("in mark 2/6 ('wrote 0x0751=0xA0') of block 0xA0 "
                      "(block 1 of 2)", flat)
        self.assertIn('manual_fan_ctrl_probe: RuntimeError: observation '
                      'failed mid-run', flat)
        # All three of block 1's windows are withheld -- the block is the unit
        # §3 defines, and the capture cannot say which arms before the cut are
        # still worth reading -- and block 2's are printed as they always were.
        # That last half is what a `--block 0x10` attachment depends on, and
        # it is the half a refusal would have cost.
        self.assertEqual(out.count('block: 0xA0 (block 1 of 2) -- NOT GRADED'),
                         3)
        self.assertEqual(out.count('no watched byte moved in this window'), 3)
        self.assertIn('3 of the 6 window(s) above were not graded', out)
        # And the reason is quoted where the block's own verdict is carried,
        # rather than the mark-set wording, which would send the operator to a
        # console that recorded every mark this block has.
        for section in (dumps_section(out), whole_block(out)):
            self.assertIn("block 0xA0, from the <value> in these files' §6 "
                          "names -- this capture records the run ending "
                          "early inside it, its windows were withheld "
                          "above", section)
        # The block section's note is the early-exit one: a mark set that does
        # hold is not what went wrong here.
        self.assertIn('What it is short is not a mark but the hold the arm '
                      'was to run for', flat)
        self.assertNotIn('A block whose mark set does not hold has no windows',
                         out)

    # The invariant the change could have broken, pinned directly rather than
    # left to the rest of the suite. §6 tells the operator to annotate what
    # they hand in, `read_capture` skips `#` rows for exactly that, and the row
    # is told apart by its opening phrase rather than by being a comment -- so
    # a hand row has to reach neither the new reader nor the exit code.
    def test_a_hand_annotated_capture_grades_exactly_as_it_did(self):
        note = '"# annotated by hand: dock attached, laptop on a desk"'
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.crashed(tmp, note)
            # The row is in the file it was written into, before anything is
            # run over it: an assertion about a row that was never written
            # would pass for the wrong reason.
            self.assertIn(note, Path(paths[0]).read_text(encoding='utf-8'))
            rc, out, _ = run(*paths)
            rc_plain, plain, _ = run(*MULTI_BLOCK)
        self.assertEqual(rc, 0)
        # Byte for byte the same report, the copies' directory swapped back for
        # the fixture's -- the strongest form of the claim, and it covers the
        # read line, the census, all six windows and the exit code at once.
        self.assertEqual(out.replace(str(tmp), str(MULTI)), plain)
        self.assertEqual(rc_plain, rc)
        # Named rather than implied: the hand row is in the file and in no
        # section of the report.
        self.assertNotIn('annotated by hand', out)
        self.assertNotIn('early-exit', out)

    # The two shapes a row this cannot place takes, each of which used to be a
    # green run. Both are refusals for the whole invocation rather than a
    # window or a block: a row that says where it stopped and cannot be said
    # to say it leaves every window's length uncertifiable, which is
    # `unplaceable_marks`'s argument for a label the parse cannot read.
    def test_a_row_this_cannot_place_refuses_the_run(self):
        cases = (
            # No timestamp, the shape a capture written before the probe
            # stamped its row has. The reason is quoted back rather than
            # discarded, so the operator can see which row of which file.
            (f"{grade.EARLY_EXIT_TAG} when the fan stalled,"
             "manual_fan_ctrl_probe: RuntimeError: observation failed "
             "mid-run",
             'the row carries no timestamp this can read'),
            # A timestamp before the first mark: there is no window for the row
            # to have cut short, and it is placed by timestamp rather than by
            # where in the file it was written -- which is why a row written
            # mid-capture and stamped at 12:00:05 lands outside every window.
            (early_exit_row('2026-01-01T12:00:05.000+01:00'),
             'no mark in the capture is at or before it'),
        )
        for line, why in cases:
            with tempfile.TemporaryDirectory() as tmp:
                paths = self.crashed(tmp, line)
                rc, out, err = run(*paths)
            flat = " ".join(err.split())
            self.assertEqual(rc, 1, why)
            # The section still prints whole, so the row is visible on the run
            # that refuses it, and says it was not placed rather than naming a
            # window it was not placed in.
            self.assertIn('=== early-exit rows (a run that did not reach its '
                          'hold) ===', out, why)
            self.assertIn(f'NOT PLACED -- {why}', " ".join(out.split()), why)
            # The refusal, and it says what is missing rather than implying
            # something was found and lost.
            self.assertIn('A row saying a run ended early has to be placed '
                          'against the window it cut short', flat, why)
            self.assertIn(why, flat, why)
            # And nothing is graded: not one window, of either block.
            self.assertNotIn('--- mark ', out, why)
            self.assertNotIn('window delta', out, why)
            self.assertNotIn('None of the §4.1-§4.3 bytes moved', out, why)
        # A row with a readable timestamp but no reason on it is placed rather
        # than refused -- the timestamp is the thing this can act on -- and the
        # report says the row carries no reason rather than quoting nothing as
        # though it had.
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.crashed(tmp, f"{grade.EARLY_EXIT_TAG} "
                                      f"{self.CRASHED_TS}")
            rc, out, _ = run(*paths)
        self.assertEqual(rc, 1)
        self.assertIn('the row records no reason', " ".join(out.split()))

    # The count is on the read line rather than in the section, because there
    # is a path where the section never prints: a capture with no MARK rows at
    # all is refused before anything else this tool says about a capture, and
    # the row is then the only record that a run stopped. It has to be visible
    # on that path too.
    def test_a_capture_with_no_marks_still_names_its_early_exit_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'no-marks.csv'
            path.write_text('ts,addr,old,new\n'
                            + early_exit_row(self.CRASHED_TS) + '\n',
                            encoding='utf-8')
            rc, out, err = run(str(path))
        self.assertEqual(rc, 1)
        self.assertIn('0 mark(s), 0 change row(s), 1 early-exit row(s)', out)
        self.assertIn('no MARK rows in these captures', err)
        # The one refusal that fired is the one about the marks: there is
        # nothing to place the row against, which is a different fact from the
        # one the early-exit refusal states.
        self.assertNotIn('cannot be placed', err)
        self.assertNotIn('=== early-exit rows', out)

    # One capture is §3's single-tool form, and the probe's own `--csv` output
    # is one file. The cross-console checks need a second console to have
    # anything to disagree with; this one needs none, exactly as the census's
    # "one capture" notice says for those.
    def test_the_check_does_not_wait_for_a_second_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = copies_of(tmp, (MULTI_BLOCK[0],),
                              {self.CAPTURE: insert_after(
                                  self.ANCHOR,
                                  early_exit_row(self.CRASHED_TS))})
            rc, out, _ = run(*paths)
        self.assertEqual(rc, 1)
        self.assertIn('one capture: the cross-console checks did not run', out)
        self.assertIn('1 early-exit row(s)', out)
        self.assertIn('NOT GRADED, 1 problem(s): early-exit', census(out))
        self.assertEqual(out.count('block: 0xA0 (block 1 of 2) -- NOT GRADED'),
                         3)
        self.assertEqual(out.count('no watched byte moved in this window'), 3)
        # And without the row the same one-capture run grades, so the refusal
        # above is the row's and not the shape's.
        rc, out, _ = run(MULTI_BLOCK[0])
        self.assertEqual(rc, 0)
        self.assertNotIn('early-exit', out)

    # A `--block` run is graded by its own block, so a day in which another
    # value's block crashed still attaches: §6 runs one `--block` per value,
    # and refusing all three over one bad value would be the opposite of what
    # that command line is for. The section prints whole either way.
    def test_a_block_run_of_a_good_value_passes_over_a_day_that_crashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.crashed(tmp, early_exit_row(self.CRASHED_TS))
            rc, out, _ = run(*paths, '--block', '0x10')
        self.assertEqual(rc, 0)
        self.assertIn('=== block 2 of 2, value under test 0x10, 3 window(s) '
                      'in it ===', out)
        self.assertEqual(out.count('no watched byte moved in this window'), 3)
        # The crash is named anyway, and the block it fell in is named as not
        # selected rather than graded: the census's own scoping, which is why
        # the section's exit-code sentence is scoped with it.
        self.assertIn('in mark 2/6 (\'wrote 0x0751=0xA0\') of block 0xA0 '
                      '(block 1 of 2)', " ".join(out.split()))
        self.assertIn('block 1 of 2: value under test 0xA0, roles control, '
                      'write, restore -- not selected in this run',
                      census(out))
        self.assertIn('still exits 0 over a day in which another value did',
                      " ".join(out.split()))
        # Nothing of *this* block's was withheld, so no banner names a reason.
        self.assertNotIn('were not graded', out)
        self.assertNotIn('NOT GRADED', out)


class ExistingMarkLabelTests(unittest.TestCase):
    """`existing_mark_labels`: what a --csv holds before a watcher appends.

    #548. The reader `windows/tools/ec_watch.py` asks at startup, so it lives
    here rather than in the prompt: the mark row's shape is the grader's, and
    a second copy in the tool is the drift `load_label_vocab` exists to stop.

    It is a preflight, not a reader, and every case below is about the
    difference. `read_capture` may raise -- a short row, a timestamp it cannot
    parse, a byte the encoding cannot decode -- because a capture that does not
    load is a capture that gets told so. This one may not, because the file it
    is pointed at is one a run is about to append to, and refusing to open it
    would lose the one warning that says what is already in it. So the
    timestamp is the text it was written as, a truncated mark row comes back
    with an empty label, a change row is not parsed at all, and an undecodable
    byte comes back as U+FFFD in a label rather than ending the run.

    `existing_mark_findings` (#718) is the same preflight seen from both
    sides: the strict reader's verdict beside the lenient one's, so the notice
    can name which of a file's rows the grader will refuse it over rather than
    listing them all as equally fine. The contract above is its contract -- it
    is the reason the notice is printed at all -- so the cases below cover
    both, and none of them is about which of the two raises.

    It is also one `open()` of the file and not two (#749). A `--csv` under
    `--label-vocab` is appended to by three watchers on purpose, so a second
    read is a second moment and the two sections of one notice could describe
    two different files -- a mark named in the placement section that the
    section above it does not list. The cases that follow stand a watcher in
    the middle of the read and assert what the notice says afterwards; the
    open count is asserted rather than the effect, because the effect is only
    visible when the race happens to land and a count is true every time.
    """

    # One of each row kind, so "which rows are skipped" and "which are marks"
    # are separable questions rather than one. The `#` and the blank are the
    # two `read_capture` skips that a hand-annotated capture relies on, and
    # every committed fixture under testdata/ opens with a `#` block.
    ROWS = [
        '# 0751 isolation, 0xA0 block',
        'ts,addr,old,new',
        '',
        '2026-01-01T12:00:05.000+01:00,0x0701,0x00,0x11',
        '2026-01-01T12:00:00.000+01:00,MARK,,wrote 0x0751=0xA0',
        '# the operator noted the settle here',
        '2026-01-01T12:00:30.000+01:00,MARK,,settled',
    ]

    def capture(self, rows, tmp):
        path = Path(tmp) / 'capture.csv'
        path.write_text(''.join(row + '\n' for row in rows))
        return str(path)

    def test_the_skip_rule_is_read_captures_and_only_marks_come_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(self.ROWS, tmp)
            self.assertEqual(grade.existing_mark_labels(path),
                             [('2026-01-01T12:00:00.000+01:00',
                               'wrote 0x0751=0xA0'),
                              ('2026-01-01T12:00:30.000+01:00', 'settled')])
        # The change row in the middle of the fixture is the case that fails
        # if the reader keeps every row rather than the mark ones, and the
        # `#` and the header are what fail it if the skip rule drifts from
        # `read_capture`'s.

    def test_a_row_read_capture_would_raise_on_comes_back_as_a_label(self):
        # A hand-edited timestamp, and a mark row truncated to three fields:
        # `read_capture` raises on both (its short-row check for the first,
        # `parse_ts` for the other) and neither stops this. The preflight has
        # one job -- say what is already in the file -- and a file it cannot
        # open is a file the operator is not warned about.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(['2026-01-01 12:00,MARK,,held',
                                 '2026-01-01T12:01:00.000+01:00,MARK,',
                                 '2026-01-01T12:02:00.000+01:00,MARK,,watch over'],
                                tmp)
            self.assertEqual(grade.existing_mark_labels(path),
                             [('2026-01-01 12:00', 'held'),
                              ('2026-01-01T12:01:00.000+01:00', ''),
                              ('2026-01-01T12:02:00.000+01:00', 'watch over')])
            # And the same file really is one `read_capture` refuses, so the
            # leniency is a difference and not a row shape that never occurs.
            with self.assertRaises(ValueError):
                grade.read_capture(path)

    def test_a_byte_the_encoding_cannot_read_does_not_stop_the_preflight(self):
        # The other thing the file can hold that `read_capture` refuses and
        # this must not: bytes. The format declares `utf-8` and every writer
        # of it declares the same, but `CsvSink` appends to a path without
        # ever decoding it, so a file written before the codec was declared
        # or annotated in an editor that saved something else is still here
        # at startup -- 0xE9, as latin-1 and cp1252 both write for `café`,
        # and as a capture cannot hold. Under the declared codec and with
        # iteration lazy, the raise comes out of the loop rather than the
        # open, and it came out of the startup path: the run died before it
        # began, on exactly the foreign capture the docstring says this
        # exists to tolerate, where appending had worked.
        #
        # The label comes back with U+FFFD where the byte was, and now that is
        # the only answer rather than one of two: the job is to name the row
        # so the operator can recognise it, not to reproduce it, and the
        # grading still refuses the same file over the same byte.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'capture.csv'
            path.write_bytes(b'ts,addr,old,new\n'
                             b'2026-01-01T12:00:00.000+01:00,MARK,,caf\xe9\n'
                             b'2026-01-01T12:00:30.000+01:00,MARK,,settled\n')
            marks = grade.existing_mark_labels(str(path))
        # Both marks, not just the one before the bad byte: laziness is what
        # made this a startup crash rather than a truncated notice, and a
        # reader that swallowed the decode error to survive it would swallow
        # the rest of the file with it.
        self.assertEqual([ts for ts, _ in marks],
                         ['2026-01-01T12:00:00.000+01:00',
                          '2026-01-01T12:00:30.000+01:00'])
        # The prefix survives and the byte does not, on every interpreter --
        # which is what `errors="replace"` is for, and what the declared
        # encoding did not take away.
        self.assertEqual(marks[0][1], 'caf\ufffd')
        self.assertEqual(marks[1][1], 'settled')

    def test_the_strict_readers_verdict_splits_the_marks_a_file_holds(self):
        # The issue's own shape, at the size it describes: six good marks and
        # one half-written row. `existing_mark_labels` returns all seven as
        # labels, which is right for what it was asked and cannot say which of
        # them `read_capture` will refuse the file over. The strict reader's
        # verdict is the split: six the grader reads, one it raises on.
        rows = ['ts,addr,old,new']
        rows += [f'2026-01-01T12:0{n}:00.000+01:00,MARK,,wrote 0x0751=0xA0'
                 for n in range(6)]
        rows.append('2026-01-01T12:06:00.000+01:00,MARK,')
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(rows, tmp)
            accepted, refused, unplaceable = grade.existing_mark_findings(path)
            # The lenient reader still names all seven, unchanged: this is
            # added beside it, not through it.
            self.assertEqual(len(grade.existing_mark_labels(path)), 7)
        self.assertEqual(len(accepted), 6)
        self.assertEqual(len(refused), 1)
        # The row is named as the grader parsed it, so the operator can find it
        # in the file rather than being told a count -- and the reason quotes
        # the row back, which is the short-row check's own message and is
        # the error the grading will raise. Asserted on the row rather than
        # on the word "short": how the reader words it is the reader's
        # business, and a reword must not read here as the notice
        # disagreeing with it.
        self.assertEqual(refused[0][0],
                         ['2026-01-01T12:06:00.000+01:00', 'MARK', ''])
        self.assertIn(repr(refused[0][0]), refused[0][1])
        # A refused file is already refused whole, so there is no second
        # verdict to add and the list says so by being empty.
        self.assertEqual(unplaceable, [])

    def test_a_hand_edited_timestamp_is_a_refused_row_and_is_named(self):
        # Free text rather than a loose ISO stamp, and deliberately: this
        # suite's `:3399` fixture leans on the *short row* for its
        # `assertRaises`, so its timestamp is not a raising one under the
        # interpreter the gate runs. `datetime.fromisoformat` was widened in
        # 3.11 and reads `'2026-01-01 12:00'` without complaint, so a fixture
        # copied from there would pass for the wrong reason -- a test that
        # looks like it covers a bad timestamp and is really covering the
        # short row a second time. A word is not an ISO 8601 stamp in any
        # version.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(['ts,addr,old,new',
                                 '2026-01-01T12:00:00.000+01:00,MARK,,settled',
                                 'when i clicked,MARK,,held'], tmp)
            accepted, refused, _ = grade.existing_mark_findings(path)
            with self.assertRaises(ValueError) as caught:
                grade.read_capture(path)
        self.assertEqual([ts for ts, _ in accepted],
                         ['2026-01-01T12:00:00.000+01:00'])
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0][0],
                         ['when i clicked', 'MARK', '', 'held'])
        # `parse_ts`'s own message, which is the exception `read_capture`
        # raised and the reason this function quotes for it.
        self.assertEqual(refused[0][1], str(caught.exception))
        self.assertIn('when i clicked', refused[0][1])

    def test_the_refusal_reasons_are_read_captures_own(self):
        # The anti-drift guard, and the one that makes the per-row conditions
        # in `partition_capture_rows` -- reached here through
        # `existing_mark_findings`, which reads once and delegates -- safe
        # rather than a second rule. Over every fixture `read_capture`
        # refuses, the first reason this returns is the exception
        # `read_capture` itself raised, byte for byte. Tighten that check or
        # widen `parse_ts` and this fails -- rather than the notice going on
        # explaining a refusal the grading no longer makes.
        #
        # The *order* of those checks is pinned by the last fixture below, not
        # by that first reason: `existing_mark_findings` replaces the first
        # row's reason with `read_capture`'s own exception, so no fixture whose
        # only bad row is the first one can see which check ran first. The
        # order *among* the three `int()` calls is not pinned at all -- every
        # fixture that reaches them has exactly one bad field -- so nothing
        # here claims it.
        fixtures = {
            # The short row, the one whose own message names the row, so it
            # is the one that can be checked to be the same row.
            'short row': ['ts,addr,old,new',
                          '2026-01-01T12:00:00.000+01:00,MARK,,settled',
                          '2026-01-01T12:01:00.000+01:00,MARK,'],
            # `parse_ts`, on a timestamp an operator edited.
            'timestamp': ['ts,addr,old,new',
                          'when i clicked,MARK,,held'],
            # The `int(addr, 16)` of a change row, outside the two reasons the
            # issue named: a mark row is not the only row that stops the
            # grader, so the notice cannot be only about mark rows.
            'change address': ['ts,addr,old,new',
                               '2026-01-01T12:00:05.000+01:00,0xzz,0x00,0x11'],
            'change old': ['ts,addr,old,new',
                           '2026-01-01T12:00:05.000+01:00,0x0701,old,0x11'],
            'change new': ['ts,addr,old,new',
                           '2026-01-01T12:00:05.000+01:00,0x0701,0x00,new'],
            # Two bad rows, so the partition has a row `read_capture` never
            # reached to name and the first is still the one it raised on.
            'two bad rows': ['ts,addr,old,new',
                             '2026-01-01T12:01:00.000+01:00,MARK,',
                             'when i clicked,MARK,,held'],
            # The order of the checks, on the one input where it is
            # observable: a change row bad in *both* ways, which
            # `read_capture` refuses for the timestamp because it reads the
            # timestamp before the hex. It is deliberately not the first bad
            # row -- `existing_mark_findings` replaces the first row's reason
            # with `read_capture`'s own exception, so a first-row fixture
            # could not see the partition's ordering at all.
            'change row bad in both ways': [
                'ts,addr,old,new',
                '2026-01-01T12:01:00.000+01:00,MARK,',
                'when i clicked,0xzz,0x00,0x11'],
        }
        for name, rows in fixtures.items():
            with self.subTest(fixture=name), \
                 tempfile.TemporaryDirectory() as tmp:
                path = self.capture(rows, tmp)
                with self.assertRaises(ValueError) as caught:
                    grade.read_capture(path)
                _, refused, _ = grade.existing_mark_findings(path)
                self.assertTrue(refused, name)
                self.assertEqual(refused[0][1], str(caught.exception))
                self.assertIsNotNone(refused[0][0])
                if name == 'short row':
                    # The short-row check is the one that puts the row in its
                    # own message, and that is what makes the first entry
                    # checkable rather than only quotable: the row named here
                    # has to be the row the reader stopped on, not merely a
                    # row it dislikes.
                    self.assertIn(repr(refused[0][0]), str(caught.exception))
                    self.assertEqual(len(refused), 1)
                if name == 'two bad rows':
                    # Both, and the reader stopped at the first -- so the
                    # second is the reason this names every one of them.
                    self.assertEqual(len(refused), 2)
                    self.assertEqual(refused[1][0],
                                     ['when i clicked', 'MARK', '', 'held'])
                if name == 'change row bad in both ways':
                    # The order, asserted on the one row whose reason is the
                    # partition's own rather than the exception text pasted
                    # over the first. Reading the hex before the timestamp is
                    # the opposite of `read_capture`'s order and would name
                    # the wrong one of two real reasons for the row.
                    self.assertEqual(len(refused), 2)
                    self.assertEqual(
                        refused[1][0],
                        ['when i clicked', '0xzz', '0x00', '0x11'])
                    self.assertIn('timestamp', refused[1][1])

    def test_the_shape_agrees_across_all_four_readers(self):
        # The half of the guard that is not the reasons. The test above holds
        # four of them, their order and the first one byte for byte, and says
        # nothing about *which rows are data rows at all* -- every fixture it
        # uses opens with a plain `ts,addr,old,new`, so the header case is
        # pinned only as a side effect, and the one fixture that puts a `#`
        # row and a blank through the partition
        # (`test_the_preflight_does_not_raise_on_any_of_them`'s 'only a
        # comment') asserts `assertIsInstance(..., tuple)`, which is that
        # nothing escapes and not what came back. A change to the skip rule
        # on any of the three readers is therefore invisible here, and the
        # failure it makes is the one #718 set out to remove: the notice
        # naming a row the grading treats differently, in either direction.
        #
        # One fixture carrying all three at once, so no reader is checked
        # against a file that happens not to exercise the rule, plus a row
        # that is none of the three -- the early-exit phrase, which the other
        # three drop and `read_early_exits` exists to keep.
        crash = '2026-01-01T12:01:00.000+01:00'
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(
                self.ROWS + [early_exit_row(crash, 'the fan stalled')], tmp)
            marks, changes = grade.read_capture(path)
            labels = grade.existing_mark_labels(path)
            accepted, refused = grade.refused_capture_rows(path)
            exits = grade.read_early_exits(path)
        # Written out rather than compared with `len`: the order is what a
        # reader is looking down, and a skip that took one of the two marks
        # would keep the count and lose the position.
        self.assertEqual(labels,
                         [('2026-01-01T12:00:00.000+01:00',
                           'wrote 0x0751=0xA0'),
                          ('2026-01-01T12:00:30.000+01:00', 'settled')])
        # The strict reader's marks are the lenient reader's pairs, in order:
        # one read as objects and one as the text they were written as, and
        # the `#` rows, the blank and the header are in neither.
        self.assertEqual([m.label for m in marks],
                         [label for _, label in labels])
        self.assertEqual([m.ts for m in marks],
                         [grade.parse_ts(ts) for ts, _ in labels])
        self.assertEqual([(c.addr, c.old, c.new) for c in changes],
                         [(0x0701, 0x00, 0x11)])
        # And the partition takes the same mark rows on a file the strict
        # reader accepts whole -- the equality, not a count, because a
        # partition that took one row too few would still hold the count.
        self.assertEqual(accepted, labels)
        self.assertEqual(refused, [])
        # The early-exit row reaches the one reader it is for, and nothing
        # else: it is a `#` row, so the other three cannot see it even on a
        # file that holds it, and `read_early_exits` is here because of that
        # rather than in spite of it.
        self.assertEqual([e.ts for e in exits], [grade.parse_ts(crash)])
        self.assertIn('the fan stalled', exits[0].reason)
        # And the hand annotation is in the file and in no return value. Named
        # rather than counted: a reader that quietly kept it as a data row
        # would not raise, it would grade.
        self.assertNotIn('the operator noted',
                         ' '.join([m.label for m in marks]
                                  + [f'{ts}{label}' for ts, label in labels]
                                  + [f'{ts}{new}' for ts, new in accepted]
                                  + [e.reason for e in exits]))

    def test_on_a_file_the_strict_reader_refuses_the_partition_names_every_row(
            self):
        # The reader-side half is the first-reason equality above. This is the
        # other half, and it is the only way it can be said mechanically:
        # `read_capture` stops at the first row it cannot grade and returns
        # nothing at all on a file like this, so "the partition equals
        # `read_capture`'s own view" has to be written out here rather than
        # compared against a call that raised.
        #
        # Expected rows written literally, not derived from the module: a
        # partition and a reader that agreed on the wrong rows would pass any
        # comparison between themselves. A `#` row, a blank, the header, one
        # good mark and one row neither can read -- every row kind the skip
        # rule decides, with a verdict for each.
        good = ('2026-01-01T12:00:00.000+01:00', 'MARK', '', 'settled')
        short = ['2026-01-01T12:01:00.000+01:00', 'MARK', '']
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(['# a hand annotation', 'ts,addr,old,new', '',
                                 ','.join(good), ','.join(short)], tmp)
            with self.assertRaises(ValueError) as caught:
                grade.read_capture(path)
            accepted, refused = grade.refused_capture_rows(path)
            labels = grade.existing_mark_labels(path)
        # The good mark, and only the good mark. The `#` row, the blank and
        # the header are in neither list: that is the whole of the shape, and
        # it is asserted here rather than inferred from the reader's silence.
        self.assertEqual(accepted, [good[:1] + good[3:]])
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0][0], short)
        # The row, not the wording: how the partition words a refusal is its
        # business, and the existing case above says so. What is checked is
        # that the row it refused is the row the reader named in the exception
        # it raised -- a partition that found a *different* bad row, or none,
        # would pass any assertion comparing the reason text alone.
        self.assertIn(repr(refused[0][0]), str(caught.exception))
        # The lenient reader still says what the file holds, both mark rows,
        # with the short one coming back under its timestamp and an empty
        # label rather than as a `ValueError` -- which is the whole of why the
        # strict one can be strict at all.
        self.assertEqual(labels, [(good[0], 'settled'), (short[0], '')])

    def test_a_byte_order_mark_does_not_turn_the_header_into_a_bad_row(self):
        # The shape's own case, and the one this tree had no answer for. With
        # `EF BB BF` at offset 0 the header's first field was not `ts`, so the
        # header was a data row: `parse_ts` raised on a timestamp no reader
        # can parse, the partition named the header -- a first field of
        # U+FEFF followed by `ts` -- as the row at fault, and the notice's
        # remedy -- fix or delete the rows above -- pointed at the row
        # carrying the column names. The anti-drift guard did its job
        # throughout; the diagnosis was invented, because nothing owned the
        # shape of a row.
        #
        # **Superseded, and the correction is the point of this case.** The
        # version of this test written alongside the shape asserted that
        # `read_capture` *grades* a capture carrying a BOM -- one mark, no
        # changes, nothing refused. Issue #748 then declared the format
        # utf-8 with no BOM at every reader and writer (#756), which is a
        # decision about what a capture is rather than about how a row is
        # read, and it puts a byte-order mark outside the format: the strict
        # reader now refuses such a file whole and by name. Left in place
        # that expectation would have un-declared the codec, so it is
        # replaced here rather than quietly dropped. What survives of it --
        # and what the rest of this case holds -- is the part about the
        # *other three* readers, which still have to read the file far enough
        # to say what it holds, and which must not turn a header into a row
        # with a bad field in it.
        #
        # Whether a Windows tool writes one is a prediction, not a case
        # measured here, and the fixture is written as bytes on purpose: the
        # point of the test is the three bytes, and a fixture that typed a BOM
        # as a character would be testing a different thing on an interpreter
        # that opened the file some other way.
        mark = b'2026-01-01T12:00:00.000+01:00,MARK,,settled\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bom.csv'
            path.write_bytes(b'\xef\xbb\xbf' + b'ts,addr,old,new\n' + mark)
            # The strict reader's own verdict, which is what the grading is:
            # a refusal of the file, and no rows at all. (The message is
            # held by the sibling case below this one; what is asserted here
            # is only that it raises rather than grading the header.)
            with self.assertRaises(ValueError):
                grade.read_capture(str(path))
            accepted, refused, unplaceable = grade.existing_mark_findings(
                str(path))
            lenient = grade.existing_mark_labels(str(path))
            # The control, in the same case: the identical fixture written the
            # same way with the three bytes absent. Without it, a case that
            # passed for the wrong reason -- a reader that had stopped
            # parsing the header altogether, say -- would look the same.
            plain = Path(tmp) / 'plain.csv'
            plain.write_bytes(b'ts,addr,old,new\n' + mark)
            plain_marks, plain_changes = grade.read_capture(str(plain))
            plain_accepted, plain_refused, _ = grade.existing_mark_findings(
                str(plain))
        # The control is what the pre-#748 version of this case compared
        # against, and it has to still hold: the strict reader takes the mark
        # and nothing else, and grades the file whole.
        self.assertEqual([m.label for m in plain_marks], ['settled'])
        self.assertEqual(plain_changes, [])
        # What the three preflights make of the same file. The mark is in all
        # three the way it is in the control, because the shape retires the
        # byte-order mark off the first field in the shared stream -- it
        # cannot be strict in one reader and lenient in another.
        self.assertEqual(accepted, plain_accepted)
        self.assertEqual([ts for ts, _ in accepted],
                         ['2026-01-01T12:00:00.000+01:00'])
        self.assertEqual(lenient, [('2026-01-01T12:00:00.000+01:00',
                                    'settled')])
        # The notice's difference from the control is exactly one refusal,
        # it is the file's rather than a row's, and nothing is refused over
        # the header. `None` is what says "the file", and it is also what
        # keeps the notice from offering the operator the row carrying the
        # column names to delete.
        self.assertEqual(len(refused), 1)
        self.assertIsNone(refused[0][0])
        self.assertNotIn('not hex', refused[0][1])
        self.assertEqual(refused[0][1], refused[0][1].strip())
        self.assertEqual(len(plain_refused), 0)
        self.assertEqual(unplaceable, [])
        # And the header is named nowhere, in either list: the remedy the
        # notice would print is not "delete the row above".
        self.assertNotIn([grade.BOM + 'ts', 'addr', 'old', 'new'],
                         [row for row, _ in refused])
        self.assertNotIn('ts,addr,old,new', refused[0][1])
        # What the strip is standing in for, asserted so this case cannot go
        # quiet: a timestamp opening with U+FEFF is not one this can read.
        # If `parse_ts` ever learned to, the fixture would pass for the wrong
        # reason and the reason would be gone.
        self.assertRaises(ValueError, grade.parse_ts, grade.BOM + 'ts')

    def test_a_change_row_bad_in_two_hex_fields_names_the_earlier_one(self):
        # The gap the anti-drift test's own comment records: the order *among*
        # the three `int()` calls "is not pinned at all", because every
        # fixture reaching them has exactly one bad field. So a partition that
        # named the *new* of a row whose `old` is also not hex would pass that
        # test -- and the operator would be sent to the wrong column of the
        # wrong row.
        #
        # Not the first bad row, for the reason the sibling fixture gives:
        # `existing_mark_findings` pastes `read_capture`'s own exception over
        # the first reason, so a first-row fixture could not see the
        # partition's own ordering at all. This one goes through
        # `refused_capture_rows` directly, and checks the reason on the row
        # the reader never reached.
        both = ['2026-01-01T12:02:00.000+01:00', '0x0701', 'not hex', 'nor is '
                'this']
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(['ts,addr,old,new',
                                 '2026-01-01T12:01:00.000+01:00,MARK,',
                                 ','.join(both)], tmp)
            with self.assertRaises(ValueError):
                grade.read_capture(path)
            accepted, refused = grade.refused_capture_rows(path)
        self.assertEqual(len(refused), 2)
        self.assertEqual(refused[1][0], both)
        # `old`, because `Change(parse_ts(ts), int(addr, 16), int(old, 16),
        # int(new, 16), path)` evaluates left to right and this row's address
        # is the one that parses.
        self.assertIn('the old of a change row is not hex', refused[1][1])
        self.assertNotIn('the new of a change row', refused[1][1])

    def test_a_malformed_change_row_is_a_refused_row_too(self):
        # The widening, pinned on its own so it cannot go quietly: a change
        # row is not a mark and holds no label, but `int(addr, 16)` is in
        # `read_capture` and a file with one in it is refused whole, so a
        # notice that named only the two reasons the issue listed would report
        # a file as checked when the grading stops on it.
        good = '2026-01-01T12:00:00.000+01:00,0x0701,0x00,0x11'
        rows = ['ts,addr,old,new', good,
                '2026-01-01T12:00:05.000+01:00,0xzz,0x00,0x11',
                '2026-01-01T12:00:06.000+01:00,0x0701,old,0x11',
                '2026-01-01T12:00:07.000+01:00,0x0701,0x00,new']
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(rows, tmp)
            accepted, refused, _ = grade.existing_mark_findings(path)
            with self.assertRaises(ValueError) as caught:
                grade.read_capture(path)
        # No marks in the fixture at all, so `accepted` is empty and the whole
        # of the notice would be the refusal list.
        self.assertEqual(accepted, [])
        self.assertEqual(len(refused), 3)
        # The first one is `read_capture`'s own exception, verbatim, and that
        # is what it says: `int()` names the value it choked on and not which
        # of the three fields it was reading. The row beside it is the other
        # half, and between them the operator has the field -- here the
        # address, the only one of the three whose value is not a plain hex
        # literal and so the only one the row itself makes obvious.
        self.assertEqual(refused[0][1], str(caught.exception))
        self.assertEqual(refused[0][0][1], '0xzz')
        # The rows `read_capture` never reached are named per row, and each
        # names the field `read_capture`'s tuple unpack gave that name to --
        # in the order `read_capture` evaluates them, so a row bad in two
        # fields is refused for the earlier one.
        for (row, reason), field, value in zip(refused[1:],
                                               ['old', 'new'],
                                               ['old', 'new']):
            self.assertIn(f'the {field} of a change row is not hex', reason)
            self.assertIn(repr(value), reason)
            self.assertNotEqual(row[0], 'ts')
        # A well-formed change row is in neither list: it is not a mark, and it
        # is not what stops the grader.
        self.assertNotIn(good.split(','), [row for row, _ in refused])

    def test_an_unplaceable_label_is_reported_from_the_graders_own_verdict(self):
        # The label side, and the two halves of its calibration. A garbage
        # label is reported with `unplaceable_marks`' own message -- asked of
        # the module rather than spelled here, so a reworded message fails
        # this rather than passing a stale string. And a `settled`/`garbage`
        # pair inside one merge window is *not* reported, because
        # `parse_mark` reads the first part that matches and `settled` places
        # the whole group; a notice that said the second console's label was
        # unreadable would be false about it.
        with tempfile.TemporaryDirectory() as tmp:
            alone = self.capture(['ts,addr,old,new',
                                  '2026-01-01T12:00:00.000+01:00,MARK,,'
                                  'garbage label'], tmp)
            accepted, refused, unplaceable = grade.existing_mark_findings(alone)
            # The window `unplaceable_marks` keys on, so the message below is
            # the module's own over the module's own marks.
            marks, _ = grade.read_capture(alone)
            _, unplaced = grade.assign_blocks(grade.coalesce_marks(marks))
            expected = [said for said
                        in grade.unplaceable_marks(unplaced).values()
                        for said in said]
            # And the calibration case: same garbage label, but not leading
            # its group. 2 s apart, inside `MARK_MERGE_SECONDS`.
            led = self.capture(['ts,addr,old,new',
                                '2026-01-01T12:00:00.000+01:00,MARK,,settled',
                                '2026-01-01T12:00:02.000+01:00,MARK,,'
                                'garbage label'], tmp)
            merged = grade.existing_mark_findings(led)
        self.assertEqual(len(unplaceable), 1)
        self.assertEqual(len(expected), 1)
        self.assertEqual(unplaceable[0][2], expected[0])
        self.assertIn("'garbage label'", unplaceable[0][2])
        self.assertEqual(unplaceable[0][1], 'garbage label')
        self.assertEqual(refused, [])
        self.assertEqual([ts for ts, _ in accepted],
                         ['2026-01-01T12:00:00.000+01:00'])
        # Both marks are named as accepted -- the file is readable and this run
        # is appending after both -- and neither group is reported unplaceable.
        self.assertEqual([ts for ts, _ in merged[0]],
                         ['2026-01-01T12:00:00.000+01:00',
                          '2026-01-01T12:00:02.000+01:00'])
        self.assertEqual((merged[1], merged[2]), ([], []))

    def test_the_preflight_does_not_raise_on_any_of_them(self):
        # `existing_mark_labels`' docstring argues for this and the whole
        # notice rests on it: the file a run is about to append to has to be
        # nameable whatever is in it, or the one warning that says what is
        # already there is the one thing lost. Every hostile fixture above,
        # through both readers.
        hostile = {
            'short row': ['ts,addr,old,new', '2026-01-01T12:00:00.000+01:00,MARK,'],
            'timestamp': ['ts,addr,old,new', 'when i clicked,MARK,,held'],
            'change address': ['ts,addr,old,new',
                               '2026-01-01T12:00:05.000+01:00,0xzz,0x00,0x11'],
            'change old': ['ts,addr,old,new',
                           '2026-01-01T12:00:05.000+01:00,0x0701,old,0x11'],
            'change new': ['ts,addr,old,new',
                           '2026-01-01T12:00:05.000+01:00,0x0701,0x00,new'],
            'two bad rows': ['ts,addr,old,new',
                             '2026-01-01T12:01:00.000+01:00,MARK,',
                             'when i clicked,MARK,,held'],
            'good garbage': ['ts,addr,old,new',
                             '2026-01-01T12:00:00.000+01:00,MARK,,garbage label'],
            'only a comment': ['# a note', ''],
            'header only': ['ts,addr,old,new'],
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, rows in hostile.items():
                with self.subTest(fixture=name):
                    path = self.capture(rows, tmp)
                    # Both readers, and no assertion on what they return: the
                    # property is that nothing escapes.
                    self.assertIsInstance(grade.existing_mark_labels(path), list)
                    self.assertIsInstance(
                        grade.existing_mark_findings(path), tuple)
            # And the byte, which is a refusal of the whole file rather than
            # of a row, and so takes the other branch entirely.
            path = Path(tmp) / 'latin1.csv'
            path.write_bytes(b'ts,addr,old,new\n'
                             b'2026-01-01T12:00:00.000+01:00,MARK,,caf\xe9\n')
            self.assertEqual(len(grade.existing_mark_labels(str(path))), 1)
            self.assertEqual(
                len(grade.existing_mark_findings(str(path))[0]), 1)

    def test_a_byte_this_python_cannot_decode_reports_the_verdict_it_observed(self):
        # The encoding question, and it no longer has two answers. `read_capture`
        # declares `utf-8`, so the 0xE9 raises on every interpreter that runs
        # this -- not under the gate's UTF-8 and not under a box whose default
        # reads the byte. The notice reports the verdict it observed, which is
        # now a property of the format rather than of the reader: a notice
        # that claimed a decode failure the grading would not have hit is
        # still the one thing this must never do, and a notice that stayed
        # silent on a file the grading *will* hit is the same failure.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'capture.csv'
            path.write_bytes(b'ts,addr,old,new\n'
                             b'2026-01-01T12:00:00.000+01:00,MARK,,caf\xe9\n'
                             b'2026-01-01T12:00:30.000+01:00,MARK,,settled\n')
            accepted, refused, unplaceable = grade.existing_mark_findings(str(path))
            raised = None
            try:
                grade.read_capture(str(path))
            except UnicodeDecodeError as e:
                raised = e
        # The refusal is the only arm left, and it is asserted rather than
        # branched on, because a test that accepts either answer no longer
        # pins anything about which one this build gives.
        self.assertIsNotNone(raised)
        # One refusal, and it is the file's rather than a row's: iteration
        # is lazy, so the raise comes out of the loop and there is no row
        # to name it by. `None` is what says so.
        self.assertEqual(len(refused), 1)
        self.assertIsNone(refused[0][0])
        self.assertIn(str(raised), refused[0][1])
        # The codec is named, and it is the format's declared one rather than
        # a re-derivation of whichever locale happens to apply -- so it is
        # `utf-8` whatever box runs this, and it matches the codec in the
        # exception's own words.
        self.assertIn('utf-8', refused[0][1].lower())
        self.assertEqual(raised.encoding.lower(), 'utf-8')
        # And the remedy, so the refusal is not only a complaint: an operator
        # holding a capture from another box is told what to do about it
        # rather than shown a decode error and left to guess.
        self.assertIn('re-save', refused[0][1].lower())
        # The rows are still named, through the lenient reader, with the
        # byte as U+FFFD: both of them, not just the one before it, and
        # that is how the operator finds the byte that stopped it.
        self.assertEqual([ts for ts, _ in accepted],
                         ['2026-01-01T12:00:00.000+01:00',
                          '2026-01-01T12:00:30.000+01:00'])
        self.assertTrue(accepted[0][1].startswith('caf'), accepted[0][1])
        self.assertEqual(accepted[1][1], 'settled')
        # A label verdict needs a file the grader can read, and one it cannot
        # read is already refused whole: there is nothing for a second list to
        # add.
        self.assertEqual(unplaceable, [])

    def test_a_leading_bom_is_refused_by_name_and_not_as_a_bad_hex_row(self):
        # The BOM half of the same decision, and the one that needed a
        # refusal of its own. `utf-8` is declared and `utf-8-sig` is not, so
        # a leading BOM is *not* retired: it decodes to U+FEFF, glues to the
        # first field, the `ts` header test misses, and the header is graded
        # as a change row. Left alone that is refused on `int("addr", 16)` --
        # a complaint about a hex literal on a line that is not a change, and
        # one that never mentions the encoding at all. So the strict reader
        # catches it before the hex is read and says what it is.
        #
        # What this does *not* decide is whether the format should ever accept
        # a BOM. That is a separate question; all this pins is that a capture
        # carrying one is refused legibly under the encoding declared here.
        bom = b'\xef\xbb\xbf'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'capture.csv'
            path.write_bytes(bom + b'ts,addr,old,new\n'
                             b'2026-01-01T12:00:00.000+01:00,MARK,,settled\n'
                             b'2026-01-01T12:00:30.000+01:00,0x0701,0x00,0x11\n')
            with self.assertRaises(ValueError) as caught:
                grade.read_capture(str(path))
            # And the notice reports that same refusal rather than explaining
            # the header in hex: the grading and the warning are one verdict.
            accepted, refused, unplaceable = grade.existing_mark_findings(str(path))
        message = str(caught.exception)
        # Named as what it is, and as the format's rule rather than as a
        # mystery about an integer: not the `int()` complaint the header
        # would otherwise produce.
        self.assertIn('byte-order mark', message.lower())
        self.assertNotIn('invalid literal for int()', message)
        # With the remedy in it, the way the decode refusal carries one.
        self.assertIn('re-save', message.lower())
        self.assertIn('utf-8', message.lower())
        self.assertIn('bom', message.lower())
        # The notice's first reason is `read_capture`'s own exception,
        # verbatim -- the anti-drift contract, holding for a refusal of the
        # file's encoding as it does for a row's contents.
        self.assertEqual(refused[0][1], message)
        # Every mark still named, through the lenient reader: the preflight
        # did not lose the run to the refusal the grading gives.
        self.assertEqual([ts for ts, _ in accepted],
                         ['2026-01-01T12:00:00.000+01:00'])
        self.assertEqual(unplaceable, [])

    def test_on_a_file_the_strict_reader_accepts_the_two_readers_agree(self):
        # The success path reuses `existing_mark_labels` rather than adding a
        # second label-extraction rule, so a file the grader takes whole reads
        # at the console exactly as it did in #548. Asserted as a list and not
        # as a count, because the order is what a reader is looking down.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(self.ROWS, tmp)
            accepted, refused, unplaceable = grade.existing_mark_findings(path)
            lenient = grade.existing_mark_labels(path)
        self.assertEqual(accepted, lenient)
        self.assertEqual(len(accepted), 2)
        self.assertEqual(refused, [])
        self.assertEqual(unplaceable, [])

    def snapshot_then_append(self, path, row):
        """A stand-in for a watcher landing a row at the instant the notice
        reads the file: the rows handed back are the real read's, and the file
        is changed afterwards.

        Patched over `capture_snapshot` rather than over `read_capture`,
        because `existing_mark_findings` does not call `read_capture` any more
        (#749) -- a stub there would go unused and pass for the wrong reason.
        The append is *after* the delegate on purpose: it is what a second
        read would have picked up and the first had not, which is the whole of
        the two-moments defect. The three-tuple is passed through whole, so
        the byte-order mark `capture_snapshot` reports off the same buffer
        (#750) survives the patch rather than being dropped on the way past.
        """
        real = grade.capture_snapshot

        def read_then_append(p):
            rows, failure, has_bom = real(p)
            with open(p, "a", newline="") as f:
                f.write(row + "\n")
            return rows, failure, has_bom
        return read_then_append

    def count_opens(self, path, call):
        """What `call` returned, and how many times it `open()`ed `path`.

        The count rather than the effect: the two reads #749 removed differ
        from one read only when the append lands between them, and a test that
        waits for that to happen is a test that passes on a quiet filesystem.
        Counting is true every run, and the opens of the target path are the
        only thing counted -- the tempfile the fixture wrote is not one of
        them.
        """
        opened = []
        real = builtins.open

        def counting(name, *args, **kwargs):
            if str(name) == str(path):
                opened.append(str(name))
            return real(name, *args, **kwargs)
        with patch.object(builtins, 'open', counting):
            return call(), len(opened)

    def test_the_capture_is_opened_once_on_both_paths(self):
        # The issue's first "Done" bullet, pinned as the count rather than as
        # a symptom. Measured on the module as #749 found it: two on the
        # clean path -- `read_capture`, then `existing_mark_labels` -- and
        # three on the decode path, where `f.encoding` was the second of them
        # and the lenient read the third. (The issue called those the third
        # and the fourth; the count is this tree's, and one lower.) The
        # encoding now comes out of the exception that raised, so this is one
        # either way.
        with tempfile.TemporaryDirectory() as tmp:
            good = self.capture(self.ROWS, tmp)
            (_, refused, _), clean = self.count_opens(
                good, lambda: grade.existing_mark_findings(good))
            self.assertEqual(refused, [])

            latin = Path(tmp) / 'latin1.csv'
            latin.write_bytes(b'ts,addr,old,new\n'
                              b'2026-01-01T12:00:00.000+01:00,MARK,,caf\xe9\n')
            (_, refused, _), decode = self.count_opens(
                str(latin), lambda: grade.existing_mark_findings(str(latin)))
        self.assertEqual(clean, 1)
        self.assertEqual(decode, 1)
        # Both are one *open* and not one reader. The skip rule is one
        # function now -- `read_capture`, `mark_labels_of` and
        # `partition_capture_rows` all call `skippable_row` -- so the
        # delegation #749 said did not exist does, and this case plus
        # `measure_mark_provenance.py --self-test` hold the count to it.
        # What still keeps the notice from being one reader is the rest of
        # the shape: the four-field test and the `MARK` branch are three
        # deliberate contracts rather than one to be merged. See
        # `docs/findings/0751-capture-row-shape.md`.

    def test_a_row_that_lands_at_the_read_is_not_in_this_notice(self):
        # The defect, made to land. A watcher appends a well-formed mark the
        # instant after the read: the notice must describe the file as it was,
        # in all three lists, and a second call must then see the new row --
        # both directions, so a function that never opened the file at all
        # cannot pass this by returning something constant.
        appended = ('2026-01-01T12:01:00.000+01:00,MARK,,garbage label')
        rows = ['ts,addr,old,new',
                '2026-01-01T12:00:00.000+01:00,MARK,,settled']
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(rows, tmp)
            with patch.object(grade, 'capture_snapshot',
                              self.snapshot_then_append(path, appended)):
                accepted, refused, unplaceable = grade.existing_mark_findings(
                    path)
            # Unpatched, and the appended row is there to be found.
            after, refused_after, unplaceable_after = \
                grade.existing_mark_findings(path)
        self.assertEqual(accepted,
                         [('2026-01-01T12:00:00.000+01:00', 'settled')])
        self.assertEqual(refused, [])
        self.assertEqual(unplaceable, [])
        # The second direction, and it is the placement verdict that moves
        # rather than the label list: a minute on, so the appended mark opens
        # its own window instead of being coalesced into the one above. Had
        # the placement pass run over a second read, this list would have
        # named a mark the accepted list above it did not hold.
        self.assertEqual([ts for ts, _ in after],
                         ['2026-01-01T12:00:00.000+01:00',
                          '2026-01-01T12:01:00.000+01:00'])
        self.assertEqual(refused_after, [])
        self.assertEqual([label for _, label, _ in unplaceable_after],
                         ['garbage label'])

    def test_a_half_written_row_at_the_read_is_refused_by_the_next_call(self):
        # The sharper case the issue names: the row that lands between the two
        # reads is one the grader cannot grade. The notice reports the file it
        # read, with no refusal in it, and the refusal appears on the next
        # call -- which is the only place it can honestly appear.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(['ts,addr,old,new',
                                 '2026-01-01T12:00:00.000+01:00,MARK,,settled'],
                                tmp)
            half = '2026-01-01T12:01:00.000+01:00,MARK,'
            with patch.object(grade, 'capture_snapshot',
                              self.snapshot_then_append(path, half)):
                accepted, refused, unplaceable = grade.existing_mark_findings(
                    path)
            after, refused_after, _ = grade.existing_mark_findings(path)
            with self.assertRaises(ValueError):
                grade.read_capture(path)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(refused, [])
        self.assertEqual(unplaceable, [])
        self.assertEqual(refused_after[0][0],
                         ['2026-01-01T12:01:00.000+01:00', 'MARK', ''])
        # A second bad row is appended *after* the read as well, so a verdict
        # re-read after the fact would name two where only one was there.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(['ts,addr,old,new',
                                 '2026-01-01T12:00:00.000+01:00,MARK,'],
                                tmp)
            with patch.object(grade, 'capture_snapshot',
                              self.snapshot_then_append(
                                  path,
                                  '2026-01-01T12:01:00.000+01:00,MARK,')):
                _, refused, _ = grade.existing_mark_findings(path)
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0][0],
                         ['2026-01-01T12:00:00.000+01:00', 'MARK', ''])

    def test_every_mark_the_notice_calls_unplaceable_is_one_it_accepted(self):
        # The internal-consistency property the two reads could not hold, now
        # held by construction: the placement verdict is computed from the
        # same rows the accepted list is extracted from, so it cannot name a
        # mark that list does not hold. Asserted on the pair rather than on
        # the label alone, and the fixture writes the timestamp in the one
        # spelling `unplaceable` normalises back to -- `accepted` carries it
        # as written, so a `T` separator would make this a test of two
        # different timestamps rather than of one list naming another.
        first = '2026-01-01 12:00:00+01:00'
        second = '2026-01-01 12:01:00+01:00'
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(['ts,addr,old,new',
                                 f'{first},MARK,,garbage label',
                                 f'{second},MARK,,settled'], tmp)
            accepted, refused, unplaceable = grade.existing_mark_findings(path)
        self.assertEqual(refused, [])
        self.assertEqual(accepted, [(first, 'garbage label'),
                                    (second, 'settled')])
        pairs = [(ts, label) for ts, label, _ in unplaceable]
        # Not vacuous: one window is reported, so the loop below runs.
        self.assertEqual(pairs, [(first, 'garbage label')])
        for pair in pairs:
            self.assertIn(pair, accepted)

    def test_a_file_with_no_marks_comes_back_empty(self):
        # The quiet side, and the reason the notice keys on marks rather than
        # on the file being non-empty: §3's block-1 start appends to a path
        # that does not exist yet or holds the header `CsvSink` wrote, and
        # neither carries a label any process could have failed to check.
        # The second reader is empty on the same fixtures, so the split adds
        # nothing to say about a file the grader takes whole.
        with tempfile.TemporaryDirectory() as tmp:
            for rows in ([], ['ts,addr,old,new'],
                         ['ts,addr,old,new',
                          '2026-01-01T12:00:05.000+01:00,0x0701,0x00,0x11']):
                with self.subTest(rows=rows):
                    path = self.capture(rows, tmp)
                    self.assertEqual(grade.existing_mark_labels(path), [])
                    self.assertEqual(grade.existing_mark_findings(path),
                                     ([], [], []))

    def test_read_capture_is_unchanged(self):
        # The reader is additive. `read_capture` still skips `#`, blank and
        # header, still returns `(marks, changes)`, and still raises on a row
        # it cannot grade -- the cases above depend on it, and so does every
        # fixture under testdata/.
        with tempfile.TemporaryDirectory() as tmp:
            marks, changes = grade.read_capture(self.capture(self.ROWS, tmp))
        self.assertEqual([m.label for m in marks],
                         ['wrote 0x0751=0xA0', 'settled'])
        self.assertEqual([(c.addr, c.old, c.new) for c in changes],
                         [(0x0701, 0x00, 0x11)])
        self.assertTrue(all(m.source.endswith('capture.csv') for m in marks))


class SelfTestModeTests(unittest.TestCase):
    # The mode the gate calls, and the one
    # `docs/ci/agent-gates-0751-self-test.patch` wires in. Driven through its
    # `run` seam rather than launched for real: a case that ran the mode would
    # have the mode run this suite, which contains the case, which runs the
    # mode. The real discovery is what
    # `python3 ec/tools/grade_0751_isolation.py --self-test` and the gate's
    # case arm do, and this file is not either of them.
    def test_the_self_test_mode_runs_the_committed_suite_and_exits_zero(self):
        def discovery(returncode, said):
            def fake_run(cmd, **kw):
                return subprocess.CompletedProcess(cmd, returncode, said)
            return fake_run

        seen = []

        def record(cmd, **kw):
            seen.append(cmd)
            return subprocess.CompletedProcess(
                cmd, 0, '....\nRan 3 tests in 0.002s\n\nOK\n')

        # The flag reaches the mode with no capture behind it and the parser
        # never run. `csv` is still a required positional, and the mode is
        # dispatched ahead of it precisely so that stays true.
        with patch.object(grade, 'self_test', return_value=0) as stub:
            rc, out, err = run('--self-test')
        self.assertEqual(rc, 0)
        stub.assert_called_once_with()
        self.assertEqual(out, '')
        self.assertEqual(err, '')

        # And the mode hands unittest this suite, by file name and not by
        # `test_*.py` -- nine other suites live in that same directory -- over
        # the tool's own directory by absolute path, so the mode works from
        # any cwd.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(grade.self_test(run=record), 0)
        printed = out.getvalue()
        self.assertEqual(seen, [[sys.executable, '-m', 'unittest', 'discover',
                                 '-s', str(grade.TOOL_DIR),
                                 '-p', grade.SUITE_FILE]])
        self.assertEqual(Path(seen[0][seen[0].index('-s') + 1]).resolve(),
                         Path(__file__).parent.resolve())
        self.assertIn('3 tests, passed', printed)
        # The count decorates and does not decide, and the mode says what it is
        # not: refusals over committed fixtures, never §4 re-applied to a
        # capture a human took.
        self.assertIn('evidence about the machine', printed)

        # Two runs the exit code alone would have called a pass. A discovery
        # that matched nothing exits 0 and prints OK, and one that failed says
        # so in its exit code and nowhere else -- a suite name that no longer
        # resolves is the shape this is for, and it is green from outside. The
        # two are told apart by the line, not by the verdict: the vacuous run
        # says why it found nothing, the failing one says nothing and passes
        # the discovery's own output through.
        zero = 'Ran 0 tests in 0.000s\n\nOK\n'
        bad = 'Ran 3 tests in 0.002s\n\nFAILED (failures=1)\n'
        for returncode, said, why in ((0, zero, 'no test ran'),
                                      (1, bad, ': FAILED\n')):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(
                    grade.self_test(run=discovery(returncode, said)), 1)
            printed = out.getvalue()
            self.assertIn(why, printed)
            # What the discovery said is passed on rather than swallowed, so a
            # failing gate's log carries the failure rather than a verdict.
            self.assertIn(said.splitlines()[0], printed)

    def test_a_run_with_no_capture_is_still_argparse_s_usage_error(self):
        # argparse names the running script in its usage line, so the line
        # itself is not asserted on. What has to hold is the shape: a command
        # line carrying no capture is a usage error, and --self-test did not
        # cost that.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                grade.main([])
        self.assertEqual(cm.exception.code, 2)
        self.assertIn('usage:', err.getvalue())
        self.assertIn('the following arguments are required: csv',
                      err.getvalue())


if __name__ == '__main__':
    unittest.main()
