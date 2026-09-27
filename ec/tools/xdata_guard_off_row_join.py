#!/usr/bin/env python3
"""The row-level join issue #832 asked for: what `--no-eq-guard` moves, at census scale.

`docs/findings/xdata-cluster-names-guard-off-recipe.md` runs the census twice
and reports what moved for **nine hand-named clusters**. Everything else the
tree has said about this flag has been counted over clusters or over names.
The 1,326 rows of `annotations/xdata-registers.csv` have never been joined to
a regeneration row by row, so "what does the flag do" has no answer at the only
granularity a reader of that CSV is holding.

This is that join. It takes a committed pair and a guard-off pair and prints
four things, each against a denominator: the register rows whose columns differ,
split by the `program` column; the `cluster_key`s that move; how many of the
moved keys' rows change rank as well, which is where the cluster-level count
and the row-level count stop being the same number; and what became of each of
the committed hand names.

**It writes nothing, and that is the point rather than a property.** The
invariant this flag exists to protect is that no `--no-eq-guard` run touches a
committed path -- `xdata_register_map.py` refuses the flag outright against
`OUT_REGISTERS`/`OUT_CLUSTERS` -- and a report that measured the guard by
writing a census is a report one argument away from writing it in the wrong
place. There is no `--write`, no `--out-`, and no code path here that opens a
file for writing at all, so the two censuses have to be produced by a
separate run and handed in.

**The join key is `addr` alone, and that is checked rather than assumed.** All
1,326 rows of the committed CSV carry a distinct `addr`, so a `main-ec` row and
a `pd` row cannot collapse into one another -- but that is a property of this
file on this tree, not a property of the format, and a census that gained an
address the other program already has would make a one-column join quietly
wrong. So the report measures the distinct-address count on both inputs and
prints it, and prints separately the addresses that sit under more than one
`program` value -- the question that decides whether one key really is one
population. An address present in one input and not the other is reported as
**its own bucket**, never dropped: a row that disappeared is a different fact
from a row that did not move, and a join that silently drops the first reports
the second.

**The `refs` column is included because the committed figure for it is 0**, and
a report that omits the column that does not move is a report that cannot be
told apart from one that never looked. The `0 of 1,326` here is reproduced from
the two CSVs, not copied from §6a; that the two agree is the point, and
`test_xdata_guard_off_row_join.py` holds the published figures to the files the
run actually wrote rather than to a fresh run of the recipe that wrote them.

**A row that moves under this flag is different under this flag, never
mis-clustered.** Both classifications are a reading of the same occurrences
under a different rule, and which one is the better description of the firmware
is not a question these two files can settle. That is the same "not found by
this method" line `check_cluster_citations.py` and `annotations/registers.yaml`
both draw, and this report keeps it: `differs` is what it says.

Nothing here resolves anything against the firmware. The inputs are four CSVs
and the tool's own two constants, and a guard-off pair is produced by
`xdata_register_map.py --no-eq-guard` writing to a scratch directory. No image
is opened, no register is read back, and no laptop, EC or Windows machine is
involved.

Usage:
    python3 xdata_guard_off_row_join.py \\
        --off-clusters /tmp/off-clusters.csv \\
        --off-registers /tmp/off-registers.csv
    python3 xdata_guard_off_row_join.py \\
        --off-clusters A --off-registers B \\
        --committed-clusters C --committed-registers D
"""
import argparse
import collections
import importlib.util
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EC = HERE.parent

_spec = importlib.util.spec_from_file_location(
    "xdata_register_map", HERE / "xdata_register_map.py")
xrm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xrm)

COMMITTED_CLUSTERS = EC / "annotations" / "xdata-clusters.csv"
COMMITTED_REGISTERS = EC / "annotations" / "xdata-registers.csv"

# The columns this report joins on, in the order it prints them. `cluster_id` is
# a *rank* and `cluster_key` a content hash, so a row whose id changed and a row
# whose key changed are two different facts and neither implies the other; the
# report counts them separately and crosses them, which is the whole of the
# reconciliation with the cluster-level "15". `refs` and `write` are the two
# §6a measures, held here for the reason in the module docstring: the one that
# does not move is what makes the one that does readable.
COLUMNS = ("cluster_id", "cluster_key", "refs", "write")

# The three values the `program` column takes. Held as a list rather than
# derived from the data so a fourth program cannot appear as a silently absent
# bucket: a split whose buckets are read off the rows being split is a split
# that reports whatever it is given.
PROGRAMS = ("main-ec", "pd", "both")


def read_rows(path):
    """The rows of a census CSV, or [] when there is no file to read.

    `xdata_register_map.py`'s own reader, for the same reason it has one: a
    census written before a column existed is still a census, and a missing
    column is a row without that field rather than a crash.
    """
    return xrm.load_cluster_rows(path)


def registers_by_addr(rows):
    """{addr: row}, or None when `addr` is not a key of this file.

    `None` rather than a dict because a registers CSV read as clusters rows is
    a missing file, and a silent `{}` would turn "the file is not there" into
    "no row moved".
    """
    if not rows or "addr" not in rows[0]:
        return None
    return {r["addr"]: r for r in rows}


def address_key(rows):
    """(rows, distinct addresses, addresses under more than one program).

    The join key is `addr` alone, so what has to be measured is whether that
    can lose a row: two rows sharing an address would be one key holding two
    populations, and the count that came back would be about whichever of them
    the dict kept. Distinct addresses is the direct answer, and the third
    number is the one the "does not this collapse a `main-ec` row into a `pd`
    row" question is actually about -- an address touched by both programs is
    two rows in this census and one key, which is why the two programs are
    split in the report rather than summed.
    """
    by_addr = collections.defaultdict(set)
    for row in rows:
        by_addr[row.get("addr", "")].add(row.get("program", ""))
    shared = sum(1 for programs in by_addr.values() if len(programs) > 1)
    return len(rows), len(by_addr), shared


def bucket(addr, on, off):
    """Where one address sits, as a label the report can count.

    Three buckets and no fourth: both censuses agree on the address universe,
    or they do not, and a row in only one of them is not a row that did not
    move. The report prints the two single-sided counts whatever they are, so
    this returning "both" everywhere is a measurement rather than a constant.
    """
    if addr in on and addr in off:
        return "both"
    return "committed only" if addr in on else "guard-off only"


def by_program(on, off, column):
    """({program: [differing, rows]}, {undeclared program: rows}) for `column`.

    The denominator is the *shared* rows of that program, not every row of it,
    so a cell cannot be read as a fraction of rows the join never compared.

    The second slot exists because `PROGRAMS` is a hand-written list and a
    census that grew a fourth program would otherwise be dropped from the
    split with nothing said -- every per-program line would still add up to the
    total, because the total is summed over what was counted, and the missing
    bucket would be invisible in exactly the way the hand-written list was
    supposed to prevent. It is empty on this tree, and the report says so.
    """
    counts = {p: [0, 0] for p in PROGRAMS}
    undeclared = collections.Counter()
    for addr in set(on) & set(off):
        program = on[addr].get("program", "")
        if program not in counts:
            undeclared[program] += 1
            continue
        counts[program][1] += 1
        if on[addr].get(column, "") != off[addr].get(column, ""):
            counts[program][0] += 1
    return counts, undeclared


def cross_tab(on, off):
    """(both, rank only, cluster only, neither) for `cluster_id`/`cluster_key`.

    The two columns crossed, because that is the question the cluster-level
    count cannot answer: a row can keep its rank and change which cluster the
    rank is over, and one cluster-level figure per generation would not see
    that row at all.
    """
    out = collections.Counter()
    for addr in set(on) & set(off):
        rank = on[addr].get("cluster_id", "") != off[addr].get("cluster_id", "")
        key = on[addr].get("cluster_key", "") != off[addr].get("cluster_key", "")
        out[(rank, key)] += 1
    return (out[(True, True)], out[(True, False)], out[(False, True)],
            out[(False, False)])


def moved_keys(on_clusters, off_clusters):
    """(moved, new_keys, per-moved-key outcome) over the two clusters CSVs.

    The third slot is the `--map` rule, read the same way `map_census()` reads
    it: a committed key absent from the guard-off census is looked up by
    membership and called *reached* only if it scores at least
    `CARRY_MIN_JACCARD` against something. `jaccard` and `CARRY_MIN_JACCARD`
    are the tool's own, imported rather than re-derived -- a second copy of the
    carry rule in this file would be a second number for the same threshold,
    and the two would drift the way every other hand-copied constant here has.
    """
    by_key = {r.get("cluster_key", ""): r for r in off_clusters}
    moved, outcomes = [], []
    for row in on_clusters:
        key = row.get("cluster_key", "")
        if not key or key in by_key:
            continue
        addrs = set(row.get("addrs", "").split())
        score, hit = max(((xrm.jaccard(addrs, set(r.get("addrs", "").split())), r)
                          for r in off_clusters), default=(0.0, None),
                         key=lambda t: t[0])
        outcomes.append({
            "key": key, "cluster_id": row.get("cluster_id", ""),
            "reached": hit if score >= xrm.CARRY_MIN_JACCARD else None,
            "jaccard": score,
        })
        moved.append(key)
    new_keys = {r.get("cluster_key", "") for r in off_clusters} \
        - {r.get("cluster_key", "") for r in on_clusters}
    return moved, sorted(new_keys), outcomes


def names_report(on_clusters, off_clusters, seeded):
    """One record per committed hand name, from `carry_names()` itself.

    Not a re-derivation of the carry: the question "does this name still
    resolve, and how did it get here" is answered by running the tool's own
    rule over the two censuses, because that is the run the guard-off census
    actually made and anything else would be a second opinion about it.
    """
    _names, report = xrm.carry_names(on_clusters, seeded, off_clusters)
    by_id = {r["cluster_id"]: r for r in off_clusters}
    out = []
    for row in sorted((r for r in on_clusters if r.get("cluster_name")),
                      key=lambda r: r["cluster_name"]):
        name = row["cluster_name"].strip()
        landed = [r for r in report if r["name"] == name]
        here = landed[0] if landed else None
        # The key the name's cluster holds *now*, which is not the key the
        # carry came from: a name seeded by key and found again is on the key
        # it always had, and one carried on overlap is on a key the committed
        # census has never seen. Both are the same field read two ways, so the
        # report prints the two keys rather than a verdict about them.
        landed_in = by_id[here["cluster_id"]] if here else {}
        out.append({
            "name": name,
            "from_id": row.get("cluster_id", ""), "from_key": row["cluster_key"],
            "from_addrs": len(row.get("addrs", "").split()),
            "resolves": here is not None,
            "to_id": landed_in.get("cluster_id", ""),
            "to_key": landed_in.get("cluster_key", ""),
            "how": here["how"] if here else "none",
            "jaccard": here["jaccard"] if here else 0.0,
            "to_addrs": len(landed_in.get("addrs", "").split()),
        })
    return out


def report(committed_clusters, committed_registers, off_clusters, off_registers,
           stream=None):
    """Print the join to `stream` as `key: value` lines. Writes no file.

    Key/value rather than prose because the write-up quotes these lines and a
    suite reads them back: a figure a reader can grep is a figure a test can
    hold, and a report only a human can parse is neither. Every count carries
    its denominator on the same line for the same reason.
    """
    stream = sys.stdout if stream is None else stream
    on_raw, off_raw = read_rows(committed_registers), read_rows(off_registers)
    on, off = registers_by_addr(on_raw), registers_by_addr(off_raw)
    if on is None or off is None:
        raise SystemExit("both --*-registers arguments must name a per-address "
                         "registers CSV (one row per address, an `addr` column)")
    on_rows, off_rows = read_rows(committed_clusters), read_rows(off_clusters)
    seeded = xrm.load_cluster_names()

    def say(key, value):
        print(f"{key}: {value}", file=stream)

    shared = sorted(set(on) & set(off))
    places = collections.Counter(bucket(a, on, off) for a in set(on) | set(off))
    on_n, on_addrs, on_shared = address_key(on_raw)
    off_n, off_addrs, off_shared = address_key(off_raw)
    say("join key", "addr")
    say("committed rows", f"{on_n} over {on_addrs} distinct addresses")
    say("guard-off rows", f"{off_n} over {off_addrs} distinct addresses")
    say("addresses under more than one program",
        f"{on_shared} committed, {off_shared} guard-off")
    say("addresses compared", f"{len(shared)} in both")
    say("addresses committed only", places["committed only"])
    say("addresses guard-off only", places["guard-off only"])

    undeclared = collections.Counter()
    for column in COLUMNS:
        split, missing = by_program(on, off, column)
        undeclared |= missing
        say(f"rows whose {column} differs",
            f"{sum(n for n, _ in split.values())} of {len(shared)}")
        for program in PROGRAMS:
            changed, rows = split[program]
            say(f"  {program}", f"{changed} of {rows}")
    # Printed unconditionally and read as "none" rather than as a zero: a line
    # that only appears when there is something to say is a line nobody can
    # tell apart from a rule that stopped running.
    say("rows whose program is not in the declared split",
        ", ".join(f"{p} {n}" for p, n in sorted(undeclared.items())) or "none")

    both, rank_only, key_only, neither = cross_tab(on, off)
    say("cluster_id and cluster_key together",
        f"both change {both}, rank only {rank_only}, key only {key_only}, "
        f"neither {neither}")
    touched = {on[a]["cluster_key"] for a in shared
               if on[a]["cluster_key"] != off[a]["cluster_key"]}
    moved, new_keys, outcomes = moved_keys(on_rows, off_rows)
    say("clusters", f"committed {len(on_rows)}, guard-off {len(off_rows)}")
    say("cluster_key that moves", f"{len(moved)} of {len(on_rows)} committed "
        f"keys are absent from the guard-off set; {len(new_keys)} guard-off "
        f"keys are new")
    say("  distinct committed keys a key-changing row sits in", len(touched))
    say("  of those, absent from the guard-off set",
        len([k for k in touched if k in set(moved)]))
    reached = [o for o in outcomes if o["reached"] is not None]
    say("  reach a new cluster on overlap", f"{len(reached)} of {len(moved)} "
        f"at or above {xrm.CARRY_MIN_JACCARD:.2f}")
    say("  reach none", f"{len(outcomes) - len(reached)} of {len(moved)}")
    for outcome in sorted(outcomes, key=lambda o: -o["jaccard"]):
        say(f"    {outcome['cluster_id']}", f"{outcome['key']} -> "
            f"{(outcome['reached'] or {}).get('cluster_id', 'none')} at "
            f"{outcome['jaccard']:.2f}")

    named = names_report(on_rows, off_rows, seeded)
    for record in named:
        key = ("same" if record["from_key"] == record["to_key"]
               else f"changed {record['from_key']} -> {record['to_key']}")
        say(f"name {record['name']}",
            f"{record['from_id']} -> {record['to_id'] or 'unresolved'}, key "
            f"{key}, {record['from_addrs']} -> {record['to_addrs']} addrs, "
            f"carried {record['how']} at {record['jaccard']:.2f}")
    say("names", f"{len(named)} committed, "
        f"{sum(1 for r in named if r['resolves'])} resolve in the guard-off "
        f"census")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--committed-clusters", default=str(COMMITTED_CLUSTERS),
                    help=f"committed clusters CSV (default: {COMMITTED_CLUSTERS})")
    ap.add_argument("--committed-registers", default=str(COMMITTED_REGISTERS),
                    help=f"committed per-address CSV (default: "
                         f"{COMMITTED_REGISTERS})")
    ap.add_argument("--off-clusters", required=True,
                    help="a regeneration's clusters CSV -- the guard-off pair's "
                         "cluster half, from a run writing to a scratch path")
    ap.add_argument("--off-registers", required=True,
                    help="a regeneration's per-address CSV, from the same run")
    args = ap.parse_args()
    for label in ("off_clusters", "off_registers"):
        if not os.path.exists(getattr(args, label)):
            ap.error(f"--{label.replace('_', '-')} does not exist: "
                     f"{getattr(args, label)} -- produce it with "
                     "`xdata_register_map.py --no-eq-guard` pointed at scratch "
                     "outputs, which the flag refuses to be given the "
                     "committed paths")
    report(args.committed_clusters, args.committed_registers,
           args.off_clusters, args.off_registers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
