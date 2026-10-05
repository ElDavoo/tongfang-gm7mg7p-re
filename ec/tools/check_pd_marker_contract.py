#!/usr/bin/env python3
"""What each `ec/tools/` module does when `PD_MARKER` fails to compare -- a
census of the per-call-site decision, recorded rather than inferred.

`trace_xdata_refs.PD_MARKER` is a `(0x20040, b"ITE8850-PD")` pair and nothing
more: it cannot refuse anything on its own, and the comment over it records one
of the several contracts its importers implement. **This file is the list of
which contract is whose**, so that the comment can point at a census instead of
at one importer, and so that a module which starts refusing -- or stops -- is a
row that moved rather than a habit nobody wrote down.

The issue this answers (#857) put it as a two-way split and it is not one. Past
"refuse" and "note" there is a shape with no decision in the function at all: a
bare `pd_verified(d)` helper that returns the boolean and leaves the call to
whoever asked, which several modules then consult in their own `main()`. Past
that one, the issue's table has no column for three more -- sites that compute
the comparison and say nothing at all about it (`silent`), sites that write the
marker's own bytes into their report without ever comparing them
(`unverified`), and `--self-test` assertions, where the comparison is the check
rather than a guard (`assert`). All seven are in `CONTRACTS`; each is read off
the enclosing function rather than asked for.

**`refuse` is the only contract that turns a bad image into no answer.**
`trace_xdata_refs.region_of()` relabels the 0x20000 band `unknown` once the
marker fails, which is what makes the rest survivable: a tool that keeps going
reports that band as unidentified, and a reader who believes the note knows so.
A tool that keeps going and prints its table to *stdout* interleaves the note
into the thing the reader was parsing, and one that keeps going silently drops
the band from both split columns while the file-wide count still stands -- so an
address whose only sites are in that band reads exactly like an address with no
sites at all. `docs/findings/pd-marker-caller-contracts.md` §3 reproduces what
that looked like.

**`unverified` is a module, not a site.** It is what `pd_call_targets.py` is:
it prints `marker b'ITE8850-PD' at 0x20040` in its report and never asks whether
the bytes are there, which is the advisory treatment this census exists to
record. A module that *does* have a contract is not filed this way even where it
also names the marker -- the bytes in `intmem_refs`' note are that note, and the
note is already a row -- so the token means "nothing here compares it" and never
"this module mentions it".

**A `predicate` row is not where the decision is, so it carries it.** The helper
returns a boolean and its callers act on it, so the `caller` column says what
each in-module caller does with the answer -- which is how the second
stdout-note site was found, one whose comparison is a helper three hundred lines
from the `print` that mishandles it. A caller that passes the boolean straight
into another call is `inline`: that call's own contract is the one that governs,
and this walk does not follow it.

**No line number is committed, anywhere in the table.** `--report` prints one,
because a person reading it wants to be told where to look, but neither the
`line` column nor the `@NNN` in a `caller` cell exists in the CSV that `--check`
diffs. A line in that file is a value every merge that grows one of the listed
modules has to edit to keep a check it never touched green, and CLAUDE.md is
about that shape rather than about this file: a durable `module` + `function`
key, and the reader who wants the line gets it from `--report` or the editor.

**Two limits, both "not found by this method", never "absent".** A site is
reached by two searches, and either can miss: by *name* (`PD_MARKER` appearing
in an assignment, a comparison or a subscript) and by *shape* (the assignment
that reads the marker, and the `if` in the same function body that tests what it
bound). A module that reads the marker's bytes through a local alias, spells the
offset and the magic as its own constants, or defers the comparison to a helper
this walk does not follow, has no row -- a fact about the walk and not about the
module. `TOOLS_DIR` is the only directory searched and the default output
names it; this file says nothing about `bios/tools/` or `windows/tools/`. Second, a site
inside a `--self-test` is `assert` rather than a contract about running the
tool, and the two are not merged: a self-test that refuses a bad image is still
`refuse`, because that is what it does.

**The table is generated and never hand-edited.** `--csv` writes it, `--check`
diffs the committed `../annotations/pd-marker-caller-contracts.csv` against a
fresh run through `trace_xdata_refs.check_table`, byte for byte and with that
module's CRLF handling. A module added, moved or re-contracted is a diff to
regenerate rather than a row someone forgot to add.

Usage:
    python3 check_pd_marker_contract.py                  the census, by contract
    python3 check_pd_marker_contract.py --csv            the same as CSV
    python3 check_pd_marker_contract.py --check          diff the committed table
    python3 check_pd_marker_contract.py --contract note-stdout
    python3 check_pd_marker_contract.py --module scan_refs.py
"""
import argparse
import ast
import csv
import io
import os
import sys

from trace_xdata_refs import check_table, repo_path

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = HERE
REPO = os.path.join(HERE, os.pardir, os.pardir)
COMMITTED_CSV = os.path.join(HERE, os.pardir, "annotations",
                             "pd-marker-caller-contracts.csv")

# The name the walk searches for. The pair itself is never restated here: a
# module that carries its own copy of the constant (`pd_image_census.py`,
# `make_bank_image.py`) is a row whose `marker` column reads `restated`, and
# that is the distinction worth keeping -- its guard is over bytes the module
# spelled out itself, not over the shared pair.
MARKER = "PD_MARKER"

# The seven contracts, in the order a reader wants them: the one that answers
# nothing, then the two that answer while saying so on a named stream, then the
# one that answers without saying anything, then the three that are not a run
# decision at all.
REFUSE = "refuse"
NOTE_STDERR = "note-stderr"
NOTE_STDOUT = "note-stdout"
SILENT = "silent"
UNVERIFIED = "unverified"
PREDICATE = "predicate"
ASSERT = "assert"

CONTRACTS = (REFUSE, NOTE_STDERR, NOTE_STDOUT, SILENT, UNVERIFIED, PREDICATE,
             ASSERT)

# What each token means, kept beside the constants rather than in the docstring
# alone because the table is what most readers read, and a vocabulary that can
# only be looked up in a paragraph is one that decays.
MEANING = {
    REFUSE: "the run stops -- a non-zero return, a sentinel the caller turns "
            "into one, or a raise",
    NOTE_STDERR: "the run continues, says why on stderr",
    NOTE_STDOUT: "the run continues, says why on stdout",
    SILENT: "the run continues and says nothing",
    UNVERIFIED: "the marker's bytes reach the output and nothing here "
                "compares them",
    PREDICATE: "the function returns the boolean; its callers resolve it",
    ASSERT: "a --self-test assertion over the comparison, not a run guard",
}

# The `check(...)` spelling the self-tests call their assertion. A bare `assert`
# statement is not here: it is `ast.Assert` rather than a call, and an assertion
# over the marker is what these tools write, not what they inherit.
ASSERT_FNS = ("check",)

# The comparison operators that make a guard's *body* the failure branch. The
# `==` form is the one that gets polarity wrong most easily: `code_pointer_sites`
# reads `if d[...] == magic: return True` and refuses with the `raise` below it,
# so a walk that took the body for the failure path would book a site as silent.
NEGATED_OPS = (ast.NotEq, ast.NotIn, ast.IsNot)


def names(node) -> set:
    """Every name and attribute tail `node` mentions.

    The tree rather than the source text, because a mention of the marker inside
    a message string is not a read of it -- `check_image_map.py`'s banner spells
    `trace_xdata_refs.PD_MARKER` in prose and would otherwise be a site. `ast`
    leaves a `Constant` a leaf, so the string it holds is never descended into.
    """
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def bound_names(target) -> set:
    """The names an assignment target binds.

    Only `Name` and the tuple/list targets above one. A store through a
    subscript binds nothing new, and counting the names in its *slice* would
    turn `wrong[off:off + len(magic)] = b"\\x00" * len(magic)` into a rebinding
    of `off` and `magic` -- which is how a site that poisons the marker to
    watch a refusal fire would come back looking like one that only reads it.
    """
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        out = set()
        for elt in target.elts:
            out |= bound_names(elt)
        return out
    return set()


def assigns(stmt) -> set:
    """The names `stmt` binds, or the empty set."""
    if isinstance(stmt, ast.Assign):
        return bound_names(stmt.targets[0])
    if isinstance(stmt, ast.AnnAssign):
        return bound_names(stmt.target)
    return set()


def negated(test) -> bool:
    """Whether an `if`'s *body* runs when the comparison came out false."""
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return True
    if isinstance(test, ast.Compare):
        return any(isinstance(op, NEGATED_OPS) for op in test.ops)
    return False


def failure_path(body, bound) -> list:
    """The statements that run when the comparison came out false, or [].

    The first `if` in this function body whose test reads the marker's answer
    decides, and polarity says which of its two sides that is. [] is not "the
    comparison succeeded" -- it is "no branch here that this walk can attribute
    to the comparison", which is what a caller-side decision looks like and what
    `silent` names.

    **`bound` grows as the walk goes**, because the guard almost never tests the
    name the unpack bound. `off, magic = PD_MARKER` is followed by
    `pd_verified = d[off:off + len(magic)] == magic` and then
    `if not pd_verified:`, so a walk that stopped at the unpack's own names would
    find no guard at all and book a module that refuses as one that says
    nothing. An assignment joins `bound` when its value reads a name already in
    it, or the marker -- `rows = residual(d, pd_verified)` carries it one step
    further, and `if args.csv:` two lines later does not, because `args` was
    never derived from the marker.
    """
    bound = set(bound)
    for i, st in enumerate(body):
        if isinstance(st, (ast.Assign, ast.AnnAssign)):
            if names(st.value) & bound or MARKER in names(st.value):
                bound |= assigns(st)
            continue
        if not isinstance(st, ast.If):
            continue
        seen = names(st.test)
        if not (seen & bound) and MARKER not in seen:
            continue
        if negated(st.test):
            return list(st.body)
        # The `== magic` shape: passing is the body, so failing is everything
        # from the `else` on, and `require_pd`-shaped helpers put their refusal
        # on the next line.
        return list(st.orelse) + list(body[i + 1:])
    return []


def terminates(stmts) -> str:
    """How the first of `stmts` that ends the run ends it, else "".

    A `Return` counts only when it carries a value: a bare `return` is the end of
    a branch that decided nothing, and reading one as a refusal would make every
    `if <guard>: ... return` in the tree a refusal site.
    """
    for st in stmts:
        for n in ast.walk(st):
            if isinstance(n, ast.Raise):
                return (ast.unparse(n.exc.func) if isinstance(n.exc, ast.Call)
                        else "raise")
            if isinstance(n, ast.Return) and n.value is not None:
                return f"return {ast.unparse(n.value)}"
            if isinstance(n, ast.Call):
                fn = ast.unparse(n.func)
                if fn in ("sys.exit", "exit", "SystemExit", "os._exit"):
                    return fn
    return ""


def printed_stream(stmts) -> str:
    """`stderr`, `stdout` or "" for where a failing branch prints.

    An explicit `file=` is the whole difference between `note-stderr` and
    `note-stdout` here, and it is the difference that decides whether a reader
    who redirected a table away from stderr still sees the reason. A branch
    printing on both is `stderr`, the one stream such a reader keeps.
    """
    seen = set()
    for st in stmts:
        for n in ast.walk(st):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "print"):
                continue
            target = ""
            for kw in n.keywords:
                if kw.arg == "file":
                    target = ast.unparse(kw.value)
            seen.add("stdout" if "stderr" not in target else "stderr")
    return "stderr" if "stderr" in seen else ("stdout" if seen else "")


def compares_marker(stmt) -> bool:
    """Whether this statement compares the marker against anything.

    The first half of the line between `unverified` and everything else:
    `pd_entry_forms` names the marker's offset inside a `check()` it *does* run,
    and is not this case.
    """
    return any(isinstance(n, ast.Compare) and MARKER in names(n)
               for n in ast.walk(stmt))


def is_assert(node, bound) -> bool:
    """Whether `node` is an assertion whose condition reads this comparison."""
    if not isinstance(node, ast.Call):
        return False
    fn = ast.unparse(node.func).split(".")[-1]
    if fn not in ASSERT_FNS:
        return False
    return any(isinstance(a, ast.Compare) and (names(a) & bound)
               for a in node.args)


def classify(path: list) -> tuple:
    """`(contract, exit, stream)` for one failure path."""
    stop = terminates(path)
    if stop:
        return (REFUSE, stop, printed_stream(path))
    stream = printed_stream(path)
    if stream == "stderr":
        return (NOTE_STDERR, "", "stderr")
    if stream == "stdout":
        return (NOTE_STDOUT, "", "stdout")
    return (SILENT, "", "")


def functions(tree):
    """`(name, body, node)` for every function and method in `tree`."""
    out = []

    def walk(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append((child.name, child.body, child))
                walk(child)
            else:
                walk(child)

    walk(tree)
    return out


def enclosing_function(node, fns):
    """The innermost recorded function whose body holds `node`, else None."""
    best = None
    for name, body, owner in fns:
        span = set()
        for st in body:
            span |= {id(n) for n in ast.walk(st)}
        if id(node) in span:
            if best is None or owner.lineno > best[2].lineno:
                best = (name, body, owner)
    return best


def blocks(body):
    """Every statement list in `body`, outermost first.

    A site is not always a direct child of its function: `dsdt_ec_fields.py`
    reads the marker inside an `if` and guards it two statements down, so a walk
    over top-level statements only would leave that module with no row at all --
    which would read as "no contract" rather than as a limit of the walk. Each
    list is searched on its own, because `failure_path()` looks at siblings and
    a guard in a sibling's branch is a different decision.

    Nested function bodies are not descended into: they are separate functions,
    and `functions()` has already listed them.
    """
    out = []

    def walk(body):
        out.append(body)
        for st in body:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for field in ("body", "orelse", "finalbody"):
                sub = getattr(st, field, None)
                if isinstance(sub, list):
                    walk(sub)
            for handler in getattr(st, "handlers", None) or []:
                walk(handler.body)

    walk(body)
    return out


def caller_decision(fns, call) -> str:
    """What the function containing `call` does with the boolean it got.

    Three shapes, because the caller does one of three things with the answer:
    binds it and decides (`verified = pd_verified(d)`, then `if not verified:`),
    tests the call directly (`if not pd_verified(d):`), or passes it straight
    on (`region_of(off, pd_verified(fw))`). The last is `inline` and is not a
    gap in the census -- that call's own contract is the one that governs, and
    following it would be a second tool's job.

    "Straight on" is decided by whether another `Call` stands between the
    `pd_verified(...)` and the name it would bind. `verified = pd_verified(d)`
    hands the answer to the assignment; `at = runtime_addr(x, pd_verified(d))`
    hands it to `runtime_addr`, and binding `at` would say nothing about the
    marker at all.

    The cell is the caller's name and the contract, with no line number. A
    `@NNN` here would be the same tripwire the `line` column was -- a value in
    a committed, `--check`-diffed file that every merge growing the caller has
    to edit -- and it carries nothing: two calls in one caller that resolve the
    same way are one decision, which is what the dedup in the caller says, and
    two that resolve differently differ in the contract word beside the name.
    """
    host = enclosing_function(call, fns)
    if host is None:
        return "inline"
    name, body, _owner = host
    for block in blocks(body):
        for i, st in enumerate(block):
            if isinstance(st, (ast.Assign, ast.AnnAssign)):
                bound = assigns(st)
                if bound and not handed_on(st.value, call):
                    for n in ast.walk(st):
                        if n is call:
                            path = failure_path(block, bound)
                            contract = classify(path)[0] if path else SILENT
                            return f"{name}() {contract}"
            if isinstance(st, ast.If):
                for n in ast.walk(st.test):
                    if n is call:
                        if negated(st.test):
                            path = list(st.body)
                        else:
                            path = list(st.orelse) + list(block[i + 1:])
                        return f"{name}() {classify(path)[0]}"
    return f"{name}() inline"


def handed_on(value, call) -> bool:
    """Whether `call` reaches `value` through another function call.

    The answer is then somebody else's decision. `region_of(off,
    pd_verified(fw))` is the case: the boolean enters `region_of`, and what
    `region_of` does with a false one is `trace_xdata_refs`'s contract, not this
    module's.
    """
    parent = {}
    for n in ast.walk(value):
        for child in ast.iter_child_nodes(n):
            parent[id(child)] = n
    node, seen = parent.get(id(call)), set()
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        if isinstance(node, ast.Call) and node is not call:
            return True
        node = parent.get(id(node))
    return False


def pure_unpack(stmt) -> bool:
    """Whether this assignment reads the marker and nothing else.

    The distinction the message-only rows turn on. `off, magic = PD_MARKER`
    followed by a comparison is the site; the same unpack *inside* a guard that
    has already decided supplies only the words of that guard's message, and
    `message_only()` says so.
    """
    value = stmt.value
    return isinstance(value, (ast.Name, ast.Attribute)) and MARKER in names(value)


def message_only(tree, block, i, bound, predicates, derived) -> bool:
    """Whether this unpack only spells the words of a guard it does not make.

    Four modules unpack the marker without ever branching on it, purely to name
    the file offset and the magic in a note that a guard has already decided to
    print. Filing those as sites would give each of them a `silent` row -- a
    contract the module does not have, sitting beside the `refuse` row on the
    same module that it contradicts. The decision belongs to the predicate's row
    instead, at the line of the call.

    The two shapes differ and the rule does not. `pd_direct_offset_sites` unpacks
    *inside* `if not pd_verified(d):`; `fw_image_diff` unpacks on the line
    *before* `if not verified[label]:`. Both are the same thing -- the guard
    reads the module's predicate, and none of the names the unpack bound is what
    that guard branches on -- so both are looked for: the guards in this
    statement's own block, and the guards this statement sits inside.
    """
    if not pure_unpack(block[i]):
        return False
    stmt = block[i]
    guards = [st for st in block if isinstance(st, ast.If)]
    guards += [n for n in ast.walk(tree)
               if isinstance(n, ast.If) and stmt in n.body]
    for guard in guards:
        seen = names(guard.test)
        if not (seen & derived or any(isinstance(n, ast.Call)
                                      and ast.unparse(n.func) in predicates
                                      for n in ast.walk(guard.test))):
            continue
        return not (seen & bound)
    return False


def predicate_derived(fns, predicates) -> set:
    """Names bound from a `pd_verified(...)` call, wherever the answer lands.

    `pd_direct_offset_sites.main` tests the call itself; `fw_image_diff.compare`
    puts both images' answers in a dict and tests `verified[label]`. Only the
    first is visible from the call node, and the second branch is exactly where
    the note gets printed.
    """
    out = set()
    for _fname, body, _owner in fns:
        for block in blocks(body):
            for st in block:
                if not isinstance(st, (ast.Assign, ast.AnnAssign)):
                    continue
                if any(isinstance(n, ast.Call) and ast.unparse(n.func)
                       in predicates for n in ast.walk(st.value)):
                    out |= assigns(st)
    return out


def returns_boolean(body, start, bound) -> bool:
    """Whether the function's own last word is the comparison.

    The site and the return are the whole decision, which is what separates a
    bare helper from a `main()` that binds the answer and hands it to
    `residual()` two statements later.
    """
    for st in body[start + 1:]:
        if isinstance(st, ast.Return) and st.value is not None:
            return bool(names(st.value) & bound)
        if isinstance(st, (ast.If, ast.For, ast.While, ast.Try,
                           ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
    return False


def module_marker(tree, name) -> str:
    """`defines`, `restated` or `imported` -- where this module's marker is."""
    restated = any(assigns(st) & {MARKER, f"{MARKER}_OFF"}
                   for st in ast.walk(tree) if isinstance(st, ast.Assign))
    if name == "trace_xdata_refs.py":
        return "defines"
    return "restated" if restated else "imported"


def sites(path: str) -> list:
    """One row per site in one module; the columns are `COLUMNS`."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        # Not an error to report here. `check_python_syntax` owns whether a
        # committed tool parses, and a row that guessed at unparseable source
        # would be the one thing in this table nobody could re-derive.
        return []
    name = os.path.basename(path)
    fns = functions(tree)
    marker = module_marker(tree, name)
    calls = {}
    for _fn_name, body, _owner in fns:
        for block in blocks(body):
            for st in block:
                for n in ast.walk(st):
                    if isinstance(n, ast.Call):
                        calls.setdefault(ast.unparse(n.func), []).append(n)

    # The predicate helpers are found first because `message_only()` needs to
    # know their names to recognise the unpack that only supplies a guard's
    # message -- a row this pass would otherwise file as `silent` beside the
    # `refuse` it contradicts.
    def candidates():
        for fname, body, _owner in fns:
            for block in blocks(body):
                for i, st in enumerate(block):
                    if MARKER not in names(st):
                        continue
                    if isinstance(st, (ast.Assign, ast.AnnAssign)):
                        yield fname, block, i, st
                    elif isinstance(st, ast.Expr):
                        # Two shapes reach here and neither is an assignment.
                        # `make_bank_image.py` restates the marker and asserts
                        # on it with `check(...)`; `pd_call_targets.py` writes
                        # the marker's own bytes into its report and compares
                        # nothing anywhere -- which is the advisory treatment
                        # this census exists to record, not a contract at all.
                        yield fname, block, i, st

    predicates = {fname for fname, block, i, st in candidates()
                  if returns_boolean(block, i, assigns(st))}
    derived = predicate_derived(fns, predicates)
    out = []
    for fname, block, i, st in candidates():
        bound = assigns(st) or names(st)
        if message_only(tree, block, i, bound, predicates, derived):
            continue
        # `lineno` is deliberately *not* a column. It is here for `--report`,
        # where a human is told where to look; the committed table is diffed by
        # `--check`, and a line number in it is a value every merge that grows
        # one of the listed modules has to edit to keep a check it never
        # touched green. `module` and `function` are the durable keys.
        row = {"module": name, "function": fname, "lineno": st.lineno,
               "marker": marker, "contract": "", "exit": "",
               "stream": "", "caller": ""}
        if isinstance(st, ast.Expr) and not compares_marker(st):
            row["contract"] = UNVERIFIED
        elif returns_boolean(block, i, bound):
            row["contract"] = PREDICATE
            # Deduped because one call line can hold two of them -- `fw_image_diff`
            # asks the same question of both images on one line, and the answer
            # is the same decision either way.
            decided = []
            for c in calls.get(fname, []):
                cell = caller_decision(fns, c)
                if cell not in decided:
                    decided.append(cell)
            row["caller"] = "; ".join(decided) or "none in this module"
        else:
            path = failure_path(block, bound)
            if is_assert(st, bound):
                row["contract"] = ASSERT
            elif path:
                (row["contract"], row["exit"],
                 row["stream"]) = classify(path)
            elif "self_test" in fname:
                # No guard and a self-test: the comparison is the check, which
                # is what `pd_site_clusters.self_test` is for -- it poisons the
                # marker on purpose to watch a refusal fire.
                row["contract"] = ASSERT
            else:
                row["contract"] = SILENT
        out.append(row)
    # An `unverified` row is a *module* with no contract at all. Where a module
    # does have one, the marker's bytes in its output are that module's message
    # -- `intmem_refs` spells the magic into the note its `main()` prints, and
    # that note already has a row -- so filing it separately would give one
    # decision two rows and read as a second, weaker claim about it.
    if any(r["contract"] != UNVERIFIED for r in out):
        out = [r for r in out if r["contract"] != UNVERIFIED]
    return out


def census(directory: str = TOOLS_DIR) -> list:
    """Every site in every non-test module under `directory`, in file order.

    A site this does not reach is not a site without a contract. The walk is
    over the parsed module rather than over its text, and a comparison reached
    through a local alias is not a row -- both are "not found by this method",
    never "there are none".
    """
    out = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".py") or name.startswith("test_"):
            continue
        out.extend(sites(os.path.join(directory, name)))
    return out


COLUMNS = ("module", "function", "marker", "contract", "exit", "stream",
           "caller")


def csv_table(rows) -> str:
    """The `--csv` table, so a reader can take the census without re-running it.

    A string rather than a write to stdout because `--check` diffs the same
    bytes this prints, and the committed file carries this module's own CRLF
    terminator -- `trace_xdata_refs.check_table` reads it with `newline=""` for
    exactly that reason, so the comparison is the family's rather than a second
    implementation. Column order is by what a reader asks first: which module,
    which function, then what it does about it. `lineno` is projected out --
    it is in the row for `--report` and is not a column here, because a line
    number in the file `--check` diffs is a value every merge that grows a
    listed module has to edit.
    """
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, restval="",
                       extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


def report(rows) -> None:
    """The census grouped by contract, for a reader who wants the shape."""
    print(f"PD_MARKER call-site census -- searched {repo_path(TOOLS_DIR)} by "
          "name and by AST, excluding test_*.py\n")
    print("A site this walk does not reach is 'not found by this method', not "
          "'there are\n  none': the marker read through an alias, or the "
          "comparison in a helper the walk\n  does not follow, has no row.\n")
    for contract in CONTRACTS:
        here = [r for r in rows if r["contract"] == contract]
        if not here:
            continue
        print(f"{contract} -- {MEANING[contract]}")
        for r in here:
            extra = f"  exit={r['exit']}" if r["exit"] else ""
            if r["caller"]:
                extra += f"  callers={r['caller']}"
            print(f"  {r['module']}:{r['lineno']} {r['function']}() "
                  f"[marker {r['marker']}]{extra}")
        print()
    unsearched = [d for d in ("bios/tools", "windows/tools")
                  if os.path.isdir(os.path.join(REPO, d))]
    if unsearched:
        print("Not searched, and nothing here is a claim about them: "
              + ", ".join(unsearched) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", action="store_true",
                    help="write the census as CSV on stdout")
    ap.add_argument("--check", nargs="?", const=COMMITTED_CSV, metavar="PATH",
                    help="diff this run against a committed table and exit "
                         "non-zero on any difference; implies --csv (default: "
                         f"{repo_path(COMMITTED_CSV)})")
    ap.add_argument("--contract", choices=CONTRACTS,
                    help="show only the sites with this contract")
    ap.add_argument("--module", metavar="NAME",
                    help="show only the sites in this module")
    args = ap.parse_args()

    if args.check is not None and (args.contract or args.module):
        # Said rather than quietly diffing a subset: a `--check` that filtered
        # first would report every row it dropped as a difference, and the
        # reason would read as a changed census.
        ap.error("--check is about the whole table; it cannot be combined with "
                 "--contract or --module")

    rows = census()
    if args.contract:
        rows = [r for r in rows if r["contract"] == args.contract]
    if args.module:
        rows = [r for r in rows if r["module"] == args.module]

    if args.csv or args.check is not None:
        table = csv_table(rows)
        if args.check is not None:
            return check_table(table, args.check)
        sys.stdout.write(table)
        return 0
    report(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
