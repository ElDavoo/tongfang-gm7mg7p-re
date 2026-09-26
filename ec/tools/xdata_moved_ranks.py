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
prints one pair; `across` prints the flip table between two of them and the
rank shift between the two *committed* censuses the table is built from;
`cause` follows the row a rank carried into the other generation, which is the
step `xdata-moved-ranks-fall.md` §4 named and did not take.

**A rank shift is a per-program figure, and its sign is a convention.** A rank
orders one program's clusters, so `main-ec-002` -> `main-ec-003` and
`pd-002` -> `pd-003` are not distances on one scale and a mean over both is a
figure about neither. And a positive delta is *down* the size ordering, because
`cluster_id` numbers clusters by descending size -- which is stated on the line
that prints it rather than left to a reader who has to know the convention
already.

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
    python3 xdata_moved_ranks.py across --old-a A --new-a B --old-b C --new-b D \\
        --cell intact-both --rows
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
    `test_xdata_cluster_names.py::TheContentKey` holds that, and the committed
    census measures clean -- so this is a bijective re-keying and the last row
    wins for none. "Unique" is the one claim here a map cannot show failing, so
    each **view** over a census prints `duplicate_keys()` over the census it
    re-keyed rather than inheriting the check from a sibling function: two
    ranks on one key leave a shorter map, not a wrong shape, and a shorter map
    is exactly what a count reads as a smaller measurement.

    The unit is the view rather than the caller, and that is the whole of the
    claim. The seven call sites reach four distinct censuses -- the two
    committed and the two guard-off -- by more routes than that:
    `flip_table` and `swept_report` re-key both committed ones, `cause_report`
    re-keys the guard-off pair for its population and reaches the committed
    pair, and `holders_by_program`'s census, again in its per-cell lookup. So
    the census is what the check belongs to and the report that reads it is
    what prints it: `pair_report` covers both censuses of the pair it reads,
    `collapse_line` covers the committed pair for `across` and `cause` and
    `collision_line` covers it again under `--swept`, and `cause_report`'s
    population block covers the guard-off pair -- which is what covers the
    per-cell lookup's and `holders_by_program`'s, because those re-key the
    same two censuses. Nothing is covered by virtue of some other census
    having been checked.
    """
    return {r["cluster_key"]: r for r in rows.values()}


def duplicate_keys(rows):
    """{cluster_key: [cluster_id, ...]} for the keys two ranks of one census
    share, in rank order.

    A precondition, checked at each view that re-keys a census rather than
    assumed at one place and inherited everywhere else. Cheap enough to run
    unconditionally, and it has to be: the failure it looks for is a number
    that is quietly too small, which is not the kind of thing a reader can
    catch from the number.
    """
    held = {}
    for cid, row in sorted(rows.items()):
        held.setdefault(row["cluster_key"], []).append(cid)
    return {k: ranks for k, ranks in held.items() if len(ranks) > 1}


def collision_line(rows, label="committed", consequence="", only_if_collision=False):
    """The line a report prints about the precondition of a census it re-keyed.

    Printed either way, so a run that reports nothing is a run that looked and
    found nothing, which is a different claim from a run that never looked. The
    one exception is `only_if_collision`, for the views that print this only
    when it bites -- `collapse_line`'s silent-on-clean rule, which holds for
    the census `pair` checks unconditionally and would be a second opinion
    otherwise. That case returns the empty string rather than a clean bill of
    health, so a caller that appends the result unconditionally cannot print
    the finding twice.

    `label` names the census in the sentence. It was the literal word
    `committed` in both f-strings, which is why the guard-off censuses could
    not be pointed at this helper at all and were carrying their own spelling
    of the same line; `label="committed"` is what the four committed census
    reports print, unchanged.
    """
    dups = duplicate_keys(rows)
    if not dups:
        if only_if_collision:
            return ""
        return (f"  cluster_key unique across the {len(rows)} {label} row(s): "
                f"0 collision(s)")
    named = "; ".join(f"{k} on {', '.join(ranks)}" for k, ranks in dups.items())
    return (f"  cluster_key COLLISION: {len(dups)} of the {len(rows)} {label} "
            f"keys carried by more than one rank ({named})"
            + (f" -- {consequence}" if consequence else ""))


def moved_ranks(committed, off):
    """{cluster_id: (committed row, guard-off row at that rank)} for every
    committed rank the guard-off census names something else at.

    Keyed on the rank and not on `cluster_key`, which is the whole of the
    change. `cluster_id` cannot collide -- `clusters_of` is a dict read keyed
    on it -- so `len(moved)` is the number of ranks the predicate matched even
    when two of them carry the same content hash. Keyed on the key it was not:
    a collision dropped a rank out of a count that still closed against
    `intact`, because `intact` is derived from `len(moved)`. The key-indexed
    views re-derive the key from this map and say what that costs them; see
    `duplicate_keys` and `collision_line`.

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
            out[cid] = (row, other)
    return out


def absent_ranks(committed, off):
    """Committed ranks the guard-off census does not carry."""
    return [cid for cid in sorted(committed) if cid not in off]


def rank_of(row):
    """(program, integer rank) from a `cluster_id` like `main-ec-014`.

    After the *last* hyphen, because the program is a two-part name and
    `main-ec-002` has a hyphen in the half that is not the number -- and
    nothing else in a clusters CSV carries the rank, so this is the one place
    the shape is read. The number comes back with its program rather than on
    its own because it is a rank *within* that program: `pd-002` and
    `main-ec-002` are not two places in one ordering, so a difference between
    two rows of different programs is `None` (`rank_delta`) rather than a
    number that invites a comparison nobody asked for.
    """
    program, _, num = row["cluster_id"].rpartition("-")
    return program, int(num)


def signed(values):
    """A mean with its sign, or `-` for an empty set -- which a program can be
    here, and which a `+0.00` would report as a measurement rather than as the
    absence of one."""
    return f"{sum(values) / len(values):+.2f}" if values else "-"


def write_movement(on, off):
    """(entering, leaving, net, entering_addrs, leaving_addrs) for the `write`
    column of two per-address registers CSVs, `on` first.

    Gross in each direction, never one signed total, so that every figure
    carries a label the arithmetic checked. The tool's convention is committed
    -> guard-off and the `==` rejection is the only thing
    `xdata_register_map.py --no-eq-guard` lifts, so a column that goes *up*
    under it has references **entering** `write` and none leaving; a signed
    sum reports that as "leaving 833", a direction the census never had and
    that a reader of `xdata-06c2-06db-timers.md` §6a would carry to the next
    page. `net` is the signed total, kept beside the two it is the difference
    of rather than instead of them.

    The two address lists are what make this one measurement with `changed`
    and not a second one: every address whose `write` differs moves one way or
    the other, so `len(entering_addrs) + len(leaving_addrs) == changed` is a
    closure `pair_report` can print and be caught by. Note the two sides
    compare differently and that is deliberate -- `changed` is a string
    inequality and this is an integer subtraction, so a cell that is
    numerically but not textually equal (`"05"` against `"5"`) is a change to
    one and no movement to the other. The closure is what says so out loud;
    the census's own cells are all canonical, so nothing real reaches it.

    Only the addresses both files carry take part. An address the guard-off
    census dropped is not a change, which is the fallback `changed` applies
    too, so the two do not disagree about one.
    """
    entering = leaving = net = 0
    entering_addrs, leaving_addrs = [], []
    for addr, row in on.items():
        other = off.get(addr)
        if other is None:
            continue
        delta = int(other["write"]) - int(row["write"])
        net += delta
        if delta > 0:
            entering += delta
            entering_addrs.append(addr)
        elif delta < 0:
            leaving -= delta
            leaving_addrs.append(addr)
    return entering, leaving, net, entering_addrs, leaving_addrs


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
    # The precondition of the two counts above, stated for **both** censuses
    # this read rather than for the one whose key some other report joins on,
    # and stated rather than inherited from the sibling function that documents
    # it. `moved` and `intact` are per rank, so a duplicated key cannot make
    # either of them wrong; what it costs is whichever view reads the key. The
    # committed census is joined on by `across` and `--swept`, and the guard-off
    # one by `cause`'s population and its `holders_by_program` index, so each
    # line names the view it costs and neither of them is this report's.
    out.append(collision_line(committed,
                              consequence="the moved and intact counts above are "
                                          "per rank and are unaffected; across and "
                                          "--swept join on the key and are not"))
    out.append(collision_line(off, "guard-off",
                              consequence="the moved and intact counts above are "
                                          "per rank and are unaffected; across and "
                                          "--swept do not read this census, but "
                                          "cause's population and its per-program "
                                          "holder index are over the key and are not"))

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
        entering, leaving, net, up, down = write_movement(on, offreg)
        out.append(f"  §6a: address universe {universe} ({len(on)} rows); "
                   f"write changes {changed} of {len(on)}; refs changes {refs} of {len(on)}; "
                   f"references entering write {entering}, leaving write {leaving}, "
                   f"net {net:+d}")
        # `changed` counts addresses and the pair above counts references, so
        # the two are not comparable as numbers; what has to hold is that the
        # pair moved every address `changed` says it moved, once, in one
        # direction or the other. Marked rather than raised, as `across`'s
        # four-term close is, because a disagreement here is a report to read
        # and not a run to abort.
        out.append(f"  closes: {len(up)} + {len(down)} = {len(up) + len(down)}, "
                   f"over the {changed} address(es) whose write column changed"
                   + ("" if len(up) + len(down) == changed else "   MISMATCH"))

    out.append("")
    out.append(f"  {'cluster_key':<14} {'name':<16} {'committed':<12} {'guard-off':<12} "
               f"{'size':>5} {'delta':>6}  verdict")
    for cid in sorted(moved, key=lambda c: (moved[c][0]["cluster_id"],
                                             moved[c][0]["cluster_key"])):
        old, new = moved[cid]
        out.append(f"  {old['cluster_key']:<14} {old['cluster_name'] or '-':<16} "
                   f"{old['cluster_id']:<12} {new['cluster_id']:<12} "
                   f"{len(addrs_of(old)):>5} {len(addrs_of(old) ^ addrs_of(new)):>6}  moved")
    for cid in sorted(committed):
        row = committed[cid]
        # The rank, not the key: an *intact* rank sharing a key with a moved one
        # is a row of this listing, and keyed on the key it used to be dropped
        # from here while the count above still said the right thing. Same
        # collision, one line further down the report than the moved listing.
        if cid in off and cid not in moved:
            out.append(f"  {row['cluster_key']:<14} {row['cluster_name'] or '-':<16} "
                       f"{cid:<12} {cid:<12} {len(addrs_of(row)):>5} {0:>6}  intact")
    return out, committed, off, moved


# --------------------------------------------------------------------------
# Two pairs, compared on the key rather than the rank.
# --------------------------------------------------------------------------

def moved_keys(committed, off):
    """The keys `moved_ranks` reports as moved, re-derived from its rank-keyed
    map because a flip table joins two censuses on the key by design.

    The projection is many-to-one if two moved ranks of one census share a key,
    so a caller that needs the ranks back asks `flip_table` for its `collapsed`.
    """
    return {old["cluster_key"] for old, _new in moved_ranks(committed, off).values()}


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

    Every count in the table is a **key** count, which is the right unit for a
    join on the key and not the same unit as `pair`'s rank counts. That is only
    the same number when keys are unique within a census, so the ranks of a
    committed census that share one come back as `collapsed`, in generation
    order, and `across_report` prints a line when it is not empty. The
    population is the whole committed census and not its moved ranks, because
    that is the census every count above is drawn from: two ranks that share a
    key and neither of which moved still leave one of them unnamed by the key,
    and a table that is silent about it reports the collision's one case that
    costs no count as though it were the only case. The four-term closure still
    closes either way -- it is set algebra over one key universe -- which is
    precisely why the closure cannot be the thing that notices.
    """
    a, b = keyed_by(committed_a), keyed_by(committed_b)
    moved_a, moved_b = (moved_keys(committed_a, off_a), moved_keys(committed_b, off_b))
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
        # Per generation, the ranks of the whole committed census sharing a key.
        # Empty on any census whose keys are distinct, which is every census
        # this tree holds, so widening the population from the moved ranks to
        # the census they are drawn from is a superset rather than a change.
        "collapsed": [duplicate_keys(committed_a), duplicate_keys(committed_b)],
    }


def collapse_line(table, label_a, label_b):
    """The line `across` and `cause` print when a key-indexed view loses a rank
    to a collision, and nothing at all when none is lost.

    Silent on the clean case on purpose: `pair` prints its precondition
    unconditionally, and a conditional line here reads as a second opinion on
    the same census rather than as the property the key-indexed counts rest on.
    The census is now the same one `pair` checks unconditionally, which is what
    makes that silence a summary rather than a second opinion.

    The ranks named are the ones the keys are read from, which is the whole
    committed census and not the moved part of it -- so a line here is not
    restricted to collisions that happened to cost a count, and the counts are
    named as key counts whether or not any of them is wrong.
    """
    collapsed = [(label, dups)
                 for label, dups in zip((label_a, label_b), table["collapsed"]) if dups]
    if not collapsed:
        return []
    named = "; ".join(f"{label}: " + ", ".join(f"{k} on {', '.join(ranks)}"
                                                for k, ranks in dups.items())
                      for label, dups in collapsed)
    ranks = sum(len(rs) for _label, dups in collapsed for rs in dups.values())
    return [f"  the counts below are keys, not the ranks `pair` counts: "
            f"{ranks} committed rank(s) across {len(collapsed)} generation(s) "
            f"share a key with another committed rank ({named})"]


def deciles(sizes):
    """Ten size cut points, so "the large clusters" is a distribution and not
    an adjective. A tenth is a whole number of rows, so this is a
    nearest-rank read rather than an interpolation: cell `i` is the value at
    0-based rank `(n * i) // 10`, and ten rows is the smallest `n` at which
    that is one whole row per cell with none doubled up at the ends.

    Below the floor the cells are returned as the set itself, marked so that a
    reader of a transcript cannot take a stretched handful for a distribution:
    two clusters of two addresses each is one distinct value, and printed over
    ten cells it is a shape. The floor is the comparison itself that needs it --
    two of these strings are read cell for cell against each other, which says
    something only if each cell is a row of its own. The empty set is reported
    before the floor rule applies; it is not a set too small to cut, it is no
    set at all."""
    ordered = sorted(sizes)
    if not ordered:
        return "no rows"
    if len(ordered) < 10:
        return (f"{len(ordered)} row(s), too few to cut ten ways: "
                + " ".join(str(n) for n in ordered))
    return " ".join(str(ordered[min(len(ordered) - 1, (len(ordered) * i) // 10)])
                    for i in range(10))


# The four cells, under the spelling the table's own verdict column carries.
# The table had two of them before the `rank A` / `rank B` columns and walked
# only the ones a key can be in by changing cell, so the 266 and the 40 were
# counted in the summary and never given a row.
CELLS = {"moved->intact": "a_to_b", "moved-in-both": "both",
         "intact->moved": "b_to_a", "intact-in-both": "neither"}

# `--cell` choices, over the cells above. `flipped` is both flip directions
# and is the default, so the report a reader has already seen is the report
# this prints.
TABLE_CELLS = {
    "flipped": ("moved->intact", "intact->moved"),
    "moved-both": ("moved-in-both",),
    "moved-a-only": ("moved->intact",),
    "moved-b-only": ("intact->moved",),
    "intact-both": ("intact-in-both",),
    "all": tuple(CELLS),
}


def rank_shift_report(a, b, table):
    """How far the numbering moved between the two committed censuses, per
    program and per cell.

    Three things this is not, and each of them is a way the pair of figures
    below gets read wrong:

    - *A mean is not a shift.* A cluster's rank can change without its
      membership changing, and its membership can change without its rank
      changing, so the two are counted apart rather than one standing in for
      the other.
    - *The two means are not the same figure.* "Changed by N on average" is
      ambiguous between the keys that changed and every shared key, and the
      two differ by however many keys sat still. Both are printed, each
      labelled, because the ambiguity is a defect in the sentence that would
      have carried either one alone.
    - *A rank is not comparable across programs.* A rank orders one program's
      clusters, so the two means are per program and there is no combined one;
      and a positive delta is *down* the size ordering, because `cluster_id`
      numbers clusters by descending size. That convention is on the line
      rather than in this docstring alone, because a signed figure whose sign
      nobody has read is the one a reader gets backwards.
    """
    def delta(key):
        return rank_of(b[key])[1] - rank_of(a[key])[1]

    shared = table["shared"]
    out = ["  rank shift between the two committed censuses; a positive delta is "
           "down the size ordering, and a delta is only comparable within one "
           "program",
           f"    over the {len(shared)} shared keys; the {len(table['only_a'])} in one "
           f"census only and the {len(table['only_b'])} in the other have no "
           "counterpart to difference, so they are in no figure below"]
    for program in sorted({a[k]["program"] for k in shared}):
        deltas = [delta(k) for k in shared if a[k]["program"] == program]
        changed = [d for d in deltas if d]
        spread = f"{min(deltas):+d} to {max(deltas):+d}" if deltas else "-"
        out.append(f"    {program:<8} {len(changed):>4} of {len(deltas):>4} changed rank; "
                   f"mean {signed(changed):>6} over those, {signed(deltas):>6} over all "
                   f"(an unchanged key at 0); range {spread}")
    for name in CELLS:
        keys = table[CELLS[name]]
        out.append(f"    of the {len(keys):>4} {name:<14} "
                   f"{sum(1 for k in keys if delta(k)):>4} changed rank")
    out.append(f"    over all {len(shared):>4} shared keys, "
               f"{sum(1 for k in shared if delta(k)):>4} changed rank -- the four cells "
               "above close on it")
    return out


def across_report(label_a, committed_a_path, off_a_path,
                  label_b, committed_b_path, off_b_path, rows=False,
                  registers=None, cell="flipped"):
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

    out += collapse_line(t, label_a, label_b)

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
    at_least_16 = [row for row in b.values() if len(addrs_of(row)) >= 16]
    out.append("")
    out.append(f"  the flipped set's size distribution, against the census: "
               f"{deciles([len(addrs_of(b[k])) for k in flipped])}")
    out.append(f"                                            the census:  "
               f"{deciles(census_sizes)}")
    out.append(f"  of the {len(at_least_8)} committed cluster(s) of 8 addresses or more, "
               f"{sum(1 for row in at_least_8 if row['cluster_key'] in flipped)} flipped; "
               f"the largest committed cluster is {max(census_sizes) if census_sizes else 0} addresses")
    # A second cut point on the same distribution rather than a second census:
    # "the large clusters" is a range, and one threshold says which end of it
    # the flip set sits at without a reader having to choose a threshold.
    out.append(f"  of the {len(at_least_16)} of 16 or more, "
               f"{sum(1 for row in at_least_16 if row['cluster_key'] in flipped)} flipped")
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
    out += rank_shift_report(a, b, t)
    out.append("")
    # The table walks one cell of the four, and the *default* cell is the
    # flipped one: the two cells nothing changed in are the ones a reader
    # cannot see a row of otherwise, and `--cell` is how they get one. The
    # sizes and the cut points above stay on `flipped` whatever this is set to,
    # because they are about the flip and not about which rows are printed.
    verdict_of = {k: name for name, field in CELLS.items() for k in t[field]}
    listed = [k for k in t["shared"] if verdict_of.get(k) in TABLE_CELLS[cell]]
    out.append(f"  {'cluster_key':<14} {'name':<16} {'rank A':<12} {'rank B':<12} "
               f"{'size':>4} {'grew':>5} {'delta A':>8} {'delta B':>8}  verdict")
    for key in (listed if rows else listed[:12]):
        ra, rb = a[key], b[key]
        da = off_a.get(ra["cluster_id"])
        db = off_b.get(rb["cluster_id"])
        grew = len(addrs_of(rb) - addrs_of(ra))
        out.append(
            f"  {key:<14} {(rb['cluster_name'] or ra['cluster_name'] or '-'):<16} "
            f"{ra['cluster_id']:<12} {rb['cluster_id']:<12} "
            f"{len(addrs_of(rb)):>4} {grew:>5} "
            f"{(len(addrs_of(da) ^ addrs_of(ra)) if da else '-'):>8} "
            f"{(len(addrs_of(db) ^ addrs_of(rb)) if db else '-'):>8}  "
            f"{verdict_of[key]}")
    if not rows and len(listed) > 12:
        out.append(f"  ({len(listed) - 12} more; --rows for all of them)")
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

    The rows themselves are keyed, because an XDATA address both programs touch
    has two homes and the two are told apart by the key the row carries. That
    makes the key the row's identity here, so the collision check goes in with
    the header rather than being left to `pair`.
    """
    a, b = keyed_by(committed_a), keyed_by(committed_b)
    index_a = {addr: [k for k, row in a.items() if addr in addrs_of(row)]
               for addr in addrs}
    index_b = {addr: [k for k, row in b.items() if addr in addrs_of(row)]
               for addr in addrs}
    out = [f"  swept addresses: {len(addrs)}",
           f"  {'address':<8} {'cluster_key':<14} {'program':<8} "
           f"{'rank A':<12} {'rank B':<12} verdict"]
    # Both holder indexes above are `keyed_by` over a whole census, so a key two
    # ranks of one generation share leaves a holder neither the rows below nor
    # the summary can name -- and the summary counts holders, so it would come
    # out short rather than look wrong. Stated here, next to the count it
    # qualifies, and stated in `collision_line`'s words rather than a second
    # spelling of them: this used to hand-roll the sentence, which is how the
    # property ended up checked at one site and not the other. Conditional, the
    # way the key-indexed views are: `pair` prints the same check over the same
    # census either way, and an unconditional line here would be a second
    # opinion on a census two blocks of output away from that one.
    for census, label in ((committed_a, "A"), (committed_b, "B")):
        line = collision_line(census, f"committed {label}",
                              consequence="the rows below and the counts that "
                                          "follow them are over the key, so a "
                                          "shared key hides a rank",
                              only_if_collision=True)
        if line:
            out.append(line)
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
    # The two population censuses, checked over themselves, and above the block
    # they qualify rather than inside it. `keys_a` and `keys_b` above are
    # `keyed_by` maps, so this is the one re-keying in the file whose counts
    # *are* the population: the `N guard-off key(s)` figure the line below
    # prints, every rate's `population` column, and `holders_by_program`'s
    # per-program index are all read off the key, and a collision makes the
    # first of those come out short with nothing else in the report looking
    # wrong. Printed either way for the reason `collision_line` says. `across`
    # gets no such line: it re-keys only the committed censuses, which
    # `collapse_line` covers, and a guard-off line there would be a second
    # opinion about a census the mode never reads.
    for census, label in ((off_a, label_a), (off_b, label_b)):
        out.append(collision_line(census, "guard-off",
                                  consequence=f"the population and every rate's "
                                              f"{label} column are over the key, "
                                              f"so a shared key hides a rank"))
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
    # Every cell below is a list of keys drawn from the same join `across`
    # makes, so it carries the same caveat and states it in the same terms.
    out += collapse_line(t, label_a, label_b)
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
    check(set(moved) == {"main-ec-001", "main-ec-002"},
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

    # `deciles`, whose floor this fixture is the case for: its flipped set is
    # the two clusters k1 and k3, two addresses each, and that line is printed
    # beside a five-row census on the theory that both are ten-cell reads. It
    # is `across_report` that puts the two side by side, so the report line is
    # asserted on as well as the helper -- a helper that stopped stretching
    # would still leave a caller free to print the stretched string itself.
    check(any("the flipped set's size distribution" in ln
              and "too few to cut ten ways" in ln for ln in lines)
          and not any("2 2 2 2 2 2 2 2 2 2" in ln for ln in lines),
          "a flipped set of two clusters is reported as the two sizes it is, "
          "on the line itself -- not `2 2 2 2 2 2 2 2 2 2` read as a decile "
          "distribution beside the census's")
    check(deciles([]) == "no rows",
          "an empty set is reported before the floor rule applies")
    check(deciles(range(1, 11)) == "1 2 3 4 5 6 7 8 9 10"
          and len(deciles(range(1, 12)).split()) == 10,
          "ten rows is the floor: one whole row per cell, and crossing it does "
          "not change the shape of the read")
    check("too few to cut ten ways" in deciles(range(1, 10)),
          "nine rows is below the floor -- the cells already double up at the "
          "ends there, so the set is returned rather than repeated")
    check(deciles([3, 1, 2]) == "3 row(s), too few to cut ten ways: 1 2 3",
          "a set below the floor comes back sorted and marked, as the set it "
          "is and not as ten numbers a reader would take for deciles")

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

    # `pair_report`'s §6a line, which had no case: the call above this block is
    # the one self-test `pair_report` makes and it passes `registers=None`, so
    # the whole registers block was dead to `--self-test` and the number on it
    # was a signed sum under a directional label that nothing read. `on_b`/`off_b`
    # are generation B's own fixture, where `0x62` goes 0 -> 5 and nothing moves
    # the other way.
    lines, _c, _o, _m = pair_report("registers", committed, off, (on_b, off_b))
    check(any("references entering write 5, leaving write 0, net +5" in ln
              for ln in lines)
          and not any("leaving write 5" in ln for ln in lines),
          "a fixture where five references entered `write` and none left says "
          "so, and the signed sum of that is not printed under the word "
          "'leaving' -- which is what it used to be")

    # A decrease, because the first fixture has none: a one-directional one
    # cannot tell "both directions are counted" from "the count happens to be
    # right". The two cancel here, so a single signed total would print 0 and a
    # single gross count would print 4.
    two_way_on = write_registers(tmp, "twoway-on.csv",
                                 [("0x60", "2"), ("0x61", "7"), ("0x62", "0")])
    two_way_off = write_registers(tmp, "twoway-off.csv",
                                  [("0x60", "6"), ("0x61", "3"), ("0x62", "0")])
    lines, _c, _o, _m = pair_report("both ways", committed, off,
                                    (two_way_on, two_way_off))
    check(any("references entering write 4, leaving write 4, net +0" in ln
              for ln in lines)
          and any("closes: 1 + 1 = 2, over the 2 address(es)" in ln
                  for ln in lines),
          "a pair that moves one reference each way reports both counts, and "
          "the closes: line says they are over the two addresses that moved")

    # A negative net, read from the helper rather than from the printed line,
    # so the two are compared as a reader would read them. Neither direction is
    # a count that can be negative and the only figure here that carries a sign
    # is the net.
    net_on = write_registers(tmp, "net-on.csv",
                             [("0x60", "0"), ("0x61", "9"), ("0x62", "4")])
    net_off = write_registers(tmp, "net-off.csv",
                              [("0x60", "3"), ("0x61", "2"), ("0x62", "4")])
    movement = write_movement(registers_of(net_on), registers_of(net_off))
    lines, _c, _o, _m = pair_report("negative net", committed, off,
                                    (net_on, net_off))
    check(movement == (3, 7, -4, ["0x60"], ["0x61"])
          and any("references entering write 3, leaving write 7, net -4" in ln
                  for ln in lines)
          and not any("entering write -" in ln or "leaving write -" in ln
                      for ln in lines),
          "a negative net is still a net: entering and leaving are counts, "
          "each naming the address it moved, and neither carries a sign")

    # The closes: line, fired rather than assumed reachable. It compares a
    # string inequality against an integer subtraction, and the census writes
    # canonical integers everywhere, so the one input that reaches it is a
    # cell that is numerically but not textually equal.
    padded_on = write_registers(tmp, "padded-on.csv", [("0x60", "5")])
    padded_off = write_registers(tmp, "padded-off.csv", [("0x60", "05")])
    lines, _c, _o, _m = pair_report("padded", committed, off,
                                    (padded_on, padded_off))
    check(any("write changes 1 of 1" in ln for ln in lines)
          and any("references entering write 0, leaving write 0, net +0" in ln
                  for ln in lines)
          and any("MISMATCH" in ln for ln in lines),
          "when `changed` and the movement disagree the closes: line says so: "
          "a `05` against a `5` is a change as text and no movement as a number")

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

    # ------------------------------------------------------------------------
    # The rank-shift fixture, lettered F and G because the `cause` block above
    # is A and B and the two would otherwise write the same file names into the
    # one scratch directory this function makes.
    #
    # A census renumbered against itself, which the fixtures above cannot be:
    # `b_committed` is written from the same `committed_rows` as `committed`,
    # so the two committed censuses are content-identical and no key changes
    # rank between them at all. This pair is the same keys and the same
    # memberships under a different numbering, plus one cluster the second
    # census gained, so every claim a rank shift can make has a case here.
    wide = [f"0x{0x400 + i:04X}" for i in range(20)]
    half = wide[:10]
    added = [f"0x{0x500 + i:04X}" for i in range(9)]
    f_committed = write_census(tmp, "f-committed.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
        ("main-ec-002", "main-ec", ["0x10"], key(2)),
        ("main-ec-003", "main-ec", wide, key(5)),
        ("main-ec-004", "main-ec", ["0x70"], key(4)),
        ("main-ec-005", "main-ec", ["0x80"], key(6)),
        ("pd-001", "pd", ["0x20", "0x21"], key(3)),
        ("pd-002", "pd", ["0x0E", "0x50"], key(8))])
    f_off = write_census(tmp, "f-off.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x10"], key(1)),
        ("main-ec-002", "main-ec", ["0x10"], key(2)),
        ("main-ec-003", "main-ec", half, key(5)),
        ("main-ec-004", "main-ec", ["0x71"], key(4)),
        ("main-ec-005", "main-ec", ["0x81"], key(6)),
        ("pd-001", "pd", ["0x20", "0x21"], key(3)),
        ("pd-002", "pd", ["0x0E", "0x50"], key(8))])
    # The renumbering is an insertion at rank 2, so the `main-ec` keys below it
    # each move down one and the two above it are the ones that did not; the
    # `pd` ranking moves as a whole, which is the shape a program's own
    # re-partition produces and the reason a rank is not one scale.
    g_committed = write_census(tmp, "g-committed.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
        ("main-ec-002", "main-ec", added, key(9)),
        ("main-ec-003", "main-ec", ["0x10"], key(2)),
        ("main-ec-004", "main-ec", wide, key(5)),
        ("main-ec-005", "main-ec", ["0x70"], key(4)),
        ("main-ec-006", "main-ec", ["0x80"], key(6)),
        ("pd-002", "pd", ["0x20", "0x21"], key(3))])
    g_off = write_census(tmp, "g-off.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
        ("main-ec-002", "main-ec", added, key(9)),
        ("main-ec-003", "main-ec", ["0x10"], key(2)),
        ("main-ec-004", "main-ec", wide, key(5)),
        ("main-ec-005", "main-ec", ["0x71"], key(4)),
        ("main-ec-006", "main-ec", ["0x81"], key(6)),
        ("pd-002", "pd", ["0x20", "0x22"], key(3))])
    lines, t3 = across_report("F", f_committed, f_off, "G", g_committed, g_off)

    def delta_of(key_):
        return rank_of(t3["b"][key_])[1] - rank_of(t3["a"][key_])[1]

    def rows_of(lines_):
        """The table's own rows: every summary line above it starts with a
        word, and the '(N more)' line with a bracket."""
        return [ln for ln in lines_ if ln.lstrip().startswith("k0000000000")]

    # The rank is re-derived from the id here rather than written beside it, for
    # the reason the moved-count predicate above is restated rather than called:
    # a bare int inside a `check()` is a census figure to
    # `check_doc_figure_pins.py`, and a rank off a synthetic id is not one --
    # but nothing in that audit can tell the two apart, and a `pd-050` that
    # happens to read 50 turns a figure `xdata-census-rederivation-checklist.md`
    # §2b marks `unheld` into one this tool appears to pin. The four ids cover
    # the three shapes that discriminate: a hyphen in the program name, a rank
    # wider than the id's three-digit field, and one of each.
    rank_ids = ["main-ec-002", "pd-050", "main-ec-1234", "pd-007"]
    check([rank_of({"cluster_id": c})[1] for c in rank_ids]
          == [int(c.rsplit("-", 1)[1]) for c in rank_ids],
          "a rank is the number after the last hyphen, so neither the two-part "
          "program name nor a rank wider than the id's three-digit field is "
          "read as a digit or as a fixed window")
    check(t3["a_to_b"] == [key(1), key(5)] and delta_of(key(1)) == 0
          and t3["neither"] == [key(2)] and delta_of(key(2)) == 1,
          "a key's membership and its rank move independently: k1 changes cell "
          "at the rank it already had, and k2 holds its cell at a different "
          "rank -- the two directions the shift is not perfectly correlated with")
    check(any("4 of    5 changed rank; mean  +1.00 over those,  +0.80 over all" in ln
              for ln in lines),
          "both means are printed and each names its population, so \"changed "
          "by N on average\" cannot be read the wrong way round: +1.00 over the "
          "four keys that changed, +0.80 over all five")
    check(any("pd          1 of    1 changed rank" in ln for ln in lines),
          "a rank shift is reported per program, so a ranking that moved in one "
          "program and not in the other is two figures rather than one average")
    shift_cells = [k for field in CELLS.values() for k in t3[field]]
    check(sorted(shift_cells) == t3["shared"]
          and sum(1 for k in shift_cells if delta_of(k)) == 5
          and sum(1 for k in t3["shared"] if delta_of(k)) == 5,
          "the four cells partition the shared keys, so the per-cell "
          "changed-rank counts close on the one figure for the whole set")
    check(any("of the 2 committed cluster(s) of 8 addresses or more, 1 flipped" in ln
              for ln in lines)
          and any("of the 1 of 16 or more, 1 flipped" in ln for ln in lines),
          "two size cut points on one distribution, so \"the large clusters\" is "
          "a range and not a threshold a reader has to pick")
    check([ln.split()[0] for ln in rows_of(lines)] == [key(1), key(3), key(5)]
          and not any("intact-in-both" in ln for ln in rows_of(lines)),
          "the default cell is the flipped one, so the table is the one the "
          "report has always printed with two rank columns beside it")
    lines, _t = across_report("F", f_committed, f_off, "G", g_committed, g_off,
                              cell="intact-both")
    check([ln.split()[0] for ln in rows_of(lines)] == [key(2)]
          and "intact-in-both" in lines[-1],
          "--cell walks a cell the default does not: a key that never changed "
          "cell gets a row of its own, and only that key gets one")
    lines, _t = across_report("F", f_committed, f_off, "G", g_committed, g_off,
                              cell="all", rows=True)
    check([ln.split()[0] for ln in rows_of(lines)] == t3["shared"],
          "--cell all is every shared key, so the cells are walkable together "
          "as well as one at a time")

    # A census that collides. Every fixture above gives each rank its own
    # `cluster_key`, which is what a real census does -- the committed one
    # measures 439 rows over 439 distinct keys, and
    # `test_xdata_cluster_names.py::TheContentKey` is what says a changed
    # membership is a new key rather than a collision -- and which is exactly
    # why the case was unreachable: `write_census` takes a key per row, so
    # nothing above could put two ranks on one.
    #
    # Three ranks share k9 below and two of them change membership. That one
    # shape used to lose ranks from two different counts, and both counts
    # still closed afterwards, which is what made it invisible: `moved` was a
    # dict keyed on the key so one of the two movers fell out of it, and the
    # intact listing tested `cluster_key not in moved` so the *intact* rank
    # sharing the same key fell out of that.
    dup_committed = write_census(tmp, "dup-committed.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(9)),
        ("main-ec-002", "main-ec", ["0x10", "0x11"], key(9)),
        ("main-ec-003", "main-ec", ["0x40"], key(9)),
        ("pd-001", "pd", ["0x20", "0x21"], key(3))])
    dup_off = write_census(tmp, "dup-off.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x10"], key(9)),
        ("main-ec-002", "main-ec", ["0x10", "0x12"], key(9)),
        ("main-ec-003", "main-ec", ["0x40"], key(9)),
        ("pd-001", "pd", ["0x20", "0x21"], key(3))])
    dup_c, dup_o = clusters_of(dup_committed), clusters_of(dup_off)

    # `moved_ranks` is keyed on the rank, and a rank is a dict key of the
    # census read, so it is the one join in the tool that cannot collapse.
    # Compared against the same two lines the floor is applied to, as above.
    dup_moved = moved_ranks(dup_c, dup_o)
    dup_inline = [cid for cid, row in dup_c.items()
                  if cid in dup_o and row["addrs"] != dup_o[cid]["addrs"]]
    check(sorted(dup_moved) == dup_inline == ["main-ec-001", "main-ec-002"],
          "a duplicated cluster_key costs a moved rank nothing: both movers are "
          "counted, and the count is the suite's own two-line predicate's over "
          "the same pair, on a census where the two carry one key")

    lines, _c, _o, _m = pair_report("dup", dup_committed, dup_off, None)
    listing = [ln for ln in lines if ln.rstrip().endswith(("moved", "intact"))]
    said_moved = next(int(ln.split()[1]) for ln in lines if ln.startswith("  moved  "))
    said_intact = next(int(ln.split()[1]) for ln in lines if ln.startswith("  intact "))
    common = [cid for cid in dup_c if cid in dup_o]
    check(said_moved == 2 and said_intact == 2
          and said_moved + said_intact == len(common) == len(listing) == 4
          and sum(1 for ln in listing if ln.endswith("moved")) == 2
          and sum(1 for ln in listing if ln.endswith("intact")) == 2,
          "the listing holds a row per rank rather than a row per key, and the "
          "counts still close over the ranks the two censuses share: 2 moved + "
          "2 intact = 4 ranks, 4 rows")

    check(any("cluster_key COLLISION" in ln and key(9) in ln
              and all(cid in ln for cid in ("main-ec-001", "main-ec-002",
                                            "main-ec-003")) for ln in lines),
          "the collision is a line of its own, naming the key and every rank "
          "carrying it, rather than a count that came out smaller")

    # The other half. A census whose keys are distinct reports none, and says
    # it looked -- which is the state every census this tree holds is in, and
    # the reason the line above is a check rather than a decoration.
    check(duplicate_keys(c) == {}
          and duplicate_keys(dup_c) == {key(9): ["main-ec-001", "main-ec-002",
                                                 "main-ec-003"]}
          and "0 collision(s)" in collision_line(c),
          "a census whose keys are distinct reports no collision and says it "
          "looked, and a census that collides reports every rank on the key")

    # The key-indexed half, where the collision still costs something: the two
    # moved ranks project onto one key, so the table's counts are keys and its
    # four terms close over them regardless. A closure that closes is not
    # evidence that nothing was lost, which is the whole reason the line is
    # printed rather than left to be inferred from the arithmetic.
    #
    # The expectation in this check was
    # `{key(9): ["main-ec-001", "main-ec-002"]}` and "4 moved rank(s)", and
    # both moved when `flip_table`'s `collapsed` population was widened from
    # the moved ranks to the whole committed census the table's cells are drawn
    # from: `k9` carries a third rank, and `main-ec-003` is intact. Nothing else
    # in the check moved with it -- the two movers, the four-term closure and
    # the absence of a `MISMATCH` are the same three assertions as before, which
    # is what a widening is supposed to look like from here.
    lines, t3 = across_report("A", dup_committed, dup_off,
                              "B", dup_committed, dup_off)
    check(t3["collapsed"] == [{key(9): ["main-ec-001", "main-ec-002",
                                        "main-ec-003"]}] * 2
          and any("the counts below are keys, not the ranks `pair` counts" in ln
                  and "6 committed rank(s) across 2 generation(s)" in ln
                  and key(9) in ln for ln in lines)
          and not any("MISMATCH" in ln for ln in lines),
          "the key-indexed half reports the collision it cannot absorb -- three "
          "committed ranks on one key, of which two moved -- and the closure "
          "closes anyway")

    # The swept cross-reference, over the same census: its holder index is
    # `keyed_by` too, so 0x0E's `main-ec` holder is whichever of the two ranks
    # the map kept, and the summary counts that rather than both.
    lines = swept_report(dup_c, dup_c, flip_table(dup_c, dup_o, dup_c, dup_o), ["0x0E"])
    check(sum(1 for ln in lines if "cluster_key COLLISION" in ln) == 2
          and any("hides a rank" in ln and key(9) in ln for ln in lines),
          "the swept cross-reference says so too: both generations are named, "
          "and the holder count below is over the key rather than over the rank")

    # ------------------------------------------------------------------------
    # The scope of the check, over the one shape the six cases above cannot
    # reach. `dup_committed` has movers, and every one of those six cases reads
    # it: a collision between two ranks that both stayed put was silent by
    # construction rather than by decision, so the property was never reached
    # in the one census where it costs nothing and says everything.
    # `write_census()` needed no new knob to express it -- it takes a key per
    # row, and the only thing wrong with the old fixtures was that every caller
    # passed a distinct one.
    #
    # The fixtures below are censuses this tool's own hash would never produce:
    # `cluster_key` is a content hash over the program and the sorted
    # membership, so two ranks with different memberships carrying one key is
    # a forgery. That is the point rather than the objection -- the census this
    # check is not guaranteed to receive is written by a regeneration, not by
    # `xdata_register_map.py`'s hash of the same tree.
    intact_committed = write_census(tmp, "intact-committed.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(1)),
        ("main-ec-002", "main-ec", ["0x10"], key(2)),
        ("pd-001", "pd", ["0x20", "0x21"], key(3))])
    intact_off = write_census(tmp, "intact-off.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(9)),
        ("main-ec-002", "main-ec", ["0x10"], key(9)),
        ("pd-001", "pd", ["0x20", "0x21"], key(3))])

    # `pair` reads two censuses. It printed the precondition for the one whose
    # key `across` and `--swept` join on and said nothing about the one `cause`
    # reads by key -- and the line it did print says so unconditionally, so the
    # silence on the second read as a clean bill of health for the pair.
    lines, _c, _o, _m = pair_report("intact", intact_committed, intact_off, None)
    check(any("cluster_key unique across the 3 committed row(s): 0 collision(s)" in ln
              for ln in lines)
          and any("cluster_key COLLISION" in ln and "of the 3 guard-off keys" in ln
                  and key(9) in ln
                  and all(cid in ln for cid in ("main-ec-001", "main-ec-002"))
                  for ln in lines)
          and any(ln.startswith("  moved      0") for ln in lines)
          and any(ln.startswith("  intact     3") for ln in lines),
          "a guard-off collision between two ranks that both stayed put is a "
          "line of its own: `pair` checked the census it does not join on and "
          "left the one `cause` does as a clean bill of health")

    # `collapsed` was derived from the moved ranks, so a census whose only
    # collision is between two intact ones reported nothing at all -- while the
    # censuses the same collision is drawn from in every other case would have
    # caught it. Nothing moved here and nothing is wrong with the four cells.
    across_committed = write_census(tmp, "across-intact-committed.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(9)),
        ("main-ec-002", "main-ec", ["0x10"], key(9)),
        ("pd-001", "pd", ["0x20", "0x21"], key(3))])
    across_off = write_census(tmp, "across-intact-off.csv", [
        ("main-ec-001", "main-ec", ["0x0E", "0x0F"], key(9)),
        ("main-ec-002", "main-ec", ["0x10"], key(9)),
        ("pd-001", "pd", ["0x20", "0x21"], key(3))])
    lines, t4 = across_report("A", across_committed, across_off,
                              "B", across_committed, across_off)
    check(t4["collapsed"] == [{key(9): ["main-ec-001", "main-ec-002"]}] * 2
          and not t4["moved_a"] and not t4["moved_b"]
          and collapse_line(t4, "A", "B")
          and any("4 committed rank(s) across 2 generation(s) share a key" in ln
                  and key(9) in ln for ln in lines)
          and not any("MISMATCH" in ln for ln in lines),
          "a committed census whose only collision is between two ranks that "
          "did not move still prints it: the population is the census the cells "
          "are drawn from, so `collapsed` is not the moved subset of it, and a "
          "zero moved count is not a reason to say nothing")

    # The guard-off population of `cause`, which is the one re-keying in the file
    # whose counts *are* the population: `len(keys_a)` prints it, every rate's
    # `population` column divides by it, and `holders_by_program` indexes it.
    # `dup_committed`/`dup_off` would do here too, but the fixture above is the
    # one whose ranks are intact, so the collision is visible in the report as
    # 3 rows over 2 keys and nothing else in the output moves.
    lines, _t, _cells = cause_report("A", intact_committed, intact_off,
                                     "B", intact_committed, intact_off,
                                     registers=(on_a, off_a, on_b, off_b))
    guard = [i for i, ln in enumerate(lines)
             if "cluster_key COLLISION" in ln and "of the 3 guard-off keys" in ln]
    population = next((i for i, ln in enumerate(lines)
                       if ln.lstrip().startswith("the population:")), -1)
    check(len(guard) == 2 and 0 <= population and all(i < population for i in guard)
          and all(key(9) in lines[i] and "main-ec-001" in lines[i]
                  and "main-ec-002" in lines[i] for i in guard)
          and lines[population].strip() == "the population: 2 guard-off key(s) "
                                          "in A, 2 in B",
          "both guard-off censuses carry their own precondition line, above the "
          "population they qualify: 3 rows are 2 keys, and every rate below "
          "divides by that 2")

    # The docstring's claim, as a case rather than as a sentence: each of the
    # six (view, census) pairs `keyed_by`'s docstring names carries a line about
    # the census in question. All four views run over one census that collides,
    # so a view that lost its check is a red run rather than prose nobody
    # executes. The wanted substring is the line the check emits and never the
    # cross-reference's own `cluster_key` column header, which every report
    # printing a key-indexed table has and which says nothing about whether the
    # check ran.
    pair_lines, _c, _o, _m = pair_report("cover", dup_committed, dup_off, None)
    across_lines, _t = across_report("A", dup_committed, dup_off,
                                     "B", dup_committed, dup_off)
    swept_lines = swept_report(dup_c, dup_c,
                               flip_table(dup_c, dup_o, dup_c, dup_o), ["0x0E"])
    cause_lines, _t, _c = cause_report("A", dup_committed, dup_off,
                                       "B", dup_committed, dup_off,
                                       registers=(on_a, off_a, on_b, off_b))
    covered = (("pair", pair_lines, "of the 4 committed keys"),
               ("pair", pair_lines, "of the 4 guard-off keys"),
               ("across", across_lines, "the counts below are keys"),
               ("--swept", swept_lines, "cluster_key COLLISION"),
               ("cause", cause_lines, "the counts below are keys"),
               ("cause", cause_lines, "of the 4 guard-off keys"))
    check(all(any(wanted in ln for ln in lines) for _view, lines, wanted in covered),
          "every view that re-keys a census carries a line about that census: "
          "`pair` for both of the two it reads, `across`, `--swept` and `cause` "
          "for the committed pair, and `cause` for the guard-off one -- which is "
          "the claim `keyed_by`'s docstring makes about the file")

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
                         "clusters of the selected cell in across, the followed "
                         "substitutions in cause")
    ap.add_argument("--cell", default="flipped", choices=list(TABLE_CELLS),
                    help="which cell of the flip table the per-key table walks "
                         "(default: flipped, the two cells a key changes between)")
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
                                 registers=quad if all(quad) else None,
                                 cell=args.cell)
    print("\n".join(lines))
    if args.swept:
        print()
        print("\n".join(swept_report(clusters_of(args.old_a),
                                     clusters_of(args.old_b), table, args.swept)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
