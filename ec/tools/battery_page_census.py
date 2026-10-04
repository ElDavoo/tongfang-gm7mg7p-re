#!/usr/bin/env python3
r"""Report what the EC's whole `0x00`-`0xFF` XDATA page did over a capture, per byte.

`evidence/battery-traces/2026-09-09-profiles.csv` is the repository's only
committed record of the full page: its `ec_hex` cell is 256 bytes on every row,
which is the entire `0x0400`-`0x04FF` XDATA page, sampled once a minute across a
charge cycle. `docs/findings/battery-trace-column-drift.md` records that nothing
outside the file itself explains the shape that wrote it and closes the
question as **not found by this method**, which is the right reading of *the
writer* and the wrong place to stop -- the file's richest column was unread.

This walks those cells and answers the only questions a committed file can
answer, per byte position:

  * did it move, and over how many distinct values;
  * what range it covered;
  * whether it is the low or high half of a little-endian pair that tracks a
    quantity the same row reports in its own columns;
  * whether `registers.yaml` has a row for it, and what `status:` that row
    carries.

**What a movement here is, and is not.** Every figure below is read out of a
committed CSV. Nothing was observed: no EC was opened, no register was read
back, and no byte was watched change on hardware. A byte that takes more than
one value across the rows is evidence the EC touched it during that window,
which is a different claim from evidence the EC *acts* on it -- the standing
example is `0x07B9`, writable and working with zero direct sites anywhere
(`registers.yaml`'s own caveat on its `absent` value). **Byte-position
correlation is not identification.** That a cell tracks `current_now` is a fact
about a file of rows; `0x04A4` is the counter-example inside this very capture,
tracking the same quantity from a different address. Where the tree already
holds a *writer* for a position, cite that instead -- the caller gets the row
name, not a guess at a meaning.

**The address a page offset means.** Offset `o` of `ec_hex` is XDATA
`0x0400 + o`, and the `registers.yaml` lookup keys on exactly that. It does
**not** mask to `addr & 0xff`, and that is not a stylistic choice: masking
collapses every page onto one another, so offset `0xA4` resolves to whichever
of `0x04A4` and `0x07A4` the map happens to hold and reports phantom matches
against registers this page does not contain. `page_address()` is the one place
that arithmetic happens, and a case in `test_battery_page_census.py` pins the
masked answer as the failure it is.

**This is a census and not a decoder.** It reports movement facts and the row
`registers.yaml` already holds. It does not infer the meaning of a byte that
has no row, because a value range and a distinct-value count are not a
semantics, and inventing one here is exactly the correlation-as-identification
error the write-up names. What a moving byte *means* is a firmware question,
answered at a writer in `ec/decompiled/`, not from a column of hex.

**And what this tool is not.** It is not in `.github/scripts/agent-gates.sh`,
and cannot be from an agent branch: the plan stage's push token has no
`workflow` scope, so a branch touching `.github/` fails at the very end of the
run. It runs by hand, which is where `check_cluster_citations.py` and
`check_doc_figure_pins.py` stand today. Its suite is not in the gate either,
for the same reason.

Usage:
    python3 ec/tools/battery_page_census.py [capture.csv] [--only MOVED|ALL]
                                            [--registers registers.yaml]
"""
import argparse
import csv
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)

# The one committed file that holds the whole page. A path argument replaces it,
# so a capture taken later can be pointed at the same census without this file
# changing; the committed deliverable is this capture.
DEFAULT_CAPTURE = os.path.join("evidence", "battery-traces",
                               "2026-09-09-profiles.csv")
DEFAULT_REGISTERS = os.path.join("ec", "annotations", "registers.yaml")

# `ec_hex` is the column holding the page, and these the two quantities the same
# row reports in its own columns that a little-endian pair can be held against.
# Both are read in the units the register pairs use -- milliamp and millivolt --
# so the comparison is a division by 1000 of a micro-unit column, never a guess
# at a scale factor.
PAGE_COLUMN = "ec_hex"
PAGE_BYTES = 256
PAGE_BASE = 0x0400
TRACKED = (("current", "current_now"), ("voltage", "voltage_now"))
SCALE = 1000


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below.

    The house spelling, shared with `trace_xdata_refs.py` and
    `walk_flow_follow.py`: a message that names a file a reader cannot open is
    a message that has to be re-derived before it can be acted on.
    """
    return os.path.relpath(path, REPO)


def page_address(offset: int) -> int:
    """The XDATA address page `offset` holds.

    Unmasked on purpose: offset `0xA4` is `0x04A4`, not `0x00A4` and not
    `0x07A4`. See the module docstring.
    """
    return PAGE_BASE + offset


def read_capture(path: str):
    """The capture's rows, or a refusal naming what is wrong with the file.

    Four refusals rather than a skip, because a capture this cannot read is not
    a capture with nothing to say: a missing `ec_hex` column means the file is
    not this shape at all, and a cell of the wrong width means the page is
    partial or the column is offset. Both would otherwise be reported as "no
    byte moved", which is the one answer that must never come from a file
    nobody read.
    """
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
    except OSError as e:
        return None, (f"{path}: could not be read ({e}); that is a broken "
                      "read, not a capture with nothing in it")

    if not fieldnames or PAGE_COLUMN not in fieldnames:
        return None, (f"{path}: no `{PAGE_COLUMN}` column, so it holds no page "
                      f"dump; this tool's subject is that column and a file "
                      "without it is out of scope rather than empty")

    if not rows:
        return None, (f"{path}: `{PAGE_COLUMN}` is present but holds no data "
                      "row, so there is no page to walk")

    for n, row in enumerate(rows):
        cell = row.get(PAGE_COLUMN) or ""
        if len(cell) != PAGE_BYTES * 2:
            return None, (f"{path} row {n}: `{PAGE_COLUMN}` holds "
                          f"{len(cell) // 2} byte(s), not the "
                          f"{PAGE_BYTES} of a whole `0x{PAGE_BASE:02X}`-"
                          f"{PAGE_BASE + PAGE_BYTES - 1:02X}` page dump, so the "
                          "capture is partial and per-byte facts about it "
                          "would be about a page that is not there")
        try:
            bytes.fromhex(cell)
        except ValueError:
            return None, (f"{path} row {n}: `{PAGE_COLUMN}` is not hex, so the "
                          "page was not decoded from this file's own bytes")
    return rows, None


def load_registers(path: str):
    """`addr -> (name, status)` for every address `registers.yaml` has a row for.

    One entry can cover several addresses (`addr: [0x04A6, 0x04A7]`), so the map
    is keyed per address and the name and status are shared across the entry --
    which is what the file says they are, and why this does not try to invent a
    per-address distinction the entry does not make. A row whose address is not
    an integer is skipped rather than refused: the vocabulary is enforced by
    `check_status_vocabulary.py`, and a second copy of that judgement here would
    be a second thing to fall out of date.
    """
    try:
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        return None, (f"{path}: could not be read ({e}), so no address can be "
                      "matched to a register row -- that is a broken read, not "
                      "a page with no named bytes")

    entries = (doc or {}).get("registers") or []
    table = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        addr = entry.get("addr")
        addrs = addr if isinstance(addr, list) else [addr]
        for one in addrs:
            if isinstance(one, int):
                table[one] = (entry.get("name"), entry.get("status"))
    return table, None


def tracked_values(rows):
    """Per row, the `{column: value}` scaled the way a register pair holds it."""
    per_row = []
    for row in rows:
        entry = {}
        for _, column in TRACKED:
            try:
                entry[column] = int(row[column]) // SCALE
            except (KeyError, TypeError, ValueError):
                entry[column] = None
        per_row.append(entry)
    return per_row


def census(rows, registers):
    """One record per page offset: what it did, and what the map calls it.

    A record holds movement facts only. `tracks` names the pair half a byte is
    and how often the pair equalled a tracked quantity -- "how often", never
    "what it is", because a page offset agreeing with a sysfs column says the
    EC writes that quantity there, not what the register is for.
    """
    tracked = tracked_values(rows)
    pages = [[int(row[PAGE_COLUMN][o * 2:o * 2 + 2], 16)
              for o in range(PAGE_BYTES)] for row in rows]
    records = []
    for offset in range(PAGE_BYTES):
        column = [page[offset] for page in pages]
        distinct = sorted(set(column))
        record = {
            "offset": offset,
            "addr": page_address(offset),
            "moved": len(distinct) > 1,
            "distinct": len(distinct),
            "low": distinct[0],
            "high": distinct[-1],
            "tracks": pair_tracking(offset, pages, tracked),
            "register": registers.get(page_address(offset)),
        }
        records.append(record)
    return records


def pair_tracking(offset: int, pages, tracked) -> str:
    """Whether `offset` is half a little-endian pair tracking a tracked column.

    Both halves are reported from the low half's perspective, so a byte that is
    a high half is named as one rather than silently compared as if it were a
    value of its own: `0x0435` on its own would equal `current_now / 256`, which
    is arithmetic, not a register. Returns "" for a byte that is neither the
    low half of a pair on the page nor a high half of one.
    """
    if offset + 1 < PAGE_BYTES:
        for name, column in TRACKED:
            matches = sum(1 for page, values in zip(pages, tracked)
                          if (page[offset] | (page[offset + 1] << 8))
                          == values[column])
            if matches:
                return f"{name} low half ({matches} row(s))"
    if offset > 0:
        for name, column in TRACKED:
            matches = sum(1 for page, values in zip(pages, tracked)
                          if (page[offset - 1] | (page[offset] << 8))
                          == values[column])
            if matches:
                return f"{name} high half ({matches} row(s))"
    return ""


def format_record(record) -> str:
    """One line per offset: what it did, then what the map calls the address."""
    if record["moved"]:
        did = (f"moved {record['distinct']} distinct "
               f"0x{record['low']:02X}-0x{record['high']:02X}")
    else:
        did = f"steady 0x{record['low']:02X}"
    parts = [f"  0x{record['addr']:04X} (offset 0x{record['offset']:02X})  {did}"]
    if record["tracks"]:
        parts.append(f"tracks {record['tracks']}")
    name, status = record["register"] or ("", "")
    if name:
        parts.append(f"registers.yaml: {name} ({status})")
    else:
        parts.append("registers.yaml: no row")
    return "  ".join(parts)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capture", nargs="?", default=DEFAULT_CAPTURE,
                    help="capture CSV holding the page dump "
                         f"(default: {DEFAULT_CAPTURE})")
    ap.add_argument("--registers", default=DEFAULT_REGISTERS,
                    help=f"registers.yaml to match addresses against "
                         f"(default: {DEFAULT_REGISTERS})")
    ap.add_argument("--only", choices=("MOVED", "ALL"), default="MOVED",
                    help="print only the offsets that took more than one value "
                         "over the capture, or all of them (default: MOVED)")
    args = ap.parse_args(argv)

    capture = args.capture if os.path.isabs(args.capture) \
        else os.path.join(REPO, args.capture)
    registers_path = args.registers if os.path.isabs(args.registers) \
        else os.path.join(REPO, args.registers)

    rows, problem = read_capture(capture)
    if problem:
        print(f"battery_page_census.py: {problem}", file=sys.stderr)
        return 1
    registers, problem = load_registers(registers_path)
    if problem:
        print(f"battery_page_census.py: {problem}", file=sys.stderr)
        return 1

    records = census(rows, registers)
    shown = [r for r in records if args.only == "ALL" or r["moved"]]

    print(f"{repo_path(capture)}: {len(rows)} row(s), "
          f"{PAGE_BYTES} page bytes per row, "
          f"{sum(1 for r in records if r['moved'])} offset(s) took more than "
          f"one value")
    print("every figure below is read out of that file; nothing here was "
          "observed on hardware, and a byte that moved is a byte the EC "
          "touched, not one it demonstrably acts on")
    for record in shown:
        print(format_record(record))
    return 0


if __name__ == "__main__":
    sys.exit(main())