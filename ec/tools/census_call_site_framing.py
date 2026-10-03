#!/usr/bin/env python3
"""Classify every bucket-A and bucket-C row of `bank-call-targets.csv` against
the committed `.asm` listings, and say where the scan's read is a real opcode.

`census_ff_fill.py` ran `listing_coverage()` and `classify_site()` over 28 rows
-- the ones naming the seventeen functions a byte scan seeded inside `common`'s
unprogrammed band -- and found none of them at an instruction boundary. That
was the right measurement for the population it was about and a sample for the
rest of the file: `bank-call-targets.csv` holds thousands of rows, and
`bank-call-audit.md` §1 carries an `anchored` column whose meaning the band
made doubtful. **This tool asks the same three-way question of every row in
buckets A and C**, which is the population the question is actually about, and
reports the rows grouped by region, bucket and anchored-ness rather than a total.

**The two functions are imported, not reimplemented**, for the reason
`is_fill` is imported rather than reimplemented: one implementation, so this
tool and the fill census cannot come to disagree about what a verdict means or
which listings are in scope. The band falls out of the same call, and the
self-test pins it at 0 / 22 / 6 so the generalization is shown not to have
changed the one population already measured.

**What the generalization settles, and what it does not.** In the band,
`anchored` failed: a site clearing the anchored bar was no more an opcode than
one that did not, which is what `bank-call-audit.md` §1 concedes and scopes to
that band. Across **bucket A** the relationship inverts the other way -- an
anchored site is at a real opcode 58.6% of the time, against 1.0% for an
unanchored one, a 57x lift. That is a clear majority, not a certainty: 955 of the
2,305 anchored bucket-A sites are still not at an instruction boundary. So §1's
caveat is correct as written and stays band-scoped, with the reason stated
rather than implied.

**The band is not the only place it fails, and this tool does not let the
aggregate imply that it is.** Across **bucket C** no anchored site this census
can see is at a boundary, while an unanchored C site is: the same inversion, in
a cell larger than the band and disjoint from it (every band row is bucket A).
A lift measured over A and C together is bucket A's number wearing C's rows, so
the report prints the cross-tab per bucket rather than as one aggregate, and
carries no prose claim of a single lift.

**What a verdict is not.** Three answers and no fourth, and each is a statement
about the committed listings rather than about the firmware:

  * `at an instruction boundary` -- the site's first byte starts an
    instruction a committed listing draws. **This makes the scan's read at that
    site a real opcode. It says nothing about the target.** The target column
    below is reported beside it, never folded into it.
  * `inside another instruction` -- the site is an operand byte, a rel8, or an
    immediate. What the scan matched is a pattern, not a transfer.
  * `no listing covers it` -- *not found by this method*, never "there is no
    code here". The caller may be code Ghidra never exported, and nothing here
    can tell that from an address nothing was decoded at. The verdict is
    scoped to **the caller's own program**: a `common` runtime address a bank
    overlay also covers is reported in its own column, because the common area
    and the bank images are separate address spaces that share those numbers.

**The target's program is a derivation, and one row has none.** A bucket-A
target below `0x8000` is in the common area; one at or above it is in the
caller's own bank, on the same-bank convention `bank-call-audit.md` §1 is about.
A bucket-C target is at or above `0x8000` seen from the common area, where
nothing in the byte says which bank is mapped -- the case
`trace_xdata_refs.offset_for_runtime()` returns `None` for and that §5 declines
to resolve. That row is reported as unresolvable rather than guessed at, and
the guess is not made anywhere in this tool.

**No table is committed.** The verdict is a function of the committed listings,
so a committed table goes stale at the next Ghidra export with no gate here to
catch it (`.github/scripts/agent-gates.sh` is a template copy an agent branch
cannot touch). `--rows` writes CSV to stdout, or to wherever `--out` points;
nothing here decides for you, and the reason not to aim it at a file in this
tree is the export above rather than a rule this tool enforces.

Usage:
    python3 census_call_site_framing.py
    python3 census_call_site_framing.py --rows
    python3 census_call_site_framing.py --rows --rows-for common
    python3 census_call_site_framing.py --self-test
"""
import argparse
import collections
import csv
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    # The imports below are by module name, the way `census_test_line_pins.py`
    # loads a sibling: the tool is run as `python3 ec/tools/<this>.py` from the
    # repository root, where the script's own directory is not on `sys.path`.
    sys.path.insert(0, HERE)

from census_ff_fill import (CALL_TARGETS, annotation_keys, classify_site,
                            index_rows, listing_coverage, listing_span,
                            norm_addr, read_csv)
from citation_callers import iter_instructions

EC = os.path.join(HERE, os.pardir)
DECOMPILED = os.path.join(EC, "decompiled")
ANNOTATIONS = os.path.join(EC, "annotations")
BUCKET_C_CODEMAP = os.path.join(ANNOTATIONS, "bucket-c-codemap.csv")

# The two buckets this tool reads. Bucket B is left to #574, which is open on
# it and wants a different `entry`/`erased`/`other` census: two branches
# writing the same rows is the conflict surface CLAUDE.md warns about. The
# schemas compose -- both key on `(region, runtime, bucket)` -- so #574 can run
# the same classification over B and join on the site.
BUCKETS = ("A", "C")

# The three verdicts, in the order the report prints them, and the only three
# there are. A tool that could answer a fourth way would make the partition
# check below vacuous.
VERDICTS = ("at an instruction boundary", "inside another instruction",
            "no listing covers it")

# The seventeen `common` fill listings inside the unprogrammed band, pinned by
# address rather than derived, for the reason `census_ff_fill.py` gives for
# `PRE_EXISTING_FILL_ROWS`: the split over them is the population #571 was
# filed against, and a tool that recomputed the set from today's listings could
# no longer reproduce the number it is checking. The band is the control --
# this tool must agree with the census that measured it first.
BAND_FILL_ADDRS = (
    "7401", "7404", "7405", "7408", "7410", "741C", "7602", "7848", "7883",
    "7BFF", "7C02", "7DF2", "7E01", "7F01", "7F02", "7FF1", "7FFF",
)


def is_anchored(row):
    """`frame_onto > 0` -- at least one of the 24 byte anchors decoded onto it.

    A candidate decoded entry point, not a call: `bank-call-audit.md` §1 says so
    where the column is defined, and the cross-tab this tool prints is the
    measurement of how far that candidacy tracks being a real opcode.
    """
    return int(row["frame_onto"]) > 0


def target_program(row):
    """Which program's address space `target` names, or None when undecidable.

    Below `0x8000` is the common area, which every program maps; at or above it
    is the caller's own bank on the same-bank convention. From the common area
    a target at or above `0x8000` names *a* bank and nothing in the byte says
    which, so this returns None rather than picking one -- the case
    `trace_xdata_refs.offset_for_runtime()` declines and `bank-call-audit.md`
    §5 declines with it.
    """
    if int(norm_addr(row["target"]), 16) < 0x8000:
        return "common"
    return row["region"] if row["region"] in ("bank0", "bank1") else None


def population():
    """Every A/C row, with its verdict and the instruction covering it.

    Selection is `bucket in BUCKETS` and nothing else. A row is never dropped
    for lacking a covering listing: that is one of the three answers.
    """
    cover = listing_coverage()
    out = []
    for row in read_csv(CALL_TARGETS):
        if row["bucket"] not in BUCKETS:
            continue
        where, hit = classify_site(row, cover)
        out.append({"row": row, "verdict": where, "hit": hit})
    return out


def other_programs(cover, region, runtime):
    """Programs other than `region` whose listings cover `runtime`, sorted.

    Reported because a `no listing covers it` verdict is scoped to the caller's
    own program, and without this the cell reads as "there is no code here" --
    the overclaim CLAUDE.md puts above every other rule. A `common` address a
    bank overlay also covers is two programs' statements about one runtime
    number, and neither is the other's.
    """
    addr = norm_addr(runtime)
    return sorted({program for (program, a) in cover
                   if a == addr and program != region})


def target_columns(row, index, annotated):
    """(program, has index row, has annotation row) for one row's target.

    Two labels and never a filter, `data_regions.py`'s discipline applied here:
    a target with no export is still classified, and an export is not a
    confirmation that the scan read the call correctly. The verdict column and
    these three are independent, and the report says so.
    """
    program = target_program(row)
    if program is None:
        return ("unresolvable", "n/a", "n/a")
    key = (program, norm_addr(row["target"]))
    return (program,
            "yes" if key in index else "no",
            "yes" if key in annotated else "no")


def at_entry_address(hit, runtime):
    """True when the covering instruction is its own listing's first.

    A statement about the **site**, not about the target: it asks whether the
    listing that happens to cover `runtime` starts at `runtime`, which is a
    fact about where the scan matched rather than about whether the scan's
    `target` is a function. The target-side counts are `target_columns()`, and
    the report prints both beside each other; neither is a subset of the other
    and they are not multiplied into a single "clears both" figure, because a
    boundary read establishes only the first.
    """
    return hit is not None and hit["listing"] == norm_addr(runtime)


def rows_csv(sites, cover, index, annotated):
    """The per-row table as CSV text, for `--rows`.

    One line per site, every site, nothing dropped -- this is the work list the
    report's distributions are summaries of, and a work list that omits its
    long tail is not one.
    """
    buf = io.StringIO()
    out = csv.writer(buf, lineterminator="\n")
    out.writerow(["region", "runtime", "opcode", "target", "bucket",
                  "frame_onto", "anchored", "verdict", "listing",
                  "listing_addr", "listing_text", "target_program",
                  "target_in_index", "target_annotated", "site_at_entry",
                  "runtime_in_other_programs"])
    for site in sites:
        row, verdict, hit = site["row"], site["verdict"], site["hit"]
        program, in_index, in_ann = target_columns(row, index, annotated)
        others = other_programs(cover, row["region"], row["runtime"])
        out.writerow([
            row["region"], row["runtime"], row["opcode"], row["target"],
            row["bucket"], row["frame_onto"],
            "yes" if is_anchored(row) else "no", verdict,
            hit["listing"] if hit else "", hit["addr"] if hit else "",
            hit["text"] if hit else "", program, in_index, in_ann,
            "yes" if at_entry_address(hit, row["runtime"]) else "no",
            ";".join(others),
        ])
    return buf.getvalue()


def report(sites, cover, index, annotated):
    """The whole census as the lines `docs/findings/call-site-framing-census.md`
    quotes."""
    out = []
    say = out.append
    total = len(sites)
    verdicts = collections.Counter(s["verdict"] for s in sites)

    say("census_call_site_framing.py -- every bucket-A and bucket-C row of "
        "bank-call-targets.csv, against the committed listings")
    say("")

    # --- the three-way split, and its denominator on the same line ---
    say("## verdicts")
    for verdict in VERDICTS:
        n = verdicts[verdict]
        say("  %-28s %5d of %d  (%.1f%%)"
            % (verdict, n, total, 100.0 * n / total))
    say("  %-28s %5d" % ("(sum of the three)", sum(verdicts.values())))
    say("")

    # --- region x bucket, so no cell is read as the whole ---
    say("## by region and bucket")
    say("  region  bucket  %s" % "  ".join("%28s" % v for v in VERDICTS))
    combos = sorted({(s["row"]["region"], s["row"]["bucket"]) for s in sites})
    for region, bucket in combos:
        cells = [sum(1 for s in sites
                     if s["row"]["region"] == region
                     and s["row"]["bucket"] == bucket
                     and s["verdict"] == v) for v in VERDICTS]
        say("  %-6s  %-6s  %s  (%d rows)"
            % (region, bucket, "  ".join("%28d" % c for c in cells), sum(cells)))
    say("")

    # --- the cross-tab, which is the finding and not one of the three answers ---
    anchored = [s for s in sites if is_anchored(s["row"])]
    plain = [s for s in sites if not is_anchored(s["row"])]
    say("## anchored against the verdict (bank-call-audit.md §1's column)")
    say("  %-28s %8s %8s %8s" % ("", "boundary", "inside", "no listing"))
    for label, group in (("anchored", anchored), ("not anchored", plain)):
        counts = collections.Counter(s["verdict"] for s in group)
        say("  %-28s %8d %8d %8d  (%d rows)"
            % (label, counts[VERDICTS[0]], counts[VERDICTS[1]],
               counts[VERDICTS[2]], len(group)))
    say("")

    # The same cross-tab per bucket, because the aggregate above is not one
    # relationship and reads as though it were. `anchored` predicts a real
    # opcode across bucket A; across bucket C it does not, and a lift measured
    # over A and C together is A's number carrying C's rows. Printed per bucket
    # so the claim cannot be read off the aggregate. The band inverts inside
    # bucket A -- every band row is one -- and the control section below prints
    # it, so the two exceptions are not confused for one cell.
    say("  the same cross-tab split by bucket, because the two rows above are "
        "two populations averaged:")
    say("  %-6s  %-18s %-18s %s"
        % ("bucket", "anchored", "not anchored", "lift"))
    for bucket in BUCKETS:
        cells = []
        rates = []
        for group in (anchored, plain):
            sub = [s for s in group if s["row"]["bucket"] == bucket]
            hits = sum(1 for s in sub if s["verdict"] == VERDICTS[0])
            if sub:
                cells.append("%d/%d %5.1f%%" % (hits, len(sub),
                                                100.0 * hits / len(sub)))
                rates.append(hits / len(sub))
            else:
                cells.append("%d row(s)" % len(sub))
                rates.append(None)
        # A lift is stated only where it is defined. `0/83` against `1/57` is a
        # real answer and prints as `0x`; a bucket whose unanchored rows contain
        # no boundary row has no baseline to divide by, and that is a different
        # thing from a zero and says so rather than borrowing the zero's name.
        if rates[0] is None or rates[1] is None:
            lift = "n/a"
        elif not rates[1]:
            lift = "n/a (no unanchored boundary row)"
        else:
            lift = "%.0fx" % (rates[0] / rates[1])
        say("  %-6s  %-18s %-18s %s" % (bucket, cells[0], cells[1], lift))
    # Scoped to the buckets actually in this population, so a `--rows-for`
    # narrowing does not print a claim about a cell it has excluded.
    present = [b for b in BUCKETS
               if any(s["row"]["bucket"] == b for s in sites)]
    if present == list(BUCKETS):
        say("  the lift is bucket A's alone; bucket C inverts like the band "
            "does, in a larger and disjoint cell")
    else:
        say("  only bucket %s is in this population, so the split above has "
            "one cell and the two-bucket reading does not apply"
            % "/".join(present))
    say("")

    # --- the boundary set as a work list, and the labels that make it one ---
    boundary = [s for s in sites if s["verdict"] == VERDICTS[0]]
    # Counted over every boundary row, not only the resolvable ones: whether
    # the *site* is a listing's entry address does not depend on which program
    # its target lives in, and the unresolvable row is a boundary row like any
    # other.
    at_entry = sum(1 for s in boundary
                   if at_entry_address(s["hit"], s["row"]["runtime"]))
    pairs = set()
    resolved = unresolved = 0
    labelled = annotated_rows = 0
    for site in boundary:
        row = site["row"]
        program, in_index, in_ann = target_columns(row, index, annotated)
        if program == "unresolvable":
            unresolved += 1
            continue
        resolved += 1
        key = (program, norm_addr(row["target"]))
        pairs.add(key)
        if in_index == "yes":
            labelled += 1
        if in_ann == "yes":
            annotated_rows += 1
    say("## the boundary set as a work list")
    say("  %d boundary row(s); %d distinct (target program, target) pair(s) "
        "behind them" % (len(boundary), len(pairs)))
    say("  %d of the %d resolvable row(s) name a target with an `index.csv` "
        "row; %d with a `ghidra-functions.csv` row (%d of the %d distinct "
        "targets do)"
        % (labelled, resolved, annotated_rows,
           len(pairs & annotated), len(pairs)))
    say("  %d boundary row(s) sit at a listing's own entry address. That is a "
        "fact about the **site** -- where the scan matched, at a listing's "
        "first byte -- and not a count of good targets; the two `index.csv` "
        "and `ghidra-functions.csv` figures above are the target side, and "
        "neither is a subset of the other" % at_entry)
    if unresolved:
        say("  %d row(s) name a target no bank can be chosen for (bucket C), "
            "reported unresolvable rather than guessed at" % unresolved)
    say("")

    # --- the misreads, and where they cluster ---
    inside = [s for s in sites if s["verdict"] == VERDICTS[1]]
    mnemonic = collections.Counter(s["hit"]["text"].split()[0] for s in inside)
    say("## the misread population, by the instruction it sits inside")
    say("  %d row(s) sit inside another instruction" % len(inside))
    for name, n in mnemonic.most_common(6):
        say("    %-6s %4d" % (name, n))
    dptr = [s for s in inside if s["hit"]["text"].startswith("mov DPTR")]
    if dptr:
        by_opcode = collections.Counter(s["row"]["opcode"] for s in dptr)
        say("  %d of them sit inside a `mov DPTR,#imm16` immediate: %s"
            % (len(dptr), ", ".join("%d %s" % (n, o)
                                    for o, n in sorted(by_opcode.items()))))
        say("  the family #508 names; this tool re-reports the addresses so it "
            "can reconcile against the population rather than recount it")
    say("")

    # --- the uncovered set, and the program scoping that keeps it honest ---
    uncovered = [s for s in sites if s["verdict"] == VERDICTS[2]]
    cross = collections.Counter()
    for site in uncovered:
        progs = other_programs(cover, site["row"]["region"],
                               site["row"]["runtime"])
        cross[(site["row"]["region"], site["row"]["bucket"],
               "bank overlay" if any(p in ("bank0", "bank1") for p in progs)
               else ("other program" if progs else "no program"))] += 1
    say("## the uncovered set, and which other programs cover the address")
    say("  %d row(s) are under no listing **in the caller's own program**; "
        "that is not found by this method, not absence of code" % len(uncovered))
    for key in sorted(cross):
        say("    %-6s %s  %-14s %4d" % (key[0], key[1], key[2], cross[key]))
    say("")

    # --- the control: the population the fill census measured first ---
    band = [s for s in sites
            if norm_addr(s["row"]["target"]) in BAND_FILL_ADDRS]
    bandv = collections.Counter(s["verdict"] for s in band)
    say("## the control: the band ff-fill-census.md measured")
    say("  %d row(s) name the %d `common` fill address(es) inside "
        "0x728F-0x7FFF" % (len(band), len(BAND_FILL_ADDRS)))
    say("  %s -- the same split census_ff_fill.py reports, from the same two "
        "imported functions" % " / ".join(str(bandv[v]) for v in VERDICTS))
    say("")

    # --- composition, reported and not resolved ---
    say("## composition with bucket-c-codemap.md")
    if os.path.exists(BUCKET_C_CODEMAP):
        reached = [r for r in read_csv(BUCKET_C_CODEMAP)
                   if r["walk_verdict"] == "reached-by-walk"]
        by_listing = collections.Counter(
            classify_site({"region": "common", "runtime": r["runtime"]},
                          cover)[0] for r in reached)
        say("  %d bucket-C site(s) the flow walk reached: %s"
            % (len(reached), ", ".join("%s %d" % (k, v)
                                       for k, v in sorted(by_listing.items()))))
        say("  the two disagree, and this tool does not resolve it: a flow walk "
            "cannot tell code from a table it wandered into, and a listing "
            "boundary set cannot see a routine Ghidra never exported")
    else:
        say("  bucket-c-codemap.csv is not in this tree; the composition is "
            "not reported rather than reported as absent")
    return "\n".join(out)


def self_test(sites, cover) -> int:
    """Known answers, the invariants that hold as the tree grows, and the
    refusals that make the known answers worth anything.

    Three halves, and the middle one is the point. Pinning the band's split
    would still pass if `classify_site` started answering "boundary" for
    everything, so what is held is the *shape*: three verdicts that partition
    the population, a selection that is exactly `bucket in {A, C}`, and a
    verdict that is a function of `(region, runtime)` alone. None of those is a
    number, and all of them survive a merge that adds rows.
    """
    bad = 0
    print("census_call_site_framing.py --self-test")

    def check(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"  {detail}" if detail and not ok else ""))

    rows = [s["row"] for s in sites]
    by_key = {(r["region"], norm_addr(r["runtime"])): r for r in rows}

    # --- the control: the band, pinned as the population it is ---
    band = [s for s in sites
            if norm_addr(s["row"]["target"]) in BAND_FILL_ADDRS]
    bandv = collections.Counter(s["verdict"] for s in band)
    check("28 rows name the seventeen band addresses",
          len(band) == 28 and {norm_addr(s["row"]["target"]) for s in band}
          == set(BAND_FILL_ADDRS),
          "got %d row(s), %d distinct target(s)"
          % (len(band), len({norm_addr(s["row"]["target"]) for s in band})))
    check("the band splits 0 / 22 / 6, as census_ff_fill.py reports it",
          tuple(bandv[v] for v in VERDICTS) == (0, 22, 6),
          "got " + " / ".join(str(bandv[v]) for v in VERDICTS))

    # --- the three verdicts, one per answer, by transcription ---
    for region, runtime, verdict, hit in (
            ("common", "0x7159", VERDICTS[1],
             {"listing": "7151", "addr": "7158", "text": "jnz 0x716c"}),
            ("bank1", "0xD756", VERDICTS[1],
             {"listing": "D6EE", "addr": "D755", "text": "jnc 0xd759"}),
            ("bank0", "0xE716", VERDICTS[1],
             {"listing": "E6F4", "addr": "E715", "text": "mov R3, #0x12"}),
            ("common", "0x0504", VERDICTS[0],
             {"listing": "0504", "addr": "0504", "text": "lcall 0x9000"}),
            ("common", "0x0372", VERDICTS[2], None)):
        got = classify_site({"region": region, "runtime": runtime}, cover)
        check("worked example: %s,%s is %s"
              % (region, runtime, verdict), got == (verdict, hit),
              "got " + repr(got))

    # --- the invariants, which are the part that holds as the tree grows ---
    check("the three verdicts partition the population exactly",
          set(collections.Counter(s["verdict"] for s in sites)) <= set(VERDICTS)
          and sum(collections.Counter(s["verdict"] for s in sites).values())
          == len(sites),
          "got " + repr(dict(collections.Counter(s["verdict"] for s in sites))))
    every = read_csv(CALL_TARGETS)
    # Compared as `(region, runtime)` multisets rather than by object identity:
    # the two `read_csv` calls build separate dicts, so `id()` says nothing
    # about whether the selection is the same set of rows.
    key = lambda r: (r["region"], norm_addr(r["runtime"]))
    check("the selection is exactly `bucket in {A, C}`",
          collections.Counter(map(key, rows))
          == collections.Counter(key(r) for r in every
                                 if r["bucket"] in BUCKETS)
          and not any(r["bucket"] not in BUCKETS for r in rows),
          "selected %d of %d" % (len(rows), len(every)))
    mismatched = [k for k, r in by_key.items()
                  if classify_site(r, cover)[0]
                  != next(s["verdict"] for s in sites if key(s["row"]) == k)]
    check("the verdict is a function of (region, runtime) alone",
          not mismatched, "disagree at " + ", ".join(map(str, mismatched[:3])))

    # --- the refusals ---
    check("refusal: bucket B is not read even when a B row is present",
          not any(s["row"]["bucket"] == "B" for s in sites)
          and any(r["bucket"] == "B" for r in every),
          "the CSV does hold B rows, so this is not vacuous")
    synthetic = {"region": "common", "runtime": "0xFFF0", "bucket": "A"}
    check("refusal: a site no listing covers classifies, and is not an error",
          classify_site(synthetic, cover) == (VERDICTS[2], None)
          and synthetic not in [s["row"] for s in sites],
          "got " + repr(classify_site(synthetic, cover)))
    # A listing that parses to no instruction must contribute no coverage, or
    # an empty listing would claim a zero-length span of the address space and
    # an address inside it would read as covered. Tested against a fixture
    # rather than the tree, because no committed listing parses to nothing and
    # a guard checked against the tree would quietly stop being a guard the day
    # one did. `listing_span` is the imported function that keeps `None` for
    # this distinct from a span of length zero.
    with tempfile.TemporaryDirectory() as scratch:
        stub = os.path.join(scratch, "EMPTY.asm")
        with open(stub, "w") as handle:
            handle.write("; a header and nothing else\n")
        check("refusal: a listing that parses to no instruction is not a span",
              listing_span(stub) is None
              and not list(iter_instructions(stub))
              and listing_coverage() != {},
              "an empty listing would otherwise cover a zero-length span")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the hand "
              "transcriptions above")
        return 1
    print("self-test passed: the band's 28 rows at 0 / 22 / 6, five worked "
          "examples by transcription, the partition / selection / "
          "function-of-the-site invariants, and the three refusals")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", action="store_true",
                    help="write one CSV row per A/C site, to stdout")
    ap.add_argument("--rows-for", metavar="REGION", default=None,
                    help="narrow --rows to one caller region")
    ap.add_argument("--out", metavar="PATH", default=None,
                    help="write --rows to this path instead of stdout. Aim it "
                         "outside the tree: the verdicts are a function of the "
                         "committed listings, so a committed table goes stale "
                         "at the next Ghidra export")
    ap.add_argument("--self-test", action="store_true",
                    help="check the band's split, the worked examples, the "
                         "structural invariants and the refusals")
    args = ap.parse_args()

    sites = population()
    if args.rows_for:
        sites = [s for s in sites if s["row"]["region"] == args.rows_for]
        if not sites:
            print(f"no bucket-A or bucket-C row has caller region "
                  f"{args.rows_for!r}", file=sys.stderr)
            return 1
    if args.rows_for and not args.rows:
        args.rows = True

    if args.rows:
        text = rows_csv(sites, listing_coverage(), index_rows(),
                        annotation_keys())
        if args.out:
            with open(args.out, "w", newline="") as handle:
                handle.write(text)
        else:
            sys.stdout.write(text)
        return 0

    if args.self_test:
        return self_test(sites, listing_coverage())
    print(report(sites, listing_coverage(), index_rows(), annotation_keys()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
