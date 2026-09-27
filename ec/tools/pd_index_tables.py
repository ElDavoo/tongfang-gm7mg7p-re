#!/usr/bin/env python3
"""Census the `switch` tables the `ITE8850-PD` image's own dispatchers consume,
the way `decode_index_table.py` censuses the main EC image's one reader.

The PD image at file `0x20000` is a separate program with its own copy of the
same compiler runtime, and `decode_index_table.py` deliberately excluded it:
its tables are not in the main EC's address space, so a census that mixed them
would be a count of two address spaces added together. What that exclusion left
is a question this tool asks instead -- whether the copy carries its own
readers, and if so what their tables are, because every table found this way is
more of the image reclassified from code to data.

**Nothing here re-implements the entry layout or the well-formedness checks.**
The shapes, `decode_table()`, `malformed()`, `census()` and `reader_call_sites()`
are imported from `decode_index_table.py`, and the region map from
`trace_xdata_refs.py`, so the PD reading and the main-EC reading of the same
prologue shape cannot drift apart. What is new here is the region selection, the
per-dispatcher grouping, the reconciliation against `pd_image_census.py`, and
the self-test.

**Two of the three dispatchers are not this family's layout, and saying so is
the point of `reader_stride`.** `decode_table()` reads 3-byte entries --
address, address, case -- because that is what the main EC reader at `0x7151`
does. The PD's `0x11C2` walks 4 bytes per entry and `0x11EF` walks 6, both
taking the pointer off the return address the same way, and the entry stride is
read off each reader's own body by `entry_stride()` rather than assumed. So a
`well_formed=no` row under `0x11C2` is a **failure of the main EC's rule, not a
verdict about that table** -- and so, in the two rows that pass it, is a
`well_formed=yes`. The column is there so a reader of the CSV is not misled,
not so a 4-byte table can be decoded with a 3-byte reader.

**What a PD well-formedness check is worth.** `malformed()` requires every
target and the default to resolve inside the caller's own region, which in the
main EC means *banked* -- below `0x8000` is common area, at or above it is the
caller's own bank. The PD image is flat, so `REGIONS` gives it base `0x0000` and
the same test only asks for a `0x0000`-`0xFFFF` CODE address. It is a weaker
check in the PD than it reads in the main EC, and the other two checks -- cases
strictly ascending, and the byte after the table being one of its own targets --
are unchanged.

**Nothing here is a live observation.** Every input is a committed file, no
register is read, no `status:` in `../annotations/registers.yaml` moves, and no
claim is made that any of these tables executes.

Usage:
    python3 ec/tools/pd_index_tables.py
    python3 ec/tools/pd_index_tables.py --spans-csv \
        > ec/annotations/pd-index-table-spans.csv
    python3 ec/tools/pd_index_tables.py --self-test
"""
import argparse
import collections
import csv
import os
import sys

from decode_index_table import (ENTRY_LEN, MAX_ENTRIES, PD_IMAGE,
                                PROLOGUE_BODY_INSNS, PROLOGUE_SHAPES,
                                SPAN_COLUMNS, census, direct_address_readers,
                                find_readers, lcalled_readers,
                                reader_call_sites)
from disasm8051 import decode
from pd_image_census import CODE_TABLE_DISPATCHERS, code_table_inline_tables
from trace_xdata_refs import PD_MARKER, REGIONS, region_of

HERE = os.path.dirname(os.path.abspath(__file__))
FIRMWARE = f"{HERE}/../firmware/GMxMGxx_11.800"

# Instructions decoded from a reader before giving up on its loop. A reader
# whose whole body is shorter than this has its stride found inside the bound
# anyway; the bound is here so a decode that finds no loop-back says so rather
# than running into the next routine.
READER_BODY_INSNS = 64

# The main EC's span columns, in its order and with its names, plus the two
# the PD needs in front of them: which dispatcher the site names, and that
# dispatcher's own entry stride.
PD_SPAN_COLUMNS = ["reader", "reader_stride"] + SPAN_COLUMNS

# The relative branches that close a reader's entry loop: `jnz` and `sjmp`.
# `jz` is excluded because these readers use it for the *dispatch* -- the
# branch taken on a key match, back into the routine's own head -- and reading
# that one's displacement would give the dispatch, not the stride.
LOOP_BRANCHES = (0x70, 0x80)
INC_DPTR = 0xA3


def entry_stride(d: bytes, off: int, limit: int) -> int:
    """Bytes one entry advances DPTR, read off `off`'s own loop.

    The reader walks entries by running a few `inc dptr` and branching back to
    the zero-test at its head, so the stride is the length of the `inc dptr` run
    that feeds the last `LOOP_BRANCHES` branch in its body. `limit` bounds the
    decode to this reader's own bytes: the PD's three dispatchers are adjacent,
    and a window that ran past one would read the next one's stride back.

    None when the decode finds no such branch inside the bound -- "not found by
    this method", and a caller that needs a number says so rather than
    defaulting to the main EC's 3."""
    insns = [x for x in decode(d, off, READER_BODY_INSNS) if x[0] < limit]
    back = None
    for n, (_, raw, _) in enumerate(insns):
        if raw[0] in LOOP_BRANCHES and raw[1] > 0x7F:
            back = n
    if back is None:
        return None
    run = 0
    for n in range(back - 1, -1, -1):
        if insns[n][1][0] != INC_DPTR:
            break
        run += 1
    return run


def pd_readers(d: bytes):
    """[(reader, sites, stride)] for every tier-2 candidate a caller names.

    A prologue candidate with no `lcall` naming it cannot have an inline table
    whatever its shape says, so it is not a reader here. The stride is read over
    a decode bounded by the *next tier-2 candidate's* file offset, which is what
    keeps one reader's loop out of the next reader's bytes."""
    cands = [r for r in find_readers(d, PD_IMAGE) if r["walks_table"]]
    out = []
    for r in lcalled_readers(d, PD_IMAGE):
        n = next(i for i, c in enumerate(cands) if c["file_offset"] == r["file_offset"])
        after = cands[n + 1]["file_offset"] if n + 1 < len(cands) else None
        limit = after if after is not None else r["file_offset"] + 0x100
        out.append((r, reader_call_sites(d, r["runtime"], PD_IMAGE),
                    entry_stride(d, r["file_offset"], limit)))
    return out


def pd_census(d: bytes):
    """[(reader, stride, site, table, reasons)] over every dispatcher, in
    reader order and then file order. The census, not a filtered view: a site
    that fails keeps its row, exactly as `index-table-spans.csv` does."""
    out = []
    for reader, sites, stride in pd_readers(d):
        for site, tbl, bad in census(d, sites):
            out.append((reader, stride, site, tbl, bad))
    return out


def well_formed(bad) -> str:
    return "yes" if not bad else "no"


def print_census(d: bytes, rows) -> None:
    print(f"{len(PROLOGUE_SHAPES)} prologue shape(s) over "
          f"{'/'.join(PD_IMAGE)}; a candidate is a reader here when an `lcall` "
          f"names it and its stride is read off its own loop")
    print()
    by_reader = collections.OrderedDict()
    for reader, stride, site, tbl, bad in rows:
        by_reader.setdefault((reader["runtime"], reader["shape"], stride), [])
        by_reader[(reader["runtime"], reader["shape"], stride)].append((tbl, bad))
    for (rt, shape, stride), items in by_reader.items():
        good = [i for i in items if i[0] is not None and not i[1]]
        note = "" if stride == ENTRY_LEN else (
            f"  -- not this family's {ENTRY_LEN}-byte entry, so the "
            "well-formedness column below is the main EC's rule applied to it "
            "and not a verdict about those tables")
        print(f"  reader 0x{rt:04X} ({shape}), {len(items)} `lcall` byte "
              f"site(s), {len(good)} well-formed under the {ENTRY_LEN}-byte "
              f"reading, stride {stride}{note}")
    print()
    print(f"  {len([r for r in rows if r[3] is not None and not r[4]])} of "
          f"{len(rows)} candidate site(s) are followed by a well-formed table")
    print()
    print("  reader  site      frame   entries  span              cases       "
          "stride  verdict")
    for reader, stride, site, tbl, bad in rows:
        if tbl is None:
            print(f"  0x{reader['runtime']:04X}  0x{site['file_offset']:05X}  "
                  f"{site['frame_onto']:2}/24   no terminator within "
                  f"{MAX_ENTRIES} entries")
            continue
        cases = [e["case"] for e in tbl["entries"]]
        span = f"0x{tbl['file_offset']:05X}-0x{tbl['end'] - 1:05X}"
        print(f"  0x{reader['runtime']:04X}  0x{site['file_offset']:05X}  "
              f"{site['frame_onto']:2}/24  {len(cases):7}  {span}  "
              f"0x{min(cases):02X}-0x{max(cases):02X}    {str(stride):>4}  "
              f"{well_formed(bad)}")
    total = sum(t["end"] - t["file_offset"] for _, _, _, t, b in rows if t and not b)
    print()
    print(f"  {total} bytes of the PD image read as table data by this method")
    direct = direct_address_readers(d, PD_IMAGE)
    print(f"  {len(direct)} direct-address candidate(s) -- `mov dptr,#imm16` "
          "then a table walk and `jmp @a+dptr`. Not this family, and decoded "
          "nowhere")
    print()


def write_spans_csv(rows) -> None:
    """One row per candidate `lcall` byte site, in `index-table-spans.csv`'s
    column contract with two columns in front of it.

    `reader` is which dispatcher the site names, because the PD has three and
    the main EC had one. `reader_stride` is that dispatcher's own entry stride,
    and it is what makes the `well_formed` column readable: the column is
    `decode_index_table.py`'s verdict under a {n}-byte reading, and it is only a
    statement about the table when the stride is {n}.

    **One deliberate difference from the main EC's file**, which is kept
    standing rather than quietly inherited: a site whose bytes reach a
    terminator keeps its span, entry count and case range even when the
    well-formedness checks fail, and only a site that never reaches one gets
    empty span fields. `index-table-spans.csv` blanks them for both, which
    costs it nothing -- all 15 of its rows pass -- and would cost this file 18
    of 28 rows, which is most of the reading. The rule the two files share is
    the one that matters: a site that fails keeps its row.""".format(n=ENTRY_LEN)
    w = csv.writer(sys.stdout)
    w.writerow(PD_SPAN_COLUMNS)
    for reader, stride, site, tbl, bad in rows:
        row = [f"0x{reader['runtime']:04X}", "" if stride is None else stride,
               f"0x{site['file_offset']:05X}", site["region"],
               f"0x{site['runtime']:04X}", site["frame_onto"],
               site["frame_over"]]
        if tbl is None:
            w.writerow(row + [""] * 7 + ["no"])
            continue
        cases = [e["case"] for e in tbl["entries"]]
        w.writerow(row + [
            len(tbl["entries"]), f"0x{tbl['file_offset']:05X}",
            f"0x{tbl['end']:05X}", f"0x{tbl['runtime']:04X}",
            f"0x{min(cases):02X}", f"0x{max(cases):02X}",
            f"0x{tbl['default']:04X}", well_formed(bad),
        ])


def self_test(d: bytes) -> int:
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    off, magic = PD_MARKER
    check(d[off:off + len(magic)] == magic,
          f"the {magic.decode()!r} marker is at file 0x{off:05X}, so the "
          "region is the PD image and not a gap")

    region_lo, region_hi = next((lo, hi) for n, lo, hi, _, _ in REGIONS
                                if n == "pd-image")
    check((region_lo, region_hi) == (0x20000, 0x30000)
          and region_of(region_lo, True)[0] == "pd-image"
          and region_of(region_hi - 1, True)[0] == "pd-image",
          "the region searched is `pd-image` at 0x20000-0x2FFFF, flat and "
          "64 KiB -- a runtime address here is not the main EC's at the same "
          "number")

    cands = find_readers(d, PD_IMAGE)
    per_shape = collections.Counter(r["shape"] for r in cands)
    check(per_shape == SHAPE_HITS and len(cands) == sum(SHAPE_HITS.values()),
          f"{len(cands)} tier-1 candidates over {len(PROLOGUE_SHAPES)} shapes: "
          + ", ".join(f"{k} {v}" for k, v in sorted(SHAPE_HITS.items()))
          + f" (got {dict(sorted(per_shape.items()))})")

    check(per_shape["pop-dph-dpl-selector-r0"] == 2 and len(cands) == 93,
          "against 2 for that one five-byte literal in the whole PD image, "
          "which is the whole reason the search is tiered: every one of the 93 "
          f"is a bare `d0 82 d0 83` or `d0 83 d0 82` at some offset (got "
          f"{len(cands)})")

    tier2 = [r for r in cands if r["walks_table"]]
    check(tuple(r["file_offset"] for r in tier2) == TIER2_SITES,
          f"{len(TIER2_SITES)} candidates reach a `movc a,@a+dptr` within "
          f"{PROLOGUE_BODY_INSNS} instructions, and the other "
          f"{len(cands) - len(tier2)} do not (got "
          + ", ".join(f"0x{r['file_offset']:05X}" for r in tier2) + ")")

    readers = pd_readers(d)
    check(tuple(r["runtime"] for r, _, _ in readers) == READERS,
          f"and {len(READERS)} of them are named by an `lcall` -- the other "
          "two have no caller, so they can have no inline table whatever their "
          "shape says (got "
          + (", ".join(f"0x{r['runtime']:04X}" for r, _, _ in readers) or "none")
          + ")")

    check(tuple(len(s) for _, s, _ in readers) == (9, 16, 3),
          "with 9 / 16 / 3 `lcall` byte sites (got "
          + " / ".join(str(len(s)) for _, s, _ in readers) + ")")

    # The reconciliation the plan asks for: the two dispatchers the committed
    # census already names must come back with the site counts it commits, or
    # the two tools disagree about the same image and neither notices.
    committed = collections.Counter(target for target, _, _, _
                                    in code_table_inline_tables(read_region(d)))
    mine = {r["runtime"]: len(s) for r, s, _ in readers}
    check(all(committed[t] == mine[t] for t in CODE_TABLE_DISPATCHERS)
          and len(committed) == len(CODE_TABLE_DISPATCHERS),
          f"and the 9 and 16 agree with `pd_image_census.py`'s committed "
          f"figures for {', '.join(f'0x{t:04X}' for t in CODE_TABLE_DISPATCHERS)}"
          f" (got {dict(committed)}, against {dict(mine)})")

    strides = tuple(stride for _, _, stride in readers)
    check(strides == STRIDES,
          f"the three entry strides, each read off its own reader's loop: "
          f"{', '.join(str(s) for s in strides)} bytes, against "
          f"{ENTRY_LEN} for the main EC's reader at 0x07151 (got "
          f"{', '.join(str(s) for s in strides)})")

    # The main EC reader's stride, through the same function, so a change to
    # the derivation cannot quietly mean something different there.
    check(entry_stride(d, 0x07151, 0x07151 + 0x100) == ENTRY_LEN,
          "and the same derivation returns "
          f"{ENTRY_LEN} for the main EC reader at 0x07151, whose 3-byte "
          "entries the whole of decode_index_table.py is written against")

    check(d[0x2119C:0x2119C + 5] == PROLOGUE_SHAPES[0].pattern
          and d[0x211C2:0x211C2 + 5] == PROLOGUE_SHAPES[0].pattern,
          "the two five-byte-literal sites are `d0 83 d0 82 f8` at file "
          "0x2119C and 0x211C2, so the enumeration kept the shape that finds "
          "them rather than replacing it")

    rows = pd_census(d)
    check(len(rows) == sum(len(s) for _, s, _ in readers) == 28,
          f"the census is {len(rows)} rows -- every candidate site, failures "
          "included (got "
          f"{len(rows)})")

    per_reader = collections.OrderedDict()
    for reader, stride, site, tbl, why in rows:
        per_reader.setdefault(reader["runtime"], [0, 0])
        per_reader[reader["runtime"]][0] += 1
        per_reader[reader["runtime"]][1] += bool(tbl is not None and not why)
    got_wf = tuple(tuple(per_reader[r]) for r in READERS)
    check(got_wf == WELL_FORMED,
          f"{WELL_FORMED} as (sites, well-formed) per reader -- 0x11EF's zero "
          "is a result, not a gap: all three of its sites decode to a single "
          f"entry under a {ENTRY_LEN}-byte reading of a {STRIDES[2]}-byte table "
          "(got " + ", ".join(f"0x{r:04X} {v[0]}/{v[1]}"
                              for r, v in per_reader.items()) + ")")

    # The whole census as a value, so a different dump re-derives it rather
    # than inheriting it. The 0x11C2 and 0x11EF rows are the main EC's rule
    # over a table of another stride, and pinning them pins that too.
    got = tuple((r["runtime"], stride, s["file_offset"], s["frame_onto"],
                 None if t is None else (len(t["entries"]), t["file_offset"],
                                         t["end"],
                                         min(e["case"] for e in t["entries"]),
                                         max(e["case"] for e in t["entries"])),
                 well_formed(w)) for r, stride, s, t, w in rows)
    differs = next((g for g, want in zip(got, CENSUS) if g != want), None)
    check(got == CENSUS,
          f"and all {len(CENSUS)} rows individually: reader, stride, site "
          "offset, frame_onto, entry count, span, case range and verdict"
          + ("" if differs is None else f" (first differing row: {differs})"))

    total = sum(t["end"] - t["file_offset"]
                for _, _, _, t, w in rows if t and not w)
    check(total == TABLE_DATA_BYTES,
          f"{TABLE_DATA_BYTES} bytes of the PD image read as table data by "
          f"this method (got {total})")

    check(not direct_address_readers(d, PD_IMAGE),
          "and no direct-address candidate at all: the PD image has no site "
          "that names a table with an immediate and then walks one")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


# The whole result, as a value, so a different dump gets it re-derived rather
# than inheriting this image's answer. One tuple per candidate `lcall` byte
# site: (reader runtime, that reader's own stride, site file offset,
# frame_onto, (entries, table file offset, one past its last byte, lowest case,
# highest case) or None, and whether the main EC's rule passed it).
#
# The `no` rows under 0x11C2 and 0x11EF are not verdicts about those tables:
# their readers walk 4- and 6-byte entries and decode_table() reads 3. That is
# why the stride is a column of the same row rather than a note in this file.
CENSUS = (
    (0x119C, 3, 0x2136C, 24, (20, 0x2136F, 0x213AF, 0x01, 0x16), "yes"),
    (0x119C, 3, 0x21F2D, 24, (8, 0x21F30, 0x21F4C, 0x01, 0x0F), "yes"),
    (0x119C, 3, 0x242C5, 24, (20, 0x242C8, 0x24308, 0x20, 0x58), "no"),
    (0x119C, 3, 0x244D2, 24, (9, 0x244D5, 0x244F4, 0x01, 0x09), "yes"),
    (0x119C, 3, 0x24C35, 24, (11, 0x24C38, 0x24C5D, 0x00, 0x0C), "yes"),
    (0x119C, 3, 0x26B4C, 24, (8, 0x26B4F, 0x26B6B, 0x01, 0x0A), "yes"),
    (0x119C, 3, 0x2A34B, 24, (7, 0x2A34E, 0x2A367, 0x00, 0x11), "yes"),
    (0x119C, 3, 0x2ADE6, 24, (15, 0x2ADE9, 0x2AE1A, 0x01, 0x0F), "yes"),
    (0x119C, 3, 0x2C879, 24, (8, 0x2C87C, 0x2C898, 0x22, 0x99), "yes"),
    (0x11C2, 4, 0x213F6, 24, (16, 0x213F9, 0x2142D, 0x00, 0x97), "no"),
    (0x11C2, 4, 0x2153E, 24, (16, 0x21541, 0x21575, 0x00, 0xEB), "no"),
    (0x11C2, 4, 0x216A7, 24, (8, 0x216AA, 0x216C6, 0x02, 0xDE), "no"),
    (0x11C2, 4, 0x21AB6, 24, (11, 0x21AB9, 0x21ADE, 0x00, 0xD1), "no"),
    (0x11C2, 4, 0x21C88, 24, (14, 0x21C8B, 0x21CB9, 0x00, 0xFF), "no"),
    (0x11C2, 4, 0x23A46, 22, (33, 0x23A49, 0x23AB0, 0x00, 0xFE), "no"),
    (0x11C2, 4, 0x24587, 24, (12, 0x2458A, 0x245B2, 0x00, 0xCA), "no"),
    (0x11C2, 4, 0x2483A, 24, (35, 0x2483D, 0x248AA, 0x00, 0xE0), "no"),
    (0x11C2, 4, 0x24FFA, 20, (32, 0x24FFD, 0x25061, 0x00, 0xFC), "no"),
    (0x11C2, 4, 0x2617D, 20, (12, 0x26180, 0x261A8, 0x03, 0xFF), "no"),
    (0x11C2, 4, 0x2776C, 20, (12, 0x2776F, 0x27797, 0x00, 0xD0), "no"),
    (0x11C2, 4, 0x27948, 20, (4, 0x2794B, 0x2795B, 0x03, 0xFF), "no"),
    (0x11C2, 4, 0x28288, 24, (24, 0x2828B, 0x282D7, 0x00, 0xFF), "no"),
    (0x11C2, 4, 0x283CF, 20, (4, 0x283D2, 0x283E2, 0x04, 0xFF), "yes"),
    (0x11C2, 4, 0x292EF, 20, (4, 0x292F2, 0x29302, 0x07, 0xFF), "yes"),
    (0x11C2, 4, 0x2CB4A, 24, (4, 0x2CB4D, 0x2CB5D, 0x01, 0xCB), "no"),
    (0x11EF, 6, 0x224FE, 24, (1, 0x22501, 0x22508, 0x00, 0x00), "no"),
    (0x11EF, 6, 0x22867, 22, (1, 0x2286A, 0x22871, 0x00, 0x00), "no"),
    (0x11EF, 6, 0x2BCEE, 20, (1, 0x2BCF1, 0x2BCF8, 0x00, 0x00), "no"),
)

# The search, per shape and then the corroborated subset of it, as a whole
# census of the region rather than a sample of it.
SHAPE_HITS = {"pop-dph-dpl-selector-r0": 2, "pop-dph-dpl": 6,
              "pop-dpl-dph": 84, "pop-dpl-dph-push-acc": 1}

TIER2_SITES = (0x2119C, 0x211C2, 0x211EF, 0x212E9, 0x21302)

# The three a caller names, in file order, and the entry stride each one's own
# loop gives. 3 is this family's stride; 4 and 6 are not, which is the finding.
READERS = (0x119C, 0x11C2, 0x11EF)
STRIDES = (3, 4, 6)

# (sites, of which well-formed) per reader above. 0x11EF's zero is a result and
# is asserted as a zero: all three of its sites decode to a single entry, which
# is what reading a 6-byte table's first six bytes as a 3-byte entry does.
WELL_FORMED = ((9, 8), (16, 2), (3, 0))

TABLE_DATA_BYTES = 322


def read_region(d: bytes) -> bytes:
    """The 64 KiB PD image as `pd_image_census.py` reads it, for the
    reconciliation above. This tool works on file offsets throughout --
    `decode_table()` and `malformed()` are the main EC's and are not
    re-implemented for a sliced buffer -- so the slice is only handed to the
    function that already expects one."""
    return d[0x20000:0x30000]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=FIRMWARE,
                    help="raw EC firmware image (default: ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--spans-csv", action="store_true",
                    help="write one row per candidate call site with its "
                         "reader's runtime address and stride, the table's "
                         "span, frame evidence and case range")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the PD reader search, the reconciliation "
                         "against pd_image_census.py, every reader's own entry "
                         "stride, and all 28 census rows")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} in "
              f"{args.firmware} -- whatever is at 0x20000 there is not this "
              "image, and this tool describes only this one", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d)

    if args.spans_csv:
        write_spans_csv(pd_census(d))
        return 0

    print_census(d, pd_census(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
