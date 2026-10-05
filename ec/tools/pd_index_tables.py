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

**Two of the three dispatchers walk entries of a different width, and
`reader_stride` is where that is now paid rather than explained.** The main EC's
reader at `0x7151` takes three bytes per entry -- address, address, case -- and
the PD's `0x11C2` takes four and `0x11EF` takes six, all three taking the
pointer off the return address the same way. The entry stride is read off each
reader's own body by `entry_stride()` rather than assumed, and
`decode_table()` is handed it, so **every row's `well_formed` column is a
statement about the table in that row** at its own reader's own layout. What an
entry looks like at each width -- two target bytes and `stride - 2` key bytes,
and a terminator and default that stay four bytes wide at all three -- is
established from the readers' own compare chains in
`docs/findings/pd-reader-entry-layouts.md`, which is also where `0x11EF`'s
layout, previously undecoded anywhere, is written up.

**What a PD well-formedness check is worth.** `malformed()` requires every
target and the default to resolve inside the caller's own region, which in the
main EC means *banked* -- below `0x8000` is common area, at or above it is the
caller's own bank. The PD image is flat, so `REGIONS` gives it base `0x0000` and
the same test only asks for a `0x0000`-`0xFFFF` CODE address. It is a weaker
check in the PD than it reads in the main EC, and the other two checks -- keys
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
import io
import os
import sys

from decode_index_table import (ENTRY_LEN, MAX_ENTRIES, PD_IMAGE,
                                PROLOGUE_BODY_INSNS, PROLOGUE_SHAPES,
                                SPAN_COLUMNS, census, direct_address_readers,
                                entry_stride, find_readers, lcalled_readers,
                                reader_call_sites)
from pd_image_census import (CODE_TABLE_DISPATCHERS, CODE_TABLE_ENTRY_WIDTHS,
                             code_table_inline_tables)
from trace_xdata_refs import PD_MARKER, REGIONS, region_of

HERE = os.path.dirname(os.path.abspath(__file__))
FIRMWARE = f"{HERE}/../firmware/GMxMGxx_11.800"

# The main EC's span columns, in its order, plus the two the PD needs in front
# of them: which dispatcher the site names, and that dispatcher's own entry
# stride. `first_case`/`last_case` become `first_key`/`last_key` -- the two
# columns sit exactly where the two case columns were -- because at 4 and 6
# bytes an entry has no single case byte, and a 4-byte entry's second key byte
# read as a case value is what put most of the 0x11C2 rows' keys out of order.
# The key is the whole of the `stride - 2` bytes the reader compares, most
# significant first, so the column is wider at the wider strides and
# `self_test` checks that this list differs from the main EC's only by the two
# renames.
PD_SPAN_COLUMN_RENAMES = {"first_case": "first_key", "last_case": "last_key"}
PD_SPAN_COLUMNS = ["reader", "reader_stride"] + [
    PD_SPAN_COLUMN_RENAMES.get(c, c) for c in SPAN_COLUMNS]


def key_hex(key: int, stride: int) -> str:
    """One entry's key as the bytes it is -- the `stride - 2` after the entry's
    two target bytes -- most significant first: `0x07` at this family's 3-byte
    entry, `0x0206` at a 4-byte one, `0x00000005` at a 6-byte one. The column
    is exactly as wide as the key, so a 3-byte table's `0x07` cannot be read as
    the same key as a 4-byte table's `0x0007`, and the width on its own says
    which reader produced the row."""
    return f"0x{key:0{2 * max(stride - 2, 1)}X}"


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
    that fails keeps its row, exactly as `index-table-spans.csv` does.

    Each dispatcher's own stride is what its sites are decoded at, so a row's
    verdict is about the table in that row rather than about the main EC's
    layout applied to it. A reader whose stride `entry_stride()` does not
    derive decodes nothing, the same as a site whose bytes reach no terminator:
    the row is kept and the other figures are left empty rather than a width
    borrowed from another reader."""
    out = []
    for reader, sites, stride in pd_readers(d):
        for site, tbl, bad in (census(d, sites, stride) if stride is not None
                               else [(s, None, []) for s in sites]):
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
        print(f"  reader 0x{rt:04X} ({shape}), {len(items)} `lcall` byte "
              f"site(s), {len(good)} well-formed, stride {stride}")
    print()
    print(f"  {len([r for r in rows if r[3] is not None and not r[4]])} of "
          f"{len(rows)} candidate site(s) are followed by a well-formed table")
    print()
    print("  reader  site      frame   entries  span              keys        "
          "  stride  verdict")
    for reader, stride, site, tbl, bad in rows:
        if tbl is None:
            print(f"  0x{reader['runtime']:04X}  0x{site['file_offset']:05X}  "
                  f"{site['frame_onto']:2}/24   no terminator within "
                  f"{MAX_ENTRIES} entries")
            continue
        keys = [e["key"] for e in tbl["entries"]]
        span = f"0x{tbl['file_offset']:05X}-0x{tbl['end'] - 1:05X}"
        print(f"  0x{reader['runtime']:04X}  0x{site['file_offset']:05X}  "
              f"{site['frame_onto']:2}/24  {len(keys):7}  {span}  "
              f"{key_hex(min(keys), stride)}-{key_hex(max(keys), stride)}    "
              f"{str(stride):>4}  {well_formed(bad)}")
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
    column contract with two columns in front of it and `first_case`/
    `last_case` renamed to `first_key`/`last_key`.

    `reader` is which dispatcher the site names, because the PD has three and
    the main EC had one. `reader_stride` is that dispatcher's own entry stride,
    and it is what the two key columns are as wide as.

    **One deliberate difference from the main EC's file**, which is kept
    standing rather than quietly inherited: a site whose bytes reach a
    terminator keeps its span, entry count and key range even when the
    well-formedness checks fail, and only a site that never reaches one gets
    empty span fields. `index-table-spans.csv` blanks them for both, which
    costs it nothing -- all of its rows pass -- and would cost this file most of
    its rows, which is most of the reading. The rule the two files share is the
    one that matters: a site that fails keeps its row."""
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
        keys = [e["key"] for e in tbl["entries"]]
        w.writerow(row + [
            len(tbl["entries"]), f"0x{tbl['file_offset']:05X}",
            f"0x{tbl['end']:05X}", f"0x{tbl['runtime']:04X}",
            key_hex(min(keys), stride), key_hex(max(keys), stride),
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

    # The reconciliation, over *every* reader rather than over the ones the
    # census already names. Walking `CODE_TABLE_DISPATCHERS` here would have
    # stayed green with a fourth dispatcher this image grew -- the two searches
    # would have agreed about the two they shared and said nothing about the
    # one neither had. `READERS` is the set derived from the bytes, so
    # comparing the two sets in both directions makes a disagreement a
    # failure whichever tool holds it.
    committed = collections.Counter(target for target, _, _, _
                                    in code_table_inline_tables(read_region(d)))
    mine = {r["runtime"]: len(s) for r, s, _ in readers}
    check(set(committed) == set(READERS) and dict(committed) == mine,
          f"and the census's per-dispatcher site counts agree with this "
          f"tool's for all {len(READERS)}, "
          f"{' / '.join(str(committed[t]) for t in READERS)} -- both searches "
          f"over the same bytes, one set equality so a dispatcher either has "
          f"is red (got {dict(sorted(committed.items()))}, against "
          f"{dict(sorted(mine.items()))})")

    check(tuple(CODE_TABLE_DISPATCHERS) == READERS,
          f"and `pd_image_census.py`'s own `CODE_TABLE_DISPATCHERS` is the "
          f"same {len(READERS)} this search derived: a dispatcher one of the "
          f"two tools knows and the other does not has to turn this red (got "
          f"{', '.join(f'0x{t:04X}' for t in CODE_TABLE_DISPATCHERS)})")

    strides = tuple(stride for _, _, stride in readers)
    check(strides == STRIDES,
          f"the three entry strides, each read off its own reader's loop: "
          f"{', '.join(str(s) for s in strides)} bytes, against "
          f"{ENTRY_LEN} for the main EC's reader at 0x07151 (got "
          f"{', '.join(str(s) for s in strides)})")

    # The census reads each dispatcher's inline bytes at its own entry width,
    # so this holds its declared widths against the strides just derived from
    # the readers' own `inc dptr` loops. It is a two-hop check on purpose --
    # `STRIDES` is what `entry_stride()` returns, checked against the readers
    # above, and this compares the census's numbers to those -- which is what
    # stops a width drifting into a second true-looking constant that nothing
    # re-derives.
    derived_widths = dict(zip(READERS, STRIDES))
    check(derived_widths == CODE_TABLE_ENTRY_WIDTHS,
          f"and the census reads each one at that width -- "
          f"{', '.join(f'0x{t:04X}={w}' for t, w in derived_widths.items())} "
          f"bytes, rather than at one window for all three (got "
          f"{CODE_TABLE_ENTRY_WIDTHS})")

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
          f"{WELL_FORMED} as (sites, well-formed) per reader -- the one `no` "
          "is 0x119C's 0x242C5 at that reader's own stride, and both of the "
          f"non-{ENTRY_LEN} readers pass at the width they walk "
          "(got " + ", ".join(f"0x{r:04X} {v[0]}/{v[1]}"
                              for r, v in per_reader.items()) + ")")

    # The stride a row was decoded and judged at is the stride in that row,
    # which is the whole point of the column: a verdict about a table is only
    # that if the table was read the way its own reader reads it.
    check(all(t is None or t["stride"] == stride
              for _, stride, _, t, _ in rows),
          "and every row's table was decoded at its own row's "
          "`reader_stride`, so `well_formed` is a statement about the table in "
          "that row rather than about one layout applied to all three "
          "readers")

    # The whole census as a value, so a different dump re-derives it rather
    # than inheriting it. The key column is `stride - 2` bytes wide, so the
    # pinned values differ in width between the three readers.
    got = tuple((r["runtime"], stride, s["file_offset"], s["frame_onto"],
                 None if t is None else (len(t["entries"]), t["file_offset"],
                                         t["end"],
                                         min(e["key"] for e in t["entries"]),
                                         max(e["key"] for e in t["entries"])),
                 well_formed(w)) for r, stride, s, t, w in rows)
    differs = next((g for g, want in zip(got, CENSUS) if g != want), None)
    check(got == CENSUS,
          f"and all {len(CENSUS)} rows individually: reader, stride, site "
          "offset, frame_onto, entry count, span, key range and verdict"
          + ("" if differs is None else f" (first differing row: {differs})"))

    total = sum(t["end"] - t["file_offset"]
                for _, _, _, t, w in rows if t and not w)
    check(total == TABLE_DATA_BYTES,
          f"{TABLE_DATA_BYTES} bytes of the PD image read as table data by "
          f"this method (got {total})")

    check(not direct_address_readers(d, PD_IMAGE),
          "and no direct-address candidate at all: the PD image has no site "
          "that names a table with an immediate and then walks one")

    # The committed CSV, regenerated into a buffer and compared byte for byte,
    # so a column renamed or a key rendered at the wrong width is a failure
    # here rather than a diff someone has to notice.
    buf = io.StringIO()
    out, sys.stdout = sys.stdout, buf
    try:
        write_spans_csv(rows)
    finally:
        sys.stdout = out
    committed = f"{HERE}/../annotations/pd-index-table-spans.csv"
    with open(committed, newline="") as fh:
        want = fh.read()
    check(buf.getvalue() == want,
          f"and the committed pd-index-table-spans.csv is what "
          f"`--spans-csv` writes -- {len(PD_SPAN_COLUMNS)} columns, "
          "`first_key`/`last_key` where the main EC has its case columns "
          + ("" if buf.getvalue() == want else " (differs from the committed "
             f"{committed})"))

    # The two column lists differ by the rename and nothing else, so a column
    # added to `SPAN_COLUMNS` later cannot be quietly dropped from this file.
    renamed = {c: PD_SPAN_COLUMN_RENAMES[c] for c in SPAN_COLUMNS
               if c in PD_SPAN_COLUMN_RENAMES}
    check(PD_SPAN_COLUMNS[2:] == [PD_SPAN_COLUMN_RENAMES.get(c, c)
                                  for c in SPAN_COLUMNS]
          and renamed == PD_SPAN_COLUMN_RENAMES,
          "the two column lists differ by the two renames alone -- "
          + ", ".join(f"{k} -> {v}" for k, v in sorted(renamed.items()))
          + f", and nothing else (got {PD_SPAN_COLUMNS[2:]})")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


# The whole result, as a value, so a different dump gets it re-derived rather
# than inheriting this image's answer. One tuple per candidate `lcall` byte
# site: (reader runtime, that reader's own stride, site file offset,
# frame_onto, (entries, table file offset, one past its last byte, lowest key,
# highest key) or None, and whether the checks passed it).
#
# Each row is decoded and checked at its own reader's own stride, so `yes` is a
# statement about the table in that row. `0x242C5` is the one that is not, and
# it is now failing under its own reader's width rather than a foreign one --
# which makes it a statement about that table, and
# docs/findings/table-reader-spellings.md hands the question of what it is on
# from there.
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
    (0x11C2, 4, 0x213F6, 24, (7, 0x213F9, 0x21419, 0x206, 0x901), "yes"),
    (0x11C2, 4, 0x2153E, 24, (7, 0x21541, 0x21561, 0x10D, 0x602), "yes"),
    (0x11C2, 4, 0x216A7, 24, (6, 0x216AA, 0x216C6, 0x207, 0x902), "yes"),
    (0x11C2, 4, 0x21AB6, 24, (5, 0x21AB9, 0x21AD1, 0x206, 0x602), "yes"),
    (0x11C2, 4, 0x21C88, 24, (4, 0x21C8B, 0x21C9F, 0x301, 0x602), "yes"),
    (0x11C2, 4, 0x23A46, 22, (13, 0x23A49, 0x23A81, 0x101, 0x1FF), "yes"),
    (0x11C2, 4, 0x24587, 24, (9, 0x2458A, 0x245B2, 0x001, 0xA04), "yes"),
    (0x11C2, 4, 0x2483A, 24, (10, 0x2483D, 0x24869, 0x201, 0x2FF), "yes"),
    (0x11C2, 4, 0x24FFA, 20, (10, 0x24FFD, 0x25029, 0x801, 0x9FF), "yes"),
    (0x11C2, 4, 0x2617D, 20, (9, 0x26180, 0x261A8, 0x501, 0x5FF), "yes"),
    (0x11C2, 4, 0x2776C, 20, (5, 0x2776F, 0x27787, 0x601, 0x6FF), "yes"),
    (0x11C2, 4, 0x27948, 20, (3, 0x2794B, 0x2795B, 0x302, 0x3FF), "yes"),
    (0x11C2, 4, 0x28288, 24, (14, 0x2828B, 0x282C7, 0x106, 0x9FF), "yes"),
    (0x11C2, 4, 0x283CF, 20, (3, 0x283D2, 0x283E2, 0x402, 0x4FF), "yes"),
    (0x11C2, 4, 0x292EF, 20, (3, 0x292F2, 0x29302, 0x701, 0x7FF), "yes"),
    (0x11C2, 4, 0x2CB4A, 24, (3, 0x2CB4D, 0x2CB5D, 0x108, 0x207), "yes"),
    (0x11EF, 6, 0x224FE, 24, (2, 0x22501, 0x22511, 0x005, 0x008), "yes"),
    (0x11EF, 6, 0x22867, 22, (7, 0x2286A, 0x22898, 0x000, 0x006), "yes"),
    (0x11EF, 6, 0x2BCEE, 20, (2, 0x2BCF1, 0x2BD01, 0x010, 0x011), "yes"),
)

# The search, per shape and then the corroborated subset of it, as a whole
# census of the region rather than a sample of it.
SHAPE_HITS = {"pop-dph-dpl-selector-r0": 2, "pop-dph-dpl": 6,
              "pop-dpl-dph": 84, "pop-dpl-dph-push-acc": 1}

TIER2_SITES = (0x2119C, 0x211C2, 0x211EF, 0x212E9, 0x21302)

# The three a caller names, in file order, and the entry stride each one's own
# loop gives. Each row below is decoded at the width beside it, so the two
# non-3 readers' verdicts are statements about their tables and not about this
# module's layout applied to them.
READERS = (0x119C, 0x11C2, 0x11EF)
STRIDES = (3, 4, 6)

# (sites, of which well-formed) per reader above. The single `no` is 0x119C's
# 0x242C5, under its own reader's own stride; every 0x11C2 and 0x11EF site
# passes at the width that reader walks.
WELL_FORMED = ((9, 8), (16, 16), (3, 3))

TABLE_DATA_BYTES = 876


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
