#!/usr/bin/env python3
"""The refusal contract of `xdata_register_map.py`'s two census flags
(issues #556 and #604).

Each flag carries three claims, and for each it is the last that is held here.
`--no-eq-guard` claims it flips the `==` rejection and nothing else, so the
pre-#178 classifier stays measurable from the committed tree; that is held by
the tool's own `--self-test`, against a literal table, and
`test_xdata_cluster_names.py` was to hold it a second way, by running the census
the flag produces, but it has raised in `setUpClass` since #528 without running
any of its six cases; the write-up says so and leaves the fix named rather than
folded in. `--export-ownership` claims it reads each routine once, from the
export that owns it, and `ec/annotations/xdata-export-ownership.md` 4-5 is the
measurement, held by the tool's own `OWNERSHIP` table. The two refusals were
held by nothing before, for either flag -- the tool's own `--self-test` cannot
hold them, because a flag that is refused with `--self-test` is by definition
not answerable from it.

All four refusals fire in `main()` before the mode dispatch, so reaching them
costs no census pass: no image, no Ghidra, no network, and nothing here touched
hardware. The two accepted runs are regenerations from the same committed text
into a `tempfile.TemporaryDirectory()`.

**The tripwires are the point of `Refusals`, not belt-and-braces.** Asserting
"the committed CSVs are unchanged" alone would also be satisfied by a run that
wrote identical bytes, and the property `main()`'s own comment states is
stronger: the refusal happens *before* any mode runs. So every mode entry point
is replaced with a recorder, and a guard that regressed fails the test cleanly
instead of overwriting the two files the whole tree is keyed to. A test that
could damage the repository on failure would be the wrong place to pin this.

**Not tested, deliberately.** `--check --self-test <flag>` together, for either
flag, is refused by argparse's mutually-exclusive group, but that is testing
argparse, and its exit code is indistinguishable from a guard firing. And no
*third* flag is covered: the two here are the two `main()` carries today, and
`TripwireCoverage` reads the mode dispatch rather than the guards, so a flag
added without its refusals would be a gap this suite could not see.
"""
import ast
import contextlib
import csv
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).parent
EC = HERE.parent
TOOL = HERE / "xdata_register_map.py"
spec = importlib.util.spec_from_file_location("xdata_register_map", TOOL)
xrm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xrm)

# The entry points `main()` dispatches to, in the order it tries them. A
# `--no-eq-guard` or `--export-ownership` run must not reach any of them; the
# tripwires replace all of them so a refusal that moved below the dispatch is
# caught wherever it moved to. Nine rather than the six this suite was written
# against: #566 added the three co-reading modes to the dispatch, and a tripwire
# naming only the old six would have let a relocated guard reach one of the
# three it did not mock. `TripwireCoverage` below keeps the two lists from
# drifting again.
MODES = ("self_test", "threshold_sweep", "co_reading_sweep",
         "co_reading_group_table", "collapse_co_readings", "map_census",
         "reconcile", "check", "write")

# The two flags `main()` guards, and the two refusals each carries. The tripwire
# is already flag-agnostic -- it mocks the same nine entry points either way --
# so the two flags are one table and the cases below loop over it. The guard
# messages are byte-identical apart from the flag name, which is what makes them
# shared constants rather than a string per flag: `main()`'s own comment says the
# two pairs are "the same two refusals, for the same two reasons", and a shared
# fragment makes that a thing a case checks rather than a sentence a reader
# believes. A flag that stopped carrying one of them goes red here.
GUARDED_FLAGS = ("--no-eq-guard", "--export-ownership")
REFUSED_WITH_A_MODE = "cannot be combined with --check or --self-test"
REFUSED_AT_THE_DEFAULTS = "would overwrite the committed census"


def run_main(*argv):
    """(exit code, stdout, stderr) for one `main()` under `argv`.

    `ap.error` raises `SystemExit` rather than returning, so the code is taken
    off the exception and handed back: a refusal is the contract, and pinning
    the spelling (`2` today) would be a false alarm about the property that
    matters if the refusal is ever rewritten as `print(...); return 1`.
    """
    out, err = io.StringIO(), io.StringIO()
    argv = [str(TOOL), *argv]
    with mock.patch.object(sys, "argv", argv), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = xrm.main()
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def committed_census():
    """The two committed census CSVs as bytes, for a byte-identical compare.

    Read through the tool's own `OUT_REGISTERS`/`OUT_CLUSTERS` rather than
    paths spelled out here, so a case follows the defaults if they move.
    """
    return (Path(xrm.OUT_REGISTERS).read_bytes(),
            Path(xrm.OUT_CLUSTERS).read_bytes())


def column_totals(path, column):
    """{addr: `column` total} from a registers CSV.

    One column at a time because the two accepted runs assert opposite signs on
    two different columns -- `AcceptedWrite` sums `write` while
    `AcceptedExportOwnershipWrite` sums `refs` -- and a reader should be able to
    see which is which from the call rather than from a helper named after
    either.
    """
    with open(path, newline="") as f:
        return {r["addr"]: int(r[column]) for r in csv.DictReader(f)}


def cluster_keys(path):
    """The `cluster_key` of every cluster in a clusters CSV.

    Read through the tool's own row reader rather than a local `csv` call, the
    way `committed_census()` reads the defaults: the suite follows the tool's
    idea of a clusters CSV rather than a second one.
    """
    return {r["cluster_key"] for r in xrm.load_cluster_rows(path)}


class TripwireCoverage(unittest.TestCase):
    """`MODES` is the dispatch, read from the tool rather than kept by hand.

    The tripwire's claim is that a refusal which moved below the dispatch
    reaches no mode at all, and that is only true while every entry point is
    mocked. #566 added three co-reading modes to a dispatch this suite had
    enumerated at six, and the gap would have been silent: a run that reached
    `co_reading_sweep` instead of `write` writes nothing, so the refusals below
    would have gone on passing. So the list is read out of `main()`'s own AST
    and a tenth mode fails here rather than going unmocked.
    """

    def test_modes_is_every_entry_point_main_dispatches_to(self):
        # `ast.walk` is breadth-first, which puts the trailing `return
        # write(args)` -- the only one at the function's own level -- first; a
        # NodeVisitor walks the fields in order, so this is source order and
        # matches the order `MODES` claims.
        class Dispatch(ast.NodeVisitor):
            def __init__(self):
                self.names = []

            def visit_Return(self, node):
                if (isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)):
                    self.names.append(node.value.func.id)

        main_fn = next(n for n in ast.walk(ast.parse(TOOL.read_text()))
                       if isinstance(n, ast.FunctionDef) and n.name == "main")
        dispatch = Dispatch()
        dispatch.visit(main_fn)
        self.assertEqual(tuple(dispatch.names), MODES)


class Refusals(unittest.TestCase):
    """Either guarded flag with `--check`, with `--self-test`, or without scratch
    outputs is refused, and the refusal costs the repository nothing.

    Two flags, two refusals each, five cases, and every case loops over
    `GUARDED_FLAGS` -- a `subTest` per flag rather than a second class, because
    the guards differ only in the flag they read and the tripwire is the same
    one either way. Each case still gives the *other* guard nothing to fire on,
    so it tests the guard it is about on both flags. The `--check` and
    `--self-test` cases are the ones that need it: at the default outputs a run
    of those is also caught by the second guard, so a case left at the defaults
    would pass on either guard and a `--check` guard that was moved below the
    dispatch would go unnoticed behind the one still above it. The issue's
    literal invocation -- a flag with `--check` at the defaults -- is refused
    either way, and the third case below is that run with the flag alone.

    The two half-scratch cases are here because the second guard is an `or` --
    a refactor that required *both* outputs to be scratch would otherwise pass
    this suite while still refusing only the runs that were always refused.
    """

    def refuse(self, *argv):
        """Run `main()` with every mode replaced by a recorder, and assert the
        three things a refusal owes: no mode ran, the exit was non-zero, and
        both committed CSVs are byte-identical to just before.
        """
        ran = []
        # The recorder takes the mode's name rather than its arguments: which
        # mode ran is the finding, and an argparse Namespace is not a sentence.
        tripwire = lambda mode: mock.Mock(side_effect=lambda *a, **kw: ran.append(mode))
        patched = [mock.patch.object(xrm, mode, tripwire(mode)) for mode in MODES]
        before = committed_census()
        with contextlib.ExitStack() as stack:
            for patcher in patched:
                stack.enter_context(patcher)
            code, _out, err = run_main(*argv)
        self.assertEqual(ran, [],
                         f"`{' '.join(argv)}` reached {ran} instead of being "
                         "refused before the mode dispatch; the modes are "
                         "mocked, so nothing was written either way")
        self.assertNotEqual(code, 0,
                            f"`{' '.join(argv)}` was not refused, and no mode "
                            f"ran: {err.strip()!r}")
        self.assertEqual(committed_census(), before,
                         f"`{' '.join(argv)}` changed a committed census CSV")
        return code, err

    def test_it_is_refused_with_check(self):
        # `--check`'s whole claim is that the committed CSVs already match a
        # fresh generation; a flag that re-buckets occurrences cannot be
        # answerable from a mode that reports on the guard's own output -- and
        # `--export-ownership` re-buckets just as much, by de-duplicating. The
        # scratch outputs are given so this is the only guard that can fire.
        for flag in GUARDED_FLAGS:
            with self.subTest(flag=flag), \
                    tempfile.TemporaryDirectory(prefix="xdata-refused-") as tmp:
                _code, err = self.refuse(
                    flag, "--check",
                    "--out-registers", os.path.join(tmp, "registers.csv"),
                    "--out-clusters", os.path.join(tmp, "clusters.csv"))
                self.assertIn(REFUSED_WITH_A_MODE, err)

    def test_it_is_refused_with_self_test(self):
        # The same guard, reached the other way round. `ap.error` prints the
        # one message for both, so both cases read the same line; they are two
        # cases because the dispatch offers them as two arguments.
        for flag in GUARDED_FLAGS:
            with self.subTest(flag=flag), \
                    tempfile.TemporaryDirectory(prefix="xdata-refused-") as tmp:
                _code, err = self.refuse(
                    flag, "--self-test",
                    "--out-registers", os.path.join(tmp, "registers.csv"),
                    "--out-clusters", os.path.join(tmp, "clusters.csv"))
                self.assertIn(REFUSED_WITH_A_MODE, err)

    def test_it_is_refused_bare_with_the_default_outputs(self):
        # The hazard: run bare, it writes a census the committed CSVs do not
        # match -- the pre-#178 one for `--no-eq-guard`, the de-duplicated one
        # for `--export-ownership`, which re-keys 35 of the 430 clusters and
        # breaks 5 of the 10 hand names. That is caught, but only afterwards and
        # by other tools -- `--check` is refused with the flag, so it
        # regenerates default and goes red, and so do the citations. The
        # guard's job is to stop the write, not to leave the repository to be
        # noticed afterwards. This is the issue's third combination verbatim,
        # and the only one where a mode would reach the committed paths if the
        # guard were not there.
        for flag in GUARDED_FLAGS:
            with self.subTest(flag=flag):
                _code, err = self.refuse(flag)
                self.assertIn(REFUSED_AT_THE_DEFAULTS, err)

    def test_it_is_refused_with_scratch_registers_only(self):
        # `or`, not `and`: clusters are still on their default here, so the
        # guard must still fire even though one output was given somewhere to
        # write. Nothing is written to the scratch path either -- a refusal
        # that redirected instead of refusing would still be a refusal that
        # does the wrong thing.
        for flag in GUARDED_FLAGS:
            with self.subTest(flag=flag), \
                    tempfile.TemporaryDirectory(prefix="xdata-refused-") as tmp:
                scratch = os.path.join(tmp, "registers.csv")
                self.refuse(flag, "--out-registers", scratch)
                self.assertFalse(os.path.exists(scratch))

    def test_it_is_refused_with_scratch_clusters_only(self):
        # The other half of the same `or`, and it fails the same way.
        for flag in GUARDED_FLAGS:
            with self.subTest(flag=flag), \
                    tempfile.TemporaryDirectory(prefix="xdata-refused-") as tmp:
                scratch = os.path.join(tmp, "clusters.csv")
                self.refuse(flag, "--out-clusters", scratch)
                self.assertFalse(os.path.exists(scratch))

    def test_the_defaults_still_point_into_the_committed_tree(self):
        # The whole hazard is premised on this, for both flags, and it is the
        # one case here that is not per-flag. If the defaults move, the
        # refusals above keep passing while meaning something else -- a bare
        # run of either flag would no longer be a threat to these two files, and
        # both guards' reasons at xdata_register_map.py:3677-3680 and
        # :3687-3697 would be stale.
        self.assertEqual(Path(xrm.OUT_REGISTERS).parent, EC / "annotations")
        self.assertEqual(Path(xrm.OUT_CLUSTERS).parent, EC / "annotations")


class AcceptedWrite(unittest.TestCase):
    """The one invocation that is not refused writes only into the temporary
    directory it was given, and writes something the guard-off flag explains.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="xdata-no-eq-guard-")
        cls.registers = os.path.join(cls.tmp.name, "registers.csv")
        cls.clusters = os.path.join(cls.tmp.name, "clusters.csv")
        cls.before = committed_census()
        # No tripwires: this is the case that has to really write, or the
        # "wrote only into the tempdir" half is vacuous.
        cls.code, _out, cls.err = run_main(
            "--no-eq-guard", "--out-registers", cls.registers,
            "--out-clusters", cls.clusters)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_run_is_accepted(self):
        self.assertEqual(self.code, 0, self.err)

    def test_both_scratch_files_exist(self):
        self.assertTrue(os.path.exists(self.registers), self.registers)
        self.assertTrue(os.path.exists(self.clusters), self.clusters)

    def test_the_committed_census_is_byte_identical_afterwards(self):
        # The issue's "writes only into the TemporaryDirectory": the two files
        # `check_cluster_citations.py` and every `main-ec-NNN` citation in the
        # tree are keyed to come back exactly as they went in.
        self.assertEqual(committed_census(), self.before)

    def test_the_scratch_census_is_not_a_copy_of_the_committed_one(self):
        # "Wrote only into the tempdir" would be indistinguishable from
        # "wrote nothing" if the scratch file could be the committed one. And
        # since #566 regenerated the committed census, this is now also a
        # direct claim that the flag was honoured: with the committed CSV
        # matching a fresh generation, a run that ignored `--no-eq-guard` would
        # reproduce it byte for byte and fail here. The write-column test below
        # is still the load-bearing one, because it survives a tree that has
        # moved since `xdata-06c2-06db-timers.md` §6a measured its figures;
        # this one is the file's existence claim, and a second opinion.
        self.assertNotEqual(Path(self.registers).read_bytes(), self.before[0],
                            "the scratch census is a byte-for-byte copy of the "
                            "committed one, so this run did not measure the "
                            "guard being off")

    def test_the_guard_only_moves_references_into_write(self):
        # Direction, not counts. The guard rejects `==` occurrences, so
        # turning it off can only add writes and cannot remove one -- which is
        # what makes the assertion survive a tree that has moved since
        # `xdata-06c2-06db-timers.md` §6a measured 833 and 210. Those are that
        # page's figures and are re-derivable from the command it prints;
        # pinning them here would make this suite red for an unrelated change.
        off = column_totals(self.registers, "write")
        committed = column_totals(xrm.OUT_REGISTERS, "write")
        self.assertEqual(set(off), set(committed))
        self.assertGreater(sum(off.values()), sum(committed.values()))
        moved = [addr for addr in off if off[addr] != committed[addr]]
        self.assertTrue(moved, "no address's `write` differs, so this run "
                              "did not measure the guard being off")


class AcceptedExportOwnershipWrite(unittest.TestCase):
    """The one `--export-ownership` invocation that is not refused writes only
    into the temporary directory it was given, and de-duplicates rather than
    removing a rejection.

    Every effect case here asserts a *relation* and never a figure, for the
    reason the sibling's does: 9,404 against 14,822 references is
    `xdata-export-ownership.md` §4's, recorded on a committed page, and pinning
    it here would make this suite red for an unrelated re-derivation. What is
    asserted instead is the sign of the relation, both sides of the two
    renumberings, and the one thing the pass must never do.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="xdata-ownership-")
        cls.registers = os.path.join(cls.tmp.name, "registers.csv")
        cls.clusters = os.path.join(cls.tmp.name, "clusters.csv")
        cls.before = committed_census()
        # No tripwires, for the same reason as `AcceptedWrite` and with the same
        # consequence: this is the case that has to really write, or the "wrote
        # only into the tempdir" half is vacuous. The two scratch paths are all
        # that stand between this run and the committed CSVs, which is exactly
        # the property the refusals above pin.
        cls.code, _out, cls.err = run_main(
            "--export-ownership", "--out-registers", cls.registers,
            "--out-clusters", cls.clusters)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_run_is_accepted(self):
        self.assertEqual(self.code, 0, self.err)

    def test_both_scratch_files_exist(self):
        self.assertTrue(os.path.exists(self.registers), self.registers)
        self.assertTrue(os.path.exists(self.clusters), self.clusters)

    def test_the_committed_census_is_byte_identical_afterwards(self):
        # The issue's "writes only into the TemporaryDirectory", and this is
        # what makes the two cases below non-vacuous: if the run had written
        # the committed files instead, "the scratch file is not a copy of the
        # committed one" would be comparing a file with itself.
        self.assertEqual(committed_census(), self.before)

    def test_the_scratch_census_is_not_a_copy_of_the_committed_one(self):
        # The shape `AcceptedWrite` uses, and a sharper second opinion here.
        # The committed census matches a fresh generation on this tree, so a
        # run that ignored `--export-ownership` would reproduce it byte for
        # byte -- the de-duplicated census is 9,404 references against the
        # committed 14,822, which is not a byte for byte anything.
        self.assertNotEqual(Path(self.registers).read_bytes(), self.before[0],
                            "the scratch census is a byte-for-byte copy of the "
                            "committed one, so this run did not measure the "
                            "pass being on")

    def test_the_pass_only_removes_references(self):
        # Direction, and the sign is the opposite of `AcceptedWrite`'s, which
        # is why that case's `assertGreater` is not reused here: the `==` guard
        # rejects occurrences, so turning it off can only add writes, while
        # this pass reads one routine once instead of 42 times and so can only
        # drop references. Neither sign is a count, and both survive a
        # re-derivation that a pinned figure would not.
        dedup = column_totals(self.registers, "refs")
        committed = column_totals(xrm.OUT_REGISTERS, "refs")
        self.assertLess(sum(dedup.values()), sum(committed.values()))
        moved = [addr for addr in dedup if dedup[addr] != committed[addr]]
        self.assertTrue(moved, "no address's `refs` differs, so this run "
                              "did not measure the pass being on")

    def test_no_address_is_lost(self):
        # The one thing the pass must never do. `OWNERSHIP["lost"]` pins it
        # from the tool's own oracle, and `--self-test` cannot be the route
        # here for the reason the flag is refused with `--self-test` in the
        # first place: the check and the flag cannot be combined. So the
        # relation is derived from the two CSVs, which is what the empty `lost`
        # set says anyway. §4's correction records the one grouping that did
        # lose `0x05E0`, and losing it would fail here.
        self.assertEqual(set(column_totals(self.registers, "refs")),
                         set(column_totals(xrm.OUT_REGISTERS, "refs")),
                         "the pass dropped or invented an address, which is "
                         "what OWNERSHIP['lost'] pins and must stay empty")

    def test_cluster_keys_are_renumbered_rather_than_rekeyed(self):
        # Two-sided on purpose, and both halves are load-bearing. A committed
        # key that survives says the pass re-keyed 35 clusters rather than
        # every one of them; a committed key that goes missing says the flip
        # is a tree-wide renumbering and not a no-op. The 35 of 430 that break
        # and the 37 that are new are `xdata-export-ownership.md` §5's figures
        # and `OWNERSHIP`'s, and they stay there.
        scratch, committed = cluster_keys(self.clusters), cluster_keys(xrm.OUT_CLUSTERS)
        self.assertTrue(committed - scratch,
                        "every committed cluster_key survives, so this run did "
                        "not measure the renumbering")
        self.assertTrue(scratch & committed,
                        "no committed cluster_key survives, so the pass re-keyed "
                        "the census wholesale rather than renumbering it")

    def test_some_hand_cluster_names_break_and_some_survive(self):
        # The same two-sided relation over the ten hand names, read through the
        # tool's own `load_cluster_names()` rather than a spelled-out path. Five
        # of the ten break, and which five is not pinned: §5 names
        # `counter-sweep` (`k733222e83898`) as `main-ec-002`'s own key and one
        # that does not survive as a single cluster at all, but a membership
        # claim would make this suite red for an unrelated re-derivation -- the
        # same trade `test_the_scratch_census_is_not_a_copy_of_the_committed_one`
        # makes against §6a's figures.
        names, scratch = set(xrm.load_cluster_names()), cluster_keys(self.clusters)
        self.assertTrue(names - scratch,
                        "every hand-named cluster_key survives the pass, so "
                        "this run did not measure the renumbering")
        self.assertTrue(names & scratch,
                        "no hand-named cluster_key survives, so the pass re-keyed "
                        "the census wholesale rather than renumbering it")


if __name__ == "__main__":
    unittest.main()
