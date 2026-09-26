#!/usr/bin/env python3
"""Why the guard-off regeneration's moved-rank count fell from 366 to 315.

`test_xdata_cluster_names.py::TheGuardOffRegeneration` asserts
`len(moved) > 300`, over the pair its `guard_off()` builds: the committed
`annotations/xdata-clusters.csv` against a regeneration of the same tree with
the `==` rejection off. The committed census has been re-derived twice since
that case was written, and the count moved **366 -> 315** across those two
re-derivations. `docs/findings/xdata-census-rederivation-checklist.md` records
the fall and guesses at its cause -- "a re-derivation that lands addresses in
already-large clusters would move fewer membership sets" -- and says in place
that the guess is not a measurement.

This is the measurement, and it is the measurement in the shape the guess is
about: both census pairs, keyed on `cluster_key` rather than on `main-ec-NNN`,
so the row a number is about survives the renumbering that produced it. `pair`
prints one pair; `across` prints the flip table between two of them.

**What this does not claim, and the two ways it is easy to overclaim.**

- *A rank is not an identity.* `cluster_id` is a rank, printed as data and
  always beside the key, because the whole question is what happens to a
  cluster when its number changes. A difference in `moved` between two pairs is
  a difference in how two rankings disagree, not a statement about a cluster
  that is still there under its old number.
- *`moved` is not a magnitude of guard perturbation.* The predicate counts a
  rank whose guard-off row holds **different addresses**; over a re-partition
  most such rows are a *substitution* of one same-sized group for another,
  with no address in common, rather than an address added to a large group.
  The tool prints the size-agreement and the total address-slot delta beside
  the count so the two are not read as one number.

Nothing here resolves anything against the firmware. Both censuses are files,
the guard-off one is a regeneration of a committed tree by
`xdata_register_map.py --no-eq-guard` writing to a scratch directory, and the
four inputs this reads are `ec/annotations/xdata-clusters.csv` and
`xdata-registers.csv` (twice over, once per generation). No image is opened, no
register is read back, and no laptop, EC or Windows machine is involved.

`--swept` takes the 43 addresses `annotations/xdata-06c2-06db-timers.md` §1
sweeps as arguments rather than holding a third copy of
`test_xdata_cluster_names.py`'s `SWEPT_43`, so that list has one owner.

Usage:
    python3 xdata_moved_ranks.py pair --old COMMITTED.csv --new GUARD-OFF.csv
    python3 xdata_moved_ranks.py pair --old A --new B --rows
    python3 xdata_moved_ranks.py pair --old A --new B \\
        --old-registers ON.csv --new-registers OFF.csv
    python3 xdata_moved_ranks.py across --old-a A --new-a B --old-b C --new-b D
    python3 xdata_moved_ranks.py across --old-a A --new-a B --old-b C --new-b D \\
        --old-a-registers ONa.csv --new-a-registers OFFa.csv \\
        --old-b-registers ONb.csv --new-b-registers OFFb.csv
    python3 xdata_moved_ranks.py across --old-a A --new-a B --old-b C --new-b D \\
        --swept 0x0460 0x0468 ...
    python3 xdata_moved_ranks.py --self-test
"""
import argparse
import csv
import os
import sys
import tempfile

COLUMNS = ("cluster_id", "program", "size", "refs", "addrs", "cluster_key",
           "cluster_name")


# --------------------------------------------------------------------------
# Reading. A census row is read for the two things every count here is about --
# the rank, which is data, and the key, which is the identity -- and for the
# membership, compared as the string the CSV holds.
# --------------------------------------------------------------------------

def clusters_of(path):
    """{cluster_id: row} from a clusters CSV."""
    with open(path, newline="") as f:
        return {r["cluster_id"]: r for r in csv.DictReader(f)}


def registers_of(path):
    """{addr: row} from a per-address registers CSV."""
    with open(path, newline="") as f:
        return {r["addr"]: r for r in csv.DictReader(f)}


def addrs_of(row):
    """The row's membership as a set."""
    return set(row["addrs"].split())


def keyed_by(rows):
    """{cluster_key: row} for a census. Keys are unique within a census --
    `test_xdata_cluster_names.py::TheContentKey` holds that -- so this is a
    bijective re-keying and the last row wins for none."""
    return {r["cluster_key"]: r for r in rows.values()}


def moved_ranks(committed, off):
    """{cluster_key: (committed row, guard-off row at that rank)} for every
    committed rank the guard-off census names something else at.

    The predicate is the suite's own two lines, string for string, because the
    floor at `test_xdata_cluster_names.py:392` is applied to exactly this and
    a near neighbour of it would be a different claim. A committed rank with
    no row at that number in the guard-off census is not moved and is not
    intact either; `pair` reports those separately rather than folding them
    into either count, which is what keeps `moved + intact == |committed|`
    from being asserted over a census whose two generations are not aligned.
    """
    out = {}
    for cid, row in committed.items():
        other = off.get(cid)
        if other is not None and row["addrs"] != other["addrs"]:
            out[row["cluster_key"]] = (row, other)
    return out


def absent_ranks(committed, off):
    """Committed ranks the guard-off census does not carry."""
    return [cid for cid in sorted(committed) if cid not in off]


# --------------------------------------------------------------------------
# One pair.
# --------------------------------------------------------------------------

def pair_report(label, committed_path, off_path, registers=None):
    """(lines, the two censuses, the moved map) for one committed/guard-off
    pair. `registers` is the pair's optional `(on, off)` registers CSVs, which
    carry §6a's per-address comparison rather than anything cluster-shaped."""
    committed, off = clusters_of(committed_path), clusters_of(off_path)
    moved = moved_ranks(committed, off)
    absent = absent_ranks(committed, off)
    common = [cid for cid in sorted(committed) if cid in off]
    intact = len(common) - len(moved)

    out = [f"pair {label}",
           f"  committed  {committed_path}: {len(committed)} rows",
           f"  guard-off  {off_path}: {len(off)} rows"]

    by_program = {p: 0 for p in sorted({r["program"] for r in committed.values()})}
    for old, _new in moved.values():
        by_program[old["program"]] = by_program.get(old["program"], 0) + 1
    out.append(f"  moved      {len(moved)}  ({', '.join(f'{p} {n}' for p, n in by_program.items())})")
    out.append(f"  intact     {intact}")
    out.append(f"  committed ranks the guard-off census does not carry: {len(absent)}"
               + (f" ({', '.join(absent[:5])}...)" if absent else ""))

    # A moved rank is a *different* cluster at the same number, so the two
    # shapes it can take are worth counting separately: a same-sized
    # substitution, and a real change of size. The first is a ranking
    # disagreement; the second is a perturbation. Reporting only the count
    # above would let the two be read as one number.
    same = sum(1 for old, new in moved.values() if len(addrs_of(old)) == len(addrs_of(new)))
    disjoint = sum(1 for old, new in moved.values() if not (addrs_of(old) & addrs_of(new)))
    slots = sum(len(addrs_of(off[cid]) ^ addrs_of(row)) for cid, row in committed.items() if cid in off)
    out.append(f"  of the moved ranks, {same} hold a guard-off row of the same size and "
               f"{disjoint} share no address with it")
    out.append(f"  guard-off membership delta over the {len(common)} rank(s) the two "
               f"censuses share: {slots} address-slots")

    if registers:
        on, offreg = registers_of(registers[0]), registers_of(registers[1])
        universe = "identical" if set(on) == set(offreg) else "NOT identical"
        changed = sum(1 for a in on if offreg.get(a, on[a])["write"] != on[a]["write"])
        refs = sum(1 for a in on if offreg.get(a, on[a])["refs"] != on[a]["refs"])
        out.append(f"  §6a: address universe {universe} ({len(on)} rows); "
                   f"write changes {changed} of {len(on)}; refs changes {refs} of {len(on)}; "
                   f"references leaving write "
                   f"{sum(int(offreg[a]['write']) - int(on[a]['write']) for a in on if a in offreg)}")

    out.append("")
    out.append(f"  {'cluster_key':<14} {'name':<16} {'committed':<12} {'guard-off':<12} "
               f"{'size':>5} {'delta':>6}  verdict")
    for key in sorted(moved, key=lambda k: (moved[k][0]["cluster_id"], k)):
        old, new = moved[key]
        out.append(f"  {key:<14} {old['cluster_name'] or '-':<16} "
                   f"{old['cluster_id']:<12} {new['cluster_id']:<12} "
                   f"{len(addrs_of(old)):>5} {len(addrs_of(old) ^ addrs_of(new)):>6}  moved")
    for cid in sorted(committed):
        row = committed[cid]
        if cid in off and row["cluster_key"] not in moved:
            out.append(f"  {row['cluster_key']:<14} {row['cluster_name'] or '-':<16} "
                       f"{cid:<12} {cid:<12} {len(addrs_of(row)):>5} {0:>6}  intact")
    return out, committed, off, moved


# --------------------------------------------------------------------------
# Two pairs, compared on the key rather than the rank.
# --------------------------------------------------------------------------

def flip_table(committed_a, off_a, committed_b, off_b):
    """The flip table, as five lists of `cluster_key` over the keys both
    committed censuses carry, plus the two one-sided sets named rather than
    netted off.

    A key is in both committed censuses only if its *membership* is in both:
    `cluster_key` is a content hash over the program and the sorted membership
    (`xdata_register_map.py`), so a key that survived a re-derivation did so
    because nothing about that cluster changed. That is a fact about the hash
    and it is the reason the flipped clusters' committed membership is measured
    separately below rather than assumed to have grown.
    """
    a, b = keyed_by(committed_a), keyed_by(committed_b)
    moved_a, moved_b = set(moved_ranks(committed_a, off_a)), set(moved_ranks(committed_b, off_b))
    shared = sorted(set(a) & set(b))
    return {
        "a": a, "b": b, "moved_a": moved_a, "moved_b": moved_b,
        "shared": shared,
        "a_to_b": [k for k in shared if k in moved_a and k not in moved_b],
        "both": [k for k in shared if k in moved_a and k in moved_b],
        "b_to_a": [k for k in shared if k not in moved_a and k in moved_b],
        "neither": [k for k in shared if k not in moved_a and k not in moved_b],
        "only_a": sorted(set(a) - set(b)),
        "only_b": sorted(set(b) - set(a)),
    }


def deciles(sizes):
    """Ten size cut points, so "the large clusters" is a distribution and not
    an adjective. A tenth is a whole number of rows, so this is a
    nearest-rank read rather than an interpolation, and a set too small to cut
    ten ways is reported as the set it is rather than stretched over ten
    cells."""
    ordered = sorted(sizes)
    if not ordered:
        return "no rows"
    return " ".join(str(ordered[min(len(ordered) - 1, (len(ordered) * i) // 10)])
                    for i in range(10))



def across_report(label_a, committed_a_path, off_a_path,
                  label_b, committed_b_path, off_b_path, rows=False,
                  registers=None):
    committed_a, off_a = clusters_of(committed_a_path), clusters_of(off_a_path)
    committed_b, off_b = clusters_of(committed_b_path), clusters_of(off_b_path)
    t = flip_table(committed_a, off_a, committed_b, off_b)
    out = [f"across {label_a} -> {label_b}",
           f"  keys in both committed censuses: {len(t['shared'])}; in one only: "
           f"{len(t['only_a'])} / {len(t['only_b'])}",
           f"  {len(t['a_to_b']):>4}  moved in {label_a}, intact in {label_b}",
           f"  {len(t['both']):>4}  moved in both",
           f"  {len(t['b_to_a']):>4}  intact in {label_a}, moved in {label_b}",
           f"  {len(t['neither']):>4}  intact in both"]

    only_a_moved = len(t["moved_a"] & set(t["only_a"]))
    only_b_moved = len(t["moved_b"] & set(t["only_b"]))
    # The arithmetic has to close over all four terms, which is why the
    # one-sided sets are split by moved/intact rather than counted once. A
    # difference of two totals that is written as a difference of two
    # subtotals is the half-renumbered transcript §6b's correction is about.
    lhs = len(t["moved_a"]) - len(t["moved_b"])
    rhs = (len(t["a_to_b"]) - len(t["b_to_a"])
           + only_a_moved - only_b_moved)
    out.append(f"  of the one-sided keys, {only_a_moved} moved in {label_a} and "
               f"{only_b_moved} moved in {label_b}")
    out.append(f"  closes: {len(t['moved_a'])} - {len(t['moved_b'])} = {lhs}, over the "
               f"four terms: ({len(t['a_to_b'])} - {len(t['b_to_a'])}) + "
               f"({only_a_moved} - {only_b_moved}) = {rhs}"
               + ("" if lhs == rhs else "   MISMATCH"))

    # The guess, measured on both halves. "How much did the cluster's own
    # membership grow" is zero for every shared key by construction, so the
    # column that can differ is the guard-off delta -- and the size
    # distribution says whether "the large clusters" is even the right
    # description of the set that changed.
    a, b = t["a"], t["b"]
    flipped = [k for k in t["shared"] if (k in t["moved_a"]) != (k in t["moved_b"])]
    grew_any = sum(1 for k in t["shared"] if addrs_of(b[k]) != addrs_of(a[k]))
    census_sizes = [len(addrs_of(row)) for row in b.values()]
    at_least_8 = [row for row in b.values() if len(addrs_of(row)) >= 8]
    out.append("")
    out.append(f"  the flipped set's size distribution, against the census: "
               f"{deciles([len(addrs_of(b[k])) for k in flipped])}")
    out.append(f"                                            the census:  "
               f"{deciles(census_sizes)}")
    out.append(f"  of the {len(at_least_8)} committed cluster(s) of 8 addresses or more, "
               f"{sum(1 for row in at_least_8 if row['cluster_key'] in flipped)} flipped; "
               f"the largest committed cluster is {max(census_sizes) if census_sizes else 0} addresses")
    out.append(f"  shared keys whose committed membership differs between the two "
               f"censuses: {grew_any} of {len(t['shared'])} -- a key is a hash of the "
               f"membership, so this is zero by construction and is printed rather than assumed")
    if registers:
        out.append("")
        out += registers_report(label_a, label_b, registers)
    out.append("")
    # The guard-off delta of each of the four cells, averaged. This is the
    # half of the guess that can differ: a cluster's committed membership
    # cannot grow under a key that survived, so a cell going quiet is the
    # guard's delta closing, not a growing cluster absorbing less.
    def mean_delta(keys, census, guard_off):
        vals = [len(addrs_of(guard_off[census[k]["cluster_id"]]) ^ addrs_of(census[k]))
                for k in keys if census[k]["cluster_id"] in guard_off]
        return f"{sum(vals) / len(vals):.2f}" if vals else "-"
    for title, keys in (("moved -> intact", t["a_to_b"]), ("moved in both", t["both"]),
                        ("intact -> moved", t["b_to_a"]), ("intact in both", t["neither"])):
        out.append(f"  mean guard-off delta over {len(keys):>4} {title:<15} "
                   f"A {mean_delta(keys, a, off_a):>6}   B {mean_delta(keys, b, off_b):>6}")
    out.append("")
    out.append(f"  {'cluster_key':<14} {'name':<16} {'size':>4} {'grew':>5} "
               f"{'delta A':>8} {'delta B':>8}  verdict")
    for key in (flipped if rows else flipped[:12]):
        ra, rb = a[key], b[key]
        da = off_a.get(ra["cluster_id"])
        db = off_b.get(rb["cluster_id"])
        grew = len(addrs_of(rb) - addrs_of(ra))
        out.append(
            f"  {key:<14} {(rb['cluster_name'] or ra['cluster_name'] or '-'):<16} "
            f"{len(addrs_of(rb)):>4} {grew:>5} "
            f"{(len(addrs_of(da) ^ addrs_of(ra)) if da else '-'):>8} "
            f"{(len(addrs_of(db) ^ addrs_of(rb)) if db else '-'):>8}  "
            f"{'moved->intact' if key in t['a_to_b'] else 'intact->moved'}")
    if not rows and len(flipped) > 12:
        out.append(f"  ({len(flipped) - 12} more; --rows for all of them)")
    return out, t


def registers_report(label_a, label_b, registers):
    """§6a's per-address comparison, for both generations and against each
    other.

    Three counts the per-pair line already prints, and the one it cannot: are
    the *same* addresses perturbed in both generations. Two runs can agree on
    210 and disagree on which 210, and that is the difference between "the
    guard is unchanged" and "the guard's total is unchanged".
    """
    on_a, off_a, on_b, off_b = (registers_of(p) for p in registers)

    def perturbed(on, off):
        return {a for a in on if a in off and off[a]["write"] != on[a]["write"]}

    p_a, p_b = perturbed(on_a, off_a), perturbed(on_b, off_b)
    added = set(on_b) - set(on_a)
    out = [f"  §6a across the two generations, over the per-address columns:"]
    for label, on, p in ((label_a, on_a, p_a), (label_b, on_b, p_b)):
        out.append(f"    {label}: write changes {len(p)} of {len(on)}")
    out.append(f"    the perturbed address sets are {'identical' if p_a == p_b else 'DIFFERENT'}"
               f" ({len(p_a - p_b)} only in {label_a}, {len(p_b - p_a)} only in {label_b})")
    out.append(f"    {label_b} adds {len(added)} address(es) to the universe and "
               f"{len(added & p_b)} of them are perturbed")
    return out


# --------------------------------------------------------------------------
# The 43 swept addresses, as a cross-reference and not a list of their own.
# --------------------------------------------------------------------------
def swept_report(committed_a, committed_b, table, addrs):
    """For each address, every committed cluster that holds it in either
    generation, and whether that cluster is one of the flipped ones.

    *Every*, not the first: an XDATA address both programs touch is a member
    of a `main-ec` cluster and of a `pd` one at the same time, and a
    cross-reference that reported one of the two would be right by accident on
    43 of 43 addresses and wrong on 5 of them. The second row per address is
    not noise, and the summary counts the `pd` holders separately.
    """
    a, b = keyed_by(committed_a), keyed_by(committed_b)
    index_a = {addr: [k for k, row in a.items() if addr in addrs_of(row)]
               for addr in addrs}
    index_b = {addr: [k for k, row in b.items() if addr in addrs_of(row)]
               for addr in addrs}
    out = [f"  swept addresses: {len(addrs)}",
           f"  {'address':<8} {'cluster_key':<14} {'program':<8} "
           f"{'rank A':<12} {'rank B':<12} verdict"]
    keys = set()
    for addr in sorted(addrs):
        held = index_a.get(addr, [])
        rows = [(k, a[k], b.get(k)) for k in held]
        rows += [(k, None, b[k]) for k in index_b.get(addr, []) if k not in held]
        if not rows:
            out.append(f"  {addr:<8} {'-':<14} {'-':<8} {'-':<12} {'-':<12} "
                       f"in no committed cluster")
            continue
        for key, ra, rb in sorted(rows):
            keys.add(key)
            in_a, in_b = key in table["moved_a"], key in table["moved_b"]
            if in_a and in_b:
                verdict = "moved in both"
            elif in_a or in_b:
                verdict = "FLIPPED" if (ra is not None and rb is not None) \
                    else ("moved in A" if in_a else "moved in B")
            else:
                verdict = "intact in both"
            out.append(f"  {addr:<8} {key:<14} {(rb or ra)['program']:<8} "
                       f"{(ra['cluster_id'] if ra else '-'):<12} "
                       f"{(rb['cluster_id'] if rb else '-'):<12} {verdict}")
    pd_keys = {k for k in keys if (b.get(k) or a[k])["program"] == "pd"}
    flipped = keys & (set(table["a_to_b"]) | set(table["b_to_a"]))
    second = sum(1 for addr in addrs
                 if len(index_b.get(addr) or index_a.get(addr)) > 1)
    wanted = set(addrs)
    complete = [k for k in keys if wanted <= addrs_of(b.get(k) or a[k])]
    out.append(f"  {len(keys)} committed cluster(s) hold at least one of the "
               f"{len(addrs)}: {len(keys) - len(pd_keys)} main-ec, {len(pd_keys)} pd; "
               f"{len(complete)} hold all of them; {second} address(es) have a second holder")
    out.append(f"  of those {len(keys)}, {len(flipped)} flipped; "
               f"{len(keys & table['moved_a'])} moved in A and "
               f"{len(keys & table['moved_b'])} moved in B")
    return out



# --------------------------------------------------------------------------
# The self-test. Synthetic censuses, because every property under test is a
# property of the bookkeeping and not of the EC: what the tool is for is
# reading two real censuses, and a fixture that could not fail would leave
# that untested.
# --------------------------------------------------------------------------

def write_census(directory, name, rows):
    """A clusters CSV holding `(cluster_id, program, addrs, cluster_key)`. The
    key is written rather than derived from the id, because a fixture whose
    key is a function of its rank cannot fail a test about a key surviving a
    renumbering -- which is the property half of this tool is about."""
    path = os.path.join(directory, name)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(COLUMNS))
        writer.writeheader()
        for cid, program, addrs, key in rows:
            writer.writerow({"cluster_id": cid, "program": program,
                             "size": len(addrs), "refs": 0,
                             "addrs": " ".join(addrs), "cluster_key": key,
                             "cluster_name": ""})
    return path


def write_registers(directory, name, rows):
    """A registers CSV holding `(addr, write)`. Only the two columns §6a's
    comparison reads are written, and a column the tool does not read is a
    column a fixture cannot accidentally make true."""
    path = os.path.join(directory, name)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["addr", "write", "refs"])
        writer.writeheader()
        for addr, write in rows:
            writer.writerow({"addr": addr, "write": write, "refs": "1"})
    return path


def self_test() -> int:
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {text}")

    print("xdata_moved_ranks.py --self-test")
    tmp = tempfile.mkdtemp(prefix="xdata-moved-ranks-")

    # Fixture vocabulary. `k` + 12 hex is the key shape
    # `xdata_register_map.py` writes, so the fixtures cannot pass by being
    # shaped unlike a real census, and a key is attached to a *membership*
    # rather than to a rank -- a key that changed content would be a fixture
    # asserting the impossible.
    def key(n):
        return f"k{n:012d}"

    # k1 and k2 swap their memberships between the committed census and the
    # guard-off one, which is the substitution the real pair is mostly made of;
    # k3 and k4 are the ranks the guard leaves alone, so the census has both a
    # mover and a non-mover, and the two programs have a mover and not. k8
    # holds an address k1 also holds, which is what an XDATA address both
    # programs touch looks like and what a swept-address cross-reference has to
    # report twice.
    committed_rows = [("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
                      ("main-ec-002", "main-ec", ["0x10"], key(2)),
                      ("pd-001", "pd", ["0x20", "0x21"], key(3)),
                      ("main-ec-003", "main-ec", ["0x40"], key(4)),
                      ("pd-002", "pd", ["0x0E", "0x50"], key(8))]
    committed = write_census(tmp, "a-committed.csv", committed_rows)
    off_rows = [("main-ec-001", "main-ec", ["0x0E", "0x10"], key(1)),
                ("main-ec-002", "main-ec", ["0x0F"], key(2)),
                ("pd-001", "pd", ["0x20", "0x21"], key(3)),
                ("main-ec-003", "main-ec", ["0x40"], key(4)),
                ("pd-002", "pd", ["0x0E", "0x50"], key(8))]
    off = write_census(tmp, "a-off.csv", off_rows)

    c, o = clusters_of(committed), clusters_of(off)
    moved = moved_ranks(c, o)
    check(set(moved) == {key(1), key(2)},
          "a rank whose guard-off row holds a different membership is moved, "
          "and the two that hold their own membership are not")

    # The predicate the floor is applied to, restated here rather than called:
    # if this and `moved_ranks` ever disagree, one of them is no longer the
    # number `test_xdata_cluster_names.py:392` asserts over.
    inline = [cid for cid, row in c.items()
              if cid in o and row["addrs"] != o[cid]["addrs"]]
    check(len(moved) == len(inline) == 2
          and sorted(row[0]["cluster_id"] for row in moved.values()) == inline,
          f"the tool's count equals the suite's own two-line predicate over "
          f"the same pair ({len(inline)} moved)")

    check(absent_ranks(c, o) == [],
          "a committed rank the guard-off census does not carry is reported, "
          "not folded into either count")

    # And the reported case: a committed rank with no row in the regeneration.
    short_off = write_census(tmp, "a-off-short.csv",
                             [r for r in off_rows if r[0] != "main-ec-003"])
    check(absent_ranks(c, clusters_of(short_off)) == ["main-ec-003"],
          "a committed rank missing from the guard-off census is named")

    # The per-program split, over a census that has one of each.
    lines, _c, _o, _m = pair_report("fixture", committed, off, None)
    check(any("main-ec 2" in ln and "pd 0" in ln for ln in lines),
          "the moved ranks are split by program, so a `pd` mover is not "
          "hidden inside a `main-ec` total")
    check(any("moved      2" in ln for ln in lines)
          and any("intact     3" in ln for ln in lines),
          "moved and intact are reported as separate counts, and they sum to "
          "the ranks the two censuses share")

    # Both flip directions, and the arithmetic over all four terms. B is the
    # same committed census with the other two movers: k1 stops moving and k3
    # starts.
    b_committed = write_census(tmp, "b-committed.csv", committed_rows)
    b_off = write_census(tmp, "b-off.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
        ("main-ec-002", "main-ec", ["0x12"], key(2)),
        ("pd-001", "pd", ["0x20", "0x23"], key(3)),
        ("main-ec-005", "main-ec", ["0x40"], key(4)),
        ("pd-003", "pd", ["0x0E", "0x50"], key(8))])
    lines, t = across_report("A", committed, off, "B", b_committed, b_off)
    check(t["a_to_b"] == [key(1)] and t["b_to_a"] == [key(3)],
          "both flip directions are reported separately, each naming its key")
    check(t["both"] == [key(2)] and t["neither"] == [key(4), key(8)],
          "a cluster that moved in both and one that moved in neither are "
          "their own rows, not the absence of the other two -- and k4's and "
          "k8's ranks moved on the way, which is a renumbering and not a "
          "membership change")
    check(any("MISMATCH" in ln for ln in lines) is False,
          "the moved-count difference closes over the four terms it is made of")

    # Keys present in only one generation, named rather than netted off.
    c_committed = write_census(tmp, "c-committed.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
        ("main-ec-009", "main-ec", ["0x50"], key(7))])
    c_off = write_census(tmp, "c-off.csv", [("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1))])
    _lines, t2 = across_report("A", committed, off, "C", c_committed, c_off)
    check(t2["only_a"] == [key(2), key(3), key(4), key(8)]
          and t2["only_b"] == [key(7)],
          "a key in only one generation is named as such, in both directions")

    # The swept-address cross-reference, over the same fixture. `0x0E` is in
    # k1 and in k8, and reporting only the first would be right by accident
    # for a swept set with no `pd` holder in it.
    lines = swept_report(c, clusters_of(b_committed), t, ["0x0E", "0x40"])
    check(sum(1 for ln in lines if ln.strip().startswith("0x0E ")) == 2,
          "an address both programs touch is reported once per committed "
          "cluster holding it, not once")
    check(sum(1 for ln in lines if "FLIPPED" in ln) == 1
          and any("k000000000004" in ln and "intact in both" in ln for ln in lines)
          and any("2 main-ec, 1 pd" in ln for ln in lines),
          "a cluster that flipped is labelled FLIPPED, one that did not is "
          "not, and the summary counts the `pd` holders separately")

    # §6a across two generations. The same perturbed count over two different
    # address sets is the case a per-pair line cannot see, so the fixture
    # moves one perturbed address and keeps the count at two.
    on_a = write_registers(tmp, "a-on.csv", [("0x60", "3"), ("0x61", "1"), ("0x62", "0")])
    off_a = write_registers(tmp, "a-guard.csv", [("0x60", "1"), ("0x61", "1"), ("0x62", "0")])
    on_b = write_registers(tmp, "b-on.csv", [("0x60", "3"), ("0x61", "0"), ("0x62", "0"),
                                             ("0x63", "4")])
    off_b = write_registers(tmp, "b-guard.csv", [("0x60", "3"), ("0x61", "0"), ("0x62", "5"),
                                                 ("0x63", "4")])
    lines = registers_report("A", "B", (on_a, off_a, on_b, off_b))
    check(sum(1 for ln in lines if ln.startswith("    the perturbed address sets are identical") or
              ln.startswith("    the perturbed address sets are DIFFERENT")) == 1,
          "whether the two generations perturb the same addresses is reported "
          "on its own, not inferred from two matching counts")
    check(any("DIFFERENT (1 only in A, 1 only in B)" in ln for ln in lines)
          and any("B adds 1 address(es) to the universe and 0 of them are perturbed" in ln
                  for ln in lines),
          "two runs can agree on a count and disagree on which addresses, and "
          "an address a re-derivation adds can be outside the guard's reach "
          "entirely")

    print(f"  {'FAILED' if bad else 'all checks passed'}"
          + (f" ({bad})" if bad else ""))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", choices=("pair", "across"),
                    help="one committed/guard-off pair, or two of them compared")
    ap.add_argument("--old", help="committed clusters CSV (pair)")
    ap.add_argument("--new", help="guard-off clusters CSV (pair)")
    ap.add_argument("--old-a", help="committed clusters CSV of pair A (across)")
    ap.add_argument("--new-a", help="guard-off clusters CSV of pair A (across)")
    ap.add_argument("--old-b", help="committed clusters CSV of pair B (across)")
    ap.add_argument("--new-b", help="guard-off clusters CSV of pair B (across)")
    ap.add_argument("--old-registers", help="guard-on registers CSV of the pair (pair)")
    ap.add_argument("--new-registers", help="guard-off registers CSV of the pair (pair)")
    ap.add_argument("--old-a-registers", help="guard-on registers CSV of pair A (across)")
    ap.add_argument("--new-a-registers", help="guard-off registers CSV of pair A (across)")
    ap.add_argument("--old-b-registers", help="guard-on registers CSV of pair B (across)")
    ap.add_argument("--new-b-registers", help="guard-off registers CSV of pair B (across)")
    ap.add_argument("--label", help="what to call the pair in the report "
                                    "(default: the committed CSV's path)")
    ap.add_argument("--label-a", help="what to call pair A in the report (across)")
    ap.add_argument("--label-b", help="what to call pair B in the report (across)")
    ap.add_argument("--rows", action="store_true",
                    help="print every flipped cluster rather than the first twelve")
    ap.add_argument("--swept", nargs="+", metavar="ADDR",
                    help="cross-reference these addresses against the clusters "
                         "holding them (across)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.mode:
        ap.error("a mode is required: pair, across, or --self-test")

    if args.mode == "pair":
        if not (args.old and args.new):
            ap.error("pair needs --old (committed) and --new (guard-off)")
        registers = ((args.old_registers, args.new_registers)
                     if args.old_registers and args.new_registers else None)
        if args.old_registers and not args.new_registers:
            ap.error("--old-registers and --new-registers go together")
        lines, _c, _o, _m = pair_report(args.label or args.old, args.old,
                                        args.new, registers)
        print("\n".join(lines))
        return 0

    missing = [f"--{n}" for n, v in (("old-a", args.old_a), ("new-a", args.new_a),
                                     ("old-b", args.old_b), ("new-b", args.new_b))
               if not v]
    if missing:
        ap.error("across needs " + ", ".join(missing))
    quad = (args.old_a_registers, args.new_a_registers,
            args.old_b_registers, args.new_b_registers)
    if any(quad) and not all(quad):
        ap.error("the four --*-registers flags go together, and across needs "
                 "both generations' guard-on and guard-off registers CSVs")
    lines, table = across_report(args.label_a or args.old_a, args.old_a,
                                 args.new_a, args.label_b or args.old_b,
                                 args.old_b, args.new_b, rows=args.rows,
                                 registers=quad if all(quad) else None)
    print("\n".join(lines))
    if args.swept:
        print()
        print("\n".join(swept_report(clusters_of(args.old_a),
                                     clusters_of(args.old_b), table, args.swept)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
