#!/usr/bin/env python3
"""Census every way the image names DPL or DPH, and say which of them rebuild
DPTR, which read it, and which do neither.

Issue #1027 asked for the census its own numbers implied and did not run: the
store forms against `0x82`/`0x83` are `trace_xdata_refs.is_dptr_rebuild()`'s
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
destination second, so the byte this file keys on is `d[i+2]` there and
`d[i+1]` everywhere else. That is the distinction
`walk_budget_census.dptr_store_byte()` already makes, so it is delegated to
rather than written a second time -- a third copy of the same operand index is
the kind of thing that gets one of them wrong later.

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

**Three buckets, and the third is not a rounding error.** `store` is every
construction `is_dptr_rebuild()` names -- the forms that replace the pointer
or one of its bytes. `read` is a load of one of the two bytes into A, an
Rn or the stack, which rebuilds nothing and must not be swept in with the
stores. `in place` is `anl`/`orl`/`xrl direct`, `inc`/`dec direct` and
`xch a,direct`, which name DPL or DPH, change it, and replace neither; the
guard declines all of them for a stated reason
(`../../docs/findings/dptr-rebuild-walk-guard.md` §3), and a bucket that did
not exist would let that decision read as an absence rather than as a
choice.

**Not counted, and named rather than left out silently.** The bit-addressed
forms (`mov bit,C`, `orl C,bit`, `anl C,bit`, `setb`/`clr` bit) take a *bit*
address, where `0x82` is the low byte of SFR `0x88` and not DPL at all, so a
sweep that counted them would be counting a different address under the same
spelling. `mov DPTR,#imm16` (`0x90`) is the one construction that replaces the
pointer and names no `direct` operand, so it appears in none of the three
tables. Both are facts about this file's keying, not about the 8051.

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
# (it prints the `0x44`/`0x45`/`0x54`/`0x55`/`0x64`/`0x65` group as A-operand
# forms, so `54 82` reads `anl a,#0x82` where the machine writes DPL). That is
# why nothing here keys on rendered text, and why the spellings below are
# written out rather than generated from a table that has the defect.
STORE_FORMS = dict(
    [(0x75, "mov  direct,#imm"),
     (0x85, "mov  direct,direct"),
     (0xD0, "pop  direct"),
     (0xF5, "mov  direct,a")]
    + [(op, "mov  direct,r%u" % (op - 0x88)) for op in range(0x88, 0x90)])
READ_FORMS = dict(
    [(0xE5, "mov  a,direct"),
     (0xC0, "push direct")]
    + [(op, "mov  r%u,direct" % (op - 0xA8)) for op in range(0xA8, 0xB0)])
IN_PLACE_FORMS = {
    0x05: "inc  direct",          0x15: "dec  direct",
    0x44: "orl  direct,#imm",     0x45: "orl  direct,a",
    0x54: "anl  direct,#imm",     0x55: "anl  direct,a",
    0x64: "xrl  direct,#imm",     0x65: "xrl  direct,a",
    0xC5: "xch  a,direct",
}
BUCKETS = (("store", STORE_FORMS,
            "every construction `is_dptr_rebuild()` names: it replaces DPTR or "
            "one of its two bytes"),
           ("read", READ_FORMS,
            "the other side of the operand order -- it loads one of the two "
            "bytes, so it rebuilds nothing and ends no window"),
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
    """`(bucket, opcode, byte)` for the instruction at `d[off]`, else None.

    The byte is the one the form names, not the one a first operand read
    would return: for `mov direct,direct` that is `d[off+2]`, and the call is
    delegated to `walk_budget_census.dptr_store_byte()` so this file holds no
    second opinion about which half of DPTR an instruction touched.
    """
    op = d[off]
    if op in STORE_FORMS:
        # Two bytes carry the operand for every store form except `0x85`,
        # whose destination is its second operand, and a form whose operand
        # byte is past the end of the buffer is not a form at all -- the same
        # bounds discipline `is_dptr_rebuild()` applies, and the reason this
        # sweep can run to the last offset of the file.
        need = 2 if op != MOV_DIRECT_DIRECT else 3
        if off + need > len(d):
            return None
        return ("store", op, dptr_store_byte(d[off:off + need]))
    if op in READ_FORMS or op in IN_PLACE_FORMS:
        # `mov a,direct`, `mov rN,direct`, `push direct` and the whole
        # in-place group name their one operand at d[off+1], and none of them
        # is the `0x85` exception.
        if off + 2 > len(d):
            return None
        bucket = "read" if op in READ_FORMS else "in place"
        return (bucket, op, d[off + 1])
    return None


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
        hit = form_at(d, off)
        if hit is None:
            continue
        bucket, op, byte = hit
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
        "and not as a count of executed instructions. What is\nabsent from the "
        "three tables is absent from this file's keying, which is a fact\nabout "
        "the keying and not about the 8051: the bit-addressed forms take a bit\n"
        "address, where 0x82 is the low byte of SFR 0x88 rather than DPL, and "
        "`mov DPTR,#imm16`\n(0x90) names no direct operand at all.")


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
