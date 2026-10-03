#!/usr/bin/env python3
"""`census_shape`'s flag set is derived from the tool, not kept beside it (#882).

`census_shape()` is the predicate that decides whether a carry line is a
re-key request, and #851 built it by naming the flags that put a run's cluster
ids off the committed census. `test_xdata_carry_notice.py` holds that each of
those is named and in `main()`'s declaration order. Neither holds that the list
is **complete**, and completeness is the whole claim: a fourth flag reaching the
clustering changes no line of `census_shape`, so a carry on a run whose ids are
off the anchor goes back to reading *"-- re-key
`annotations/xdata-cluster-names.csv` if the name moved"* -- #851's bug,
restored by an edit that looks like an improvement.

So both sides of that claim are read out of `xdata_register_map.py`'s own AST
and compared here. The derived side walks `generate()`'s call closure and
collects every `args.<name>` it can reach; the named side is `census_shape`'s
own `args` reads. **Neither is a set held in this file** -- not even the
expected three -- because a set written down here is a third place for the
claim to live, and the whole point is that the tool and this suite cannot drift.

`--no-writer-axis` gets the other half. It is declared for the whole parser and
read only by the two modes that can use it, so before this change every other
mode parsed it and ignored it: `--check --no-writer-axis` exited 0 with stdout
and stderr byte-identical to `--check`. `main()` now refuses it outside those
two modes, and the *pair* is derived here from the same AST rather than written
into the guard, so a third mode reaching `args.no_writer_axis` turns the guard's
own condition red.

Reading committed text only. `ast.parse` over the tool, plus `main()` driven
in-process with every mode entry point replaced by a recorder -- so a refusal is
observed to happen *before* the dispatch, and a census pass is never run. No
image, no Ghidra, no network, no laptop, no Windows. That is deliberate rather
than incidental: the property is a relation between two sets of names, and a
census run would cost the most and settle the least.
"""
import ast
import contextlib
import functools
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).parent
EC = HERE.parent
TOOL = HERE / "xdata_register_map.py"
spec = importlib.util.spec_from_file_location("xdata_register_map", TOOL)
xrm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xrm)

SOURCE = TOOL.read_text()

# The namespace both readers look under, `args.<name>`: the shape
# `census_shape` writes in code and the shape `main()` binds `parse_args()` to.
# Spelled once so the injection helper and the recorders below cannot drift from
# the readers; the readers themselves take it from `namespace_of` and do not
# depend on it.
NAMESPACE = "args"

# The flag `main()`'s fifth guard is about, under the name the parser binds it
# to. One spelling, because `guard_accepts` needs the dest to find the guard and
# `flag_readers` needs it to find the readers -- and a second spelling would let
# the guard and the reader drift apart quietly, which is the failure this suite
# exists to catch wearing a different hat.
WRITER_AXIS = "no_writer_axis"

# The two reads the derivation subtracts, and why they are the only two: they
# decide where a run *writes*, not what it says, so a run carrying either
# clusters exactly as a default run does and naming it would put a flag on a
# carry line that never moved a key -- the overclaim `census_shape` exists to
# stop, in the other direction. Subtracted rather than ignored because they are
# exactly what `outputs()` reads; `TheExclusion` holds both halves of that.
OUTPUT_PATHS = frozenset({"out_registers", "out_clusters"})

# A derived flag `census_shape` deliberately does not name, mapped to the reason
# it does not. Empty on the committed tree, and the emptiness is not the claim:
# `TheNegativeControls` exempts a real injected flag and shows what recording a
# difference buys and what omitting the reason costs. A difference left out of
# here fails as a mismatch, which is the safe direction -- an omission goes red.
EXEMPT = {}

# The dest an injection carries, spelled once because three cases share it and a
# fourth spelling would be a fourth place to look when one of them goes red.
INJECTED = "an_injected_flag"

# argparse's actions that take no value, for `takes_a_value`. Copied rather than
# imported for the reason `test_readme_suite_table.py` gives for its two regexes:
# a reader reaching into a sibling for the standard library's rules would be a
# reader whose subject is the sibling.
NO_VALUE_ACTIONS = frozenset({
    "store_true", "store_false", "store_const", "append_const", "count",
    "help", "version",
})


@functools.lru_cache(maxsize=None)
def main_of(source):
    """`main()`'s `FunctionDef`, the root every reader below starts from.

    Cached on the source, and the reason is measurable rather than tidiness: the
    cases below re-derive the same sets over a five-thousand-line source, and a
    reader that re-parsed it per lookup made a suite that needs no census take
    longer to run than most that do.
    """
    return next(n for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.FunctionDef) and n.name == "main")


@functools.lru_cache(maxsize=None)
def functions(source):
    """{name: `FunctionDef`} for every module-level `def` in `source`.

    Cached for the reason `main_of` is.

    Module level only, and the walk is over `ast.parse(source).body`: a `def`
    nested in a top-level `if` is not among them, and neither is a name bound
    inside a function. That is a limit rather than a claim -- a flag read out of
    a nested closure is not covered here, and nothing in this file says it is.
    """
    return {node.name: node for node in ast.parse(source).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def namespace_of(source):
    """The name `main()` binds `parse_args()` to, so no reader assumes `args`.

    Read off the assignment rather than written above, for the reason
    `test_xdata_register_map.py`'s `guarded_flags` reads the same thing: a
    reader keyed to a spelling the tool stops using silently reaches nothing,
    and a case comparing two empty sets passes on that.
    """
    return next(
        (target.id for node in ast.walk(main_of(source))
         if isinstance(node, ast.Assign) for target in node.targets
         if isinstance(target, ast.Name) and isinstance(node.value, ast.Call)
         and isinstance(node.value.func, ast.Attribute)
         and node.value.func.attr == "parse_args"), None)


def bare_callees(fn):
    """Every name `fn` calls, descending into call arguments.

    Descending is the opposite of what `test_xdata_register_map.py`'s
    `dispatch_names` does, and deliberately so. That reader is enumerating an
    entry-point *dispatch*, where a call that is only another call's argument is
    the callee's business; here the question is what a flag can *reach*, and a
    module-level function reached as an argument is reachable all the same.
    Measured on the committed tool the two rules disagree: `generate()` calls
    `name_clusters(..., load_cluster_rows(...), load_cluster_names())`, and
    under a no-descent rule those two are invisible along with the several more
    reachable only through them. A blind spot is the one failure this suite
    exists to close, so the rule that closes it is the one taken -- and a reader
    that over-collects stays diagnosable, because `derived_flags` reports which
    function each flag was read in.
    """
    found = []

    class Callees(ast.NodeVisitor):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                found.append(node.func.id)
            self.generic_visit(node)

    Callees().visit(fn)
    return found


def closure(source, root="generate"):
    """`root`'s transitive closure over module-level defs, sorted.

    Bare-name callees only, and only where the name is a module-level binding of
    `source`. A method reached as `self.foo` is not followed: the tool's modes
    are top-level functions, and a reader that chased attributes would follow
    `os.path.join` into the standard library.
    """
    defined = functions(source)
    seen, pending = set(), [root]
    while pending:
        name = pending.pop(0)
        if name in seen or name not in defined:
            continue
        seen.add(name)
        pending.extend(callee for callee in bare_callees(defined[name])
                       if callee in defined)
    return sorted(seen)


def args_reads(node, namespace):
    """The `<namespace>.<name>` reads inside `node`, as a set of dests."""
    return {n.attr for n in ast.walk(node)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == namespace}


def derived_flags(source, exclude=OUTPUT_PATHS, namespace=None):
    """{dest: frozenset(function names)} for every `args` read in `generate()`'s
    closure, less `exclude`.

    The dict rather than a bare set is what makes an over-collect diagnosable: a
    failure names the flag *and* the function it was read in, so a future helper
    taking `args` for an unrelated reason is a one-line fix rather than a
    puzzle.
    """
    ns = namespace or namespace_of(source)
    defined, out = functions(source), {}
    for name in closure(source):
        for dest in args_reads(defined[name], ns):
            if dest in exclude:
                continue
            out.setdefault(dest, set()).add(name)
    return {dest: frozenset(readers) for dest, readers in out.items()}


def effective(derived, exempt=EXEMPT):
    """`derived` less the exemptions that carry a reason.

    An exemption whose reason is empty or whitespace is **not** subtracted, so
    the difference fails the comparison instead of passing quietly. The reason is
    the whole content of an entry -- it is what a later reader reads to know the
    difference is deliberate -- and an entry without one has recorded nothing,
    which is a difference smuggled rather than recorded.
    """
    return {dest: readers for dest, readers in derived.items()
            if not exempt.get(dest, "").strip()}


def named_flags(source, namespace=None):
    """The dests `census_shape` itself reads, which is all it can name.

    Read from the function rather than kept, and read as *reads* rather than as
    the list it emits: a `census_shape` that gained a flag would otherwise have
    to be taught its own name here as well as in the tool. The emitted list is
    held by `test_xdata_carry_notice.py`, character for character, so the two
    halves of the claim live in two suites and each is a test rather than a copy.
    """
    ns = namespace or namespace_of(source)
    return args_reads(functions(source)["census_shape"], ns)


def injecting(source, function, attribute, namespace=NAMESPACE):
    """`source` with one more `<namespace>.<attribute>` read in `function`.

    An `ast.unparse` round trip rather than a text edit, so the statement lands
    inside the parsed body of the named function however that function happens
    to be spelled -- a rename, a re-wrap or a re-indent cannot silently move the
    injection somewhere inert, which is the failure mode a source-level
    `str.replace` has and the reason this cannot be one.
    """
    tree = ast.parse(source)
    target = next(node for node in tree.body
                  if isinstance(node, ast.FunctionDef) and node.name == function)
    target.body.append(ast.Expr(value=ast.Attribute(
        value=ast.Name(id=namespace, ctx=ast.Load()),
        attr=attribute, ctx=ast.Load())))
    return ast.unparse(tree)


def dispatch_modes(source):
    """The mode entry points `main()` returns into, in source order.

    Read rather than kept, and that is the point: the tripwire in `refuse` has
    to mock every entry point, and a tuple that missed one would leave a mode
    able to run a real census while a case believed it could not. One level of
    nesting, because `main()` is a flat `if <ns>.<mode>: return <mode>(<ns>)`
    chain and a `return` inside a comprehension in some future guard is not a
    dispatch.
    """
    found = []
    for node in main_of(source).body:
        statements = node.body if isinstance(node, ast.If) else [node]
        for stmt in statements:
            if (isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Name)):
                found.append(stmt.value.func.id)
    return found


def dispatch_dests(source, namespace=None):
    """{mode: {dests `main()` reaches it under}} for the dispatch.

    The other half of `dispatch_modes`, and what turns a *function that reads a
    flag* into the *modes* the flag is accepted in: a refusal is written in
    `main()`'s namespace and the two spellings are not the same set until this
    maps one to the other.
    """
    ns = namespace or namespace_of(source)
    out = {}
    for node in main_of(source).body:
        if not isinstance(node, ast.If):
            continue
        dests = {n.attr for n in ast.walk(node.test)
                 if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                 and n.value.id == ns}
        for stmt in node.body:
            if (isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Name)):
                out.setdefault(stmt.value.func.id, set()).update(dests)
    return out


def flag_readers(source, attribute, namespace=None):
    """{module-level functions reading `args.<attribute>}`."""
    ns = namespace or namespace_of(source)
    return {name for name, fn in functions(source).items()
            if attribute in args_reads(fn, ns)}


def derived_accepts(source, attribute, namespace=None):
    """The mode dests the readers of `attribute` are dispatched under.

    The two readers above joined, and it is the whole of what "the modes that can
    use this flag" means. A function reading the flag that `main()` does not
    dispatch reaches no mode, so admitting its dests would admit a flag the
    parser has no spelling for.
    """
    dests = dispatch_dests(source, namespace)
    return {dest for name in flag_readers(source, attribute, namespace)
            for dest in dests.get(name, set())}


def guard_accepts(source, attribute, namespace=None):
    """The mode dests `main()`'s refusal of `attribute` lets through.

    The guard is the `ap.error` one whose test names the flag on the **left** of
    its `and`; what it waves through is the `or` under the `not` beside it. The
    positional dependence is `main()`'s, not the reader's, and it is stated here
    because it is a real limit: a guard written
    `if (args.check or args.self_test) and args.<flag>:` would answer `set()`
    here, and the case that owns the guard would then compare an empty
    expectation rather than go red on a guard that had stopped being read --
    which is why `GUARD_SHAPES` pins that shape and pins what this reader then
    derives rather than what it ought to.
    """
    ns = namespace or namespace_of(source)
    for node in ast.walk(main_of(source)):
        if not (isinstance(node, ast.If)
                and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "error"
                        for stmt in node.body for n in ast.walk(stmt))):
            continue
        test = node.test
        if not (isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And)
                and len(test.values) == 2):
            continue
        flag, allowed = test.values
        if not (isinstance(flag, ast.Attribute) and isinstance(flag.value, ast.Name)
                and flag.value.id == ns and flag.attr == attribute):
            continue
        if not (isinstance(allowed, ast.UnaryOp) and isinstance(allowed.op, ast.Not)
                and isinstance(allowed.operand, ast.BoolOp)):
            continue
        return args_reads(allowed.operand, ns)
    return set()


# The two `main()` guard shapes `guard_accepts` is pinned on, keyed by the words
# its docstring uses for each. Synthetic, because the committed `main()` has
# only the one shape and a reader that could not tell the two apart would leave
# the case below green against a source that has the other. `demo_flag` and not
# a committed flag, for the reason `demo_mode` is not a committed mode in the
# sibling suite: a flag already in the committed source cannot show a reader
# stopped working.
GUARD_SHAPES = {
    "the flag on the right of the `and`, so the wrong side is read":
        ("def main():\n"
         "    args = ap.parse_args()\n"
         "    if (args.check or args.demo_other) and args.demo_flag:\n"
         "        ap.error('refused')\n",
         set()),
    "the flag on the left and the modes under a `not`":
        ("def main():\n"
         "    args = ap.parse_args()\n"
         "    if args.demo_flag and not (args.check or args.demo_other):\n"
         "        ap.error('refused')\n",
         {"check", "demo_other"}),
}


def declaration_of(dest, source=SOURCE):
    """The `ap.add_argument(...)` call in `main()` that declares `dest`, or None.

    One walk serving three readers below. A dest argparse produces no spelling
    for has none in `main()` either, so it is reported rather than guessed at --
    and a case that drives `main()` with a dest the parser does not know fails on
    argparse's "unrecognized arguments", which is the loud direction and not a
    silent pass.
    """
    for node in ast.walk(main_of(source)):
        if (isinstance(node, ast.Call) and node.args
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            first = node.args[0]
            options = (first.elts if isinstance(first, (ast.List, ast.Tuple))
                       else [first])
            for option in options:
                if (isinstance(option, ast.Constant)
                        and isinstance(option.value, str)
                        and option.value.startswith("--")
                        and option.value.lstrip("-").replace("-", "_") == dest):
                    return node
    return None


def spelling_of(dest, source=SOURCE):
    """The long option `main()`'s parser declares for `dest`.

    dest -> spelling is argparse's own `-`-for-`_` rule, recovered rather than
    written down: a case that spells `--self-test` by hand is a second place for
    the parser's vocabulary to live, and it is this suite's whole subject that
    the tool and the test cannot drift.
    """
    node = declaration_of(dest, source)
    if node is None:
        return f"--{dest.replace('_', '-')}"
    first = node.args[0]
    options = first.elts if isinstance(first, (ast.List, ast.Tuple)) else [first]
    return next(o.value for o in options
                if isinstance(o, ast.Constant) and o.value.startswith("--"))


def takes_a_value(dest, source=SOURCE):
    """Whether `main()`'s parser gives `dest` an argument.

    Read off the committed parser rather than kept, and by argparse's own rule
    rather than by counting positional arguments: `--map` is declared
    `add_argument("--map", metavar="OLD_CSV", help=...)`, so the value it
    requires is described entirely in keywords and a positional count says it
    takes none. A mode handed no value it needs fails on argparse's "expected
    one argument" instead of reaching this guard, which is the confusion
    `test_xdata_register_map.py` declines to have in its `--check`/`--self-test`
    pair.
    """
    node = declaration_of(dest, source)
    if node is None:
        return False
    def keyword(name, default=None):
        return next((k.value.value for k in node.keywords if k.arg == name
                     and isinstance(k.value, ast.Constant)), default)
    if keyword("action", "store") in NO_VALUE_ACTIONS:
        return False
    return keyword("nargs") != 0


def mode_of(dest, source=SOURCE):
    """The mode function `main()` dispatches `dest` to."""
    return next(name for name, dests in dispatch_dests(source).items()
                if dest in dests)


def run_main(*argv):
    """(exit code, stdout, stderr) for one `main()` under `argv`.

    `ap.error` raises `SystemExit` rather than returning, so the code is taken
    off the exception and handed back: a refusal is the contract, and pinning
    the spelling (`2` today) would be a false alarm about the property that
    matters if a refusal is ever rewritten as `print(...); return 1`.
    """
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(sys, "argv", [str(TOOL), *argv]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = xrm.main()
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def committed_census():
    """The two committed census CSVs as bytes, for a byte-identical compare.

    Read through the tool's own `OUT_REGISTERS`/`OUT_CLUSTERS` rather than paths
    spelled out here, so a case follows the defaults if they move.
    """
    return (Path(xrm.OUT_REGISTERS).read_bytes(),
            Path(xrm.OUT_CLUSTERS).read_bytes())


@contextlib.contextmanager
def driving(ran, source=SOURCE):
    """Replace every mode entry point with a recorder for the duration.

    The tripwire, and the point of it is `test_xdata_register_map.py`'s: saying
    "the committed CSVs are unchanged" would also be satisfied by a run that
    wrote identical bytes, and the property `main()` states is stronger -- the
    refusal happens *before* any mode runs. So every entry point is replaced, and
    a guard that moved below the dispatch is caught wherever it moved to. A test
    that could damage the repository on failure would be the wrong place to pin
    this, so nothing is really written by any case here.
    """
    def entry(name):
        def record(*a, **kw):
            ran.append(name)
            return 0
        return record

    with contextlib.ExitStack() as stack:
        for mode in dispatch_modes(source):
            stack.enter_context(mock.patch.object(
                xrm, mode, mock.Mock(side_effect=entry(mode))))
        yield


def refuse(ran, *argv):
    """Run `main()` with every mode replaced by a recorder, and assert the three
    things a refusal owes: no mode ran, the exit was non-zero, and both
    committed CSVs are byte-identical to just before.

    Asserted by raising rather than through a `TestCase`, so the helper is a
    module function rather than a mixin every case has to be inside; each
    message names the invocation, because "the committed CSVs changed" is not
    actionable without knowing which run did it.
    """
    with driving(ran):
        before = committed_census()
        code, _out, err = run_main(*argv)
        if committed_census() != before:
            raise AssertionError(f"`{' '.join(argv)}` changed a committed "
                                 "census CSV")
    if ran:
        raise AssertionError(
            f"`{' '.join(argv)}` reached {ran} instead of being refused before "
            "the mode dispatch; the modes are mocked, so nothing was written "
            "either way")
    if code == 0:
        raise AssertionError(f"`{' '.join(argv)}` was not refused, and no mode "
                             f"ran: {err.strip()!r}")
    return code, err


def accepts(ran, dest):
    """Exit code for `--no-writer-axis` in the mode dispatched under `dest`,
    with every mode entry point a recorder.

    The accepted direction, through the same tripwire, so it costs no census
    either: what is under test is which branch of `main()` the argv takes, not
    what the mode would have printed.
    """
    with driving(ran):
        code, _out, _err = run_main(
            f"--{WRITER_AXIS.replace('_', '-')}", spelling_of(dest))
    return code


class TheShape(unittest.TestCase):
    """Every `args` read in `generate()`'s closure is a flag `census_shape`
    names, and every flag it names is one that reaches the clustering.

    A set equality rather than a count. A count of the flags is a value every
    merge that adds or removes one has to edit; the claim is that the two sets
    are the same set, and a reader who wants to know how big it is can ask.
    """

    def test_the_derived_set_equals_the_named_one(self):
        derived, named = set(effective(derived_flags(SOURCE))), named_flags(SOURCE)
        self.assertEqual(
            derived, named,
            f"census_shape names {sorted(named - derived)}, which nothing in "
            f"generate()'s closure reads, and generate()'s closure reads "
            f"{sorted(derived - named)}, which census_shape does not name: a "
            "flag in the second set is one whose run will still be told to "
            "re-key a file it cannot judge, and a flag in the first set is one "
            "named for a run shape the tool cannot produce")

    def test_the_failure_names_the_function_each_flag_was_read_in(self):
        # The reason `derived_flags` returns a dict. The closure is transitive
        # -- the right reading, since the question is what a flag can reach --
        # so a future helper taking `args` for an unrelated reason over-collects
        # into a set that would otherwise look identical to the real one.
        # Naming the contributor is the difference between "Lists differ" and a
        # flag plus a function to go and look at.
        readers = derived_flags(SOURCE)
        self.assertTrue(readers,
                        "nothing was derived, so the case above is comparing "
                        "two empty sets")
        for dest, contributors in readers.items():
            with self.subTest(flag=dest):
                self.assertTrue(contributors,
                                f"{dest} was derived with no contributing "
                                "function, so a reader that lost the attribution "
                                "would look the same to the case above")
                for contributor in contributors:
                    with self.subTest(flag=dest, function=contributor):
                        self.assertIn(contributor, closure(SOURCE))

    def test_the_closure_reaches_the_clustering(self):
        # What the derivation is a statement *about*, so that a refactor which
        # quietly changes the question goes red rather than passing on a set
        # that happens to match. `scan` carries the two re-bucketing flags into
        # the census and `build` carries the floor into `components`, which is
        # the clustering itself.
        reached = closure(SOURCE)
        for expected in ("generate", "census_and_groups", "scan", "build",
                         "components"):
            with self.subTest(function=expected):
                self.assertIn(expected, reached)

    def test_the_writer_is_outside_the_closure(self):
        # The other half, and the reason `TheExclusion`'s inertness is a
        # measurement rather than a permanent property. `outputs()` is reached
        # from `check` and `write` beside `generate`, not from it -- so the
        # output-path subtraction removes nothing today, and would start
        # removing something the day a refactor inlined the writers into the
        # generator. Named because a reader that grew to include `outputs` would
        # quietly bring two more flags in with it.
        self.assertNotIn("outputs", closure(SOURCE))


class TheExclusion(unittest.TestCase):
    """The output-path subtraction is real, load-bearing, and currently inert.

    Three claims, because each has its own failure. That the two names are the
    ones `outputs()` actually reads is what stops the exclusion growing over a
    real flag. That `generate()`'s closure reads neither of them *on this tree*
    is a measurement, and a property of where `outputs()` is called from rather
    than a permanent one -- measured with the filter switched off, since the
    default subtracts both names and would make the comparison empty whatever
    the source said. That subtracting them changes something when a closure does
    read them is the only case that catches a deleted filter, and it needs an
    injected read because the committed tree cannot show one; it carries that
    read through the middle case's expression as well, so the measurement is
    shown going red rather than only asserted.
    """

    def test_the_exclusion_names_outputs_own_reads(self):
        # Equality, not containment. A reader that excluded a third dest would
        # still pass the control case -- removing a flag `census_shape` names
        # fails the comparison, so the mistake shows up there and not here --
        # but it would go red here, naming the dest it does not account for.
        self.assertEqual(OUTPUT_PATHS, args_reads(functions(SOURCE)["outputs"],
                                                  NAMESPACE))

    def test_the_exclusion_is_currently_inert(self):
        # A measurement on this tree, not a permanent property, and the case
        # above is what explains it. If this goes red because a refactor
        # inlined the writers into the generator, the exclusion has started
        # doing the work it was written for -- and the case below is what then
        # has something to check.
        #
        # `exclude=frozenset()` is load-bearing rather than a slip. The default
        # already subtracts both names, so intersecting the default with them is
        # empty for *any* source and this case could never fail. The claim here
        # is the one the default cannot express: that `generate()`'s closure
        # reads neither name, which is a question about the closure alone, so
        # the filter is switched off to ask it. The case below injects a read
        # and shows this same expression going red on it.
        self.assertEqual(
            set(OUTPUT_PATHS) & set(derived_flags(SOURCE, exclude=frozenset())),
            set(),
            "a flag the derivation subtracts is one the clustering actually "
            "reads, so the exclusion is no longer inert and `outputs()` has "
            "moved into generate()'s closure")

    def test_the_exclusion_excludes_when_the_closure_reads_them(self):
        # The non-vacuity control, and it has to be injected: `outputs()` is not
        # in `generate()`'s closure on the committed tree, so without a read put
        # inside a function that *is*, a reader that stopped subtracting
        # anything would pass every other case here.
        injected = injecting(SOURCE, "build", "out_registers")
        self.assertIn("out_registers", set(derived_flags(injected, exclude=())),
                      "the injection did not land, so this case is measuring "
                      "the reader and not the filter")
        self.assertNotIn("out_registers", set(derived_flags(injected)))
        # And the same injection through the expression the case above asserts,
        # so "this can go red" is shown rather than claimed: the filter off, the
        # intersection is exactly the injected name. Without this the case above
        # would be an assertion about an empty set that no source could widen.
        self.assertEqual(
            set(OUTPUT_PATHS) & set(derived_flags(injected, exclude=frozenset())),
            {"out_registers"},
            "the inertness case above does not go red on a closure that reads an "
            "output path, so it is not a measurement of this tree")


class TheNegativeControls(unittest.TestCase):
    """An injected flag reaches the derived set, names its function, and breaks
    the control case -- so the control case is a claim about the tool rather
    than about this reader.

    Every case is on a copy of the committed source, and none of them could be
    written against the real tree: on the real tree they would all be vacuous,
    because an injection that were not collected would leave the control case
    green. A suite that cannot show its own reader failing is not evidence that
    the reader works.
    """

    def assert_collected(self, derived, function):
        self.assertIn(INJECTED, derived,
                      f"the injection into {function} was not collected, so "
                      "every case in this class is measuring the reader and not "
                      "the tool")
        self.assertEqual(derived[INJECTED], frozenset({function}),
                         "the injection was collected from the wrong function, "
                         "so a failure would name a place the reader has to be "
                         "checked against")

    def test_a_flag_injected_into_the_census_call_is_caught(self):
        # `census_and_groups` is where #851's two re-bucketing flags are read, on
        # the way into `scan`. An injected one changes no line of the tool.
        derived = derived_flags(injecting(SOURCE, "census_and_groups", INJECTED))
        self.assert_collected(derived, "census_and_groups")
        self.assertNotEqual(set(derived), named_flags(SOURCE),
                            "the injected flag did not break the comparison, so "
                            "the control case would not go red for a real one")

    def test_a_flag_injected_into_the_builder_is_caught(self):
        # `build` rather than `census_and_groups`, because the issue names both
        # and only one of them is the whole claim: `--threshold` reaches the
        # clustering from here, and so would any future flag that moved the
        # floor, the similarity, or the `components` call itself.
        derived = derived_flags(injecting(SOURCE, "build", INJECTED))
        self.assert_collected(derived, "build")
        self.assertNotEqual(set(derived), named_flags(SOURCE))

    def test_a_flag_only_the_named_side_grows_is_also_caught(self):
        # The other direction, and the one a hand-kept list gets wrong most
        # easily: `census_shape` naming a flag no closure reads is a claim about
        # a run shape the tool cannot produce, and the same comparison catches it.
        source = injecting(SOURCE, "census_shape", "an_unreachable_flag")
        self.assertIn("an_unreachable_flag", named_flags(source))
        self.assertNotIn("an_unreachable_flag", set(derived_flags(source)))
        self.assertNotEqual(set(effective(derived_flags(source))),
                            named_flags(source))

    def test_an_exempt_flag_with_a_reason_is_a_recorded_difference(self):
        # The escape hatch, used properly. A deliberate difference goes in
        # `EXEMPT` with the reason it is deliberate, the two sides are then
        # compared *after* the subtraction, and the control case stays green --
        # which is the point: the reason is what a later reader reads, and it is
        # in the suite rather than in a sentence somebody has to believe.
        derived = derived_flags(injecting(SOURCE, "build", INJECTED))
        recorded = effective(derived, {INJECTED: "stands in for a difference "
                                                     "that was written down"})
        self.assertNotIn(INJECTED, recorded)
        self.assertEqual(set(recorded), named_flags(SOURCE))

    def test_an_exemption_without_a_reason_is_not_a_way_through(self):
        # Both halves of a smuggled difference. An empty reason is a difference
        # nobody wrote down, which is the defect the entry exists to prevent; a
        # whitespace one is the same thing with a key typed. Either way the
        # exemption is not subtracted, so the injected flag stays in the derived
        # set and the comparison goes red -- silencing the control case costs a
        # second edit.
        derived = derived_flags(injecting(SOURCE, "build", INJECTED))
        for label, reason in (("empty", ""), ("whitespace", "   ")):
            with self.subTest(reason=label):
                self.assertIn(INJECTED, effective(derived, {INJECTED: reason}))
                self.assertNotEqual(set(effective(derived, {INJECTED: reason})),
                                    named_flags(SOURCE))

    def test_every_exemption_carries_a_reason(self):
        # The rule `effective` is read under, asserted over the whole table so a
        # future entry cannot arrive reasonless. Empty today, and that is fine:
        # the two cases above exercise it with a real entry.
        for dest, reason in EXEMPT.items():
            with self.subTest(flag=dest):
                self.assertTrue(
                    reason.strip(),
                    f"EXEMPT exempts {dest} with no reason given, so the "
                    "difference is recorded nowhere a reader would look")


class TheWriterAxisIsRefused(unittest.TestCase):
    """`--no-writer-axis` is refused by every mode that cannot use it, and
    reaches the two that can.

    The refused and accepted sets are both derived, from the tool's AST and from
    `main()`'s own dispatch, so neither is a second hand-kept list that can drift
    from the guard. A third function reading `args.no_writer_axis` moves the
    derived pair and the case below it goes red -- which is the direction that
    matters, since the guard is the thing with to be wrong.

    Before this change the flag parsed into every mode and was read by two, so
    `--check --no-writer-axis` exited 0 with stdout and stderr byte-identical to
    `--check`: a run whose numbers are a default run's, wearing a flag that says
    it measured what the second relation is worth.

    The two sets partition the modes the parser *names*. The bare default has no
    dest to partition -- it is the `return write(args)` at the end of the
    dispatch, not an `if` -- and it is the run with the most behind it, so it has
    its own case rather than being folded into the partition.
    """

    def setUp(self):
        self.accepted = derived_accepts(SOURCE, WRITER_AXIS)
        self.refused = ({d for dests in dispatch_dests(SOURCE).values()
                         for d in dests} - self.accepted)

    def test_the_guard_admits_exactly_the_functions_that_read_the_flag(self):
        admits = guard_accepts(SOURCE, WRITER_AXIS)
        self.assertEqual(
            admits, self.accepted,
            f"main()'s refusal waves through {sorted(admits)}, and the "
            f"functions reading args.{WRITER_AXIS} are dispatched under "
            f"{sorted(self.accepted)}: a third reader has to be added to the "
            "guard, and a mode the guard admits that reads nothing is a flag "
            "accepted and ignored, which is what the guard exists to stop")

    def test_every_guard_shape_the_reader_names_is_collected_too(self):
        # The positional dependence `guard_accepts` states, pinned on synthetic
        # source because the committed `main()` has only one of the two shapes.
        # Equality rather than membership, so each source carries exactly one
        # guard and this says the reader records that one and no other.
        for shape, (source, expected) in GUARD_SHAPES.items():
            with self.subTest(shape=shape):
                self.assertEqual(guard_accepts(source, "demo_flag"), expected)

    def test_the_two_sides_partition_the_dispatch(self):
        # The refusal is only total if it leaves the modes that read the flag
        # reachable, and only safe if it covers every other one. Asserted as a
        # partition of the derived dispatch rather than as two lists, so a mode
        # added to `main()` lands on one side automatically. The bare default is
        # not in either half and is not meant to be -- see the class docstring,
        # and the bare case below for it.
        every = {d for dests in dispatch_dests(SOURCE).values() for d in dests}
        self.assertEqual(self.refused | self.accepted, every,
                         "the refused and accepted sets do not cover main()'s "
                         "dispatch, so some mode is neither refused nor "
                         "exercised here")
        self.assertTrue(self.accepted,
                        f"no mode reads args.{WRITER_AXIS}, so the guard "
                        "refuses the flag everywhere and it is dead")

    def test_the_flag_is_refused_with_every_mode_that_cannot_read_it(self):
        # One `subTest` per derived mode rather than a case each: the modes
        # differ only in the argument they are spelled with, and writing them out
        # here would be a hand-kept copy of the set the partition case already
        # derives. `--map` and `--reconcile` take a value they never see, the
        # refusal being before the dispatch and the entry points mocked.
        for dest in sorted(self.refused):
            argv = [spelling_of(dest)] + (["a-value-it-never-reads"]
                                          if takes_a_value(dest) else [])
            with self.subTest(mode=dest):
                _code, err = refuse([], f"--{WRITER_AXIS.replace('_', '-')}",
                                    *argv)
                self.assertIn("--no-writer-axis only changes what", err)

    def test_the_flag_is_refused_bare(self):
        # The issue's invocation, and the one where a mode *would* be reached if
        # the guard were not there: the flag alone falls through to `write`,
        # which regenerates the committed pair. Its own case because the bare
        # run is the one with a write behind it -- the case above passes a mode
        # flag, and every one of those returns before a write too.
        _code, err = refuse([], f"--{WRITER_AXIS.replace('_', '-')}")
        self.assertIn("--no-writer-axis only changes what", err)

    def test_the_bare_run_would_write_the_committed_pair(self):
        # What the case above rests on, and the one thing here that is not
        # asserted through a mock. `--no-writer-axis` alone falls through to
        # `write`, so without the guard it regenerates the two CSVs the tree is
        # keyed to -- but the tripwires mock `write`, and a mock writes nothing,
        # so a bare run refused for any reason would satisfy the case above
        # whether or not there was a file behind it. If the defaults ever moved
        # off `annotations/`, the bare case would be a run with no consequence
        # behind it and the refusal would still be green.
        self.assertEqual(Path(xrm.OUT_REGISTERS).parent, EC / "annotations")
        self.assertEqual(Path(xrm.OUT_CLUSTERS).parent, EC / "annotations")

    def test_the_modes_that_read_it_are_reached(self):
        # The other direction, and the one that catches a guard widened past the
        # flag's own readers: the mode runs, so the flag reached a mode that can
        # act on it rather than being refused everywhere. The refusal is in
        # `main()` and not in the parser, so the flag stays declared for the two
        # modes that use it.
        for dest in sorted(self.accepted):
            with self.subTest(mode=dest):
                ran = []
                code = accepts(ran, dest)
                self.assertEqual(
                    ran, [mode_of(dest)],
                    f"{spelling_of(dest)} with --{WRITER_AXIS.replace('_', '-')} "
                    f"reached {ran}: the flag has to stay usable in the modes "
                    "that read it, and the tripwire is what makes that checkable "
                    "without running a census")
                self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
