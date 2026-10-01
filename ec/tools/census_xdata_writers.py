#!/usr/bin/env python3
"""Enumerate the write sites for one XDATA byte, and say what each store is.

`trace_xdata_refs.classify()` answers "what happens in an 8-instruction window
around this `MOV DPTR,#addr`", and what it prints is a **direction**: `read x1`,
`write x1`, `read x1, write x1`. A direction is not a writer. The `0x0751` site
table carries 29 such cells and 8 of them say `write`, and neither the cell nor
the `static_refs: 29` beside it in `registers.yaml` says *which* of those sites
store, *what* they store, or *under what condition they run*. That is the gap
`ec/annotations/manual-fan-ctrl-0751.md` 9 and the `MANUAL_FAN_CTRL` note both
hedge around with the words "at least three paths", and this is the measurement
behind either a number or a stated reason there cannot be one.

**Nothing is re-implemented here.** The site list, the window, the
classification and the terminator are `trace_xdata_refs.sites_for()`,
`walk_why()` and `classify()`; the two sites whose own window holds no `movx`
are resolved by `walk_flow_follow.follow_site()`, which is the only way their
stores are visible at all; and the blind spot that keeps the count open is
read out of the committed `walk_branch_arms` table. A second opcode walk over
the same bytes would be a second thing to keep in step with the first, which is
what `docs/findings/dptr-rebuild-walk-guard.md` is about.

**One row per site, not per store.** `0xA818` carries two read-modify-writes of
`0x0751` in one window, and `ec-07c4-07d5-sites.md` 2 draws exactly this line:
a count of instructions is not a count of decisions. So `store_count` is a
column and the site is the unit.

**The blind-store / read-modify-write split is the interesting half.**
`access_shape` is derived, from a closed vocabulary, by one rule: a
`movx @dptr,a` with a `movx a,@dptr` still pending is a read-modify-write, and
one without is a blind store -- the accumulator did not come from this byte, so
the store replaces it outright. Those are the two shapes a driver author has to
plan around, because a blind store is the only one that can destroy a bit a
host set and a read-modify-write is the only one that provably preserves every
bit the EC does not name. `mask` says what the store did to the accumulator
between the load and the store; it is a rendering of the bytes rather than a
classification of them, so a modifier this tool has never seen prints itself
instead of being folded into a shape there is no vocabulary for.

**The condition columns are hand-filled, and that is the arrangement
`xdata-0860-census-sites.csv` and `check_site_census.py` already use.** The
mechanical columns are derived from the image on every run; `condition` and
`condition_evidence` are read off the branch that gates each site by a person
reading the listing, and `--check` carries them through rather than
regenerating them. Two rules make that safe: the vocabulary is closed, and a
condition with no evidence cell is refused rather than rendered into a row that
would read as an answer.

**What `host-write-through` coming back empty means.** It is a bucket in the
vocabulary, not a row in the table, and its being empty is the answer issues
#102 and #104 need: the host writes `0x0751` over `ECRR`, and the image holds no
`MOV DPTR,#0x0751` site for that path, so no instruction for it can be found
here. "Not found by this method", never "the host does not write it" -- and
that is why the empty bucket is reported with a reason on every run rather than
left out, because a bucket quietly missing and a bucket nobody looked for are
the same file.

**And the count is not closed, and the tool says why on every run.**
`walk_branch_arms.descend()` charges a `movx` to no address once DPTR has been
rebuilt at run time, and across the `0x0751` arm table that is 100 stores over
its 171 rows. Any of them could be a `0x0751` writer that no site scan can
name. That is issue #34, and it stays open; `--self-test` holds the figure
against the committed table so the gap is a number that moves rather than a
caveat that gets copied forward.

**Nothing here is measured on hardware.** A store is an instruction, not an
event: whether the EC acts on the value, and whether the condition under which
it stores is ever true at run time, are both open, and
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` 4 step 6 is where a
human with the machine answers the second. `MANUAL_FAN_CTRL` stays
`present-untested` and nothing here moves it.

Usage:
    python3 census_xdata_writers.py ../firmware/GMxMGxx_11.800 0x0751
    python3 census_xdata_writers.py ../firmware/GMxMGxx_11.800 0x0751 --csv
    python3 census_xdata_writers.py --self-test ../firmware/GMxMGxx_11.800
    python3 census_xdata_writers.py --check
"""
import argparse
import collections
import csv
import difflib
import io
import os
import sys

from check_register_counts import counts_for
from disasm8051 import OPCODE_LEN
from trace_xdata_refs import (PD_MARKER, budget_end, classify, mnemonic,
                              offset_for_runtime, region_of, runtime_addr,
                              sites_for, walk_why)
# Both one-directional: walk_flow_follow and walk_branch_arms import only
# trace_xdata_refs and disasm8051, so neither can reach back here.
from walk_flow_follow import MAX_DEPTH, MAX_INSNS, NO_MOVX, follow_site

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
ANNOT = os.path.join(HERE, os.pardir, "annotations")
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")

# The two tables this tool holds to, named rather than discovered. The
# mechanical columns are address-parameterised -- 0x075B/0x075C and the PL bytes
# are the obvious next caller -- but the hand-filled columns are per-address
# prose, so a committed table is per-address too and `--check` has to be told
# which one it is diffing. That is a refusal rather than a directory glob: a
# glob would let `--check` diff against whichever file sorted first, and a
# check that picks its own subject is a check that decides what the file says.
WRITERS_CSV = os.path.join(ANNOT, "manual-fan-ctrl-0751-writers.csv")
SITES_CSV = os.path.join(ANNOT, "manual-fan-ctrl-0751-sites.csv")
ARMS_CSV = os.path.join(ANNOT, "manual-fan-ctrl-0751-arms.csv")

# `walk_why()`'s own default, named here so the budget-truncation test is a
# comparison against the function's parameter rather than a threshold somebody
# chose.
WINDOW = walk_why.__defaults__[0]

# `movx a,@dptr` and `movx @dptr,a` -- the two opcodes `classify()` already
# counts, and the whole question this tool asks.
MOVX_READ = 0xE0
MOVX_WRITE = 0xF0

# How a store reached the byte. Derived, closed, and the whole of
# `access_shape`.
BLIND = "blind-store"
RMW = "read-modify-write"

# How much is established about a site. `window-truncated` is not a lesser kind
# of found: the window ended on the budget token rather than on a control-flow
# opcode, so a longer window might hold more -- `walk_budget_census.py` is
# where that mechanism is committed -- and the row says so instead of letting a
# cut window read as a complete one. `unresolved` is a site the classification
# calls a writer and the store scan could not locate (an indirect `movx @Ri`, or
# a write behind a DPTR handoff the follow did not resolve), and it carries the
# reason in `mask` rather than reporting a store it did not find.
FOUND = "found"
TRUNCATED = "window-truncated"
UNRESOLVED = "unresolved"
STATUSES = (FOUND, TRUNCATED, UNRESOLVED)

# What the hand-filled column may say, and nothing else. The four are the ones
# issue #196 named; the order is the order they are reported in.
BOOT_DEFAULT = "boot-default"
TEMPERATURE_GATE = "temperature-gate"
MODE_DECODE = "mode-decode"
HOST_WRITE_THROUGH = "host-write-through"
CONDITIONS = (BOOT_DEFAULT, TEMPERATURE_GATE, MODE_DECODE, HOST_WRITE_THROUGH)

# Why a bucket with no row is the shape it is. `host-write-through` is the one
# this census expects to come back empty, and an empty bucket is a result, so it
# is printed with a reason rather than omitted.
BUCKET_REASONS = {
    HOST_WRITE_THROUGH: "the host writes 0x0751 over ECRR, which is not a "
                        "MOV DPTR,#0x0751 site, so no instruction for that "
                        "path exists to be found here. Not found by this "
                        "method, never 'the host does not write it'",
}

# `mask` for a store nothing was read into, and for a load-then-store with
# nothing in between. Two cells for two shapes, because "the accumulator held an
# unrelated value" and "the accumulator held the byte unmodified" are different
# statements about what a store can destroy.
NO_SOURCE = "no load"
UNMODIFIED = "unmodified"

# Several stores in one window render in program order, joined by this rather
# than by the ` ; ` the site tables use between instructions -- a reader
# meeting ` ; ` in a `mask` cell would take it for a disassembly.
SEQUENCE = " then "

# Derived columns in order, then the hand-filled ones. `addr` is first so a
# committed table names the byte it is about and `--check` can take the address
# from the file rather than the command line -- the hand-filled columns are
# per-address prose, so a check that was handed the address separately could be
# pointed at a table that does not describe it. `site_file_offset` is the join
# key into the sites table rather than a row number: a bank window maps one
# file offset to a different runtime address per bank, and a row index is a
# value every inserted site has to renumber.
COLUMNS = ["addr", "site_runtime", "region", "site_file_offset",
           "store_runtime", "access_shape", "mask", "store_count", "status"]
HAND_COLUMNS = ["condition", "condition_evidence"]
CSV_COLUMNS = COLUMNS + HAND_COLUMNS


def repo_path(path: str) -> str:
    return os.path.relpath(path, REPO)


def render(text: str) -> str:
    """`disasm8051.mnemonic()`'s spacing collapsed -- the spelling the committed
    `window` cells carry, so a `mask` cell reads beside them."""
    return " ".join(text.split())


def stores_in(insns):
    """[(store offset, shape, mask cell), ...] for one decoded segment.

    The rule is one sentence and it is the whole of `access_shape`: a
    `movx @dptr,a` is a read-modify-write when a `movx a,@dptr` is still
    pending, and a blind store when none is. "Pending" is cleared by *any*
    `movx`, because within one segment DPTR cannot move -- `walk_why()` returns
    at `is_dptr_rebuild()` and names the reload as the terminator -- so an
    intervening `movx` of either direction is on this same byte and is the
    register's own.

    The store scan deliberately does not stop at a control-flow opcode the way
    `walk_why()` does. A segment handed over by `follow_site()` is already
    `walk_why()`'s output, so the flow stop has been paid for where it belongs,
    and a second one here would silently drop the store after a call. What it
    does do is refuse to reason across a `movx` it did not decode, which is the
    same bound the window itself carries.
    """
    out = []
    loaded = False
    since = []             # the rendered text between the load and the store
    for i, raw, text in insns:
        op = raw[0]
        if op == MOVX_READ:
            loaded, since = True, []
        elif op == MOVX_WRITE:
            if loaded:
                cell = SEQUENCE.join(since) if since else UNMODIFIED
            else:
                cell = NO_SOURCE
            out.append((i, RMW if loaded else BLIND, cell))
            # A store is not a load: whether the *next* store is a modify
            # depends on whether a read followed this one, not on this one.
            loaded, since = False, []
        elif loaded:
            since.append(render(text))
    return out


def site_record(d: bytes, addr: int, off: int, pd_verified: bool) -> dict:
    """One site: the direction the window alone gives, the direction the
    follow gives, whether it is a writer, its stores, and the status.

    Both directions are kept because they are different claims.
    `manual-fan-ctrl-0751-sites.csv`'s `access` cell is the linear one, and
    `--check` holds this tool's re-derivation of it against the committed
    table; the followed one is weaker -- it was reached past a branch -- and
    would fail that comparison for the two sites it applies to, which is why
    the two are separate fields rather than one over-written.
    """
    insns, why = walk_why(d, off, WINDOW)
    linear = classify(insns)
    direction, stores, followed = linear, [], False
    if linear == NO_MOVX:
        f = follow_site(d, addr, off, pd_verified, MAX_DEPTH, MAX_INSNS)
        direction = f.followed
        # follow_site()'s blocks are (segment start runtime, [(runtime, text)]),
        # which has lost the raw bytes the store scan needs, so each segment is
        # re-walked at the same bounds the follow used rather than recovered:
        # same function, same budgets, and a scan over a reconstructed
        # instruction would be a second decoder to keep in step.
        for n, (start, _) in enumerate(f.blocks):
            noff = offset_for_runtime(start, f.region)
            if noff is None:
                # Unreachable while follow_site() stands: it appends a block
                # only after `offset_for_runtime()` has resolved that same
                # start, so a None here means it changed. Raised rather than
                # defaulted, because a silent `or off` would re-scan the
                # anchor -- which holds no `movx` for exactly the sites this
                # branch exists for -- and report a site that has stores as
                # one that has none.
                raise ValueError(
                    f"0x{start:04X} is in follow_site()'s blocks but not "
                    f"reachable from region {f.region}; the follow and this "
                    "scan no longer agree on what it walked")
            seg = walk_why(d, noff, WINDOW if n == 0 else MAX_INSNS)[0]
            stores += [(i, shape, cell) for i, shape, cell in stores_in(seg)]
        followed = True
    else:
        stores = stores_in(insns)

    writes = "write" in direction
    if not writes:
        status = None
    elif not stores:
        status = UNRESOLVED
    elif why == budget_end(WINDOW):
        status = TRUNCATED
    else:
        status = FOUND
    return {"offset": off, "region": region_of(off, pd_verified)[0],
            "runtime": runtime_addr(off, pd_verified), "linear": linear,
            "direction": direction, "followed": followed, "writer": writes,
            "stores": stores, "status": status, "terminator": why}


def row_for(addr: int, site: dict, pd_verified: bool) -> dict:
    """One writer site as a row: the mechanical columns, in the committed
    spelling.

    Split out of `writer_rows()` and pure, because `unresolved` is a status the
    committed data never exercises -- no `0x0751` site's window claims a write
    the scan cannot place -- and a status nothing can build is a status nothing
    can check. The suite hands this a hand-made record and reads the row.
    """
    row = {"addr": f"0x{addr:04X}",
           "site_runtime": f"0x{site['runtime']:04X}", "region": site["region"],
           "site_file_offset": f"0x{site['offset']:05X}",
           "store_runtime": SEQUENCE.join(
               f"0x{runtime_addr(i, pd_verified):04X}"
               for i, _, _ in site["stores"]),
           "access_shape": site["stores"][0][1] if site["stores"] else "",
           "mask": SEQUENCE.join(cell for _, _, cell in site["stores"]),
           "store_count": str(len(site["stores"])), "status": site["status"]}
    if site["status"] == UNRESOLVED:
        # The reason goes into the cell a reader is already looking at, rather
        # than into a column that is empty on every other row. A `store_count`
        # of 0 beside a direction that says "write" is the contradiction, and
        # the mask cell is where a reader will look for what happened instead.
        row["mask"] = f"{site['direction']} -- no movx @dptr,a in the window"
    return row


def writer_rows(d: bytes, addr: int, pd_verified: bool):
    """(rows, all_sites, problems) for one address.

    `rows` is one dict per **writer site**, in file order, with the mechanical
    columns filled and the hand-filled ones absent. `all_sites` is every site,
    writer or not, so the caller can reconcile rather than take the count on
    trust.

    The reconciliations are `register_ref_table.reconcile()`'s, carried here
    rather than inherited: the scanned sites have to sum to what `sites_for()`
    found and main + PD to the file-wide total, so a site dropped between the
    two is a failure rather than a quietly shorter table.
    """
    all_sites = [site_record(d, addr, off, pd_verified)
                 for off in sites_for(d, addr)]
    total, main, pd = counts_for(d, addr, pd_verified)
    writers = [s for s in all_sites if s["writer"]]
    problems = []
    if len(all_sites) != total:
        problems.append(
            f"0x{addr:04X}: {len(all_sites)} site(s) scanned, {total} found by "
            "sites_for() -- a site was dropped between the two")
    if main + pd != total:
        problems.append(
            f"0x{addr:04X}: {main} + {pd} sites do not add up to {total} -- "
            "some site is outside the mapped regions")
    if len(writers) + len(all_sites) - len(writers) != total:
        # Unreachable by construction and asserted anyway: the partition is
        # this tool's headline claim, and a claim nothing checks is a claim
        # that decays.
        problems.append(f"0x{addr:04X}: writer and read-only sites do not "
                        "add up to the site count")
    return [row_for(addr, s, pd_verified) for s in writers], all_sites, problems


def read_committed(path: str):
    """The rows of a committed writers table, in file order.

    A file with the wrong header is a ValueError rather than an empty
    population, for `walk_budget_census.read_sites()`'s reason: a silently
    empty read is a check that reports nothing and exits 0.
    """
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        missing = sorted(set(CSV_COLUMNS) - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"{repo_path(path)} has no {', '.join(missing)} "
                             "column(s); it is not a census_xdata_writers table")
        return [dict(r) for r in reader]


def addresses_in(committed):
    """The addresses a committed table is about, in order.

    `--check` takes its subject from here rather than from the command line,
    because the hand-filled columns are per-address prose: handed the address
    separately, the same command would check a table about one byte against the
    census of another and report every row as drift. A table with no row at all
    yields no address, and the caller says so rather than guessing one.
    """
    out = []
    for row in committed:
        try:
            addr = int(row["addr"], 16)
        except (KeyError, ValueError):
            raise ValueError("a committed writers table row has no readable "
                             "`addr`; the column is what --check takes the "
                             "address from")
        if addr not in out:
            out.append(addr)
    return out


def hand_for(committed, offset: str) -> dict:
    """The hand-filled cells for one site, or empty ones.

    A site with no committed row comes back empty rather than raising, so the
    two directions of the join are two separate reports and the first one
    printed is the interesting one.
    """
    for row in committed:
        if row["site_file_offset"] == offset:
            return {c: row[c] for c in HAND_COLUMNS}
    return {c: "" for c in HAND_COLUMNS}


def validate_rows(rows, committed):
    """Problems with the hand-filled cells, and the conditions seen.

    Every clause is a refusal. `condition` is a closed vocabulary, a condition
    with no evidence is a claim with nothing behind it, evidence with no
    condition is a citation of a row that does not exist, and a committed row
    with no derived site is a site the scan cannot find -- which is the
    direction a `--check` that only diffed would not see, because a diff
    reports it as one changed line among others rather than as a table and an
    image that no longer describe the same set of sites.
    """
    problems = []
    seen = set()
    derived = {r["site_file_offset"] for r in rows}
    for row in rows:
        where = row["site_file_offset"]
        cells = hand_for(committed, where)
        condition, evidence = cells["condition"], cells["condition_evidence"]
        if row["status"] not in STATUSES:
            problems.append(f"{where}: status {row['status']!r} is not one of "
                            f"{', '.join(STATUSES)}")
        if row["access_shape"] not in (BLIND, RMW):
            # An `unresolved` row has no shape by definition -- that is what
            # "unresolved" means -- so the empty cell is allowed there and
            # nowhere else. Without the exemption a real unresolved site could
            # never be committed, and the status would be one the tool can
            # report but its own table cannot carry.
            if not (row["status"] == UNRESOLVED and not row["access_shape"]):
                problems.append(f"{where}: access_shape "
                                f"{row['access_shape']!r} is not one of "
                                f"{BLIND}, {RMW}")
        if condition and condition not in CONDITIONS:
            problems.append(f"{where}: condition {condition!r} is not one of "
                            f"{', '.join(CONDITIONS)}")
        if condition and not evidence:
            problems.append(f"{where}: condition {condition!r} with no "
                            "condition_evidence -- a hand-filled value with "
                            "nothing behind it")
        if not condition and evidence:
            problems.append(f"{where}: condition_evidence {evidence!r} with no "
                            "condition")
        seen.add(condition)
    for row in committed:
        if row["site_file_offset"] not in derived:
            problems.append(
                f"{row['site_file_offset']}: a row in the committed table that "
                "this run derived no writer site for -- the table and the image "
                "no longer describe the same set of sites")
    return problems, seen


def csv_table(rows, committed, notes: bool = True):
    """(the table as a string, problems) so `--check` diffs the same bytes it
    prints.

    The hand-filled cells are carried in from `committed` rather than
    regenerated -- that is the whole arrangement -- and a bucket with no row is
    reported to stderr rather than rendered, so an empty `host-write-through`
    is a recorded result and a vocabulary someone has grown is a failure.
    """
    problems, seen = validate_rows(rows, committed)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_COLUMNS)
    for row in rows:
        cells = {c: row[c] for c in COLUMNS} | hand_for(committed, row["site_file_offset"])
        w.writerow([cells[c] for c in CSV_COLUMNS])
    if notes:
        for condition in CONDITIONS:
            if condition not in seen:
                print(f"note: no writer site carries condition {condition!r} -- "
                      f"{BUCKET_REASONS.get(condition, 'no reason recorded')}",
                      file=sys.stderr)
    return buf.getvalue(), problems


def check_sites(all_sites, addr: int, path: str = SITES_CSV):
    """(problems, read-only sites) holding the derivation to the committed
    site table, in both directions.

    Re-deriving `classify()` from the image has to give back the `access` cell
    the table committed, or this run is measuring a different walk than the one
    the table was cut with and every row above it is about the wrong
    population. The comparison is against the **linear** direction for the
    reason `site_record()` keeps the two apart: the committed `access` cell is
    the window's own verdict, and a site the flow follow resolved is a weaker
    claim that would fail the comparison for exactly the two rows it is here to
    explain.
    """
    problems = []
    # The address is compared as the *spelling* the table uses. An int here
    # would silently match no row, and the join would then report every derived
    # site as unrecorded -- a check that fails for a reason of its own making,
    # which is worse than no check because it reads as a disagreement about the
    # firmware.
    want = f"0x{addr:04X}"
    try:
        with open(path, newline="") as f:
            committed = {r["file_offset"]: r
                         for r in csv.DictReader(f) if r["addr"] == want}
    except OSError as e:
        return [f"{repo_path(path)}: {e}"], []
    derived = {f"0x{s['offset']:05X}": s for s in all_sites}
    for offset, row in committed.items():
        site = derived.get(offset)
        if site is None:
            problems.append(f"{offset}: a {want} site in {repo_path(path)} that "
                            "sites_for() no longer finds")
            continue
        if site["linear"] != row["access"]:
            problems.append(
                f"{offset}: this run classifies the site {site['linear']!r} "
                f"where {repo_path(path)} commits {row['access']!r}")
    for offset in derived:
        if offset not in committed:
            problems.append(f"{offset}: a {want} site this run finds that "
                            f"{repo_path(path)} does not record")
    return problems, [s for s in all_sites if not s["writer"]]


def check_table(generated: str, path: str) -> int:
    """Exit code for `--check`: 0 when this run reproduces `path` exactly.

    Read with `newline=""` for the reason `walk_budget_census.check_table()`
    gives, and a **missing** file is a failure rather than something to create:
    a `--check` that writes the file it is checking has stopped checking it.
    """
    try:
        with open(path, newline="") as f:
            on_disk = f.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if generated == on_disk:
        print(f"{repo_path(path)}: this run reproduces it byte for byte "
              f"({generated.count(chr(10))} lines)")
        return 0
    print(f"note: {repo_path(path)} differs from what this run produced. The "
          "mechanical columns are the product of the command on the page that "
          "names it, so regenerate rather than edit; `condition` and "
          "`condition_evidence` are hand-filled off the listing and are carried "
          "through, so re-read the gate before changing one", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(), generated.splitlines(),
                                     "committed", "generated", lineterm="", n=0):
        print(line, file=sys.stderr)
    return 1


def arms_gap(addr: str = "0x0751"):
    """((rows, unattributed stores), reason) for one address's committed arms
    table.

    Read out of the committed CSV rather than re-run, because the table is the
    thing a reader is being shown. This is the reason the writer count is not
    closed: a `movx` after DPTR has been rebuilt at run time is charged to no
    address by `walk_branch_arms.descend()`, and any of these could be a writer
    that no site scan names.
    """
    rows = stores = 0
    try:
        with open(ARMS_CSV, newline="") as f:
            for row in csv.DictReader(f):
                if row["addr"] != addr:
                    continue
                rows += 1
                stores += int(row["unattributed"] or 0)
    except (OSError, ValueError, KeyError) as e:
        return None, f"{repo_path(ARMS_CSV)}: {e}"
    return (rows, stores), None


# --- self-test ---------------------------------------------------------------
#
# Every fixture is a byte transcription, never an address in the image, for the
# reason `test_walk_branch_arms.py` states in its own docstring: a fixture
# anchored at an address keeps testing what it was written to test only until
# the bytes there change. These were read out of `r2 -a 8051` against a
# `make_bank_image.py` bank image, so the store scan is graded by a second
# disassembler rather than by its own decoder.
#
# The shapes and masks are hand-transcribed; the offsets are the fixture's,
# because that is all a `common`-region buffer can name. Each row is
# (label, bytes, expected [(store offset, shape, mask), ...]).
SELF_TEST_STORES = (
    # 0x0898A: FAN BOOST cleared when both sensors are under 0x46. One store,
    # one bit.
    ("anl 0xbf", "90 07 51 e0 54 bf f0 7f ac 12 a7 3f",
     [(0x06, RMW, "anl a,#0xbf")]),
    # 0x0A812: the boot-time Gaming default. The `clr a` that supplies the
    # stored value is in the *previous* window, behind the site's own
    # `mov dptr`, so nothing here was read from 0x0751 -- the blind store, and
    # the one that can destroy a bit a host set.
    ("blind store", "90 07 51 f0 80 0b",
     [(0x03, BLIND, NO_SOURCE)]),
    # 0x0A818: two read-modify-writes in one site. The pair is why the row is a
    # site and `store_count` a column.
    ("two stores in one site", "90 07 51 e0 54 ef f0 e0 44 80 f0 e4 ff",
     [(0x06, RMW, "anl a,#0xef"), (0x0A, RMW, "orl a,#0x80")]),
    # 0x0A3BB: `xrl a,#0x40` is a toggle, not a set or a clear, and the mask
    # column has to say which rather than render all three the same.
    ("xrl toggle", "90 07 51 e0 64 40 f0 22",
     [(0x06, RMW, "xrl a,#0x40")]),
    # 0x0ABE8's and 0x0C741's fall-through, as the flow follow re-decodes it:
    # a segment that starts at an access rather than at a `mov dptr`.
    ("two stores in a followed segment", "e0 54 7f f0 e0 44 10 f0 22",
     [(0x03, RMW, "anl a,#0x7f"), (0x07, RMW, "orl a,#0x10")]),
    # A load, a store, then a second store with no load between. The shape a
    # scan that treated a store as a load would get wrong, and the one the
    # "a store is not a load" reset exists for.
    ("load, store, store", "e0 f0 44 80 f0",
     [(0x01, RMW, UNMODIFIED), (0x04, BLIND, NO_SOURCE)]),
    # A load and a store with nothing in between is not a blind store: the
    # `UNMODIFIED` cell is the whole difference, and a scan that answered
    # "blind" to everything would pass most of the cases above.
    ("load then store", "e0 f0",
     [(0x01, RMW, UNMODIFIED)]),
    # One load, two stores. The second is blind, because the store before it
    # was not a read -- and each mask is the instruction between *its* store
    # and the read, not everything since.
    ("load then two stores", "e0 44 80 f0 44 10 f0",
     [(0x03, RMW, "orl a,#0x80"), (0x06, BLIND, NO_SOURCE)]),
    # A `mov dptr` between the load and the store is rendered into `mask`
    # rather than folded away, because the store is of a byte the load never
    # touched. `walk_why()` ends a window at a reload so this shape does not
    # arise in the image; it is here so a change that widened the window meets
    # it rather than reporting a modify of the wrong byte.
    ("a rebuild is not folded away", "e0 90 07 51 f0",
     [(0x04, RMW, "mov dptr,#0x0751")]),
    # Nothing stores here, and saying so is the answer rather than a zero.
    ("no store", "90 07 51 e0 30 e1 15", []),
)

# The `0x0751` figure the write-up quotes, held against the committed arms
# table. A census whose blind spot has moved must be able to say so.
SELF_TEST_ARMS = (171, 100)


def decode_fixture(raw: bytes):
    """`walk_why()`-shaped triples over a flat fixture.

    The same `disasm8051.OPCODE_LEN` lengths and the same `mnemonic()` the tool
    uses on the image, and deliberately *not* `walk_why()`: the fixtures include
    a `ret` and an `lcall`, and a walk that stopped at them would test the
    window rather than the store scan. The bytes are the oracle either way --
    what is hand-transcribed is the expected shape and mask, so a decoder that
    turned `anl` into `orl` fails on the mask string rather than agreeing with
    itself.
    """
    out = []
    i = 0
    while i < len(raw):
        n = OPCODE_LEN[raw[i]]
        out.append((i, raw[i:i + n], mnemonic(raw, i)))
        i += n
    return out


def self_test(fw_path: str) -> int:
    """Known answers, over hand-transcribed bytes and the committed arms
    table. 0 failures exits 0."""
    problems = checks = 0
    for label, raw, expected in SELF_TEST_STORES:
        got = stores_in(decode_fixture(bytes(int(t, 16) for t in raw.split())))
        checks += 1
        if got != expected:
            problems += 1
            print(f"census_xdata_writers.py: {label}: scan says "
                  f"{[(hex(i), s, c) for i, s, c in got]}, expected "
                  f"{[(hex(i), s, c) for i, s, c in expected]}", file=sys.stderr)
    gap, err = arms_gap()
    checks += 1
    if err:
        problems += 1
        print(f"census_xdata_writers.py: {err}", file=sys.stderr)
    elif gap != SELF_TEST_ARMS:
        problems += 1
        print(f"census_xdata_writers.py: the arms table records {gap[0]} row(s) "
              f"and {gap[1]} unattributed store(s); the write-up quotes "
              f"{SELF_TEST_ARMS[0]} and {SELF_TEST_ARMS[1]}", file=sys.stderr)
    # The vocabularies are closed, and both are asserted by name rather than by
    # length: a fourth status that is a synonym for one of the three would keep
    # the count right and let `--check` go green on it.
    checks += 1
    if (set(STATUSES), set(CONDITIONS)) != ({FOUND, TRUNCATED, UNRESOLVED},
                                            {BOOT_DEFAULT, TEMPERATURE_GATE,
                                             MODE_DECODE, HOST_WRITE_THROUGH}):
        problems += 1
        print("census_xdata_writers.py: the status or condition vocabulary "
              "changed; a new value is a deliberate edit to this file and to "
              "the suite, not something to let through", file=sys.stderr)
    if problems:
        print(f"{problems} failure(s)", file=sys.stderr)
        return 1
    print(f"{checks} check(s) passed: {len(SELF_TEST_STORES)} hand-transcribed "
          f"byte fixture(s) and the arms table's {SELF_TEST_ARMS[0]}-row / "
          f"{SELF_TEST_ARMS[1]}-unattributed-store figure")
    return 0


def census(d: bytes, addr: int, pd_verified: bool):
    """(summary, problems) for one address, so `main()` and the suite run the
    same path and cannot end up comparing different things."""
    rows, all_sites, problems = writer_rows(d, addr, pd_verified)
    site_problems, read_only = check_sites(all_sites, addr)
    problems += site_problems
    writers = [s for s in all_sites if s["writer"]]
    return {
        "rows": rows, "all_sites": all_sites, "read_only": read_only,
        "writers": writers,
        "stores": sum(len(s["stores"]) for s in writers),
        "shapes": collections.Counter(s["stores"][0][1] for s in writers),
        "followed": [s for s in writers if s["followed"]],
        "truncated": [s for s in writers if s["status"] == TRUNCATED],
        "unresolved": [s for s in writers if s["status"] == UNRESOLVED],
    }, problems


def report(addr: int, summary) -> None:
    """The stderr summary, on every run whatever else it did.

    The count of stores this method could not place is the half a reader of the
    table alone does not get: a table of ten sites is indistinguishable from a
    census that believes there are ten.
    """
    gap, err = arms_gap(f"0x{addr:04X}")
    print(f"0x{addr:04X}: {len(summary['writers'])} writer site(s) and "
          f"{len(summary['read_only'])} read-only site(s) of "
          f"{len(summary['all_sites'])} found by sites_for()", file=sys.stderr)
    print(f"  {summary['stores']} store instruction(s): "
          + ", ".join(f"{k} {v}" for k, v in sorted(summary["shapes"].items()))
          + (f"; {len(summary['followed'])} of them at a site resolved only by "
             "following a branch past it, which is the weaker claim"
             if summary["followed"] else ""), file=sys.stderr)
    for s in summary["truncated"]:
        print(f"  {s['runtime']:#06x}: window-truncated ({s['terminator']}) -- "
              "a longer window might hold more", file=sys.stderr)
    for s in summary["unresolved"]:
        print(f"  {s['runtime']:#06x}: unresolved -- {s['direction']}",
              file=sys.stderr)
    if err:
        print(f"  {err}", file=sys.stderr)
    else:
        print(f"  the arm walk charges {gap[1]} store(s) to no address over its "
              f"{gap[0]} row(s); any of them could be a writer this method "
              "cannot name (issue #34, open)", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("addr", nargs="?", help="hex address, e.g. 0x0751")
    ap.add_argument("--csv", action="store_true",
                    help="write the table on stdout instead of the per-site "
                         "readable census")
    ap.add_argument("--check", nargs="?", const=WRITERS_CSV, metavar="PATH",
                    help="re-derive the table and diff it against a committed "
                         "writers table, exiting non-zero on any difference "
                         f"(default: {repo_path(WRITERS_CSV)}). The address is "
                         "read from that table, not from the command line. A "
                         "missing file fails; it is never created")
    ap.add_argument("--self-test", action="store_true",
                    help="the hand-transcribed byte fixtures and the arms "
                         "table\'s unattributed figure, against r2")
    args = ap.parse_args()
    if args.self_test:
        return self_test(args.firmware)
    if args.check is None and not args.addr:
        ap.error("give a firmware image and an address, or --self-test")
    if args.check is not None and args.addr:
        ap.error("--check takes the address from the committed table it is "
                 "diffing -- the hand-filled columns are per-address prose, so "
                 "an address given here could check one byte\'s table against "
                 "another byte\'s census. The plain run is where it goes")

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the annotations were written against", file=sys.stderr)
        return 1

    committed = []
    if args.check is not None:
        try:
            committed = read_committed(args.check)
            addrs = addresses_in(committed)
        except (OSError, ValueError) as e:
            print(f"note: {e}", file=sys.stderr)
            return 1
        if not addrs:
            print(f"note: {repo_path(args.check)} has no data row, so it names "
                  "no address to check", file=sys.stderr)
            return 1
    else:
        addrs = [int(args.addr, 16)]

    # `problems` is a list of strings, not a count: every one of them names
    # something a reader has to go and look at, and a bare "3 problem(s)" over
    # an address would be the least useful line in the output. `--check`'s diff
    # is the exception -- it has already printed itself.
    problems = []
    rc = 0
    for addr in addrs:
        summary, found = census(d, addr, pd_verified)
        problems += found
        report(addr, summary)
        text, cell_problems = csv_table(summary["rows"], committed)
        problems += cell_problems
        if args.check is not None:
            rc |= check_table(text, args.check)
        elif args.csv:
            sys.stdout.write(text)
        else:
            for row in summary["rows"]:
                cells = {c: row[c] for c in COLUMNS} | hand_for(committed, row["site_file_offset"])
                print("  " + "  ".join(f"{c}={cells[c]}" for c in CSV_COLUMNS))
    for problem in problems:
        print(f"census_xdata_writers.py: {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s) for "
              + ", ".join(f"0x{a:04X}" for a in addrs), file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
