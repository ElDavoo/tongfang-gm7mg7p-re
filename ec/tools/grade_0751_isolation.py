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
`0x0751` holds the written value in the after-dump and what the before-dump
held (§4.6).

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

A byte with no change row in a window is a line of zeros, not a missing line:
absence would read as missing data, and "no line" is the shape a correct
`confirmed-inert` answer takes. What the zero does not carry is the other
half, and it is the half that decides the status call: the figures are
arithmetic over the rows this capture holds, so they say what was recorded
between these samples and nothing about the byte between them. `ZERO_SCOPE_NOTE`
is that sentence, in the words both printed homes and the runbook's §4.4, §6
and §7 use -- the `--dump-pair` paragraph below states the same fact from the
other end, over the wider bracket.

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
it, whose after file is what §6 says to pass last. The pair it names is one
that can be read: a refused pair is named with the reason instead, and the
walk goes on past it, so one mistyped entry cannot hide a later pair that is
a usable bracket. The other precondition is stated on the same terms: when no
file name and neither flag names the value that was written, the comparison has
nothing to be against and the section says that too, on the dumps alone,
because no file can stand in for a number the way one can stand in for a
missing dump. And the before-side is read, for the same reason: `still` claims
the byte survived the write, which is a statement about what it held before it,
so when the block's first `--dump` already holds the value that was written --
or when only one `--dump` was handed in for the block at all -- the section
drops the word and says which of the two it is, the file that would support it
being the before-dump whose `0x0751` byte `report_dumps` printed two lines
above. And a file that cannot be opened is on those same terms: the path and
the OS error are printed in the section that would have read it, nothing is
compared over it, and the run carries on -- the readback is a fact about two
files on disk, and a mistyped path is a fact about the command line rather
than about the machine. The unreadable `--dump` keeps its place in its block's
list with nothing behind it rather than being dropped from it, because the
readback is taken over the block's last one and deleting an entry would
promote the dump before it into that place. None of these is a claim about the
machine; each is a claim about which files were handed in and what those files
can be read as saying.

One thing is read that is not a byte at all: §3's per-block integrity check.
§3 calls that check mechanical and then leaves the operator to eyeball it
against the mark list `ec_watch.py` prints at stop. Here the marks are grouped
into blocks -- one per write under test, opened by the step-2 no-op control
arm, carrying the stage boundaries §3's steps 2, 3 and 4 mark, and closed by
the step-5 restore -- and each block's last mark has to be that restore *in
every capture that recorded any mark in it*. That last clause is the whole of
issue #450 and it is not a formality: the block's last window is a fused group
of whatever the three consoles recorded, so a restore that reached two of them
and missed the third made the block read as closed on the strength of one of
the two. Which of the three it missed is not fixed -- it is whichever failed to
record the mark, and `closers_note` names that one rather than assuming it.
`0x0700` is the one that matters *when it is the one missed*, because of §3's
three `--start 0x0700 --len 0x0100`, `--start 0x0F00 --len 0x0060` and
`--start 0x0400 --len 0x0060`: it is the only sweep that covers `0x0751`, and
so the only one that can hold the byte's own change rows, which such a capture
holds with nothing in it saying which arm they belong to. A block whose last
mark is not the restore in some or all of the captures is `void` or `PARTIAL`:
the capture cannot show the byte being put back in the console that took it
elsewhere, so its last window never closes there. It is printed as such, by
name, with the label it did end on, the captures behind the verdict, and the
exit code is not zero. Its windows are withheld like any other block that fails
a mark check: each prints a `not graded` line naming the capture that ends the
block where, and the block's own line reads `-- NOT GRADED, its windows are not
printed`.

**A mark is a stage boundary as often as it is a write.** Three of the six
rounds §3 asks for in a block are not writes at all: `settled`, `held` and
`watch over` name a stage, carry no `0x0751=` value, and exist because a
window runs from one mark to the next -- so the end-of-watch mark is what
closes the write's ~60 s observation window, and without it the write's window
runs on into the `restored` write that §4.4's control-vs-write comparison is
then taken over. A boundary carries no value, so it cannot name a block; it
joins the one already open, or waits for the next `write` the way the control
arm does, and a block reads `settle, control, hold, write, watch, restore`
with `--block` selecting all six of its windows. **They are optional, not
required.** A capture carrying only the three action marks grades exactly as
it always did -- the probe's own two-mark capture, and every fixture under
`ec/tools/testdata/0751-isolation-run-*/` but the staged one, included -- and
what it costs is the write's window, which the block's `roles` line says on its
face rather than a check refusing the run.

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
rather than written down, before any window is printed: every mark recorded
in every capture, every capture spelling it the same way, every block's last
mark its restore *in each capture*, and every label one of the forms §3
fixes. A boundary is one mark like any other here, so a `watch over` one
console missed or that two spelled differently withholds its block's windows
on exactly the terms a `write` would. A block that fails any of those checks
is summarised where its windows would be and the windows are not printed --
they are correct as arithmetic and wrong as evidence about a labelled action,
and printing them in the usual format is the defect. The census that carries
the diagnosis is printed whole either way, and names which capture is short,
which two disagree, and what the consequence is.

**A verdict is a statement about every capture or it is not one.** The three
consoles are three processes reading three ranges, and each mark is typed into
one of them by hand, so nothing about a mark's presence is shared: one console
recording it is not two, and `coalesce_marks` joining the labels hides that
rather than repairing it. `block_verdict` therefore reads each capture's own
closing mark off the block, and every block line names the captures its word
rests on -- a block that closed in all three and one that closed in one of
three read differently for that reason alone, and only the first is one a
fold-in can file.

**One `#` row is a record about the run rather than an annotation of it.**
`read_capture` skips every row whose first field starts with `#`, so an
operator can annotate a capture by hand, and that skip is load-bearing. The
probe's `except BaseException` handler writes exactly such a row when a run
stops part way through, and the restore is in a `finally`, so the block still
holds its restore: a write window cut at 5 s passes the void check and grades
in the same format as one that ran its hold, which is the false green that row
is in the file to stop. The row is told apart by the phrase it opens with and
given a timestamp, which is the only thing that can say which arm it cut
short. A placed row is charged to the block whose window it falls in, withholds
that block's windows and turns the exit code to 1; a row that cannot be placed
refuses the run. A hand-written `#` row opens with something else and is
skipped, as §6's annotations are. None of this is a claim about the machine.

The census also names each block by the value its `write` mark carries, so a
window list, a `--dump` pair and a §4.6 verdict can all say which block they
are about. §6 stamps every dump with the `<value>` of the block it belongs to,
and a per-block invocation is meant to be attached per block, so `--block`
takes that value rather than a position in the mark stream: `0xA0`, `A0` and
`a0` are the same block. A value that is in no block is an error rather than
a run that grades everything, a `--block` and a `--wrote` that name different
values are an error too -- both name the value under test -- and so is a
value in *two* blocks, which is what §3's own remedy for a void block produces
when the re-done block is appended to the set rather than run on its own
`<date>`: the census names every block carrying it whatever run was scoped to,
and `--block` is refused on it. Only the run over the whole day has its exit
code held at 1 by that, whether or not either of them is void; a `--block` run
over one of the day's unambiguous values still grades that block and exits 0,
on the scope `void` and `withheld` already take.

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
(`../../windows/tools/ec_watch.py:211-214` against the close at `:330-332`),
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
per capture; marks within `MARK_MERGE_SECONDS` are one window, not several. The
gap each of those joins was made on is recorded and reported, so a group that
closed just inside the window reads differently from one that closed
comfortably inside it. That is a report and not a refusal: §3's three consoles
are supposed to fuse, and the distance is there for a reader to judge the join
by, not as grounds for a new exit code.

**The other side of that boundary is the one that costs a day.** Three consoles
marking one action 7 s apart is not a group that fused; it is three groups, so
each console's mark opens its own window and the two that follow read as
captures that never recorded the action at all. Nothing above says a mark was
lost, and the mark-set check's `missing` sentence -- correct for a capture that
really did not record it -- says it anyway, sending the operator after a
watcher that exited early rather than after three consoles that were a few
seconds slow. So the marks of the same action that fell *outside* the join are
recorded too, as `boundary_gaps`, one per capture, and when every capture a
window is short a mark for did record that action within `MARK_SPLIT_SECONDS`
of it the sentence is replaced by one that says what is true: the consoles were
marked further apart than the merge, here is how far, redo the block. The two
arms are the point -- a capture that recorded the mark and a capture that did
not send the operator to different terminals.

**A window's `total` carries no time base of its own.** §4.4's comparison is
the duty byte's total movement under the control arm against its total
movement under the write, and a byte that drifts for 30 s and one that drifts
for 3 s have totals that are not two answers to the same question. Every
window therefore prints its span, and a span outside the band §3's own pacing
implies says what that costs the comparison. It is a report and not a
refusal, as the gap above is: the window is graded on the rows it holds and
the exit code does not turn on how long it ran. The last window of a capture
is a lower bound rather than a length, because `ec_watch.py` writes a row when
a byte changes and a quiet tail after the last one is in no row at all.

**The closing section has four cases, not two.** A run that graded nothing
says so, a run that graded every one of its windows -- and every one of those
is a window of a value under test -- reports its movement and compares it to
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

**A window this run read is not automatically a window of a value under
test.** The fourth case is the one where nothing was withheld and nothing needs
to be: a mark the block walk could not place opens a window that is graded --
its rows are real, and there is no other arm to mis-file them under -- and
that window is a window of nothing, because the labels are the only thing that
attributes a window to a block. So a plain unscoped run over a day with a
stray mark in it can print "consistent with the static prediction" over a set
that is not the whole capture's windows of anything. The closing section counts
those windows, beside the note for a mark that could not be read at all, and
declines the capture-level comparison over the rest: the "nothing moved"
reading by narrowing the claim to the windows that do belong to a value under
test, the "something moved" one by naming these windows as part of the set the
movement is a claim over -- a union of group names over the windows printed,
which is not a set it can narrow to -- and by declining the attribution
underneath it over the capture rather than over them. A `--block` run makes the
count structurally zero rather than by a guard -- `shown` is that block's own
windows, and a window in no block is in none of them -- so the count never
competes with the selected-block case below it. A day with a stray mark in it
is not the three-value read either, and now says so rather than reading as one.

Nothing here touches hardware; it reads files only.

`--self-test` runs this tool's own committed suite,
`test_grade_0751_isolation.py`, and hands back its exit code: the entry point
every tool in `check_ghidra_tooling()` has, and the one
`docs/ci/agent-gates-0751-self-test.patch` prepares for that gate to call --
prepared rather than landed, so nothing runs it per commit yet. It is
dispatched before the parser rather than after, because `csv` is a required
positional and relaxing it to `nargs="*"` would give up the bare run's exit 2
-- and the refusals are what this tool is for, so a mode that made a command
line with no capture in it a passing run would be one of them. `call_graph.py`
and `grade_name_basis.py` dispatch after parsing only because neither has a
required positional. The suite runs in a subprocess rather than being imported,
because it loads this file a second time under the name `grade`; two copies of
one module in one interpreter is the ordering accident
`docs/findings.md` §16 is written about.

Usage:
    python3 ec/tools/grade_0751_isolation.py capture-0700-07ff.csv \
        [capture-0f00-0f5f.csv] [capture-0400-045f.csv] \
        [--dump before-0700.txt] [--dump after-0700.txt]
    python3 ec/tools/grade_0751_isolation.py capture.csv --wrote 0xA0
    python3 ec/tools/grade_0751_isolation.py capture.csv --block 0xa0
    python3 ec/tools/grade_0751_isolation.py capture.csv \
        --dump-pair before-0700.txt after-0700.txt \
        --dump-pair before-0f00.txt after-0f00.txt
    python3 ec/tools/grade_0751_isolation.py --self-test

A capture this cannot read is refused by name and not raised out of. The one
input the format does not cover is a probe console log from before
`manual_fan_ctrl_probe.py --csv`, which is free-form text rather than rows;
`ec/tools/probe_log_to_capture.py` converts one into this schema, and says in
the file it writes that the timestamps in it are reconstructed.
"""
import argparse
import csv
import datetime
import io
import os
import re
import subprocess
import sys
import textwrap

MANUAL_FAN_CTRL = 0x0751

# The suite `--self-test` runs, and the directory it is discovered in. Absolute
# so the mode works from any cwd, and named by file rather than by
# `test_*.py` so the gate's cost is this suite's and not the whole directory's
# -- `ec/tools/` holds other suites.
SUITE_FILE = "test_grade_0751_isolation.py"
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))

# How close two marks have to be to count as one action. The procedure holds
# ~30 s between the control arm and the write and ~60 s before the restore, so
# this only has to be wide enough to cover pressing Enter in each of three
# consoles; a window that opened twice for one action would report "nothing
# moved" for half of it.
MARK_MERGE_SECONDS = 5

# How wide a gap has to be, of that window, before a fused group is called
# close -- a floor and not a ceiling, which is the whole point of it. The
# committed three-console fixture puts one action at 12:00:10, :11 and :12,
# so being three consoles costs ~1 s per adjacent pair and a group that fused
# for that reason alone is comfortably inside, which is not the case a reader
# needs warning about. 4.0 s is a hesitation rather than a press, and it sits
# 1 s short of the edge at which the group would have been two windows, so
# that edge is named rather than left to the reader to compute. Deliberately
# not `MARK_MERGE_SECONDS`: every group here is already at or under that by
# construction, so a threshold equal to it would call every group in every
# report close. Deliberately not `grade_gpu_door.py`'s `CLOSE_MARKS_SECONDS`
# of 5 either -- that one equals its own window meaningfully only because
# that grader does not fuse, so its number says nothing about where a fuse
# came close.
CLOSE_GAP_SECONDS = 4.0

# How far a mark of the *same* action may sit outside the merge window and
# still read as that action having been marked too slowly rather than as a
# capture that never recorded it. §3 says to mark each console "within a few
# seconds of each other" and paces the arms themselves ~30 s apart, so 15 s is
# transcribed from that: half the shortest stretch the procedure leaves
# between two of its own marks, past which a mark is more plausibly the next
# arm than a slow press on this one. A judgement rather than a measurement --
# no run of the day has been timed, and the number is here to be moved when
# one is.
#
# Deliberately not `MARK_MERGE_SECONDS`, and for a stronger reason than
# `CLOSE_GAP_SECONDS` gives: a mark inside the merge window is *joined* by
# construction, so there is no mark of the same action inside it and a
# threshold equal to it could never fire. The distance this bounds is the one
# on the other side of the boundary, where every mark of the same action is by
# definition further away than the merge.
MARK_SPLIT_SECONDS = 15.0

# The band a window's span is expected to land in, as a floor and a ceiling
# rather than a target. Both are transcribed from §3 and are judgements, not
# measurements, for the reason `MARK_SPLIT_SECONDS` gives.
#
# The floor is §3's own "~10 s settle" -- the shortest stretch of time the
# procedure budgets for anything, so a window shorter than it is one the
# operator closed faster than the procedure's own pacing, and §4.4's two arms
# are then not two windows of a comparable length.
#
# The ceiling is §3's `--seconds 240`, the whole of what one set of three
# watchers runs for. A window the watcher opened cannot be longer than that,
# so a real `--seconds 240` day does not reach it: what does is a capture that
# was cut short, edited, or written by something other than that watcher, and
# the freeze-and-thaw hole `evidence/README.md` records for a suspend is the
# shape that would land one. The band is a floor and a lid rather than a
# target because §3 sets a length for neither end of the stream.
SPAN_FLOOR_SECONDS = 10.0
SPAN_CEILING_SECONDS = 240.0

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
# per block would be noise on a three-value run. The `PARTIAL` clause is here
# rather than in a note of its own because the two are the same finding over
# more or fewer consoles -- a block whose restore reached some of them is short
# it, and the operator's next move is the same.
#
# The last sentence is a second run rather than a redo appended to this one,
# and that is the whole of the change from the sentence it replaces. §3 fixes
# the three CSVs as one file for all three blocks, so "redo the void block"
# read as an instruction to append a fourth block of the same value into the
# set this run is already refusing -- a state the census above now names and
# `--block` refuses, and one this note used to send the operator into. The
# remedy a re-done block needs is a `<date>` of its own, which is what §3's
# `<date>` placeholder and §3a's own note already do for a second pass.
VOID_BLOCK_NOTE = (
    "A void block is short the restore mark §3's step 5 makes, so its last "
    "window never closes and the block is not a finished one. The usual cause "
    "is the mark itself: ec_watch.py writes a mark into the CSV only while "
    "the sink is open, so a restore typed after the watcher has exited is "
    "printed in its `marks:` list and recorded nowhere else -- which is why "
    "this reads the CSVs and not that list. A block marked PARTIAL is short "
    "the same mark in some of the captures and not the others, which is the "
    "same hole over fewer consoles: the block line names the ones that ended "
    "elsewhere, and their rows for the missing arm are filed under whichever "
    "window their timestamps fall in. Run the block again per §3, on "
    "its own <date> and its own set of the three CSVs rather than appended to "
    "this one: a second block of a value already in this set stops the value "
    "naming a block, which the census above names and the exit code reflects. "
    "The exit code is 1 while any block is void or partial.")

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

# §6's label forms, spelled as §6 spells them, for the message that quotes
# them back at a mark the parse could not read. The operator cannot fix an
# unplaceable mark from a description of the problem; the forms are the whole
# of what has to change. Three of them name a write and carry a value; three
# are the stage boundaries `MARK_FORMS` gives no value to.
REQUIRED_LABEL_FORMS = ("no-op wrote 0x0751=0xA0", "wrote 0x0751=0x10",
                        "restored 0x0751=0xA0", "settled", "held",
                        "watch over")

# The leading word of each form, the role it makes the mark, and whether the
# form carries a `0x0751=` value. Ordered so that `no-op wrote ...` reads as
# the control arm rather than as the write under test: §3 spells the control
# arm out that way precisely so the two cannot be confused, and the grader
# reading it the other way round would undo the point of the prefix.
#
# The last three take no value, and are the reason the flag is here: a
# boundary is the bare word, where every action form has to be followed by
# `0x0751=...`, so a matcher that required a trailing value could not read
# one at all -- and a form table that said so had to be able to say which
# forms are exempt. The stage boundaries come last because no action word
# prefixes one of them; the order between them is the order §3's block runs in.
MARK_FORMS = (("control", "no-op", True), ("restore", "restored", True),
              ("write", "wrote", True), ("settle", "settled", False),
              ("hold", "held", False), ("watch", "watch over", False))

# The roles that name a stage rather than a write, read off `MARK_FORMS` so
# the two cannot disagree about which forms carry no value. `parse_mark`
# returns `(role, None)` for one of these and `assign_blocks` files it against
# the block rather than opening a value under test with it.
BOUNDARY_ROLES = tuple(role for role, _, takes_value in MARK_FORMS
                       if not takes_value)

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

# The `#` row `windows/tools/manual_fan_ctrl_probe.py` writes when its run
# stops part way through, and the one `#` row this reads: a record *about* the
# run rather than an annotation *of* the capture. `read_capture` skips every
# `#` row so an operator can annotate a file by hand, and that skip is the
# invariant this row is read beside rather than through -- a hand annotation
# does not open with this phrase, and one that did would be the operator
# saying so.
#
# Two spellings of one phrase, one in each file, and they cannot share a
# constant: this tool cannot import the probe, because `ecrw` binds kernel32
# at import time and that import is Windows-only. What holds them together is
# the probe's offline suite and its `--self-test`, both of which read this one
# by path -- the arrangement `arm_labels` and `REQUIRED_LABEL_FORMS` already
# use. A drifted tag is not a quiet failure: `read_early_exits` would match
# nothing, and every capture of a crashed run would grade as one that finished.
EARLY_EXIT_TAG = "# the run ended early:"

# The passing case, in as many words, because the block section is the one
# place in this report that carries no address and would otherwise be the one
# place a reader could mistake for a result.
INTACT_BLOCK_NOTE = (
    "Every block's last mark is its restore, so the capture is complete "
    "enough to read. That is a statement about what was captured and not "
    "about what the EC did: nothing here is a §7 verdict, and a void block "
    "is a hole in the record rather than a finding about a register.")

# A label the parse could not place, and the one refusal `--block` does not
# narrow. Scoping it to the selected block would be the wrong direction rather
# than the smaller one: the run is holding a block the unreadable label may
# have been a `write` for and cannot name, and that label may instead have been
# a `restore` between a block's write and its restore, which would leave the
# selected block void where a scoped refusal would print it `intact` and exit 0.
# `unplaceable_marks` is where that is reasoned, and this is where the reader
# is told so.
UNREAD_MARK_NOTE = (
    "A mark this cannot read is a mark no block can be attributed to, and "
    "the labels are the only thing that says which block a window is a "
    "window of: one the parse cannot place could have been a write -- in "
    "which case the capture is holding a block this run cannot name -- or a "
    "restore typed between a block's write and its restore, which would "
    "close that block early and leave it void rather than intact. So a "
    "capture carrying one cannot be read block by block: --block narrows "
    "what is graded, not what is known, and this refusal holds for the "
    "whole run whichever block was selected. The census above names every "
    "mark the parse could not read, per capture; the fix is the label, which "
    "has to be one of the forms §6 fixes. The exit code is 1 until "
    "they do.")

# The window that was read and is a window of nothing, which is the one gap
# the banner above is not about: nothing here was refused, so there is no
# refusal for the banner to name, and the rows are real. What a mark in no
# block leaves unknown is the *arm* its window is a window of -- the labels
# are the only thing that attributes a window, which is the same reasoning
# `INTACT_BLOCK_NOTE` and `MARK_SET_NOTE` are written on. A static claim about
# what an unattributed window would have shown is not made here either, so
# nothing in it is a verdict about the machine.
#
# It ends at the count on purpose. It is printed above the whole
# `moved_groups` / `withheld` / `graded_unplaced` chain, and which of those
# sentences follows it is not its to decide: the movement line, the withheld
# branch and the no-block branch carry three different denominators, and one of
# them carries none at all. A "the claim below is over the other N" sentence
# here was true of exactly one of them and false of the other two -- on a run
# that also withheld a window it sat above a sentence claiming *all* `graded`,
# unattributed ones included, which is the overclaim this note exists beside.
# The scope is stated by the branch that owns the sentence instead, so a
# reader never has to take the denominator of a claim from a line that does not
# carry one.
UNPLACED_GRADED_NOTE = (
    "{unplaced} of the {graded} graded window(s) above are in no block: a "
    "window is a window of a value under test only by the mark that opened "
    "it, so these rows are real and the arm they belong to is unknown, and "
    "the static prediction is a claim about the whole capture. The census "
    "above names each of these by timestamp and label, in no block and so "
    "beyond what `--block` can select.")

# The withheld banner's reason and its refusal, split out because the banner
# names its count over two different denominators and the rest of the sentence
# is one sentence either way. A `--block` run reads its own block's windows and
# the day's mark stream is larger, so `len(shown)` is not `len(windows)` there
# -- and the banner used to say "of the 2 window(s) above" directly under two
# headers numbered 4/8 and 5/8, which is false about the windows printed above
# it. The per-window headers and the section header are *not* renumbered to
# match: the whole-stream numbering is what makes a `--block` run a subset of
# the whole-capture run (§6 runs one `--block` per value and reads the
# attachments side by side), and the section header's own count is simply true
# -- the block does have 2 windows. So the banner names both denominators
# instead, and the one it names first is unchanged for a whole-capture run,
# where the two coincide by construction and the existing wording is correct.
#
# The reason is left saying every withholding reason on both paths, even
# though `--block` can only reach the first two of them: it is one sentence and
# narrowing it would be a claim about which path this run took, which the loop
# above the print is what decides. The refusal at the end is the load-bearing
# half and survives both, so what a withheld window would have shown is not
# quotable from either kind of run. The early-exit reason is the second clause
# for the same reason the third is there: a `--block` run is graded by its own
# block, and a crash in a different block's capture is not this run's exit
# code, but the banner cannot say which of its windows were withheld for which
# reason without becoming a table.
WITHHELD_REASON = (
    "the mark set of the block they fall in does not hold, or that block's "
    "capture records the run ending early inside it, or the window falls in "
    "no block at all and either no label could be read for it or the captures "
    "disagree about the action it opened. What they would have shown is not "
    "reported here and is not to be quoted from this run.")

# The block section's note for a block withheld for an early exit rather than
# for its mark set. A block like that is intact by the check above -- the
# restore is there, because the probe's `finally` puts it back whether or not
# the run got to its hold -- so the note that explains a mark set would be
# explaining a failure this block did not have, and a reader who has been sent
# to fix a missing mark would be sent to a console that recorded all of them.
EARLY_EXIT_NOTE = (
    "A block whose capture records the run ending early inside it is withheld "
    "for the same reason and a different one. What it is short is not a mark "
    "but the hold the arm was to run for: the restore is there, so the check "
    "above passed, and the one row that says the run stopped is the whole of "
    "the record of how far it got. Its windows are left out rather than "
    "printed in the usual format and quoted -- a window that ran five seconds "
    "of a thirty-second hold reads exactly like one that ran all of it, which "
    "is the false green the row is in the file to stop -- the section above "
    "names the row, the window it fell in and the block, and the exit code is "
    "1 while the row is there. Redo that block per §3; the other blocks in "
    "the same capture are not affected by it and still print.")

# The one refusal this adds, and it is the whole run rather than one block: a
# row that cannot be placed against a window says nothing about any arm, so
# every window below would be a window of a length nobody could name. The
# exit code is 1 and nothing is printed, which is the register the
# repeated-capture refusal and the "no MARK rows" refusal are written on --
# each a statement about which files were handed in, none of them about the
# machine.
EARLY_EXIT_REFUSAL = (
    "A row saying a run ended early has to be placed against the window it "
    "cut short, and these rows cannot be placed: {why}. So the run is refused "
    "rather than partly reported: a window is a window of a value under test "
    "only by the mark that opened it, and a window whose length this cannot "
    "bound is not quotable as one. Nothing in these captures is reported and "
    "the exit code is 1 until the rows place. The row the probe writes is "
    "stamped -- see windows/tools/manual_fan_ctrl_probe.py's "
    "`except BaseException` -- so a row that carries no timestamp is a "
    "capture written before that, or one annotated by hand, and the fix is to "
    "re-run the block or to put a timestamp of its own on the row.")

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

# What a zero on one of those lines is a zero of, in the words the two printed
# homes and the runbook's §4.4, §6 and §7 all carry. One constant because the
# claim is made in three places and cashed in at a fourth, and four spellings
# of it is four chances to fix the grammar and leave the gap.
#
# The gap: `ec_watch.py` writes a change row when a byte *differs* between two
# of its sweeps, so a capture is a log of recorded transitions rather than a
# sampling of levels. A duty byte that wobbles and returns between two sweeps
# is in no row, and what this tool knows about it is that no row was written
# -- not that it did not move. §3's own pacing note puts a number on the
# interval and declines to put one on the sweep: `--interval` is slept
# *between sweeps*, one sweep of the three watchers is 448 ECRR reads, and
# issue #94 owns how long that takes. So the per-byte period is `--interval`
# plus a duration nothing here measures, and the wider bracket that closes
# part of it is `--dump-pair` -- complementary, not stronger.
#
# The parenthetical token beside the figures (`(0 changes)`) is left as it is:
# it counts what the report counted, which is true, and two committed cases
# assert it literally. What the sentence adds is what the token does not say,
# which is the difference between "no row was written" and "the byte held
# still". No `--dump-pair` sentence needs it and the two readers that print
# these figures never print together, so it goes in neither.
ZERO_SCOPE_NOTE = (
    "A zero here is a zero of observed transitions, not a measurement of the "
    "byte: `ec_watch.py` writes a change row only when a byte differs between "
    "two of its sweeps, `--interval` is slept between sweeps rather than "
    "between bytes, and the per-byte sampling period is `--interval` plus a "
    "sweep duration nothing in this repo measures (issue #94), so a move that "
    "completes inside one sampling period is in no change row at all. The "
    "wider bracket, `--dump-pair`, closes part of that gap and is "
    "complementary rather than stronger."
)

# What the "other addresses" bucket prints under an address none of the two
# tuples above claims, transcribed from ec/annotations/registers.yaml for the
# same reason CONTEXT is transcribed: this is a report an operator runs
# against a capture and two dumps, and it takes no repository file as an
# input, so there is no path by which it could read the YAML. A name is
# copied here or not at all, and registers.yaml stays the one place a name
# is argued for.
#
# Each entry, keyed by its low address, is (partner, unit, headline).
# `partner` is the high byte of a little-endian 16-bit value registers.yaml
# defines, or None for a byte it defines alone; `unit` is what the assembled
# reading is in, empty where no unit is established -- which is itself the
# point for 0x0436. The six are the battery bytes on the 0x0400 page that
# the tuple above does not already carry: §3's main arm holds a fixed CPU
# load, and these are what a battery reads while it does, so the pair that
# dumps 0x0400-0x045F lands in this bucket on a real run whatever the
# capture held. Every one of them is `present-untested` in registers.yaml,
# so what is printed here is the name and the two bytes -- not a reading of
# what the EC does with them.
#
# A headline names what the byte is. The two derived bytes are not one
# thing: each named routine branches on a selector and computes something
# different on each branch, so a headline giving only one of them states as
# settled what registers.yaml's own note for 0x0448 already hedges ("0xBE
# when its selector is nonzero"). Both headlines therefore carry the
# branch, and the notes below carry the rest, naming
# ec/annotations/ghidra-functions.csv as the row that records it -- a
# register note is one path of the two, and the annotation row is where
# the second is written down.
XDATA_NAMES = {
    0x0434: (0x0435, "mA", "BAT_CURRENT_MA 0x0434/0x0435 -- battery current, "
             "little-endian mA"),
    0x0436: (0x0437, "", "XDATA_0436_PAIR 0x0436/0x0437 -- 16-bit, and "
             "deliberately unnamed (see below)"),
    0x0438: (0x0439, "mV", "BAT_VOLTAGE_MV 0x0438/0x0439 -- pack terminal "
             "voltage, little-endian mV"),
    0x0448: (None, None, "XDATA_0448 -- battery voltage / 100, computed by "
             "scale_0438_into_0448 (bank1 0xF416) when its selector is 0, "
             "and the constant 0xBE when it is not"),
    0x0449: (None, None, "XDATA_0449 -- battery current / 100, computed by "
             "store_scaled_quotient_0449 (bank1 0xF3D7) when its selector is "
             "0, and from 0x060C/0x060D when it is not"),
    0x044C: (None, None, "XDATA_044C -- the busiest byte on this page in "
             "evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv"),
}

# What a name on its own line cannot carry, printed under the entry when the
# pair reaches the bucket. Three shapes, one mechanism.
#
# 0x0436 is the entry whose name is withheld. registers.yaml records the name
# upstream gives 0x0436/0x0437 and declines it: in
# 2026-09-18-profile-switch-0400-07ff.csv the low byte steps by exactly +0x14
# every ~35 s, which reads as a counter rather than as a charge level. The
# name itself is not printed, because a report is something an operator acts
# on and this one has been retracted on this board; saying who proposed it
# and what refutes it is what is left. Every clause of that reason is scoped
# to the file that carries it, because the page has a second committed file
# and it does not say the same thing -- see the note. The experiment that
# would settle it is a live read beside WMI's RemainingCapacity (#172), and
# it has not been run.
#
# 0x0448 and 0x0449 are the two names that are printed, where what the
# headline cannot fit is which branch produced the byte and whether this run
# is on it. Both routines branch on R7 and neither sets it, so the branch is
# not knowable from a dump pair; the note says so rather than leaving the
# quotient reading as one unqualified kind of number. The 0xBE is in evidence
# rather than hypothetical -- the sweep summary's 0x0448 row ends on exactly
# it -- so a report that named only the quotient would be wrong about a value
# a committed file has already recorded.
#
# The premise of that last clause held and its conclusion did not, which is
# the shape issue #358 found here. 0xBE is in evidence; it is also a quotient
# the computed arm produces, at a dividend of 19000-19099. The note therefore
# keeps the sentence it always printed and carries the correction beside it,
# dated, rather than editing a sentence operators have already read -- the
# report is the deliverable here, not the YAML, so a retraction that stopped
# at ec/annotations/registers.yaml would leave the tool contradicting it.
XDATA_NAME_NOTE = {
    0x0436: (
        "The name upstream gives this pair is not printed, and the reason "
        "is one file's, not the page's. In "
        "evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv the low "
        "byte steps 0x70 -> 0x84 -> 0x98 -> 0xAC -> 0xC0, exactly +0x14 "
        "every ~35 s, which is a periodic ramp rather than a charge "
        "reading, and that file has no 0x0437 row. The other committed "
        "file covering this page, "
        "evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv, "
        "summarises a window the first does not cover: it records 13 "
        "changes of 0x0436 and 1 of 0x0437, so the high byte does move "
        "somewhere, and it supports that change count and those two "
        "endpoints and nothing else, the 32,499-row log behind it not "
        "being committed. Neither file says what the value is, so no unit "
        "is claimed for it here either. The name stays a placeholder "
        "until a live read puts the pair beside WMI's RemainingCapacity "
        "(issue #172, not run); ec/annotations/registers.yaml carries the "
        "record."),
    0x0448: (
        "The quotient above is one of two things the named routine writes "
        "here, and this report cannot say which one a run took. "
        "scale_0438_into_0448 branches on R7: at 0 it reads 0x0438/0x0439 "
        "and divides by 100, and at any nonzero value it reads nothing at "
        "all and writes the constant 0xBE. That branch is recorded in the "
        "bank1,0xF416,scale_0438_into_0448 row of "
        "ec/annotations/ghidra-functions.csv, and it is what "
        "ec/annotations/registers.yaml's XDATA_0448 note carries as the "
        "parenthetical it does. R7 is set nowhere in that listing or in "
        "the 0x198A it calls, so the origin of the selector is not "
        "established and neither is the branch. The constant is not a "
        "hypothetical: evidence/ec-watch/2026-09-18-ac-plugin-sweep-"
        "summary.csv carries 0x0448,4,0x8B,0xBE, so a committed file has "
        "already recorded this byte ending a window on exactly 0xBE. Read "
        "0xBE as the branch the routine took and not as a voltage. "
        # The sentence above is left as written and corrected underneath,
        # per the reasoning in the block comment over this table: this is
        # printed to an operator, so the retraction has to reach the output
        # and not only the repository.
        "Correction (2026-10-03, issue #358): the sentence above reads "
        "0xBE as the branch and not as a voltage, and that is too strong. "
        "0xBE is 190, and 190 is a quotient 0xA5E6 produces for a "
        "dividend of 19000-19099 at divisor 100, so the computed arm can "
        "produce this byte too. Every voltage recorded for this pack is "
        "below that window, so the constant arm is still the likelier "
        "reading of a committed 0xBE and nothing here claims which arm "
        "ran; what is retracted is only that the value cannot be a "
        "voltage."),
    0x0449: (
        "The same branch, and the same gap. store_scaled_quotient_0449 at "
        "R7 = 0 reads 0x0434/0x0435 and divides by 100, and at any nonzero "
        "value it calls bank1 0xF3C9 instead, which reads 0x060C/0x060D, "
        "masks the high byte, multiplies by 10 and divides by 0x22 or 0x44 "
        "according to bit 6 of SYSTEM_ID (0x0456) -- a different pair and "
        "a different divisor, neither of them the battery current. That "
        "call is recorded in the bank1,0xF3D7,store_scaled_quotient_0449 "
        "row of ec/annotations/ghidra-functions.csv, and the bit-6 "
        "dependence is recorded under SYSTEM_ID in "
        "ec/annotations/registers.yaml; the XDATA_0449 note there carries "
        "the first path and not this one, which is why the branch is named "
        "here as well. The selector's origin is not established either. So "
        "the name above is the selector-zero path, and a value on the "
        "other is a different computation of a different pair rather than "
        "a second reading of this one."),
}


def xdata_name_lines(addr, common, before, after):
    """The register name for one "other" address, and the value it makes.

    Empty for an address this table does not name, so the naming is
    additive: an address registers.yaml gives no name to prints exactly as
    it did before this table existed, a bare `0xNNNN` on the flat list and
    nothing under it. Most of a dump is such an address, and the table is
    an aid rather than a claim that every address on the page has one.

    The 16-bit value is little-endian and assembled from the pair's own two
    dumps. Both halves are in `common` whenever the low one is, so the high
    byte's *unchanged* value is a byte this section has already read rather
    than a new one, and the assembly is the subtraction registers.yaml
    describes, done once here instead of by eye at the terminal. It is
    printed when `common` holds both halves and skipped otherwise, since
    `common` is the intersection and a byte one dump does not reach is the
    coverage gap the section already prints above.
    """
    entry = XDATA_NAMES.get(addr)
    if entry is None:
        return []
    partner, unit, headline = entry
    lines = [f"      0x{addr:04X}  {headline}"]
    if partner is not None and partner in common:
        lo = before[addr] | before[partner] << 8
        hi = after[addr] | after[partner] << 8
        suffix = f" {unit}" if unit else ""
        lines.append(f"        0x{lo:04X} -> 0x{hi:04X}"
                     f"  ({lo} -> {hi}{suffix})")
    if addr in XDATA_NAME_NOTE:
        lines.extend(note_lines(XDATA_NAME_NOTE[addr]))
    return lines


class Change:
    def __init__(self, ts, addr, old, new, source):
        self.ts = ts
        self.addr = addr
        self.old = old
        self.new = new
        self.source = source


class EarlyExit:
    """One `#` row saying a run stopped, and when it stopped.

    `ts` is the whole of what makes the row worth reading: a window is a
    window of an arm only by its position in the mark stream, and a row that
    says *that* a run ended rather than *when* cannot be said to cut any arm
    short. It is None for a row carrying no timestamp this can read, which is
    the shape a capture written before the probe stamped its row has -- kept
    rather than dropped, because a row this cannot place is refused and a row
    it never returned would be a false green.

    `reason` is the rest of the row verbatim. Nothing here parses it and
    nothing here claims to know who wrote the row: the tool name the probe
    puts in it is for whoever opens the file.
    """

    def __init__(self, ts, reason, source):
        self.ts = ts
        self.reason = reason
        self.source = source


class Window:
    """One mark and everything that changed before the next mark."""

    def __init__(self, ts, label, source):
        self.ts = ts
        self.label = label
        self.source = source
        self.changes = []
        self.levels = {}
        # How long the window is, in seconds, from its own mark to the mark
        # that closes it -- or for the last window of a capture to the last
        # row the capture holds, which is a lower bound and not a length.
        # `span_is_bound` is what tells the two apart and is read by
        # `span_note` and by the line `report_window` prints: a bound that is
        # small says the window was *at least* that long and nothing more, so
        # nothing may be concluded from its being under the band. Set by
        # `build_windows`, which is the only place that knows where the next
        # mark is.
        self.span = 0.0
        self.span_is_bound = False
        # The raw per-capture marks this window was merged from, the gap each
        # adjacent pair of them was joined on, the marks of the same action
        # that fell *outside* the join, and the block it fell in. All four are
        # set by `coalesce_marks` and `assign_blocks` rather than at
        # construction: a mark read out of a CSV has no block until the whole
        # mark stream has been walked, and `coalesce_marks` is the only place
        # that knows which raw rows one action was recorded as. The gaps ride
        # beside `marks` rather than inside it because a gap is a property of
        # the join -- of two consoles' rows together -- and not of either row.
        self.marks = []
        self.mark_gaps = []
        self.boundary_gaps = []
        self.block = None


class Block:
    """One §3 block: its stage boundaries, a control arm, a write under test,
    and its restore.

    `value` is what the block's `write` mark carried, and is what `--block`
    and the `block:` line take: the value under test is the one thing a
    window, a dump and a §4.6 verdict can all be named by. The three stage
    boundaries carry no value of their own, so a block that has them reads
    `settle, control, hold, write, watch, restore` on its `roles` line and one
    that has not reads the three actions alone; both grade, and the line is
    what says which a run was handed.
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
    def closers(self):
        """`(capture, that capture's last mark in this block)` per capture.

        Derived from the block's own marks rather than stored, so `block_verdict`
        needs nothing run over it first: a reader that builds a block from
        `assign_blocks` and asks what it closed on gets the answer rather than
        an empty record (`windows/tools/test_manual_fan_ctrl_probe.py` does
        exactly that). Storing it is the alternative and is worse twice over --
        it makes the verdict depend on a call the caller may not know it has to
        make, and it puts a second copy of this computation somewhere that can
        disagree with this one.

        The record exists because the fused last window is one console's answer
        in the grammar of three: `coalesce_marks` joins the labels and
        `parse_mark` takes the first that parses, so a block that closed on the
        restore in two of the three captures has the same last window as one
        that closed in all of them (#450). Every mark carries the capture it was
        recorded in, so the per-capture answer is available from the block.

        Keyed on `capture_key` for the reason that function gives: `m.source`
        is a path as given, and one file handed in under two spellings is one
        capture rather than two. The path printed is the one the *closing*
        mark carries, and the order is by each capture's *first* mark in the
        block, which is the order the operator typed them in and does not move
        when one capture's last mark lands later than another's.

        A capture that recorded no mark in this block is absent rather than
        present-and-empty: a block exists because a mark opened it, and that
        mark is in some capture.
        """
        first, last = {}, {}
        for w in self.windows:
            for m in w.marks:
                key = capture_key(m.source)
                if key not in first or m.ts < first[key].ts:
                    first[key] = m
                if key not in last or m.ts > last[key].ts:
                    last[key] = m
        return [(last[key].source, last[key].label)
                for key in sorted(first, key=lambda k: first[k].ts)]

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


# The byte-order mark, as the character a UTF-8 decode of `EF BB BF` gives
# it. Named because the alternative is three invisible bytes in a string
# literal in a loop, and a reader who cannot see what is being stripped
# cannot tell it from a typo.
BOM = "\ufeff"

# The same mark as bytes, which is the form the question is actually asked in:
# whether a *file* carries a BOM is a fact about its first three bytes, and
# `starts_with_bom` is the one place that question is answered.
BOM_BYTES = BOM.encode("utf-8")


def starts_with_bom(raw):
    """Whether `raw` opens with a UTF-8 byte-order mark.

    The one question, asked of bytes rather than of a decoded field, so
    there is one answer to check. `rows_from_bytes` normalises a leading
    U+FEFF off the first field of every row, because that is what the row's
    identity needs -- but a reader downstream of the stream therefore
    cannot see the mark, and the strict reader is the one that has to refuse
    the file over it. So it is asked of the bytes here, and both callers
    hand it a buffer they had to read anyway: `read_capture` off the single
    open it now makes and streams its rows from (#786), and
    `capture_snapshot` off the one it has made since #749. There is no
    second open that could be asked a third time, which is what the prose in
    `docs/findings.md`, `0751-capture-row-shape.md` and `ec_watch-marks.md`
    counted until #786."""
    return raw[:len(BOM_BYTES)] == BOM_BYTES


def bom_refusal(path):
    """The one sentence a capture carrying a byte-order mark is refused with.

    Returned rather than raised so both callers say the same words: the
    strict reader raises it, and `existing_mark_findings` reports the very
    same string as the file's refusal. That is the anti-drift contract the
    notice runs on -- the warning an operator reads and the error the
    grading raises are one verdict, not two that have to agree.

    The equality is held for a file that is *both* marked and not
    utf-8-decodable, because the mark is refused first on both sides, so
    this sentence is the one that names a file carrying two faults and not
    only a file carrying one. A function is the whole of that contract: the
    notice's reader cannot call `read_capture` (#749), so it cannot ask the
    reader what it would say and quote it -- the sentence has to be the same
    string for the two to be the same, and the *order* has to be stated in
    both places rather than discovered by running one of them. The order is
    pinned in `ExistingMarkLabelTests` at both inputs, by
    `test_a_leading_bom_is_refused_by_name_and_not_as_a_bad_hex_row` over a
    marked file that decodes and by
    `test_a_marked_and_undecodable_file_is_refused_by_the_mark` over one that
    does not -- the second of which carries the control that makes the order
    an assertion rather than a coincidence."""
    return (f"{path}: starts with a byte-order mark, so its first field is "
            f"'{BOM}ts' and not 'ts'. A capture is utf-8 with no BOM; "
            f"re-save this one without one.")


def normalised_rows(rows):
    """`rows` with a leading byte-order mark off the first field of each.

    The row's first field, normalised -- the other half of the shape
    `skippable_row` holds the other half of. Split out of `capture_rows` so
    the notice's one read (`capture_snapshot`, #749) and the four readers that
    stream a capture through `capture_rows` cannot disagree about what a first
    field may look like: a reader that normalised and one that did not would
    differ on exactly the file where it matters, and neither would raise.
    Applied to every row rather than to the first, and the reason is the
    format's: the first three bytes of a file are the only place one occurs
    in practice, so the two readings agree on every file that exists, and a
    uniform rule is the one that can be written down once."""
    for row in rows:
        if row and row[0].startswith(BOM):
            row[0] = row[0].lstrip(BOM)
        yield row


def capture_rows(path, errors=None):
    """Every row of one capture CSV, with the first field normalised.

    The one place that opens a capture from a path, and -- through
    `rows_from_bytes`, which this delegates the row shape to -- the one place
    the row shape is stated at all: `existing_mark_labels`,
    `refused_capture_rows` and `read_early_exits` reach it from here, and so
    do `read_capture` and `capture_snapshot`. Every one of them now reads a
    capture once and streams its rows off the bytes that read returned, so a
    capture has one moment rather than two on every path (#786;
    `capture_snapshot` had it in #749, the strict reader is the one that had
    two opens, and #767 gave `main` the same by reading one snapshot per
    capture rather than calling two readers over it).

    **`main` is not a caller of this**, and that is the shape rather than an
    omission: it reads one `capture_snapshot` per capture and hands the same
    row list to the strict rules and to `early_exits_of` (#767), so a capture
    `main` grades was opened once rather than once per reader.

    A stream and not a filtered iterator, because the readers do not agree on
    which rows to drop: `skippable_row` is the filter three of them apply,
    and `read_early_exits` keeps exactly the rows the other three skip --
    `EARLY_EXIT_TAG` opens with `#`, so a stream filtering here would drop
    every early-exit row. A generator rather than a list, so laziness still
    holds and an undecodable byte comes out of the loop at its row: reading
    the file into bytes is not decoding it, and `rows_from_bytes` is where
    the decode stays lazy.

    The codec is declared, not inherited: `utf-8`, the encoding the format
    is defined in, whatever the interpreter reading the file would have
    preferred, and it is why the single-byte-locale cases this stream used
    to have an opinion about are gone rather than merely rare: a cp1252
    capture's 0xE9, and the same three bytes read as `ï»¿` under one, are
    bytes the format does not contain, and whether this stream raises on
    such a byte or replaces it is the caller's decision. They are gone
    because #748 declared the codec at the four readers before this change,
    so the `ï»¿` reading is withdrawn by that rather than settled here.

    `errors` is that decision, passed straight through, and the two in the
    tree are deliberate and have to stay different: the strict readers
    (`read_capture`, `read_early_exits`) pass none and let a byte outside
    the format raise, and the two preflights pass `errors="replace"` so a
    capture saved by something else comes back with U+FFFD in a label the
    operator is being shown anyway, rather than taking down the run about
    to append to that same file.

    A leading U+FEFF is stripped from every row's first field by
    `normalised_rows`, and that is the row's *identity* rather than a repair:
    `EF BB BF` at offset 0 decodes under the declared `utf-8` to U+FEFF,
    which glues itself to the first field of the header and makes
    `row[0] == "ts"` false. Without the strip the header is a data row and
    the notice names the row carrying the column names as a row whose
    timestamp no reader can parse, with a fix-or-delete-the-rows-above
    remedy that offers the row holding the column names for deletion. It
    is also what lets `read_early_exits` see a first-line early-exit row the
    U+FEFF used to hide. With `capture_snapshot`'s pass over the one buffer
    the notice reads (#749), none of the reads the grader makes of a capture
    -- every reader in this module, all of them through `rows_from_bytes` --
    leaves a mark on a first field.
    **Two readers outside that scope are not covered**:
    `check_capture_encoding`'s `count` and `grade_timer_sweep.load` each
    spell the `ts`/`#` test out with no strip, so a BOM'd header is a data
    row to both, each a second copy of `skippable_row`.

    The strip is here rather than at the open as `encoding="utf-8-sig"`
    because the format declares utf-8 *with no BOM* and the strict reader
    refuses a file that carries one, by name (`read_capture`, through
    `starts_with_bom` on the buffer it read -- the mark is gone from the
    rows by the time it gets there, and `bom_refusal` is the one sentence it
    says). Pinning the codec retired the "the encoding is not this tool's to
    decide" question this paragraph used to turn on, and that was #748's
    doing at the readers rather than this change's; what is left of it is
    that the preflights still have to read such a file far enough to say what
    it holds, and the shape is what can say it.

    What it does not cover, now for a different reason than it used to: a
    U+FEFF somewhere other than offset 0, which the strict reader
    normalises rather than refuses -- the first three bytes being the only
    place one occurs in a file this format defines.
    """
    with open(path, "rb") as f:
        raw = f.read()
    yield from rows_from_bytes(raw, errors=errors)



def skippable_row(row):
    """Whether a capture row carries no data: a blank line, a `#` annotation,
    or the `ts,addr,old,new` header.

    The one definition of what makes a row skippable, called by
    `read_capture`, `existing_mark_labels` and `refused_capture_rows` -- the
    three that agree on it. `read_early_exits` does not and cannot; see
    `capture_rows`.

    Blank lines and `#` lines are skipped so an operator can annotate a
    capture by hand without breaking this, which is why `#` is a test of the
    first field rather than of the line: in a CSV a `#` opens a row, not a
    file.

    Deliberately only this much of the shape. The four-field test and the
    branch that decides a row is a mark are not one rule spelled four times:
    they are three different contracts -- a `ValueError` in `read_capture`,
    a tolerated short row in `existing_mark_labels`, a *named refusal* in
    `refused_capture_rows` -- and merging them would delete the preflight
    rather than state the shape once. `ExistingMarkLabelTests` holds the
    three to each other instead.
    """
    return not row or row[0].startswith("#") or row[0] == "ts"


def parse_ts(s):
    return datetime.datetime.fromisoformat(s)


def read_capture(path):
    """(marks, changes) from one ec_watch.py CSV.

    The strict reader, and the one the other three are written against: rows
    come from `rows_from_bytes`, the ones to drop from `skippable_row`, and
    what is left goes to `take_capture_row` -- this reader's one row, and the
    body the notice's strict pass runs over its own read (#749).

    **One `open()`, one read, one row list** (#786). This used to be two: a
    three-byte binary probe for the mark, then `capture_rows` opening the
    same file again to stream the rows. §3 runs three watchers on one `--csv`
    and `CsvSink.row` flushes every row, so a capture is a file with a second
    writer on it by design, and the two reads were two moments -- and the
    strict reader is where that costs the most, because `normalised_rows`
    takes the mark off the first field of every row, so a file re-saved
    between the two opens used to be graded as though it carried no mark: no
    refusal, and a verdict that disagreed with the notice's. The shape to do
    it in was already in this file, in `capture_snapshot` (#749).

    What the fold does **not** buy is a lock. One `open()` is one moment and
    the file is still moving after it; what it removes is the moment *inside*
    one read, where the mark and the rows could come from different files.
    `main` used to read the same capture twice over, through this and
    `read_early_exits`, and takes one `capture_snapshot` over both passes
    instead (#767) -- so this is no longer on `main`'s path at all, and the
    two-tuple this returns is a contract with the tools that unpack it rather
    than one `main` reads.

    `utf-8`, declared rather than inherited from the interpreter reading the
    file, and no `errors=`: a byte outside the format is a refusal of the
    file, not something to grade past. The writers declare the same codec
    (`ec_watch.py`'s `CsvSink` and the four other classes that write this
    shape), so the bytes are a property of the format and the same capture
    grades the same way whichever box reads it.

    A capture is utf-8 *with no BOM*, and this is where that is decided, so
    it is asked of the file rather than left to a row. `utf-8` is not
    `utf-8-sig`: `EF BB BF` at offset 0 decodes to a U+FEFF that glues
    itself to the first field, `skippable_row`'s `ts` test then misses, and
    the header would be graded as a data row and refused on
    `int("addr", 16)` -- a complaint about a hex literal on a line that is
    not a change, offered for deletion along with the rows above it. Named
    before any row is read, with the remedy, the way a decode refusal names
    the codec. `starts_with_bom` on the buffer rather than a test on the row
    because `rows_from_bytes` has already taken the mark off the first field
    by the time a row could be tested, and it is the file that carries it.

    *First* of the two file-level refusals, and now by construction rather
    than by program order: the mark is asked of the raw bytes before any
    decode is attempted, because a decode cannot start until the mark test
    has returned, so on a file that is both marked and not utf-8-decodable
    this is the sentence and `existing_mark_findings` names it there too.
    The mark is decidable from three bytes without the file decoding at all
    and the decode failure is not, and this reader has to have the mark
    before it reads a row. `bom_refusal`'s docstring is where that agreement
    is stated; this is where it is one side of.

    Whether the format should ever *accept* a BOM is a separate question
    this does not decide. What is decided is that a capture carrying one is
    refused legibly under the encoding declared here, and that the preflights
    -- which still read the file to say what it holds -- see the header as
    the header rather than as a bad row.
    """
    with open(path, "rb") as f:
        raw = f.read()
    if starts_with_bom(raw):
        raise ValueError(bom_refusal(path))
    marks, changes = [], []
    for row in rows_from_bytes(raw):
        if skippable_row(row):
            continue
        take_capture_row(row, path, marks, changes)
    return marks, changes


def existing_mark_labels(path):
    """(ts, label) for the mark rows `path` already holds, as `(text, str)`.

    A preflight, not a reader, and the difference is the whole contract: what
    is asked is which marks are already in a file a watcher is about to append
    to, and the answer has to survive a file this cannot grade. So it takes
    `skippable_row` -- `read_capture`'s rule, named once -- and none of its
    strictness. The timestamp is left as the text it was written as, a short
    mark row comes back with an empty label rather than a `ValueError`, and a
    change row is not parsed at all, so a hand-edited or half-written file is
    still something the caller can name. `read_capture` raises in
    `take_capture_row` -- on a short row, on a timestamp `parse_ts` cannot
    read -- and this must not: refusing to open a capture would be the wrong
    way to lose the one warning that says what is already in it.

    Nor may the file's *encoding*. The format declares `utf-8` and
    `read_capture` refuses a file that is not it, but a capture on the box
    is not necessarily one the format wrote: a file from before the codec was
    declared, one an operator annotated in an editor that saved something
    else, one another tool produced. `CsvSink` appends to the same path
    without ever decoding it, so those bytes are still here at startup. Under
    the declared codec and with iteration lazy, a lone 0xE9 -- a byte UTF-8
    cannot decode, and latin-1 and cp1252 both write for `café` -- raises
    `UnicodeDecodeError` out of the loop on the run that would otherwise have
    appended to that file fine. Hence `errors="replace"`: the byte comes back
    as U+FFFD inside a label the operator is being shown anyway, which is a
    smaller loss than the day, and the grading still refuses the file over the
    same byte. Declaring the codec made the strict reader's verdict a fact
    about the format rather than about the interpreter; it did not make this
    one lenient, because the notice's job is to survive the file the grading
    will not.

    Both that policy and the first-field normalisation live in
    `capture_rows`, so this cannot be strict about one and lenient about the
    other. The rows to drop come from `skippable_row` and none of this
    reader's strictness with them: a `#` row, a blank and the header are the
    same three here as in the reader whose rules they are, and a header whose
    first field carried a byte-order mark is still the header rather than a
    row whose timestamp nobody can read.

    The shape of a mark row is the grader's and lives here rather than in
    `ec_watch.py` for the same reason `parse_mark` does: the prompt loads this
    module by path precisely so no second copy of the rule can drift from the
    thing that enforces it (#548). What this spends on the *rows* is
    `mark_labels_of`, which `existing_mark_findings` also calls -- over the
    rows of its own single read, so a mark the notice lists is a mark it read
    in the same breath (#749).

    A published reader, not a test fixture, and three things outside this
    module's own suite are why. `measure_mark_provenance.py` holds this in
    the `families` oracle table and compares what it returns on a constructed
    file -- the census run as much as `--self-test`. `ec_watch.py`'s
    `load_label_vocab` reads this *name* off the grader, so a staged copy
    that predates it is refused by a message naming the path, and
    `test_ec_watch.py` holds what the staged one returns against this one.
    `ec_watch-marks.md` documents it as the reader the prompt reaches and as
    the extraction `existing_mark_findings` shares.
    """
    return mark_labels_of(capture_rows(path, errors="replace"))


def refused_capture_rows(path):
    """(accepted, refused) over one capture, by the rules `read_capture` at
    `take_capture_row` applies, for the rows its own reader never got to.

    Not a second reader and not a second rule. `read_capture` stops at the
    first row it cannot grade, so its exception names one row and the rest of
    a file that holds more than one bad row would be a fix-one, re-run,
    meet-the-next loop. The checks in `partition_capture_rows` are its, over
    the same `capture_rows` stream and behind the same `skippable_row` --
    `read_capture`'s short-row test and its `MARK` branch, re-applied rather
    than re-derived -- and that re-application is what lets the rows it never
    reached be named with the reason it would have refused each. It is the
    re-applied half, not the first reason, that the two readers share a body
    over: the first reason is `read_capture`'s own exception, which
    `existing_mark_findings` puts there rather than re-deriving it. What holds
    the re-applied half is
    `ExistingMarkLabelTests.test_the_refusal_reasons_are_read_captures_own`,
    which runs this over every fixture and asserts that first reason is the
    exception `read_capture` itself raised, verbatim. Tighten
    `take_capture_row` or `parse_ts` and that fails rather than the notice
    quietly disagreeing with the grading; the same test holds the ordering the
    rest is spelled in and the wording each refused row is named with.

    The order of the checks is `read_capture`'s, and it is load-bearing. It
    reads the timestamp before a change row's hex -- Python evaluates the
    arguments of its `Change(...)` left to right -- so a *change* row bad in
    both ways is refused here for the timestamp, which is the reason the grader
    will give rather than one picked here. A mark row is never hex-read at
    all: `read_capture`'s own body, `take_capture_row`, branches on
    `addr == "MARK"` before the `int()` calls, and so does this. That test
    holds this to the reader as well, through its last fixture: a change row
    bad in both ways and *not* the first bad row, because the first row's
    reason is `read_capture`'s own exception pasted over this one's and so
    cannot show which check ran first.

    `errors="replace"` as `existing_mark_labels` reads it, under the same
    declared `utf-8`, so a byte outside the format does not stop this either;
    the row is named with U+FFFD where the byte was, which is what the
    operator is shown anyway, and the grading still refuses the file over the
    same byte. A change row that parses is in neither list -- it is not a
    mark, and the notice is about the marks in a file and the rows that stop
    the grader reading it.

    A `# the run ended early:` row can never be refused here, and cannot be
    named by this: `skippable_row` takes it before the partition sees it, and
    it is not a mark row either, so it is in neither list. That is the shape
    working rather than a gap in it -- the row is read, by
    `read_early_exits`, and a crash row is a record about the run rather than
    a row of the capture.

    Neither can a header carrying a byte-order mark, and that is the case
    this shape was extended for. `read_capture` refuses such a file whole,
    before it reads a row; the mark comes off the first field in
    `capture_rows`, so here the header is the header, this returns nothing
    for it, and `existing_mark_findings` reports the reader's own refusal
    with no row attached -- rather than a complaint about `int("addr", 16)`
    against the row that carries the column names, which is what the
    partition said when the mark was still glued to the first field.

    The path here is the entry point, and the only part of this that opens
    anything: `existing_mark_findings` reads once and hands its own rows
    straight to `partition_capture_rows` (#749), so what is left of this is
    the open -- lenient, through `capture_rows` -- and a delegate. Three
    cases in `test_grade_0751_isolation.py` reach it:
    `test_the_shape_agrees_across_all_four_readers` partitions beside the
    other three readers, `test_on_a_file_the_strict_reader_refuses_the_
    partition_names_every_row` beside `existing_mark_labels` over the same
    path, and `test_a_change_row_bad_in_two_hex_fields_names_the_earlier_one`
    directly -- that last one because `existing_mark_findings` pastes
    `read_capture`'s own exception over the first reason, so the order of
    the checks is only observable through a path-taking entry that does not
    do that. **No program in the tree calls it**, and that is what a search
    of this tree finds rather than a claim that none ever will.
    """
    return partition_capture_rows(capture_rows(path, errors="replace"), path)


def take_capture_row(row, path, marks, changes):
    """`read_capture`'s one row, as its own loop body, appending to the two
    lists it would have appended to.

    Moved out rather than spelled twice because `existing_mark_findings` now
    runs the strict rules over rows it read itself (#749): a second copy of
    this body would be a second set of rules the notice could apply, and the
    whole of its value is that its verdict is the reader's. Same order, same
    exceptions, same messages -- it is the body, in a function of its own.

    The order inside the `Change(...)` call is load-bearing and is left exactly
    as it was: Python evaluates its arguments left to right, so the timestamp
    is read before the hex and a change row bad in both ways is refused for the
    timestamp. `partition_capture_rows` spells that order again to *name* the
    rows rather than stop at them, and
    `test_the_refusal_reasons_are_read_captures_own` holds the two together.

    The byte-order mark is *not* checked here, which is where #748 left it and
    where the row's own shape now disagrees. `rows_from_bytes` takes a leading
    U+FEFF off the first field of every row, so a row reaching this no longer
    carries one and the test would be dead in both callers; the mark is refused
    where it can be seen at all -- of the file, in `read_capture` through
    `starts_with_bom` on the buffer it read and in the notice through
    `capture_snapshot` -- with `bom_refusal`'s one sentence, so a file
    carrying one gets the refusal that names it on either path rather than a
    complaint about a hex literal from only one of them.
    """
    if len(row) < 4:
        raise ValueError(f"{path}: short row {row!r}")
    ts, addr, old, new = row[0], row[1], row[2], row[3]
    if addr == "MARK":
        marks.append(Window(parse_ts(ts), new, path))
    else:
        changes.append(Change(parse_ts(ts), int(addr, 16),
                              int(old, 16), int(new, 16), path))


def mark_labels_of(rows):
    """(ts, label) for the mark rows among `rows`, as `(text, str)`.

    `existing_mark_labels`' extraction, over rows rather than a path, so the
    notice lists the labels of the rows it read in its one open and the
    preflight lists the labels of the rows it read in its own (#749). The skip
    rule is `skippable_row`'s, which is the duplication #548 left and the row
    shape now owns; `test_the_skip_rule_is_read_captures_and_only_marks_
    come_back` plus `measure_mark_provenance.py --self-test` are what hold the
    four-field test and the `MARK` branch below to the reader's.
    """
    out = []
    for row in rows:
        if skippable_row(row):
            continue
        if len(row) > 1 and row[1] == "MARK":
            out.append((row[0], row[3] if len(row) > 3 else ""))
    return out


def existing_mark_provenance(path):
    """(ordinal, ts, label, provenance) for the mark rows `path` holds.

    `existing_mark_labels` with the position and the fifth column, and the
    two are one reader: a preflight that names a mark has to be able to say
    *which* mark, and a flat `(ts, label)` list cannot -- #719 measured that
    as the sharpest limit of the shape that was chosen over a comment row, and
    [its page](0751-mark-provenance-shapes.md) says so.

    **`ordinal` is a row ordinal and not a line number.** It is 0-based over
    every row `csv.reader` yields -- the header, the `#` rows and the blank
    lines included, all of which `skippable_row` drops below -- so a quoted
    field carrying an embedded newline is one position and two lines, and on
    a hand-annotated capture the two are different numbers. The ordinal is
    what a reader can produce from the rows it already has; a line number
    would have to re-open the file as text and re-derive the record
    boundaries `csv` is what decided them by.

    **`None` and `""` are different answers, and holding them apart is the
    whole of what the column is for.** A mark row carries three states and
    they must not collapse into two:

      * `None` -- the column is absent, so nothing was recorded. A file
        written before the column existed, or a `manual_fan_ctrl_probe.py`
        capture.
      * `""` -- the column is there and empty: a process that held no
        `--label-vocab` to record.
      * the text -- a process that held one, naming itself and the
        vocabulary.

    So a four-column mark row never reads as "this process did not hold the
    flag". It reads as *not recorded*, which is a weaker claim about a
    different thing, and a caller that read it the other way would turn a
    pre-change capture into evidence about a console that was never asked.
    That is the backward-compatibility case `ec_watch.Marker` writes the
    column always to keep reachable.

    **What a populated column is not.** It is *a process that said it was
    checking, wrote this*; it is not *this label was checked*. The
    per-label verdict is `parse_mark` and `unplaceable_marks`, which are
    per-label, already exist, and know nothing about who typed what. Neither
    shape of provenance moves that boundary, and a consumer that prints this
    as a checking verdict is reporting something false.

    A preflight, on `existing_mark_labels`' contract rather than
    `read_capture`'s: `capture_rows(path, errors="replace")` and
    `skippable_row`, so a short row, a timestamp `parse_ts` cannot read and a
    byte outside the declared codec all come back as something to name rather
    than as an exception. The file is one a watcher is about to append to, and
    a preflight that would not open it loses the one warning this exists to
    print. A two-column mark row comes back as `(N, ts, "", None)`.

    The skip rule and the mark branch are spelled here rather than shared,
    which is the duplication #548 left and the row shape still owns: the
    rule is `skippable_row` and the branch is a decision, and the three
    readers that have one keep a different contract for it. The guard
    against the two drifting is a test rather than a refactor --
    `MarkProvenanceTests` holds this to `mark_labels_of` over every committed
    fixture under `testdata/`, so a mark this reaches and a mark the notice
    lists cannot part.
    """
    out = []
    for ordinal, row in enumerate(capture_rows(path, errors="replace")):
        if skippable_row(row):
            continue
        if len(row) > 1 and row[1] == "MARK":
            out.append((ordinal, row[0], row[3] if len(row) > 3 else "",
                        row[4] if len(row) > 4 else None))
    return out


def partition_capture_rows(rows, path):
    """(accepted, refused) over already-read `rows`, by the rules
    `take_capture_row` applies, for the ones `read_capture` never got to.

    Takes rows rather than a path so `existing_mark_findings` can partition the
    rows of its single read beside the marks it placed from the same rows --
    the two lists the notice prints cannot then be describing two different
    files, because there is only one file in this function (#749). The rows are
    read through `capture_rows` by whoever opens the file, leniently, for the
    reason `existing_mark_labels` argues -- a preflight has to survive a file
    the grading will not -- which `capture_rows` states as its one split,
    strict readers bare and preflights `errors="replace"`. The skip rule is
    that same stream's `skippable_row`, so the shape is not spelled here a
    second time.
    """
    accepted, refused = [], []
    for row in rows:
        if skippable_row(row):
            continue
        if len(row) < 4:
            refused.append((row, f"short row: {len(row)} field(s), "
                                  "read_capture needs four"))
            continue
        ts, addr, old, new = row[0], row[1], row[2], row[3]
        try:
            parse_ts(ts)
        except ValueError as e:
            refused.append((row, "read_capture cannot read this "
                                 f"timestamp: {e}"))
            continue
        if addr == "MARK":
            accepted.append((ts, new))
            continue
        for field, text in (("address", addr), ("old", old), ("new", new)):
            try:
                int(text, 16)
            except ValueError as e:
                refused.append((row, f"the {field} of a change row is not "
                                     f"hex: {e}"))
                break
    return accepted, refused


def capture_snapshot(path):
    """(rows, decode_failure, has_bom) for one capture, from one `open()` and
    one read.

    The bytes are the moment, which is the whole of it. §3 runs three watchers
    on one `--csv` and `CsvSink.row` flushes every row, so a capture is a file
    with a second writer on it by design -- and two reads of it are two
    moments, microseconds apart or not. Whatever landed between them is a row
    one of the two answers has and the other does not.

    **Two callers, and between them they cover every read of a capture in the
    grading path.** `existing_mark_findings` has read this way since #749, and
    `main` does too (#767), which took the per-capture census line off two
    readers and onto one snapshot: the mark and change counts and the
    early-exit count in that one printed line are now off the same buffer
    rather than off two opens a few lines apart. What that does **not** buy
    is a lock -- a row landing after this read is still graded, by the
    whole-file grading `report_census` already tells the operator about.

    `open(path, "rb")` and one `read()`, so there is no second open to be a
    second moment. The decode is then the format's, through `rows_from_bytes`:
    the same `utf-8` `read_capture` declares (#748), over the same bytes, and
    through the same code path rather than a second one that happens to agree
    -- which is what #786 turned the containment the anti-drift suite holds
    from an observation about these two functions into a property of the one
    below them. The refusal this returns is the refusal `read_capture` would
    have raised over them, and it is raised before any row is looked at, which
    is what makes it a refusal of the file rather than of a row.

    On a file that decodes, `decode_failure` is None and `rows` is every row
    `csv.reader` reads. On one that does not, `decode_failure` is the
    `UnicodeDecodeError` the decode raised and `rows` is the *same bytes* read
    leniently -- for the listing only, since a strict verdict over a file this
    cannot decode is a refusal of the file, not a partial one.

    `rows` comes back normalised by `rows_from_bytes`, because the
    notice reads one capture and must not be the one place in the tree where a
    leading U+FEFF is still glued to a first field. Which is why the mark is
    reported rather than left in the rows: the stream strips it, and it is
    the strip that makes a BOM'd header the header -- so a reader downstream
    cannot see the mark, and the caller's job is to be told there was one.
    Asked of the buffer rather than of a second `open` of `path`, because this
    function is the one read (#749) and a third one would be a third moment.
    """
    with open(path, "rb") as f:
        raw = f.read()
    has_bom = starts_with_bom(raw)
    try:
        return (list(rows_from_bytes(raw)), None, has_bom)
    except UnicodeDecodeError as e:
        return (list(rows_from_bytes(raw, errors="replace")), e, has_bom)


def capture_lines(raw, **errors):
    """`raw` as the lines `open(path, newline="", encoding="utf-8")` would
    have iterated.

    A `TextIOWrapper` over the buffer rather than `raw.decode()` and a split,
    and the wrapper is the point rather than the convenience: the line
    splitting is part of the contract (`newline=""` is universal newlines with
    the terminators kept, so `\\r`, `\\n` and `\\r\\n` all end a line, and
    `str.splitlines` would break on a dozen characters that are perfectly
    legal inside a label), and declaring the *format's* codec here rather than
    inheriting this interpreter's is what makes a `UnicodeDecodeError` from
    here the one `read_capture` would have raised over the same bytes (#748)
    rather than one this tool decided to raise -- and the one it raises on
    every box rather than on the ones whose default happens to read the file.

    **A generator, and that is a change.** It used to be `readlines()`, which
    decoded the whole buffer before the caller saw a single line, and #786
    made that the wrong shape for a strict reader: an undecodable byte has to
    come out of the loop at the row it stopped on, so `read_capture` names
    one row rather than the whole file. Handing the lines over as they are
    decoded gives the caller the same lines in the same order and stops no
    further than the caller asked for, so the exception is the one that byte
    produced rather than one found in a whole-file decode. What that does
    *not* promise is that `position` in it is the file offset -- it is the
    decoder's own, over whichever chunk the byte landed in, and it is
    measured rather than assumed in
    `docs/findings/0751-strict-reader-two-moments.md`.
    """
    with io.TextIOWrapper(io.BytesIO(raw), newline="",
                          encoding="utf-8", **errors) as text:
        yield from text


def existing_mark_findings(path):
    """(accepted, refused, unplaceable) about a `--csv` a watcher is about to
    append to: the mark rows `read_capture` takes, the rows it will refuse the
    file over, and the marks its placement pass cannot place.

    The union of `existing_mark_labels`' contract (never raise on the content)
    and `read_capture`'s (decide by the strict rules), because the notice
    `ec_watch.py` prints at startup is only worth the operator's attention if
    the reason it gives is the enforcing reader's. A copy of `read_capture`'s
    rules spelled into the prompt would be right until the reader changed, and
    the operator would have fixed a row the grading accepts. So the strict
    rules are run first and their verdict is the verdict; the per-row
    conditions only name the rows the strict pass never got to.

    **One `open()`, one read, one row list, and all three lists out of it**
    (#749). This used to be two opens of a file three watchers are appending
    to by design, microseconds apart, and the two sections of one notice could
    describe two different files: a mark named in the placement section that
    the section above it does not list, or listed as accepted although the
    placement pass never saw it. `capture_snapshot` reads the bytes once and
    the strict rules, the label extraction and the partition all run over the
    rows of that one buffer.

    What that does **not** fix is the file moving. A mark that lands after
    this call is still graded, by the whole-file grading, which is what the
    closing paragraph below already tells the operator. It is also one
    `open()` and not one reader: the four-field test and the `MARK` branch are
    still per-reader, deliberately, because they are three different contracts
    rather than one rule spelled four times (`skippable_row`'s own docstring).
    What the row shape does own -- the skip rule and the first field -- is
    owned by `capture_rows`/`normalised_rows` and `skippable_row` for this
    loop too, and `ExistingMarkLabelTests` counts the opens, so the claim is a
    test rather than a promise.

    Three lists, and each answers one question:

    - `accepted` -- the mark rows the strict reader takes, as `(ts, label)`
      with the timestamp *as written*, which is #548's deliberate choice and
      the display an operator already reads. On a file `read_capture` accepts
      this is exactly `existing_mark_labels`, called rather than written out
      again -- `mark_labels_of` over the same rows -- so the success path
      grows no second label-extraction rule.
    - `refused` -- `(row, reason)` per row the strict reader raises on: a
      short row, a timestamp `parse_ts` cannot read, a change row whose hex
      does not parse. The first reason is `read_capture`'s own
      exception text verbatim, because that reader stops at the first bad row
      and its message is the error the grading will raise. `row` is None for a
      refusal that is the file's rather than one row's -- the encoding and a
      byte-order mark, below.
    - `unplaceable` -- `(ts, label, message)` for the marks `unplaceable_marks`
      reports, with *its* sentence, so the operator reads the same words the
      grading will print rather than a paraphrase of them.

    `unplaceable` is empty whenever the file is refused, and that is the whole
    of why: a label verdict needs a file the grader can read, and one it
    cannot read is already refused whole, so a second list would add nothing
    the refusal has not said. The notice prints one line in its place saying
    so, rather than leaving the operator to wonder whether the tool checked.

    `unplaceable` is a *group* verdict and not a per-label one, and the
    wording has to keep that straight. `coalesce_marks` joins the consoles'
    labels with `' / '` and `parse_mark` reads the first part that matches, so
    a window whose first label is `settled` places over a second console's
    unparseable one. What is reported is what `unplaceable_marks` returned:
    a whole window, or nothing.

    The encoding is the one thing here that is a property of the format
    rather than of the file, and it is why a byte can refuse a whole capture
    while a hand-edited timestamp refuses only a row. `read_capture` declares
    `utf-8`, so a capture in anything else is not this format's and is
    refused whole rather than decoded row by row -- a per-row decode would
    make the meaning of the file a property of this reader again, which is
    the failure the declaration removes. What the refusal below names is the
    `UnicodeDecodeError`'s *own* `encoding`: out of the decode that failed,
    so it cannot name a codec other than the one the format really used, and
    named from the one buffer this read rather than from a second `open()` of
    a moving file. It names the remedy with it, so an operator holding a file
    from another box is told what to do rather than shown a decode error and
    left to guess. The verdict reported is the one the format defines, so it
    is the same on every interpreter -- and the notice reports the verdict it
    observed rather than predicting one, which is the half of #748's
    correction that does not depend on what the codec turns out to be.

    A leading byte-order mark is the other refusal of the file rather than of
    a row, and it arrives the same way: `read_capture` raises before it reads
    anything, this function is told `has_bom` off the buffer it had to read
    anyway, and a file-level refusal short-circuits as the decode one below it
    does: the partition does not run, so a second bad row in the same file
    goes unnamed for the reason the second list is empty. For the notice, the
    reason names the mark and the remedy, no row is attached to offer for
    deletion, and every mark in the file is still listed.

    **Which of the two names a file carrying both is a rule, and it is the
    mark.** Each branch is a single-condition test over one buffer, so nothing
    forced an order, and the two callers had drifted apart: the strict reader
    asked the mark first, this one asked the decode first, and a file that is
    both a BOM'd and not utf-8-decodable got two sentences that disagreed
    about what was wrong with it. The mark goes first on both sides because it
    is the cheaper and always-decidable test -- three bytes, no decode -- and
    because it is the one the strict reader must have before it reads a row.
    The decode branch is still reached, by every file that has no mark and a
    byte the codec cannot read, and on those the two readers still differ by
    contract: the notice's reason contains the exception rather than being it,
    and the suite holds that separately.

    `build_windows` is deliberately not on the label path: it indexes
    `windows[0]`, so it needs a mark list and the change rows, and neither is
    what a label verdict is about. `coalesce_marks([])` and `assign_blocks([])`
    return empty without a guard, so an empty or mark-less file needs none
    here either -- and a file with no marks coming back empty is what keeps
    §3's block-1 start quiet.
    """
    accepted, refused, unplaceable = [], [], []
    rows, decode_failure, has_bom = capture_snapshot(path)
    if has_bom:
        # The mark is asked of the bytes this had to read anyway, and it is
        # asked *first*, before the decode below -- not for tidiness but
        # because `read_capture` asks it first too, and the two have to name
        # one file one way. The mark is a fact about the first three bytes,
        # decidable without the file decoding at all, and the strict reader
        # has to have it before it reads a row; the decode failure is the fact
        # that costs the whole buffer. So the cheaper and always-decidable test
        # goes first on both sides, and a file that is both a BOM'd and not
        # utf-8-decodable is named by `bom_refusal` on both -- the one
        # sentence, so the warning the operator reads and the error the grading
        # raises are the same words and the two cannot drift. This cannot call
        # `read_capture` to learn that, because the whole of #749 is that it
        # does not; the order is stated here and pinned by the case
        # `test_a_marked_and_undecodable_file_is_refused_by_the_mark` in this
        # module's own suite.
        #
        # The mark is off the first field by now, `capture_snapshot` having
        # applied the same rule `capture_rows` does, so the header is the
        # header and the marks below it are all still named: the reason and
        # the remedy come out, and the row carrying the column names is not
        # offered for deletion.
        refused.append((None, bom_refusal(path)))
        return mark_labels_of(rows), refused, unplaceable
    if decode_failure is not None:
        # A refusal of the file rather than of a row, and on firmer ground
        # than the lazy loop this replaces: the strict decode is over the
        # whole buffer, so a byte it cannot read means no row list came back
        # at all rather than one that stopped short of a row. The rows are
        # still named -- from those same bytes, read leniently, with U+FFFD
        # where the byte was, which is how the operator finds the byte that
        # stopped it. The codec is the exception's own `encoding` rather than
        # a re-derivation of what the format declares, so it is the answer
        # from the decode that failed and cannot disagree with it.
        #
        # Asked second, and that is not the same as retired: a file with no
        # mark and a byte the codec cannot read still lands here, and that
        # file is the one `read_capture` reports as the bare
        # `UnicodeDecodeError` rather than a sentence of its own. What the
        # reorder changed is only which of the two names a file carrying both
        # -- and `read_capture` names the mark there too, so the two agree
        # either way.
        refused.append((None, "the grader's reader cannot decode a byte of "
                              f"this file in the {decode_failure.encoding} a "
                              f"capture is defined to be, and raises before it "
                              f"reaches a row: {decode_failure}. A capture is "
                              f"utf-8; this one is written in something else. "
                              f"Re-save it as utf-8, or re-run the capture "
                              f"with a writer that declares the codec."))
        return mark_labels_of(rows), refused, unplaceable
    marks, changes = [], []
    try:
        for row in rows:
            if skippable_row(row):
                continue
            take_capture_row(row, path, marks, changes)
    except ValueError as e:
        accepted, refused = partition_capture_rows(rows, path)
        if refused:
            refused[0] = (refused[0][0], str(e))
        else:
            # The partition named no row. Over one row list that is a
            # contradiction rather than a file that moved: the strict pass
            # raised on a row this just decided was fine, so one of the two
            # is wrong about what grades. Reported as a refusal of the file
            # rather than dropped -- a refusal this function could not tie to
            # a row is still one that happened, and the anti-drift test holds
            # the two readers together precisely so that arriving here means
            # the rules have drifted rather than the file having changed under
            # a second read. A file-level refusal is not the case: the
            # byte-order mark is refused before any row is read (above), and
            # a decode refusal never reaches this loop at all.
            refused.append((None, str(e)))
    else:
        accepted = mark_labels_of(rows)
        _, unplaced = assign_blocks(coalesce_marks(marks))
        for window, said in unplaceable_marks(unplaced).items():
            unplaceable += [(m.ts.isoformat(sep=" "), m.label, message)
                            for m, message in zip(window.marks, said)]
    return accepted, refused, unplaceable


def read_early_exits(path):
    """The early-exit rows of one capture: a second reader over what
    `read_capture` drops.

    A second reader rather than a change to `read_capture`, for two
    independent reasons. Its two-tuple is a contract with other tools --
    `grade_gpu_door.py`, `manual_fan_ctrl_probe.py` and
    `scan_mark_collisions.py` each import this module and unpack it -- and its
    skip rule is the invariant this has to be added beside rather than
    through: `#` rows are skipped *so that* an operator can annotate a capture
    by hand without breaking this, and every committed fixture under
    `ec/tools/testdata/` opens with a `#` block.

    A row is recognised by the phrase alone, not by being a comment, and its
    remainder is the timestamp the writer stamped. A row that opens with the
    phrase and carries no timestamp this can read comes back with `ts=None`
    and the rest of the line as its reason, so the caller can refuse it by
    name instead of the capture grading as one that finished.

    The declared `utf-8` and, unlike the preflight readers, no `errors=`: a
    capture in another encoding is a grading-time failure here as well as a
    notice-time one, which was already true and is now the format's rule
    rather than a side effect of the interpreter. The codec is named in the
    `UnicodeDecodeError` this propagates, so the failure says which one.

    Its test is *not* `skippable_row`, and the reason is the phrase itself:
    `EARLY_EXIT_TAG` opens with `#`, so this reader keeps exactly the rows
    the other three drop. That is also why the shared seam is `capture_rows`
    rather than a filtered iterator -- filtering inside the stream would take
    every early-exit row in the tree with it. So the two decisions sit side
    by side: the stream owns opening the file, the decode policy and the
    first field, and each reader owns which rows are its own. Which is also
    why the stream's first-field normalisation reaches this reader at all:
    without it, a byte-order mark at offset 0 glued itself to the first
    field of whatever row came first, and a crash row written on line 1 was
    invisible to the one reader that exists to find it, and now is: the
    normalisation is what makes it so, not a caller. This is no longer
    `main`'s path into an early-exit row -- `main` reads one snapshot per
    capture and hands its rows to `early_exits_of` (#767) -- so nothing here
    is reached for a capture the strict rules refused; that one is answered
    by the printed refusal `main` makes, and by `existing_mark_findings`,
    which names the same files `bom_refusal` speaks for.
    """
    return early_exits_of(capture_rows(path), path)


def early_exits_of(rows, path):
    """The early-exit rows among `rows`: `read_early_exits`' own body, over a
    row list rather than a path.

    The shape `mark_labels_of` and `partition_capture_rows` already have
    (#749), taken for the same reason and no new one: the rule below is
    `read_capture`'s counterpart, so a second copy of it would be a second set
    of rules the notice could apply, and the whole of its value is that its
    verdict is the reader's.

    **The path here is the entry point, and `main` is no longer a caller of
    it** (#767). It used to read the same capture a second time, a few lines
    after the strict read, so the early-exit count it appended to the census
    line came from a different moment than the mark and change counts already
    in that line -- and §3 runs three watchers on one `--csv` with
    `CsvSink.row` flushing every row, so the two opens were microseconds apart
    or not and a row landing between them was a row the two halves of one
    printed line disagreed about. `main` now takes one `capture_snapshot` per
    capture and hands the same row list to the strict pass and to this, so the
    census line is one moment rather than two.

    So this takes rows and the caller decides what they are, and the phrase
    test below is the whole of what it decides. It is `read_early_exits`' body
    unchanged, and that is the claim: `test_early_exits_of_is_read_early_exits_
    over_one_row_list` holds the two to each other rather than leaving a
    reader to check them against each other by reading.
    """
    out = []
    for row in rows:
        if not row or not row[0].startswith(EARLY_EXIT_TAG):
            continue
        rest = row[0][len(EARLY_EXIT_TAG):].strip()
        said = ", ".join(part for part in [rest, *row[1:]] if part)
        try:
            ts = parse_ts(rest)
        except ValueError:
            out.append(EarlyExit(None, said, path))
            continue
        # What is left of the row once the timestamp is off the front: the
        # writer's reason, in whichever field it was put.
        out.append(EarlyExit(ts, said[len(rest):].strip(" ,"), path))
    return out


def read_dump(path):
    """addr -> byte, from `ecrw.py dump` output (`0700: 12 34 ...`).

    `#` lines are skipped, as `read_capture` skips them. The two are written
    by the same operator out of the same run, and §6 tells them to annotate
    what they hand in; a comment carrying a colon is otherwise read as a row
    of bytes and raises out of `int()`. `newline=""` as the five readers
    above pass it, so a hand-annotated dump is read the way it is written.

    It opens with no handling of its own and raises `OSError` at a file that
    is not there, which is the right contract for the one place a dump is
    parsed and the wrong one for a caller with a whole `--dump` list to get
    through. `read_dumps` and `read_dump_pairs` below are the forms the
    report goes through; this stays as they are built on it, and as the test
    helper that reads one committed fixture calls it directly.
    """
    values = {}
    with open(path, newline="", encoding="utf-8") as f:
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


def read_dumps(paths):
    """(--dump entries in the order given, the ones that would not open).

    An entry that would not open keeps its place in the first list with
    `values` of `None` rather than being left out of it, because
    `report_dumps` takes the §4.6 readback from the block's *last* `--dump`:
    a dropped entry promotes the one before it into that place, and the
    verdict then reads "the last dump" over a file the operator did not name
    last. `failed` carries those entries with the error, which is what the
    report prints and a bare `None` cannot say.

    `OSError` and nothing wider, deliberately. A dump that opens and is not
    decodable raises `UnicodeDecodeError`, and one holding a line that is not
    hex raises `ValueError`; a malformed file and a missing one are different
    faults, and swallowing the first under "not read" would report a parse
    failure as an input one. A narrow catch that has to grow later is visible
    in a diff.
    """
    dumps, failed = [], []
    for path in paths:
        try:
            dumps.append((path, read_dump(path)))
        except OSError as exc:
            dumps.append((path, None))
            failed.append((path, exc))
    return dumps, failed


def read_dump_pairs(arg_pairs):
    """(the --dump-pair entries that opened, those with a side that did not).

    A pair with either side unreadable is dropped whole rather than compared
    over what is left. A whole-block read is the intersection of two files,
    and one of them not being there is not a bracket: `0 address(es)
    compared` over the survivor would be a result about nothing, which is the
    same false green `SAME_FILE_PAIR`'s line is written against. `failed`
    keeps the pair's two paths and, per side that would not open, the error,
    so the report can print it under the pair the operator actually typed.

    `OSError` only, for the reason `read_dumps` gives.
    """
    pairs, failed = [], []
    for before, after in arg_pairs:
        sides = []
        try:
            before_values = read_dump(before)
        except OSError as exc:
            sides.append(("before", exc))
        try:
            after_values = read_dump(after)
        except OSError as exc:
            sides.append(("after", exc))
        if sides:
            failed.append((before, after, sides))
        else:
            pairs.append((before, after, before_values, after_values))
    return pairs, failed


def capture_key(path):
    """Which file this path names, as the one key every comparison shares.

    A path is what the operator hands in and the identity is what the file
    resolves to, so `x.csv`, `./x.csv` and a symlink to it are one capture --
    the reason `report_dump_pairs` gives.

    It is a function rather than a rule written into each caller because
    `read_capture` stores `m.source` as the path *as given*, while
    `distinct_captures` keys the count on the resolved one. A run handed one
    file twice under two spellings therefore holds two `m.source` values for
    one file, and a comparison that mixes the two -- marking a window's rows
    against the run's capture list -- reads one file as two captures, or as a
    capture missing from itself. Both sides of every such comparison go
    through here, or the two sections of the report count captures
    differently, which is the defect `capture_key` is here to prevent.

    The key is for looking up, not for printing. Every site that names a
    capture prints `os.path.basename` of a path `distinct_captures` kept, and
    what that keeps is the first spelling *as it was handed in* rather than a
    resolved one, so a capture is still named the way the operator typed it.
    Resolving cannot be folded into the print, because a symlink resolves to
    a different filename than the one the operator gave.
    """
    return os.path.realpath(path)


def distinct_captures(paths):
    """The capture paths that are each one file, and the repeats dropped.

    The first spelling of each file is the one kept, and a repeat comes back
    as `(path as given, path it repeats, the file both resolve to)`, so a
    caller can name all three: two spellings of one file is one file, and the
    operator has to be able to see which of the two was dropped.

    Keyed on `capture_key` rather than on the string, for the reason it gives.
    Through it rather than on `os.path.realpath` directly, so there is one
    spelling of "which file is this" in the module instead of a rule stated
    here and re-derived by every caller that has to agree with it. One
    spelling of the test, so `main` and the readers cannot disagree about
    which captures a run has.
    """
    kept, seen, repeats = [], {}, []
    for path in paths:
        resolved = capture_key(path)
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

    The gap each adjacent pair was joined on rides along in `mark_gaps` as
    well, as `(earlier mark, later mark, seconds)`. It is the distance the
    close test above measures between the same two marks, carried onto the
    window rather than left to be worked out again by whoever reads the
    report. It is recorded beside `marks` rather than inside it because a gap
    is a property of the join -- of two consoles' rows together -- and not of
    any one of them. A group of one mark has none, and that is the ordinary
    case.

    `boundary_gaps` is the same quantity on the other side of the boundary:
    the marks of the *same* action that did not join, as `(mark, seconds)`
    measured from this group's earliest mark, one per capture and never a mark
    of a different action -- a restore thirty seconds later is not a boundary
    for a control arm, and recording it would put a number on every window of
    every run. Per capture rather than per side because the report has to name
    *which* console was how far out, and one mark for the side cannot say that
    for the second and third console of a three-console day.
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
    for n, (w, g) in enumerate(zip(windows, groups)):
        w.marks = g
        w.mark_gaps = [(a, b, (b.ts - a.ts).total_seconds())
                       for a, b in zip(g, g[1:])]
        w.boundary_gaps = boundary_marks(w, groups, n)
    return windows


def boundary_marks(w, groups, index):
    """The marks of this window's action that fell outside the merge.

    The run of consecutive groups either side of this one that carry the same
    action, walked outwards until one does not. Not only the two adjacent
    groups: three consoles marking one action 7 s apart open three windows, and
    the first of them is 14 s from the third -- so a neighbour-only rule would
    answer for the second console and leave the third looking like a capture
    that never recorded the action, which is the half of the same day this
    exists to correct.

    A group counts only when `parse_mark` reads it as the same `(role, value)`
    as this window's own label, and a window whose own label does not read
    yields nothing: a neighbouring mark of a different action is the next arm
    rather than a console that was slow with this one, and recording it would
    put a distance on every window of every run. The chain stops at the first
    group that is a different action, so a restore thirty seconds later is
    never a boundary for a control arm.

    One mark per capture, the nearer of the two sides, because the question
    the report asks is per console: `window_mark_problems` has to say that
    *this* capture recorded the action 7.0 s out, and one mark for the side
    cannot answer that for the second and third console.

    Empty for a window whose whole action fused into one group, which is the
    ordinary case: there is then no other mark of this action anywhere in the
    capture, and no boundary to describe.
    """
    action = parse_mark(w.label)
    if action == (None, None):
        return []
    seen = {}
    for step in (-1, 1):
        n = index + step
        while 0 <= n < len(groups):
            if parse_mark(groups[n][0].label) != action:
                break
            for m in groups[n]:
                away = (m.ts - w.ts).total_seconds()
                here = seen.get(m.source)
                if here is None or abs(away) < abs(here[1]):
                    seen[m.source] = (m, away)
            n += step
    return [seen[source] for source in sorted(seen)]


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

    Each window's `span` is recorded here rather than left to the two readers
    to work out, because it is a property of the window and both print it. A
    window but the last runs to the next mark, and that is a length.

    The last window has no next mark, and its `span` is measured to the last
    change row it holds, which is a **lower bound and not a length**:
    `ec_watch.py` writes a row when a byte changes, so a quiet tail after the
    last change is in no row and the capture cannot say how long it ran.
    `span_is_bound` is set with it, and `span_note` reads that before drawing
    anything from a span under the band -- a small bound says the window was
    at least that long and nothing more, so calling it short would be a
    conclusion the figure does not carry. A window with no change row of its
    own bounds at zero, which is the same fact rather than a missing one.
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
        if end is not None:
            w.span = (end - w.ts).total_seconds()
        else:
            w.span = ((w.changes[-1].ts - w.ts).total_seconds()
                      if w.changes else 0.0)
            w.span_is_bound = True
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

    §3 fixes the labels the operator types and `ec_watch.py` writes them into
    the CSV verbatim, so the leading word is the only handle on it. Only that
    word and the value are read, case-insensitively: everything after the
    value is the operator's, and what is checked here is which action the
    mark names and which value it names -- not how it was punctuated.

    `no-op wrote ...` is the control arm and `wrote ...` is the write under
    test, which is the whole reason §3 spells the prefix out: read the other
    way round, the two are the same sentence with a prefix and the control arm
    becomes indistinguishable from what it is a control for.

    A stage boundary is matched on the word alone -- it *is* the word, or
    begins with the word and a space -- because §3 types it with nothing after
    it, and every action form is followed by `0x0751=...` so none of them can
    be. That is what the third field of `MARK_FORMS` is for: a boundary has
    to match with no value at all rather than with a value that happens not
    to be there, so the form table has to say which forms are exempt instead
    of the parse inferring it from a regex that did not match.

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
        for role, word, takes_value in MARK_FORMS:
            if part != word and not part.startswith(word + " "):
                continue
            if not takes_value:
                return role, None
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

    A stage boundary names a stage rather than a write and carries no value, so
    it cannot name a block and is filed against one that is already open:
    `settled` and `held` sit in front of the write they belong to, and
    `watch over` sits behind it. While no block is open a boundary waits for
    the next `write` exactly as the control arm does, which is what keeps a
    boundary typed between two blocks from being swallowed by the first of
    them. §3 prints all three inside one block, so a block reads
    `settle, control, hold, write, watch, restore` and the windows they open
    are that block's.

    The labels are the only thing that says a run was one block or the next.
    A gap in the timestamps says only how long the operator took, and a mark
    stream read on timestamps alone grades whatever it is handed under
    whatever heading it happens to fall in.

    What is left over is returned rather than folded into a neighbour: a
    control arm whose write never came, a restore with no block open, and a
    label this cannot read are three different things and are reported as
    three. They are graded as the windows the capture did hold -- their rows
    are real and there is no other arm to mis-file them under -- with `block:
    unplaced` on their header, unless one of the checks reaches them. The
    unreadable ones are refused because a label this cannot read is a label it
    cannot say what a window is a window of (`unplaceable_marks`), and one the
    captures spelled two ways, or that one of them did not record, is refused
    too, because the window it opens is then not the action any capture
    recorded (`unplaced_window_problems`).
    """
    blocks, unplaced, pending, current = [], [], [], None
    for w in windows:
        role, value = parse_mark(w.label)
        if role in BOUNDARY_ROLES:
            # Onto the open block if there is one, and held for the next
            # `write` if there is not. §3's three boundaries are inside one
            # block, and `watch over` is the one that arrives with a block
            # open; the other two are the control arm's case, and waiting is
            # what keeps a boundary typed between two blocks from joining the
            # wrong one.
            if current is None:
                pending.append(w)
            else:
                current.windows.append(w)
        elif role == "control":
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


def repeated_values(blocks):
    """The values more than one block is under test, as `{value: [block]}`.

    The value under test is what a block, a `--dump` pair and a §4.6 verdict
    are all named by, and `--block` takes it rather than a position in the
    mark stream, so a value carried by two blocks names no single block. A
    day reaches this by running §3's own remedy for a void block: the redo is
    a second `no-op`/`wrote`/`restored` set carrying the same value, appended
    into the same three CSVs, and nothing in the marks says which attempt a
    window belongs to.

    Ordered by first appearance rather than by value, so a caller that names
    the blocks gets them in the order the census prints them. Only values
    carried by more than one block are in the result -- a day with no repeat
    is an empty dict.
    """
    out = {}
    for b in blocks:
        out.setdefault(b.value, []).append(b)
    return {v: bs for v, bs in out.items() if len(bs) > 1}


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
            f"{m.label!r} is not one of the forms §6 fixes ("
            + ", ".join(repr(f) for f in REQUIRED_LABEL_FORMS)
            + "), and a mark this cannot read is a mark no block can be "
              "attributed to"
            for m in w.marks]
    return out


def unplaced_window_problems(unplaced, captures):
    """The agreement problems on the windows in no block, per window.

    `labels` and `missing` come along, both of `missing`'s arms, and `void`
    does not: the void check is a block's last recorded mark in a capture, and
    a window in no block has no block to have one in. That is a property of
    what the check is defined over rather than a limit found by looking and not
    finding a case, and it is said here rather than left for a reader to infer
    from the check's absence.

    The agreement checks engage at two or more captures, exactly as they do
    over a block: with one there is no other console for the mark to be
    missing from and no second spelling to disagree with it.

    A dict rather than a list because `main` prints each refusal in the window
    it belongs to and counts the window rather than the problem -- the shape
    `unplaceable_marks` returns, and the one the branch reading it expects.
    """
    names, _ = distinct_captures(path for path, _ in captures)
    known = {capture_key(p) for p in names}
    out = {}
    for w in unplaced:
        problems = window_mark_problems(w, names, known)
        if problems:
            out[w] = [text for _, _, text in problems]
    return out


def split_mark_gaps(w, names, by_source):
    """`{capture: seconds}` for every absent capture that marked the same
    action just outside the merge, or `{}` when the sentence stands.

    The second arm of the `missing` check, and the condition that chooses
    between the two. It is `{}` unless **every** capture this window is short
    a mark for recorded that same action within `MARK_SPLIT_SECONDS` of it: one
    capture that recorded the action and one that never did are two different
    days' worth of trouble, and a sentence naming the second would be false
    about the first.

    `by_source` is the caller's own grouping of this window's marks, so both
    readers ask the same question of the same rows and cannot disagree about
    which capture is absent. It is keyed on `capture_key`, and so is `near`
    below: `m.source` is a path as given and one file can have been handed in
    under two spellings, so a `near` keyed on the string would fail to find
    the boundary mark of a capture the caller had already found under its
    other spelling.

    The threshold is a **distance**, so it is compared against the magnitude:
    `boundary_marks` records `m.ts - w.ts`, which is negative for a mark on
    the *before* side of this window's mark, and `-20.0 > 15.0` is false. A
    console that marked 20 s early is outside the 15 s this sentence tells
    the operator to stay inside, so on a signed compare it passed a bound it
    breaks, and the report named it as one of the consoles that came close.
    The signed value is what comes back, because the readers say which side
    of the mark the mark fell on.
    """
    absent = [p for p in names if capture_key(p) not in by_source]
    if not absent:
        return {}
    near = {capture_key(m.source): seconds for m, seconds in w.boundary_gaps}
    if any(capture_key(p) not in near
           or abs(near[capture_key(p)]) > MARK_SPLIT_SECONDS
           for p in absent):
        return {}
    return {p: near[capture_key(p)] for p in absent}


def window_mark_problems(w, names, known):
    """One window's agreement problems, as `check_block_marks` returns them.

    Both of them are properties of the marks alone -- which captures recorded
    the action, and whether they spelled it the same way -- and neither names a
    block, so a window the block walk could not place is checked by the same
    two as one it could. Lifted out of `check_block_marks` for that reason
    rather than written a second time.

    `names` and `known` are the run's, passed in rather than re-derived per
    window so that every window is read against the same capture list the
    census counted, and cannot disagree with it.

    The `missing` problem has two arms and they are not the same claim. The
    one below is a capture that did not record the action, and it is right
    for that. It is **false** when every absent capture recorded the same
    action just outside the merge: nothing was missed, the three consoles
    marked one action further apart than the merge fuses, and the split opened
    a window per console that each later window then reads as a capture that
    missed it. `split_mark_gaps` decides, and the other arm says what is true
    in its place.
    """
    by_source = {}
    for m in w.marks:
        by_source.setdefault(capture_key(m.source), []).append(m.label)
    spellings = {label for labels in by_source.values() for label in labels}
    problems = []
    if len(spellings) > 1:
        said = "; ".join(
            f"{os.path.basename(p)}: {by_source[capture_key(p)][0]!r}"
            for p in names if capture_key(p) in by_source)
        problems.append(("labels", w, (
            f"the captures spell this action differently -- {said} -- so "
            "the window it opens is not the action any of them recorded")))
    if len(names) > 1 and set(by_source) != known:
        absent = [os.path.basename(p) for p in names
                  if capture_key(p) not in by_source]
        split = split_mark_gaps(w, names, by_source)
        if split:
            # Magnitude and a side word, the way the census's own line under a
            # capture formats it. The distance is signed, and a sentence
            # reading `console-0.csv at -7.0s` puts a bare negative in prose
            # where the reader has to do the sign arithmetic to learn which
            # side of the mark the console marked on.
            how = ", ".join(
                f"{os.path.basename(p)} at {abs(d):.1f}s "
                f"{'after' if d > 0 else 'before'}"
                for p, d in split.items())
            problems.append(("missing", w, (
                f"recorded in {len(by_source)} of {len(names)} capture(s), "
                f"absent from {', '.join(absent)} -- and every one of them "
                f"recorded this same action just outside the "
                f"{MARK_MERGE_SECONDS}s merge ({how}). That is the consoles "
                f"marking one action further apart than the merge fuses, not "
                f"captures losing it: the split opened a window per console "
                f"and each later one reads as a capture that missed the mark. "
                f"Redo the block, marking each console within "
                f"{MARK_SPLIT_SECONDS:g}s of the others")))
        else:
            problems.append(("missing", w, (
                f"recorded in {len(by_source)} of {len(names)} capture(s), "
                f"absent from {', '.join(absent)}. The capture(s) that missed "
                "it have their rows for this arm filed under whichever "
                "window their timestamps fall in, and nothing in the result "
                "ties them to the arm whose mark is gone -- so this arm can "
                "read quiet for want of a mark rather than because nothing "
                "moved")))
    return problems


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
        want of a mark rather than because nothing moved. It has a second
        arm, for the case where the capture did record the action and the
        merge split it away from the other two; `window_mark_problems` says
        which of the two applies.
      * an action the captures spelled differently. Same failure, found one
        step earlier: `coalesce_marks` joins the labels with ' / ', so the
        window opens on a label no console typed.
      * a block whose last recorded mark in some capture is not the restore.
        Per block *and* per capture, not the file's global last mark: a
        capture that recorded only one block would otherwise look complete
        for every block in the day.

    The first two are `window_mark_problems`, and the third is not: it is
    defined over a block, and the windows a block walk could not place are
    checked by `unplaced_window_problems` for the other two. The third is also
    what `block_verdict` reports, over `Block.closers` -- the same per-capture
    answer, derived from the block rather than from this loop, so the verdict
    and the complaint cannot be two reads that disagree about which capture
    ended the block where (#450).

    The agreement checks need a second capture to have anything to disagree
    with, so they engage at two or more and the census says so below that
    rather than letting one capture pass a check it never ran.
    """
    # `main` refuses a repeated capture before this runs; the line is held here
    # too, because these are the checks a repeat would switch on and a reader
    # reached directly still has one capture counted once. `known` is keyed on
    # `capture_key` for the same reason, and the two sites that build it -- this
    # one and the one in `unplaced_window_problems` -- have to agree: they are
    # the same set of the same run, and the windows a block walk could not
    # place are held to the same mark set as the ones it could.
    names, _ = distinct_captures(path for path, _ in captures)
    known = {capture_key(p) for p in names}
    problems = []
    for w in block.windows:
        problems += window_mark_problems(w, names, known)
    for path in names:
        here = block.marks_in(path)
        if here and parse_mark(here[-1].label)[0] != "restore":
            problems.append(("void", block.windows[-1], (
                f"{os.path.basename(path)} ends this block on "
                f"{here[-1].label!r}, not the restore, so its last window "
                "never closes in that capture")))
    return problems


def charge_early_exits(early_exits, windows):
    """(placed, refused): the rows a window puts in a block, and the rest.

    A placed row is appended to `Block.problems` as one more
    `(kind, window, text)` row -- the shape `check_block_marks` returns and
    the shape the window loop, `report_census` and `block_marker` already
    read. So a block an early exit falls in is withheld by the machinery that
    withholds every other block with a problem, and the window report, the
    block verdict and the exit code cannot disagree about which blocks were
    graded. That is `Block.problems`' own reason for being one list, and the
    new kind rides on it rather than beside it.

    The block, not the one window, is the unit charged: §3 defines a block, it
    is what the void check already withholds on, and the capture cannot say
    which arms before the cut were still worth reading. It is also why
    this can be quiet about the void check -- a run that stopped still records
    its restore, so the block reads `intact` and the void check has nothing to
    say. What it is short is a *hold*, and that is a different fact wearing
    the same word on the block line.

    A row that cannot be placed -- no readable timestamp, a timestamp whose
    offset does not match the marks it would be placed against, no window at
    or before it, or a window in no block -- is refused by the caller instead
    of filed anywhere. It is a run-level refusal on `unplaceable_marks`'s
    argument: block attribution rests entirely on the labels and where each
    row falls, so a row this cannot place leaves every block's completeness
    uncertifiable, and `--block` narrows what is graded rather than what is
    known.

    **The offset check is a refusal rather than a comparison that raises**
    (#767). `parse_ts` is `datetime.fromisoformat`, which accepts a bare
    `YYYY-MM-DDThh:mm:ss` and returns a *naive* datetime, so a stamp cut
    before its offset still parses and arrives here as a `ts` while every
    window's carries the offset `manual_fan_ctrl_probe.now()` wrote -- and
    `w.ts <= e.ts` below raises `TypeError: can't compare offset-naive and
    offset-aware datetimes` straight out of `main`, killing a run over a file
    the operator did nothing wrong to. No race is needed for that: a watcher
    killed mid-`flush` leaves that file on disk, and so does a hand-edited or
    truncated row. Checked here rather than in the reader because the two
    ends are the question: the row alone is well-formed, and it is only
    against *these* windows that it cannot be placed, which is why the reason
    names the mismatch and not a fault of the row.
    """
    placed, refused = [], []
    order = sorted(windows, key=lambda w: w.ts)
    for e in early_exits:
        if e.ts is None:
            refused.append((e, "the row carries no timestamp this can "
                               "read, so nothing in it says when the run "
                               "stopped"))
            continue
        if any((w.ts.tzinfo is None) != (e.ts.tzinfo is None) for w in order):
            refused.append((e, f"its timestamp {e.ts.isoformat(sep=' ')} "
                               f"carries {'no' if e.ts.tzinfo is None else 'a'} "
                               f"UTC offset and the marks in these captures "
                               f"do not agree, so the two cannot be compared "
                               f"and there is no window for it to have cut "
                               f"short"))
            continue
        before = [w for w in order if w.ts <= e.ts]
        if not before:
            refused.append((e, "no mark in the capture is at or before it, so "
                               "there is no window for it to have cut short"))
            continue
        w = before[-1]
        if w.block is None:
            refused.append((e, f"it falls in the window {w.label!r} opened, "
                               "which is in no block"))
            continue
        w.block.problems.append(("early-exit", w, (
            f"{os.path.basename(e.source)} records that the run ended early "
            f"at {e.ts.isoformat(sep=' ')}: "
            f"{e.reason or 'the row carries no reason'}")))
        placed.append((e, w))
    return placed, refused


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


def mark_gap_note(w):
    """The lines that say how close a fused group came to splitting.

    `coalesce_marks` fuses marks that land within `MARK_MERGE_SECONDS` of
    each other and records on the window the gap it decided each join on.
    This is where that surfaces. A report that names a group and its verdict
    without the distance reads the same whether three consoles agreed at once
    or one hesitated for five seconds, and a reader who expected one action
    boundary has nothing to judge the join by.

    A measured distance between two recorded rows, and only that. Not a claim
    that the operator took two actions -- `probe-hold-mark-merge.md` records
    what the writer side of the distance costs (the probe's `hold` plus the
    inter-arm re-snapshot) as unmeasured, and a figure measured on the reader
    side does not measure it.

    Empty for a group of one mark: there is no join to describe, and a line
    saying there was none would be noise on the ordinary window.
    """
    if not w.mark_gaps:
        return []
    gaps = [gap for _, _, gap in w.mark_gaps]
    widest = max(gaps)
    listed = ", ".join(f"{g:.1f}s" for g in gaps)
    lines = textwrap.wrap(
        f"joined {len(w.marks)} mark row(s), adjacent gap(s) {listed}, "
        f"window {MARK_MERGE_SECONDS}s", width=72, initial_indent="    ",
        subsequent_indent="    ")
    if widest >= CLOSE_GAP_SECONDS:
        lines += textwrap.wrap(
            f"the widest of those, {widest:.1f}s, is at or above the "
            f"{CLOSE_GAP_SECONDS}s this report calls close: the group stayed "
            f"together by under a second of the {MARK_MERGE_SECONDS}s "
            f"window, so a reader who expected two actions has the distance "
            f"here to judge the join rather than take it on trust",
            width=72, initial_indent="    ", subsequent_indent="    ")
    return lines


def span_line(w):
    """How long the window is, as the one line both readers print it on.

    The last window of a capture is marked as a bound rather than a length,
    and says what it is a bound to: `build_windows` measures it to the last
    change row, and `ec_watch.py` writes a row when a byte changes, so a
    quiet tail after that row is in no row of the file and the window's true
    end is not in the capture. The figure is arithmetic over the rows, and
    printing it as a length would be the overclaim `docs/findings.md` §4 is a
    record of.
    """
    if w.span_is_bound:
        return (f"    window span at least {w.span:.1f}s, to the last row in "
                "the capture")
    return f"    window span {w.span:.1f}s"


def span_note(w):
    """The lines that say what a span outside §3's own pacing costs.

    §4.4's control-vs-write comparison is `total` over one window against
    `total` over another, and neither figure carries a time base: a duty byte
    that drifts for 30 s and one that drifts for 3 s have totals that are not
    two answers to the same question. Before `build_windows` recorded the
    span there was nothing in the report to notice that with, so the
    comparison was taken over windows of unequal and unknown length and read
    as though it had not been.

    A report and not a refusal, on the line `mark_gap_note` draws: the window
    is graded on the rows it holds, the exit code does not turn on it, and no
    `window delta` figure changes. What changes is that the reader has the
    number before taking the comparison.

    Empty for a span inside the band, and for a bound that is under it: a
    lower bound says the window was at least that long and nothing more, so
    calling it short would be a conclusion the figure does not carry. A bound
    over the ceiling still fires -- that much length is established however
    much longer the window was.
    """
    if w.span >= SPAN_CEILING_SECONDS:
        why = (f"this window ran {w.span:.1f}s, at or above the "
               f"{SPAN_CEILING_SECONDS:g}s the three watchers are started "
               f"with. The watchers are started without `--auto-mark`, so "
               f"nothing in a §3 capture names a suspend that happened in it, "
               f"and a freeze the rows do not cover is the likeliest way a "
               f"window runs that long -- a guess, not a reading, and every "
               f"row after the gap is filed in here")
    elif w.span_is_bound or w.span >= SPAN_FLOOR_SECONDS:
        return []
    else:
        why = (f"this window ran {w.span:.1f}s, under the "
               f"{SPAN_FLOOR_SECONDS:g}s §3's own pacing budgets for its "
               f"shortest stretch, so the arm it is a window of ran for a "
               f"fraction of the ~30s one beside it")
    return textwrap.wrap(
        f"{why}. §4.4's control-vs-write comparison is taken over two "
        f"windows, and a difference in `total` between two of unequal length "
        f"is a difference in how long each byte was watched rather than one "
        f"the write made. This is a report and not a refusal: the window is "
        f"graded on the rows it holds and the figure is here to judge it by.",
        width=72, initial_indent="    ", subsequent_indent="    ")


def report_census(captures, windows, blocks, unplaced, unreads, unagreed,
                  selected):
    """What the marks say, before anything is read over them.

    Two listings, because they answer two questions. Per capture: the labels
    that capture recorded, in order, each with the role the parse gave it and
    the block it fell in -- which is the only place a mark that went missing,
    or a label two consoles spelled differently, is visible as such. Per
    action: how many of the N captures recorded it and whether they agree,
    which is the comparison §6 asks for in a sentence rather than in prose.

    A capture the per-action listing says did not record an action reads
    `-- did not record it` unless every absent capture recorded the same
    action just outside the merge, in which case it reads as the distance
    that says so. This is the site that matters most under `--block`: the
    census is whole-capture while only the selected block's windows print, so
    a split in a block this run did not grade is visible here and nowhere
    else.

    Printed whole even under `--block`, because a run that scoped itself and
    said so is the point: the blocks it did not grade are named here as not
    selected, so a reader can see that the scoping is there and not that the
    other blocks are missing.

    A window in no block carries its outcome here too, for the same reason and
    a step further: under `--block` the window section prints the selected
    block's own windows, so this is the only section that can say what the run
    did with a stray the scope kept out of it. It names the refusal and the
    kinds behind it rather than the defect, because it is the refusal the run
    made and not a finding the marks make on their own -- and because the
    clause is a property of the marks, it prints the same either way `--block`
    scoped the run or not.

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
            said.setdefault(capture_key(m.source), m.label)
        where = f"block {w.block.name}" if w.block else "unplaced"
        head = (f"  action {i} at {w.ts.isoformat(sep=' ')}  {where}: "
                f"{w.label!r} in {len(said)} of {len(names)} capture(s)")
        if len(said) == len(names) and len(set(said.values())) == 1:
            print(head + ", one label each")
        else:
            print(head + ":")
            # `-- did not record it` is the sentence that sends the operator
            # looking for a watcher that exited early, and it is false of a
            # capture that recorded the action a few seconds too far from the
            # other two for the merge to fuse. `split_mark_gaps` is the same
            # condition the `missing` problem takes its second arm from, so
            # the line under a capture and the sentence on its window cannot
            # disagree about which of the two this is. The `in N of M` head
            # above is a fact about the group either way and stays.
            split = split_mark_gaps(w, names, said)
            for path in names:
                got = said.get(capture_key(path))
                if got:
                    line = repr(got)
                elif path in split:
                    d = split[path]
                    line = (f"recorded the same action {abs(d):.1f}s "
                            f"{'after' if d > 0 else 'before'} this mark")
                else:
                    line = "-- did not record it"
                print(f"    {os.path.basename(path):44} {line}")
        # The per-action entry, not the per-capture rows above: a gap is
        # between two consoles' rows and printing it under either one of them
        # would attribute it to that console alone. And the census is the
        # whole capture under `--block` while only the selected block's
        # windows print, so this is where a fused group in a block this run
        # did not grade stays visible.
        for line in mark_gap_note(w):
            print(line)

    repeated = repeated_values(blocks)
    for i, b in enumerate(blocks, 1):
        line = (f"  block {i} of {len(blocks)}: value under test {b.name}, "
                f"roles {', '.join(b.roles)}")
        if selected is not None and b is not selected:
            line += " -- not selected in this run"
        elif b.problems:
            # The kinds, not just the count: a reader of a fold-in wants to
            # know whether a block is short a mark or a capture is short one,
            # and the two send the operator to different terminals. The
            # heading is not "mark-set", because a block withheld for an early
            # exit is not short a mark -- it holds all of them.
            kinds = ", ".join(sorted({k for k, _, _ in b.problems}))
            line += f" -- NOT GRADED, {len(b.problems)} problem(s): {kinds}"
        # Independent of the clause above, because it is a fact about the
        # value rather than about this block: one block being void does not
        # make its value a shared one, and a shared one does not need a block
        # to be void. Printed on every block carrying the value, not on the
        # first, so a reader holding the day's census can see which blocks a
        # single `--block` would have had to choose between -- and `--block`
        # refuses rather than choosing (see `main`).
        #
        # What put the value in two blocks is not named here, because this
        # cannot know: the shapes that reach it are §3's re-done block
        # appended to the set, and marks the merge did not fuse because the
        # consoles typed them too far apart, which is a different defect with
        # its own line above. The clause says the one thing true of both --
        # the value names no single block, so `--block` is refused on it and
        # the exit code holds -- and the lines above say what each block
        # itself is short of.
        if b.value in repeated:
            twins = repeated[b.value]
            which = ", ".join(str(x.index) for x in twins)
            line += (f" -- {b.name} is the value under test of {len(twins)} "
                     f"block(s) of this run ({which}), so it names no one of "
                     "them and --block is refused on it")
        print(line)
    if unplaced:
        # The kinds are named from `window_mark_problems`, the function
        # `unplaced_window_problems` called, so they cannot name a kind the
        # refusal did not carry -- and what makes the two agree is the key
        # rather than the shared `names`, `known` being compared against
        # `capture_key`, so it is built the way `unplaced_window_problems`
        # and `check_block_marks` build it, for the reason the latter gives.
        # `unagreed` is `main`'s decision to refuse the window, only reported.
        known = {capture_key(p) for p in names}
        for w in unplaced:
            role, _ = parse_mark(w.label)
            if role is not None:
                line = (f"  unplaced: {w.ts.isoformat(sep=' ')}  {w.label!r} "
                        "-- in no block, so the void check cannot reach it -- "
                        "there is no block whose last mark in a capture it "
                        "could be -- and `--block` cannot select it either")
                # What this run did with the window, which under `--block` the
                # window section cannot say: only the selected block's windows
                # print there, so a scoped attachment would otherwise carry the
                # whole diagnosis and no outcome for it, and a reader holding
                # the two attachments side by side would see `NOT GRADED` in
                # one and not the other over a byte-identical census. It says
                # NOT GRADED and not that the mark was wrong -- the refusal is
                # what the captures disagree about, in a block's own words.
                #
                # A property of the marks, so it prints scoped and unscoped
                # alike, and it never names a window in `unreads`: that guard
                # is `parse_mark` returning no role, which is the predicate
                # `unplaceable_marks` keys on, so the two are complementary
                # over `unplaced` and the clause cannot reach a window whose
                # unreadable label `main`'s earlier branch refused instead.
                if w in unagreed:
                    kinds = ", ".join(sorted(
                        {k for k, _, _
                         in window_mark_problems(w, names, known)}))
                    line += (f" -- NOT GRADED, {len(unagreed[w])} problem(s): "
                             f"{kinds}")
                print(line)


def report_early_exits(exits, placed, refused, windows, blocks):
    """The rows that say a run stopped, and what this run did about them.

    Printed whole, above the window header, on the census's reasoning rather
    than its own: §6 runs one `--block` per value and reads the attachments
    side by side, so a section that named only the selected block's rows would
    read as a day in which no run ever crashed. A row this run did not charge
    is named as unplaced here rather than only in the refusal, so the section
    is the whole of what the capture holds on this question.

    Printed at all only when a capture carries one. A run in which nothing
    stopped has nothing to say here, and the section is below the census
    rather than inside it, so every case in this tool's suite that cuts the
    census on the next `===` header keeps reading the same text.

    The rows are named per capture, with the window and the block each fell
    in, and the consequence is the paragraph under them rather than a line at
    each: withholding is per block, so one sentence covers every window that
    lost its number to it.
    """
    print("\n=== early-exit rows (a run that did not reach its hold) ===")
    landed = {row: w for row, w in placed}
    why = dict(refused)
    for path, rows in exits:
        print(f"  {os.path.basename(path)} ({len(rows)} row(s)):")
        for e in rows:
            w = landed.get(e)
            if w is not None:
                where = (f"in mark {windows.index(w) + 1}/{len(windows)} "
                         f"({w.label!r}) of block {w.block.name} "
                         f"(block {w.block.index} of {len(blocks)})")
            else:
                where = f"NOT PLACED -- {why[e]}"
            at = e.ts.isoformat(sep=" ") if e.ts else "no readable timestamp"
            print(wrap_note(f"{at}  {where}: "
                            f"{e.reason or 'the row records no reason'}",
                            indent=4))
    print()
    # Not `EARLY_EXIT_NOTE`: that one belongs to the block section below, and
    # this is a whole report's worth of runs in which one block is the whole
    # report, so printing it twice would be the same paragraph twice on one
    # screen. This one says what this run did about the rows and stops; the
    # block section is where the intact-but-withheld half is explained.
    #
    # The exit-code clause is scoped rather than stated flat, because this
    # section prints whole under `--block` and the run's exit code is that
    # block's alone: a run over a value that did not crash exits 0 over a day
    # in which another value did, which is the scoping `report_census` and
    # `report_blocks` already keep.
    print(wrap_note(
        "A placed row withholds the windows of the block it names, and "
        "whether that turns this run's exit code to 1 is that block's own "
        "answer: `--block` scopes the decision as it scopes everything else, "
        "so a run over a value that did not crash still prints its windows "
        "and still exits 0 over a day in which another value did. A row this "
        "cannot place is the exception, and refuses the run outright. Neither "
        "is a claim about the machine -- they are claims about which files "
        "were handed in and which block this run graded."))


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
    than leaving a bare refusal with no diagnosis on it. The mark gap a
    graded window reports is reported here as well, and so is the span and
    its note: a group that only just stayed one window, and a window that ran
    for a time §3's pacing does not imply, are both facts about the capture,
    and withholding the window's verdict is not a reason to withhold those
    with it.
    """
    print(f"\n--- mark {n}/{total}: {w.ts.isoformat()}  {w.label!r} "
          f"({w.source})")
    print(f"    block: {where} -- NOT GRADED")
    for line in mark_gap_note(w):
        print(line)
    print(span_line(w))
    for line in span_note(w):
        print(line)
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
    as a mark the walk could not place. The mark gap goes beside it and for
    the same reason: a window built from more than one raw mark says so, and
    the verdicts below are about the group rather than about any one of the
    rows that formed it.

    The span is on a line of its own, below `window runs to`, and the two are
    kept apart on purpose. That line says where this *read* stops, which under
    `--block` is the end of the block rather than the end of the window; the
    span is how long the window is in the capture. A reader who took the first
    for the second would be reading a scoping fact as a measurement, which is
    the one thing the second is not.
    """
    end = end or ("the next mark" if n < total else "the end of the capture")
    print(f"\n--- mark {n}/{total}: {w.ts.isoformat()}  {w.label!r} "
          f"({w.source})")
    where = "unplaced" if block is None else \
        f"{block.name} (block {block.index} of {total_blocks})"
    print(f"    block: {where}")
    for line in mark_gap_note(w):
        print(line)
    print(f"    window runs to {end}")
    print(span_line(w))
    for line in span_note(w):
        print(line)

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
    print("    line in every window, so a byte with no change row in it is a "
          "zero here and")
    print("    not a missing line.")
    print(wrap_note(ZERO_SCOPE_NOTE, indent=4))
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


def block_verdict(block):
    """`intact`, `void` or `partial`: whether the block closed on its restore.

    The one predicate §3's integrity check is, and it is here rather than
    inlined at `report_blocks` because the two dump sections need the same
    answer and a second copy of it is a thing that drifts. A block that is
    `void` is short the mark that says the byte was put back, so its windows
    are withheld; that is a statement about what the capture holds and
    nothing else.

    **Per capture, over `Block.closers` and not over the fused last window.**
    The three consoles are three processes reading three ranges and each mark
    is typed into one of them by hand, so the fused label is whichever
    console's spelling `parse_mark` reads first and the fused *existence* is
    whichever console recorded one. A block whose restore reached two of the
    three has a fused window reading `restored ...`, and grading that window
    grades the block `intact` on the strength of one of the two -- which is
    how a console holding its own change rows and no restore mark at all came
    to be reported as a closed block off the other two's (#450). Which console
    that is depends on which one missed the mark; see the module docstring.
    The three words are the three shapes the per-capture record has: every
    capture that recorded anything in the block closed on the restore, none of
    them did, or some did and some did not.

    `partial` is a word of its own rather than a qualified `intact` because
    `intact` is the word a fold-in files, and the whole point is that a
    fold-in must not be able to file this one. It is not a third kind of
    evidence either: `report_blocks` counts it beside `void` and the same
    note answers it, because a block short its restore in one console is as
    unable to close its last window in that console as one short in all three.

    `Block.closers` is a property, so this needs nothing run over the block
    first. A block with no windows would answer `void` on an empty record,
    which is also what a caller that never built one gets.
    """
    closers = block.closers
    closed = [label for _, label in closers
              if parse_mark(label)[0] == "restore"]
    if closed and len(closed) == len(closers):
        return "intact"
    return "partial" if closed else "void"


def closers_note(block):
    """Which captures closed a block on the restore, and which did not.

    The clause `report_blocks` appends to every block's line, and the
    per-capture answer behind the verdict word above it: a block that closes
    in every capture and one that closes in one of three read the same without
    this, and the operator's next move after either is to a console rather
    than to §3, so the console is named.

    The label each capture that did not close ended on is quoted with it,
    because that is the row the operator has to go and find and it is the only
    thing in the report that says what that console took the block to be.
    Captures that all ended on one label share it rather than repeating it
    once per name -- a day where every console stops at the write says the same
    thing three times otherwise, and the names are the part that differs.

    Reads the same `Block.closers` the verdict reads, so the clause and the
    word above it cannot disagree about which captures closed.
    """
    closed, groups = [], {}
    for path, label in block.closers:
        if parse_mark(label)[0] == "restore":
            closed.append(os.path.basename(path))
        else:
            groups.setdefault(label, []).append(os.path.basename(path))
    note = "; the restore is in " \
        + (", ".join(closed) if closed else "none of them")
    if not groups:
        return note
    said = []
    for label, names in groups.items():
        who = ", ".join(names)
        said.append(f"{who} all end on {label!r}" if len(names) > 1
                    else f"{who} ends on {label!r}")
    return f"{note} -- {'; '.join(said)}"


def block_marker(block):
    """The words one block's own reads carry, or '' if it has nothing to mark.

    Keyed on `block.problems`, not on the restore check alone, and the two are
    different facts `report_blocks` prints as two: a block can hold its
    restore and still be short an action earlier in it. `missing-mark` and
    `disagreeing-marks` are both that shape -- `block_verdict` calls their
    one block `intact` and `main` still withholds every one of its windows --
    so a marker keyed on the restore alone would print nothing for a block
    whose windows the run refused anyway, which is the defect this exists to
    stop.

    What a marker names is the windows rather than the block's findings,
    because the windows are what this run refused and what it is not entitled
    to speak for. `VOID` and `PARTIAL` here mean what `report_blocks` means by
    them: short a restore mark in every capture or in some, not that anything
    did or did not happen.

    The early-exit branch is a third fact rather than a fourth wording of the
    first: a block that holds its restore and whose capture records the run
    ending early inside it is intact, and a marker saying its mark set does not
    hold would send the operator to a console that recorded all of them. It
    wins over the mark-set wording when a block has both, because the census
    above prints the kinds and this line is the one a reader takes to a
    terminal. It does not win over `partial`, for the reason above: that one
    *is* short a mark, in some capture, so the operator has to be sent to it.
    """
    if not block.problems:
        return ""
    verdict = block_verdict(block)
    if verdict == "void":
        return "VOID, its windows were withheld above"
    if verdict == "partial":
        return ("PARTIAL, its windows were withheld above -- the restore is "
                "not in every capture")
    if any(k == "early-exit" for k, _, _ in block.problems):
        return ("this capture records the run ending early inside it, its "
                "windows were withheld above")
    return "its mark set does not hold, its windows were withheld above"


def verdict_marker(here):
    """The words to carry on a read for one value, from that value's blocks.

    Empty when every one of them had its windows printed, which is most
    reads: the marker's whole job is to say a block's windows were withheld,
    so the common path stays byte-identical to what it printed before this
    existed.

    Two blocks in one capture can share a value -- the same value written
    twice in a day, which `Block.index` exists to tell apart -- and then a
    read under that value spans both, so the marker names both rather than
    only the one that was refused. A read over a withheld and a printed block
    is not a read of one block, and a reader told only the withheld half is
    told a half-truth.
    """
    markers = [block_marker(b) for b in here]
    if not any(markers):
        return ""
    if len(markers) == 1:
        return markers[0]
    return "; ".join(f"block {i} of {len(markers)} is "
                     + (m if m else "intact, its windows were printed")
                     for i, m in enumerate(markers, 1))


def verdicts_for(blocks, selected):
    """The block verdicts the two dump sections carry, as {value: marker}.

    Built from the same block set `report_blocks` checked -- every block
    unscoped, the selected one alone otherwise. That scoping is the whole
    reason this is not `for b in blocks`: on a `--block 0xA0` run the other
    blocks were never looked at, and an index over all of them would print
    "0x00 is VOID" about a block this run knows nothing of, which is the
    defect this exists to fix, one step removed. A value this run did not
    check gets no entry at all, and the reader says so in words rather than
    letting the group line read as a result for a block it knows nothing of.

    A value in one block that had its windows printed is in the index with an
    empty marker rather than left out, so "checked and nothing to mark" and
    "not checked" stay two different answers.
    """
    index = {}
    for block in blocks if selected is None else [selected]:
        index.setdefault(block.value, []).append(block)
    return {value: verdict_marker(here) for value, here in index.items()}


def verdict_note(value, verdicts):
    """(marker, section-level note lines) for one read.

    An empty marker when the run has nothing to say about that value's block,
    which is most reads: the marker exists for a block whose windows were
    withheld, and an intact block's were printed. The two ways of having
    nothing to say are kept apart on purpose. `verdicts is None` is a caller
    that passed no index at all, and degrades to what the report printed
    before the marker existed; a value the index does not name is a run that
    checked a different block, and the operator is told that rather than left
    to read a group line that looks like a normal result.

    The marker comes back bare rather than already carrying the ` -- ` the
    group line puts in front of it, so each caller can decide how to set it:
    one appends it to an existing line, the other only asks whether there is
    one.
    """
    if value is None or verdicts is None:
        return "", []
    if value not in verdicts:
        return "", [wrap_note(
            f"no block under test 0x{value:02X} is in this run, so no "
            "verdict is carried on this read: which blocks it did check is "
            "in the section above")]
    return verdicts[value], []


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

    **The verdict is per capture, and every line names the captures it rests
    on.** A block's last *fused* window is one console's mark in the grammar
    of three, so grading it grades the block on whichever of them recorded
    one, and a block whose restore reached two of the three consoles read as a
    finished block to the third -- which is how a console holding its own
    change rows and no restore mark at all reads as a closed block off the
    other two's (#450). `block_verdict` reads each capture's
    closing mark and returns one of three words, and `closers_note` appends the
    captures behind whichever one printed, so the console that was missed is
    named rather than assumed. `PARTIAL` is the mixed case, and it
    counts in the tally below exactly as `void` does, because a block short
    its restore in one console is as unable to close that console's last
    window as one short in all three.

    `intact` prints as well, so a reader of a fold-in can see that the check
    ran and held rather than inferring it from the absence of a complaint --
    silence about a missing restore is the failure mode this exists to stop,
    and the absence of the passing case is the same shape.

    A block whose mark set does not hold is intact here and not graded
    anyway, which is two different facts and are printed as two: the restore
    is there, and an action before it is missing from a capture. Only the
    second one withholds the windows. So does a block whose capture records
    the run ending early inside it, and for the same reason: the restore is
    written from a `finally`, so it lands whether or not the arm got to its
    hold, and the capture is short a hold rather than short a mark.
    `EARLY_EXIT_NOTE` is what this section says for that one, because the
    mark-set note would be sending the operator after a mark the block has.

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
        # The capture breakdown rides on the verdict word's own line rather
        # than on the `value under test` one below: a reader who takes this
        # section's verdict into a fold-in takes the line that says `intact`,
        # and the two facts it is made of -- which restore, recorded where --
        # belong together or the second is not read.
        note = closers_note(block)
        verdict = block_verdict(block)
        if verdict == "intact":
            print(f"  block {i}/{total}: intact -- last mark {last.label!r} is "
                  f"the restore{note}")
        elif verdict == "partial":
            # Counted beside `void` rather than apart from it: a block short
            # its restore in one console cannot close its last window in that
            # console, so it is as unreadable as one short in all three, and
            # the note below is the one that says what to do about it.
            void += 1
            # Branched on `parse_mark` because this is the only one of the
            # three verdicts whose clause can contradict the note beside it.
            # `intact` and `void` each name a block that closed in every
            # capture or in none, so their clause is a statement about the
            # block and holds whichever console typed the fused label first.
            # Here the block closed in some of them, and the note says which:
            # a fused label whose first spelling is the short console's write
            # cannot be called the restore on the same line that names that
            # write as what the short capture ended on.
            if parse_mark(last.label)[0] == "restore":
                clause = (f"last mark {last.label!r} is the restore, but not "
                          "in every capture")
            else:
                clause = f"last mark is {last.label!r}, not the restore"
            print(f"  block {i}/{total}: PARTIAL -- {clause}{note}")
        else:
            void += 1
            print(f"  block {i}/{total}: VOID -- last mark is {last.label!r}, "
                  f"not the restore{note}")
        tail = (f"value under test {block.name}; roles "
                f"{', '.join(block.roles)}")
        if block.problems:
            tail += " -- NOT GRADED, its windows are not printed"
        print(f"    {tail}")
    # One note under the section, as before, and which one is the decision
    # rather than an ordering accident: a block withheld for an early exit is
    # intact, so the mark-set note would be explaining a failure it did not
    # have. An early exit wins over a mark set here for the reason
    # `block_marker` gives: the kinds are on the census line above, and this
    # paragraph is the one that says what to do about it.
    early = any(k == "early-exit"
                for b in shown for k, _, _ in b.problems)
    if void:
        note = VOID_BLOCK_NOTE
    elif early:
        note = EARLY_EXIT_NOTE
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


# Why a `--dump-pair` given one file twice is not a bracket, as one string
# both readers print. `report_dump_pairs` drops such a pair from the
# whole-block read and `report_readback` withholds it as a §4.6 readback, and
# one spelling is the point of the predicate below rather than a tidiness: two
# readers deciding the same thing must not be able to disagree about what they
# said. Kept as the line the whole-block section already printed, so the
# suite's `both sides are the same file` assertion is over the reason rather
# than over one reader's phrasing of it.
SAME_FILE_PAIR = (
    "both sides are the same file, so this pair is not graded: a read "
    "compared with itself proves nothing. Pass the before and after dumps "
    "of one range as two different files.")


def pair_refusal(before, after):
    """Why a --dump-pair cannot be read at all, or `None` if it can.

    The one place the answer lives, because two readers need it and one of
    them had their own copy: `report_dump_pairs` skips such a pair, and
    `report_readback` must not hand the operator the same pair as the way to
    take a readback. Nothing propagated the refusal out of the first loop, so
    §4.6 named a pair the block section was calling not a bracket -- and a
    self-diff's after file *is* its before file, so following that hint passes
    §4.6 a pre-write dump and the section then reports the byte as one that
    something put back. Whether a pair can be read is a fact about the two
    files, so it is asked once and both readers print what comes back.

    Path identity rather than the `<value>-before-`/`<value>-after-` spelling,
    for the reason `report_dump_pairs` gives and for the same reason its own
    check was already on resolved paths: `x.txt` and `./x.txt` are the same
    mistake written two ways, and §6's naming is a convention the flag does
    not require.

    A `disagree` pair and a pair belonging to a block a `--block` run is not
    testing are refused too, in `report_dump_pairs`, and neither is left out
    by accident. They are left out on purpose: both are about which block a
    bracket is filed under, where this is about whether it is a bracket at
    all, and a predicate that grew to cover them would change which pair §4.6
    names on shapes no committed fixture reaches. This is the shape they have
    somewhere to go when that change is made.
    """
    if os.path.realpath(before) == os.path.realpath(after):
        return SAME_FILE_PAIR
    return None


def report_dumps(dumps, wrote, pairs, block_value=None, verdicts=None,
                 unread=()):
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

    `verdicts` carries the block section's verdict for each value, so a read
    taken for a block whose windows were withheld is marked as one. The read
    itself is still taken -- it is a claim about two files on disk, true
    whatever the CSV mark set did -- so what changes is the claim's scope, and
    `verdicts=None` degrades to the pre-marker output rather than to an
    error. A group for a block this run did not check is given no verdict at
    all, for the reason `verdicts_for` gives.

    The heading line is unchanged whatever the grouping does. It is what both
    §4.6 readers in the test suite cut the section on, and a heading that
    grows a value in it breaks both of them for no gain -- the block is
    named on the first line under it instead.

    A dump that would not open is in the run's dump list with no bytes behind
    it rather than out of it, which is `read_dumps`' half of the contract and
    is load-bearing here: the readback is taken from the block's last dump,
    and deleting the unreadable one promotes the dump before it into that
    place, where "the last dump still holds the written 0xA0" would be a true
    sentence about a file the operator did not name last. It prints its own
    line in the group instead of the byte it cannot have, so the section
    keeps its shape and the operator can see which file is missing rather
    than finding a silently shorter list.

    The "no dump given" line is only for a run that handed in none, and stays
    byte for byte: the tests assert it, and it is true of every run it is
    printed for. A run that handed in dumps and had every one of them fail to
    open is a different fact, and printing the same sentence would be false --
    the operator did give files, and this is what became of them.
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

    unreadable = dict((path, exc) for path, exc in unread)
    for value, how, here in groups:
        # Nothing is carried for a group this run will not read: a `--block`
        # run's other blocks were never checked, so a verdict on one would be
        # about a block the run knows nothing of. `verdict_note` answers for
        # the value once, and the group line and the readback below are the
        # two places that want it.
        marker, notes = verdict_note(
            value, None if block_value is not None
            and value != block_value else verdicts)
        if value is None:
            print("  no block named: these files carry no §6 <value> and "
                  "neither --block nor --wrote was given")
        else:
            suffix = f" -- {marker}" if marker else ""
            if how == "name":
                print(f"  block 0x{value:02X}, from the <value> in these "
                      f"files' §6 names{suffix}")
            else:
                print(f"  block 0x{value:02X}, from --block/--wrote; these "
                      f"files carry no <value> of their own{suffix}")
            for line in notes:
                print(line)
        if block_value is not None and value != block_value:
            for path, _ in here:
                print(f"    {path}: belongs to block 0x{value:02X}, not the "
                      f"block under test (0x{block_value:02X}) -- not read "
                      "for §4.6 here")
            continue
        for path, values in here:
            if values is None:
                print(f"  {path}: not read: {unreadable[path]}")
                continue
            v = values.get(MANUAL_FAN_CTRL)
            if v is None:
                print(f"  {path}: 0x{MANUAL_FAN_CTRL:04X} not covered by this "
                      "dump")
            else:
                print(f"  {path}: 0x{MANUAL_FAN_CTRL:04X} = 0x{v:02X}")
        report_readback(here, wrote, pairs, value, marker)
    if block_value is not None and not any(v == block_value
                                          for v, _, _ in groups):
        print(f"  no dump was given for block 0x{block_value:02X}, so §4.6's "
              "readback for it was not taken; the dumps named above are "
              "another block's")
    if all(values is None for _, values in dumps):
        print(f"  none of the {len(dumps)} dump(s) given could be read, so "
              "§4.6 was not checked; each is named above")


def report_readback(here, wrote, pairs, value, marker=""):
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

    `marker` is the caller's verdict for this value, and it is why the
    verdict sentence below is not the last word on a refused block. "The last
    dump holds the written 0xA0" is true or false of the last file on disk
    and is true here whatever the CSV mark set did, so the sentence is kept
    -- and the scoping line below says what it is a reading of. The dumps
    were still read; a block being `void` says the capture is short a mark,
    not that these bytes were never in evidence. The marker itself is
    already on the group line above and is not repeated here.

    Preconditions stand between these dumps and that sentence, and this is
    where each one that is missing is said. One is that the block's last
    dump holds `0x0751` at all; the notice above covers that one, and a
    `--dump-pair` can be named in its place because a file can stand in for
    a missing file. The pair named is one that can be *read*, and that is
    `pair_refusal`'s question rather than coverage's: a pair given one file
    twice reaches the address and is not a readback of anything, so it is
    named with the reason and the walk goes on to the next pair rather than
    stopping on it. Another is that something names the value that was
    written -- the block's own, off a §6 file name, or off `--wrote` or
    `--block` -- and no file can stand in for a number, so that notice is
    printed on the dumps alone, whether or not a pair was given. When both
    are missing the two notices print together: they are two independent
    facts, and the second conditioned on the first would make the tail of
    the section depend on a condition the reader cannot see.

    The other one is not a missing input but a limit on what the comparison
    that *was* taken can say. "Still" asserts that the byte held the written
    value before the write as well as after it, and the file that would
    support that half is the block's first `--dump` -- whose `0x0751` byte
    `report_dumps` has already printed two lines above this call. So the
    before-side is read too, and the word is gated on what it found there. A
    first dump that demonstrably held something else is the case the verdict
    lines were written for and leaves both of them exactly as they are. A
    first dump that already holds the written value gets a line of its own,
    naming what that leaves open rather than which of the two readings
    happened: the write did not take, or the dump named `before` was taken
    after it, and nothing in the files separates those. A group of one dump
    keeps the value comparison and its calibration clause and loses the word,
    because one file says nothing about what the byte held beforehand, and a
    run is not required to hand in a pair -- refusing the comparison there
    would throw away a fact the operator can use. A first dump that does not
    reach `0x0751` has no before-side value to compare against, so it is not
    a case here and the section reads as it always has.

    The third precondition is the block's last dump not being readable at all,
    and it is the reason `read_dumps` keeps an entry it could not fill in
    rather than leaving it out. A group whose last entry is one of those has
    no last *read*, and the pair walk answers it the way it answers a last
    dump that does not reach the address: the readback was not taken, and a
    `--dump-pair` that does cover `0x0751` is named with the file to pass.
    Without it, dropping that entry promotes the dump before it, and the
    verdict prints over a file the operator did not name last -- a true
    sentence about the wrong file, which is the failure this notice exists to
    stop. A first dump that would not open has no before-side value for the
    reason the coverage case has none, so it drops the word the way the
    one-dump group does.
    """
    last_values = here[-1][1]
    if last_values is None or last_values.get(MANUAL_FAN_CTRL) is None:
        if last_values is None:
            print(f"  the block's last --dump is {here[-1][0]}, which was not "
                  "read, so the §4.6 readback was not taken -- nothing here "
                  "says what the byte held after the write")
        else:
            print(f"  the last --dump does not cover 0x{MANUAL_FAN_CTRL:04X}, "
                  "so the §4.6 readback was not taken -- nothing here says "
                  "what the byte held after the write")
        for before_path, after_path, before, after in pairs:
            if MANUAL_FAN_CTRL not in set(before) & set(after):
                continue
            reason = pair_refusal(before_path, after_path)
            if reason is not None:
                # This hint ends in an instruction, and on a self-diff the
                # instruction is the defect: the pair's after file *is* its
                # before file, so following it hands this section a pre-write
                # dump and the comparison above reports a byte that something
                # put back. Named with the reason rather than dropped, so the
                # operator can see which pair was not read instead of
                # finding no hint at all, and `continue` rather than `break`
                # because one refused entry must not hide a later pair that
                # can be read -- the refusal decides, not the position.
                print(f"    a --dump-pair reaches 0x{MANUAL_FAN_CTRL:04X} and "
                      f"is not one to read from: {before_path} -> "
                      f"{after_path}")
                print(f"      {reason}")
                continue
            print(f"    a --dump-pair does cover it: {before_path} -> "
                  f"{after_path}; both files reach "
                  f"0x{MANUAL_FAN_CTRL:04X}")
            print(f"      pass the after file as the last --dump to take "
                  f"the readback: {after_path}")
            break
    written = value if value is not None else wrote
    if written is None:
        # The other precondition, and the same kind of fact as the coverage
        # notice above: a claim about which files and which numbers were
        # handed in. Not gated on `pairs` as that one is, because a pair can
        # stand in for a missing --dump and not for a missing value -- and not
        # gated on it having printed either, for the reason the docstring
        # gives. The group line above has already said the files carry no
        # block; that is an attribution, and this is the comparison, which is
        # a different thing to have been left out.
        print("  nothing here names the value that was written, so the §4.6 "
              "readback was not taken -- no §6 <value> in these files' names, "
              "and neither --wrote nor --block on the command line. Pass "
              "--wrote 0xNN to take it; --block names a value too.")
        return
    if wrote is not None and value is not None and wrote != value:
        print(f"  these dumps are named for block 0x{value:02X} but --wrote "
              f"says 0x{wrote:02X}; the readback below is against the "
              "block's own write")
    last = (last_values.get(MANUAL_FAN_CTRL)
            if last_values is not None else None)
    if last is None:
        return
    # The before-side, read after the two guards above rather than beside them,
    # because neither of the lines below is a statement about an absent input:
    # they are about what the comparison that was just taken can support, and
    # saying them over a readback that was not taken would name a conclusion
    # no comparison on this page reached.
    first_values = here[0][1]
    first = (first_values.get(MANUAL_FAN_CTRL)
             if first_values is not None else None)
    still = "still "
    if len(here) == 1:
        # `here[0] is here[-1]`, so this file is being read as both sides of
        # the write. It settles whether the byte holds the written value now
        # and nothing about whether it ever did not.
        print(f"  one --dump for this block, so nothing here says what "
              f"0x{MANUAL_FAN_CTRL:04X} held before the write; the line below "
              "is that one file read once")
        still = ""
    elif first_values is None:
        # The one-dump case above, with the reason stated: the block's first
        # `--dump` could not be opened, so there is no earlier read of the
        # byte for "still" to be about.
        print(f"  the first --dump, {here[0][0]}, was not read, so nothing "
              f"here says what 0x{MANUAL_FAN_CTRL:04X} held before the "
              "write; the line below is the last of them read once")
        still = ""
    elif first == written:
        print(f"  the first --dump already holds the written 0x{written:02X}, "
              "so these files do not show the write landing: either the write "
              "did not take, or the dump named before was taken after it. "
              "Nothing here separates the two.")
        still = ""
    if last == written:
        print(f"  the last dump {still}holds the written 0x{written:02X}. Per "
              "CLAUDE.md that is a readback, not evidence the EC acted on it.")
    else:
        # The one writer ruled out is named, and the rest are not counted: the
        # census that would supply a count is open-ended by its own account,
        # so a numeral here is one every later census has to keep right. What
        # is worth stating is which candidate the operator should NOT spend the
        # run on.
        #
        # The `0x898A` store is `90 07 51 / e0 / 54 bf / f0` in bank0: it loads
        # the register and applies `anl a,#0xbf`, so it maps X -> X & ~0x40.
        # That is the whole of what the bytes say about it, and it is a fact
        # about the byte the register holds WHEN IT RUNS: the gate at 0x8946 is
        # `jnb acc.6,0x8998` on the live `0x0751`, not on what was written, so
        # `X & ~0x40` comes out as `written` only while X == written and
        # nothing between the write and the last dump keeps the two in step.
        # The store is therefore named on either byte that puts it in reach --
        # `written & 0x40`, the transition it is the known producer of (`0x40`
        # read back as `0x00` is what `anl a,#0xbf` does to it), or
        # `last & 0x40`, the state it runs in -- and only ruled out on the two
        # bytes both clear.
        #
        # The `xrl a,#0x40` rows in `manual-fan-ctrl-0751-writers.csv` are what
        # makes the second one reachable on a written value with bit 6 clear,
        # and they are also why the exclusion cannot be keyed on `written`
        # alone. `xrl` is a pure toggle of bit 6, so on its own it does
        # round-trip -- the row sets the bit, this store clears it, and the byte
        # lands back where it started -- but only while that row is the sole
        # intervening writer, and the same table's 0xA818, 0xABE8/0xC741 and
        # 0xAC00/0xC759 rows move other bits in the same pass. So the byte this
        # store reads is not the value written on any of those readings.
        print(f"  the last dump holds 0x{last:02X}, not the written "
              f"0x{written:02X} -- the byte moved back. What remains is the "
              "EC's other 0x0751 write paths or the vendor service, and §3a's "
              "service-stopped run is what separates them.")
        if written & 0x40:
            print("  The bank0 0x8978 temperature clear is among them: that "
                  "store is the anl a,#0xbf at 0x898E, which clears bit 6 "
                  f"(0x40) and nothing else, and the written 0x{written:02X} "
                  f"has bit 6 set -- 0x{written:02X} & 0xbf is "
                  f"0x{written & 0xBF:02X}, a different value -- so it can turn "
                  "the written value into another one "
                  "(ec/annotations/manual-fan-ctrl-0751.md §9).")
        elif last & 0x40:
            print("  The bank0 0x8978 temperature clear is among them: that "
                  "store is the anl a,#0xbf at 0x898E, which clears bit 6 "
                  "(0x40) and nothing else, so it runs only on a byte holding "
                  f"bit 6 set, and the last dump holds 0x{last:02X}, which is "
                  "one. It reads 0x0751 as the register stands rather than as "
                  f"it was written, so the written 0x{written:02X} having bit 6 "
                  f"clear -- 0x{written:02X} & 0xbf is "
                  f"0x{written & 0xBF:02X}, which is the value written -- does "
                  "not settle it: an xrl a,#0x40 row in "
                  "manual-fan-ctrl-0751-writers.csv can set that bit in "
                  "between (ec/annotations/manual-fan-ctrl-0751.md §9).")
        else:
            print("  It is not the bank0 0x8978 temperature clear on either of "
                  "those two bytes: that store is the anl a,#0xbf at 0x898E, "
                  "which clears bit 6 (0x40) and nothing else, so it runs only "
                  f"on a byte holding bit 6 set, and the written 0x{written:02X} "
                  f"has bit 6 clear -- 0x{written:02X} & 0xbf is "
                  f"0x{written & 0xBF:02X}, which is the value written -- so on "
                  "its own it did not change this byte; neither does the byte at "
                  "the last dump. It reads 0x0751 as the register stands "
                  "rather than as it was written, so that is what the two bytes "
                  "rule out and not a proof it never ran "
                  "(ec/annotations/manual-fan-ctrl-0751.md §9).")
        if last & 0x40:
            print("  Where the byte stands now is what that store runs on next: "
                  f"it holds 0x{last:02X}, so bit 6 is set now and that store is "
                  "live from here.")
        else:
            print("  Where the byte stands now is what that store runs on next: "
                  f"it holds 0x{last:02X}, so bit 6 is clear now and that store "
                  "stays out of reach while it does.")
    if marker:
        # The marker itself is on the group line above, and is not restated
        # here: a second copy of those words is a second thing to keep in
        # step, and this line's job is only to say what kind of read the
        # sentence above is.
        print(f"  That is a read of these files and not of block "
              f"0x{value:02X}'s windows, whose verdict is on the group line "
              "above: it says nothing about §4.1-§4.3 for that block, and "
              "the captures above did not hold a mark this could have been "
              "read against.")


def report_dump_pairs(pairs, block_value=None, wrote=None, verdicts=None,
                      failed=()):
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

    The "everything else" bucket names what registers.yaml names, and only
    that. The `0x0400` pair is the one that reaches it, and on a real run it
    is expected to: the bytes on that page that are a battery's own numbers
    move while a run watches it. §3's fixed CPU load is one thing that would
    move them and is not an established reason for it — the one committed
    row-level capture of this page is a battery-mode cycle with no load step in
    it, four of the nine addresses XDATA_NAMES covers moved in it, and
    xdata-0400-045f.md §8 names no cause for any of them. Four
    undifferentiated addresses left the operator to go and look them up, and
    split a byte pair across two rows leaves the 16-bit reading an addition
    to do by hand in the one report meant to save the hand work (#219). So
    each address `XDATA_NAMES` covers gets a line of its own under the flat
    list, and a pair is also printed assembled. That is the name and the two
    bytes read out of the two dumps, and it does not grade them: the heading
    keeps its "not graded here", and §3's own question is about `0x0751` and
    not about the battery.

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

    That same "nothing in the body distinguishes it" is why the block
    section's verdict rides on the group line rather than anywhere inside
    the bracket. A pair for a block whose windows were withheld is still
    compared -- a void block says the capture is short a mark, not that
    these two files disagree about anything -- but a bracket under a group
    line that names no verdict reads as an answer about that block's §4.1-
    §4.3, which is the one thing this run cannot give. The marker goes on
    the group line and nowhere else, so the bracket body and
    `group_body()`'s cut are untouched.

    Returns how many pairs were actually compared, so the closing summary
    cannot report a whole-block read for a run that took none -- a `--block`
    run handed only another block's pairs is 0.

    A pair whose before or after side would not open is named here and
    compared nowhere, and it is `read_dump_pairs` that decides which: it is
    not in `pairs` to begin with, so it cannot be counted by the loop below
    and the closing paragraph's `if graded:` cannot qualify a bracket that was
    never read. The section keeps its shape around it for the same reason
    §4.6's does -- the operator handed in a `--dump-pair` and the output has to
    say what became of it, in the position it was handed in, rather than
    leaving a shorter list to be read as the whole of the input. The "no dump
    pair given" line is for a run that was given none, and stays byte for byte
    because it is true of every run it is printed for; a run whose only pair
    would not open gets its own sentence, since the operator did hand one in.
    """
    print("\n=== whole-block dump pairs (§4.1-§4.3) ===")
    if not pairs and not failed:
        print("  no dump pair given (--dump-pair); the whole-block read is not "
              "checked")
        return 0
    for before_path, after_path, sides in failed:
        print(f"\n  {before_path} -> {after_path}")
        for side, exc in sides:
            print(f"    {side}: not read: {exc}")
        print("    this pair is not compared: a whole-block read is the "
              "intersection of two files and it needs both of them")
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
        # Nothing is carried for a group this run will not read: a `--block`
        # run's other blocks were never checked, so a verdict on one would be
        # about a block the run knows nothing of.
        marker, notes = verdict_note(
            value, None if block_value is not None
            and value != block_value else verdicts)
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
        else:
            suffix = f" -- {marker}" if marker else ""
            if how == "name":
                print(f"  block 0x{value:02X}, from the <value> in these "
                      f"files' §6 names{suffix}")
            elif how == "one-name":
                print(f"  block 0x{value:02X}, from the <value> in one of "
                      f"these two file names; the other carries none{suffix}")
            else:
                print(f"  block 0x{value:02X}, from --block/--wrote; these "
                      f"files carry no <value> of their own{suffix}")
            for line in notes:
                print(line)
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
            reason = pair_refusal(before_path, after_path)
            if reason is not None:
                # A pair is whatever the operator says it is, and the same
                # file twice is the one input error this flag cannot see on
                # its own. Grading it would print "unchanged" for every
                # address, which is a true statement about nothing -- the file
                # agrees with itself by construction. Flagged and skipped
                # rather than fatal, so the window report and the §4.6
                # readback the operator also needs still get printed. The
                # predicate is `pair_refusal`, not a test written here,
                # because `report_readback` has to refuse the same pair.
                print(f"\n  {before_path} -> {after_path}")
                print(f"    {reason}")
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
                # The names go on their own lines *under* that list and not
                # beside it. The suite's `differing_addresses()` recovers the
                # set of differing addresses by reading the line immediately
                # after this heading and nothing else, so a register name or
                # a `0x0438/0x0439` partner spelled on that line would be
                # read as one more differing address and break the
                # cross-check against the captures (#219).
                for a in others:
                    for line in xdata_name_lines(a, set(common), before,
                                                 after):
                        print(line)

    # Gated on `failed` being empty as well as on `groups` being non-empty and
    # on the block being absent, and both extra terms are the same fact the
    # group lines above are: the sentence is a claim about which block the
    # pairs named above belong to, and a pair that could not be read was never
    # filed under one. Without the `groups` term, a `--block` run whose only
    # pair would not open was told the pair was another block's. Without the
    # `failed` term, that same run told the same thing with a readable pair
    # naming another block beside the unreadable one: the readable one files a
    # group, so the footer fires, and the pair the run never filed is named
    # under it -- and so is the first half, since a pair that named the block
    # under test and would not open is a pair that was given. The unreadable
    # pair's own line above says what became of it, the readable pair's line
    # says whose it is, and the paragraph below this one says nothing was
    # compared, so the section loses the unfounded sentence and not the fact.
    if block_value is not None and not failed and groups \
            and not any(v == block_value for v, _, _ in groups):
        print(f"  no --dump-pair was given for block 0x{block_value:02X}, so "
              "the whole-block read for it was not taken; the pairs named "
              "above are another block's")

    if graded:
        print("\n  Every `unchanged` above says the byte did not differ "
              "between these two reads, which is not a claim that it did not "
              "move inside the block: §5, a byte that does not move inside a "
              "window may still move at the next suspend, AC transition or "
              "EC reset. This bracket is complementary to the windowed CSV "
              "read above, not a stronger one -- a byte that moved and was "
              "back where it started by the after-dump reads unchanged here "
              "whether or not the captures recorded the move, and a byte that "
              "moves entirely between two of ec_watch.py's sweeps is in no "
              "change row at all. Neither gap is closed by the other read. "
              "`0x0F5D-0x0F5F` is a bucket of its own for the reason printed "
              "under it, and §4.2's prediction is about the `0x0F00-0x0F5C` "
              "bytes above it.")
    else:
        # Printed outside the group loop and ungated, this paragraph used to
        # close a run that compared nothing, over a section whose only lines
        # were refusals: there is no `unchanged` above it to qualify, and a
        # reader who found one would be reading a note about a bracket that
        # was never taken. Strictly narrower than before -- an empty `pairs`
        # has already returned above -- so the only runs it stops printing
        # on are the ones where it was describing lines that do not exist.
        # Said rather than dropped, for the reason §4.6's refusal is: a
        # silent ending after a refusal is the same defect one step down.
        print("\n  no dump pair here was compared, so there is no whole-block "
              "read to qualify: the pairs above were refused, and each says "
              "why")
    return graded


def self_test(run=None):
    """Run the committed suite in a subprocess and return its exit code.

    `run` is `subprocess.run` unless a caller passes its own. That seam is what
    the suite's own case for this mode drives: a `--self-test` case that ran
    the mode for real would have the mode run the suite that contains it, which
    runs the case again, and so on. The real discovery is what the gate calls,
    and what `python3 ec/tools/grade_0751_isolation.py --self-test` runs by
    hand.
    """
    cmd = [sys.executable, "-m", "unittest", "discover",
           "-s", TOOL_DIR, "-p", SUITE_FILE]
    proc = (subprocess.run if run is None else run)(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # unittest's summary on one stream, so there is one thing to parse and one
    # thing to print: it writes to stderr, and its verdict is the exit code.
    out = proc.stdout or ""
    if out and not out.endswith("\n"):
        out += "\n"
    # The count decorates and never decides. An expected count in a runner
    # turns every added test into a failure, which is the wrong trade --
    # tools/run-tests.sh gives the same reason for printing its own counts.
    m = re.search(r"^Ran (\d+) tests? ", out, re.M)
    n = int(m.group(1)) if m else 0
    if proc.returncode:
        print(out, end="")
        print(f"{SUITE_FILE}: FAILED")
        return 1
    if not n:
        # A discovery that matched nothing exits 0 and prints OK, which from
        # the outside is indistinguishable from a suite that passed. A renamed
        # file, a moved -s, a pattern that no longer matches: each turns a gate
        # green without running anything, and the moment to notice is before it
        # has stopped failing. tools/run-tests.sh refuses the same empty glob a
        # level up, and says the same thing about it.
        print(out, end="")
        print(f"{SUITE_FILE}: FAILED -- no test ran, which is not a pass. It "
              f"is discovered at {os.path.relpath(TOOL_DIR)}; if that is not "
              "where the suite is, this mode is looking in the wrong place.")
        return 1
    print(f"{SUITE_FILE}: {n} test{'s' if n != 1 else ''}, passed")
    # The gate's own deferral, in the same place and for the same reason: a
    # run that exercises nothing a reader can see is a check that gets
    # dropped. These are refusals over hand-built CSVs committed under
    # ec/tools/testdata/ -- no EC is opened, no register is read back, and no
    # capture was taken on the machine.
    print("\nnote  this is the tool's own refusals over the committed "
          "fixtures in\n      ec/tools/testdata/, not a run of the procedure "
          "on a laptop: §4 is not\n      re-applied to a real capture here, "
          "nothing is graded over a mark a\n      human took, and no sentence "
          "this prints is evidence about the machine.")
    return 0


def main(argv=None):
    # `sys.argv[1:]` spelled out because argparse does that itself for a None,
    # and the flag has to be readable before the parser ever sees the list.
    argv = sys.argv[1:] if argv is None else list(argv)
    if "--self-test" in argv:
        return self_test()
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
                    help="ecrw.py dump output; repeat for before- and after-"
                         "-- a file that cannot be read is named with the "
                         "error where it would have been read and takes no "
                         "part in the comparison")
    ap.add_argument("--dump-pair", action="append", nargs=2, default=[],
                    metavar=("BEFORE", "AFTER"),
                    help="one range's ecrw.py dump before/after pair, as §3's "
                         "steps 0 and 6 take it; repeat per range, and never "
                         "the same file twice -- a pair read against itself "
                         "proves nothing and is not graded, and a pair whose "
                         "before or after file cannot be read is named with "
                         "the error and not compared either. Read for the "
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
    exits = []
    for path in paths:
        # A refusal of a file is an exception, and the exception's own text is
        # the sentence -- `bom_refusal`, the `UnicodeDecodeError` of the
        # declared codec, a short row, a timestamp `parse_ts` cannot read -- so
        # it is printed here rather than restated. Two reasons it is printed
        # and not caught higher: a file this cannot read is a file the operator
        # named on the command line and can be pointed at a different one, and
        # one raised out of `main` is a traceback over a §6 file list that is
        # otherwise a clean refusal.
        #
        # "Nothing was graded", and not "nothing was read": §6 passes one CSV
        # per watcher, so a later path here can be refused after an earlier one
        # has been read and had its census line printed, and telling that
        # operator nothing was read would be false about the two captures that
        # were. The path is named here as well as in the refusal above so the
        # sentence says which file ended the run. Returning rather than
        # continuing to the next path is deliberate and is the same choice the
        # repeat refusal above makes: every section of the report below is
        # about the captures as one set, so a set one of whose members is
        # unreadable has no report, and the census lines already on stdout are
        # counts rather than a grade.
        #
        # **One `open()` and one read per capture, and both passes over it**
        # (#767). This used to be two: `read_capture` for the marks and
        # changes, then `read_early_exits` for the crash rows, a few lines
        # apart, and the two counts were appended to one printed line -- so
        # the census line this tool prints per capture was a composite of two
        # moments on a file §3 has three watchers appending to by design. The
        # refusals are `read_capture`'s, in its order, off the one buffer: the
        # mark first (three bytes, decidable without a decode, and the one the
        # strict rules must have before they read a row), then the decode, so a
        # file carrying both faults is named the same way here as
        # `read_capture` and `existing_mark_findings` name it.
        #
        # `read_capture` itself is not called; its signature and executable
        # body are unchanged, and only its docstring is not. Its two-tuple is
        # a contract with the other tools that unpack it, and taking that
        # contract over would be a change to a reader other
        # programs depend on to fix a problem in this one. The strict rules
        # below are its two (`skippable_row` and `take_capture_row`), over
        # rows this read, and
        # `test_read_capture_still_returns_the_two_tuple_the_other_tools_unpack`
        # holds the reader to the contract while this holds the rules to it.
        rows, decode_failure, has_bom = capture_snapshot(path)
        try:
            if has_bom:
                raise ValueError(bom_refusal(path))
            if decode_failure is not None:
                raise decode_failure
            m, c = [], []
            for row in rows:
                if skippable_row(row):
                    continue
                take_capture_row(row, path, m, c)
        except ValueError as refusal:
            print(f"\n{refusal}", file=sys.stderr)
            print(f"{path}: nothing was graded. A capture is what "
                  "`ec_watch.py --mark --csv` and "
                  "`manual_fan_ctrl_probe.py --csv` write, in the schema "
                  "`ec/tools/probe_log_to_capture.py` reads into; a probe "
                  "console log predating that mode is converted with it "
                  "rather than graded as one.", file=sys.stderr)
            return 1
        captures.append((path, m))
        marks += m
        changes += c
        read = f"{path}: {len(m)} mark(s), {len(c)} change row(s)"
        # Counted here rather than at the section below, because this line is
        # what a capture with no MARK rows is refused on -- and a capture with
        # no marks and an early-exit row in it is the one the refusal has to
        # be able to name. Off the same `rows` the marks above came from, so
        # the two numbers in this line describe one file rather than two.
        found = early_exits_of(rows, path)
        if found:
            exits.append((path, found))
            read += f", {len(found)} early-exit row(s)"
        print(read)

    if not marks:
        print("\nno MARK rows in these captures. ec_watch.py writes them only "
              "when --mark and --csv are both given; without them a byte that "
              "moved 400 ms after the write and one that moved 40 s after it "
              "cannot be told apart, and §4 cannot be applied.", file=sys.stderr)
        return 1

    windows = build_windows(marks, changes)
    blocks, unplaced = assign_blocks(windows)
    unreads = unplaceable_marks(unplaced)
    unagreed = unplaced_window_problems(unplaced, captures)
    for block in blocks:
        block.problems = check_block_marks(block, captures)
    # After the block walk, because that is what a row is charged to, and
    # after `check_block_marks`, because `Block.problems` is assigned there:
    # appending to a list this replaces would drop the row on the floor again.
    early_placed, early_refused = charge_early_exits(
        [e for _, rows in exits for e in rows], windows)

    selected = None
    twins = None
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
        # Left `None` for a value more than one block carries, so the census
        # prints the whole day with nothing marked `-- not selected in this
        # run`: no block was selected, and marking one of them would name the
        # block this refusal is about to decline to choose.
        twins = repeated_values(blocks).get(wanted)
        if not twins:
            selected = next((b for b in blocks if b.value == wanted), None)

    report_census(captures, windows, blocks, unplaced, unreads, unagreed,
                  selected)
    if exits:
        # Whole, and not scoped to the selected block, the way the census is:
        # §6 runs one `--block` per value, and an attachment for a good value
        # that said nothing about a crash in another one would be a report of
        # a day in which nothing stopped.
        report_early_exits(exits, early_placed, early_refused, windows, blocks)

    if early_refused:
        # Before the window report, and not per block: a row that cannot be
        # placed says nothing about any arm, so a window printed beside it
        # would be a window of a length this run cannot name. `--block` does
        # not narrow it away, on `unplaceable_marks`' argument -- and, as
        # with that one, a scoped refusal here would print the block that was
        # selected `intact` and exit 0 over a capture that says otherwise.
        why = "; ".join(text for _, text in early_refused)
        print(f"\n{EARLY_EXIT_REFUSAL.format(why=why)}", file=sys.stderr)
        return 1

    # The two refusals `--block` can earn, in one place and in this order: a
    # value two blocks carry, then a value in none. Both leave `selected` at
    # `None` -- the first deliberately, above -- so the ambiguous case has to
    # be asked about before the no-match one, or a value two blocks carry
    # would be reported as a value in no block, which is the opposite of what
    # is wrong with it.
    if twins:
        # Named, not selected, because the value is what identifies a block:
        # `--block`'s own help, §6's per-value dump names and the per-block
        # lines above all take the value rather than a position in the mark
        # stream, and nothing in the marks says which of the blocks a window
        # belongs to. Taking the first of them is a verdict on whichever came
        # first rather than on any of them, and the shape §3's own remedy
        # produces puts the attempt that came out void first. A selector that
        # could reach another would make appending a re-done block under the
        # same value a supported thing to do, which is the state the census
        # line above and `VOID_BLOCK_NOTE` are removing.
        #
        # After the census, which is where the blocks are named with their
        # indices, so the refusal points at lines the operator has just read
        # rather than repeating the day at them. The remedy is given as a
        # pointer rather than as this run's diagnosis, because a value can
        # reach this two ways and the census above says which: §3's re-done
        # block appended to the set wants a second `<date>`, and a day whose
        # consoles marked too far apart for the merge wants the distances the
        # census already named.
        which = " and ".join(f"block {b.index} of {len(blocks)}" for b in twins)
        print(f"\n--block {args.block!r} names {len(twins)} blocks in these "
              f"captures, {which}. The value under test is what identifies a "
              "block, so a value this many blocks carry names none of them "
              "one: this is not graded as the first of them, because a first "
              "match over several is a verdict on whichever came first rather "
              "than on any. Read the census above for what each of them is "
              "short of; where this is §3's re-done block, the remedy is that "
              "block on its own <date> and its own set of the three CSVs "
              "(§3). --block names one block of a value that is in one block.",
              file=sys.stderr)
        return 1

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
    graded_unplaced = 0
    for i in shown:
        w = windows[i]
        if w in unreads:
            # A label this cannot read is a window it cannot say what it is a
            # window of. An unplaced mark whose label *is* readable -- a stray
            # restore, a control arm whose write never came -- is graded
            # below, with `unplaced` on its header, unless the branch under
            # this one refuses it first: its rows are real and there is no
            # other arm to mis-file them under, but the window it opens is
            # still not the action any capture recorded.
            withheld += 1
            report_withheld_window(w, i + 1, len(windows), "unplaced",
                                   unreads[w])
            continue
        if w in unagreed:
            # The two agreement checks the block branch below runs, over a
            # window no block's mark set can reach. Window-scoped, so a
            # `--block` run is still decided by its own block alone -- unlike
            # the branch above it, which is fatal for the whole run because an
            # unreadable label can change which blocks there are at all
            # (`unplaceable_marks` is where that is reasoned). A window
            # already in no block cannot re-shape one, and no block's
            # completeness rests on it.
            withheld += 1
            report_withheld_window(w, i + 1, len(windows), "unplaced",
                                   unagreed[w])
            continue
        if w.block is not None and w.block.problems:
            withheld += 1
            report_withheld_window(
                w, i + 1, len(windows),
                f"{w.block.name} (block {w.block.index} of {len(blocks)})",
                [text for _, on, text in w.block.problems if on is w])
            continue
        if w.block is None:
            # Counted here, where the window is printed, and not over `shown`
            # in one go: a window can be both in no block and withheld -- the
            # 12:00 stray in `unread-window/` is exactly that -- and the
            # withheld banner already names it. Taking the count at the print
            # point makes the two figures disjoint by construction, so the
            # banner's "1 of the 8" and the note's "1 of the 7" cannot be one
            # window counted twice, and the denominators differ the way the
            # `graded` figure below them already does.
            graded_unplaced += 1
        for name in report_window(w, i + 1, len(windows), w.block,
                                  len(blocks),
                                  end if i == shown[-1] else None):
            if name not in moved_groups:
                moved_groups.append(name)

    # The windows the loop above actually printed. `len(shown)` and not
    # `len(windows)`: on a --block run that is that block's own windows rather
    # than the whole mark stream's, and a figure over the stream would be
    # counting windows this run was never shown. `withheld` is subtracted from
    # the same set it was counted over, so the two cannot name one window
    # twice.
    #
    # It no longer shares a denominator with the withheld banner, which names
    # both on a `--block` run, so the agreement the two used to have by
    # construction is stated here instead of there. On a `--block` run it is
    # also 0 or `len(shown)`, and that is a property of the paths rather than
    # a fixture: the two "in no block" refusals are fed from `assign_blocks`'
    # `unplaced` list, whose windows have no block and so cannot be in `shown`,
    # which leaves only the block's own mark set -- and a block either has
    # problems or does not. The two sentences below that print `graded` are
    # therefore unreachable on a `--block` run: a withheld block grades
    # nothing, so `graded == 0` takes the branch before either of them.
    graded = len(shown) - withheld

    void = report_blocks(blocks, selected)
    # The same scope `void` and `withheld` take, and for the same reason: a
    # `--block` run is about one block, and the value of another block being
    # carried twice is not a fact about this one. `--block` on a repeated
    # value is refused above, so the selected block's own value is never one,
    # and this is 0 on every run that gets that far. Counted over the blocks
    # the block section just graded rather than over `blocks`, so the figure
    # and that section's lines cannot disagree about which blocks it covers.
    graded_blocks = blocks if selected is None else [selected]
    repeated = sum(1 for b in graded_blocks
                   if b.value in repeated_values(blocks))

    # The verdicts the block section just printed, indexed for the two file
    # sections. Built here rather than passed down from `report_blocks` so the
    # index is over the same block set that section checked -- `verdicts_for`
    # takes `selected` and scopes itself, which is the one thing a dump
    # section cannot work out for itself.
    verdicts = verdicts_for(blocks, selected)

    # Both file lists are read before either is printed, so §4.6 can name a
    # --dump-pair that covers 0x0751 while it is saying the readback was not
    # taken. The print order is unchanged and is the one §6 documents: the
    # per-window read, then 0x0751 across the dumps, then the whole-block
    # bracket on the same §4.1-§4.3 bytes.
    #
    # A file that would not open is not allowed to end the run. These two
    # readers are where that is decided, and they decide it the way the two
    # neighbouring `--dump-pair` refusals already do -- named, not graded, and
    # the window report and the §4.6 readback still printed -- because a
    # mistyped path is a claim about which files were handed in, exactly as a
    # self-diff is, and unlike a repeated capture: every section of this
    # report is about the captures, while a dump is one input among several
    # and the section that would have read it prints the omission in full.
    dumps, unread = read_dumps(args.dump)
    pairs, failed_pairs = read_dump_pairs(args.dump_pair)
    report_dumps(dumps, wrote, pairs,
                 selected.value if selected is not None else None, verdicts,
                 unread)
    graded_pairs = report_dump_pairs(
        pairs, selected.value if selected is not None else None, wrote,
        verdicts, failed_pairs)

    print("\n=== what this does and does not settle ===")
    if withheld:
        # Two denominators on a `--block` run, one on a whole-capture run.
        # `withheld` is the count the loop above took, printed on both paths
        # rather than the `All` that `withheld == len(shown)` would license
        # here: the text reports what was counted, and does not bake in an
        # invariant a future refusal path could break. The block's own count
        # comes first because the windows printed directly above are its
        # windows, and the capture's second because they are numbered in the
        # day's mark stream and the withheld ones are 2 of the day's 8, which
        # is the number a reader needs before §7's `confirmed-inert` call.
        # Whole-capture wording is left byte for byte: the two counts are one
        # number there, so it is already correct, and five tests pin it.
        if selected is None:
            scope = f"{len(shown)} window(s) above"
        else:
            scope = (f"{len(shown)} window(s) of this block ({withheld} of the "
                     f"capture's {len(windows)} window(s))")
        print(f"  {withheld} of the {scope} were not graded: {WITHHELD_REASON}")
    if unreads:
        # The line the withheld banner above would have printed, and printed
        # on its own when the run's unreadable windows are not in `shown` at
        # all -- a window in no block is not in the selected block's windows,
        # so the banner counts none of them while the exit code still turns on
        # them. Next to the banner rather than inside it because the two are
        # not one count: `withheld` is this block's and `unreads` is the run's.
        print(f"  {UNREAD_MARK_NOTE}")
    if graded_unplaced:
        # Beside the note above and before the `moved_groups` branch rather
        # than inside any one arm, which is what makes the branches compose
        # with no new interaction: silent when the count is zero, so
        # `withheld:` / `elif selected` / `else` are untouched by its presence
        # and cannot disagree with it. A run that both selected a block and
        # withheld part of it is scoped by the more specific of the two, as
        # the comment inside the `moved_groups` branch argues, and that
        # argument is unaffected. The branch below never competes with the
        # selected-block one because a `--block` run makes this count
        # structurally zero: `shown` is `[i for i, w in enumerate(windows) if
        # w.block is selected]`, and `w.block is None` cannot be in it.
        #
        # The count and not a scope, because every branch reachable with it
        # non-zero states its own scope below -- see `UNPLACED_GRADED_NOTE`.
        print("  " + UNPLACED_GRADED_NOTE.format(
            unplaced=graded_unplaced, graded=graded))
    if moved_groups:
        print(f"  At least one of the §4.1-§4.3 bytes moved after a mark: "
              f"{', '.join(moved_groups)}.")
        if withheld:
            # The movement is a fact about the windows that were printed, and
            # over a run that withheld some, it is the attribution below it
            # that decides what the fact is evidence of. Scoped here and not
            # left to the banner, so a reader who reads only the movement
            # line cannot take it for the whole run.
            #
            # The withheld window is the one exclusion this sentence can make,
            # and it can make it for the reason #725's `elif graded_unplaced:`
            # arm reasons from: a window that never reaches `report_window`
            # cannot have fed `moved_groups`, so naming it as outside the set
            # is true by construction, before the tool has to know anything.
            # A window in no block that was *graded* is not in that position
            # -- its rows do feed `moved_groups` -- so it is named as part of
            # the set instead of being subtracted from it, and `placed` is not
            # computed here. The same `0x0784` row inside block 1's write
            # window and inside `unread-window/`'s 12:04 stray prints this
            # sentence over the same `graded` and leaves the same
            # `moved_groups`, so a narrower one would be true of the first
            # placement and false of the second and the tool cannot say which
            # one it is in.
            unplaced_clause = ""
            if graded_unplaced:
                unplaced_clause = (
                    f" The {graded_unplaced} graded window(s) in no block are "
                    "part of it, and this run cannot say which arm they are a "
                    "window of.")
            print(f"  That is the {graded} window(s) that were graded. The "
                  f"{withheld} window(s) withheld above are not part of it, "
                  "and what they would have shown is not reported here."
                  f"{unplaced_clause}")
        elif selected is not None and len(blocks) > 1:
            # The same scoping, for a `--block` run that withheld nothing: a
            # clean block is graded whole, so the branch above has no count to
            # print and the movement line would be a claim about the day
            # reached with nothing between it and the attribution under it.
            # Placed here rather than in the `withheld` branch because the two
            # are not additive -- one of them already scopes the line -- and
            # because a run that both selected a block and withheld part of it
            # is scoped by the more specific of the two.
            print(f"  That is block {selected.index} of {len(blocks)}, value "
                  f"under test {selected.name}, over its {graded} window(s). "
                  f"The other {len(blocks) - 1} block(s) were not checked in "
                  "this run, so what they would have shown is not reported "
                  "here.")
        elif graded_unplaced:
            # The `moved_groups` half's own unattributed case, and the
            # counterpart of the no-movement chain's third arm: the same count
            # and the same two strays, but something moved, so what needs
            # scoping is the line above rather than an `else` this run did not
            # take. Every window here was read, so nothing was withheld and
            # neither arm above fires -- which is what let the movement reach
            # the attribution with no scope at all.
            #
            # The withheld arm's wording cannot be reused for a reason that is
            # `moved_groups` itself: it is a union of group *names* over
            # `shown`, carrying no window identity, so a `0x0784` step inside
            # an unattributed window and the same step inside a block's own
            # window print the same line and leave the same `moved_groups`.
            # "That is the 6 window(s) that belong to a value under test" is
            # therefore not a narrower true sentence here but a false one --
            # the row that produced this line, moved into the 12:00 stray
            # instead of into block 1's write window, grades this run the same
            # and moves under the same arm. So the movement stays over all
            # `graded` and the unattributed windows are named as part of it.
            #
            # "A run it only read part of" is left off for the reason the
            # no-movement arm leaves it off and states in its own comment: this
            # run read every window it was shown, so the gap is what an
            # unattributed window is a window of, not the coverage. The decline
            # itself is that arm's, unchanged, because it is the same claim
            # over the same set of windows.
            #
            # Last in the chain because the two arms above it are the more
            # specific: a withheld window or a selected block is a reason this
            # run is already smaller than the day, and this one adds an
            # attribution gap to a run that is the whole capture. The withheld
            # case over the same set of `graded` windows is a different
            # sentence with a different fix and is deliberately not handled
            # here. Nor can a `--block` run reach this: `graded_unplaced` is
            # structurally 0 there, the same argument the count's own comment
            # above makes.
            print(f"  That is the {graded} window(s) that were graded. The "
                  f"{graded_unplaced} in no block are part of it, and this "
                  "run cannot say which arm they are a window of. The static "
                  "prediction is a claim about the whole capture, and this "
                  "output does not make it over a run in which "
                  f"{graded_unplaced} of its {graded} graded window(s) are "
                  "in no block.")
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
        elif graded_unplaced:
            # The one sentence under the movement that is a claim about the
            # capture rather than about the windows printed, so it is the one
            # the scope above cannot reach and this one has to take. What is
            # kept and what is dropped is a reading, not a trimming: "capture
            # it in full" is advice and stays, and so does the observation
            # that something here contradicts §5 or §4.2 -- scoped to the
            # windows this run read, which is what the run can support.
            # Scoping is not retracting, and a PL that moved is still the
            # more interesting outcome on either reading.
            #
            # The scope is `graded` and the count rather than `placed`, for
            # #725's reason rather than its wording: `moved_groups` carries no
            # window identity, so the same row in a block's own window and in
            # an unattributed one leave the same sentence here.
            #
            # After the trigger-group split and not before it, because that
            # sentence says *what* moved -- a mailbox poke rather than a table
            # move -- and says on static evidence why, which is a claim over
            # the row that moved and not over the capture. Taking it here
            # would trade the only attribution this branch gives for a second
            # copy of the scope printed above.
            #
            # Unreachable from a `--block` run, as the count's own comment
            # says: that run's `shown` is the block's own windows.
            print("  That contradicts the static prediction in "
                  "ec/annotations/manual-fan-ctrl-0751.md §5 if it is the "
                  "PLs, or §4.2 if it is the fan table -- over the "
                  f"{graded} window(s) above, not over the capture as a "
                  f"whole: {graded_unplaced} of them are a window of an arm "
                  "this run cannot name. Capture it in full, it is the more "
                  "interesting outcome.")
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
        # not the block it sits in, because the three withholding paths above
        # do not agree on whether there is one. A window refused for its
        # block's mark set is in that block; the windows refused in no block
        # are in none at all, and the census has just said so in the same run
        # ("a mark this cannot read is a mark no block can be attributed
        # to"). So the sentence this branch ends on is the one fact all three
        # paths support -- the run is not a three-value read -- and it
        # declines to say which of them happened rather than picking the one it
        # was written against.
        if graded_unplaced:
            # A second reason the claim is not over every graded window, and
            # the count above has already said how many windows it covers. A
            # window this run *read* is not thereby a window of a value under
            # test: a label is the only thing that attributes one, and the
            # strays in `unread-window/` name 0x99, which no block's. So the
            # movement is stated over the graded windows that are windows of a
            # value under test, and the unattributed ones are named as outside
            # it beside the withheld ones. Without this the branch prints a
            # count naming 1 of the 7 in no block directly above a sentence
            # claiming all 7 -- the disclosure contradicted by the claim it
            # annotates, and #530 is about that sentence. Two reasons, one
            # sentence: the withheld wording is kept for the windows it is
            # about, because this branch is still the refusal-based one and
            # `unread-window/` withheld a window whether or not it also read an
            # unattributed one.
            placed = graded - graded_unplaced
            print(f"  None of the §4.1-§4.3 bytes moved in any of the "
                  f"{placed} window(s) that were graded and belong to a value "
                  f"under test: that is what those {placed} windows show, and "
                  f"neither the {withheld} window(s) withheld above nor the "
                  f"{graded_unplaced} graded window(s) in no block are part "
                  "of it. The static prediction is a claim about the whole "
                  "capture, and this output does not make it over a run it "
                  "only read part of -- a run in which every window was "
                  "graded, and every one of them a window of a value under "
                  "test, is what would. §7's `confirmed-inert` needs all three "
                  "values, and a window in no block, or one this report "
                  "refused to read, is one this run cannot speak for -- "
                  "whether the refused one sits in a block of its own is not "
                  "something this output can say -- so the paragraph below is "
                  "as far as this run goes.")
        else:
            print(f"  None of the §4.1-§4.3 bytes moved in any of the "
                  f"{graded} window(s) that were graded: that is what those "
                  f"{graded} windows show, and the {withheld} window(s) "
                  "withheld above are not part of it. The static prediction is "
                  "a claim about the whole capture, and this output does not "
                  "make it over a run it only read part of -- a run in which "
                  "every window was graded is what would. §7's "
                  "`confirmed-inert` needs all three values, and a window this "
                  "report refused to read is one this run cannot speak for -- "
                  "whether it sits in a block of its own is not something this "
                  "output can say -- so the paragraph below is as far as this "
                  "run goes.")
    elif graded_unplaced:
        # Every window was read and some of them are a window of nothing.
        # This is the withheld branch's gap reached from the other side:
        # nothing was refused, so there is no banner to point at, and a count
        # above zero means `graded > 0` and `withheld == 0`, so neither of the
        # two branches above this one fires -- yet the run's windows are still
        # not all windows of a value under test, and the sentence below would
        # be the whole-capture claim over a set that is not one. The mark
        # stream put a window here that no block's completeness check covers
        # (`unplaced:` in the census) and whose own window-scoped checks found
        # nothing to object to, which is the other half of how it got here --
        # `unplaced_window_problems` reaches these windows now, and one it
        # objects to was withheld above rather than counted here. The label is
        # the only thing that could say which arm the surviving one is: a
        # stray restore, or a control arm whose write never came, is real
        # arithmetic over rows the capture really recorded, with an arm this
        # run cannot name. That is the same reasoning `INTACT_BLOCK_NOTE`
        # states for the other direction -- a fact about what was captured, not
        # about what the EC did.
        #
        # The withheld branch's "a run it only read part of" is *not* reused,
        # because it would be inaccurate here: this run read every window it
        # was shown. The narrower gap is the count -- what an unattributed
        # window is a window of -- and the sentence says that one and declines
        # over the rest, the way the branch above declines over the withheld
        # windows. Placed before the `selected` case because a `--block` run
        # cannot reach either: `shown` is that block's own windows there, so
        # `graded_unplaced` is 0 by construction rather than by a guard.
        placed = graded - graded_unplaced
        print(f"  None of the §4.1-§4.3 bytes moved in any of the {placed} "
              f"window(s) that belong to a value under test: that is what "
              f"those {placed} windows show, and the {graded_unplaced} graded "
              "window(s) in no block above are not part of it. The static "
              "prediction is a claim about the whole capture, and this output "
              f"does not make it over a run in which {graded_unplaced} of its "
              f"{graded} graded window(s) are in no block. §7's "
              "`confirmed-inert` needs all three values, and a window in no "
              "block is one this run read and cannot say is a window of any "
              "of them -- so the paragraph below is as far as this run goes.")
    elif selected is not None and len(blocks) > 1:
        # A `--block` run over a day of more than one value graded every
        # window it was shown, so `graded == len(shown)`, `withheld == 0` and
        # neither branch above fires: it reached the whole-capture sentence
        # over one value of a day. §6's own command line passes `--block` and
        # §7 keys `confirmed-inert` on all three values, so the strongest
        # line an attachment printed once per value has to say which value it
        # is about. The run already knows -- the header counts the block, the
        # integrity check names the blocks it skipped, and `end` stopped at
        # the block rather than at the capture.
        #
        # `len(blocks) > 1` is the part that does not read as obvious. A
        # `--block` run over a *one*-block capture is not this case: there
        # the block is the whole capture, the windows it graded are the whole
        # mark stream, and the whole-capture comparison is exactly the claim
        # that run can support -- the integrity check even calls the skipped
        # set "the other 0 block(s)". Scoping it there would decline a
        # comparison that is true, which is a new overclaim in place of the
        # old one.
        print(f"  None of the §4.1-§4.3 bytes moved in any of the {graded} "
              f"window(s) in block {selected.index} of {len(blocks)}, value "
              f"under test {selected.name}: that is what those {graded} "
              f"windows show. The other {len(blocks) - 1} block(s) are not "
              "part of it. The static prediction is a claim about the whole "
              "capture, and this output does not make it over one block of "
              "them -- the same CSVs graded without --block is what would.")
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
        if not graded:
            # The pair *was* compared, so the count above it stands and the
            # sentence stays as it is; what is added is the scope the
            # withheld banner gives the windowed movement, applied to the
            # bracket. The line above is otherwise a counterweight to "no
            # window in this run was graded, so this output says nothing
            # about §4.1-§4.3 for it", and a bracket read for a block whose
            # windows were all refused is the one case where the two read as
            # if they contradicted each other. Scoped here for the same
            # reason the `moved_groups` companion is scoped there: a reader
            # who reads only this sentence is the case.
            #
            # Named from `verdicts` rather than from `selected`, because the
            # shape is not a `--block` one -- an unscoped run can withhold
            # every window too, and `verdicts` is over the same block set
            # the block section checked, so the names are only ever blocks
            # this run said something about.
            refused = [v for v, marker in verdicts.items() if marker]
            if refused:
                names = ", ".join(f"0x{v:02X}" for v in refused)
                print(f"  Those pairs are a read of two dump files, and not a "
                      f"statement about §4.1-§4.3 for block {names}, whose "
                      "windows this run refused to print above. The bracket "
                      "still stands as a reading of the files; what it is not "
                      "is evidence about a block the section above has "
                      "already given its verdict, and the reason is there.")
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
    print(wrap_note(ZERO_SCOPE_NOTE))
    # Seven ways a run can be refused rather than graded, and they are seven
    # facts about the input rather than seven verdicts about the machine: a
    # block short its restore, a mark set that cannot support a block's
    # windows, a window in no block whose marks the captures spell two ways or
    # that one of them did not record, a label the block walk could not place,
    # a value under test two blocks carry, a --block that named no block or
    # named two, and a capture named twice. The last three are not in this
    # expression at all -- all three are refused above, before the closing
    # section prints -- so the other four reach it, and they are not scoped
    # alike. `void` and `withheld` are this run's selected block:
    # `report_blocks` grades `selected` alone, and `withheld` is counted over
    # `shown`, which is that block's own windows, so a `--block` run says
    # nothing about the other blocks and passes if this one held. `repeated`
    # takes that same scope and is 0 on every run that reaches here with a
    # `--block`, because a repeated value is refused above -- the census line
    # is the whole-capture half of the same fact, printed whatever the run was
    # scoped to. The agreement refusal on a window in no block is counted into
    # `withheld`, so it takes that same scope: a window already in no block
    # cannot re-shape one, and no block's completeness rests on it. An early
    # exit lands the same way -- its block's windows are withheld, so it is
    # decided by the block it fell in, and a `--block` run over a value that
    # did not crash passes over a day in which another value did. The
    # unplaceable row is the one early-exit path with no such scope: like
    # `unreads`, it is refused above, for the whole run, because a row that
    # cannot be placed against a window leaves every block's length
    # uncertifiable. `unreads` is the whole capture's however the run was
    # scoped, per `unplaceable_marks`, and `UNREAD_MARK_NOTE` above is the
    # line that says so where the exit code is read from.
    #
    # `repeated` is the one of the four that needs no block to be short of
    # anything: a day whose two `0x00` blocks are both intact is graded over
    # in full and every check above passes it, so without this term it would
    # exit 0 over a day `3blocks/` holds at 1 for a different reason.
    #
    # `graded_unplaced` is the one shape in this section that is not a refusal
    # at all, and it is left out on purpose. Every term above counts something
    # this run declined to grade -- a window it would not print, or a value it
    # would not grade twice -- while `graded_unplaced` counts windows it read,
    # printed with their rows, and graded, over an arm the labels cannot name.
    # Folding it in would report a run that read and graded every window as one
    # that could not read them -- the one thing the closing section above is
    # careful not to say about itself. It is a disclosure rather than a
    # refusal, so the section says it in prose where §7's call is read from:
    # the `elif graded_unplaced:` branch declines the capture-level
    # comparison and stops at "as far as this run goes". A second
    # machine-readable channel for it would be one fact owned twice. And the
    # term is zero under `--block` by construction rather than by a guard --
    # `shown` is the selected block's own windows there, and a window in no
    # block is in none of them -- so it could only move the exit code of a
    # day-level run, and §6's documented command line passes `--block` per
    # value. That command line's day-level counterpart is #506.
    #
    # `unagreed`'s fold into `withheld` is a *refusal* counted under a term
    # already here, which is a different shape and is not the argument for this
    # one: a window that cannot be graded is not the case this is, and the two
    # have different `--block` semantics for the reason each of their own
    # comments give.
    return 1 if (void or unreads or withheld or repeated) else 0


def rows_from_bytes(raw, errors=None):
    """Every row of a capture's bytes, with the first field normalised.

    **The one place the row shape and the decode policy are stated** (#786),
    and the reason `read_capture` and the notice can be held to one message
    rather than to two that happen to agree. It takes bytes because every
    reader in this module now reads a capture exactly once and has them in
    hand: `read_capture`, which asks `starts_with_bom` of the same buffer
    before it decodes a byte of it; `capture_rows`, for the readers that are
    handed a path; and `capture_snapshot`, which is the notice's one read.
    One shape for all of them, so a `csv.reader` and a `normalised_rows`
    spelled once per reader is not a shape that can drift.

    A generator over a lazily-iterated `TextIOWrapper`, and the laziness is
    the point rather than a saving: `capture_lines` hands the lines over as
    they are decoded, so a byte outside `utf-8` comes out of the loop at the
    row it stopped on. `read_capture` can therefore raise a
    `UnicodeDecodeError` naming one row of a large capture instead of
    refusing the whole file for a byte near its end -- which is what
    `refused_capture_rows`' fix-one, re-run, meet-the-next contract rests on.
    Reading a file into bytes is not decoding it; the two are separate, and
    conflating them is the reading of the laziness
    `0751-file-refusal-order.md` rejected an option on, which
    `docs/findings/0751-strict-reader-two-moments.md` takes apart.

    `errors` is the caller's decode policy, passed straight through and
    unchanged from `capture_rows`: bare for the strict readers, so a byte
    outside the format raises, and `errors="replace"` for the preflights,
    which have to survive a file the grading will not. The strict reader and
    the notice answering the same exception out of the same call is what
    `MarkBeforeCodecTests` holds them to.

    At the end of the file rather than beside the readers that call it, for
    the reason `MarkBeforeCodecTests` is at the end of its suite: prose
    across `docs/findings/` pins lines of this file by number, and a block
    added mid-file moves every pin below it.
    """
    return normalised_rows(csv.reader(capture_lines(raw, errors=errors)))


if __name__ == "__main__":
    sys.exit(main())
