#!/usr/bin/env python3
"""Label every bucket-C and paged call site in the main EC image with the data
region it lands in, and write that as committed data rather than console output.

`data_regions.py` answers two different questions about a byte offset, and only
one of them is answered for a population anywhere in the tree:

  * *is this offset inside a listed region* -- `region_at()`, which
    `audit_call_targets.py` already prints for a sample of each bucket and
    `bucket_c_codemap.py` already carries as a column over bucket C; and
  * *is this offset on one of that region's entry boundaries* -- a modulo test
    against `stride`, which until now only `--for-offset` computed, for one
    address, on demand.

The second is the sharper one, and it is the one nothing answered at any scale.
`docs/findings/ec-data-regions.md` §"The payoff" argues from it with two named
sites: `0x06952` scores 24 of 24 anchors and sits 71 bytes into a stride-3
region, and `0x00381` scores 15 of 24 and sits 82 bytes into another. Both are
inside a table; neither is on its grid; both are the phantom mechanism -- a
table entry read one byte out of frame. A tool that reports only the first
question cannot tell those from the sites that really are entries, and neither
can a reader of the console tables.

**Two populations in one file, keyed on `file_offset`.** The absolute forms'
bucket C and the 2-byte paged `ajmp`/`acall` family are different scans with
different columns and different reasons to exist, but the two `file_offset` sets
are disjoint by construction -- a byte in `(0x02, 0x12)` has low five bits
`0x02`/`0x12`, neither of which is a paged opcode -- so `file_offset` alone is a
key with no tie to break and `family` is a column rather than part of one. The
file is sorted by `file_offset` alone, which is what lets two branches that both
regenerate it produce the same bytes and merge in content rather than in prose.

**`bank-call-targets.csv` and its siblings are not touched.** This is the
sibling `audit_call_targets.py`'s `write_paged_csv()` docstring names ("A
sibling of `write_csv()` rather than more columns on it"), one step further
along: one more column on that file needs `build_ec_decompile.py`'s
`CALL_TARGET_COLUMNS` edited, and that list's `--self-test` runs in the cheap
gate, so the column would turn a gate assertion red for an unrelated cause --
the cheapest way to get a gate switched off. `ec/tools/test_data_regions.py`
holds that sibling contract from its own side and is not edited; this file's
suite asserts it from this side.

**`entry_aligned` is three-valued, and the rule is keyed on `confidence`, not
on `shape`.** A `read-by-hand` region has a uniform entry grid that a human
read, so `yes`/`no` answers a real question about a real grid. An `inferred`
region had its extent extended by pattern, and `common-0656-address-table`'s
`note` **used to** claim the stride was not uniform across it -- 121 of its 176
words are `0x032F + 3k` and the rest are not on that progression. That claim was
wrong: reading the words edge by edge (issue #1144) shows the stride *is*
uniform and the content is mixed, the span being a directory of five `ljmp`
tables plus 36 ordinary code addresses
(`docs/findings/0656-directory-words.md`). Nothing here moves, because the rule
never rested on the note -- an extent chosen by pattern does not claim a grid, so
a modulo test there answers a question the file does not pose, and the cell is
**empty**. So is `inferred-unchecked`'s, which is the tier `--check` cannot
reach and is therefore not a claim at all. Keying on `confidence` rather than
on `shape`
because it is a field the source of truth already carries, that `load()`
already validates against a closed vocabulary and `unchecked()` already filters
by, and that a future entry reaches with no edit here; a shape-keyed rule would
hardcode a list into this tool and need editing whenever a shape is added, which
is the shape-vocabulary coupling `test_data_regions.py` exists to prevent.

The empty cell is therefore *not* the same absence as `in_data_region=no`, and
`in_data_region` is in the header for that reason: `no` means no region was
found and the question does not arise; `yes` with an empty `entry_aligned` means
a region was found and the question is undefined *for it*, with
`region_confidence` naming the reason in the row itself. `--check` refuses
either conflation.

**The honest boundary of that rule.** A future `read-by-hand` region with a
genuinely non-uniform grid would get a `no` where the right answer is undefined.
That is the weaker of the two possible failures -- the reverse would silently
assert an alignment the file does not claim -- and `--check` re-deriving the
stride from the image is what catches such an entry when it is added.

**Annotate, never suppress.** Every site is a row, whether or not it is inside a
listed region; the counts in `bank-call-audit.md` rest on exactly the rows they
always did. `in_data_region=no` never means "a call", `entry_aligned=no` never
means "a phantom", and a region being listed is not proof its site is one.
Nothing here is a behavioural claim, no `status:` in `registers.yaml` moves, and
nothing in this tool was observed on hardware: the two inputs are committed
files. A zero anywhere in its output is "not found by this method", never
"absent" -- `docs/findings.md` §4c, and this file's entire subject is one
method's blind spots.

The relative-branch family is the obvious third population and is deliberately
absent: the issue named these two, `bank-relative-branch-targets.csv` is already
a third sibling, and nothing about the argument above is specific to it. It is a
one-line extension of the same walk when it is wanted.

Usage:
    python3 bank_call_regions.py ../firmware/GMxMGxx_11.800 --write
    python3 bank_call_regions.py ../firmware/GMxMGxx_11.800 --check
    python3 bank_call_regions.py ../firmware/GMxMGxx_11.800 --self-test
    python3 bank_call_regions.py ../firmware/GMxMGxx_11.800 --csv
"""
import argparse
import csv
import difflib
import io
import os
import sys

from audit_call_targets import paged_survey, survey
from data_regions import load as load_data_regions, region_at
from trace_xdata_refs import PD_MARKER

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
DEFAULT_FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")
DEFAULT_YAML = os.path.join(EC, "annotations", "data-regions.yaml")
DEFAULT_CSV = os.path.join(EC, "annotations", "bank-call-regions.csv")

# The two censuses this file joins, and the column that picks the population out
# of each. Named rather than derived so `--check`'s join and the self-test that
# transcribes its headline are reading the same two names.
BUCKET_C_CENSUS = "bank-call-targets.csv"
PAGED_CENSUS = "bank-paged-call-targets.csv"

FAMILIES = ("bucket-c", "paged")

# The one `confidence` tier whose entry grid is a claim the modulo test may be
# asked about. Named from `data_regions.CONFIDENCES` rather than redefined, and
# an unknown tier is refused at the row rather than treated as one of these.
ALIGNABLE = "read-by-hand"

# Columns, in the order they are written. The first nine are the issue's
# "at minimum" list; `region_stride` and `entry_offset` are here so
# `entry_aligned` is re-derivable from the row alone
# (`entry_offset % region_stride == 0`) rather than being a value a reader has
# to take on trust, which is the whole of "rather than leaving it implicit".
COLUMNS = ("file_offset", "family", "region", "runtime", "opcode", "target",
           "anchored", "frame_onto", "frame_over", "in_data_region",
           "region_name", "region_shape", "region_confidence",
           "region_stride", "entry_offset", "entry_aligned")

# The comment block written above the header. A committed artefact needs to
# carry its own provenance and its own meaning without a per-row column for
# either, and this is the file a reader opens to find out what `entry_aligned`
# means -- the same reasoning `call_graph_gaps.py`'s `HEADER_NOTE` gives, whose
# `call-graph-unreached.csv` and `call-graph-unresolved.csv` are the two
# committed tables here already carrying a block like this. **`csv.DictReader`
# does not skip it**: run on the whole file it reads the first `#` line as the
# fieldnames and every later `#` line as a row, which is a parse that succeeds
# and answers nothing. So a consumer has to drop the `#` lines first, which is
# what `parse()` below and `call_graph_gaps.py`'s `read_rows()` do.
HEADER_NOTE = """\
# bank-call-regions.csv -- generated by ec/tools/bank_call_regions.py; do not
# edit by hand. Re-derive with `python3 ec/tools/bank_call_regions.py
# ec/firmware/GMxMGxx_11.800 --write`, and gate a change with the same command
# plus `--check`.
# Two populations in one file, keyed on `file_offset` alone and sorted by it:
# `family` is `bucket-c` for a common-area `ljmp`/`lcall` to a banked address,
# and `paged` for a 2-byte `ajmp`/`acall`. The two sets are disjoint by
# construction, so one sort key has no tie to break.
#
# `in_data_region` is `no` when no span in ec/annotations/data-regions.yaml
# contains the site, and that NEVER means "a call" -- it means this method did
# not place the row. `region_name`/`region_shape`/`region_confidence`/
# `region_stride`/`entry_offset` are empty exactly when it is `no`.
#
# `entry_aligned` is THREE-valued, and which of the three a row gets is decided
# by `region_confidence`:
#   yes / no   the region is `read-by-hand`, so its `region_stride` is a claim
#              about a uniform entry grid, and the cell says whether this site
#              is on that grid -- `entry_offset % region_stride == 0`, both
#              columns being here so the test is checkable from the row alone.
#   (empty)    the region is `inferred` (its extent was extended by pattern, so
#              the grid is not a claim -- common-0656-address-table's `note`
#              used to claim its stride was not uniform; reading its words one
#              at a time (issue #1144) shows the stride IS uniform and the
#              content is mixed) or `inferred-unchecked` (the tier --check
#              cannot reach). The question is UNDEFINED there, not false, and
#              `region_confidence` says which in the row itself.
# An empty cell is therefore not the same absence as `in_data_region=no`:
# `no` means the question does not arise, `yes` with an empty `entry_aligned`
# means a region was found and the question is undefined for it.
# For a `repeat-bytes` region the stride is the pattern LENGTH, so "aligned"
# there means on a pattern boundary rather than on a field boundary. The rule
# and its boundary are argued in
# docs/findings/bank-call-regions-csv.md.
#
# Nothing here is a behavioural claim. No register was read back, no EC was
# opened, no capture was read: both inputs are committed files. No `status:` in
# registers.yaml moves -- these are addresses in a code image, not XDATA
# registers -- and nothing here is evidence about the laptop. A region being
# listed is not proof its site is a table entry; see
# docs/findings/ec-data-regions.md "Limits" and docs/findings.md 4c.
#
# This file is a SIBLING of annotations/bank-call-targets.csv and
# annotations/bank-paged-call-targets.csv, not another column on either.
# Those two are unchanged, as is build_ec_decompile.py's CALL_TARGET_COLUMNS;
# docs/findings/ec-data-regions.md "Reading the column in the tools" gives the
# reason, and the argument for the committed sibling is in
# docs/findings/bank-call-regions-csv.md.
"""


def refuse(reason: str) -> None:
    """One exit for every refusal here, so `--check` and `--self-test` agree.

    Raised rather than returned because every case in this tool is a case where
    rendering the row anyway would be the worse answer: an unknown region name
    or an offset outside the image is a claim the image cannot support, and a
    `yes` with no name is the conflation the three-valued cell exists to keep
    apart. `--self-test` counts the refusals it provoked and `--check` applies
    the same function to every committed row.
    """
    raise SystemExit(f"error: {reason}")


def entry_offset(off: int, region):
    """`off` counted from its region's first byte, or None when there is none."""
    return None if region is None else off - region["file_lo"]


def entry_aligned(off: int, region) -> str:
    """`yes`, `no`, or `""` -- and the refusal that is not one of the three.

    The rule, in one place so the CSV writer, `--check` and the self-test cannot
    answer differently: a `read-by-hand` region has a grid a human read, so the
    modulo test answers a real question; any other tier does not claim a grid, so
    the cell is empty rather than false. A null stride inside the aligning tier
    is refused instead of divided by -- that is `inferred-unchecked` reaching the
    row level, the tier `--check` reports rather than passes.
    """
    if region is None:
        return ""            # no region found; the question does not arise
    if region["confidence"] != ALIGNABLE:
        return ""            # the grid is not a claim for this tier
    if region["stride"] is None:
        refuse(f"{region['name']} is {ALIGNABLE} with a null stride, so "
               f"0x{off:05X} cannot be placed on an entry boundary")
    return "yes" if entry_offset(off, region) % region["stride"] == 0 else "no"


def validate(row: dict, regions, image_len: int) -> None:
    """The row-level refusals. Raises rather than returns.

    A row that reaches this has been parsed out of a file, so what is worth
    refusing is the ways a row can assert something the image or the YAML does
    not support: an offset that is not a byte of this image, a region name
    nothing re-derives, a cell outside its closed vocabulary, and the two
    directions of the `in_data_region`/`region_name` conflation. The fifth
    refusal -- an alignment computed against a null stride -- lives in
    `entry_aligned()`, because it is the one that needs a region rather than a
    row. Each is checked where it can be, rather than trusting the writer:
    `--check` runs this over every committed row, and the self-test runs it over
    mutations of one.
    """
    off = offset_of(row)
    if off < 0 or off >= image_len:
        refuse(f"file_offset {row['file_offset']} is outside the {image_len}-byte"
               f" image; a site is a byte of this image or it is not a site")

    if row["family"] not in FAMILIES:
        refuse(f"family is {row['family']!r}, which is neither "
               f"{' nor '.join(repr(f) for f in FAMILIES)}. The join in "
               f"`--check` reads this cell to decide which census to compare "
               f"against, so a third value has no population to belong to")

    named = row["region_name"]
    if named and named not in {r["name"] for r in regions}:
        refuse(f"{named!r} is not a region in data-regions.yaml, so this row "
               f"names a span nothing re-derives")
    # Compared against the vocabulary rather than for truthiness: `"no"` is a
    # truthy string, and a bare `if row["in_data_region"]` reads every row of the
    # file as a `yes`. The vocabulary is closed for the same reason
    # `data_regions.load()` closes `shape` and `confidence` -- a cell holding a
    # third value is a row whose meaning nobody can say out loud.
    if row["in_data_region"] not in ("yes", "no"):
        refuse(f"in_data_region is {row['in_data_region']!r}, which is neither "
               f"'yes' nor 'no'")
    if row["in_data_region"] == "yes" and not named:
        refuse(f"0x{off:05X} is marked in_data_region=yes with an empty "
               f"region_name. The two answer different questions and the cell "
               f"is meaningless without the other half")
    if row["in_data_region"] == "no" and named:
        refuse(f"0x{off:05X} is marked in_data_region=no but names "
               f"{named!r}; a named region is a found one")


def offset_of(row: dict) -> int:
    """A row's `file_offset` as an int, or -1 when the cell is not one.

    `-1` rather than a raise so the caller's own range check is what refuses it:
    a `file_offset` that does not parse is the outside-the-image case, and
    routing it through one refusal rather than two keeps that a single answer.
    """
    try:
        return int(str(row["file_offset"]), 16)
    except (TypeError, ValueError):
        return -1


def rows(d: bytes, regions):
    """Every labelled site as a row dict, sorted by `file_offset`.

    Both populations come out of `audit_call_targets.py`'s own surveys rather
    than a second enumeration here: those are the censuses whose figures every
    other file quotes, and a walk written twice is a second answer to their
    question. Bucket C is the `survey()` rows whose bucket is `C`; the paged
    family is `paged_survey()` whole, which has no bucket column because a paged
    target is inside the caller's own page.
    """
    out = []
    for family, population in (("bucket-c",
                                [r for r in survey(d)[0] if r["bucket"] == "C"]),
                               ("paged", paged_survey(d)[0])):
        for r in population:
            off = r["file_offset"]
            region = region_at(regions, off)
            # A stride is rendered only when there is one. `str(None)` is the
            # string "None", which would be a cell holding a Python value in a
            # file whose every other empty cell is empty -- and no region
            # carries a null stride today, so nothing would catch it but a
            # future `inferred-unchecked` entry. `entry_aligned()` refuses that
            # combination in the aligning tier; this is the other half.
            stride = region["stride"] if region else None
            out.append({
                "file_offset": f"0x{off:05X}",
                "family": family,
                "region": r["region"],
                "runtime": f"0x{r['runtime']:04X}",
                "opcode": r["opcode"],
                "target": f"0x{r['target']:04X}",
                "anchored": "yes" if r["anchored"] else "no",
                "frame_onto": str(r["frame_onto"]),
                "frame_over": str(r["frame_over"]),
                "in_data_region": "yes" if region else "no",
                "region_name": region["name"] if region else "",
                "region_shape": region["shape"] if region else "",
                "region_confidence": region["confidence"] if region else "",
                "region_stride": "" if stride is None else str(stride),
                "entry_offset": ("" if region is None
                                 else str(entry_offset(off, region))),
                "entry_aligned": entry_aligned(off, region),
            })
    out.sort(key=lambda r: r["file_offset"])
    return out


def table(d: bytes, regions) -> str:
    """The committed bytes, as one string.

    Written to a string rather than straight to a file so `--check` diffs it
    against the committed copy and `--csv` hands it to stdout, and so the
    header comment block and the table are one value: a check that re-derived
    only the rows could not tell a dropped header from a reworded one.
    """
    buf = io.StringIO()
    buf.write(HEADER_NOTE)
    w = csv.DictWriter(buf, fieldnames=list(COLUMNS), lineterminator="\n")
    w.writeheader()
    w.writerows(rows(d, regions))
    return buf.getvalue()


def parse(text: str, columns):
    """The committed file as `(offset, row)` pairs, past the `#` header block.

    The comment lines are dropped before `DictReader` rather than after: run on
    the whole file it would read the block as the header and produce one column
    called `# bank-call-regions.csv -- generated by ...`, which is a parse that
    succeeds and answers nothing -- `call_graph_gaps.py`'s `read_rows()` gives
    the same reason. The `fieldnames` check is not decoration: without it a
    truncated file parses as a short row and the diff below reports every cell of
    it rather than naming the missing column.
    """
    reader = csv.DictReader([ln for ln in text.splitlines(True)
                             if not ln.startswith("#")])
    if tuple(reader.fieldnames or ()) != tuple(columns):
        refuse(f"the committed file's header is "
               f"{list(reader.fieldnames or [])}, not {list(columns)}")
    return [(int(r["file_offset"], 16), r) for r in reader]


def census_offsets(path: str, bucket: str = None):
    """The `file_offset`s in a committed census CSV, one set.

    Read from the committed file rather than recomputed, which is what makes the
    join in `check_join()` a *relation* between two committed artefacts rather
    than a second census: if `bank-call-targets.csv` moves, this moves with it
    and the join goes red, which is the property a count of the tree cannot have.
    """
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if bucket is not None:
        rows = [r for r in rows if r["bucket"] == bucket]
    return {int(r["file_offset"], 16) for r in rows}


def check_join(text: str) -> int:
    """Both `file_offset` sets against the two censuses they are drawn from.

    A join, deliberately, rather than a count. The headline figures are
    transcriptions of `bank-call-audit.md`'s own headline and live in
    `--self-test`
    alone; a figure in `--check` would be a value every census change had to
    edit, and this file would be red for a cause that has nothing to do with it.

    A `family` outside the two is reported here as well as refused by
    `validate()`: this function is callable on its own, and a row it cannot
    place has to be said so rather than raising out of the join.
    """
    got = {family: set() for family in FAMILIES}
    problems = 0
    for off, row in parse(text, COLUMNS):
        family = row["family"]
        if family not in got:
            problems += 1
            print(f"error: 0x{off:05X} has family {family!r}, which is in "
                  f"neither census this file joins against", file=sys.stderr)
            continue
        got[family].add(off)
    for family, census, bucket in ((FAMILIES[0], BUCKET_C_CENSUS, "C"),
                                   (FAMILIES[1], PAGED_CENSUS, None)):
        want = census_offsets(os.path.join(EC, "annotations", census), bucket)
        if got[family] == want:
            continue
        problems += 1
        for label, side in (("only here", got[family] - want),
                            ("only in " + census, want - got[family])):
            shown = sorted(side)[:8]
            print(f"error: {family} site(s) {label}: "
                  + (", ".join(f"0x{o:05X}" for o in shown)
                     + ("" if len(side) <= len(shown) else
                        f", and {len(side) - len(shown)} more")))
    return problems


def check(d: bytes, regions, path: str, firmware: str = "") -> int:
    """Re-derive every cell of every row, and validate every committed row.

    Two halves, because they catch different mistakes. The diff catches a file
    the image and the YAML do not produce -- a stale cell, a dropped row, a
    re-ordered one. The validation catches a file that is *self-consistent* and
    still wrong: a row naming a region nothing re-derives, an offset outside the
    image, or the `in_data_region`/`region_name` conflation the three-valued
    `entry_aligned` depends on being kept apart.
    """
    if not os.path.exists(path):
        print(f"error: {path} does not exist. --check compares; it never "
              "creates. Generate the table with --write and commit it.",
              file=sys.stderr)
        return 1

    text = open(path, newline="").read()
    problems = 0

    # The diff names the first mismatching offset and both values rather than
    # printing a count: a count tells a reader how far off it is, and the offset
    # tells them where to look.
    want = table(d, regions).splitlines(True)
    got = text.splitlines(True)
    if want != got:
        # Named by `file_offset` rather than by line number: the file is sorted
        # by that column, so it is the key a reader looks the row up by, and it
        # survives the header block being rewrapped. A dropped or re-ordered row
        # names the offset that moved rather than the line it moved to.
        first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b),
                     min(len(got), len(want)))
        named = []
        for side in (got, want):
            cells = (next(csv.reader([side[first]]), [])
                     if first < len(side) else [])
            named.append(cells[0] if cells else "(no such row)")
        shown = (lambda side: side[first].strip() if first < len(side)
                 else "(absent)")
        print(f"error: the committed table is not what this run derives from "
              f"the image, first differing at {named[0]} (committed) against "
              f"{named[1]} (re-derived):\n"
              f"  committed   {shown(got)}\n"
              f"  re-derived  {shown(want)}",
              file=sys.stderr)
        sys.stdout.writelines(list(difflib.unified_diff(
            got, want, fromfile=f"committed {path}",
            tofile="regenerated"))[:40])
        problems += 1

    # Every committed row, validated rather than the regenerated ones: a row the
    # writer would refuse is a row `--write` cannot produce, and `--check` has to
    # be able to say so about a file it did not write.
    for off, row in parse(text, COLUMNS):
        try:
            validate(row, regions, len(d))
        except SystemExit as exc:
            print(f"  0x{off:05X}: {exc}", file=sys.stderr)
            problems += 1

    problems += check_join(text)

    if not problems:
        print(f"bank-call-regions.csv re-derived from "
              f"{os.path.basename(firmware) if firmware else 'the image'}: every "
              f"cell of every row matches it and the YAML, and both file_offset "
              f"sets match the two censuses they are drawn from")
    return 1 if problems else 0


# The transcriptions of `bank-call-audit.md`'s headline, on
# `bucket_c_codemap.py`'s stated ground: they are a committed document's figure,
# not a count of the tree, and this is the one mode that may carry them. Nothing
# in `--check` asserts a figure.
HEADLINE = (140, 83)

# The paged census's own total, same ground: `bank-call-audit.md`'s count of
# `ajmp`/`acall` sites over the same three regions `paged_survey()` walks.
PAGED_HEADLINE = 3481

# The oracle, transcribed from `docs/findings/ec-data-regions.md` §"The payoff"
# rather than from this tool's own output: a tool that graded its map against
# itself would pass whatever the map said. As `(offset, region_name,
# entry_aligned)`, with `""` for an empty cell and `None` for a region_name on a
# site inside no region.
ORACLE = [
    (0x055DC, "common-055a8-be-words", "yes"),
    (0x00381, "common-032f-ljmp-table", "no"),
    (0x06952, "common-690b-ff-triples", "no"),
    (0x06E83, "common-6e7d-be-words", "yes"),
    # The 24-of-24 site no region covers: `ec-data-regions.md` §4, and the
    # reason an empty `entry_aligned` on a `no` row means the question did not
    # arise rather than that the site is off a grid.
    (0x021C6, None, ""),
    # The `inferred` region, where the cell is empty for the other reason: a
    # region was found and the grid is not a claim for it.
    (0x00686, "common-0656-address-table", ""),
]

# The two questions the whole file exists to keep apart, stated as the pairs
# `docs/findings/ec-data-regions.md` argues from: 0x06952 and 0x055DC are both
# inside a region, and only one of them is on its grid.
INSIDE_BUT_OFF = (0x06952, 0x00381)
INSIDE_AND_ON = (0x055DC, 0x06E83)


def self_test(d: bytes, regions) -> int:
    """The refusals, each run with the mutation in place, plus the oracle.

    A check that has quietly stopped rejecting everything looks exactly like a
    check that is working, so each refusal here is provoked rather than asserted
    to exist, and the oracle is transcribed from a document rather than from this
    tool's own map.
    """
    bad = 0

    def expect(label, ok):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}")

    def refuses(mutated):
        """Does `validate()` reject this row? Every call below is a mutation of
        `good`, so the helper takes the mutation rather than a row to compare
        against -- there is no unmutated case here to pass."""
        try:
            validate(mutated, regions, len(d))
        except SystemExit:
            return True
        return False

    print("bank_call_regions.py --self-test")

    built = {int(r["file_offset"], 16): r for r in rows(d, regions)}
    # A site that is inside a region, so the refusals below have a row whose
    # `in_data_region`/`region_name` pair is right to begin with. 0x055DC is
    # the findings file's own worked example and it is a bucket-C site.
    good = built[0x055DC]

    # --- the refusals -----------------------------------------------------
    expect("an unknown region name is refused",
           refuses(dict(good, region_name="common-ffff-nonesuch")))
    expect("a file_offset past the end of the image is refused",
           refuses(dict(good, file_offset=f"0x{len(d):05X}")))
    expect("a negative file_offset is refused",
           refuses(dict(good, file_offset="-1")))
    expect("in_data_region=yes with an empty region_name is refused",
           refuses(dict(good, region_name="")))
    expect("in_data_region=no with a region_name is refused",
           refuses(dict(good, in_data_region="no")))
    expect("an in_data_region outside yes/no is refused",
           refuses(dict(good, in_data_region="maybe")))
    expect("a family outside the two populations is refused",
           refuses(dict(good, family="relative")))
    expect("a row computing entry_aligned against a null stride is refused",
           _refuses_null_stride(regions))

    # --- the oracle, from the findings file rather than from this map -----
    for off, want_name, want_aligned in ORACLE:
        row = built.get(off)
        expect(f"0x{off:05X} is "
               + (f"inside {want_name}" if want_name
                  else "outside every listed region")
               + f" and entry_aligned is {want_aligned or '(empty)'}",
               row is not None
               and row["region_name"] == (want_name or "")
               and row["entry_aligned"] == want_aligned)

    # --- the distinction the file exists to carry ------------------------
    inside = {off for off, row in built.items() if row["in_data_region"] == "yes"}
    expect(f"every site the findings file calls entry-aligned is inside a "
           f"region ({', '.join('0x%05X' % o for o in INSIDE_AND_ON)})",
           all(o in inside for o in INSIDE_AND_ON))
    expect(f"and every site it calls not entry-aligned is inside one too "
           f"({', '.join('0x%05X' % o for o in INSIDE_BUT_OFF)}) -- in a region "
           f"and on its grid are two questions, and a file carrying only the "
           f"first would answer both alike",
           all(o in inside for o in INSIDE_BUT_OFF))
    expect("`entry_aligned` is populated exactly where a region was found and "
           "its grid is a claim, so an empty cell is only ever a region that "
           "does not pose the question",
           all((row["entry_aligned"] != "")
               == (row["in_data_region"] == "yes"
                   and row["region_confidence"] == ALIGNABLE)
               for row in built.values()))

    # --- the transcriptions of bank-call-audit.md's headline ------------
    bucket_c = [o for o, row in built.items() if row["family"] == "bucket-c"]
    paged = [o for o, row in built.items() if row["family"] == "paged"]
    anchored = sum(1 for o in bucket_c if built[o]["anchored"] == "yes")
    expect(f"bucket C still holds {HEADLINE[0]} site(s), {HEADLINE[1]} anchored",
           (len(bucket_c), anchored) == HEADLINE)
    expect(f"the paged family still holds {PAGED_HEADLINE} site(s)",
           len(paged) == PAGED_HEADLINE)

    # --- the committed file passes its own check --------------------------
    expect("the committed file reproduces byte for byte from the image",
           table(d, regions) == open(DEFAULT_CSV).read())
    expect("and its file_offset set joins against both censuses",
           check_join(open(DEFAULT_CSV).read()) == 0)

    print(f"{'self-test passed' if not bad else f'self-test FAILED: {bad}'}")
    return 1 if bad else 0


def _refuses_null_stride(regions) -> bool:
    """`entry_aligned()` on a `read-by-hand` region whose stride is null.

    Written out rather than inlined in the `expect(...)` above because that call
    is an asserting call, and `check_doc_figure_pins.py` reads every int constant
    inside one as a pin for a figure in some document.
    """
    region = next(r for r in regions if r["confidence"] == ALIGNABLE)
    try:
        entry_aligned(region["file_lo"], dict(region, stride=None))
    except SystemExit:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: the committed one)")
    ap.add_argument("--regions", default=DEFAULT_YAML,
                    help="data-regions.yaml to read (default: the one beside "
                         "this tool)")
    ap.add_argument("--csv-path", default=DEFAULT_CSV,
                    help="the committed table --check compares against and "
                         "--write writes")
    ap.add_argument("--write", action="store_true",
                    help="regenerate the committed table from the image")
    ap.add_argument("--check", action="store_true",
                    help="re-derive every cell and fail on any mismatch; never "
                         "writes, and a missing file is a failure rather than "
                         "something to create")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusals, each with its mutation in place, and "
                         "the oracle from ec-data-regions.md")
    ap.add_argument("--csv", action="store_true",
                    help="the table on stdout rather than to the committed "
                         "file")
    args = ap.parse_args()

    if sum((args.write, args.check, args.self_test, args.csv)) > 1:
        ap.error("--write, --check, --self-test and --csv are four different "
                 "claims about this image; run them separately")

    regions = load_data_regions(args.regions)
    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1

    path = args.csv_path if os.path.isabs(args.csv_path) else os.path.join(
        HERE, args.csv_path)

    if args.self_test:
        return self_test(d, regions)
    if args.check:
        return check(d, regions, path, args.firmware)
    if args.csv:
        sys.stdout.write(table(d, regions))
        return 0
    if args.write:
        with open(path, "w", newline="") as fh:
            fh.write(table(d, regions))
        print(f"wrote {path}")
        return 0

    ap.error("give --write, --check, --self-test or --csv")
    return 1


if __name__ == "__main__":
    sys.exit(main())
