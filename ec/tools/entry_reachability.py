#!/usr/bin/env python3
"""Which program's transfers name a given address -- reachability, per program.

`census_forwarder_targets.py` answers *which bank* a forwarder's `imm16` is
read in. This answers the question that decides what may be concluded from a
listing at an address a forwarder names: **which program's own code transfers
reach it.** The two are different questions and answering one does not answer
the other, which is the gap issue #336 fell into -- a bank-1 listing was read as
though bank 1 were where the forwarder landed, and no transfer this scan can
resolve in bank 1 names that address at all.

**Why this is keyed on the program and not on the address.** A 16-bit `lcall`
target does not name a bank: the same three bytes are a same-bank and a
cross-bank call. So "something calls 0xC1E7" is not a property of the address;
it is a property of the address *and the program the caller's bytes are in*.
`census_forwarder_targets.py` resolves that for forwarders by way of the stub
they route through. This resolves it the other way, by asking each program in
turn which of its own transfers name the address -- so the answer for bank 1
cannot be contaminated by bank 0's call sites, which is the shape of the
mistake being corrected.

**The three families, and what a zero here does not mean.** `call_sites()`,
`paged_sites()` and `relative_sites()` are `audit_call_targets.py`'s own, used
by import rather than re-derived: they are the census the call-target tables
were built from, and a second implementation of "every transfer in this image"
here would be a second thing to be wrong. They are the three *statically
resolvable* families, which is not every way a target can be reached:

  * an indirect transfer (`jmp @A+DPTR` and its three siblings) computes its
    target at run time, and no scan of the image resolves one;
  * a fall-through from the preceding instruction reaches an entry that no
    transfer names -- `fallthrough_in()` below reports that case separately
    rather than counting it as a caller;
  * a value used as data and only later transferred.

So a program reported as naming nothing is **not reached by this method**, never
"unreachable" and never "dead". `registers.yaml`'s own caveat about its scans
is the same rule, and it is a rule about a scan's *reach*, not about the words
that describe it.

**What this tool reads.** One file: `ec/firmware/GMxMGxx_11.800`, through
`read_image()`. No annotation file is an input, so no `status:` in
`ec/annotations/registers.yaml` can move on any of this -- and `--self-test`
holds that to the reads rather than to the text, by recording every path the
tool opens and asserting the firmware image is the only one.

**Reachability is not liveness.** That a transfer names an address says the
linker put a reference there. Whether the code runs is not established by any
of this, and nothing here was observed on hardware: the one input is
`ec/firmware/GMxMGxx_11.800`, read through the region windows
`audit_call_targets.py` already pins.

Usage:
    python3 ec/tools/entry_reachability.py 0xC1E7
    python3 ec/tools/entry_reachability.py --csv 0xC1E7 0xC389 0xC201
    python3 ec/tools/entry_reachability.py --self-test
"""
import argparse
import builtins
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir))
sys.path.insert(0, HERE)

from audit_call_targets import (AUDITED, call_sites,  # noqa: E402
                                paged_sites, region_bounds, relative_sites)
from build_ec_decompile import COMMON_END, FIRMWARE, file_offset  # noqa: E402
from disasm8051 import OPCODE_LEN  # noqa: E402

# The three families, named as the report names them. `audit_call_targets.py`
# splits them across sections 1, 5 and 6 of its own report, and the labels here
# match those so a row reads the same in both places.
FAMILIES = (("abs", call_sites), ("paged", paged_sites), ("rel", relative_sites))

# How many bytes before an entry to look for a fall-through into it. One
# instruction is at most three bytes, so three is the whole of the question;
# a larger window would find an unrelated earlier instruction and call it a
# caller.
FALLTHROUGH_WINDOW = 3


def read_image(path=None):
    """The firmware image bytes -- this tool's one input.

    Named separately from `main()` so the self-test can watch the reads: the
    claim that no register `status:` can move on any of this is a claim about
    which files are opened, and a check that watches the opens is a check that
    can fail when a second input appears.
    """
    with open(path or FIRMWARE, "rb") as handle:
        return handle.read()


def runtime_of(program, offset):
    """Runtime address of a file `offset` found while scanning `program`.

    The scan functions yield file offsets, because that is what a byte index
    into the one image is; a report line has to name the address a reader can
    look up in a listing, which is the runtime one. Below `COMMON_END` the two
    coincide, and `region_bounds` puts `common` at file offset 0, so the
    subtraction is skipped rather than done and undone.
    """
    if offset < COMMON_END:
        return offset
    return COMMON_END + (offset - region_bounds(program)[0])


def sites_naming(d, program, target):
    """`(family, site runtime)` for every transfer in `program` naming `target`.

    One program at a time and never the whole image, which is the whole point:
    a site found while scanning bank 0 says nothing about bank 1, and mixing
    them is the mistake this module exists to make impossible.
    """
    lo, hi = region_bounds(program)
    out = []
    for family, scan in FAMILIES:
        for offset, _op, tgt in scan(d, lo, hi):
            if tgt == target:
                out.append((family, runtime_of(program, offset)))
    return out


def fallthrough_in(d, program, entry):
    """`(site runtime, entry)` when the instruction before `entry` falls in.

    An entry no transfer names may still be reached simply by the instruction
    before it running off its end into it. That is a real way in, and folding
    it into the caller list would misreport it as a reference the linker wrote;
    it is reported as its own thing instead.

    The walk starts `FALLTHROUGH_WINDOW` bytes back and steps forward by the
    opcode table's own lengths, so a start offset that is not an instruction
    boundary produces a decode that does not end on `entry` and is discarded
    rather than believed. Every byte is read through `file_offset`, the
    repository's own runtime-to-file mapping, because reading bank 1's window
    at bank 0's offset lands in a different 32 KiB and would decode a
    different instruction.

    `None` when no such walk lands on it, which is the ordinary answer and is
    not a claim that nothing reaches the entry.
    """
    start = entry - FALLTHROUGH_WINDOW
    # The walk has to stay inside the program it is decoding. `region_bounds` is
    # in file offsets and `entry` is a runtime address, so the window test is
    # made against the runtime base rather than against that: a bank entry's
    # three preceding bytes may not reach below 0x8000, where the common
    # area's copy of them would be. The `common` program is the other
    # direction -- it *is* the 0x0000-0x7FFF window and holds nothing at or
    # above 0x8000, so `file_offset('common', 0xC1E4)` would hand back bank 0's
    # bytes and this would report bank 0's instruction as the common area's.
    if entry >= COMMON_END:
        if program == "common" or start < COMMON_END:
            return None
    elif start < 0:
        return None
    at = start
    while at < entry:
        length = OPCODE_LEN[d[file_offset(program, at)]]
        at += length
    return (start, at) if at == entry else None


def report(d, targets):
    """The per-program table for each target, plus its coverage denominators.

    The denominators are printed beside every count because the number they
    qualify is otherwise unreadable: an empty row means nothing without the
    window it was empty over.
    """
    lines = []
    for target in targets:
        lines.append("0x%04X" % target)
        for program in AUDITED:
            sites = sites_naming(d, program, target)
            lo, hi = region_bounds(program)
            scanned = sum(1 for _f, scan in FAMILIES for _o, _t, _tgt
                          in scan(d, lo, hi))
            where = ", ".join("%s from 0x%04X" % (f, a) for f, a in sites)
            lines.append("    %-7s %s" % (program, where or "-- names it nowhere --"))
            fall = fallthrough_in(d, program, target)
            if fall is not None:
                lines.append("             (fall-through into it from the "
                             "instruction at 0x%04X, which is not a call)"
                             % fall[0])
            lines.append("             over %d transfer sites in this "
                         "program's own window%s"
                         % (scanned,
                            "" if sites else "; naming it nowhere is not "
                                              "reached by this method"))
        lines.append("")
    return "\n".join(lines)


def write_csv(d, targets):
    w = csv.writer(sys.stdout)
    w.writerow(["target", "program", "naming_families", "naming_sites",
                "fallthrough_site", "sites_scanned_in_program"])
    for target in targets:
        for program in AUDITED:
            sites = sites_naming(d, program, target)
            lo, hi = region_bounds(program)
            scanned = sum(1 for _f, scan in FAMILIES for _o, _t, _tgt
                          in scan(d, lo, hi))
            fall = fallthrough_in(d, program, target)
            w.writerow([
                "0x%04X" % target, program,
                " ".join(f for f, _a in sites),
                " ".join("0x%04X" % a for _f, a in sites),
                "" if fall is None else "0x%04X" % fall[0],
                scanned,
            ])


def self_test(d) -> int:
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print("  %s  %s" % ("ok  " if ok else "FAIL", text))

    # The positive control, and the reason the module is worth anything: the
    # scan has to find the call sites an annotation already names. `bank0,0xA389`
    # and `ghidra-variables.csv` both record a `lcall 0xC1E7` at 0xD9E7 in bank
    # 0, and `bank1,19A8` records bank 0's 0xC118 lcalling the annotated
    # `test_3202_bit0` at 0xC0E7. A scan that found nothing anywhere would be
    # consistent with every claim below it, so these two are what make a zero
    # mean something.
    for program, target, expected in (("bank0", 0xC1E7, [0xD9E7]),
                                      ("bank0", 0xC0E7, [0xC118, 0xCBB5])):
        found = [a for _f, a in sites_naming(d, program, target)]
        check(found == expected,
              "%s names 0x%04X at %s -- the call sites the annotations already "
              "record, so a zero elsewhere is a property of the address and "
              "not of the scan"
              % (program, target, ", ".join("0x%04X" % a for a in expected)))

    # And the negative, which is the finding: bank 1 names 0xC1E7 nowhere,
    # while bank 0 names it once. Keyed per program, so the two cannot be
    # confused for each other -- which is the whole of what went wrong.
    b0 = sites_naming(d, "bank0", 0xC1E7)
    b1 = sites_naming(d, "bank1", 0xC1E7)
    check(bool(b0) and not b1,
          "bank 0 names 0xC1E7 and bank 1 names it nowhere -- answered per "
          "program, so bank 0's site is not read as bank 1's")

    # The bank window is not the same question as the common area. A target
    # below 0x8000 is one set of bytes every program runs, so the three
    # programs must agree about it; a target at or above 0x8000 must not.
    check(sites_naming(d, "common", 0xC1E7) == [],
          "the common area names 0xC1E7 nowhere either, so the answer is not an "
          "artefact of scanning one window")

    # The fall-through walk is a separate claim and is held to its own: it finds
    # the run of three `jnb` at bank1 0xC1DE that falls into 0xC1E7, and it does
    # not fire on an entry whose preceding bytes do not decode onto it.
    fall = fallthrough_in(d, "bank1", 0xC1E7)
    check(fall is not None and fall[1] == 0xC1E7,
          "bank1 0xC1E7 is reached by fall-through from the bytes at 0x%04X, "
          "which is reported as its own thing and not as a call site"
          % (fall[0] if fall else 0))
    check(fallthrough_in(d, "bank1", 0xCC64) is None,
          "and the walk does not fire on an entry whose preceding bytes do not "
          "decode onto it")

    # The walk starts three bytes back and steps by the opcode table, so an
    # entry whose predecessor is a three-byte instruction is still found. If
    # the window were one byte this would go red.
    check(fallthrough_in(d, "bank0", 0xCC5F) == (0xCC5C, 0xCC5F),
          "a three-byte predecessor is still inside the window, so the walk is "
          "not silently restricted to one-byte instructions")

    # A target nobody names anywhere is reported, not dropped: the absence of a
    # row is how a method's blind spot looks like a finding.
    check(sites_naming(d, "bank0", 0xCC64) == []
          and sites_naming(d, "bank1", 0xCC64) == [],
          "an address no transfer in any program names comes back as an empty "
          "list per program rather than as a missing row")

    # The calibration refusal, checked where it is load-bearing: the sentence
    # that *reports* a program as naming nothing must name the method's limit,
    # and must not contain the word that would upgrade "not found" into a
    # verdict about the bytes. A whole-file scan for the words would trip on
    # this module's own refusal -- it has to say "unreachable" to disclaim it.
    reported = report(d, [0xC1E7]).lower()
    strong = [w for w in ("unreachable", "dead code", "never called",
                          "not called", "unreferenced", "absent")
              if w in reported]
    check(not strong,
          "what the report prints about a program that names nothing says no "
          "more than the scan found"
          + ("" if not strong else " -- it says " + ", ".join(strong)))
    check("not reached by this method" in reported,
          "and it says the limit in the same breath, so a reader cannot take "
          "the empty row for more than it is")

    # What the tool reads, which is what decides whether a register `status:`
    # could move on any of this. Checked against the reads rather than against
    # a path constant: `builtins.open` is watched for the length of the run
    # and the image read through it, and the recorded set has to be exactly
    # the firmware image. A second input -- an annotation file, anything --
    # puts a second path in that set and this goes red, which is the property
    # the old substring test could not have: it compared a constant to itself.
    opened = []
    real_open = builtins.open

    def watch(path, *a, **kw):
        if isinstance(path, (str, bytes, os.PathLike)):
            opened.append(os.path.realpath(os.fsdecode(path)))
        return real_open(path, *a, **kw)

    builtins.open = watch
    try:
        through_watch = read_image()
        report(through_watch, [0xC1E7])
    finally:
        builtins.open = real_open
    check(opened == [os.path.realpath(FIRMWARE)] and through_watch == d,
          "a full run opens the firmware image and nothing else (opened %s), "
          "so no status: in ec/annotations/registers.yaml can move on any of "
          "this"
          % (", ".join(os.path.relpath(p, ROOT) for p in opened) or "nothing"))

    print()
    print("self-test FAILED: %d check(s) disagree" % bad if bad
          else "self-test passed: the positive controls find the sites the "
               "annotations record, bank 1 names 0xC1E7 nowhere, and no claim "
               "here outruns the method")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*",
                    help="runtime addresses, 0x-prefixed or bare hex")
    ap.add_argument("--csv", action="store_true",
                    help="one row per (target, program) on stdout, instead of "
                         "the table")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the positive controls against the "
                         "annotations, the per-program split, and the "
                         "fall-through walk")
    args = ap.parse_args()

    d = read_image()

    if args.self_test:
        return self_test(d)

    targets = [int(t, 16) for t in args.targets]

    if args.csv:
        write_csv(d, targets)
        return 0

    print(report(d, targets))
    return 0


if __name__ == "__main__":
    sys.exit(main())