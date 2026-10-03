#!/usr/bin/env python3
"""Re-render `pd/7B14.c` with one annotation row removed, and diff it.

`docs/findings.md` §18 records that across the #238 merge `ec/decompiled/pd/
7B14.c` gained a `DAT_EXTMEM_07c9` token (21 -> 22) and dropped the constant
`0x1c` its first argument used to carry, while `pd/7B14.asm` still shows
`clr A` / `add A, #0x1c` building it -- and that "what made Ghidra re-render
the file is not recorded in the committed tree". This probe is the experiment
that decides the question, and it is deliberately narrow: it re-renders the PD
program three times from the committed Ghidra project, once unchanged and once
with each of the two candidate annotation rows removed, and diffs `7B14.c`
between the arms.

**Which rows, and why these two.** `0x7B14` itself has hand-decoded rows in
both annotation layers, so the issue's "no annotation on 0x7B14 to point at"
was already false against the committed tree. The *callee* is where the arity
is decided, and both layers carry a row there:

  * `ghidra-variables.csv` has `pd,0x9028,param_1,r6_value,artifact` -- the
    shape issue #259 settled at bank1 0x9EA1, where naming a
    decompiler-promoted scratch register as an artifact shortened the
    signature the call sites are read against.
  * `ghidra-functions.csv` has `pd,9028,make_dptr_r6_minus_3_9028`, whose
    `signature` column is empty.

  The only effect of a function row that reaches the decompiler is
  `f.setName(...)` (`ApplyAnnotations.java`; the row also sets the plate
  comment, which the exporter prints and the decompiler does not read), and its
  signature column is *recorded, not applied*, so no function row can have moved
  an arity by any path the code contains. That is why both arms run rather than
  one: a rename is not provably inert -- Ghidra's decompiler is name-sensitive
  and this tree does not model that -- so the counterfactual decides rather than
  the argument. The `drop-function` arm measures ONE row, so what it settles is
  that row and not the function layer.

**What the arms are compared against.** Not only against the committed file,
but against each other and against a `baseline` arm that drops nothing. A
re-export that moved `7B14.c` with no annotation involved would be a
different finding from one that moved only when a row was removed, and only
the baseline arm tells those apart. The probe refuses to report a diff it has
not first shown to be a diff between two renders of the same inputs.

**Nothing here is a hardware result.** `--run` needs Ghidra and the committed
project; it reads the committed firmware, the committed project and the
committed annotation CSVs, writes only under the scratch directory, and never
opens the committed `.rep` for writing or edits a committed CSV. It is a text
measurement over the repository's own decompiler input.

**The scratch annotation CSVs are copies, and the committed ones are never
edited.** Removing a correct hand-decoded annotation to stabilise a number is
the thing `xdata-register-map.md` §7.1's policy already rejected, and a probe
that could do it by accident would be a tool that could do it by design.

**Why the project owner is corrected in the copy.** The committed project
records its owner as `dave` (`ec/ghidra/project/ec.rep/project.prp`), and
Ghidra refuses to open a project owned by another user with
`NotOwnerException` before it analyses anything --
`docs/findings.md` §18 records this as one of two pre-existing defects. The
copy is rewritten to whoever is running the probe and the committed file is
left byte-identical, which is what §18 says the export-only run for it did.

Usage:
    python3 ec/tools/pd_9028_render_probe.py --self-test   # no Ghidra
    python3 ec/tools/pd_9028_render_probe.py --run         # needs Ghidra
    python3 ec/tools/pd_9028_render_probe.py --run --work /tmp/probe
"""
import argparse
import csv
import difflib
import getpass
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_ec_decompile as B                                         # noqa: E402

REPO = B.REPO
FUNCTIONS = B.ANNOTATIONS
VARIABLES = B.VARIABLES

# The two candidate rows, and the baseline that drops neither. `key` is the
# column each layer keys on -- a function row is keyed on a stable address,
# a variable row on a decompiler placeholder -- so the arm that removes one
# and the arm that removes the other are not removing the same thing.
ARMS = {
    "baseline": None,
    "drop-variable": ("variables", ("pd", "0x9028", "param_1")),
    "drop-function": ("functions", ("pd", "9028")),
}

# What the probe reads back out of each render. One file, because the question
# is about one file.
WATCH = ("pd", "7B14.c")


def read_csv(path):
    """Committed CSV rows and the header, read strictly."""
    with open(path, newline="") as f:
        reader = csv.reader(f, strict=True)
        rows = list(reader)
    return rows[0], rows[1:]


def drop_row(path, out, key, columns):
    """`path` read strictly, one row removed, written to `out`.

    **`out` is always a different file from `path`, and there is no path
    through this function that returns `path`.** That is the guard, and it is
    checked here rather than left to the caller: a probe whose counterfactual
    silently edited the committed CSV would produce a run that looks clean and
    a tree that is wrong.

    Raises if the key matches no row, which is the other failure this has to
    have loudly rather than quietly: an arm that removes nothing still
    produces a plausible render, and the reader would have no way to tell an
    experiment from a no-op.
    """
    if os.path.abspath(out) == os.path.abspath(path):
        raise ValueError("refusing to write the annotation CSV over itself: %s"
                         % path)
    header, rows = read_csv(path)
    idx = [header.index(c) for c in columns]
    kept = [r for r in rows if tuple(r[i] for i in idx) != key]
    if len(kept) == len(rows):
        raise KeyError("no row in %s has %s = %r; the arm would drop nothing "
                       "and its render would be indistinguishable from the "
                       "baseline" % (os.path.relpath(path, REPO),
                                     "/".join(columns), key))
    with open(out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(kept)
    return len(rows) - len(kept)


def arm_csvs(arm, work):
    """`(functions_path, variables_path, dropped)` for one arm.

    The layer the arm targets is a scratch copy with one row removed; the
    other layer is passed as the committed path, so the arm differs from the
    baseline in exactly the row it names and in nothing else.
    """
    target = ARMS[arm]
    if target is None:
        return FUNCTIONS, VARIABLES, None
    layer, key = target
    src = FUNCTIONS if layer == "functions" else VARIABLES
    columns = ("scope", "addr") if layer == "functions" else ("scope", "addr",
                                                              "key")
    out = os.path.join(work, "annotations", "%s-%s.csv" % (layer, arm))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n = drop_row(src, out, key, columns)
    if layer == "functions":
        return out, VARIABLES, n
    return FUNCTIONS, out, n


def retake_owner(project_copy):
    """The project owner the copy claims, rewritten to whoever is running this.

    Returns the owner string it found, so a caller can print what it changed
    rather than doing it silently. `docs/findings.md` §18 records the
    `NotOwnerException` this works around.
    """
    prp = os.path.join(project_copy, "ec.rep", "project.prp")
    with open(prp) as f:
        text = f.read()
    owner = None
    for line in text.splitlines():
        if 'NAME="OWNER"' in line:
            start = line.index('VALUE="') + len('VALUE="')
            owner = line[start:line.index('"', start)]
            break
    if owner is None:
        raise SystemExit("error: no OWNER state in %s; refusing to guess at a "
                         "Ghidra project layout" % prp)
    me = getpass.getuser()
    if owner != me:
        with open(prp, "w") as f:
            f.write(text.replace('VALUE="%s"' % owner, 'VALUE="%s"' % me))
    return owner


def export(arm, work, ghidra):
    """Re-render the PD program under one arm; return the exported file's text.

    The three programs are not re-exported: `pd.bin` is where every row in
    play lives, and a bank run would be two more Ghidra invocations adding
    nothing this probe reads.
    """
    out_dir = os.path.join(work, arm)
    os.makedirs(out_dir, exist_ok=True)
    imgs = B.build_images(out_dir)
    fw = open(B.FIRMWARE, "rb").read()
    pd = fw[0x20000:0x30000]
    rows, _b0, _b1, _pdseeds = B.seed_rows(fw, pd, B.call_target_rows())
    _spec, basis, annot_spec = B.write_specs(out_dir, rows)
    context = B.write_context(out_dir, imgs, B.sha256(B.FIRMWARE))
    B.ghidra_preflight(ghidra)

    funcs, variables, dropped = arm_csvs(arm, out_dir)

    project = os.path.join(out_dir, "project")
    if os.path.isdir(project):
        shutil.rmtree(project)
    shutil.copytree(B.PROJECT, project)
    owner = retake_owner(project)

    raw_index = os.path.join(out_dir, "index-raw.csv")
    listing = os.path.join(out_dir, "listing-raw.csv")
    header = ("program\taddr\tname\tsize\tseed_basis\tannotated\ttype\t"
              "basis\tevidence\tout_file\n")
    for p in (raw_index, listing):
        with open(p, "w", newline="") as f:
            f.write(header)

    cmd = [ghidra, project, "ec", "-process", "pd.bin", "-noanalysis",
           "-scriptPath", B.SCRIPTS,
           "-postScript", "SeedFunctions.java", annot_spec,
           "-postScript", "ApplyAnnotations.java", funcs, B.XDATA,
           os.path.join(out_dir, "reports"), variables,
           "-postScript", "ExportDecompile.java", os.path.join(out_dir, "out"),
           raw_index, "per-function", context, basis,
           "-postScript", "ExportListing.java", os.path.join(out_dir, "out"),
           listing, "per-function", context, basis]
    B.run(cmd, stdout=open(os.path.join(out_dir, "ghidra.log"), "w"),
          stderr=subprocess.STDOUT)
    path = os.path.join(out_dir, "out", WATCH[0], WATCH[1])
    if not os.path.isfile(path):
        raise SystemExit("error: %s produced no %s; read %s"
                         % (arm, os.path.join(*WATCH),
                            os.path.join(out_dir, "ghidra.log")))
    with open(path) as f:
        return f.read(), dropped, owner


def diff_of(a, b):
    """The unified diff between two renders of the watched file, as lines."""
    return list(difflib.unified_diff(a.splitlines(), b.splitlines(),
                                     fromfile="a", tofile="b", lineterm=""))


def committed_watch():
    """The committed `pd/7B14.c`, read with its handle closed."""
    path = os.path.join(B.DECOMPILED if hasattr(B, "DECOMPILED") else
                        os.path.join(REPO, "ec", "decompiled"),
                        WATCH[0], WATCH[1])
    with open(path, errors="replace") as f:
        return f.read()


def describe(arm, text, dropped, owner):
    """What one arm produced, in the words the write-up uses."""
    if dropped is None:
        print("  %-16s no row removed; project owner in the copy was %r"
              % (arm, owner))
    else:
        print("  %-16s removed %d row(s) from %s; project owner in the copy "
              "was %r" % (arm, dropped, ARMS[arm][0], owner))
    against = diff_of(committed_watch(), text)
    if not against:
        print("  %-16s   byte-identical to the committed ec/decompiled/%s/%s"
              % ("", WATCH[0], WATCH[1]))
    else:
        print("  %-16s   DIFFERS from the committed file in %d diff line(s):"
              % ("", len(against)))
        for line in against:
            print("      " + line)


def self_test():
    """The plumbing, on a fixture, with no Ghidra and no project.

    What is exercised is the part that can fail silently: an arm that drops
    the wrong number of rows, drops none, or writes over the file it read.
    The Ghidra arm cannot be here -- it needs the toolchain and minutes of
    wall clock -- so it is deliberately not in `tools/run-tests.sh` either,
    and this is what stands in for it.
    """
    ok = True

    def assert_that(cond, what):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", what))
        ok = ok and bool(cond)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "ann.csv")
        with open(src, "w", newline="") as f:
            f.write("scope,addr,key,name\n"
                    "pd,0x9028,param_1,r6_value\n"
                    "pd,0x9026,param_1,x\n"
                    "bank1,0x9EA1,param_1,y\n")
        out = os.path.join(tmp, "copy.csv")
        n = drop_row(src, out, ("pd", "0x9028", "param_1"),
                     ("scope", "addr", "key"))
        assert_that(n == 1, "dropping one row reports one row dropped")
        header, rows = read_csv(out)
        kept = {tuple(r[:3]) for r in rows}
        assert_that(header == ["scope", "addr", "key", "name"]
                    and len(rows) == 2
                    and kept == {("pd", "0x9026", "param_1"),
                                 ("bank1", "0x9EA1", "param_1")},
                    "and the copy keeps the header and every other row, so the "
                    "arm differs from the baseline in one row and nothing else")

        # The guard that matters most: this is the function that could edit a
        # committed CSV, and there is no path through it that can.
        try:
            drop_row(src, src, ("pd", "0x9028", "param_1"),
                     ("scope", "addr", "key"))
            refused = False
        except ValueError:
            refused = True
        assert_that(refused, "writing the copy over the file it read is "
                             "refused, not performed")
        with open(src) as f:
            assert_that("param_1,r6_value" in f.read(),
                    "and the source is still intact afterwards")

        # A key that matches nothing must be loud. The alternative is an arm
        # that drops no row, renders normally, and is indistinguishable from
        # the baseline -- an experiment that cannot fail.
        try:
            drop_row(src, os.path.join(tmp, "copy2.csv"),
                     ("pd", "0x9999", "param_1"), ("scope", "addr", "key"))
            loud = False
        except KeyError:
            loud = True
        assert_that(loud, "a key that matches no row raises rather than "
                          "writing a copy that dropped nothing")

        # A two-column key (the function layer) drops by scope+addr only.
        out2 = os.path.join(tmp, "copy3.csv")
        with open(os.path.join(tmp, "fn.csv"), "w", newline="") as f:
            f.write("scope,addr,name\npd,9028,f\npd,9026,f\n")
        n2 = drop_row(os.path.join(tmp, "fn.csv"), out2, ("pd", "9028"),
                      ("scope", "addr"))
        assert_that(n2 == 1 and len(read_csv(out2)[1]) == 1,
                    "the function layer drops on (scope, addr) alone, which is "
                    "the key it is written against")

    # The arms resolve to the rows they claim, read out of the committed CSVs.
    for arm in ("drop-variable", "drop-function"):
        target = ARMS[arm]
        layer, key = target
        path = FUNCTIONS if layer == "functions" else VARIABLES
        columns = ("scope", "addr") if layer == "functions" else ("scope",
                                                                  "addr", "key")
        header, rows = read_csv(path)
        idx = [header.index(c) for c in columns]
        hits = [r for r in rows if tuple(r[i] for i in idx) == key]
        assert_that(len(hits) == 1,
                    "the %s arm's key %r matches exactly one committed row in "
                    "%s" % (arm, key, os.path.relpath(path, REPO)))
    assert_that(ARMS["baseline"] is None and set(ARMS) == set(
        ("baseline", "drop-variable", "drop-function")),
        "and the three arms are the baseline plus one per layer -- the "
        "baseline is what tells a row's effect from the re-export's own")

    # The committed file is what the diff is taken against, and it must exist
    # and be non-empty or every arm would "agree" trivially.
    text = committed_watch()
    assert_that(len(text) > 0 and "stage_07c9_index_then_dispatch_on_flag_bits"
                in text,
                "the committed pd/7B14.c is present and is the file under test")

    # `diff_of` distinguishes the three cases a reader has to tell apart.
    assert_that(diff_of("a\n", "a\n") == []
                and diff_of("a\n", "b\n")
                and diff_of("a\n", "a\nb\n"),
                "diff_of reports no diff, a change, and an addition as three "
                "different things -- a probe that called all three 'identical' "
                "would answer no question")

    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def run(args):
    """Every arm, in order, each diffed against the committed file."""
    work = os.path.abspath(args.work or "/tmp/pd-9028-probe")
    os.makedirs(work, exist_ok=True)
    print("pd_9028_render_probe.py -- re-rendering pd/7B14.c under each arm "
          "into %s" % work)
    print()
    print("  committed inputs: %s, %s"
          % (os.path.relpath(B.PROJECT, REPO),
             os.path.relpath(B.FIRMWARE, REPO)))
    print("  the committed .rep and both annotation CSVs are read-only here; "
          "every write is under the scratch directory.")
    print()
    for arm in ARMS:
        text, dropped, owner = export(arm, work, args.ghidra)
        describe(arm, text, dropped, owner)
        print()
    print("  a DIFFERS line is a measurement of Ghidra's decompiler over this "
          "repository's")
    print("  committed inputs. It is not a hardware result and not a statement "
          "about")
    print("  the EC's behaviour: nothing here opened an EC.")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true",
                      help="re-render pd/7B14.c under each arm (needs Ghidra)")
    mode.add_argument("--self-test", action="store_true",
                      help="known answers; no Ghidra, no project")
    ap.add_argument("--work", help="scratch directory for --run (created)")
    ap.add_argument("--ghidra",
                    default=os.environ.get("GHIDRA_HEADLESS",
                                           "analyzeHeadless"),
                    help="analyzeHeadless path")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.run:
        ap.error("one of --run or --self-test is required; --run needs Ghidra "
                 "and is not wired into tools/run-tests.sh")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
