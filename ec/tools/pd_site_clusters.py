#!/usr/bin/env python3
"""Assign each `0x07D0` / `0x07CC` `MOV DPTR` site in the ITE8850-PD image to
the committed Ghidra routine that contains it.

`../annotations/ec-0x07d0-sites.md` 6 names the limit of the 254-site
enumeration it commits: *"Whether some of those sites sit in the same
function is not determined -- that needs a recursive disassembly the repo has
deliberately not attempted."* The recursion was not attempted; the Ghidra `pd`
project was built instead, and `../decompiled/index.csv` now carries a
committed routine boundary for every function in it. So the question the
enumeration left open is answerable without a single byte of new firmware
analysis: read the committed boundaries, and ask which of them a site falls
inside. This tool does that and nothing else.

What it is: a join between two committed tables -- the 254 enumerated sites
and the committed `pd` routine set -- plus the same for the six `0x07CC`
sites, which have no enumeration of their own and get one here.

**A cluster is a statement about the committed routine set, never about the
firmware.** "43 of the 254 sites are inside a routine this project has
committed, across 19 of them" is what this reports, and the complement is
reported in the same words: the rest fall outside every boundary
`../decompiled/index.csv` records. That is not "these sites have no routine" --
Ghidra seeds a function from an annotation row, and a site no annotation has
named is in bytes the project has no function over. `pd_unannotated_census.py`
measures that residue and the decision this rests on is written down in
`../annotations/pd-index-geometry.md` 1. Read the two halves together; a
reader who sees only the first will over-read it, which is the failure this
tool's calibration rules exist to prevent.

**Nothing here re-derives the dump layout or the 8051 encoding.** The site
scan, the region map, the file-offset/runtime conversion and the access
classification are all `trace_xdata_refs.py`'s, called; the opcode tables are
`disasm8051.py`'s, imported. What is new is the containment test and the
report around it. That is the discipline `../annotations/pd-index-geometry.md`
1 states and `pd_index_geometry.py` follows, and it is why this tool is a new
file rather than another `--callers` mode on `pd_index_geometry.py`: a routine
boundary is not a term decode, and the two would have shared only the imports.

**Three ways this refuses rather than fits**, and each is a real shape in the
committed inputs rather than a hypothetical:

  * A cluster naming a routine that is not in `../decompiled/index.csv` is
    refused. A routine is the name of a committed range; a name that resolves
    to nothing is a typo, a renamed function, or a cluster invented by a
    reader -- and the third is the one that would otherwise survive a count.
  * A site two committed ranges both contain is **not** attributed to either.
    `../decompiled/index.csv` does carry overlapping `pd` ranges today (they
    are the Ghidra function tails a `0xB05` seed and a `0xBAB` seed both
    cover), and picking the later start would be a tie-break dressed as a
    fact. The site is reported as ambiguous and left out of every cluster, and
    the report names it. No site in either address's set is ambiguous today,
    so this changes no committed row -- `--self-test` pins the policy on a
    hand-built pair rather than on that accident.
  * A dump whose `0x20000` region is not the ITE8850-PD image is refused with
    the offset in the message, off `trace_xdata_refs.PD_MARKER`, rather than
    clustered: a containment test over the wrong program's bytes produces a
    tidy table about nothing.

**This is static analysis of committed firmware and nothing else.** No
register was read back, no write was attempted, nothing ran on the machine.
It says nothing about the EC's own `0x07D0` or `0x07CC`, which live in the
main image's XDATA map, reference zero sites by the scan this tool calls, and
are a different byte from either address here. `../annotations/registers.yaml`
keeps `DO-NOT-WRITE-BLIND` on the first, and this tool neither lifts nor
proposes lifting it.

Read-only: it opens the firmware image and `../decompiled/index.csv` for
reading, and writes nothing. `../annotations/pd-0x07d0-07cc-clusters.csv` is
its output, committed beside the write-up the way `ec-0x07d0-sites.csv` sits
beside its own, and `--check` is what holds the two together.

Usage:
    python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800 0x07CC
    python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800 --csv
    python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800 --check
    python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800 --notes
    python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import csv
import difflib
import io
import os
import sys

import trace_xdata_refs as T

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
ANNOT = os.path.join(HERE, os.pardir, "annotations")
DEFAULT_FIRMWARE = os.path.join("firmware", "GMxMGxx_11.800")

# Issue #25's two addresses. `0x07D0` is DBD1 (ECSpec's
# BATTERY_CHARGE_LIMIT_DOWN, the byte #1's live test wants to write blind) and
# `0x07CC` is USB_C_POWER_PRIORITY; both are `registers.yaml` entries whose
# `static_refs` are PD-image counts, which is what makes them this tool's
# population rather than the EC image's.
DEFAULT_ADDRS = ("0x07D0", "0x07CC")

# The committed routine set. index.csv is what the decompile export wrote, so
# it is the boundary set every other tool in this directory reads rather than
# the annotation CSV, which is an input to it.
INDEX_CSV = os.path.join(HERE, os.pardir, "decompiled", "index.csv")
PD_PROGRAM = "pd"

# Output table, committed beside ../annotations/pd-0x07d0-07cc-structure.md.
CLUSTERS_CSV = os.path.join(ANNOT, "pd-0x07d0-07cc-clusters.csv")

# The `0x07D0` enumeration. Not an input to the clustering -- the sites are
# re-derived from the image, so that this tool's population is its own -- but
# the set it derives is held against it, because a join whose left side has
# quietly stopped being the enumeration every other file quotes would still
# add up.
ENUMERATED_CSV = os.path.join(ANNOT, "ec-0x07d0-sites.csv")

# The cell a site gets when no committed routine contains it, and the one two
# committed routines both contain. Neither is a function name, and both are
# refused by validate_table() rather than looked up.
NO_CLUSTER = "-"
COLUMNS = ["addr", "file_offset", "region", "runtime", "function",
           "function_addr", "function_size", "access"]


def repo_path(path: str) -> str:
    return os.path.relpath(os.path.abspath(path), REPO).replace(os.pardir, "/")


class NotPdImage(Exception):
    """The 0x20000 region is not the image this tool clusters."""


def require_pd(d: bytes) -> bytes:
    """Refuse a dump whose 0x20000 region is not the ITE8850-PD image.

    A containment test over the wrong program's bytes produces a tidy table
    about nothing, and the marker is the only thing in the file that says
    which program it is, so it is checked rather than assumed. Takes the
    image rather than a path so the refusal is exercisable on doctored bytes
    without a committed fixture that a byte in a firmware image cannot
    describe.
    """
    off, magic = T.PD_MARKER
    if d[off:off + len(magic)] != magic:
        raise NotPdImage(
            f"no {magic.decode()!r} marker at file 0x{off:05X} -- "
            "0x20000-0x2FFFF is not the image this tool clusters")
    return d


def load_image(fw_path: str) -> bytes:
    with open(fw_path, "rb") as f:
        return require_pd(f.read())


def routines(index_csv: str = INDEX_CSV, program: str = PD_PROGRAM):
    """The committed routine set as `(start, size, name, type)`, start-ordered.

    Only the four columns the containment test needs, so that a re-export
    which adds a column cannot change the clustering. A row with no name or a
    size that is not a positive integer is skipped rather than folded in: a
    nameless range is not a routine to name a cluster after, and a zero-length
    one contains nothing, so neither can make a site's attribution wrong.
    """
    out = []
    with open(index_csv, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("program") != program:
                continue
            name = (r.get("name") or "").strip()
            if not name:
                continue
            try:
                start, size = int(r["addr"], 16), int(r["size"])
            except (KeyError, TypeError, ValueError):
                continue
            if size <= 0:
                continue
            out.append((start, size, name, (r.get("type") or "").strip()))
    out.sort()
    return out


def containing(rs, runtime: int):
    """Every committed routine whose `[start, start+size)` covers `runtime`."""
    return [r for r in rs if r[0] <= runtime < r[0] + r[1]]


def sites(d: bytes, addr: int):
    """`(file_offset, runtime, region, access)` for one address, offset-ordered.

    The scan and the region map are trace_xdata_refs.py's, and the access
    classification is its `classify()` over its own `walk_why()` window -- so
    this tool holds the same eight-instruction, five-terminator window the
    enumeration that motivated it did, and a `0x07CC` row means here what a
    `0x07D0` row means in `ec-0x07d0-sites.csv`.

    `region_of()` and `runtime_addr()` both take the `pd_verified` flag
    `trace_xdata_refs` threads through its own CLI, and it is passed `True`
    here without being a parameter: `require_pd()` has already refused any
    image without the marker, so the "unknown" region that flag produces is
    unreachable by the time a site is looked up. Re-deriving it would be a
    second gate on the same fact.
    """
    rows = []
    for off in T.sites_for(d, addr):
        region = T.region_of(off, True)[0]
        runtime = T.runtime_addr(off, True)
        if runtime is None:
            continue
        insns, _why = T.walk_why(d, off)
        rows.append((off, runtime, region, T.classify(insns)))
    return sorted(rows)


def cluster_rows(d: bytes, addrs, rs):
    """One row per site per address, cluster column filled or `NO_CLUSTER`.

    Also returns the ambiguous sites, which get no row of their own kind --
    they carry `NO_CLUSTER` like any other unclustered site and are reported
    separately by --notes, because "outside every committed routine" and
    "inside two of them" are different statements and the CSV has one column
    for the first.
    """
    rows, ambiguous = [], []
    for text in addrs:
        addr = int(text, 16)
        for off, runtime, region, access in sites(d, addr):
            hits = containing(rs, runtime)
            if len(hits) == 1:
                start, size, name, _type = hits[0]
                rows.append([f"0x{addr:04X}", f"0x{off:05X}", region,
                             f"0x{runtime:04X}", name, f"0x{start:04X}",
                             str(size), access])
            else:
                rows.append([f"0x{addr:04X}", f"0x{off:05X}", region,
                             f"0x{runtime:04X}", NO_CLUSTER, NO_CLUSTER,
                             NO_CLUSTER, access])
                if hits:
                    ambiguous.append((addr, runtime,
                                      ", ".join(h[2] for h in hits)))
    return rows, ambiguous


def table(rows) -> str:
    """The CSV text, as a string rather than a write to stdout, so `--check`
    diffs the same bytes this prints. Committed tables in this directory carry
    the csv module's own CRLF terminator; `validate_table()` reads with
    `newline=""` for the same reason, so a red --check names a real difference.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    w.writerows(rows)
    return buf.getvalue()


def validate_table(rows, rs, found):
    """Problems with a cluster table, as a list of strings; empty is the pass.

    `rs` is the committed routine set and `found` the per-address set of
    runtimes the image itself yields, keyed `0x07D0` / `0x07CC`. The checks
    are the ones that let a table keep adding up while meaning nothing:

      * a `function` cell naming a routine the project has not committed,
        which is a cluster no reader can check against `decompiled/index.csv`;
      * a runtime the image yields and the table does not hold, and one the
        table holds and the image does not yield -- the two halves of a
        dropped site, and only the second is visible in a diff of two runs
        that both dropped the same row;
      * a per-address site count that does not equal the count the image
        yields, which is what a cluster silently split into two, or a row
        duplicated, looks like when the set check passes;
      * a runtime attributed to a routine that does not contain it, which a
        hand-edited cell produces and neither of the two above notices.
    """
    bad = []
    by_addr = collections.defaultdict(list)
    for r in rows:
        by_addr[r[0]].append(r)
    known = {name: (start, size) for start, size, name, _t in rs}
    for addr in sorted(set(by_addr) | set(found)):
        have = by_addr.get(addr, [])
        want = found.get(addr, set())
        if len(have) != len(want):
            bad.append(f"{addr}: table holds {len(have)} site(s), the image "
                       f"yields {len(want)}")
        seen = set()
        for r in have:
            runtime = int(r[3], 16)
            if runtime in seen:
                bad.append(f"{addr}: runtime 0x{runtime:04X} is listed twice")
            seen.add(runtime)
            if runtime not in want:
                bad.append(f"{addr}: 0x{runtime:04X} is in the table and not "
                           "in the image")
            name = r[4]
            if name == NO_CLUSTER:
                continue
            if name not in known:
                bad.append(f"{addr}: 0x{runtime:04X} is attributed to "
                           f"{name!r}, which is not a routine "
                           f"{repo_path(INDEX_CSV)} commits")
                continue
            start, size = known[name]
            if not start <= runtime < start + size:
                bad.append(f"{addr}: 0x{runtime:04X} is attributed to "
                           f"{name!r} (0x{start:04X}-0x{start + size - 1:04X}), "
                           "which does not contain it")
        for runtime in sorted(want - seen):
            bad.append(f"{addr}: 0x{runtime:04X} is in the image and not in "
                       "the table")
    return bad


def read_table(path: str):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError(f"{repo_path(path)} is empty")
    if rows[0] != COLUMNS:
        raise ValueError(f"{repo_path(path)} header is {rows[0]}, expected {COLUMNS}")
    return rows[1:]


def enumerated_set(path: str = ENUMERATED_CSV, addr: str = "0x07D0"):
    """The runtimes `ec-0x07d0-sites.csv` enumerates, as a set.

    Set equality rather than a count, and against the committed file rather
    than a literal: the point is that this tool's left side of the join is the
    enumeration `registers.yaml` and `docs/findings.md` 3b cite, and both a
    site added and a site lost have to move the assertion.
    """
    with open(path, newline="") as f:
        return {r["runtime"] for r in csv.DictReader(f) if r["addr"] == addr}


def access_class(access: str) -> str:
    """The three buckets `ec-0x07d0-sites.md` 3 reports, over classify()'s
    vocabulary rather than a new one: a site that reads, a site that writes,
    and a site this method does not resolve -- which is a DPTR handed to a
    callee, or a window with no `movx` in it. A read-modify-write is counted
    under read, as it is there.
    """
    if "read" in access:
        return "read"
    if "write" in access:
        return "write"
    return "unresolved"


def report(rows, addrs, ambiguous) -> str:
    out = []
    for addr in addrs:
        mine = [r for r in rows if r[0] == addr]
        clusters = collections.OrderedDict()
        for r in mine:
            if r[4] != NO_CLUSTER:
                clusters.setdefault((r[5], r[4], r[6]), []).append(r)
        inside = sum(len(v) for v in clusters.values())
        out.append(f"{addr}  {len(mine)} MOV DPTR site(s) in the "
                   f"ITE8850-PD image")
        out.append(f"  {inside} inside a routine {repo_path(INDEX_CSV)} "
                   f"commits, across {len(clusters)} of them")
        out.append(f"  {len(mine) - inside} outside every committed routine "
                   "boundary -- a statement about this project's routine set, "
                   "not about the firmware")
        tally = collections.Counter(access_class(r[7]) for r in mine)
        out.append("  sites by access: " + ", ".join(
            f"{tally[k]} {k}" for k in ("read", "write", "unresolved") if tally[k]))
        if not clusters:
            out.append("")
            continue
        out.append("")
        out.append(f"  {'sites':>5}  {'at':<8} {'size':>4}  routine")
        for (at, name, size), members in sorted(
                clusters.items(), key=lambda kv: (-len(kv[1]), kv[0][0])):
            t = collections.Counter(access_class(r[7]) for r in members)
            out.append(f"  {len(members):>5}  {at:<8} {size:>4}  {name}   "
                       + ", ".join(f"{t[k]} {k}" for k in
                                   ("read", "write", "unresolved") if t[k]))
            if len(members) > 1:
                out.append(f"          {_fmt_runtimes(members)}")
        out.append("")
    if ambiguous:
        out.append("  ambiguous -- inside two committed routines, attributed "
                   "to neither:")
        for addr, runtime, names in ambiguous:
            out.append(f"    {addr} 0x{runtime:04X}  {names}")
        out.append("")
    return "\n".join(out)


def _fmt_runtimes(members, limit: int = 13) -> str:
    rts = [r[3] for r in members]
    if len(rts) <= limit:
        return " ".join(rts)
    return " ".join(rts[:limit]) + f" ... +{len(rts) - limit} more"


def check_table(generated: str, path: str) -> int:
    """Exit code for `--check`: 0 when this run reproduces `path` exactly."""
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
    print(f"note: {repo_path(path)} differs from what this run produced; the "
          "file is the product of the command on the page that names it, so "
          "regenerate rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(), generated.splitlines(),
                                     "committed", "generated", lineterm="", n=0):
        print(line, file=sys.stderr)
    return 1


# ---------------------------------------------------------------- self-test

def found_sets(rows):
    """`{'0x07D0': {runtime, ...}}` -- what the image yields, for validate_table.

    Runtimes rather than file offsets because the containment test is in
    runtime addresses and index.csv is a runtime table; the file offset is
    `runtime + 0x20000` for every row here and re-deriving that here would be
    a second copy of `trace_xdata_refs.REGIONS` to keep in step.
    """
    out = collections.defaultdict(set)
    for r in rows:
        out[r[0]].add(int(r[3], 16))
    return out


def self_test(fw_path: str) -> int:
    d = load_image(fw_path)
    rs = routines()
    addrs = list(DEFAULT_ADDRS)
    rows, ambiguous = cluster_rows(d, addrs, rs)
    found = found_sets(rows)
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else '!  '} {text}")

    # The left side of the join is the enumeration every other file quotes.
    # A set, not a count: a site added to either side has to move this.
    derived = {r[3] for r in rows if r[0] == "0x07D0"}
    check(derived == enumerated_set(),
          f"the {len(derived)} runtimes this tool derives for 0x07D0 are the "
          f"ones {repo_path(ENUMERATED_CSV)} enumerates "
          f"({len(derived - enumerated_set())} extra, "
          f"{len(enumerated_set() - derived)} missing)")

    # Every site's region is the PD image, on both addresses. A site in the
    # main EC would be a different program's byte and this tool's whole
    # subject would be wrong; region_of() is trace_xdata_refs.py's call, so
    # this holds the two together rather than re-deriving the map.
    check(all(r[2] == "pd-image" for r in rows),
          "every site of both addresses is in the pd-image region")

    # The table this run builds is a valid table, which is the property the
    # refusals below are shown to break.
    check(not validate_table(rows, rs, found),
          "the table this run derives passes validate_table()")

    # Refusal 1: a cluster naming a routine the project has not committed.
    # One cell, one difference from the real row.
    forged = [list(r) for r in rows]
    victim = next((r for r in forged if r[4] != NO_CLUSTER), None)
    check(victim is not None, "the derived table has a clustered row to forge")
    if victim is not None:
        victim[4] = "state_machine_of_the_07d0_byte"
        problems = validate_table(forged, rs, found)
        check(any("not a routine" in p for p in problems),
              "a cluster naming a routine index.csv does not commit is refused")

    # Refusal 2: a site attributed to a committed routine that does not
    # contain it. The name is real and the site is real, so every count in
    # the table still adds up and only the containment check sees it.
    moved = [list(r) for r in rows]
    clustered = [r for r in moved if r[4] != NO_CLUSTER]
    if len({r[4] for r in clustered}) > 1:
        clustered[0][4] = next(r[4] for r in clustered if r[4] != clustered[0][4])
        problems = validate_table(moved, rs, found)
        check(any("does not contain it" in p for p in problems),
              "a site attributed to a committed routine that does not contain "
              "it is refused")
    else:
        check(False, "a site attributed to a routine that does not contain it "
                     "is refused (fewer than two clusters to move between)")

    # Refusal 3: a dropped site, in both directions. Removing a row is what a
    # merge conflict does. Swapping one row for a fabricated one keeps the
    # row count identical, which is the case the count check cannot see and
    # the membership check exists for.
    dropped = [list(r) for r in rows][1:]
    problems = validate_table(dropped, rs, found)
    check(any("in the image and not in the table" in p for p in problems)
          and any("table holds" in p for p in problems),
          "a site missing from the table is reported, by count and by runtime")
    swapped = [list(r) for r in rows][1:]
    planted = list(rows[0])
    planted[1], planted[3], planted[4:7] = "0x2FFF0", "0xFFF0", [NO_CLUSTER] * 3
    swapped.append(planted)
    problems = validate_table(swapped, rs, found)
    check(not any("table holds" in p for p in problems)
          and any("in the table and not in the image" in p for p in problems)
          and any("in the image and not in the table" in p for p in problems),
          "a planted row the image does not yield is reported, and so is the "
          "real row it displaced, although the row count is unchanged")

    # The ambiguity policy, on a hand-built pair rather than on the committed
    # set, because no site of either address is ambiguous today and an
    # accident is not a test. Two ranges that overlap, one site in both.
    fake = [(0x1000, 0x40, "outer_range", "logic"),
            (0x1010, 0x10, "inner_range", "gate")]
    check(len(containing(fake, 0x1014)) == 2,
          "two overlapping committed ranges both contain 0x1014")
    check(containing(fake, 0x1030) == [fake[0]],
          "a site only the outer range contains attributes to it")
    check(containing(fake, 0x1000) == [fake[0]]
          and containing(fake, 0x1040) == []
          and containing(fake, 0x100F) == [fake[0]]
          and containing(fake, 0x1020) == [fake[0]],
          "each boundary is exclusive: a range covers its first byte and "
          "stops before the one past its last (0x1000-0x103F)")

    # The refusal is exercised on the real path too: a site that falls in two
    # committed ranges gets NO_CLUSTER and an ambiguity entry, not a pick.
    check(not ambiguous,
          f"no site of either address falls in two committed ranges "
          f"({len(ambiguous)} do)")

    # The header the CSV is written with, so a column added here and not there
    # is a red --check rather than a silently wider table.
    check(table(rows).splitlines()[0] == ",".join(COLUMNS),
          f"the table's header is {','.join(COLUMNS)}")

    # The import this tool's calibration rests on: without the PD marker the
    # image is refused, and a containment test over the wrong program's bytes
    # produces a tidy table about nothing. Built in memory rather than
    # committed as a fixture, since the claim is about the marker's absence
    # and a committed binary would be a second copy of the firmware to keep
    # in step with the first.
    off, magic = T.PD_MARKER
    wrong = bytearray(d)
    wrong[off:off + len(magic)] = b"\x00" * len(magic)
    try:
        require_pd(bytes(wrong))
        check(False, "a dump whose 0x20000 region is not the PD image is refused")
    except NotPdImage as exc:
        check(f"0x{off:05X}" in str(exc) and "not the image this tool clusters" in str(exc),
              f"a dump whose 0x20000 region is not the PD image is refused: {exc}")

    if bad:
        print(f"self-test FAILED: {bad} check(s)")
        return 1
    print("self-test passed: the derived site set is the committed "
          "enumeration, and each of the three refusals fires")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=None,
                    help=f"raw EC firmware image (default {DEFAULT_FIRMWARE})")
    ap.add_argument("addrs", nargs="*", metavar="ADDR",
                    help=f"XDATA addresses to cluster; default {' '.join(DEFAULT_ADDRS)}")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site cluster table as CSV on stdout")
    ap.add_argument("--check", nargs="?", const=CLUSTERS_CSV, metavar="CSV",
                    help="validate a cluster table and confirm this run "
                         f"reproduces it byte for byte; default {repo_path(CLUSTERS_CSV)}")
    ap.add_argument("--notes", action="store_true",
                    help="also name every site that is ambiguous or unclustered")
    ap.add_argument("--self-test", action="store_true",
                    help="known answers, including the three refusals")
    args = ap.parse_args()

    fw = args.firmware or os.path.join(HERE, DEFAULT_FIRMWARE)
    if args.self_test:
        return self_test(fw)

    addrs = args.addrs or list(DEFAULT_ADDRS)
    try:
        # Re-spelled the way cluster_rows() spells its own `addr` cell, so the
        # report groups rows by the string it also writes to the CSV. A report
        # that groups on a different spelling of the same address prints zeros
        # beside a full table, which is the worst way for this to be wrong.
        addrs = [f"0x{int(a, 16):04X}" for a in addrs]
    except ValueError as exc:
        ap.error(f"address is not hexadecimal: {exc}")
    if any(not 0 <= int(a, 16) <= 0xFFFF for a in addrs):
        ap.error("XDATA address outside 0x0000-0xFFFF")

    try:
        d = load_image(fw)
    except (OSError, NotPdImage) as exc:
        # stderr, so a --csv redirect stays a clean CSV.
        print(f"note: {exc}", file=sys.stderr)
        return 1

    rs = routines()
    rows, ambiguous = cluster_rows(d, addrs, rs)
    found = found_sets(rows)

    if args.check:
        rc = 0
        for line in validate_table(read_table(args.check), rs, found):
            print(f"note: {args.check}: {line}", file=sys.stderr)
            rc = 1
        return check_table(table(rows), args.check) or rc

    if args.csv:
        print(table(rows), end="")
        return 0
    print(report(rows, addrs, ambiguous))
    if args.notes:
        for r in rows:
            if r[4] == NO_CLUSTER:
                print(f"  {r[0]}  {r[3]}  outside every committed routine "
                      f"boundary  ({r[7]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
