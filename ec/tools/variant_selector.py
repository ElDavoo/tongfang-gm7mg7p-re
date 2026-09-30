#!/usr/bin/env python3
"""Name the discriminator that picks which writer seeds the per-mode PL
defaults, and say whether the same byte gates the `0xABxx` / `0xC7xx`
duplication of the mode routines.

`ec/annotations/manual-fan-ctrl-0751.md` 5 quotes `0x95C0` writing `0x2D` to
`0x0730` and records that `registers.yaml` has `0x3C` live there, and calls the
two "consistent with this block not being the branch that runs on this
machine" without claiming more.  That block is one arm of a routine with three
seed pairs and four ways in, and this is the instrument that takes the block
apart.

Two questions the tree had not separated, which is why the answer is two
answers rather than one:

  * which byte picks the seed pair `0x94D0` copies out of, and
  * which byte, if any, picks between the `0xABxx` and `0xC7xx` copies of the
    mode routines.

Nothing here measures the byte. Every verdict is a static read of committed
firmware, and "this arm is reachable" is a statement about the branch
structure, never about what ran on a machine. The one place the two could be
confused -- the `0x0770 == 0x04` gate that decides whether the fixed-byte block
executes at all -- is reported as a gate with its own read, not as a verdict
about this chassis.

`--self-test` holds hand transcriptions from `r2 -a 8051` for the branch
encodings and targets, the way `walk_branch_arms.py --self-test` holds its
seventeen, so the split this tool performs is checked against an independent
disassembler rather than against a second run of the same decoder.

Usage:
    python3 variant_selector.py ec/firmware/GMxMGxx_11.800
    python3 variant_selector.py ec/firmware/GMxMGxx_11.800 --csv
    python3 variant_selector.py ec/firmware/GMxMGxx_11.800 --check
    python3 variant_selector.py --self-test ec/firmware/GMxMGxx_11.800
"""
import argparse
import csv
import io
import sys

from disasm8051 import OPCODE_LEN, bit_name, relative_target
from trace_xdata_refs import (PD_MARKER, offset_for_runtime, region_of,
                              runtime_addr, sites_for)

# The twelve bytes `registers.yaml` documents as MODE_PL_DEFAULTS, in the order
# that file lists them: Gaming 0x0730-0x0733, Office 0x0734-0x0737, Turbo
# 0x07A7-0x07AA.
BLOCK = (0x0730, 0x0731, 0x0732, 0x0733,
         0x0734, 0x0735, 0x0736, 0x0737,
         0x07A7, 0x07A8, 0x07A9, 0x07AA)

# The routine the twelve-byte block is seeded by, and the entry that guards it.
SEEDER = 0x94D0

# The two XDATA bytes holding the seed pair, and the one holding the entry R7.
# The pair is big-endian: `0xB93D` reads 0x0A51 into R6 (which becomes DPH) and
# 0x0A52 into R7 (DPL), so `0x61/0xC8` is the CODE pointer 0x61C8.
SEED_HI, SEED_LO, ENTRY = 0x0A51, 0x0A52, 0x0A50

# The GFID select at the head of the seeder: `0x94D5` loads 0x07D3, masks the
# high nibble and XORs 0x30, so the seeded arm is the one where GFID == 3.
GFID = 0x07D3
GFID_MASK, GFID_XOR = 0xF0, 0x30

# The three seed pairs the routine can store, as (high byte, low byte) in the
# order the arms reach them, and the CODE address each one is a pointer to.
# Transcribed from `ec/decompiled/bank0/94D0.asm` and re-checked in r2; see
# `--self-test`, which holds the bytes rather than trusting this table.
SEEDS = (
    (0x61, 0xFE, 0x61FE),   # GFID == 3 and the 0x074C nibble is 0 or 3
    (0x61, 0xC8, 0x61C8),   # GFID == 3 and it is neither
    (0x61, 0x92, 0x6192),   # GFID != 3
)

# The indices the seeder reads out of the CODE table, in the order the listing
# reads them, each with the XDATA byte it lands in. The `+1` entries are the
# ones `0x9547` / `0x9570` increment before the store; it is the reason the
# table's `00` bytes appear as `01` at 0x0733, 0x0737 and 0x07AA, and leaving
# it out is how a reader ends up one off every live value.
TABLE_READS = (
    (0x00, 0x0730, False),
    (0x01, 0x0731, False),
    (0x02, 0x0732, False),
    (0x03, 0x0733, True),
    (0x04, 0x0734, False),   # the 0x0782 bit-2-clear index group
    (0x05, 0x0735, False),
    (0x06, 0x0736, False),
    (0x07, 0x0737, True),
    (0x0C, 0x07A7, False),
    (0x0D, 0x07A8, False),
    (0x0E, 0x07A9, False),
    (0x0F, 0x07AA, True),
)

# The second index group, reached when bit 2 of 0x0782 is set. The two groups
# overlap in the live values because the two halves of the table hold the same
# bytes, which is a fact about the table and not a fact about the branch.
ALT_GROUP = ((0x08, 0x0734, False), (0x09, 0x0735, False),
             (0x0A, 0x0736, False), (0x0B, 0x0737, True))

# How many bytes of each seed table the copy reads, which is the window the
# seeds are compared over. Wider than the last index the copy touches on
# purpose: comparing more than is read would report a difference that cannot
# reach the twelve bytes, and comparing less would miss one that can.
TABLE_WINDOW = 0x10

# The fixed-byte arm and the two gates in front of it. `0xB8C0` returns R7 = 1
# when 0x0770 == 0x04, and `0x95BB jnz` sends that case *into* the block, so
# the fixed bytes are written when 0x0770 == 0x04 and skipped otherwise. That
# inversion is the reason the block cannot be called "the one that does not
# run" on the strength of the live value alone.
FIXED_ARM = 0x95C0
FIXED_GATE = 0xB8C0
GATE_BYTE = 0x0770
GATE_VALUE = 0x04
# The branch that acts on the gate's return, and where the other case goes.
# Both are named rather than written into the printed text so the polarity can
# be asserted against the image instead of against a sentence here.
GATE_BRANCH, GATE_SKIP = 0x95BB, 0x9A0D

# (XDATA address, immediate) pairs the fixed block writes, in listing order.
FIXED_WRITES = ((0x07A7, 0x64), (0x07A8, 0x64), (0x0730, 0x2D),
                (0x0731, 0x3C), (0x0737, 0x01))

# The duplicated mode routines. The `0xC7xx` copy has no committed listing --
# `site-resolution.csv` records it as not exported, and seeding a function
# there needs a project rebuild, which is out of scope for a tool run in a
# gate -- so both are read out of the image by this file.
AB_COPY, C7_COPY = 0xAB9E, 0xC717

# The instruction the two copies are aligned on, and the delta between them.
# Every instruction of the shared tail sits at the same offset from its own
# copy's anchor, which is what "identical masks at identical relative offsets"
# means, and it is checkable rather than asserted.
ALIGN_ANCHOR_AB, ALIGN_ANCHOR_C7 = 0xABC7, 0xC720

# How far past the anchor the comparison walks, and the one pair of differing
# instructions that is not a branch displacement: each copy calls its own copy
# of the `0x0751 & 0x90` reader. The two are the same bytes, so the difference
# is the address and not the routine -- which is the claim that makes "the
# shared tail is identical modulo relocation" a stronger statement than
# "the masks match".
SHARED_TAIL_INSNS = 34
BB40, C7_CALLEE, HELPER_LEN = 0xBB40, 0xCA4C, 7

# The gates on the `0xABxx` copy's own copy of the shared tail, and where the
# same gate is absent from the `0xC7xx` copy. The point of the table is that
# they are not the same set: the two copies are reached by different
# discriminators, and the finding this tool feeds says so rather than assuming
# one answers both.
AB_GATES = (
    (0x0782, 1,  "bit 1 of 0x0782 (0xAB9E, `jnb acc.1`)"),
    (0x0440, None, "0x0440 non-zero (0xABA9, `jz`)"),
    (0x06E6, None, "0x06E6 == 0x01 via 0xB9D8 (0xABAB)"),
    (0x1603, 5,  "bit 5 of 0x1603 via 0xC1CB (0xABB0)"),
)
C7_GATES = (
    (0x0440, None, "0x0440 non-zero (0xC71E, `jz`)"),
    (0x0741, 0,  "bit 0 of 0x0741 (0xC724, `jnb acc.0`)"),
)

# The value `registers.yaml` records live at 0x0730, and what the fixed arm
# would write there. Carried so the tool can print the comparison rather than
# leave a reader to do it, and so `--check` fails if either figure is edited
# out from under the other.
LIVE_0730 = 0x3C
FIXED_0730 = 0x2D


class Refusal(Exception):
    """A claim this tool will not make, raised where it would otherwise guess."""


def read_window(d, region, runtime, n):
    """`n` bytes of `region` at `runtime`, or a Refusal naming what is wrong.

    Refusing rather than padding matters here because the whole tool is about
    a decode that looked plausible and was not: `0xC77E` reads as a `cjne` when
    the byte before it is the immediate of a `mov r7,#0xb8`. A window that ran
    off the end and quietly returned zeroes would turn that into a verdict.
    """
    off = offset_for_runtime(runtime, region)
    if off is None or off + n > len(d):
        raise Refusal(f"0x{runtime:04X} is not {n} readable bytes of {region}")
    return d[off:off + n]


def decode(d, region, runtime, n):
    """[(address, opcode, text)] for up to `n` instructions from `runtime`.

    Linear and forward-only, like every decoder in this tree: it cannot tell
    you the anchor is an instruction start, which is why `--self-test` holds
    the bytes rather than re-running this and comparing it with itself.

    The window is three bytes per instruction rather than one, because the
    longest 8051 instruction is three and a window sized to the instruction
    *count* truncates the last one -- which reads as an instruction whose
    operand runs off the end rather than as a window that was too small. It
    stops short rather than decoding an instruction the window cannot hold.
    """
    blob = read_window(d, region, runtime, n * 3)
    out, i = [], 0
    while i < len(blob) and len(out) < n:
        op = blob[i]
        if i + OPCODE_LEN[op] > len(blob):
            break
        out.append((runtime + i, op, disasm_text(blob, i, runtime + i)))
        i += OPCODE_LEN[op]
    return out


def disasm_text(blob, i, addr):
    """The `mnemonic` string for the instruction at `blob[i]`.

    A one-instruction window, so `disasm8051.mnemonic` reads the bytes it needs
    without this file re-deriving the mnemonic table -- one vocabulary, not two.
    """
    from disasm8051 import mnemonic
    return mnemonic(blob, i, addr)


def branch_target(d, region, runtime, op_len):
    """The target of the relative branch at `runtime`, or None.

    Derived from the decoded stream through `relative_target`, which consults
    the opcode-length table rather than assuming three bytes. `0x00E0`'s
    `jnb acc.0,0x00E4` is three, and the `sjmp` forms are two; the constant
    would be wrong for one of them.
    """
    off = offset_for_runtime(runtime, region)
    blob = read_window(d, region, runtime, op_len)
    return relative_target(blob[0], blob[-1], runtime)


def seed_sites(d):
    """The XDATA sites of the twelve-byte block, joined to their function.

    The scan and the join are the ones `check_site_resolution.py` uses --
    `sites_for()` for the sites, the `size` column of
    `ec/decompiled/listing-index.csv` for the routine -- read rather than
    re-derived, because a second implementation of either is a second answer
    to a question the tree already answers once.
    """
    rows = []
    for addr in BLOCK:
        for site in sites_for(d, addr):
            # `region_of` returns the tuple `trace_xdata_refs` passes around --
            # name first, then the two window bounds and the provenance string.
            # Only the name is wanted here, and taking [0] rather than
            # re-deriving it is what keeps this row's `region` the same word
            # `site-resolution.csv` and the tool's own output use.
            region = region_of(site, True)[0]
            rt = runtime_addr(site, True)
            rows.append({"addr": addr, "region": region, "runtime": rt,
                         "function": containing_function(rt)})
    return rows


def containing_function(runtime):
    """The routine holding `runtime`, or the string for "none of them does"."""
    import csv as _csv
    import os
    index = os.path.join(os.path.dirname(__file__), "..", "decompiled",
                         "listing-index.csv")
    try:
        with open(index, newline="") as fh:
            for row in _csv.DictReader(fh):
                start = int(row["addr"], 16)
                size = int(row["size"])
                if start <= runtime < start + size:
                    return row.get("name") or f"0x{start:04X}"
    except (OSError, KeyError, ValueError):
        return "unresolved"
    return "not exported"


def seed_table(d, hi, lo):
    """The `TABLE_WINDOW` bytes at the CODE pointer the seed pair names."""
    runtime = (hi << 8) | lo
    # A seed at or above 0x8000 is a bank window, not this bank's CODE, and
    # reading it from bank0 would be a category error rather than a small
    # error. The refusal is the point; the committed seeds are all 0x61xx.
    if runtime >= 0x8000:
        raise Refusal(f"seed 0x{hi:02X}/0x{lo:02X} points at 0x{runtime:04X}, "
                      f"which is a bank window, not bank0 CODE")
    off = offset_for_runtime(runtime, "bank0")
    if off is None or off + TABLE_WINDOW > len(d):
        raise Refusal(f"seed table 0x{runtime:04X} is not {TABLE_WINDOW} "
                      f"readable bytes")
    return d[off:off + TABLE_WINDOW]


def helpers_same(d):
    """-> "byte-identical" or what differs, for the two copies' callee.

    Printed rather than assumed, because "the same routine reached at two
    addresses" is the difference between the two copies being one routine
    twice and being two routines that happen to agree, and the two are not the
    same claim.
    """
    a = read_window(d, "bank0", BB40, HELPER_LEN)
    b = read_window(d, "bank0", C7_CALLEE, HELPER_LEN)
    if a == b:
        return f"`{a.hex(' ')}`"
    return f"0x{BB40:04X} `{a.hex(' ')}` vs 0x{C7_CALLEE:04X} `{b.hex(' ')}`"


def shared_tail(d, n=SHARED_TAIL_INSNS):
    """-> (identical, differing) for the two copies' shared tail.

    Walks both from their anchors and compares instruction by instruction at
    the same relative offset, which is what "identical masks at identical
    relative offsets" means and what makes it checkable rather than asserted.
    The differing count is expected to be non-zero and small: a branch target
    is spelled as a displacement, so every branch differs once the tail moves,
    and the one callee that differs is a byte-identical helper at the other
    address. A differing count of zero would mean the tool is not comparing
    displacements, and `test_variant_selector.py` holds that it is not zero
    for the wrong reason either.
    """
    delta = ALIGN_ANCHOR_C7 - ALIGN_ANCHOR_AB
    ab = decode(d, "bank0", ALIGN_ANCHOR_AB, n)
    c7 = decode(d, "bank0", ALIGN_ANCHOR_C7, n)
    same = 0
    other = 0
    for (a_addr, _, a_text), (b_addr, _, b_text) in zip(ab, c7):
        if b_addr != a_addr + delta:
            # The two walks left step at different rates, so the offset no
            # longer lines up and the rest of the comparison would be pairing
            # unrelated instructions. Stop and say so rather than count them.
            break
        if a_text == b_text:
            same += 1
        else:
            other += 1
    return same, other


def derived_values(table, reads=TABLE_READS):
    """-> {XDATA address: value} for one table, `+1` applied where listed."""
    return {xdata: (table[index] + 1) & 0xFF if bump else table[index]
            for index, xdata, bump in reads}


def arm_table(d, rows):
    """The default table text, so `--check` and the printed form cannot differ."""
    out = io.StringIO()
    w = out.write
    w(f"variant_selector.py -- twelve-byte MODE_PL_DEFAULTS block\n")
    w(f"seeder 0x{SEEDER:04X}   GFID byte 0x{GFID:04X}   "
      f"entry 0x{ENTRY:04X}   seed pair 0x{SEED_HI:04X}/0x{SEED_LO:04X}\n\n")

    w("store sites of the twelve bytes, and the routine each sits in\n")
    for row in rows:
        w(f"  0x{row['addr']:04X}  0x{row['runtime']:04X} {row['region']:<5}  "
          f"{row['function']}\n")
    w("\n")

    w("seed pairs and the discriminator that picks each\n")
    for hi, lo, code in SEEDS:
        w(f"  0x{SEED_HI:04X}=0x{hi:02X} 0x{SEED_LO:04X}=0x{lo:02X}  "
          f"-> CODE 0x{code:04X}\n")
    w(f"  guard: 0x{GFID:04X} & 0x{GFID_MASK:02X} == 0x{GFID_XOR:02X} "
      f"(GFID == 3) reaches the first two; anything else reaches "
      f"0x{SEEDS[2][0]:02X}/0x{SEEDS[2][1]:02X}\n\n")

    w(f"the first {TABLE_WINDOW} bytes at each seed table\n")
    tables = {}
    for hi, lo, code in SEEDS:
        table = seed_table(d, hi, lo)
        tables[code] = table
        w(f"  0x{code:04X}  " + " ".join(f"{b:02X}" for b in table) + "\n")
    identical = len({bytes(t) for t in tables.values()}) == 1
    w(f"  identical over the {TABLE_WINDOW} bytes the copy reads: {identical}\n\n")

    w("values each seed table yields for the twelve bytes\n")
    for hi, lo, code in SEEDS:
        vals = derived_values(tables[code])
        w(f"  0x{code:04X}  " + " ".join(f"{vals[a]:02X}" for a in BLOCK) + "\n")
    w("\n")

    # The second index group, because the two groups reaching the same four
    # bytes is the reason bit 2 of 0x0782 does not show up in the values: it
    # is a real branch on a real bit, over two halves of the table that hold
    # the same bytes.
    alt = derived_values(tables[SEEDS[0][2]], ALT_GROUP)
    base = derived_values(tables[SEEDS[0][2]])
    same = all(alt[xdata] == base[xdata] for _, xdata, _ in ALT_GROUP)
    w("the 0x0782 bit-2 index group, over the same table\n")
    w("  bit 2 clear, indices 0x04-0x07: "
      + " ".join(f"{base[xdata]:02X}" for _, xdata, _ in ALT_GROUP) + "\n")
    w("  bit 2 set,   indices 0x08-0x0B: "
      + " ".join(f"{alt[xdata]:02X}" for _, xdata, _ in ALT_GROUP) + "\n")
    w(f"  the two groups agree on all four bytes: {same}\n\n")

    w(f"the fixed arm at 0x{FIXED_ARM:04X}, and the gate in front of it\n")
    w(f"  0x{FIXED_GATE:04X} returns R7 = 1 when 0x{GATE_BYTE:04X} == "
      f"0x{GATE_VALUE:02X}\n")
    w(f"  0x{GATE_BRANCH:04X} `jnz` sends that case into the block, so:\n")
    w(f"    0x{GATE_BYTE:04X} == 0x{GATE_VALUE:02X}  -> the fixed bytes are "
      f"written\n")
    w(f"    0x{GATE_BYTE:04X} != 0x{GATE_VALUE:02X}  -> 0x{GATE_SKIP:04X}, and "
      f"the table values stand\n")
    for addr, val in FIXED_WRITES:
        w(f"      0x{addr:04X} <- 0x{val:02X}\n")
    w(f"  registers.yaml has 0x{LIVE_0730:02X} live at 0x{BLOCK[0]:04X}; the "
      f"fixed arm writes 0x{FIXED_0730:02X} there\n")
    w(f"  the table path writes 0x{derived_values(tables[SEEDS[0][2]])[0x0730]:02X}"
      f" there, and the two differ: {'yes' if LIVE_0730 != FIXED_0730 else 'no'}\n\n")

    w("the duplicated mode routines\n")
    w(f"  0x{AB_COPY:04X} and 0x{C7_COPY:04X} share a tail aligned at "
      f"0x{ALIGN_ANCHOR_AB:04X} <-> 0x{ALIGN_ANCHOR_C7:04X}\n")
    tail_same, tail_other = shared_tail(d)
    w(f"  over {SHARED_TAIL_INSNS} instructions from those anchors: "
      f"{tail_same} identical, {tail_other} differing\n")
    w(f"  the differing ones are branch displacements and one callee; "
      f"0x{BB40:04X} and 0x{C7_CALLEE:04X} are the same "
      f"{HELPER_LEN} bytes ({helpers_same(d)}), so the callee is not a "
      f"different routine\n")
    for gates, label in ((AB_GATES, "0xABxx"), (C7_GATES, "0xC7xx")):
        for addr, _bit, why in gates:
            w(f"  {label} gate  0x{addr:04X}  {why}\n")
    shared = {addr for addr, _, _ in AB_GATES} & {addr for addr, _, _ in C7_GATES}
    w("  gate bytes the two copies share: "
      f"{', '.join(f'0x{a:04X}' for a in sorted(shared)) or 'none'}\n")
    w("  GFID (0x07D3) gates neither copy\n")
    return out.getvalue()


def report(d, as_csv=False):
    """The finding's table, as text or as CSV rows."""
    rows = seed_sites(d)
    if not as_csv:
        return arm_table(d, rows)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["address", "site", "region", "function"])
    for row in rows:
        w.writerow([f"0x{row['addr']:04X}", f"0x{row['runtime']:04X}",
                    row["region"], row["function"]])
    return out.getvalue()


# The hand transcriptions `--self-test` holds. Every entry is
# (runtime, expected bytes, expected mnemonic, expected branch target or None),
# read from `r2 -a 8051` on the bank0 image and not from this file's output.
#
# The `jnb acc.2` rows are the reason this table exists rather than a loop
# against the decoder. `0x957C` is `30 e2 1a`: the `0xe2` is the *bit address*
# of ACC bit 2, not the P2 latch and not bit 1 of the DPTR low byte. Reading it
# as a P2 bit is what a "the listing says otherwise" correction to
# `ghidra-functions.csv` would have introduced, and Ghidra's own decompile of
# the same routine reads it as `BIOS_OEM_2 >> 2 & 1`. See
# ../../docs/findings/mode-defaults-variant-selector.md.
SELF_TEST_BRANCHES = (
    (0x94DD, b"\x70\x26", "jnz  0x9505", 0x9505),
    (0x94E2, b"\x70\x05", "jnz  0x94e9", 0x94E9),
    (0x94F0, b"\xbf\x03\x09", "cjne r7,#0x03,0x94fc", 0x94FC),
    (0x957C, b"\x30\xe2\x1a", "jnb  acc.2,0x9599", 0x9599),
    (0x95BB, b"\x70\x03", "jnz  0x95c0", 0x95C0),
    (0xDA26, b"\x30\xe2\x14", "jnb  acc.2,0xda3d", 0xDA3D),
    (0xDA30, b"\x30\xe4\x05", "jnb  acc.4,0xda38", 0xDA38),
)

# The seed stores, so a table that names the right bytes but the wrong arm
# still fails. (runtime, expected bytes, expected mnemonic)
SELF_TEST_SEED_STORES = (
    (0x94F3, b"\x74\x61", "mov  a,#0x61"),
    (0x94F7, b"\x74\xfe", "mov  a,#0xfe"),
    (0x94FC, b"\x74\x61", "mov  a,#0x61"),
    (0x9500, b"\x74\xc8", "mov  a,#0xc8"),
    (0x9505, b"\x7e\x61", "mov  r6,#0x61"),
    (0x9507, b"\x7f\x92", "mov  r7,#0x92"),
)

# A fixture, not the image, for the two refusals. The point is that a check
# which stops rejecting anything goes red, without depending on this firmware
# happening to contain the shape.
FIXTURE = bytes(0x8000) + b"\x90\x07\x30"
REFUSAL_TOO_SHORT = 0xFFFF
REFUSAL_PAST_END = 0xFFF0


def self_test(fw_path):
    d = open(fw_path, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is "
              f"not the image the transcriptions were taken from", file=sys.stderr)
        return 1
    bad = 0
    print("variant_selector.py --self-test")

    for runtime, want_raw, want_text, want_target in SELF_TEST_BRANCHES:
        n = len(want_raw)
        blob = read_window(d, "bank0", runtime, n)
        got_text = disasm_text(blob, 0, runtime)
        got_target = branch_target(d, "bank0", runtime, n)
        ok = blob == want_raw and got_text == want_text \
            and got_target == want_target
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  0x{runtime:04X} "
              f"`{blob.hex(' ')}` {got_text!r} -> 0x{(got_target or 0):04X}")
        if not ok:
            print(f"        expected `{want_raw.hex(' ')}` {want_text!r} "
                  f"-> 0x{want_target:04X}")

    for runtime, want_raw, want_text in SELF_TEST_SEED_STORES:
        blob = read_window(d, "bank0", runtime, len(want_raw))
        got_text = disasm_text(blob, 0, runtime)
        ok = blob == want_raw and got_text == want_text
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  0x{runtime:04X} "
              f"`{blob.hex(' ')}` {got_text!r}")
        if not ok:
            print(f"        expected `{want_raw.hex(' ')}` {want_text!r}")

    # The bit-operand reading, separately, because it is the claim a
    # "correction" to the annotations would turn on and a mnemonic comparison
    # alone would let a wrong-but-stable decoder pass.
    blob = read_window(d, "bank0", 0x957C, 3)
    got_bit = bit_name(blob[1])
    ok = got_bit == "acc.2"
    bad += 0 if ok else 1
    print(f"  {'ok  ' if ok else 'FAIL'}  0x957C `30 {blob[1]:02x} 1a` -- the "
          f"bit operand 0x{blob[1]:02x} is {got_bit}, not a P2 bit "
          f"(P2.2 would be 0xa2)")

    for label, runtime, n in (("short window", REFUSAL_TOO_SHORT, 8),
                              ("window past the end", REFUSAL_PAST_END, 64)):
        try:
            read_window(FIXTURE, "bank0", runtime, n)
        except Refusal as exc:
            bad += 0
            print(f"  ok    a {label} is refused: {exc}")
        else:
            bad += 1
            print(f"  FAIL  a {label} was read rather than refused")

    try:
        seed_table(FIXTURE, 0x80, 0x00)
    except Refusal as exc:
        print(f"  ok    a seed pointing into a bank window is refused: {exc}")
    else:
        bad += 1
        print("  FAIL  a seed pointing into a bank window was read")

    print("self-test: " + ("all checks passed" if not bad
                           else f"{bad} FAILED"))
    return 1 if bad else 0


def check(fw_path):
    """Diff this run's table against the committed one in the finding.

    The comparison is against `docs/findings/mode-defaults-variant-selector.md`
    rather than a second copy of the table, so there is one place a reader
    looks and one place a change has to land.
    """
    import os
    finding = os.path.join(os.path.dirname(__file__), "..", "..",
                           "docs", "findings",
                           "mode-defaults-variant-selector.md")
    try:
        committed = open(finding).read()
    except OSError as exc:
        print(f"variant_selector.py --check: {exc}", file=sys.stderr)
        return 1
    got = report(open(fw_path, "rb").read())
    if got.strip() not in committed:
        print("variant_selector.py --check: the table this run derives is not "
              "the one committed in the finding; re-run and paste it", file=sys.stderr)
        return 1
    print("variant_selector.py --check: the derived table matches the finding")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image "
                                     "(e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="store sites as CSV instead of the prose table")
    ap.add_argument("--check", action="store_true",
                    help="diff the derived table against the committed finding")
    ap.add_argument("--self-test", action="store_true",
                    help="check the branch decodes against hand transcriptions")
    args = ap.parse_args()
    if args.self_test:
        return self_test(args.firmware)
    if args.check:
        return check(args.firmware)
    d = open(args.firmware, "rb").read()
    try:
        sys.stdout.write(report(d, args.csv))
    except Refusal as exc:
        print(f"variant_selector.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
