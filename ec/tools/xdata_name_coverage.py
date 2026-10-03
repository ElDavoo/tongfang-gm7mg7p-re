#!/usr/bin/env python3
"""The name-indexed half of the carry report: what happened to *every* hand
name, rather than to every new cluster (issue #881).

`carry_names()` in `xdata_register_map.py` answers the question a **cluster**
asks -- "what name does this cluster carry" -- and appends one record per new
cluster. A hand name whose `cluster_key` is not a cluster of this run, and
which no new cluster reaches at `CARRY_MIN_JACCARD`, is therefore in no record
at all, and no cell of the tally accounts for it either: those five counters
sum the number of *clusters* that carried a name, which is not the number of
names in `annotations/xdata-cluster-names.csv`. On a run that re-clusters the
two differ, and a reader holding only what the run printed cannot tell "every
name is accounted for" from "two names fell under the floor".

This module is the transpose. One record per **row of the names file**, so
every name produces an outcome on every run that builds a census -- the two
lists are transposes of one another, which is why a name can appear here and
in no cluster's record at all.

**A sibling of `cluster_name_shape.py`, not a part of the tool.** `xdata_register_map`
imports this module, so importing it back would be a cycle. `jaccard` is
therefore restated below rather than shared: a shared copy that drifted would be
a worse defect than the duplication. The alternative -- moving `jaccard` into a
third module -- is a reorganisation of a file no bug in it asks for, and that
file is the one every `--no-eq-guard` line citation in the tree resolves
against.

**The outcomes are the cluster-indexed half's, plus two.** `seeded`, `exact`,
`overlap` and `none` mean here what they mean there. `tie` cannot occur: a tie
is two named rows being the joint best match for *one* new cluster, which is a
claim about a cluster and has no name-indexed spelling. The mirror of that is
this module's own:

    duplicate      two new clusters reach this name at the same best score,
                   or one reaches it and a hand claim reaches it elsewhere.
                   Which of them the name belongs to is a fact about the
                   clustering and not a coin this module flips, so a tie
                   between the claimants is carried to none -- the same
                   refusal `tie` already makes. A hand claim wins outright,
                   and unequal scores pick the better cluster, because a
                   refusal is for an undecidable case and not for a multi-claim
                   as such
    key-not-found  the names file's key is not a cluster of the committed
                   census, so there is no membership to score against. That is
                   **not** a score of `0.00`: a name with nothing to be
                   compared against and a name compared against every cluster
                   and matching none are different findings, and printing them
                   the same way would make the first look like the second

**Every one of these says *not carried by this method*.** None says a name was
lost, gone, absent or dropped, for the reason `xdata_register_map.py`'s own
module docstring gives: a function that stopped decompiling, a threshold that
moved and a cluster that stopped existing are four different things, and this
rule can only report that it did not fire.

Nothing here needs the firmware. It reads the two committed CSVs and the names
file, and `test_xdata_name_coverage.py` drives it on synthetic fixtures: no
image, no Ghidra, no hardware, no Windows, no network.
"""


def jaccard(a, b) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


# The `how` values that mean the name is on a cluster of this run's written
# census. The tally and the per-name lines both key off this one list, so the
# clause and the lines cannot disagree about which names went unwritten.
CARRIED = ("seeded", "exact", "overlap")
# `seeded` and `exact` are the two whose `name` is a *fact about a key*: the
# names file named this exact key, or a named row of the committed census has
# it. `overlap` is this rule's own arithmetic, and arithmetic is what a second
# pass is allowed to overrule.
BY_KEY = ("seeded", "exact")

# Every `how` whose record carries a name, which is what makes a cluster a
# claimant of one. `duplicate` is here as well as `overlap` because
# `carry_names()`'s second pass rewrites a losing record's `how` to
# `duplicate` and *keeps* its name, so a caller running after that pass --
# every caller of `coverage()` -- has to count the losers as claims too.
CLAIMED = ("seeded", "exact", "overlap", "duplicate")


def duplicate_claims(report):
    """{name: [(cluster_id, score), ...]} for the names more than one new
    cluster reaches, best score first, ties broken by cluster id.

    Every record that carries a name takes part (`CLAIMED`, above), and that
    is deliberate: the question is how many clusters this run put the name on,
    and a cluster that got it by key is one of them. `resolve_duplicate()` is
    where the kinds are told apart.

    `duplicate` is in `CLAIMED` alongside `overlap` because `carry_names()`'s
    second pass rewrites a losing record's `how` to `duplicate` and *keeps* its
    name -- so a caller that runs after that pass, which is every caller of
    `coverage()`, has to recognise the losers as claims too. Reading only
    `overlap` there finds no multi-claim at all, and reports a name this rule
    explicitly refused as a `none` against a single cluster.
    """
    claims = {}
    for r in report:
        name = (r.get("name") or "").strip()
        if not name or r.get("how") not in CLAIMED:
            continue
        claims.setdefault(name, []).append((r["cluster_id"], r["jaccard"]))
    return {n: sorted(v, key=lambda t: (-t[1], t[0]))
            for n, v in claims.items() if len(v) > 1}


def resolve_duplicate(claimants, by_key) -> set:
    """The cluster ids of a multi-claim that keep the name.

    `by_key` maps cluster id to the `how` of the record that claimed the name
    on it, so a hand claim can be told from a guess. The rules are applied in
    the order of what they are evidence of:

    1. **a hand claim keeps it, and no guess can take it from it.** `seeded` is
       a human saying which cluster this name is, and this rule's own
       arithmetic does not overrule the hand. Two hand claims are the names
       file listing one name against two keys; both are the file, and refusing
       either would overrule the file this module exists to report on
    2. otherwise the highest-scoring guess keeps it
    3. two guesses at the same best score keep it to **neither**. Which of the
       two clusters the name belongs to is a fact about the clustering, and
       picking one would make the written CSV depend on the sort order

    A set rather than one id because rule 1 can keep two. Every caller turns
    it into a per-record yes/no, so the callers do not care how many.
    """
    hands = [c for c in claimants if by_key.get(c[0]) in BY_KEY]
    if hands:
        return {c[0] for c in hands}
    if claimants[0][1] != claimants[1][1]:
        return {claimants[0][0]}
    return set()


def coverage(old_rows, seeded, new_rows, report, min_jaccard):
    """One record per row of the names file, sorted by name.

    Each record is `{name, key, how, jaccard, carried_to, detail, clusters}`,
    where `clusters` is how many new clusters this name was scored against --
    the denominator the printed line needs, carried on the record because
    `print_coverage()` is handed the list and nothing else.

    A name the run carried takes the outcome the report already gave it, so
    this never contradicts the cluster-indexed half about a name both of them
    have something to say about. A name the run did not carry is scored here
    instead, from its own side: the membership the name is anchored to, against
    every new cluster. That is the case `carry_names()` has no record for, and
    it is the whole reason this function exists.

    **Carried is asked before duplicate, and the order is the claim.** A name
    seeded onto one key that two *other* clusters also reach is carried: it is
    on a row of the written census, and reporting it as a duplicate would
    claim the name is on no row, which is the one thing this report is not
    allowed to say. The two refused guesses are not lost by that -- they are
    the `duplicate` records in the cluster-indexed report, which is the half
    that speaks in clusters.

    `jaccard` is `None` for a `key-not-found` name, never `0.0`: a name with no
    membership to score has not scored zero, and a `0.00` in a report is a
    reading of it.
    """
    by_key = {r.get("cluster_key", ""): r for r in old_rows}
    landed = {}
    for r in report:
        name = (r.get("name") or "").strip()
        if name and r.get("how") in CARRIED:
            landed[name] = r
    claims = duplicate_claims(report)
    out = []
    for key, name in sorted(seeded.items(), key=lambda kv: (kv[1], kv[0])):
        clusters = len(new_rows)
        here = landed.get(name)
        if here is not None:
            out.append({"name": name, "key": key, "how": here["how"],
                        "jaccard": here["jaccard"],
                        "carried_to": here["cluster_id"], "detail": "",
                        "clusters": clusters})
            continue
        dup = claims.get(name)
        if dup is not None:
            # Two new clusters, the same best score: reported as a duplicate
            # and carried to none. `detail` names them so the record stands on
            # its own without the printed line beside it.
            out.append({"name": name, "key": key, "how": "duplicate",
                        "jaccard": dup[0][1], "carried_to": "",
                        "detail": ", ".join(cid for cid, _s in dup),
                        "clusters": clusters})
            continue
        addrs = set((by_key.get(key) or {}).get("addrs", "").split())
        if not addrs:
            out.append({"name": name, "key": key, "how": "key-not-found",
                        "jaccard": None, "carried_to": "", "detail": "",
                        "clusters": clusters})
            continue
        scored = sorted(((jaccard(addrs, set(r["addrs"].split())), r["cluster_id"])
                         for r in new_rows), key=lambda t: (-t[0], t[1]))
        best = scored[0][0] if scored else 0.0
        winners = [t for t in scored if t[0] == best]
        if best < min_jaccard:
            detail = ""
        else:
            # The score cleared the floor and the name is still on no cluster,
            # so "under the floor" would be false here and the line has to say
            # something else. What is provable **from this side** is narrow:
            # the clusters it matched, and that none of them carries it -- a
            # cluster that carries nothing is reached by a `tie`, so claiming
            # those clusters "carry a different name" would be an overclaim
            # about a record this function has not looked at.
            detail = (f"best Jaccard {best:.2f} against "
                      f"{', '.join(cid for _s, cid in winners)}, and this run "
                      f"carries it on none of them")
        out.append({"name": name, "key": key, "how": "none",
                    "jaccard": best, "carried_to": "", "detail": detail,
                    "clusters": clusters})
    return out


def tally_clauses(cov, names_rel) -> str:
    """The `names:` line's conditional tail: `""` when there is nothing to add.

    A run where every name is carried prints today's line, character for
    character. That is the constraint #851 left in place and the reason these
    are clauses rather than two more unconditional counters: a sixth cell
    would be a different line on every run in the tree's transcripts, and
    "the committed shape is byte-identical" is a property a reader can check
    by diffing stderr rather than one they have to take on trust.

    **The duplicate clause counts a refusal, not a carry.** A record reaches
    `how == "duplicate"` here only when the carried branch above it did not
    take it, and `coverage()` asks carried first precisely so that a name on a
    row of the written census is never reported as unwritten. So every name
    this cell counts is one `resolve_duplicate()` refused -- carried to
    **none** of the claimants, the same decision `print_coverage()` prints and
    `carry_names()` writes. A clause reading "carried to two clusters" here
    would contradict the per-name line beside it and the CSV, and would be the
    overclaim this module's own docstring rules out; the tally is the line a
    reader takes away from the block, so it has to say what the rule did
    rather than the reverse of it.

    "More than one cluster" rather than a fixed count, because
    `duplicate_claims()` returns any name in more than one record and this cell
    sums across names of differing claimant counts.
    """
    out = []
    dupes = sum(1 for r in cov if r["how"] == "duplicate")
    if dupes:
        out.append(f", claimed by more than one cluster, not carried {dupes}")
    lost = sum(1 for r in cov if r["how"] not in CARRIED)
    if lost:
        out.append(f", and {lost} of the {len(cov)} names in {names_rel} are "
                   f"not carried by this method")
    return "".join(out)


def print_coverage(cov, min_jaccard, stream) -> None:
    """One line per name this run did not carry, to `stream`.

    A carried name prints nothing: the cluster-indexed lines above already say
    how it got there, and a name printed twice for one outcome is the same
    redundancy the tally is a tally of.
    """
    for r in cov:
        if r["how"] in CARRIED:
            continue
        if r["how"] == "duplicate":
            n = len(r["detail"].split(", "))
            print(f"    {r['name']} ({r['key']}) is claimed by {n} clusters at "
                  f"Jaccard {r['jaccard']:.2f} ({r['detail']}); carried to none, "
                  f"because the rule will not pick between them", file=stream)
        elif r["how"] == "key-not-found":
            print(f"    {r['name']} ({r['key']}) has no membership in the "
                  f"committed census to score against, so this method cannot "
                  f"say whether it would be carried; not carried by this run",
                  file=stream)
        elif r["detail"]:
            # The score cleared the floor and the name is still not carried,
            # so "under the floor" would be false here. `detail` says which
            # cluster and why instead.
            print(f"    {r['name']} ({r['key']}) is not carried by this run: "
                  f"{r['detail']}", file=stream)
        else:
            print(f"    {r['name']} ({r['key']}) is not carried by this run: "
                  f"best Jaccard {r['jaccard']:.2f} against any of the "
                  f"{r['clusters']} clusters, under the {min_jaccard:.2f} floor",
                  file=stream)
