#!/usr/bin/env python3
"""Census the bucket-C sites that fall outside every span
`ec/annotations/data-regions.yaml` lists, so the population where a real call
and a table entry look identical stops being one undifferentiated remainder.

**What this is and is not.** `bucket_c_codemap.py` classified all 140 bucket-C
sites against a recovered code map of the common area and labelled 35 of them
inside a listed data region. This tool takes the rows that map **declined** --
`data_regions.region_at()` returns `None` for each -- and asks each one the
questions that population has never been asked, with the evidence beside the
answer. It is a census over an existing classification, not a second walk:
`bucket_c_codemap.build()` and `audit_call_targets.survey()` are *run*, never
reimplemented, for the reason `bucket_c_codemap.bucket_c_rows()` gives for its
own census read.

**This does not settle bucket C, and settles no site.** Every verdict is a
reading of bytes by one method, and the fourth value -- `unresolved` -- is the
one a coverage hole earns. `0x021C6` is *not* decided here: it is recorded with
what each method said about it and nothing more. A `code` verdict is not a
behavioural observation, and no register is read, no capture opened, and no
`status:` in `registers.yaml` moves.

**Two questions are kept apart, on purpose.** `verdict` answers "is the byte
inside something a method read as code", and `on_instruction_boundary` answers
"does it *start* an instruction". Those are different questions and folding them
together is how a site gets reported as a call it is not: a `0x12` byte that is
the *operand* of a `mov dptr,#imm16` is covered by a decoded span and starts
nothing. `0x055DC` is the precedent that separates them -- reached, covered, and
genuinely a table entry on the same evidence -- which is why the boolean is a
column rather than a detail of the reason string.

**`grid_state` is ungated; the verdict is not.** Whether a byte sits on some
listed table's stride grid is a measurement, so it is recorded as one for every
row. Whether that makes it a *table entry* is a much stronger claim, and it is
gated on adjacency: the nearest listed region is hundreds of bytes from most
rows here, so an ungated "on its grid" would call a row a table entry on the
strength of one byte matching a shape at some distance. Reporting the grid
answer and the distance side by side lets a reader weigh the two, and lets the
report state the base rate -- what share of this population is on *any* nearby
grid -- which is what decides whether `0x021C6`'s alignment is interesting or
arithmetic.

**The population is derived, never written down.** It is the bucket-C rows
`data_regions.region_at()` declines, and `--check` holds
`unplaced + labelled == the bucket-C count the image's own scan produces`, so
listing a new region moves this table rather than leaving a hand-kept figure
stale in three prose files. Those prose files are deliberately not edited: no
region is added here, so the number is not moving, and
`test_bucket_c_unplaced.py` holds the derived count against each of them
instead.

**A zero in any column is "not found by this method", never "absent."** The
subject of this file is one method's blind spots, so `docs/findings.md` §4c
binds on it harder than anywhere else in the tree. `table-entry` has no members
on the committed image, and that is reported as a result rather than read as
"there are none".

Usage:
    python3 bucket_c_unplaced.py ../firmware/GMxMGxx_11.800
    python3 bucket_c_unplaced.py ../firmware/GMxMGxx_11.800 --check
    python3 bucket_c_unplaced.py ../firmware/GMxMGxx_11.800 --self-test
    python3 bucket_c_unplaced.py ../firmware/GMxMGxx_11.800 --csv
    python3 bucket_c_unplaced.py ../firmware/GMxMGxx_11.800 --for-offset 0x021C6
"""
import argparse
import bisect
import collections
import csv
import difflib
import io
import os
import sys

import bucket_c_codemap
from bucket_c_codemap import (NOT_A_FUNCTION, containing_function,
                               verdict_for as walk_verdict_for)
from data_regions import entry_value, region_at
from disasm8051 import OPCODE_LEN
from trace_xdata_refs import PD_MARKER

DEFAULT_FIRMWARE = "../firmware/GMxMGxx_11.800"
DEFAULT_CSV = "../annotations/bucket-c-unplaced.csv"
DEFAULT_ANNOTATIONS = "../annotations/ghidra-functions.csv"
DEFAULT_INDEX = "../decompiled/index.csv"

# The four verdicts, ordered, first match wins. Closed because a verdict is a
# count of something, and a fifth value would make the count mean nothing --
# `bucket_c_codemap.verdict_for()` refuses one for the same reason, and
# `data_regions.py` refuses a shape outside its vocabulary rather than guessing
# a decoder.
TRAMPOLINE = "trampoline"
TABLE_ENTRY = "table-entry"
CODE = "code"
UNRESOLVED = "unresolved"
VERDICTS = (TRAMPOLINE, TABLE_ENTRY, CODE, UNRESOLVED)

# The closed per-verdict reason sets. Every row must carry one of these, and
# `check_verdict()` refuses a reason that is not in its verdict's set: a reason
# column that can hold an unbounded number of shapes is a column nobody can
# grep, and the four verdicts mean different things so the reasons cannot be
# pooled either.
#
# `unresolved` is the one that borrows rather than restates. Its reasons are
# `bucket_c_codemap.WALK_REASONS`, the walk's own closed vocabulary, because
# "not decided by this method, and here is the terminator that stopped it" is
# exactly what that vocabulary already means; reusing it keeps the two files
# from being able to disagree about why a site is unresolved.
TRAMPOLINE_REASONS = frozenset({"target-named-by-a-trampoline"})
TABLE_ENTRY_REASONS = frozenset({"shape-decodes-on-the-nearest-regions-grid"})
CODE_REASONS = frozenset({
    "on-an-instruction-boundary-this-walk-decoded",
    "mid-instruction-in-a-span-this-walk-decoded",
    "inside-a-ghidra-common-function",
})
VERDICT_REASONS = {
    TRAMPOLINE: TRAMPOLINE_REASONS,
    TABLE_ENTRY: TABLE_ENTRY_REASONS,
    CODE: CODE_REASONS,
    UNRESOLVED: bucket_c_codemap.WALK_REASONS,
}

# `grid_state` is what the *measurement* says, ungated, and is closed for the
# same reason the verdicts are. `stride not declared` is the cell for a region
# whose stride is null -- `data_regions.check()` reports that as a span it
# cannot re-derive, and no entry carries it today. It is here rather than a
# crash so that a region list `data_regions.py` can read is a region list this
# tool can census: annotating the row beats refusing the run.
GRID_HOLDS = "on-grid shape-holds"
GRID_FAILS = "on-grid shape-fails"
GRID_OFF = "off-grid"
GRID_NO_STRIDE = "stride not declared"
GRID_STATES = (GRID_HOLDS, GRID_FAILS, GRID_OFF, GRID_NO_STRIDE)

# Six preceding bytes: the width `audit_call_targets.py`'s section 4 table
# prints for its ten best-framed sites. The issue this answers names that gap
# directly -- those ten got six bytes of context and the rest got none -- so the
# width is that one's rather than a number chosen here.
PREV_BYTES = 6

NOT_NAMED = "no"
YES = "yes"
NO = "no"

# Columns 1-6 are `bank-call-targets.csv`'s own, in its own spelling, so a row
# keyed on `file_offset` joins across the three files. `bucket` and
# `in_data_region` are carried *nowhere*, and that is not an omission: every row
# here is bucket C and outside every listed region by construction, so both
# would be columns that cannot disagree with themselves -- the reason `region`
# is not carried into `bucket-c-codemap.csv` either.
CSV_HEAD = [
    "file_offset", "runtime", "opcode", "target", "frame_onto", "frame_over",
    "prev_bytes", "nearest_region", "bytes_to_nearest_region", "grid_state",
    "bytes_below_frontier", "walk_verdict", "walk_reason", "containing_function",
    "in_ghidra_function", "on_instruction_boundary", "target_is_trampoline_entry",
    "target_named_in", "verdict", "verdict_reason",
]


# --- the population --------------------------------------------------------

class Site:
    """One unplaced site's answers, kept together so they cannot disagree.

    Built once per site and read by the row writer, the report and the suite.
    Deriving each column where it is used instead is how a report ends up
    printing a frontier distance the CSV does not carry.
    """

    def __init__(self, census, row):
        d = census.d
        off = row["file_offset"]
        self.row = row
        self.off = off
        self.region, self.region_distance = nearest_region(census.regions, off)
        self.grid = grid_state(d, self.region, off)
        self.walk_reason, entry = census.codemap.reason_for(off)
        self.walk_verdict = walk_verdict_for(self.walk_reason)
        self.entry = entry
        self.on_boundary = off in census.reached
        self.in_walk_span = off in census.covered
        self.ghidra = containing_function(census.functions, off)
        self.in_ghidra = self.ghidra != NOT_A_FUNCTION
        self.frontier = bytes_below_frontier(census.sorted_pcs, off)
        self.is_trampoline_target = row["target"] in census.trampoline_targets
        self.verdict, self.verdict_reason = verdict_for(self)
        check_verdict(self.verdict, self.verdict_reason)


class Census:
    """Everything one run reads, built once.

    `bucket_c_codemap.build()` is the expensive half and it is *called*, not
    redone: the walk is a function of that module's seed set, and a second
    enumeration here would be a second answer to its question.
    """

    def __init__(self, d: bytes, annotations_path=None, index_path=None):
        (self.rows, self.seeds, self.reached, self.descents, self.codemap,
         self.known, self.functions, self.regions) = bucket_c_codemap.build(d)
        self.d = d
        _, _, tramp = bucket_c_codemap.survey(d)
        self.trampoline_targets = {t for _, t in tramp.values()}
        # `covered` is every byte the walk decoded *into*, operand bytes
        # included. It is what separates "inside something read as code" from
        # "starts an instruction", so it is built from the block spans rather
        # than from `reached`, which holds instruction starts only.
        self.covered = self._covered_bytes()
        self.sorted_pcs = sorted(self.reached)
        self.annotations = annotation_names(annotations_path)
        self.index = index_names(index_path)

    def _covered_bytes(self) -> set:
        out = set(self.reached)
        for rec in self.descents.values():
            for _, pcs, _ in rec.blocks:
                for pc in pcs:
                    for step in range(OPCODE_LEN[self.d[pc]]):
                        out.add(pc + step)
        return out

    def unplaced(self):
        """The bucket-C rows `data_regions.region_at()` declines, in order."""
        return [r for r in self.rows
                if region_at(self.regions, r["file_offset"]) is None]

    def labelled(self):
        """The bucket-C rows a listed region *contains*. Never dropped.

        `data_regions.py` refuses filtering rather than suppressing a labelled
        site, and this is the same rule read from the other side: the invariant
        that the two populations partition bucket C is only meaningful while
        both halves are counted.
        """
        return [r for r in self.rows
                if region_at(self.regions, r["file_offset"]) is not None]

    def sites(self):
        return [Site(self, r) for r in self.unplaced()]


# --- the naming sources ----------------------------------------------------

def annotation_names(path: str = None):
    """{address: sorted[(name, scope)]} from `annotations/ghidra-functions.csv`.

    Read from the annotations CSV rather than from `ec/decompiled/index.csv`
    because CLAUDE.md names that CSV the editable surface and the index is
    generated from it. Reading the generated file instead would make a name that
    appeared only in a `call-target` or `auto` seed row indistinguishable from
    one a person wrote down, which is the difference between "annotated" and
    "discovered"; the index is read separately, and its extra names reported as
    unannotated rather than folded in.
    """
    return _names_by_address(path or _default_path(DEFAULT_ANNOTATIONS), "scope")


def index_names(path: str = None):
    """{address: sorted[(name, program)]} from `ec/decompiled/index.csv`."""
    return _names_by_address(path or _default_path(DEFAULT_INDEX), "program")


def _default_path(relative):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)


def _names_by_address(path: str, scope_col: str):
    out = collections.defaultdict(list)
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                addr = int(row["addr"], 16)
            except (KeyError, TypeError, ValueError):
                continue
            out[addr].append(((row.get("name") or "").strip(),
                              (row.get(scope_col) or "").strip()))
    return {a: sorted(v) for a, v in out.items()}


def names_for(names, target: int) -> str:
    """The names one source carries for `target`, or `no`.

    Scope-qualified, because the same address is a different routine in each
    bank and a bare name would hide the disagreement that makes bucket C
    unresolvable in the first place.
    """
    pairs = names.get(target) or []
    return " | ".join(f"{scope}:{name}" for name, scope in pairs) or NOT_NAMED


# --- the per-site questions ------------------------------------------------

def nearest_region(regions, off: int):
    """(region, distance) for the listed region closest to `off`, or None.

    Distance is measured **from the span's half-open edge**: 0 for a site inside
    `[file_lo, file_hi)`, `file_lo - off` before it, and `off - file_hi` after
    it. The last of those is the number `ec-data-regions.md` §4 states for
    `0x021C6` -- "0x12 past the region's `file_hi` of `0x21B4`" -- so measuring
    from the last entry byte instead would put this column one away from the
    committed sentence it exists to support, and §4 says 0x13 for *that*
    measurement in the same breath.

    A site at exactly `file_hi` therefore reads 0, the same as one inside: the
    span is half-open, so `file_hi` is where the next entry of a table that ran
    on would start, and `data_regions.check()` tests the shape at that very
    offset when it decides whether a span is declared short.

    Ties break on the region name. The region order in the YAML is stable today,
    and relying on that would make the table stable for a reason nobody wrote
    down.
    """
    best = None
    for reg in regions:
        if reg["file_lo"] <= off < reg["file_hi"]:
            dist = 0
        elif off < reg["file_lo"]:
            dist = reg["file_lo"] - off
        else:
            dist = off - reg["file_hi"]
        if best is None or (dist, reg["name"]) < (best[0], best[1]["name"]):
            best = (dist, reg)
    return (None, None) if best is None else (best[1], best[0])


def grid_state(d: bytes, region, off: int) -> str:
    """Whether `off` is on `region`'s stride grid, and whether its shape decodes.

    Ungated on purpose: this is the measurement, and whether it makes the site a
    table *entry* is the verdict, gated separately in `verdict_for()`. The decode
    is `data_regions.entry_value()` against the region's own declared `file_lo`,
    so a null stride is answered rather than crashing -- `check()` cannot
    re-derive such a region and says so, and this census is not the place to
    refuse a region list `data_regions.py` will read.
    """
    if region is None or not region["stride"]:
        return GRID_NO_STRIDE
    stride = region["stride"]
    if (off - region["file_lo"]) % stride:
        return GRID_OFF
    if entry_value(d, region["file_lo"], off, stride, region["shape"]) is None:
        return GRID_FAILS
    return GRID_HOLDS


def bytes_below_frontier(sorted_pcs, off: int):
    """Bytes between `off` and the nearest decoded instruction start below it.

    The gap `docs/findings/bucket-c-codemap.md` §Limits declines to carry,
    materialised as a column. Measured to the nearest instruction *start* at or
    below the site rather than to the nearest decoded byte, because that is the
    definition `bucket-c-codemap.md`'s own figure for `0x021C6` was taken
    under, and a column that disagrees with a committed sentence by two is a
    column a reader cannot reconcile.

    `None` when the site sits below every instruction this walk decoded, which
    is a fact about the seed set rather than a distance and is rendered as such
    rather than as a number.
    """
    i = bisect.bisect_right(sorted_pcs, off)
    return None if i == 0 else off - sorted_pcs[i - 1]


def prev_bytes_of(d: bytes, off: int, count: int = PREV_BYTES) -> str:
    """`count` bytes immediately below `off`, as one space-separated hex string."""
    return " ".join(f"{b:02x}" for b in d[max(0, off - count):off])


def verdict_for(site) -> tuple:
    """(verdict, reason) for one `Site`. Ordered, first match wins.

    1. `trampoline` -- the **target** is an address a BL51 trampoline names, so
       the linker itself recorded it as a real banked entry point. A claim about
       the target, not the site: a bucket-C site is a `0x12`/`0x02` byte and
       cannot itself be a trampoline.
    2. `table-entry` -- on the nearest region's grid, that region's shape
       decodes under the site, **and** the region is within one stride of it.
       The adjacency gate is load-bearing. Without it "this byte matches that
       region's shape" is a statement about one byte at an arbitrary distance,
       and a row hundreds of bytes past a table's end would be reported as being
       in it. The gate is what makes the verdict a claim about *this table*
       rather than about `shape`.
    3. `code` -- covered by a span this walk decoded, or inside a `common`
       function `ec/decompiled/index.csv` records. The reason says which, and
       the two walk reasons are kept apart because "starts an instruction" is
       the question `on_instruction_boundary` answers *beside* this one.
    4. `unresolved` -- everything else, carrying the walk's own reason for
       having stopped. A coverage hole is not a table and not a call, so
       `docs/findings.md` §4c binds hardest here.
    """
    if site.is_trampoline_target:
        return TRAMPOLINE, "target-named-by-a-trampoline"
    if site.grid == GRID_HOLDS and _adjacent(site):
        return TABLE_ENTRY, "shape-decodes-on-the-nearest-regions-grid"
    if site.in_walk_span:
        return CODE, ("on-an-instruction-boundary-this-walk-decoded"
                      if site.on_boundary
                      else "mid-instruction-in-a-span-this-walk-decoded")
    if site.in_ghidra:
        return CODE, "inside-a-ghidra-common-function"
    return UNRESOLVED, site.walk_reason


def _adjacent(site) -> bool:
    """Is the nearest listed region within one stride of the site?

    One stride rather than some distance of its own: the span's own entry width
    is the unit the region is measured in, so this introduces no constant that a
    later edit would have to re-argue.
    """
    if site.region is None or not site.region["stride"]:
        return False
    return site.region_distance <= site.region["stride"]


def check_verdict(verdict: str, reason: str) -> None:
    """Refuse a verdict/reason pair outside the closed vocabulary.

    Three separate refusals because they are three separate mistakes: a verdict
    outside the tuple, a reason outside its verdict's set, and an empty reason.
    The third is the one a hand-edited table gets wrong -- a row whose
    `verdict_reason` cell is blank still looks like a row, and a reader cannot
    tell it from a site this method declined for no stated reason at all.
    """
    if verdict not in VERDICTS:
        raise SystemExit(
            f"error: verdict {verdict!r} is not one of {', '.join(VERDICTS)}; a "
            "verdict is a count of four and a fifth makes the count mean "
            "nothing")
    if not str(reason).strip():
        raise SystemExit(
            f"error: {verdict} carries an empty reason. A row with no stated "
            "reason cannot be told apart from a site this method declined for "
            "no reason at all.")
    if reason not in VERDICT_REASONS[verdict]:
        raise SystemExit(
            f"error: reason {reason!r} is not a {verdict} reason; that verdict's "
            f"reasons are {', '.join(sorted(VERDICT_REASONS[verdict]))}")


# --- the table -------------------------------------------------------------

def row_for(census: Census, site: Site) -> list:
    """One CSV row, in `CSV_HEAD` order, for one `Site`."""
    return [
        f"0x{site.off:05X}",
        f"0x{site.row['runtime']:04X}",
        site.row["opcode"],
        f"0x{site.row['target']:04X}",
        site.row["frame_onto"],
        site.row["frame_over"],
        prev_bytes_of(census.d, site.off),
        site.region["name"] if site.region else NOT_NAMED,
        site.region_distance,
        site.grid,
        site.frontier if site.frontier is not None else NOT_NAMED,
        site.walk_verdict,
        site.walk_reason,
        (f"0x{site.entry:04X} ({census.descents[site.entry].basis})"
         if site.entry is not None else ""),
        site.ghidra,
        YES if site.on_boundary else NO,
        YES if site.is_trampoline_target else NO,
        names_for(census.annotations, site.row["target"]),
        site.verdict,
        site.verdict_reason,
    ]


def csv_text(d: bytes, annotations_path=None, index_path=None) -> str:
    """The whole census as CSV text, from the image.

    Written to a string rather than to a file so `--check` can diff it against
    the committed copy and `--csv` can hand it to stdout. This tool writes no
    committed file except the table itself, which is generated by redirecting
    `--csv` and is never hand-edited.
    """
    census = Census(d, annotations_path, index_path)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_HEAD)
    for site in census.sites():
        w.writerow(row_for(census, site))
    return buf.getvalue()


def table_dicts(d: bytes, annotations_path=None, index_path=None):
    """The census as a list of `CSV_HEAD`/cell dicts.

    The same rows `csv_text()` writes, keyed rather than positional, so a caller
    can read one column without re-parsing the CSV. The report builds its own
    list over the same `row_for()` because it holds the `Census` it needs for the
    figures it prints around the table; this is the entry point for a caller that
    only wants the rows.
    """
    census = Census(d, annotations_path, index_path)
    return [dict(zip(CSV_HEAD, row_for(census, site)))
            for site in census.sites()]


# --- reporting -------------------------------------------------------------

def report(d: bytes, annotations_path=None, index_path=None) -> None:
    """The plain run: the population, the verdicts, the gap, the base rate."""
    census = Census(d, annotations_path, index_path)
    table = [dict(zip(CSV_HEAD, row_for(census, site)))
             for site in census.sites()]
    unplaced, labelled = census.unplaced(), census.labelled()

    print(f"## 1. The population: {len(unplaced)} site(s) outside every region")
    print()
    print(f"  {len(census.rows)} bucket-C site(s) by the image's own scan, of")
    print(f"  which {len(labelled)} fall inside a span data-regions.yaml lists and")
    print(f"  {len(unplaced)} fall outside every one of them;")
    print(f"  {sum(1 for r in unplaced if r['anchored'])} of those are anchored.")
    print()
    print("  The count is derived from `region_at()` on every run, so listing a")
    print("  new region moves this table. It is not written down anywhere.")
    print()

    print("## 2. The verdicts")
    print()
    counts = collections.Counter(t["verdict"] for t in table)
    meaning = {
        TRAMPOLINE: "the target is an address a trampoline names",
        TABLE_ENTRY: "adjacent to a listed region, on its grid, shape decodes",
        CODE: "inside something a method read as code",
        UNRESOLVED: "not decided by this method; the reason is in the next column",
    }
    print("| verdict | sites | what it means |")
    print("|---|---:|---|")
    for verdict in VERDICTS:
        print(f"| `{verdict}` | {counts.get(verdict, 0)} | {meaning[verdict]} |")
    print()
    print("  A zero is \"not found by this method\", never \"absent\" --")
    print("  docs/findings.md §4c, and the caveat this file is most subject to.")
    print()
    onb = sum(1 for t in table if t["on_instruction_boundary"] == YES)
    print(f"  `code` does not mean the byte starts an instruction. That is the")
    print(f"  separate `on_instruction_boundary` column, and it says yes for")
    print(f"  {onb} of the {len(table)} rows.")
    print()
    for reason, n in sorted(collections.Counter(
            t["verdict_reason"] for t in table).items(),
            key=lambda kv: (-kv[1], kv[0])):
        print(f"  {reason:<46} {n}")
    print()

    print("## 3. The gap below the walk's frontier")
    print()
    print("  Distance to the nearest instruction start this walk decoded at or")
    print("  below the site: the gap `bucket-c-codemap.md` §Limits declines to")
    print("  carry. No threshold is applied to it -- a row is never promoted out")
    print("  of `unresolved` by sitting far below the frontier, because a cut")
    print("  would be a hand-set value every future seed set has to re-argue.")
    print()
    gaps = [t["bytes_below_frontier"] for t in table
            if t["bytes_below_frontier"] != NOT_NAMED]
    far = [g for g in gaps if g > 0]
    print(f"  {len(gaps)} of the {len(table)} row(s) have a frontier below them;")
    print(f"  {len(gaps) - len(far)} sit on a decoded instruction and the other")
    print(f"  {len(far)} are in a gap, {min(far)} to {max(far)} bytes deep.")
    for t in sorted(table, key=_gap_order, reverse=True)[:3]:
        print(f"    `{t['file_offset']}` {t['bytes_below_frontier']} bytes below"
              f" the frontier, {t['walk_verdict']} ({t['walk_reason']}),"
              f" target {t['target']}")
    print()

    print("## 4. Is the target named anywhere")
    print()
    named = [t for t in table if t["target_named_in"] != NOT_NAMED]
    both = [t for t in named if "|" in t["target_named_in"]]
    print(f"  {len(named)} of the {len(table)} site(s) name their target in")
    print(f"  `annotations/ghidra-functions.csv`: {len(named) - len(both)} in one")
    print(f"  bank, {len(both)} in both banks under different names.")
    print()
    print("  Both-banks-different-names is the shape of the problem rather than a")
    print("  resolution of it: the same address is a different routine in each")
    print("  bank, which is why `offset_for_runtime()` returns None. It says the")
    print("  address is a plausible entry point, not that any site reaches one.")
    print()
    generated = sorted({t["target"] for t in table
                        if t["target_named_in"] == NOT_NAMED
                        and int(t["target"], 16) in census.index})
    print(f"  {len(generated)} target(s) are named in `decompiled/index.csv` but")
    print(f"  not annotated: {', '.join(generated) or 'none'}.")
    print("  Those are `call-target`/`auto` seed rows rather than hand")
    print("  annotations, and they are reported as not annotated rather than")
    print("  folded in -- the index is generated, so its extra names are what the")
    print("  decompiler found rather than what a person wrote down.")
    print()

    print("## 5. The base rate the best-framed site's alignment is worth")
    print()
    holds = sum(1 for t in table if t["grid_state"] == GRID_HOLDS)
    on_grid = sum(1 for t in table
                  if t["grid_state"] in (GRID_HOLDS, GRID_FAILS))
    print(f"  {on_grid} of the {len(table)} unplaced site(s) sit on their nearest")
    print(f"  region's stride grid, and {holds} of those decode under that")
    print("  region's shape. That share is the rate at which alignment and a")
    print("  shape match arrive by accident, and it is what decides whether any")
    print("  one site's alignment means anything.")
    print()
    site = next((t for t in table if t["file_offset"] == "0x021C6"), None)
    if site:
        print("  `0x021C6`, the 24-of-24 site `ec-data-regions.md` §4 is about:")
        for col in ("verdict", "verdict_reason", "grid_state",
                    "bytes_to_nearest_region", "bytes_below_frontier",
                    "walk_verdict", "walk_reason", "on_instruction_boundary",
                    "target_is_trampoline_entry", "target_named_in"):
            print(f"    {col:<28} {site[col]}")
        print()
        print("  Two readings stay open and this table picks neither: a real call")
        print("  into bank space, or another misframed table or an unnamed")
        print("  routine. Its target being the one address of the 102 that a")
        print("  trampoline names is evidence, not a verdict -- a byte scan does")
        print("  not say which bank is mapped when the common area runs.")
        print()

    print("## 6. What this does not decide")
    print()
    print(f"  bucket C still holds {len(census.rows)} site(s), `offset_for_runtime()`")
    print("  still returns None for all of them, and no `registers.yaml` status")
    print("  moves. Nothing here is a behavioural claim: no register was read")
    print("  back, no capture was opened, no EC was powered.")


def _gap_order(t):
    """Sort key putting rows with no frontier below last, then furthest first."""
    if t["bytes_below_frontier"] == NOT_NAMED:
        return (0, 0)
    return (1, int(t["bytes_below_frontier"]))


# --- self-test -------------------------------------------------------------

# The oracle, transcribed from `ec/annotations/bank-call-audit.md` §5 and
# `docs/findings/ec-data-regions.md` §4 rather than read back from this tool's
# own output -- see `test_bucket_c_unplaced.py`'s docstring. A tool that graded
# its own census against itself would pass whatever the census said.
ORACLE_SITE = 0x021C6
ORACLE_TARGET = 0xE000
ORACLE_TRIPLES_REGION = "common-219c-ff-triples"
ORACLE_LABELED_ABSENT = (0x055DC, 0x00381, 0x06952)
ORACLE_FAR_REGION = 0x12          # the gap §4 pins past the triples' file_hi
ORACLE_BYTE_BEFORE = 0xE0         # d[0x21C5]
ORACLE_FRONTIER = 921             # what bucket-c-codemap.md §Limits states


def self_test(d: bytes, annotations_path=None, index_path=None) -> int:
    """The refusals, and the oracle. `--check` is the reproducibility half."""
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    def refuses(fn, *a):
        try:
            fn(*a)
        except SystemExit:
            return True
        return False

    print("bucket_c_unplaced.py --self-test")
    print()

    # 1. The vocabulary is closed. Three refusals, because they are three
    #    separate mistakes: a verdict outside the tuple, a reason outside its
    #    verdict's set, and an empty reason.
    for verdict in VERDICTS:
        check(not refuses(check_verdict, verdict, sorted(VERDICT_REASONS[verdict])[0]),
              f"{verdict!r} accepts one of its own reasons")
    for outside in ("probably-code", "", "Code", "CODE", "resolved", None, 0):
        check(refuses(check_verdict, outside, "ret"),
              f"verdict {outside!r} is refused, not rendered")
    for verdict in VERDICTS:
        for other in VERDICTS:
            if other != verdict:
                check(refuses(check_verdict, verdict,
                              sorted(VERDICT_REASONS[other])[0]),
                      f"{verdict!r} refuses {other!r}'s reason -- the sets are "
                      "disjoint, so a reason cannot drift between verdicts")
    for blank in ("", "   ", "\t"):
        check(refuses(check_verdict, UNRESOLVED, blank),
              f"reason {blank!r} is refused rather than rendered blank")

    # 2. The vocabularies are drawn from closed sets rather than restated.
    check(VERDICT_REASONS[UNRESOLVED] is bucket_c_codemap.WALK_REASONS,
          "the unresolved reasons are the walk's own vocabulary, borrowed "
          "rather than restated, so the two files cannot disagree about why a "
          "site is unresolved")
    check(len({frozenset(s) for s in VERDICT_REASONS.values()}) == len(VERDICTS),
          "no two verdicts share a reason set, so a reason belongs to exactly "
          "one verdict")
    check(GRID_STATES == (GRID_HOLDS, GRID_FAILS, GRID_OFF, GRID_NO_STRIDE),
          "the grid vocabulary carries the three answers plus the null-stride "
          "cell, so a region with no stride is annotated rather than fatal")

    census = Census(d, annotations_path, index_path)
    unplaced, labelled = census.unplaced(), census.labelled()

    # 3. The population partitions bucket C, and the unplaced half is exactly
    #    what `region_at()` declines -- both directions, because one direction
    #    also passes for a census that dropped every row.
    check(len(unplaced) + len(labelled) == len(census.rows),
          f"unplaced ({len(unplaced)}) + labelled ({len(labelled)}) == the "
          f"{len(census.rows)} bucket-C site(s) the image's own scan produces")
    check({r["file_offset"] for r in unplaced}.isdisjoint(
        {r["file_offset"] for r in labelled}),
        "no site is both placed and unplaced")
    check(all(region_at(census.regions, r["file_offset"]) is None
              for r in unplaced),
          "every row of the population is one `region_at()` declines")
    check(all(region_at(census.regions, r["file_offset"]) is not None
              for r in labelled),
          "every labelled site is one `region_at()` finds")

    # 4. The oracle, from bank-call-audit.md §5 and ec-data-regions.md §4.
    offs = {r["file_offset"] for r in unplaced}
    check(ORACLE_SITE in offs,
          f"0x{ORACLE_SITE:05X} is in the population -- the site §4 is about")
    for off in ORACLE_LABELED_ABSENT:
        check(off not in offs,
              f"0x{off:05X} is labelled and therefore absent from it")
    check(d[ORACLE_SITE - 1] == ORACLE_BYTE_BEFORE,
          f"d[0x{ORACLE_SITE - 1:05X}] == 0x{ORACLE_BYTE_BEFORE:02X}, the byte "
          "between the site and the triples' last entry")
    region, distance = nearest_region(census.regions, ORACLE_SITE)
    check(distance == ORACLE_FAR_REGION
          and region["name"] == ORACLE_TRIPLES_REGION,
          f"the site is 0x{distance:X} bytes past {region['name']}'s file_hi, "
          "which is what §4 pins")

    table = [dict(zip(CSV_HEAD, row_for(census, site)))
             for site in census.sites()]
    site = next((t for t in table if t["file_offset"] == "0x021C6"), None)
    if site is None:
        check(False, "0x021C6 has a row in the census")
    else:
        check(site["verdict"] == TRAMPOLINE
              and site["target"] == f"0x{ORACLE_TARGET:04X}",
              f"its target 0x{ORACLE_TARGET:04X} is an address a trampoline "
              f"names, so the verdict is {TRAMPOLINE!r}")
        check(site["grid_state"] == GRID_FAILS,
              "the region shape does not decode at the site, so the grid cell "
              "says so beside the verdict rather than the verdict implying it")
        check(site["bytes_below_frontier"] == ORACLE_FRONTIER,
              f"it is {site['bytes_below_frontier']} bytes below the walk's "
              f"frontier, the figure bucket-c-codemap.md §Limits states")
        check(site["target_named_in"] == NOT_NAMED,
              "its target is named nowhere in the annotations CSV -- the address "
              "the linker recorded is one no hand annotation names")

    # 5. The grid measurement is ungated, so it must be able to disagree with
    #    the verdict. Were every on-grid row also a table entry the two columns
    #    would be one column and the adjacency gate would be untested.
    check(any(t["grid_state"] == GRID_HOLDS and t["verdict"] != TABLE_ENTRY
              for t in table),
          "at least one row sits on a region's grid and is not called a table "
          "entry, which is the adjacency gate doing its work")
    check(all(t["verdict"] != TABLE_ENTRY or t["grid_state"] == GRID_HOLDS
              for t in table),
          "no row is a table entry without the grid measurement saying so")
    check(all(t["bytes_to_nearest_region"] == NOT_NAMED
              or t["nearest_region"] != NOT_NAMED for t in table),
          "every row that names a nearest region also records the distance to "
          "it, so `on-grid` is never read without knowing how far away")

    # 6. `on_instruction_boundary` is a question `verdict` does not answer.
    check(any(t["on_instruction_boundary"] == NO and t["verdict"] == CODE
              for t in table),
          "a site can be `code` and still start no instruction, which is the "
          "distinction the boolean exists to keep")

    # 7. The naming sources are read, not merged: a name that appears only in a
    #    generated seed row is reported as not annotated.
    unannotated = {int(t["target"], 16) for t in table
                   if t["target_named_in"] == NOT_NAMED}
    check(bool(unannotated & set(census.index)),
          "at least one target is named in the index but not annotated, and it "
          "is reported as not annotated")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the refusals or "
              "with the audit")
        return 1
    print("self-test passed: the vocabulary is closed, the population partitions "
          "bucket C, and 0x021C6 is still the site whose target a trampoline "
          "names")
    return 0


# --- check -----------------------------------------------------------------

def check_csv(d: bytes, path, annotations_path=None, index_path=None) -> int:
    """Diff the regenerated table against the committed one. Exit 1 on a diff.

    A *missing* file fails rather than being created. Writing it would make
    `--check` the thing that decides what the committed table is, which is the
    arrangement `bucket_c_codemap.check_csv()` and `data_regions.py` both
    refuse: the tool re-derives and the file is compared.
    """
    if not os.path.exists(path):
        print(f"error: {path} does not exist. --check compares; it never "
              "creates. Generate the table with --csv and commit it.",
              file=sys.stderr)
        return 1
    want = open(path).read()
    got = csv_text(d, annotations_path, index_path)
    if got == want:
        print(f"bucket-c-unplaced.csv: {got.count(chr(10)) - 1} row(s) match the "
              "committed file, byte for byte")
        return 0
    diff = list(difflib.unified_diff(want.splitlines(True), got.splitlines(True),
                                     fromfile=f"committed {path}",
                                     tofile="regenerated"))
    sys.stdout.writelines(diff)
    print("error: the committed table is not what this run derives from the "
          "image", file=sys.stderr)
    return 1


def for_offset(d: bytes, off: int, annotations_path=None,
               index_path=None) -> int:
    """Print one site's row as a field/value list. The debugging entry point."""
    census = Census(d, annotations_path, index_path)
    site = next((s for s in census.sites() if s.off == off), None)
    if site is None:
        inside = region_at(census.regions, off)
        print(f"0x{off:05X} is not an unplaced bucket-C site"
              + (f" (it is inside {inside['name']})" if inside else ""))
        return 1
    for col, cell in zip(CSV_HEAD, row_for(census, site)):
        print(f"  {col:<28} {cell}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default %(default)s)")
    ap.add_argument("--check", action="store_true",
                    help="regenerate the committed table in memory and diff it")
    ap.add_argument("--self-test", action="store_true",
                    help="check the refusals and the census oracle, and exit")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per unplaced site on stdout")
    ap.add_argument("--for-offset", type=lambda s: int(s, 0),
                    help="print one site's row as a field/value list")
    ap.add_argument("--csv-path", default=DEFAULT_CSV,
                    help="the committed table --check compares against")
    ap.add_argument("--annotations", default=DEFAULT_ANNOTATIONS,
                    help="annotations/ghidra-functions.csv, the naming source")
    ap.add_argument("--index", default=DEFAULT_INDEX,
                    help="ec/decompiled/index.csv, read for the agreement check")
    args = ap.parse_args()

    if args.check and args.self_test:
        ap.error("--check and --self-test are two different claims about this "
                 "image; run them separately")
    if args.csv and args.for_offset is not None:
        ap.error("--csv and --for-offset are two different tables; run them "
                 "separately")

    here = os.path.dirname(os.path.abspath(__file__))
    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1

    def resolve(path):
        return path if os.path.isabs(path) else os.path.join(here, path)

    annotations, index = resolve(args.annotations), resolve(args.index)

    if args.self_test:
        return self_test(d, annotations, index)
    if args.check:
        return check_csv(d, resolve(args.csv_path), annotations, index)
    if args.csv:
        sys.stdout.write(csv_text(d, annotations, index))
        return 0
    if args.for_offset is not None:
        return for_offset(d, args.for_offset, annotations, index)

    report(d, annotations, index)
    return 0


if __name__ == "__main__":
    sys.exit(main())