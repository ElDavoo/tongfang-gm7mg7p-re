#!/usr/bin/env python3
r"""Issue #99: write only the power-mode byte 0x0751 and watch whether the EC
moves anything else on its own.

The vendor service writes a whole bundle per power mode (0x0751, PL1/PL2/PL4,
the fan table, GPU bytes; see windows/vendor-ec-map.md "Power modes"). This
isolates the mode byte: it reads a fixed watch-set plus the fan table
(0x0F00-0x0F5F) and the temperature range (0x0400-0x045F) every 0.5 s, holds a
no-op control arm, writes 0x0751 to one target value, holds, then restores the
original. If the EC derived the PLs or the fan table from the mode byte, they
would move here with nothing else writing them.

The defaults are the procedure's, not this tool's: 30 s per arm and a 0.5 s
cadence are what §3 of docs/hardware-tests/manual-fan-ctrl-0751-isolation.md
asks for, and that file is the reference whenever the two disagree. What the
single-tool form does *not* do is §3b of that file: the service-stopped second
pass, the by-hand package-power notes, and the other seven of §6's ten files --
the six range dumps and the snapshot, none of which this tool writes. With
`--csv` it does produce what §6's three CSVs hold, in one appended file rather
than three, and the grader reads that with no conversion -- but not at equal
coverage: FANTBL and TEMP sweep their ranges whole, while WATCH reads 14
addresses of the 0x0700-0x07FF page where §3's `ec_watch.py --start 0x0700
--len 0x0100` takes all 256, so §4.4's whole-page instruction is not
reproduced. This tool produces no range dump.

Two arms, because 0x075B/0x075C (the fan duty bytes -- the vendor's
ADDR_EC_MAIN_FAN_L/R_DUTY_BYTE, issue #123) move with the die
whether or not anything wrote 0x0751. The control arm writes 0x0751 back the
value it already holds and holds for the same time, so its duty movement is the
baseline the write under test has to beat -- what
docs/hardware-tests/manual-fan-ctrl-0751-isolation.md §4.4 asks a human to
compare. The tool prints both arms' numbers and does not grade them: telling
duty drift from thermal drift is the reader's call (§4.4).

The two arms are labelled `no-op wrote 0x0751=0xNN` and `wrote 0x0751=0xNN` --
the labels §3 requires and ec/tools/grade_0751_isolation.py windows on. A
control arm that reads like the write under test is indistinguishable from it.
The restore in the `finally` is a third mark, `restored 0x0751=0xNN` (§3's
step 5), and it is the one the grader's block walk closes a block on: a
capture whose last mark is not a restore comes back `VOID` with its windows
withheld, so a run that wrote the byte back and never recorded it reads as a
run that never put it back.

0x0400-0x045F is the EC's own temperature reading (0x043E CPU_TEMP, 0x044F
GPU_TEMP), so the duty reading is taken against a measured die rather than an
assumed one. It stops at 0x045F because the fan-tach bytes (0x0460-0x046F) start
right after, and reading those through ECRR stalled the fans on a sibling board
(#94, docs/related-projects.md).

The other rows this range prints are not all sensors: 0x0434/0x0435 is battery
current in mA, 0x0438/0x0439 is terminal voltage in mV, and 0x0448/0x0449 are
those two divided by 100. ec/annotations/xdata-0400-045f.md maps all 96 bytes --
46 of them with a registers.yaml entry, which is 44 entered by the sweep plus
the two that were already there (0x043E, 0x044F) and is carried as 41 entries
because five are entered as 16-bit pairs, the other 50 named there as
deliberately not entered -- so a row that moves here is either nameable or
accounted for. Treat the electrical ones as context: they move with the pack,
not with 0x0751.

**That wider watch set is 206 ECRR reads per sweep, up from 110 -- an 87%
increase, and `ecrw.Ec.read` (ecrw.py:135) is one ECRR DeviceIoControl per byte
with nothing between calls.** This run is the one
`manual-fan-ctrl-0751-isolation.md` §3 holds under a fixed load, and a block
that moves the fans itself is worth less than no block. There is no safe
interval derivable without the driver and the machine (#94 is the open work), so
`--interval`'s 0.5 s default is §3's starting point and nothing more: if the
fans audibly change during a run, stop and raise it.

`--block` sweeps the same 206 addresses in **56** IOCTLs instead, through the
driver's `MMRD` -- `ecrw.Ec.readmany`, four bytes per call. 56 is 8 + 24 + 24:
the 14 `WATCH` addresses land on 8 blocks, the fan table is 24, the
temperature range is 24. It is **not** the 52 that `206/4` suggests, because
the watch set is not contiguous; and 56 calls still read 224 bytes, so the
saving is in calls and not in traffic. **The flag is off by default and
nothing in this repository has run it.** What is committed is that the handler
marshals four bytes and copies four back
(`../native/ACPIDriver.sys.analysis.md` walks it, `0x1400015EC`); whether the
BIOS hands back what four single reads would have is a live question. #94 is
untouched by any of this: it is what makes the *per-byte* path safe, by
skipping the fan-tach bytes and pacing, and a block read is neither of those.

**What a human can check, and what it would not settle.** At idle -- not under
a load, not during a probe run, since a read that moves the fans is the
failure being looked for:

    ecrw.py read 0x0750 0x0751 0x0752 0x0753     # four ECRR reads
    ecrw.py dump 0x0750 0x04 --block             # one MMRD at 0xFE410750
    ecrw.py read 0x0751 0x0752 0x0753 0x0754     # the same four, one byte on
    ecrw.py dump 0x0750 0x08 --block             # 0x0750-0x0757, two MMRDs

Compare each `dump --block` line against the `read` above it, byte for byte at
the four addresses it names. Issue #147 words the check as one `MMRD` at
`0xFE410000 + 0x0751`, which is **unaligned** -- `0x0751 % 4 == 1` -- and this
tool cannot ask that question: `read_dword` refuses an unaligned start and
`readmany` covers the enclosing block instead, so the block path only ever
issues the aligned shape. The aligned rows are therefore the ones that bear on
`--block`. Issuing an unaligned `MMRD` would take a `--mmrd` escape in
`ecrw.py` that this tool does not have, and an aligned pass beside an
unaligned fail would be a real result about the access width rather than
about the flag. Even four matching readbacks at one address would not be proof
that a wider read is safe across the window: per CLAUDE.md a readback that
matches is not evidence the EC acts on the access the way it acts on the byte
one, and #94 is still the open question of what this traffic does to a fan.

`--level-block` adds 16 more -- `0x0860`-`0x086E` and `0x06E6`, 222 reads per
sweep -- and is opt-in for exactly that reason: the #99/#122 run's footprint and
its documented 206 stay as committed rather than growing under a flag nobody
reading that run knows about. **Nothing in the level block is written.** The
only byte this tool writes is `0x0751`, in `{0x00, 0x10, 0xA0}`; the
`0x086x` path is read-only, and a read-only watch set is the whole reason the
capture is safe to leave running.

With `--level-block` the summary also reports the two readings
docs/hardware-tests/level-block-0860-086e.md §4 asks for off one capture: the
values `0x0860` was seen at (its `0xFF` is the EC's own busy mark,
ec/annotations/xdata-086x-dispatch.md §4), and the values the three result
bytes `0x086B`/`0x086C`/`0x086E` were seen at, against the three clamp
constants `0x23`/`0x14`/`0x0F` of xdata-086x-dispatch.md §5. Both are
reported, neither is graded: whether the results track fan speed is a human's
reading of a capture on the machine, and `0x086E` carries no clamps at all, so
a `0x23` there means nothing of the kind one on `0x086B` means.

`--csv` writes what `ec_watch.py --mark --csv` writes -- `ts,addr,old,new`, with
this run's three marks as the `MARK` rows -- so the capture is read by
`ec/tools/grade_0751_isolation.py` with no conversion (issue #124). The marks
are free here: this tool performs both writes and the restore itself and so
already knows when each landed, which is the one thing `ec_watch.py` needs a
stdin thread for. The restore's mark is the one that closes the block: the
grader's block walk refuses a capture whose last mark is not a restore, so
without it both arms of a perfectly good run come back ungraded, and what they
would have shown is not reported. The file is appended, so a second mode's run
extends the capture rather than replacing it, and the marks say which arm each
row belongs to. A run that dies part way through records why in a `#` row,
which the reader skips by design: the restore and its mark still land, so the
block would otherwise read `intact` over a window that was cut short. One
`MARK` row is one action only while the marks are more than the grader's
`MARK_MERGE_SECONDS` (5 s) apart, and a `--csv` run at or under that window is
refused before the EC is opened rather than left to write a capture no block
can be read out of: the grader's `coalesce_marks` closes a group at exactly the
window, so the three marks would fold into one. §3's ~30 s hold and this
tool's default both clear the floor, and a hold above it is the operator's
decision again -- the re-snapshot between two arms adds to the gap by a cost
nothing here has measured, so the floor is the conservative side.

Values under test are limited to the three the vendor itself writes: 0xA0
Office, 0x00 Gaming, 0x10 Turbo (a no-op if that is already the mode). The
control arm's write is deliberately not gated on that set -- it re-writes the
value the EC already holds, so it introduces nothing the machine has not seen,
and gating it would make the tool refuse to run in a mode the vendor UI has
set. Restores 0x0751 in a finally block, which wraps both arms.

`--self-test` opens no EC. It checks the watch set's read-safety guard and the
floor a `--csv` run's hold is held to, and hands a synthesised three-mark block
to the real `ec/tools/grade_0751_isolation.py` -- its reader, and then the
block walk and `check_block_marks` that issue #457 made load-bearing, with the
two-mark capture this tool used to write kept as the negative control -- so a
mark set the grader refuses is a failing row here rather than a green
self-test. It is the tool's own logic on a fixture, in the sense
windows/tools/ecrw_fake.py gives that phrase.

Run elevated, next to ecrw.py. Needs the vendor's ACPI driver present.

Usage:
  manual_fan_ctrl_probe.py 0xA0 [hold_seconds] [--interval 0.5]
                           [--csv PATH] [--level-block] [--block]
  manual_fan_ctrl_probe.py 0xA0 --self-test        # no EC, no driver
"""
import argparse
import csv
import datetime
import importlib.util
from pathlib import Path
import sys
import tempfile
import time

from ecrw import Ec, block_runs

MODE = 0x0751
WATCH = [0x0751, 0x0783, 0x0784, 0x0785, 0x0786, 0x0787,
         0x07C5, 0x07C6, 0x075B, 0x075C, 0x0743, 0x0744, 0x0745, 0x0746]
FANTBL = list(range(0x0F00, 0x0F60))
# Exclusive of 0x0460: the fan-tach bytes are the next page (issue #94).
TEMP = list(range(0x0400, 0x0460))
# The block --level-block adds: 0x0860-0x086E and the 0x06E6 gate byte that
# gate_06e6_442_then_sync_046a_from_086b tests (xdata-086x-dispatch.md §7).
# 0x0440 and 0x0442 are already in TEMP, so that file's clamp guards (§5) and
# its gates (§7) are in the same capture without a new byte for them.
LEVEL = list(range(0x0860, 0x086F)) + [0x06E6]
ALL = WATCH + FANTBL + TEMP
ALLOWED = {0x00, 0x10, 0xA0}
DUTY = (0x075B, 0x075C)
TEMPS = (0x043E, 0x044F)

# The four bytes --level-block's own readings are taken from. 0x0860 is the
# dispatch selector and the busy mark; the other three are the results
# compute_level_blocks_086b_086c_086e computes (xdata-086x-dispatch.md §5).
BUSY = 0x0860
BUSY_VALUE = 0xFF
RESULT_BYTES = (0x086B, 0x086C, 0x086E)
# Which of the three carry §5's clamps. Split by name rather than by slicing
# RESULT_BYTES, because the whole point of the split is that it is not
# symmetric and a `[0:2]` at the use site would read as a shape rather than a
# fact.
CLAMPED_RESULTS = (0x086B, 0x086C)
UNCLAMPED_RESULTS = (0x086E,)
LEVEL_BYTES = (BUSY,) + RESULT_BYTES
# The three constants those first two are clamped at, and which the third is
# not: 0x086E has no cap at all, so a result byte sitting at one of these is a
# direct read of a live guard on 0x086B/0x086C and nothing of the kind on
# 0x086E. §5 of xdata-086x-dispatch.md is the source of the three.
CLAMPS = (0x23, 0x14, 0x0F)
# The fan-tach page, named as a range so the self-test and the offline suite
# can assert the read path stays off it without each spelling the endpoints out
# again. TEMP stops before it; this is the thing it stops before.
FAN_TACH = list(range(0x0460, 0x0470))

# How close two marks have to be to count as one action, restated from
# ec/tools/grade_0751_isolation.py:260 rather than imported: this file runs
# next to ecrw.py on a Windows box, so main() must not depend on the
# repository layout to know a number (the self-test reaches the grader by
# path, and that is the one place that may). Pinned against the grader's own
# constant by windows/tools/test_manual_fan_ctrl_probe.py, so a window that
# moves there fails this tool's suite and names itself. The window is the
# grader's and stays there; 5 s is right for its three-console procedure.
MARK_MERGE_SECONDS = 5


def watch_set(level_block=False):
    """The addresses one sweep reads, in the order it reads them."""
    return ALL + LEVEL if level_block else ALL


def block_ioctls(addrs):
    """The IOCTLs one `--block` sweep of `addrs` costs, four bytes each.

    56 for the default watch set against 206 per-byte reads, and not the 52
    that `206/4` suggests: the 14 `WATCH` addresses are scattered over
    `0x0743`-`0x07C6` and fall on 8 blocks, not on 14/4 of one. Pinned in
    `test_ecrw.py` against the real `ecrw.block_runs` and the real watch set.
    """
    return sum(((start + length - 1) & ~3) // 4 - (start & ~3) // 4 + 1
               for start, length in block_runs(addrs))


def block_span(addrs):
    """The EC bytes a `--block` sweep of `addrs` reads, padding included.

    Wider than `addrs` wherever a run's ends are unaligned -- which is what
    #94's page is about, since a block that covered `0x0460`-`0x046F` would be
    a four-byte access to the page that stalled the fans on a sibling board,
    not a narrower one.
    """
    return {a for start, length in block_runs(addrs)
            for a in range(start & ~3, ((start + length - 1) & ~3) + 4)}


def marks_clear(hold):
    """Whether `hold` keeps this run's three marks clear of each other.

    The floor is the grader's `MARK_MERGE_SECONDS` and the test is `<=`, not
    `<`: `coalesce_marks` closes a group at exactly the window, so a hold *at*
    it folds the marks as surely as one under it. One place for the rule
    because the guard, the self-test and the suite all have to read it the
    same way, and a rule restated three times is a rule that drifts.

    `hold` is judged alone, which is the conservative side: the real gap
    between two marks is `hold` plus the re-snapshot between the arms, whose
    cost nothing here has measured. A hold above the floor is therefore the
    operator's decision again, not a claim that the capture is safe.
    """
    return hold > MARK_MERGE_SECONDS


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


# The self-test's mark timeline. The grader's `coalesce_marks` folds marks
# within `MARK_MERGE_SECONDS` (5) of each other into one window, so a self-test
# that stamped its marks on the wall clock would hand the block walk a single
# window with a joined label and no block at all -- a check that could not tell
# a good mark set from a coalesced one. A hold apart is what the suite's own
# `Clock` puts between two arms, and the stamps are the shape `now` produces,
# so `parse_ts` reads them exactly as it reads a capture's.
SELFTEST_EPOCH = 1700000000.0
SELFTEST_HOLD = 30.0


def mark_ts(seconds):
    """A `now()`-shaped stamp `seconds` after `SELFTEST_EPOCH`."""
    return (datetime.datetime.fromtimestamp(SELFTEST_EPOCH + seconds)
            .astimezone().isoformat(timespec="milliseconds"))


def arm_labels(orig, target):
    """The three `MARK` labels one run writes, in the order it writes them.

    §3's three action forms with this run's values in them: the control arm
    writes the byte back the value it already holds, the write arm writes the
    value under test, and the restore puts `orig` back again. One function
    rather than the f-strings that were at each label site, because the
    `--self-test` and the offline suite have to exercise the labels *this tool*
    writes -- a second spelling of them is a spelling that agrees today and
    drifts tomorrow, and a drifted label is a capture the grader's `parse_mark`
    cannot place, which is a whole run refused rather than one mark.

    The restore carries `orig` and not `target`: the label names the value
    being put back, which is the same value the no-op arm wrote and the one
    the block is closed against.
    """
    return (f"no-op wrote 0x{MODE:04X}=0x{orig:02X}",
            f"wrote 0x{MODE:04X}=0x{target:02X}",
            f"restored 0x{MODE:04X}=0x{orig:02X}")


class MarkCsv:
    """Append-only capture in `ec_watch.py --mark --csv`'s row shape.

    `ts,addr,old,new` with the arm boundaries as `ts,MARK,,label`, which is
    what `ec/tools/grade_0751_isolation.py` already reads -- the format is not
    this file's to define, and a capture here that grader cannot open would be
    a third shape rather than a cheaper one. `ec_validate.py`'s `SampleCsv` is
    the same shape minus the lock; this run is one thread too, and there is
    nothing here to interleave with.

    Append is the part that carries: §4 of
    docs/hardware-tests/level-block-0860-086e.md wants the same session for
    three modes, so the second run has to extend the capture rather than
    replace it, with the marks saying which arm each row followed. What a run
    appends is a *complete* block -- control, write, restore -- so the second
    run extends a finished block rather than an open one, and the grader's
    block walk reads each of them separately. The header goes to a new file
    only, and `read_capture` skips it either way.
    """

    def __init__(self, path):
        self._fh = open(path, "a", newline="")
        self._writer = csv.writer(self._fh)
        if self._fh.tell() == 0:
            self.row(["ts", "addr", "old", "new"])

    def row(self, values):
        self._writer.writerow(values)
        self._fh.flush()

    def mark(self, label, ts=None):
        # `ts` is the self-test's, and only the self-test's: a real run wants
        # the wall clock, and the marks it stamps have to be as far apart as
        # the arms they bracket -- which is what the real clock says and what
        # a self-test running in milliseconds does not.
        self.row([now() if ts is None else ts, "MARK", "", label])

    def close(self):
        self._fh.close()


def snap(ec, addrs=ALL, block=False):
    if not block:
        return {a: ec.read(a) for a in addrs}
    out = {}
    for start, length in block_runs(addrs):
        out.update(ec.readmany(start, length))
    # Keyed by `addrs`, not by what the blocks covered: a run whose ends are
    # unaligned is read past on both sides, and diff() and the level-block
    # report walk the keys they are handed -- a snapshot with padding in it
    # would report movement in bytes this run never asked for.
    return {a: out[a] for a in addrs}


def diff(base, cur):
    # Over `base`'s keys rather than a module-level set: the two snapshots came
    # from the same `snap`, and --level-block makes "the watch set" a runtime
    # choice rather than a constant, so a hardcoded range here would silently
    # grade the widened sweeps against the default set.
    return [(a, base[a], cur[a]) for a in base if base[a] != cur[a]]


def hold_and_observe(ec, hold, interval, base, label,
                     addrs=ALL, sink=None, observed=None, block=False):
    """Sweep for `hold` seconds; return what moved, as addr -> (first, last, n).

    `first` is the value at the arm's opening snapshot, not the value before
    the last change, so the number is the arm's net -- the same
    first/last/count arithmetic the grader prints as a `window delta`, where
    it is one of three movement figures. A drifting byte reports its net, not
    the last step. §4.4 keys the control-vs-write comparison on *total*
    movement, which this tool does not print: its per-arm change rows are
    printed as they happen, so a reader can sum them, but nothing here does
    the summing. A §3 three-capture run gets the figure printed for it by
    `ec/tools/grade_0751_isolation.py`.

    `base` is the caller's, not a fresh one: the write arm's baseline has to
    be the state the control arm settled into, or the control's own motion
    would be attributed to the write. `interval` is the operator's, because
    §3's cadence is a starting point and not a value this tool can pick safely
    (#94). `label` names the arm in the change rows so a read-through knows
    which window a line belongs to. One code path for both arms is deliberate
    -- anything that consumes these rows, a CSV sink among them (issue #124),
    attaches to one place rather than to two loops.

    `sink`, if given, gets every change row this loop would have printed.
    `observed`, if given, is the caller's {addr: {values}} accumulating set for
    the level-block bytes: it answers a different question from a change row,
    because a value held for a whole arm produces none at all and would be in
    neither `moved` nor a capture. `block` is the operator's --block, passed to
    `snap` and to nothing else: the two paths read differently and compare
    identically.
    """
    moved = {}
    if observed is not None:
        for a in observed:
            observed[a].add(base[a])
    t0 = time.time()
    while time.time() - t0 < hold:
        cur = snap(ec, addrs, block)
        for a, o, n in diff(base, cur):
            print(f"    +{time.time()-t0:4.1f}s  [{label}] 0x{a:04X}: "
                  f"0x{o:02X} -> 0x{n:02X}")
            if sink:
                sink.row([now(), f"0x{a:04X}", f"0x{o:02X}", f"0x{n:02X}"])
            if observed is not None and a in observed:
                observed[a].add(n)
            prior = moved.get(a)
            moved[a] = (prior[0], n, prior[2] + 1) if prior else (o, n, 1)
        if observed is not None:
            for a in observed:
                observed[a].add(cur[a])
        base = cur
        time.sleep(interval)
    return moved


def fmt(motion):
    return "no change" if motion is None \
        else f"0x{motion[0]:02X} -> 0x{motion[1]:02X} ({motion[2]} changes)"


def report_level_block(arms):
    """The two readings §4 of docs/hardware-tests/level-block-0860-086e.md
    takes off one capture, per arm. Reported, not graded.

    `arms` is [(label, {addr: {values the arm saw}})]. The values rather than
    the motion, because §4 asks what the bytes *sat at*: a result byte that
    holds one value for a whole arm produces no change row and would read as
    absent from a report built on the change rows alone, which is the opposite
    of what a level block does most of the time.

    Two lines have to stay apart, because xdata-086x-dispatch.md §5 gives
    `0x086B` and `0x086C` the three clamps and `0x086E` none. A result sitting
    at `0x23`/`0x14`/`0x0F` is a direct read of the guard on the first two and
    means nothing of the kind on the third, so the third line says so rather
    than repeating the first two's wording and letting a reader supply the
    exception.

    The closing line is the gap this read has that a capture does not: a busy
    mark that comes and goes between two sweeps leaves no row, because the
    capture records transitions and not values, and the interval is the only
    lever. Per CLAUDE.md, "not seen" is "not found by this method".
    """
    print("\nlevel block (--level-block) -- reported, not graded")
    for label, values in arms:
        print(f"  {label}")
        for a in LEVEL_BYTES:
            seen = " ".join(f"0x{v:02X}" for v in sorted(values[a]))
            if a == BUSY:
                note = "busy mark 0xFF: SEEN" if BUSY_VALUE in values[a] \
                    else "busy mark 0xFF: not seen"
            elif a in CLAMPED_RESULTS:
                hit = [c for c in CLAMPS if c in values[a]]
                note = "clamp value(s) " + " ".join(f"0x{c:02X}" for c in hit) \
                    if hit else "clamp values 0x23/0x14/0x0F: none"
            else:
                note = "no clamps: 0x23/0x14/0x0F mean nothing here"
            print(f"    0x{a:04X}  seen at {seen or '(never read)'}  "
                  f"-- {note}")
    print("  a busy mark that opens and closes between two sweeps leaves no "
          "row above: the\n  capture records transitions, not values, and "
          "--interval is the only lever (#94)")


def self_test():
    """The tool's own logic on a fixture. Opens no EC and reads no register.

    Two things it can establish. The watch set's read-safety guard, and the
    floor a `--csv` run's hold is held to, are arithmetic over this file's own
    constants, with the counts they are supposed to hold to written into the
    check rather than read out of the thing being checked. The mark set is
    settled by handing a synthesised capture to the real
    `ec/tools/grade_0751_isolation.py` -- its reader, and then the block
    walk and `check_block_marks` that #457 made load-bearing, with the
    two-mark capture this tool used to write kept beside it as the negative
    control. Reading was never the part that decided anything: the reader has
    not changed since, and a mark set the grader's block walk refuses is a
    whole run ungraded, so "the grader can grade this capture" is a check
    rather than a claim. What this cannot establish is anything about the
    machine -- the sense `ecrw_fake.py` gives that phrase, and the reason this
    is not a substitute for the run
    docs/hardware-tests/level-block-0860-086e.md describes.
    """
    ok = True

    def check(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
        if not cond:
            ok = False

    print("manual_fan_ctrl_probe.py --self-test (no EC, no driver)")

    default, widened = watch_set(), watch_set(level_block=True)
    check("the default watch set is 206 addresses: 0x045F in, the fan-tach "
          "page out (#94)", len(default) == 206
          and 0x045F in default and not set(default) & set(FAN_TACH))
    check("--level-block widens it to 222 and still stops before 0x0460",
          len(widened) == 222 and not set(widened) & set(FAN_TACH))
    check("the 16 it adds are 0x0860-0x086E and 0x06E6, overlapping the "
          "default set nowhere",
          set(widened) - set(default) == set(LEVEL)
          and not set(LEVEL) & set(default))
    check("0x0440 and 0x0442 are already watched, so xdata-086x-dispatch.md's "
          "clamp guards and gates need no new byte",
          0x0440 in default and 0x0442 in default)
    check("--block costs 56 IOCTLs for the default set, not the 52 a "
          "contiguous 206 would give",
          block_ioctls(default) == 56 and block_ioctls(widened) == 61)
    check("no block of either set covers a fan-tach byte, so --block cannot "
          "widen the access to the page #94 is about",
          not block_span(default) & set(FAN_TACH)
          and not block_span(widened) & set(FAN_TACH))
    check("a hold at the grader's MARK_MERGE_SECONDS would fold the three "
          "marks and is refused, the next value up is not, and this tool's "
          "own 30 s hold clears the floor",
          not marks_clear(MARK_MERGE_SECONDS)
          and marks_clear(MARK_MERGE_SECONDS + 0.5)
          and marks_clear(SELFTEST_HOLD))

    # Imported here, not at module scope: this tool runs next to ecrw.py on a
    # Windows box, where the repository layout is not something to depend on at
    # import time, and a self-test that cannot reach the grader is a self-test
    # that checked a shape it wrote rather than the shape the grader reads.
    grader_path = Path(__file__).resolve().parents[2] / "ec/tools" \
        / "grade_0751_isolation.py"
    spec = importlib.util.spec_from_file_location("grade_0751_isolation",
                                                  grader_path)
    grader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "self-test.csv"
        sink = MarkCsv(str(path))
        for n, label in enumerate(arm_labels(0x10, 0xA0)):
            sink.mark(label, mark_ts(n * SELFTEST_HOLD))
        # A change in each of the two arms' windows, so the window walk has
        # something to file and the restore's own window is the empty one a
        # real run's is.
        sink.row([mark_ts(1), f"0x{BUSY:04X}", "0x00", f"0x{BUSY_VALUE:02X}"])
        sink.row([mark_ts(SELFTEST_HOLD + 1), f"0x{BUSY:04X}",
                  f"0x{BUSY_VALUE:02X}", "0x00"])
        sink.close()
        first = path.read_text().splitlines()
        # The second mode's run has to extend the capture rather than replace
        # it, and a run appends a whole block, so the first run's block has to
        # survive intact at the front of the second run's file.
        again = MarkCsv(str(path))
        for n, label in enumerate(arm_labels(0x10, 0x00), start=3):
            again.mark(label, mark_ts(n * SELFTEST_HOLD))
        again.close()
        both = path.read_text().splitlines()
        # The shape this tool used to write, kept as the negative control: the
        # checks below are worth nothing if the same walk reads a capture the
        # real one refuses as VOID, which is what that one was.
        void_path = Path(tmp) / "no-restore.csv"
        void_sink = MarkCsv(str(void_path))
        for n, label in enumerate(arm_labels(0x10, 0xA0)[:2]):
            void_sink.mark(label, mark_ts(n * SELFTEST_HOLD))
        void_sink.close()
        marks, changes = grader.read_capture(str(path))
        windows = grader.build_windows(marks, changes)
        blocks, unplaced = grader.assign_blocks(windows)
        for block in blocks:
            block.problems = grader.check_block_marks(
                block, [(str(path), marks)])
        void_marks, void_changes = grader.read_capture(str(void_path))
        void_blocks, _ = grader.assign_blocks(
            grader.build_windows(void_marks, void_changes))
        void_problems = [problem for block in void_blocks
                         for problem in grader.check_block_marks(
                             block, [(str(void_path), void_marks)])]

    check("the real grader's reader takes the capture this tool writes, the "
          "three labels in the order this run writes them",
          len(marks) == 6 and len(changes) == 2
          and [m.label for m in marks]
          == list(arm_labels(0x10, 0xA0)) + list(arm_labels(0x10, 0x00))
          and changes[0].addr == BUSY and changes[0].new == BUSY_VALUE)
    check("a second run appends: the first run's rows are still there",
          both[:len(first)] == first and len(both) > len(first))
    check("the header is written once, to a new file only",
          both.count("ts,addr,old,new") == 1)
    check("the marks are a hold apart, so the grader's coalescing keeps six "
          "windows and does not fold them into one",
          len(windows) == 6)
    check("the block walk reads two blocks and files nothing in no block",
          len(blocks) == 2 and not unplaced)
    check("each block is intact: its last mark is its own restore",
          all(grader.block_verdict(b) == "intact" for b in blocks))
    check("each block's roles are control, write, restore",
          [b.roles for b in blocks]
          == [["control", "write", "restore"]] * 2)
    check("no block's mark set withholds its windows",
          not any(b.problems for b in blocks))
    check("the two-mark capture is VOID, so a capture of that shape could not "
          "have passed the block-walk rows above",
          len(void_blocks) == 1
          and grader.block_verdict(void_blocks[0]) == "void"
          and len(void_problems) == 1)

    print(f"\nself-test {'passed' if ok else 'FAILED'}: the tool's own logic "
          "on a fixture. No EC was opened, no register was read, and nothing "
          "here\nsays anything about the machine -- that is what "
          "docs/hardware-tests/level-block-0860-086e.md is for.")
    return 0 if ok else 1


def report(name, moved, heading):
    print(f"\n{name} -- {heading}")
    if not moved:
        print("  nothing moved on its own")
    for a, (o, n, c) in sorted(moved.items()):
        # Neither arm's duty number means anything on its own; §4.4 is the
        # comparison between them.
        tag = " (fan duty, MAIN_FAN_L/R_DUTY -- §4.4)" if a in DUTY else ""
        print(f"  0x{a:04X}: 0x{o:02X} -> 0x{n:02X} "
              f"({c} change{'' if c == 1 else 's'}){tag}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", type=lambda s: int(s, 16),
                    help="the value to write to 0x0751: 0xA0, 0x00 or 0x10")
    # Both defaults are §3's, and the docstring says so: the procedure is the
    # reference, and the tool is the half that changed to match it.
    ap.add_argument("hold", nargs="?", type=float, default=30.0,
                    help="seconds per arm; §3's hold is ~30 s (default: 30). "
                         f"A --csv run needs a hold above the grader's "
                         f"MARK_MERGE_SECONDS ({MARK_MERGE_SECONDS:g}s), or "
                         "its three marks fold into one window")
    ap.add_argument("--interval", type=float, default=0.5,
                    help="seconds between sweeps; §3's starting point, not a "
                         "validated-safe value (default: 0.5)")
    ap.add_argument("--csv", metavar="PATH",
                    help="append every change to this capture, in the shape "
                         "ec_watch.py --mark --csv writes and "
                         "ec/tools/grade_0751_isolation.py reads; this run's "
                         "two arm boundaries and its restore are its MARK "
                         "rows, and the restore is the one the grader's block "
                         "walk closes a block on")
    ap.add_argument("--level-block", action="store_true",
                    help="also watch 0x0860-0x086E and 0x06E6 (16 more reads "
                         "per sweep, 222 in all), read-only, and report the "
                         "busy mark and the clamp constants; see "
                         "docs/hardware-tests/level-block-0860-086e.md")
    ap.add_argument("--self-test", action="store_true",
                    help="the watch set's read-safety guard, the hold a "
                         "--csv run is held to, and this run's "
                         "mark set against the real grader's reader and block "
                         "walk; opens no EC and reads no register")
    ap.add_argument("--block", action="store_true",
                    help="sweep 4 bytes per IOCTL (MMRD) instead of 1 (ECRR): "
                         "56 IOCTLs per sweep instead of 206, on a path that "
                         "has never been run against the driver -- see this "
                         "tool's help for the one check that settles it")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    target, hold, interval = args.target, args.hold, args.interval
    if target not in ALLOWED:
        sys.exit(f"value 0x{target:02X} not in the vendor set {{0x00,0x10,0xA0}}")
    if args.csv and not marks_clear(hold):
        # Refused rather than warned, and only here because this is the only
        # path a MARK row exists on. A terminal-only run at a short hold has
        # no capture to misread, and refusing one would be a guard against a
        # failure that cannot happen. A --csv run is the opposite case: the
        # marks are this tool's own, one per arm and one `hold` apart, so it
        # knows which captures its own reader cannot read -- and it finds out
        # late and totally, at the grading, with one window and no block.
        # `sys.exit(msg)` and not `ap.error`: a short hold is a value the tool
        # will not honour, the same class as an out-of-set target above, and
        # argparse's exit 2 is the code a mistyped flag gets.
        sys.exit(f"hold {hold:g}s is at or under the grader's "
                 f"MARK_MERGE_SECONDS ({MARK_MERGE_SECONDS:g}s): a --csv "
                 "capture's three marks would fold into one window, and no "
                 "block can be read out of it. Hold more than "
                 f"{MARK_MERGE_SECONDS:g}s (the default is 30) or drop --csv")
    addrs = watch_set(args.level_block)
    ec = Ec()
    orig = ec.read(MODE)
    print(f"0x0751 currently 0x{orig:02X}; control arm, then writing "
          f"0x{target:02X}, holding {hold:g}s each, sweeping every "
          f"{interval:g}s")
    print("  no interval here is validated (#94 owns making these tools safe "
          "by default): if the fans audibly change, stop and raise it")
    if args.level_block:
        print(f"  level block: {len(LEVEL)} more addresses, {len(addrs)} ECRR "
              f"reads per sweep; 0x0860-0x086E and 0x06E6, and nothing there "
              f"is written")
    if args.block:
        print(f"  --block: {block_ioctls(addrs)} MMRD IOCTLs per sweep instead "
              f"of {len(addrs)} ECRR reads, four bytes each. The path has "
              f"never been run against the driver and the per-byte read is "
              f"the default; see this tool's help for the one comparison that "
              f"settles it")
    if args.csv:
        print(f"  capture: {args.csv} (appended; ec/tools/"
              f"grade_0751_isolation.py reads this shape unchanged)")
    base = snap(ec, addrs, args.block)
    control, written = {}, {}
    # One {addr: {values}} per arm, so the level-block report can say what a
    # byte sat at across a whole arm -- a value held for 30 s is in no change
    # row and would otherwise read as a byte that was never there.
    seen = ([{a: set() for a in LEVEL_BYTES}, {a: set() for a in LEVEL_BYTES}]
            if args.level_block else None)
    sink = MarkCsv(args.csv) if args.csv else None
    # One call for all three, before the try: the `finally` names the restore's
    # label, and a name bound inside the try would be out of scope there for a
    # run that failed before it got there.
    no_op, mark, restored = arm_labels(orig, target)
    try:
        # The control arm writes the byte back the value it already holds. It
        # is not the restore step and not optional: without it there is no
        # baseline to read the write's duty movement against (§4.4). The label
        # is printed before the write so it timestamps the action, and `base`
        # is the caller's so the byte's own movement stays in the record.
        print(no_op)
        if sink:
            sink.mark(no_op)
        ec.write(MODE, orig)
        control = hold_and_observe(ec, hold, interval, base, no_op, addrs,
                                   sink, seen[0] if seen else None, args.block)
        # Re-snapshot: the write window opens from the state the control arm
        # settled into, so the two arms share a starting point. This is what
        # the grader's per-mark windows do.
        base = snap(ec, addrs, args.block)
        print(mark)
        if sink:
            sink.mark(mark)
        ec.write(MODE, target)
        written = hold_and_observe(ec, hold, interval, base, mark, addrs,
                                   sink, seen[1] if seen else None, args.block)
    except BaseException as exc:
        # Whatever ended the run -- an observation that raised, a Ctrl-C at the
        # keyboard -- the `finally` below still restores and still records the
        # restore, so the block would read `intact` over a window cut short in
        # a place nothing in the capture says. `read_capture` skips a `#` row
        # by design, for an operator annotating a file by hand, and
        # `build_windows` never sees one at all: this row is the only record
        # that the arm did not run to its hold. Written before the restore
        # mark so the reason is in the file rather than in a terminal nobody
        # reads twice.
        if sink:
            sink.row([f"# the run ended early: {type(exc).__name__}: {exc}"])
        raise
    finally:
        ec.write(MODE, orig)
        # The mark goes after the write and before the readback. After, so a
        # restore whose write raised leaves the block VOID rather than
        # recording a restore that did not happen; before the readback, so a
        # readback that raises cannot cost the capture the mark that says the
        # write landed. Printed as the same string the CSV row carries, the
        # way the two arm boundaries are: the by-eye check and the capture the
        # grader reads are the same run, and a restore that reached the screen
        # and not the file is the case §3 exists to catch.
        print(restored)
        if sink:
            sink.mark(restored)
        try:
            time.sleep(0.4)
            # Kept a line of its own, and worded as the readback it is: four
            # matching readbacks say the byte was written and nothing about
            # what the EC did with it (CLAUDE.md).
            print(f"  0x{MODE:04X} readback 0x{ec.read(MODE):02X} -- a "
                  "readback, not evidence the EC acted on it")
        finally:
            # The restore's mark is already on disk, so the readback is all
            # that is left in here, and the readback is exactly what a run
            # that has just crashed fails at. Closing regardless is what
            # leaves a crashed run's capture a file rather than a handle
            # waiting on the collector.
            if sink:
                sink.close()

    print("\nSUMMARY: two arms, same hold, differing only in the write.")
    report("control arm", control,
           "no-op write -- the baseline the write under test has to beat")
    report("write under test", written, f"0x0751 = 0x{target:02X}")

    # §4.5's precondition for reading anything into the two duty numbers: the
    # load has to have been flat across both. Printed, not judged.
    for a in TEMPS:
        name = "CPU_TEMP" if a == 0x043E else "GPU_TEMP"
        print(f"\n{name} 0x{a:04X}: control {fmt(control.get(a))}, "
              f"write {fmt(written.get(a))}")
        print("  a duty difference means something only if this held steady "
              "across both arms (§4.5)")

    if seen:
        report_level_block([(f"control arm -- {no_op}", seen[0]),
                            (f"write under test -- {mark}", seen[1])])
    return 0


if __name__ == "__main__":
    sys.exit(main())
