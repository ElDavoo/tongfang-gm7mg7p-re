#!/usr/bin/env python3
"""Measure the caller frames `--callers` scans, so `MIN_FRAME_INSNS` is a number.

`ec/tools/pd_index_geometry.py`'s `--callers` mode files each caller row
`unresolved` when its frame holds no literal register load, and now files it
`frame too short to say` when the frame is under `MIN_FRAME_INSNS` instructions
instead. That threshold is a claim about how much of a caller was read, and a
claim like that needs the distribution behind it rather than the five rows of
`../annotations/pd-index-callers.csv` to argue from. This tool produces that
distribution, over every caller row the byte scan and the two entry picks
produce across the whole PD image.

**Every row is one `(site, entry pick, caller)` triple, not one site.** The
sites come from `base_sites(d, WHOLE_IMAGE)`, which is the same whole-image
census `--bases all` prints and the same one `pd-index-geometry.md` 7 uses; the
rows come from `pd_index_geometry.caller_rows()` over them. The frame length is
`len(frame_of(d, caller_file_offset))`, the same quantity the `frame_insns`
column of that CSV now carries, read here off the row rather than recomputed --
so this tool measures the column, and `test_pd_caller_frame_quality.py` is what
checks the column against the image independently.

**The two framing measures disagree, which is the reason this reports a
separate column at all.** `converges_from()` steps `inline_arg_len()` and
`case_table_len()` into its walk and `frame_of()` does not, so `frame_onto == 0`
names the empty case only in one direction: every row it catches has an empty
frame, and rows with an empty frame are not all rows it catches. The
cross-tabulation below is what makes that visible rather than asserted, and it
is why the threshold is carried as an instruction count -- a rule keyed on
`frame_onto` would silently grade the rows the two measures disagree about by
the stricter of the two.

**What a bucket count is.** A row in the shortest buckets is one where the scan
had little or nothing to read, which is *not* a finding about the index; that is
why `pd_index_geometry.py` words its new status value around the frame rather
than the index. The distribution is what says the vocabulary needs the extra
value rather than only one conservative `unresolved` -- and it says it by showing
that the short frames are, with the one exception the write-up names, rows that
carry no literals at all. The figure over the committed image is stable; a
figure over the repository's own tables is not, and none is printed here.

This tool is **not** in `.github/scripts/agent-gates.sh`, and cannot be from an
agent branch: that file lives under `.github/`, which the pipeline's push token
cannot write. `pd_index_geometry.py --self-test`, which this measurement
backing the same way, is not there either. Run both by hand; neither is run by
CI, and nothing here implies otherwise.

Usage:
    python3 ec/tools/pd_caller_frame_quality.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/pd_caller_frame_quality.py ec/firmware/GMxMGxx_11.800 --csv
    python3 ec/tools/pd_caller_frame_quality.py ec/firmware/GMxMGxx_11.800 --self-test
"""

import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pd_index_geometry as P  # noqa: E402

DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")

# The buckets the report prints, smallest first, derived from the threshold
# rather than written beside it: the split is *at*
# `pd_index_geometry.MIN_FRAME_INSNS`, not near it, so the line a reader checks
# is the line the criterion draws. Hand-writing these as "0", "1", "2", "3",
# ">=4" would make the wide bucket a second statement of the threshold that
# could be moved on its own, and a moved one lands a row in a bucket the
# cross-tabulation has no cell for.
CSV_FIELDS = ("frame_insns_bucket", "rows", "frame_onto_zero", "carries_literals",
              "unresolved", "short_frame_status")


def buckets() -> tuple:
    """Every bucket label, shortest first, splitting at MIN_FRAME_INSNS."""
    return tuple(str(n) for n in range(P.MIN_FRAME_INSNS)) \
        + (f">={P.MIN_FRAME_INSNS}",)


def bucket_of(insns: int) -> str:
    """Which printed bucket a frame length falls in."""
    return str(insns) if insns < P.MIN_FRAME_INSNS else buckets()[-1]


def caller_site_addrs(d: bytes):
    """PD runtime addresses for the whole-image base census, deduplicated.

    Deduplicated because `base_sites()` emits one row per `MOV DPTR` opcode and
    two sites can share a runtime address; `caller_rows()` is a function of the
    address alone, so passing the same one twice would count its rows twice.
    """
    return sorted({row["runtime"] for row in P.base_sites(d, P.WHOLE_IMAGE)})


def caller_frames(d: bytes):
    """Every caller row over the whole image, each with its frame length.

    The row dicts come from `pd_index_geometry.caller_rows()` unchanged; only
    the site list is wider than that tool's default four, and the two therefore
    cannot disagree about what a caller row *is*.
    """
    addrs = caller_site_addrs(d)
    groups = P.caller_rows(d, addrs)
    rows = [r for g in groups for p in g["picks"] for r in p["rows"]]
    labels = buckets()
    stray = sorted({b for b in (bucket_of(r["frame_insns"]) for r in rows)
                    if b not in labels})
    if stray:
        raise ValueError("bucket_of() put %s outside the buckets %s: the "
                         "bucket labels and MIN_FRAME_INSNS have drifted apart"
                         % (stray, list(labels)))
    return addrs, rows


def row_key(r: dict) -> tuple:
    """What identifies one caller row, for a relation between *sets* of them.

    The row's full identity, so the set is over rows rather than over something
    one row projects onto. The file offset alone is not one: `caller_rows()`
    offers each entry to every site it precedes, so one address is the caller
    row of more than one site and a key that stopped there would merge them --
    and a merged pair can satisfy both sides of the relation at once, which is
    the failure the set form exists to make visible.

    `kind` and `entry` ride along for the same reason rather than because they
    are known to separate anything: they are what makes the tuple *the* row, and
    a key has to be the identity rather than a list of the fields that happen to
    distinguish rows on one image.
    """
    return (r["site"], r["entry"], r["kind"], r["file_offset"])


def census(d: bytes):
    """The bucketed cross-tabulation the report prints, plus the raw totals.

    Returned as a dict of bucket -> (rows, onto_zero, literals, unresolved,
    short_frame) so the shape is checkable rather than reformatted for display:
    a `--csv` consumer and the `--self-test` both read the same numbers the
    table prints.

    `frame_onto_zero_rows` and `empty_frame_rows` are the two *sets* the
    one-way framing relation is about, keyed by `row_key()`. They are returned
    as well as counted because a relation between two sets is not checkable
    from their sizes: any two counts in the right order satisfy
    `a <= b`, including the order a violation would produce, so a check on the
    counts would hold whatever the rows actually are. The counts beside them in
    the same dict are `len()` of these sets, so the figures the report prints
    and the relation the self-test asserts cannot drift apart.
    """
    addrs, rows = caller_frames(d)
    out = {b: dict(rows=0, frame_onto_zero=0, carries_literals=0,
                   unresolved=0, short_frame=0) for b in buckets()}
    onto_zero_rows, empty_frame_rows = set(), set()
    for r in rows:
        cell = out[bucket_of(r["frame_insns"])]
        cell["rows"] += 1
        cell["frame_onto_zero"] += r["frame_onto"] == 0
        cell["carries_literals"] += bool(r["literals"])
        cell["unresolved"] += r["status"] == P.UNRESOLVED_CALLER
        cell["short_frame"] += r["status"] == P.CALLER_SHORT_FRAME
        if r["frame_onto"] == 0:
            onto_zero_rows.add(row_key(r))
        if r["frame_insns"] == 0:
            empty_frame_rows.add(row_key(r))
    return out, dict(rows=len(rows), sites=len(addrs),
                     frame_onto_zero=len(onto_zero_rows),
                     empty_frame=len(empty_frame_rows),
                     frame_onto_zero_rows=onto_zero_rows,
                     empty_frame_rows=empty_frame_rows)


def print_report(d: bytes) -> None:
    table, totals = census(d)
    print("Caller frame length over every base site in the PD image, from "
          f"{totals['sites']} distinct site(s) in "
          f"{P.fmt_span(P.WHOLE_IMAGE)}")
    print("  Sites come from base_sites(d, WHOLE_IMAGE); rows come from "
          "caller_rows() over them.")
    print("  frame_insns is len(frame_of(d, caller_file_offset)); the "
          f"'>= {P.MIN_FRAME_INSNS}' bucket is where "
          "pd_index_geometry.MIN_FRAME_INSNS draws the line.\n")
    print(f"  {'frame insns':<12} {'rows':>6} {'onto==0':>8} {'lits':>6} "
          f"{'unres.':>7} {'short':>6}")
    for b in buckets():
        c = table[b]
        print(f"  {b:<12} {c['rows']:>6} {c['frame_onto_zero']:>8} "
              f"{c['carries_literals']:>6} {c['unresolved']:>7} "
              f"{c['short_frame']:>6}")
    print(f"  {'total':<12} {totals['rows']:>6}")
    print("\n  'lits' counts rows whose frame holds a literal register load, "
          "'unres.' the\n  `unresolved` ones and 'short' the `frame too short "
          "to say` ones. A row with a literal\n  load is a positive finding at "
          "any frame length, so it is never filed short.")
    print(f"\n  The two framing measures are not the same predicate: "
          f"{totals['frame_onto_zero']} row(s) have\n  frame_onto == 0 against "
          f"{totals['empty_frame']} with an empty frame. Every row the first "
          "catches\n  is in the second, so `frame_onto == 0` is a one-way "
          "test of the empty case -- which\n  is why the criterion is an "
          "instruction count and not a test on either column.")


def write_csv(d: bytes) -> None:
    table, _ = census(d)
    w = csv.writer(sys.stdout)
    w.writerow(CSV_FIELDS)
    for b in buckets():
        c = table[b]
        w.writerow([b, c["rows"], c["frame_onto_zero"], c["carries_literals"],
                    c["unresolved"], c["short_frame"]])


def self_test(d: bytes) -> int:
    """--self-test: properties of the report that hold whatever the census is.

    Deliberately not a set of expected counts. A figure over the whole image is
    a property of the committed firmware and belongs in the write-up beside the
    command that prints it; a figure here would be a second place every future
    change to `caller_rows()` or the term model has to be reflected in, which is
    the failure CLAUDE.md's "No totals of the repository's own text" is about.
    What is asserted instead are the relations the report's own claims rest on:
    the buckets partition the rows, the one-way framing relation holds, and the
    threshold is the boundary the tool's import says it is.
    """
    names = buckets()
    short, wide = names[:-1], names[-1:]
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else '!  '} {text}")

    # Before the census, not after: bucket_of() and buckets() read the same
    # constant, so a disagreement between them is the one thing that would make
    # every number below meaningless, and it is cheaper to say so than to
    # cross-tabulate rows into buckets that do not exist.
    check(all(bucket_of(int(b)) == b for b in short)
          and bucket_of(P.MIN_FRAME_INSNS) in wide,
          "bucket_of() puts every printed bucket label back where it came "
          "from, so the labels and MIN_FRAME_INSNS cannot drift apart")

    table, totals = census(d)
    check(sum(table[b]["rows"] for b in names) == totals["rows"],
          f"the {len(names)} buckets partition every caller row: none is "
          "dropped and none is counted twice")
    check(all(table[b]["short_frame"] == 0 for b in wide),
          f"no row in the `{wide[0]}` bucket is filed "
          f"`{P.CALLER_SHORT_FRAME}`")
    check(sum(table[b]["short_frame"] for b in names) ==
          sum(table[b]["rows"] - table[b]["carries_literals"] for b in short),
          f"every row below {P.MIN_FRAME_INSNS} instructions that carries no "
          f"literal is filed `{P.CALLER_SHORT_FRAME}`, and every row that is "
          "filed it carries no literal")
    check(sum(table[b]["carries_literals"] for b in short) <=
          sum(table[b]["short_frame"] for b in names),
          f"no row carrying a literal load is filed `{P.CALLER_SHORT_FRAME}`: "
          "a short frame is never a reason to lose a positive finding")
    # The relation, not the two sizes. `a <= b` on the counts holds for any two
    # figures in that order, and a violation here makes the sets disagree while
    # leaving their sizes in it -- one row moving out of the empty set and one
    # in is invisible to a count -- so this is the check that has to be a set
    # inclusion to be the claim it names. The figures stay in the message
    # because they are what a reader wants to see, and they are `len()` of the
    # two sets above.
    check(totals["frame_onto_zero_rows"] <= totals["empty_frame_rows"],
          f"`frame_onto == 0` ({totals['frame_onto_zero']}) catches only rows "
          f"with an empty frame ({totals['empty_frame']}), so it is a one-way "
          "test of that case and not an identification of it")
    check(bucket_of(P.MIN_FRAME_INSNS - 1) in short
          and bucket_of(P.MIN_FRAME_INSNS) in wide,
          f"the buckets split at {P.MIN_FRAME_INSNS} instructions, which is "
          "pd_index_geometry.MIN_FRAME_INSNS")
    check(P.caller_status({}, {"R3"}, P.MIN_FRAME_INSNS) == P.UNRESOLVED_CALLER
          and P.caller_status({}, {"R3"}, P.MIN_FRAME_INSNS - 1)
          == P.CALLER_SHORT_FRAME,
          f"caller_status() flips at the same {P.MIN_FRAME_INSNS} the buckets "
          "split at, so the report's wide bucket is exactly the set of rows "
          "that can read `unresolved`")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree")
    else:
        print("self-test passed: the buckets partition the caller rows and the "
              f"short-frame line is at {P.MIN_FRAME_INSNS} instructions")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Bucket whole-image PD caller rows by frame length.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="?", default=DEFAULT_FIRMWARE,
                    help="EC firmware image (default: the committed one)")
    ap.add_argument("--csv", action="store_true",
                    help="write the cross-tabulation as CSV")
    ap.add_argument("--self-test", action="store_true",
                    help="assert the report's relations and exit")
    args = ap.parse_args(argv)

    with open(args.image, "rb") as fh:
        d = fh.read()
    if args.self_test:
        return self_test(d)
    if args.csv:
        write_csv(d)
    else:
        print_report(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())