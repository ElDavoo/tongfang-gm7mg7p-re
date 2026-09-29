#!/usr/bin/env python3
"""The refusal contract of `xdata_register_map.py`'s two census flags
(issues #556 and #604).

Each flag carries three claims, and for each it is the last that is held here.
`--no-eq-guard` claims it flips the `==` rejection and nothing else, so the
pre-#178 classifier stays measurable from the committed tree; that is held by
the tool's own `--self-test`, against a literal table, and
`test_xdata_cluster_names.py` was to hold it a second way, by running the census
the flag produces, and could not: it raised in `setUpClass` from #528 until
issue #753, which dropped the copy-and-patch recipe its error message named and
put this flag in its place. The six cases it could not run now run, and a
seventh was added beside them that pins the census to the figures
`xdata-06c2-06db-timers.md` §6a publishes -- the census-identity claim, where
`AcceptedWrite` below holds direction on purpose so that it survives an
unrelated re-derivation. The sentence that said otherwise, "but it has raised in
`setUpClass` since #528 without running any of its six cases", is corrected
here beside itself per `../../docs/findings.md` §4a-4d rather than deleted; the
write-up named that fix and left it unfolded.
`--export-ownership` claims it reads each routine once, from the
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

# The `main()` shapes `TripwireCoverage` pins its readers on, kept as
# strings rather than written out per case so the reading and the pin cannot
# drift apart. None of them is reachable from the committed dispatch, which is
# the point: the real one dispatches all nine modes as `return`, so only a
# synthetic source can show that a reader stopped depending on that shape.
STATEMENT_DISPATCH = ("def main():\n"
                      "    if args.demo_mode:\n"
                      "        demo_mode(args)\n"
                      "        return 0\n")
ASSIGNMENT_DISPATCH = "def main():\n    rc = demo_mode(args)\n    return rc\n"
WITH_DISPATCH = ("def main():\n"
                 "    with demo_mode(args):\n"
                 "        pass\n"
                 "    return 0\n")
COMPREHENSION_DISPATCH = "def main():\n    xs = [demo_mode(a) for a in y]\n    return 0\n"
# `demo_mode` and not `write`, and the difference is the whole of issue #694: a
# tenth mode is by definition not in `MODES`, so pinning the reader on a name
# that is in it measures a filter the reader already had rather than the path
# that fails. `xrm` is not a name either reader resolves, so the terminal is the
# whole of what is under test.
ATTRIBUTE_DISPATCH = "def main():\n    return xrm.demo_mode(args)\n"

# The attribute calls the committed `main()` makes, which is the whole of the
# benign set, measured off that `main()`'s own AST rather than named from a
# reading of it. It is a maintained list and it is wrong the first time it is
# written down -- it is, against the four names the issue proposed, which are
# all here but for `ArgumentParser` and `parse_args` -- so it is held as a
# partition in both directions by the case that owns the name, and
# `test_the_benign_set_names_nothing_the_tool_defines` holds the other failure
# a list has: widening it to cover a name the tool itself defines.
BENIGN_ATTRIBUTES = frozenset({
    "ArgumentParser",                 # `argparse.ArgumentParser(...)`
    "add_argument",                   # every flag, on the parser and the group
    "add_mutually_exclusive_group",   # the group carrying the two guarded flags
    "error",                          # the four refusal guards
    "join",                           # the default `--registers` path
    "parse_args",                     # `ap.parse_args()`
})

# The dispatch positions `TripwireCoverage`'s docstring names, keyed by the
# words it uses for each. A key is the `subTest` label, so a failure names the
# phrase the claim was written in rather than an index into a tuple.
DISPATCH_POSITIONS = {
    "assignment right-hand side": ASSIGNMENT_DISPATCH,
    "`with` header": WITH_DISPATCH,
    "bare comprehension": COMPREHENSION_DISPATCH,
}


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


def main_of(source):
    """The `main()` of `source`, which both dispatch readers below start from."""
    return next(n for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.FunctionDef) and n.name == "main")


def dispatch_names(source):
    """The bare-name calls `main()` in `source` dispatches to, in source order.

    A call is recorded on the way in and the walk does not descend past it into
    its arguments, so a call that is only *another call's* argument is that
    callee's business and not `main()`'s dispatch. That is what keeps the two
    `list(...)` defaults at `xdata_register_map.py:3634` and `:3637` out: they
    are real, they are bare names, and a reader collecting every one of them
    records `list` twice on top of the nine. The attribute calls fall out for
    free under the `ast.Name` restriction, with no exclusion list to maintain --
    and a name-based list is what the issue proposed, and it is wrong the first
    time it is written down for exactly those two calls.

    A NodeVisitor walks the fields in order, so this is pre-order, which is
    source order for the flat `if args.*` chain the committed dispatch is. A
    mode reached through a wrapper (`return run(demo_mode(args))`) records the
    wrapper rather than the mode, and that is correct rather than a gap: the
    entry point `main()` dispatches to has changed, so `MODES` has to change
    with it and a tenth name turning up is the coverage change firing.
    """
    class Dispatch(ast.NodeVisitor):
        def __init__(self):
            self.names = []

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                self.names.append(node.func.id)
            # Deliberately no `generic_visit`: see the docstring.

    dispatch = Dispatch()
    dispatch.visit(main_of(source))
    return dispatch.names


def attribute_calls(source):
    """Every attribute call `main()` in `source` makes, terminal names, sorted.

    Unfiltered, and that is the point: there is no `MODES` in here, so the set
    this returns does not move when a mode is added. The reader it replaces
    filtered by `call.func.attr in MODES`, which is the one filter a tenth mode
    cannot pass -- it is a tenth because it is not in `MODES`, so it was dropped
    before the set was built and the boundary was green for exactly the case it
    exists to catch.

    It uses `ast.walk` rather than the visitor `dispatch_names` needs, because
    a full descent is right here: the `list(...)` defaults nested inside
    `ap.add_argument(...)` are bare names, not attributes, so descending costs
    this reader nothing that the positional rule was built to keep out. There
    is no ordering property to hold either, and the result is sorted so a
    failure names a set rather than a position.
    """
    return sorted({call.func.attr for call in ast.walk(main_of(source))
                   if isinstance(call, ast.Call)
                   and isinstance(call.func, ast.Attribute)})


def module_level_names(source):
    """The names `source` binds at module level, sorted.

    The derived half of the attribute rule, and it is the half a maintained
    list cannot argue with. The rule is: *an attribute call in `main()` is
    suspicious if and only if its terminal name is bound at module level in the
    tool's own source*, because that is what a mode is -- a top-level `def` in
    `xdata_register_map.py` that `main()` dispatches to. Measured on the
    committed tool, the rule separates the two sets cleanly: no name in
    `BENIGN_ATTRIBUTES` is bound at module level, and every name in `MODES` is.
    So a maintainer who widens the benign set to silence a red has to add a name
    the tool itself defines, and this is what says so.

    Only the tool's own top-level bindings count. The walk is over
    `ast.parse(source).body` and does not descend, so a `def` nested in a
    top-level `if` is not among them and neither is a name bound inside a
    function. A name the source reaches under a spelling it does not bind is not
    covered either, and nothing here claims it is.
    """
    bound = set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            bound.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            # `import a.b` binds `a`, and `import a.b as c` binds `c`.
            bound.update((a.asname or a.name).split(".")[0] for a in node.names)
    return sorted(bound)


def mode_attributes(source):
    """The attribute calls in `main()` of `source` that are not benign, sorted.

    The other half of the boundary `dispatch_names` cannot close by itself: a
    mode dispatched as `return xrm.demo_mode(args)` is not a bare-name call, so
    that reader records nothing for it. This one is a *residue* --
    `attribute_calls` less the committed tree's own `BENIGN_ATTRIBUTES` -- so
    it reports every attribute call the benign set does not account for, whether
    or not it could be a mode. A tenth mode reached that way is a name the tool
    defines, so it is in the residue, and it fails here loudly rather than
    being missed quietly.

    It is the residue rather than `attribute_calls` under a different name so
    that a red here says *which* call: the failure carries the offending
    terminal name, which is the difference between a reader that reports and
    one that answers `[]`.
    """
    return sorted(set(attribute_calls(source)) - BENIGN_ATTRIBUTES)


class TripwireCoverage(unittest.TestCase):
    """`MODES` is the dispatch, read from the tool rather than kept by hand.

    The tripwire's claim is that a refusal which moved below the dispatch
    reaches no mode at all, and that is only true while every entry point is
    mocked. #566 added three co-reading modes to a dispatch this suite had
    enumerated at six, and the gap would have been silent: a run that reached
    `co_reading_sweep` instead of `write` writes nothing, so the refusals below
    would have gone on passing. So the list is read out of `main()`'s own AST,
    by `dispatch_names`, on its own stated rule: every bare-name call in
    `main()` that is not another call's argument -- which is an assignment
    right-hand side, a `with` header and a bare comprehension as much as a
    statement or a `return` -- and a tenth mode fails here rather than going
    unmocked. The enumeration is a claim the suite holds rather than one a
    reader has to take on trust: `DISPATCH_POSITIONS` carries a source for each
    of the three the committed `main()` cannot show, keyed by the words above,
    and the case below walks it.

    Statement position is in that sentence because it was not, until issue
    #608: the reader then implemented `visit_Return`, and a tenth mode reached
    as `demo_mode(args); return 0` landed in neither the recorded list nor
    `MODES`, so every case here stayed green with the mode unmocked. The one
    shape left out is a mode dispatched through an attribute, and
    `mode_attributes` asserts against it rather than leaving it to this
    docstring to promise.
    """

    def test_modes_is_every_entry_point_main_dispatches_to(self):
        self.assertEqual(tuple(dispatch_names(TOOL.read_text())), MODES)

    def test_a_mode_dispatched_as_a_statement_is_collected_too(self):
        # The regression pin, and it is on synthetic source because the real
        # `main()` dispatches all nine as a `return`: an edit narrowing
        # `dispatch_names` back to `visit_Return` would leave the case above
        # green. This is the issue's shape verbatim.
        self.assertEqual(dispatch_names(STATEMENT_DISPATCH), ["demo_mode"])

    def test_every_position_the_docstring_names_is_collected_too(self):
        # The rest of that sentence, and on synthetic source for the same
        # reason the case above is: the committed `main()` dispatches all nine
        # modes as a `return`, so the committed tree cannot show a reader
        # stopped reaching the other positions. Equality, not the membership
        # the attribute reader needs -- each source carries exactly one
        # bare-name call, so this says the reader records that one and no
        # other, where a membership check would pass a reader that
        # over-collected. The committed-dispatch case is what holds the reader
        # against over-collection on a real `main()`.
        for position, source in DISPATCH_POSITIONS.items():
            with self.subTest(position=position):
                self.assertEqual(dispatch_names(source), ["demo_mode"])

    def test_the_dispatch_reaches_no_mode_as_an_attribute(self):
        # The real tree, against the assertion the docstring claims for it. The
        # message carries the residue rather than a bare `Lists differ`: the
        # whole of issue #694 is that this reader used to answer `[]` to the
        # one call it existed to catch, so a failure that does not say which
        # name would leave the reader a step from that again.
        residue = mode_attributes(TOOL.read_text())
        self.assertEqual(
            residue, [],
            f"main() reaches {residue} as an attribute, and the benign calls "
            f"are {sorted(BENIGN_ATTRIBUTES)}: a name outside them is a call "
            "into the tool's own module, which is what a mode is")

    def test_a_mode_reached_as_an_attribute_is_caught_by_the_other_reader(self):
        # So the case above is a property of the committed dispatch and not a
        # helper that would answer `[]` to anything. `dispatch_names` records
        # nothing for this shape -- that is the whole reason `mode_attributes`
        # exists, and pinning it here keeps the residual boundary stated as a
        # measurement rather than as a sentence a reader has to trust.
        #
        # `demo_mode`, and not `write`: the reader used to filter by `MODES`, so
        # a source naming a tenth mode was dropped before the set was built and
        # this case measured the filter rather than the path that fails. The
        # assertion below is the precondition that says which path is under
        # test, and without it a `write` here would have gone on passing.
        self.assertNotIn("demo_mode", MODES)
        self.assertEqual(dispatch_names(ATTRIBUTE_DISPATCH), [])
        self.assertEqual(mode_attributes(ATTRIBUTE_DISPATCH), ["demo_mode"])

    def test_the_benign_attribute_set_is_exactly_the_committed_one(self):
        # `BENIGN_ATTRIBUTES` is a maintained list, and a maintained list is
        # wrong the first time it is written down: it was written two names
        # short against the committed `main()`. Both directions are asserted
        # because each has its own failure. A new attribute call nobody
        # classified is the one that matters and is the residue; a name nothing
        # calls is dead weight that hides a later widening. A set, not a count,
        # because neither side is a number any merge has to edit.
        committed = set(attribute_calls(TOOL.read_text()))
        benign = set(BENIGN_ATTRIBUTES)
        self.assertEqual(
            committed - benign, set(),
            f"main() reaches {sorted(committed - benign)} as an attribute and "
            "BENIGN_ATTRIBUTES does not account for it: add the name, or read "
            "the call as a defect")
        self.assertEqual(
            benign - committed, set(),
            f"BENIGN_ATTRIBUTES names {sorted(benign - committed)}, which "
            "main() does not reach: a name nothing calls cannot be benign, and "
            "carrying it only widens the residue's blind spot")

    def test_the_benign_set_names_nothing_the_tool_defines(self):
        # The derived guard, and the failure a list has that the partition
        # above cannot see. Adding `demo_mode` to `BENIGN_ATTRIBUTES` would make
        # the residue `[]` for a tenth mode forever, and the partition case
        # would stay green with it; this is the case that goes red instead,
        # because `demo_mode` is a name the tool defines at module level and a
        # mode is exactly that.
        module_level = set(module_level_names(TOOL.read_text()))
        self.assertEqual(
            sorted(BENIGN_ATTRIBUTES & module_level), [],
            f"BENIGN_ATTRIBUTES covers {sorted(BENIGN_ATTRIBUTES & module_level)}, "
            "which the tool defines at module level: an attribute call whose "
            "terminal name the tool binds is a call into the tool's own module, "
            "and the benign set is for the calls that are not")
        # And the non-vacuity control, in the spirit of a checker that located
        # nothing having to say so rather than exit 0: the intersection above is
        # empty on this tree because the two sets separate, not because the
        # reader found nothing. Every `MODES` name *is* a module-level binding.
        self.assertEqual(
            sorted(set(MODES) - module_level), [],
            f"MODES names {sorted(set(MODES) - module_level)}, which the tool "
            "does not bind at module level: the guard above is then holding an "
            "empty intersection for want of a subject, and the reader it uses is "
            "not reaching the tool's own bindings")

    def test_a_dispatched_name_the_tool_defines_is_a_suspect(self):
        # The rule the derived guard states, in both directions, on synthetic
        # source -- the committed `main()` cannot show either, because it makes
        # no attribute call the tool does not already define. The same call in a
        # tool that defines `demo_mode` and in one that does not, so the case is
        # a statement of what makes an attribute call suspicious rather than a
        # restatement that the committed tree happens to satisfy.
        defining = ("def demo_mode(args):\n    return 0\n\n\n"
                    "def main():\n    return xrm.demo_mode(args)\n")
        not_defining = "def main():\n    return xrm.demo_mode(args)\n"
        for tool_defines_it, source, expected in (
                (True, defining, ["demo_mode"]), (False, not_defining, [])):
            with self.subTest(tool_defines_the_name=tool_defines_it):
                self.assertEqual(mode_attributes(source), ["demo_mode"])
                self.assertEqual(
                    sorted(set(mode_attributes(source))
                           & set(module_level_names(source))),
                    expected,
                    "a residue is a suspect only where the tool binds the name "
                    "at module level")


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
