#!/usr/bin/env python3
"""Census every way the image names DPL or DPH in a byte-addressed `direct`
operand, and say which of them rebuild DPTR, which read it, and which do
neither.

Issue #1027 asked for the census its own numbers implied and did not run: the
store forms against `0x82`/`0x83` were `trace_xdata_refs.is_dptr_rebuild()`'s
list, and the *read* forms -- `mov a,0x82`, `mov r5,0x82`, `push 0x82` -- had
never been counted anywhere in the tree, though the discriminator between the
two directions is exactly the thing a sweep that searches rendered text gets
wrong. This counts both, from the bytes, and counts the in-place forms
beside them so the third bucket is a measurement rather than a silence.

**The discriminator is the operand position, and it is `dptr_store_byte()`'s
rather than this file's.** `mov 0x82,<src>` writes DPTR's low byte and
`mov <dst>,0x82` reads it; the two spellings are one apart in the opcode map
(`0xF5` against `0xE5`, `0x75` against `0xA8`-`0xAF`, `0xD0` against `0xC0`),
and only the byte says which is which. One 8051 form breaks the pattern
inside itself: `mov direct,direct` (`0x85`) names its **source** first and its
destination second, so the byte this file keys on for the store is `d[i+2]`
there and `d[i+1]` everywhere else. That is the distinction
`walk_budget_census.dptr_store_byte()` already makes, so the store half is
delegated to rather than written a second time -- a third copy of the same
operand index is the kind of thing that gets one of them wrong later.

**`0x85` is in two buckets because one instruction is two references.**
`85 83 f0` is `mov B,DPH`: it reads DPH and writes B, so its source is a
read-form reference and its destination is not a DPTR write at all. Classifying
the instruction by its store half alone drops those four references in this
image -- `form_at()` therefore returns *every* reference an instruction makes,
and the two halves need not agree, because `85 82 82` would read and write the
same byte.

**This is a byte census, not a disassembly.** Every offset is examined rather
than every instruction boundary, because this tool has no way to know where
instruction boundaries are without a decode, and a decode would be a different
claim: these are byte pairs at every offset of the file, so they include bytes
that are data, bytes in a lookup table, and bytes in the separate PD 8051
image, alongside the ones a program actually executes. Read as "found by this
method", never as a count of executed instructions. The `mov DPTR,#imm16`
census of `../../docs/findings/dptr-rebuild-walk-guard.md` §1 is **the same
kind of measurement over the same population** -- a byte sweep for `0x90` at
every offset of this same file -- so the two are labelled beside each other
and never added together.

**A form this image does not use is reported as not found by this method**,
which is the phrasing `ec/annotations/registers.yaml` asks for and which
`trace_xdata_refs.py` states for the same reason: a zero is a fact about this
method over this file, and calling it an absence is the overclaim
`../../CLAUDE.md`'s calibration rule exists to prevent. It is not a claim that
the firmware cannot contain the form.

**Three buckets, and the third is not a rounding error.** `store` is the
form that replaces the pointer or one of its bytes -- every construction
`is_dptr_rebuild()` names, plus the two `mov direct,@Ri` forms it does not,
which `../../docs/findings/dptr-rebuild-walk-guard.md` §3 records as a gap
in the guard rather than a decision in it. `read` is a load of one of the
two bytes into A, an Rn, an indirect cell or the stack, which rebuilds
nothing and must not be swept in with the stores. `in place` is the
arithmetic, logical, `inc`/`dec`, `clr`, `djnz` and `xch` group, which name
DPL or DPH, change it, and replace neither; the guard declines all of them
for a stated reason (`../../docs/findings/dptr-rebuild-walk-guard.md` §3),
and a bucket that did not exist would let that decision read as an absence
rather than as a choice.

**The three tables are the whole byte-addressed `direct` map, and the one
class left out is named rather than left out silently.** The base 8051 has
**41** such opcodes and its 8052 extension adds **eight** -- the six
`direct,A`/`direct,#data` rows of the logical group and the two `SUBB` forms
`0x96`/`0x97`, the base 8051's `SUBB` group being `0x94`/`0x95` alone -- for
**49** between them, and every one of them is in one of
these three tables; `test_dptr_rebuild_forms.py` holds their union against
that map written out a second time, because a hand-written list that is
merely *nearly* complete reads exactly like a complete one. That map is
written from the instruction set, and the committed Ghidra listings under
`ec/decompiled/*/*.asm` corroborate it wherever they carry an instance --
every entry except `0x96`/`0x97`, which appear nowhere in them and so rest on
the instruction set alone. The listings are also the reason nothing here is
taken from `disasm8051.mnemonic()`: that renderer is correct about the
accumulator rows (`54 82` renders as `anl a,#0x82`, which is what the
machine executes, and `OPCODE_LEN[0x54] == 2` is right), but it emits the
`direct,A`/`direct,#data` rows `0x42`/`0x43`/`0x52`/`0x53`/`0x62`/`0x63` as
`db 0x42` and `db 0x63` where the machine writes a byte address, and its
`OPCODE_LEN` is one short for `0x26`, `0x36`, `0x96` and `0x97`. The
cross-check that did exist, over all 256 opcodes, could not be that oracle: it
held the *store* table to `is_dptr_rebuild()`, which omitted the same two
opcodes and so agreed on exactly the rows that were wrong, and it never
looked at the read or in-place tables at all. The excluded class is the
bit-addressed forms
(`0x0A`/`0x2A`/`0x4A`/`0x5A`/`0x6A`/`0x72`/`0x7A`/`0x82`/`0x92`/`0xA0`/`0xA2`/
`0xB0`/`0xB2`/`0xC1`/`0xD2`, and the three `jb`/`jnb`/`jbc` rows), which take
a *bit* address where `0x82` is the low byte of SFR `0x88` and not DPL at all,
so a sweep that counted them would be counting a different address under the
same spelling. `mov DPTR,#imm16` (`0x90`) is the one construction that
replaces the pointer and names no `direct` operand, so it appears in none of
the three tables. Both exclusions are facts about this file's keying, not
about the 8051.

**Nothing here is a claim about the EC.** Every input is a committed file.
No register was read back, no capture opened, no hardware or Windows
involved, and no `registers.yaml` row changes: a `mov DPL,A` is a reference
to the byte `0x82`, not to any XDATA address, and `static_refs` counts
addresses.

Usage:
    python3 dptr_rebuild_forms.py ../firmware/GMxMGxx_11.800
    python3 dptr_rebuild_forms.py ../firmware/GMxMGxx_11.800 --csv
"""
import argparse
import collections
import csv
import io
import os
import sys

from trace_xdata_refs import MOV_DIRECT_DIRECT, DPL, DPH
from walk_budget_census import dptr_store_byte

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")

# The three buckets, as opcode -> the disassembly's spelling of the form. The
# names are the 8051's, and `disasm8051.mnemonic()` does not render all of them
# (it emits the `direct,A`/`direct,#data` rows `0x42`/`0x43`/`0x52`/`0x53`/
# `0x62`/`0x63` of the logical group as `db 0x42` and `db 0x63`, where the
# machine writes a byte address). That is why nothing here keys on rendered
# text, and why the spellings below are written out rather than generated from
# a table that has the defect. The accumulator rows the renderer *does* get
# right are not a reason to trust it: `0x44`/`0x54`/`0x64` are two-byte
# `a,#imm` and `0x45`/`0x55`/`0x65` two-byte `a,direct`, exactly as it prints
# them, which is why the defect is confined to the other side of the group.
STORE_FORMS = dict(
    [(0x75, "mov  direct,#imm"),
     (0x85, "mov  direct,direct"),
     (0x86, "mov  direct,@r0"),
     (0x87, "mov  direct,@r1"),
     (0xD0, "pop  direct"),
     (0xF5, "mov  direct,a")]
    + [(op, "mov  direct,r%u" % (op - 0x88)) for op in range(0x88, 0x90)])
READ_FORMS = dict(
    [(0x25, "add  a,direct"),
     (0x27, "addc a,direct"),
     (0x35, "addc a,direct"),
     # `0x45`/`0x55`/`0x65` are the *source* form of the logical group: the
     # accumulator is the destination, so they load the byte and change
     # nothing at the address they name. The committed Ghidra listings say so
     # directly -- `45 82` decodes `orl A, DPL` and `65 f0` decodes
     # `xrl A, B` -- and the `0x42`/`0x52`/`0x62` rows below are the same
     # group with the operand on the other side, which is why the two halves
     # of the group belong in different buckets.
     (0x45, "orl  a,direct"),     (0x55, "anl  a,direct"),
     (0x65, "xrl  a,direct"),
     (0x85, "mov  direct,direct"),
     (0x95, "subb a,direct"),
     (0xA6, "mov  @r0,direct"),
     (0xA7, "mov  @r1,direct"),
     (0xB5, "cjne a,direct,rel"),
     (0xC0, "push direct"),
     (0xE5, "mov  a,direct")]
    + [(op, "mov  r%u,direct" % (op - 0xA8)) for op in range(0xA8, 0xB0)])
IN_PLACE_FORMS = {
    0x05: "inc  direct",          0x15: "dec  direct",
    0x26: "add  direct,a",        0x36: "addc direct,a",
    # Eight entries here are 8052 additions a base-MCS-51 opcode map does not
    # have: the `direct,A`/`direct,#data` rows of the logical group
    # `0x42`/`0x43`/`0x52`/`0x53`/`0x62`/`0x63`, and the `SUBB` pair
    # `0x96`/`0x97` -- the base 8051's `SUBB` group is `0x94`/`0x95` alone.
    # The logical-group six are the writing side of the `0x45`/`0x55`/`0x65`
    # rows in `READ_FORMS`: two bytes for the `direct,A` form, three for
    # `direct,#data`. The committed listings render them `42 f0 orl B, A` and
    # `63 65 ff xrl 0x65, #0xff`; they carry no instance of `0x96` or `0x97`,
    # so those two rest on the instruction set alone.
    0x42: "orl  direct,a",        0x43: "orl  direct,#imm",
    0x52: "anl  direct,a",        0x53: "anl  direct,#imm",
    0x62: "xrl  direct,a",        0x63: "xrl  direct,#imm",
    0x96: "subb direct,#imm",     0x97: "subb direct,a",
    0xC2: "clr  direct",          0xC5: "xch  a,direct",
    0xD5: "djnz direct,rel",
}
BUCKETS = (("store", STORE_FORMS,
            "it replaces DPTR or one of its two bytes -- every construction "
            "`is_dptr_rebuild()` names, and the two `mov direct,@Ri` forms it "
            "does not, which dptr-rebuild-walk-guard.md §3 records as a gap "
            "in the guard rather than a decision in it"),
           ("read", READ_FORMS,
            "the other side of the operand order -- it loads one of the two "
            "bytes, so it rebuilds nothing and ends no window; `0x85` is here "
            "as well as in `store`, because it is both at once"),
           ("in place", IN_PLACE_FORMS,
            "names DPL/DPH and changes it in place rather than replacing it; "
            "the guard declines all of these for the reason in "
            "dptr-rebuild-walk-guard.md §3, and they are listed so that reads "
            "as a choice rather than a silence"))

COLUMNS = ("bucket", "opcode", "form", "dpl", "dph", "references")


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below."""
    return os.path.relpath(path, REPO)


def form_at(d: bytes, off: int):
    """Every `(bucket, opcode, byte)` the instruction at `d[off]` names.

    A list, and empty rather than None when the instruction is not a form,
    because the list is the honest shape: `mov direct,direct` is a read of its
    source *and* a store of its destination at one instruction, so a return
    value that can carry only one of them has to drop the other. In
    instruction operand order, which for `0x85` is source first.

    The store half's byte is the one the form writes, not the one a first
    operand read would return, and the call is delegated to
    `walk_budget_census.dptr_store_byte()` so this file holds no second
    opinion about which half of DPTR an instruction touched. The read half is
    `d[off+1]` for every form in the three tables including `0x85`, so the
    two delegates are complementary rather than two answers to one question.
    """
    op = d[off]
    if op in STORE_FORMS or op in READ_FORMS or op in IN_PLACE_FORMS:
        # Two bytes carry the operand for every form in the three tables
        # except `0x85`, whose destination is its second operand, and a form
        # whose operand byte is past the end of the buffer is not a form at
        # all -- the same bounds discipline `is_dptr_rebuild()` applies, and
        # the reason this sweep can run to the last offset of the file.
        need = 2 if op != MOV_DIRECT_DIRECT else 3
        if off + need > len(d):
            return []
        if op == MOV_DIRECT_DIRECT:
            return [("read", op, d[off + 1]),
                    ("store", op, dptr_store_byte(d[off:off + need]))]
        bucket = ("store" if op in STORE_FORMS else
                  "read" if op in READ_FORMS else "in place")
        return [(bucket, op, d[off + 1])]
    return []


def census(d: bytes):
    """`{bucket: {opcode: {byte: n}}}` -- every form the file names at every
    offset.

    Every offset of the buffer is examined rather than every instruction
    boundary, because this file has no way to know where the boundaries are
    without a decode, and a decode would be a different claim -- see the
    module docstring. The forms that would run past the end of the buffer are
    the ones `form_at()` declines, and on a dump whose last region is erased
    there are none.
    """
    found = collections.defaultdict(
        lambda: collections.defaultdict(collections.Counter))
    for off in range(len(d)):
        for bucket, op, byte in form_at(d, off):
            if byte in (DPL, DPH):
                found[bucket][op][byte] += 1
    return found


def rows_for(found, bucket: str, forms: dict):
    """The CSV rows of one bucket, opcodes in ascending order, zeros included.

    A form the image does not use is a row carrying nothing, because a table
    that lists only the forms it found cannot be read as an answer about the
    ones it did not.
    """
    tallies = found.get(bucket, {})
    for op in sorted(forms):
        halves = tallies.get(op, {})
        yield (bucket, "0x%02X" % op, forms[op], halves.get(DPL, 0),
               halves.get(DPH, 0), halves.get(DPL, 0) + halves.get(DPH, 0))


def as_csv(found) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for bucket, forms, _ in BUCKETS:
        for row in rows_for(found, bucket, forms):
            w.writerow(row)
    return buf.getvalue()


def print_summary(found) -> None:
    width = max(len(forms[op]) for _, forms, _ in BUCKETS for op in forms)
    for bucket, forms, why in BUCKETS:
        print(f"\n{bucket} forms -- {why}")
        tallies = found.get(bucket, {})
        dpl = dph = 0
        for row in rows_for(found, bucket, forms):
            _, op, form, lo, hi, total = row
            dpl += lo
            dph += hi
            # A zero is a fact about this method over this file, and says so
            # rather than rendering a bare 0 a reader could take for an
            # absence.
            count = ("%6d" % total if total
                     else " not found by this method")
            print(f"  {op}  {form:<{width}s}  {count}   "
                  f"DPL {lo} / DPH {hi}")
        print(f"{dpl + dph} {bucket}-form references, over {len(tallies)} of "
              f"the {len(forms)} opcodes the table names: "
              f"DPL {dpl} / DPH {dph}")
    print(
        "\nEvery figure above is a byte census over every offset of the file, "
        "not a disassembly:\nthey include bytes that are data, table entries "
        "and the separate PD 8051 image, so read\nthem as found by this method "
        "and not as a count of executed instructions. The three tables\nare "
        "the whole map of byte-addressed direct operands: 41 in the base 8051\n"
        "plus the eight its 8052 extension adds. Two classes are out of them,\n"
        "and both are out because of this file's keying rather than because\n"
        "of the 8051:\n"
        "the bit-addressed forms take a bit "
        "address, where 0x82 is\nthe low byte of SFR 0x88 rather than DPL, and "
        "`mov DPTR,#imm16` (0x90) names no direct operand at\nall.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("--csv", action="store_true",
                    help="write the census as CSV on stdout instead of the "
                         "per-form summary")
    args = ap.parse_args()

    try:
        d = open(args.firmware, "rb").read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1

    found = census(d)
    if args.csv:
        sys.stdout.write(as_csv(found))
        return 0

    print(f"{repo_path(args.firmware)}: {len(d)} bytes swept at every offset.")
    print_summary(found)
    return 0


if __name__ == "__main__":
    sys.exit(main())
