#!/usr/bin/env python3
"""Census every all-`0xFF` listing in `ec/decompiled`, and say what put it there.

`citation_callers.is_fill` answers one question about a committed listing: is
every one of its instruction lines a `0xFF` first byte? Thirty listings answer
yes. Twenty-nine now carry an `ec/annotations/ghidra-functions.csv` row saying
so; one -- `pd,0012` -- is issue #489's, and this tool reports it without
touching it. The seventeen `common` rows are issue #561's, and the reason they
existed at all is the question this tool exists to answer: nothing in the
project put them there but a *byte scan*. All seventeen carry
`seed_basis=call-target` in `ec/decompiled/index.csv`, so the address is where a
`74 01` byte pair read as a call target, and this tool reads back the
instruction that pair actually sits inside.

**Three claims, and the method settles each of them differently.** Whether a
listing is fill is a fact about its bytes, and `is_fill` is the only
implementation of that question here -- imported, not reimplemented, so this
tool and the `call_graph.py` veto cannot come to disagree about the population.
Where the bytes live is a fact about the firmware, read through
`build_ec_decompile.file_offset` for the same reason: a hand-rolled
`0x08000 + addr` is bank 0's mapping and reads bank 1 and PD at the wrong
place. Whether an address is an *entry point* is not settled by either, because
a byte scan that matches `74 01` inside a `jnz`'s rel8 has found a pattern, not
a call -- so every `bank-call-targets.csv` row naming one of these addresses is
classified against the committed listings and printed, all 28 of them, split
into the three answers the question actually has.

**What this is not.** Nothing here is a behavioural claim, and nothing here
was observed on hardware: every input is a committed file. A listing being
fill is not a statement about what the EC does at that address, and a byte scan
having matched a pad is not a statement about the linker's intent -- the
`0x728F`-`0x7FFF` band is measured, its cause is not. The 6 sites under no
listing are reported as such and not dropped: "no committed listing covers this
address" is not "there is no code here", and it is the same calibration rule
`is_fill` applies to a listing it reads no instruction from.

Usage:
    python3 census_ff_fill.py
    python3 census_ff_fill.py --self-test
"""
import argparse
import collections
import csv
import os
import sys
import tempfile

from build_ec_decompile import (BANK_WINDOWS, COMMON_END, FIRMWARE, PD_WINDOW,
                                file_offset)
from citation_callers import is_fill, iter_instructions, norm_addr

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
DECOMPILED = os.path.join(EC, "decompiled")
INDEX_CSV = os.path.join(DECOMPILED, "index.csv")
ANNOTATIONS = os.path.join(EC, "annotations", "ghidra-functions.csv")
CALL_TARGETS = os.path.join(EC, "annotations", "bank-call-targets.csv")
PAGED_TARGETS = os.path.join(EC, "annotations", "bank-paged-call-targets.csv")
RELATIVE_TARGETS = os.path.join(EC, "annotations",
                                "bank-relative-branch-targets.csv")
TABLE_CSVS = (os.path.join(EC, "annotations", "index-table-entries.csv"),
              os.path.join(EC, "annotations", "bank0-8038-dispatch-table.csv"))

# The runtime address `ec/annotations/pd-xdata-overlap.md` §3.1 reads live PD
# code at. It is not one of the seventeen -- it is *inside* `common/741C`'s
# span, so the EC's own listing covers it as three more `mov R7,A` -- which is
# the whole of the collision: one runtime address, two programs, and the
# programs disagree about what is there.
PD_OVERLAP_SITE = 0x7421

# The twelve fill rows that carried a `ghidra-functions.csv` row before issue
# #561 added the seventeen. Pinned by address rather than derived, because the
# "12 annotated before / 18 unannotated" pair is the population #561 was filed
# against and a tool that recomputed it from today's file could no longer
# reproduce either number. The census prints each one's current state, so a
# rename or a dropped row fails the self-test instead of quietly renumbering
# the write-up.
PRE_EXISTING_FILL_ROWS = (
    ("bank0", "F566"), ("bank0", "F583"), ("bank0", "FAE8"),
    ("bank0", "FF17"), ("bank0", "FF90"),
    ("bank1", "F512"), ("bank1", "F70D"), ("bank1", "F727"),
    ("bank1", "F73E"), ("bank1", "F902"), ("bank1", "FF17"),
    ("bank1", "FF63"),
)

# The one fill listing this issue leaves alone. `seed_basis=annotation`, a
# different program, and #489's row -- named here so the census can report it
# as the unannotated remainder rather than the reader having to notice.
PD_FILL_ROW = ("pd", "0012")


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def byte_width(parts):
    """How many byte slots one instruction line carries.

    The `.asm` byte region is three fixed slots and an absent slot is the single
    character `-`, so the count is "tokens before the first pad", read by
    position for the reason `citation_callers.iter_instructions` gives: a
    fixed-width column regex drops a `jnz`'s two-byte form."""
    width = 1
    while width < len(parts) and parts[width] != "-":
        width += 1
    return width - 1


def listing_span(path):
    """(first, last, insns) for one `.asm`, or None if it reads no instruction.

    `last` is the address of the final byte, not the address of the final
    instruction, because a span is a byte range and the firmware read below is
    a byte read. None for a listing with no instruction line is *not found by
    this method*, and it is kept distinct from a span of length zero."""
    first = last = None
    insns = 0
    for parts in iter_instructions(path):
        addr = int(parts[0], 16)
        if first is None:
            first = addr
        last = addr + byte_width(parts) - 1
        insns += 1
    return None if first is None else (first, last, insns)


def listing_paths():
    """Every committed `.asm`, sorted, as (program, addr, path).

    Sorted by program and then numerically rather than by filename, so the
    report reads in address order -- `F512` before `FF17`, not after."""
    out = []
    for program in sorted(os.listdir(DECOMPILED)):
        directory = os.path.join(DECOMPILED, program)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".asm"):
                continue
            out.append((program, norm_addr(name[:-4]),
                        os.path.join(directory, name)))
    return out


def fill_listings():
    """Every listing `is_fill` accepts, as census rows.

    The predicate is imported rather than reimplemented: this population and
    the `fill-at-citer` veto's are then the same 30 listings by construction,
    which is what lets the census quote the veto's blast radius instead of a
    second, slightly different count of it."""
    rows = []
    for program, addr, path in listing_paths():
        if not is_fill(path):
            continue
        first, last, insns = listing_span(path)
        rows.append({"program": program, "addr": addr, "path": path,
                     "first": first, "last": last, "insns": insns,
                     "bytes": last - first + 1})
    return rows


def program_window(program):
    """(first, last) file offsets of one program's own bytes.

    The walk in `pad_extent` stops here rather than at the end of the file. The
    dump lays four 32 KiB images end to end, so a run of `0xFF` that reaches a
    window's last byte is bounded by *this program ending*, not by the next
    image's first byte happening to be something else -- and reporting the
    neighbour's byte as what stopped the run would be an artefact of the dump's
    layout dressed up as a finding about the program."""
    base = PD_WINDOW if program == "pd" else (
        0 if program == "common" else BANK_WINDOWS[program])
    return base, base + 0x8000 - 1


def pad_extent(fw, program, addr):
    """(start, end, length) of the `0xFF` run containing `addr`, measured.

    Walked in the firmware rather than assumed from a listing, because the
    listing is a function boundary the byte scan drew and the pad is not
    bounded by it -- `common/7401.asm` stops at 0x7403 because 0x7404 is
    another seeded function, not because the fill ends there."""
    off = file_offset(program, addr)
    if fw[off] != 0xFF:
        return None
    lo, hi = program_window(program)
    start = off
    while start > lo and fw[start - 1] == 0xFF:
        start -= 1
    end = off
    while end < hi and fw[end + 1] == 0xFF:
        end += 1
    return (start, end, end - start + 1)


def span_bytes(fw, program, first, last):
    """The firmware's own bytes for a listing's span, read through file_offset.

    Length and content both checked. A short read would otherwise compare `0xFF`
    against nothing and pass, which is the shape of a clean result reported
    over bytes that were never fetched."""
    off = file_offset(program, first)
    chunk = fw[off:off + (last - first + 1)]
    return chunk if len(chunk) == last - first + 1 else None


def span_is_fill(fw, program, first, last):
    """True when every byte of the span, in the firmware, is `0xFF`.

    The byte confirmation, kept separate from `is_fill` on purpose. `is_fill`
    reads the listing and asks about the *instructions Ghidra drew*; this reads
    the image and asks about the *bytes the listing is supposed to be a decode
    of*. They agree on every committed fill listing, and where they could
    disagree is where a listing that does not match the firmware would show
    up -- which is why the self-test pins the disagreement as well."""
    chunk = span_bytes(fw, program, first, last)
    return chunk is not None and bool(chunk) and all(b == 0xFF for b in chunk)


def index_rows():
    """(program, addr) -> row, from the generated listing index."""
    return {(r["program"], norm_addr(r["addr"])): r
            for r in read_csv(INDEX_CSV)}


def annotation_keys():
    """The (scope, addr) keys `ghidra-functions.csv` carries."""
    return {(r["scope"], norm_addr(r["addr"])) for r in read_csv(ANNOTATIONS)}


def annotation_names():
    """(scope, addr) -> the name the annotation row gives it.

    Separate from the index's `name` because the two are different files with
    different update rules: the CSV is hand-edited and the index is written by
    a Ghidra export, so between the two they disagree on every row this
    repository has annotated but not yet re-exported."""
    return {(r["scope"], norm_addr(r["addr"])): r["name"]
            for r in read_csv(ANNOTATIONS)}


def nearest_entries(index, program, first, last):
    """The nearest exported entry below and above a span, in the same program.

    "Exported" is the listing index's own vocabulary: a row in `index.csv` is a
    function Ghidra named, which is what makes a neighbour worth naming. The
    upper neighbour is `None` where the span reaches the end of the program's
    address space -- `common`'s last byte is 0x7FFF and nothing is above it --
    and that None is printed as a fact rather than smoothed over."""
    below = above = None
    for (prog, addr), row in index.items():
        if prog != program:
            continue
        value = int(addr, 16)
        if value < first and (below is None or value > below[0]):
            below = (value, row)
        if value > last and (above is None or value < above[0]):
            above = (value, row)
    return below, above


def listing_coverage():
    """(program, addr) -> the instruction covering it, over every listing.

    An address a listing's own first byte starts is mapped to that listing too,
    which is what makes the "at an instruction boundary" answer available: a
    byte scan's match at an opcode *is* a boundary, and "not one of these 28 is
    a boundary" is only a finding if the boundary case is implemented."""
    cover = {}
    for program, addr, path in listing_paths():
        for parts in iter_instructions(path):
            start = int(parts[0], 16)
            for k in range(byte_width(parts)):
                cover[(program, "%04X" % (start + k))] = {
                    "listing": os.path.splitext(os.path.basename(path))[0],
                    "addr": "%04X" % start,
                    "text": " ".join(parts[4:]),
                }
    return cover


def call_target_rows(addrs):
    """The `bank-call-targets.csv` rows whose target is one of `addrs`.

    Keyed on `target`, not on the site, because the question is where the scan
    said the call went. `file_offset` is the site's own file position and
    `runtime` is where that lands in the caller's program, which for a bank is
    not the file offset -- reading `0x15756` as runtime `0x15756` would look
    the site up in a program that has no byte there."""
    out = []
    for row in read_csv(CALL_TARGETS):
        if norm_addr(row["target"]) in addrs:
            out.append(row)
    return out


def classify_site(row, cover):
    """One site as boundary / inside / none, against the committed listings.

    Three answers and no fourth. A site under no listing is `none`, not
    `absent`: the caller may be code Ghidra never exported, and the census has
    no way to tell that from an address nothing was ever decoded at."""
    key = (row["region"], norm_addr(row["runtime"]))
    hit = cover.get(key)
    if hit is None:
        return "no listing covers it", None
    where = "at an instruction boundary" if hit["addr"] == key[1] \
        else "inside another instruction"
    return where, hit


def table_rows_in(addrs, path, column="target_runtime"):
    """Rows of a decoded address table whose target falls in `addrs`.

    Zero is the finding, so the total is printed beside it. A table census
    reporting "none" with no denominator reads as a check that found nothing to
    look at."""
    return [r for r in read_csv(path) if norm_addr(r[column]) in addrs]


def report():
    """The whole census as the lines `docs/findings/ff-fill-census.md` quotes."""
    fw = open(FIRMWARE, "rb").read()
    index = index_rows()
    annotated = annotation_keys()
    names = annotation_names()
    rows = fill_listings()
    out = []
    say = out.append

    say("census_ff_fill.py -- every all-0xFF listing in ec/decompiled")
    say("")

    # --- the census, one row per listing, with its total on the same line ---
    say("## fill listings")
    total = len(listing_paths())
    marked = [r for r in rows if (r["program"], r["addr"]) in annotated]
    say("%d fill listing(s) of %d committed listings; %d annotated, "
        "%d unannotated" % (len(rows), total, len(marked), len(rows) - len(marked)))
    say("")
    say("scope  addr   listing span  insns  size  seed_basis  name             "
        "annot  nearest entry below / above")
    for row in rows:
        entry = index.get((row["program"], row["addr"]), {})
        below, above = nearest_entries(index, row["program"], row["first"],
                                       row["last"])
        say("  %-5s %s  %04X-%04X    %4d  %4s  %-11s  %-17s %-5s  %s / %s" % (
            row["program"], row["addr"], row["first"], row["last"],
            row["insns"], entry.get("size", "?"), entry.get("seed_basis", "?"),
            entry.get("name", "?"),
            "yes" if (row["program"], row["addr"]) in annotated else "no",
            below[1]["addr"] if below else "none",
            above[1]["addr"] if above else "none"))
    say("")
    families = collections.Counter(
        names[(r["program"], r["addr"])].rsplit("_", 1)[0] for r in marked)
    for family, n in sorted(families.items()):
        say("  %d annotated fill row(s) named %s_*" % (n, family))
    # The annotation name and the index name are printed apart on purpose. The
    # seventeen new rows are named in the CSV today, but nothing rewrites
    # `index.csv` or a listing header until a Ghidra export runs, so the two
    # disagree on this tree and a reader counting `FUN_CODE_*` in the index
    # would otherwise conclude the rows did not land.
    stale = [r for r in marked
             if index[(r["program"], r["addr"])]["name"] != names[(r["program"], r["addr"])]]
    if stale:
        say("  %d row(s) whose index.csv name still predates the annotation row "
            "(%s ...): no Ghidra export has run, so the listing headers and the "
            "index keep the old name until one does"
            % (len(stale), ", ".join("%s,%s" % (r["program"], r["addr"])
                                     for r in stale[:3])))
    unannotated = [r for r in rows if (r["program"], r["addr"]) not in annotated]
    say(f"  unannotated: {len(unannotated)} -- "
        + ", ".join(f"{r['program']},{r['addr']}" for r in unannotated))
    say("")

    # --- the bytes, from the firmware rather than from the listing ---
    say("## byte confirmation (ec/firmware/GMxMGxx_11.800, through file_offset)")
    read = 0
    bad = []
    pads = collections.Counter()
    for row in rows:
        read += row["bytes"]
        if not span_is_fill(fw, row["program"], row["first"], row["last"]):
            bad.append(f"{row['program']},{row['addr']}")
            continue
        extent = pad_extent(fw, row["program"], row["first"])
        pads[(row["program"], "%05X-%05X" % (extent[0], extent[1]))] += 1
    say(f"{read} byte(s) read across {len(rows)} span(s); "
        f"{len(bad)} span(s) with a byte that is not 0xFF"
        + (f" ({', '.join(bad)})" if bad else ""))
    for (program, extent), n in sorted(pads.items()):
        first, last = (int(part, 16) for part in extent.split("-"))
        lo, hi = program_window(program)
        below = "the window starts here" if first == lo \
            else "0x%02X" % fw[first - 1]
        above = "the window ends here" if last == hi \
            else "0x%02X" % fw[last + 1]
        say(f"  {program}: {n} listing(s) in the {last - first + 1}-byte 0xFF "
            f"pad at file {extent}, inside that program's own window "
            f"0x{lo:05X}-0x{hi:05X}; the byte below it is {below} and the one "
            f"above is {above}")
    say("")

    # --- provenance: the scan rows, classified, none dropped ---
    say("## provenance (ec/annotations/bank-call-targets.csv)")
    # The `common` fill listings, not the unannotated ones: the question is
    # what put these addresses in the project, and that does not change when an
    # annotation row does, so reading it off `unannotated` would empty this
    # section the moment the rows land.
    seeds = {r["addr"] for r in rows if r["program"] == "common"}
    sites = call_target_rows(seeds)
    cover = listing_coverage()
    verdicts = collections.Counter()
    for row in sites:
        verdicts[classify_site(row, cover)[0]] += 1
    say(f"{len(sites)} row(s) name the {len(seeds)} common fill "
        f"address(es); {len({norm_addr(r['target']) for r in sites})} distinct "
        f"target(s)")
    by_region = collections.Counter(r["region"] for r in sites)
    say("  by caller region: "
        + ", ".join(f"{k} {v}" for k, v in sorted(by_region.items())))
    say("  by bucket: "
        + ", ".join(f"{k} {v}" for k, v in
                    sorted(collections.Counter(r["bucket"] for r in sites).items())))
    for where in ("at an instruction boundary", "inside another instruction",
                  "no listing covers it"):
        say(f"  {where}: {verdicts[where]} of {len(sites)}")
    for row in sites:
        where, hit = classify_site(row, cover)
        detail = "the site is in no committed listing" if hit is None else (
            "`%s` at %s in %s/%s.asm" % (hit["text"], hit["addr"],
                                         row["region"], hit["listing"]))
        say("    %-6s %s %-6s -> 0x%s  %s: %s" % (
            row["region"], row["runtime"], row["opcode"], norm_addr(row["target"]),
            where, detail))
    say("")

    # --- the wider band, so the seventeen are not read as the only ones ---
    say("## the band's wider context")
    extent = pad_extent(fw, "common", 0x7401)
    band = {"%04X" % a for a in range(extent[0], extent[1] + 1)}
    say(f"  band: file 0x{extent[0]:05X}-0x{extent[1]:05X}, "
        f"{extent[2]} byte(s), all 0xFF; the last common-area byte is "
        f"0x{COMMON_END - 1:04X} and 0x{COMMON_END:04X} is "
        f"0x{fw[file_offset('common', COMMON_END)]:02X}")
    for label, path in (("direct-call", CALL_TARGETS),
                        ("paged-family", PAGED_TARGETS),
                        ("PC-relative-family", RELATIVE_TARGETS)):
        in_band = [r for r in read_csv(path)
                   if int(norm_addr(r["target"]), 16) in
                   range(extent[0], extent[1] + 1)]
        say(f"  {label}: {len(in_band)} row(s) target the band, "
            f"{len({norm_addr(r['target']) for r in in_band})} distinct target(s)")
    for path in TABLE_CSVS:
        in_band = table_rows_in(band, path)
        say(f"  {os.path.basename(path)}: {len(in_band)} of "
            f"{len(read_csv(path))} entries target the band")
    say("")

    # --- the same runtime addresses in the other program ---
    say("## cross-program reading (the PD image, file_offset('pd', addr))")
    live_total = 0
    for row in rows:
        if row["program"] != "common":
            continue
        chunk = span_bytes(fw, "pd", row["first"], row["last"])
        live = [row["first"] + k for k, b in enumerate(chunk or b"")
                if b != 0xFF]
        live_total += len(live)
        tag = ""
        if row["first"] <= PD_OVERLAP_SITE <= row["last"]:
            off = file_offset("pd", PD_OVERLAP_SITE)
            tag = ("  <- ec/annotations/pd-xdata-overlap.md 3.1; PD bytes "
                   + " ".join("%02x" % b for b in fw[off:off + 5]))
        say("    %04X-%04X  EC common 0xFF throughout, PD: %d of %d byte(s) "
            "are not 0xFF (first at 0x%04X)%s" % (
                row["first"], row["last"], len(live), row["bytes"],
                live[0] if live else 0, tag))
    say(f"  {live_total} PD byte(s) across the {len([r for r in rows if r['program'] == 'common'])} "
        f"common span(s) are not 0xFF: the two programs disagree about the "
        f"same runtime addresses")
    return "\n".join(out), rows, sites


def self_test() -> int:
    """Known answers, and the three refusals that make them worth anything.

    Both halves. A census that only pins its totals would still print 30 if
    `is_fill` started answering yes to a listing with a `movc` in it, and the
    three refusals are where that would show up: a span the firmware does not
    have 0xFF in, a listing that parses to no instruction, and the `pd` row
    this issue leaves to #489.
    """
    fw = open(FIRMWARE, "rb").read()
    rows = fill_listings()
    index = index_rows()
    annotated = annotation_keys()
    bad = 0
    print("census_ff_fill.py --self-test")

    def check(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"  {detail}" if detail and not ok else ""))

    keys = {(r["program"], r["addr"]) for r in rows}
    check("30 fill listings of the committed tree", len(rows) == 30,
          f"got {len(rows)}")
    check("the 12 pre-existing fill rows are all still annotated",
          all(k in annotated for k in PRE_EXISTING_FILL_ROWS),
          "missing " + ", ".join(f"{p},{a}" for p, a in PRE_EXISTING_FILL_ROWS
                                 if (p, a) not in annotated))
    check("29 of the 30 are annotated, 1 is not",
          sum(1 for r in rows if (r["program"], r["addr"]) in annotated) == 29,
          "got %d" % sum(1 for r in rows if (r["program"], r["addr"]) in annotated))
    check("the one unannotated is pd,0012, issue #489's",
          [k for k in keys if k not in annotated] == [PD_FILL_ROW],
          "got " + ", ".join(f"{p},{a}" for p, a in sorted(keys - annotated)))

    # The seventeen, their instruction counts, and the band they sit in. The
    # counts are `index.csv`'s `size` re-read out of the listing, so a listing
    # that grew or lost a line fails rather than reporting a stale pair.
    want = {"7401": 3, "7404": 1, "7405": 3, "7408": 8, "7410": 5, "741C": 17,
            "7602": 17, "7848": 17, "7883": 17, "7BFF": 3, "7C02": 17,
            "7DF2": 15, "7E01": 17, "7F01": 1, "7F02": 16, "7FF1": 14,
            "7FFF": 1}
    common = {r["addr"]: r for r in rows if r["program"] == "common"}
    check("the 17 common fill listings and their instruction counts",
          {a: r["insns"] for a, r in common.items()} == want,
          "got " + ", ".join(f"{a}:{r['insns']}" for a, r in sorted(common.items())))
    check("each is seeded by a call-target byte scan and is also in bank1",
          all(index[("common", a)]["seed_basis"] == "call-target"
              and index[("common", a)]["also_in"] == "bank1" for a in want),
          "got " + ", ".join(f"{a}:{index[('common', a)]['seed_basis']}"
                             for a in want if a in index))
    extent = pad_extent(fw, "common", 0x7401)
    check("the enclosing pad is 0x728F-0x7FFF, 3441 bytes",
          (extent[0], extent[1], extent[2]) == (0x728F, 0x7FFF, 3441),
          "got 0x%05X-0x%05X, %d" % extent)
    check("0x728E is live code and 0x8000 is not fill",
          fw[0x728E] == 0x22 and fw[file_offset("common", COMMON_END)] == 0xE4,
          "got 0x%02X and 0x%02X" % (fw[0x728E],
                                      fw[file_offset("common", COMMON_END)]))
    in_band = {a for program, a in index
               if program == "common" and 0x728F <= int(a, 16) <= 0x7FFF}
    check("the seventeen are the only common-area exports in the band",
          in_band == set(want), "got " + ", ".join(sorted(in_band)))
    pd_in_band = {a for program, a in index
                  if program == "pd" and 0x728F <= int(a, 16) <= 0x7FFF}
    check("the PD program holds 7 exports at the same runtime addresses",
          len(pd_in_band) == 7, "got %d" % len(pd_in_band))

    # Provenance: the count, the region split and the three-way classification.
    sites = call_target_rows(set(want))
    cover = listing_coverage()
    verdicts = collections.Counter(classify_site(r, cover)[0] for r in sites)
    check("28 bank-call-targets.csv rows name the seventeen", len(sites) == 28,
          "got %d" % len(sites))
    check("they cover all seventeen distinct addresses",
          {norm_addr(r["target"]) for r in sites} == set(want),
          "got %d" % len({norm_addr(r["target"]) for r in sites}))
    check("none of them is at an instruction boundary",
          verdicts["at an instruction boundary"] == 0,
          "got %d" % verdicts["at an instruction boundary"])
    check("22 sit inside another instruction, 6 under no listing",
          (verdicts["inside another instruction"],
           verdicts["no listing covers it"]) == (22, 6),
          "got %d and %d" % (verdicts["inside another instruction"],
                             verdicts["no listing covers it"]))
    worked = next((r for r in sites
                   if (r["region"], norm_addr(r["runtime"])) == ("common", "7159")),
                  None)
    check("the worked example: common,0x7159 is inside the jnz at 0x7158",
          worked is not None
          and classify_site(worked, cover)[1] == {"listing": "7151",
                                                  "addr": "7158",
                                                  "text": "jnz 0x716c"},
          "got " + repr(classify_site(worked, cover)[1]) if worked else "no row")

    # The cross-program reading, at the one address the PD overlap file names.
    off = file_offset("pd", PD_OVERLAP_SITE)
    check("PD 0x7421 reads 90 04 a6 12 90 and EC common 0x7421 reads 0xFF",
          fw[off:off + 5] == bytes.fromhex("9004a61290")
          and fw[file_offset("common", PD_OVERLAP_SITE)] == 0xFF,
          "got " + fw[off:off + 5].hex(" "))

    # --- the three refusals ---
    check("refusal: a span the firmware does not hold 0xFF in is not fill",
          not span_is_fill(fw, "common", 0x728E, 0x728E)
          and span_is_fill(fw, "common", 0x7401, 0x7403),
          "0x728E is 0x%02X" % fw[0x728E])
    # A fixture rather than a committed listing, because no committed listing
    # parses to nothing -- so the case is a guard, and a guard tested against
    # the tree would silently stop being one the day a listing did.
    with tempfile.TemporaryDirectory() as scratch:
        empty = os.path.join(scratch, "EMPTY.asm")
        with open(empty, "w") as f:
            f.write("; a header and nothing else\n")
        check("refusal: a listing that parses to no instruction is not fill",
              listing_span(empty) is None and not is_fill(empty))
    check("refusal: the pd row is reported and left unannotated",
          PD_FILL_ROW in keys and PD_FILL_ROW not in annotated,
          f"{PD_FILL_ROW[0]},{PD_FILL_ROW[1]} in keys="
          f"{PD_FILL_ROW in keys}, annotated={PD_FILL_ROW in annotated}")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the hand "
              "transcriptions above")
        return 1
    print("self-test passed: 30 fill listings, 29 annotated, the 17 common "
          "rows and their counts, the 0x728F-0x7FFF band, the 28/0/22/6 "
          "provenance split and the three refusals")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true",
                    help="check the census against the hand-transcribed "
                         "answers, and the three refusals")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    text, _rows, _sites = report()
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
