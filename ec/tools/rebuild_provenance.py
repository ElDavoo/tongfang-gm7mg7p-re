#!/usr/bin/env python3
"""Does a `--mode rebuild-project` from the committed inputs re-derive the
names the export carries at rowless addresses?

`docs/findings/named-without-a-row.md` §6 leaves that open, and says what
answering it needs: a rebuild, which writes the project database, which is why
that write-up cannot have run one. This runs it, in a scratch copy of the
repository, and reads the answers back out.

**Why the copy, and why this tool exists at all.** In the committed tree
`build_ec_decompile.py` resolves `project_dir = PROJECT` -- the committed
`ec/ghidra/project` -- and `write_outputs()` opens with `shutil.rmtree(OUTDIR)`
where `OUTDIR` is the committed `ec/decompiled`. A rebuild run in the tree
therefore destroys both: the database `.gitattributes` makes git refuse to
merge, and every exported `.c` and `.asm`. Copying the repository is what keeps
that from being a way to lose a working tree, so copying it is a step this tool
performs rather than a habit the reader is asked to remember:

  * `--run` **refuses** a scratch path inside the repository, before anything is
    copied. The refusal is a self-test case, not a comment.
  * it copies the tree with `.git` excluded, and runs the rebuild in the copy.
    No committed `.gpr`, `.rep`, `.c` or `.asm` is opened for writing.
  * the `NotOwnerException` a rebuild hits -- the committed `ec.rep/project.prp`
    carries `<STATE NAME="OWNER" ... VALUE="dave" />` -- is cleared with
    `JAVA_TOOL_OPTIONS=-Duser.name=dave`, which edits no file anywhere. Not even
    in the copy. The `.prp` edit §9 used by hand stays a documented fallback for
    a JVM that will not take the option.

**A partial run is never diffed.** This is the property the tool exists to hold.
A rebuild killed part-way leaves a short `ec/decompiled` behind, and diffing
that against the committed tree produces a report full of differences that read
exactly like the finding being hunted. So no diff is taken until the rebuild
exits zero *and* the copy's own manifest accounts for the copy's own export. A
run that fails either test reports **not measured** and exits non-zero, which is
a result: the answers stay open rather than being answered by a truncated run.

**Why the two questions are kept apart.** §6 asks whether a rebuild re-derives
these names (Q1), and separately what the rebuilt export says about the whole
tree (Q3). A rebuild re-imports, re-seeds and re-analyses, and the seed set has
moved many times since the committed database was built, so a difference
anywhere is expected to be about seeds and analysis state rather than about the
handful of addresses in question. Reading Q1 off the whole-tree diff would be
wrong in both directions. Q1 is therefore read off the `name` column at the
addresses themselves; the diff is reported beside it, not under it.

**Q1 and Q2 read the same column.** Q1 is the census population -- the index
rows marked `annotated=yes` that no `ghidra-functions.csv` row backs, which is
§6's population and is derived here from `second_copy_census.py` rather than
transcribed, so a population that moves is a population the tool follows. Q2 is
the four `pd` call sites §6 names, which took rows of their own in #489 and are
therefore a fixed list.

**No `--check`, deliberately.** The answers come from a rebuild, so there is
nothing here a gate could ratchet on without a Ghidra run and a scratch copy
per run. What a `--check` *could* assert -- that the committed `.c` files and
`manifest.csv` are unaltered -- is already held by `c-digests.csv` and
`build_ec_decompile.py --check`, and a second check of it here would be a check
that has quietly stopped checking anything else.

**Not wired into any gate.** `.github/scripts/agent-gates.sh` is
template-copied and an agent branch cannot carry a change to it, so this tool is
invoked directly, exactly as `second_copy_census.py` is.

Usage:
    python3 ec/tools/rebuild_provenance.py --run          # the measurement
    python3 ec/tools/rebuild_provenance.py --run --scratch /var/tmp/ec
    python3 ec/tools/rebuild_provenance.py --self-test    # no Ghidra, no network
"""

import argparse
import collections
import contextlib
import csv
import io
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import second_copy_census

EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
# The owner in the committed `ec.rep/project.prp`, which is the whole of
# #572's NotOwnerException. Supplied to the JVM rather than written into the
# file: the three write-ups that hit it (`docs/findings.md`, and
# `pd-unannotated-listings.md` and `pd-07d0-accessor-stubs.md` under
# `docs/findings/`) all say the option, and none of them edited the copy.
PROJECT_OWNER = "dave"
OWNER_OPTION = "-Duser.name=%s" % PROJECT_OWNER

# The tree, relative to the copy's root, and the one path inside it a rebuild
# writes. Both are compared by this tool and neither is copied back.
DECOMPILED_REL = os.path.join("ec", "decompiled")
MANIFEST_REL = os.path.join("ec", "ghidra", "manifest.csv")
# The two index CSVs, named rather than joined: `tree_differences()` is handed a
# `ec/decompiled` directory and walks it, so what it matches on is a name
# relative to that directory, while the paths above are relative to the tree's
# root. One spelling of each, so the two cannot be crossed again.
INDEX_NAME = "index.csv"
LISTING_NAME = "listing-index.csv"
INDEX_REL = os.path.join(DECOMPILED_REL, INDEX_NAME)
LISTING_REL = os.path.join(DECOMPILED_REL, LISTING_NAME)

# The four `pd` addresses §6 asks about. They are a list rather than something
# derived, because #489 gave each a row of its own and they are no longer in the
# census population -- the census reports on the names that are still rowless,
# and these four are the ones it can no longer see.
PD_CALL_SITES = ("3497", "998B", "9C1B", "9C4D")

# The kinds a difference can be, and the order they are reported in. A kind is
# the answer to "is it an index.csv row, a .c or a .asm" that issue #623 asks
# for, so it is a closed vocabulary rather than a suffix anyone can widen by
# adding a file. The order is the reading order of the question, not an
# alphabetical accident, and "the first difference" is the first in it.
KINDS = ("index-row", "listing-row", "manifest-column", "c", "asm",
         "missing-from-copy", "new-in-copy", "other")

# How much of the committed export a run has to have produced before its diff
# is read at all, as a fraction of the committed count, per program.
#
# A floor and not an equality, and that is the whole design: a rebuild is
# allowed to come out different from the committed export -- that is the
# question -- so a guard that demanded they match would refuse the very result
# it exists to catch, and report "not measured" on the run that measured
# something. What a floor refuses is the other shape, a run that stopped early
# and left a tenth of the export missing, which is not a result about
# provenance but an unfinished job. Missing a program outright is refused
# exactly, because that is a run that did not do the work rather than one that
# did it differently.
TRUNCATION_FLOOR = 0.9

# The default ceiling on the rebuild. Three programs, a fresh import, auto
# analysis and 2,710 decompiles is a long job; the default is a ceiling rather
# than a budget, and a run that reaches it is reported as not measured rather
# than as an answer.
DEFAULT_TIMEOUT = 7200

# How long to wait for a signalled build to be gone before giving up on reaping
# it. It is a bound on the wait, not a second ceiling: a run that reaches the
# timeout is reported as not measured either way, and this only decides whether
# the tool leaves a zombie behind on its way out.
KILL_GRACE = 30

# What the copy must not carry, and why each is here. `.git` is the repository
# history, which no build input reads and which is the largest single thing in
# the tree. `__pycache__` is bytecode this repository's own tools wrote earlier
# in the same run, and copying it would put a stale module in front of a
# rebuild.
COPY_EXCLUDE = (".git", "__pycache__", "*.pyc")


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def within(path, root):
    """Whether `path` is `root` or something under it, both realpath'd.

    realpath on both sides because the answer has to survive the runner's
    symlinked temp directory: `/tmp` is a symlink on macOS, and a comparison
    of the unresolved strings would decide that a scratch directory under it is
    outside a repository that is itself under it.
    """
    a = os.path.realpath(path)
    b = os.path.realpath(root)
    return a == b or a.startswith(b.rstrip(os.sep) + os.sep)


def scratch_refusal(repo, scratch):
    """Why `scratch` may not be used, or None when it may.

    The check that keeps a rebuild out of the tree it is measuring. It is a
    function rather than a line in `--run` so the self-test can hold it against
    a fixture repository, and it is asked before anything is copied -- a refusal
    that deleted first and apologised later would be the failure it exists to
    prevent.
    """
    if within(scratch, repo):
        return ("refusing to run in %s: the scratch path is inside the "
                "repository at %s, and a rebuild there rewrites the committed "
                "project database and the whole export. Point --scratch "
                "somewhere else." % (scratch, repo))
    return None


def program_counts(index_rows):
    """-> {program: row count} over an index.csv, in the order the rows come."""
    counts = collections.Counter(r.get("program") for r in index_rows)
    return dict(counts)


def keyed_by(rows, key):
    return {tuple(r[k] for k in key): r for r in rows}


def csv_field_differences(have_rows, want_rows, key, label):
    """Differences between two CSVs, per field of a per-key row.

    Reported this way rather than as a byte diff because the reader's question
    is which *row* moved and which *column* of it, and a file-level difference
    on a 2,700-row export answers neither. A key on one side only is a whole row
    added or dropped, which is its own kind rather than a field that changed.
    """
    out = []
    have = keyed_by(have_rows, key)
    want = keyed_by(want_rows, key)
    for k in sorted(set(have) | set(want)):
        a, b = have.get(k), want.get(k)
        where = "%s %s" % (label, " ".join(k))
        if a is None:
            out.append({"kind": "new-in-copy", "where": where,
                        "detail": "no such row in the committed tree"})
            continue
        if b is None:
            out.append({"kind": "missing-from-copy", "where": where,
                        "detail": "no such row in the rebuilt export"})
            continue
        for column in a:
            if a.get(column) != b.get(column):
                out.append({"kind": "index-row" if label == "index.csv"
                            else "listing-row",
                            "where": where,
                            "detail": "%s: %r -> %r" % (column, b.get(column),
                                                         a.get(column))})
    return out


def tree_differences(committed, copy):
    """Differences between two `ec/decompiled` trees, classified by kind.

    The two index CSVs are compared row by row and the manifest separately; every
    other file is compared as bytes, because a `.c` that differs is a finding in
    its own right and there is no row to point at inside it.
    """
    out = []
    for name, kind in ((INDEX_NAME, "index-row"), (LISTING_NAME, "listing-row")):
        a, b = os.path.join(committed, name), os.path.join(copy, name)
        if not (os.path.isfile(a) and os.path.isfile(b)):
            out.append({"kind": "missing-from-copy" if os.path.isfile(a)
                        else "new-in-copy", "where": name,
                        "detail": "the file is not on both sides"})
            continue
        out += csv_field_differences(read_csv(b), read_csv(a),
                                     ("program", "addr"), name)
    for root, _dirs, names in os.walk(committed):
        for leaf in names:
            path = os.path.join(root, leaf)
            rel = os.path.relpath(path, committed)
            if rel in (INDEX_NAME, LISTING_NAME):
                continue
            other = os.path.join(copy, rel)
            if not os.path.isfile(other):
                out.append({"kind": "missing-from-copy", "where": rel,
                            "detail": "in the committed tree, not in the copy"})
            elif open(path, "rb").read() != open(other, "rb").read():
                kind = "c" if leaf.endswith(".c") else (
                    "asm" if leaf.endswith(".asm") else "other")
                out.append({"kind": kind, "where": rel, "detail": "bytes differ"})
    for root, _dirs, names in os.walk(copy):
        for leaf in names:
            rel = os.path.relpath(os.path.join(root, leaf), copy)
            if rel in (INDEX_NAME, LISTING_NAME):
                continue
            if not os.path.isfile(os.path.join(committed, rel)):
                out.append({"kind": "new-in-copy", "where": rel,
                            "detail": "in the copy, not in the committed tree"})
    return out


def manifest_differences(committed_path, copy_path):
    out = []
    if not (os.path.isfile(committed_path) and os.path.isfile(copy_path)):
        return [{"kind": "missing-from-copy"
                 if os.path.isfile(committed_path) else "new-in-copy",
                 "where": MANIFEST_REL, "detail": "the file is not on both sides"}]
    out += csv_field_differences(read_csv(copy_path), read_csv(committed_path),
                                 ("program",), "manifest.csv")
    for d in out:
        d["kind"] = "manifest-column"
    return out


def truncation_problems(committed_root, copy_root, exit_code):
    """Whether this run finished, or whether its diff may not be read.

    Three questions, and the third is the one that makes the first two worth
    asking. The rebuild has to have exited zero; every program the committed
    manifest records has to be in the copy's manifest as well, because a program
    that is simply absent is a run that did not do the work; and each program's
    rebuilt count has to clear `TRUNCATION_FLOOR` of the committed one, which is
    the signal that separates "the export came out different" from "the export
    stopped coming out".

    It reads the copy's own files only. A rebuild is allowed to disagree with the
    committed tree -- that is what it is being run to find out -- so the only
    question asked of the committed side is how much of the export is missing.
    """
    out = []
    if exit_code != 0:
        out.append("the rebuild exited %s, so whatever it left behind is not a "
                   "result" % (exit_code if exit_code is not None else "on a signal"))
    c_manifest = os.path.join(committed_root, MANIFEST_REL)
    x_manifest = os.path.join(copy_root, MANIFEST_REL)
    if not os.path.isfile(x_manifest):
        out.append("%s is not in the copy, so the run recorded no manifest and "
                   "there is nothing to check the export against" % MANIFEST_REL)
        return out
    if not os.path.isfile(c_manifest):
        out.append("%s is missing from the tree this run was copied from, so "
                   "there is no baseline to compare a short export against"
                   % MANIFEST_REL)
        return out
    committed = {r.get("program"): r for r in read_csv(c_manifest)}
    rebuilt = {r.get("program"): r for r in read_csv(x_manifest)}
    for program in sorted(committed):
        if program not in rebuilt:
            out.append("the rebuilt manifest carries no %s row, so that program "
                       "was not exported" % program)
            continue
        try:
            want = int(committed[program]["functions"])
            got = int(rebuilt[program]["functions"])
        except (KeyError, TypeError, ValueError):
            out.append("%s: a `functions` count in one of the two manifests is "
                       "not a number, so the run cannot be checked" % program)
            continue
        if got < want * TRUNCATION_FLOOR:
            out.append("%s: the rebuild exported %d function(s) against the "
                       "committed tree's %d, under the %.0f%% floor, so this "
                       "reads as a run that stopped early rather than as a "
                       "result about provenance"
                       % (program, got, want, TRUNCATION_FLOOR * 100))
    return out


def counter_moves(committed_rows, rebuilt_rows):
    """The manifest counters that moved, per program, committed against rebuilt.

    The whole-tree diff says *that* the two exports differ; this says which
    counters account for it, which is the difference between a rebuild that
    found more functions and one that could not resolve rows the committed
    database resolves. `seeds_applied` is printed even when it holds still,
    because that is the reading which keeps the other two honest: a rebuild
    seeded from a different seed set would move them for a reason that has
    nothing to do with the database.
    """
    have = {r.get("program"): r for r in committed_rows}
    want = {r.get("program"): r for r in rebuilt_rows}
    columns = ("functions", "seeds_applied", "annotations_applied",
               "annotations_unmatched", "functions_named")
    out = ["  program  %s" % "  ".join("%-20s" % c for c in columns)]
    for program in sorted(set(have) | set(want)):
        a, b = have.get(program), want.get(program)
        if a is None or b is None:
            out.append("  %-8s (one manifest has no %s row)" % (program, program))
            continue
        cells = []
        for column in columns:
            cells.append("%-20s" % ("%s -> %s" % (a.get(column), b.get(column))
                                    if a.get(column) != b.get(column) else
                                    a.get(column)))
        out.append("  %-8s %s" % (program, "  ".join(cells)))
    return out


def is_placeholder(name):
    """Whether `name` is one of the forms Ghidra writes for itself.

    Read out of `isPlaceholderName()` in `TongFang.java` by the exporter's own
    parser rather than transcribed here, so a prefix added to the Java is
    recognised without a second list to keep in step. A name this returns true
    for at a rowless address is a finding and not an answer: it is a name no
    committed CSV row wrote, in the namespace the exporter reserves for Ghidra's
    own output.
    """
    from build_ec_decompile import placeholder_name_tests
    for kind, literal in placeholder_name_tests():
        if (name or "").startswith(literal) if kind == "startsWith" \
                else (name or "") == literal:
            return True
    return False


def name_at(rows, program, addr):
    """The `name` an index.csv carries at one address, or None if it has no
    row there at all."""
    for r in rows:
        if r.get("program") == program and r.get("addr", "").upper() == addr.upper():
            return r.get("name")
    return None


def name_answers(have_rows, want_rows, sites, title):
    """Q1 and Q2, as a table: what each address is called in each tree.

    `have_rows` is the rebuilt export and `want_rows` the committed one, so the
    columns read committed-then-rebuilt and a row whose two cells agree is the
    shape of the result worth having. An address the copy does not carry at all
    is reported as absent rather than skipped: an address that stopped being
    exported is a different answer from one whose name changed, and reading it as
    a blank would collapse the two.
    """
    lines = ["## %s" % title, "",
             "  program addr    committed name              rebuilt name"
             "              reading"]
    verdicts = []
    for program, addr in sites:
        was, now = name_at(want_rows, program, addr), name_at(have_rows, program, addr)
        if now is None:
            verdict = "not exported by the rebuild"
        elif was is None:
            verdict = "no committed row; the rebuild names it `%s`" % now
        elif was == now:
            verdict = "re-derived: the rebuild puts the same name there"
        else:
            verdict = "**differs**: the rebuild puts `%s` there" % now
        if now is not None and was is not None and was != now and is_placeholder(now):
            verdict += " -- and that is a Ghidra placeholder form, a name at a " \
                       "rowless address that no committed input produces"
        lines.append("  %-6s %-7s %-26s %-26s %s"
                     % (program, addr, was or "(no row)", now or "(no row)", verdict))
        verdicts.append((program, addr, was, now, verdict))
    return "\n".join(lines), verdicts


def run_build(copy_root, ghidra, timeout):
    """The rebuild, in the copy, with the owner supplied to the JVM."""
    env = dict(os.environ)
    existing = env.get("JAVA_TOOL_OPTIONS", "").strip()
    env["JAVA_TOOL_OPTIONS"] = (existing + " " + OWNER_OPTION).strip()
    cmd = [sys.executable, os.path.join(copy_root, "ec", "tools",
                                         "build_ec_decompile.py"),
           "--work", os.path.join(copy_root, "work"),
           "--mode", "rebuild-project", "--ghidra", ghidra]
    print("+ (in %s) %s" % (copy_root, " ".join(cmd)))
    print("  JAVA_TOOL_OPTIONS=%s   # %s satisfies the OWNER check in the "
          "copied project.prp without editing any file" % (env["JAVA_TOOL_OPTIONS"],
                                                            OWNER_OPTION))
    try:
        return _wait_for(cmd, copy_root, env, timeout)
    finally:
        if existing:
            print("  note: the caller's own JAVA_TOOL_OPTIONS (%r) was kept and "
                  "the owner option appended to it" % existing)


def _wait_for(cmd, cwd, env, timeout):
    """`cmd`'s exit code, or None when the ceiling arrived first.

    The handle is held rather than left to `subprocess.run`, because the handle
    is the only thing that names the group a timed-out build has to be taken
    down with. `start_new_session=True` is what makes that possible: the child
    leads a group of its own, so the group is the child's pid.
    """
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, start_new_session=True)
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(proc, timeout)
        return None


def _kill_group(proc, timeout):
    """Signal the group a timed-out build left running, and reap the leader.

    `proc.pid` and never `os.getpgid(os.getpid())`. The child was started with
    `start_new_session=True` and is therefore a group leader in its own right,
    so it cannot be in this process's group: our own group is the caller's --
    the shell, the CI step, whatever invoked the tool -- and signalling it
    would take that down instead, leaving the launcher and the JVM untouched.

    Signalling the group rather than the process is the second half, and it is
    why this is not `proc.terminate()`: a launcher signalled on its own orphans
    the JVM it started, and that JVM keeps the copied project locked, so the
    next run in the same scratch directory fails for a reason that has nothing
    to do with the code being measured.
    """
    print("  the rebuild reached the %.0f-minute ceiling; stopping it and "
          "reporting the run as not measured" % (timeout / 60.0))
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except OSError:
        pass
    try:
        proc.wait(timeout=KILL_GRACE)
    except subprocess.TimeoutExpired:
        pass


def copy_tree(repo, scratch):
    """The copy. Returns the path the rebuild runs in."""
    if os.path.isdir(scratch):
        shutil.rmtree(scratch)
    print("  copying %s -> %s (excluding %s)"
          % (repo, scratch, ", ".join(COPY_EXCLUDE)))
    shutil.copytree(repo, scratch, ignore=shutil.ignore_patterns(*COPY_EXCLUDE),
                    symlinks=True)
    return scratch


def run(args):
    repo = os.path.abspath(args.repo)
    scratch = os.path.abspath(args.scratch
                              if args.scratch
                              else os.path.join(tempfile.gettempdir(),
                                                "ec-rebuild-provenance"))
    print("rebuild_provenance.py --run")
    refusal = scratch_refusal(repo, scratch)
    if refusal:
        # Before the copy, before the build, before anything. A refusal that had
        # already made a scratch directory would have made one inside the tree
        # it is refusing to write in.
        print("  %s" % refusal)
        return 1

    copy_root = copy_tree(repo, scratch)
    code = run_build(copy_root, args.ghidra, args.timeout)
    if code is None:
        problems = ["the rebuild did not finish inside %d s" % args.timeout]
    else:
        problems = truncation_problems(repo, copy_root, code)
    log = os.path.join(copy_root, "work", "ghidra.log")
    if os.path.isfile(log):
        owner_failed = "NotOwnerException" in open(log, errors="replace").read()
    else:
        owner_failed = False
    if owner_failed:
        print("  the copy's Ghidra log carries a NotOwnerException, so the "
              "owner option did not take. The fallback, and the one §9 used by "
              "hand, is to edit OWNER in %s's ec/ghidra/project/ec.rep/"
              "project.prp -- in the copy, never in this tree -- and re-run."
              % copy_root)
    if problems:
        print("\n## not measured\n")
        for p in problems:
            print("  %s" % p)
        print("\n  No diff was taken. A run that did not finish produces a "
              "short export, and a diff against a short export is "
              "indistinguishable from the difference being looked for.")
        return 1

    committed_index = read_csv(os.path.join(repo, INDEX_REL))
    rebuilt_index = read_csv(os.path.join(copy_root, INDEX_REL))
    # One read of the annotation CSV, shared by the population and the census.
    # Reading it twice to ask one question is invisible right up until the file
    # is big enough for it to matter.
    ann_rows = second_copy_census.read_csv(second_copy_census.ANNOTATIONS)
    named = second_copy_census.population(committed_index, ann_rows)
    verdicts = second_copy_census.census(named, committed_index, ann_rows)
    sites = [(v["program"], v["addr"]) for v in verdicts]
    print("\n## the run\n")
    print("  the rebuild exited 0 and the copy's manifest accounts for the "
          "copy's export, so what follows is read off a run that finished")
    for program, count in sorted(program_counts(rebuilt_index).items()):
        print("    %-6s %d exported function(s)" % (program, count))
    print()
    for line in counter_moves(read_csv(os.path.join(repo, MANIFEST_REL)),
                              read_csv(os.path.join(copy_root, MANIFEST_REL))):
        print(line)

    print()
    table, _ = name_answers(rebuilt_index, committed_index, sites,
                            "Q1 -- the names at the census addresses, "
                            "committed against rebuilt")
    print(table)
    print("\n  The population is read from `second_copy_census.py` rather than "
          "transcribed, so it is the same list `--check` prints.")

    print()
    table, _ = name_answers(rebuilt_index, committed_index,
                            [("pd", a) for a in PD_CALL_SITES],
                            "Q2 -- the four `pd` call sites")
    print(table)

    diffs = (tree_differences(os.path.join(repo, DECOMPILED_REL),
                              os.path.join(copy_root, DECOMPILED_REL))
             + manifest_differences(os.path.join(repo, MANIFEST_REL),
                                    os.path.join(copy_root, MANIFEST_REL)))
    diffs.sort(key=lambda d: (KINDS.index(d["kind"]) if d["kind"] in KINDS
                              else len(KINDS), d["where"], d["detail"]))
    print("\n## Q3 -- the rebuilt export against the committed tree\n")
    if not diffs:
        print("  0 differences: index.csv, listing-index.csv, every .c and "
              "every .asm, and manifest.csv all match the committed tree "
              "byte for byte")
    else:
        tally = collections.Counter(d["kind"] for d in diffs)
        print("  %d difference(s): %s"
              % (len(diffs), ", ".join("%d %s" % (n, k) for k, n in tally.items())))
        print("\n  the first, which is the one Q3 asks for:")
        print("    %-19s %s -- %s" % (diffs[0]["kind"], diffs[0]["where"],
                                      diffs[0]["detail"]))
        if len(diffs) > 1:
            print("\n  the rest, capped at 20:")
            for d in diffs[1:21]:
                print("    %-19s %s -- %s" % (d["kind"], d["where"], d["detail"]))
            if len(diffs) > 21:
                print("    ... and %d more; the full listing is the copy's tree "
                      "against this one" % (len(diffs) - 21))

    print("\n## Q4 -- is the committed database reproducible from the committed "
          "inputs?\n")
    print("  %s" % ("Yes, on what this run saw: the rebuild reproduced the "
                    "committed export exactly, so the committed .gpr/.rep is a "
                    "function of ec/firmware/GMxMGxx_11.800 plus the two "
                    "annotation CSVs and nothing else."
                    if not diffs else
                    "No, not entirely: the rebuilt export differs from the "
                    "committed one, so the committed database carries analysis "
                    "state that the committed inputs do not re-derive. Where "
                    "the first difference is a .c or an .asm rather than a CSV "
                    "row, that is a claim about the decompiler's output; where "
                    "it is a CSV row or a manifest column, it is a claim about "
                    "seeds and names, which have moved since the database was "
                    "built. Which of the two it is, is Q3's answer above."))
    print("\n  The copy is left at %s. Nothing in the tree it was copied from "
          "was written." % copy_root)
    return 0


# --------------------------------------------------------------------------
# Self-test -- fixtures, no Ghidra, no network, no copy of this repository
# --------------------------------------------------------------------------

def _fixture_repo(scratch):
    """A tiny two-tree repository, so the classifier and the refusal are held
    against a shape rather than against whatever the committed export happens to
    be today.

    The `.c` and `.asm` names are the real ones -- one program, one address,
    one of each -- because a fixture using names the tool does not recognise
    would pass a classifier that had stopped classifying.
    """
    root = os.path.join(scratch, "repo")
    committed = os.path.join(root, "ec", "decompiled", "common")
    os.makedirs(committed)
    os.makedirs(os.path.join(root, "ec", "ghidra"))
    with open(os.path.join(committed, "0100.c"), "w") as f:
        f.write("// common @ 0100   twice   [named]\nvoid twice(void)\n")
    with open(os.path.join(committed, "0100.asm"), "w") as f:
        f.write("0100     02 00 20 ljmp    0x0020\n")
    with open(os.path.join(committed, "0020.c"), "w") as f:
        f.write("// common @ 0020   twice   [named]\nvoid twice(void)\n")
    rows = [("program", "addr", "name", "out_file"),
            ("common", "0100", "twice", "common/0100.c"),
            ("common", "0020", "twice", "common/0020.c")]
    for name in ("index.csv", "listing-index.csv"):
        with open(os.path.join(root, "ec", "decompiled", name), "w",
                  newline="") as f:
            csv.writer(f).writerows(rows)
    with open(os.path.join(root, "ec", "ghidra", "manifest.csv"), "w",
              newline="") as f:
        csv.writer(f).writerows([("program", "functions", "decompiled", "failed"),
                                 ("common", "2", "2", "0")])
    return root


def _clone_fixture(root, scratch, name):
    """A second copy of the fixture tree, for the rebuild side of a comparison."""
    copy = os.path.join(scratch, name)
    shutil.copytree(root, copy)
    return copy


# A launcher that starts a child of its own and then hangs -- the shape of
# `analyzeHeadless`, without Ghidra -- and a child that says so when it is
# signalled. Sources rather than inline programs, so what the self-test spawns
# can be read next to the assertion it is there to fail.
#
# The child has to announce itself rather than be inspected: a pid belonging to
# a process this one did not fork says nothing reliable about whether the
# process behind it is still running, and nothing at all about whether it was
# ever signalled.
_LAUNCHER = """
import subprocess, sys, time

child = subprocess.Popen([sys.executable, sys.argv[3], sys.argv[1], sys.argv[2]])
open(sys.argv[4], "w").write(str(child.pid))
time.sleep(600)
"""

_GRANDCHILD = """
import signal, sys, time

def signalled(*_):
    with open(sys.argv[2], "w") as f:
        f.write("SIGTERM")
    sys.exit(0)

signal.signal(signal.SIGTERM, signalled)
with open(sys.argv[1], "w") as f:
    f.write("ready")
time.sleep(600)
"""


def _hanging_launcher(box):
    """`box`'s launcher and child scripts, written out. Their paths, in order."""
    out = []
    for name, source in (("launcher.py", _LAUNCHER), ("grandchild.py", _GRANDCHILD)):
        path = os.path.join(box, name)
        with open(path, "w") as f:
            f.write(source)
        out.append(path)
    return out[0], out[1]


def _await_file(path, seconds=30.0):
    """Whether `path` appears within `seconds`, polled.

    A file rather than a pipe, because what is being waited for is a process
    announcing that it is up, and a pipe's other end would be held by a process
    this one does not own.
    """
    end = time.time() + seconds
    while time.time() < end:
        if os.path.isfile(path):
            return True
        time.sleep(0.02)
    return os.path.isfile(path)


def self_test() -> int:
    """What can be wrong on a machine that never runs Ghidra.

    Everything the run answers needs a rebuild, and a rebuild needs Ghidra and
    an hour. What does not are the parts around it -- the diff classification,
    the refusal that keeps a rebuild out of the tree, and the timeout that has
    to take a build's whole process group down -- and each of those is wrong in
    a way that only shows when it is exercised: a classifier that returned
    nothing would report an empty diff beside a rebuild that changed everything,
    a refusal that came after the copy would have already made one, and a
    timeout aimed at the wrong process group would leave the JVM holding the
    copy it was meant to release.
    """
    bad = 0
    print("rebuild_provenance.py --self-test")

    def check(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print("  %s  %s%s" % ("ok  " if ok else "FAIL", label,
                              "" if ok or not detail else "  " + detail))

    # `__enter__` hands back the directory name, so `box` is a path and
    # the object it came from is not needed here.
    with tempfile.TemporaryDirectory(
            prefix="rebuild-provenance-selftest-") as box:
        root = _fixture_repo(box)

        # --- the refusals, all on fixtures ---
        #
        # The refusal, end to end, against a scratch path inside the fixture
        # repository. If it were asked after the copy, this would create
        # `inside/` and the second assertion would catch it.
        inside = os.path.join(root, "inside")
        refused = main(["--run", "--repo", root, "--scratch", inside])
        check("refusal: a rebuild into a path inside the repository is refused",
              refused == 1)
        check("refusal: the refusal happens before anything is copied, so the "
              "tree it refused is untouched", not os.path.exists(inside))
        check("a scratch path outside the repository is not refused",
              scratch_refusal(root, os.path.join(box, "outside")) is None)
        check("the repository itself counts as inside itself, not beside it",
              scratch_refusal(root, root) is not None)

        # The classifier: one .c differing, one .asm differing, one index.csv
        # row differing, and a file present on one side only. Each is a kind
        # Q3 asks to be told apart, so each gets its own assertion.
        copy = _clone_fixture(root, box, "rebuilt")
        with open(os.path.join(copy, "ec", "decompiled", "common", "0100.c"),
                  "w") as f:
            f.write("// common @ 0100   twice   [named]\nvoid twice(int)\n")
        with open(os.path.join(copy, "ec", "decompiled", "common", "0100.asm"),
                  "w") as f:
            f.write("0100     02 00 20 ljmp    0x0020 ; rebuilt\n")
        os.remove(os.path.join(copy, "ec", "decompiled", "common", "0020.c"))
        rows = [("program", "addr", "name", "out_file"),
                ("common", "0100", "thunk_twice", "common/0100.c"),
                ("common", "0020", "twice", "common/0020.c")]
        for name in ("index.csv", "listing-index.csv"):
            with open(os.path.join(copy, "ec", "decompiled", name), "w",
                      newline="") as f:
                csv.writer(f).writerows(rows)
        with open(os.path.join(copy, "ec", "ghidra", "manifest.csv"), "w",
                  newline="") as f:
            csv.writer(f).writerows([("program", "functions", "decompiled",
                                      "failed"), ("common", "1", "1", "1")])

        diffs = (tree_differences(os.path.join(root, "ec", "decompiled"),
                                  os.path.join(copy, "ec", "decompiled"))
                 + manifest_differences(
                     os.path.join(root, "ec", "ghidra", "manifest.csv"),
                     os.path.join(copy, "ec", "ghidra", "manifest.csv")))
        by_kind = collections.Counter(d["kind"] for d in diffs)
        check("a .c that differs is classified as a .c", by_kind["c"] == 1,
              str(dict(by_kind)))
        check("an .asm that differs is classified as an .asm",
              by_kind["asm"] == 1, str(dict(by_kind)))
        check("an index.csv row that differs is classified as an index row",
              by_kind["index-row"] == 1, str(dict(by_kind)))
        check("the same change in listing-index.csv is told from the index's",
              by_kind["listing-row"] == 1, str(dict(by_kind)))
        check("a manifest column that differs is classified as one, and each "
              "column of the row is told apart",
              by_kind["manifest-column"] == 3, str(dict(by_kind)))
        check("a file on one side only is classified as missing from the copy, "
              "not as a difference of content", by_kind["missing-from-copy"] == 1,
              str(dict(by_kind)))
        check("the index-row difference names the column and both values",
              any(d["kind"] == "index-row" and d["detail"].startswith("name: ")
                  and "thunk_twice" in d["detail"] and "twice" in d["detail"]
                  for d in diffs))
        check("every classified kind is one of the closed vocabulary",
              all(d["kind"] in KINDS for d in diffs))

        # An identical pair is an empty diff, and that empty answer is the shape
        # of result worth having -- so it needs a fixture that produces it, or
        # the run can only ever be believed when it finds something.
        same = _clone_fixture(root, box, "identical")
        clean = (tree_differences(os.path.join(root, "ec", "decompiled"),
                                  os.path.join(same, "ec", "decompiled"))
                 + manifest_differences(
                     os.path.join(root, "ec", "ghidra", "manifest.csv"),
                     os.path.join(same, "ec", "ghidra", "manifest.csv")))
        check("a rebuilt tree identical to the committed one is 0 differences",
              not clean, str(clean[:2]))

        # The partial-run guard, at both ends of the floor. This is the property
        # the tool exists to hold: a run that stopped early produces a diff that
        # reads exactly like the finding being hunted.
        short = _clone_fixture(root, box, "short")
        with open(os.path.join(short, "ec", "ghidra", "manifest.csv"), "w",
                  newline="") as f:
            csv.writer(f).writerows([("program", "functions", "decompiled",
                                      "failed"), ("common", "1", "1", "0")])
        got = truncation_problems(root, short, 0)
        check("a rebuild that exported a fraction of the committed tree is "
              "refused as not measured", len(got) == 1 and "floor" in got[0],
              str(got))
        check("a rebuild that exited non-zero is refused whatever it left",
              len(truncation_problems(root, same, 1)) == 1)
        check("a rebuild that finished and matched is not refused",
              truncation_problems(root, same, 0) == [])
        dropped = _clone_fixture(root, box, "dropped")
        os.remove(os.path.join(dropped, "ec", "ghidra", "manifest.csv"))
        check("a copy carrying no manifest at all is refused",
              len(truncation_problems(root, dropped, 0)) == 1)
        with open(os.path.join(dropped, "ec", "ghidra", "manifest.csv"), "w",
                  newline="") as f:
            csv.writer(f).writerows([("program", "functions", "decompiled",
                                      "failed"), ("bank0", "2", "2", "0")])
        gone = truncation_problems(root, dropped, 0)
        check("a rebuild that did not export a committed program is refused, "
              "exactly rather than by the floor",
              len(gone) == 1 and "not exported" in gone[0], str(gone))

        # The timeout path, the one place the tool signals a process group it
        # is not itself part of. `_kill_group` is driven directly rather than
        # through a wall-clock ceiling, so the fixture is known to be up -- the
        # launcher reports readiness only once its own child is -- instead of
        # the test racing the clock to catch it.
        launcher, grandchild = _hanging_launcher(box)
        ready, marker = os.path.join(box, "ready"), os.path.join(box, "signalled")
        proc = subprocess.Popen(
            [sys.executable, launcher, ready, marker, grandchild,
             os.path.join(box, "grandchild.pid")], start_new_session=True)
        try:
            check("a child started with start_new_session leads a group of its "
                  "own, so the group to signal is never this process's",
                  _await_file(ready)
                  and os.getpgid(proc.pid) != os.getpgid(os.getpid()))
            with contextlib.redirect_stdout(io.StringIO()):
                _kill_group(proc, DEFAULT_TIMEOUT)
            check("the timeout takes the process the launcher started, not "
                  "only the launcher", _await_file(marker))
            proc.wait(timeout=KILL_GRACE)
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            proc.wait()

        # The counter table, which is where Q3's shape is accounted for. A
        # column that held still and a column that moved must be told apart:
        # printing a held-still counter as `1549 -> 1549` would read as a
        # movement, and `seeds_applied` holding still is the reading that keeps
        # the other two honest.
        moved = counter_moves(
            [{"program": "bank0", "functions": "750", "seeds_applied": "1549",
              "annotations_applied": "828", "annotations_unmatched": "0",
              "functions_named": "697"}],
            [{"program": "bank0", "functions": "750", "seeds_applied": "1549",
              "annotations_applied": "823", "annotations_unmatched": "5",
              "functions_named": "692"}])
        joined = "\n".join(moved)
        check("a counter that moved is printed as both values",
              "0 -> 5" in joined and "828 -> 823" in joined, joined)
        check("a counter that held still is printed once, not as a movement",
              "->" not in joined.split("seeds_applied")[1].split("\n")[0]
              and "1549" in joined, joined)
        check("a program one manifest has and the other does not is reported "
              "rather than counted as zero",
              "one manifest has no" in "\n".join(
                  counter_moves([{"program": "bank0", "functions": "1"}],
                                [{"program": "pd", "functions": "1"}])))

        # The two name tables, which is where Q1 and Q2 are read from.
        # `name_answers(have, want, ...)` takes the rebuilt export first and the
        # committed one second, which is the order the run calls it in and the
        # order a misread of it would silently reverse.
        want = read_csv(os.path.join(root, "ec", "decompiled", "index.csv"))
        table, answers = name_answers(want, want, [("common", "0100")], "Q1")
        check("an address whose name the rebuild reproduces reads as re-derived",
              "re-derived" in answers[0][4], answers[0][4])
        check("an address the rebuild drops is reported as not exported rather "
              "than skipped", "not exported" in name_answers(
                  read_csv(os.path.join(same, "ec", "decompiled", "index.csv")),
                  want, [("common", "9999")], "Q1")[1][0][4])
        check("a rebuilt name in Ghidra's reserved namespace at a rowless "
              "address is called out as a finding, not absorbed",
              "placeholder" in name_answers(
                  rows_as_rows(("common", "0100", "FUN_CODE_0100")), want,
                  [("common", "0100")], "Q1")[1][0][4])
        check("a rebuilt name outside that namespace is not called one",
              "placeholder" not in name_answers(
                  rows_as_rows(("common", "0100", "renamed_by_hand")), want,
                  [("common", "0100")], "Q1")[1][0][4])
        check("the committed name at a census address is read out of the "
              "committed index, not asserted here",
              name_at(want, "common", "0100") == "twice")
        check("an address no index row carries reads as no row, not as an "
              "empty name", name_at(want, "common", "9ABC") is None)

    print()
    if bad:
        print("self-test FAILED: %d check(s) disagree with the readings above"
              % bad)
        return 1
    print("self-test passed: the classifier tells an index row, a listing row, "
          "a manifest column, a .c, an .asm and a file on one side only apart, "
          "and reads an identical pair as no differences at all; the partial-run "
          "guard refuses a short count, a non-zero exit, a missing manifest and "
          "a program that was never exported, and lets a finished run through; "
          "the timeout signals the build's own process group, so the launcher "
          "and the JVM it started go together; "
          "the counter table tells a moved counter from one that held still; "
          "the name tables read a re-derived name, a dropped address and a "
          "Ghidra placeholder apart; and a rebuild into the tree is refused "
          "before anything is copied")
    return 0


def rows_as_rows(*rows):
    """Index rows for a fixture: `(program, addr, name)` into the shape
    `name_answers` reads."""
    return [{"program": p, "addr": a, "name": n} for p, a, n in rows]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="store_true",
                        help="copy the tree to scratch, rebuild there, and read "
                             "the answers back out. Needs Ghidra and an hour")
    parser.add_argument("--self-test", action="store_true",
                        help="the parts of a run that need no Ghidra, from "
                             "fixtures; no Ghidra, no network, no copy of this "
                             "repository")
    parser.add_argument("--scratch", default=None,
                        help="where the copy goes (default: a directory under "
                             "the system temp dir). Refused if it is inside "
                             "--repo")
    parser.add_argument("--repo", default=REPO,
                        help="the tree to copy and compare against (default: "
                             "this one)")
    parser.add_argument("--ghidra", default=os.environ.get(
        "GHIDRA_HEADLESS", "analyzeHeadless"), help="analyzeHeadless path")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="ceiling on the rebuild in seconds (default: %d). A "
                             "run that reaches it is reported as not measured"
                             % DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.run:
        parser.error("nothing to do: pass --run for the measurement or "
                     "--self-test for the offline checks")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
