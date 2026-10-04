#!/usr/bin/env python3
"""Read the two computed-dispatch tables bank_attribution.py's closure stops at,
and hand them over as edges -- so a `jmp @a+dptr` is a place the walk arrives
rather than a place it gives up.

`bank-attribution.md` 5 names two blind spots in one breath and this file is
the answer to both. `closure()` descends with `walk_branch_arms.descend()`,
which ends an arm at a computed jump because no byte-derived walk can resolve
one, and it does not follow a call out of the bank window because the common
area is mapped in every bank and no bank owns those bytes. Those two decisions
between them put this image's 15 `?C?CCASE` index tables and its `jmp @a+dptr`
jump tables outside both closures: the reader at `0x7151` is itself common area,
and a jump table is exactly what a byte scan cannot enumerate.

**Two mechanisms, three provenance values, and they are not the same kind of
claim.** An `index-table` edge is read out of a committed CSV -- every row of
`annotations/index-table-entries.csv` already carries the `?C?CCASE` reader's
site and the target it names -- so nothing here decodes it a second time. A
`dispatch-table` edge is read out of the bytes at run time: the table base is
taken from the `mov dptr,#imm16` that loads it and the *entry point is the row
address*, not the target the row names. That is deliberate. `descend()` on a
row address decodes the `ljmp` and records the target as a callee
(`descend(d, "bank1", 0x8A45, ...)` ends `tail jump to a callee` with callee
`0x8A6C`), and `closure()` follows a callee it already trusts. So the target is
derived by the walk rather than asserted here, which is what makes this a
control-flow edge and not a table lookup wearing one. The two `dispatch-*`
values are the two shapes that idiom takes in this image, and the difference is
recorded rather than folded: `dispatch-inline` puts the stride arithmetic in
the site itself, `dispatch-shared` puts it in a callee the site calls.

**The three values are calibrated as table edges, never as control flow the
firmware proved.** The `?C?CCASE` reader pops the return address into DPTR
(`ec/annotations/bank-call-audit.md` 4, 9), so the index table's address is
never an immediate and never appears in a scan; these edges are read out of
data. What they add to a closure is reachability under a table's own framing,
which is strictly more than a byte-derived walk could say and strictly less
than an attribution. `bank-attribution.md` 8 carries the same standing caveat,
and every attribution downstream stays "attributed by this closure".

**Why the CSV's `site` column is re-checked against the bytes, and not trusted.**
`index-table-entries.csv` records a `site` as a runtime address, and two of the
bank0-window sites -- `0x8662` and `0x918A` -- are *also* addresses bank1's
closure reaches, for unrelated reasons: bank1 holds `f0 22 90` where bank0
holds `12 71 51`, so the same address is different code in each window. Seeding
those rows into bank1 would attribute bank0's table to bank1 on the strength
of a numerical coincidence, so `index_table_sites()` gates every row on the
site's bytes *in the window being walked*. On this image that admits 125 rows
for bank0 and none for bank1, which is the right answer for a reason the CSV
never claimed.

**A table whose loading site is outside the closure is reported, not used.**
`edges()` filters on reachability, so an unreachable dispatch contributes
nothing -- but `tables()` still enumerates it and `unreachable()` names it, so
"this table did not fire" is distinguishable from "this table is not here".
That is the one calibration the region map (#50) needs and it costs one
membership test.

**Nothing here was measured on hardware.** No register was read back, no
capture was taken, and no `status:` in `../annotations/registers.yaml` moves --
none could, because this file only reads a committed image and a committed
CSV.

Usage:
    python3 ec/tools/dispatch_edges.py --self-test
"""
import argparse
import collections
import csv
import os
import sys

from trace_xdata_refs import offset_for_runtime

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
ENTRIES_CSV = os.path.join(EC, "annotations", "index-table-entries.csv")

# Both bank windows are 0x8000-0xFFFF, so a target below this is the common
# area and no bank owns it. Recorded here rather than imported from
# bank_attribution.py: this file must stay importable by it without a cycle,
# and the two are the same number for the same reason, which is stated where
# each is defined rather than in a third place.
BANK_FLOOR = 0x8000

# The `?C?CCASE` reader's call, as the bytes an index-table site must hold in
# the window being walked. decode_index_table.py's own search is for the
# reader's prologue; this is the one three-byte call every row's site is,
# checked here because the CSV's `site` column is a bare address and says
# nothing about which window it was read in.
READER_CALL = b"\x12\x71\x51"

# The inline shape, as offsets from the `anl a,#mask` that bounds the index:
#
#   +0  54 mm      anl  a,#mask
#   +2  90 hi lo   mov  dptr,#base
#   +5  f8         mov  r0,a
#   +6  28         add  a,r0
#   +7  28         add  a,r0
#   +8  73         jmp  @a+dptr
#
# Three adds of A to itself is the stride-3 multiply, `anl a,#mask` is what
# bounds it, and the mask is therefore the row count minus one -- so the shape
# carries its own length and a table cannot be sized by guessing.
INLINE_TAIL = b"\xf8\x28\x28\x73"

# The shared shape: the caller loads the base and calls a routine that does
# the stride arithmetic itself.
#
#   +0  90 hi lo   mov  dptr,#base
#   +3  12 dl dh   lcall dispatcher
#
# The dispatcher's own prologue is `anl 0x00,#mask` (`53 00 mm`), which is
# where this shape's row count comes from -- it is not at the call site, so
# reading it is the one step that is not visible in the six bytes above.
SHARED_CALL = 0x12
SHARED_MASK = b"\x53\x00"

# Every row of either shape is a three-byte `ljmp`, which is why seeding the
# row address is enough: `descend()` follows the `ljmp` itself.
STRIDE = 3
LJMP = 0x02

KIND_INDEX = "index-table"
KIND_INLINE = "dispatch-inline"
KIND_SHARED = "dispatch-shared"
KINDS = (KIND_INDEX, KIND_INLINE, KIND_SHARED)

# Why a CSV site contributes no edge, as a reason rather than a silent drop.
# The index tables dispatch within the common area, which every bank maps and
# no bank owns, so their targets are unattributable by construction rather
# than by this tool's coverage. Recorded and reported, never deferred as work.
EXCLUDED_COMMON = ("the 0x7151 reader dispatches within the common area, which "
                   "every bank maps and no bank owns")


def index_rows():
    """Every row of the committed index-table CSV, as dicts with its runtime
    columns parsed.

    Read rather than re-decoded on purpose: `decode_index_table.py --all-csv`
    already resolved each entry's `?C?CCASE` address field against the reader's
    layout, and a second decode here could only disagree with the committed
    file it is supposed to agree with.
    """
    with open(ENTRIES_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            row["site_rt"] = int(row["site"], 16)
            row["target_rt"] = int(row["target_runtime"], 16)
            yield row


def index_table_sites(d: bytes, region: str):
    """{site: [row, ...]} for the index tables whose targets a bank could own,
    keyed by the `lcall` address in `region`'s own window.

    The window check is the load-bearing half. Every row is kept only when the
    site holds `READER_CALL` in `region` -- the two bank0-window sites bank1's
    closure also reaches fail that test in bank1, because a bank window holds
    different code at the same runtime address and the CSV does not say which
    window a `site` was read in.
    """
    out = {}
    for row in index_rows():
        if row["target_rt"] < BANK_FLOOR:
            continue
        off = offset_for_runtime(row["site_rt"], region)
        if off is None or d[off:off + 3] != READER_CALL:
            continue
        out.setdefault(row["site_rt"], []).append(row)
    return out


def excluded_index_sites(d: bytes, region: str):
    """CSV sites this walk cannot use, as (site, reason) sorted by site, so an
    absent edge is never ambiguous between "the table is not here" and "the
    table is here and dispatches below `BANK_FLOOR`".

    One row per *site*, not per entry: the question a caller asks is which
    tables were left out, and returning 91 rows for four tables would answer a
    different one. A site is judged on whether any of its rows names a banked
    target, so a table whose entries all dispatch into the common area is not
    reported as excluded for being unreachable.
    """
    targets = collections.defaultdict(list)
    for row in index_rows():
        targets[row["site_rt"]].append(row["target_rt"])
    out = []
    for site in sorted(targets):
        if site >= BANK_FLOOR:
            continue
        if any(t >= BANK_FLOOR for t in targets[site]):
            # Banked target from a site below the floor. This walk does not
            # reach common-area sites at all, and naming that here is what
            # keeps it from reading as a statement about the table.
            out.append((site, "the site is common area, which this closure "
                              "does not walk"))
        else:
            out.append((site, EXCLUDED_COMMON))
    return out


def _ljmp_run(d: bytes, region: str, base: int, rows: int):
    """How many of `rows` rows from `base` are the three-byte `ljmp` the shape
    claims, counted from the base and stopping at the first that is not.

    Stopping rather than rejecting is what keeps a truncated table honest in
    both directions: the rows that are `ljmp` are real rows and are edged into,
    and the ones past the stop are not fabricated to fill the mask. A mask that
    admits more indices than the table has rows is a fact about the firmware
    this reports rather than hides -- `truncated_tables()` names them -- and it
    is one of the reasons the row count is read from the mask and not from a
    constant.
    """
    for i in range(rows):
        off = offset_for_runtime(base + STRIDE * i, region)
        if off is None or d[off] != LJMP:
            return i
    return rows


def dispatch_tables(d: bytes, region: str):
    """Every `jmp @a+dptr` table in `region` whose base a `mov dptr,#imm16`
    names, in the two shapes this image uses, whether or not the walk reaches
    it.

    Enumerated from the bytes rather than listed, so a table this file has
    never seen is still found -- and the row count comes from the `anl` mask
    the shape carries, never from a constant here. `rows` is that mask's bound
    capped at the first row that is not an `ljmp`, and a table where the cap
    bit is what `truncated_tables()` reports.
    """
    lo, hi = (0, 0x7FFF) if region == "common" else (BANK_FLOOR, 0xFFFF)
    out = []
    for addr in range(lo, hi + 1):
        off = offset_for_runtime(addr, region)
        if off is None:
            continue
        raw = d[off:off + 9]
        if len(raw) == 9 and raw[0] == 0x54 and raw[2] == 0x90 and raw[5:9] == INLINE_TAIL:
            base = raw[3] << 8 | raw[4]
            rows = raw[1] + 1
            usable = _ljmp_run(d, region, base, rows)
            if base >= BANK_FLOOR and usable:
                out.append({"kind": KIND_INLINE, "site": addr + 8, "load": addr + 2,
                            "base": base, "rows": usable, "masked": rows,
                            "shape": "inline"})
            continue
        raw = d[off:off + 6]
        if len(raw) != 6 or raw[0] != 0x90 or raw[3] != SHARED_CALL:
            continue
        base = raw[1] << 8 | raw[2]
        callee = raw[4] << 8 | raw[5]
        coff = offset_for_runtime(callee, region)
        if coff is None or d[coff:coff + 2] != SHARED_MASK:
            continue
        rows = d[coff + 2] + 1
        usable = _ljmp_run(d, region, base, rows)
        if base >= BANK_FLOOR and usable:
            out.append({"kind": KIND_SHARED, "site": addr + 3, "load": addr,
                        "base": base, "rows": usable, "masked": rows,
                        "shape": "shared", "callee": callee})
    return out


def truncated_tables(d: bytes, region: str):
    """Tables whose `anl` mask admits more indices than the table has `ljmp`
    rows, as (site, base, masked, usable).

    The gap is a fact about the firmware this reports rather than papers over:
    the site really does dispatch through the table, and the indices past the
    last `ljmp` really do read whatever follows it. Seeding them would put
    fabricated targets in a closure, so `dispatch_tables()` stops at the last
    real row and this names what it stopped short of.
    """
    return [t for t in dispatch_tables(d, region) if t["rows"] < t["masked"]]


def edges(d: bytes, region: str, reached):
    """The entry points `region`'s closure is missing, as a list of records with
    the kind of mechanism each came from.

    `reached` is the closure's own set of decoded addresses, and it gates both
    kinds by the same rule: an edge is emitted only once the instruction that
    *dispatches* the table -- the `lcall 0x7151` for an index table, the
    `jmp @a+dptr` for a dispatch table -- is already inside the walk. A table
    nothing reached must not put bytes in the closure, because that is an
    attribution with no control flow behind it at all; the walk arriving at a
    dispatch it cannot resolve is the evidence, and the table is what resolves
    it.

    Gating the index tables on reachability rather than seeding them
    unconditionally is what makes the two mechanisms comparable, and it is also
    what lets `bank_attribution.py` run one fixpoint instead of two rules: a
    pass either adds edges or it does not.

    Each record names the site that produced it, which is what
    `bank_attribution.py` puts in a table edge's `frm`: `entry_chain()` treats
    `frm is None` as "a seed the linker wrote down", and a table edge with no
    `frm` would count its handlers as linker-named in the one section whose
    job is telling those apart.
    """
    out = []
    for site, site_rows in sorted(index_table_sites(d, region).items()):
        if site not in reached:
            continue
        for row in site_rows:
            out.append({"addr": row["target_rt"], "kind": KIND_INDEX,
                        "site": site, "edge_row": row["index"],
                        "base": row["entry_runtime"]})
    for table in dispatch_tables(d, region):
        if table["site"] not in reached:
            continue
        for i in range(table["rows"]):
            out.append({"addr": table["base"] + STRIDE * i, "kind": table["kind"],
                        "site": table["site"], "edge_row": f"row{i}",
                        "base": f"0x{table['base']:04X}"})
    return out


def unreachable(d: bytes, region: str, reached):
    """The dispatch tables this region has but its closure does not fire. The
    negative half of the calibration `edges()` applies silently: a table
    outside the walk is named rather than dropped, so a consumer can tell it
    from a table the image does not contain."""
    return [t for t in dispatch_tables(d, region) if t["site"] not in reached]


# --- self-test ---------------------------------------------------------------
#
# Relations, not a census. Every figure this file would pin is a count over the
# committed firmware, and the pins that *are* here are ones a re-derived table
# could break silently: a shape that stops matching, a row that stops being an
# `ljmp`, a site that stops holding the reader in the window it was read in.

# The `0xEFE7` determination, as the reason rather than the conclusion. The
# question was whether the seventh `jmp @a+dptr` byte-scan hit is a dispatch or
# a byte inside a data table, and an earlier reading of this issue held it a
# table byte. It is a dispatch, and the bytes underneath that answer cannot be
# moved by another merge:
#
#   * 0xEFE7 holds 0x73, the last byte of the 14-byte routine at 0xEFDA, which
#     `ec/decompiled/index.csv` already records as
#     `bank1,EFDA,dispatch_index_3x_from_byte_00,14` and
#     `ec/decompiled/bank1/EFDA.asm` draws as `jmp @A+DPTR`;
#   * the table it dispatches is loaded two instructions earlier by
#     `mov dptr,#0xefe8` at 0xEF9A, immediately before `lcall 0xEFDA` at
#     0xEF9D -- so the base is a `mov dptr` six bytes up, exactly the shape the
#     other sites use;
#   * row 14 of that table is at 0xF012 and reads `02 f0 40` = `ljmp 0xF040`,
#     which the committed inventory independently names
#     `bank1,F012,table_efe8_row14_ljmp_f040`.
#
# Per the pattern `bank-attribution.md` 4 already uses for 0x808C, the bytes
# are the pin and the listing is not: `ef/decompiled/*.asm` is a regenerable
# export, so a later annotation redrawing them is not a regression.
DISPATCHER = {
    "region": "bank1",
    "jmp": 0xEFE7,
    "jmp_byte": b"\x73",
    "routine": (0xEFDA, 14),        # half-open span of the dispatcher itself
    "load": 0xEF9A,
    "load_bytes": b"\x90\xef\xe8",
    "call": 0xEF9D,
    "call_bytes": b"\x12\xef\xda",
    "base": 0xEFE8,
    "rows": 16,                     # the dispatcher's own `anl 0x00,#0x0f`
    "row14": 0xF012,
    "row14_bytes": b"\x02\xf0\x40",
}


def _bytes_at(d, region, addr, n):
    off = offset_for_runtime(addr, region)
    return None if off is None else d[off:off + n]


def self_test() -> int:
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {text}")

    print("dispatch_edges.py --self-test")
    print()
    print("No firmware on the command line: every check reads the committed")
    print("image relative to this file, and says so rather than taking a path")
    print("that could be pointed at something else.")
    print()

    sys.path.insert(0, HERE)
    import bank_attribution as ba

    d = open(os.path.join(EC, "firmware", "GMxMGxx_11.800"), "rb").read()
    _rows, _stubs, tramp = ba.survey(d)
    seeds = ba.seeds_for(tramp)
    closures = {b: ba.closure(d, b, seeds[b]) for b in (0, 1)}

    # The 0xEFE7 determination. Checked as the reason -- the bytes at the jump,
    # the base-loading `mov dptr`, the call into the dispatcher, and the row the
    # committed inventory independently names -- because the conclusion
    # "therefore it is a dispatch" is a reading and the bytes are the evidence.
    det = DISPATCHER
    region = det["region"]
    jmp_raw = _bytes_at(d, region, det["jmp"], 1)
    load_raw = _bytes_at(d, region, det["load"], 3)
    call_raw = _bytes_at(d, region, det["call"], 3)
    row_raw = _bytes_at(d, region, det["row14"], 3)
    routine = det["routine"]
    routine_raw = _bytes_at(d, region, routine[0], routine[1])
    check(jmp_raw == det["jmp_byte"] and routine_raw is not None
          and routine_raw.endswith(det["jmp_byte"]) and len(routine_raw) == routine[1],
          f"{region} 0x{det['jmp']:04X} is `{jmp_raw.hex(' ') if jmp_raw else '?'}`, "
          f"the last byte of the {routine[1]}-byte routine at "
          f"0x{routine[0]:04X} that the committed inventory names "
          f"`dispatch_index_3x_from_byte_00` -- a dispatch, not a byte in a table")
    check(load_raw == det["load_bytes"] and call_raw == det["call_bytes"],
          f"and its base is loaded by `{load_raw.hex(' ') if load_raw else '?'}` "
          f"at 0x{det['load']:04X} immediately before `{call_raw.hex(' ') if call_raw else '?'}` "
          f"at 0x{det['call']:04X}, the `mov dptr` + `lcall` shape the other "
          f"sites use"
          + ("" if load_raw == det["load_bytes"] and call_raw == det["call_bytes"]
             else f" -- expected `{det['load_bytes'].hex(' ')}` and "
                  f"`{det['call_bytes'].hex(' ')}`"))
    check(row_raw == det["row14_bytes"],
          f"and row 14 of the 0x{det['base']:04X} table is "
          f"`{row_raw.hex(' ') if row_raw else '?'}` at 0x{det['row14']:04X}, which "
          f"the committed inventory independently names "
          f"`table_efe8_row14_ljmp_f040`"
          + ("" if row_raw == det["row14_bytes"]
             else f" -- expected `{det['row14_bytes'].hex(' ')}`"))

    print()
    print("Index-table edges: the CSV's `site` is a bare address, so each row")
    print("is re-checked against the bytes in the window being walked.")
    banked = {r["site_rt"] for r in index_rows() if r["target_rt"] >= BANK_FLOOR}
    common = {r["site_rt"] for r in index_rows() if r["site_rt"] < BANK_FLOOR}
    check(not (banked & common),
          f"the {len(banked)} banked-target sites and the {len(common)} "
          f"common-area sites in index-table-entries.csv are disjoint, so the "
          f"floor splits them without a third case")
    excluded = excluded_index_sites(d, "bank0")
    check(len(excluded) == len(common)
          and {s for s, _ in excluded} == common
          and all(why == EXCLUDED_COMMON for _s, why in excluded),
          f"and all {len(excluded)} common-area site(s) are reported excluded "
          f"with the reason rather than dropped: "
          + ", ".join(f"0x{s:04X}" for s, _ in excluded[:6]))
    for bank in (0, 1):
        name = f"bank{bank}"
        admitted = index_table_sites(d, name)
        rows = sum(len(v) for v in admitted.values())
        targets = {r["target_rt"] for v in admitted.values() for r in v}
        check(all(t >= BANK_FLOOR for t in targets),
              f"{name}: {rows} rows over {len(admitted)} sites name "
              f"{len(targets)} distinct banked targets, every one at or above "
              f"0x{BANK_FLOOR:04X}, so no edge lands in the common area")
        # The two addresses that are the same number in both bank windows, so
        # the gate is what decides -- asserted here because it is invisible in
        # the CSV, which carries `site` with no region on it.
        for site in (0x8662, 0x918A):
            off = offset_for_runtime(site, name)
            raw = d[off:off + 3] if off is not None else b""
            check((raw == READER_CALL) == (site in admitted),
                  f"{name} 0x{site:04X} is `{raw.hex(' ')}` -- "
                  + ("the `lcall 0x7151`, so its table is admitted here"
                     if raw == READER_CALL else
                     "not the reader, so the row stays out of this window's "
                     "closure even though the bare address is the one the CSV "
                     "names"))

    print()
    print("Dispatch-table edges: the row count comes from the `anl` mask the")
    print("shape carries, and every row must be the `ljmp` that makes seeding a")
    print("row address enough.")
    for bank in (0, 1):
        name = f"bank{bank}"
        tables = dispatch_tables(d, name)
        shaped = collections.Counter(t["shape"] for t in tables)
        check(all(t["rows"] >= 2 for t in tables)
              and all(t["base"] >= BANK_FLOOR for t in tables)
              and all(_ljmp_run(d, name, t["base"], t["rows"]) == t["rows"]
                      for t in tables),
              f"{name}: {len(tables)} table(s) -- "
              + ", ".join(f"{n} {shape}" for shape, n in sorted(shaped.items()))
              + f" -- every row seeded is a three-byte `ljmp` from a banked "
                f"base, and every row count came from its mask")
        # The shapes must not overlap: an entry the inline scan found and the
        # shared scan also found would be two provenance values for one
        # dispatch, and the pair would not partition the tables.
        check(len({t["site"] for t in tables}) == len(tables),
              f"{name}: the two shapes name {len(tables)} distinct sites, so "
              f"the provenance values partition the tables rather than overlap")

    print()
    print("A mask that admits more indices than the table has rows is reported,")
    print("not padded: the site dispatches, and the indices past the last `ljmp`")
    print("would read whatever follows the table.")
    for bank in (0, 1):
        name = f"bank{bank}"
        cut = truncated_tables(d, name)
        for t in cut:
            print(f"  --   {name} site 0x{t['site']:04X}: mask admits "
                  f"{t['masked']} indices, table has {t['rows']} `ljmp` row(s) "
                  f"from 0x{t['base']:04X}; the rest are not seeded")
        check(all(t["rows"] < t["masked"] and t["rows"] >= 1 for t in cut),
              f"{name}: {len(cut)} table(s) short of their mask, each stopped at "
              f"its last real `ljmp` row rather than filled in"
              if cut else
              f"{name}: every table's mask matches its `ljmp` row count, so "
              f"nothing had to be truncated")

    print()
    print("Reachability is what separates a table that fires from one that does")
    print("not, and the negative half is reported rather than dropped.")
    for bank in (0, 1):
        name = f"bank{bank}"
        reached = closures[bank][0]
        tables = dispatch_tables(d, name)
        fired = [t for t in tables if t["site"] in reached]
        idle = unreachable(d, name, reached)
        got = edges(d, name, reached)
        sites = {e["site"] for e in got if e["kind"] != KIND_INDEX}
        check(sorted(sites) == sorted(t["site"] for t in fired),
              f"{name}: {len(fired)} of its {len(tables)} table(s) have the "
              f"`jmp @a+dptr` inside the walk and fire; the other "
              f"{len(idle)} are named by unreachable() instead of vanishing, "
              f"and no edge exists for a site outside the walk")
        check(all(e["kind"] in KINDS for e in got),
              f"{name}: every one of its {len(got)} edge(s) carries one of "
              f"{len(KINDS)} provenance values, so the mechanisms stay "
              f"separable downstream")
        check(all(e["site"] > 0 for e in got),
              f"{name}: and every edge names the site that produced it, which is "
              f"what keeps entry_chain() from reading a table handler as a "
              f"linker-written seed")

    print()
    print("A `dispatch-table` edge seeds the ROW address, so the walk derives the")
    print("target rather than this file asserting it.")
    fired = [t for t in dispatch_tables(d, "bank1") if t["site"] in closures[1][0]]
    check(bool(fired), "bank1 has at least one firing table to check the row "
                      "address against")
    for table in fired:
        off = offset_for_runtime(table["base"], "bank1")
        raw = d[off:off + 3]
        target = raw[1] << 8 | raw[2]
        check(raw[0] == LJMP and target >= BANK_FLOOR,
              f"bank1 row 0 of the 0x{table['base']:04X} table (site "
              f"0x{table['site']:04X}, {table['shape']}) is `{raw.hex(' ')}` = "
              f"`ljmp 0x{target:04X}` -- seeding 0x{table['base']:04X} and "
              f"letting descend() follow it reaches a banked target")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the 0xEFE7 determination, the reader-byte "
                         "gate on the index-table sites, and the dispatch "
                         "shapes against the committed image")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())