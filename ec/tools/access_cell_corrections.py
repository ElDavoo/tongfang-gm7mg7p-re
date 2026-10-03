#!/usr/bin/env python3
"""The one place a committed `access` cell may differ from what
`classify(walk(d, file_offset))` returns at `walk()`'s own budget of 8.

**A corrected cell cannot simply be typed into a CSV.** Three site tables and
`walk_budget_census.py` both refuse a hand-edit: `csv_table()`'s `--check`
diffs the generator's output against the committed file and says "regenerate
rather than edit", and `census_table()` refuses the whole run when it cannot
re-derive a committed `access` cell from the image. Both would go red on a
cell a person corrected by hand, and both would be right to. So a correction
has to be something the tool *derives*, which is what this module is: a table
of sites whose committed cell is not the budget-8 verdict, each carrying the
**instruction budget at which the tool itself produces that string**.

That budget is the load-bearing part. An entry is not an assertion a reader
has to take on trust; `verify()` re-walks the image at the recorded budget and
raises unless `classify()` hands back exactly the string the entry claims. A
correction that cannot be re-derived is a claim, and this repository does not
keep those -- so the module refuses one rather than exporting it.

**Why these three and not more.** `walk_budget_census.py`'s `verdict_for()`
splits every budget-truncated row into class A and class B, and the three
class-B rows are the ones whose committed cell is *short* rather than wrong:
no store to DPL/DPH sits between the budget-8 cut and the first `movx` the
larger budget reaches, so the extra access belongs to this same site and no
larger budget has to be chosen to get a different answer. Class A is the
opposite -- the extra access rides a rebuilt DPTR and is not this register's
at all -- and no budget fixes those. `../../docs/findings/class-b-access-cell-corrections.md`
carries the bytes, the second method for each and the census run that produces
the tie-breaker.

**What this is not.** `classify()` and `walk()` are untouched, so every other
row of every committed table still satisfies `classify(walk(d, off)) ==
access` byte for byte. These three rows keep their `window` and `terminator`
cells too: they are still genuinely budget-truncated, and saying so is
separate from saying what the access is. And nothing here is a statement about
what the EC or the PD firmware does with any byte -- it is a direction class
over a linear decode, on both sides.

Usage:
    python3 access_cell_corrections.py --self-test
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")

Correction = collections.namedtuple(
    "Correction", "offset table addr access budget reason evidence")


def _c(offset, table, addr, access, budget, reason, evidence):
    return Correction(offset, table, addr, access, budget, reason,
                      tuple(e.strip() for e in evidence.split(";")))


CORRECTIONS = (
    _c(0x2BECB, "ec-07d6-07d7-sites.csv", "0x07D6",
       "write x4, walks 4 consecutive bytes (inc dptr)", 64,
       "Four `movx @dptr,a` stores with three `inc dptr` between them and no "
       "flow opcode or DPTR rebuild in front of any of them: 0xBECF writes "
       "0x07D6, 0xBED2 writes 0x07D7, 0xBED5 writes 0x07D8, 0xBED7 writes "
       "0x07D9. walk()'s eighth instruction from the site ends at 0xBED4, an "
       "`inc dptr`, which is why the budget-8 cell counted two writes and "
       "three walked bytes rather than four of each. Second method: the "
       "committed listing, whose function is exported as "
       "write_07d6_07d7_07d8_07d9_then_store_07df and whose annotation row "
       "decodes the same four stores by hand.",
       "ec/decompiled/pd/BECB.asm; ec/decompiled/pd/BECB.c; "
       "ec/annotations/ghidra-functions.csv"),

    _c(0x2E8D4, "ec-0x07d0-sites.csv", "0x07D0",
       "read x1, write x1", 64,
       "The site writes 0x07D0 at 0xE8D8 and reads it straight back at "
       "0xE8E3, with no `mov 0x82,a` / `mov 0x83,a` and no `mov DPTR,#imm` "
       "between them; the window then ends on `lcall 0x128d` at 0xE8F6. The "
       "read feeds a `mul AB` against the record stride 0x17, which is the "
       "indexing this function exists to do, so it is a real access to the "
       "byte and not a masked one. Second method: the annotation row on "
       "`index_07d0_by_0x17_then_fill_128d_and_call_f604`, whose comment "
       "already says the function 'reads the byte back from 0x07D0'. The "
       "second `mov DPTR,#0x07d0` at 0xE8F9 is past that call and is "
       "already a row of its own at `read x1`, so this does not count it "
       "twice.",
       "ec/decompiled/pd/E8D4.asm; ec/decompiled/pd/E8D4.c; "
       "ec/annotations/ghidra-functions.csv"),

    _c(0x0DD4A, "xdata-0400-045f-sites.csv", "0x045A",
       "read x2, write x2", 64,
       "Two reads and two writes with nothing between them but the mask and "
       "the OR: 0x0DD4D reads, 0x0DD50 writes back `(old & 0xF0)`, 0x0DD51 "
       "reads that back into R7, and 0x0DD5A writes `(old & 0xF0) | (0x32 & "
       "0x0F)`. walk()'s eighth instruction ends at 0x0DD55, so the second "
       "write is the one the budget dropped; the window ends on the `ret` at "
       "0x0DD5B. Second method: the export "
       "`or_intmem_32_low_nibble_into_045a`, whose annotation spells out the "
       "two writes and the net `(old & 0xF0) | (internal 0x32 & 0x0F)`. "
       "Internal RAM 0x32 has no registers.yaml entry and its role is not "
       "established; that is a gap in this repository, not a claim that "
       "nothing owns the byte.",
       "ec/decompiled/bank0/DD4A.asm; ec/decompiled/bank0/DD4A.c; "
       "ec/annotations/ghidra-functions.csv"),
)

BY_OFFSET = {c.offset: c for c in CORRECTIONS}


def corrected(offset: int, derived: str) -> str:
    """`derived` unless `offset` is a corrected site, in which case its cell.

    Keyed on the file offset alone rather than on a `(table, offset)` pair.
    The offset *is* the site: `trace_xdata_refs.sites_for()` only ever hands
    `walk()` the address of a `MOV DPTR,#imm16`, so one offset names one
    address and one decode, and scoping a correction to the table that
    happened to commit it would make the same bytes answer two ways in two
    committed files. The `table` each entry records is kept for the reader and
    for `verify()`'s message, not for the lookup.

    `derived` is returned unchanged for every other offset, so a caller needs
    no test of its own and an uncorrected table is unaffected by this module
    existing.
    """
    entry = BY_OFFSET.get(offset)
    return entry.access if entry is not None else derived


def verify(d: bytes) -> None:
    """Raise unless every entry's `access` is what the image gives at its
    recorded budget.

    The refusal is the point rather than a guard rail. An entry whose string
    cannot be re-derived is a claim about bytes that the bytes do not carry,
    and the whole reason this table exists instead of a hand-edit is that such
    a thing is not kept in this repository. Raising rather than warning
    because `csv_table()` and `census_table()` call `corrected()` on every
    row of every table: a correction that quietly stopped being derivable
    would leave a committed cell no producer could reproduce, and `--check`
    would go green against it.

    `trace_xdata_refs` is imported here rather than at module scope because
    `trace_xdata_refs.csv_table()` imports `corrected()` -- the dependency
    runs corrections -> decoder, and a module-level import both ways is a
    cycle that resolves differently depending on which module was imported
    first.
    """
    from trace_xdata_refs import classify, walk

    for c in CORRECTIONS:
        got = classify(walk(d, c.offset, c.budget))
        if got != c.access:
            raise ValueError(
                f"{c.table} row 0x{c.offset:05X} ({c.addr}) is recorded as "
                f"{c.access!r}, but classify(walk(image, 0x{c.offset:05X}, "
                f"{c.budget})) returns {got!r}; a correction the image does "
                f"not produce is a claim, and this repository does not keep "
                f"those. Either the bytes changed or the budget recorded "
                f"beside the cell is the wrong one.")


def main() -> int:
    """`--self-test`, which is the only thing here to run.

    The module produces no table of its own -- it *is* the table, plus the one
    check that the table is re-derivable -- so there is nothing to print and
    nothing to diff. What a reader needs is the way to re-derive the corrected
    cells against the committed firmware without running anything else, which
    is this. The flag takes no different code path from running without it;
    it is spelled out because `--self-test` is how every other tool here names
    the same thing, and a reader who types it should not wonder whether it
    turned anything on.
    """
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("--self-test", action="store_true",
                    help="accepted for symmetry with the other tools here; "
                         "this module re-derives its corrections either way, "
                         "and exits non-zero if one does not come back")
    args = ap.parse_args()

    if not os.path.isfile(args.firmware):
        print(f"note: {args.firmware} is not a file", file=sys.stderr)
        return 1
    with open(args.firmware, "rb") as f:
        d = f.read()
    try:
        verify(d)
    except ValueError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    print(f"self-test passed: {len(CORRECTIONS)} corrected access cell(s), "
          f"each re-derived from {os.path.relpath(args.firmware, REPO)} at "
          f"its recorded budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
