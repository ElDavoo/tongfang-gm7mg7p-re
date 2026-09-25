#!/usr/bin/env python3
"""Apply §4 of docs/hardware-tests/manual-fan-ctrl-0751-isolation.md to a
capture, mechanically, so the sweep half of the procedure is read the same way
twice.

Input is what the procedure already produces: the `ec_watch.py --mark --csv`
captures for the `0x0700-0x07FF` sweep, the `0x0F00-0x0F5F` fan table and the
`0x0400-0x045F` temperature range, and, optionally, the `before-*`/`after-*`
`ecrw.py dump` files from its steps 0 and 6. Each mark in a CSV opens a window
that runs to the next mark, and for every window this reports whether the
bytes §4 names moved inside it:

  * `0x0783-0x0785` -- PL1/PL2/PL4 (§4.1)
  * `0x0F00-0x0F5C` -- the fan table (§4.2)
  * `0x0F5D-0x0F5F` -- the fan-table reload mailbox, which is not a §4.x
    byte: a change there is a host request and/or the tail of a table that
    was written, and neither is §4.2's answer
  * `0x07C6`        -- the byte the vendor brackets its fan-table write with (§4.3)

and, reported but not graded, the fan duty bytes `0x075B`/`0x075C`
and `CPU_TEMP` `0x043E` / `GPU_TEMP` `0x044F` (§4.4/§4.5), plus whether
`0x0751` still holds the written value in the after-dump (§4.6).

Every context byte gets a `window delta` line in every window, whether or not
it moved: first value, last value, the endpoint net, the total movement (the
sum of the absolute steps it took inside the window), the max excursion (the
furthest it got from the value it opened the window at), and how many times it
moved. That is arithmetic on rows already in the capture, not a new judgement:
§4.4's comparison is how far the duty bytes moved between one mark and the next,
and reading that off the change rows means doing the subtraction by eye across
two terminal windows -- or, for a byte that went somewhere and came back, the
counting and adding by eye that the figures do instead.

The three movement figures are all on the line because they are not
interchangeable. Net is an endpoint statistic, so it is the right summary of a
clean monotonic step and blind to movement that came back; §4.4 keys the
control-vs-write comparison on total, because a fan duty under a fixed load
wanders in both arms and the wander cannot separate them, while how far the
byte actually travelled can. Max excursion is the read for a write arm whose
response is a ramp to a new duty followed by wander.

A byte that held still is a line of zeros, not a missing line: absence would
read as missing data rather than as the strongest negative result the
procedure can produce.

`--dump-pair` reads the same §4.1-§4.3 bytes a second, wider way, from a
before/after dump pair per range -- the range dumps §3's steps 0 and 6 take,
which bracket the whole block where each CSV window brackets one arm of it.
That bracket is complementary to the windowed one, not a stronger form of
it: a byte that moved at any point in the block and is back where it
started by the after-dump reads unchanged here, and a byte that moves
entirely between two of `ec_watch.py`'s sweeps is in no change row at all.
Each read has a gap the other does not close. An address one dump covers and
the other does not is a coverage gap, never a change.

Nothing handed in is taken on trust. A capture given twice is one console and
not two, and the run is refused before a mark is read: a file that agrees with
itself satisfies every cross-console check there is, and the census would have
counted the one console as two. A `--dump-pair` given the same file twice is
not a bracket and is not graded, on the same reasoning: a read diffed against
itself holds every byte equal by construction. The first is fatal and the
second is flagged and skipped, because a repeated pair is one entry among
several and the window report is still worth printing, where every section of
this report is about the captures. And §4.6 is a coverage statement before it
is a comparison -- when the last `--dump` does not cover `0x0751` the section
says the readback was not taken, and names a `--dump-pair` that does cover
it, whose after file is what §6 says to pass last. None of the three is a
claim about the machine; each is a claim about which files were handed in.

One thing is read that is not a byte at all: §3's per-block integrity check.
§3 calls that check mechanical and then leaves the operator to eyeball it
against the mark list `ec_watch.py` prints at stop. Here the marks are grouped
into blocks -- one per write under test, opened by the step-2 no-op control
arm and closed by the step-5 restore -- and each block's last mark has to be
that restore. A block whose last mark is not the restore is void: the capture
cannot show the byte being put back, so its last window never closes. It is
printed as void, by name and with the label it did end on, and the exit code
is not zero. Its windows are withheld like any other block that fails a mark
check: each prints a `not graded` line naming the capture that ends the block
where, and the block's own line reads `-- NOT GRADED, its windows are not
printed`.

**The mark set is a precondition of the windows, and is checked as one.**
A window is arithmetic over rows: every change after a mark belongs to that
mark's window, and which mark that is comes from the timestamps alone. So a
mark one console missed, or that two consoles spelled differently, raises
nothing. That console's rows are still filed under whichever window their
timestamps fall in, and the other two consoles' marks usually cover for it --
which is exactly what makes the failure invisible rather than what prevents
it. Nothing in the result ties those rows to the arm whose mark went missing,
so a no-op arm can read as thermally quiet for want of a mark rather than
because nothing moved, and the whole run reports that in the same confident
format as a result.

So §6's "the marks in all three CSVs must carry the same labels" is checked
rather than written down, before any window is printed: every action recorded
in every capture, every capture spelling it the same way, every block's last
mark its restore *in each capture*, and every label one of the three forms
§3 fixes. A block that fails any of those is summarised where its windows
would be and the windows are not printed -- they are correct as arithmetic and
wrong as evidence about a labelled action, and printing them in the usual
format is the defect. The census that carries the diagnosis is printed whole
either way, and names which capture is short, which two disagree, and what the
consequence is.

The census also names each block by the value its `write` mark carries, so a
window list, a `--dump` pair and a §4.6 verdict can all say which block they
are about. §6 stamps every dump with the `<value>` of the block it belongs to,
and a per-block invocation is meant to be attached per block, so `--block`
takes that value rather than a position in the mark stream: `0xA0`, `A0` and
`a0` are the same block. A value that is in no block is an error rather than
a run that grades everything, and a `--block` and a `--wrote` that name
different values are an error too -- both name the value under test.

The cross-console checks engage at two or more captures, which is §6's form.
With one there is no other console for a mark to be missing from and no
second spelling to disagree with it, so "the consoles agree" has nothing to be
true of; the census says so in as many words rather than letting the single
capture pass a check it never ran. The count is of distinct captures, so a
file given twice cannot reach the threshold with itself. The void rule and
the label parse run either way.

This is the check over the committed CSVs, not the by-eye one at the machine,
and the two are not the same reading. `ec_watch.py` appends a mark to its own
list and prints it whether or not the CSV sink is still open
(`../../windows/tools/ec_watch.py:121-123` against the close at `:221-222`),
so the last label a human reads off the terminal can be one the capture never
received -- the case §3 wants caught. The committed CSV is what the fold-in
reads, so the CSV is where the check belongs.

`--block VALUE` grades one block of a multi-block capture and reports that
block's windows alone, which is what makes the output something a fold-in can
attach per block: §6's three CSVs are one set for the whole run, so without it
every invocation prints every block's windows and the three attachments differ
only in the `--dump`/`--dump-pair` section, where it decides which block's
files are read and not merely printed. Every window carries a `block:` line
naming the block its marks fall in, and every dump and dump pair is grouped
under the block it names or the run was given, so an unscoped run's output
says the same thing the scoped one does.

None of this is a register behaviour. A void block says the capture is short a
mark; it says nothing about `0x0751`, and no line of any block verdict is a
status.

**This is not the §7 call and cannot be.** §7 moves `MANUAL_FAN_CTRL` off
`present-untested` on fan duty or package power moving under a fixed load.
Those bytes are captured and printed here, but printing them is not grading
them: a fan's duty moves with the die whether or not anything wrote
`0x0751` -- separating those is what the procedure's no-op control arm is
for, not this script. (The duty bytes used to be excluded for a second
reason as well, that §4.4 called their identity unconfirmed. Issue #123
identified them, so that reason is gone; the die-drift one is not, and it
alone keeps them out of the graded set.) Package power is read
by hand from HWiNFO (§4.5) and is in no capture. What this script says is
"of the bytes the sweep covers, these moved and these did not"; the call still
comes from a human holding the rest of the notes.

One action is marked in every watcher, so the same write appears as a MARK row
per capture; marks within `MARK_MERGE_SECONDS` are one window, not several.

**The closing section has three cases, not two.** A run that graded nothing
says so, a run that graded everything reports its movement and compares it to
the static prediction, and a run that graded some of its windows says the
movement over those and declines to compare it -- because "consistent with the
static prediction" is a claim about the capture, and over a subset of the
capture's windows it is a claim about the subset wearing the whole capture's
wording. Both halves of the partly-graded case are scoped: the "nothing moved"
reading names the windows it is a reading of, and the "something moved" one
says the same before the attribution underneath it. The withheld banner that
opens the section is not what carries that, and a reader who reads only the
line under it is the case this is for. §7's `confirmed-inert` needs all three
values, so a day that withheld a block leaves a gap in the call that no
sentence here can close.

Nothing here touches hardware; it reads files only.

Usage:
    python3 ec/tools/grade_0751_isolation.py capture-0700-07ff.csv \
        [capture-0f00-0f5f.csv] [capture-0400-045f.csv] \
        [--dump before-0700.txt] [--dump after-0700.txt]
    python3 ec/tools/grade_0751_isolation.py capture.csv --wrote 0xA0
    python3 ec/tools/grade_0751_isolation.py capture.csv --block 0xa0
    python3 ec/tools/grade_0751_isolation.py capture.csv \
        --dump-pair before-0700.txt after-0700.txt \
        --dump-pair before-0f00.txt after-0f00.txt
"""
import argparse
import csv
import datetime
import os
import re
import sys
import textwrap

MANUAL_FAN_CTRL = 0x0751

# How close two marks have to be to count as one action. The procedure holds
# ~30 s between the control arm and the write and ~60 s before the restore, so
# this only has to be wide enough to cover pressing Enter in each of three
# consoles; a window that opened twice for one action would report "nothing
# moved" for half of it.
MARK_MERGE_SECONDS = 5

# The bytes §4 asks about, in its order. Everything else in the sweep is
# reported as context only: §4.4 says to read the whole 0x0700-0x07FF range
# rather than the two addresses issue #99 names, because the neighbourhood
# around them is still the least mapped part of that page -- 0x0786 in
# particular carries three disagreeing vendor names (issue #123).
#
# The fan table stops at 0x0F5C because of what the next three bytes are.
# ec/annotations/manual-fan-ctrl-0751.md §6 decodes the handler at 0x888D as
# requiring 0xFD/0xC9 in 0x0F5D/0x0F5E as a magic and a selector in 1..3 in
# 0x0F5F, written by the host to ask the EC to copy a table -- and
# windows/vendor-ec-map.md calls the same three bytes the last three GPU duty
# slots, the tail of the row SetEcFanTable writes. So they are the trigger and
# the tail of a written table, not §4.2's subject: filed under the fan table,
# a host poke reads as the EC reloading its own table from the mode byte
# alone, which is the one thing §6 says it does not do on static evidence. The
# group is named for the address range so a `not covered by this pair` or
# `unchanged across the block` line about it explains itself.
TRIGGER_GROUP = ("fan-table reload trigger 0x0F5D-0x0F5F "
                 "(host-written; see below)")

WATCHED = (
    ("PL1/PL2/PL4 (§4.1)", range(0x0783, 0x0786)),
    ("fan table (§4.2)", range(0x0F00, 0x0F5D)),
    (TRIGGER_GROUP, range(0x0F5D, 0x0F60)),
    ("fan-table bracket byte 0x07C6 (§4.3)", range(0x07C6, 0x07C7)),
)

# What to print under a watched group that has hits, keyed by group name so
# both readers print the same words from one spelling -- the same reason
# CONTEXT is one tuple they both walk. The trigger is the one group that
# needs one: its value lines say only that three bytes differ, and read on
# their own under a §4.2 heading they are the false positive this group
# exists to stop. The group is in WATCHED rather than split out inside
# report_dump_pairs, which would break the "no third category" invariant its
# docstring states and leave the windowed reader filing a host mailbox poke
# as a fan-table move.
GROUP_NOTE = {
    TRIGGER_GROUP: (
        "these three are the mailbox ec/annotations/manual-fan-ctrl-0751.md "
        "§6 decodes at 0x888D -- 0xFD/0xC9 and a 1-3 selector, written by "
        "the host to ask the EC to copy a table -- and the last three GPU "
        "duty slots (windows/vendor-ec-map.md), so they move when a table "
        "is written as well. A change here is not §4.2's answer: §4.2 asks "
        "whether 0x0751 alone reloaded the table, and the table's own bytes "
        "are the line above."),
}

# §4.2's own named next step, for the whole-block read only, and only once a
# table byte has actually changed. All three of its arguments are required
# (windows/tools/fan_table_replay.py), so the line names them and the tool
# says what it walks: the changed table is worth replaying, and the windowed
# read is not the place to say so because it prints change rows as they
# happen rather than an endpoint pair.
FAN_TABLE_NEXT_STEP = (
    "§4.2's next step for a table that did change: replay it with "
    "windows/tools/fan_table_replay.py -- the 0x0F00-0x0F5F capture, a dump "
    "taken after it, and a decoded Fan/Table MQTT capture (--csv --final "
    "--mqtt, all three are required). It walks the states the capture passed "
    "through backwards from that dump and checks each against what the "
    "service published.")

# What a void block means, in the operator's words rather than this file's.
# Printed once however many blocks are void: the per-block line already names
# which they are and the label each ended on, so repeating the explanation
# per block would be noise on a three-value run.
VOID_BLOCK_NOTE = (
    "A void block is short the restore mark §3's step 5 makes, so its last "
    "window never closes and the block is not a finished one. The usual cause "
    "is the mark itself: ec_watch.py writes a mark into the CSV only while "
    "the sink is open, so a restore typed after the watcher has exited is "
    "printed in its `marks:` list and recorded nowhere else -- which is why "
    "this reads the CSVs and not that list. Redo the void block per §3; the "
    "exit code is 1 while any block is void.")

# The same, for a mark set that cannot support the windows taken over it. A
# void block is short a mark at the end; this is an action that is missing
# from a capture, or spelled differently by two of them, somewhere in the
# middle. The windows are arithmetic either way, so the only thing that
# separates the two cases is whether the mark that opened them is one the
# operator meant -- which is the whole of what is checked.
MARK_SET_NOTE = (
    "A block whose mark set does not hold has no windows worth printing. A "
    "window is every change after a mark up to the next one, and which mark "
    "that is comes from the timestamps alone, so a mark one console missed, or "
    "that two consoles spelled differently, does not fail anything: that "
    "console's rows are filed under whichever window they fall in, and the "
    "other two usually cover for it, so nothing in the result ties them to "
    "the arm whose mark went missing. Its windows are left out rather than "
    "printed in the usual format and quoted, the census above names which "
    "capture is short and what the consequence is, and the exit code is 1 "
    "until the marks do.")

# §6's three label forms, spelled as §6 spells them, for the message that
# quotes them back at a mark the parse could not read. The operator cannot fix
# an unplaceable mark from a description of the problem; the three forms are
# the whole of what has to change.
REQUIRED_LABEL_FORMS = ("no-op wrote 0x0751=0xA0", "wrote 0x0751=0x10",
                        "restored 0x0751=0xA0")

# The leading word of each form, and the role it makes the mark. Ordered so
# that `no-op wrote ...` reads as the control arm rather than as the write
# under test: §3 spells the control arm out that way precisely so the two
# cannot be confused, and the grader reading it the other way round would
# undo the point of the prefix.
MARK_FORMS = (("control", "no-op"), ("restore", "restored"), ("write", "wrote"))

# §6's `<value>` inside a dump's own file name -- the shape §3's step 0 and
# step 6 redirects write. It is how a dump says which block it belongs to,
# which is the only thing in a dump that says so: a dump is a whole-range
# read with no marks in it.
DUMP_VALUE = re.compile(r"-0751-isolation-([0-9a-f]{1,2})-(?:before|after)-",
                        re.I)

# The value inside a mark label, `0x0751=0xA0`. The address is spelled as §3
# and the probe spell it; `0x0*751` also takes `0x751`, which is the same
# address to the operator and would otherwise read as an unplaceable mark.
MARK_VALUE = re.compile(r"0x0*751\s*=\s*(?:0x)?([0-9a-f]{1,2})\b", re.I)

# The passing case, in as many words, because the block section is the one
# place in this report that carries no address and would otherwise be the one
# place a reader could mistake for a result.
INTACT_BLOCK_NOTE = (
    "Every block's last mark is its restore, so the capture is complete "
    "enough to read. That is a statement about what was captured and not "
    "about what the EC did: nothing here is a §7 verdict, and a void block "
    "is a hole in the record rather than a finding about a register.")

# The bytes §4.4/§4.5 name but this script does not grade. They get their own
# section because they are what §7's call is made on, and a reader should not
# have to find them in the generic "other addresses" list to notice them --
# and they get a line in every window, holding still or not, so that the no-op
# control arm and the write under test can be compared by eye: change row by
# change row, and then as the total movement the rows add up to, which is the
# figure §4.4 keys on. The duty pair is identified -- issue #123 gave them the
# vendor's ADDR_EC_MAIN_FAN_L/R_DUTY_BYTE names and entries in registers.yaml
# -- and it stays out of WATCHED anyway, because a duty byte drifts on a
# warming die whether or not anything wrote 0x0751: grading it would report
# "moved" on every window, the no-op control arm included, and leave nothing
# to compare. The two temperatures are confirmed-working, and are here as the
# record of whether the load was flat.
CONTEXT = (
    ("fan duty 0x075B/0x075C -- MAIN_FAN_L/R_DUTY (§4.4)",
     range(0x075B, 0x075D)),
    ("CPU_TEMP 0x043E / GPU_TEMP 0x044F -- confirmed (§4.5)",
     (0x043E, 0x044F)),
)


class Change:
    def __init__(self, ts, addr, old, new, source):
        self.ts = ts
        self.addr = addr
        self.old = old
        self.new = new
        self.source = source


class Window:
    """One mark and everything that changed before the next mark."""

    def __init__(self, ts, label, source):
        self.ts = ts
        self.label = label
        self.source = source
        self.changes = []
        self.levels = {}
        # The raw per-capture marks this window was merged from, and the
        # block it fell in. Both are set by `coalesce_marks` and
        # `assign_blocks` rather than at construction: a mark read out of a
        # CSV has no block until the whole mark stream has been walked, and
        # `coalesce_marks` is the only place that knows which raw rows one
        # action was recorded as.
        self.marks = []
        self.block = None


class Block:
    """One §3 block: a control arm, a write under test, and its restore.

    `value` is what the block's `write` mark carried, and is what `--block`
    and the `block:` line take: the value under test is the one thing a
    window, a dump and a §4.6 verdict can all be named by.
    """

    def __init__(self, value, windows):
        self.value = value
        self.windows = windows
        # 1-based, the position in the mark stream rather than anything the
        # operator names: two blocks on one day are the same value written
        # twice, and the number is the only thing that tells those apart.
        self.index = 0
        # (kind, window, text) per problem `check_block_marks` found. Kept on
        # the block rather than returned beside it so the window report, the
        # block verdict and the exit code are all reading one list and cannot
        # disagree about which blocks were graded.
        self.problems = []

    @property
    def name(self):
        return f"0x{self.value:02X}" if self.value is not None else "unnamed"

    @property
    def roles(self):
        """The block's marks as `assign_blocks` read them, in order.

        Read on demand rather than at construction: a block is opened by its
        write and closed by a restore that has not been seen yet, so the
        role of its last mark is not knowable when the block is made.
        """
        return [parse_mark(w.label)[0] or "unreadable" for w in self.windows]

    def marks_in(self, path):
        """Every raw mark of this block that one capture recorded, in order."""
        here = [m for w in self.windows for m in w.marks if m.source == path]
        return sorted(here, key=lambda m: m.ts)


def parse_ts(s):
    return datetime.datetime.fromisoformat(s)


def read_capture(path):
    """(marks, changes) from one ec_watch.py CSV.

    Blank lines and `#` lines are skipped so an operator can annotate a
    capture by hand without breaking this.
    """
    marks, changes = [], []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "ts":
                continue
            if len(row) < 4:
                raise ValueError(f"{path}: short row {row!r}")
            ts, addr, old, new = row[0], row[1], row[2], row[3]
            if addr == "MARK":
                marks.append(Window(parse_ts(ts), new, path))
            else:
                changes.append(Change(parse_ts(ts), int(addr, 16),
                                      int(old, 16), int(new, 16), path))
    return marks, changes


def read_dump(path):
    """addr -> byte, from `ecrw.py dump` output (`0700: 12 34 ...`).

    `#` lines are skipped, as `read_capture` skips them. The two are written
    by the same operator out of the same run, and §6 tells them to annotate
    what they hand in; a comment carrying a colon is otherwise read as a row
    of bytes and raises out of `int()`.
    """
    values = {}
    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            base, _, rest = line.partition(":")
            if not rest.strip():
                continue
            addr = int(base.strip(), 16)
            for i, b in enumerate(rest.split()):
                values[addr + i] = int(b, 16)
    return values


def distinct_captures(paths):
    """The capture paths that are each one file, and the repeats dropped.

    The first spelling of each file is the one kept, and a repeat comes back
    as `(path as given, path it repeats, the file both resolve to)`, so a
    caller can name all three: two spellings of one file is one file, and the
    operator has to be able to see which of the two was dropped.

    Keyed on `os.path.realpath` rather than on the string, for the reason
    `report_dump_pairs` gives -- a path is what the operator hands in, and
    `x.csv`, `./x.csv` and a symlink to it are one capture. One spelling of
    the test, so `main` and the readers cannot disagree about which captures
    a run has.
    """
    kept, seen, repeats = [], {}, []
    for path in paths:
        resolved = os.path.realpath(path)
        if resolved in seen:
            repeats.append((path, seen[resolved], resolved))
        else:
            seen[resolved] = path
            kept.append(path)
    return kept, repeats


def coalesce_marks(marks):
    """One window per action, however many consoles recorded it.

    The procedure runs one `--mark --csv` watcher per console, so a single
    action lands as several MARK rows seconds apart. Left alone, the changes
    that follow would be assigned to whichever of them happened to be last and
    the other two would report "nothing moved" for a write that did move
    things. A group starts at its *earliest* mark -- the window has to open
    before the first press, or the reaction is attributed to the wrong action
    -- and carries every label and source in it.

    The raw rows ride along on the window in `marks` rather than only their
    joined label. A joined label cannot say which console recorded which
    spelling of an action, and the mark-set checks are per capture.
    """
    groups = []
    for m in sorted(marks, key=lambda w: w.ts):
        close = groups and (m.ts - groups[-1][-1].ts).total_seconds() \
            <= MARK_MERGE_SECONDS
        if close:
            groups[-1].append(m)
        else:
            groups.append([m])
    windows = [Window(g[0].ts,
                      " / ".join(dict.fromkeys(m.label for m in g)),
                      ", ".join(dict.fromkeys(m.source for m in g)))
               for g in groups]
    for w, g in zip(windows, groups):
        w.marks = g
    return windows


def build_windows(marks, changes):
    """Assign every change to the last mark at or before it, and record the
    level each byte held where its window opened.

    Changes before the first mark belong to no window: the procedure has the
    operator let the sweep settle for ~10 s before marking, so they are the
    settling noise, not a reaction to anything. They still set the level the
    mark opened on, though, and that is worth more than their being dropped:
    without them a byte that moved while the sweep settled and then held still
    would print as level-unknown, when the captures in hand do say what it
    settled to. One time-ordered pass does both.
    """
    windows = coalesce_marks(marks)
    ordered = sorted(changes, key=lambda c: c.ts)
    last, i = {}, 0
    while i < len(ordered) and ordered[i].ts < windows[0].ts:
        last[ordered[i].addr] = ordered[i].new
        i += 1
    for n, w in enumerate(windows):
        w.levels = dict(last)
        end = windows[n + 1].ts if n + 1 < len(windows) else None
        while i < len(ordered) and (end is None or ordered[i].ts < end):
            w.changes.append(ordered[i])
            last[ordered[i].addr] = ordered[i].new
            i += 1
    return windows


def parse_value(text):
    """The byte a `--block` or `--wrote` names, or None if it is not one.

    Hex with or without the `0x`, in either case, because §6 spells the value
    `a0` in a file name and `0xA0` in a mark label and the operator is not
    going to remember which flag wants which. The two flags name the same
    thing, so they read the same way; a `--block` and a `--wrote` that name
    different values is caught in main rather than reconciled here.
    """
    try:
        return int(text.strip().lower().removeprefix("0x"), 16)
    except (AttributeError, ValueError):
        return None


def parse_mark(label):
    """(role, value) for one mark label, or (None, None) if it carries neither.

    §3 fixes the three labels the operator types and `ec_watch.py` writes them
    into the CSV verbatim, so the leading word is the only handle on it. Only
    that word and the value are read, case-insensitively: everything after the
    value is the operator's, and what is checked here is which action the
    mark names and which value it names -- not how it was punctuated.

    `no-op wrote ...` is the control arm and `wrote ...` is the write under
    test, which is the whole reason §3 spells the prefix out: read the other
    way round, the two are the same sentence with a prefix and the control arm
    becomes indistinguishable from what it is a control for.

    The value is `int`, not the text, because it is compared against another
    block's and against `--block`, and `0xA0` / `A0` / `a0` are one value
    rather than three spellings of a name.

    `coalesce_marks` joins the consoles' labels for one action with ' / ', so
    the first spelling decides and the disagreement is reported beside it --
    one console recording the mark is what makes it that mark, and the other
    consoles' wording is exactly what the disagreement check is about.
    """
    for part in label.split(" / "):
        part = part.strip().lower()
        for role, word in MARK_FORMS:
            if not part.startswith(word + " "):
                continue
            m = MARK_VALUE.search(part)
            return (role, int(m.group(1), 16)) if m else (None, None)
    return None, None


def assign_blocks(windows):
    """The windows grouped into §3's blocks, and the ones in no block.

    A block is opened by a `write` mark and named by the value that mark
    carries -- the value under test is the one thing a window, a `--dump`
    pair and a §4.6 verdict can all be named by, and §6 stamps the dumps with
    it. The no-op control arm in front of the write joins that block, because
    §4.4's comparison is between the two and a control arm in a block of its
    own would be an arm with nothing to compare against. A `restore` closes
    the block it is in, so a block that never gets one is left open and comes
    back void rather than running into the next one.

    The labels are the only thing that says a run was one block or the next.
    A gap in the timestamps says only how long the operator took, and a mark
    stream read on timestamps alone grades whatever it is handed under
    whatever heading it happens to fall in.

    What is left over is returned rather than folded into a neighbour: a
    control arm whose write never came, a restore with no block open, and a
    label this cannot read are three different things and are reported as
    three. They are graded as the windows the capture did hold -- their rows
    are real and there is no other arm to mis-file them under -- with `block:
    unplaced` on their header, and the unreadable ones refused as well
    because a label this cannot read is a label it cannot say what a window
    is a window of.
    """
    blocks, unplaced, pending, current = [], [], [], None
    for w in windows:
        role, value = parse_mark(w.label)
        if role == "control":
            # Held for the write that follows rather than added where it
            # stands: a control arm after a block's write and before its
            # restore belongs to the next block, which is what a restore that
            # never arrived would otherwise swallow.
            pending.append(w)
        elif role == "write":
            current = Block(value, pending + [w])
            pending = []
            blocks.append(current)
        elif role == "restore":
            if current is None:
                unplaced.append(w)
            else:
                current.windows.append(w)
                current = None
        else:
            unplaced.append(w)
    unplaced = sorted(pending + unplaced, key=lambda w: w.ts)
    for i, block in enumerate(blocks, 1):
        block.index = i
    for block in blocks:
        for w in block.windows:
            w.block = block
            for m in w.marks:
                m.block = block
    for w in unplaced:
        for m in w.marks:
            m.block = None
    return blocks, unplaced


def unplaceable_marks(unplaced):
    """The marks the label parse could not read, per unplaceable window.

    Fatal for the whole run rather than for one block, which is the
    conservative direction and the reason for it: block attribution rests
    entirely on the labels, so a mark this cannot read leaves every block's
    completeness uncertifiable -- not only the one it would have landed in.
    `--block` scoping narrows what is graded, not what is known.
    """
    out = {}
    for w in unplaced:
        if parse_mark(w.label)[0] is not None:
            continue
        out[w] = [
            f"{os.path.basename(m.source)} at {m.ts.isoformat(sep=' ')}: "
            f"{m.label!r} is not one of the three forms §6 fixes ("
            + ", ".join(repr(f) for f in REQUIRED_LABEL_FORMS)
            + "), and a mark this cannot read is a mark no block can be "
              "attributed to"
            for m in w.marks]
    return out


def check_block_marks(block, captures):
    """The problems in one block's mark set, each against the window it is on.

    Three, and all three are comparisons over rows already read rather than
    new heuristics:

      * an action some capture did not record. `coalesce_marks` groups the
        marks by time, so that capture's rows are filed under whichever
        window their timestamps fall in rather than under the arm whose mark
        it missed -- and the other two consoles' marks usually cover for it,
        which is what makes the failure invisible rather than what prevents
        it. A control arm whose marks went missing can read as quiet for
        want of a mark rather than because nothing moved.
      * an action the captures spelled differently. Same failure, found one
        step earlier: `coalesce_marks` joins the labels with ' / ', so the
        window opens on a label no console typed.
      * a block whose last recorded mark in some capture is not the restore.
        Per block *and* per capture, not the file's global last mark: a
        capture that recorded only one block would otherwise look complete
        for every block in the day.

    The agreement checks need a second capture to have anything to disagree
    with, so they engage at two or more and the census says so below that
    rather than letting one capture pass a check it never ran.
    """
    # `main` refuses a repeated capture before this runs; the line is held here
    # too, because these are the checks a repeat would switch on and a reader
    # reached directly still has one capture counted once.
    names, _ = distinct_captures(path for path, _ in captures)
    known = set(names)
    problems = []
    for w in block.windows:
        by_source = {}
        for m in w.marks:
            by_source.setdefault(m.source, []).append(m.label)
        spellings = {label for labels in by_source.values()
                     for label in labels}
        if len(spellings) > 1:
            said = "; ".join(
                f"{os.path.basename(p)}: {by_source[p][0]!r}"
                for p in names if p in by_source)
            problems.append(("labels", w, (
                f"the captures spell this action differently -- {said} -- so "
                "the window it opens is not the action any of them recorded")))
        if len(names) > 1 and set(by_source) != known:
            absent = ", ".join(os.path.basename(p)
                               for p in names if p not in by_source)
            problems.append(("missing", w, (
                f"recorded in {len(by_source)} of {len(names)} capture(s), "
                f"absent from {absent}. The capture(s) that missed it have "
                "their rows for this arm filed under whichever window their "
                "timestamps fall in, and nothing in the result ties them to "
                "the arm whose mark is gone -- so this arm can read quiet for "
                "want of a mark rather than because nothing moved")))
    for path in names:
        here = block.marks_in(path)
        if here and parse_mark(here[-1].label)[0] != "restore":
            problems.append(("void", block.windows[-1], (
                f"{os.path.basename(path)} ends this block on "
                f"{here[-1].label!r}, not the restore, so its last window "
                "never closes in that capture")))
    return problems


def window_delta(w, addr):
    """One context byte's movement inside one window, as a printed line.

    `net` is the endpoint difference, `total` the sum of the absolute steps the
    byte took inside the window, `max` the furthest it got from the value it
    opened the window at. They are all here because §4.4's comparison is not
    answered by any one of them on its own: a byte that steps and settles says
    the same thing in all three, a byte that steps and wanders back does not.

    With no in-window change the byte did not move, so all three figures are
    zero and that is what the line says -- the line existing at all is the
    point, since no line reads as missing data rather than as a held byte. The
    level comes from `w.levels`: a change-row capture records transitions, not
    values, so a byte that has never appeared is known not to have moved while
    its level is not in evidence, and the line says that rather than filling
    something in.
    """
    seq = [c for c in w.changes if c.addr == addr]
    first = seq[0].old if seq else w.levels.get(addr)
    if first is None:
        level = "???? -> ????"
    else:
        level = f"0x{first:02X} -> 0x{seq[-1].new if seq else first:02X}"
    net = seq[-1].new - first if seq else 0
    total = sum(abs(c.new - c.old) for c in seq)
    peak = max((abs(c.new - first) for c in seq), default=0)
    if seq:
        count = f"({len(seq)} change{'' if len(seq) == 1 else 's'})"
    elif first is None:
        count = "(0 changes, level not in these captures)"
    else:
        count = "(0 changes)"
    return (f"window delta  0x{addr:04X}  {level}  net {net:+d}  "
            f"total {total}  max {peak}  {count}")


def note_lines(text):
    """Text as the lines to print under a group, at the value lines' indent.

    Six spaces and the same ~72 columns the rest of this file is written to,
    so a note reads as part of the group it is printed under rather than as a
    paragraph the report drifted into.
    """
    return textwrap.wrap(text, width=72,
                         initial_indent="      ", subsequent_indent="      ")


def group_note(name):
    """The note for a watched group, or [] for the groups that need none.

    Empty rather than absent so both readers can call it unconditionally in a
    loop that has already decided the group has something to say.
    """
    note = GROUP_NOTE.get(name)
    return note_lines(note) if note else []


def wrap_note(text, indent=2):
    """One paragraph at a given indent, as `report_blocks` prints its own.

    A note that belongs to a section rather than to a group under one is set
    at the two spaces every section-level paragraph in this report is set at;
    one that belongs to a window is set at the four its body is. The wrap
    width is the file's 72 either way, because the two indents and the same
    measure are what make a note read as part of the thing it is under.
    """
    pad = " " * indent
    return "\n".join(textwrap.wrap(text, width=72, initial_indent=pad,
                                   subsequent_indent=pad))


def report_census(captures, windows, blocks, unplaced, unreads, selected):
    """What the marks say, before anything is read over them.

    Two listings, because they answer two questions. Per capture: the labels
    that capture recorded, in order, each with the role the parse gave it and
    the block it fell in -- which is the only place a mark that went missing,
    or a label two consoles spelled differently, is visible as such. Per
    action: how many of the N captures recorded it and whether they agree,
    which is the comparison §6 asks for in a sentence rather than in prose.

    Printed whole even under `--block`, because a run that scoped itself and
    said so is the point: the blocks it did not grade are named here as not
    selected, so a reader can see that the scoping is there and not that the
    other blocks are missing.

    Nothing here is a result. It is a statement about which labels the
    captures hold, and the windows below are only as good as it is.
    """
    # The same invariant as the refusal in `main` and as `check_block_marks`,
    # and for the same reason: the count, the one-capture notice and the
    # listing below are of the captures the operator really handed in, each of
    # them once. `main` is in front of this and has refused the run already if
    # there was a repeat, so what is defended here is a reader reached
    # directly -- which the test suite does.
    names, _ = distinct_captures(path for path, _ in captures)
    marks_by_path = dict(captures)
    total = sum(len(marks_by_path[path]) for path in names)
    print("\n=== mark census (§3/§6) ===")
    print(f"  {len(names)} capture(s), {total} mark row(s), "
          f"{len(windows)} action(s) after the merge")
    if len(names) < 2:
        print("  one capture: the cross-console checks did not run -- a mark "
              "cannot be missing from another console that is not there, and "
              "a label has nothing to disagree with it. The void check and "
              "the label parse did run.")
    if unreads:
        for lines in unreads.values():
            for line in lines:
                print(wrap_note(line))

    for path in names:
        marks = marks_by_path[path]
        print(f"  {os.path.basename(path)} ({len(marks)} mark(s)):")
        for m in marks:
            role, _ = parse_mark(m.label)
            where = m.block.name if m.block else "unplaced"
            print(f"    {m.ts.isoformat(sep=' ')}  {role or 'UNREADABLE':10}  "
                  f"{where:9}  {m.label!r}")

    for i, w in enumerate(windows, 1):
        said = {}
        for m in w.marks:
            said.setdefault(m.source, m.label)
        where = f"block {w.block.name}" if w.block else "unplaced"
        head = (f"  action {i} at {w.ts.isoformat(sep=' ')}  {where}: "
                f"{w.label!r} in {len(said)} of {len(names)} capture(s)")
        if len(said) == len(names) and len(set(said.values())) == 1:
            print(head + ", one label each")
            continue
        print(head + ":")
        for path in names:
            got = said.get(path)
            print(f"    {os.path.basename(path):44} "
                  + (repr(got) if got else "-- did not record it"))

    for i, b in enumerate(blocks, 1):
        line = (f"  block {i} of {len(blocks)}: value under test {b.name}, "
                f"roles {', '.join(b.roles)}")
        if selected is not None and b is not selected:
            line += " -- not selected in this run"
        elif b.problems:
            # The kinds, not just the count: a reader of a fold-in wants to
            # know whether a block is short a mark or a capture is short one,
            # and the two send the operator to different terminals.
            kinds = ", ".join(sorted({k for k, _, _ in b.problems}))
            line += (f" -- NOT GRADED, {len(b.problems)} mark-set "
                     f"problem(s): {kinds}")
        print(line)
    if unplaced:
        for w in unplaced:
            role, _ = parse_mark(w.label)
            if role is not None:
                print(f"  unplaced: {w.ts.isoformat(sep=' ')}  {w.label!r} -- "
                      "in no block, so no §3 integrity check covers it and "
                      "`--block` cannot select it")


def report_withheld_window(w, n, total, where, problems):
    """One window the mark set will not support, and why, in its place.

    The header and the block line are the same as a graded window's, so the
    mark is still locatable and the numbering still matches the whole-capture
    run. The body is not printed: these windows are correct as arithmetic and
    wrong as evidence about a labelled action, and printing them in the usual
    format is the defect these checks exist for. What replaces it is the one
    thing the operator needs to fix the input.

    `where` is the `block:` line's tail -- a block's name and position, or
    `unplaced` for a mark no block could take -- and `problems` this window's
    own, so a block whose problem is on another mark says so here too rather
    than leaving a bare refusal with no diagnosis on it.
    """
    print(f"\n--- mark {n}/{total}: {w.ts.isoformat()}  {w.label!r} "
          f"({w.source})")
    print(f"    block: {where} -- NOT GRADED")
    for text in problems:
        print(wrap_note(f"not graded -- {text}.", indent=4))


def report_window(w, n, total, block, total_blocks, end=None):
    """One window: the watched bytes that moved, and the context bytes.

    `end` overrides what the last window of a `--block` read runs to. It
    stops the read there, but it does not end the capture, and the default's
    "the end of the capture" would be the one false sentence in a report
    whose whole job is not to claim more than the capture holds.

    The `block:` line goes under the header and above everything else, so
    every window says which block it belongs to without a reader having to
    count marks back to the one that opened it. A window in no block says
    `unplaced` rather than nothing: there is no §3 shape to check it against,
    and a bare absence of the line would read as an older report rather than
    as a mark the walk could not place.
    """
    end = end or ("the next mark" if n < total else "the end of the capture")
    print(f"\n--- mark {n}/{total}: {w.ts.isoformat()}  {w.label!r} "
          f"({w.source})")
    where = "unplaced" if block is None else \
        f"{block.name} (block {block.index} of {total_blocks})"
    print(f"    block: {where}")
    print(f"    window runs to {end}")

    # The group names that had hits, in WATCHED order, so main can say which
    # bytes moved rather than only that some did: a mailbox poke and a
    # fan-table move are different answers to §4.2, and "at least one of
    # §4.1-§4.3 moved" cannot tell them apart.
    moved = []
    for name, addrs in WATCHED:
        hits = [c for c in w.changes if c.addr in addrs]
        if not hits:
            continue
        moved.append(name)
        print(f"    {name}:")
        for c in hits:
            dt = (c.ts - w.ts).total_seconds()
            print(f"      0x{c.addr:04X}  0x{c.old:02X} -> 0x{c.new:02X}"
                  f"   (+{dt:.1f}s)")
        for line in group_note(name):
            print(line)
    if not moved:
        print("    no watched byte moved in this window")

    print("    fan duty / temperature bytes (§4.4/§4.5) -- context, "
          "not graded here:")
    print("    net is the raw byte difference across the whole window, not a "
          "duty")
    print("    percentage; total is the sum of the absolute steps the byte "
          "took inside it,")
    print("    and max is the furthest it got from the value it opened the "
          "window at. §4.4")
    print("    keys the control-vs-write comparison on total. Every context "
          "byte gets a")
    print("    line in every window, so a byte that held still is a zero here "
          "and not a")
    print("    missing line.")
    for name, addrs in CONTEXT:
        print(f"      {name}:")
        for a in addrs:
            print(f"        {window_delta(w, a)}")
        for c in w.changes:
            if c.addr not in addrs:
                continue
            dt = (c.ts - w.ts).total_seconds()
            print(f"        0x{c.addr:04X}  0x{c.old:02X} -> 0x{c.new:02X}"
                  f"   (+{dt:.1f}s)")

    others = sorted({c.addr for c in w.changes
                     if not any(c.addr in a for _, a in WATCHED)
                     and not any(c.addr in a for _, a in CONTEXT)})
    if others:
        print(f"    other addresses that moved ({len(others)}), not graded "
              "here -- read them against §4.4 and §4.5 by hand:")
        print("      " + " ".join(f"0x{a:04X}" for a in others))
    return moved


def report_blocks(blocks, selected=None):
    """§3's per-block integrity check, one verdict per block, and the count
    of the ones that cannot be read as a finished block.

    Whether the capture is complete enough to read at all, which is a
    different question from what it says. A block whose last mark is not the
    restore is missing the mark that says the byte was put back; the last of
    its windows runs on to the end of the capture instead of closing, so §4
    has an arm it cannot read. The verdict names the label the block did end
    on, because "void" on its own sends the operator back to the terminals to
    find out which block and which mark.

    `intact` prints as well, so a reader of a fold-in can see that the check
    ran and held rather than inferring it from the absence of a complaint --
    silence about a missing restore is the failure mode this exists to stop,
    and the absence of the passing case is the same shape.

    A block whose mark set does not hold is intact here and not graded
    anyway, which is two different facts and are printed as two: the restore
    is there, and an action before it is missing from a capture. Only the
    second one withholds the windows.

    `selected` grades one block of a multi-block capture (`--block VALUE`)
    and says the rest were not looked at, so the count this returns is about
    the block that was asked for and about nothing else.
    """
    total = len(blocks)
    if selected is None:
        print(f"\n=== {total} block(s), one per no-op control arm (§3) ===")
        shown = list(blocks)
    else:
        print(f"\n=== block {selected.index} of {total}, its integrity check "
              f"===  (value under test {selected.name})")
        print(f"    the other {total - 1} block(s) were not checked in this "
              "run; run it without --block to check them all")
        shown = [selected]
    void = 0
    for block in shown:
        i = block.index
        last = block.windows[-1]
        if parse_mark(last.label)[0] == "restore":
            print(f"  block {i}/{total}: intact -- last mark {last.label!r} is "
                  "the restore")
        else:
            void += 1
            print(f"  block {i}/{total}: VOID -- last mark is {last.label!r}, "
                  "not the restore")
        tail = (f"value under test {block.name}; roles "
                f"{', '.join(block.roles)}")
        if block.problems:
            tail += " -- NOT GRADED, its windows are not printed"
        print(f"    {tail}")
    if void:
        note = VOID_BLOCK_NOTE
    elif any(b.problems for b in shown):
        note = MARK_SET_NOTE
    elif selected is None:
        note = INTACT_BLOCK_NOTE
    else:
        return void
    print()
    print(wrap_note(note))
    return void


def dump_block(path, fallback):
    """(value, how) for a --dump: which block it is, and what says so.

    §6 stamps every dump with the `<value>` of the block it belongs to, and
    that name is the only thing in a dump that says so -- a dump is a
    whole-range read with no marks in it. Where the name carries none, the
    value the operator gave on the command line is the only other thing that
    can, and the report prints which of the two it used so a reader is never
    left guessing which.
    """
    m = DUMP_VALUE.search(os.path.basename(path))
    if m:
        return int(m.group(1), 16), "name"
    if fallback is not None:
        return fallback, "flag"
    return None, "none"


def dump_pair_block(before, after, fallback):
    """(value, how) for a --dump-pair: which block it is, and what says so.

    A pair is one range's bracket for one block, so it is that block's if
    either of its two file names says so -- a name is the only thing in a
    dump that says which block it belongs to, and one of the two carrying it
    is that statement with the other silent, the same reading
    `report_readback` gives a name against `--wrote`. `dump_block` is the
    thing asked, not re-implemented: the name beats the flag, and the report
    says which of the two it used.

    Two names that disagree are not settled here. A pair is one block's, so
    a before-dump of 0xA0 and an after-dump of 0x10 bracket two different
    blocks, and picking either file's block would file a bracket over the
    wrong bytes with a clean face. The pair is named, the disagreement
    printed, and nothing is read from it -- the same non-fatal handling the
    same-file-twice pair gets, because it is the same class of thing: an
    input error, stated, with the window report and the §4.6 readback the
    operator also needs still printed. `disagree` carries no value for the
    same reason.

    The fallback is only consulted when neither name speaks, so a pair that
    names its own block is never quietly re-filed under the run's `--block`.
    """
    b, b_how = dump_block(before, None)
    a, a_how = dump_block(after, None)
    if b_how == "name" and a_how == "name" and b != a:
        return None, "disagree"
    if b_how == "name" and a_how == "name":
        return b, "name"
    if b_how == "name" or a_how == "name":
        return (b, "one-name") if b_how == "name" else (a, "one-name")
    if fallback is not None:
        return fallback, "flag"
    return None, "none"


def report_dumps(dumps, wrote, pairs, block_value=None):
    """0x0751 in each --dump, and what the last of them says about §4.6.

    Coverage is stated before anything is compared. A run may hand in dumps
    that do not reach the address at all, and `--wrote` is optional, so "the
    readback was not taken" has to be a line of its own: without it a run
    whose last dump stops short of `0x0751` ends the section looking exactly
    like a run where the check was taken and the answer held.

    A pair is named only when both of its files cover the address -- the same
    intersection `report_dump_pairs` compares under. A pair whose before-dump
    alone reaches `0x0751` cannot become a readback, and pointing at one
    would send the operator after a byte that is not there.

    Dumps are grouped by the block they name, and the readback is taken from
    the last dump *of the block being graded* rather than the last dump
    given. A three-value day hands in six dumps and the `0xA0` verdict under
    the `0x10` block's windows is the shape this fixes: one number, a name
    that does not go with it, and nothing in the output to catch it.

    The heading line is unchanged whatever the grouping does. It is what both
    §4.6 readers in the test suite cut the section on, and a heading that
    grows a value in it breaks both of them for no gain -- the block is
    named on the first line under it instead.
    """
    print("\n=== 0x0751 across the dumps (§4.6) ===")
    if not dumps:
        print("  no dump given (--dump); §4.6 not checked")
        return
    fallback = block_value if block_value is not None else wrote
    groups = []
    for path, values in dumps:
        value, how = dump_block(path, fallback)
        for value_, how_, here in groups:
            if value_ == value:
                here.append((path, values))
                break
        else:
            groups.append([value, how, [(path, values)]])

    for value, how, here in groups:
        if value is None:
            print("  no block named: these files carry no §6 <value> and "
                  "neither --block nor --wrote was given")
        elif how == "name":
            print(f"  block 0x{value:02X}, from the <value> in these files' "
                  "§6 names")
        else:
            print(f"  block 0x{value:02X}, from --block/--wrote; these files "
                  "carry no <value> of their own")
        if block_value is not None and value != block_value:
            for path, _ in here:
                print(f"    {path}: belongs to block 0x{value:02X}, not the "
                      f"block under test (0x{block_value:02X}) -- not read "
                      "for §4.6 here")
            continue
        for path, values in here:
            v = values.get(MANUAL_FAN_CTRL)
            if v is None:
                print(f"  {path}: 0x{MANUAL_FAN_CTRL:04X} not covered by this "
                      "dump")
            else:
                print(f"  {path}: 0x{MANUAL_FAN_CTRL:04X} = 0x{v:02X}")
        report_readback(here, wrote, pairs, value)
    if block_value is not None and not any(v == block_value
                                          for v, _, _ in groups):
        print(f"  no dump was given for block 0x{block_value:02X}, so §4.6's "
              "readback for it was not taken; the dumps named above are "
              "another block's")


def report_readback(here, wrote, pairs, value):
    """What the last dump of one block says about §4.6, and whether at all.

    Split out of `report_dumps` because the grouping above means this is now
    a question about one block's dumps rather than about the run's last file,
    and because the value the readback is compared against is the block's own
    rather than one number for the run. A three-value day graded in one
    invocation hands in six dumps and writes three values, and a single
    `--wrote` against all of them would call the 0x10 block's byte "not the
    written 0xA0" -- the exact mis-attribution the grouping exists to stop,
    one level down. Where the file name names a block and `--wrote` names
    another, the name is the more specific of the two statements and the
    disagreement is printed rather than resolved silently.
    """
    if here[-1][1].get(MANUAL_FAN_CTRL) is None:
        print(f"  the last --dump does not cover 0x{MANUAL_FAN_CTRL:04X}, so "
              "the §4.6 readback was not taken -- nothing here says what the "
              "byte held after the write")
        for before_path, after_path, before, after in pairs:
            if MANUAL_FAN_CTRL in set(before) & set(after):
                print(f"    a --dump-pair does cover it: {before_path} -> "
                      f"{after_path}; both files reach "
                      f"0x{MANUAL_FAN_CTRL:04X}")
                print(f"      pass the after file as the last --dump to take "
                      f"the readback: {after_path}")
                break
    written = value if value is not None else wrote
    if written is None:
        return
    if wrote is not None and value is not None and wrote != value:
        print(f"  these dumps are named for block 0x{value:02X} but --wrote "
              f"says 0x{wrote:02X}; the readback below is against the "
              "block's own write")
    last = here[-1][1].get(MANUAL_FAN_CTRL)
    if last is None:
        return
    if last == written:
        print(f"  the last dump still holds the written 0x{written:02X}. Per "
              "CLAUDE.md that is a readback, not evidence the EC acted on it.")
    else:
        print(f"  the last dump holds 0x{last:02X}, not the written "
              f"0x{written:02X} -- something put it back; §3a's service-stopped "
              "run is what separates the vendor service from the EC.")


def report_dump_pairs(pairs, block_value=None, wrote=None):
    """The same watched bytes, read across a whole block instead of a window.

    A pair is §3's own bracket for one range -- step 0 and step 6, ~100 s
    apart -- and a CSV window is one arm of that block. So this is a wider
    bracket on the same question, not a better answer: a byte that moved
    anywhere in the block and is back at its starting value by the
    after-dump reads unchanged here, and a byte that moves entirely between
    two of `ec_watch.py`'s sweeps is in no change row at all. Each read has
    a gap the other does not close, and neither emits a status.

    Only the intersection of the two address sets is compared. `read_dump`
    returns what it saw, so an address past the end of the shorter dump is
    simply missing from it, and a plain `!=` over the union would call every
    one of them a difference. A gap like that is coverage, printed as such.

    `0x0F5D-0x0F5F` is reported under a heading of its own, and the heading
    is not a fifth §4. The dump §3 takes for this range is `ecrw.py dump
    0x0F00 0x0060`, so it reaches those three bytes, and two different
    things write them. The host does: ec/annotations/manual-fan-ctrl-0751.md
    §6 decodes the handler at `0x888D` as checking `0x0F5D = 0xFD` and
    `0x0F5E = 0xC9` as a magic, reading `0x0F5F` as a table selector accepted
    only in 1..3, and then copying two 0x30-byte tables into `0x0F00` and
    `0x0F30`; windows/vendor-ec-map.md records the same handshake from
    `RefreshDefaultFanTable` and calls the mailbox the last three GPU duty
    slots, which is where they sit inside the row `SetEcFanTable` writes at
    `0x0F50-0x0F5F`. §3's main arm runs with the vendor service up, so a mode
    switch is exactly when a host poke there is possible. Under §4.2's
    heading such a difference would read as the one result §4.2 exists to
    look for -- the EC reloading its own table -- where the annotation says
    on static evidence that the trigger is the mailbox, on explicit host
    request, and the selector is never read from `0x0751`. A difference there
    is a host request and/or the tail of a table that was written; which of
    those it was is the run's question, and neither is §4.2's, which asks
    about the `0x0F00-0x0F5C` bytes above.

    The bucketing is `report_window`'s, unchanged: the four watched groups,
    then the §4.4/§4.5 context bytes printed and not graded, then everything
    else named for the human. No third category -- a byte's membership in one
    bucket is the same question here as it is per window.

    A §4.4/§4.5 group the pair's addresses do not cover is named *not
    covered by this pair* as well, on the §4.1-§4.3 branch's reasoning: §3
    dumps one range per pair, so the temperatures are in neither the `0x0700`
    nor the `0x0F00` one, and silence under a heading that promises them
    reads as "nothing moved" when it means "never read". A group the pair
    does cover but that held still still prints nothing -- that is the
    windowed read's silence, not this branch's, and the §6 fixture never
    reaches it.

    Pairs are grouped by the block they name, the way `report_dumps` groups
    the dumps, and a `--block` run takes no read from another block's. The
    bracket is wider than the window and answers the same question, so a
    pair filed under the wrong block is a result about the wrong bytes: the
    two `a0`/`10` pairs in the two-value fixture read the same two bytes in
    the opposite order and print byte-identical brackets, so nothing in a
    bracket's body distinguishes them and the group line above it is the
    whole of the attribution. The heading is unchanged for the reason
    `report_dumps` gives: both §4.6 readers in the test suite cut the
    section on it.

    Returns how many pairs were actually compared, so the closing summary
    cannot report a whole-block read for a run that took none -- a `--block`
    run handed only another block's pairs is 0.
    """
    print("\n=== whole-block dump pairs (§4.1-§4.3) ===")
    if not pairs:
        print("  no dump pair given (--dump-pair); the whole-block read is not "
              "checked")
        return 0
    fallback = block_value if block_value is not None else wrote
    groups = []
    for pair in pairs:
        value, how = dump_pair_block(pair[0], pair[1], fallback)
        # Grouped on the pair's own reading rather than on the value alone, so
        # a group line cannot claim that a file it holds says something it does
        # not: `report_dumps` can only mix `name` and `flag` in one group, and
        # both of those have to name the same value, while a pair also has the
        # one-name and disagree shapes.
        for value_, how_, here in groups:
            if (value_, how_) == (value, how):
                here.append(pair)
                break
        else:
            groups.append([value, how, [pair]])

    graded = 0
    for value, how, here in groups:
        if how == "disagree":
            # Before the `value is None` line, which would be false for it:
            # these two files name a value each, and it is their disagreement
            # that leaves the pair with none to be filed under.
            print("  the two file names name different blocks, so this pair is "
                  "one of neither and is not compared; which two they name is "
                  "printed with it below")
        elif value is None:
            print("  no block named: these files carry no §6 <value> and "
                  "neither --block nor --wrote was given")
        elif how == "name":
            print(f"  block 0x{value:02X}, from the <value> in these files' "
                  "§6 names")
        elif how == "one-name":
            print(f"  block 0x{value:02X}, from the <value> in one of these "
                  "two file names; the other carries none")
        else:
            print(f"  block 0x{value:02X}, from --block/--wrote; these files "
                  "carry no <value> of their own")
        if how == "disagree":
            for before_path, after_path, _, _ in here:
                b, _ = dump_block(before_path, None)
                a, _ = dump_block(after_path, None)
                print(f"\n    {before_path} -> {after_path}: the before side "
                      f"names block 0x{b:02X} and the after side 0x{a:02X}; a "
                      "pair is one block's before and after, so there is "
                      "nothing here to read. Pass the two dumps of one "
                      "range.")
            continue
        if block_value is not None and value != block_value:
            for before_path, after_path, _, _ in here:
                print(f"\n    {before_path} -> {after_path}: belongs to block "
                      f"0x{value:02X}, not the block under test "
                      f"(0x{block_value:02X}) -- not read for §4.1-§4.3 here")
            continue
        for before_path, after_path, before, after in here:
            if os.path.realpath(before_path) == os.path.realpath(after_path):
                # Path identity, not the before-/after- naming: a pair is
                # whatever the operator says it is, and the same file twice is
                # the one input error this flag cannot see on its own. Grading
                # it would print "unchanged" for every address, which is a true
                # statement about nothing -- the file agrees with itself by
                # construction. Flagged and skipped rather than fatal, so the
                # window report and the §4.6 readback the operator also needs
                # still get printed.
                print(f"\n  {before_path} -> {after_path}")
                print("    both sides are the same file, so this pair is not "
                      "graded: a read compared with itself proves nothing. "
                      "Pass the before and after dumps of one range as two "
                      "different files.")
                continue
            graded += 1
            common = sorted(set(before) & set(after))
            moved = [a for a in common if before[a] != after[a]]
            print(f"\n  {before_path} -> {after_path}, {len(common)} "
                  "address(es) compared")

            only_before = sorted(set(before) - set(after))
            only_after = sorted(set(after) - set(before))
            if only_before or only_after:
                print("    coverage gap, not a change: whatever moved in the "
                      "part one of these does not cover is outside this read.")
                print("      before dump only: "
                      + (" ".join(f"0x{a:04X}" for a in only_before)
                         or "none"))
                print("      after dump only:  "
                      + (" ".join(f"0x{a:04X}" for a in only_after)
                         or "none"))

            for name, addrs in WATCHED:
                hits = [a for a in moved if a in addrs]
                if not any(a in addrs for a in common):
                    # The fan table is not in a 0x0700 dump and the PLs are not
                    # in a 0x0F00 one, and the 0x0400 pair covers none of
                    # §4.1-§4.3 at all, so §6's pairs each cover some of
                    # §4.1-§4.3 and not all. Silence there would read as
                    # "nothing moved".
                    print(f"    {name}: not covered by this pair")
                elif not hits:
                    print(f"    {name}: unchanged across the block")
                else:
                    print(f"    {name}:")
                    for a in hits:
                        print(f"      0x{a:04X}  0x{before[a]:02X} -> "
                              f"0x{after[a]:02X}")
                    for line in group_note(name):
                        print(line)
                    if name == "fan table (§4.2)":
                        for line in note_lines(FAN_TABLE_NEXT_STEP):
                            print(line)

            # `None` is a group this pair's addresses do not reach at all, kept
            # apart from one that is reached and held still: "never read" is a
            # different answer from "read and did not move", and the
            # temperatures are in neither the 0x0700 nor the 0x0F00 dump, so
            # the two bytes §4.5's comparison rests on would otherwise vanish
            # under a heading that promises them. A reached group that did not
            # move stays silent, as it does per window. `context_groups` rather
            # than `groups` because the block grouping above is still being
            # walked by name.
            context_groups = []
            for name, addrs in CONTEXT:
                if not any(a in addrs for a in common):
                    context_groups.append((name, None))
                else:
                    context_groups.append(
                        (name, [a for a in moved if a in addrs]))
            context_groups = [(name, hits) for name, hits in context_groups
                              if hits is None or hits]
            if context_groups:
                print("    fan duty / temperature bytes (§4.4/§4.5) -- "
                      "context, not graded here:")
                for name, hits in context_groups:
                    if hits is None:
                        print(f"      {name}: not covered by this pair")
                        continue
                    print(f"      {name}:")
                    for a in hits:
                        print(f"        0x{a:04X}  0x{before[a]:02X} -> "
                              f"0x{after[a]:02X}")

            others = [a for a in moved
                      if not any(a in addrs for _, addrs in WATCHED)
                      and not any(a in addrs for _, addrs in CONTEXT)]
            if others:
                print(f"    other addresses that differ ({len(others)}), "
                      "not graded here -- read them against §4.4 and §4.5 "
                      "by hand:")
                print("      " + " ".join(f"0x{a:04X}" for a in others))

    if block_value is not None and not any(v == block_value
                                           for v, _, _ in groups):
        print(f"  no --dump-pair was given for block 0x{block_value:02X}, so "
              "the whole-block read for it was not taken; the pairs named "
              "above are another block's")

    print("\n  Every `unchanged` above says the byte did not differ between "
          "these two reads, which is not a claim that it did not move inside "
          "the block: §5, a byte that does not move inside a window may "
          "still move at the next suspend, AC transition or EC reset. This "
          "bracket is complementary to the windowed CSV read above, not a "
          "stronger one -- a byte that moved and was back where it started "
          "by the after-dump reads unchanged here whether or not the "
          "captures recorded the move, and a byte that moves entirely "
          "between two of ec_watch.py's sweeps is in no change row at all. "
          "Neither gap is closed by the other read. `0x0F5D-0x0F5F` is a "
          "bucket of its own for the reason printed under it, and §4.2's "
          "prediction is about the `0x0F00-0x0F5C` bytes above it.")
    return graded


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+",
                    help="ec_watch.py --mark --csv capture(s), one per "
                         "watcher, and never the same file twice -- the "
                         "cross-console checks key off how many captures "
                         "there are, and a file listed twice is one console "
                         "agreeing with itself. By resolved path, so ./x.csv "
                         "and x.csv are the same repeat")
    ap.add_argument("--dump", action="append", default=[], metavar="FILE",
                    help="ecrw.py dump output; repeat for before- and after-")
    ap.add_argument("--dump-pair", action="append", nargs=2, default=[],
                    metavar=("BEFORE", "AFTER"),
                    help="one range's ecrw.py dump before/after pair, as §3's "
                         "steps 0 and 6 take it; repeat per range, and never "
                         "the same file twice -- a pair read against itself "
                         "proves nothing and is not graded. Read for the "
                         "whole-block report and independent of --dump, whose "
                         "§4.6 readback still comes from the last of that "
                         "block's --dump flags. Pairs are grouped by the "
                         "block they name, and --block scopes that report as "
                         "it scopes the --dump one: a pair of another "
                         "block's is named and not read")
    ap.add_argument("--wrote", metavar="VALUE",
                    help="the value written to 0x0751, spelled as --block "
                         "takes it (0xA0, A0 or a0); must agree with --block "
                         "when both are given, since both name the value "
                         "under test")
    ap.add_argument("--block", metavar="VALUE",
                    help="grade one block of a multi-block capture by the "
                         "value its write mark carried -- 0xA0, A0 and a0 are "
                         "the same block -- taking the windows from that "
                         "block's no-op control arm through its restore, and "
                         "report that block's §3 verdict alone, so the output "
                         "can be attached per block; default is every block")
    args = ap.parse_args(argv)

    paths, repeats = distinct_captures(args.csv)
    if repeats:
        # Refused, where a `--dump-pair` naming one file twice is only flagged
        # and skipped, and the asymmetry is the shape of the report rather
        # than a difference in how much the input is trusted: a repeated pair
        # is one entry among several, so dropping it still leaves a window
        # report and a §4.6 readback worth printing, while every section of
        # this report is about the captures -- the census, the agreement
        # checks, the void check. A skip would hand back a report that is
        # quietly a single-capture run, which is the thing the operator has to
        # be told about rather than left to infer. A wrong command line is
        # fatal elsewhere here too (--wrote, --block, a --block in no block),
        # and this is one. None of which is a claim about the machine: it is
        # a claim about which files were handed in, before any of them is
        # read.
        for given, first, resolved in repeats:
            if given == first:
                print(f"\n{given!r} is given twice, and both times it is "
                      f"{resolved}.", file=sys.stderr)
            else:
                print(f"\n{given!r} and {first!r} are both {resolved}.",
                      file=sys.stderr)
        print("A capture given twice is one console and not two, so nothing "
              "was read: the census would have counted it twice, the "
              "cross-console checks would have run with a file agreeing with "
              "itself, and a mark that file did not record would have read as "
              "recorded. §6 passes one CSV per watcher; pass each of them "
              "once.", file=sys.stderr)
        return 1

    wrote = parse_value(args.wrote) if args.wrote else None
    if args.wrote and wrote is None:
        print(f"\n--wrote {args.wrote!r} is not a value: the value written to "
              "0x0751 is hex, with or without the 0x (0xA0, A0, a0).",
              file=sys.stderr)
        return 1

    captures = []
    marks, changes = [], []
    for path in paths:
        m, c = read_capture(path)
        captures.append((path, m))
        marks += m
        changes += c
        print(f"{path}: {len(m)} mark(s), {len(c)} change row(s)")

    if not marks:
        print("\nno MARK rows in these captures. ec_watch.py writes them only "
              "when --mark and --csv are both given; without them a byte that "
              "moved 400 ms after the write and one that moved 40 s after it "
              "cannot be told apart, and §4 cannot be applied.", file=sys.stderr)
        return 1

    windows = build_windows(marks, changes)
    blocks, unplaced = assign_blocks(windows)
    unreads = unplaceable_marks(unplaced)
    for block in blocks:
        block.problems = check_block_marks(block, captures)

    selected = None
    if args.block is not None:
        wanted = parse_value(args.block)
        if wanted is None:
            print(f"\n--block {args.block!r} is not a value: the value under "
                  "test is hex, with or without the 0x (0xA0, A0, a0).",
                  file=sys.stderr)
            return 1
        if wrote is not None and wrote != wanted:
            print(f"\n--block 0x{wanted:02X} and --wrote 0x{wrote:02X} name "
                  "different values. Both are the value under test for this "
                  "run, so one of them is a wrong command line; pass the same "
                  "one twice or neither.", file=sys.stderr)
            return 1
        selected = next((b for b in blocks if b.value == wanted), None)

    report_census(captures, windows, blocks, unplaced, unreads, selected)

    if args.block is not None and selected is None:
        found = ", ".join(b.name for b in blocks) or "none"
        print(f"\n--block {args.block!r} is not a block in these captures: "
              f"the values under test are {found}. A value that is not one of "
              "them is not graded as an empty one -- a mistyped --block would "
              "otherwise print a clean report over the wrong block's marks.",
              file=sys.stderr)
        return 1

    if selected is None:
        shown = list(range(len(windows)))
        end = None
        print(f"\n=== {len(windows)} window(s), one per mark ===")
    else:
        # Selected by which block each window belongs to, not by counting the
        # blocks before this one: `assign_blocks` leaves the windows it could
        # not place in the same list, so a range of that length runs short by
        # however many of them come first, and prints a window in no block in
        # place of this block's own restore -- the census says of such a
        # window that `--block` cannot select it, and printing it anyway
        # would be the mis-attribution this tool exists to stop.
        shown = [i for i, w in enumerate(windows) if w.block is selected]
        # The windows keep their place in the whole mark stream rather than
        # being renumbered from one, so a `--block` run is a subset of the
        # whole-capture run and the two attachments can be read side by side.
        end = (f"the end of block {selected.index} of {len(blocks)}, which is "
               "where this read stops")
        print(f"\n=== block {selected.index} of {len(blocks)}, value under "
              f"test {selected.name}, {len(shown)} window(s) in it ===")

    # The union over the windows, in WATCHED order: which watched groups saw a
    # change row at all. The closing paragraph has to name them, because a
    # mailbox poke and a fan-table move are different answers and "at least
    # one of §4.1-§4.3 moved" reads the same for both.
    moved_groups = []
    withheld = 0
    for i in shown:
        w = windows[i]
        if w in unreads:
            # A label this cannot read is a window it cannot say what it is a
            # window of. An unplaced mark whose label *is* readable -- a stray
            # restore, a control arm whose write never came -- is graded
            # below, with `unplaced` on its header: its rows are real and
            # there is no other arm to mis-file them under.
            withheld += 1
            report_withheld_window(w, i + 1, len(windows), "unplaced",
                                   unreads[w])
            continue
        if w.block is not None and w.block.problems:
            withheld += 1
            report_withheld_window(
                w, i + 1, len(windows),
                f"{w.block.name} (block {w.block.index} of {len(blocks)})",
                [text for _, on, text in w.block.problems if on is w])
            continue
        for name in report_window(w, i + 1, len(windows), w.block,
                                  len(blocks),
                                  end if i == shown[-1] else None):
            if name not in moved_groups:
                moved_groups.append(name)

    # The windows the loop above actually printed. `len(shown)` and not
    # `len(windows)`: it is the denominator the withheld banner already uses,
    # so the two counts agree by construction, and on a --block run it is that
    # block's own windows rather than the whole mark stream's.
    graded = len(shown) - withheld

    void = report_blocks(blocks, selected)

    # Both file lists are read before either is printed, so §4.6 can name a
    # --dump-pair that covers 0x0751 while it is saying the readback was not
    # taken. The print order is unchanged and is the one §6 documents: the
    # per-window read, then 0x0751 across the dumps, then the whole-block
    # bracket on the same §4.1-§4.3 bytes.
    dumps = [(p, read_dump(p)) for p in args.dump]
    pairs = [(b, a, read_dump(b), read_dump(a))
             for b, a in args.dump_pair]
    report_dumps(dumps, wrote, pairs,
                 selected.value if selected is not None else None)
    graded_pairs = report_dump_pairs(
        pairs, selected.value if selected is not None else None, wrote)

    print("\n=== what this does and does not settle ===")
    if withheld:
        print(f"  {withheld} of the {len(shown)} window(s) above were not "
              "graded: the mark set of the block they fall in does not hold, "
              "or no block could be attributed to them at all. What they "
              "would have shown is not reported here and is not to be quoted "
              "from this run.")
    if moved_groups:
        print(f"  At least one of the §4.1-§4.3 bytes moved after a mark: "
              f"{', '.join(moved_groups)}.")
        if withheld:
            # The movement is a fact about the windows that were printed, and
            # over a run that withheld some, it is the attribution below it
            # that decides what the fact is evidence of. Scoped here and not
            # left to the banner, so a reader who reads only the movement
            # line cannot take it for the whole run.
            print(f"  That is the {graded} window(s) that were graded. The "
                  f"{withheld} window(s) withheld above are not part of it, "
                  "and what they would have shown is not reported here.")
        if moved_groups == [TRIGGER_GROUP]:
            # The trigger group alone, with no table byte: the difference is
            # the mailbox the host writes to ask for a copy, and reading it
            # as the mode byte reloading the table is the attribution the
            # split exists to stop -- here in the windowed reader.
            print("  That is the host-written reload mailbox, not a §4.2 "
                  "result: ec/annotations/manual-fan-ctrl-0751.md §6 decodes "
                  "the handler at 0x888D as requiring 0xFD/0xC9 and a 1-3 "
                  "selector there, and reads the selector from 0x0F5F and "
                  "never from 0x0751 -- so on static evidence a mode change "
                  "alone does not reload the table. The vendor service writes "
                  "that mailbox, so which arm it happened in is the first "
                  "thing to record.")
        else:
            print("  That contradicts the static prediction in "
                  "ec/annotations/manual-fan-ctrl-0751.md §5 if it is the "
                  "PLs, or §4.2 if it is the fan table -- capture it in "
                  "full, it is the more interesting outcome.")
    elif graded == 0:
        print("  No window in this run was graded, so this output says nothing "
              "about §4.1-§4.3 for it -- which is the honest answer here, and "
              "not a quiet one.")
    elif withheld:
        # Some windows and not all. The clean sentence below is a claim about
        # the capture; over a subset of its windows it is a claim about the
        # subset, and the whole difference between the two is in a phrase that
        # does not name the windows. So the fact is stated over the windows
        # that were read, the withheld ones are named as outside it, and the
        # run-level comparison is declined rather than quietly narrowed -- the
        # overclaim `docs/findings.md` §4 is a record of.
        #
        # The clause about `confirmed-inert` names the withheld *window* and
        # not the block it sits in, because the two withholding paths above do
        # not agree on whether there is one. A window refused for its block's
        # mark set is in that block; a window refused for an unreadable label
        # is in no block at all, and the census has just said so in the same
        # run ("a mark this cannot read is a mark no block can be attributed
        # to"). So the sentence this branch ends on is the one fact both paths
        # support -- the run is not a three-value read -- and it declines to
        # say which of them happened rather than picking the one it was
        # written against.
        print(f"  None of the §4.1-§4.3 bytes moved in any of the {graded} "
              f"window(s) that were graded: that is what those {graded} "
              f"windows show, and the {withheld} window(s) withheld above "
              "are not part of it. The static prediction is a claim about the "
              "whole capture, and this output does not make it over a run it "
              "only read part of -- a run in which every window was graded is "
              "what would. §7's `confirmed-inert` needs all three values, and "
              "a window this report refused to read is one this run cannot "
              "speak for -- whether it sits in a block of its own is not "
              "something this output can say -- so the paragraph below is as "
              "far as this run goes.")
    else:
        print("  None of the §4.1-§4.3 bytes moved in any window: consistent "
              "with the static prediction, for this capture's window only "
              "(§5: a byte that does not move inside the window may still "
              "move at the next suspend, AC transition or EC reset).")
    if graded_pairs:
        print("  The whole-block dump pairs above were read as a second, "
              "wider bracket on the same §4.1-§4.3 bytes. That is two "
              "brackets, not two results: each has a gap the other does not "
              "close, and neither grades the duty or temperature bytes the "
              "pairs happen to print.")
    print("  Any fan duty and temperature bytes printed above are "
          "context, not a result: 0x075B/0x075C are the vendor's "
          "ADDR_EC_MAIN_FAN_L/R_DUTY_BYTE (issue #123), which the Control "
          "Center only reads, and a fan's duty moves with the die "
          "whether or not anything wrote 0x0751 -- which is what §3's no-op "
          "control arm measures, and what this script cannot. CPU package "
          "power (§4.5) is in no EC sweep and is still read by hand.")
    print("  §7 keys `confirmed-working` on fan duty or package power moving "
          "under a fixed load, so this output is an input to that call and "
          "not the call itself. `confirmed-inert` as a standalone control "
          "additionally needs all three values, with and without the vendor "
          "service (§3a).")
    # Five ways a run can be refused rather than graded, and they are five
    # facts about the input rather than five verdicts about the machine: a
    # block short its restore, a mark set that cannot support its windows, a
    # label the block walk could not place, a --block that named no block, and
    # a capture named twice.
    return 1 if (void or unreads or withheld) else 0


if __name__ == "__main__":
    sys.exit(main())
