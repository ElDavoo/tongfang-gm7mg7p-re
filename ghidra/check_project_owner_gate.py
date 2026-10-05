#!/usr/bin/env python3
"""Hold two things about the committed Ghidra projects that a driver cannot
check for itself: that each one still records an owner, and that each driver
which copies a project for a run still retakes it on the copy.

**Why this is a check and not a comment.** Every committed `.rep` records
`VALUE="dave"` in its `project.prp`, and `analyzeHeadless` refuses a project
owned by anyone else -- `ghidra.util.NotOwnerException`, at the open, before a
pre-script runs. `ghidra/project_owner.py` is the rewrite that makes the
disposable copy openable, and `docs/findings/ghidra-project-owner.md` carries
the measurement. What is left open is the half a driver cannot see: both drivers
now call the rewrite from one function each and preflight the result, and a
rewrite deleted from either of those functions is caught by that driver's own
`--self-test`. **But neither driver's self-test looks at the other driver, at
the committed projects' own state, or at the third site** -- and this file is the
one place all three are visible together, which is what makes it a gate rather
than a second copy of what the drivers already assert.

**What is asserted, and what is not.** For each committed project named below:
that `project.prp` is readable and carries a non-empty OWNER state. For each
driver that copies a committed project to scratch: that its copy path reaches
`project_owner.rewrite_owner`. Both are properties of committed text, so they are
cheap, need no Ghidra and no image, and do not move when an annotation row is
added. **Nothing here claims a project opens.** That is a run's evidence
(`--self-test --oracle`), it needs a real export, and this file reads no
firmware and starts no JVM.

**The third site is reported, not required.** `windows/tools/decompile_native.py`
opens the committed project in place and makes no scratch copy, so "retake the
copy" has nothing to attach to there and requiring it would be a claim about a
mechanism that site does not have. It is in `NO_COPY_SITE` so the omission is a
named, deliberate state rather than a hole in a scan, and `--check` prints it.

**This asserts properties, never a census.** Not how many projects there are, not
how many drivers call the rewrite, not how many rows anything has: those are
values every landing edit has to touch, which is the shape
`CLAUDE.md` records costing this repository more than the checks were worth. A
new project or a fourth driver is a new row here and nothing else.

**What a green run is not.** It says the committed owner state is present and
the drivers still normalise their copies. It does not say the rewrite is
*sufficient* for the open, that the `.gbf` records inside the database are not a
second gate, or that any export has run.

Usage:
    python3 ghidra/check_project_owner_gate.py --check
    python3 ghidra/check_project_owner_gate.py --self-test
"""

import argparse
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, HERE)

import project_owner  # noqa: E402  (the path insert above is what makes this work)

# The committed projects, as the paths Ghidra is handed -- one row per component,
# so a project added later is a row here and nothing else.
# `windows/ghidra/project` is in it because a project nobody copies is still a
# project an export opens, and its owner state is the same committed fact.
PROJECTS = (
    os.path.join("ec", "ghidra", "project", "ec.rep"),
    os.path.join("bios", "ghidra", "project", "bios.rep"),
    os.path.join("windows", "ghidra", "project", "uniwill_native.rep"),
)

# The drivers that copy a committed project to scratch for a run, so "retake the
# owner on the copy" is a mechanism they have and a rewrite in them is expected.
# A driver added here is a new row and nothing else.
COPY_SITES = (
    os.path.join("ec", "tools", "build_ec_decompile.py"),
    os.path.join("bios", "tools", "bios_extract.py"),
)

# Drivers that open a committed project *in place*, with no scratch copy, so the
# owner rewrite has nothing to attach to. Named rather than skipped, so the scan
# below reports "this site has no copy" instead of saying nothing at all about
# it -- a driver that moves from this list to `COPY_SITES` is a real change, and
# one that moves the other way silently is the case this exists to make visible.
NO_COPY_SITE = (
    os.path.join("windows", "tools", "decompile_native.py"),
)


def project_problems(rep_dir):
    """What is wrong with one committed project's owner state, as a list of
    strings; empty is a pass.

    Deliberately `expect_user=None`: this asks what the committed project
    records, not whether *this* user may open it. The committed owner is
    expected to be somebody else -- that is the whole premise -- so asking for
    the running user here would report the tree red on the machine that happens
    to match, and pass on the machine that cannot run.
    """
    problems = project_owner.owner_problems(rep_dir)
    if not problems:
        return []
    return ["%s: %s" % (os.path.relpath(rep_dir, REPO), p)
            for p in problems]


def _names_a_project(node):
    """Whether an expression names a Ghidra project directory.

    Read off the AST -- the identifiers in it, and the string literals a
    `os.path.join` carries -- rather than off the line, so a driver that spelled
    the source differently is still seen. `PROJECT`, `project_dir` and
    `os.path.join(work, "project-copy")` all match; `src`, `scratch` and
    `out_fn` do not.

    The word is the whole of the test, and that is the honest limit of it: a
    driver that copied a project under a name carrying no `project` in it would
    not be checked. The alternative -- resolving each argument through the
    module's own assignments to see whether it lands on a `.rep` -- buys a
    rename-proof check at the cost of a dataflow pass over three call sites,
    and a check that cannot follow a rename is not more trustworthy, only
    quieter. `driver_problems` reports a driver it found no project copy in, so
    the omission shows up as a question rather than as silence.
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and "project" in child.id.lower():
            return True
        if isinstance(child, ast.Attribute) and "project" in child.attr.lower():
            return True
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if "project" in child.value.lower():
                return True
    return False


def _copies_a_project(tree):
    """-> the names of the functions in a parsed driver that `shutil.copytree`
    a Ghidra project into a scratch directory.

    The source argument is what decides it, and the destination alone would be
    wrong: both drivers also copytree *out* of a run -- per-program decompile
    directories into `OUTDIR`, a listings directory into the tree -- and none of
    those copies is a project Ghidra is then asked to open. Requiring a rewrite
    on all of them would be requiring a mechanism those copies do not have.
    """
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if not (isinstance(func, ast.Attribute)
                    and func.attr == "copytree"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "shutil"):
                continue
            if call.args and _names_a_project(call.args[0]):
                out.append(node.name)
                break
    return out


def _call_graph(tree):
    """-> ({name: {names it calls}}, {names whose body calls rewrite_owner}).

    Built from the module's own `def`s, so a call to a name defined elsewhere --
    `shutil.copytree`, a builtin -- is simply not an edge and does not become a
    dead end to walk.
    """
    funcs = {n.name: n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef)}
    edges = {name: set() for name in funcs}
    retakes = set()
    for name, node in funcs.items():
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if isinstance(func, ast.Attribute) and func.attr == "rewrite_owner":
                retakes.add(name)
            elif isinstance(func, ast.Name) and func.id in funcs:
                edges[name].add(func.id)
    # Undirected, because the direction that matters is the one a future split
    # would happen to put the rewrite on: a helper that makes the copy and a
    # caller that retakes it is the same mechanism as one function that does
    # both, and a check that could only see one of those two shapes would report
    # a correct driver as broken the day somebody tidied it.
    both = {name: edges[name] | {caller for caller, callees in edges.items()
                                 if name in callees}
            for name in funcs}
    return both, retakes


def _reaches_rewrite_owner(tree, func_name, graph=None):
    """Whether a copy in `func_name` is joined to an owner rewrite in the same
    module, in either call direction.

    Not "does this function's body call the helper". That is red on a driver
    which does the copy in a helper and the rewrite at the call site -- both real
    drivers are one line away from that shape -- and it is also blind to the
    opposite error, a rewrite called on a project nobody copies.

    **The limit, stated rather than hidden:** joining the two in one component is
    weaker than showing the rewrite is applied to *this* copy. Deciding that
    needs the argument each call site passes, which is a dataflow pass over code
    whose every real instance is a single function that does both. What this
    rules out is the failure that has actually happened -- the rewrite deleted
    from the copy path -- and it rules it out without going red on a rename.
    """
    edges, retakes = graph if graph else _call_graph(tree)
    if func_name not in edges:
        return False
    seen = set()
    pending = [func_name]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        if name in retakes:
            return True
        pending += [n for n in edges.get(name, ()) if n not in seen]
    return False


def driver_problems(repo, rel):
    """What is wrong with one driver's project-copy path, as a list of strings.

    Three refusals, and the first is the one that matters: a driver that copies
    a committed project and no longer retakes it cannot open, and the failure
    surfaces minutes later as a `NotOwnerException` in a log rather than here.
    A driver that cannot be parsed is refused too, and reported as that, because
    a scan that found nothing in an unreadable file would otherwise report
    nothing found -- which is what a clean run reports.
    """
    path = os.path.join(repo, rel)
    try:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        tree = ast.parse(source)
    except OSError as exc:
        return ["%s: does not read: %s" % (rel, exc.strerror)]
    except SyntaxError as exc:
        return ["%s: does not parse: %s" % (rel, exc)]
    copies = _copies_a_project(tree)
    if not copies:
        return ["%s: copies no project, so there is no owner rewrite to check "
                "for; if it means to, this is the row that says so"
                % rel]
    out = []
    graph = _call_graph(tree)
    for name in copies:
        if not _reaches_rewrite_owner(tree, name, graph):
            out.append("%s: %s() copies a project and no owner rewrite is "
                       "reachable from it, so the copy inherits the committed "
                       "owner and analyzeHeadless raises NotOwnerException at "
                       "the open, before it reads a single annotation"
                       % (rel, name))
    return out


def check(repo=REPO, quiet=False):
    """Every committed project and every copy site. 0 clean, 1 on a finding."""
    problems = []
    for rel in PROJECTS:
        problems += project_problems(os.path.join(repo, rel))
    for rel in COPY_SITES:
        problems += driver_problems(repo, rel)

    for problem in problems:
        print(problem)
    if problems:
        print("%d project-owner gate problem(s) found." % len(problems))
        return 1
    if not quiet:
        print("project owner gate: every committed project carries an OWNER "
              "state, and every driver that copies one retakes it on the copy.")
        for rel in NO_COPY_SITE:
            print("  note  %s opens its project in place and makes no scratch "
                  "copy, so there is no owner rewrite to check for there." % rel)
    return 0


# --------------------------------------------------------------------------
# The refusals, over fixtures written to be known-wrong
# --------------------------------------------------------------------------

PRP_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<FILE_INFO>
    <BASIC_INFO>
        <STATE NAME="OWNER" TYPE="string" VALUE="dave" />
    </BASIC_INFO>
</FILE_INFO>
"""

DRIVER_GOOD = '''\
import os
import shutil

import project_owner

PROJECT = "/somewhere/project"

def copy_project_for_export(work):
    copy_dir = os.path.join(work, "project-copy")
    shutil.copytree(PROJECT, copy_dir)
    rep_dir = os.path.join(copy_dir, "ec.rep")
    project_owner.rewrite_owner(rep_dir, work)
    return copy_dir
'''

# The known-bad cases, as (label, source, what the problem must mention). Each
# is the good driver with exactly one thing wrong, so a check that has stopped
# discriminating cannot pass all of them by accident.
DRIVER_BAD = (
    ("no rewrite",
     DRIVER_GOOD.replace("    project_owner.rewrite_owner(rep_dir, work)\n", ""),
     "no owner rewrite is reachable"),
    # The two halves of the same over-claim, and the one that decides how the
    # destination is read: a driver copying something that is not a project is
    # *not* a driver with a missing rewrite, because it never had a project to
    # rewrite. A check that flagged both would be reporting the shape of
    # `shutil.copytree` rather than the property.
    ("a copy of something else only",
     DRIVER_GOOD.replace("shutil.copytree(PROJECT, copy_dir)",
                         "shutil.copytree(other, copy_dir)"),
     "copies no project"),
    ("no copytree at all",
     DRIVER_GOOD.replace("    shutil.copytree(PROJECT, copy_dir)\n", ""),
     "copies no project"),
    ("a rewrite under another name",
     DRIVER_GOOD.replace("rewrite_owner(rep_dir, work)",
                         "retake(rep_dir, work)"),
     "no owner rewrite is reachable"),
    ("unparseable",
     DRIVER_GOOD.replace("def copy_project_for_export(work):",
                         "def copy_project_for_export(work)\n"),
     "does not parse"),
)

# The good driver with the copy split across two functions the way both real
# drivers split it. `_calls_rewrite_owner` follows the module's own call graph
# rather than searching one body, so this is the case that says so: a body-only
# search reports this correct driver as never retaking anything, and would be
# red on the tree.
DRIVER_SPLIT = '''\
import os
import shutil

import project_owner

PROJECT = "/somewhere/project"

def copy_project_for_export(work):
    retake(make_the_copy(work), work)
    return os.path.join(work, "project-copy")


def make_the_copy(work):
    copy_dir = os.path.join(work, "project-copy")
    shutil.copytree(PROJECT, copy_dir)
    return os.path.join(copy_dir, "ec.rep")


def retake(rep_dir, work):
    project_owner.rewrite_owner(rep_dir, work)
'''


def _driver_fixture(tmp, name, source):
    path = os.path.join(tmp, name)
    with open(path, "w") as handle:
        handle.write(source)
    return name


def self_test():
    """The refusals, plus the good cases they are refusals of. 0 pass, 1 fail."""
    import shutil
    import tempfile

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print("  %s  %s" % ("ok  " if cond else "FAIL", label)
              + ("  (%s)" % detail if detail and not cond else ""))
        if not cond:
            ok = False

    print("check_project_owner_gate.py --self-test")

    # A project that reads and names an owner: the known-good case first, because
    # a guard exercised only on known-bad input cannot tell "clean" from "never
    # ran". This fixture rather than the committed tree, so the answer is known
    # by construction rather than by whatever the repository currently records.
    tmp = tempfile.mkdtemp()
    try:
        good = os.path.join(tmp, "good.rep")
        os.makedirs(good)
        with open(os.path.join(good, "project.prp"), "w") as handle:
            handle.write(PRP_TEXT)
        check("a project whose project.prp carries an OWNER has no problem",
              not project_problems(good), str(project_problems(good)))
        check("and the owner it records is read back, not guessed",
              project_owner.read_owner(good) == "dave")

        faults = (
            ("no project.prp", None),
            ("not XML", "\x00binary\n"),
            ("no OWNER state", PRP_TEXT.replace(
                'NAME="OWNER" TYPE="string" VALUE="dave"',
                'NAME="OWNERX" TYPE="string" VALUE="dave"')),
            ("empty owner", PRP_TEXT.replace('VALUE="dave"', 'VALUE=""')),
        )
        for label, text in faults:
            # A directory per fault, or the second case is checking the first
            # one's leftover -- a loop that only ever creates its fixture once is
            # a loop whose later assertions are about nothing.
            rep = os.path.join(tmp, "broken-%s.rep" % label.replace(" ", "-"))
            os.makedirs(rep)
            if text is not None:
                with open(os.path.join(rep, "project.prp"), "w") as handle:
                    handle.write(text)
            problems = project_problems(rep)
            check("%s is reported" % label, len(problems) == 1, str(problems))

        _driver_fixture(tmp, "good_driver.py", DRIVER_GOOD)
        problems = driver_problems(tmp, "good_driver.py")
        check("a driver that copies and retakes has no problem",
              not problems, str(problems))
        _driver_fixture(tmp, "split_driver.py", DRIVER_SPLIT)
        problems = driver_problems(tmp, "split_driver.py")
        check("a driver that copies in one function and retakes in another has "
              "no problem either -- the call graph is followed, not one body",
              not problems, str(problems))

        for label, source, want in DRIVER_BAD:
            _driver_fixture(tmp, "bad_driver.py", source)
            problems = driver_problems(tmp, "bad_driver.py")
            check("a driver with %s is reported" % label,
                  len(problems) == 1 and want in problems[0], str(problems))
        missing = driver_problems(tmp, "no_such_driver.py")
        check("a driver that does not read is reported, rather than passing "
              "for one that does not copy",
              len(missing) == 1 and "does not read" in missing[0],
              str(missing))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="the committed projects and driver copy sites")
    parser.add_argument("--self-test", action="store_true",
                        help="the refusals, over fixtures written to be "
                             "known-wrong")
    parser.add_argument("--repo", default=REPO, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    return check(args.repo)


if __name__ == "__main__":
    sys.exit(main())