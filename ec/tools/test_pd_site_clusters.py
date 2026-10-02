#!/usr/bin/env python3
"""Cases for `pd_site_clusters.py`'s join between the enumerated sites and
the committed `pd` routine set.

The tool's whole product is an attribution, and an attribution's failure mode
is a plausible-looking one: every site gets *a* routine or a plausible
`-`, every per-address count still adds up, and nothing says the split is
wrong. So the cases split three ways, and the third is the largest.

**The claim, as the issue stated it.** The runtimes this tool derives for
`0x07D0` are the runtimes `ec-0x07d0-sites.csv` enumerates -- a set, not a
count, so a site gained on either side moves the assertion rather than being
absorbed by it. Every site's region is the PD image on both addresses, which
is the premise the whole file rests on: a site in the main EC would be a
different program's byte of the same number. And the per-address cluster
counts sum to the per-address totals, so no site is dropped between the
enumeration and the table.

**The instrument, held to the file it reads.** The routine set is not
restated here as a list; it is read from `ec/decompiled/index.csv` by a
second, deliberately naive comprehension, and the two are compared as sets,
so an added or dropped row has to move the test whichever end moved. The
containment rule is then held on hand-built ranges at their four boundaries
(inside, last byte, one past the last, and in an overlap) because a boundary
off by one is the defect that would quietly move sites between a routine and
the unclustered bucket.

**The refusals, and they are the point.** Each of the four ways a table can
add up while meaning nothing is run through `--check` as a doctored copy on
disk, so what is tested is the exit code a CI run would see and not a helper
returning a list: a cluster naming a routine `index.csv` does not commit, a
site attributed to a committed routine that does not contain it, a row the
image does not yield, and a row the image yields that the table does not
hold. The last two are separate because a table that swaps one row for
another keeps its row count, which is the case a count cannot catch.

**And the reconciliation everything else quotes.** The per-address totals are
held against `ec/annotations/registers.yaml`'s own `static_refs` and
`static_refs_pd_image` for both addresses -- a third committed file, which
neither the tool nor this suite derives anything from. If that file ever
stops agreeing with what the image yields, the disagreement is the finding,
and it is this test that sees it.

Nothing here asserts a count of the tree. The population is held as a
relationship between three committed files, so a routine added to
`index.csv` or a site added to the enumeration moves the arithmetic and not
a literal.
"""
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
# pd_site_clusters imports its sibling by bare module name, the way the rest of
# this directory does, so the tool directory goes on the path before the load
# rather than after.
sys.path.insert(0, HERE)

import pd_site_clusters as psc  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")
REGISTERS = os.path.join(HERE, os.pardir, "annotations", "registers.yaml")

# The two addresses of issue #25, and the `registers.yaml` entry each is.
ADDRS = {"0x07D0": 0x07D0, "0x07CC": 0x07CC}


def run(*args):
    return subprocess.run([sys.executable, os.path.join(HERE, "pd_site_clusters.py"),
                           *args], cwd=REPO, capture_output=True, text=True)


def _rows(text):
    return [r for r in csv.reader(io.StringIO(text)) if r]


def _read(path):
    with open(path, newline="") as f:
        return f.read()


class TestTheJoin(unittest.TestCase):
    """The product: every enumerated site placed or explicitly not placed."""

    @classmethod
    def setUpClass(cls):
        cls.rs = psc.routines()
        cls.d = psc.load_image(FIRMWARE)
        cls.rows, cls.ambiguous = psc.cluster_rows(cls.d, list(ADDRS), cls.rs)
        cls.found = psc.found_sets(cls.rows)

    def test_derived_runtimes_are_the_committed_enumeration(self):
        # `0x07D0` only: it is the address with a committed enumeration, and
        # `0x07CC` has none -- the cluster table beside this tool's output is
        # the first enumeration of it, which is why `TestReconciliation`
        # holds that address against `registers.yaml` instead.
        derived = {r[3] for r in self.rows if r[0] == "0x07D0"}
        self.assertEqual(derived, psc.enumerated_set())

    def test_every_site_is_in_the_pd_image(self):
        self.assertTrue(self.rows)
        self.assertEqual({r[2] for r in self.rows}, {"pd-image"})

    def test_the_clusters_partition_every_address(self):
        # The property, not the figures: every site of an address is in
        # exactly one cluster or carries the no-cluster marker, the clusters
        # add up to the address's total, and the table's own site set is the
        # one the image yields.
        for addr in ADDRS:
            with self.subTest(addr=addr):
                mine = [r for r in self.rows if r[0] == addr]
                clustered = [r for r in mine if r[4] != psc.NO_CLUSTER]
                names = {r[4] for r in clustered}
                self.assertEqual(len({r[3] for r in mine}), len(mine))
                self.assertEqual(len(self.found[addr]), len(mine))
                # Every cluster name denotes a disjoint, non-empty set of
                # rows, so no site is counted under two routines and no name
                # is carried by zero of them.
                grouped = [r for n in sorted(names) for r in clustered
                           if r[4] == n]
                self.assertEqual(len(grouped), len(clustered))
                self.assertEqual(len({id(r) for r in grouped}),
                                 len({id(r) for r in clustered}))

    def test_no_site_is_attributed_to_a_routine_that_does_not_contain_it(self):
        known = {name: (start, size) for start, size, name, _t in self.rs}
        for r in self.rows:
            if r[4] == psc.NO_CLUSTER:
                continue
            start, size = known[r[4]]
            with self.subTest(runtime=r[3], function=r[4]):
                self.assertTrue(start <= int(r[3], 16) < start + size)

    def test_the_tool_reports_both_halves_of_the_split(self):
        # "inside a routine this project has committed" read without the
        # complement is the overclaim the whole tool is written against, so
        # the report has to carry the unclustered half in its own words.
        out = run(FIRMWARE)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        for addr in ADDRS:
            self.assertIn(addr, out.stdout)
        self.assertIn("outside every committed routine", out.stdout)
        self.assertIn("not about the firmware", out.stdout)

    def test_no_site_of_either_address_is_ambiguous(self):
        self.assertEqual(self.ambiguous, [])

    def test_ambiguous_sites_are_reported_and_not_attributed(self):
        # A site two committed ranges both contain gets the no-cluster marker
        # and an entry in the ambiguity list. Built by handing the tool a
        # routine set that overlaps the real one, so the policy is exercised
        # on the code path and not only on a pair of tuples.
        d = psc.load_image(FIRMWARE)
        first = next(r for r in self.rows if r[4] != psc.NO_CLUSTER)
        runtime = int(first[3], 16)
        widened = list(self.rs)
        widened.append((runtime, 3, "shadow_of_a_real_routine", "logic"))
        rows, ambiguous = psc.cluster_rows(d, list(ADDRS), widened)
        self.assertTrue(any(rt == runtime and a == int(first[0], 16)
                            for a, rt, _n in ambiguous))
        for r in rows:
            if r[3] == first[3]:
                self.assertEqual(r[4], psc.NO_CLUSTER)
                self.assertEqual(r[5], psc.NO_CLUSTER)


class TestHeldToIndexCsv(unittest.TestCase):
    """The instrument: `routines()` against the file it reads, and the
    containment rule at its boundaries."""

    def test_routines_is_exactly_the_named_positive_size_pd_rows(self):
        # Deliberately a second, naive comprehension of the same CSV rather
        # than a restatement of the answer, so a row added or dropped in
        # index.csv moves this whichever end moved.
        with open(psc.INDEX_CSV, newline="") as f:
            want = {(int(r["addr"], 16), int(r["size"]), r["name"].strip())
                    for r in csv.DictReader(f)
                    if r["program"] == psc.PD_PROGRAM and r["name"].strip()
                    and int(r["size"]) > 0}
        got = {(start, size, name)
               for start, size, name, _t in psc.routines()}
        self.assertEqual(got, want)

    def test_containment_boundaries(self):
        rs = [(0x1000, 0x10, "outer", "logic"), (0x2000, 0x10, "inner", "gate")]
        self.assertEqual(psc.containing(rs, 0x1000), [rs[0]])   # first byte
        self.assertEqual(psc.containing(rs, 0x100F), [rs[0]])   # last byte
        self.assertEqual(psc.containing(rs, 0x1010), [])        # one past
        self.assertEqual(psc.containing(rs, 0x0FFF), [])        # one before
        self.assertEqual(psc.containing(rs, 0x2005), [rs[1]])

    def test_overlap_is_reported_rather_than_tie_broken(self):
        rs = [(0x1000, 0x40, "outer", "logic"), (0x1010, 0x10, "inner", "gate")]
        self.assertEqual(len(psc.containing(rs, 0x1014)), 2)


class TestTheRefusals(unittest.TestCase):
    """`--check` on a doctored copy, so what is under test is the exit code a
    CI run sees and not a helper's return value."""

    @classmethod
    def setUpClass(cls):
        cls.rows, _ = psc.cluster_rows(psc.load_image(FIRMWARE),
                                       list(ADDRS), psc.routines())

    def _check(self, rows, expect):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "doctored.csv")
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(psc.COLUMNS)
                w.writerows(rows)
            out = run(FIRMWARE, "--check", path)
        self.assertNotEqual(out.returncode, 0, out.stdout + out.stderr)
        for phrase in expect:
            self.assertIn(phrase, out.stderr)

    def test_the_committed_table_passes(self):
        out = run(FIRMWARE, "--check")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("byte for byte", out.stdout)

    def test_a_cluster_naming_an_uncommitted_routine_is_refused(self):
        rows = [list(r) for r in self.rows]
        rows[0][4] = "a_routine_nobody_committed"
        self._check(rows, ["is not a routine"])

    def test_a_site_attributed_outside_its_routine_is_refused(self):
        rows = [list(r) for r in self.rows]
        clustered = [r for r in rows if r[4] != psc.NO_CLUSTER]
        other = next(r[4] for r in clustered if r[4] != clustered[0][4])
        clustered[0][4] = other
        self._check(rows, ["does not contain it"])

    def test_a_row_the_image_does_not_yield_is_refused(self):
        rows = [list(r) for r in self.rows][1:]
        planted = list(self.rows[0])
        planted[1], planted[3] = "0x2FFF0", "0xFFF0"
        planted[4:7] = [psc.NO_CLUSTER] * 3
        rows.append(planted)
        # The row count is unchanged, so this is the case only the membership
        # half of validate_table() can see.
        self._check(rows, ["in the table and not in the image",
                           "in the image and not in the table"])

    def test_a_dropped_row_is_refused(self):
        rows = [list(r) for r in self.rows][1:]
        self._check(rows, ["in the image and not in the table", "table holds"])

    def test_a_renamed_routine_is_refused_even_though_the_count_holds(self):
        # The whole table renamed to one invented routine: every per-address
        # count is unchanged, and the check still goes red on every row.
        rows = [list(r) for r in self.rows]
        for r in rows:
            if r[4] != psc.NO_CLUSTER:
                r[4] = "one_big_routine"
        self._check(rows, ["is not a routine"])


class TestReconciliation(unittest.TestCase):
    """The per-address totals against the third committed file that quotes
    them, so a disagreement there is a finding rather than a surprise."""

    @classmethod
    def setUpClass(cls):
        with open(REGISTERS) as f:
            entries = yaml.safe_load(f)["registers"]
        cls.by_addr = {e["addr"]: e for e in entries
                       if e.get("addr") in ADDRS.values()}
        cls.found = psc.found_sets(
            psc.cluster_rows(psc.load_image(FIRMWARE), list(ADDRS),
                             psc.routines())[0])

    def test_both_addresses_have_a_registers_yaml_entry(self):
        self.assertEqual(set(self.by_addr), set(ADDRS.values()))

    def test_derived_totals_are_the_ones_registers_yaml_records(self):
        for text, addr in ADDRS.items():
            entry = self.by_addr[addr]
            with self.subTest(addr=text):
                self.assertEqual(len(self.found[text]), entry["static_refs"])
                self.assertEqual(len(self.found[text]),
                                 entry["static_refs_pd_image"])
                # The other program's count stays at zero, and this tool
                # derives no site for it -- the claim the whole file rests on.
                self.assertEqual(entry["static_refs_main_ec"], 0)

    def test_trace_xdata_refs_still_counts_what_this_tool_clusters(self):
        out = subprocess.run(
            [sys.executable, os.path.join(HERE, "trace_xdata_refs.py"),
             FIRMWARE, *ADDRS, "--counts-only"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        for text, addr in ADDRS.items():
            with self.subTest(addr=text):
                self.assertIn(f"{text}: {len(self.found[text])} direct "
                              f"MOV DPTR site(s)", out.stdout)


class TestNoRegression(unittest.TestCase):
    """The inputs this change leans on still hold, and the tree is untouched."""

    def test_the_tools_own_self_test_passes(self):
        out = run(FIRMWARE, "--self-test")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("self-test passed", out.stdout)
        self.assertNotIn("FAIL", out.stdout)

    def test_the_enumeration_this_tool_joins_against_is_unchanged(self):
        # The whole table, not just its runtimes: this change adds a cluster
        # column beside the enumeration and must not move a single `access`,
        # `window` or framing cell in it. Compared column-wise rather than
        # through trace_xdata_refs.py's own --check, because that path always
        # appends the `census` column and the 0x07D0 table carries none --
        # which is why no committed table is that command's default.
        out = subprocess.run(
            [sys.executable, os.path.join(HERE, "trace_xdata_refs.py"),
             FIRMWARE, "0x07D0", "--csv", "--terminator-column"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(_rows(out.stdout), _rows(_read(psc.ENUMERATED_CSV)))

    def test_the_decoder_the_tool_depends_on_still_passes_its_own(self):
        out = subprocess.run(
            [sys.executable, os.path.join(HERE, "disasm8051.py"), "--self-test"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_the_status_vocabulary_is_unchanged(self):
        out = subprocess.run(
            [sys.executable, os.path.join(HERE, "check_status_vocabulary.py"),
             "--check"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


class TestWritesNothing(unittest.TestCase):
    """The tool is read-only, and a run that left a file behind would be a
    finding about the tree rather than about the machine."""

    def test_working_tree_is_byte_identical_across_a_run(self):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                                capture_output=True, text=True).stdout
        run(FIRMWARE)
        run(FIRMWARE, "--csv")
        run(FIRMWARE, "--check")
        after = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                               capture_output=True, text=True).stdout
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
