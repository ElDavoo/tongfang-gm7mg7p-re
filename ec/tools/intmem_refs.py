#!/usr/bin/env python3
"""Census the direct internal-RAM byte references to a set of addresses.

`scan_refs.py` answers "how many `MOV DPTR,#addr` sites exist in this file",
which is an XDATA question. The internal-RAM half of the map has no equivalent
in the tree, and that gap is not academic: deciding whether a scheduler counter
is private to one routine is a question about who *writes a direct byte*, and
`MOV DPTR` cannot see a single one of them. This tool is that census.

**A byte list of the opcodes that name a direct address, and nothing else.**
Each entry is (opcode, direction, mnemonic) where direction is `read`, `write`
or `rmw`. An opcode absent from the table is not searched for: adding one is a
claim about the image's encoding and belongs in the same file as the reason,
next to the entry.

**What a hit is and is not.** This is an unframed byte scan, exactly as
`scan_refs.py` is: a two-byte pattern occurs just as readily in the middle of
some other instruction, in a jump table, or in a data region, and the scan
cannot tell those apart. So every site is reported with two labels rather than
being filtered, and neither label is a verdict:

  * the region it falls in, from `trace_xdata_refs.REGIONS` -- so a hit in the
    ITE8850-PD image is never silently added to a count about the EC;
  * `in_data_region`, the label `annotations/data-regions.yaml` gives it, and
    `scan_refs.py`'s own header is explicit that it is a LABEL, not a filter:
    `in_data_region=0` means "no site falls in a listed region", never "no site
    is a phantom".

A site no linear walk syncs onto is a *candidate* for a misframed read and
nothing more -- `disasm8051.converges_from`'s docstring says to read the pair,
not either half, and a site preceded by data it cannot decode into alignment
scores 0/24 without being wrong. The `frame` column carries that pair for the
same reason `bank-call-targets.csv` carries it, so a reader can adjudicate
rather than take the count. **Not to be filtered on automatically**: dropping
the low-scoring sites would make a future scan's zero look like absence, which
is the `docs/findings.md` §4c failure `scan_refs.py`'s header already cites.

**Not found by this method, never absent.** Indirect access -- a pointer built
in Rn/Rm, a computed address, a table read at a computed offset -- is invisible
here, as it is to `scan_refs.py`. A zero count means this scan found no
encoding of the address in these opcodes; it does not mean the address is
untouched. The bit-addressable forms (`setb`/`clr`/`mov`/carry ops) name *bits*,
so `d2 44` is a write to a bit of byte `0x28`, never to byte `0x44`; they are
deliberately not in OPCODES, because counting them as byte writes is the error
`docs/findings/charge-target-caller-chain.md`'s issue #1183 had to correct.

The region map comes from `trace_xdata_refs.REGIONS` and the decoder tables
from `disasm8051`, so neither is re-derived here.

Usage:
    python3 intmem_refs.py ../firmware/GMxMGxx_11.800 0x44 0x45
    python3 intmem_refs.py ../firmware/GMxMGxx_11.800 0x44 --writers
    python3 intmem_refs.py ../firmware/GMxMGxx_11.800 0x44 --self-test
"""
import argparse
import collections
import sys

from data_regions import load as load_data_regions, region_at
from disasm8051 import converges_from
from trace_xdata_refs import PD_MARKER, region_of, runtime_addr

# trace_xdata_refs.py regions that are the main EC firmware, as opposed to the
# PD image sharing the dump. The same split scan_refs.py makes, off the same
# table, because a file-wide total that adds the two together is the mistake
# that put LIGHTBAR_BAT_* on a register the EC never reads.
MAIN_EC_REGIONS = ("common", "bank0", "bank1")
PD_REGION = "pd-image"

# (opcode, direction, mnemonic) for every opcode whose operand names a direct
# internal-RAM byte. `rmw` reads and writes (the arithmetic and the exchanges),
# because "who writes this counter" is exactly the question that has to count
# them: a `b5 44` / `cjne a,0x44` neither writes 0x44 nor leaves it alone
# unless the compare fails.
#
# Deliberately absent, and each for a stated reason:
#   0x90 `mov dptr,#imm16` -- XDATA, and scan_refs.py owns that scan. The two
#     are not interchangeable: in this image `90 05 44` is a real instruction
#     naming XDATA 0x0544, and reading its two low bytes as `inc 0x44` is the
#     mistake docs/findings/scheduler-divide-down-cycle.md corrects.
#   0x02/0x12 `ljmp`/`lcall` -- a code address, not a data one. `02 c2 45` is
#     `ljmp 0xC245`, and its middle and last bytes are a `clr 0x45` to a scan
#     anchored one byte in.
#   0xd2/0xb2/0xc1/0x92/0xa2/0xa0/0xb0 -- bit-addressable, so they name a bit
#     of some byte rather than a byte. `0xc2` (CLR direct) is here instead: same
#     length as `0xc1`, different meaning, and reading one as the other is the
#     latent hole disasm8051.py's TEXTBOOK_BIT_SITES pair exists to catch.
#   the immediate forms (0x24 `add a,#imm`, 0x74 `mov a,#imm`, ...) -- an
#     immediate is not a reference to anything, so a scan for them would only
#     turn up the constants that happen to equal the address.
OPCODE_TABLE = (
    (0x05, "write", "inc  0x44"),
    (0x15, "rmw", "dec  0x44"),
    (0x25, "rmw", "add  a,0x44"),
    (0x35, "rmw", "addc a,0x44"),
    (0x45, "rmw", "orl  a,0x44"),
    (0x55, "rmw", "anl  a,0x44"),
    (0x65, "rmw", "xrl  a,0x44"),
    (0x75, "write", "mov  0x44,#imm"),
    (0x85, "copy", "mov  0x44,0xNN"),
    (0x95, "rmw", "subb a,0x44"),
    (0xA5, "unused", "reserved -- never an instruction"),
    (0xB5, "read", "cjne a,0x44,rel"),
    (0xC2, "write", "clr  0x44"),
    (0xC5, "rmw", "xch  a,0x44"),
    (0xD5, "rmw", "djnz 0x44,rel"),
    (0xE5, "read", "mov  a,0x44"),
    (0xF5, "write", "mov  0x44,a"),
)

# The mnemonic column is a *template* with the address already substituted, so
# an operator adding an entry writes the shape and the census renders it. Built
# from the table rather than stored twice, for the reason the two tables above
# would otherwise be a pair that can disagree.
TEMPLATES = {op: text.replace("0x44", "0x%02x") for op, _d, text in OPCODE_TABLE}

CAVEAT = (
    "Direct internal-RAM byte census over the opcodes in OPCODE_TABLE.\n"
    "Unframed byte scan: a hit may be a misframed read, a table entry, or\n"
    "data. 'frame' is converges_from's onto/over pair -- evidence about\n"
    "framing, not proof; read the pair, not either half. 'in_data_region' is\n"
    "a LABEL from annotations/data-regions.yaml, never a filter.\n"
    "Indirect access is invisible here. A zero means 'not found by this\n"
    "method', never 'absent' or 'private'. setb/clr/cpl/mov on 0xd2/0xb2/0xc1/\n"
    "0x92/0xa2 name a BIT address and are not counted as byte writes.\n"
)

# (file offset, opcode, address) triples the self-test pins, each transcribed
# from a disasm8051.py decode of the committed image. Kept as bytes and an
# address rather than as mnemonics so the assertion is against the image and
# not against this module's own rendering of it.
SELF_TEST = (
    # 0x0D81 `05 44` inc 0x44 -- the scheduler's own, and 24/24 onto it.
    (0x0D81, 0x05, 0x44, (24, 0)),
    # 0x0DC1 `f5 44` mov 0x44,a -- the scheduler's own clear, and 24/24 onto
    # it. It is not the only main-EC hit for 0x44: the others are the
    # scheduler's own reads and five sites that are not writes on their bytes,
    # each adjudicated in docs/findings/scheduler-divide-down-cycle.md.
    (0x0DC1, 0xF5, 0x44, (24, 0)),
    # 0x0DC7 `05 45` inc 0x45, and 0x0E0E `f5 45` mov 0x45,a: the two writes to
    # the second counter, both in the same routine.
    (0x0DC7, 0x05, 0x45, (24, 0)),
    (0x0E0E, 0xF5, 0x45, (24, 0)),
    # 0x0B0AC: the `05 44` the issue read as a second `inc 0x44`. The bytes
    # are `e0 30 02 05 44 04 f0 80` -- a `movx a,@dptr`, a `jnb`, then `orl
    # a,#0x04`. The `05` is the jnb's displacement and the `44` is the orl's
    # opcode, and 0 of 24 anchors land on the pair. This is the misframing
    # docs/findings/scheduler-divide-down-cycle.md corrects, pinned so the
    # correction cannot be quietly undone by a future scan that still sees the
    # bytes.
    (0x0B0AC, 0x05, 0x44, (0, 24)),
    # 0x12E66 and 0x13540: the two `05 44` pairs the issue read as bank-1
    # `inc 0x44`. Both are `90 05 44` = `mov dptr,#0x0544` -- an XDATA
    # address, which is a different address space from an internal-RAM byte
    # and is scan_refs.py's question rather than this one's. 1 of 24 and 0 of
    # 24 anchors agree.
    (0x12E66, 0x05, 0x44, (1, 23)),
    (0x13540, 0x05, 0x44, (0, 24)),
    # 0x16434: `45 45`, a `orl a,0x45` at 24 of 24 -- the frame score a reader
    # would most take as settled, and the sharpest illustration of why it
    # cannot be taken alone. The bytes are `03 44 44 03 45 45 03 46 46 05`, a
    # run of repeated single-byte values that a linear walk steps through
    # cleanly because every one of them is a 1- or 2-byte instruction. It sits
    # in the gap between bank1/E3B5.asm and bank1/E490.asm, in no committed
    # listing. This is the bank0,D091 standing warning, and it is why the
    # frame column is a pair a reader adjudicates rather than a filter.
    (0x16434, 0x45, 0x45, (24, 0)),
)


def pd_verified(data: bytes) -> bool:
    """Whether the dump carries the PD image's marker at its own offset.

    Checked rather than assumed, so a different dump whose 0x20000 region is
    something else gets labelled `unknown` by region_of() and counted in
    neither column -- the same guard scan_refs.py carries.
    """
    off, magic = PD_MARKER
    return data[off:off + len(magic)] == magic


def scan(data: bytes, addrs, verified: bool):
    """addr -> [ (file offset, opcode, direction, frame) ] for every hit.

    Every site is kept, including the ones whose frame score says a linear walk
    would not land on them, and including the `0xa5` reserved opcode. A census
    that dropped either would report a number a reader could not audit, and the
    drop is the call that turns "not found by this method" into "absent".
    """
    wanted = set(addrs)
    hits = collections.defaultdict(list)
    for op, direction, _text in OPCODE_TABLE:
        for i in range(len(data) - 1):
            if data[i] != op or data[i + 1] not in wanted:
                continue
            off = i
            hits[data[i + 1]].append(
                (off, op, direction, converges_from(data, off)))
    for lst in hits.values():
        lst.sort()
    return hits


def render(data, addrs, hits, regions, verified) -> None:
    for a in addrs:
        sites = hits.get(a, [])
        ec = sum(1 for off, _o, _d, _f in sites
                 if region_of(off, verified)[0] in MAIN_EC_REGIONS)
        pd = sum(1 for off, _o, _d, _f in sites
                 if region_of(off, verified)[0] == PD_REGION)
        verdict = "referenced" if ec else (
            "referenced in the PD image ONLY, not by the EC" if pd
            else "NOT FOUND BY THIS METHOD (see the caveat above)")
        labelled = sum(1 for off, _o, _d, _f in sites
                       if region_at(regions, off) is not None)
        # Trailing, so the columns agent-gates.sh's smoke test greps for
        # (`refs=`, `referenced`) keep their shape.
        print(f"0x{a:02X}  refs={len(sites):<3} ec={ec:<3} pd={pd:<3} "
              f"in_data_region={labelled}  {verdict}")
        for off, op, direction, (onto, over) in sites:
            name, _lo, base, _how = region_of(off, verified)
            rt = runtime_addr(off, verified)
            rt_s = f"0x{rt:04X}" if rt is not None else "unmapped"
            print(f"    file 0x{off:05X}  {name:<8} runtime {rt_s:<8} "
                  f"{TEMPLATES[op] % a:<18} {direction:<5} "
                  f"frame={onto}/{over}")


def self_test(data: bytes, verified: bool) -> int:
    """Pin the SELF_TEST triples against the image, the table and the framing.

    Three things are asserted per row and the distinction matters: the image
    holds `op addr` at the offset, the scan *finds* that row when asked for
    that address (so the table and the pattern agree), and converges_from
    reports the pinned pair. A row whose bytes are not in the image fails; a
    row the scan stops finding fails; a row whose framing moved fails. The last
    is what keeps the 0x0B0AC misframing reading honest -- if a future image
    change made those bytes a real `inc 0x44`, the 0/24 would be the signal and
    this test is where it surfaces.
    """
    bad = 0
    for off, op, addr, frame in SELF_TEST:
        got = data[off:off + 2]
        want = bytes((op, addr))
        if got != want:
            bad += 1
            print(f"  !   file 0x{off:05X} is `{got.hex(' ')}`, expected "
                  f"`{want.hex(' ')}`")
            continue
        hits = scan(data, [addr], verified)
        rows = [s for s in hits.get(addr, []) if s[0] == off and s[1] == op]
        if not rows:
            bad += 1
            print(f"  !   the scan did not report file 0x{off:05X} as "
                  f"`{TEMPLATES[op] % addr}`")
            continue
        got_frame = rows[0][3]
        if got_frame != frame:
            bad += 1
        ok = got_frame == frame
        print(f"  {'ok ' if ok else '!  '} file 0x{off:05X} is "
              f"`{got.hex(' ')}` = `{TEMPLATES[op] % addr}`, scan finds it, "
              f"frame {got_frame[0]}/{got_frame[1]} "
              f"(expected {frame[0]}/{frame[1]})")

    # The table is a closed list and this is what holds it to one: a row added
    # for an opcode that is not in the 8051's direct-address map, or a row
    # dropped from it, changes what a zero means and the census would not say so.
    for op, direction, _text in OPCODE_TABLE:
        if direction not in ("read", "write", "rmw", "copy", "unused"):
            bad += 1
            print(f"  !   opcode 0x{op:02X} has direction {direction!r}, which "
                  f"is not one of read/write/rmw/copy/unused")
        if 0xA5 != op and direction == "unused":
            bad += 1
            print(f"  !   opcode 0x{op:02X} is marked unused but is not the "
                  f"one reserved opcode")
    covered = {op for op, _d, _t in OPCODE_TABLE}
    # 0x00 `nop` and 0xff are the byte values an unframed scan is most likely
    # to invent a hit out of; neither names a direct address, so a row for
    # either would be a claim the map does not support.
    for op in (0x00, 0xFF):
        if op in covered:
            bad += 1
            print(f"  !   opcode 0x{op:02X} names no direct address and should "
                  f"not be in the table")

    # The bit-addressable forms are the error this tool exists partly to avoid,
    # so the exclusion is asserted rather than left to the docstring: the same
    # two bytes read as a bit write and as a byte write name different bytes.
    for op in (0xD2, 0xB2, 0xC1, 0x92, 0xA2, 0xA0, 0xB0):
        if op in covered:
            bad += 1
            print(f"  !   opcode 0x{op:02X} is bit-addressable and must not be "
                  f"in the table")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the image or "
              "with this module's own table")
    else:
        print(f"self-test passed: {len(SELF_TEST)} site(s) pinned against the "
              f"image, and all {len(OPCODE_TABLE)} table rows carry a direction "
              f"the renderer knows")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?",
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("addrs", nargs="*",
                    help="one or two hex digit direct addresses, e.g. 0x44")
    ap.add_argument("--writers", action="store_true",
                    help="print only the sites that write or rmw the address")
    ap.add_argument("--self-test", action="store_true",
                    help="pin the table against the committed image")
    args = ap.parse_args()

    if not args.firmware:
        ap.error("give a firmware image and one or more addresses, or --self-test")

    data = open(args.firmware, "rb").read()
    verified = pd_verified(data)

    if args.self_test:
        return self_test(data, verified)

    try:
        addrs = [int(a, 16) for a in args.addrs]
    except ValueError:
        ap.error("addresses are hex, e.g. 0x44")
    for a in addrs:
        if not 0 <= a <= 0xFF:
            ap.error(f"0x{a:x} is not a direct byte address (0x00-0xFF)")
    if not addrs:
        ap.error("give at least one address, e.g. 0x44")

    print(CAVEAT)
    if not verified:
        print(f"note: no {PD_MARKER[1].decode()!r} marker at file "
              f"0x{PD_MARKER[0]:05X} -- sites in 0x20000-0x2FFFF belong to an "
              "unidentified region and are counted in neither ec= nor pd=\n")

    hits = scan(data, addrs, verified)
    if args.writers:
        # Filtering is opt-in and never changes a count printed above: a
        # read/write split is a question about direction, which is a different
        # question from whether there are any sites at all.
        for a in addrs:
            for off, op, direction, frame in hits.get(a, []):
                if direction == "read":
                    continue
                name = region_of(off, verified)[0]
                print(f"0x{a:02X}  file 0x{off:05X}  {name:<8} "
                      f"{TEMPLATES[op] % a:<18} {direction:<5} "
                      f"frame={frame[0]}/{frame[1]}")
        return 0

    render(data, addrs, hits, load_data_regions(), verified)
    return 0


if __name__ == "__main__":
    sys.exit(main())
