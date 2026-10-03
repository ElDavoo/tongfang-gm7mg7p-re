#!/usr/bin/env python3
"""How many clusters the 0x0300-0x05FF working page holds, on both sides of the
re-derivation, and which of them the added addresses landed in.

`annotations/xdata-cluster-names.csv`'s `mode-oem-init` note claims the pass
"merged three of the page's clusters into one". Nothing had tested it. This
counts the page's clusters in both censuses, splits the added addresses by
whether they are on the page, and reports the correspondence in **both**
directions -- because the two directions are not the same measurement and
picking either one alone decides the answer:

  * **Absorption**, the direction the claim is about: how many *earlier* page
    clusters each later page cluster took in. This is the count
    `xdata_register_map.py --map` already computes, at the same
    `CARRY_MIN_JACCARD`, and it is reported here per program rather than
    across both.
  * **Feeding**, the direction the same data supports when the Jaccard
    threshold is not consulted: how many earlier page clusters contributed at
    least one *page* address to each later one.

**Why both, and it is not belt-and-braces.** `CARRY_MIN_JACCARD = 0.50` is not
reliable at counting many-into-one merges, and the `1/n` bound usually quoted
for it is a statement about *equal* merges only. If three equal disjoint
clusters merge into their union, each of the three scores `1/3` against it --
below 0.50 for any pairwise comparison, at *any* threshold a carry rule could
use, because for an `n`-into-one merge of equal-sized clusters the score is
`1/n` however the threshold is set. An *unequal* merge has no such bound: its
dominant feeder scores `max|Ai| / sum(|Aj|)` against the feeders' union, which
rises towards 1.0 as one feeder comes to dominate and can clear 0.50 outright.
Neither makes the column a counter, because what it scores is each earlier
cluster against the whole later one, so everything else the later cluster holds
dilutes the best score back towards 0 -- the same feeder that clears 0.50
against the feeders' union can sit far below it against the cluster that took
them. So a zero in this column can mean an equal merge, an unequal merge, or no
merge at all, and a rule that sees some merges and not others is not one that
can be trusted to count them.
[`docs/findings/xdata-page-cluster-count.md`](../../docs/findings/xdata-page-cluster-count.md)
§4 works both mechanisms through on this repository's own pair. The feeding
column carries no threshold: it asks only whether an address arrived, so it is
the column that can carry a merge, and the two are printed side by side so the
disagreement between them is visible rather than resolved in whichever
direction was implemented first.

Feeding is deliberately the weaker question, and it is labelled as such. One
address landing in a large cluster is not a merge of anything, and a large
cluster accumulates such addresses by being large. That is why the report
prints, beside every feeding count, how much of each contributing cluster's
page membership actually crossed over -- a feeder that gave up one address of
three is a different event from one that gave up all of it, and the count alone
cannot tell them apart.

**A page address count is a union, never a sum.** An address both programs
touch is indexed under a `main-ec` row and a `pd` row at the same instant, so
summing per-row membership counts such an address twice. The rule is printed on
its own output line rather than left for a reader to infer from two numbers
that disagree, and `--self-test` holds a fixture where the two differ.

**The page is a membership filter, not a clustering parameter.** Nothing here
re-derives either census: both are read as files, and the two generations are
the two guard-on CSVs the 155-address figure is defined over, so the added set
is `set(registers_b) - set(registers_a)` exactly as
`xdata_moved_ranks.py`'s `added_addresses` derives it. `xdata_register_map.py`
is not imported; `CARRY_MIN_JACCARD` is restated here with a self-test
asserting the two constants agree, because a second copy of a threshold that
silently drifted would make every absorption figure here a different rule from
the one the rest of the tree uses.

**What this cannot show.** Both censuses are committed text and the far one is
a historical commit, not a live reading: no image is opened, no register is
read back, and no laptop, EC or Windows machine is involved. A correspondence
here is arithmetic over two clusterings, so a merge or a split it reports is a
statement about the co-reading matrix at threshold 0.5, not about the firmware.

Usage:
    python3 xdata_page_clusters.py --old-clusters OLD.csv --new-clusters NEW.csv
    python3 xdata_page_clusters.py --old-clusters OLD.csv --new-clusters NEW.csv \\
        --old-registers A.csv --new-registers B.csv --page 0x0300 0x05FF [--rows]
    python3 xdata_page_clusters.py --self-test
"""
import argparse
import csv
import os
import re
import sys
import tempfile

# The membership-overlap score `xdata_register_map.py` carries a name across a
# re-derivation at. Restated rather than imported: this tool opens no module
# from beside it, so a rename there cannot silently change the rule here, and
# `self_test` holds the two constants equal so a drift is caught rather than
# absorbed.
CARRY_MIN_JACCARD = 0.50

# How many earlier page clusters make a later one the "three ... into one" the
# note names. The threshold is the claim's own number, not a tuned one, and it
# is a named constant so the verdict line reads as a test of that sentence
# rather than as a fact about the page.
MERGE_CLAIM = 3


def clusters_of(path):
    """The rows of a clusters CSV, in file order."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def registers_of(path):
    """{int: row} from a per-address registers CSV.

    The key is the parsed address rather than the CSV's `0xNNNN` text, because
    the added set is a set difference between two of these and a string set
    would be a difference over spellings. Every generator here writes one
    spelling, so the two agree today and only one of them is right.
    """
    with open(path, newline="") as f:
        return {int(r["addr"], 16): r for r in csv.DictReader(f)}


def addrs_of(row):
    """The row's membership, from the `addrs` column and never `addr_range`.

    `addr_range` is a min-max span, so a cluster holding `0x0300` and `0x300E`
    spans every address between them and counting over it would invent
    membership the census does not claim. It cannot be used to count, only to
    describe, which is why `xdata_register_map.py --threshold-sweep` prints it
    and counts nothing by it.
    """
    return {int(tok, 16) for tok in (row.get("addrs") or "").split()}


def jaccard(a, b):
    return 0.0 if not a and not b else len(a & b) / len(a | b)


def page_of(row, page):
    """The row's addresses inside the page."""
    lo, hi = page
    return {a for a in addrs_of(row) if lo <= a <= hi}


def page_clusters(rows, page):
    """The rows holding at least one address on the page, in file order."""
    return [r for r in rows if page_of(r, page)]


def page_addresses(rows, page):
    """Every address on the page that any row holds -- a union, not a sum.

    The two differ wherever an address is in two rows, and here they do: an
    XDATA address both programs touch is one address with a `main-ec` home and
    a `pd` home, so summing the per-row counts reports it twice. The callers
    print the rule next to the number; this is the function that obeys it.
    """
    out = set()
    for row in rows:
        out |= page_of(row, page)
    return out


def added_addresses(old_registers, new_registers):
    """`set(b) - set(a)`: the addresses the later census has that the earlier
    one did not. The same derivation `xdata_moved_ranks.py` uses, over the two
    guard-on registers CSVs -- which is what the note's 155 is defined over."""
    return set(new_registers) - set(old_registers)


def correspondences(old_rows, new_rows, page):
    """(absorbed, feeding) for the two directions of the correspondence.

    `absorbed` is `{new_id: [(old_id, jaccard), ...]}` over the earlier *page*
    clusters that clear `CARRY_MIN_JACCARD` against each later cluster of the
    **same program**, which is the rule `xdata_register_map.py --map` applies
    and the one the note's 0.84 is a score under. Matching across programs is
    not done and not approximated: a shared address number is not a shared
    byte, so a `main-ec` cluster and a `pd` cluster with the same membership
    are two different things and a correspondence across them would be a
    sentence about neither.

    `feeding` is `{new_id: [(old_id, crossed, total), ...]}` and carries no
    threshold at all: an earlier page cluster is a feeder when at least one of
    its page addresses is in the later cluster. `crossed`/`total` is how much
    of the feeder's page membership got there, because a count that cannot
    distinguish a whole cluster arriving from one address of three arriving is
    not the count a merge claim needs.
    """
    old_page = page_clusters(old_rows, page)
    absorbed, feeding = {}, {}
    for new in page_clusters(new_rows, page):
        new_page = page_of(new, page)
        same = [o for o in old_page if o["program"] == new["program"]]
        absorbed[new["cluster_id"]] = [
            (o["cluster_id"], jaccard(page_of(o, page), new_page))
            for o in same
            if jaccard(page_of(o, page), new_page) >= CARRY_MIN_JACCARD]
        feeders = []
        for o in same:
            own = page_of(o, page)
            crossed = len(own & new_page)
            if crossed:
                feeders.append((o["cluster_id"], crossed, len(own)))
        feeding[new["cluster_id"]] = sorted(feeders)
    return absorbed, feeding


def _fmt_addr(value):
    return f"0x{value:04X}"


def duplicate_ids(rows):
    """{cluster_id: [row index, ...]} for an id two rows of one census share.

    A precondition rather than an assumption, and the failure it looks for is a
    count that is quietly too small: `absorbed`, `feeding` and the holders map
    are all keyed by `cluster_id`, so two rows under one id collapse into one
    entry and a page cluster disappears from the report without anything else
    moving. `cluster_id` is a rank and is unique in every census in this tree,
    so this is expected to find nothing -- which is why it is printed either
    way. A run that reports nothing is a run that looked and found nothing,
    which is a different claim from a run that never looked.
    """
    held = {}
    for index, row in enumerate(rows):
        held.setdefault(row["cluster_id"], []).append(index)
    return {cid: ix for cid, ix in held.items() if len(ix) > 1}


def collision_line(rows, label):
    """The one line a report prints about that precondition."""
    dupes = duplicate_ids(rows)
    if not dupes:
        return f"    {label}: every cluster_id is one row, so nothing is keyed twice"
    return (f"    {label}: {len(dupes)} cluster_id(s) are held by more than one row "
            f"({', '.join(sorted(dupes)[:5])}), so the tables below key those rows "
            "together and undercount the page")


def page_cluster_report(old_label, old_path, new_label, new_path, page,
                        old_registers=None, new_registers=None, rows=False):
    """The report, as a list of lines.

    Every figure is printed beside the rule that produced it, and the two
    correspondence directions are printed as two sections rather than merged
    into one verdict, because they disagree on this pair and a reader who saw
    only one of them would draw the wrong conclusion.
    """
    old_rows, new_rows = clusters_of(old_path), clusters_of(new_path)
    old_page = page_clusters(old_rows, page)
    new_page = page_clusters(new_rows, page)
    old_addrs, new_addrs = page_addresses(old_rows, page), page_addresses(new_rows, page)
    by_id = {r["cluster_id"]: r for r in new_rows}
    # Once: the holders table and the two correspondence sections below all read
    # it, and two calls would be two chances for the two to disagree.
    absorbed, feeding = correspondences(old_rows, new_rows, page)
    lo, hi = page
    out = [f"page {_fmt_addr(lo)}-{_fmt_addr(hi)}",
           f"  old  {old_label}: {len(old_rows)} rows, {len(old_page)} on the page, "
           f"{len(old_addrs)} distinct page addresses",
           f"  new  {new_label}: {len(new_rows)} rows, {len(new_page)} on the page, "
           f"{len(new_addrs)} distinct page addresses",
           f"  page clusters: {len(old_page)} -> {len(new_page)} "
           f"({len(new_page) - len(old_page):+d})",
           "  distinct page addresses are a union over the rows holding them, not a "
           "sum over rows: an address both programs touch is indexed under a "
           "main-ec row and a pd row, and summing would count it twice"]
    out += ["", "  " + collision_line(old_rows, "old").lstrip(),
            "  " + collision_line(new_rows, "new").lstrip()]

    if not old_addrs and not new_addrs:
        # Named rather than printed as a confident 0, so a page nothing touches
        # reads as a page nothing touches and not as a measurement that came
        # back empty.
        out.append(f"  nothing on {_fmt_addr(lo)}-{_fmt_addr(hi)} in either census; "
                   "every count below is over an empty page")

    if old_registers and new_registers:
        added = added_addresses(old_registers, new_registers)
        on = sorted(a for a in added if lo <= a <= hi)
        off = sorted(a for a in added if not lo <= a <= hi)
        out += ["",
                f"  added addresses: {len(added)}",
                f"    {'on the page':<14} {len(on):>4}",
                f"    {'off the page':<14} {len(off):>4}"
                + (("  " + " ".join(_fmt_addr(a) for a in off)) if off else "")]
        # Every on-page address is in some row, and a row holding one is a page
        # cluster by definition -- so this map is empty exactly when the on-page
        # set is, and the two cases are worded apart rather than run together.
        # "Landed nowhere" would be the wrong sentence for an added set with
        # nothing on the page to land.
        holders = {}
        for new in new_page:
            hit = sorted(a for a in on if a in addrs_of(new))
            if hit:
                holders[new["cluster_id"]] = hit
        if on and not holders:
            out.append("  the on-page added addresses are in no page cluster of this "
                       "page, which is a disagreement to read and not a quiet zero")
        elif on:
            out += ["",
                    f"  page clusters the {len(on)} on-page added address(es) landed in: "
                    f"{len(holders)}"]
            header = (f"    {'cluster_key':<14} {'id':<12} {'added':>6} "
                      f"{'absorbed':>8} {'fed by':>7}  name")
            out += [header]
            for cid in sorted(holders, key=lambda c: (by_id[c]["program"], c)):
                row = by_id[cid]
                out.append(f"    {row['cluster_key']:<14} {cid:<12} "
                           f"{len(holders[cid]):>6} {len(absorbed[cid]):>8} "
                           f"{len(feeding[cid]):>7}  {row['cluster_name'] or '-'}")
        else:
            out.append("  no added address is on this page, so there is none to "
                       "attribute to a page cluster")

    out += ["",
            f"  absorption at CARRY_MIN_JACCARD {CARRY_MIN_JACCARD:.2f} -- how many "
            "earlier page clusters each later one took in",
            "    an n-into-one merge of equal-sized clusters scores 1/n per "
            "cluster, below the threshold at any setting; an unequal merge's "
            "dominant feeder scores max|Ai|/sum(|Aj|) against the feeders' "
            "union and can clear it, but this column scores it against the "
            "whole later cluster, so everything else that cluster holds "
            "dilutes it; a zero here is not evidence of no merge"]
    listed = [(cid, v) for cid, v in absorbed.items() if v]
    listed.sort(key=lambda t: (-len(t[1]), t[0]))
    if listed:
        for cid, hits in (listed if rows else listed[:12]):
            best = max(score for _cid, score in hits)
            out.append(f"    {by_id[cid]['cluster_key']:<14} {cid:<12} "
                       f"{len(hits):>3} earlier page cluster(s), best "
                       f"{best:.2f}  {by_id[cid]['cluster_name'] or '-'}")
        if not rows and len(listed) > 12:
            out.append(f"    ... {len(listed) - 12} more; --rows prints them all")
    else:
        out.append("    no later page cluster took in an earlier page cluster at this "
                   "threshold")

    out += ["",
            "  feeding -- how many earlier page clusters put at least one page "
            "address in each later one, with no threshold",
            "    a count is not a merge: a large cluster collects single addresses "
            "by being large, so how much of each feeder's page membership crossed "
            "is printed beside it"]
    fed = [(cid, v) for cid, v in feeding.items() if v]
    fed.sort(key=lambda t: (-len(t[1]), t[0]))
    if fed:
        for cid, feeders in (fed if rows else fed[:12]):
            whole = sum(1 for _c, crossed, total in feeders if crossed == total)
            out.append(f"    {by_id[cid]['cluster_key']:<14} {cid:<12} "
                       f"{len(feeders):>3} feeder(s), {whole} of them whole  "
                       f"{by_id[cid]['cluster_name'] or '-'}")
        if not rows and len(fed) > 12:
            out.append(f"    ... {len(fed) - 12} more; --rows prints them all")
    else:
        out.append("    no later page cluster holds a page address of an earlier one, "
                   "so the page's clusters share no membership across the two "
                   "censuses at all")

    heavy = [(cid, v) for cid, v in feeding.items() if len(v) >= MERGE_CLAIM]
    # A feeder that gave up its whole page membership is a different event from
    # one that gave up an address, so the two are counted apart and the verdict
    # names the whole-feeder case. Counting all feeders together would let one
    # large cluster's incidental collection read as a merge of three.
    whole_heavy = [(cid, v) for cid, v in heavy
                   if sum(1 for _c, crossed, total in v if crossed == total)
                   >= MERGE_CLAIM]
    out.append("")
    if whole_heavy:
        out.append(f"  verdict: {len(whole_heavy)} later page cluster(s) took in "
                   f"{MERGE_CLAIM} or more earlier page clusters whole:")
        for cid, feeders in sorted(whole_heavy, key=lambda t: (-len(t[1]), t[0])):
            whole = [f for f, crossed, total in feeders if crossed == total]
            out.append(f"    {by_id[cid]['cluster_key']} ({cid}) took in "
                       f"{len(whole)} whole: {', '.join(whole)}")
            if rows:
                for f, crossed, total in feeders:
                    out.append(f"      {f}: {crossed}/{total} page address(es) across")
    else:
        out.append(f"  verdict: no later page cluster took in {MERGE_CLAIM} or more "
                   f"earlier page clusters whole, so the note's 'merged {MERGE_CLAIM} "
                   "of the page's clusters into one' has no referent in this pair")
    if heavy and len(whole_heavy) < len(heavy):
        partial = sorted(cid for cid, _v in heavy
                         if (cid, _v) not in whole_heavy)
        out.append(f"  {len(partial)} further cluster(s) draw page addresses from "
                   f"{MERGE_CLAIM} or more earlier ones without taking any of them in "
                   "whole, which is a large cluster collecting addresses rather than "
                   "a merge of the page's clusters: "
                   + ", ".join(by_id[c]["cluster_key"] for c in partial))

    # The count direction is threshold-free and independent of both columns
    # above, so it is printed beside them rather than as a third finding. It is
    # a *net*: merges and splits happen in the same pass and a merge into one
    # is only ever one term in it, so the sign says the page's clusters grew
    # overall and says nothing on its own about whether any two of them became
    # one. That is why it cannot decide the verdict above and the verdict
    # cannot be read off it.
    out.append(f"  count check: the page holds {len(old_page)} cluster(s) before and "
               f"{len(new_page)} after, {len(new_page) - len(old_page):+d} net. A "
               f"{MERGE_CLAIM}-into-one merge is one term in that net, not the whole "
               "of it -- splits move it the other way -- so neither the sign nor its "
               "size decides the verdict above")
    return out


def self_test() -> int:
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {text}")

    print("xdata_page_clusters.py --self-test")
    tmp = tempfile.mkdtemp(prefix="xdata-page-clusters-")

    def key(n):
        return f"k{n:012d}"

    def write_clusters(name, rows):
        """(cluster_id, program, addrs, key) -> a clusters CSV path."""
        path = os.path.join(tmp, name)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cluster_id", "program", "addrs", "cluster_key",
                        "cluster_name"])
            for cid, program, addrs, k, cname in rows:
                w.writerow([cid, program, " ".join(_fmt_addr(a) for a in sorted(addrs)),
                            k, cname])
        return path

    def write_registers(name, addrs):
        path = os.path.join(tmp, name)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["addr", "refs", "write"])
            for a in addrs:
                w.writerow([_fmt_addr(a), "1", "0"])
        return path

    def _run_argv(argv):
        """(rc, stdout, stderr) for an arbitrary argv, so a case that is about
        what `main()` *says* can read stderr rather than only stdout."""
        import contextlib
        import io
        out, err = io.StringIO(), io.StringIO()
        saved = sys.argv
        sys.argv = argv
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main()
        except SystemExit as exit:
            rc = exit.code
        finally:
            sys.argv = saved
        return rc, out.getvalue(), err.getvalue()

    def run(old_c, new_c, old_r=None, new_r=None, page=(0x0300, 0x05FF)):
        """(rc, stdout) for one invocation. `page=None` passes no `--page` at
        all, so the default is reachable from here -- it is the page the note
        names, and a default nothing can reach is a default nothing checks."""
        import contextlib
        import io
        argv = ["xdata_page_clusters.py", "--old-clusters", old_c,
                "--new-clusters", new_c]
        if page is not None:
            argv += ["--page", hex(page[0]), hex(page[1])]
        if old_r and new_r:
            argv += ["--old-registers", old_r, "--new-registers", new_r]
        out = io.StringIO()
        saved = sys.argv
        sys.argv = argv
        try:
            with contextlib.redirect_stdout(out):
                rc = main()
        except SystemExit as exit:
            rc = exit.code
        finally:
            sys.argv = saved
        return rc, out.getvalue()

    # -- The threshold's blind spot on equal-sized merges, which is the reason
    # -- both directions are reported --------------------------------------
    # Three equal disjoint page clusters, merged into their union, plus one
    # later cluster that genuinely took a fourth in whole. The three score 1/3
    # against the union, so only the fourth is visible to absorption. This is
    # the equal-sized shape and nothing more: an unequal merge's dominant
    # feeder can clear the threshold, and is lost instead to the rest of the
    # later cluster's membership.
    old_c = write_clusters("old.csv", [
        ("main-ec-001", "main-ec", {0x0300, 0x0301}, key(1), ""),
        ("main-ec-002", "main-ec", {0x0310, 0x0311}, key(2), ""),
        ("main-ec-003", "main-ec", {0x0320, 0x0321}, key(3), ""),
        ("main-ec-004", "main-ec", {0x0330, 0x0331, 0x0332, 0x0333}, key(4), ""),
    ])
    new_c = write_clusters("new.csv", [
        ("main-ec-001", "main-ec", {0x0300, 0x0301, 0x0310, 0x0311,
                                    0x0320, 0x0321, 0x0340}, key(5), ""),
        ("main-ec-002", "main-ec", {0x0330, 0x0331, 0x0332, 0x0333}, key(4), ""),
    ])
    old_r = write_registers("old-r.csv", {0x0300, 0x0301, 0x0310, 0x0311,
                                          0x0320, 0x0321, 0x0330, 0x0331,
                                          0x0332, 0x0333})
    new_r = write_registers("new-r.csv", {0x0300, 0x0301, 0x0310, 0x0311,
                                          0x0320, 0x0321, 0x0330, 0x0331,
                                          0x0332, 0x0333, 0x0340})
    rc, out = run(old_c, new_c, old_r, new_r)
    absorbed, feeding = correspondences(clusters_of(old_c), clusters_of(new_c),
                                       (0x0300, 0x05FF))
    check(rc == 0 and len(absorbed["main-ec-001"]) == 0
          and len(feeding["main-ec-001"]) == 3,
          "three equal page clusters merged into their union are three feeders and "
          "no absorption: the 0.50 carry rule scores each of them 1/3 and cannot "
          "see the merge, which is why the report prints both directions")
    check("merged 3 of the page's clusters into one" not in out
          and "took in 3 or more earlier page clusters whole" in out
          and "k000000000005" in out,
          "the verdict line is answered by the threshold-free whole-feeder count, "
          "so a merge the carry rule cannot see is still reported as one")
    check("1/n" in out and "unequal" in out and "dilutes" in out,
          "the absorption column states on its own line that the 1/n bound is "
          "for equal-sized merges, that an unequal merge's dominant feeder can "
          "clear the threshold, and that this column scores against the whole "
          "later cluster, so its zero is not read as evidence of no merge")

    # -- The union rule -----------------------------------------------------
    # One address in a main-ec row and a pd row: a sum over rows would report
    # it twice, and the page's cluster count is unaffected by either reading.
    dup_c = write_clusters("dup.csv", [
        ("main-ec-001", "main-ec", {0x0400, 0x0401, 0x0402}, key(1), ""),
        ("pd-001", "pd", {0x0402, 0x0403}, key(2), ""),
    ])
    rows_dup = clusters_of(dup_c)
    union = page_addresses(rows_dup, (0x0300, 0x05FF))
    total = sum(len(page_of(r, (0x0300, 0x05FF))) for r in rows_dup)
    check(len(union) == 4 and total == 5 and 0x0402 in union,
          "an address both programs touch is one page address: the union is the "
          "set, and summing per-row membership would count it twice")
    _rc, out_dup = run(dup_c, dup_c)
    check("union over the rows holding them, not a sum over rows" in out_dup
          and "5 distinct page addresses" not in out_dup
          and "4 distinct page addresses" in out_dup,
          "the report prints the union rule beside the number, and prints the "
          "union rather than the sum")

    # -- A page nothing touches, and an empty added set ---------------------
    empty_c = write_clusters("empty.csv", [
        ("main-ec-001", "main-ec", {0x0700}, key(1), ""),
    ])
    empty_r = write_registers("empty-r.csv", {0x0700})
    _rc, out_empty = run(empty_c, empty_c, empty_r, empty_r,
                         page=(0x0300, 0x05FF))
    check("nothing on 0x0300-0x05FF" in out_empty,
          "a page neither census touches is named on its own line, so its zeros "
          "read as an empty page rather than as a measurement")
    same_r = write_registers("same-r.csv", {0x0700, 0x0701, 0x0702})
    _rc, out_noadd = run(empty_c, empty_c, empty_r, same_r)
    # Matched rather than compared as a literal: the two figures are read out of
    # the report's own lines by their labels, so a column realignment is not a
    # red here and a changed count still is.
    added_lines = {m.group(1): int(m.group(2)) for m in
                   (re.search(r"(on|off) the page\s+(\d+)", ln)
                    for ln in out_noadd.splitlines()) if m}
    check(added_lines == {"on": 0, "off": 2}
          and "no added address is on this page" in out_noadd,
          "an added set that is entirely off the page is reported as off the page "
          "with nothing to attribute, rather than as a confident zero on-page")

    # -- Per-program correspondence ----------------------------------------
    # Same membership, two programs, one shared address. A correspondence that
    # ignored the program would match each row to the other program's.
    per_c = write_clusters("per.csv", [
        ("main-ec-001", "main-ec", {0x0500, 0x0501, 0x0502}, key(1), ""),
        ("pd-001", "pd", {0x0500, 0x0501, 0x0502}, key(2), ""),
    ])
    per_new = write_clusters("per-new.csv", [
        ("main-ec-001", "main-ec", {0x0500, 0x0501, 0x0502, 0x0503}, key(3), ""),
        ("pd-001", "pd", {0x0500, 0x0501, 0x0502}, key(2), ""),
    ])
    absorbed_per, _feeding_per = correspondences(clusters_of(per_c),
                                                 clusters_of(per_new),
                                                 (0x0300, 0x05FF))
    check(absorbed_per["main-ec-001"] == [("main-ec-001", 0.75)]
          and absorbed_per["pd-001"] == [("pd-001", 1.0)],
          "a correspondence is matched within a program: a main-ec row and a pd "
          "row of identical membership do not match each other, because a shared "
          "address number is not a shared byte")

    # -- A large cluster collecting addresses is not a merge ---------------
    # Five earlier page clusters each keep most of their own membership and
    # contribute one address to one large later cluster, so the feeder count
    # clears MERGE_CLAIM while no feeder is whole. A count without the
    # whole-feeder distinction reads this as a five-into-one merge; it is a
    # large cluster collecting addresses that five clusters kept.
    big_c = write_clusters("big-old.csv", [
        ("main-ec-001", "main-ec", {0x0300, 0x0301, 0x0302}, key(1), ""),
        ("main-ec-002", "main-ec", {0x0310, 0x0311, 0x0312}, key(2), ""),
        ("main-ec-003", "main-ec", {0x0320, 0x0321, 0x0322}, key(3), ""),
        ("main-ec-004", "main-ec", {0x0330, 0x0331, 0x0332}, key(4), ""),
        ("main-ec-005", "main-ec", {0x0340, 0x0341, 0x0342}, key(5), ""),
    ])
    big_new = write_clusters("big-new.csv", [
        ("main-ec-001", "main-ec", {0x0302, 0x0312, 0x0322, 0x0332, 0x0342,
                                    0x0350, 0x0351, 0x0352, 0x0353, 0x0354},
         key(6), ""),
        ("main-ec-002", "main-ec", {0x0300, 0x0301}, key(7), ""),
        ("main-ec-003", "main-ec", {0x0310, 0x0311}, key(8), ""),
        ("main-ec-004", "main-ec", {0x0320, 0x0321}, key(9), ""),
        ("main-ec-005", "main-ec", {0x0330, 0x0331}, key(10), ""),
        ("main-ec-006", "main-ec", {0x0340, 0x0341}, key(11), ""),
    ])
    _rc, out_big = run(big_c, big_new)
    _absorbed_big, feeding_big = correspondences(clusters_of(big_c),
                                                clusters_of(big_new),
                                                (0x0300, 0x05FF))
    check(len(feeding_big["main-ec-001"]) == 5
          and all(c < t for _f, c, t in feeding_big["main-ec-001"]),
          "a later cluster fed by more than MERGE_CLAIM earlier ones is counted "
          "as fed, with how much of each feeder crossed, so the count is a fact "
          "about membership rather than a verdict")
    check("no later page cluster took in 3 or more earlier page clusters whole"
          in out_big
          and "collecting addresses rather than a merge" in out_big,
          "five earlier clusters each contributing one of three addresses to a "
          "large later cluster is reported as that large cluster collecting "
          "addresses, not as a merge of the page's clusters: only a whole feeder "
          "counts toward the merge verdict")

    # -- The page bounds are the page --------------------------------------
    # A cluster whose membership straddles both ends of the page and reaches
    # past each of them. The page is inclusive at both ends, so the straddling
    # row is a page cluster holding exactly the three in-range addresses; run
    # over a wider range it holds more, which is what makes the bounds a
    # property of the run rather than of the fixture.
    edge_c = write_clusters("edge.csv", [
        ("main-ec-001", "main-ec", {0x02FF, 0x0300, 0x0301, 0x05FF, 0x0600}, key(1), ""),
    ])
    _absorbed_edge, feeding_edge = correspondences(
        clusters_of(edge_c), clusters_of(edge_c), (0x0300, 0x05FF))
    rc_edge, out_edge = run(edge_c, edge_c, page=(0x0300, 0x05FF))
    rc_wide, out_wide = run(edge_c, edge_c, page=(0x0200, 0x06FF))
    check(rc_edge == 0 and rc_wide == 0
          and "3 distinct page addresses" in out_edge
          and "5 distinct page addresses" in out_wide,
          "the page is an inclusive address range and the report counts what is "
          "inside it: 0x02FF and 0x0600 are outside 0x0300-0x05FF and inside "
          "0x0200-0x06FF, so the same cluster counts differently per run")

    # The default *is* the page the note names, so a run that passes no --page
    # has to land on the same answer as one that passes it -- and has to land on
    # a page at all, which the straddling fixture makes checkable: 0x02FF and
    # 0x0600 are outside it.
    _rc, out_default = run(edge_c, edge_c, page=None)
    check("page 0x0300-0x05FF" in out_default
          and "3 distinct page addresses" in out_default,
          "with no --page the range is 0x0300-0x05FF, the working page "
          "annotations/xdata-cluster-names.csv records, rather than the whole "
          "address space")

    # -- The counting rule the note's own arithmetic depends on -------------
    # A sum over per-row membership on a page where two rows share an address
    # is wrong by exactly the shared count, so the two rules are compared
    # where they are built rather than in the report's text.
    check(len(page_addresses(rows_dup, (0x0300, 0x05FF)))
          == len(set().union(*[page_of(r, (0x0300, 0x05FF)) for r in rows_dup])),
          "the union is a set union of the per-row page memberships, so the rule "
          "the count rests on is the one the code implements")

    # -- The threshold is the tree's, not a second copy that drifted ---------
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "xdata_register_map.py"), encoding="utf-8") as f:
            source = f.read()
        found = re.search(r"^CARRY_MIN_JACCARD\s*=\s*([0-9.]+)", source, re.M)
        sibling = float(found.group(1)) if found else None
    except OSError:
        sibling = None
    check(sibling is not None and sibling == CARRY_MIN_JACCARD,
          f"the carry threshold restated here is the one "
          f"xdata_register_map.py uses ({CARRY_MIN_JACCARD:.2f}), so an absorption "
          "figure here is the same rule as a --map figure and not a second rule "
          "that has drifted")

    # -- A census where one id is two rows is reported, not absorbed --------
    # `absorbed`, `feeding` and the holders map are keyed by cluster_id, so two
    # rows under one id would collapse into one entry and a page cluster would
    # vanish from the report with every printed count still looking reasonable.
    dupe_c = write_clusters("dupe.csv", [
        ("main-ec-001", "main-ec", {0x0400, 0x0401}, key(1), ""),
        ("main-ec-001", "main-ec", {0x0402, 0x0403}, key(2), ""),
    ])
    dupe = duplicate_ids(clusters_of(dupe_c))
    _rc, out_dupe = run(dupe_c, dupe_c)
    check(list(dupe) == ["main-ec-001"]
          and "held by more than one row" in out_dupe
          and "undercount the page" in out_dupe,
          "a cluster_id held by two rows is named, because the report's tables "
          "are keyed by it and would otherwise count one page cluster where the "
          "census has two")
    _rc, out_clean = run(old_c, new_c)
    check("every cluster_id is one row" in out_clean,
          "the same line is printed when there is no collision, so a clean run "
          "reports having looked rather than staying silent about it")

    # -- A missing input is named, not raised -------------------------------
    # The far side is a worktree under /tmp, so a path that has gone away is the
    # ordinary failure here and the message has to say which one and how to get
    # it back. Checked through `main()` because that is the only way to reach
    # argparse's exit.
    rc_missing, _out_missing, err_missing = _run_argv(
        ["xdata_page_clusters.py", "--old-clusters", os.path.join(tmp, "absent.csv"),
         "--new-clusters", old_c])
    said_missing = err_missing.rpartition("error:")[2]
    check(rc_missing == 2 and "absent.csv does not exist" in said_missing
          and "git worktree add" in said_missing,
          "a census path that is not there is named with how to reach the far "
          "side, rather than surfacing as a traceback from open()")

    print(f"  {'FAILED' if bad else 'all checks passed'}"
          + (f" ({bad})" if bad else ""))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old-clusters", help="earlier census's clusters CSV")
    ap.add_argument("--new-clusters", help="later census's clusters CSV")
    ap.add_argument("--old-registers", help="earlier census's registers CSV; "
                                            "with --new-registers it is what the "
                                            "added set is derived from")
    ap.add_argument("--new-registers", help="later census's registers CSV")
    ap.add_argument("--label", help="what to call the earlier census "
                                    "(default: its path)")
    ap.add_argument("--label-new", help="what to call the later census "
                                        "(default: its path)")
    ap.add_argument("--page", nargs=2, type=lambda s: int(s, 16),
                    metavar=("LO", "HI"), default=(0x0300, 0x05FF),
                    help="the address range counted as the page (default "
                         "0x0300 0x05FF, the working page "
                         "annotations/xdata-cluster-names.csv records)")
    ap.add_argument("--rows", action="store_true",
                    help="print every cluster in both correspondence tables "
                         "rather than the first twelve")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    # Checked before the flags are demanded, so `--self-test` needs no census
    # paths beside it; the other way round, a self-test run handed a stale path
    # would fail on a file it never opens.
    if args.self_test:
        return self_test()
    missing = [f"--{n}" for n, v in (("old-clusters", args.old_clusters),
                                     ("new-clusters", args.new_clusters))
               if not v]
    if missing:
        ap.error("this tool needs " + " and ".join(missing)
                 + ", the two censuses' clusters CSVs, or --self-test")
    # The two registers flags are a pair for the same reason `--old-registers`
    # is useless alone: the added set is a set difference, and a difference
    # against one side is a membership, not an addition.
    if bool(args.old_registers) != bool(args.new_registers):
        ap.error("--old-registers and --new-registers go together: the added set "
                 "is set(new) - set(old) and neither half is an addition")
    # Named rather than raised as a traceback: a missing path here is almost
    # always a worktree that was not checked out, and saying so is the whole of
    # what the reader needs to fix it.
    for path in (args.old_clusters, args.new_clusters, args.old_registers,
                 args.new_registers):
        if path and not os.path.isfile(path):
            ap.error(f"{path} does not exist. The far side is reached with "
                     "`git worktree add --detach <dir> e169a0e4`, as "
                     "xdata-flip-cause-derivation.md 1 does; a path under /tmp "
                     "needs that worktree to still be there")
    print("\n".join(page_cluster_report(
        args.label or args.old_clusters, args.old_clusters,
        args.label_new or args.new_clusters, args.new_clusters,
        tuple(args.page),
        old_registers=registers_of(args.old_registers) if args.old_registers else None,
        new_registers=registers_of(args.new_registers) if args.new_registers else None,
        rows=args.rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
