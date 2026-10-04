#!/usr/bin/env python3
"""Which of the PD image's `0x260`-record bases this machine's ECMG read path
can reach at all, derived rather than asserted, and checkable against the
document that says so.

`ec/annotations/pd-index-geometry.md` §3.2 puts the record stride at `0x260`
for the `0x0400`-`0x04A8` arrays, and the `base_list` column of
`ec/annotations/pd-base-strides.csv` is every base the term decode resolved,
one row per stride. Neither file says which of those bytes a *live* read on
this machine can return: that is a property of the host's memory-mapped ECMG
window, not of the EC or of the PD image.

The window is `ec_timer_capture.HOST_WINDOW`, taken from the page census of the
2026-09-24 run on the GM7MG7P itself
(`docs/hardware-tests/xdata-06c2-06db-sweep.md` §3, committed at
`evidence/ec-watch/2026-09-24-host-window-page-census.txt`): `0x0000`-`0x07FF`
and `0x0C00`-`0x0FFF` hold data, and every byte of `0x0800`-`0x0BFF` and of
`0x1000`-`0xFFFF` reads `0xFF` whatever the EC holds. That is *consistent
with* the window not mapping those pages; it is not a statement about what the
EC holds there, and it is the same reading `docs/findings.md` §4g already takes
for `0x0A40`-`0x0A5F`.

**What "reachable" means here, precisely, and in one place.** `sampleable()`
is the definition: an address is sampleable when it is inside the window *and*
not on the fan page `0x0460`-`0x046F`, which is the same pair of conditions
`ec_timer_capture.check_addrs` refuses on before it reads anything. Everything
below is arithmetic on that one predicate, so "reachable" cannot mean "inside
the window" in one place and "an operator can actually put this in `--addrs`"
in another -- which is the way a table comes to report a record as covered when
16 of its 608 bytes were never sampled. The fan page is a carve-out inside the
window and it sits inside the `0x0400`-`0x04A8` block the procedure samples, so
a count that ignored it would be a figure no command in the procedure produces.

Both derived figures use it, at two strengths. A base is **readable** at slot
`n` when `base + n * RECORD_STRIDE` is itself sampleable; that is a claim about
one address and is what the per-stride split is. A record is **covered** only
when every one of its `0x260` bytes is, and `reachable_bytes` reports how far
it gets, so a base whose slot-0 record is cut by the fan page is reported as
partly reachable rather than as covered. A run that samples a record's first
bytes and reports the record as covered is overclaiming, so
`grade_pd_index_block.py` prints the reachable length next to every address
rather than the stride it belongs to.

Offline: it opens no capture and no EC, and it reads two committed files. It
is a pure function of them, which is what lets `--check` hold a *document* to
what the tree derives now -- the failure mode `CLAUDE.md` names twice, where a
prose figure of a derived table is stale at the next merge that moves it.

Usage:
  pd_index_block_readability.py                 the per-stride split table
  pd_index_block_readability.py --slots         the same, plus per-slot reach
  pd_index_block_readability.py --table         the markdown table, for a doc
  pd_index_block_readability.py --check DOC     is DOC's table the derivation?
  pd_index_block_readability.py --self-test     known answers, no arguments
"""

import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ec_timer_capture import (FAN_PAGE, HOST_WINDOW, check_addrs,   # noqa: E402
                              in_window)

# The stride `pd-index-geometry.md` §3.2 collapses the two decoded terms into,
# restated here rather than imported: that file keeps no module for it, and a
# number this tool's output is read against belongs where its derivation is
# cited.
RECORD_STRIDE = 0x260

# **Which families the record stride is a claim about.** §7.4 says it outright:
# "not one site with a `0x5E`, `0x77`, `0x17`, `0x67` or `0x04` stride also
# applies a `0x200×` term", and §7.2's census agrees -- only `0x60` and `0x1F`
# resolve one. So `0x260` is the record stride of those two and nothing here
# may place a `0x5E` base at `base + 0x260`, which would be arithmetic dressed
# as a layout claim about a family the geometry explicitly excludes.
#
# That is why `PAGED_STRIDES` is a list and not a heuristic: `0x260` reaching
# `0x0DA7` for a `0x5E` base is true of the addition and says nothing about
# where that array's second record is, and printing it beside the `0x60` rows
# would let a reader take both as the same kind of statement.
PAGED_STRIDES = ("0x60", "0x1F")

STRIDES_CSV = os.path.join(HERE, "..", "annotations", "pd-base-strides.csv")

# `unresolved` is not a stride: it is the census's own bucket for sites the term
# decode does not resolve to one, and it holds every address in the low run. It
# is carried through `--check` so a document that lists it is compared against
# the same rows the CSV has, but it is never reported as a record family --
# there is no stride to place its bases at.
UNRESOLVED = "unresolved"

# How many slots past the base to report. Slot 0 is the array the bases name;
# slots 1 and 2 are what the window leaves of the next indices, and slot 2 is
# where the `0x60` family runs out of window entirely -- which is the fact the
# procedure's two-index arm rests on, so it is printed rather than asserted in
# prose.
SLOTS = 3


def load_rows(path=STRIDES_CSV):
    """Every CSV row, as dicts, in file order."""
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def load_strides(path=STRIDES_CSV):
    """`[(stride, [base, ...])]` for every resolved stride, in CSV row order.

    The CSV's own `bases` column is not read: it is a count this tool derives
    from `base_list` beside it, and a count both would have to agree about.
    """
    out = []
    for row in load_rows(path):
        bases = [int(tok, 16) for tok in row["base_list"].split()]
        out.append((row["stride"], bases))
    return out


def paged_sites(stride, path=STRIDES_CSV):
    """The CSV's `sites_with_page_term` for this stride.

    The column is the census's own count of sites applying a `0x200×` term,
    which is what makes a `0x260` record stride available for the family at
    all (§3.2, §7.2). Reading it rather than restating the family list is what
    lets the self-test hold `PAGED_STRIDES` to the committed data.
    """
    for row in load_rows(path):
        if row["stride"] == stride:
            return int(row["sites_with_page_term"])
    raise KeyError(f"{stride} is not a row in {os.path.basename(path)}")


def slot_start(base, slot, stride=RECORD_STRIDE):
    """The address of slot `slot` of the record at `base`."""
    return base + slot * stride


def sampleable(addr):
    """Whether `ec_timer_capture.py` will read `addr` without refusing it.

    The window and the fan page, and nothing else: these are the two conditions
    `ec_timer_capture.check_addrs` refuses on, imported rather than restated so
    that "reachable" here cannot drift from "sampleable" there. The fan page is
    not a boundary an operator can argue past -- `check_addrs` refuses it before
    `/dev/mem` is opened, and an address it refuses is one no capture can hold.
    """
    return in_window(addr) and addr not in FAN_PAGE


def readable_at(base, slot, stride=RECORD_STRIDE):
    """Whether slot `slot` of the record at `base` begins at a sampleable byte.

    A claim about the first byte alone, which is the weakest thing this host can
    be asked and the only one the split table needs. It is `sampleable` rather
    than `in_window` because a record starting *on* the fan page is not readable
    by a capture either; no committed base sits there, so the split is unchanged
    today and the distinction is the tool's rather than the table's.
    """
    return sampleable(slot_start(base, slot, stride))


def _walk_end(base, slot, stride=RECORD_STRIDE):
    """The offset at which a sweep over this record stops leaving the window.

    Stated as its own value so the self-test can express what a record counts
    without restating the walk, and so the two cannot come to mean different
    things -- a record beginning outside the window stops at offset 0 and
    contributes nothing, which is the case a whole-record comparison gets wrong.
    """
    start = slot_start(base, slot, stride)
    n = 0
    while n < stride and in_window(start + n):
        n += 1
    return start + n


def reachable_addrs(base, slot, stride=RECORD_STRIDE):
    """The bytes of slot `slot` a capture can actually sample, in order.

    Stopped at the first byte outside the window, so a record that runs off the
    end of a window and would later re-enter it -- which `0x0000`-`0x07FF`
    followed by `0x0C00`-`0x0FFF` makes possible at a large index -- reports the
    bytes a sequential `ec_timer_capture.py` sweep would actually walk through,
    not the bytes that exist somewhere in the mapping. The fan page is skipped
    rather than treated as a stopping point, because it is a hole inside the
    window rather than its edge: `0x0400`-`0x04A8` contains it, and a sweep
    over that block reads `0x0470`-`0x065F` after the hole as readily as
    `0x0400`-`0x045F` before it.

    Returning the addresses rather than a count is what keeps this honest, and
    it is why `grade_pd_index_block.slot_index` places exactly these bytes: a
    count alone would let the tail of a record be placed from the wrong offset
    once a hole had been skipped over.
    """
    start = slot_start(base, slot, stride)
    return [a for a in range(start, _walk_end(base, slot, stride))
            if sampleable(a)]


def reachable_bytes(base, slot, stride=RECORD_STRIDE):
    """Bytes of slot `slot` a capture can sample, counting up from its first.

    The length of `reachable_addrs`, so the table, the grader's per-address
    note and the address list `--addrs` takes are all one figure: the fan page
    comes out of it exactly as `check_addrs` takes it out of the command, and a
    record reported as covered is one every byte of which can be sampled.
    """
    return len(reachable_addrs(base, slot, stride))


def split(strides=None):
    """Per stride: the bases, and how many are readable at each slot.

    Returned as `{stride: {...}}` with `bases` the addresses themselves, so a
    caller can print the unreadable ones rather than only counting them: the
    addresses are the finding, the count is arithmetic.
    """
    rows = {}
    for stride, bases in (strides if strides is not None else load_strides()):
        rows[stride] = {
            "bases": bases,
            "readable": {n: [b for b in bases if readable_at(b, n)]
                         for n in range(SLOTS)},
        }
    return rows


def window_text():
    return " ".join(f"{lo:#06x}-{hi:#06x}" for lo, hi in HOST_WINDOW)


def print_table(out, rows=None, only_resolved=True):
    """The per-stride table, as prose a document can quote.

    Columns are `stride`, bases, and readable / not readable at slot 0 -- the
    slot the bases themselves are at. Slot 1 and 2 are a separate table,
    because a column that changed meaning halfway across a markdown table is
    the misreading this avoids.
    """
    rows = rows if rows is not None else split()
    print(f"# host window {window_text()} "
          f"(ec_timer_capture.HOST_WINDOW, the 2026-09-24 census on this "
          f"machine); record stride {RECORD_STRIDE:#x} "
          f"(pd-index-geometry.md 3.2)", file=out)
    print("# 'readable' is the record's first byte being sampleable: inside "
          "the window and not on the fan page, which is what "
          "ec_timer_capture.check_addrs accepts. It is not the whole record; "
          "see the slot table.", file=out)
    print("# a page that reads 0xFF is consistent with the window not mapping "
          "it, and says nothing about what the EC holds there.", file=out)
    print(file=out)
    print("| stride | bases | readable | not readable |", file=out)
    print("|---|---:|---:|---:|", file=out)
    for stride, row in rows.items():
        if only_resolved and stride == UNRESOLVED:
            continue
        n = len(row["bases"])
        r = len(row["readable"][0])
        print(f"| `{stride}` | {n} | {r} | {n - r} |", file=out)
    return 0


def print_slots(out):
    """Per slot: bases whose first byte is sampleable, and how many bytes of the
    record a capture can read from there.

    Only the families `PAGED_STRIDES` names, because the record stride is a
    claim about those and about nothing else (§7.4). The other families' bases
    are still reported -- slot 0 says whether the base address itself is
    readable, which needs no stride -- but they are not given slots, and their
    absence here is the scope statement rather than an omission.

    The rows come from `slot_table_lines`, the same builder `--check` reads a
    document's copy back through, so the table printed and the table checked
    cannot be two derivations that agree only today.
    """
    print(f"# slot reach over the host window {window_text()}, at the "
          f"{RECORD_STRIDE:#x} record stride", file=out)
    print(f"# only the {' and '.join(PAGED_STRIDES)} families carry the "
          f"0x200x page term, so {RECORD_STRIDE:#x} is the record stride of "
          f"those and of no other (pd-index-geometry.md 7.2, 7.4). The other "
          f"families are not placed at higher slots here.", file=out)
    print("# 'first bytes in window' is where a sweep starts; 'bytes in "
          "window' is how many bytes of that record it can actually read, "
          "which stops at the window edge and leaves out the fan page "
          "0x0460-0x046F wherever the record spans it. A record whose figure "
          "is short of 608 was not wholly sampled.", file=out)
    print(file=out)
    print("| stride | slot | bases whose first byte is sampleable | "
          "bytes of that record a capture can read, min-max |", file=out)
    print("|---|---:|---:|---:|", file=out)
    for stride, slot, bases, span in slot_table_lines():
        print(f"| `{stride}` | {slot} | {bases} | {span} |", file=out)
    return 0


def _document_table(text):
    """The markdown table `print_table` writes, as read back out of a document.

    Tolerates the document's own heading, caption and `|` padding, and refuses
    a table with no row rather than returning an empty one: an empty set
    compared against a derivation would agree with it by accident, which is
    the vacuous pass `--check` exists to make impossible.
    """
    out = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            continue
        stride = cells[0].strip("`")
        if not stride or not all(cells):
            continue
        if set("".join(cells)) <= set("-: "):
            continue          # the |---|---:|---:|---:| separator
        try:
            values = [int(c) for c in cells[1:]]
        except ValueError:
            continue
        out.append((stride, values))
    return out


def slot_table_lines():
    """The per-slot table rows, as the derivation produces them.

    Same four-cell shape a document quotes, so `check_document` can compare the
    two without the document having to reproduce the caption. `--` for a slot
    with no readable base, which is what `print_slots` writes.
    """
    rows = split()
    out = []
    for stride, row in rows.items():
        if stride not in PAGED_STRIDES:
            continue
        for n in range(SLOTS):
            got = row["readable"][n]
            if not got:
                out.append((stride, n, 0, "--"))
                continue
            spans = [reachable_bytes(b, n) for b in got]
            out.append((stride, n, len(got), f"{min(spans)}-{max(spans)}"))
    return out


def _is_span(cell):
    """Whether a cell is the `min-max` range `print_slots` writes.

    Both ends digits, either side of one hyphen. The split table's last column
    is a bare count, which is what tells the two tables apart here rather than
    by their captions.
    """
    lo, sep, hi = cell.partition("-")
    return bool(sep) and lo.isdigit() and hi.isdigit()


def _document_slot_table(text):
    """The slot table `print_slots` writes, as read back out of a document.

    Distinguished from the slot-0 table by the shape of its last two cells: a
    slot row's third cell is a slot *number* and its fourth is a range, where
    the split table's are counts. Reading the shape rather than the caption
    keeps a document written by a person checkable, and the two tables are
    separate statements that can go stale apart.
    """
    out = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            continue
        stride = cells[0].strip("`")
        if not stride or not all(cells):
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        try:
            slot, bases = int(cells[1]), int(cells[2])
        except ValueError:
            continue
        span = cells[3]
        if span != "--" and not _is_span(span):
            continue          # the split table's counts, not a slot row's range
        out.append((stride, slot, bases, span))
    return out


def _report_mismatch(path, label, got, want):
    """Name both sides of a disagreement, row for row.

    Both halves, because an operator cannot otherwise tell which cell to go and
    look at, and the row is named by its stride and slot rather than by its
    position -- a table row quoted by line number is a row the next insert moves.
    """
    print(f"error: {path}'s {label} is not what this run derives from "
          f"{os.path.relpath(STRIDES_CSV, os.path.join(HERE, '..', '..'))} "
          f"and ec_timer_capture.HOST_WINDOW", file=sys.stderr)
    for row in got:
        if row not in want:
            print(f"  document: {' '.join(str(c) for c in row)}", file=sys.stderr)
    for row in want:
        if row not in got:
            print(f"  derived:  {' '.join(str(c) for c in row)}", file=sys.stderr)
    return 1


def check_document(path, rows=None):
    """True when the document's two tables are what this run derives.

    Read by row shape rather than by the tool's own caption, because the
    document is written by a person and a caption is not a contract. A
    document whose table cannot be parsed at all is *not* a pass: it raises,
    for the reason `--check` exists rather than falling back to "no rows, so
    nothing to disagree with".

    **Both tables are checked, and the slot one is the load-bearing half.**
    The slot table is where the fan page shows up: a slot-0 record spanning
    `0x0460`-`0x046F` is not wholly sampleable, and a document still quoting
    `608-608` there while the derivation says `592-608` is quoting a figure no
    `--addrs` argument reproduces. Checking only the split table would leave
    exactly the claim that goes stale unheld.
    """
    rows = rows if rows is not None else split()
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    found = _document_table(text)
    if not found:
        raise SystemExit(f"error: {path} carries no four-column table for "
                         f"--check to read; the table is what this check holds "
                         f"to the derivation")
    want = [(stride, (len(row["bases"]), len(row["readable"][0]),
                      len(row["bases"]) - len(row["readable"][0])))
            for stride, row in rows.items() if stride != UNRESOLVED]
    got = [(stride, tuple(values)) for stride, values in found
           if stride != UNRESOLVED]
    if got != want:
        return _report_mismatch(path, "readability table", got, want)

    got_slots = _document_slot_table(text)
    if not got_slots:
        raise SystemExit(f"error: {path} carries no per-slot table for "
                         f"--check to read; the reachable-length figures are "
                         f"what that check holds to the derivation")
    want_slots = list(slot_table_lines())
    if got_slots != want_slots:
        return _report_mismatch(path, "slot table", got_slots, want_slots)
    return 0


# Known answers, read off the committed inputs rather than off this tool's own
# output, and each one a relation the procedure document and the write-up both
# rest a sentence on. The `0x60` family is the array the procedure samples:
# every one of its bases begins at a sampleable byte, slot 1 begins inside the
# window and is cut short, and no slot-2 record begins inside it at all.
#
# The third check is the one that keeps "reachable" a single meaning. It holds
# `reachable_addrs` to `check_addrs`, the capture tool's own guard, in both
# directions over the whole record: every address the guard accepts inside the
# record is one this tool counts, and every address it counts is one the guard
# accepts. A `reachable_bytes` that walked straight through the fan page would
# pass a check against the window alone and fail this one, and the figure it
# prints is the one an operator would put in `--addrs`.
SELF_TEST = [
    ("0x60 stride, slot 0: every record begins at a sampleable byte",
     lambda rows: all(readable_at(b, 0) for b in rows["0x60"]["bases"])),
    ("0x60 stride, slot 1: every record begins at a sampleable byte",
     lambda rows: all(readable_at(b, 1) for b in rows["0x60"]["bases"])),
    ("0x60 stride, slot 1: no record is wholly readable",
     lambda rows: all(reachable_bytes(b, 1) < RECORD_STRIDE
                      for b in rows["0x60"]["bases"])),
    ("0x60 stride, slot 2: no record begins inside the window",
     lambda rows: not rows["0x60"]["readable"][2]),
    # The walk stops at the window edge, so the expected set runs to that edge
    # rather than over the whole record: a record beginning outside the window
    # contributes nothing, even where its later bytes re-enter the mapping at
    # `0x0C00`, because those are not bytes a sequential sweep over this record
    # walks through.
    ("what a record counts reachable is exactly what the capture guard accepts",
     lambda rows: all(
         set(reachable_addrs(b, n)) == {
             a for a in range(slot_start(b, n), _walk_end(b, n))
             if check_addrs([a]) is None}
         for stride, row in rows.items() if stride in PAGED_STRIDES
         for b in row["bases"] for n in range(SLOTS))),
    ("a record is only reported whole when every one of its bytes is readable",
     lambda rows: all(
         (reachable_bytes(b, n) == RECORD_STRIDE) == all(
             sampleable(a) for a in
             range(slot_start(b, n), slot_start(b, n) + RECORD_STRIDE))
         for stride, row in rows.items() if stride in PAGED_STRIDES
         for b in row["bases"] for n in range(SLOTS))),
    ("readable at a slot iff that slot's first byte is sampleable",
     lambda rows: all(readable_at(b, n) == sampleable(slot_start(b, n))
                      for r in rows.values() for b in r["bases"]
                      for n in range(SLOTS))),
    ("a slot the guard refuses every byte of is not readable",
     lambda rows: all(not (readable_at(b, n) and not reachable_bytes(b, n))
                      for r in rows.values() for b in r["bases"]
                      for n in range(SLOTS))),
    ("the split partitions the bases: no base is counted twice or not at all",
     lambda rows: all(len(r["readable"][0]) + len(
         [b for b in r["bases"] if not readable_at(b, 0)]) == len(r["bases"])
         for r in rows.values())),
    # The scope half of the record-stride claim, held against the committed
    # CSV's own `sites_with_page_term` column rather than against this tool's
    # reading of §7.4. `0x260` collapses a `0x60` term and a `0x200x` term, so
    # the families it may be placed over are exactly the ones the census
    # counted a page term for. If a future re-run gives one of the others a
    # page term, this goes red and the constant moves with the data instead of
    # a slot table quietly claiming a layout §7.4 excludes.
    ("the paged families are the ones the census counts a page term for",
     lambda rows: set(PAGED_STRIDES) == {
         stride for stride, bases in load_strides()
         if stride != UNRESOLVED and paged_sites(stride) and bases}),
]


def self_test():
    rows = load_strides()
    split_rows = split(rows)
    for what, holds in SELF_TEST:
        if not holds(split_rows):
            print(f"FAIL: {what}", file=sys.stderr)
            return 1
    print(f"self-test: {len(SELF_TEST)} checks pass against "
          f"{os.path.relpath(STRIDES_CSV, os.path.join(HERE, '..', '..'))}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slots", action="store_true",
                    help="the per-slot reach table as well as the split")
    ap.add_argument("--table", action="store_true",
                    help="print the markdown slot-0 table and nothing else")
    ap.add_argument("--check", metavar="DOC",
                    help="exit 1 unless DOC's table is what this run derives")
    ap.add_argument("--self-test", action="store_true",
                    help="run the known answers above and exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.check:
        return check_document(args.check)
    if args.table:
        return print_table(sys.stdout)
    if not args.slots:
        return print_table(sys.stdout)
    print_table(sys.stdout)
    print()
    print_slots(sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())