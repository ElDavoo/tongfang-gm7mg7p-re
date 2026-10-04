#!/usr/bin/env python3
"""Who reads the `??82` XDATA cells `lcall 0x104D` fills in, counted per program
and per direction -- and, on this image, the written answer that none does.

`../../docs/findings/pd-inline-arg-trampoline.md` §5 gives the cells and stops:
"What reads those cells was not traced." The issue that followed (#1142) measured
it with `trace_xdata_refs.py --counts-only` and read the result as "174 writers
against one reader". That reading is wrong in two ways at once, and separating
them is what this tool is for.

**A `MOV DPTR` site is not a reader.** `--counts-only` tallies direct
`MOV DPTR,#imm16` *sites*; the direction of the access comes from the window that
follows, and nothing in a count knows it. Decoded, the single `0x0A82` site in
the PD image is `mov dptr,#0x0a82 / mov a,r7 / movx @dptr,a / inc dptr / ...` --
a *writer*, walking three consecutive bytes. It is already annotated
`store_4bytes_to_0a82 [writer]` in `../annotations/ghidra-functions.csv`. So
`0x0A82` is 174 deposits against **no** identified reader, not one.

**A site in `bank0` is not a site in the PD image.** `0x0782`'s eleven sites are
all in the main EC, a separate program with its own XDATA map
(`../annotations/pd-xdata-overlap.md`); none of them is a consumer of the 107
values the PD image writes there. `../annotations/pd-xdata-span-sites.csv` already
carries the split for that address (`main_ec=11, pd_image=0`) and this tool's
`where` column reproduces it rather than blending the two into one number.

So every count here is **per program and per direction**, and a blended figure is
not printed: the blend is the defect, and a table with a "total readers" column
would put it back.

**Three spellings are swept per cell, and `--blind-spots` prints what each one
cannot find.** `MOV DPTR,#imm16` is one of them and the only one
`--counts-only` looks for; a consumer that builds the address in registers is
invisible to it. All three run for every cell and each contributes its own
column, so a cell three methods miss is a cell three methods missed rather than
one a single method missed. A fourth way in -- the helper's own entry points --
names no cell and is counted separately; `entries()` is its measurement.

**An independent second census agrees, which is what makes the zero a result.**
`../annotations/xdata-registers.csv` is built from the Ghidra decompile rather
than from a byte scan, so it has different blind spots, and over the same cells
it reads `0x0A82` as 0 reads against writes and has no row at all for `0x0882`.
Two methods whose blind spots differ, converging on "no PD-side reader", is the
strongest statement this evidence carries; neither method alone is.

**Every zero here is "not found by this method".** It is not a claim that the
firmware cannot contain a consumer, and `../../CLAUDE.md`'s calibration rule and
`docs/findings.md` §4c both ask for that wording rather than the confident one.

Usage:
    python3 pd_inline_arg_readers.py ../firmware/GMxMGxx_11.800
    python3 pd_inline_arg_readers.py ../firmware/GMxMGxx_11.800 --blind-spots
    python3 pd_inline_arg_readers.py ../firmware/GMxMGxx_11.800 --csv > ../annotations/pd-inline-arg-readers.csv
    python3 pd_inline_arg_readers.py ../firmware/GMxMGxx_11.800 --check
"""
import argparse
import collections
import csv
import io
import os
import sys

from disasm8051 import OPCODE_LEN
from trace_xdata_refs import (PD_MARKER, REGIONS, check_table, classify,
                              region_of, repo_path, sites_for, walk_why)

from pd_inline_arg_sites import DEST_LOW, TRAMPOLINE

HERE = os.path.dirname(os.path.abspath(__file__))
SITES_CSV = os.path.join(HERE, os.pardir, "annotations",
                         "pd-inline-arg-sites.csv")
READERS_CSV = os.path.join(HERE, os.pardir, "annotations",
                           "pd-inline-arg-readers.csv")

COLUMNS = ["dest", "deposits", "mov_dptr_sites", "mov_dptr_reads",
           "mov_dptr_writes", "mov_dptr_by_region", "dptr_halves",
           "dptr_from_accumulator", "pd_side_reads", "reason"]

# The three cell sweeps, what each finds, and what it cannot find. Named as
# data because `--blind-spots` prints this list and the table's columns are
# named from it: a miss condition kept in prose beside a column computed in code
# is a miss condition that will eventually disagree with the column.
#
# The fourth is here rather than as a column because it is **not a per-cell
# measurement and cannot be made into one**. An entry that hands the helper its
# destination in a register reaches a different cell at every call, and no byte
# in the image says which -- so a column of its own would hold the same number on
# every row, which is a census of the entry spelling wearing a row's clothes.
# `--entries` reports it as the population it is.
METHODS = (
    ("mov-dptr", "mov_dptr_reads",
     "direct `MOV DPTR,#imm16` at the cell, direction from the window that "
     "follows",
     "a DPTR built any other way; a `movx` past the first branch, a DPTR "
     "reload, or the 8-instruction budget; a window handed to a subroutine, "
     "which `classify()` reports as unresolved rather than as a direction"),
    ("dptr-halves", "dptr_halves",
     "`mov DPL,#data8` and `mov DPH,#data8` as an adjacent pair, so the address "
     "is fixed by the bytes alone",
     "either byte loaded from a register or the accumulator; a pair further "
     "apart than `PAIR_REACH`, which this tool does not pair up"),
    ("dptr-from-accumulator", "dptr_from_accumulator",
     "`mov A,#data8` then `mov DPL,a` / `mov DPH,a`, each byte's A reloaded "
     "outright before its store",
     "an A built by `add`/`addc` rather than loaded outright -- the idiom "
     "`computed_dptr_sites.py` exists to decode, with the carry in hand, and "
     "which is a different tool and a different claim"),
)

# Forwarders to the helper that take the destination in R1:R2 rather than
# leaving it in DPTR. Named because the entry sweep has to know which targets to
# look for and `INLINE_ARG_CALLS` is keyed on `lcall 0x104D` alone: `ljmp
# 0x104D` and these two are the other spellings of the same entry, and a scan
# for the one the committed census counts would miss all of them.
FORWARDERS = (0x107E, 0x1098)

# DPTR's two bytes. `trace_xdata_refs` spells them DPL/DPH and explains at
# length why it keys on bytes rather than on rendered text; the same applies
# here and the reasoning is not repeated.
DPL, DPH = 0x82, 0x83
MOV_DIRECT_IMM = 0x75     # mov direct,#data8
MOV_DIRECT_A = 0xF5       # mov direct,a
MOV_A_IMM = 0x74          # mov a,#data8
MOV_DPTR = 0x90
ABS_CALL = (0x02, 0x12)   # ljmp / lcall, the two absolute 3-byte forms

# How far apart two immediate DPTR-half loads may be and still be called one
# address. Small on purpose: this tool is looking for a *direct* naming of the
# cell, and a long reach would be a claim about which loads belong together that
# no decode here supports. The same kind of parameter `pd_inline_arg_dest.REACH`
# is, and stated for the same reason.
PAIR_REACH = 3
# How many instructions the accumulator walk looks ahead for the second byte's
# store. The idiom is `mov a,#lo ; mov DPL,a ; mov a,#hi ; mov DPH,a`, which is
# three instructions between the first load and the last store.
ACC_REACH = 6


def directions(d: bytes, off: int) -> dict:
    """(reads, writes, unresolved) for the window at a `MOV DPTR` site.

    `classify()`'s own vocabulary, parsed rather than re-decided: the counts
    come from the same window every committed `access` cell in the repository's
    `*-sites.csv` tables was classified from, so a disagreement here would be a
    disagreement with those tables rather than a fresh judgement. A window that
    names no direction at all -- a CODE pointer, or nothing a `movx` -- leaves
    all three at zero rather than being sorted into one of them, which is the
    distinction `classify()` draws and this does not re-word.
    """
    text = classify(walk_why(d, off)[0])
    reads = writes = unresolved = 0
    for part in text.split(", "):
        if part.startswith("read x"):
            reads += int(part[6:])
        elif part.startswith("write x"):
            writes += int(part[7:])
    if text.startswith("DPTR handed to"):
        unresolved = 1
    return {"reads": reads, "writes": writes, "unresolved": unresolved}


def half_index(d: bytes) -> dict:
    """{address: [offsets]} for an adjacent `mov DPL,#lo` / `mov DPH,#hi` pair.

    Both bytes immediate is what fixes the address without running the program,
    and adjacency is the whole of the pairing claim: a DPL load and a DPH load
    further apart may still be one DPTR, but deciding that needs the framing
    this tool refuses to guess, so `PAIR_REACH` bounds it and is named rather
    than tuned.

    **Built as an index over the whole image in one pass, and queried by
    address afterwards.** The alternative -- a `half_sites(d, addr)` that
    rescans per address -- is 65536 sweeps of a 256 KiB buffer, which is the
    difference between a tool that runs and one that does not.

    **A pair counts as a hit whatever follows it, and that is a deliberate
    limit.** This names the cell; it does not decode the access. Deciding
    whether the instruction after the pair reads or writes would need the same
    window `directions()` uses and the same framing assumptions, and a pair
    found by a byte scan has no guaranteed boundary to start one at. So the
    column is "sites naming this cell by immediate halves" and the direction
    columns beside it come from the `mov-dptr` method alone.
    """
    out = collections.defaultdict(list)
    for i in range(len(d) - 2):
        if d[i] != MOV_DIRECT_IMM or d[i + 1] not in (DPL, DPH):
            continue
        first = d[i + 2]
        j = i + 3
        while j < min(i + 3 + PAIR_REACH, len(d) - 2):
            if d[j] == MOV_DIRECT_IMM and d[j + 1] in (DPL, DPH) \
                    and d[j + 1] != d[i + 1]:
                lo = first if d[i + 1] == DPL else d[j + 2]
                hi = d[j + 2] if d[j + 1] == DPH else first
                out[(hi << 8) | lo].append(i)
                break
            j += 1
    return out


def accumulator_index(d: bytes) -> dict:
    """{address: [offsets]} for `mov A,#lo ; mov DPL,a ; mov A,#hi ; mov DPH,a`.

    A short forward walk that tracks the accumulator rather than assuming it:
    a byte is recorded only when a `mov A,#data8` has established it since the
    walk started, so an A carried in from a register stops the count instead of
    making it a guess. That refusal is the method's miss condition, and it is
    why the `add`/`addc` idiom `computed_dptr_sites.py` decodes with the carry in
    hand is named as outside this tool rather than approximated inside it.

    A store's direction is not decided here either, for the reason
    `half_index()` gives: this finds the naming, `mov_dptr_reads` carries the
    directions.
    """
    out = collections.defaultdict(list)
    for i in range(len(d) - 2):
        if d[i] != MOV_A_IMM:
            continue
        # Seeded from the `mov A,#data8` that *is* the start of the window.
        # Leaving it unset made every walk break on its first store, which is
        # how the method reported zero everywhere and looked like a measurement
        # of the firmware rather than a broken walk.
        acc = d[i + 1]
        lo = hi = None
        j = i + 2
        for _ in range(ACC_REACH):
            if j >= len(d):
                break
            if d[j] == MOV_A_IMM:
                acc = d[j + 1]
            elif d[j] == MOV_DIRECT_A and d[j + 1] in (DPL, DPH):
                # Each half is kept separately and the walk runs to its end
                # rather than stopping at the first store, so DPH before DPL
                # reaches the same address as DPL before it. A walk that broke
                # on the first store found half the addresses there are, and
                # the ones it missed looked like a property of the firmware.
                if d[j + 1] == DPL:
                    lo = acc
                else:
                    # The accumulator holds the *high* byte for DPH and the low
                    # one for DPL, so the address is the DPH store's value
                    # shifted up rather than masked against itself -- which is
                    # what made a fixture decode as `0x0008`.
                    hi = acc
                if lo is not None and hi is not None:
                    out[((hi << 8) | lo)].append(i)
                    break
            j += OPCODE_LEN[d[j]]
    return out


def helper_entries(d: bytes, target: int) -> list:
    """Offsets of every `lcall`/`ljmp` naming `target`, anywhere in the dump.

    A byte sweep for the two absolute forms, which is the method
    `pd_inline_arg_sites.sites()` uses and for the same reason: an entry spelled
    some other way carries no target byte, and that is what the miss condition
    says. Nothing here turns an entry into a destination, because an entry that
    takes the high byte in a register cannot be -- see `entries()`.
    """
    return [i for i in range(len(d) - 2)
            if d[i] in ABS_CALL and ((d[i + 1] << 8) | d[i + 2]) == target]


def pd_span():
    """(lo, hi) file offsets of the PD image, off `REGIONS`.

    Read off the same table every other tool in this directory reads, so there
    is one definition of where the second program starts."""
    lo, hi = next(((lo, hi) for name, lo, hi, _, _ in REGIONS
                   if name == "pd-image"), (0, 0))
    return lo, hi


def row_for(d: bytes, dest: int, deposits: int, halves: dict,
            accum: dict) -> dict:
    """One cell's census, as a dict keyed by `COLUMNS`.

    `mov_dptr_by_region` is the column that carries the finding: a
    `region=count` tally in the cell, so "11 sites, all of them in another
    program" is visible without running anything, and it is why the table has no
    blended total column.
    """
    sites = sites_for(d, dest)
    reads = writes = 0
    by_region = collections.Counter()
    pd_reads = 0
    for off in sites:
        region = region_of(off, True)[0]
        by_region[region] += 1
        got = directions(d, off)
        reads += got["reads"]
        writes += got["writes"]
        if region == "pd-image":
            pd_reads += got["reads"]

    pd_lo, pd_hi = pd_span()
    in_pd = lambda offs: sum(1 for off in offs if pd_lo <= off < pd_hi)
    pd_halves = in_pd(halves.get(dest, ()))
    pd_accum = in_pd(accum.get(dest, ()))

    if pd_reads:
        reason = f"pd-side reads found: {pd_reads}"
    elif by_region.get("pd-image"):
        reason = (f"{by_region['pd-image']} pd-image MOV DPTR site(s), none of "
                  "them a read")
    else:
        reason = "no pd-image site by any of the three cell sweeps"

    return {
        "dest": f"0x{dest:04X}",
        "deposits": deposits,
        "mov_dptr_sites": len(sites),
        "mov_dptr_reads": reads,
        "mov_dptr_writes": writes,
        "mov_dptr_by_region": ";".join(f"{k}={v}" for k, v in
                                       sorted(by_region.items())),
        "dptr_halves": pd_halves,
        "dptr_from_accumulator": pd_accum,
        "pd_side_reads": pd_reads,
        "reason": reason,
    }


def census(d: bytes) -> list:
    """One row per cell the deposits land in, most-deposited first.

    The cell set is read out of `pd-inline-arg-sites.csv`'s `dest` column rather
    than enumerated here, so the population is the one the committed census
    produced. Rows that tool's own backward decode recovers but this scan left
    empty are in neither -- `pd_inline_arg_dest.py` names them, and merging the
    two populations here would quietly make one claim out of two.

    The two register-fed indexes are built once here and handed to `row_for()`,
    because building one per row would be nine sweeps of the whole image over
    the same bytes."""
    counts = collections.Counter()
    with open(SITES_CSV, newline="") as f:
        for r in csv.DictReader(f):
            if r["dest"]:
                counts[int(r["dest"], 16)] += 1
    halves, accum = half_index(d), accumulator_index(d)
    return [row_for(d, dest, n, halves, accum)
            for dest, n in counts.most_common()]


def csv_table(rows: list) -> str:
    """The `--csv` table, as a string rather than a write, because `--check`
    diffs the same bytes this prints."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for row in rows:
        w.writerow([row[c] for c in COLUMNS])
    return buf.getvalue()


def blind_spots(d: bytes) -> list:
    """(name, column, what, misses, population) for each cell sweep.

    A method's population is printed beside its miss conditions because a blind
    spot stated without a size is not one. "DPTR can be built in registers" is a
    shrug; "the PD image has N sites naming `0x82`/`0x83` through this method,
    of which M reach a cell this census names" is a boundary a reader can judge.
    """
    lo, hi = pd_span()
    hi = min(hi, len(d))

    def in_pd(pred):
        return sum(1 for i in range(lo, hi) if pred(i))

    populations = {
        "mov-dptr": in_pd(lambda i: i + 3 <= hi and d[i] == MOV_DPTR),
        "dptr-halves": in_pd(lambda i: i + 3 <= hi
                             and d[i] == MOV_DIRECT_IMM
                             and d[i + 1] in (DPL, DPH)),
        "dptr-from-accumulator": in_pd(lambda i: i + 2 <= hi
                                       and d[i] == MOV_A_IMM),
    }
    return [(name, col, what, misses, populations[name])
            for name, col, what, misses in METHODS]


def entries(d: bytes) -> list:
    """(target, opcode label, count) for every entry spelling into the helper.

    The fourth sweep, and the reason it has no column: an entry's destination
    arrives in a register, so it does not name a cell and cannot be counted per
    one. What it *can* be counted as is the number of ways into the helper,
    which is the population fact the committed census's own total is one reading
    of -- `12 10 4d` finds the `lcall 0x104D` form alone, and this is what the
    other three spellings add.

    Split by opcode because the two are not the same shape: `lcall` returns and
    so carries its four inline bytes, `ljmp` does not return and carries none,
    and lumping them into one row would hide that the second kind has no
    argument block for a reader to be surprised about.
    """
    lo, hi = pd_span()
    out = []
    for target in (TRAMPOLINE,) + FORWARDERS:
        for op, label in ((0x12, "lcall"), (0x02, "ljmp")):
            offs = [o for o in helper_entries(d, target) if d[o] == op]
            out.append((target, label, len(offs),
                        sum(1 for o in offs if lo <= o < hi)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-cell table as CSV on stdout instead of "
                         "the summary")
    ap.add_argument("--blind-spots", dest="blind", action="store_true",
                    help="print each method's population and its miss "
                         "conditions, instead of the summary")
    ap.add_argument("--check", nargs="?", const=READERS_CSV, metavar="PATH",
                    help="diff this run against the committed table and exit "
                         f"non-zero on any difference (default: {repo_path(READERS_CSV)})")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- the "
              "pd region is unidentified, so a site in it cannot be told "
              "from the\nmain EC's and every count below would be a blend\n",
              file=sys.stderr)
        return 1

    if args.blind:
        print("The three sweeps that name a cell, each with the population it "
              "sees in the\nPD image and what it cannot find.  The first is the "
              "one\n`trace_xdata_refs.py --counts-only` uses; the issue read "
              "its output as a reader\ncount, and this tool exists because that "
              "is a direction the count never resolves.\n")
        for name, col, what, misses, pop in blind_spots(d):
            print(f"  {name}  (column `{col}`)")
            print(f"    finds:  {what}")
            print(f"    sees:   {pop} candidate site(s) in the PD image")
            print(f"    blind:  {misses}\n")
        print(f"The fourth way in, which has no column because it does not name "
              "a cell:\n`lcall`/`ljmp` into "
              f"0x{TRAMPOLINE:04X} or a forwarder to it, taking the\n"
              "destination in registers.  An entry like that reaches a "
              "different cell at every\ncall, and no byte in the image says "
              "which, so it can be counted as an\nentry and not as a "
              "destination.\n")
        print(f"  {'target':>8}  {'form':<6} {'sites':>6}  {'of which pd-image':>18}")
        for target, label, n, pd_n in entries(d):
            print(f"  0x{target:04X}  {label:<6} {n:>6}  {pd_n:>18}")
        print("\nA consumer reached some other way -- a computed jump, a "
              "dispatch table, a pointer\nbuilt by arithmetic and carried "
              "across instructions -- is found by none of\nthese four, and no "
              "zero here says otherwise.")
        return 0

    try:
        rows = census(d)
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if not rows:
        print(f"note: {repo_path(SITES_CSV)} names no destination cell, which "
              "is not a population to census\n", file=sys.stderr)
        return 1

    generated = csv_table(rows)
    if args.check is not None:
        return check_table(generated, args.check)
    if args.csv:
        sys.stdout.write(generated)
        return 0

    totals = collections.Counter()
    for row in rows:
        totals["deposits"] += row["deposits"]
        totals["sites"] += row["mov_dptr_sites"]
        totals["reads"] += row["mov_dptr_reads"]
        totals["writes"] += row["mov_dptr_writes"]
        totals["halves"] += row["dptr_halves"]
        totals["accum"] += row["dptr_from_accumulator"]
        totals["pd_reads"] += row["pd_side_reads"]

    print("Every cell `lcall 0x104D` deposits into, and what the three cell "
          "sweeps\nfind naming it.  Split by program and by direction, because "
          "the blend of the\ntwo is the misreading this tool is here to "
          "correct.\n")
    print(f"{'cell':>8} {'deposits':>9} {'MOV DPTR':>9} {'read':>5} {'write':>6} "
          f"{'halves':>7} {'A':>3}  where")
    for row in rows:
        print(f"{row['dest']:>8} {row['deposits']:>9} "
              f"{row['mov_dptr_sites']:>9} {row['mov_dptr_reads']:>5} "
              f"{row['mov_dptr_writes']:>6} {row['dptr_halves']:>7} "
              f"{row['dptr_from_accumulator']:>3}  "
              f"{row['mov_dptr_by_region'] or '--'}")
    print(f"\nOver every cell named by the committed census: "
          f"{totals['deposits']} deposits,\n{totals['sites']} direct `MOV "
          f"DPTR` site(s) -- {totals['reads']} read, {totals['writes']} write --\n"
          f"{totals['halves']} immediate-half pair(s) and "
          f"{totals['accum']} accumulator-built site(s) naming them\n"
          f"anywhere in the PD image.  **{totals['pd_reads']} of all of that is "
          "a read inside the PD image.**\n")
    print("**Read per row, never summed across programs.** A site in `bank0` is "
          "the main\nEC's own register of that number, a different program with "
          "its own XDATA map\n(`../annotations/pd-xdata-overlap.md`), and it is "
          "not a consumer of what the PD\nimage writes there.  The `where` "
          "column is what says which is which, and a read\nin another program "
          "is not a zero for this one.\n")
    print("Per row, why the read column says what it says:\n")
    for row in rows:
        print(f"  {row['dest']}  {row['reason']}")
    print("\nA fourth way in has no column because it does not name a cell: "
          "`lcall`/`ljmp` into\n"
          f"0x{TRAMPOLINE:04X} or a forwarder, taking the destination in "
          "registers.  `--blind-spots`\nprints it beside the population it "
          "sees.\n")
    print(f"`--blind-spots` prints what each sweep cannot find, "
          f"`{repo_path(READERS_CSV)}`\nis this table (`--check` reproduces "
          "it), and the second, independent\ncensus -- built from the "
          "decompile rather than from a byte scan -- is\n"
          "../annotations/xdata-registers.csv.  The write-up is\n"
          "../../docs/findings/pd-inline-arg-readers.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())