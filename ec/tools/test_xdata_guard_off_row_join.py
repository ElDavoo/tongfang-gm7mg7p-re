#!/usr/bin/env python3
"""What `--no-eq-guard` moves at census scale, held to the figures already published.

`xdata_register_map.py` refuses the flag with an argument that quotes no figure
at all, while the next refusal in the same `main()` argues from measured ones.
This suite is the measurement that closes that asymmetry, and the two halves
have different jobs and both are here.

**The load-bearing class is `ThePublishedFigures`.** Every figure it holds comes
from a page that already prints it -- `annotations/xdata-06c2-06db-timers.md`
§6a, `docs/findings/xdata-cluster-names-guard-off-recipe.md`,
`annotations/xdata-register-map.md` §4.4 -- and is **typed into the case as a
constant** rather than re-derived from the run that produced the CSVs, so what
is compared is a published figure against a regeneration and never one derived
from the other. That distinction is the whole reason this class exists and it
has bitten this tree before (#753: the recipe had been re-pointed three times
and a `source.replace()` that stopped matching failed silently, so the suite
was comparing the tool against itself). A case that re-derives its
expectations from its own inputs agrees with itself by construction and keeps
agreeing after the recipe changes underneath it.

**The other half asserts arithmetic rather than constants.** `TheRowLevelJoin`
pins the denominators -- 1,169 / 108 / 49 over 1,326 -- because those are
properties of the committed CSV, and pins no count of moved rows, because a
typed 507 is a claim that goes stale silently. Every row is accounted for in
exactly one bucket and the per-program split sums to its total, so a report
that dropped a program, or counted one twice, fails here rather than in a
write-up nobody re-runs.

**`TheRefusalQuotesThePageItCites` is the same discipline applied to prose.**
The `--export-ownership` refusal quotes what flipping the flag would cost, and
what it quoted were denominators from a census the tree no longer has. It holds
the sites that state that cost against the page the refusal cites and against a
fresh `--export-ownership` run, so the chain has no link a human-typed numeral
is holding up: page and prose edited together to a new wrong number still fails
at the census. That is the one class here that reads the committed CSVs for
their row counts rather than asserting figures about them, because the claim it
holds *is* about those row counts.

Nothing here resolves anything against the firmware. The only inputs are four
CSVs, two pages, and regenerations produced by the committed tool writing to a
scratch directory; no image is opened, no register is read back, and no laptop,
EC or Windows machine is involved.
"""
import collections
import csv
import functools
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
EC = HERE.parent
REPO = EC.parent
TOOL = HERE / "xdata_register_map.py"
JOIN = HERE / "xdata_guard_off_row_join.py"
CLUSTERS = EC / "annotations" / "xdata-clusters.csv"
REGISTERS = EC / "annotations" / "xdata-registers.csv"
NAMES = EC / "annotations" / "xdata-cluster-names.csv"
OWNERSHIP_PAGE = EC / "annotations" / "xdata-export-ownership.md"

# The census tool is imported by path because `ec/tools/` is not on `sys.path`
# when the runner invokes this file. Importing it costs a dict of constants, not
# a census.
_spec = importlib.util.spec_from_file_location(
    "xdata_register_map", TOOL)
xrm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xrm)

# The tool's report is `key: value` lines, indented for the sub-figures. A key
# may hold a comma and an apostrophe but not a colon, which every key in the
# report respects -- `Report.value()` says so when one does not, rather than
# splitting a line in a way the tool never meant.
LINE = re.compile(r"(\s*)([^:]+):\s*(.*)$")
FIGURE = re.compile(r"(\d+) of ([\d,]+)")
# A figure as prose spells it rather than as a report cell, so the article is
# optional: "507 of the 1,326 register rows" is the same shape as "507 of
# 1,326", and a rule that wanted one of them would be a rule about a spelling.
FIGURE_IN_PROSE = re.compile(r"\d[\d,]* of (?:the )?[\d,]{3,}")

# `open(..., "w")` and its two other write modes. Held against the tool's
# source rather than described in its docstring, because a description is the
# thing that goes stale when the next mode is added.
WRITE_OPEN = re.compile(r"open\([^)]*['\"][wax]")


def rows_of(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _comment_above(lines, anchor):
    """The `# ` block immediately above `anchor`, and the index `anchor` is on.

    Module level rather than a method on one class, because two classes in this
    file now read a comment off the tool's source and a second copy of "walk
    backwards until a line is not a comment" is a second thing to keep right.
    """
    at = next(i for i, line in enumerate(lines) if line.strip() == anchor)
    above = []
    for line in reversed(lines[:at]):
        if not line.strip().startswith("#"):
            break
        above.append(line)
    if not above:
        raise AssertionError(f"{anchor} has no comment above it")
    return list(reversed(above)), lines, at


def guard_off():
    """(clusters path, registers path) for a guard-off census of this tree.

    Built the way §6a builds it -- the committed tool run with `--no-eq-guard`,
    the switch that "re-runs the census with the `==` rejection turned off" --
    because that is the mechanism the published figures are re-derivable from,
    and a second recipe would be a second thing to keep pointed at the guard.
    Both CSVs go to a scratch directory the flag requires: it refuses the
    committed output paths outright, which is the invariant
    `TheToolWritesNothing` holds from the other side. ~3 s, cached because
    every class below wants the same regeneration.
    """
    tmp = tempfile.mkdtemp(prefix="xdata-guard-off-join-")
    out_clusters = os.path.join(tmp, "clusters.csv")
    out_registers = os.path.join(tmp, "registers.csv")
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--no-eq-guard", "--out-clusters",
         out_clusters, "--out-registers", out_registers],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"the guard-off run failed: {proc.stderr}")
    return out_clusters, out_registers


@functools.lru_cache(maxsize=1)
def joined():
    """The tool's own report over the committed pair and the guard-off one."""
    off_clusters, off_registers = guard_off()
    proc = subprocess.run(
        [sys.executable, str(JOIN), "--off-clusters", off_clusters,
         "--off-registers", off_registers],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"the join failed: {proc.stderr}")
    return proc.stdout, off_clusters, off_registers


def _figure(key, value):
    """(count, denominator) for a `N of M` value, or a failure naming `key`."""
    match = FIGURE.search(value)
    if not match:
        raise AssertionError(f"{key!r} is not a `N of M` figure: {value!r}")
    return int(match.group(1)), int(match.group(2).replace(",", ""))


@functools.lru_cache(maxsize=1)
def ownership_join():
    """The join's report over the committed census and the export-ownership one.

    The `--export-ownership` twin of `joined()`, and built by the same recipe
    the page's own fence spells out: a default run and a flag run, both to a
    scratch directory, joined on `addr`. `xdata_guard_off_row_join.py` is
    already parameterised for exactly this -- `--committed-*` default to the
    committed CSVs and `--off-*` are handed in -- so this is the existing tool
    rather than a second one. Its report **keys** are census-neutral (they name
    columns and clusters, not the flag), which is the only reason its
    hard-coded "guard-off" wording is tolerable here; see the write-up for what
    that costs a reader.

    The committed pair is passed explicitly rather than left to the default so
    that both runs in this helper are the same generation, and so the case can
    say which four files the figures came from.
    """
    tmp = tempfile.mkdtemp(prefix="xdata-ownership-join-")
    before = {name: os.path.join(tmp, f"before-{name}.csv")
              for name in ("clusters", "registers")}
    after = {name: os.path.join(tmp, f"after-{name}.csv")
             for name in ("clusters", "registers")}
    for outputs, flag in ((before, []), (after, ["--export-ownership"])):
        proc = subprocess.run(
            [sys.executable, str(TOOL), *flag,
             "--out-clusters", outputs["clusters"],
             "--out-registers", outputs["registers"]],
            capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise AssertionError(f"the {' '.join(flag) or 'default'} run "
                                 f"failed: {proc.stderr}")
    proc = subprocess.run(
        [sys.executable, str(JOIN),
         "--committed-clusters", before["clusters"],
         "--committed-registers", before["registers"],
         "--off-clusters", after["clusters"],
         "--off-registers", after["registers"]],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"the join failed: {proc.stderr}")
    return proc.stdout


class Report:
    """The tool's `key: value` output, addressable by key and indentation.

    A report a human reads is not a report a test can hold, and this file's
    whole job is to hold one: the write-up quotes these lines verbatim, so a
    figure that drifted out of the tool and stayed in the page would be a page
    asserting something the tool no longer says. `figure()` returns the
    `(count, denominator)` pair, with the denominator carried, because "507"
    alone is a number about an unknown population -- which is the shape of
    complaint issue #832 opened with.
    """

    def __init__(self, text):
        self.rows = [(len(m.group(1)), m.group(2), m.group(3))
                     for m in (LINE.match(line) for line in text.splitlines())
                     if m]

    def value(self, key, indent=0):
        found = [v for i, k, v in self.rows if i == indent and k == key]
        if len(found) != 1:
            raise AssertionError(f"{key!r} at indent {indent} is not a key of "
                                 f"the report {len(found)} time(s): a line "
                                 f"that stopped being printed, or a key that "
                                 f"stopped being unique")
        return found[0]

    def below(self, key):
        """[(indent, key, value)] for the lines indented under `key`."""
        at = next(i for i, (indent, k, _) in enumerate(self.rows)
                  if indent == 0 and k == key)
        out = []
        for row in self.rows[at + 1:]:
            if row[0] == 0:
                break
            out.append(row)
        return out

    def figure(self, key, indent=0):
        """(count, denominator) for a `N of M` value."""
        return _figure(key, self.value(key, indent))

    def split(self, key):
        """{program: (changed, rows)} for a `rows whose C differs` key.

        Read by position rather than by a global key lookup, because
        `main-ec` is a sub-key once per column and a lookup by name would
        find four of them and refuse.
        """
        return {k: _figure(k, v) for i, k, v in self.below(key) if i == 2}

    def names(self):
        """{name: value} for the `name N:` lines."""
        return {k[len("name "):]: v for i, k, v in self.rows
                if i == 0 and k.startswith("name ")}

    def names_by_key(self):
        """{name: True} for the names whose `cluster_key` is unchanged.

        The key-same split, not the `resolves` count on the `names` line. Those
        are two different questions and the difference is the whole of what the
        hand-name figure is about: a name can *resolve* under the flip onto a
        different cluster and still have had to be re-keyed, which is the thing
        a `cluster_key` citation does not survive. So the kept count is the
        names the report prints `key same` for, and the rest is every name whose
        key changed or that failed to resolve at all.
        """
        return {name: "key same" in value for name, value in self.names().items()}


class ThePublishedFigures(unittest.TestCase):
    """The figures the tree already prints, against the files the run wrote.

    Each value below is a figure another page states, and the citation is in
    the comment on the assertion that holds it. Nothing here is derived from
    this suite's own inputs: that is `TheRowLevelJoin`'s job, and doing it here
    too would make this class agree with itself.
    """

    @classmethod
    def setUpClass(cls):
        cls.text, cls.off_clusters, cls.off_registers = joined()
        cls.report = Report(cls.text)

    def test_the_6a_row_counts_are_reproduced(self):
        # `xdata-06c2-06db-timers.md` §6a's table, "cluster rows | 445 | 439"
        # as committed, read off the guard-off run's own `--out-` paths.
        self.assertIn("guard-off 445", self.report.value("clusters"))
        self.assertIn("committed 439", self.report.value("clusters"))

    def test_the_6a_write_and_refs_figures_are_reproduced(self):
        # §6a's own heredoc, printed at `xdata-06c2-06db-timers.md:988-989`:
        # "addresses whose 'write' changes: 211 of 1326" and "addresses whose
        # 'refs' changes: 0 of 1326". The second is the one that matters most
        # -- it is the figure that does not move, and a report that stopped
        # comparing the column would print nothing for it rather than a wrong
        # number, which is the failure this assertion is shaped to catch.
        # 210 -> 211 is issue #424: the `&&` site the classifier used to file
        # `address-taken` is now a read, so under `--no-eq-guard` it reaches
        # `write` like the other 832 `==` sites instead of being the one that
        # did not.
        self.assertEqual(self.report.figure("rows whose write differs"),
                         (211, 1326))
        self.assertEqual(self.report.figure("rows whose refs differs"),
                         (0, 1326))

    def test_the_join_pages_both_and_main_ec_cells_are_reproduced(self):
        # `xdata-no-eq-guard-census-scale-join.md`'s row-level table, the
        # `cluster_id` row: "464 of 1,169" and "34 of 49". The `both` cell is
        # the one that column exists for -- the addresses both programs touch
        # are 49 rows the tree had no per-program rate for -- so it is held
        # here beside the `main-ec` cell it is read against.
        split = self.report.split("rows whose cluster_id differs")
        self.assertEqual(split["both"], (34, 49))
        self.assertEqual(split["main-ec"], (464, 1169))

    def test_the_6a_main_ec_cluster_count_is_reproduced(self):
        # §6a: "main-EC clusters at threshold 0.50 | 394 | 389". The report
        # counts the CSV's rows rather than the program's clusters, so this is
        # read off the same two files §6a's line names.
        off = {r["cluster_id"] for r in rows_of(self.off_clusters)
               if r["program"] == "main-ec"}
        on = {r["cluster_id"] for r in rows_of(CLUSTERS)
              if r["program"] == "main-ec"}
        self.assertEqual((len(on), len(off)), (389, 394))

    def test_the_124_intact_and_315_changed_ranks_are_reproduced(self):
        # The recipe page's "315 of 439 ranks change membership, 124 survive
        # intact" -- the cluster-level half, and the figure the write-up's
        # reconciliation is against. A rank whose guard-off row at the same id
        # holds the same addresses is what that page means by intact, so this
        # is the definition rather than a paraphrase of it.
        off = {r["cluster_id"]: r for r in rows_of(self.off_clusters)}
        on = rows_of(CLUSTERS)
        intact = sum(1 for r in on
                     if r["cluster_id"] in off
                     and set(off[r["cluster_id"]]["addrs"].split())
                     == set(r["addrs"].split()))
        self.assertEqual((intact, len(on) - intact), (124, 315))
        self.assertEqual(len(on), 439)

    def test_the_fifteen_moved_cluster_keys_are_reproduced(self):
        # `xdata-register-map.md` §4.4: "Of the 15, 10 reach a new cluster on
        # overlap and 5 do not reach one at all by this rule". Both halves,
        # because the split is the claim and the total alone would not catch a
        # tool that called all fifteen a match.
        self.assertRegex(self.report.value("cluster_key that moves"),
                         r"^15 of 439 ")
        below = {k: v for _i, k, v in self.report.below("cluster_key that moves")}
        self.assertRegex(below["reach a new cluster on overlap"],
                         r"^10 of 15 at or above 0\.50$")
        self.assertRegex(below["reach none"], r"^5 of 15$")

    def test_the_ten_reached_and_five_unreached_scores_span_what_4_4_says(self):
        # §4.4's "(best scores 0.50-0.97 for the ten, 0.02-0.33 for the five)",
        # read off the report's own per-key rows. A threshold change would then
        # show up as a range that moved rather than as a count that stayed.
        reached, lost = [], []
        for _i, _k, value in self.report.below("cluster_key that moves"):
            match = re.search(r"-> (\S+) at (\d\.\d\d)$", value)
            if not match:
                continue
            (lost if match.group(1) == "none" else reached).append(
                float(match.group(2)))
        self.assertEqual((len(reached), len(lost)), (10, 5))
        self.assertEqual((min(reached), max(reached)), (0.50, 0.97))
        self.assertEqual((min(lost), max(lost)), (0.02, 0.33))

    def test_the_439_the_15_are_a_fraction_of_is_the_439_ranks_are_counted_over(self):
        # The three figures close against the same denominator, so a report
        # that mixed a pair of generations could not satisfy all three at once.
        self.assertEqual(len(rows_of(CLUSTERS)), 439)
        self.assertIn("committed 439", self.report.value("clusters"))


class TheRowLevelJoin(unittest.TestCase):
    """The join's own arithmetic, held without pinning a count it invented."""

    @classmethod
    def setUpClass(cls):
        cls.text, cls.off_clusters, cls.off_registers = joined()
        cls.report = Report(cls.text)
        cls.committed = rows_of(REGISTERS)

    def test_the_denominators_are_the_committed_csv_own(self):
        # 1,169 `main-ec`, 108 `pd`, 49 `both` over 1,326 rows. A property of
        # the committed file, so asserted by value: a census that gained a
        # program would make every cell in the report a fraction of a
        # population nothing else in the tree has measured.
        counts = collections.Counter(r["program"] for r in self.committed)
        self.assertEqual((counts["main-ec"], counts["pd"], counts["both"]),
                         (1169, 108, 49))
        self.assertEqual(sum(counts.values()), 1326)

    def test_every_row_is_accounted_for_in_exactly_one_bucket(self):
        # The rank/key cross-tab has to close. If it did not, a row could sit
        # in two cells and every figure in the report would be about an
        # unknown population -- which is what the `--export-ownership` refusal
        # after this flag's own quotes its numbers to avoid.
        cells = [int(v) for v in re.findall(r"\d+", self.report.value(
            "cluster_id and cluster_key together"))]
        self.assertEqual(len(cells), 4, "four cells, and every one is a count")
        self.assertEqual(sum(cells), 1326)

    def test_the_per_program_split_sums_to_the_total(self):
        for column in ("cluster_id", "cluster_key", "refs", "write"):
            key = f"rows whose {column} differs"
            total, rows = self.report.figure(key)
            split = self.report.split(key)
            self.assertEqual(set(split), {"main-ec", "pd", "both"}, column)
            self.assertEqual(sum(changed for changed, _ in split.values()),
                             total, f"{column}: the split does not sum")
            self.assertEqual(sum(n for _, n in split.values()), rows,
                             f"{column}: the split's denominators do not sum")

    def test_a_both_row_mixes_the_main_ec_clustering_with_summed_counts(self):
        # What the `both` cells *are*, since the page's rate is read off them
        # and the two halves of that column are not the same kind of cell. On a
        # `program=both` row `xdata_register_map.py` picks one program --
        # `primary = "main-ec" if "main-ec" in seen else "pd"` (`:3022`) -- and
        # reads `cluster_id` (`:3029`) and `cluster_key` (`:3058`) from that
        # group alone, "the two programs have separate XDATA maps and a cluster
        # must not span them" (`:346`). `refs` and `write` are the other kind:
        # the sum over both programs (`:191`), which is why the row carries
        # `refs_main_ec`/`refs_pd` and `write_main_ec`/`write_pd` beside them.
        # So `34 of 49` is about the main-EC clustering of those 49 addresses,
        # and the last assertion is the structural reason the write-up claims
        # nothing measured about their PD one: there is one `cluster_id` column
        # to compare, not two.
        both = [r for r in self.committed if r["program"] == "both"]
        self.assertEqual(len(both), 49)
        clusters = {c["cluster_id"]: c for c in rows_of(CLUSTERS)}
        for row in both:
            where = row["cluster_id"]
            with self.subTest(addr=row["addr"]):
                self.assertEqual(clusters[where]["program"], "main-ec",
                                 f"{where} is not a main-EC cluster, so the "
                                 f"`both` cell is not about main-ec")
                self.assertIn(row["addr"], clusters[where]["addrs"].split())
                for column in ("refs", "write"):
                    self.assertEqual(
                        int(row[column]),
                        int(row[f"{column}_main_ec"]) + int(row[f"{column}_pd"]),
                        f"{column} is not the sum over both programs")
        self.assertEqual(
            [c for c in self.committed[0] if c.startswith("cluster_id")],
            ["cluster_id"],
            "a second per-program cluster id would make a `both` row say which "
            "cluster each program put the address in")

    def test_the_both_bucket_moves_faster_than_main_ec(self):
        # The page's one rate comparison -- `both` against `main-ec` -- is
        # arithmetic over two cells of the same split, and a multiplier is the
        # one figure on the page no other line prints, so nothing re-derives
        # it: a draft of that sentence put it at four times, which the two
        # cells make 1.7. The cells themselves are `ThePublishedFigures`'
        # business; what is this class's is the quotient. Held as the quotient
        # rather than as a round number, so a census that moved either cell
        # moves this with it and turns the sentence above stale rather than
        # leaving it to be caught by a reader. What the `both` rate is a rate
        # *over* is the case above's, not this one's: these are two cells of a
        # split, and the split's `both` column is the main-EC clustering of the
        # 49 addresses rather than a count over both programs.
        split = self.report.split("rows whose cluster_id differs")
        both = split["both"][0] / split["both"][1]
        main_ec = split["main-ec"][0] / split["main-ec"][1]
        self.assertAlmostEqual(both, 0.69, places=2)
        self.assertAlmostEqual(main_ec, 0.40, places=2)
        self.assertAlmostEqual(both / main_ec, 1.7, delta=0.1)

    def test_the_cluster_id_and_key_counts_reconcile_with_the_cross_tab(self):
        # `rows whose cluster_id differs` counts a rank and
        # `rows whose cluster_key differs` counts a content hash, and neither
        # implies the other -- a row can keep its number and change which
        # cluster the number is over. The cross-tab is what says how the two
        # overlap, so two numbers printed with no reconciliation would be the
        # shape this case exists to refuse.
        value = self.report.value("cluster_id and cluster_key together")
        cells = dict(zip(("both", "rank only", "key only", "neither"),
                         (int(v) for v in re.findall(r"\d+", value))))
        self.assertEqual(cells["both"] + cells["rank only"],
                         self.report.figure("rows whose cluster_id differs")[0])
        self.assertEqual(cells["both"] + cells["key only"],
                         self.report.figure("rows whose cluster_key differs")[0])

    def test_the_key_moving_rows_sit_in_exactly_the_moved_keys(self):
        # The reconciliation itself, and it is asserted as two **sets** rather
        # than as the two counts the report prints. The counts cannot disagree:
        # `touched` is a subset of the moved keys by construction, because
        # `cluster_key` is a content hash of program plus sorted members
        # (`xdata_register_map.py:1997-2007`) -- a committed key that still
        # existed guard-off would carry the same membership, so its rows would
        # carry the same key and would not be in `touched` at all. Comparing
        # the two counts would be comparing a number with itself. The sets can
        # disagree: a committed key could leave the guard-off census with no
        # key-changing row sitting in it, or a key-changing row could sit in a
        # committed cluster that kept its key under some route the report does
        # not report. So the set equality is the claim, and it is the one that
        # makes the 15 the row count's own population rather than a number
        # that happens to match.

        # CORRECTION (#1128, 2026-10-04): the hash citation read
        # `xdata_register_map.py:2600`, a `"shared_functions": ...` cell in
        # `cluster_rows_build()` -- near the right key, and not the hash. It is
        # `cluster_key()` itself at `:1997`. Held by
        # `ec/tools/check_py_citations.py`.
        below = self.report.below("cluster_key that moves")
        reported = {k: v for _i, k, v in below}
        self.assertEqual(
            int(reported["of those, absent from the guard-off set"]),
            int(reported["distinct committed keys a key-changing row sits in"]),
            "the report's own two counts disagree, so the tool no longer "
            "believes `touched` is a subset of the moved keys")
        # Both sides recomputed from the CSVs, over the same two files the
        # report reads, so this compares the tool's join against the rows
        # rather than the tool against itself.
        on = {r["addr"]: r for r in self.committed}
        off = {r["addr"]: r for r in rows_of(self.off_registers)}
        touched = {on[a]["cluster_key"] for a in on.keys() & off.keys()
                   if on[a]["cluster_key"] != off[a]["cluster_key"]}
        off_keys = {r.get("cluster_key", "") for r in rows_of(self.off_clusters)}
        moved = {r.get("cluster_key", "") for r in rows_of(CLUSTERS)
                 if r.get("cluster_key", "") not in off_keys}
        self.assertTrue(touched, "no key-changing row, so there is nothing to "
                                 "reconcile against the moved keys")
        self.assertEqual(touched, moved,
                         "the committed clusters a key-changing row sits in "
                         "are not the committed keys the guard-off census "
                         "dropped; the 15 and the 336 would be two "
                         "populations rather than one at two granularities")

    def test_a_row_missing_from_one_census_is_its_own_bucket(self):
        # Both censuses here cover one address universe, so both "only"
        # buckets are empty -- and they are reported rather than assumed, since
        # a row that disappeared is a different fact from a row that did not
        # move, and a join that dropped it would go on reporting the second.
        self.assertEqual(self.report.value("addresses committed only"), "0")
        self.assertEqual(self.report.value("addresses guard-off only"), "0")
        self.assertEqual(self.report.value("addresses compared"), "1326 in both")

    def test_no_row_falls_outside_the_declared_program_split(self):
        # The tool splits by a hand-written three-value list, so a fourth
        # program would be dropped from every cell while the cells still summed
        # to the total. The line is what stops that being invisible, and it is
        # printed unconditionally so that its absence cannot be mistaken for a
        # rule that stopped running.
        self.assertEqual(
            self.report.value("rows whose program is not in the declared split"),
            "none")

    def test_the_names_section_covers_the_committed_census(self):
        # Nine hand names, and the report is not allowed to quietly carry eight
        # of them: `xdata-cluster-names.csv` is the census's editable surface
        # and a name it stops naming is a claim that went missing.
        named = {r["cluster_name"].strip() for r in rows_of(CLUSTERS)
                 if r.get("cluster_name")}
        self.assertEqual(len(named), 9)
        self.assertEqual(set(self.report.names()), named)
        self.assertRegex(self.report.value("names"),
                         r"^9 committed, 9 resolve in the guard-off census$")

    def test_the_rekeyed_name_is_named_with_both_of_its_keys(self):
        # `mode-oem-init` is the one name the recipe page reports changing on
        # both columns, and the cell that says so is the pair of keys. A report
        # printing only "key changed" would leave the reader to diff two CSVs
        # to learn which key it landed on.
        line = self.report.names()["mode-oem-init"]
        self.assertIn("kefb63d82f8c7 -> kc0f2a0be0103", line)
        self.assertIn("92 -> 93 addrs", line)
        self.assertIn("carried overlap at 0.97", line)

    def test_every_other_name_is_seeded_and_holds_its_key(self):
        # The other eight arrive by key, which is the one route that needs no
        # threshold. Asserted as a set rather than one at a time so a name that
        # silently changed route would be named by the difference.
        rekeyed = {n for n, v in self.report.names().items()
                   if "key changed" in v or "unresolved" in v}
        self.assertEqual(rekeyed, {"mode-oem-init"})
        for name, line in self.report.names().items():
            if name == "mode-oem-init":
                continue
            self.assertIn("carried seeded at 1.00", line)


class TheJoinKeyIsUnique(unittest.TestCase):
    """`addr` alone is the join key, which is a fact about this CSV and can
    stop being one. The tool reports it; this holds that the report is right
    and that the question it answers -- can a join on `addr` collapse a
    `main-ec` row into a `pd` row -- is the one being asked.

    Both programs touching one address would be two rows in this census and one
    key, which is why the report splits by program rather than summing. The
    number asserted here is 0 on this tree, and the case is about the check
    existing rather than about the 0: a census that gained such an address
    would make the split load-bearing rather than a convenience, and the only
    thing standing between that and a silently wrong join is a check that runs.
    """

    @classmethod
    def setUpClass(cls):
        cls.text, _off_clusters, off_registers = joined()
        cls.report = Report(cls.text)
        cls.pairs = (rows_of(REGISTERS), rows_of(off_registers))

    def test_addr_is_a_key_in_both_censuses(self):
        for rows in self.pairs:
            self.assertEqual(len({r["addr"] for r in rows}), len(rows))

    def test_no_address_is_under_more_than_one_program(self):
        self.assertRegex(self.report.value("addresses under more than one program"),
                         r"^0 committed, 0 guard-off$")
        for rows in self.pairs:
            programs = collections.defaultdict(set)
            for row in rows:
                programs[row["addr"]].add(row["program"])
            self.assertEqual([a for a, p in programs.items() if len(p) > 1], [])


class TheRefusalArguesFromAFigure(unittest.TestCase):
    """The issue's title complaint, held so it cannot come back quietly.

    The `--no-eq-guard` refusal used to be an instruction with no result
    recorded anywhere, while the `--export-ownership` refusal below it quoted
    measured numbers. That asymmetry was the whole of the issue, so it is
    pinned here: the comment above the refusal has to name a figure the tool
    measures and the page that records it. **The two blocks keep their line
    counts**, because `check_eq_guard_citations.py` resolves `check_refusal`
    and `committed_output_refusal` from the code immediately below this one,
    and a line added above them moves both pins and turns that gate red for a
    reason that has nothing to do with the finding.
    """

    REFUSAL = "if args.no_eq_guard and (args.check or args.self_test):"
    SIBLING = "if args.export_ownership and (args.check or args.self_test):"
    PAGE = "xdata-no-eq-guard-census-scale-join.md"

    def comment_above(self, anchor):
        lines = TOOL.read_text(encoding="utf-8").splitlines()
        return _comment_above(lines, anchor)

    def setUp(self):
        self.comment, self.lines, self.at = self.comment_above(self.REFUSAL)
        self.text = "\n".join(self.comment)

    def test_the_refusal_comment_names_a_measured_figure(self):
        self.assertRegex(
            self.text, FIGURE_IN_PROSE,
            "the refusal quotes no figure, which is what issue #832 opened on")

    def test_the_refusal_comment_names_the_page_that_records_it(self):
        self.assertIn(self.PAGE, self.text,
                      "a figure with no write-up behind it is a number a "
                      "future re-derivation cannot go and re-read")

    def test_the_refusal_comment_does_not_call_a_moved_row_mis_clustered(self):
        # CLAUDE.md's rule, in the place a reader of this flag meets it.
        # "Different under the flag" is a measurement; "mis-clustered" is a
        # verdict on the firmware that two CSVs cannot support.
        self.assertNotIn("mis-cluster", self.text.lower())

    def test_the_comment_block_keeps_its_six_lines(self):
        # Six was the count before the edit and is the count after; see the
        # class docstring for what moving it would cost.
        self.assertEqual(len(self.comment), 6,
                         "the --no-eq-guard refusal comment changed length; "
                         "the check_refusal anchor below it moves with it")

    def test_the_error_call_keeps_its_four_lines(self):
        call = next(i for i in range(self.at, len(self.lines))
                    if self.lines[i].lstrip().startswith("ap.error("))
        joined = " ".join(line.strip() for line in self.lines[call:call + 4])
        self.assertIn("changes what the census says", joined)
        self.assertTrue(joined.rstrip('")').endswith("committed one."))
        self.assertNotIn("ap.error", self.lines[call + 4],
                         "the refusal grew a line, and the "
                         "committed_output_refusal anchor below it moves with it")

    def test_the_committed_output_refusal_is_untouched(self):
        # The other half of the flag's contract, and the one this change does
        # not make: a guard-off run must still be given scratch outputs. Read
        # with the quote characters and the wrapping collapsed, so the check
        # is on the sentence rather than on how the tool happens to fold it.
        flat = re.sub(r"\s+", " ", re.sub(r"[\"']", " ",
                                          "\n".join(self.lines)))
        self.assertIn("--no-eq-guard would overwrite the committed census, so "
                      "it must be given scratch outputs", flat)

    def test_the_sibling_refusal_cites_the_page_that_measured_its_cost(self):
        # The cost of flipping --export-ownership is measured in a write-up,
        # and the refusal names it rather than quoting its figures: they moved
        # with every seeded routine, and a refusal carrying them was a line
        # every such branch had to edit (2026-10-04).
        comment, _lines, _at = self.comment_above(self.SIBLING)
        self.assertIn("annotations/xdata-export-ownership.md",
                      "\n".join(comment))


class TheToolWritesNothing(unittest.TestCase):
    """The invariant the issue is really about, from the tool's own side.

    `xdata_register_map.py` refuses `--no-eq-guard` against the committed
    output paths, and that refusal is left exactly as it is. A measurement that
    overwrote the census to take its reading would be a second, quieter way
    round the same guard, so this tool has no `--write`, no `--out-` and no
    code path that opens a file for writing.
    """

    @classmethod
    def setUpClass(cls):
        cls.source = JOIN.read_text(encoding="utf-8")

    def test_no_write_mode_is_ever_opened(self):
        # The grep finds nothing today, and that is the state worth holding:
        # the tool delegates every read to `xdata_register_map.py`'s own loader
        # and opens no file itself, so there is no line for a future mode to
        # add a write to without this going red first. A tool that opened even
        # one read would still pass -- the property is the write, not the read.
        self.assertIsNone(WRITE_OPEN.search(self.source),
                          "the tool must not be able to write; that is the "
                          "invariant the flag's second refusal protects")

    def test_there_is_no_output_option_at_all(self):
        # Over the argument parser rather than the whole file, because the
        # docstring names `--write` to say that there isn't one and a grep over
        # the prose would read its own explanation as the thing it forbids.
        parser = self.source[self.source.index("def main()"):]
        for flag in ("--write", "--out-clusters", "--out-registers"):
            self.assertNotIn(f'"{flag}"', parser,
                             f"{flag} would give this tool a way to touch a "
                             f"census path")

    def test_a_full_guard_off_run_leaves_the_tree_exactly_as_it_was(self):
        # Before and after rather than "empty": this suite is committed into a
        # working tree, so a literal emptiness check would be red on every
        # branch not yet committed, and a gate that is always red is not a
        # gate. What is held is that the run changes nothing, which is the
        # same claim with a denominator this tree can actually supply.
        before = self._status()
        scratch = tempfile.mkdtemp(prefix="xdata-nothing-")
        subprocess.run(
            [sys.executable, str(TOOL), "--no-eq-guard", "--out-clusters",
             os.path.join(scratch, "clusters.csv"), "--out-registers",
             os.path.join(scratch, "registers.csv")],
            capture_output=True, text=True, check=True)
        self.assertEqual(self._status(), before)

    def test_the_flag_is_still_refused_against_the_committed_paths(self):
        for extra in (["--check"], ["--self-test"], [],
                      ["--out-clusters", str(CLUSTERS)],
                      ["--out-registers", str(REGISTERS)]):
            proc = subprocess.run(
                [sys.executable, str(TOOL), "--no-eq-guard"] + extra,
                capture_output=True, text=True, check=False)
            self.assertNotEqual(
                proc.returncode, 0,
                f"--no-eq-guard {' '.join(extra) or '(bare)'} was accepted, and "
                f"a bare run writes the committed CSVs")

    @staticmethod
    def _status():
        proc = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                              capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise unittest.SkipTest("git is not available here")
        return proc.stdout


if __name__ == "__main__":
    unittest.main()
