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
prints one pair; `across` prints the flip table between two of them; `cause`
follows the row a rank carried into the other generation, which is the step
`xdata-moved-ranks-fall.md` §4 named and did not take.

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

`cause` is the one mode whose output is a *rate*, and the rate is the whole
of it: two mechanisms make opposite predictions about the clusters that
stopped moving, and a rate the cells that did *not* flip show at the same rate
is not a mechanism either. So the two control cells are counted exactly the way
the two flipped ones are, and the population the rates are read against -- every
guard-off key of one generation, and where it lands in the other -- is printed
above them. The membership a substitution carries is followed into the other
census per program, because an XDATA address both programs touch has two homes
and a lookup that reports the first is right by accident.

**What `cause` cannot do**, which is why its output is located-or-null and not
a verdict: the working-page and added-address counts say which side of a
substitution those addresses landed on. They are a necessary-condition proxy
for "the co-reading matrix re-clustered this row", not a demonstration that it
did, and the mode does not compare the matrix either way.

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
    python3 xdata_moved_ranks.py cause --old-a A --new-a B --old-b C --new-b D \\
        --old-a-registers ONa.csv --new-a-registers OFFa.csv \\
        --old-b-registers ONb.csv --new-b-registers OFFb.csv
    python3 xdata_moved_ranks.py cause --old-a A --new-a B --old-b C --new-b D \\
        --old-a-registers ONa.csv --new-a-registers OFFa.csv \\
        --old-b-registers ONb.csv --new-b-registers OFFb.csv \\
        --page 0x0300 0x05FF --rows
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
    not noise, and the summary counts the `pd` holders separately. Its
    second-holder count is over the rows this loop makes -- the union of both
    generations' holders -- so the summary cannot disagree with the rows above
    it.
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
    # The loop's rows are kept as well as printed, so the second-holder count
    # below is over the rows this loop made rather than a second reading of the
    # two holder indexes -- which is how the count and the loop came to
    # disagree, the `or` having picked one generation without saying which. A
    # list rather than a map because the loop is over `sorted(addrs)`, so an
    # address passed twice is printed twice and is counted once per visit
    # rather than collapsed into one.
    printed = []
    for addr in sorted(addrs):
        held = index_a.get(addr, [])
        rows = [(k, a[k], b.get(k)) for k in held]
        rows += [(k, None, b[k]) for k in index_b.get(addr, []) if k not in held]
        printed.append(rows)
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
    second = sum(1 for rows in printed if len(rows) > 1)
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
# Where a rank's substitution went. `across` asks whether a key moved; this
# asks about the row that was sitting at the rank when it did, because that is
# what the two candidate mechanisms make opposite predictions about. A
# re-partition that merely reordered predicts the substitution is still in the
# other generation, at a different rank. The added addresses re-clustering the
# working page predicts it is not, and its members are drawn from the page.
# Neither is assumed here: both are counted, and the two cells that did not
# flip are counted the same way, because a rate the quiet cells show at the
# same rate is not a mechanism.
# --------------------------------------------------------------------------

def rank_of(row):
    """(program, integer rank) from a `cluster_id` like `main-ec-014`.

    The number is a rank *within* its program: `pd-002` and `main-ec-002` are
    not two places in one ordering, so a difference between two rows of
    different programs is `None` rather than a number that invites a
    comparison nobody asked for.
    """
    program, _, num = row["cluster_id"].rpartition("-")
    return program, int(num)


def rank_delta(old, new):
    """The signed rank difference, or None across programs."""
    (prog_old, num_old), (prog_new, num_new) = rank_of(old), rank_of(new)
    return None if prog_old != prog_new else num_new - num_old


def added_addresses(registers):
    """`set(on_b) - set(on_a)`: the addresses a re-derivation added.

    `registers_report` already prints the *size* of this set; the page test
    needs the membership, so it is derived here from the same two guard-on
    registers CSVs rather than read out of
    `annotations/xdata-cluster-names.csv`'s prose about it, which keeps
    editing that note from being able to move a count.
    """
    on_a, _off_a, on_b, _off_b = (registers_of(path) for path in registers)
    return set(on_b) - set(on_a)


def holders_by_program(off):
    """{program: {addr: [cluster_key, ...]}} over one census.

    Per program rather than flat, because an XDATA address both programs touch
    has a `main-ec` home and a `pd` home at the same instant. A flat index
    hands a `main-ec` row's addresses to a `pd` row half the time and is right
    by accident the other half -- the mistake `swept_report` is written not to
    make, and the one that is invisible at 43 addresses.
    """
    index = {}
    for key, row in keyed_by(off).items():
        for addr in addrs_of(row):
            index.setdefault(row["program"], {}).setdefault(addr, []).append(key)
    return index


def destination(index, row):
    """(verdict, detail) for one guard-off row followed into another
    generation's census, addressing the rows of *its own* program.

    `reappears` is not one of the three verdicts here: it is settled by the
    caller's key lookup, because a membership that came back unchanged is the
    same content hash and therefore findable by key. That is worth saying
    plainly, because it means "still co-clustered together" and "reappears
    under the same key" are one event and not two, and the only case left for
    "still together" is `absorbed`: the same addresses, in one row, with more
    in it.
    """
    addrs = addrs_of(row)
    held = index.get(row["program"], {})
    others = [p for p in index if p != row["program"]]
    holders, unplaced, second = {}, 0, 0
    for addr in addrs:
        keys = held.get(addr)
        if not keys:
            unplaced += 1
        for key in keys or ():
            holders.setdefault(key, set()).add(addr)
        # A member with a home in another program is counted, not resolved:
        # the verdict below is about this row's own program's rows, and
        # quietly reporting the other program's would be a different answer.
        if any(addr in index[p] for p in others):
            second += 1
    if unplaced:
        verdict = "unplaced"
    elif len(holders) == 1:
        verdict = "absorbed"
    else:
        verdict = "split"
    detail = f"{len(holders)} row(s)"
    if unplaced:
        detail += f", {unplaced} address(es) with no holder"
    if second:
        detail += f", {second} member(s) also in another program"
    return verdict, detail


def cause_pd_report(committed_a, committed_b, off_a, off_b):
    """Whether the `pd` side of the two generations is the same partition at
    all, which is what the per-program split of the cells turns on.

    Every split it makes says a `pd` number, and a `pd` number only means
    something if `pd` could have moved. It could not, or it could, and the
    difference is one equality rather than a rate: an address both programs
    touch is in a `pd` row in one generation and the *same* `pd` row in the
    other, so a flipped `pd` key would be a contradiction rather than a
    finding. Printed as the comparison it is, so that a non-zero `pd` cell
    above is visible as a disagreement with this line instead of a surprise.
    """
    def pd_of(rows):
        return {r["cluster_key"]: r["addrs"] for r in rows.values()
                if r["program"] == "pd"}

    def verdict(one, other):
        a, b = pd_of(one), pd_of(other)
        if a == b:
            return f"identical ({len(a)} pd row(s) either way)"
        return (f"DIFFERENT ({len(a)} and {len(b)} pd row(s), "
                f"{len(set(a) & set(b))} of them under the same key)")

    return (f"    the pd side: committed {verdict(committed_a, committed_b)}; "
            f"guard-off {verdict(off_a, off_b)}")


def cause_report(label_a, committed_a_path, off_a_path,
                 label_b, committed_b_path, off_b_path, rows=False,
                 registers=None, page=(0x0300, 0x05FF)):
    """The same two pairs `across` reads, asked where each moved rank's
    substitution went, per cell, against the two cells that did not flip.

    `registers` is required rather than optional here, unlike `across`: the
    added-address count is one of the two mechanism tests, and printing `0`
    for a set the mode was not given would be a wrong answer rather than an
    absent one.
    """
    committed_a, off_a = clusters_of(committed_a_path), clusters_of(off_a_path)
    committed_b, off_b = clusters_of(committed_b_path), clusters_of(off_b_path)
    t = flip_table(committed_a, off_a, committed_b, off_b)
    added = added_addresses(registers)
    lo, hi = page
    page_str = f"0x{lo:04X}-0x{hi:04X}"

    # The population every per-cell rate below is read against: each guard-off
    # key of one generation, and where it lands in the other. Without it a
    # rate is a rate of something unnamed, and "most of the rows reappear" is
    # the sentence that has to be earned rather than assumed.
    keys_a, keys_b = keyed_by(off_a), keyed_by(off_b)
    both = sorted(set(keys_a) & set(keys_b))
    deltas = [d for d in (rank_delta(keys_a[k], keys_b[k]) for k in both)
              if d is not None]
    spread = [0, 0, 0, 0]
    for delta in deltas:
        spread[min(abs(delta), 3)] += 1

    out = [f"cause {label_a} -> {label_b}",
           f"  page {page_str}; the added set is {len(added)} address(es)"]
    out.append("")
    out.append(f"  the population: {len(keys_a)} guard-off key(s) in {label_a}, "
               f"{len(keys_b)} in {label_b}")
    out.append(f"    {len(both)} of the first reappear in the second under the same key, "
               f"{len(keys_a) - len(both)} only in the first, "
               f"{len(keys_b) - len(both)} only in the second")
    out.append(f"    the rank delta of those {len(both)}: 0 on {spread[0]}, "
               f"+/-1 on {spread[1]}, +/-2 on {spread[2]}, further on {spread[3]}"
               + (f"; mean {sum(deltas) / len(deltas):+.2f}, "
                  f"range {min(deltas):+d}..{max(deltas):+d}" if deltas else ""))
    def page_addrs(off):
        """The census's distinct page addresses.

        Distinct, not memberships: a page address both programs touch sits in a
        `main-ec` row and a `pd` row at once, so the two counts differ, and a
        cell's coverage below is a distinct count too. The rate rows count
        memberships, which is the right denominator for "of this cell's
        addresses, how many are on the page" -- a different question. Taken per
        census, because the two generations do not have the same page: the
        155 added addresses are 151 of the difference.
        """
        return {a for row in off.values() for a in addrs_of(row)
                if lo <= int(a, 16) <= hi}

    pop_addrs = {a for row in off_a.values() for a in addrs_of(row)}
    pop_page = page_addrs(off_a)
    pop_page_memberships = sum(1 for row in off_a.values() for a in addrs_of(row)
                               if lo <= int(a, 16) <= hi)
    out.append(f"    their members: {sum(len(addrs_of(r)) for r in off_a.values())} "
               f"membership(s) over {len(pop_addrs)} distinct address(es); "
               f"{len(pop_page)} of them in the page, held "
               f"{pop_page_memberships} time(s)"
               + ("" if pop_page_memberships == len(pop_page) else
                  " -- one address is in two rows, which is a `pd` holder and a "
                  "`main-ec` holder of the same byte")
               + f"; {label_b}'s holds {len(page_addrs(off_b))}")
    out.append(cause_pd_report(committed_a, committed_b, off_a, off_b))
    out.append("")
    out.append("  per cell: the row the key's rank carried in the generation that moved,")
    out.append("  and where that row's membership went in the other generation")

    def cell_records(keys, side):
        """One record per key: the row at the key's rank in the subject
        generation's guard-off census, and that row followed into the other
        generation's.

        The subject row is always there. `moved_ranks` needs a row to differ
        from before it calls a rank moved, so a committed rank the guard-off
        census does not carry is in no cell rather than in a cell with a
        missing row -- `pair`'s `absent` line is what names it, and counting it
        here as well would be the same rank in two reports.
        """
        committed, off, other = ((keyed_by(committed_a), off_a, off_b) if side == "a"
                                 else (keyed_by(committed_b), off_b, off_a))
        other_keys, index = keyed_by(other), holders_by_program(other)
        recs = []
        for key in keys:
            held = committed[key]
            row = off[held["cluster_id"]]
            addrs = addrs_of(row)
            found = other_keys.get(row["cluster_key"])
            if found is not None:
                verdict, detail = "reappears", ""
                other_rank, delta = found["cluster_id"], rank_delta(row, found)
            else:
                verdict, detail = destination(index, row)
                other_rank, delta = "-", None
            recs.append({
                "key": key, "program": row["program"], "size": len(addrs),
                "committed": held, "subject": row,
                "substitution": row["cluster_key"] != key,
                "verdict": verdict, "detail": detail, "other_rank": other_rank,
                "delta": delta,
                "page": sum(1 for a in addrs if lo <= int(a, 16) <= hi),
                "added": sum(1 for a in addrs if a in added)})
        return recs

    cells = {}
    for title, keys, side, subject in (("moved -> intact", t["a_to_b"], "a", label_a),
                                       ("moved in both", t["both"], "a", label_a),
                                       ("intact -> moved", t["b_to_a"], "b", label_b),
                                       ("intact in both", t["neither"], "a", label_a)):
        recs = cells[title] = cell_records(keys, side)
        progs = sorted({r["program"] for r in recs})

        def by_program(pred, recs=recs, progs=progs):
            return ", ".join(f"{p} {sum(1 for r in recs if r['program'] == p and pred(r))}"
                             for p in progs) or "none"

        def count(pred):
            return sum(1 for r in recs if pred(r))

        rep = [r for r in recs if r["verdict"] == "reappears"]
        gone = [r for r in recs if r["verdict"] != "reappears"]
        near = sum(1 for r in rep if r["delta"] is not None and abs(r["delta"]) <= 2)
        out.append("")
        out.append(f"  {title}: {len(recs)} key(s), {by_program(lambda r: True)}"
                   f" -- subject: {subject}"
                   + ("" if all(r["substitution"] for r in recs) else
                      "  [the row is the committed membership itself, so there is no substitution]"))
        out.append(f"    the subject row reappears in the other generation: {len(rep)} "
                   f"({by_program(lambda r: r['verdict'] == 'reappears')})"
                   f" -- rank 0 on {count(lambda r: r['delta'] == 0)}, "
                   f"|delta| <= 2 on {near}, further on {len(rep) - near}")
        out.append(f"    it does not: {len(gone)} "
                   f"({by_program(lambda r: r['verdict'] != 'reappears')})"
                   f" -- split across rows {count(lambda r: r['verdict'] == 'split')}, "
                   f"absorbed into one larger row {count(lambda r: r['verdict'] == 'absorbed')}, "
                   f"an address with no holder {count(lambda r: r['verdict'] == 'unplaced')}")
        out.append(f"    the subject rows' {sum(r['size'] for r in recs)} address(es): "
                   f"{sum(r['page'] for r in recs)} in the page, "
                   f"{sum(r['added'] for r in recs)} of the {len(added)} added")
        out.append(f"    the subject rows by size: "
                   f"{deciles([r['size'] for r in recs])}"
                   f"   the committed rows at the same ranks: "
                   f"{deciles([len(addrs_of(r['committed'])) for r in recs])}")
        touched = {a for r in recs for a in addrs_of(r["subject"])
                   if lo <= int(a, 16) <= hi}
        subject_off, subject_label = (off_a, label_a) if side == "a" else (off_b, label_b)
        out.append(f"    they touch {len(touched)} distinct page address(es) of the "
                   f"{len(page_addrs(subject_off))} in {subject_label}'s guard-off census")

    # The comparison the counts above exist for, with the denominators they
    # need: a cell whose rows hold more addresses has more chances to touch the
    # page, so raw counts across cells of 71 and 23 keys are not comparable,
    # and a cell that reappears at the population's rate is not a mechanism.
    # The two control cells are in the same table for that reason.
    out.append("")
    out.append("  the four cells beside each other and the population, as rates:")
    out.append(f"    {'measure':<22} {'moved->intact':>14} {'moved in both':>14} "
               f"{'intact->moved':>14} {'intact in both':>14} {'population':>14}")

    def rate(num, den):
        return f"{num}/{den} {100.0 * num / den:5.1f}%" if den else f"{num}/0   --"

    def cell_rate(cell, num, den):
        recs = cells[cell]
        return rate(sum(num(r) for r in recs), sum(den(r) for r in recs))

    is_rep = lambda r: r["verdict"] == "reappears"
    near_rep = lambda r: r["verdict"] == "reappears" and r["delta"] is not None \
        and abs(r["delta"]) <= 2
    size = lambda r: r["size"]
    page = lambda r: r["page"]
    added_n = lambda r: r["added"]
    out.append(f"    {'reappears':<22} "
               + " ".join(f"{cell_rate(c, is_rep, lambda r: 1):>14}"
                          for c in cells)
               + f" {rate(len(both), len(keys_a)):>14}")
    out.append(f"    {'reappears within 2':<22} "
               + " ".join(f"{cell_rate(c, near_rep, is_rep):>14}" for c in cells)
               + f" {rate(spread[0] + spread[1] + spread[2], len(both)):>14}")
    out.append(f"    {'members in the page':<22} "
               + " ".join(f"{cell_rate(c, page, size):>14}" for c in cells)
               + f" {rate(len(pop_page), sum(len(addrs_of(r)) for r in off_a.values())):>14}")
    out.append(f"    {'members of the added':<22} "
               + " ".join(f"{cell_rate(c, added_n, size):>14}" for c in cells)
               + f" {rate(0, sum(len(addrs_of(r)) for r in off_a.values())):>14}")
    out.append("    (the population's added count is 0 by construction: the added")
    out.append("     set is the difference between the two guard-on universes, so no")
    out.append("     address in it is a member of any row of the older census.)")

    # A cell's page rate is not comparable to another's without the size of the
    # rows behind it -- a ten-address row has ten chances to sit on the page
    # where a one-address row has one, and these cells do not hold rows of the
    # same size. So the rate is broken out by row size, with the committed row
    # at the *same rank* beside it, which holds rank constant as well: it is
    # the same row number on both sides, so the pair is the change at that
    # rank and nothing else.
    with_sub = [c for c in cells if any(r["substitution"] for r in cells[c])]
    out.append("")
    out.append("  page rate by the size of the row, the committed row at the same rank")
    out.append("  written first, and the subject row count in brackets. A band holding a")
    out.append("  handful of rows is not a rate, which is what the brackets are for.")
    out.append(f"    {'band':<10}" + "".join(f"{c:>24}" for c in with_sub))
    for band_lo, band_hi in ((1, 1), (2, 2), (3, 4), (5, 8), (9, 10 ** 8)):
        label = ("size %d" % band_lo if band_lo == band_hi else
                 "size %d+" % band_lo if band_hi > 10 ** 7 else
                 "size %d-%d" % (band_lo, band_hi))
        columns = []
        for cell in with_sub:
            sel = [r for r in cells[cell] if band_lo <= r["size"] <= band_hi]
            if not sel:
                columns.append(f"{'-':>24}")
                continue
            committed_addrs = [a for r in sel for a in addrs_of(r["committed"])]
            committed_page = sum(1 for a in committed_addrs if lo <= int(a, 16) <= hi)
            subject_page = sum(r["page"] for r in sel)
            subject_all = sum(r["size"] for r in sel)
            columns.append(
                f"{100 * committed_page / len(committed_addrs):5.1f} -> "
                f"{100 * subject_page / subject_all:5.1f} ({len(sel):>4})")
        out.append(f"    {label:<10}" + "".join(columns))

    out.append("")
    out.append(f"  {'cluster_key':<14} {'program':<8} {'size':>4} {'subject row':<14} "
               f"{'rank subj':<11} {'rank other':<11} {'delta':>5} {'page':>4} "
               f"{'of 155':>6}  destination")
    every = [r for recs in cells.values() for r in recs]
    for rec in (every if rows else every[:12]):
        subject = rec["subject"]
        delta = "-" if rec["delta"] is None else f"{rec['delta']:+d}"
        out.append(
            f"  {rec['key']:<14} {rec['program']:<8} {rec['size']:>4} "
            f"{subject['cluster_key']:<14} {subject['cluster_id']:<11} "
            f"{rec['other_rank']:<11} {delta:>5} "
            f"{rec['page']:>4} {rec['added']:>6}  {rec['verdict']}"
            + (f" ({rec['detail']})" if rec["detail"] not in ("", "-") else ""))
    if not rows and len(every) > 12:
        out.append(f"  ({len(every) - 12} more; --rows for all of them)")
    return out, t, cells


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

    # A census pair of its own, because the pair above cannot be the case: its
    # `0x0E` is held by two clusters in *both* generations, so a count reading
    # either generation's holders gets the same two. Here generation A holds the
    # address under a `main-ec` and a `pd` key and generation B under the
    # `main-ec` key alone. Each census is passed as its own guard-off, so
    # nothing moves and every row reads `intact in both`.
    second_a = write_census(tmp, "second-a.csv", [
        ("main-ec-001", "main-ec", ["0x0E"], key(1)),
        ("pd-001", "pd", ["0x0E", "0x20"], key(2))])
    second_b = write_census(tmp, "second-b.csv", [
        ("main-ec-002", "main-ec", ["0x0E"], key(1))])
    sa, sb = clusters_of(second_a), clusters_of(second_b)
    lines = swept_report(sa, sb, flip_table(sa, sa, sb, sb), ["0x0E"])
    # The figure is read back out of the tool's own summary line rather than
    # recomputed beside it, so the two are compared as a reader would read them.
    per_addr = {}
    for ln in lines:
        if ln.startswith("  0x"):
            per_addr[ln.split()[0]] = per_addr.get(ln.split()[0], 0) + 1
    summary = [ln for ln in lines if "second holder" in ln]
    said = int(summary[0].rsplit("; ", 1)[1].split(" ")[0]) if summary else -1
    check(per_addr.get("0x0E") == 2 and said == 1
          and said == sum(1 for n in per_addr.values() if n > 1),
          "the second-holder count is over both generations' holders, so it "
          "equals the number of addresses that printed more than one row: "
          "2 rows for 1 address, counted once")

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

    # ------------------------------------------------------------------------
    # `cause`, over a fourth pair of censuses. The one above cannot exercise
    # the mode: its two generations share a committed census, so every cell
    # but one is empty. These are built so each of the four things a
    # substitution can do is present, and so the two cells that did not flip
    # are counted the same way as the two that did -- a fixture where the
    # control is missing could not catch a mode that only reads the flipped
    # cells.
    #
    # The universe: 0x0300 and 0x0301 are the two added addresses, and they
    # are the only members of the page anywhere in the fixture, so "in the
    # page" and "of the added set" are the same two addresses and a fixture
    # that confused the two would pass.
    universe_a = [("0x0E", "1"), ("0x0F", "1"), ("0x10", "1"), ("0x13", "2"),
                  ("0x14", "1"), ("0x20", "1"), ("0x21", "1"), ("0x22", "1"),
                  ("0x40", "1"), ("0x41", "1"), ("0x50", "1"), ("0x60", "1"),
                  ("0x61", "1")]
    universe_b = universe_a + [("0x0300", "4"), ("0x0301", "4")]
    d_on = write_registers(tmp, "d-on.csv", universe_a)
    d_off = write_registers(tmp, "d-guard.csv", universe_a)
    e_on = write_registers(tmp, "e-on.csv", universe_b)
    e_off = write_registers(tmp, "e-guard.csv", universe_b)

    # The committed censuses share six keys and differ by one, so every cell
    # has a member and the one-sided set is non-empty in the B direction.
    committed_d = write_census(tmp, "d-committed.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
        ("main-ec-002", "main-ec", ["0x10"], key(2)),
        ("main-ec-003", "main-ec", ["0x40", "0x41"], key(3)),
        ("main-ec-004", "main-ec", ["0x60"], key(5)),
        ("pd-001", "pd", ["0x20", "0x21", "0x22"], key(6)),
        ("pd-002", "pd", ["0x0E", "0x50"], key(8))])
    committed_e = write_census(tmp, "e-committed.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
        ("main-ec-002", "main-ec", ["0x10"], key(2)),
        ("main-ec-003", "main-ec", ["0x40", "0x41"], key(3)),
        ("main-ec-004", "main-ec", ["0x60"], key(5)),
        ("main-ec-005", "main-ec", ["0x0300", "0x0301"], key(7)),
        ("pd-001", "pd", ["0x20", "0x21", "0x22"], key(6)),
        ("pd-002", "pd", ["0x0E", "0x50"], key(8))])

    # Generation A's guard-off census. k9 sits at k1's rank and is the
    # substitution that reappears one rank over in B; k10 sits at k3's rank
    # and is absorbed into a larger row there; k12 sits at k8's rank and its
    # two addresses land in two different `pd` rows of B, one of which has a
    # `main-ec` holder as well.
    off_d = write_census(tmp, "d-off.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F", "0x13"], key(9)),
        ("main-ec-002", "main-ec", ["0x10"], key(2)),
        ("main-ec-003", "main-ec", ["0x40", "0x14"], key(10)),
        ("main-ec-004", "main-ec", ["0x60"], key(5)),
        ("pd-001", "pd", ["0x20", "0x21", "0x22"], key(6)),
        ("pd-002", "pd", ["0x0E", "0x22"], key(12))])
    off_e = write_census(tmp, "e-off.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
        ("main-ec-002", "main-ec", ["0x0E", "0x0F", "0x13"], key(9)),
        ("main-ec-003", "main-ec", ["0x40", "0x14", "0x61"], key(13)),
        ("main-ec-004", "main-ec", ["0x0300", "0x0301"], key(11)),
        ("pd-001", "pd", ["0x20", "0x21", "0x22"], key(6)),
        ("pd-002", "pd", ["0x50", "0x61", "0x0E"], key(14))])

    lines, _t, cells = cause_report("A", committed_d, off_d, "B", committed_e,
                                    off_e, rows=True,
                                    registers=(d_on, d_off, e_on, e_off))
    check([r["key"] for r in cells["moved -> intact"]] == [key(1)]
          and [r["key"] for r in cells["intact -> moved"]] == [key(2), key(5)]
          and [r["key"] for r in cells["moved in both"]] == [key(3), key(8)]
          and [r["key"] for r in cells["intact in both"]] == [key(6)],
          "all four cells are filled from the fixture, the two controls "
          "included -- a mode that read only the flipped cells would see two "
          "of these and pass nothing")

    # The population the per-cell rates are read against, named in both
    # directions rather than netted to a difference.
    check(any("2 of the first reappear in the second under the same key, "
              "4 only in the first, 4 only in the second" in ln for ln in lines)
          and any("0 on 1, +/-1 on 1, +/-2 on 0, further on 0" in ln
                  for ln in lines),
          "the population a cell's rate is read against is printed, with the "
          "one-sided keys named and the survivors' rank deltas spread")

    # Mechanism 1, the reading that was going to be the answer: a substitution
    # that reappears at a neighbouring rank. k9 sits at main-ec-001 in A and
    # main-ec-002 in B, so the delta is +1 and the cell reports one reappearance
    # inside two ranks and no rank-0 case.
    check(any("moved -> intact: 1 key(s)" in ln for ln in lines)
          and any("reappears in the other generation: 1" in ln for ln in lines)
          and any("rank 0 on 0, |delta| <= 2 on 1, further on 0" in ln
                  for ln in lines)
          and any("main-ec-001" in ln and "main-ec-002" in ln and "  +1 " in ln
                  for ln in lines),
          "a substitution that reappears at a neighbouring rank is reported as "
          "reappearing, with that rank, rather than as a row that went missing")

    # Mechanism 2: a substitution new to the generation, drawn from the added
    # addresses. k11 is the row at k5's rank in B and holds both added
    # addresses; in A they are in no row at all, so the destination is
    # `unplaced` and the page and added counts are 2.
    check(any("intact -> moved: 2 key(s)" in ln for ln in lines)
          and any("an address with no holder 1" in ln for ln in lines)
          and any("5 address(es): 2 in the page, 2 of the 2 added" in ln
                  for ln in lines)
          and any("unplaced (0 row(s), 2 address(es) with no holder)" in ln
                  for ln in lines),
          "a substitution built from the added addresses is counted against the "
          "page and the added set, and its members are reported as having no "
          "holder in the generation that predates them")

    # Neither mechanism: the control cell gets the same three verdicts, split
    # and absorbed, and the same page and added columns.
    check(any("moved in both: 2 key(s)" in ln for ln in lines)
          and any("it does not: 2" in ln and "split across rows 1, absorbed "
                  "into one larger row 1" in ln for ln in lines)
          and any("4 address(es): 0 in the page, 0 of the 2 added" in ln
                  for ln in lines),
          "a control cell is counted with the same verdicts as a flipped one, "
          "so a rate the controls show is visible as such")

    # The per-program lookup, which is the reason a first-match membership
    # search is wrong here: 0x0E is in two `main-ec` rows of B and one `pd`
    # row, and a flat index would report whichever it met first.
    index_e = holders_by_program(clusters_of(off_e))
    check(sorted(index_e["main-ec"]["0x0E"]) == [key(1), key(9)]
          and index_e["pd"]["0x0E"] == [key(14)],
          "an address both programs touch is indexed under each program's own "
          "rows, so a `pd` holder is never reported for a `main-ec` row")
    check(any("split (2 row(s), 1 member(s) also in another program)" in ln
              for ln in lines),
          "a row whose addresses land in two of its own program's rows is a "
          "split, and a member that also has a home in the other program is "
          "counted rather than resolved")

    # The degenerate cell, pinned because it is the one whose rate would look
    # like the strongest result in the report if it were not labelled.
    check(any("intact in both: 1 key(s)" in ln
              and "[the row is the committed membership itself, so there is no "
              "substitution]" in ln for ln in lines)
          and any("reappears in the other generation: 1" in ln for ln in lines),
          "a cell with no substitution says so on its own line, so its "
          "reappearance rate is not read as a mechanism")

    # Both branches of the pd comparison: identical on the committed side here,
    # different on the guard-off side, and both are reported.
    check(any("the pd side: committed identical (2 pd row(s) either way); "
              "guard-off DIFFERENT (2 and 2 pd row(s), 1 of them under the same "
              "key)" in ln for ln in lines),
          "whether the two generations' `pd` partitions are the same partition "
          "at all is reported on its own, so a `pd` cell above it is visible as "
          "a disagreement rather than a surprise")

    # A committed rank the guard-off census does not carry lands in no cell at
    # all rather than in a cell whose subject row is missing: `moved_ranks`
    # needs a row to differ from before it calls a rank moved. k3 therefore
    # leaves `moved in both` and arrives in `intact -> moved`, and
    # `absent_ranks` is what names the rank -- one report of it, not two.
    off_d_short = write_census(tmp, "d-off-short.csv",
                               [r for r in (("main-ec-001", "main-ec", ["0x0E", "0x0F", "0x13"], key(9)),
                                            ("main-ec-002", "main-ec", ["0x10"], key(2)),
                                            ("main-ec-004", "main-ec", ["0x60"], key(5)),
                                            ("pd-001", "pd", ["0x20", "0x21", "0x22"], key(6)),
                                            ("pd-002", "pd", ["0x0E", "0x22"], key(12)))
                                if r[0] != "main-ec-003"])
    _short_lines, _t2, short_cells = cause_report(
        "A", committed_d, off_d_short, "B", committed_e, off_e,
        registers=(d_on, d_off, e_on, e_off))
    check(absent_ranks(clusters_of(committed_d), clusters_of(off_d_short))
          == ["main-ec-003"]
          and [r["key"] for r in short_cells["moved in both"]] == [key(8)]
          and key(3) in [r["key"] for r in short_cells["intact -> moved"]],
          "a committed rank with no row in the guard-off census is in no cell, "
          "rather than in a cell with a missing subject row -- `absent_ranks` "
          "is the one place that names it")

    print(f"  {'FAILED' if bad else 'all checks passed'}"
          + (f" ({bad})" if bad else ""))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", choices=("pair", "across", "cause"),
                    help="one committed/guard-off pair, or two of them compared, "
                         "or where a moved rank's substitution went")
    ap.add_argument("--old", help="committed clusters CSV (pair)")
    ap.add_argument("--new", help="guard-off clusters CSV (pair)")
    ap.add_argument("--old-a", help="committed clusters CSV of pair A (across, cause)")
    ap.add_argument("--new-a", help="guard-off clusters CSV of pair A (across, cause)")
    ap.add_argument("--old-b", help="committed clusters CSV of pair B (across, cause)")
    ap.add_argument("--new-b", help="guard-off clusters CSV of pair B (across, cause)")
    ap.add_argument("--old-registers", help="guard-on registers CSV of the pair (pair)")
    ap.add_argument("--new-registers", help="guard-off registers CSV of the pair (pair)")
    ap.add_argument("--old-a-registers", help="guard-on registers CSV of pair A (across, cause)")
    ap.add_argument("--new-a-registers", help="guard-off registers CSV of pair A (across, cause)")
    ap.add_argument("--old-b-registers", help="guard-on registers CSV of pair B (across, cause)")
    ap.add_argument("--new-b-registers", help="guard-off registers CSV of pair B (across, cause)")
    ap.add_argument("--label", help="what to call the pair in the report "
                                    "(default: the committed CSV's path)")
    ap.add_argument("--label-a", help="what to call pair A in the report (across, cause)")
    ap.add_argument("--label-b", help="what to call pair B in the report (across, cause)")
    ap.add_argument("--rows", action="store_true",
                    help="print every row rather than the first twelve: the "
                         "flipped clusters in across, the followed substitutions "
                         "in cause")
    ap.add_argument("--page", nargs=2, type=lambda s: int(s, 16), metavar=("LO", "HI"),
                    default=(0x0300, 0x05FF),
                    help="the address range the page test counts against "
                         "(cause; default 0x0300 0x05FF, the working page "
                         "annotations/xdata-cluster-names.csv records)")
    ap.add_argument("--swept", nargs="+", metavar="ADDR",
                    help="cross-reference these addresses against the clusters "
                         "holding them (across)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.mode:
        ap.error("a mode is required: pair, across, cause, or --self-test")

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
        ap.error(f"{args.mode} needs " + ", ".join(missing))
    quad = (args.old_a_registers, args.new_a_registers,
            args.old_b_registers, args.new_b_registers)
    if any(quad) and not all(quad):
        ap.error("the four --*-registers flags go together, and across needs "
                 "both generations' guard-on and guard-off registers CSVs")
    if args.mode == "cause":
        # Not optional, unlike across: the added-address count is one of the
        # two mechanism tests, and a mode that printed 0 for a set it was
        # never handed would be wrong rather than silent about it.
        if not all(quad):
            ap.error("cause needs both generations' guard-on and guard-off "
                     "registers CSVs; the added-address count is one of the "
                     "two mechanism tests")
        lines, table, _cells = cause_report(
            args.label_a or args.old_a, args.old_a, args.new_a,
            args.label_b or args.old_b, args.old_b, args.new_b, rows=args.rows,
            registers=quad, page=tuple(args.page))
        print("\n".join(lines))
        return 0
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
