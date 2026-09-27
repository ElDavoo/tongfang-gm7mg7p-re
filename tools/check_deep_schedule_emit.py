#!/usr/bin/env python3
"""Hold the shape of the prepared nightly's second artifact, and read one.

`docs/ci/agent-gates-deep-schedule.yml` is prepared rather than landed: a human
`cp`s it into `.github/workflows/`, so it is the one place in the deep-gate
story an agent may edit. It is also a file **nothing executes**, and an
invariant held only in a comment above code no runner reaches is a comment.
This is the other half of it -- five claims about the file's shape, checked
against the committed text, so a change that breaks one is red before a human
copies the file rather than after a night's artifact is wrong.

`--check` holds:

  1. An `upload-artifact` for the CSV whose `path:` is `${{ runner.temp }}`-
     rooted, coupled to the file the emit step actually writes -- the same file,
     not a second file that happens to end in `.csv`. And no upload in the file
     names the committed report, which is the `refuses_committed_report`
     invariant as a held claim rather than as a parenthetical about
     `runner.temp`.
  2. Two `upload-artifact` uses, distinct `name:` values, both carrying
     `${{ github.run_id }}`. Distinct is the load-bearing half: equal names
     make upload-artifact v4+ *merge* the two files into one artifact, so "a
     landed nightly leaves two artifacts" would be quietly false.
  3. The emit step passes `--emit-csv` to a `$RUNNER_TEMP` path, pins
     `SDAS8051` empty in both directions, and does not pass `--limit`. A
     sampled CSV cannot be joined row-for-row against the committed report,
     which is the whole use.
  4. The header `verify_reassembly.emit_csv` writes today is **byte-identical**
     to the first line of `ec/ghidra/reassembly.csv`. Nothing asserts this
     anywhere, and a column added on one side only is how the diff this
     artifact exists for stops working without anything going red.
  5. `refuses_committed_report()` still refuses the committed report, called
     from *outside* the tool, so a rename of its constants is caught here too.

Holds 4 and 5 are the only ones that touch `verify_reassembly.py`, and they do
it by loading the module and calling two functions -- `ec/tools/verify_reassembly.py`
is 2,268 lines and other branches are near it, so this asserts the invariant
from outside rather than growing it. No assembler, no Ghidra, no network.

`--diff NIGHT.csv ec/ghidra/reassembly.csv` is the reader half, and it prints
**every** moved row uncapped. The cap is the defect being reported -- the log
capped at `MOVED_CAP = 20` and said "and N more" -- and a reader with the same
habit reproduces it. Rows present on only one side are named as such. A pair
that moves nothing says so in words, and a run that located nothing exits
non-zero, because "found nothing" and "found nothing wrong" must not read alike
from the exit code (the §14b shape `tools/run-tests.sh` and
`tools/check_doc_patch_refs.py` both name).

**A nightly diff is expected to differ, and this tool is not an alarm.** It
comes from two directions, and the reader has to be able to tell them apart,
which is why every moved line names *which column* moved.

  * **The assembler.** The committed report was measured with a pinned nix
    build of SDCC -- 2,704 of its 2,711 rows, the 7 exceptions having been
    added or replaced later under apt without re-running the rest;
    `project-setup` installs the apt one, and §14h measured that
    difference at 52 rows -- all of them `assembler-gap` on one side, none
    regressed. This is standing, documented and settles nothing.
  * **Annotation drift.** `verify()` reads each row's `name` out of
    `ec/decompiled/listing-index.csv` at run time, and a row already in the
    report is not rewritten when that name later changes. So a function
    renamed after its row was written shows up as a moved `name` and nothing
    else -- and `listing_digest`, which is the column that says whether the
    *code* moved, stays put. On this tree that is 138 rows, measured by
    `docs/findings/deep-schedule-row-csv.md`.

`assembler` is the one column `--diff` does not compare: it differs by
construction, and comparing it would report every row as moved every night,
which is the cap-shaped defect in a new place. Every other column is compared,
`name` included -- it is how the second class above becomes visible at all.

**What this does not check, which is most of the value.** Nothing here runs the
schedule; it is not in `.github/workflows/`, so no nightly has run this. Every
verdict is a claim about a file's *shape* and a pair of files' *join*, and a
green run says the wiring is right -- not that a nightly produced anything. The
"a landed nightly leaves two artifacts" acceptance criterion needs the `cp`,
which is a human's line and out of scope for the token this branch pushes with.

Usage:
    python3 tools/check_deep_schedule_emit.py [--check]
    python3 tools/check_deep_schedule_emit.py --diff NIGHT.csv REPORT.csv
    python3 tools/check_deep_schedule_emit.py --self-test
"""
import argparse
import collections
import contextlib
import csv
import importlib.util
import io
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCHEDULE = REPO / "docs" / "ci" / "agent-gates-deep-schedule.yml"
REPORT = REPO / "ec" / "ghidra" / "reassembly.csv"
VERIFY = REPO / "ec" / "tools" / "verify_reassembly.py"

# The three spellings one step's text is read in. `${{ runner.temp }}` and
# `${RUNNER_TEMP}` are two runners use for the same directory, and a check that
# accepted only one of them would be red on an edit that changed nothing. The
# GitHub expression is accepted in a *destination* as a tolerance rather than as
# a shape: the schedule deliberately keeps `${{ }}` out of the `run:` block,
# where it would be template injection, so nothing here depends on it being
# there and a file that spells a destination that way is still under
# `runner.temp`.
RUNNER_TEMP_EXPR = "${{ runner.temp }}"
RUNNER_TEMP_SHELL = ("$RUNNER_TEMP", "${RUNNER_TEMP}", RUNNER_TEMP_EXPR)
RUN_ID = "${{ github.run_id }}"

UPLOAD = "actions/upload-artifact@"
EMIT_FLAG = "--emit-csv"
LIMIT_FLAG = "--limit"

# The value after `--emit-csv`, quoted or bare, `=`-joined or not. The quoted
# forms are read whole rather than as a whitespace-delimited word, because
# `"${{ runner.temp }}/deep-gates-csv.csv"` carries a space inside the
# expression and a token regex would hand back `${{` and then refuse a
# correctly-rooted destination for a reason that reads as a typo.
DESTINATION = re.compile(r"--emit-csv[\s=]+(?:\"([^\"]*)\"|'([^']*)'|(\S+))")

# A shell comment inside a `run:` block is still text this reads, and a rule
# that fires on the sentence stating it is a rule everybody disables -- which is
# how a check dies, and the reason the strip is here rather than a note asking
# the next editor not to name a flag in prose. The schedule's own emit step has
# to say *why* it passes no `--limit`, and that sentence is inside the block.
# `#` is only a comment at the start of a line or after whitespace, so a `#` in
# a path or a word is not mistaken for one.
COMMENT = re.compile(r"(?:^|(?<=\s))#.*$", re.MULTILINE)


def shell_code(run):
    """`run` with its shell comments removed.

    What every flag rule below is read against, and also what selects the emit
    step: a step whose only mention of `--emit-csv` is a comment about it is
    not the emit step.
    """
    return COMMENT.sub("", run or "")


def destination(run):
    """The path after `--emit-csv` in `run`, or None if it is not there."""
    match = DESTINATION.search(shell_code(run))
    if not match:
        return None
    return next(g for g in match.groups() if g is not None)

# An `SDAS8051` assignment in the emit step's shell. The two alternatives are
# the two things that can go wrong and they are not the same failure: a
# non-empty value points the re-encode at a different binary than the "Name the
# assembler" step printed, and no assignment at all leaves the reading to
# whatever the runner's environment happens to carry.
SDAS_ASSIGN = re.compile(r"(?:^|[\s;&|(])SDAS8051=(?:'([^']*)'|\"([^\"]*)\"|(\S*))",
                         re.MULTILINE)

# The key two reports are joined on, and the column that is not compared. See
# the module docstring for why the `assembler` cell is excluded: it names the
# build, and the nightly's build is *meant* to differ from the committed one.
KEY = ("program", "addr")
NOT_COMPARED = ("assembler",)

# What one schedule read found. A namedtuple rather than a dict so a field
# added without a reader is a TypeError at construction.
Schedule = collections.namedtuple("Schedule", "uploads emit_run destination")

# One `upload-artifact` step, read across. See `upload_steps` for why `step`
# and `name` are separate fields rather than one.
Upload = collections.namedtuple("Upload", "step name path cond")

# What one join found: the two populations, the rows that moved, and the rows
# only one side carried. `duplicate` is reported rather than resolved to the
# first, because a key appearing twice is a defect in the artifact this tool
# reads and resolving it would hide one row's disagreement behind another's.
Join = collections.namedtuple(
    "Join", "left right left_rows right_rows moved only_left only_right "
    "duplicate compared")


def load_verify():
    """`verify_reassembly.py` as a module, by path.

    Loaded rather than imported because the two live in different directories
    and this one is a `tools/` tool, not an `ec/tools/` one. `importlib` rather
    than `sys.path` because the file's own name is not a package member and the
    sibling-load pattern eight suites already use is the arrangement that keeps
    a name change from becoming an ImportError here.
    """
    spec = importlib.util.spec_from_file_location("verify_reassembly", VERIFY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def steps(doc):
    """Every step of every job, as the list `doc` holds.

    The job name is not part of the key. `deep` is what the file happens to
    call its job today, and a check that read it would report a broken
    discovery the day the job is renamed rather than a broken schedule.
    """
    out = []
    for job in (doc.get("jobs") or {}).values():
        if isinstance(job, dict):
            out += [s for s in (job.get("steps") or []) if isinstance(s, dict)]
    return out


def upload_steps(doc):
    """The `upload-artifact` steps, as `Upload` records in file order.

    `step` and `name` are both carried and they are not the same field: the
    run id belongs in `with.name`, which is the *artifact's* name and the thing
    two uploads would collide on, while `step` is the label a reader sees in the
    workflow's own step list. Reading the step's name for the run-id check would
    pass on any file whose step labels happen to be stable, and the collision
    hold would then be comparing two strings nobody uploads under.
    """
    out = []
    for step in steps(doc):
        uses = step.get("uses")
        if isinstance(uses, str) and uses.startswith(UPLOAD):
            with_ = step.get("with") or {}
            out.append(Upload(step.get("name"),
                              str(with_.get("name", "")),
                              str(with_.get("path", "")),
                              step.get("if")))
    return out


def emit_run(doc):
    """The `run:` of the step that passes `--emit-csv`, or None.

    The step is *selected* on the comment-stripped text, so the schedule's own
    emit step -- whose block explains at length why it does not pass `--limit`
    and why it pins `SDAS8051` -- is recognised by the command rather than by a
    sentence about the command.
    """
    for step in steps(doc):
        run = step.get("run")
        if isinstance(run, str):
            code = shell_code(run)
            if EMIT_FLAG in code:
                return code
    return None


def scan(text):
    """`(Schedule, [problem])` for one schedule file's text.

    The subject is the text rather than the file, so a case can point this at
    two lines of fixture and read the finding. `emit_run` is resolved here and
    its absence is *not* a problem on its own -- the four holds below that need
    it say so themselves, naming the missing step, which is a better message
    than one derived from a `None` two calls away.
    """
    problems = []
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return Schedule([], None, None), [
            "the file does not parse as YAML: %s" % exc]
    if not isinstance(doc, dict):
        return Schedule([], None, None), [
            "the file parsed to %s, not a workflow mapping" % type(doc).__name__]

    uploads = upload_steps(doc)
    run = emit_run(doc)
    dest = destination(run)
    found = Schedule(uploads, run, dest)

    # Hold 2: two artifacts, and two *names*. Every check here that could be
    # satisfied by a count is also satisfied by a name where one exists, so the
    # name is the thing compared.
    if len(uploads) != 2:
        problems.append(
            "%d upload-artifact step(s), and the schedule is supposed to leave "
            "two artifacts -- the log and the per-row CSV. Equal names would "
            "merge them into one, so a count is not the claim; the two names "
            "are checked separately below." % len(uploads))
    names = [u.name for u in uploads]
    if len(set(names)) != len(names):
        problems.append(
            "two upload-artifact steps share a name (%s). upload-artifact v4+ "
            "merges same-named uploads into one artifact, so the pair a reader "
            "is told to join by run id would not exist."
            % ", ".join(sorted({n for n in names if names.count(n) > 1})))
    for upload in uploads:
        label = upload.step or upload.name
        if RUN_ID not in upload.name:
            problems.append(
                "the artifact %r (step %r) does not carry %s in its name, so a "
                "reader cannot tell this night's artifact from last night's "
                "without cross-referencing the run list"
                % (upload.name, label, RUN_ID))
        if str(upload.cond) != "always()":
            problems.append(
                "the upload step %r is `if: %s`, not `if: always()`. The log "
                "anyone wants is the one from the run that failed, and a run "
                "that fails with no artifact is the silence the schedule "
                "exists to remove." % (label, upload.cond))
        if not upload.path.startswith(RUNNER_TEMP_EXPR):
            problems.append(
                "the upload step %r collects `%s`, which is not rooted at "
                "%s. The committed report is under the repository, and an "
                "upload rooted there could name it -- which is the one path "
                "`--emit-csv` refuses."
                % (label, upload.path, RUNNER_TEMP_EXPR))
        if REPORT.name in upload.path:
            problems.append(
                "the upload step %r collects `%s`, which names the committed "
                "report. `reassembly.csv` is written by `--report` and by "
                "nothing else." % (label, upload.path))

    # Hold 3, in the four clauses it is made of. Each names what it refuses,
    # because "the emit step is wrong" is not something a reader can act on.
    if run is None:
        problems.append(
            "no step passes %s, so the schedule leaves the log and nothing "
            "else. The per-row content of a night would exist only as a "
            "capped list in the log, which is what the artifact is for."
            % EMIT_FLAG)
    else:
        if dest is None:
            problems.append(
                "the step this read as the emit step does not pass %s a path. "
                "The flag appears in it, but not as an argument this can read "
                "-- a mention in one of the step's own `echo` lines will do it "
                "-- and the destination has to be a literal $RUNNER_TEMP path "
                "rather than a shell variable, so the file that is written and "
                "the file that is uploaded can be held to be the same one."
                % EMIT_FLAG)
        elif not dest.startswith(RUNNER_TEMP_SHELL):
            problems.append(
                "%s writes to `%s`, which is not under $RUNNER_TEMP. A "
                "destination inside the repository is one a later edit can "
                "point at the committed report, and `refuses_committed_report` "
                "is the guard that would have to catch it." % (EMIT_FLAG, dest))
        else:
            # Hold 1, as a coupling rather than a substring: the upload has to
            # collect the file the step writes. A CSV upload that names a
            # second `.csv` is a schedule that looks right and leaves an
            # artifact nobody joined.
            collected = [u for u in uploads
                         if u.path.endswith(PurePosixPath(dest).name)]
            if not collected:
                problems.append(
                    "no upload-artifact collects `%s`, the file %s writes. A "
                    "night would leave the CSV on the runner and upload "
                    "something else." % (dest, EMIT_FLAG))
        if LIMIT_FLAG in run:
            problems.append(
                "the emit step passes %s, so its CSV covers a sample of the "
                "firmware. A sampled CSV cannot be joined row-for-row against "
                "the committed report, which is the only thing this artifact "
                "is for." % LIMIT_FLAG)
        assigns = [m for m in SDAS_ASSIGN.finditer(run)]
        non_empty = [m for m in assigns
                     if (m.group(1) or m.group(2) or m.group(3) or "")]
        if non_empty:
            problems.append(
                "the emit step sets SDAS8051 to `%s`. `find_assembler()` "
                "prefers it over PATH, so the CSV's `assembler` column would "
                "name a different binary than the schedule's own \"Name the "
                "assembler\" step printed beside it."
                % (non_empty[0].group(1) or non_empty[0].group(2)
                   or non_empty[0].group(3)))
        elif not assigns:
            problems.append(
                "the emit step never pins SDAS8051, so the reading is left to "
                "whatever the runner's environment happens to carry. Empty on "
                "purpose is the same instruction to `find_assembler()` as unset "
                "-- and it keeps holding when a runner stops being bare.")

    return found, problems


def header_line(path):
    """The first line of `path`, as bytes.

    Bytes rather than text: the claim is that the two headers are the *same
    bytes*, and decoding first would let a line-ending difference read as
    agreement on some platforms and disagreement on others.
    """
    with open(path, "rb") as f:
        return f.readline()


def header_coupling(repo=REPO):
    """`(problems, ok_count)` for holds 4 and 5, against the committed tree.

    The only part of `--check` that writes anything, and it writes into a
    `tempfile` it makes itself: `emit_csv` is asked for a zero-row report so
    the header is produced by the real writer rather than transcribed here. A
    transcription would be a second copy of the column list, which is the drift
    this hold exists to catch.
    """
    problems = []
    held = 0
    try:
        verify = load_verify()
    except Exception as exc:                      # a broken reader, not a verdict
        return ["cannot read %s, so holds 4 and 5 were not evaluated: %s"
                % (VERIFY.name, exc)], 0

    # Hold 5 first, because it is the cheaper of the two and its refusal
    # message is the one that explains why the emit step writes where it does.
    with contextlib.redirect_stdout(io.StringIO()):
        refuses = verify.refuses_committed_report(
            str(REPO / "ec" / "ghidra" / REPORT.name))
    if refuses is True:
        held += 1
    else:
        problems.append(
            "refuses_committed_report() no longer refuses %s. A second path "
            "to the committed report is the hazard it was written for, and "
            "this is the only thing that holds that." % REPORT)

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "night.csv"
        # A `sdas` that cannot exist, so the header is produced without an
        # assembler: `assembler_version()` swallows the failure and returns
        # `unknown`, and the column under test is the one above it.
        with contextlib.redirect_stdout(io.StringIO()):
            rc = verify.emit_csv([], "no-such-assembler", str(out))
        if rc != 0 or not out.is_file():
            problems.append(
                "emit_csv() exited %r without writing a file, so the header "
                "hold could not be evaluated." % rc)
            return problems, held
        try:
            written, committed = header_line(out), header_line(
                repo / "ec" / "ghidra" / REPORT.name)
        except OSError as exc:
            problems.append("cannot read a header to compare: %s" % exc)
            return problems, held
    if written == committed:
        held += 1
    else:
        problems.append(
            "the header emit_csv() writes today is\n    %s\nwhich is not the "
            "committed report's\n    %s\nA column on one side only is how the "
            "(program, addr) join this artifact exists for stops working, and "
            "nothing else in the tree compares the two."
            % (written.decode("utf-8", "replace").strip(),
               committed.decode("utf-8", "replace").strip()))
    return problems, held


def read_rows(path):
    """`(fields, {(program, addr): row}, duplicates)` for one report CSV.

    A duplicate key is returned rather than resolved: a key appearing twice is
    a defect in the file being read, and keeping the last one would hide one
    row's disagreement behind another's.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or ())
        rows, dupes = {}, set()
        for row in reader:
            key = tuple(row.get(col) or "" for col in KEY)
            if key in rows:
                dupes.add(key)
            rows[key] = row
    return fields, rows, sorted(dupes)


def join(left, right):
    """`Join` for two report CSVs, on `(program, addr)`.

    Every column is compared except `NOT_COMPARED`, and a row is *moved* when
    any of them differs. That is a superset of what §14h compared -- outcome,
    `instructions_checked`, `instructions_unchecked`, `detail` -- and
    deliberately so: `listing_digest` was identical on both of its runs, which
    is the strongest thing either file can say, and a diff that stopped
    watching it would go quiet on the one change that matters most.
    """
    lf, lr, ld = read_rows(left)
    rf, rr, rd = read_rows(right)
    compared = [c for c in lf if c not in NOT_COMPARED]
    moved = []
    for key in sorted(set(lr) & set(rr)):
        fields = [c for c in compared
                  if (lr[key].get(c) or "") != (rr[key].get(c) or "")]
        if fields:
            moved.append((key, fields, lr[key], rr[key]))
    return Join(
        left=left, right=right,
        left_rows=len(lr), right_rows=len(rr),
        moved=moved,
        only_left=sorted(set(lr) - set(rr)),
        only_right=sorted(set(rr) - set(lr)),
        duplicate=sorted(set(ld) | set(rd)),
        compared=compared)


def report_join(result, stream=None):
    """Print one join, uncapped, and return how many problems it found.

    Uncapped on purpose and stated here so a later reader does not "fix" it:
    `verify_reassembly.py` caps its own moved-row list at `MOVED_CAP = 20` and
    prints "and N more", which is the reason this tool exists. A cap on this
    output would put the defect back one level up.
    """
    out = stream or sys.stdout
    for key, fields, here, there in result.moved:
        for col in fields:
            print("  moved  %s %s  %-22s %s -> %s"
                  % (key[0], key[1], col,
                     (there.get(col) or "(blank)"),
                     (here.get(col) or "(blank)")), file=out)
    for key in result.only_left:
        print("  only in %s  %s %s" % (Path(result.left).name, key[0], key[1]),
              file=out)
    for key in result.only_right:
        print("  only in %s  %s %s" % (Path(result.right).name, key[0], key[1]),
              file=out)
    for key in result.duplicate:
        print("  DUPLICATE  %s %s appears in both files' join key"
              % (key[0], key[1]), file=out)

    if not result.moved and not result.only_left and not result.only_right:
        print("  no row moved between the two, and no row is on one side "
              "only", file=out)
    return len(result.duplicate)


def diff_mode(left, right):
    """`--diff`: print the join, and 0 if it ran, 1 if it could not, 2 if a
    file could not be read.

    A moved row is **not** a failure. §14h measured 52 of them between the
    committed report and the apt build a runner installs, so a nightly that
    differs is a nightly working; treating that as an error would train a
    reader to ignore the tool on the one night it found something. What *is* a
    failure is locating nothing, for the reason the module docstring gives.
    """
    for path in (left, right):
        if not Path(path).is_file():
            print("  cannot read %s: no such file" % path, file=sys.stderr)
            return 2
    try:
        lf, _lr, _ld = read_rows(left)
        rf, _rr, _rd = read_rows(right)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        print("  cannot read one of the two reports: %s" % exc,
              file=sys.stderr)
        return 2
    if lf != rf:
        print("  the two headers differ, so a (program, addr) join would be "
              "reading two different tables:\n    %s: %s\n    %s: %s"
              % (left, ",".join(lf), right, ",".join(rf)), file=sys.stderr)
        return 1
    missing = [c for c in KEY if c not in lf]
    if missing:
        print("  neither file has a %s column, so there is no key to join on"
              % " or ".join(missing), file=sys.stderr)
        return 1

    result = join(left, right)
    print("joined on (%s); every column compared except %s, which names the "
          "build rather than the reading" % (", ".join(KEY),
                                             ", ".join(NOT_COMPARED)))
    print("%-34s %6d row(s)" % (Path(left).name, result.left_rows))
    print("%-34s %6d row(s)" % (Path(right).name, result.right_rows))
    report_join(result)
    if not result.left_rows and not result.right_rows:
        print("  located no row at all: the population is empty, which is a "
              "broken discovery rather than a pair that agrees", file=sys.stderr)
        return 1
    print("%d row(s) moved, %d only in %s, %d only in %s"
          % (len(result.moved), len(result.only_left), Path(left).name,
             len(result.only_right), Path(right).name))
    return 1 if result.duplicate else 0


def self_test():
    """The refusals, on synthetic schedule text and on reports built here.

    An oracle never recorded from this tool: a self-test that derives its
    expectation from the code under test asserts nothing, which is the note
    `disasm8051.self_test` and `verify_gap_text.self_test` both make about
    their own digests. The schedules below are typed, not generated from the
    committed file, so a shape that stopped matching this checker would not be
    satisfied by the checker having been written to match it.
    """
    ok = True

    def assert_that(cond, what):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", what))
        ok = ok and bool(cond)

    def problems_for(**kw):
        return scan(schedule_text(**kw))[1]

    def quiet(fn, *argv, **kwargs):
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            rc = fn(*argv, **kwargs)
        return sink.getvalue(), rc

    # The control: the shape the file has, held green. Without it, every
    # refusal below is a check that has stopped checking.
    base = problems_for()
    assert_that(base == [], "the shape below is clean, so the refusals that "
                "follow are the refusals and not the baseline")

    # The same control with the emit step explaining itself, which is what the
    # committed schedule's block does: it has to say *why* it passes no
    # `--limit` and why it pins `SDAS8051`, and both sentences are inside the
    # `run:`. A rule that fires on the text stating it is a rule everybody
    # disables, and this is the case that decides whether the tool survives a
    # week -- so it is pinned rather than left to be discovered.
    chatty = problems_for(comments="no --limit here, and SDAS8051 is pinned "
                                   "empty rather than to a nix path")
    assert_that(chatty == [],
                "an emit step whose own comments name --limit and SDAS8051 is "
                "clean: comments are stripped before the flag rules are read, "
                "so the schedule can document what it does not do")

    # The pre-#416 file, transcribed: one upload, no emit step. This is the
    # control the whole check exists for, and it is the two things that were
    # absent rather than a hand-wave about them.
    before = problems_for(n_uploads=1, emit=False)
    assert_that(any("no step passes --emit-csv" in p for p in before),
                "a schedule with no emit step is refused for that, and the "
                "message says which step is missing")
    assert_that(any("1 upload-artifact step(s)" in p for p in before),
                "and for having one artifact rather than two")

    # Equal names merge the two uploads into one artifact on v4+, so the
    # "two artifacts" claim goes quietly false. A count cannot see this.
    same = problems_for(log_name="deep-gates-csv-" + RUN_ID)
    assert_that(any("share a name" in p for p in same),
                "two uploads sharing a name are refused: v4+ would merge them "
                "into one artifact, which is the claim that would be false")
    assert_that(len(same) == 1,
                "and that is the only thing wrong with it -- a name clash is "
                "not a whole schedule")

    # The run id is what pairs a night's two files for a reader.
    for field, kw in (("log", {"log_name": "deep-gates-log"}),
                      ("csv", {"csv_name": "deep-gates-csv"})):
        found = problems_for(**kw)
        assert_that(sum("does not carry ${{ github.run_id }}" in p
                        for p in found) == 1,
                    "the %s artifact's name without the run id is refused, and "
                    "the other one is not" % field)

    # `if: always()` is what puts an artifact on the night a reader wants.
    found = problems_for(log_always=False)
    assert_that(any("not `if: always()`" in p for p in found),
                "an upload that is not `if: always()` is refused")

    # The invariant, as a claim rather than a parenthetical.
    for kw, why in (({"csv_path": "ec/ghidra/deep-gates-csv.csv"},
                     "under the repository"),
                    ({"csv_path": "deep-gates-csv.csv"},
                     "not rooted at ${{ runner.temp }}"),
                    ({"csv_path": RUNNER_TEMP_EXPR + "/" + REPORT.name},
                     "names the committed report")):
        found = problems_for(**kw)
        assert_that(bool(found), "a CSV artifact %s is refused" % why)

    # The coupling: the file the step writes is the file the upload collects.
    found = problems_for(upload_csv_name="some-other-csv.csv")
    assert_that(any("no upload-artifact collects" in p for p in found),
                "an upload that collects a second CSV is refused even though "
                "it is rooted at ${{ runner.temp }} -- two well-formed paths "
                "are not the same path")

    # A sampled CSV cannot be joined against the committed report.
    found = problems_for(extra_run=" --limit 100")
    assert_that(any("passes --limit" in p for p in found),
                "an emit step passing --limit is refused")

    # The boundary the emit step's own log section sits on: the flag named in a
    # message rather than passed as an argument. The step is still found --
    # `echo "=== per-row CSV (--emit-csv) ==="` is a real mention in real code
    # -- and what is refused is the missing destination, which is the half that
    # couples the file written to the file uploaded.
    mention = problems_for(mention_only=True)
    assert_that(any("not as an argument" in p for p in mention),
                "a step that only *mentions* --emit-csv in one of its own "
                "messages is refused for having no destination to read, which "
                "is the clause that cannot be satisfied by a sentence")

    # SDAS8051, both directions, because they are two different mistakes.
    nix = problems_for(sdas="SDAS8051=/nix/store/abc-sdcc/bin/sdas8051 ")
    assert_that(any("sets SDAS8051 to `/nix/store" in p for p in nix),
                "a non-empty SDAS8051 is refused: it would point the CSV's "
                "`assembler` column at a different binary than the schedule "
                "prints beside it")
    unset = problems_for(omit_sdas=True)
    assert_that(any("never pins SDAS8051" in p for p in unset),
                "and so is an emit step that never pins it, which leaves the "
                "reading to whatever the runner's environment carries")

    # Holds 4 and 5, against the committed tree, through the real functions.
    committed, held = header_coupling()
    assert_that(committed == [] and held == 2,
                "the committed tree: emit_csv()'s header is byte-identical to "
                "the report's, and refuses_committed_report() still refuses "
                "the report (%s)" % (committed or "2 of 2 held"))

    # The cap, as a control. 52 rows printed as 52 lines is the whole reason
    # this tool exists, and a reader with the log's habit would reintroduce it.
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "night.csv", Path(tmp) / "report.csv"
        write_rows(a, 52, outcome="match")
        write_rows(b, 52, outcome="assembler-gap")
        text, rc = quiet(diff_mode, str(a), str(b))
        lines = [ln for ln in text.splitlines() if ln.startswith("  moved")]
        assert_that(len(lines) == 52 and "more" not in text,
                    "a 52-row diff prints 52 lines, not 20 and \"and N more\" "
                    "-- the MOVED_CAP = 20 defect as a control (%d lines, "
                    "exit %r)" % (len(lines), rc))
        assert_that(rc == 0,
                    "and a diff that moved 52 rows is not a failure: §14h "
                    "measured 52 between the committed report and the apt "
                    "build a runner installs, so that is a nightly working")

    # Nothing moving, said in words.
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "night.csv", Path(tmp) / "report.csv"
        write_rows(a, 3, outcome="match", assembler="sdas8051 02.00")
        write_rows(b, 3, outcome="match", assembler="sdas8051 05.50.4")
        text, rc = quiet(diff_mode, str(a), str(b))
        assert_that("no row moved" in text and rc == 0,
                    "a pair whose only difference is the `assembler` column "
                    "moves nothing -- that column names the build, and "
                    "comparing it would report every row every night")

    # One side's row is named as such, not dropped into a moved count.
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "night.csv", Path(tmp) / "report.csv"
        write_rows(a, 3, outcome="match")
        write_rows(b, 4, outcome="match")
        text, rc = quiet(diff_mode, str(a), str(b))
        assert_that("only in report.csv" in text and rc == 0,
                    "a row on one side only is named as such")

    # Two headers, so a join would be reading two different tables.
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "night.csv", Path(tmp) / "report.csv"
        write_rows(a, 1, outcome="match")
        write_rows(b, 1, outcome="match", extra="detail")
        _text, rc = quiet(diff_mode, str(a), str(b))
        assert_that(rc == 1, "two different headers exit 1 rather than "
                    "comparing two tables and calling it agreement")

    # §14b's shape: found nothing is not found nothing wrong.
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "night.csv", Path(tmp) / "report.csv"
        write_rows(a, 0, outcome="match")
        write_rows(b, 0, outcome="match")
        text, rc = quiet(diff_mode, str(a), str(b))
        assert_that(rc == 1 and "located no row" in text,
                    "a pair with no rows exits 1 and says the population is "
                    "empty, so a broken discovery cannot read as agreement")

    with tempfile.TemporaryDirectory() as tmp:
        _text, rc = quiet(diff_mode, str(Path(tmp) / "nope.csv"),
                          str(Path(tmp) / "also-nope.csv"))
        assert_that(rc == 2, "a file that is not there is 2, distinct from "
                    "both the empty and the disagreeing answers")

    # Unparseable text is a reported problem, not a traceback.
    _found, broken = scan("steps: [\n  this is not: valid\n")
    assert_that(broken and "does not parse" in broken[0],
                "a schedule that does not parse is reported in words")
    _found, shape = scan("- a list\n- not a workflow\n")
    assert_that(shape and "not a workflow mapping" in shape[0],
                "and one that parses to the wrong shape too")

    print()
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def write_rows(path, n, outcome="match", assembler="sdas8051 02.00",
               extra=None):
    """A `write_report`-shaped CSV of `n` rows, for the join's cases.

    The columns are the committed report's own, in its order, because a fixture
    with a different column set would pass a `--diff` that compared nothing.
    """
    fields = ["program", "addr", "name", "outcome", "listing_digest",
              "instructions_checked", "instructions_unchecked", "detail",
              "assembler"]
    if extra:
        fields.insert(-1, extra)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(fields)
        for i in range(n):
            w.writerow(["bank0", "%04X" % (0x1000 + i), "fn_%04X" % i, outcome,
                        "d%031d" % i, 4, 0, "", assembler])


def schedule_text(csv_path="$RUNNER_TEMP/deep-gates-csv.csv",
                  csv_name="deep-gates-csv-" + RUN_ID,
                  upload_csv_name=None,
                  log_name="deep-gates-" + RUN_ID,
                  log_always=True, n_uploads=2, emit=True, sdas="SDAS8051='' ",
                  extra_run="", omit_sdas=False, comments="", mention_only=False):
    """A schedule carrying the shape `--check` holds, with a knob per refusal.

    Typed rather than derived from the committed file, so the cases below are
    comparing a hand-written control against a hand-written expectation rather
    than a file against itself.
    """
    steps = [
        "      - name: Checkout\n        uses: actions/checkout@abc # v7\n",
        "      - name: Deep gates\n        run: |\n"
        "          AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh 2>&1 \\\n"
        "            | tee \"$RUNNER_TEMP/deep-gates.log\"\n",
    ]
    if emit:
        # Assembled line by line rather than by one format string, because a
        # block scalar's indentation is set by its first non-empty line: an
        # empty comment knob concatenated onto the command would indent the
        # command 20 spaces and end the block two lines later.
        body = ["          %spython3 ec/tools/verify_reassembly.py \\"
                % ("" if omit_sdas else sdas),
                '            --work "$RUNNER_TEMP/reasm-csv" --jobs 4 \\',
                '            --emit-csv "%s"%s' % (csv_path, extra_run)]
        if mention_only:
            # The flag survives only in the step's own announcement, which is
            # what the committed schedule's log section does at the top of the
            # block. Real code, a real mention, and not an argument.
            body[-1] = "            --report%s" % extra_run
            body.insert(0, '          echo "=== per-row CSV (--emit-csv) ==="')
        if comments:
            body.insert(0, "          # " + comments)
        steps.append("      - name: Emit the per-row CSV\n"
                     "        if: always()\n        run: |\n"
                     + "\n".join(body) + "\n")
    steps.append(
        "      - name: Upload the deep gates log\n"
        "        if: %s\n"
        "        uses: actions/upload-artifact@sha # v7.0.1\n"
        "        with:\n          name: %s\n"
        "          path: %s/deep-gates.log\n"
        "          if-no-files-found: warn\n          retention-days: 90\n"
        % ("always()" if log_always else "success()", log_name,
           RUNNER_TEMP_EXPR))
    if n_uploads == 2:
        steps.append(
            "      - name: Upload the deep gates CSV\n"
            "        if: always()\n"
            "        uses: actions/upload-artifact@sha # v7.0.1\n"
            "        with:\n          name: %s\n          path: %s/%s\n"
            "          if-no-files-found: warn\n          retention-days: 90\n"
            % (csv_name, RUNNER_TEMP_EXPR,
               upload_csv_name or csv_path.rsplit("/", 1)[-1]))
    return ("name: Deep gates\n\non:\n  workflow_dispatch:\n\n"
            "permissions:\n  contents: read\n\njobs:\n  deep:\n"
            "    runs-on: ubuntu-latest\n    steps:\n" + "".join(steps))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="hold the prepared schedule's shape against "
                         "ec/ghidra/reassembly.csv (the default)")
    ap.add_argument("--schedule", metavar="PATH", default=None,
                    help="read this schedule instead of the committed one. It "
                         "exists so a suite can run --check over a mutated "
                         "*copy* of the real file as a subprocess, which is the "
                         "only way to see the exit code a consumer sees; "
                         "patching SCHEDULE in-process could not, and a typed "
                         "fixture is this tool's own idea of what the file "
                         "looks like")
    ap.add_argument("--diff", nargs=2, metavar=("NIGHT.csv", "REPORT.csv"),
                    help="join two report CSVs on (program, addr) and print "
                         "every row that moved, uncapped")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusals, on typed schedule text and on reports "
                         "written into a tempfile")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.diff:
        return diff_mode(*args.diff)

    subject = Path(args.schedule) if args.schedule else SCHEDULE
    try:
        text = subject.read_text(encoding="utf-8")
    except OSError as exc:
        print("cannot read %s: %s" % (subject, exc), file=sys.stderr)
        return 1
    found, problems = scan(text)
    problems = list(problems) + header_coupling()[0]

    # The scope and the population print whether or not anything was found, the
    # way `tools/check_doc_patch_refs.py` does it: a reader holding only the
    # exit code should be able to tell a clean file from a discovery that
    # matched nothing. The counts are of this run, not of the tree.
    # Repository-relative where the subject is in the repository, so the line
    # reads the same whichever file it names. A `--schedule` copy under a
    # tempdir is not, and printing it absolute is the honest answer there.
    shown = (subject.relative_to(REPO) if subject.is_relative_to(REPO)
             else subject)
    print("the prepared schedule %s, and the header and the refusal it "
          "depends on in %s and %s"
          % (shown, REPORT.relative_to(REPO), VERIFY.relative_to(REPO)))
    try:
        columns = len(read_rows(REPORT)[0])
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        # The hold below already refuses a header it cannot read; this is the
        # count beside it, so a broken census prints as a broken census rather
        # than taking the run down with a traceback before the verdict.
        columns = 0
        problems.append("cannot read the committed report's header: %s" % exc)
    print("%d upload-artifact step(s), %d named; --emit-csv writes %s; "
          "%d column(s) compared by --diff, %s not"
          % (len(found.uploads), len({u.name for u in found.uploads}),
             found.destination, max(columns - len(NOT_COMPARED), 0),
             ", ".join(NOT_COMPARED)))
    for problem in problems:
        print("  FAIL  %s" % problem)
    if not found.uploads:
        print("  found no upload-artifact step at all, which is a broken "
              "discovery rather than a clean file", file=sys.stderr)
        return 1
    if problems:
        print("%d problem(s) with the prepared schedule's shape" % len(problems),
              file=sys.stderr)
        return 1
    print("the shape is as documented: two artifacts, distinct names carrying "
          "the run id, the CSV under $RUNNER_TEMP, and a header the committed "
          "report still matches byte for byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
