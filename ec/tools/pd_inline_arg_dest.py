#!/usr/bin/env python3
"""`pd-inline-arg-sites.csv`'s `dest` column derived by decoding backward from
each call, where it was derived by scanning backward for a byte pattern.

`pd_inline_arg_sites.dptr_before()` finds the nearest preceding `90 xx xx` within
`DPTR_SCAN` bytes. That is a byte scan, and its own docstring says so: it cannot
tell a `mov dptr,#imm16` from the same three bytes inside another instruction. 64
of the 458 rows find nothing in range and write an **empty** `dest` cell, which a
reader has to know is "not found by this scan" rather than "there is none" -- and
`../../docs/findings/pd-inline-arg-trampoline.md` §5 says so in prose, where a
reader looking at the CSV will not see it.

This tool replaces the scan with a decode, for the rows and only: every
candidate start offset in `REACH` bytes before the call is decoded forward with
`disasm8051.OPCODE_LEN`, stepping over an `INLINE_ARG_CALLS` argument block or a
`CASE_TABLE_CALLS` table exactly as `converges_from()` does. A start that lands
**exactly** on the call is a walk that reaches it; one that steps over it is not.
The `mov dptr,#imm16` in force at the call is the last one such walk decodes
before it, which is the answer `dptr_before()` was approximating.

**Two things this reads from the image and not from the table.** `dptr_before()`
is not called and `pd-inline-arg-sites.csv`'s `dest` and `dptr_gap` columns are
not read, so this tool's rows are derived from the firmware and could in
principle disagree with the committed column; `../tools/test_pd_inline_arg_dest.py`
asserts that it does not, from the image rather than by re-running the scan. The
population is read from the table, because which calls to decode is a census
result and re-deriving it here would be a second claim about one entry spelling
-- `pd_inline_arg_sites.py`'s, which is `12 10 4d` and counts `lcall` only.

**The reach is a parameter, and the ambiguity is what it buys.** There is no
terminator to stop at: a run of straight-line code has no backward edge to find,
so "how far back to look" is a choice and not a derivation. `REACH` below is 64
because that is where the rows this tool exists to fix stop appearing, and the
tool prints the whole recovery curve beside the default so a reader can see the
figure is a function of that number rather than a property of the firmware. Two
rows' answers move if it moves, which is why `decoded-ambiguous` is a token
rather than a value.

**A disagreement between walks is reported, never resolved.** Two walks that both
reach the call can each decode a `mov dptr` and disagree about which is in force
-- one starts inside what is to another an instruction. Picking the nearer, or
the more common, or the one that agrees with the committed table, would be three
ways of dressing a coin flip as a measurement. Such a row gets
`decoded-ambiguous` and both candidates, and that is the whole answer.

**Empty is a token, never a blank.** A row whose walks carry no `mov dptr` gets
`no-mov-dptr-on-converging-walk`, and a row no walk reaches at all gets
`no-converging-walk`. Both are the explicit "not done by this method" the
`trace_xdata_refs` docstring argues for against a blank that reads as agreement,
and neither is ever rendered as an empty cell.

This is a linear decode and no more. It does not follow branches, does not know
which function a site is in, and does not decide which of two framings is the
real one -- `../../ec/README.md`, "toolchain proven, not attempted". Every row
here is a static reading of bytes.

Usage:
    python3 pd_inline_arg_dest.py ../firmware/GMxMGxx_11.800
    python3 pd_inline_arg_dest.py ../firmware/GMxMGxx_11.800 --reach-sweep
    python3 pd_inline_arg_dest.py ../firmware/GMxMGxx_11.800 --csv > ../annotations/pd-inline-arg-dest.csv
    python3 pd_inline_arg_dest.py ../firmware/GMxMGxx_11.800 --check
"""
import argparse
import collections
import csv
import io
import os
import sys

from disasm8051 import OPCODE_LEN, case_table_len, inline_arg_len
from trace_xdata_refs import PD_MARKER, check_table, repo_path

HERE = os.path.dirname(os.path.abspath(__file__))
SITES_CSV = os.path.join(HERE, os.pardir, "annotations",
                         "pd-inline-arg-sites.csv")
DEST_CSV = os.path.join(HERE, os.pardir, "annotations",
                        "pd-inline-arg-dest.csv")

# How far back a walk is allowed to start, in bytes. A parameter and not a
# derived quantity -- there is no backward edge in straight-line code to stop
# at -- so it is stated here, printed by `--reach-sweep`, and carried in no cell
# of the table. 64 is where the recovery of the rows this tool exists to fix
# flattens; the sweep is what lets a reader check that rather than take it.
REACH = 64
# The reaches `--reach-sweep` prints. The default is one of them, so the curve
# and the table cannot be about different numbers.
SWEEP = (32, 48, 64, 80, 96, 128, 192)

COLUMNS = ["file_offset", "runtime", "walks_converging", "mov_dptr_sites",
           "dest_decoded", "dest_reason", "dest_candidates"]

# The four tokens a row's `dest_reason` can carry. Named constants because they
# are the per-row accounting the write-up's figure is built from, and a bare
# string spelled in several places is several chances to write one of them two
# ways.
NO_WALK = "no-converging-walk"
NO_DPTR = "no-mov-dptr-on-converging-walk"
AMBIGUOUS = "decoded-ambiguous"
UNIQUE = "decoded-unique"


def walk_to(d: bytes, start: int, target: int):
    """Instruction offsets from `start` to `target`, or None if it misses.

    None for a walk that steps *over* `target` as well as for one that runs out
    of buffer: a run that passed the call without landing on it is a different
    framing, and calling that a walk that reached it is the mistake
    `converges_from()`'s `onto`/`over` pair exists to keep apart.

    `inline_arg_len()` and `case_table_len()` are stepped over for the reason
    `converges_from()` steps over them: a walk that decoded a four-byte argument
    block as instructions is misframed from there on, and every row behind one
    would report a `mov dptr` that is not one.

    **The `start` bounds check is here rather than left to the caller.**
    `decode_row()` breaks out of its own loop when the start goes negative, but
    a helper that IndexErrors on a start its caller's loop happened to stop
    short of is the latent-hole shape `trace_xdata_refs.is_dptr_rebuild()`
    documents for the same operand, and a test that sweeps the whole reach
    reaches it. One comparison, and the function answers None for a start that
    is not in the buffer rather than raising.
    """
    insns = []
    i = start
    while i < target:
        if i < 0 or i >= len(d):
            return None
        n = OPCODE_LEN[d[i]]
        if i + n > len(d):
            return None
        insns.append(i)
        i += n + inline_arg_len(d, i) + case_table_len(d, i)
    return insns if i == target else None


def dptr_in_force(insns: list, d: bytes):
    """The last `mov dptr,#imm16` on a walk, and its offset, or (None, None).

    Last rather than first because the question is which pointer is live *at the
    call*: a run that loads DPTR twice has the second load in force, and taking
    the first would answer a question about the start of the run instead.
    """
    at = None
    value = None
    for i in insns:
        if d[i] == 0x90 and i + 3 <= len(d):
            at = i
            value = (d[i + 1] << 8) | d[i + 2]
    return at, value


def decode_row(d: bytes, off: int, reach: int = REACH) -> dict:
    """One row's backward decode, as a dict keyed by `COLUMNS`.

    Every converging walk contributes the DPTR *it* leaves in force; the row's
    value is the one they all agree on. Two walks that agree are not two
    confirmations -- a walk starting one byte later usually contains the same
    instructions -- so the row reports the count and the token, not a
    confidence.

    **Agreement is tested on the destination, not on the loaded DPTR** -- and
    the destination *is* the loaded DPTR, unchanged.

    It used not to be. Reading the byte at `0x104D` as `mov r0,#0x82` made the
    helper overwrite the caller's low byte with that literal, so
    `mov dptr,#0x0A98` and `mov dptr,#0x0A82` were two spellings of the same
    deposit and agreement was tested on the high byte alone. Read as
    `mov r0,0x82` -- a `direct` address, `DPL` -- the helper saves the caller's
    DPTR into R0:B and restores it before the store, so the low byte is the
    caller's own and there is nothing to substitute. The destination and the
    load are now the same number, and the candidates below are keyed on the
    loaded DPTR directly.

    Two walks that disagree on that number have disagreed about what this tool
    answers, so they are `decoded-ambiguous` rather than being folded together
    on their high byte. `mov_dptr_sites` still records every load's offset, so
    the disagreement stays visible.
    """
    converging = []
    for back in range(1, reach + 1):
        start = off - back
        if start < 0:
            break
        insns = walk_to(d, start, off)
        if insns is not None:
            converging.append(insns)

    candidates = collections.Counter()
    loads = set()
    for insns in converging:
        at, value = dptr_in_force(insns, d)
        if value is not None:
            loads.add(at)
            candidates[value] += 1

    decoded = ""
    if not converging:
        reason = NO_WALK
    elif not candidates:
        reason = NO_DPTR
    elif len(candidates) == 1:
        reason = UNIQUE
        decoded = f"0x{candidates.most_common(1)[0][0]:04X}"
    else:
        # Sorted so the cell is a function of the row and not of walk order,
        # which a table reproduced byte for byte cannot depend on.
        reason = AMBIGUOUS

    return {
        "walks_converging": len(converging),
        "mov_dptr_sites": "|".join(f"0x{i:05X}" for i in sorted(loads)),
        "dest_decoded": decoded,
        "dest_reason": reason,
        "dest_candidates": "|".join(f"0x{v:04X}x{c}"
                                    for v, c in sorted(candidates.items())),
    }


def read_sites(path: str) -> list:
    """The committed call population, as `(file_offset, runtime)` pairs.

    Read rather than re-derived, and the reason is the write-up's: the census
    scans for `12 10 4d`, which is one spelling of the entry. `lcall 0x107E` and
    `lcall 0x1098` reach the same helper with the destination built in registers
    and are in none of those 458 rows. Widening the population is a change to
    that file's claim, filed as its own follow-up; this tool decodes the rows
    that exist."""
    with open(path, newline="") as f:
        return [(int(r["file_offset"], 16), int(r["runtime"], 16))
                for r in csv.DictReader(f)]


def rows(d: bytes, reach: int = REACH) -> list:
    out = []
    for off, runtime in read_sites(SITES_CSV):
        row = decode_row(d, off, reach)
        row["file_offset"] = f"0x{off:05X}"
        row["runtime"] = f"0x{runtime:04X}"
        out.append({c: row[c] for c in COLUMNS})
    return out


def csv_table(rows: list) -> str:
    """The `--csv` table, as a string rather than a write, because `--check`
    diffs the same bytes this prints."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for row in rows:
        w.writerow([row[c] for c in COLUMNS])
    return buf.getvalue()


def by_dest(rows: list) -> collections.Counter:
    """Decoded destinations, most common first.

    Over the *decoded* value rather than the committed `dest`, because that is
    the column this tool produces and the figure the write-up quotes is about
    it. A row with no value contributes nothing, which is why the summary prints
    the reason tally beside this one rather than letting the two be read as
    halves of a population."""
    c = collections.Counter(r["dest_decoded"] for r in rows if r["dest_decoded"])
    return c


def sweep(d: bytes) -> list:
    """(reach, unique, ambiguous, none) for each reach in `SWEEP`.

    The recovery curve, so the default's figure is a point on a curve rather
    than a bare number. The column that matters for reading it is `unique`: it
    rises with the reach and would keep rising, because a long enough walk
    eventually reaches back to *some* `mov dptr` whether or not the framing is
    real. A reader deciding whether to trust a row's value should be asking
    where the curve flattens, and that is what this prints."""
    out = []
    for reach in SWEEP:
        c = collections.Counter(r["dest_reason"] for r in rows(d, reach))
        out.append((reach, c[UNIQUE], c[AMBIGUOUS],
                    c[NO_DPTR] + c[NO_WALK]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-row decode as CSV on stdout instead of "
                         "the summary")
    ap.add_argument("--reach-sweep", dest="sweep", action="store_true",
                    help="print the recovery curve over several backward reaches, "
                         "instead of the summary")
    ap.add_argument("--check", nargs="?", const=DEST_CSV, metavar="PATH",
                    help="diff this run against the committed table and exit "
                         f"non-zero on any difference (default: {repo_path(DEST_CSV)})")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- the "
              "pd region is unidentified, so the calls in it cannot be told "
              "from the main EC's\n", file=sys.stderr)
        return 1

    try:
        population = read_sites(SITES_CSV)
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if not population:
        print(f"note: {repo_path(SITES_CSV)} has no rows, which is not a "
              "population to decode\n", file=sys.stderr)
        return 1

    generated = csv_table(rows(d))
    if args.check is not None:
        return check_table(generated, args.check)
    if args.csv:
        sys.stdout.write(generated)
        return 0

    if args.sweep:
        curve = sweep(d)
        print("Backward reach against what it recovers.  The reach is a "
              "parameter --\nstraight-line code has no backward edge to stop at "
              "-- so this is the curve the\ndefault sits on, not a property of "
              "the firmware.  A row is only ever\ndecoded from walks that land "
              "*exactly* on its call.\n")
        print(f"{'reach':>6}  {'decoded-unique':>15}  {'ambiguous':>10}  "
              f"{'no value':>9}")
        for reach, uniq, amb, none in curve:
            mark = "  <- default" if reach == REACH else ""
            print(f"{reach:>6}  {uniq:>15}  {amb:>10}  {none:>9}{mark}")
        default = next(row for row in curve if row[0] == REACH)
        print(f"\n{default[1] + default[2]} rows carry a value at the default "
              f"reach and {default[3]} carry none, which\nis 'not found by this "
              "decode' and not 'there is none'.  `decoded-unique`\nkeeps rising "
              "with the reach and would keep rising, because a long\nenough walk "
              "reaches *some* `mov dptr` whether or not the framing is\nreal: "
              "what flattens is the recovery of the rows the scan missed,\n"
              "which is what the default was chosen for.")
        return 0

    rs = rows(d)
    reasons = collections.Counter(r["dest_reason"] for r in rs)
    dests = by_dest(rs)
    resolved = reasons[UNIQUE] + reasons[AMBIGUOUS]

    print(f"The {len(rs)} rows of {repo_path(SITES_CSV)}, each decoded backward "
          f"from its call\nover {REACH} bytes.  A walk is counted only if it "
          "lands exactly on the call,\nand a value only if every walk that "
          "carries a `mov dptr` agrees on it.\n")
    print(f"{resolved} of {len(rs)} carry a value "
          f"({reasons[UNIQUE]} agreeing, {reasons[AMBIGUOUS]} not),\n"
          f"and {reasons[NO_DPTR]} carry no `mov dptr` on any converging walk "
          f"and {reasons[NO_WALK]} have no walk that\nreaches the call at "
          f"all.  Both are 'not found by this method', never 'there is "
          "none'.\n")
    print("Why each row has the value it has:\n")
    for reason, n in reasons.most_common():
        print(f"  {n:>4}  {reason}")
    print("\nThe decoded destinations, most common first.  Each is the DPTR "
          "the caller\nloaded, unchanged: `mov r0,0x82` reads its operand as "
          "the direct address\n`DPL`, so the helper saves the caller's DPTR "
          "into R0:B and restores it\nbefore the store rather than "
          "substituting a literal for the low byte.\n")
    for dest, n in dests.most_common():
        print(f"  {n:>4}  {dest}")
    print(f"\n`--reach-sweep` prints the curve this sits on, and "
          f"{repo_path(DEST_CSV)}\nis the per-row table holding it "
          "(`--check` reproduces it).  The scan this\nreplaces, and the prose "
          "behind its empty cells, are in\n"
          "../../docs/findings/pd-inline-arg-trampoline.md 5 and\n"
          "../../docs/findings/pd-inline-arg-readers.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())