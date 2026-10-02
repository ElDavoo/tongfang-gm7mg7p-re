#!/usr/bin/env python3
"""Hold a verdict for every row the relative-containment page puts on trial.

`xdata-export-ownership.md` 6 told a reader to look at the `containment`
column before trusting a fold. That column is `|A & B| / |A|` with `A` the
smaller body, so a four-statement stub scores `1.00` against any larger body
that happens to spell those four statements: the score of a copy and the score
of a fragment are the same number. The column cannot carry the judgement the
page assigned it, and this is the artefact that says so per row instead of in
prose.

**The population.** Every non-owner row in the committed map whose owner is at
least twice its size and which scores `1.00` against it -- the rows a relative
check has to spare the 42-file class to get right. It is derived from the
committed CSV rather than typed, so a tree that grows a row gets one
population and one verdict obligation rather than a stale list.

**The check is two-way, and the two failures are different mistakes.** A
member with no verdict is an unfinished pass; a verdict naming a member the
population no longer contains is a stale one, and a reader who saw only the
first message would go looking for a row that is not there. They are reported
separately for that reason, not for tidiness. The `owner_out_file` on every
ledger row is held against the map's too, because a verdict recorded against
one owner says nothing about a class that has since re-formed.

**What a verdict is not.** It is a reading of two committed `.c` files, with
the reading's reason in `basis`. No mechanical criterion decides it, and that
is measured rather than assumed: the obvious candidates all fail on this tree.
Asking whether the member's bytes lie inside the owner's range says no for
essentially every non-owner row, including the 42-file class that is known to
be one routine, because the committed `size` is a product of the very boundary
defect this work is about -- `bank1/8001.c` is three bytes for the 393-byte
run it decompiles. Asking whether the member's text is a literal slice of the
owner's says no for `common/0877.c`, which plainly is the tail of
`common/0902.c` with one `_d_5 = 0;` interleaved. So the verdict is a person
reading two files, and this tool's job is to make sure that reading exists for
every row and has not drifted from the map it was recorded against.
"""
import argparse
import collections
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import export_ownership  # noqa: E402

ANNOT_DIR = os.path.join(os.path.dirname(HERE), "annotations")
MAP_CSV = os.path.join(ANNOT_DIR, "xdata-export-ownership.csv")
VERDICTS_CSV = os.path.join(ANNOT_DIR, "xdata-export-ownership-verdicts.csv")

COLUMNS = ["out_file", "owner_out_file", "verdict", "basis"]

# The population's two clauses, named rather than inlined because a reader who
# disagrees with either should be able to see what the other reading selects
# without re-reading the loop. `MIN_OWNER_MULTIPLE` is the issue's own "an
# owner at least twice their size"; `POPULATION_CONTAINMENT` is the exact
# score, so a row the committed threshold merely admits is not on trial.
MIN_OWNER_MULTIPLE = 2
POPULATION_CONTAINMENT = 1.00

# Closed, because the alternative is a verdict nobody can enumerate: a token
# that is not here is refused rather than treated as `undecided`, so a typo
# cannot quietly become "we looked and could not tell".
#
#   re-export  the member's statements are a run of the owner's body -- the
#              shape the exporter's overlapping cuts produce, which is the
#              shape this pass exists to remove, so the fold stands.
#   fragment   the member is a routine in its own right that the owner's text
#              contains without being an export of it. Its references are not
#              counted through the owner, so the fold does not stand.
#   undecided  the two files do not settle it. Counted, never dropped: a
#              population of undecided rows has not been worked through.
VERDICTS = ("re-export", "fragment", "undecided")


def load_map(path=MAP_CSV) -> list:
    """The committed ownership map as a list of dicts."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def population(records) -> list:
    """The rows a relative check has to get right, in map order.

    Derived from the committed map rather than re-derived from the `.c` tree,
    so the ledger is held against the artefact it is about. `--check` on
    `export_ownership.py` is what holds that artefact to the tree.
    """
    return [r for r in records
            if r["shared"] == "yes"
            and float(r["containment"]) == POPULATION_CONTAINMENT
            and int(r["owner_body_lines"]) >= MIN_OWNER_MULTIPLE
            * int(r["body_lines"])]


def load_verdicts(path=VERDICTS_CSV) -> list:
    """The committed ledger as a list of dicts, refusing a malformed row.

    A `basis` carrying an unquoted comma reads back with the fields after the
    comma shoved under a spare key and the citation truncated, and a reader
    checking the ledger against the population would never know: the row still
    has a verdict and a member. `csv.DictReader` hides the extra fields under
    `None` rather than raising, so the width is checked here rather than
    trusted.
    """
    with open(path, newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise SystemExit(f"{path} is empty")
        if header != COLUMNS:
            raise SystemExit(f"{path} header is {header}, not {COLUMNS}")
        out = []
        for n, cells in enumerate(reader, start=2):
            if len(cells) != len(COLUMNS):
                raise SystemExit(
                    f"{path}:{n}: {len(cells)} fields, not {len(COLUMNS)} -- "
                    f"a comma inside a value needs quoting: {cells[:1]}")
            out.append(dict(zip(COLUMNS, cells)))
    return out


def disagree(records, verdicts) -> list:
    """Every disagreement between the population and the ledger.

    Returned rather than printed so a caller can decide what a disagreement
    means: `--check` exits on one, `--table` refuses to render a table it
    cannot stand behind. Each entry is `(kind, message)` and the kinds are
    distinct -- an unfinished pass and a stale row are different mistakes and
    want different fixes.
    """
    by_file = {r["out_file"]: r for r in records}
    ledger = {}
    out = []
    for v in verdicts:
        if v["out_file"] in ledger:
            # Two rows for one member, and the dict below would keep whichever
            # came last. The verdict a reader reads would then depend on the
            # order of a file whose order means nothing, which is the opposite
            # of what a ledger is for.
            out.append(("duplicate-verdict",
                        f"the ledger carries {v['out_file']} more than once, "
                        f"so the verdict that counts would be whichever row "
                        f"comes last"))
            continue
        ledger[v["out_file"]] = v

    for r in population(records):
        v = ledger.get(r["out_file"])
        if v is None:
            out.append(("no-verdict",
                        f"{r['out_file']} is on trial (owner "
                        f"{r['owner_out_file']}, {r['body_lines']} of "
                        f"{r['owner_body_lines']} statements) and the ledger "
                        f"has no verdict for it"))
            continue
        if v["verdict"] not in VERDICTS:
            out.append(("unknown-verdict",
                        f"{r['out_file']} carries verdict "
                        f"{v['verdict']!r}, which is not one of "
                        f"{', '.join(VERDICTS)}"))
        if v["owner_out_file"] != r["owner_out_file"]:
            out.append(("owner-moved",
                        f"{r['out_file']} is owned by "
                        f"{r['owner_out_file']} in the map but the ledger "
                        f"records {v['owner_out_file']}"))
        if not v["basis"].strip():
            out.append(("no-basis",
                        f"{r['out_file']} has a verdict and no basis, which is "
                        f"a claim with nothing a reader can check"))

    for v in verdicts:
        if v["out_file"] not in by_file:
            out.append(("not-in-map",
                        f"the ledger carries {v['out_file']}, which the map "
                        f"does not have a row for"))
        elif v["out_file"] not in {r["out_file"] for r in population(records)}:
            out.append(("not-in-population",
                        f"the ledger carries a verdict for {v['out_file']}, "
                        f"which is not in the population (it is "
                        f"{by_file[v['out_file']]['shared']} against "
                        f"{by_file[v['out_file']]['owner_out_file']})"))
    return out


def tally(verdicts) -> collections.Counter:
    """How many rows each verdict was recorded for."""
    return collections.Counter(v["verdict"] for v in verdicts)


def render_table(records, verdicts) -> str:
    """The markdown the write-up carries, generated rather than typed.

    Refuses to render while the two disagree: a table of a population the
    ledger does not cover is a table that reads as complete.
    """
    bad = disagree(records, verdicts)
    if bad:
        raise SystemExit("refusing to render a table the ledger does not "
                         "support: " + bad[0][1])
    by_file = {r["out_file"]: r for r in records}
    ledger = {v["out_file"]: v for v in verdicts}
    pop = sorted(population(records),
                 key=lambda r: (-float(r["member_share"]), r["out_file"]))
    lines = ["| member | owner | member / owner | containment | verdict |",
             "|---|---|---:|---:|---|"]
    for r in pop:
        v = ledger[r["out_file"]]
        lines.append(f"| `{r['out_file']}` | `{r['owner_out_file']}` "
                     f"| {r['body_lines']}/{r['owner_body_lines']} "
                     f"| {r['containment']} | **{v['verdict']}** |")
    return "\n".join(lines)


def check(args) -> int:
    """The population and the ledger describe each other, in both directions."""
    bad = disagree(args.records, args.verdicts)
    for _, message in bad:
        print(f"{VERDICTS_CSV}: {message}", file=sys.stderr)
    counts = tally(args.verdicts)
    print(" ".join(f"{v}={counts[v]}" for v in VERDICTS))
    if bad:
        print(f"{len(bad)} disagreement(s) between {MAP_CSV} and "
              f"{VERDICTS_CSV}", file=sys.stderr)
        return 1
    print(f"{VERDICTS_CSV}: every row of the population carries a verdict, "
          f"and every verdict names a row of the population")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true",
                       help="derive the population from the committed map and "
                            "hold the ledger against it in both directions")
    modes.add_argument("--table", action="store_true",
                       help="print the markdown verdict table the write-up "
                            "carries; refuses while the two disagree")
    ap.add_argument("--map", default=MAP_CSV,
                    help=f"the ownership map (default: {MAP_CSV})")
    ap.add_argument("--verdicts", default=VERDICTS_CSV,
                    help=f"the ledger (default: {VERDICTS_CSV})")
    args = ap.parse_args(argv)
    args.records = load_map(args.map)
    args.verdicts = load_verdicts(args.verdicts)
    if args.table:
        print(render_table(args.records, args.verdicts))
        return 0
    return check(args)


if __name__ == "__main__":
    sys.exit(main())