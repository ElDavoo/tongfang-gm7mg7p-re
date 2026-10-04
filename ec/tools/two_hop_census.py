#!/usr/bin/env python3
"""The cells that took a *second* hop to resolve, one row each, and a --check.

`register_ref_table.py` resolves a DPTR handoff by decoding the callee's own
entry point. That answers the question for a handoff sitting at the site, and
it stopped there for two reasons this file is the record of closing:

  * a handoff the site only reaches **after a branch** never reached the
    resolver at all -- `site_rows()` bucketed a site first and resolved a
    handoff second, and only for the depth-0 `HANDOFF` label, so a verdict
    one branch down stayed `other->flow` whatever `--callee-depth` said. It is
    the `other->flow->` columns now, and the `0x4B40` cell is the one
    `docs/findings/walk-flow-follow.md` 2 recorded as direction-unresolved.
  * a handoff whose **own callee forwards DPTR again** resolved to nothing at
    depth 1, because the resolver stops at the first callee. It is the
    `handoff->callee->` columns now, and the two `LIGHTBAR_BAT_*` cells
    `ec/annotations/static-refs-audit.md` 5.2 named are the ones that moved.

Both new columns are **weaker** than the one beside them -- branch-then-call
and call-then-call are each two hops of a linear best-effort decode, where
`handoff->read` is one -- which is why they are separate columns rather than
more cells in an existing one. This file does not re-derive that argument; it
records which cells landed in each column, so the claim has a committed
artifact behind it rather than a sentence to be trusted.

**The selection is definitional, not hand-picked.** A row is emitted when the
site's class at that mode is one of the three *resolved* members of the two
new class tuples. Nothing here names an address: a `registers.yaml` entry that
grows, or an image that resolves one cell further, moves the census by
regenerating it rather than by someone editing a list. `two_hop_census.py
--check` is what keeps the committed file honest, and it is the same
`--check`-against-the-committed-table idiom `walk_flow_follow.py` and
`check_site_resolution.py` use.

**A `mode` column, because the two shapes are not comparable.** `flow` rows
were resolved past a branch and are held to `--callee-depth 1 --follow-flow`;
`depth2` rows were resolved through a second call and are held to
`--callee-depth 2`. Counting them as one population would average a
branch-then-call claim with a call-then-call one, which is the mistake the
separate columns exist to prevent.

**`--check` regenerates every mode the file records, whatever `--mode` says.**
A single-mode regeneration diffed against a whole file that holds both would
report the other mode's rows as drift, so `--mode` narrows what is *printed*
and nothing else. The one thing `--check` refuses is a mode the committed file
records and this tool does not implement, because those rows cannot be
regenerated at all and dropping them would look like a clean run.

**What a row here is not.** Nothing is measured on hardware: every input is the
committed image, a `read` is an instruction that loads a byte on a path this
method chose, and no register was read back and no capture opened. An address
with no row is not thereby resolved -- it is "not found by this method", never
"absent", and `0x07B9` is the standing counter-example.

Usage:
    python3 ec/tools/two_hop_census.py
    python3 ec/tools/two_hop_census.py --csv
    python3 ec/tools/two_hop_census.py --mode flow
    python3 ec/tools/two_hop_census.py --check
"""
import argparse
import csv
import difflib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import yaml                                            # noqa: E402

from check_register_counts import DEFAULT_YAML          # noqa: E402
import register_ref_table as rrt                       # noqa: E402
from trace_xdata_refs import PD_MARKER                 # noqa: E402

REPO = os.path.join(HERE, os.pardir, os.pardir)
ANNOT = os.path.join(HERE, os.pardir, "annotations")
CENSUS_CSV = os.path.join(ANNOT, "two-hop-dptr-handoffs.csv")
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")

# The two modes, and the class tuple each is measured against. `flow` is a
# handoff the branch reached and the callee then settled; `depth2` is a handoff
# the first callee forwarded and the second settled. The three resolved members
# of each tuple are the selection -- the fourth is the unresolved bucket, which
# is not a cell that took the second hop and so is deliberately not here.
MODES = {
    "flow": (rrt.FLOW_CALLEE_CLASSES[:3], 1, True),
    "depth2": (rrt.HANDOFF_DEPTH2_CLASSES[3:6], 2, False),
}

# `callee_window` is the window of the *first* callee on every row, and
# `callee2_window` the second's, so the two never mean different windows in
# one column name. A `depth2` row's first callee did not settle a direction --
# that is what a forwarder is -- so its `callee` column names the routine and
# its window says what the forwarder did instead.
COLUMNS = ("addr", "file_offset", "region", "runtime", "mode", "via", "callee",
           "callee_window", "callee2", "callee2_window", "class")


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below.

    A path outside the tree -- the doctored copy a test writes to a temporary
    directory -- keeps its own name rather than becoming a chain of `../` that
    says less than the path the caller passed.
    """
    rel = os.path.relpath(path, REPO)
    return path if rel.startswith(os.pardir) else rel


def census_rows(d: bytes, regs, pd_verified: bool, mode: str):
    """The cells of one mode, in file order, as `--csv` rows.

    Every address in registers.yaml is walked and every site of it classified,
    rather than the census naming the addresses it expects: the selection is
    "the class is one of this mode's three resolved labels", and a selection
    that had to be told which addresses to look at would be hand-picked with
    an extra step.
    """
    resolved, depth, follow_flow = MODES[mode]
    wanted = {label for label, _ in resolved}
    rows = []
    for _name, addr in rrt.addresses(regs):
        for r in rrt.site_rows(d, addr, pd_verified, depth, follow_flow):
            o, region, rt, label, callee, window, _win, via, chain, _stop = r
            if label not in wanted:
                continue
            # `callee` from site_rows() is the routine resolve_handoff()
            # *settled on*, which for a depth2 row is the second link of the
            # chain -- so both links are read off the chain here, or every
            # depth2 row would name the same routine twice. A flow row's chain
            # is one link long, so it records only that one: its second hop is
            # the branch, and `via` already names it.
            second = chain[-1] if chain and len(chain) > 1 else None
            first = chain[0] if chain else callee
            # The window the class came from is the settling callee's, and
            # site_rows() carries exactly one. So it goes in the column of
            # whichever routine it describes: `callee_window` on a flow row,
            # `callee2_window` on a depth2 row. The first callee of a depth2
            # row is a forwarder -- that is what made the row take two hops --
            # so it has no direction and no window of its own to record.
            callee_window = "" if second is not None else (window or "")
            callee2_window = (window or "") if second is not None else ""
            rows.append([f"0x{addr:04X}", f"0x{o:05X}", region,
                         f"0x{rt:04X}" if rt is not None else "", mode,
                         via or "",
                         f"0x{first:04X}" if first is not None else "",
                         callee_window,
                         f"0x{second:04X}" if second is not None else "",
                         callee2_window,
                         label])
    return rows


def census_table(d: bytes, regs, pd_verified: bool, modes) -> str:
    """The whole file, as a string, so `--check` diffs the bytes it prints."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for mode in modes:
        for row in census_rows(d, regs, pd_verified, mode):
            w.writerow(row)
    return buf.getvalue()


def load_recorded_modes(path: str):
    """The modes the committed census actually records.

    Read for one purpose, the one `walk_flow_follow.load_recorded()` reads its
    bounds for: a `--check` that re-derived a population the file does not hold
    would diff a different measurement against it and report a difference that
    says nothing. Refused rather than defaulted, because a default here is a
    `--check` that goes green against rows it never looked at.
    """
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or "mode" not in rows[0]:
        raise ValueError(f"{repo_path(path)} has no 'mode' column; it is not a "
                         "two_hop_census table")
    return {r["mode"] for r in rows}


def describe_modes(modes) -> str:
    return ", ".join(sorted(modes))


def check_table(generated: str, path: str) -> int:
    """Exit code for `--check`: 0 when this run reproduces `path` exactly."""
    try:
        with open(path, newline="") as f:
            on_disk = f.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if generated == on_disk:
        # No line count in this message: a figure of the repository's own text
        # in a success line is stale at the next census row, and the write-up
        # pastes this line verbatim.
        print(f"{repo_path(path)}: this run reproduces it byte for byte")
        return 0
    print(f"note: {repo_path(path)} differs from what this run produced; the "
          "file is the product of the command on the page that names it, so "
          "regenerate rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(), generated.splitlines(),
                                     "committed", "generated", lineterm="", n=0):
        print(line, file=sys.stderr)
    return 1


def print_rows(rows_by_mode) -> None:
    """The human form: one block per mode, then the standing caveats."""
    for mode, rows in rows_by_mode.items():
        print(f"{mode}: {len(rows)} cell(s)")
        for row in rows:
            print(f"  {row[0]}  {row[1]}  {row[4]}  via={row[5] or 'at site'}  "
                  f"callee={row[6] or '-'}"
                  + (f" -> {row[8]}" if row[8] else "")
                  + f"  {row[10]}")
        print()
    print("Each row is a cell that took a *second* hop: a branch and then a "
          "call (`flow`),\nor a call whose own callee forwards DPTR on again "
          "(`depth2`). Both are weaker\nthan the one-hop column beside them, "
          "which is why they are columns apart. A `flow` row's class\ncomes "
          "from the callee's entry point; a `depth2` row's comes from the "
          "*second* callee's.\nBoth are one linear best-effort decode each, "
          "on a path this method chose.\n\n"
          "An address with no row is not thereby resolved -- it is 'not found "
          "by this method', never 'absent';\n0x07B9 is the standing "
          "counter-example. Nothing here is measured on hardware.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("--registers", default=DEFAULT_YAML,
                    help="registers.yaml to tabulate (default: the one beside this tool)")
    ap.add_argument("--mode", choices=sorted(MODES),
                    help="one mode only (default: every mode, which is what "
                         "--check compares against)")
    ap.add_argument("--csv", action="store_true",
                    help="write the census as CSV on stdout instead of the "
                         "per-cell listing")
    # A bare flag rather than an optional positional taking a path, because
    # `nargs="?"` swallows the next flag's *value*: `--check --mode flow` would
    # read `--mode` as the path and go looking for a file named `--mode`. There
    # is exactly one census this tool checks, so the flag needs no argument;
    # `check_table()` is what the suite drives for the diff path.
    ap.add_argument("--check", action="store_true",
                    help="diff this run against the committed census and exit "
                         f"non-zero on any difference ({repo_path(CENSUS_CSV)}). "
                         "Always regenerates every mode the file records, so "
                         "--mode does not narrow it: a single-mode diff would "
                         "report the other modes' rows as drift")
    args = ap.parse_args()

    # The `--check` guards come before the image is read, so a run asked for
    # something this tool cannot regenerate says so rather than first
    # complaining about a firmware path the caller did not get wrong.
    #
    # A `--check --mode X` where the committed census does not record X would
    # diff a partial regeneration against the whole file and report the other
    # mode's rows as drift, so it is refused with both sides named. Given no
    # `--mode`, it regenerates every mode the file records, which is the only
    # whole-file comparison that means anything -- and a mode the file holds
    # but this tool does not implement cannot be regenerated at all, so that
    # is refused too rather than silently dropped from the diff.
    modes = sorted(MODES) if args.mode is None else [args.mode]
    if args.check:
        try:
            recorded = load_recorded_modes(CENSUS_CSV)
        except (OSError, ValueError) as e:
            print(f"note: {e}", file=sys.stderr)
            return 1
        unknown = sorted(recorded - set(MODES))
        if unknown:
            print(f"note: {repo_path(CENSUS_CSV)} records "
                  f"{describe_modes(unknown)}, which this tool does not "
                  f"implement; it can only regenerate "
                  f"{describe_modes(set(MODES))}", file=sys.stderr)
            return 1
        # `--check` always regenerates *every* recorded mode, whatever
        # `--mode` says, because the committed file holds all of them. A
        # single-mode regeneration diffed against the whole file would report
        # the other modes' rows as drift -- which is the failure this guard
        # exists to stop, and it would fire on every `--check --mode flow`.
        # `--mode` therefore narrows what is *printed* and nothing else.
        modes = sorted(recorded)

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the annotations were written against", file=sys.stderr)
        return 1

    with open(args.registers) as f:
        regs = yaml.safe_load(f)["registers"]

    if args.check:
        return check_table(census_table(d, regs, pd_verified, modes), CENSUS_CSV)

    if args.csv:
        sys.stdout.write(census_table(d, regs, pd_verified, modes))
        return 0

    print_rows({m: census_rows(d, regs, pd_verified, m) for m in modes})
    return 0


if __name__ == "__main__":
    sys.exit(main())
