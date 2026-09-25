#!/usr/bin/env python3
"""The `--no-eq-guard` refusal contract (issue #556).

The flag carries three claims. The first -- that it flips the `==` rejection
and nothing else, so the pre-#178 classifier stays measurable from the
committed tree -- is held by the tool's own `--self-test`, against a literal
table. `test_xdata_cluster_names.py` was to hold it a second way, by running
the census the flag produces, but it has raised in `setUpClass` since #528
without running any of its six cases; the write-up says so and leaves the fix
named rather than folded in. This suite holds the other two claims, the
refusals, which nothing held before -- the tool's own `--self-test` cannot,
because a flag that is refused with `--self-test` is by definition not
answerable from it.

Both refusals fire in `main()` before the mode dispatch, so reaching them costs
no census pass: no image, no Ghidra, no network, and nothing here touched
hardware. The one accepted run is a regeneration from the same committed text
into a `tempfile.TemporaryDirectory()`.

**The tripwires are the point of `Refusals`, not belt-and-braces.** Asserting
"the committed CSVs are unchanged" alone would also be satisfied by a run that
wrote identical bytes, and the property `main()`'s own comment states is
stronger: the refusal happens *before* any mode runs. So every mode entry point
is replaced with a recorder, and a guard that regressed fails the test cleanly
instead of overwriting the two files the whole tree is keyed to. A test that
could damage the repository on failure would be the wrong place to pin this.

**Not tested, deliberately.** `--check --self-test --no-eq-guard` together is
refused by argparse's mutually-exclusive group, but that is testing argparse,
and its exit code is indistinguishable from a guard firing.
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
# `--no-eq-guard` run must not reach any of them; the tripwires replace all of
# them so a refusal that moved below the dispatch is caught wherever it moved
# to. Nine rather than the six this suite was written against: #566 added the
# three co-reading modes to the dispatch, and a tripwire naming only the old six
# would have let a relocated guard reach one of the three it did not mock.
# `TripwireCoverage` below keeps the two lists from drifting again.
MODES = ("self_test", "threshold_sweep", "co_reading_sweep",
         "co_reading_group_table", "collapse_co_readings", "map_census",
         "reconcile", "check", "write")


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


def write_totals(path):
    """{addr: write references} from a registers CSV."""
    with open(path, newline="") as f:
        return {r["addr"]: int(r["write"]) for r in csv.DictReader(f)}


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
    """`--no-eq-guard` with `--check`, with `--self-test`, or without scratch
    outputs is refused, and the refusal costs the repository nothing.

    Two refusals, five cases, and each case gives the *other* guard nothing to
    fire on so it tests the guard it is about. The `--check` and `--self-test`
    cases are the ones that need it: at the default outputs a run of those is
    also caught by the second guard, so a case left at the defaults would pass
    on either guard and a `--check` guard that was moved below the dispatch
    would go unnoticed behind the one still above it. The issue's literal
    invocation -- `--no-eq-guard --check` at the defaults -- is refused either
    way, and the third case below is that run with the flag alone.

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
        # answerable from a mode that reports on the guard's own output. The
        # scratch outputs are given so this is the only guard that can fire.
        with tempfile.TemporaryDirectory(prefix="xdata-refused-") as tmp:
            _code, err = self.refuse(
                "--no-eq-guard", "--check",
                "--out-registers", os.path.join(tmp, "registers.csv"),
                "--out-clusters", os.path.join(tmp, "clusters.csv"))
        self.assertIn("cannot be combined with --check or --self-test", err)

    def test_it_is_refused_with_self_test(self):
        # The same guard, reached the other way round. `ap.error` prints the
        # one message for both, so both cases read the same line; they are two
        # cases because the dispatch offers them as two arguments.
        with tempfile.TemporaryDirectory(prefix="xdata-refused-") as tmp:
            _code, err = self.refuse(
                "--no-eq-guard", "--self-test",
                "--out-registers", os.path.join(tmp, "registers.csv"),
                "--out-clusters", os.path.join(tmp, "clusters.csv"))
        self.assertIn("cannot be combined with --check or --self-test", err)

    def test_it_is_refused_bare_with_the_default_outputs(self):
        # The hazard: run bare, it writes the pre-#178 census over
        # `xdata-registers.csv` and `xdata-clusters.csv`. That is caught, but
        # only afterwards and by other tools -- `--check` is refused with the
        # flag, so it regenerates guard-on and goes red, and so do the
        # citations. The guard's job is to stop the write, not to leave the
        # repository to be noticed afterwards. This is the issue's third
        # combination verbatim, and the only one where a mode would reach the
        # committed paths if the guard were not there.
        _code, err = self.refuse("--no-eq-guard")
        self.assertIn("would overwrite the committed census", err)

    def test_it_is_refused_with_scratch_registers_only(self):
        # `or`, not `and`: clusters are still on their default here, so the
        # guard must still fire even though one output was given somewhere to
        # write. Nothing is written to the scratch path either -- a refusal
        # that redirected instead of refusing would still be a refusal that
        # does the wrong thing.
        with tempfile.TemporaryDirectory(prefix="xdata-refused-") as tmp:
            scratch = os.path.join(tmp, "registers.csv")
            self.refuse("--no-eq-guard", "--out-registers", scratch)
            self.assertFalse(os.path.exists(scratch))

    def test_it_is_refused_with_scratch_clusters_only(self):
        # The other half of the same `or`, and it fails the same way.
        with tempfile.TemporaryDirectory(prefix="xdata-refused-") as tmp:
            scratch = os.path.join(tmp, "clusters.csv")
            self.refuse("--no-eq-guard", "--out-clusters", scratch)
            self.assertFalse(os.path.exists(scratch))

    def test_the_defaults_still_point_into_the_committed_tree(self):
        # The whole hazard is premised on this. If the defaults move, the
        # refusals above keep passing while meaning something else -- a bare
        # `--no-eq-guard` run would no longer be a threat to these two files,
        # and the guard's reason at xdata_register_map.py:3605-3608 would be stale.
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
        off = write_totals(self.registers)
        committed = write_totals(xrm.OUT_REGISTERS)
        self.assertEqual(set(off), set(committed))
        self.assertGreater(sum(off.values()), sum(committed.values()))
        moved = [addr for addr in off if off[addr] != committed[addr]]
        self.assertTrue(moved, "no address's `write` differs, so this run "
                              "did not measure the guard being off")


if __name__ == "__main__":
    unittest.main()
