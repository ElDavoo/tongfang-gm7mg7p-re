#!/usr/bin/env python3
r"""Issue #284: write 0x0743 bit 1 with bit 0 held set, and watch 0x07C4 bit 3,
to decide whether the EC firmware's bit-3 writer is the ASL's `DBEN` gate.

The chain, from the committed annotation rows in
ec/annotations/ghidra-functions.csv and nothing else:

  * `0x96AD=apply_oem_overrides_then_fill_08xx` "copies 0x0745 to 0x09EA and
    0x0746 to 0x09EB when 0x0743 bit 0 is set, calls 0x94C0 with 0x0743
    bit 1". So bit 0 is a **gate** and bit 1 is the **value** -- two different
    bits, and reading one as the other makes a probe that cannot move the byte
    it is watching.
  * `0x94C0=set_07c4_bit4_from_r7` is a read-modify-write of 0x07C4 driven by
    R7: non-zero ORs 0x10 (bit 4) in, zero ANDs 0xEF out. Bit 1 of 0x0743
    becomes **bit 4** of 0x07C4.
  * `0x83FF=sync_0788_and_07d4_from_09e9` "only when bit 0 of 0x0743 ... is
    set -- copies 0x09EA and 0x09EB into 0x07D4 and 0x07D5, sets or clears
    bit 3 of 0x07C4 to follow bit 4". So bit 4 becomes **bit 3**, and bit 0
    is the gate on the routine that does that last hop.

A probe that flipped bit 0 and watched bit 3 would therefore open a gate onto
a bit 4 that never moved, and report "nothing moved" while proving nothing.
The two arms here are the other way round, and both hold bit 0 set:

  arm A   0x0743 | 0x03      bit 0 set (gate), bit 1 set   -- the value
  arm B   0x0743 | 0x01, ~0x02   bit 0 still set, bit 1 clear
  restore 0x0743 exactly as read

Both arms preserve bits 2-7 of whatever the byte already held. That matters
because bit 2 is cTGP enable, and the vendor's own power-mode write puts
0x03 on AC and 0x00 on battery (ec/annotations/registers.yaml,
CTGP_DB_CTRL), so on AC arm A is already a state the machine has been in and
on battery arm A *forces* `DB function control` on. The tool prints which of
the two it is about to do, because the difference is the safety argument.

**This tool prints; it does not score.** There is no verdict, no pass/fail and
no status word, and a value that holds across an arm is not a result:
`../../CLAUDE.md`, "a register write being accepted (readback matches) is not
evidence the EC acts on it". Issue #168 owns grading a capture. The procedure
that reads one is docs/hardware-tests/ctgp-dben-07c4-bit3.md, and it is
written and not run.

**Four ECRR reads per sweep** -- 0x0743 for the readback, 0x07C4, 0x07D4 and
0x07D5 -- against gpu_block_watch.py's 24 and manual_fan_ctrl_probe.py's 206,
so the #94 pacing exposure is far smaller than theirs. That is not a safety
argument, and no interval here is validated: `ecrw.Ec.read` is one ECRR
DeviceIoControl per byte with nothing between calls. The 0.5 s default is
manual_fan_ctrl_probe.py's and is a starting point. If the fans audibly
change, stop and raise it.

The 30 s and 0.5 s defaults are that probe's and a starting point, not
validated ones; the procedure is the reference whenever the two disagree.

Run elevated, next to ecrw.py, with the vendor driver loaded. Without
`--i-mean-it` this prints the byte script and refuses: no EC is opened, no
file is created, and `--csv` is required for a run that acts, because a
capture is the only record of one.

Usage:
  # plan it, with the byte 0x0743 currently holds (from `ecrw.py read 0x0743`)
  ctgp_dben_probe.py --orig 0x03
  # run it
  ctgp_dben_probe.py --csv ../../evidence/ec-watch/<date>-ctgp-dben-07c4-bit3.csv ^
      --seconds 30 --interval 0.5 --i-mean-it
"""
import argparse
import csv
import datetime
import sys
import time

from ecrw import Ec, EcError

CTRL = 0x0743       # CTGP_DB_CTRL: bit 0 the gate, bit 1 the value
DBEN = 0x07C4       # the byte; bit 3 is the DSDT's DBEN
CPUA = 0x07D4       # 0x83FF copies 0x09EA here, in the same block
DBAP = 0x07D5       # ... and 0x09EB here

# 0x07D4/0x07D5 are watched because the *same* 0x83FF block writes them, one
# instruction apart from the bit-3 write. That is what lets a reader tell
# "the routine ran and bit 3 followed" from "the routine ran": the two bytes
# the block moves only ever move together with it.
WATCH = [
    (CTRL, "GNEN b0, ECDC b1", "confirmed-working",
     "dsdt.dsl:52204, registers.yaml CTGP_DB_CTRL"),
    (DBEN, "DBEN b3, DBST b5", "present-untested",
     "dsdt.dsl:52238, registers.yaml GPU_DYNAMIC_BOOST_STATUS"),
    (CPUA, "CPUA", "present-untested", "dsdt.dsl:52254, registers.yaml CPUA"),
    (DBAP, "DBAP", "present-untested", "dsdt.dsl:52254, registers.yaml DBAP"),
]

GATE_BIT = 0x01       # 0x0743 bit 0 -- the 0x83FF block's guard, nothing more
VALUE_BIT = 0x02      # 0x0743 bit 1 -- what 0x94C0 is handed
OBSERVED_BIT = 0x08  # 0x07C4 bit 3 -- the DSDT's DBEN, the bit under test

COLS = ["ts", "mark", "t_s", "ctrl_written", "ctrl_read", "dben_byte",
        "dben_b3", "cpua", "dbap"]

# The two arms, named for the bit each one drives rather than for a value,
# because a value is only true for one starting byte.
ARMS = ("arm A 0x0743 bit 1 set", "arm B 0x0743 bit 1 clear")


def arm_bytes(orig):
    """The two arm bytes, as a pair.

    Both force bit 0 and preserve bits 2-7, so the only difference between
    them is bit 1 -- the one the two annotation rows say carries the value.
    """
    return orig | GATE_BIT | VALUE_BIT, (orig | GATE_BIT) & ~VALUE_BIT & 0xFF


def _int(s):
    return int(s, 16) if str(s).lower().startswith("0x") else int(s, 0)


def print_watch_set():
    """The citation list, once, before anything is opened.

    Printed rather than left to a flag alone because a capture is evidence,
    and evidence that does not record what was watched is a capture of
    nothing in particular -- the same reason gpu_block_watch.py prints its
    table. A "status:" cell is registers.yaml's own vocabulary, quoted, and
    present-untested is what it says about 0x07C4 today.
    """
    print(f"watch set -- {len(WATCH)} addresses, {len(WATCH)} ECRR reads a "
          f"sweep, one clock")
    for addr, name, status, cite in WATCH:
        role = ""
        if addr == DBEN:
            role = (f"  <- the bit under test, 0x07C4 bit "
                    f"{OBSERVED_BIT.bit_length() - 1}")
        print(f"  0x{addr:04X}  {name:<18}  {status:<18}  {cite}{role}")
    print("  no status here is a claim about the EC acting on the byte; "
          "present-untested is what registers.yaml says.\n")


def print_plan(orig=None):
    """The byte script, with no EC opened.

    `orig` is a value the operator already read (`ecrw.py read 0x0743`) so the
    two arms can be resolved to numbers; without it they print as the
    expressions they are, which is the whole of what can be said about a byte
    this run has not read.
    """
    print("planned byte script -- nothing is opened, nothing is written:")
    if orig is None:
        print("  arm A   orig | 0x03            bit 0 set (gate), bit 1 set")
        print("  arm B   (orig | 0x01) & ~0x02  bit 0 set (gate), bit 1 clear")
        print("  restore orig                   exactly what the run reads")
    else:
        arm_a, arm_b = arm_bytes(orig)
        print(f"  0x0743 read as 0x{orig:02X}")
        print(f"  arm A   orig | 0x03            -> 0x{arm_a:02X}")
        print(f"  arm B   (orig | 0x01) & ~0x02  -> 0x{arm_b:02X}")
        print(f"  restore orig                   -> 0x{orig:02X}")
    print("  bits 2-7 are read from orig and written back unchanged in all "
          "three")
    # The vendor writes 0x03 on AC and 0x00 on battery
    # (registers.yaml, CTGP_DB_CTRL), so which of the two this is decides
    # whether arm A is a state the machine has already been in or one it is
    # being pushed into. Both arms open bit 0 either way.
    if orig is None:
        print("  bit 0 in orig: unknown until the run reads it -- the vendor "
              "writes 0x0743=0x03 on AC and 0x00 on battery, and both arms "
              "open the gate")
    elif orig & GATE_BIT:
        print("  bit 0 in orig: already set -- arm A is close to the 0x03 "
              "the vendor writes on AC")
    else:
        print("  bit 0 in orig: CLEAR -- arm A forces `DB function control` "
              "on, which on battery is a state the vendor has not put there")


def sample(ec, mark, written, t0):
    """One sweep: the write that is in force, and the four bytes worth having.

    A wide time series rather than a change log. gpu_block_watch.py's
    `ts,addr,old,new` records differences, so a bit that goes up inside one
    arm and comes back before the next reads as quiet; this question is what
    the byte did *across* a settle interval, so every sample is a row and the
    arm's name is on it. `dben_b3` is the bit under test on its own, so a
    reader does not have to re-derive it from `dben_byte` to sort the CSV.
    """
    ctrl = ec.read(CTRL)
    dben = ec.read(DBEN)
    return [
        datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        mark, round(time.time() - t0, 1),
        f"0x{written:02X}", f"0x{ctrl:02X}", f"0x{dben:02X}",
        (dben & OBSERVED_BIT) >> (OBSERVED_BIT.bit_length() - 1),
        f"0x{ec.read(CPUA):02X}", f"0x{ec.read(DBAP):02X}",
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=float, default=30.0,
                    help="seconds to hold each arm (default 30; a starting "
                         "point, not a validated one)")
    ap.add_argument("--interval", type=float, default=0.5,
                    help="seconds between sweeps (default 0.5; a starting "
                         "point, not a validated-safe one -- #94)")
    ap.add_argument("--csv", help="required with --i-mean-it: a capture is the "
                                  "only record of a run that acts")
    ap.add_argument("--i-mean-it", action="store_true",
                    help="required: this writes a live 0x0743")
    ap.add_argument("--orig", type=_int,
                    help="planning only: the byte 0x0743 already holds, so a "
                         "run without --i-mean-it can resolve the two arms to "
                         "numbers. Refused with --i-mean-it, which reads the "
                         "byte for itself.")
    args = ap.parse_args(argv)

    print_watch_set()

    if args.i_mean_it and args.orig is not None:
        print("refusing: --orig is a planning value and a real run reads "
              "0x0743 for itself; drop one of the two.", file=sys.stderr)
        return 2
    if not args.i_mean_it:
        print_plan(args.orig)
        print("refusing to write without --i-mean-it", file=sys.stderr)
        return 2
    if not args.csv:
        print("refusing: --csv is required, because a capture is the only "
              "record of a run that acts", file=sys.stderr)
        return 2

    fh = open(args.csv, "a", newline="")
    try:
        w = csv.writer(fh)
        # Append, and a header only on an empty file: the procedure's §3 is
        # one CSV per run, but a re-run into the same file must not stack a
        # second header on the first run's rows.
        if fh.tell() == 0:
            w.writerow(COLS)

        with Ec() as ec:
            orig = ec.read(CTRL)
            arm_a, arm_b = arm_bytes(orig)
            print(f"baseline: 0x0743 = 0x{orig:02X} "
                  f"(bit 0 {'set' if orig & GATE_BIT else 'CLEAR'}, bit 1 "
                  f"{'set' if orig & VALUE_BIT else 'clear'}), "
                  f"0x07C4 = 0x{ec.read(DBEN):02X}")
            if orig & GATE_BIT:
                print("  bit 0 was already set, so the vendor writes this "
                      "state on AC (registers.yaml CTGP_DB_CTRL: 0x03 on AC, "
                      "0x00 on battery) and arm A is close to a state this "
                      "machine has already been in")
            else:
                print("  bit 0 was clear, so both arms FORCE `DB function "
                      "control` on for the length of the run; the vendor "
                      "writes 0x0743=0x00 on battery")
            print(f"  arm A 0x{arm_a:02X}  arm B 0x{arm_b:02X}  restore "
                  f"0x{orig:02X}, bits 2-7 untouched in all three")
            print(f"holding {args.seconds:g}s an arm, sweeping every "
                  f"{args.interval:g}s")
            print("no interval here is validated (#94); if the fans audibly "
                  "change, stop and raise it.")

            t0 = time.time()
            try:
                for mark, byte in zip(ARMS, (arm_a, arm_b)):
                    print(f"\n[{mark}] 0x0743 = 0x{byte:02X}", flush=True)
                    ec.write(CTRL, byte)
                    arm_end = time.time() + args.seconds
                    while True:
                        row = sample(ec, mark, byte, t0)
                        w.writerow(row)
                        fh.flush()
                        print("  ".join(str(x) for x in row), flush=True)
                        if time.time() >= arm_end:
                            break
                        time.sleep(args.interval)
            finally:
                # A finally rather than an except clause, because what puts the
                # byte back has to include a Ctrl-C: KeyboardInterrupt is a
                # BaseException, so `except EcError` cannot see it.
                ec.write(CTRL, orig)
                print(f"\nrestored 0x0743 -> 0x{orig:02X}, readback = "
                      f"0x{ec.read(CTRL):02X}")
    except EcError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
