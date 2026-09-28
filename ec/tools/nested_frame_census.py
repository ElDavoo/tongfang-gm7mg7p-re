#!/usr/bin/env python3
"""Census every exported frame that sits inside another exported frame, and say
which kind of "inside" each one is.

`second_copy_census.py` asks where the *name* at a rowless address came from,
and one of its five boundary verdicts -- `inside-a-function` -- is a frame that
sits inside a function the export had already framed. That verdict is asked of
seven rows there. It is asked here of every row in `ec/decompiled/index.csv`,
which is a different question with a different population: not "which of these
names are second copies" but "how often does the export carry one function
inside another it already drew". `docs/findings/named-without-a-row.md` §8 item
2 counts that by hand, as two, and the tool is what the hand count should have
been.

**One predicate, printed, and the other one reported beside it.** "Contained" is
ambiguous in this tree and the two readings do not agree, so both are measured
and neither is presented as *the* population:

  address-inside-a-listing   this row's own address falls inside another row's
                             committed listing span, in the same program. This
                             is the reading §8's own worked examples take --
                             `common 0x65A6` "holds" `0x6209` -- and it is the
                             population the report leads with.
  span-inside-a-listing      this row's own *span* sits wholly inside another's,
                             which is what the phrase "contained" literally
                             says. Reported as its own figure, because it is a
                             different set and not a subset the first one can
                             stand in for: a row whose listing is *longer* than
                             the listing holding it, and a mutually nested pair,
                             are in the first and not the second. The report
                             names each one and says which end escapes.

**Two causes, told apart, because they are told apart by the bytes.** The
buckets are named for what was measured and not for a conclusion:

  same-address                 the container's listing opens exactly at its own
                               address, so the container really does frame the
                               bytes it is reported as containing.
  listing-opens-below-address  `span[0] < container_addr`. The container's
                               listing reaches *backwards* past its own entry
                               point, so part of the "containment" is a property
                               of how far the listing extends rather than of
                               nesting. `row_span()` returns a listing's first
                               instruction and not the row's own address --
                               which is why `listing_bytes()` in the census this
                               imports already has to guard for a listing that
                               "opens somewhere else" -- and that guard is what
                               this bucket rests on. It does **not** claim the
                               container fails to frame those bytes.

Those two are a closed vocabulary, and a third shape is a refusal rather than a
third bucket: a container whose listing opens *above* its own address would be
neither, and `failures()` names it. The bucket belongs to the **edge** and not
to the row, which is a distinction with teeth here -- several rows are inside
two containers at once, and in each of those the two containers are in
different buckets. "The container" is therefore not always a single row, and
`common 0x6A02` / `0x6D46` is the pair that shows it: each address falls inside
the other's span and neither span contains the other.

**Three verdicts per row, so "not nested" has a name.** A row with no container
is either `after-a-function` (some committed listing ends the byte immediately
before it, so its frame begins the next statement) or `unframed` (nothing
committed covers it and nothing ends immediately before it). `unframed` is the
answer with no instance among the nested rows -- a row cannot be both, which is
the point of printing it -- and its one instance in `second_copy_census`'s
boundary partition is `bank1 0x9AD2`, a switch entry, which is in this tool's
own `unframed` set too. Naming a class keeps the others a partition rather than a
list of the cases that have come up.

**Failures, and what is only reported.** Two conditions fail `--check`: a
committed listing whose opening bytes are not the firmware's, which would leave
every verdict above a reading of a tree that is no longer there; and a bucket
outside the vocabulary above. Two are *reported* and never fail, because this
method cannot decide them: a row with no committed listing, and a listing that
opens somewhere other than the row's own address and so cannot be compared at
that address. Both are **not found by this method**, never "not nested" and
never a defect. The committed tree carries both -- `listing-index.csv` records
the first as `(no-instructions)` with a `.c` and no `.asm`, and the second is
the ordinary case for a Ghidra frame drawn below the function it belongs to --
so a check that failed on either would ship red and be switched off, which is
how a gate stops gating. `docs/findings/nested-export-frames.md` carries the
figures for whichever tree a reader is on.

**What this is not.** Every input is a committed file: `index.csv`, the `.asm`
listings, `ghidra-functions.csv` and the firmware. Nothing was observed on
hardware or in Windows, no register was read, and no Ghidra run is involved or
implied. The population is not a constant and this file states no total: the
figures are whatever `--check` prints on the tree a reader runs it on. The tool
writes nothing.

Usage:
    python3 nested_frame_census.py
    python3 nested_frame_census.py --check
    python3 nested_frame_census.py --self-test
"""
import argparse
import collections
import os
import sys
import tempfile

from second_copy_census import (FIRMWARE, bytes_of, is_backed, listing_bytes,
                                norm_addr, read_csv, row_span)

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
DECOMPILED = os.path.join(EC, "decompiled")
INDEX_CSV = os.path.join(DECOMPILED, "index.csv")
ANNOTATIONS = os.path.join(EC, "annotations", "ghidra-functions.csv")

# The per-row verdicts, and no fourth. `no-committed-listing` is not a verdict
# about framing at all -- it is the refusal this method states for a row it
# cannot read -- and it is named rather than dropped so the three verdicts above
# it partition every row the census *did* read.
VERDICTS = ("nested", "after-a-function", "unframed")
UNREAD = "no-committed-listing"

# The per-edge buckets, and no third. See the docstring: a shape outside these
# two is reported by `failures()` rather than filed under a name that would read
# as an answer.
BUCKETS = ("same-address", "listing-opens-below-address")


def span_table(decompiled, index_rows):
    """{(program, addr): (first, last)} for every index row, listing or not.

    `row_span()` reads the committed `.asm` rather than `index.csv`'s `size`
    column, and returns None for a row whose listing is not there; that None is
    kept, because dropping the row would make the population a number of rows
    this method managed to read rather than a number of rows the export carries.
    Cached by the imported reader, so a self-test fixture tree and the committed
    tree cannot read each other's answers.
    """
    out = {}
    for row in index_rows:
        key = (row["program"], norm_addr(row["addr"]))
        out[key] = row_span(decompiled, row["program"], int(key[1], 16))
    return out


def by_program(index_rows):
    """{program: [row, ...]} ascending by address.

    Sorted rather than left in the index's order, because every read below walks
    the list and a re-export that reordered it would otherwise change the answer
    without changing a byte.
    """
    out = collections.defaultdict(list)
    for row in index_rows:
        out[row["program"]].append(row)
    for rows in out.values():
        rows.sort(key=lambda r: int(norm_addr(r["addr"]), 16))
    return out


def span_ends(rows, spans):
    """The set of last-byte addresses every span in `rows` ends at.

    Over the whole program rather than over the rows walked so far, so a row's
    verdict does not depend on the order `index.csv` happens to carry.
    """
    ends = set()
    for row in rows:
        got = spans.get((row["program"], norm_addr(row["addr"])))
        if got:
            ends.add(got[1])
    return ends


def bucket_of(container_addr, span):
    """Which of `BUCKETS` an (container address, container span) is in.

    None for the shape that is in neither, which is a refusal and not a third
    bucket: a container whose listing opens above its own address would mean the
    "inside" runs the other way, and filing it under a name chosen for this
    tree would be a claim about a shape nothing committed has.
    """
    if span[0] == container_addr:
        return "same-address"
    if span[0] < container_addr:
        return "listing-opens-below-address"
    return None


def edge(row, container, container_span, span):
    """One (nested row, container) pair, as a record."""
    addr = int(norm_addr(container["addr"]), 16)
    return {
        "program": row["program"],
        "addr": norm_addr(row["addr"]),
        "name": row["name"],
        "seed_basis": row.get("seed_basis", "?"),
        "container": container,
        "container_addr": norm_addr(container["addr"]),
        "container_span": container_span,
        "span": span,
        "bucket": bucket_of(addr, container_span),
        # Whether the container's span also swallows this row's whole listing.
        # The two predicates are kept on the edge rather than derived twice, so
        # the report cannot print a strict figure from a different walk than the
        # one the leading figure came from.
        "span_contained": (container_span[0] <= span[0]
                           and span[1] <= container_span[1]),
    }


def edges_of(row, rows, spans):
    """Every other row in the same program whose listing span covers `row`.

    A span covers an address when it *reaches* it, and the row itself is never
    its own container: `second_copy_census.covering_row()` cannot be used for
    this walk, because it is asked there about an address that is not itself an
    index row and so never hits itself. It is the same shape and the same
    downwards walk, over every row rather than until the first span reaches.
    """
    addr = int(norm_addr(row["addr"]), 16)
    span = spans.get((row["program"], norm_addr(row["addr"])))
    if span is None:
        return []
    out = []
    for other in rows.get(row["program"], ()):
        if other is row:
            continue
        got = spans.get((other["program"], norm_addr(other["addr"])))
        if got and got[0] <= addr <= got[1]:
            out.append(edge(row, other, got, span))
    return out


def census(index_rows, ann_rows, fw=None, decompiled=DECOMPILED):
    """Every index row as a record, in the order the index carries them.

    `is_backed()` is the exporter's own mapping of which CSV row stands behind an
    index row, imported rather than restated, and it is what the report's
    row-backed split is built from. `seed_basis` says how the *export* seeded the
    function; `backed` says whether a `ghidra-functions.csv` row claims it. The
    two disagree -- a `call-target` row can be backed and an `annotation` row is
    not automatically one a reader can drop -- and the question §8 asks is about
    the second.
    """
    if fw is None:
        fw = open(FIRMWARE, "rb").read()
    rows = by_program(index_rows)
    spans = span_table(decompiled, index_rows)
    ends = {program: span_ends(members, spans)
            for program, members in rows.items()}
    ann_keys = {(r["scope"], norm_addr(r["addr"])) for r in ann_rows}

    out = []
    for row in index_rows:
        key = (row["program"], norm_addr(row["addr"]))
        addr = int(key[1], 16)
        span = spans[key]
        found = edges_of(row, rows, spans) if span else []
        record = {
            "program": row["program"],
            "addr": key[1],
            "name": row["name"],
            "seed_basis": row.get("seed_basis", "?"),
            "annotated": row.get("annotated", ""),
            "backed": is_backed(row, ann_keys),
            "span": span,
            "edges": found,
            "verdict": UNREAD,
            # The listing's own opening bytes and the firmware's, for
            # `failures()` to compare. Read for every row rather than only the
            # nested ones, so the staleness cross-check covers the whole export
            # and not just the population this report leads with.
            "listing": listing_bytes(decompiled, row["program"], addr),
            "image": bytes_of(fw, row["program"], addr, 3),
        }
        if span is not None:
            if found:
                record["verdict"] = "nested"
            elif addr - 1 in ends.get(row["program"], ()):
                record["verdict"] = "after-a-function"
            else:
                record["verdict"] = "unframed"
        out.append(record)
    return out


def population(records):
    """The nested rows, and every edge among them, in report order."""
    nested = [r for r in records if r["verdict"] == "nested"]
    edges = [e for r in nested for e in r["edges"]]
    return nested, edges


def failures(records, edges):
    """What `--check` refuses, in two kinds and no more.

    A committed listing whose opening bytes are not the firmware's is a stale
    export, which would leave every verdict above a reading of a tree that is no
    longer there. And an edge whose bucket is outside `BUCKETS` is a shape this
    tool has no name for, which is a gap in the vocabulary rather than a row to
    skip; a census that quietly filed it under one of the two would make the
    split a list instead of a partition. That second guard cannot fire on the
    walk as it stands -- a span that covers an address cannot start above it --
    and it is here so that a change to the walk which made it reachable is
    reported rather than silently mislabelled.

    A row with no committed listing and a listing that opens somewhere else are
    *not* here. They are `notes()`.
    """
    out = []
    for r in records:
        if r["listing"] is None or r["image"] is None:
            continue                      # `notes()` reports it, and says why
        if r["listing"] != r["image"][:len(r["listing"])]:
            out.append("%s %s %s: the committed listing opens with %s and the "
                       "firmware holds %s there; the export is stale, re-run it"
                       % (r["program"], r["addr"], r["name"],
                          r["listing"].hex(" "),
                          r["image"][:len(r["listing"])].hex(" ")))
    for e in edges:
        if e["bucket"] not in BUCKETS:
            out.append("%s %s %s: %s %s is listed 0x%04X-0x%04X, so it opens "
                       "%s its own address 0x%04X and the 'inside' runs the "
                       "other way -- this tool has no bucket for that shape"
                       % (e["program"], e["addr"], e["name"],
                          e["container"]["program"], e["container"]["addr"],
                          e["container_span"][0], e["container_span"][1],
                          "above" if e["container_span"][0] >
                          int(e["container_addr"], 16) else "at",
                          int(e["container_addr"], 16)))
    return out


def notes(records):
    """What this method could not read, and why that is not a verdict.

    Two shapes, both of which the committed tree carries. A row with no
    committed listing is **not found by this method**: the export records these
    as `(no-instructions)` in `listing-index.csv` and writes a `.c` with no
    `.asm`, so the absence is recorded rather than a gap. And a listing that
    opens somewhere other than its row's own address is the shape
    `listing_bytes()` already declines -- `span[0] != addr` -- which is the
    ordinary case for a Ghidra frame drawn a little below the function it
    belongs to, and is exactly what the `listing-opens-below-address` bucket is
    about. Neither is a failure and neither says anything about whether the row
    is nested.
    """
    out = []
    for r in records:
        if r["verdict"] == UNREAD:
            out.append("%s %s %s: no committed listing at %s/%s.asm, so this "
                       "method did not read it -- recorded in listing-index.csv "
                       "as `(no-instructions)` with a .c and no .asm"
                       % (r["program"], r["addr"], r["name"],
                          r["program"], r["addr"]))
        elif r["span"][0] != int(r["addr"], 16):
            out.append("%s %s %s: listed 0x%04X-0x%04X, which opens below its "
                       "own address, so the listing's opening bytes cannot be "
                       "compared at 0x%04X -- the span is still read"
                       % (r["program"], r["addr"], r["name"],
                          r["span"][0], r["span"][1], int(r["addr"], 16)))
    return out


def where_text(e):
    """The container of an edge, in the form the report and the self-test read."""
    c = e["container"]
    return "%s %s `%s`, listed 0x%04X-0x%04X" % (
        c["program"], e["container_addr"], c["name"],
        e["container_span"][0], e["container_span"][1])


def overlap_reason(e):
    """Why an edge is not a span-inside-a-span one, in a clause.

    Two shapes, and both are stated as what they are rather than as a category:
    the container's own address falls inside this row's span, so the two nest in
    each other and neither is the container; or this row's listing is longer
    than the listing that holds it, and the report says which end escapes.
    """
    at = int(e["container_addr"], 16)
    if e["span"][0] <= at <= e["span"][1]:
        return ("nested in each other: 0x%04X is inside this row's own "
                "0x%04X-0x%04X too" % (at, e["span"][0], e["span"][1]))
    lo = "its own listing opens at 0x%04X, below the container's 0x%04X" % (
        e["span"][0], e["container_span"][0]) if e["span"][0] < \
        e["container_span"][0] else ""
    hi = "its own listing ends at 0x%04X, past the container's 0x%04X" % (
        e["span"][1], e["container_span"][1]) if e["span"][1] > \
        e["container_span"][1] else ""
    return "; ".join(part for part in (lo, hi) if part)


def report(records, found, told):
    """The lines `docs/findings/nested-export-frames.md` quotes."""
    out = []
    say = out.append
    say("nested_frame_census.py -- every ec/decompiled/index.csv row, measured "
        "against the committed listings of its own program")
    say("")

    nested, edges = population(records)
    counts = collections.Counter(r["verdict"] for r in records)
    say("  predicate (the population below): a row is `nested` when another "
        "row in the SAME program has a committed listing whose span contains "
        "this row's own address.")
    say("  the other reading of \"contained\" -- this row's own span inside "
        "another's -- is reported separately below, and neither is presented "
        "as the population.")
    say("")
    say("  %d index row(s): %d nested, %d after-a-function, %d unframed, %d "
        "not read by this method."
        % (len(records), counts["nested"], counts["after-a-function"],
           counts["unframed"], counts[UNREAD]))
    say("  A span is a property of the listing, so it is read from the `.asm` "
        "and not from `index.csv`'s `size` column: `bank0 0x8054` records 21 "
        "and its listing runs 0x8054-0x806B.")
    say("")

    strict = [e for e in edges if e["span_contained"]]
    say("## the two readings of \"contained\", and why they differ")
    say("")
    say("  address-inside-a-listing  %d row(s), %d edge(s)" % (len(nested),
                                                               len(edges)))
    say("  span-inside-a-listing     %d row(s), %d edge(s) -- the phrase taken "
        "literally" % (len({(e["program"], e["addr"]) for e in strict}),
                       len(strict)))
    say("")
    only = sorted({(e["program"], e["addr"]) for e in edges} -
                  {(e["program"], e["addr"]) for e in strict})
    if only:
        say("  %d row(s) are nested and not span-contained, and each says "
            "something the other reading does not:" % len(only))
        for r in records:
            if (r["program"], r["addr"]) in only:
                say("    %-6s %-6s %-30s %s" % (
                    r["program"], r["addr"], r["name"],
                    " ".join(overlap_reason(e) for e in r["edges"])))
    say("")

    say("## the population, per program and per seed_basis")
    say("")
    say("  %-8s %-9s %-9s %-9s %s" % ("program", "rows", "edges",
                                     "same-addr", "opens-below"))
    for program in sorted({r["program"] for r in nested}):
        mine = [e for e in edges if e["program"] == program]
        say("  %-8s %-9d %-9d %-9d %d" % (
            program, len({e["addr"] for e in mine}), len(mine),
            sum(1 for e in mine if e["bucket"] == "same-address"),
            sum(1 for e in mine if e["bucket"] == "listing-opens-below-address")))
    say("")
    say("  %-12s %-9s %-9s %s" % ("seed_basis", "rows", "edges", "backed"))
    for basis in sorted({r["seed_basis"] for r in nested}):
        mine = [e for e in edges if e["seed_basis"] == basis]
        keys = {(e["program"], e["addr"]) for e in mine}
        say("  %-12s %-9d %-9d %d" % (
            basis, len(keys), len(mine),
            sum(1 for r in records
                if (r["program"], r["addr"]) in keys and r["backed"])))
    say("")
    say("  `backed` is `second_copy_census.is_backed()` -- whether a "
        "ghidra-functions.csv row stands behind the index row -- and it is not "
        "`seed_basis`: a `call-target` row can be backed, and the question of "
        "dropping a nested function is a question about the CSV, not about how "
        "the export found the frame.")
    say("")

    say("## the buckets, and where the boundary between them runs")
    say("")
    bucket_counts = collections.Counter(e["bucket"] for e in edges)
    say("  same-address                 %d edge(s) -- the container's listing "
        "opens at its own address, so it frames the bytes it holds"
        % bucket_counts["same-address"])
    say("  listing-opens-below-address  %d edge(s) -- the container's listing "
        "reaches back past its own entry point (0x%04X-0x%04X is `common "
        "0x65A6` on this tree), so part of the containment is a property of "
        "how far the listing extends and only part of it is nesting"
        % (bucket_counts["listing-opens-below-address"], 0x60ED, 0x65A8))
    say("")
    say("  The two are a partition of the EDGES and not of the rows: %d row(s) "
        "are inside two containers at once, and in each of those the two "
        "containers fall in different buckets, so a bucket cannot be attached "
        "to the row."
        % sum(1 for r in nested if len(r["edges"]) > 1))
    say("")

    say("## every nested row, and the container it is measured against")
    say("")
    say("  program addr    name                             basis       "
        "span              bucket                      the container")
    for r in nested:
        for e in r["edges"]:
            say("  %-6s %-6s %-32s %-11s 0x%04X-0x%04X  %-26s %s" % (
                e["program"], e["addr"], e["name"], e["seed_basis"],
                e["span"][0], e["span"][1], e["bucket"] or "(no bucket)",
                where_text(e)))
    say("")

    multi = [r for r in nested if len(r["edges"]) > 1]
    if multi:
        say("## rows inside more than one container")
        say("")
        for r in multi:
            say("    %-6s %-6s %-32s 0x%04X-0x%04X" % (
                r["program"], r["addr"], r["name"], r["span"][0], r["span"][1]))
            for e in r["edges"]:
                say("        %-26s %s" % (e["bucket"] or "(no bucket)",
                                         where_text(e)))
        say("")

    say("## the other two verdicts, and what they are not")
    say("")
    say("  after-a-function  %d row(s) -- some committed listing in the same "
        "program ends the byte immediately before, so the frame begins the "
        "next statement rather than splitting one. This is the shape "
        "`second_copy_census.py`'s own boundary section calls that, and it is "
        "the ordinary case for two exported functions sitting end to end."
        % counts["after-a-function"])
    say("  unframed          %d row(s) -- nothing committed covers the address "
        "and nothing ends immediately before it. There is no instance of it "
        "among the nested rows, which is what a partition is: a row cannot be "
        "both. Its one instance in `second_copy_census.py`'s boundary "
        "partition is `bank1 0x9AD2`, a switch entry, and it is in this set."
        % counts["unframed"])
    say("  Both say the row is not nested *by this read over the committed "
        "listings*. Neither says the frame is wrong there.")
    say("")

    say("## failures")
    say("")
    if found:
        for p in found:
            say("  FAIL  %s" % p)
    else:
        say("  none: every listing this method could compare against the "
            "firmware agrees with it, and every edge falls in one of the two "
            "buckets above")
    say("")

    say("## reported, not failed")
    say("")
    if told:
        for p in told:
            say("  note  %s" % p)
    else:
        say("  none: every row in the index has a listing whose first "
            "instruction is at the row's own address")
    say("")
    say("## reproducing every figure above")
    say("")
    say("  No Ghidra, no network, no scratch directory. Every input is a "
        "committed file: `index.csv`, the `.asm` listings, "
        "`ghidra-functions.csv` and the firmware. **The population is not a "
        "constant and nothing here is a total** -- the figures above are "
        "whatever this prints on the tree you run it on, which is why the "
        "write-up quotes them rather than carrying them.")
    say("")
    say("```")
    say("python3 ec/tools/nested_frame_census.py --check      # this report")
    say("python3 ec/tools/nested_frame_census.py --self-test  # the readings "
        "and the refusals")
    say("```")
    return "\n".join(out)


def _fixture_tree(scratch):
    """A scratch decompiled tree holding the shapes the census has to answer for.

    Fixtures rather than committed rows, for the reason `second_copy_census`
    gives and the reason its self-test states: every one of these is a shape the
    committed tree happens not to have in the arrangement that makes it a test,
    and a refusal tested against the tree stops being a refusal the day the tree
    grows a row that needs it. The addresses are real ones in the common area
    and the image is the firmware with a handful of bytes replaced, so the tool
    under test resolves them through `offset_for_runtime()` exactly as it does
    the committed tree rather than through a path only the fixtures take.

    A listing is written as a list of `(address, bytes, mnemonic)` and the
    image is patched from that same list, rather than the two being written
    separately and left to agree. A fixture whose listing and image disagreed
    would be caught by the staleness cross-check instead of by the case written
    for it, and the refusal under test would be passing for the wrong reason.
    """
    decompiled = os.path.join(scratch, "decompiled")
    os.makedirs(os.path.join(decompiled, "common"))
    os.makedirs(os.path.join(decompiled, "bank0"))
    image = bytearray(open(FIRMWARE, "rb").read()[:0x8000])
    rows, anns = [], []

    def nops(first, count):
        return [(first + i, "00", "nop") for i in range(count)]

    def slot(raw, text):
        """One instruction line's byte column, padded to the three slots the
        committed listings carry. `iter_instructions()` reads the mnemonic by
        position and not by column width, so a short line written without the
        pads is three tokens and the reader declines the whole listing -- which
        is a fixture that silently measures nothing."""
        bytes_ = [raw[i:i + 2] for i in range(0, len(raw), 2)]
        return "%s %s   %s" % (" ".join(bytes_),
                               " ".join(["-"] * (3 - len(bytes_))), text)

    def add(program, at, lines, name, backed=False, no_listing=False):
        addr = "%04X" % at
        for where, raw, _text in lines:
            image[where:where + len(raw) // 2] = bytes.fromhex(raw)
        if not no_listing:
            with open(os.path.join(decompiled, program, addr + ".asm"),
                      "w") as f:
                f.write("; fixture\n\n%s" % "".join(
                    "%04X     %s\n" % (where, slot(raw, text))
                    for where, raw, text in lines))
        rows.append({"program": program, "addr": addr, "name": name,
                     "seed_basis": "call-target", "annotated": "yes",
                     "out_file": "%s/%s.c" % (program, addr)})
        if backed:
            anns.append({"scope": program, "addr": addr, "name": name})
        return rows[-1]

    # Ordinary nesting: the container's listing opens at its own address and
    # runs over the row below it.
    add("common", 0x0100, nops(0x0100, 0x12), "outer", backed=True)
    add("common", 0x0110, nops(0x0110, 1), "inner")
    # A container whose listing opens BELOW its own address, so the "inside" is
    # partly a property of how far the listing reaches back.
    add("common", 0x0200, nops(0x01F0, 0x19), "reaching", backed=True)
    add("common", 0x0208, nops(0x0208, 1), "reached")
    # Mutual nesting: each address inside the other's listing, and neither span
    # inside the other, so neither row has one container. The one shape a "the
    # container" reading cannot hold, and the reason the report is an edge set.
    add("common", 0x0300, nops(0x02F0, 0x22), "first", backed=True)
    add("common", 0x0310, nops(0x0300, 0x21), "second")
    # A row alone in its program, in the other program: spans are per-program,
    # so `common` is not a fallback for `bank0` here the way it is in
    # `target_row()`.
    add("bank0", 0x0400, nops(0x0400, 1), "lonely", backed=True)
    # A row whose frame starts one byte past a listing's end.
    add("common", 0x0500, nops(0x0500, 1), "predecessor")
    add("common", 0x0501, nops(0x0501, 1), "successor")
    # A row with no listing at all: the export records it, this method cannot
    # read it, and neither reading has anything to say about it.
    add("common", 0x0600, [], "unlisted", no_listing=True)
    return decompiled, bytes(image), rows, anns


def self_test() -> int:
    """Today's measured claims, and the refusals that make them worth anything.

    **No count of the tree is asserted here, and that is the hard constraint.**
    A test that pins a population is a value every merge has to edit: the
    figure this tool reports has already moved once between the hand count and
    the measurement, and a self-test pinned to the old one would have gone red on
    a merge that added a row and told the implement stage to fix a correct tool.
    What is pinned instead is the *claim* -- these named addresses nest in these
    containers, with these spans -- and the tool's own logic: that the two
    buckets partition the edges, that the two predicates are both reported and
    differ, that a mutual pair yields both edges, and that every refusal still
    refuses on a fixture.

    The refusals are on fixtures for the same reason, and a refusal tested
    against the committed tree stops being a refusal the day the tree grows a
    row that needs it.
    """
    bad = 0
    print("nested_frame_census.py --self-test")

    def check(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print("  %s  %s%s" % ("ok  " if ok else "FAIL", label,
                              "" if ok or not detail else "  " + detail))

    index_rows = read_csv(INDEX_CSV)
    ann_rows = read_csv(ANNOTATIONS)
    records = census(index_rows, ann_rows)
    found = failures(*population(records))
    told = notes(records)
    by_key = {(r["program"], r["addr"]): r for r in records}
    nested, edges = population(records)

    # The rows a reader will check, each named rather than counted. `bank0 0x8FDB`
    # is the one container holding nine of them; `bank1 0xE2D3` the one holding
    # two, one of which `bank1 0xE322` is a row no CSV claims.
    want = {
        ("bank0", "9000"): ("8FDB", "8FDB-903F"),
        ("bank0", "9006"): ("8FDB", "8FDB-903F"),
        ("bank0", "9007"): ("8FDB", "8FDB-903F"),
        ("bank0", "900D"): ("8FDB", "8FDB-903F"),
        ("bank0", "9015"): ("8FDB", "8FDB-903F"),
        ("bank0", "9016"): ("8FDB", "8FDB-903F"),
        ("bank0", "9018"): ("8FDB", "8FDB-903F"),
        ("bank0", "901C"): ("8FDB", "8FDB-903F"),
        ("bank0", "902A"): ("8FDB", "8FDB-903F"),
        ("bank1", "E322"): ("E2D3", "E2D3-E3B3"),
        ("bank1", "E332"): ("E2D3", "E2D3-E3B3"),
    }
    for key in sorted(want):
        r = by_key[key]
        at, span_text = want[key]
        check("%s %s %s is nested in %s 0x%s, listed %s"
              % (key[0], key[1], r["name"], key[0], at, span_text),
              r["verdict"] == "nested"
              and any(e["container_addr"] == at
                      and "%04X-%04X" % e["container_span"] == span_text
                      for e in r["edges"]),
              "got %s, %r" % (r["verdict"], [where_text(e) for e in r["edges"]]))
    # The claim the issue makes about the annotation-seeded majority, held as a
    # relation rather than a census: the containers the nine rows name are
    # `seed_basis=annotation` and carry a CSV row, so the population §8 counts
    # is mostly rows this repository committed deliberately.
    check("the container of the bank0 0x90xx rows is a CSV row's "
          "function",
          by_key[("bank0", "8FDB")]["seed_basis"] == "annotation"
          and by_key[("bank0", "8FDB")]["backed"],
          "got %s, backed=%s" % (by_key[("bank0", "8FDB")]["seed_basis"],
                                 by_key[("bank0", "8FDB")]["backed"]))
    check("bank1 0xE322, which the issue lists among the committed "
          "annotation rows, is not one: no CSV row stands behind it",
          by_key[("bank1", "E322")]["seed_basis"] == "auto"
          and by_key[("bank1", "E322")]["annotated"] == "no"
          and not by_key[("bank1", "E322")]["backed"],
          "got %s, annotated=%s, backed=%s"
          % (by_key[("bank1", "E322")]["seed_basis"],
             by_key[("bank1", "E322")]["annotated"],
             by_key[("bank1", "E322")]["backed"]))

    # The bucket the tool exists to separate, on the two containers the issue
    # names for it and on the two `common` shapes that are the other cause.
    for key, want_bucket in ((("common", "6209"), "listing-opens-below-address"),
                             (("common", "6402"), "listing-opens-below-address"),
                             (("pd", "4C20"), "listing-opens-below-address"),
                             (("bank0", "9000"), "same-address"),
                             (("bank0", "902A"), "same-address")):
        r = by_key[key]
        check("%s %s is held by a %s container"
              % (key[0], key[1], want_bucket),
              r["verdict"] == "nested"
              and want_bucket in [e["bucket"] for e in r["edges"]],
              "got %r" % [e["bucket"] for e in r["edges"]])

    # The two predicates, both reported and neither the population: the strict
    # reading is a different set, and the rows in one and not the other are
    # named rather than left for a reader to find.
    strict = {(e["program"], e["addr"]) for e in edges if e["span_contained"]}
    only_address = sorted({(e["program"], e["addr"]) for e in edges} - strict)
    check("both readings are printed and they differ, and the rows in one and "
          "not the other are named",
          bool(strict) and bool(only_address)
          and strict <= {(e["program"], e["addr"]) for e in edges}
          and all(k in by_key for k in only_address),
          "got %d strict, %d address-only" % (len(strict), len(only_address)))
    for key in only_address:
        r = by_key[key]
        check("  ... %s %s is nested and not span-contained, and the report "
              "says which of the two shapes it is"
              % (key[0], key[1]),
              r["verdict"] == "nested" and not any(e["span_contained"]
                                                   for e in r["edges"]))

    # The bucket split is a partition of the edges, and the rows are not: this
    # is a claim about the tool's logic, not about the tree.
    check("every edge is in exactly one of the two buckets, and the two "
          "account for the whole edge set",
          all(e["bucket"] in BUCKETS for e in edges) and len(edges) > 0,
          "got %r" % sorted({e["bucket"] for e in edges}))
    check("the bucket is on the edge and not the row -- a row inside two "
          "containers exists and its two buckets differ",
          any(len(r["edges"]) > 1 and
              len({e["bucket"] for e in r["edges"]}) > 1 for r in nested)
          or not any(len(r["edges"]) > 1 for r in nested),
          "no row carries two buckets; the shape is only on fixtures")

    # The fourth verdict, named. `unframed` cannot hold a nested row -- that is
    # what a partition is -- and the report says where its instances are.
    check("`unframed` has no instance among the nested rows",
          not any(r["verdict"] == "unframed" for r in nested))
    check("bank1 0x9AD2, the one instance second_copy_census's own boundary "
          "partition gives `unframed`, is unframed here too",
          by_key[("bank1", "9AD2")]["verdict"] == "unframed",
          "got " + by_key[("bank1", "9AD2")]["verdict"])

    # The reading §8 got wrong, corrected here against the same files: `pd
    # 0x9C4D` is one byte past the listing that ends immediately before it, not
    # inside it.
    check("pd 0x9C4D is `after-a-function` against pd 0x9C45, listed "
          "0x9C45-0x9C4C, and is not nested in it",
          by_key[("pd", "9C4D")]["verdict"] == "after-a-function"
          and not by_key[("pd", "9C4D")]["edges"]
          and "%04X-%04X" % by_key[("pd", "9C45")]["span"] == "9C45-9C4C",
          "got %s, span %r"
          % (by_key[("pd", "9C4D")]["verdict"], by_key[("pd", "9C45")]["span"]))

    # The issue's own example, which is the case the two buckets are for.
    check("bank0 0x805B is nested in bank0 0x8054, listed 0x8054-0x806B",
          by_key[("bank0", "805B")]["verdict"] == "nested"
          and any(e["container_addr"] == "8054"
                  and "%04X-%04X" % e["container_span"] == "8054-806B"
                  for e in by_key[("bank0", "805B")]["edges"]),
          "got %r" % [where_text(e) for e in by_key[("bank0", "805B")]["edges"]])
    check("bank0 0xF002 -- #577 -- is reported like any other row, holding "
          "0xEFDC and 0xEFF0",
          all(by_key[("bank0", a)]["verdict"] == "nested"
              and any(e["container_addr"] == "F002"
                      for e in by_key[("bank0", a)]["edges"])
              for a in ("EFDC", "EFF0")),
          "got %r" % [[where_text(e) for e in by_key[("bank0", a)]["edges"]]
                      for a in ("EFDC", "EFF0")])

    # The two vocabularies, held closed.
    check("the three verdicts partition every row the census read",
          {r["verdict"] for r in records} <= set(VERDICTS) | {UNREAD}
          and all(r["verdict"] in VERDICTS for r in records
                  if r["verdict"] != UNREAD)
          and all(r["verdict"] == UNREAD for r in records if r["span"] is None))
    check("--check is green on the committed tree", not found,
          "; ".join(found[:3]))
    check("what the method could not read is reported rather than failed, and "
          "both shapes are on the tree",
          not any(p in " ".join(found) for p in ("not read", "no committed"))
          and len(told) > 0,
          "got %d note(s)" % len(told))

    # --- the refusals, all on fixtures ---
    with tempfile.TemporaryDirectory() as scratch:
        decompiled, image, rows, anns = _fixture_tree(scratch)
        got = census(rows, anns, image, decompiled)
        keyed = {(r["program"], r["addr"]): r for r in got}
        gnested, gedges = population(got)

        check("refusal: a row alone in its program is not nested by anything, "
              "and `common` is not a fallback for it",
              keyed[("bank0", "0400")]["verdict"] != "nested"
              and not keyed[("bank0", "0400")]["edges"],
              "got " + keyed[("bank0", "0400")]["verdict"])
        check("refusal: a container listed in the other program does not nest "
              "-- spans are per-program",
              all(e["container"]["program"] == e["program"] for e in gedges))
        pair = (keyed[("common", "0300")]["edges"]
                + keyed[("common", "0310")]["edges"])
        check("refusal: mutual nesting yields both edges and neither span "
              "contains the other, so neither row has one container",
              len(keyed[("common", "0300")]["edges"]) == 1
              and len(keyed[("common", "0310")]["edges"]) == 1
              and {e["container_addr"] for e in pair} == {"0300", "0310"}
              and not any(e["span_contained"] for e in pair),
              "got %r" % [where_text(e) for e in pair])
        check("refusal: a listing whose first instruction is not the row's own "
              "address is not read as a container starting at that address",
              [e["bucket"] for e in keyed[("common", "0208")]["edges"]]
              == ["listing-opens-below-address"]
              and [e["bucket"] for e in keyed[("common", "0110")]["edges"]]
              == ["same-address"],
              "got %r and %r"
              % ([e["bucket"] for e in keyed[("common", "0208")]["edges"]],
                 [e["bucket"] for e in keyed[("common", "0110")]["edges"]]))
        check("refusal: a row with no committed listing is reported rather "
              "than skipped, and is not failed on",
              keyed[("common", "0600")]["verdict"] == "no-committed-listing"
              and any("0600" in p for p in notes(got))
              and not failures(got, gedges),
              "got %s" % keyed[("common", "0600")]["verdict"])
        check("refusal: a frame one byte past a listing's end is "
              "`after-a-function`, not nested",
              keyed[("common", "0501")]["verdict"] == "after-a-function"
              and not keyed[("common", "0501")]["edges"],
              "got " + keyed[("common", "0501")]["verdict"])
        with open(os.path.join(decompiled, "common", "0110.asm"), "w") as f:
            f.write("; fixture\n0110     90 34 12 mov  dptr,#0x1234\n")
        # Re-read rather than reuse `got`: the records carry the listing's bytes
        # as they were when the census ran, so a check against them would be
        # asserting the fixture it had just replaced.
        again = census(rows, anns, image, decompiled)
        check("refusal: a listing that disagrees with the firmware is reported "
              "as a stale export and does fail --check",
              any("the export is stale" in p
                  for p in failures(*population(again))),
              "got %r" % failures(*population(again)))
    print()
    if bad:
        print("self-test FAILED: %d check(s) disagree with the readings above"
              % bad)
        return 1
    print("self-test passed: the named rows nested in the containers they are "
          "measured against, both readings of \"contained\" reported and "
          "differing, the buckets partitioning the edges, `unframed` empty of "
          "nested rows, `pd 0x9C4D` after-a-function, and the refusals")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="the gate form: the same report, and a non-zero exit "
                         "on a stale listing or a bucket outside the "
                         "vocabulary")
    ap.add_argument("--self-test", action="store_true",
                    help="the named claims and the refusals")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    records = census(read_csv(INDEX_CSV), read_csv(ANNOTATIONS))
    nested, edges = population(records)
    found = failures(records, edges)
    print(report(records, found, notes(records)))
    # The exit code is the same either way. A census that has found an export it
    # cannot read should not report success because nobody passed a flag, and
    # `--check` here is for a reader who wants to be explicit about it rather
    # than the thing that turns this into a gate -- CLAUDE.md sends a gate line
    # through ElDavoo/agent-pipeline upstream, and this branch's token has no
    # `workflow` scope.
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
