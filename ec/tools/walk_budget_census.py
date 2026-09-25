#!/usr/bin/env python3
"""Name every row a given `walk()` budget truncates, and say what a larger
budget would have put in that row's `access` cell instead.

`trace_xdata_refs.walk()` bounds its own loop with `max_insns`, and
`../../docs/findings/opcode-len-bounds-census.md` drove that loop from every
one of the image's 262144 start offsets to count where it stops: `max_insns (8)
exhausted` fires 119530 times. That figure is a property of the file, and
nothing in the tree had asked what it means for the nine committed tables whose
`window` column this same function produces. This asks, and the answer is that
45 of their rows are truncated, so their windows are shorter than the code
around them and their `access` cells are summaries of a cut.

**The terminator is re-derived here, not re-implemented.** Every row goes
through `trace_xdata_refs.walk_why()`, the function `trace_xdata_refs.py`
itself now uses to render the `terminator` column, so the rows named here and
the cells in the six re-cut tables are one measurement in two places. The
terminator vocabulary is `trace_xdata_refs.TERMINATORS` plus its
`budget_end()`; a row is budget-truncated exactly when its terminator is the
budget token, which is the definition rather than a threshold somebody chose.

**A truncated row is not a wrong row.** The census emits one row per
truncated row and says what a larger budget would have made of it, and it
refuses to say more than the bytes support. There are two findings a larger
budget produces, they are not the same, and the `verdict` column separates
them mechanically:

- `A` -- a direct store to DPL (`0x82`) or DPH (`0x83`) sits in the
  instructions the budget-8 window does not include, between the cut and the
  `movx` whose direction changed the cell. `walk()`'s guard tests
  `d[i] == MOV_DPTR` and cannot see the `mov 0x82,a` / `mov 0x83,a` form, so
  at a larger budget the cell counts an access through an *indexed* DPTR as
  though it were the site register's own. Ten of the thirteen moving rows are
  this. `../annotations/pd-index-geometry.md` records the refutation for the
  `0xC2FA` row and `pd_index_geometry.py --self-test` asserts it, so the
  repository already holds the contrary reading for at least one of them.
- `B` -- no such store. The budget-8 window was simply short, and the larger
  cell counts this same site's own further accesses. Three of the thirteen.

`undecided` is the third answer and it is a real one, not a formality: the
diagnosis needs a window long enough to hold the store, so a `--extend` too
small to reach the first extended `movx` leaves the question open, and the
row says so rather than falling into `B` because it found no store in the
instructions it happened to be shown. Nothing in the committed census is
`undecided`; `test_walk_budget_census.py` reaches the case deliberately.

**This does not settle what the budget should be.** `--extend` defaults to 64
because that is the figure issue #846's own table used, kept as a named
default so the diagnosis column is re-derivable and a reader can re-run it at
another value; it is not a recommendation, and the `moves` column is the
finding that a budget of 64 would rewrite 13 committed `access` cells, 10 of
them wrongly. `walk()`'s own `max_insns` stays 8.

**Two populations, kept apart.** The nine tables below are every committed
`window` column that `trace_xdata_refs.walk()` produces, all keyed on
`file_offset`. `manual-fan-ctrl-0751-arms.csv` also has a `window` column and
is not among them: `walk_branch_arms.py` produces it, its key is `site_runtime`
rather than a file offset, and its 171 cells are arm listings that end on a
flow opcode by construction. Folding it in would count another tool's
guarantee as this one's measurement.

**Nothing here is a claim about the EC.** Every input is a committed file: a
site table and `ec/firmware/GMxMGxx_11.800`. No register was read back, no
capture opened, no hardware or Windows involved. A `classify()` cell is a
reading aid over at most 8 (or `--extend`) instructions of a linear window,
and the module docstring of `trace_xdata_refs.py` says what else that decode
cannot do.

Usage:
    python3 walk_budget_census.py ../firmware/GMxMGxx_11.800
    python3 walk_budget_census.py ../firmware/GMxMGxx_11.800 --csv
    python3 walk_budget_census.py ../firmware/GMxMGxx_11.800 --budget 16
    python3 walk_budget_census.py ../firmware/GMxMGxx_11.800 --check
"""
import argparse
import collections
import csv
import difflib
import io
import os
import sys

from trace_xdata_refs import (budget_end, classify, is_terminator, walk,
                              walk_why)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
ANNOT = os.path.join(HERE, os.pardir, "annotations")
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")
CENSUS_CSV = os.path.join(ANNOT, "walk-budget-census.csv")

# Every committed `window` column trace_xdata_refs.walk() produces, in the
# order their `.md` page numbers them. Listed rather than globbed, because a
# glob over `*-sites.csv` would pick up `xdata-0860-census-sites.csv` (no
# `window` column, and not this tool's output) and miss nothing else, and
# because a reader has to be able to see what was left out.
TABLES = ("ec-07c4-07d5-sites.csv",
          "ec-07d6-07d7-sites.csv",
          "ec-09e9-09eb-sites.csv",
          "ec-0x07d0-sites.csv",
          "ec-0x07d1-sites.csv",
          "manual-fan-ctrl-0751-sites.csv",
          "xdata-0400-045f-sites.csv",
          "xdata-086x-dispatch-sites.csv",
          "xdata-1c3x-consumers-sites.csv")

# The budget the diagnosis column is measured at. Issue #846's own table used
# 64; nothing here says 64 is right, and --extend takes any value. It only
# has to be larger than 8 for the comparison to mean anything, and the
# `undecided` verdict is what catches a value that is not.
EXTEND = 64

# walk()'s own default, read off the function rather than written out here, so
# that changing the signature cannot leave this tool censusing a budget the
# decode no longer uses. This is the answer to "which rows does the committed
# budget truncate" -- 8 is a fact about the code, not a choice made here.
BUDGET = walk.__defaults__[0]

COLUMNS = ("table", "addr", "file_offset", "max_insns", "extend",
           "terminator_at_budget", "terminator_at_extend", "access_at_budget",
           "access_at_extend", "moves", "verdict")

# `mov 0x82,a` is 0xF5 0x82 and `mov 0x82,rn` is 0x8F 0x82; the DPH pair is
# the same opcodes with 0x83. These are the forms walk()'s `d[i] == MOV_DPTR`
# guard cannot see, and they are the whole of the class A/B split below.
DPL = 0x82
DPH = 0x83
DIRECT_STORE_OPCODES = (0xF5, 0x8F)

MOVX_READ = 0xE0
MOVX_WRITE = 0xF0


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below."""
    return os.path.relpath(path, REPO)


def is_direct_dp_store(raw: bytes) -> bool:
    """A store to DPL or DPH that `walk()`'s guard cannot see.

    Two bytes, `0xF5 nn` (`mov nn,a`) and `0x8F nn` (`mov nn,rn`), with `nn` a
    direct SFR address. `OPCODE_LEN` is asked rather than `raw[1] ==` tested,
    so a 3-byte instruction whose second byte happens to be 0x82 is not
    mistaken for one of these.
    """
    return (len(raw) == 2 and raw[0] in DIRECT_STORE_OPCODES
            and raw[1] in (DPL, DPH))


def verdict_for(extra, why_at_extend: str, budget: int, extend: int,
                moved: bool) -> str:
    """Class A, class B, `undecided`, or `unchanged` -- the cell, from the
    bytes.

    `extra` is the instructions the budget-`budget` window does not include,
    so the question is answered on exactly the region the budget hid. The
    test is mechanical: the first `movx` in that region, and whether a direct
    store to DPL/DPH sits in front of it.

    `undecided` is returned whenever the evidence needed for the test is not
    in `extra` -- the extension budget ran out before the first `movx` -- and
    never because no store was found. Those two are different states and the
    cell has to tell them apart: "no store here" is the finding (class B), and
    "the window was too short to see one" is the absence of a finding.

    `unchanged` is the honest cell for a row whose `access` is the same at
    both budgets. A diagnosis there would be a finding about nothing, and the
    one thing it must not be is a class: a row that keeps its cell is not
    evidence of anything about DPL/DPH."""
    if not moved:
        return ("unchanged: the `access` cell is the same at both budgets, so "
                "there is nothing here for a larger budget to be wrong about")
    if why_at_extend == budget_end(extend):
        return (f"undecided: a budget of {extend} is still exhausted here, so "
                f"the {budget}-instruction cut hides the access this cell is "
                f"about; re-run with a larger --extend")
    first_movx = next((k for k, (_, raw, _) in enumerate(extra)
                       if raw[0] in (MOVX_READ, MOVX_WRITE)), None)
    if first_movx is None:
        return ("undecided: no `movx` in the instructions the budget hides, so "
                "what changed the cell is not an access this census can name")
    store = next((k for k in range(first_movx) if is_direct_dp_store(extra[k][1])),
                 None)
    if store is None:
        return ("B: no store to DPL/DPH precedes the first extra `movx`, so the "
                "larger budget counts this site's own further accesses and the "
                "committed cell is short rather than wrong")
    half = "DPL" if extra[store][1][1] == DPL else "DPH"
    direction = "read" if extra[first_movx][1][0] == MOVX_READ else "write"
    return (f"A: `mov 0x{extra[store][1][1]:02X},…` ({half}) at "
            f"0x{extra[store][0]:05X} precedes the extra {direction} at "
            f"0x{extra[first_movx][0]:05X}, and walk()'s MOV_DPTR guard cannot "
            f"see that form, so the larger budget files an indexed access "
            f"under the site register")


def read_sites(path: str):
    """The `(addr, file_offset)` pairs of a committed site table, in file
    order, with the table's own `access` cell alongside.

    `file_offset` is the key rather than `runtime` because it is the only
    column that means the same thing in every region: a `pd-image` row's
    runtime address belongs to a different program in a different address
    space (`../annotations/xdata-1c3x-consumers.md` is the page that says so
    at length). A table without the two columns is a ValueError rather than an
    empty population -- a silently empty census is a census that reports zero
    truncated rows and reads as a clean sweep."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "file_offset" not in reader.fieldnames \
                or "addr" not in reader.fieldnames:
            raise ValueError(f"{repo_path(path)} has no addr/file_offset "
                             "columns; it is not a trace_xdata_refs site table")
        rows = []
        for row in reader:
            rows.append((row["addr"], row["file_offset"],
                         row.get("access", ""), int(row["file_offset"], 16)))
    return rows


def census_table(d: bytes, budget: int, extend: int):
    """(the census CSV, per-table terminator tallies, the verdict tally, rows
    whose committed `access` cell this run does not reproduce, and terminators
    outside the vocabulary).

    The mismatched rows are the loud ones. Re-deriving `classify()` from the
    image has to give back the cell the table committed, or the census is
    measuring a different walk than the one the table was cut with and every
    verdict below it is about the wrong population. That is checked **only at
    `BUDGET`**, and the restriction is the point rather than a limitation: the
    committed site tables were cut at that budget, so at any other one their
    `access` cells are not what this run should reproduce and a difference is
    the answer, not a fault. Running `--budget 16` is a real question with a
    real answer, and refusing it as a mismatch would refuse the question.

    The off-vocabulary terminators are loud for the same reason one step
    earlier: a `walk_why()` that grew a sixth way to stop would put a token in
    this CSV that nothing can classify, and `--check` would go green on it.
    `is_terminator()` is the closed set, and the census refuses rather than
    rendering the odd token into a cell -- the same refusal
    `load_census_map()` makes, for the same reason: a cell that reads as an
    answer is worse than a run that stops."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    tallies = {}
    moving = 0
    classes = collections.Counter()
    mismatched = []
    unknown = set()
    for name in TABLES:
        path = os.path.join(ANNOT, name)
        tally = collections.Counter()
        for addr, offset, committed, off in read_sites(path):
            insns, why = walk_why(d, off, budget)
            tally[why] += 1
            if not is_terminator(why):
                unknown.add((name, offset, why))
            if why != budget_end(budget):
                continue
            at_extend, why_extend = walk_why(d, off, extend)
            if not is_terminator(why_extend):
                unknown.add((name, offset, why_extend))
            access_budget = classify(insns)
            if budget == BUDGET and access_budget != committed:
                mismatched.append((name, offset, committed, access_budget))
            access_extend = classify(at_extend)
            extra = at_extend[len(insns):]
            moved = access_extend != access_budget
            verdict = verdict_for(extra, why_extend, budget, extend, moved)
            if moved:
                moving += 1
                # Only over the rows that actually move: a verdict on a row
                # whose cell is identical either way is a finding about
                # nothing, and counting it would put A and B above 13.
                classes[verdict.split(":")[0]] += 1
            w.writerow([name, addr, offset, budget, extend, why, why_extend,
                        access_budget, access_extend,
                        "yes" if moved else "no", verdict])
        tallies[name] = tally
    return (buf.getvalue(), tallies, moving, classes, mismatched,
            sorted(unknown))


def load_recorded_budgets(path: str) -> set:
    """The `max_insns` values the committed census actually records.

    Read for one purpose: `--check` at a budget this file does not record
    would diff a different census against it and report a difference that says
    nothing, so that run is refused instead. Refused rather than defaulted,
    the way `trace_xdata_refs.load_census_map()` refuses a `census_state` it
    does not define -- a default budget here is a `--check` that goes green
    against rows it never looked at."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or "max_insns" not in rows[0]:
        raise ValueError(f"{repo_path(path)} has no max_insns column; it is "
                         "not a walk_budget_census census")
    return {int(r["max_insns"]) for r in rows}


def check_table(generated: str, path: str) -> int:
    """Exit code for `--check`: 0 when this run reproduces `path` exactly.

    Read with `newline=""` for the reason
    `trace_xdata_refs.check_table()` gives: the committed census carries the
    csv module's own CRLF terminator, and universal-newline translation would
    report a difference on every run."""
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


def print_summary(tallies, moving: int, classes, budget: int, extend: int) -> None:
    """The per-table terminator tally, then the 45, then the 13.

    The four tables with no truncated row are printed with the rest rather
    than left out. A zero is the other half of the finding, and a table that
    does not appear cannot be told from a table that was not looked at -- so
    `xdata-086x-dispatch-sites.csv`'s 0 is the same kind of claim as
    `ec-0x07d0-sites.csv`'s 4, and both are re-derived on this run."""
    total = 0
    rows = 0
    for name in TABLES:
        tally = tallies[name]
        n = tally[budget_end(budget)]
        total += n
        rows += sum(tally.values())
        other = ", ".join(f"{k} {v}" for k, v in sorted(tally.items())
                          if k != budget_end(budget))
        print(f"{name:30s} {sum(tally.values()):4d} rows  "
              f"{budget_end(budget)} {n:3d}   {other}")
    print(f"\n{total} of {rows} rows across {len(TABLES)} tables are truncated "
          f"at a budget of {budget}.")
    print(f"A budget of {extend} changes {moving} of their `access` cells: "
          + ", ".join(f"{k} {v}" for k, v in sorted(classes.items()))
          + f", and the other {total - moving} keep the cell they have.")
    print("`A` means a store to DPL/DPH that walk()'s MOV_DPTR guard cannot see "
          "sits in\nthe instructions the budget hides, so the larger budget "
          "files an indexed access under\nthe site register. `B` means the "
          "window was short and the larger cell is this same\nsite's own "
          "further accesses. `undecided` is a --extend too small to see "
          "either, and is\nnever a guess. The module docstring is the long "
          "version.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("--budget", type=int, default=BUDGET,
                    help="the walk() budget to census (default: walk()'s own, "
                         f"{BUDGET})")
    ap.add_argument("--extend", type=int, default=EXTEND,
                    help="the larger budget the diagnosis column is measured "
                         f"at (default: {EXTEND}, issue #846's figure; not a "
                         "recommendation)")
    ap.add_argument("--csv", action="store_true",
                    help="write the census as CSV on stdout instead of the "
                         "per-table summary")
    ap.add_argument("--check", nargs="?", const=CENSUS_CSV, metavar="PATH",
                    help="diff this run against the committed census and exit "
                         f"non-zero on any difference (default: {repo_path(CENSUS_CSV)})")
    args = ap.parse_args()

    if args.budget < 1 or args.extend < 1:
        print("note: --budget and --extend are both instruction counts and "
              "both have to be at least 1", file=sys.stderr)
        return 1
    if args.extend <= args.budget:
        print(f"note: --extend {args.extend} is not larger than --budget "
              f"{args.budget}, so the diagnosis column would compare the "
              "committed cell with itself", file=sys.stderr)
        return 1

    d = open(args.firmware, "rb").read()
    table, tallies, moving, classes, mismatched, unknown = census_table(
        d, args.budget, args.extend)

    for name, offset, committed, got in mismatched:
        print(f"note: {name} row {offset} commits access {committed!r} and this "
              f"run re-derives {got!r} from {args.firmware} at walk()'s own "
              f"budget of {BUDGET}; the census below would be measuring a walk "
              "this table was not cut with", file=sys.stderr)
    if mismatched:
        return 1

    for name, offset, token in unknown:
        print(f"note: {name} row {offset} ended on {token!r}, which is not one "
              "of trace_xdata_refs.TERMINATORS or its budget_end(); a token "
              "nothing can classify would go into the census and into --check",
              file=sys.stderr)
    if unknown:
        return 1

    if args.check is not None:
        try:
            recorded = load_recorded_budgets(args.check)
        except (OSError, ValueError) as e:
            print(f"note: {e}", file=sys.stderr)
            return 1
        if args.budget not in recorded:
            print(f"note: {repo_path(args.check)} records a budget of "
                  f"{', '.join(str(b) for b in sorted(recorded))} and this run "
                  f"used {args.budget}; --check at a budget the file does not "
                  "record would diff a different census against it and report "
                  "a difference that says nothing", file=sys.stderr)
            return 1
        return check_table(table, args.check)

    if args.csv:
        sys.stdout.write(table)
        return 0

    print_summary(tallies, moving, classes, args.budget, args.extend)
    return 0


if __name__ == "__main__":
    sys.exit(main())
