#!/usr/bin/env python3
"""Which byte the two `pop`s at a `?C?CCASE` helper receive, measured over the
whole population of the dispatch tables that helper walks.

`../../docs/findings/pd-inline-arg-trampoline.md` §3 settles the order of the
two `pop`s in the PD image's `0x104D` from a comparison -- 40 distinct
four-byte values against 427 -- and says in the same paragraph that adopting
that column is an inference rather than a measurement. This tool supplies a
second witness that is not that comparison: `ec/annotations/bank-call-audit.md`
§9 reads the order off the Keil `switch` helper at `common,0x7151` in the
*main* EC by looking at where its `mov` instructions put the bytes, and this
runs that reading over every table the helper walks rather than over the one
§9 read entry by entry.

**Two different byte orders, and the census needs both.** §9 settles the order
of the two bytes *inside* an entry -- offset 0 is the high address byte --
which is a property of `0x7166`/`0x7168` and not a distributional claim. The
order the `pop`s themselves are in is a different question, one link further
back: it decides whether `DPTR` points at the table at all. So the default mode
prints two blocks and keeps them apart:

  * **the entry order**, `malformed()` re-run with each entry's two address
    bytes exchanged. Decisive -- every table that passes one way fails the
    other -- and it is the reading §9 records.
  * **the base order**, `decode_table()` re-run at the byte-swapped return
    address. This is the link from the entry order back to the `pop`s, and it
    is where the sharpest statement lives: under the swap, DPTR either does not
    resolve from the caller's own region at all or finds no `00 00` terminator
    within `decode_index_table.MAX_ENTRIES`.

**The resolution count alone is the weaker of the two tests, and the tool says
so rather than quoting the one that flatters it.** `malformed()` asks that every
target resolve inside the caller's own region, and for a *banked* caller that
window is `0x8000`-`0xFFFF`, which most byte-swapped addresses still land in --
so on the bank0 tables the resolution counts barely move. The clause that
separates cleanly is the fall-through one: the byte after the table must be one
of its own targets, and exchanging the two address bytes changes which address
that is. Both clauses are in the same verdict, and the verdict is what the
census reports per site.

**Arm locality is a proxy and is labelled one.** How many arms land in the same
256-byte page as their own table base is suggestive and not a test: a `switch`
arm may legitimately point forward into the next page or backward into the
previous one, so the rate is reported per reading and never as a fraction of
every arm. `bank-call-audit.md` §10.1 records thirty entries of these fifteen
tables sharing a target with another entry of the same table, which is the same
caution in another form.

**A decode is not a measurement of what executes.** Nothing here runs on
hardware, no register is read, no `status:` in `../annotations/registers.yaml`
moves. Even a clean result says the byte-swapped reading does not fit these
tables. It does not say which routines execute, and it does not carry over to
code that dispatches through `DPTR` to somewhere other than a switch table.

Usage:
    python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800 --simulate
    python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800 \
        --simulate --at 0x0D148
    python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800 --pd-siblings
    python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import os
import sys

from decode_index_table import (ENTRY_LEN, MAX_ENTRIES, MAIN_EC, REGION_SETS,
                                SITE_0X8038, decode_table, find_readers,
                                lcalled_readers, malformed, reader_call_sites)
from disasm8051 import OPCODE_LEN, mnemonic, relative_target
from trace_xdata_refs import (PD_MARKER, offset_for_runtime, region_of,
                              runtime_addr)

HERE = os.path.dirname(os.path.abspath(__file__))
FIRMWARE = f"{HERE}/../firmware/GMxMGxx_11.800"

# The two readings of the two address bytes of an entry, as the census names
# its columns. The first is what `0x7166`/`0x7168` read off the reader's own
# `mov` destinations and what `decode_index_table.decode_table()` builds; the
# second is the same pair exchanged, which is the reading that would follow from
# the two `pop`s taking the return address the other way round, computed here
# rather than argued against.
READINGS = ("address big-endian", "byte-swapped")

# The bare pop pair this tool's population is counted over, and the helper it
# opens at the main EC's one site. Both are held as bytes and re-derived from
# the image rather than spelled as addresses, so a different dump re-checks the
# population instead of inheriting this one's answer.
POP_PAIR = bytes.fromhex("d083d082")
POP_PAIR_SWAPPED = bytes.fromhex("d082d083")

# The reader's own claims about which byte goes where, as offsets into its 38
# bytes -- what `--self-test` holds against the image. Held as (offset, bytes,
# what) rather than as a whole hex string so a failure names the instruction
# that moved rather than the routine that did not.
READER_ENTRY_BYTE = (
    (0x10, bytes.fromhex("93f8"), "`movc a,@a+dptr ; mov r0,a` at 0x7161 puts "
                               "offset 0 of the entry in R0"),
    (0x12, bytes.fromhex("740193f582"), "`mov a,#1 ; movc a,@a+dptr ; mov dpl,a` "
                                        "at 0x7163 puts offset 1 in DPL"),
    (0x17, bytes.fromhex("8883"), "`mov dph,r0` at 0x7168 takes it from R0, so "
                                  "offset 0 is the high address byte"),
)
# The walk's stride and its loop head: three `inc dptr` then a relative branch
# back to 0x7156, which is the `clr a` the entry scan starts at.
READER_STRIDE = (0x21, bytes.fromhex("a3a3a380df"), 0x05)
# How many `inc dptr` the stride is made of, so the check above counts
# instructions rather than bytes -- the same three as `ENTRY_LEN` is a
# coincidence of this routine, not the property, and ENTRY_LEN is the width of
# an entry rather than a count of instructions.
STRIDE_INSNS = 3

# `simulate()` executes the opcodes above and nothing else. Confined to this
# routine's own bytes and deliberately short: an opcode missing here raises
# rather than being skipped, so the transcript cannot quietly execute a partial
# program and report a dispatch that never happened.
SIM_LEN = {0xA3: 1, 0x60: 2, 0x68: 1, 0x70: 2, 0x73: 1, 0x74: 2, 0x80: 2,
           0x88: 2, 0x93: 1, 0xD0: 2, 0xE4: 1, 0xF5: 2, 0xF8: 1}
SIM_REGS = ("A", "R0", "DPL", "DPH")
SIM_SFR = {"A": 0xE0, "DPL": 0x82, "DPH": 0x83, "R0": 0xF8}
# The PC-relative forms this routine uses. Separate from SIM_LEN because the
# two sets answer different questions -- `BRANCHES` is which opcodes need
# `relative_target()`, `SIM_LEN` is which it can execute at all -- and an
# opcode in one and not the other is a bug in this file rather than a reason
# to guess a target.
BRANCHES = (0x60, 0x70, 0x80)
# Steps before the walk is called not-found. A `switch` table on this image is
# under fifty entries, so a run that gets here is a selector that matches
# nothing from a base that was never a table -- which is a result, and is
# reported as one rather than as a hang.
SIM_STEPS = 512
# Instructions printed before the transcript is elided. A run that dispatches
# inside the table's first entry is shorter than this and prints whole; a run
# that walks off is not, and gets its head, an elision line and its tail.
SIM_HEAD = 22


def byte_swapped(addr: int) -> int:
    """`addr` with its two bytes exchanged. The whole of what "the other
    reading" means here, so that a caller cannot swap one byte by accident and
    call it the other reading."""
    return ((addr & 0xFF) << 8) | (addr >> 8)


def arms_of(tbl, reading):
    """Every address the reader would dispatch to under `reading`: each entry's
    target and then the default. One list per table per reading, so the two
    columns are computed by the same code path and differ only in the swap."""
    targets = [e["target"] for e in tbl["entries"]] + [tbl["default"]]
    return targets if reading == READINGS[0] else [byte_swapped(a) for a in targets]


def swapped_table(tbl):
    """`tbl` with the two bytes of every entry address and of the default
    exchanged -- what `decode_table()` returns if the reader had put offset 0
    in DPL. A copy rather than a mutation: `malformed()` reads the case bytes
    and the span too, and those are the same under both readings, so the two
    verdicts differ only in the address field."""
    out = dict(tbl)
    out["entries"] = [dict(e, target=byte_swapped(e["target"]))
                      for e in tbl["entries"]]
    out["default"] = byte_swapped(tbl["default"])
    return out


def unresolved(tbl, reading) -> int:
    """How many of the table's arms do not resolve from the caller's own region
    under `reading`. One of `malformed()`'s three clauses, reported on its own
    because it is the clause a reader is most likely to over-read -- see the
    module docstring."""
    return sum(1 for a in arms_of(tbl, reading)
               if offset_for_runtime(a, tbl["region"]) is None)


def local_arms(tbl, reading) -> tuple:
    """(arms in their own table's 256-byte page, arms) under `reading`.

    A proxy, and reported as a rate against the number of *entries* rather than
    of entries-plus-default: the default is the fall-through a selector that
    matches nothing lands on, and counting it with the arms would let a table
    with one arm and a far-away default read better than one with eight."""
    targets = [byte_swapped(e["target"]) if reading == READINGS[1]
               else e["target"] for e in tbl["entries"]]
    page = tbl["runtime"] >> 8
    return sum(1 for t in targets if (t >> 8) == page), len(targets)


def readers(d: bytes) -> list:
    """Every `?C?CCASE` reader in the main EC an `lcall` names, with its sites.

    Discovered rather than addressed, so a dump whose reader moved, or a second
    one appearing, shows up here instead of being missed. On the committed image
    the list is one reader with the fifteen sites `bank-call-audit.md` §10
    tabulates."""
    out = []
    for reader in lcalled_readers(d, MAIN_EC):
        out.append((reader, reader_call_sites(d, reader["runtime"], MAIN_EC)))
    return out


def census(d: bytes) -> list:
    """[(reader, site, table, bad)] for every table of every reader, in file
    order. `bad` is `malformed()`'s verdict under `READINGS[0]`; the other
    reading's is computed where it is reported, so a caller holding a table can
    ask for either without the census having already discarded one."""
    out = []
    for reader, sites in readers(d):
        for site in sites:
            tbl = decode_table(d, site["file_offset"] + OPCODE_LEN[0x12])
            out.append((reader, site, tbl,
                        [] if tbl is None else malformed(d, tbl)))
    return out


def verdict_cell(bad: list) -> str:
    """`malformed()`'s reasons as one short table cell.

    A count by reason rather than the reasons themselves: the swapped column's
    reasons name every arm that fails to resolve, and printing them all turns
    the table into a wall of addresses that says "many" once per table without
    saying anything about which clause is separating. The first site's reasons
    are spelled out below the table, which is where a reader can see that the
    count is doing real work."""
    if not bad:
        return "ok"
    tally = collections.Counter(
        "unresolvable" if "does not resolve" in why else
        "fall-through" if "the byte after the table" in why else why
        for why in bad)
    return " ".join(f"{n} {why}" for why, n in sorted(tally.items()))


def well_formed_under(d: bytes, tbl, reading) -> list:
    """`malformed()`'s reasons under `reading`, empty for a well-formed table.
    The one place the other reading's verdict is computed, so the census's
    per-site column, its totals and `--self-test`'s comparison cannot disagree
    about it. The other reading's table is a copy with the two address bytes
    exchanged, so the case bytes and the span are identical either way and only
    the address field differs."""
    return malformed(d, swapped_table(tbl) if reading == READINGS[1] else tbl)


def verdict(d: bytes, tbl, reading) -> str:
    """`verdict_cell()` of `well_formed_under()`."""
    return verdict_cell(well_formed_under(d, tbl, reading))


def print_census(d: bytes, rows) -> None:
    """Both readings over every table, then the totals that are a property of
    the committed image rather than of this repository."""
    for reader, sites in readers(d):
        print(f"reader 0x{reader['runtime']:04X} ({reader['shape']}, "
              f"file 0x{reader['file_offset']:05X}), named by "
              f"{len(sites)} `lcall` byte site(s)\n")

    print("The entry order -- `malformed()` under each reading.  The left-hand "
          "column is\nwhat `decode_index_table.decode_table()` builds and what "
          "bank-call-audit.md §9 records;\nadopting it over the other is the "
          "reading, not this tool's finding.\n")
    width = max(len(r) for r in READINGS)
    print(f"  {'site':<8}  {'region':<6}  {'entries':>7}  "
          + "  ".join(f"{r:>{width}}" for r in READINGS))
    for reader, site, tbl, _ in rows:
        if tbl is None:
            print(f"  0x{site['file_offset']:05X}  {site['region']:<6}  "
                  f"{'-':>7}  not established by this method under either "
                  "reading:\n           no `00 00` terminator within "
                  f"{MAX_ENTRIES} entries of file "
                  f"0x{site['file_offset'] + OPCODE_LEN[0x12]:05X}.  That is a "
                  "finding about\n           `decode_index_table`, not a zero "
                  "here, and it is reported rather than rounded away")
            continue
        print(f"  0x{site['file_offset']:05X}  {site['region']:<6}  "
              f"{len(tbl['entries']):7}  "
              + "  ".join(f"{verdict(d, tbl, r):>{width}}" for r in READINGS))

    print("\nArms not resolving from the caller's own region, one count per "
          "reading -- `malformed()`'s\nfirst clause on its own, because it is "
          "the clause a reader is most likely to over-read.\n"
          "For a banked caller that window is 0x8000-0xFFFF and most swapped "
          "addresses land\ninside it, so on the bank0 tables this column stays "
          "at zero for both readings; the\nfall-through clause above is what "
          "separates them there.\n")
    print(f"  {'site':<8}  {'region':<6}  "
          + "  ".join(f"{r:>{width}}" for r in READINGS))
    for reader, site, tbl, _ in rows:
        if tbl is None:
            continue
        print(f"  0x{site['file_offset']:05X}  {site['region']:<6}  "
              + "  ".join(f"{unresolved(tbl, r):>{width}}" for r in READINGS))

    print("\nArm locality, a PROXY: entries landing in the same 256-byte page as "
          "their own table\nbase.  A `switch` arm may legitimately point "
          "forward or backward, so this is a\nrate and not a test, and it is "
          "printed beside the verdict rather than in place of it.\n")
    print(f"  {'site':<8}  " + "  ".join(f"{r:>{width}}" for r in READINGS))
    for reader, site, tbl, _ in rows:
        if tbl is None:
            continue
        cells = [f"{n}/{d}" for n, d in (local_arms(tbl, r) for r in READINGS)]
        print(f"  0x{site['file_offset']:05X}  "
              + "  ".join(f"{c:>{width}}" for c in cells))

    good = {r: sum(1 for _, _, tbl, _ in rows if tbl is not None
                   and not well_formed_under(d, tbl, r))
            for r in READINGS}
    print(f"\n  {len(rows)} candidate site(s); well-formed: "
          + "  ".join(f"{good[r]} of {len(rows)}" for r in READINGS))
    print("  A well-formed verdict is corroboration, not proof: a run of data "
          "can pass all\n  three clauses without being a table "
          "(bank-call-audit.md §10.2).")

    # One site's reasons in full, because the cells above are counts. Without
    # it "6 unresolvable" is a number with nothing behind it, and the whole
    # point of the second column is what those addresses are.
    example = next((tbl for _, _, tbl, _ in rows if tbl is not None), None)
    if example is not None:
        site = next(s for r, s, t, _ in rows if t is example)
        first = example["entries"][0]
        print(f"\nWhat the second column is counting, in full, for the table at "
              f"file 0x{example['file_offset']:05X}\n(the `lcall` at 0x"
              f"{site['file_offset']:05X}, {len(example['entries'])} entries):\n")
        for a in arms_of(example, READINGS[0])[:4]:
            print(f"    entry target 0x{a:04X} -> 0x{byte_swapped(a):04X}")
        print(f"  default      0x{example['default']:04X} -> "
              f"0x{byte_swapped(example['default']):04X}")
        print(f"  first entry case 0x{first['case']:02X} at file "
              f"0x{first['file_offset']:05X}, unchanged by either reading -- "
              "the case byte is\n  the third byte of an entry and the swap "
              "only exchanges the two address bytes in front of it\n")
        for why in well_formed_under(d, example, READINGS[1]):
            print(f"    byte-swapped: {why}")

    print("\nThe base order -- the same walk started at the byte-swapped return "
          "address.\nThis is the link from the entry order back to the two "
          "`pop`s: under the swap, DPTR\nnames the address the `lcall` pushed "
          "with its bytes exchanged rather than the table.\n")
    print(f"  {'site':<8}  {'region':<6}  {'return':<8}  {'swapped':<8}  "
          f"{'entries found':>13}  case values")
    for reader, site, tbl, _ in rows:
        ret = site["runtime"] + OPCODE_LEN[0x12]
        swapped = byte_swapped(ret)
        off = offset_for_runtime(swapped, site["region"])
        if off is None:
            found, cases = "unresolvable", f"0x{swapped:04X} does not resolve " \
                                           f"from {site['region']}"
        else:
            other = decode_table(d, off)
            if other is None:
                found = "none"
                cases = f"no `00 00` terminator within {MAX_ENTRIES} entries"
            else:
                found = str(len(other["entries"]))
                cs = [e["case"] for e in other["entries"]]
                ascending = cs == sorted(cs) and len(set(cs)) == len(cs)
                cases = f"0x{min(cs):02X}-0x{max(cs):02X}, strictly ascending" \
                        if cs and ascending else "not strictly ascending"
        print(f"  0x{site['file_offset']:05X}  {site['region']:<6}  "
              f"0x{ret:04X}    0x{swapped:04X}    {found:>13}  {cases}")

    print(f"\nA count of 0 entries found is 'no table is there by this method' "
          "and not\n'no table exists', and `unresolvable` is the region rule "
          "`trace_xdata_refs.offset_for_runtime`\nstates rather than a "
          "measurement of this one: a target at or above 0x8000 is a bank, and "
          "a common-area\nroutine is not told which bank is mapped.  Neither "
          "is a claim that the swap is impossible; both\nare claims that it "
          "does not fit these tables.")

    print("\nThe two blocks answer two questions and the second is not a "
          "re-run of the\nfirst.  The first is which byte of an entry is the "
          "high one -- §9 reads that off\n`0x7166`/`0x7168` directly.  The "
          "second is whether the `pop`s put DPTR on the table\nat all, which is "
          "the step from that reading back to the order of the two `pop`s.  "
          "The\nfirst is settled by the bytes; the second is what this "
          "population adds to §3 of the PD\nwrite-up, and it is a second "
          "witness to the *reading* -- a decode over committed\ntables, which "
          "says nothing about which routines execute.")


class Machine:
    """The four registers this routine touches, as bytes.

    A dict and named accessors rather than a byte array indexed by SFR number,
    because the transcript's whole point is that a reader can see which register
    each value is in -- and `mov dph,r0` taking the high byte from R0 three
    instructions after `movc` put it there is exactly the step a hand-trace
    skips. This is the executable version of the check.
    """

    def __init__(self, a, r0, dpl, dph):
        self.v = {"A": a, "R0": r0, "DPL": dpl, "DPH": dph}

    def rd(self, direct: int) -> int:
        return self.v[_sfr(direct, "read")]

    def wr(self, direct: int, val: int) -> None:
        self.v[_sfr(direct, "write")] = val & 0xFF

    def dptr(self) -> int:
        return (self.v["DPH"] << 8) | self.v["DPL"]

    def row(self) -> str:
        return " ".join(f"{k}=0x{self.v[k]:02X}" for k in SIM_REGS)


def _sfr(direct: int, what: str) -> str:
    """The register name behind a directly addressed byte, or a loud refusal.

    A refusal rather than a default, because this routine is supposed to touch
    only A, R0, DPL and DPH; an unmodelled direct reaching the default would
    make the transcript a claim about a program it did not run.
    """
    for name, addr in SIM_SFR.items():
        if addr == direct:
            return name
    raise SystemExit(f"simulate(): {what} of unmodelled direct 0x{direct:02x}; "
                     "this routine is supposed to touch only A, R0, DPL and DPH")


def simulate(d: bytes, region: str, entry: int, pops: list, machine: Machine):
    """(the address dispatched to, the transcript, the stopping reason) for the
    reader entered at `entry` with `pops` on the stack.

    `pops` is what the two `pop`s take off it, in order, and it is a parameter
    rather than a derivation because that is the question. The MCS-51 `lcall`
    pushes the low byte first, so the high byte is on top of the stack and
    `pop DPH` then `pop DPL` hands back the return address in order; exchanging
    the two leaves DPTR on the byte-swapped address, and whether this image's
    tables fit that swapped DPTR is the thing being measured. Note the direction
    of that: the swap is the reading that departs from the architecture, and
    `boot_xdata_sites.py`'s `_push_return` implements the push order this
    documents.

    `movc a,@a+dptr` reads through `offset_for_runtime()` from `region`, the
    same region rule the rest of this repository uses, so a banked caller reads
    its own bank and a common-area one is refused anything at or above 0x8000
    rather than handed a guess.

    The transcript is returned rather than printed, because the two runs are of
    very different lengths -- one dispatches within the table's first entry, the
    other walks off into the image -- and how much of it to show is a decision
    about the report rather than about the routine. Every executed instruction
    is in it either way; `print_simulate()` chooses which of them a reader sees.

    A dispatch of None is a result, not a failure: the walk ran `SIM_STEPS`
    instructions without reaching either a matching case or a `00 00`, which is
    what a selector that matches nothing looks like when the base was never a
    table."""
    stack = list(pops)
    pc = entry
    lines = []
    for _ in range(SIM_STEPS):
        op = d[pc]
        if op not in SIM_LEN:
            raise SystemExit(f"simulate(): unmodelled opcode 0x{op:02X} at "
                             f"0x{pc:04X}; add it to SIM_LEN or the transcript "
                             "stops being a claim about the whole routine")
        n = SIM_LEN[op]
        b1 = d[pc + 1] if n > 1 else None
        next_pc = (pc + n) & 0xFFFF
        # Every branch here is PC-relative, so the target is the displacement
        # added to the *next* instruction's address -- the decoder's own
        # arithmetic, so a transcript that branched somewhere else would mean
        # the tool had re-derived the 8051 wrongly.
        rel = relative_target(op, d[pc + n - 1], pc) if op in BRANCHES else None
        taken = None
        stop = None
        if op == 0xA3:
            machine.v["DPL"] = (machine.v["DPL"] + 1) & 0xFF
        elif op == 0x60:
            taken = rel if machine.v["A"] == 0 else None
        elif op == 0x68:
            # `XRL A,Rn` likewise names its register in the opcode's low three
            # bits; `68` is `xrl a,r0` with no operand byte at all.
            machine.v["A"] ^= machine.rd(SIM_SFR["R0"] + (op & 0x07))
        elif op == 0x70:
            taken = rel if machine.v["A"] != 0 else None
        elif op == 0x74:
            machine.v["A"] = b1
        elif op == 0x80:
            taken = rel
        elif op == 0x88:
            # `MOV direct,Rn` carries the register in the low three bits of the
            # opcode itself and the direct byte after it -- 8051, not a reading
            # of the operand -- so `88 83` is `mov dph,r0` and takes R0 from
            # the opcode, not from `b1`.
            machine.wr(b1, machine.rd(SIM_SFR["R0"] + (op & 0x07)))
        elif op == 0x93:
            off = offset_for_runtime(machine.dptr(), region)
            if off is None:
                stop = (f"`movc a,@a+dptr` read through DPTR=0x"
                        f"{machine.dptr():04X}, which does not resolve from "
                        f"{region}")
                break
            if off + machine.v["A"] >= len(d):
                stop = (f"`movc a,@a+dptr` read through DPTR=0x"
                        f"{machine.dptr():04X}, past the end of the dump")
                break
            machine.v["A"] = d[off + machine.v["A"]]
        elif op == 0xD0:
            machine.wr(b1, stack.pop(0))
        elif op == 0xE4:
            machine.v["A"] = 0
        elif op == 0xF5:
            machine.wr(b1, machine.v["A"])
        elif op == 0xF8:
            machine.v["R0"] = machine.v["A"]
        elif op == 0x73:
            lines.append(_step(d, pc, machine))
            return machine.dptr(), lines, "jumped"
        lines.append(_step(d, pc, machine))
        pc = taken if taken is not None else next_pc
    else:
        stop = (f"the walk reached no dispatch in {SIM_STEPS} instructions and "
                "left DPTR at "
                f"0x{machine.dptr():04X}")
    return None, lines, stop


def _step(d: bytes, pc: int, machine: Machine) -> str:
    """One transcript line for the instruction at `pc`, after it has run."""
    n = OPCODE_LEN[d[pc]]
    return (f"  0x{pc:04X}  {d[pc:pc + n].hex(' '):<7}  "
            f"{mnemonic(d, pc, pc):<18}  {machine.row()}  "
            f"DPTR=0x{machine.dptr():04X}")


def print_transcript(lines: list, head: int) -> None:
    """`lines`, with the middle elided when it is long, and the elision said
    out. An abridged transcript that does not say it was abridged is a
    transcript of a shorter program."""
    for line in lines[:head]:
        print(line)
    if len(lines) <= head:
        return
    print(f"  ... {len(lines) - head} more instruction(s), the same "
          f"{len(SIM_LEN)} opcodes over and over ...")
    for line in lines[-3:]:
        print(line)


def print_simulate(d: bytes, site_off: int, region: str, entry: int) -> None:
    """The transcript `--simulate` prints: `0x7151`'s own bytes over one
    committed table, under both push orders, differing in nothing but which
    stack byte the first `pop` takes."""
    tbl = decode_table(d, site_off + OPCODE_LEN[0x12])
    if tbl is None:
        print(f"no table after file 0x{site_off:05X}", file=sys.stderr)
        raise SystemExit(1)
    ret = runtime_addr(site_off, True) + OPCODE_LEN[0x12]
    selector = tbl["entries"][0]["case"]
    print(f"reader 0x{entry:04X} entered with its return address 0x{ret:04X} on "
          f"the stack\nand a selector of 0x{selector:02X} in A.  The table is "
          f"at file 0x{tbl['file_offset']:05X}, runtime\n0x{tbl['runtime']:04X} "
          f"({tbl['region']}), {len(tbl['entries'])} entries of "
          f"{ENTRY_LEN} bytes, first case 0x{selector:02X} "
          f"at 0x{tbl['entries'][0]['target']:04X}.\n")
    for label, pops in ((f"the two `pop`s take 0x{ret >> 8:02X} then "
                         f"0x{ret & 0xFF:02X}, so DPTR = the return address",
                         [ret >> 8, ret & 0xFF]),
                        (f"the two `pop`s take 0x{ret & 0xFF:02X} then "
                         f"0x{ret >> 8:02X}, so DPTR = the byte-swapped "
                         f"0x{byte_swapped(ret):04X}",
                         [ret & 0xFF, ret >> 8])):
        print("=" * 78)
        print(label)
        print("=" * 78)
        machine = Machine(selector, 0x22, 0x33, 0x44)
        jumped, lines, why = simulate(d, region, entry, list(pops), machine)
        print_transcript(lines, SIM_HEAD)
        print()
        if jumped is None:
            print(f"  {len(lines)} instruction(s) executed and {why}.")
        elif jumped == tbl["entries"][0]["target"]:
            print(f"  {len(lines)} instruction(s) executed; `clr a ; "
                  f"jmp @a+dptr` transfers to 0x{jumped:04X}, which is case "
                  f"0x{selector:02X} of\n  the table this call carries -- a "
                  "handler that exists.")
        else:
            print(f"  {len(lines)} instruction(s) executed; `clr a ; "
                  f"jmp @a+dptr` transfers to 0x{jumped:04X}, which is not a "
                  f"target of\n  this table (case 0x{selector:02X} would be "
                  f"0x{tbl['entries'][0]['target']:04X}).")
        print()


def print_pd_siblings(d: bytes) -> None:
    """The `pop dph ; pop dpl` population across both images, its mirror in the
    other order, and what is already established about each part of it.

    A population and a pointer, not a second analysis. The PD-side readers that
    walk a table are `pd_index_tables.py`'s subject and their tables are decoded
    there; `../../docs/findings/table-reader-spellings.md` reads the shapes. What
    this mode adds is the count, the per-target `lcall` figure, and the mirrored
    order's own population -- so a reader asking "why is the oracle the main EC's
    `0x7151` and not one of these" has the answer in front of them.

    A zero `lcall` count is 'not found by this method' and never 'there is no
    caller': a dispatch through a table is not a `12 xx xx` byte sequence, so
    this scan cannot see it. The main EC's own nine zero-`lcall` candidates are
    the same case, and `../../docs/findings/pd-inline-arg-trampoline.md` §7
    already applies the caveat to the EC-side zero."""
    pd_verified = d[PD_MARKER[0]:PD_MARKER[0] + len(PD_MARKER[1])] == PD_MARKER[1]
    both = REGION_SETS["both"]
    found = find_readers(d, both)

    def occurrences(pat):
        return [i for i in range(len(d) - len(pat) + 1)
                if d[i:i + len(pat)] == pat]

    hits = occurrences(POP_PAIR)
    mirror = occurrences(POP_PAIR_SWAPPED)
    by_region = lambda pat: ", ".join(
        f"{n} in {r}" for r, n in sorted(collections.Counter(
            region_of(i, pd_verified)[0] for i in occurrences(pat)).items()))

    print(f"`{POP_PAIR.hex(' ')}` occurs {len(hits)} time(s) in this dump, by a "
          f"byte scan over the whole file;\n{by_region(POP_PAIR)}.\n")
    print(f"  {'file':<8}  {'runtime':<8}  {'region':<9}  {'tier':<6}  shape"
          "                        `lcall` sites")
    by_site = {r["file_offset"]: r for r in found}
    for off in hits:
        reader = by_site.get(off)
        shape = reader["shape"] if reader else "(no enumerated shape)"
        tier = ("tier 2" if reader and reader["walks_table"] else "tier 1") \
            if reader else "-"
        if reader:
            n = len(reader_call_sites(d, reader["runtime"], both))
            calls = str(n) + ("" if n else "  (not found by this method)")
        else:
            calls = "not a reader candidate"
        print(f"  0x{off:05X}  0x{runtime_addr(off, pd_verified):04X}    "
              f"{region_of(off, pd_verified)[0]:<9}  {tier:<6}  {shape:<26}"
              f"  {calls}")

    print(f"\n`0x21052` is the second `pop` pair inside the PD image's `0x104D` "
          "helper -- the one\n`../../docs/findings/pd-inline-arg-trampoline.md` "
          "§3 is about, and the routine whose\ntwo `pop`s are the question this "
          "whole tool exists to give a second witness to.\n`0x2113E` and "
          "`0x21157` are neither readers nor dispatchers: both pop three more\n"
          "bytes into `A`/`r1`/`r2`/`r3` after the pair, so they are an "
          "argument-unpacking shape.")

    print(f"\nThe mirrored order, `{POP_PAIR_SWAPPED.hex(' ')}`, occurs "
          f"{len(mirror)} time(s) in the same\ndump; "
          f"{by_region(POP_PAIR_SWAPPED)}.  It is one of the enumerated shapes "
          "in\n`decode_index_table.PROLOGUE_SHAPES` as much as the first is, so "
          "the shape column\nabove is that tool's search rather than a second "
          "one.  In the main EC those\nmatches are the `pop dpl ; pop dph` half "
          "of a `push dph ; push dpl` the same routine\nissued a few bytes "
          "earlier around one XDATA read -- a DPTR saved and restored rather\n"
          "than a return address -- and `decode_index_table.py --self-test` "
          "holds each of them\nas that byte pattern.  That is a negative result "
          "about the other order's *readers*,\nnot evidence about which byte a "
          "`pop` receives, and it is the committed tool's\nfinding rather than "
          "this one's.")

    print("\nThe PD-side readers that walk a table are `pd_index_tables.py`'s "
          "subject and\n`../../docs/findings/table-reader-spellings.md` reads "
          "the shapes; two of them walk\nfour- and six-byte entries rather than "
          "this family's three, which is that file's\n`reader_stride` column.  "
          "Their own layouts are a separate investigation and this mode does\n"
          "not touch them.  Nothing here is a claim that any of these routines "
          "executes, or about\nwhich byte its `pop`s take: `0x7151`'s is the "
          "question this tool measures, and the\nrest are named so a reader "
          "knows what was available and not taken.")


def self_test(d: bytes) -> int:
    """The byte shapes the whole argument rests on, re-derived from the image
    rather than inherited -- so a different dump checks them."""
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    readers_ = readers(d)
    check(len(readers_) == 1,
          f"exactly one `?C?CCASE` reader in the main EC is named by an "
          f"`lcall` (got {len(readers_)})")
    if not readers_:
        print("\nself-test FAILED")
        return 1
    reader, sites = readers_[0]
    check(d[reader["file_offset"]:reader["file_offset"] + len(POP_PAIR)]
          == POP_PAIR,
          f"file 0x{reader['file_offset']:05X} opens `{POP_PAIR.hex(' ')}`, the "
          "pair whose order this tool measures")

    base = reader["file_offset"]
    for rel, raw, what in READER_ENTRY_BYTE:
        check(d[base + rel:base + rel + len(raw)] == raw,
              f"its offset +0x{rel:02X} (runtime 0x{base + rel:04X}) is "
              f"`{raw.hex(' ')}` -- {what}")

    rel, raw, head = READER_STRIDE
    stride, branch = raw[:-2], raw[-2:]
    check(d[base + rel:base + rel + len(stride)] == stride
          and len(stride) == STRIDE_INSNS,
          f"its offset +0x{rel:02X} (runtime 0x{base + rel:04X}) is "
          f"`{stride.hex(' ')}`, three `inc dptr`")
    # `relative_target` is the decoder's own, so the loop head is resolved the
    # way every other PC-relative site in this repository is rather than by
    # arithmetic written here -- and it takes the displacement as the
    # instruction's *last* byte, which is the form the 3-byte `sjmp` family
    # needs and the one a hand-written subtraction gets wrong.
    at = base + rel + len(stride)
    target = relative_target(d[at], d[at + OPCODE_LEN[0x80] - 1], at)
    check(d[at:at + len(branch)] == branch and target == base + head,
          f"which `sjmp`s back to runtime 0x{base + head:04X}, the `clr a` the "
          f"entry scan starts at (got 0x{target:04X})")

    check(OPCODE_LEN[0x12] == 3,
          f"`lcall` is {OPCODE_LEN[0x12]} bytes in `disasm8051.OPCODE_LEN`, the "
          "width the table offset is derived from")

    rows = census(d)
    check(all(tbl is not None for _, _, tbl, _ in rows),
          f"every one of the {len(rows)} `lcall` sites is followed by a table "
          "reaching a `00 00` terminator")
    check(sum(1 for _, _, _, bad_ in rows if bad_) == 0,
          f"and {sum(1 for _, _, _, bad_ in rows if not bad_)} of "
          f"{len(rows)} are well-formed under the address-big-endian reading")

    # The falsifiable half, and the reason the census is worth anything: the
    # two columns have to come out different, or the tool is measuring nothing.
    swapped_good = sum(1 for _, _, tbl, _ in rows if tbl is not None
                       and not well_formed_under(d, tbl, READINGS[1]))
    check(swapped_good < len(rows),
          f"and {swapped_good} of {len(rows)} under the byte-swapped reading, "
          "so the two columns are computed differently")

    check(all(byte_swapped(byte_swapped(a)) == a for a in (0x8038, 0x0054, 0xFFFF)),
          "`byte_swapped()` is its own inverse on these addresses")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=FIRMWARE,
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--simulate", action="store_true",
                    help="execute the reader's own bytes over one committed "
                         "table under both push orders, instead of the census")
    ap.add_argument("--at", default=f"0x{SITE_0X8038:05X}",
                    help="file offset of the `lcall` preceding the table "
                         "--simulate runs over (default: the 0x8038 table)")
    ap.add_argument("--pd-siblings", dest="pd_siblings", action="store_true",
                    help="the `pop dph ; pop dpl` population across both "
                         "images, as counts and a pointer")
    ap.add_argument("--self-test", dest="self_test", action="store_true",
                    help="re-check the byte shapes the census's two readings "
                         "rest on, against the image")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded decodes were taken from", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d)
    if args.pd_siblings:
        print_pd_siblings(d)
        return 0
    if args.simulate:
        reader = readers(d)
        if not reader:
            print("no `?C?CCASE` reader in the main EC is named by an `lcall`; "
                  "rerun --self-test", file=sys.stderr)
            return 1
        entry = reader[0][0]["runtime"]
        site_off = int(args.at, 16)
        print_simulate(d, site_off, region_of(site_off, True)[0], entry)
        return 0

    rows = census(d)
    if not rows:
        print("no `?C?CCASE` reader in the main EC is named by an `lcall`; "
              "rerun --self-test", file=sys.stderr)
        return 1
    print_census(d, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
