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
arm, carrying the stage boundaries §3's steps 2, 3 and 4 mark, and closed by
the step-5 restore -- and each block's last mark has to be that restore. A
block whose last mark is not the restore is void: the capture cannot show the
byte being put back, so its last window never closes. It is printed as void,
by name and with the label it did end on, and the exit code is not zero. Its
windows are withheld like any other block that fails a mark check: each prints
a `not graded` line naming the capture that ends the block where, and the
block's own line reads `-- NOT GRADED, its windows are not printed`.

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
per capture; marks within `MARK_MERGE_SECONDS` are one window, not several.

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
declines the capture-level comparison over the rest. A `--block` run makes the
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
        # The raw per-capture marks this window was merged from, and the
        # block it fell in. Both are set by `coalesce_marks` and
        # `assign_blocks` rather than at construction: a mark read out of a
        # CSV has no block until the whole mark stream has been walked, and
        # `coalesce_marks` is the only place that knows which raw rows one
        # action was recorded as.
        self.marks = []
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
    there is one answer to check. `capture_rows` normalises a leading U+FEFF
    off the first field of every row, because that is what the row's
    identity needs -- but a reader downstream of the stream therefore
    cannot see the mark, and the strict reader is the one that has to refuse
    the file over it. So it is asked of the bytes here, and of them twice
    rather than twice differently: `read_capture` hands it the three it
    read, and `capture_snapshot` hands it the buffer it had to read anyway
    because it reads a capture exactly once (#749)."""
    return raw[:len(BOM_BYTES)] == BOM_BYTES


def path_starts_with_bom(path):
    """`starts_with_bom` over the first bytes of `path`, and nothing more.

    An `open` of its own, and on purpose: the strict reader has to know
    before it reads a row, and a row cannot tell it. It reads three bytes
    and declares no `encoding=`, so it adds no site to the list the encoding
    page keeps. The notice does not come through here -- it reads the file
    once (#749) and answers the same question from the buffer it already
    had."""
    with open(path, "rb") as f:
        return starts_with_bom(f.read(len(BOM_BYTES)))


def bom_refusal(path):
    """The one sentence a capture carrying a byte-order mark is refused with.

    Returned rather than raised so both callers say the same words: the
    strict reader raises it, and `existing_mark_findings` reports the very
    same string as the file's refusal. That is the anti-drift contract the
    notice runs on -- the warning an operator reads and the error the
    grading raises are one verdict, not two that have to agree
    (`ExistingMarkLabelTests.test_a_leading_bom_is_refused_by_name_and_not_
    as_a_bad_hex_row` asserts the equality, so the two cannot drift)."""
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
    Applied to every row rather than to the first, for the reason
    `capture_rows` gives: the first three bytes of a file are the only place
    one occurs in practice, so the two readings agree on every file that
    exists, and a uniform rule is the one that can be written down once."""
    for row in rows:
        if row and row[0].startswith(BOM):
            row[0] = row[0].lstrip(BOM)
        yield row


def capture_rows(path, errors=None):
    """Every row of one capture CSV, with the first field normalised.

    The one place a capture is opened, so the shape of a row is stated once
    rather than four times: `read_capture`, `existing_mark_labels`,
    `refused_capture_rows` and `read_early_exits` all read from here.

    A stream and not a filtered iterator, because the four readers do not
    agree on which rows to drop: `skippable_row` is the filter three of them
    apply, and `read_early_exits` keeps exactly the rows the other three
    skip -- `EARLY_EXIT_TAG` opens with `#`, so a stream that filtered here
    would drop every early-exit row in the tree. A generator rather than a
    list so laziness still holds, which is what lets a byte the encoding
    cannot read come out of the loop at the row it stopped on instead of
    out of the open.

    The codec is declared, not inherited: `utf-8`, the encoding the format
    is defined in, whatever the interpreter reading the file would have
    preferred. That is what makes the same capture grade the same way on
    every box, and it is why the single-byte-locale cases this stream used
    to have an opinion about are gone rather than merely rare -- a cp1252
    capture's 0xE9 is now a byte the format does not contain, and whether
    this stream raises on it or replaces it is the caller's decision alone.

    `errors` is that decision, passed straight through, and the two in the
    tree are deliberate and have to stay different: the strict readers
    (`read_capture`, `read_early_exits`) pass none and let a byte outside
    the format raise, and the two preflights pass `errors="replace"` so a
    capture from before the codec was declared, or annotated in an editor
    that saved something else, comes back with U+FFFD in a label the
    operator is being shown anyway rather than taking down the run that was
    about to append to that same file.

    A leading U+FEFF is stripped from every row's first field by
    `normalised_rows`, and that is the row's *identity* rather than a repair:
    `EF BB BF` at offset 0 decodes under the declared `utf-8` to U+FEFF, which
    glues itself to the first field of the header and makes `row[0] == "ts"`
    false. Without the strip the header is a data row, `parse_ts` cannot read a
    `ts` that opens with U+FEFF, and the notice names the row carrying the
    column names as a row whose timestamp no reader can parse -- with a
    fix-or-delete-the-rows-above remedy, so the row it offers for deletion is
    the one holding the column names. It is also what lets `read_early_exits`
    see an early-exit row written on the first line, which the U+FEFF used to
    hide along with everything else on it. `capture_snapshot` puts the same
    rule over the one buffer the notice reads (#749), so a leading mark is
    never still on a first field anywhere in the tree.

    The strip is here rather than at the open as `encoding="utf-8-sig"`
    because the format declares utf-8 *with no BOM* and the strict reader
    refuses a file that carries one, by name (`read_capture`, through
    `path_starts_with_bom` -- the mark is gone from the rows by the time it
    gets there, and `bom_refusal` is the one sentence it says). Pinning the
    codec retired the "the encoding is not this tool's to decide" question this
    paragraph used to turn on; what is left of it is that the three preflights
    still have to read such a file far enough to say what it holds, and the
    shape is the one place that can say it. Applied to every row rather than
    to the first: the first three bytes of a file are the only place one
    occurs in practice, so the two readings agree on every file that exists,
    and a uniform rule is the one that can be written down once.

    What it does not cover, now for a different reason than it used to: a
    U+FEFF somewhere other than offset 0, which the strict reader
    normalises rather than refuses. The file-level refusal is about the
    first three bytes because that is the only place a byte-order mark
    occurs in a file this format defines, and the two readings agree on
    every such file. The same three bytes read as `ï»¿` under a single-byte
    locale, which no U+FEFF strip catches, is not reachable at all now that
    the codec is declared rather than inherited.
    """
    with open(path, newline="", encoding="utf-8", errors=errors) as f:
        yield from normalised_rows(csv.reader(f))



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
    come from `capture_rows`, the ones to drop from `skippable_row`, and what
    is left goes to `take_capture_row` -- this reader's one row, and the body
    the notice's strict pass runs over its own read (#749).

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
    before any row is read, with the remedy, the way the decode refusal
    below names the codec. `path_starts_with_bom` rather than a test on the
    row because `capture_rows` has already taken the mark off the first
    field by the time a row could be tested, and it is the file that carries
    it.

    Whether the format should ever *accept* a BOM is a separate question
    this does not decide. What is decided is that a capture carrying one is
    refused legibly under the encoding declared here, and that the preflights
    -- which still read the file to say what it holds -- see the header as
    the header rather than as a bad row.
    """
    if path_starts_with_bom(path):
        raise ValueError(bom_refusal(path))
    marks, changes = [], []
    for row in capture_rows(path):
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
    the open -- lenient, through `capture_rows` -- and a delegate, kept for
    a caller that holds a path rather than rows.
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
    timestamp. `refused_capture_rows` spells that order again to *name* the
    rows rather than stop at them, and
    `test_the_refusal_reasons_are_read_captures_own` holds the two together.

    The byte-order mark is *not* checked here, which is where #748 left it and
    where the row's own shape now disagrees. `capture_rows` takes a leading
    U+FEFF off the first field of every row, so a row reaching this no longer
    carries one and the test would be dead in both callers; the mark is refused
    where it can be seen at all -- of the file, in `read_capture` through
    `path_starts_with_bom` and in the notice through `capture_snapshot` -- with
    `bom_refusal`'s one sentence, so a file carrying one gets the refusal that
    names it on either path rather than a complaint about a hex literal from
    only one of them.
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


def partition_capture_rows(rows, path):
    """(accepted, refused) over already-read `rows`, by the rules
    `take_capture_row` applies, for the ones `read_capture` never got to.

    Takes rows rather than a path so `existing_mark_findings` can partition the
    rows of its single read beside the marks it placed from the same rows --
    the two lists the notice prints cannot then be describing two different
    files, because there is only one file in this function (#749). The rows are
    read through `capture_rows` by whoever opens the file, leniently, for the
    reason `refused_capture_rows` gives; the skip rule is that same stream's
    `skippable_row`, so the shape is not spelled here a second time.
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

    `open(path, "rb")` and one `read()`, so there is no second open to be a
    second moment. The decode is then the format's, in `capture_lines`: the
    same `utf-8` `read_capture` declares (#748), over the same bytes, so the
    refusal this returns is the refusal `read_capture` would have raised over
    them -- and it is raised before any row is looked at, which is what makes
    it a refusal of the file rather than of a row.

    On a file that decodes, `decode_failure` is None and `rows` is every row
    `csv.reader` reads. On one that does not, `decode_failure` is the
    `UnicodeDecodeError` the decode raised and `rows` is the *same bytes* read
    leniently -- for the listing only, since a strict verdict over a file this
    cannot decode is a refusal of the file, not a partial one.

    `rows` comes back normalised by `capture_rows`' own rule, because the
    notice reads one capture and must not be the one place in the tree where a
    leading U+FEFF is still glued to a first field. Which is why the mark is
    reported rather than left in the rows: `capture_rows` strips it, and it is
    the strip that makes a BOM'd header the header -- so a reader downstream
    cannot see the mark, and the caller's job is to be told there was one.
    Asked of the buffer rather than of a second `open` of `path`, because this
    function is the one read (#749) and a third one would be a third moment.
    """
    with open(path, "rb") as f:
        raw = f.read()
    has_bom = starts_with_bom(raw)
    try:
        return (list(normalised_rows(csv.reader(capture_lines(raw)))),
                None, has_bom)
    except UnicodeDecodeError as e:
        return (list(normalised_rows(
            csv.reader(capture_lines(raw, errors="replace")))), e, has_bom)


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
    """
    with io.TextIOWrapper(io.BytesIO(raw), newline="",
                          encoding="utf-8", **errors) as text:
        return text.readlines()


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

    A leading byte-order mark is the second refusal of the file rather than
    of a row, and it arrives the same way: `read_capture` raises before it
    reads anything, this function is told `has_bom` off the buffer it had to
    read anyway, and the partition has nothing to add, because the shape
    retires the mark off the first field first. The consequence for the
    notice is the point of it -- the reason names the mark and the remedy, and
    no row is attached for it to offer for deletion, so the operator is not
    pointed at the header, while every mark in the file is still listed.

    `build_windows` is deliberately not on the label path: it indexes
    `windows[0]`, so it needs a mark list and the change rows, and neither is
    what a label verdict is about. `coalesce_marks([])` and `assign_blocks([])`
    return empty without a guard, so an empty or mark-less file needs none
    here either -- and a file with no marks coming back empty is what keeps
    §3's block-1 start quiet.
    """
    accepted, refused, unplaceable = [], [], []
    rows, decode_failure, has_bom = capture_snapshot(path)
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
        refused.append((None, "the grader's reader cannot decode a byte of "
                              f"this file in the {decode_failure.encoding} a "
                              f"capture is defined to be, and raises before it "
                              f"reaches a row: {decode_failure}. A capture is "
                              f"utf-8; this one is written in something else. "
                              f"Re-save it as utf-8, or re-run the capture "
                              f"with a writer that declares the codec."))
        return mark_labels_of(rows), refused, unplaceable
    if has_bom:
        # The second refusal of the file rather than of a row, and asked of
        # the bytes this had to read anyway: `read_capture` refuses such a
        # capture before it reads a row, and this cannot call `read_capture`
        # because the whole of #749 is that it does not. So it is refused
        # here, off `capture_snapshot`'s own `has_bom`, with `bom_refusal` --
        # the one sentence, so the warning the operator reads and the error
        # the grading raises are the same words and the two cannot drift.
        #
        # The mark is off the first field by now, `capture_snapshot` having
        # applied the same rule `capture_rows` does, so the header is the
        # header and the marks below it are all still named: the reason and
        # the remedy come out, and the row carrying the column names is not
        # offered for deletion.
        refused.append((None, bom_refusal(path)))
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
    independent reasons. Its two-tuple is a contract with a second tool --
    `grade_gpu_door.py` imports this module and unpacks it at `:421` -- and its
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
    normalisation is what makes it so, not a caller. The only caller is
    `main`, which calls `read_capture` unguarded the line before, so a
    capture the strict reader refused whole raises out of `main`; a
    refused one is `existing_mark_findings`' to answer, via `bom_refusal`.
    """
    out = []
    for row in capture_rows(path):
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

    `labels` and `missing` come along, and `void` does not: the void check is
    a block's last recorded mark in a capture, and a window in no block has no
    block to have one in. That is a property of what the check is defined over
    rather than a limit found by looking and not finding a case, and it is
    said here rather than left for a reader to infer from the check's absence.

    The agreement checks engage at two or more captures, exactly as they do
    over a block: with one there is no other console for the mark to be
    missing from and no second spelling to disagree with it.

    A dict rather than a list because `main` prints each refusal in the window
    it belongs to and counts the window rather than the problem -- the shape
    `unplaceable_marks` returns, and the one the branch reading it expects.
    """
    names, _ = distinct_captures(path for path, _ in captures)
    known = set(names)
    out = {}
    for w in unplaced:
        problems = window_mark_problems(w, names, known)
        if problems:
            out[w] = [text for _, _, text in problems]
    return out


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
    """
    by_source = {}
    for m in w.marks:
        by_source.setdefault(m.source, []).append(m.label)
    spellings = {label for labels in by_source.values() for label in labels}
    problems = []
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
        want of a mark rather than because nothing moved.
      * an action the captures spelled differently. Same failure, found one
        step earlier: `coalesce_marks` joins the labels with ' / ', so the
        window opens on a label no console typed.
      * a block whose last recorded mark in some capture is not the restore.
        Per block *and* per capture, not the file's global last mark: a
        capture that recorded only one block would otherwise look complete
        for every block in the day.

    The first two are `window_mark_problems`, and the third is not: it is
    defined over a block, and the windows a block walk could not place are
    checked by `unplaced_window_problems` for the other two.

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

    A row that cannot be placed -- no readable timestamp, no window at or
    before it, or a window in no block -- is refused by the caller instead of
    filed anywhere. It is a run-level refusal on `unplaceable_marks`'s
    argument: block attribution rests entirely on the labels and where each
    row falls, so a row this cannot place leaves every block's completeness
    uncertifiable, and `--block` narrows what is graded rather than what is
    known.
    """
    placed, refused = [], []
    order = sorted(windows, key=lambda w: w.ts)
    for e in early_exits:
        if e.ts is None:
            refused.append((e, "the row carries no timestamp this can "
                               "read, so nothing in it says when the run "
                               "stopped"))
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
            # and the two send the operator to different terminals. The
            # heading is not "mark-set", because a block withheld for an early
            # exit is not short a mark -- it holds all of them.
            kinds = ", ".join(sorted({k for k, _, _ in b.problems}))
            line += f" -- NOT GRADED, {len(b.problems)} problem(s): {kinds}"
        print(line)
    if unplaced:
        for w in unplaced:
            role, _ = parse_mark(w.label)
            if role is not None:
                print(f"  unplaced: {w.ts.isoformat(sep=' ')}  {w.label!r} -- "
                      "in no block, so the void check cannot reach it -- there "
                      "is no block whose last mark in a capture it could be "
                      "-- and `--block` cannot select it either")


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


def block_verdict(block):
    """`intact` or `void`: whether the block's last mark is its restore.

    The one predicate §3's integrity check is, and it is here rather than
    inlined at `report_blocks` because the two dump sections need the same
    answer and a second copy of it is a thing that drifts. A block that is
    `void` is short the mark that says the byte was put back, so its windows
    are withheld; that is a statement about what the capture holds and
    nothing else.
    """
    last = block.windows[-1]
    return "intact" if parse_mark(last.label)[0] == "restore" else "void"


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
    to speak for. `VOID` here means the same thing `report_blocks` means by
    it: short a restore mark, not that anything did or did not happen.

    The early-exit branch is a third fact rather than a fourth wording of the
    first: a block that holds its restore and whose capture records the run
    ending early inside it is intact, and a marker saying its mark set does not
    hold would send the operator to a console that recorded all of them. It
    wins over the mark-set wording when a block has both, because the census
    above prints the kinds and this line is the one a reader takes to a
    terminal.
    """
    if not block.problems:
        return ""
    if block_verdict(block) == "void":
        return "VOID, its windows were withheld above"
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
        if block_verdict(block) == "intact":
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


def report_dumps(dumps, wrote, pairs, block_value=None, verdicts=None):
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
    dump still holds the written 0xA0" is true or false of two files on disk
    and is true here whatever the CSV mark set did, so the sentence is kept
    -- and the scoping line below says what it is a reading of. The dumps
    were still read; a block being `void` says the capture is short a mark,
    not that these bytes were never in evidence. The marker itself is
    already on the group line above and is not repeated here.
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


def report_dump_pairs(pairs, block_value=None, wrote=None, verdicts=None):
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
    exits = []
    for path in paths:
        m, c = read_capture(path)
        captures.append((path, m))
        marks += m
        changes += c
        read = f"{path}: {len(m)} mark(s), {len(c)} change row(s)"
        # Counted here rather than at the section below, because this line is
        # what a capture with no MARK rows is refused on -- and a capture with
        # no marks and an early-exit row in it is the one the refusal has to
        # be able to name.
        rows = read_early_exits(path)
        if rows:
            exits.append((path, rows))
            read += f", {len(rows)} early-exit row(s)"
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
    dumps = [(p, read_dump(p)) for p in args.dump]
    pairs = [(b, a, read_dump(b), read_dump(a))
             for b, a in args.dump_pair]
    report_dumps(dumps, wrote, pairs,
                 selected.value if selected is not None else None, verdicts)
    graded_pairs = report_dump_pairs(
        pairs, selected.value if selected is not None else None, wrote,
        verdicts)

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
            print(f"  That is the {graded} window(s) that were graded. The "
                  f"{withheld} window(s) withheld above are not part of it, "
                  "and what they would have shown is not reported here.")
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
    # Six ways a run can be refused rather than graded, and they are six
    # facts about the input rather than six verdicts about the machine: a
    # block short its restore, a mark set that cannot support a block's
    # windows, a window in no block whose marks the captures spell two ways or
    # that one of them did not record, a label the block walk could not place,
    # a --block that named no block, and a capture named twice. The last two
    # are not in this expression at all -- both are refused above, before the
    # closing section prints -- so the other four reach it, and they are not
    # scoped alike. `void` and `withheld` are this run's selected block:
    # `report_blocks` grades `selected` alone, and `withheld` is counted over
    # `shown`, which is that block's own windows, so a `--block` run says
    # nothing about the other blocks and passes if this one held. The
    # agreement refusal on a window in no block is counted into `withheld`, so
    # it takes that same scope: a window already in no block cannot re-shape
    # one, and no block's completeness rests on it. An early exit lands the
    # same way -- its block's windows are withheld, so it is decided by the
    # block it fell in, and a `--block` run over a value that did not crash
    # passes over a day in which another value did. The unplaceable row is the
    # one early-exit path with no such scope: like `unreads`, it is refused
    # above, for the whole run, because a row that cannot be placed against a
    # window leaves every block's length uncertifiable. `unreads` is the whole
    # capture's however the run was scoped, per `unplaceable_marks`, and
    # `UNREAD_MARK_NOTE` above is the line that says so where the exit code is
    # read from.
    return 1 if (void or unreads or withheld) else 0


if __name__ == "__main__":
    sys.exit(main())
