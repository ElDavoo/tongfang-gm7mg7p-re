#!/usr/bin/env python3
"""A cluster's `refs` is the sum of its members' `refs_<program>`, and not of
their `refs` (issue #343).

`ec/annotations/xdata-clusters.csv` and `ec/annotations/xdata-registers.csv`
sit next to each other and both have a column called `refs`, and they are not
the same quantity. `xdata_register_map.py`'s `cluster_rows_build()` computes a
cluster row as `refs = sum(group[a]["refs"] for a in members)`, where `group` is
the **per-program** group -- so a `program=both` address sitting in a `main-ec`
cluster contributes only its main-EC half. The registers CSV already carries
that half, in the `refs_main_ec` / `refs_pd` columns at 22-23 that #713 added
and `../../docs/findings/xdata-per-program-counts.md` documents.

**The named input is those two columns, not a freshly generated census.** A
check that re-ran `xdata_register_map.py` could only ever compare the census
with itself: the fresh generation and the committed CSV would agree by
construction, and a change to the apportionment would move both together and
be caught by nothing. Reading `refs_main_ec` / `refs_pd` out of the committed
registers CSV is what makes the assertion about the *committed pair*, and it is
why this check needs no image, no decompile and no Ghidra: two file reads.

**What it checks, per cluster, over every row of the committed clusters CSV:**

  * `refs == Σ over addrs of refs_<program>` -- the rule above. This is the
    claim issue #343 asks for, and it is stronger than the corpus total
    `--self-test` checks, because a total cannot say which cluster a change
    landed in.
  * `size == len(addrs)`; `addr_range == min-max(addrs)`, bare when
    `min == max`, which is how the single-address clusters are written and a
    rule rather than a discrepancy; every member present in the registers CSV;
    and every non-`both` member's own `program` equal to its cluster's. These
    three measured intact when the rule above was established, and a change
    that broke one of them would be a second defect rather than a consequence
    of the first -- so they are held here, beside the rule, instead of waiting
    to be rediscovered as a mystery.
  * `Σ cluster refs == Σ registers refs`, **as the weaker claim it is.** The
    `both` split sums back to the same total, so this identity holds whether or
    not any individual cluster is apportioned per program. It is the oracle
    `xdata_register_map.py --self-test` already asserts, kept so that a rule
    above it failing has somewhere to be localised.

**What it does not establish.** Every figure here re-derives from the two
committed CSVs; nothing was read back from hardware and no register was
observed. Passing means the two files' `refs` columns agree under the
definition above -- not that either column counts what a reader assumes it
counts. The write-up is
`../../docs/findings/xdata-cluster-refs-projection.md`.

Usage:
    python3 ec/tools/check_cluster_refs_projection.py
    python3 ec/tools/check_cluster_refs_projection.py --clusters /tmp/after.csv
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)

CLUSTERS = os.path.join(EC, "annotations", "xdata-clusters.csv")
REGISTERS = os.path.join(EC, "annotations", "xdata-registers.csv")

# The named input, as the two columns the registers CSV carries them in. A
# written-out two-entry literal rather than a table derived from the `program`
# column, chosen so that a `program` value it has no half for is a refusal at
# `check()`'s `column is None` branch and not a silent fallback. The spelling is
# `_pd` and not `_pd_image` for the reason `program_suffix()` gives in
# `xdata_register_map.py`, which is where these two were generated.
PER_PROGRAM_REFS = {"main-ec": "refs_main_ec", "pd": "refs_pd"}


def read(path):
    """The rows of a CSV, read the way the tool that wrote it reads it back."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def addrs_of(row):
    """A cluster row's membership, as the list of hex addresses it carries."""
    return row["addrs"].split()


def hexaddr(addr: int) -> str:
    return f"0x{addr:04X}"


def check(clusters_path=CLUSTERS, registers_path=REGISTERS):
    """(problems, population) for one census against its registers CSV.

    `population` is what the run recomputed rather than sampled: every cluster
    row of `clusters_path`, so a red line says how much of the file the rule
    was applied to.
    """
    clusters = read(clusters_path)
    registers = {r["addr"]: r for r in read(registers_path)}

    problems = []
    for row in clusters:
        cid = row["cluster_id"]
        column = PER_PROGRAM_REFS.get(row["program"])
        if column is None:
            problems.append(
                f"{cid}: `program` is `{row['program']}`, which is neither "
                f"`main-ec` nor `pd`, so there is no per-program column to "
                f"recompute this cluster's `refs` from")
            continue

        members = addrs_of(row)
        missing = [a for a in members if a not in registers]
        for addr in missing:
            problems.append(
                f"{cid}: `{addr}` is a member and is not a row of "
                f"{os.path.relpath(registers_path, REPO)}, so this cluster's "
                f"`refs` cannot be recomputed from the named input at all")
        if missing:
            continue

        # A `both` member contributes only its cluster's half. A member whose
        # own `program` is the cluster's contributes all of it, which is why
        # this reads one column rather than branching on the member.
        expected = sum(int(registers[a][column]) for a in members)

        if int(row["refs"]) != expected:
            raw = sum(int(registers[a]["refs"]) for a in members)
            shared = sum(1 for a in members if registers[a]["program"] == "both")
            problems.append(
                f"{cid}: `refs` is {row['refs']}, and the sum of its "
                f"{len(members)} members' `{column}` is {expected}. A cluster's "
                f"`refs` is the census's per-program figure -- the members' "
                f"`refs_<program>`, not their unsuffixed `refs` (which sums to "
                f"{raw} here"
                + (f", because {shared} of them "
                   f"{'is a `program=both` address carrying' if shared == 1 else 'are `program=both` addresses carrying'}"
                   f" a whole count each" if raw != expected else "")
                + ")")
        if int(row["size"]) != len(members):
            problems.append(
                f"{cid}: `size` is {row['size']}, and `addrs` carries "
                f"{len(members)} address(es)")
        want_range = (f"{hexaddr(int(members[0], 16))}-"
                      f"{hexaddr(int(members[-1], 16))}"
                      if len(members) > 1 else hexaddr(int(members[0], 16)))
        if row["addr_range"] != want_range:
            problems.append(
                f"{cid}: `addr_range` is `{row['addr_range']}`, and its "
                f"membership's range is `{want_range}`")
        for addr in members:
            own = registers[addr]["program"]
            if own not in ("both", row["program"]):
                problems.append(
                    f"{cid}: `{addr}` is `program={own}`, so a "
                    f"`{row['program']}` cluster's `{column}` sum is reading a "
                    f"program the cluster does not hold")

    # The weaker identity, kept for what it can localise rather than for what
    # it can prove. See the docstring: it cannot distinguish a per-program
    # projection from a raw one, because the `both` split sums back to the same
    # total.
    cluster_total = sum(int(r["refs"]) for r in clusters)
    register_total = sum(int(r["refs"]) for r in registers.values())
    if cluster_total != register_total:
        problems.append(
            f"the clusters CSV's `refs` sums to {cluster_total} and the "
            f"registers CSV's to {register_total}, so the two files do not "
            f"describe one census")

    return problems, len(clusters)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clusters", default=CLUSTERS,
                        help=f"clusters CSV to check (default: {CLUSTERS})")
    parser.add_argument("--registers", default=REGISTERS,
                        help=f"registers CSV whose per-program `refs` columns "
                             f"are the named input (default: {REGISTERS})")
    args = parser.parse_args(argv)

    if not os.path.exists(args.clusters):
        print(f"{args.clusters} does not exist", file=sys.stderr)
        return 1
    if not os.path.exists(args.registers):
        print(f"{args.registers} does not exist", file=sys.stderr)
        return 1

    problems, population = check(args.clusters, args.registers)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(f"{len(problems)} projection(s) disagree over {population} "
              f"cluster(s)", file=sys.stderr)
        return 1
    print(f"{population} cluster(s) recomputed: every cluster's `refs` is the "
          f"sum of its members' `refs_<program>` in "
          f"{os.path.relpath(args.registers, REPO)} -- the per-program share, "
          f"not the unsuffixed `refs` -- and `size`, `addr_range` and "
          f"membership agree with it")
    return 0


if __name__ == "__main__":
    sys.exit(main())