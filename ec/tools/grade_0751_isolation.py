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

Each context byte that moved in a window is also summarised as a
`window delta` -- first value, last value, net, and how many times it moved
inside the window. That is arithmetic on rows already in the capture, not a
new judgement: §4.4's deciding comparison is how far the duty bytes drifted
between one mark and the next, and reading that off the change rows means
doing the subtraction by eye across two terminal windows.

`--dump-pair` reads the same §4.1-§4.3 bytes a second, wider way, from a
before/after dump pair per range -- the range dumps §3's steps 0 and 6 take,
which bracket the whole block where each CSV window brackets one arm of it.
That bracket is complementary to the windowed one, not a stronger form of
it: a byte that moved at any point in the block and is back where it
started by the after-dump reads unchanged here, and a byte that moves
entirely between two of `ec_watch.py`'s sweeps is in no change row at all.
Each read has a gap the other does not close. An address one dump covers and
the other does not is a coverage gap, never a change.

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

Nothing here touches hardware; it reads files only.

Usage:
    python3 ec/tools/grade_0751_isolation.py capture-0700-07ff.csv \
        [capture-0f00-0f5f.csv] [capture-0400-045f.csv] \
        [--dump before-0700.txt] [--dump after-0700.txt]
    python3 ec/tools/grade_0751_isolation.py capture.csv --wrote 0xA0
    python3 ec/tools/grade_0751_isolation.py capture.csv \
        --dump-pair before-0700.txt after-0700.txt \
        --dump-pair before-0f00.txt after-0f00.txt
"""
import argparse
import csv
import datetime
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

# The bytes §4.4/§4.5 name but this script does not grade. They get their own
# section because they are what §7's call is made on, and a reader should not
# have to find them in the generic "other addresses" list to notice them --
# but they are printed per window precisely so the no-op control arm and the
# write under test can be compared by eye, change row by change row and then
# as the net the rows add up to. The duty pair is identified -- issue #123
# gave them the vendor's ADDR_EC_MAIN_FAN_L/R_DUTY_BYTE names and entries in
# registers.yaml -- and it stays out of WATCHED anyway, because a duty byte
# drifts on a warming die whether or not anything wrote 0x0751: grading it
# would report "moved" on every window, the no-op control arm included, and
# leave nothing to compare. The two temperatures are confirmed-working, and
# are here as the record of whether the load was flat.
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


def coalesce_marks(marks):
    """One window per action, however many consoles recorded it.

    The procedure runs one `--mark --csv` watcher per console, so a single
    action lands as several MARK rows seconds apart. Left alone, the changes
    that follow would be assigned to whichever of them happened to be last and
    the other two would report "nothing moved" for a write that did move
    things. A group starts at its *earliest* mark -- the window has to open
    before the first press, or the reaction is attributed to the wrong action
    -- and carries every label and source in it.
    """
    groups = []
    for m in sorted(marks, key=lambda w: w.ts):
        close = groups and (m.ts - groups[-1][-1].ts).total_seconds() \
            <= MARK_MERGE_SECONDS
        if close:
            groups[-1].append(m)
        else:
            groups.append([m])
    return [Window(g[0].ts,
                   " / ".join(dict.fromkeys(m.label for m in g)),
                   ", ".join(dict.fromkeys(m.source for m in g)))
            for g in groups]


def build_windows(marks, changes):
    """Assign every change to the last mark at or before it.

    Changes before the first mark belong to no window: the procedure has the
    operator let the sweep settle for ~10 s before marking, so they are the
    settling noise, not a reaction to anything.
    """
    windows = coalesce_marks(marks)
    for c in sorted(changes, key=lambda c: c.ts):
        prior = [w for w in windows if w.ts <= c.ts]
        if prior:
            prior[-1].changes.append(c)
    return windows


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


def report_window(w, n, total):
    end = "the next mark" if n < total else "the end of the capture"
    print(f"\n--- mark {n}/{total}: {w.ts.isoformat()}  {w.label!r} "
          f"({w.source})")
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

    groups = [(name, [c for c in w.changes if c.addr in addrs])
              for name, addrs in CONTEXT]
    groups = [(name, hits) for name, hits in groups if hits]
    if groups:
        print("    fan duty / temperature bytes (§4.4/§4.5) -- context, "
              "not graded here:")
        print("    net is the raw byte difference across the whole window, "
              "not a duty percentage:")
        for name, hits in groups:
            print(f"      {name}:")
            for a in sorted({c.addr for c in hits}):
                seq = [c for c in hits if c.addr == a]
                print(f"        window delta  0x{a:04X}  "
                      f"0x{seq[0].old:02X} -> 0x{seq[-1].new:02X}  "
                      f"net {seq[-1].new - seq[0].old:+d}  "
                      f"({len(seq)} change{'' if len(seq) == 1 else 's'})")
            for c in hits:
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


def report_dumps(dumps, wrote):
    print("\n=== 0x0751 across the dumps (§4.6) ===")
    if not dumps:
        print("  no dump given (--dump); §4.6 not checked")
        return
    for path, values in dumps:
        v = values.get(MANUAL_FAN_CTRL)
        if v is None:
            print(f"  {path}: 0x{MANUAL_FAN_CTRL:04X} not covered by this dump")
        else:
            print(f"  {path}: 0x{MANUAL_FAN_CTRL:04X} = 0x{v:02X}")
    if wrote is None:
        return
    last = dumps[-1][1].get(MANUAL_FAN_CTRL)
    if last is None:
        return
    if last == wrote:
        print(f"  the last dump still holds the written 0x{wrote:02X}. Per "
              "CLAUDE.md that is a readback, not evidence the EC acted on it.")
    else:
        print(f"  the last dump holds 0x{last:02X}, not the written "
              f"0x{wrote:02X} -- something put it back; §3a's service-stopped "
              "run is what separates the vendor service from the EC.")


def report_dump_pairs(pairs):
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
    """
    print("\n=== whole-block dump pairs (§4.1-§4.3) ===")
    if not pairs:
        print("  no dump pair given (--dump-pair); the whole-block read is not "
              "checked")
        return
    for before_path, after_path, before, after in pairs:
        common = sorted(set(before) & set(after))
        moved = [a for a in common if before[a] != after[a]]
        print(f"\n  {before_path} -> {after_path}, {len(common)} address(es) "
              "compared")

        only_before = sorted(set(before) - set(after))
        only_after = sorted(set(after) - set(before))
        if only_before or only_after:
            print("    coverage gap, not a change: whatever moved in the part "
                  "one of these does not cover is outside this read.")
            print("      before dump only: "
                  + (" ".join(f"0x{a:04X}" for a in only_before) or "none"))
            print("      after dump only:  "
                  + (" ".join(f"0x{a:04X}" for a in only_after) or "none"))

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
        # different answer from "read and did not move", and the temperatures
        # are in neither the 0x0700 nor the 0x0F00 dump, so the two bytes
        # §4.5's comparison rests on would otherwise vanish under a heading
        # that promises them. A reached group that did not move stays silent,
        # as it does per window.
        groups = []
        for name, addrs in CONTEXT:
            if not any(a in addrs for a in common):
                groups.append((name, None))
            else:
                groups.append((name, [a for a in moved if a in addrs]))
        groups = [(name, hits) for name, hits in groups
                  if hits is None or hits]
        if groups:
            print("    fan duty / temperature bytes (§4.4/§4.5) -- "
                  "context, not graded here:")
            for name, hits in groups:
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
            print(f"    other addresses that differ ({len(others)}), not "
                  "graded here -- read them against §4.4 and §4.5 by hand:")
            print("      " + " ".join(f"0x{a:04X}" for a in others))

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


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+",
                    help="ec_watch.py --mark --csv capture(s)")
    ap.add_argument("--dump", action="append", default=[], metavar="FILE",
                    help="ecrw.py dump output; repeat for before- and after-")
    ap.add_argument("--dump-pair", action="append", nargs=2, default=[],
                    metavar=("BEFORE", "AFTER"),
                    help="one range's ecrw.py dump before/after pair, as §3's "
                         "steps 0 and 6 take it; repeat per range. Read for "
                         "the whole-block report and independent of --dump, "
                         "whose §4.6 readback still comes from the last one")
    ap.add_argument("--wrote", help="the value written to 0x0751 (e.g. 0xA0)")
    args = ap.parse_args(argv)

    wrote = int(args.wrote, 0) if args.wrote else None

    marks, changes = [], []
    for path in args.csv:
        m, c = read_capture(path)
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
    print(f"\n=== {len(windows)} window(s), one per mark ===")
    # The union over the windows, in WATCHED order: which watched groups saw a
    # change row at all. The closing paragraph has to name them, because a
    # mailbox poke and a fan-table move are different answers and "at least
    # one of §4.1-§4.3 moved" reads the same for both.
    moved_groups = []
    for i, w in enumerate(windows, 1):
        for name in report_window(w, i, len(windows)):
            if name not in moved_groups:
                moved_groups.append(name)

    dumps = [(p, read_dump(p)) for p in args.dump]
    report_dumps(dumps, wrote)

    # After the §4.6 readback, so the section order stays the one §6
    # documents: the per-window read, then 0x0751 across the dumps, then the
    # whole-block bracket on the same §4.1-§4.3 bytes.
    pairs = [(b, a, read_dump(b), read_dump(a))
             for b, a in args.dump_pair]
    report_dump_pairs(pairs)

    print("\n=== what this does and does not settle ===")
    if moved_groups:
        print(f"  At least one of the §4.1-§4.3 bytes moved after a mark: "
              f"{', '.join(moved_groups)}.")
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
    else:
        print("  None of the §4.1-§4.3 bytes moved in any window: consistent "
              "with the static prediction, for this capture's window only "
              "(§5: a byte that does not move inside the window may still "
              "move at the next suspend, AC transition or EC reset).")
    if pairs:
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
