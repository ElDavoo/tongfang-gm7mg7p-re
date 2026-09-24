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
pass, the by-hand package-power notes, the before/after range dumps §4.6 reads,
and §6's eight-file set. This tool produces neither a MARK-CSV nor a dump.

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
increase, and `ecrw.Ec.read` (ecrw.py:115) is one ECRR DeviceIoControl per byte
with nothing between calls.** This run is the one
`manual-fan-ctrl-0751-isolation.md` §3 holds under a fixed load, and a block
that moves the fans itself is worth less than no block. There is no safe
interval derivable without the driver and the machine (#94 is the open work), so
`--interval`'s 0.5 s default is §3's starting point and nothing more: if the
fans audibly change during a run, stop and raise it.

Values under test are limited to the three the vendor itself writes: 0xA0
Office, 0x00 Gaming, 0x10 Turbo (a no-op if that is already the mode). The
control arm's write is deliberately not gated on that set -- it re-writes the
value the EC already holds, so it introduces nothing the machine has not seen,
and gating it would make the tool refuse to run in a mode the vendor UI has
set. Restores 0x0751 in a finally block, which wraps both arms.

Run elevated, next to ecrw.py. Needs the vendor's ACPI driver present.

Usage:
  manual_fan_ctrl_probe.py 0xA0 [hold_seconds] [--interval 0.5]
"""
import argparse
import sys
import time

from ecrw import Ec

MODE = 0x0751
WATCH = [0x0751, 0x0783, 0x0784, 0x0785, 0x0786, 0x0787,
         0x07C5, 0x07C6, 0x075B, 0x075C, 0x0743, 0x0744, 0x0745, 0x0746]
FANTBL = list(range(0x0F00, 0x0F60))
# Exclusive of 0x0460: the fan-tach bytes are the next page (issue #94).
TEMP = list(range(0x0400, 0x0460))
ALL = WATCH + FANTBL + TEMP
ALLOWED = {0x00, 0x10, 0xA0}
DUTY = (0x075B, 0x075C)
TEMPS = (0x043E, 0x044F)


def snap(ec):
    return {a: ec.read(a) for a in ALL}


def diff(base, cur):
    return [(a, base[a], cur[a]) for a in ALL if base[a] != cur[a]]


def hold_and_observe(ec, hold, interval, base, label):
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
    -- anything that later consumes these rows (a CSV sink, issue #124) attaches
    to one place rather than to two loops.
    """
    moved = {}
    t0 = time.time()
    while time.time() - t0 < hold:
        cur = snap(ec)
        for a, o, n in diff(base, cur):
            print(f"    +{time.time()-t0:4.1f}s  [{label}] 0x{a:04X}: "
                  f"0x{o:02X} -> 0x{n:02X}")
            seen = moved.get(a)
            moved[a] = (seen[0], n, seen[2] + 1) if seen else (o, n, 1)
        base = cur
        time.sleep(interval)
    return moved


def fmt(motion):
    return "no change" if motion is None \
        else f"0x{motion[0]:02X} -> 0x{motion[1]:02X} ({motion[2]} changes)"


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
                    help="seconds per arm; §3's hold is ~30 s (default: 30)")
    ap.add_argument("--interval", type=float, default=0.5,
                    help="seconds between sweeps; §3's starting point, not a "
                         "validated-safe value (default: 0.5)")
    args = ap.parse_args(argv)
    target, hold, interval = args.target, args.hold, args.interval
    if target not in ALLOWED:
        sys.exit(f"value 0x{target:02X} not in the vendor set {{0x00,0x10,0xA0}}")
    ec = Ec()
    orig = ec.read(MODE)
    print(f"0x0751 currently 0x{orig:02X}; control arm, then writing "
          f"0x{target:02X}, holding {hold:g}s each, sweeping every "
          f"{interval:g}s")
    print("  no interval here is validated (#94 owns making these tools safe "
          "by default): if the fans audibly change, stop and raise it")
    base = snap(ec)
    control, written = {}, {}
    try:
        # The control arm writes the byte back the value it already holds. It
        # is not the restore step and not optional: without it there is no
        # baseline to read the write's duty movement against (§4.4). The label
        # is printed before the write so it timestamps the action, and `base`
        # is the caller's so the byte's own movement stays in the record.
        no_op = f"no-op wrote 0x0751=0x{orig:02X}"
        print(no_op)
        ec.write(MODE, orig)
        control = hold_and_observe(ec, hold, interval, base, no_op)
        # Re-snapshot: the write window opens from the state the control arm
        # settled into, so the two arms share a starting point. This is what
        # the grader's per-mark windows do.
        base = snap(ec)
        mark = f"wrote 0x0751=0x{target:02X}"
        print(mark)
        ec.write(MODE, target)
        written = hold_and_observe(ec, hold, interval, base, mark)
    finally:
        ec.write(MODE, orig)
        time.sleep(0.4)
        print(f"restored 0x0751 -> 0x{ec.read(MODE):02X}")

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


if __name__ == "__main__":
    main()
