#!/usr/bin/env python3
"""`name_clusters()` run the way `generate()` and `--self-test` run it (issue #959).

`xdata_register_map.py`'s `name_clusters()` is what fills `cluster_name` into
the generated rows, and no suite ran it: both of its callers inside the tool
pass `load_cluster_names()` as the seed, and the three nearest suites each cover
a different half. `TheCarry` exercises
`carry_names()` on hand-built fixtures, so the `seeded` *precedence* is held but
only against a key the fixture chose. `TheNamesFile` reads the names file and
the census as two files and never runs the function that joins them.
`TheGeneratorsAreUnchanged` regenerates cell for cell and excludes `cluster_name`
by name, correctly, because it is an identity column rather than a membership --
and that exclusion is why nothing caught a fill that puts the right name on the
wrong row. `TheGuardOffRegeneration` calls `carry_names()` directly with `{}`,
deliberately and correctly, to exercise the route its own assertion is about.

`name_clusters()` is not the only caller of `carry_names()` outside a suite:
`self_test()` also drives it directly, over a synthetic split it builds, and
`xdata_guard_off_row_join.py`'s `names_report()` calls it and keeps only the
report. This suite covers `name_clusters()` because it is the one whose result
is filled into `cluster_name` and written into `xdata-clusters.csv`, which is
what the gap below was about.

So this suite runs the seeded route, over the committed census and a guard-off
regeneration, and holds what that run decides rather than what a fixture gives.
The properties are the design's rather than this tree's: the seeded route and
the withheld route fill **the same names on the same rows** and disagree only
in the label (`seeded` against `exact`), and every key the names file anchors
lands on the row the names file names.

Everything here reads committed text. The census is the committed pair plus a
`--no-eq-guard` regeneration into a scratch directory, which is that flag's own
refusal contract: `--no-eq-guard` is refused with `--check` and `--self-test`,
and refused again against the committed output paths, so every run here writes
to a temp dir and the committed CSVs are inputs. No image, no Ghidra, no
hardware, no Windows, no network.
"""
import csv
import functools
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
EC = HERE.parent
TOOL = HERE / "xdata_register_map.py"
CLUSTERS = EC / "annotations" / "xdata-clusters.csv"
NAMES = EC / "annotations" / "xdata-cluster-names.csv"

spec = importlib.util.spec_from_file_location("xdata_register_map", TOOL)
xrm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xrm)

# `xdata_name_coverage.coverage`'s own list, rather than a second spelling of
# it here. Which outcomes put a name on a row of the written census is that
# module's one decision and the two halves of the report have to agree about
# it, so a suite carrying its own tuple would hold the copy rather than the
# rule, and a rule that changed would leave this file asserting the old one.
CARRIED = xrm.xdata_name_coverage.CARRIED


def clusters_of(path):
    """[rows] of a clusters CSV, read straight off disk."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def names_of(path):
    """`{cluster_name: cluster_key}` for the names file, read off disk.

    Not `load_cluster_names()`, which is the same file read a second way. The
    run under test *uses* `load_cluster_names()`; the expectation beside it
    reads the CSV, so a case cannot pass because both sides of a comparison went
    wrong together -- the reasoning `spellings_by_program()`'s docstring gives
    for the same reason at census length.
    """
    with open(path, newline="") as f:
        return {r["cluster_name"]: r["cluster_key"].strip()
                for r in csv.DictReader(f) if r["cluster_key"].strip()}


def fill_of(rows):
    """`{cluster_id: cluster_name}` as `name_clusters()` filled the rows.

    The column the function writes, keyed by the id the rest of the census is
    keyed by. `name_clusters()` writes into the rows it is handed, so every call
    here is given its own copies; that is what keeps a forged seed from reaching
    the rows the next case reads.
    """
    return {r["cluster_id"]: r["cluster_name"] for r in rows}


def run(seeded, committed, off):
    """`(report, coverage, fill)` for one seed map over the same two censuses.

    Every caller of `name_clusters()` outside a suite and this differ in one
    thing: the seed. Both of the tool's pass `load_cluster_names()`, and no
    caller outside a suite passes anything else, so a case that passes `{}` is
    holding a route only a suite takes, and one that passes the names file is
    holding the route every non-suite caller takes.
    """
    rows = [dict(r) for r in off]
    report, cov = xrm.name_clusters(rows, committed, seeded)
    return report, cov, fill_of(rows)


def seeded_records(report, filled, seeded, committed_by_key):
    """{cluster_id: why} for the `seeded` records that do not hold their claim.

    A record is a claim about a **row**: the names file names this key, this
    name goes on that row, and the committed census agrees that this key is the
    row carrying this name. The four clauses are the four ways that breaks, and
    the last is the one nothing else in the tree reaches -- a names-file key
    belonging to some *other* row satisfies "the key is in the census" and fails
    here.

    `from_key == ""` is the `seeded` branch's own shape rather than an assertion
    about a key: `carry_names()` assigns `name` and `how` there and leaves
    `from_key` at its `""` initial, where the `exact` branch assigns it to the
    key. That difference is what tells a seeded record from an exact one at the
    record level, so it is held rather than assumed.
    """
    bad = {}
    for r in report:
        if r["how"] != "seeded":
            continue
        held = committed_by_key.get(r["cluster_key"], {}).get("cluster_name", "")
        if r["from_key"] != "":
            why = (f"from_key is {r['from_key']!r}, not the empty string the "
                   "seeded branch leaves it at")
        elif r["cluster_key"] not in seeded:
            why = f"{r['cluster_key']} is not a key the names file anchors"
        elif seeded[r["cluster_key"]] != r["name"]:
            why = f"the names file says {seeded[r['cluster_key']]!r} for this key"
        elif filled.get(r["cluster_id"]) != r["name"]:
            why = f"the row was filled {filled.get(r['cluster_id'])!r}"
        elif held != r["name"]:
            why = (f"the committed census carries {held!r} on "
                   f"{r['cluster_key']}, so this name is anchored to a row that "
                   "is not the one carrying it")
        else:
            continue
        bad[r["cluster_id"]] = why
    return bad


def overlap_records(report, filled, seeded, off_keys):
    """{key: why} for a names-file key the census can no longer reach.

    **Derived, and that is the whole case.** The population is "the names file
    anchors a key the regeneration no longer has", so nothing here names an id,
    a key or a score: a typed pair goes stale silently, and one did -- the
    `mode-oem-init` key now reads `kefb63d82f8c7`, the third it has carried and
    the second re-key, each move recorded on the row itself for a re-derivation
    that moved the membership, so a case comparing an older pair would have gone
    on passing. The property is that such a name still arrives, by membership
    rather than by key, on a row that carries it. A content hash alone hands each
    of these a brand-new identity and loses the name; only the overlap carry
    brings it along.
    """
    bad = {}
    for key in seeded:
        if key in off_keys:
            continue
        reached = [r for r in report
                   if r["how"] == "overlap" and r["from_key"] == key]
        if not reached:
            bad[key] = ("no cluster of the regeneration reached this name on "
                        "membership, so a content hash alone loses it")
            continue
        for r in reached:
            if filled.get(r["cluster_id"]) != seeded[key]:
                bad[key] = (f"{r['cluster_id']} was filled "
                            f"{filled.get(r['cluster_id'])!r} rather than the "
                            "name the carry report carried into it")
    return bad


def coverage_records(cov, report, names):
    """{name: why} for a names-file row without a matching coverage record.

    The transpose has to hold from both ends: one record per row of the names
    file, whatever the run did with it, and every carried record agreeing with
    the cluster-indexed half about the name, the outcome and the row. The first
    clause is the reason `xdata_name_coverage.py` exists -- a name the run did
    not carry used to be in no record and in no cell of the tally, so a reader
    holding only the printed line could not tell "every name is accounted for"
    from "two names fell under the floor".

    `jaccard is None` is held to `key-not-found` and to nothing else, which is
    that module's own distinction: a name with no membership to score against
    has not scored zero, and a `0.00` in a report is a reading of it.
    """
    bad = {}
    for name in names:
        if not any(r["name"] == name for r in cov):
            bad[name] = ("no coverage record, so this row of the names file "
                         "produces no outcome at all")
    for r in cov:
        if r["name"] not in names:
            bad.setdefault(r["name"], "a coverage record for a name the names "
                                       "file does not carry")
            continue
        if (r["jaccard"] is None) != (r["how"] == "key-not-found"):
            bad[r["name"]] = (f"how={r['how']} with jaccard {r['jaccard']}; a "
                              "score of None belongs to `key-not-found` and to "
                              "nothing else")
        if r["how"] not in CARRIED:
            continue
        landed = [x for x in report
                  if x["name"] == r["name"] and x["how"] in CARRIED]
        if len(landed) != 1:
            bad[r["name"]] = (f"coverage carries it to {r['carried_to']} but the "
                              f"report holds {len(landed)} carried record(s) "
                              "naming it")
        elif (landed[0]["how"] != r["how"]
              or landed[0]["cluster_id"] != r["carried_to"]
              or landed[0]["jaccard"] != r["jaccard"]):
            bad[r["name"]] = (f"coverage says {r['how']} onto "
                              f"{r['carried_to']} at {r['jaccard']}, the report "
                              f"says {landed[0]['how']} onto "
                              f"{landed[0]['cluster_id']} at "
                              f"{landed[0]['jaccard']}")
    return bad


def _describe(bad, what):
    """The offender mapping as a failure message; "" when there is nothing."""
    if not bad:
        return ""
    named = "; ".join(f"{k}: {v}" for k, v in sorted(bad.items())[:4])
    if len(bad) > 4:
        named += f"; and {len(bad) - 4} more"
    return f"{what}: {named}"


@functools.lru_cache(maxsize=1)
def guard_off():
    """(clusters.csv path, registers.csv path) for the guard-off census.

    Built the way `annotations/xdata-06c2-06db-timers.md` §6a builds it and the
    way `test_xdata_cluster_names.py`'s own `guard_off()` does: the committed
    tool run with `--no-eq-guard`, which is the switch that re-runs the census
    with the `==` rejection turned off. That flag is refused together with
    `--check` and `--self-test`, and refused again against the committed output
    paths, so both CSVs go to a scratch directory and the run reads the
    committed decompile and writes nothing into it.

    **Copied rather than imported.** `test_xdata_cluster_names.py` builds the
    same census, and importing it would put one `lru_cache` behind a module
    object neither suite owns -- so deleting or renaming that file would take
    this one's census with it. The same rule keeps two suites from moving a
    shared temp dir out from under each other. It costs a second run of a
    regeneration that reads committed text.
    """
    tmp = tempfile.mkdtemp(prefix="xdata-seeded-route-")
    out_clusters = os.path.join(tmp, "clusters.csv")
    out_registers = os.path.join(tmp, "registers.csv")
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--no-eq-guard", "--out-clusters",
         out_clusters, "--out-registers", out_registers],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"the guard-off run failed: {proc.stderr}")
    return out_clusters, out_registers


class TheSeededRoute(unittest.TestCase):
    """The route production takes, over the committed census and a regeneration.

    **The two routes, and why both are here.** `carry_names()` reaches the same
    names two ways: a key the names file anchors is `seeded`, and the same key
    found in the committed census is `exact`. `generate()` and `--self-test()`
    both pass the names file, so `seeded` is what a real run reports and `exact`
    is what the withheld route reports. They are the same claim arrived at
    differently, which is what `carry_names()`'s own docstring says of the two,
    so the disagreement between them is the design working rather than two
    implementations drifting. `TheGuardOffRegeneration` keeps the withheld route
    because that is the route its assertion is about; this suite sits beside it
    rather than replacing it, which is the choice
    `docs/findings/xdata-two-largest-case-restatement.md` records.
    """

    @classmethod
    def setUpClass(cls):
        clusters, _registers = guard_off()
        cls.committed = clusters_of(CLUSTERS)
        cls.off = clusters_of(clusters)
        cls.off_on_disk = fill_of(cls.off)
        cls.names = names_of(NAMES)
        cls.seeded = xrm.load_cluster_names()
        cls.committed_by_key = {r["cluster_key"]: r for r in cls.committed}
        cls.off_keys = {r["cluster_key"] for r in cls.off}

    def both_routes(self):
        """`(withheld, seeded)`, each a `(report, coverage, fill)` triple."""
        committed = list(self.committed)
        return run({}, committed, self.off), run(self.seeded, committed, self.off)

    def test_the_seeded_route_writes_the_names_the_withheld_route_does(self):
        # The round trip. `name_clusters()` fills `cluster_name` into the rows it
        # is handed, and that column is what reaches `xdata-clusters.csv`, so a
        # seed that changed *which* name lands on a row would rename clusters in
        # the census and nothing else in the tree would notice: the
        # reproducibility case compares every other cell and excludes this one
        # on purpose, because it is an identity column rather than a membership.
        (_wr, _wc, withheld), (_sr, _sc, seeded) = self.both_routes()
        differing = sorted(cid for cid in set(seeded) | set(withheld)
                           if seeded.get(cid) != withheld.get(cid))
        self.assertEqual(
            differing, [],
            "the two routes filled `cluster_name` differently, so seeding the "
            "census with its own names file moved a name between rows; the two "
            "are the same claim arrived at differently and they land on the "
            "same rows. First: " + "; ".join(
                f"{cid} seeded {seeded.get(cid)!r} against withheld "
                f"{withheld.get(cid)!r}" for cid in differing[:4]))

        # And the seeded fill is the column that run wrote to its own CSV.
        # `generate()` reached that file through the writer, so this compares
        # the in-process fill against the artifact the same run left behind: a
        # name mangled on the way out, or computed twice with the two copies
        # disagreeing, shows here rather than in a byte diff nobody diffs --
        # the reasoning `test_the_console_block_agrees_with_the_csv_it_wrote`
        # gives at census length.
        #
        # Over the rows that carry a name rather than over the whole fill. The
        # fill is one entry per cluster of the regeneration, so an
        # `assertEqual` on the two mappings prints every empty cell between the
        # disagreements -- several thousand characters of `''` and one line of
        # reason at the end of it.
        named = {cid: n for cid, n in seeded.items() if n}
        written = {cid: n for cid, n in self.off_on_disk.items() if n}
        self.assertEqual(
            named, written,
            "the in-process fill is not the `cluster_name` column the guard-off "
            "run wrote to its own CSV; named rows in the fill but not in the "
            "column: "
            f"{sorted(set(named) - set(written))}; in the column but not the "
            f"fill: {sorted(set(written) - set(named))}; naming a different "
            "cluster: "
            + ", ".join(f"{cid} {named[cid]!r} against {written[cid]!r}"
                        for cid in sorted(set(named) & set(written))
                        if named[cid] != written[cid])[:2000])

    def test_the_two_routes_differ_only_where_the_names_file_anchors(self):
        # The disagreement, held as the relation it is. The rows whose `how`
        # moves between the routes are exactly the rows whose key the names file
        # anchors, each `exact` without the seed and `seeded` with it -- which is
        # the whole content of the `seeded` outcome: a human saying so outranks
        # the tool's guess about which row it is guessing at.
        #
        # A set relation rather than a tally, for the reason CLAUDE.md gives: a
        # count of rows is a value every seeding branch moves, and it would go
        # red on a re-derivation that changed nothing here. A tenth name in the
        # names file, or a tenth re-key, moves the set and leaves the equality
        # standing.
        (withheld, _wc, _wf), (seeded, _sc, _sf) = self.both_routes()
        how_without = {r["cluster_id"]: r["how"] for r in withheld}
        how_with = {r["cluster_id"]: r["how"] for r in seeded}
        moved = {cid for cid in how_with if how_with[cid] != how_without[cid]}
        anchored = {r["cluster_id"] for r in self.off
                    if r["cluster_key"] in self.seeded}
        self.assertTrue(
            anchored,
            "no key the names file anchors is a cluster of the regeneration, so "
            "there is no disagreement to hold and the equality below is vacuous")
        self.assertEqual(
            moved, anchored,
            "the rows whose outcome moves between the routes are not the rows "
            "the names file anchors; a key that is neither seeded nor exact is "
            "the carry's own arithmetic and must read the same either way")
        self.assertEqual(sorted({how_without[c] for c in anchored}), ["exact"])
        self.assertEqual(sorted({how_with[c] for c in anchored}), ["seeded"])

    def test_every_seeded_record_names_the_row_its_key_names(self):
        # What the fill is for: a hand name is a claim about a cluster, and this
        # is that the cluster the names file names is the cluster the name
        # reached. The last clause of `seeded_records()` is the one the tree had
        # no way to state -- a key that is in the census but belongs to another
        # row satisfies every check that only asks whether the key resolves.
        (_wr, _wc, _wf), (seeded, _sc, fill) = self.both_routes()
        self.assertTrue(
            [r for r in seeded if r["how"] == "seeded"],
            "no cluster of the regeneration took a name from the names file, so "
            "nothing here shows the seed reaching a row at all")
        bad = seeded_records(seeded, fill, self.seeded, self.committed_by_key)
        self.assertEqual(
            bad, {},
            _describe(bad, "seeded record(s) whose claim does not hold"))

    def test_a_name_the_key_no_longer_finds_reaches_its_row_by_overlap(self):
        # The half a content hash cannot do, over every name the key fails to
        # find rather than over one of them named in advance. Both routes report
        # it `overlap`: it is the same membership under both, and the seed does
        # not reach it because the names file anchors a key the regeneration
        # moved.
        (wr, _wc, withheld_fill), (sr, _sc, seeded_fill) = self.both_routes()
        self.assertTrue(
            self.off_keys.difference(self.seeded),
            "every key the names file anchors is still a cluster of the "
            "regeneration, so no name is being carried across a re-key here and "
            "the overlap rule is untested by this tree")
        for report, fill, route in ((wr, withheld_fill, "withheld"),
                                    (sr, seeded_fill, "seeded")):
            with self.subTest(route=route):
                bad = overlap_records(report, fill, self.seeded, self.off_keys)
                self.assertEqual(bad, {}, _describe(bad, f"{route} route"))

    def test_every_names_file_row_gets_a_coverage_record(self):
        # The transpose, held through `name_clusters()` rather than through
        # `xdata_name_coverage.coverage()` alone, because the claim is about the
        # two halves agreeing and a caller that built one without the other
        # would be holding a property nothing produces.
        (_wr, _wc, _wf), (seeded, cov, _sf) = self.both_routes()
        bad = coverage_records(cov, seeded, self.names)
        self.assertEqual(
            bad, {},
            _describe(bad, "names-file row(s) without a coverage record that "
                           "agrees with the report"))

    def test_a_mis_keyed_name_is_refused_where_the_census_check_passes(self):
        # The negative control, and the justification for the whole suite: a
        # names-file row re-keyed onto a different cluster's key. `TheNamesFile`
        # reads the two files and asks whether each key is a cluster of the
        # census, and the forged key **is** one, so that case stays green -- a
        # check that passes on a name attached to the wrong row is worse than no
        # check, because it is read as the row being right.
        #
        # Both rows derived, for the reason every other exhibit here is: the key
        # to move is one the regeneration still has, so the forgery is a re-key
        # rather than a deletion, and the key to move it onto is a cluster of the
        # regeneration carrying no name, so the forged row cannot be caught by
        # "this name is already claimed there".
        movable = sorted(k for k in self.seeded if k in self.off_keys)
        spare = sorted(k for k in self.off_keys
                       if k not in self.seeded
                       and not self.committed_by_key.get(
                           k, {}).get("cluster_name", ""))
        self.assertTrue(
            movable and spare,
            "the committed names file no longer has a key the regeneration kept "
            "to move, or the regeneration has no unnamed cluster to move it "
            "onto, so this case is no longer about a re-key")
        forged = dict(self.seeded)
        name = forged.pop(movable[0])
        forged[spare[0]] = name
        self.assertEqual(len(forged), len(self.seeded),
                         "the forgery changed how many names the map holds "
                         "rather than which key holds which one")

        (_wr, _wc, withheld), _ = self.both_routes()
        report, cov, fill = run(forged, list(self.committed), self.off)

        # The census-key check the tree already has, run over the forged map. It
        # passes, which is the whole point: the forged key is a real cluster.
        self.assertEqual(
            {k: n for k, n in forged.items() if k not in self.committed_by_key},
            {},
            "the forged key is not a cluster of the committed census, so this "
            "case would be showing something `TheNamesFile` already catches "
            "rather than the gap it was written for")

        # And the three claims that do catch it. Named rather than counted: the
        # case is about the anchor clause, and a census with several names off
        # its key would be caught here too.
        #
        # Compared as `{id: name}` over the rows that carry one, because the
        # fills are one entry per cluster of the regeneration and an
        # `assertNotEqual` on the two mappings prints every empty cell between
        # them -- several thousand characters of `''` and one line of reason at
        # the end of it.
        named = lambda f: {cid: n for cid, n in f.items() if n}
        forged_named, withheld_named = named(fill), named(withheld)
        moved_rows = sorted(
            cid for cid in set(forged_named) | set(withheld_named)
            if forged_named.get(cid) != withheld_named.get(cid))
        self.assertTrue(
            moved_rows,
            "the forged seed did not move a name between rows, so nothing here "
            "shows a fill sensitive to which key the names file anchors")
        bad = seeded_records(report, fill, forged, self.committed_by_key)
        self.assertTrue(
            any("the committed census carries" in why for why in bad.values()),
            f"the forged name was refused, but not for the reason this case "
            f"exists: {bad}")
        # The transpose catches it too, and for a reason worth naming: the
        # forged map leaves the name on **two** rows -- the key it was moved off
        # still resolves `exact` in the committed census, and the key it was
        # moved onto is now `seeded` -- so `resolve_duplicate()`'s first rule
        # keeps both, because both claims are by key and neither is the tool's
        # guess. The coverage list names one `carried_to` where the report holds
        # two carried records, or reports the pair disagreeing; either is the
        # disagreement the transpose exists to surface, and which clause of
        # `coverage_records()` states it first is the helper's ordering rather
        # than a claim, so both are accepted here.
        #
        # Compared against `self.names`, the file's own rows, rather than
        # against `forged`: the coverage list is built from the seed, so asking
        # it to agree with the seed is the comparison that cannot fail.
        cbad = coverage_records(cov, report, self.names)
        self.assertTrue(
            cbad,
            "every forged row produced a coverage record agreeing with the "
            "report, so the transpose cannot tell a re-keyed name from a named "
            "one")

        # The forgery stayed in its copies. `setUpClass` hands the same
        # regeneration to every case in the class, so a run that wrote through
        # would leave a filled row behind for whatever ran next and the
        # assertions above would be a lie about which rows they had checked.
        self.assertEqual(fill_of(self.off), self.off_on_disk)


if __name__ == "__main__":
    unittest.main()