#!/usr/bin/env python3
"""Decode the inline `switch` tables the main EC image's one table-reading
subroutine consumes -- the bank-0 table at runtime 0x8038 in particular.

ec/annotations/bank-call-audit.md section 8 met that table as a side effect:
four PC-relative branch sites resolve outside their region, and one of them,
file 0x0803B, scores 24 of 24 anchors while plainly sitting in data. That
section read the bytes from 0x8038 as `sjmp` + `index, address` triples.
This tool reads them against the code that consumes them instead, and the
two readings disagree -- section 9 corrects section 8 in place.

**How the table is found, and why it is not a DPTR scan.** Nothing in this
image loads DPTR with #0x8038 or #0x803A: the reader takes its pointer off
the *stack*. The table sits inline immediately after an `lcall` to a
subroutine that begins `pop dph ; pop dpl ; mov r0,a`, so the return address
the call pushed is the table's own address and the accumulator carries the
selector. That is the shape Keil C51 emits for a `switch` on a byte (its
runtime calls the helper `?C?CCASE`); the name is a name for the idiom, not
a symbol read out of this image. So the search here is for the prologue
shape, then for `lcall` bytes naming it -- an immediate-DPTR scan finds this
table zero times, which is the blind spot that framing is meant to cover.

**Entry layout, taken from the reader rather than from the table.** The
helper reads the first two bytes of an entry as a big-endian address and the
*third* as the case value, and stops on an all-zero address, after which two
more bytes give the default. Address-then-case, not case-then-address:
section 8 read them the other way round, which shifts every entry by one byte
and puts a phantom `sjmp` at the table's head.

**What a well-formed verdict is worth.** An `lcall` byte site is a byte scan
and over-counts (bank-call-audit.md section 1 says why), so each candidate's
table is checked rather than assumed: case values strictly ascending, every
target and the default resolving inside the caller's own region, and the byte
after the table being one of the table's own targets -- the fall-through a
compiler emits for the first case. All of that is corroboration, not
proof; nothing here is evidence that any handler executes, and no `status:`
in ../annotations/registers.yaml follows from a decode.

Usage:
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --at 0x0D148
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --all-tables
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --csv \
        > ec/annotations/bank0-8038-dispatch-table.csv
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import csv
import sys

from disasm8051 import converges_from, decode
from trace_xdata_refs import (PD_MARKER, REGIONS, offset_for_runtime,
                              region_of, runtime_addr)

# `pop dph ; pop dpl ; mov r0,a` -- the reader's first five bytes. The two
# pops are what make the table findable at all: they turn the pushed return
# address into the table pointer, so the table is named by the *position* of
# the call and never by an immediate.
READER_PROLOGUE = bytes.fromhex("d083d082f8")

LCALL = 0x12

# The main EC image, i.e. the regions a common-area subroutine can be called
# from. The PD image at 0x20000 is a separate program with its own copy of
# the same compiler runtime, so its readers are not this one and its tables
# are not in this address space.
MAIN_EC = ("common", "bank0", "bank1")

ENTRY_LEN = 3  # address_hi, address_lo, case value

# Entries read before giving up on finding the terminator. No table in this
# image comes close (the largest has 49), and the cap is what stops a
# phantom `lcall` site inside data from walking the whole region.
MAX_ENTRIES = 64

# Instructions decoded into a handler window before giving up. Only the last
# window needs it: every other one is bounded by the next target.
MAX_BODY_INSNS = 64

RET_OPCODES = (0x22, 0x32)  # ret, reti

# The table ec/annotations/bank-call-audit.md section 9 is about, as the file
# offset of the `lcall` that precedes it.
SITE_0X8038 = 0x08035

MOV_DPTR = 0x90


def find_readers(d: bytes):
    """File offsets in the main EC image whose bytes open with the
    stack-pointer-to-table prologue."""
    out = []
    for name, lo, hi, base, _ in REGIONS:
        if name not in MAIN_EC:
            continue
        for i in range(lo, hi - len(READER_PROLOGUE)):
            if d[i:i + len(READER_PROLOGUE)] == READER_PROLOGUE:
                out.append(i)
    return out


def reader_call_sites(d: bytes, reader_runtime: int):
    """Every `lcall <reader>` *byte* in the main EC image, with frame
    evidence. A byte scan, with the over-count bank-call-audit.md section 1
    describes: the same three bytes occur inside data and as operand bytes
    of other instructions, so a site is a candidate until its table decodes."""
    want = bytes((LCALL, reader_runtime >> 8, reader_runtime & 0xFF))
    out = []
    for name, lo, hi, base, _ in REGIONS:
        if name not in MAIN_EC:
            continue
        for i in range(lo, hi - len(want)):
            if d[i:i + len(want)] == want:
                onto, over = converges_from(d, i)
                out.append({"file_offset": i, "region": name,
                            "runtime": runtime_addr(i, True),
                            "frame_onto": onto, "frame_over": over})
    return out


def decode_table(d: bytes, off: int):
    """Decode the inline table at file offset `off`.

    Returns a dict with the entries, the terminator, the default address and
    the file offset one past the table, or None if the bytes do not reach a
    terminator inside MAX_ENTRIES."""
    region, lo, _, _ = region_of(off, True)
    entries = []
    i = off
    while len(entries) <= MAX_ENTRIES:
        if i + ENTRY_LEN > len(d):
            return None
        target = (d[i] << 8) | d[i + 1]
        if target == 0:
            if i + ENTRY_LEN + 2 > len(d):
                return None
            return {
                "file_offset": off,
                "region": region,
                "runtime": runtime_addr(off, True),
                "entries": entries,
                "terminator_offset": i,
                "default": (d[i + 2] << 8) | d[i + 3],
                "default_offset": i + 2,
                "end": i + 4,
            }
        entries.append({"file_offset": i, "runtime": runtime_addr(i, True),
                        "target": target, "case": d[i + 2]})
        i += ENTRY_LEN
    return None


def malformed(d: bytes, tbl) -> list:
    """The ways `tbl` fails to read as a table, as a list of reasons -- empty
    for a well-formed one. Each check is a property the compiler's own output
    has and a run of arbitrary data generally does not."""
    bad = []
    if not tbl["entries"]:
        bad.append("no entries")
        return bad
    cases = [e["case"] for e in tbl["entries"]]
    if cases != sorted(cases) or len(set(cases)) != len(cases):
        bad.append("case values not strictly ascending")
    region = tbl["region"]
    for target in [e["target"] for e in tbl["entries"]] + [tbl["default"]]:
        if offset_for_runtime(target, region) is None:
            bad.append(f"0x{target:04X} does not resolve from {region}")
    end_runtime = runtime_addr(tbl["end"], True)
    if end_runtime not in [e["target"] for e in tbl["entries"]]:
        bad.append(f"the byte after the table (0x{end_runtime:04X}) is not one "
                   "of its own targets")
    return bad


def body_bounds(tbl):
    """{target: end file offset} for each entry, bounding a handler at the
    next target *by address*. A reading window, not a decoded function
    boundary: a handler that falls through into the next one gets the same
    window as one that does not."""
    stops = sorted({e["target"] for e in tbl["entries"]} | {tbl["default"]})
    out = {}
    for target in stops:
        nxt = next((s for s in stops if s > target), None)
        here = offset_for_runtime(target, tbl["region"])
        end = offset_for_runtime(nxt, tbl["region"]) if nxt else None
        out[target] = (here, end)
    return out


def body_summary(d: bytes, tbl, target: int):
    """What the window at `target` names: its first instruction, the XDATA
    addresses its `mov dptr,#imm16` loads hold, and the subroutines it calls.

    The walk is disasm8051.py's linear one, so it reads a branch's
    displacement as an instruction and keeps going -- fine for listing the
    addresses a window names, useless as a control-flow trace. It stops at
    the next target or at the first `ret`, whichever comes first, so a body
    with an early return is under-read rather than run on into whatever
    follows it."""
    here, end = body_bounds(tbl)[target]
    xdata, calls = [], []
    first = None
    for i, raw, text in decode(d, here, MAX_BODY_INSNS, target):
        if first is None:
            first = text
        if end is not None and i >= end:
            break
        if raw[0] == MOV_DPTR:
            xdata.append((raw[1] << 8) | raw[2])
        elif raw[0] == LCALL:
            calls.append((raw[1] << 8) | raw[2])
        elif raw[0] in RET_OPCODES:
            break
    return {"first_insn": first, "xdata": sorted(set(xdata)),
            "calls": sorted(set(calls))}


def print_table(d: bytes, tbl) -> None:
    end_runtime = runtime_addr(tbl["end"], True)
    print(f"table at file 0x{tbl['file_offset']:05X} "
          f"({tbl['region']} runtime 0x{tbl['runtime']:04X})")
    print(f"  {len(tbl['entries'])} entries of {ENTRY_LEN} bytes, "
          f"file 0x{tbl['file_offset']:05X}-0x{tbl['terminator_offset'] - 1:05X}")
    print(f"  terminator 0x{d[tbl['terminator_offset']]:02X}"
          f"{d[tbl['terminator_offset'] + 1]:02X} at file "
          f"0x{tbl['terminator_offset']:05X} (an address field of 0x0000)")
    print(f"  default 0x{tbl['default']:04X} at file 0x{tbl['default_offset']:05X}")
    print(f"  table ends at file 0x{tbl['end']:05X} (runtime 0x{end_runtime:04X})")
    bad = malformed(d, tbl)
    print("  well-formed" if not bad else "  MALFORMED: " + "; ".join(bad))
    print()
    print("  case  entry     target  stride  first instruction")
    prev = None
    for e in tbl["entries"]:
        summary = body_summary(d, tbl, e["target"])
        stride = "" if prev is None else f"0x{e['target'] - prev:02X}"
        print(f"  0x{e['case']:02X}  0x{e['file_offset']:05X}  "
              f"0x{e['target']:04X}  {stride:>6}  {summary['first_insn']}")
        prev = e["target"]
    print()


def print_bodies(d: bytes, tbl) -> None:
    print("  what each window names (linear decode, not a control-flow trace):")
    for e in tbl["entries"]:
        s = body_summary(d, tbl, e["target"])
        print(f"    0x{e['target']:04X} case 0x{e['case']:02X}  "
              f"xdata {' '.join(f'0x{a:04X}' for a in s['xdata'])}")
        print(f"                     calls "
              f"{' '.join(f'0x{a:04X}' for a in s['calls']) or '-'}")
    s = body_summary(d, tbl, tbl["default"])
    print(f"    0x{tbl['default']:04X} default   "
          f"xdata {' '.join(f'0x{a:04X}' for a in s['xdata'])}")
    print()


def print_readers(d: bytes, readers, sites) -> None:
    print(f"reader search: {len(readers)} subroutine(s) in the main EC image open "
          f"`{READER_PROLOGUE.hex(' ')}`")
    for off in readers:
        print(f"  file 0x{off:05X} runtime 0x{runtime_addr(off, True):04X} "
              f"({region_of(off, True)[0]})")
    for immediate in (0x8038, 0x803A):
        want = bytes((MOV_DPTR, immediate >> 8, immediate & 0xFF))
        hits = [i for i in range(len(d) - 3) if d[i:i + 3] == want]
        print(f"  `mov dptr,#0x{immediate:04X}` byte sites file-wide: {len(hits)}")
    print(f"  {len(sites)} `lcall` byte site(s) name the reader")
    print()


def census(d: bytes, sites):
    """Every candidate call site with its table, decoded and checked."""
    out = []
    for site in sites:
        tbl = decode_table(d, site["file_offset"] + 3)
        out.append((site, tbl, [] if tbl is None else malformed(d, tbl)))
    return out


def print_census(d: bytes, rows) -> None:
    good = [r for r in rows if r[1] is not None and not r[2]]
    print(f"{len(good)} of {len(rows)} candidate site(s) are followed by a "
          "well-formed table")
    print()
    print("  site      region  frame   entries  span              cases")
    for site, tbl, bad in rows:
        if tbl is None:
            print(f"  0x{site['file_offset']:05X}  {site['region']:<6}  "
                  f"{site['frame_onto']:2}/24   no terminator within "
                  f"{MAX_ENTRIES} entries")
            continue
        cases = [e["case"] for e in tbl["entries"]]
        span = f"0x{tbl['file_offset']:05X}-0x{tbl['end'] - 1:05X}"
        note = "" if not bad else "  MALFORMED: " + "; ".join(bad)
        print(f"  0x{site['file_offset']:05X}  {site['region']:<6}  "
              f"{site['frame_onto']:2}/24  {len(cases):7}  {span}  "
              f"0x{min(cases):02X}-0x{max(cases):02X}{note}")
    total = sum(t["end"] - t["file_offset"] for _, t, b in rows if t and not b)
    print()
    print(f"  {total} bytes of this image read as table data by this method")
    print()


def write_csv(d: bytes, tbl) -> None:
    """One row per entry, plus a `default` row, on stdout.

    No comment header: the columns are named after the `bank-*-targets.csv`
    ones so that whatever region map issue #50 lands can read this with
    `csv.DictReader` and fold it in or supersede it, and a leading `#` line
    would be the one thing that stops it."""
    w = csv.writer(sys.stdout)
    w.writerow(["index", "entry_file_offset", "entry_runtime", "target_runtime",
                "target_file_offset", "stride_from_prev", "target_first_insn",
                "notes"])
    prev = None
    for e in tbl["entries"]:
        s = body_summary(d, tbl, e["target"])
        w.writerow([
            f"0x{e['case']:02X}", f"0x{e['file_offset']:05X}",
            f"0x{e['runtime']:04X}", f"0x{e['target']:04X}",
            f"0x{offset_for_runtime(e['target'], tbl['region']):05X}",
            "" if prev is None else f"0x{e['target'] - prev:02X}",
            s["first_insn"],
            "xdata " + " ".join(f"0x{a:04X}" for a in s["xdata"]),
        ])
        prev = e["target"]
    s = body_summary(d, tbl, tbl["default"])
    w.writerow([
        "default", f"0x{tbl['default_offset']:05X}",
        f"0x{runtime_addr(tbl['default_offset'], True):04X}",
        f"0x{tbl['default']:04X}",
        f"0x{offset_for_runtime(tbl['default'], tbl['region']):05X}",
        "", s["first_insn"],
        "reached when no case matches; xdata "
        + " ".join(f"0x{a:04X}" for a in s["xdata"]),
    ])


# The reader, hand-decoded with `r2 -a 8051` against a make_bank_image.py
# bank-0 image and transcribed in ../annotations/bank-call-audit.md section 9.
# The whole entry layout above is read off these 38 bytes, so they are the
# oracle for it: if they change, nothing else in this file means what it says.
READER_SITE = (0x07151, 0x7151, bytes.fromhex(
    "d083d082f8e4937012740193700da3a393f8740193f5828883e4737402"
    "936860efa3a3a380df"))

# The 0x8038 table as section 9 reports it: (case, entry file offset, target).
TABLE_0X8038 = (
    (0x00, 0x08038, 0x8054), (0x01, 0x0803B, 0x8094), (0x02, 0x0803E, 0x80D7),
    (0x03, 0x08041, 0x811A), (0x04, 0x08044, 0x815D), (0x05, 0x08047, 0x819D),
    (0x06, 0x0804A, 0x81DF), (0x07, 0x0804D, 0x8231),
)

# Target-to-target deltas, which is the reason section 9 exists at all rather
# than a sentence in section 8: that section read a 0x43 stride off the first
# three entries, and it does not survive entry 3.
STRIDES_0X8038 = (0x40, 0x43, 0x43, 0x43, 0x40, 0x42, 0x52)

# The three sites ec/annotations/bank-call-targets.csv offers as independent
# corroboration that this table is entered as code, hand-decoded against the
# bank image each one lives in: (file offset of the instruction the scan's
# bytes actually belong to, its bytes, the scanned site inside them). All
# three are phantoms, which is what makes them worth pinning here.
CORROBORATION_SITES = (
    (0x08040, bytes.fromhex("02811a"), "the case byte of the 0x02 entry plus "
     "the address field of the 0x03 one"),
    (0x0AA17, bytes.fromhex("30e102" "8038"), "displacement of `jnb acc.1` plus "
     "the `sjmp 0xAA54` after it"),
    (0x165D1, bytes.fromhex("4002" "80d7"), "displacement of `jc` plus the "
     "`sjmp 0xE5AC` after it"),
)

DEFAULT_FIRMWARE = "../firmware/GMxMGxx_11.800"


def self_test(d: bytes) -> int:
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    readers = find_readers(d)
    check(readers == [READER_SITE[0]],
          f"exactly one stack-pointer-to-table reader in the main EC image, at "
          f"file 0x{READER_SITE[0]:05X} (got "
          f"{', '.join(f'0x{r:05X}' for r in readers) or 'none'})")

    off, rt, raw = READER_SITE
    check(d[off:off + len(raw)] == raw,
          f"its {len(raw)} bytes are as hand-decoded -- the entry layout is read "
          "off these and off nothing else")

    for immediate in (0x8038, 0x803A):
        want = bytes((MOV_DPTR, immediate >> 8, immediate & 0xFF))
        hits = [i for i in range(len(d) - 3) if d[i:i + 3] == want]
        check(not hits,
              f"no `mov dptr,#0x{immediate:04X}` anywhere in the file, so an "
              "immediate-DPTR scan finds this table zero times "
              f"(got {len(hits)})")

    tbl = decode_table(d, SITE_0X8038 + 3)
    check(tbl is not None and not malformed(d, tbl),
          "the table after the `lcall` at file 0x08035 decodes well-formed")
    if tbl is None:
        print("\nself-test FAILED")
        return 1

    got = tuple((e["case"], e["file_offset"], e["target"]) for e in tbl["entries"])
    check(got == TABLE_0X8038,
          f"{len(TABLE_0X8038)} entries, cases 0x00-0x07, targets "
          f"0x{TABLE_0X8038[0][2]:04X}-0x{TABLE_0X8038[-1][2]:04X} "
          f"(got {len(got)} entries)")

    check(tbl["terminator_offset"] == 0x08050 and tbl["default"] == 0x8274
          and tbl["end"] == 0x08054,
          "terminator at file 0x08050, default 0x8274, table ending at file "
          f"0x08054 (got 0x{tbl['terminator_offset']:05X}, "
          f"0x{tbl['default']:04X}, 0x{tbl['end']:05X})")

    strides = tuple(b[2] - a[2] for a, b in zip(TABLE_0X8038, TABLE_0X8038[1:]))
    check(strides == STRIDES_0X8038,
          "the target stride is 0x43 for the first three steps only and then "
          f"0x40/0x42/0x52 (got {', '.join(f'0x{s:02X}' for s in strides)})")

    # The correction section 9 makes, asserted as the two readings differing
    # on a specific byte rather than as prose: section 8 took file 0x08038 for
    # an `sjmp` whose displacement 0x54 targets 0x808E, and 0x808E is not an
    # entry of the table.
    sjmp_target = 0x803A + d[0x08039]
    check(d[0x08038] == 0x80 and sjmp_target == 0x808E
          and sjmp_target not in [e["target"] for e in tbl["entries"]],
          f"file 0x08038 reads as `sjmp 0x{sjmp_target:04X}` to a byte scan and "
          "0x808E is no entry of the decoded table -- the two readings disagree, "
          "which is what section 9 corrects")

    for off, raw, what in CORROBORATION_SITES:
        check(d[off:off + len(raw)] == raw,
              f"file 0x{off:05X} is `{raw.hex(' ')}` -- {what}")

    rows = census(d, reader_call_sites(d, rt))
    good = [r for r in rows if r[1] is not None and not r[2]]
    check(len(rows) == 15 and len(good) == 15,
          f"15 `lcall` byte sites name the reader and all 15 are followed by a "
          f"well-formed table (got {len(good)} of {len(rows)})")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--at", help="file offset of the `lcall` preceding a table, "
                                 "e.g. 0x0D148 (default: the 0x8038 table)")
    ap.add_argument("--all-tables", action="store_true",
                    help="decode the table after every call site naming the reader")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per entry on stdout instead of the tables")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the reader bytes, the 0x8038 table and the "
                         "call-site census against the committed image")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded decodes were taken from", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d)

    readers = find_readers(d)
    if len(readers) != 1:
        print(f"expected one table reader in the main EC image, found "
              f"{len(readers)} -- rerun --self-test", file=sys.stderr)
        return 1
    sites = reader_call_sites(d, runtime_addr(readers[0], True))

    site = int(args.at, 16) if args.at else SITE_0X8038
    tbl = decode_table(d, site + 3)

    if args.csv:
        if tbl is None:
            print(f"no table after file 0x{site:05X}", file=sys.stderr)
            return 1
        write_csv(d, tbl)
        return 0

    print_readers(d, readers, sites)
    if args.all_tables:
        print_census(d, census(d, sites))
        return 0
    if tbl is None:
        print(f"no table after file 0x{site:05X}")
        return 1
    print_table(d, tbl)
    print_bodies(d, tbl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
