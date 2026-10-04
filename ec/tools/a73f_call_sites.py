#!/usr/bin/env python3
"""Every transfer into `0xA73F` in the EC image, and the value each site
loads into R7 first.

`0xA73F` is a four-instruction routine (`store_r7_at_6a_then_jump_1666`) that
takes the byte in R7 and pushes it into the `0x09F1` mailbox ring in bank1 --
`docs/findings/a73f-09f1-mailbox-payload.md` is the walk. Until this existed
the sites were known only as far as the eight `mov R7,#imm` pairs a reader
could see in the committed `.asm` listings, which is a listing-derived
population: it cannot see a site no listing covers, and it cannot see a site
reached by a tail jump.

**The population is the committed census, not a byte scan of `12 a7 3f`.**
`audit_call_targets.py` already enumerates every direct `lcall`/`ljmp` in the
image into `ec/annotations/bank-call-targets.csv`, and reading that table is
what `a5e6_quotient.py` and `code_table_records.py` both do, for the reason
`a5e6_quotient.py` states: re-running the scan here would assert this tool
against itself. It would also answer a strictly smaller question. The opcode
`12` is `lcall` only; four of the transfers into `0xA73F` are `02` -- `ljmp`
tail calls, where the site pushes no return address of its own -- and a
`12 a7 3f` scan is blind to every one of them. Reading the census is also what
brings each site's `bucket` and `own_bank`/`other_bank` framing verdict with
it, which is the answer to "is this byte really an instruction here" that a
raw byte scan would have to re-argue from scratch.

**A new file rather than a column on `audit_call_targets.py`, for the reason
`computed_dptr_sites.py` states for itself.** That tool's `--csv` output is
`bank-call-targets.csv` byte for byte, and it is the table the rest of the
repository quotes; a new column would change the meaning of a file several
other tools re-derive, without changing any value in it. `r7` here is a
question about R7 alone.

**The `r7` column is a backward BYTE-PATTERN scan, and says so.** `r7` is the
nearest `7f nn` byte pair at or before the site within `WINDOW` bytes and
`r7_gap` is how far back it was found, so a gap of 2 -- the pair immediately
preceding the three-byte transfer -- can be told from a gap of 44. This is not
a decoded backward walk and not control-flow recovery, exactly as
`pd_inline_arg_sites.py` states for its own `dptr_load`: an intervening
branch can write R7 without the `7f` pair being wrong, and `r1r2_predecessor.py`'s
docstring is the longer argument against the linear form.

**A pair further back than the adjacent instruction is only reported when a
forward branch corroborates it.** A bare `7f nn` at some distance is a weak
reading on its own, because the nearer pairs in this image include ones that
belong to a *different* dispatch entirely -- `0xC827` is `mov r7,#0x12` in a
run of `7f nn` / `lcall 0x2990` pairs that tail-jumps away at `0xC829`, and
nothing joins it to the site. So a non-adjacent pair is reported only if a
forward branch (`sjmp` or `ljmp`) sits between the pair and the site and
targets the site exactly; `r7_branch` records that branch. The check is what
turns the gap-44 readings at `0xC5A5` and `0xC603` into evidence -- each is
reached by an `sjmp` that immediately follows its own `mov R7,#imm` -- while
`0xC848`, which no branch targets, stays empty. Widening the window without
this would publish `0x12` for `0xC848`, a value the image does not support.

The branch check is itself a byte scan, so `r7_branch` is corroboration and
not a decode; the listings cited in the write-up are what settle each one. A
site with no corroborated pair in range gets an empty cell, which is **"not
found by this scan"** and never "R7 was left alone".

Usage:
    python3 a73f_call_sites.py ../firmware/GMxMGxx_11.800
    python3 a73f_call_sites.py ../firmware/GMxMGxx_11.800 --csv
    python3 a73f_call_sites.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))

TARGET = 0xA73F
TARGET_CSV = os.path.join("ec", "annotations", "bank-call-targets.csv")

# How far back the `mov R7,#imm` scan looks. It has to reach past 44, the
# distance to the `0xB1` and `0xB2` loads that `sjmp` into `0xC5A5` and
# `0xC603`; a narrower window reports those two sites as unresolved, which is
# the same as claiming the image holds no `mov R7` for them. It is deliberately
# wider than 44 so the choice is not tuned to the two sites that need it.
WINDOW = 64

MOV_R7_IMM = 0x7F  # `mov Rn,#imm` is 0x78-0x7F; 0x7F is Rn = R7.
SJMP = 0x80
LJMP = 0x02

COLUMNS = ("region", "runtime", "opcode", "file_offset", "r7", "r7_gap",
           "r7_at", "r7_branch")


def targets_csv_path(repo: str = REPO) -> str:
    return os.path.join(repo, TARGET_CSV)


def read_census(path: str, target: int = TARGET):
    """Every row of the committed transfer census aimed at `target`.

    The census is read, never regenerated: see the module docstring.
    """
    wanted = f"0x{target:04x}"
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["target"].lower() == wanted:
                rows.append(row)
    rows.sort(key=lambda r: int(r["runtime"], 16))
    return rows


def nearest_mov_r7(data: bytes, site: int, window: int = WINDOW):
    """`(value, gap, address)` of the nearest `7f nn` before `site`.

    `gap` is the distance back from the site to the opcode byte, so the pair
    that immediately precedes a three-byte transfer reads as 2. `(None, None,
    None)` is "not found within the window".
    """
    for gap in range(2, window + 1):
        at = site - gap
        if at < 0:
            break
        if data[at] == MOV_R7_IMM:
            return data[at + 1], gap, at
    return None, None, None


def branch_into(data: bytes, site: int, low: int):
    """`at` of a forward branch in `(low, site)` whose target is `site`.

    The corroboration `rows_for` requires of a non-adjacent pair: a branch
    that reaches the site from after the pair is what distinguishes a load
    this site arrives on from one that merely sits nearby in the byte
    stream. Scans `sjmp` (relative) and `ljmp` (absolute) over the same
    window the pair was found in.

    Returns the branch nearest the site, or `None` when no branch targets it.
    """
    found = None
    for at in range(max(low, 0), site - 2):
        op = data[at]
        if op == SJMP:
            rel = data[at + 1]
            if rel > 127:
                rel -= 256
            target = at + 2 + rel
        elif op == LJMP:
            target = (data[at + 1] << 8) | data[at + 2]
        else:
            continue
        if target == site:
            found = at
    return found


def rows_for(data: bytes, census, window: int = WINDOW):
    """The reported table: one row per transfer site, plus its R7 reading.

    A pair adjacent to the transfer (gap 2) is reported as it stands. A pair
    further back is reported only when `branch_into` finds a forward branch
    from after it to the site; an uncorroborated pair is dropped rather than
    published, which is what keeps `0xC848` empty instead of reading
    `0x12` out of an unrelated dispatch table.
    """
    out = []
    for row in census:
        site = int(row["file_offset"], 16)
        value, gap, at = nearest_mov_r7(data, site, window)
        branch = None
        if value is not None and gap > 2:
            branch = branch_into(data, site, at)
            if branch is None:
                value = gap = at = None
        out.append({
            "region": row["region"],
            "runtime": row["runtime"],
            "opcode": row["opcode"],
            "file_offset": row["file_offset"],
            "r7": "" if value is None else f"0x{value:02X}",
            "r7_gap": "" if gap is None else str(gap),
            "r7_at": "" if at is None else f"0x{at:04X}",
            "r7_branch": "" if branch is None else f"0x{branch:04X}",
        })
    return out


def csv_table(rows) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(COLUMNS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def report(data: bytes, rows) -> None:
    by_op = collections.Counter(r["opcode"] for r in rows)
    by_region = collections.Counter(r["region"] for r in rows)
    resolved = [r for r in rows if r["r7"]]
    gaps = collections.Counter(r["r7_gap"] for r in resolved)
    values = collections.Counter(r["r7"] for r in resolved)

    print(f"{len(rows)} transfers into 0x{TARGET:04X} in the committed census. "
          f"A raw `12 a7 3f`\nbyte scan finds the {by_op.get('lcall', 0)} "
          f"`lcall` ones and none of the {by_op.get('ljmp', 0)} `ljmp` tail "
          "calls.\n")
    print("  region     site(s)")
    for region, n in sorted(by_region.items()):
        print(f"  {region:<9} {n:>7}")
    print("  opcode     site(s)")
    for opcode, n in sorted(by_op.items()):
        print(f"  {opcode:<9} {n:>7}")

    corroborated = [r for r in rows if r["r7_branch"]]
    print(f"\n{len(resolved)} of them carry an R7 reading; "
          f"{len(rows) - len(resolved)} do not. "
          f"{len(corroborated)} of the readings sit further back than the\n"
          "adjacent instruction and are held to a forward branch that "
          "reaches the site.\n")
    print("  runtime  opcode  r7     gap  r7_at      branch")
    for r in rows:
        print(f"  {r['runtime']:>6}  {r['opcode']:<6}  {r['r7'] or '-':<6} "
              f"{r['r7_gap'] or '-':>3}  {r['r7_at'] or '-':<9} "
              f"{r['r7_branch'] or '-'}")

    print("\n  gap      site(s)   (bytes back from the transfer to `7f`)")
    for gap in sorted(gaps, key=int):
        print(f"  {gap:<8} {gaps[gap]:>7}")
    print("  A gap of 2 is the pair immediately preceding the transfer. A "
          "larger\n  gap is reported only where the `branch` column names a "
          "forward branch\n  landing on the site from after the pair; "
          "without one it is dropped rather\n  than published. The column "
          "is what tells the two apart.\n")

    print("  r7       site(s)")
    for value in sorted(values):
        print(f"  {value:<8} {values[value]:>7}")
    unresolved = [r["runtime"] for r in rows if not r["r7"]]
    print(f"\n  {len(unresolved)} site(s) have no corroborated pair in range "
          f"and read as\n  not-found: {', '.join(unresolved)}. That is a "
          "limit of the method, not a\n  statement that R7 is unchanged "
          "there.")


def self_test(data: bytes, census) -> int:
    """The invariants a CSV diff cannot see.

    The table's own reproducibility is `--csv`; what sits under it is that
    each `file_offset` still decodes to the transfer the row claims, that a
    non-adjacent R7 reading is held to a real branch decoded out of the image,
    and that the backward scan is a function of the bytes rather than of the
    site happening to sit where it does. The last two are checked against the
    image and against fixtures, because the image's far pairs are all
    corroborated and so never exercise the branch check's negative case -- a
    case only a fixture can reach is a case nothing tests.
    """
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    OPCODE_LEN = {"lcall": 3, "ljmp": 3}
    for row in census:
        site = int(row["file_offset"], 16)
        length = OPCODE_LEN[row["opcode"]]
        raw = data[site:site + length]
        want = bytes([0x12 if row["opcode"] == "lcall" else 0x02]) + \
            TARGET.to_bytes(2, "big")
        check(raw == want,
              f"{row['runtime']} still decodes to {row['opcode']} "
              f"0x{TARGET:04X} ({raw.hex(' ')})")

    check(bool(census), "the census records at least one transfer into the "
                        "target")
    check(all(r["region"] in ("common", "bank0", "bank1")
              for r in census),
          "every site is in the main EC's code regions")

    rows = rows_for(data, census)
    farther = [r for r in rows if r["r7"] and r["r7_gap"] != "2"]
    check(all(r["r7_gap"] == "2" or r["r7_branch"] for r in rows if r["r7"]),
          "every R7 further back than the adjacent instruction is held to a "
          "forward branch that reaches its site")
    check(bool(farther),
          "the committed image still exercises the non-adjacent reading, so "
          "the branch check is not dead code here")

    # Each non-adjacent reading must be a real branch, decoded from the image,
    # landing exactly on the site its row reports.
    for r in farther:
        at = int(r["r7_at"], 16)
        br = int(r["r7_branch"], 16)
        op = data[br]
        rel = data[br + 1]
        if rel > 127:
            rel -= 256
        target = (br + 2 + rel) if op == SJMP else \
            (data[br + 1] << 8) | data[br + 2]
        check(op in (SJMP, LJMP) and at < br < int(r["file_offset"], 16)
              and target == int(r["file_offset"], 16),
              f"{r['runtime']}: the branch at 0x{br:04X} follows the load at "
              f"0x{at:04X} and targets the site")

    # A `7f` that is an operand byte rather than an opcode: the scan cannot
    # tell the two apart, and a fixture is the only place that is visible.
    fixture = bytearray(b"\x00" * 64)
    fixture[42:44] = b"\x7f\x5a"          # an adjacent `mov R7,#0x5A`
    fixture[10:12] = b"\x90\x7f"          # `7f` as the low byte of a DPTR load
    fixture[44:47] = b"\x12\xa7\x3f"
    value, gap, at = nearest_mov_r7(bytes(fixture), 44)
    check((value, gap, at) == (0x5A, 2, 42),
          f"the adjacent pair wins over the older operand byte (got "
          f"{value!r} at gap {gap})")

    bare = bytes(b"\x00" * 64)
    value, gap, _at = nearest_mov_r7(bare, 44)
    check(value is None and gap is None,
          "a site with no pair in range reads as not-found, not as a value")

    beyond = bytearray(b"\x00" * 64)
    beyond[40:42] = b"\x7f\x11"
    value, gap, _at = nearest_mov_r7(bytes(beyond), 8, window=32)
    check(value is None,
          "a pair further back than the window is not read, rather than "
          "widening the window to reach it")

    # The branch check is what stops a widened window publishing a load that
    # belongs to a different dispatch: a far pair with nothing branching to
    # the site is dropped, and the same pair *is* kept once a branch exists.
    unlinked = bytearray(b"\x00" * 64)
    unlinked[10:12] = b"\x7f\x12"
    unlinked[44:47] = b"\x12\xa7\x3f"
    census_row = [{"region": "bank0", "runtime": "0x002C",
                   "opcode": "lcall", "file_offset": "0x0002C"}]
    check(rows_for(bytes(unlinked), census_row, window=64)[0]["r7"] == "",
          "a far pair that no branch delivers to the site is dropped, not "
          "published")
    check(branch_into(bytes(unlinked), 44, 10) is None,
          "and the reason is that nothing branches to the site")

    linked = bytearray(unlinked)
    linked[12:14] = b"\x80\x1e"          # `sjmp` to 0x002C
    check(branch_into(bytes(linked), 44, 10) == 12,
          "a branch from after the pair to the site is found")
    check(rows_for(bytes(linked), census_row, window=64)[0]["r7"] == "0x12",
          "and with it the far pair is reported as corroborated")

    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware",
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout instead "
                         "of the report")
    ap.add_argument("--targets-csv", default=None, metavar="PATH",
                    help="the committed transfer census to read (default: "
                         f"{TARGET_CSV})")
    ap.add_argument("--window", type=int, default=WINDOW, metavar="N",
                    help=f"backward window in bytes for the R7 scan "
                         f"(default: {WINDOW})")
    ap.add_argument("--self-test", dest="self_test", action="store_true",
                    help="re-check the site framing and the R7 scan against "
                         "the image and a fixture")
    args = ap.parse_args()

    if args.self_test:
        data = open(args.firmware, "rb").read()
        return self_test(data, read_census(args.targets_csv or targets_csv_path()))

    data = open(args.firmware, "rb").read()
    census = read_census(args.targets_csv or targets_csv_path())
    rows = rows_for(data, census, args.window)
    if args.csv:
        sys.stdout.write(csv_table(rows))
        return 0
    report(data, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())