#!/usr/bin/env python3
"""Offline checks for `check_cluster_refs_projection.py`: a cluster's `refs` is
the sum of its members' `refs_<program>`, and not of their `refs` (issue #343).

The rule itself is one line over two committed CSVs, and **a one-line rule is
the shape that cannot tell whether it can fire.** Every case here is therefore
either the committed tree passing or the check refusing a scratch copy of it
that has been changed in one specific way -- an off-by-one in a `refs` cell, a
`both` row's split moved from one program to the other, a cluster's `program`
flipped, an `addr_range` written the way a multi-address cluster writes it.
Nothing here constructs a census from scratch: the point is that the rule reads
what is committed, so every fixture is the committed pair with one edit on it,
written to a `tempfile` and never back.

The two that decide whether the check means what its docstring says:

  * `TheBothSplitMoved` changes a `both` row's `refs_main_ec` / `refs_pd`
    **without changing its `refs`**, so a check reading the unsuffixed column
    sees nothing and a check reading the per-program one goes red. That
    asymmetry is the whole claim; an implementation that summed `refs` would
    pass every other case in this file.
  * `TheCorpusTotalCannotTell` moves one cluster's `refs` up and another's down
    by the same amount, leaving `Σ cluster refs == Σ registers refs` true.
    That identity is what `xdata_register_map.py --self-test` asserts, and it
    holding is exactly what it cannot notice -- so the corpus total is kept as
    the weaker claim it is, beside the per-cluster rule that can.

No image, no decompile, no Ghidra, no network, and nothing here touched
hardware or Windows: every figure re-derives from the two committed CSVs, which
is the calibration the write-up
(`../../docs/findings/xdata-cluster-refs-projection.md`) records.
"""
import csv
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
EC = HERE.parent
TOOL = HERE / "check_cluster_refs_projection.py"
CLUSTERS = EC / "annotations" / "xdata-clusters.csv"
REGISTERS = EC / "annotations" / "xdata-registers.csv"

_spec = importlib.util.spec_from_file_location("check_cluster_refs_projection", TOOL)
proj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(proj)


def rows_of(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def scratch(directory, clusters_edit=None, registers_edit=None):
    """(clusters path, registers path) for a copy of the committed pair.

    `*_edit` is called with the list of row dicts and returns nothing; it
    mutates in place. `tempfile` rather than a fixed directory under the repo,
    so a case that fails part way cannot leave a plausible census behind for a
    later case to read as committed.
    """
    paths = {}
    for name, source, edit in (("clusters", CLUSTERS, clusters_edit),
                               ("registers", REGISTERS, registers_edit)):
        fieldnames, data = rows_of(source)
        if edit is not None:
            edit(data)
        out = Path(directory) / f"{name}.csv"
        with open(out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        paths[name] = out
    return paths["clusters"], paths["registers"]


def problems_of(clusters_edit=None, registers_edit=None):
    """The check's problems over a scratch copy of the committed pair."""
    with tempfile.TemporaryDirectory(prefix="cluster-refs-") as tmp:
        clusters, registers = scratch(tmp, clusters_edit, registers_edit)
        return proj.check(str(clusters), str(registers))[0]


def one_cluster_with_a_both_member(rows):
    """A cluster row holding an address the registers CSV calls `both`.

    Found rather than named: which cluster a `both` address lands in is a
    property of the census's ranking, and #274 is the write-up that says a rank
    is not an identity. A case that named `main-ec-001` would go red on the
    next re-derivation for a reason that says nothing about the rule.
    """
    _fields, registers = rows_of(REGISTERS)
    both = {r["addr"] for r in registers if r["program"] == "both"}
    for row in rows:
        if both & set(row["addrs"].split()):
            return row["cluster_id"]
    raise AssertionError("no committed cluster holds a `program=both` address")


class TheCommittedTree(unittest.TestCase):
    """The claim, on the tree it is committed to."""

    def test_the_committed_pair_is_a_projection(self):
        problems, population = proj.check(str(CLUSTERS), str(REGISTERS))
        self.assertEqual(problems, [], "\n".join(problems))
        # The population, rather than a claim about it: the check is asked to
        # recompute every row and to say how many rows that was, so a run that
        # sampled would have to say so here.
        self.assertEqual(population, len(rows_of(CLUSTERS)[1]))

    def test_the_run_exits_zero_and_prints_its_population(self):
        # The tool as `main()` returns it, which is the only arrangement that
        # observes a process status. A checker imported by a suite and never
        # run has not been shown to be a command.
        proc = subprocess.run([sys.executable, str(TOOL)],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"{len(rows_of(CLUSTERS)[1])} cluster(s) recomputed",
                      proc.stdout)
        self.assertEqual(proc.stderr, "")

    def test_a_missing_file_is_a_failure_not_a_traceback(self):
        proc = subprocess.run(
            [sys.executable, str(TOOL), "--clusters", "/nonexistent/clusters.csv"],
            capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("does not exist", proc.stderr)

    def test_a_bare_address_range_is_a_rule_and_not_a_discrepancy(self):
        # The single-address clusters write `addr_range` bare -- `0x0440`, not
        # `0x0440-0x0440` -- and there are a lot of them, so an implementation
        # that wrote the range form would be "correct" against a large minority
        # of the file and wrong against the rest. Derived, not counted: which
        # clusters are singletons is a property of the census.
        _fields, clusters = rows_of(CLUSTERS)
        singletons = [r for r in clusters if len(r["addrs"].split()) == 1]
        self.assertTrue(singletons,
                        "no committed cluster is a singleton, so the bare-range "
                        "rule below is not being exercised by the tree at all")
        for row in singletons:
            with self.subTest(cluster=row["cluster_id"]):
                self.assertNotIn("-", row["addr_range"])
        # And the check holds the rule rather than passing them by accident.
        problems = problems_of(
            clusters_edit=lambda rows: next(
                r.__setitem__("addr_range", r["addr_range"] + "-" + r["addr_range"])
                for r in rows if len(r["addrs"].split()) == 1))
        self.assertTrue(any("addr_range" in p for p in problems),
                        "a singleton's range written as a span was accepted")


class TheRefusals(unittest.TestCase):
    """One edit per rule, each shown to make the check red on its own."""

    def test_one_ref_off_by_one_is_refused(self):
        cid = one_cluster_with_a_both_member(rows_of(CLUSTERS)[1])

        def bump(rows):
            row = next(r for r in rows if r["cluster_id"] == cid)
            row["refs"] = str(int(row["refs"]) + 1)

        problems = problems_of(clusters_edit=bump)
        about_cluster = [p for p in problems if p.startswith(f"{cid}: ")]
        self.assertEqual(len(about_cluster), 1, "\n".join(problems))
        # The message has to name the column that decides the row, or it is a
        # red line a reader cannot argue from.
        self.assertIn("refs_main_ec" if cid.startswith("main-ec") else "refs_pd",
                      about_cluster[0])
        # And it moves the corpus total too, which is why the two rules are
        # reported separately: a reader has to be able to tell "this cluster's
        # apportionment is wrong" from "the two files no longer add up".
        self.assertTrue(any("do not describe one census" in p for p in problems),
                        "the corpus total was still reported as agreeing, which "
                        "would leave a moved cluster looking like a moved "
                        "census")

    def test_a_both_rows_split_moved_is_refused(self):
        # **The case that decides whether the check reads the per-program
        # columns or the unsuffixed `refs`.** One reference moves from the pd
        # half of a `both` row to its main-EC half: `refs_main_ec` +1,
        # `refs_pd` -1, and `refs` untouched, so the two halves still add up to
        # the row's own figure and the unsuffixed column is bit-for-bit what it
        # was. A check summing `refs` sees nothing at all; this one is red.
        _fields, registers = rows_of(REGISTERS)
        victim = next(r for r in registers
                      if r["program"] == "both" and int(r["refs_pd"]) > 0)
        addr = victim["addr"]

        def move(rows):
            row = next(r for r in rows if r["addr"] == addr)
            row["refs_main_ec"] = str(int(row["refs_main_ec"]) + 1)
            row["refs_pd"] = str(int(row["refs_pd"]) - 1)

        problems = problems_of(registers_edit=move)
        # **In exactly the clusters that hold it, and nowhere else.** The
        # equality rather than a `assertTrue` is the part that discriminates: a
        # check summing the unsuffixed `refs` is red on the committed tree
        # already -- 58 clusters disagree with a raw sum -- so "something was
        # refused" is satisfied by an implementation that does not read these
        # columns at all. What only a per-program read can produce is a refusal
        # confined to the clusters whose own `refs_<program>` moved, and that
        # is what is asserted.
        holders = {r["cluster_id"] for r in rows_of(CLUSTERS)[1]
                   if addr in r["addrs"].split()}
        self.assertTrue(holders, f"{addr} is a member of no committed cluster")
        self.assertEqual({p.split(":")[0] for p in problems}, holders,
                         f"moving one reference between {addr}'s two halves "
                         f"refused {sorted({p.split(':')[0] for p in problems})}"
                         f" and the clusters holding it are {sorted(holders)}")

        # And the edit kept the identity #713 put there, so the red above is
        # attributable to the projection and not to the split ceasing to be a
        # split.
        edited = next(r for r in registers if r["addr"] == addr)
        moved = {k: int(v) for k, v in edited.items()
                 if k in ("refs", "refs_main_ec", "refs_pd")}
        self.assertEqual(moved["refs_main_ec"] + moved["refs_pd"], moved["refs"])

    def test_a_flipped_program_is_refused(self):
        # A program-keyed rule, so that keying on nothing cannot satisfy it:
        # flipping a main-EC cluster to `pd` makes its members' `refs_pd`
        # cells the named input, which is not what the row says.
        cid = one_cluster_with_a_both_member(rows_of(CLUSTERS)[1])
        other = "pd" if cid.startswith("main-ec") else "main-ec"

        def flip(rows):
            next(r for r in rows if r["cluster_id"] == cid).__setitem__(
                "program", other)

        problems = problems_of(clusters_edit=flip)
        self.assertTrue(problems,
                        f"{cid} re-labelled `{other}` was accepted, so the rule "
                        f"is not keyed on the cluster's `program` at all")
        self.assertIn(cid, "\n".join(problems))

    def test_a_member_the_registers_csv_does_not_carry_is_refused(self):
        # The named input has to be complete, or the sum silently omits a term
        # and the cluster's `refs` is compared against a partial one.
        def drop(rows):
            del rows[0]

        problems = problems_of(registers_edit=drop)
        self.assertTrue(problems, "a registers CSV missing a member was accepted")
        self.assertIn("cannot be recomputed", "\n".join(problems))

    def test_a_size_that_is_not_the_membership_is_refused(self):
        def bump(rows):
            row = next(r for r in rows if len(r["addrs"].split()) > 1)
            row["size"] = str(int(row["size"]) + 1)

        problems = problems_of(clusters_edit=bump)
        self.assertTrue(any("`size`" in p for p in problems),
                        "a `size` that disagrees with `addrs` was accepted")

    def test_a_foreign_member_is_refused(self):
        # An address a `main-ec` cluster holds whose own `program` is `pd`: the
        # per-program column of a program the cluster does not hold is not a
        # figure about this cluster, and the sum has to say so rather than read
        # it. One `program` cell on the registers CSV is the whole forgery --
        # the row keeps its membership, and every `refs_<program>` cell stays
        # put, so nothing else in the file moves with it.
        _fields, registers = rows_of(REGISTERS)
        _fields, clusters = rows_of(CLUSTERS)
        holders = {a for r in clusters if r["program"] == "main-ec"
                   for a in r["addrs"].split()}
        victim = next(r for r in registers
                      if r["program"] == "main-ec" and r["addr"] in holders)

        def relabel(rows):
            next(r for r in rows if r["addr"] == victim["addr"]).__setitem__(
                "program", "pd")

        problems = problems_of(registers_edit=relabel)
        self.assertTrue(problems,
                        f"{victim['addr']} re-labelled `pd` was accepted as a "
                        f"member of the main-EC cluster that holds it")
        self.assertIn("so a `main-ec` cluster's", "\n".join(problems))


class TheCorpusTotalCannotTell(unittest.TestCase):
    """Why the per-cluster rule exists beside the total `--self-test` asserts.

    One cluster's `refs` up by one and another's down by one leaves
    `Σ cluster refs == Σ registers refs` exactly where it was -- and the
    `--self-test` oracle that asserts it, one number for the whole file, cannot
    see either edit. So the total is kept as the weaker claim it is rather than
    as a substitute for the rule.
    """

    def test_a_balanced_move_is_invisible_to_the_total_and_red_to_the_rule(self):
        _fields, clusters = rows_of(CLUSTERS)
        cid = one_cluster_with_a_both_member(clusters)
        donor = next(r["cluster_id"] for r in clusters
                     if r["cluster_id"] != cid and r["refs"].isdigit())

        def move(rows):
            up = next(r for r in rows if r["cluster_id"] == cid)
            up["refs"] = str(int(up["refs"]) + 1)
            down = next(r for r in rows if r["cluster_id"] == donor)
            down["refs"] = str(int(down["refs"]) - 1)

        with tempfile.TemporaryDirectory(prefix="cluster-refs-") as tmp:
            clusters_path, registers_path = scratch(tmp, clusters_edit=move)
            problems, _population = proj.check(str(clusters_path),
                                               str(registers_path))
            by_id = {r["cluster_id"]: int(r["refs"])
                     for r in rows_of(registers_path)[1]}
            total = sum(by_id.values())
        self.assertTrue(problems,
                        "a cluster's `refs` was changed by one in each "
                        "direction and the check passed, so the corpus total "
                        "it also asserts is doing the work here")
        # The corpus total is *not* among the refusals -- it still holds, and
        # that is the point of the class.
        self.assertNotIn("do not describe one census", "\n".join(problems))


class TheBothRowIdentities(unittest.TestCase):
    """The two `both`-row identities #713 put in, held corpus-wide.

    Neither is this check's rule, and both are what make the rule's input a
    *split* rather than a second census: without them, a `refs_pd` column that
    stopped being the other half of `refs_main_ec` would leave the per-cluster
    sums still adding up to the total while describing nothing.
    """

    @classmethod
    def setUpClass(cls):
        _fields, registers = rows_of(REGISTERS)
        cls.registers = registers
        cls.both = [r for r in registers if r["program"] == "both"]

    def test_every_row_splits_into_its_two_halves(self):
        # On every row, not only on the `both` ones: a `main-ec` row's `refs_pd`
        # is `0` and its `refs_main_ec` is the whole figure, which is what keeps
        # the columns populated corpus-wide for a `csv.DictReader` consumer.
        for row in self.registers:
            with self.subTest(addr=row["addr"]):
                self.assertEqual(int(row["refs"]),
                                 int(row["refs_main_ec"]) + int(row["refs_pd"]))

    def test_the_two_halves_sum_to_the_census_total(self):
        halves = (sum(int(r["refs_main_ec"]) for r in self.registers),
                  sum(int(r["refs_pd"]) for r in self.registers))
        self.assertEqual(sum(halves), sum(int(r["refs"]) for r in self.registers))

    def test_a_both_row_carries_both_halves(self):
        # The claim that is specific to a `both` row: a split with a zero in one
        # half is a column that stopped counting the other program, and on the
        # unsuffixed total it is invisible.
        self.assertTrue(self.both,
                        "no committed `program=both` row, so nothing here is "
                        "being exercised")
        for row in self.both:
            with self.subTest(addr=row["addr"]):
                self.assertGreater(int(row["refs_main_ec"]), 0)
                self.assertGreater(int(row["refs_pd"]), 0)


if __name__ == "__main__":
    unittest.main()