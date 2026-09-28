#!/usr/bin/env python3
"""Hold the half of the prepared nightly's shape its sibling does not.

**Which half is which, first, so two tools are not mistaken for two opinions.**
`docs/ci/agent-gates-deep-schedule.yml` has two checkers over it and they hold
disjoint sets of claims. `tools/check_deep_schedule_emit.py` holds the *second
artifact*: two uploads, distinct names carrying the run id, both `if:
always()`, the CSV under `$RUNNER_TEMP`, `--emit-csv` with no `--limit`,
`SDAS8051` pinned empty, and the header `verify_reassembly.emit_csv` writes
today being byte-identical to `ec/ghidra/reassembly.csv`'s. This file holds
the other five, which are about the file as a *workflow* rather than about one
of its artifacts. Neither re-derives anything the other does, and a claim
neither holds is a claim neither of them is evidence for.

`--check` holds:

  1. `on:` carries a `schedule:` whose every entry has a `cron:`, **and**
     `workflow_dispatch`. The two are what make this file a nightly a human can
     also run on demand, and `docs/agent-pipeline.md` item 1 describes the
     schedule in exactly those words.
  2. The gate script is invoked **once**, and as
     `AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh`. Both halves are
     needed and neither is sufficient: a second invocation is a second gate
     that can disagree with the first, and the deep flag is what distinguishes
     this file from the cheap tier `ci.yml` already runs on every commit.
     Dropping the flag would leave a "nightly" re-encoding nothing, silently,
     with the log looking like a pass.
  3. That invocation's output goes through a `tee` to a path under
     `$RUNNER_TEMP`, downstream of the command rather than merely present in
     the same block. **What this does not hold: `set -o pipefail`.** The
     schedule's own comment calls it load-bearing -- without it the status is
     `tee`'s, which is zero however the gate ended, so a failing deep tier
     reads as a passing one -- and this tool does not check it. That gap is
     named in `docs/findings/deep-schedule-lint-baseline.md` rather than
     quietly filled here, because a sixth rule the issue did not ask for is a
     scope decision and not this tool's to make.
  4. `permissions:` is top-level `contents: read` and nothing wider, and no
     job carries its own. A job-level block is how "nothing wider" stops being
     true while the top-level line still reads correctly, so the claim is held
     over the whole file rather than over the key the issue named.
  5. Every `uses:` is a full 40-hex SHA or a local `./` path that resolves on
     disk. This is zizmor's `unpinned-uses` audit, held offline.

Holds 4 and 5 are the two audits zizmor runs over this file that can be decided
from committed bytes. Neither is a lint, and neither runs zizmor: they are the
two shapes, re-derived, so a prepared file nothing lints still has a floor under
the part of the lint that matters most here. No network, no `git`, no linter,
no assembler.

**A green run says the wiring is right, and nothing more.** Nothing here runs
the schedule: it is prepared, not landed, so no nightly has run this file and
no artifact exists to read. Every verdict is a claim about a file's *shape*.
In particular a green run is **not** a claim that actionlint or zizmor pass --
`docs/findings/deep-schedule-lint-baseline.md` records which of those were
actually measured and which could not be, and the honest answer as of
2026-09-28 is one of the three checks actionlint performs (shellcheck over
every `run:` block) with the other two unmeasured. This tool does not close
that gap and does not claim to.

`shell_code()` and `RUNNER_TEMP_SHELL` are imported from the sibling rather
than rewritten, for the reason `tools/check_dmi_descriptor.py` gives for
`check_status_vocabulary`: two checkers reading the same file must not come to
disagree about what a comment is or which three spellings of `$RUNNER_TEMP`
count, or a schedule can be clean to one and red to the other for no reason.
`tools/test_check_deep_schedule_shape.py` pins the agreement.

Usage:
    python3 tools/check_deep_schedule_shape.py [--check]
    python3 tools/check_deep_schedule_shape.py --schedule PATH
    python3 tools/check_deep_schedule_shape.py --self-test
"""
import argparse
import collections
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCHEDULE = REPO / "docs" / "ci" / "agent-gates-deep-schedule.yml"

# Reused rather than restated; see the module docstring.
sys.path.insert(0, str(HERE))
from check_deep_schedule_emit import (  # noqa: E402
    RUNNER_TEMP_SHELL, steps, shell_code)

# The key `on:` parses to, under both YAML revisions a reader might have.
# PyYAML implements YAML 1.1, where the bare word `on` is the boolean true, so
# a workflow's triggers arrive as `doc[True]` -- a checker that wrote
# `doc.get("on")` would find nothing, and would either refuse a correct file or
# pass everything while believing it had read the triggers. Both spellings are
# accepted so this tool says nothing about which parser read the file.
ON_KEYS = (True, "on")

# The gate script, and the one form of calling it this file may use. Counted as
# occurrences in comment-stripped `run:` text rather than as steps, so a block
# that runs it twice is the finding it is rather than a step count that reads
# one.
GATE = ".github/scripts/agent-gates.sh"
GATE_CALL = re.compile(r"AGENT_GATES_DEEP=1\s+" + re.escape(GATE) + r"(?!\S)")

# A `| tee <path>`, capturing the path. The pipe is part of the pattern because
# "goes through a tee" is the claim: a step that merely runs `tee` is not one.
# `-a` is accepted because appending to the same log is the same record; the
# path stops at a quote, a space, a backslash or a pipe, so the three
# `$RUNNER_TEMP` spellings -- two of which are shell-quoted here -- come out
# whole.
TEE = re.compile(r"\|\s*tee\s+(?:-a\s+)?[\"']?([^\"'\s\\|]+)")

# `owner/repo@<ref>`: the shape every non-local `uses:` has to be before the
# `@`. The ref itself is the 40-hex test below.
USES = re.compile(r"^(?P<action>[\w.\-]+/[\w.\-]+)@(?P<ref>\S+)$")
SHA = re.compile(r"^[0-9a-f]{40}$")

# The one `permissions:` mapping hold 4 permits, as a constant because the
# fixture's default and the checker's expectation have to be the same object by
# construction rather than by two spellings agreeing.
READ_ONLY = {"contents": "read"}

# The local action the committed schedule uses, and the one the fixture points
# at. A real directory with a real `action.yml` in this repository, so a
# fixture naming it exercises hold 5's resolution path rather than skipping it:
# a synthetic `./.github/actions/fake` would have to invent a tree, and a
# fixture that never resolves is a fixture that never tested the refusal.
LOCAL_ACTION = "./.github/actions/project-setup"

# What one schedule read found. A namedtuple rather than a dict so a field
# added without a reader is a TypeError at construction. `uses` is read across
# every job, so a second job cannot add an unpinned action unnoticed.
Shape = collections.namedtuple("Shape", "triggers permissions uses gate tee")

# One `uses:` and where it was read from: a step's, or a job's (a reusable
# workflow call). Both are the same claim to zizmor and both are places an
# unpinned reference can appear, so a checker reading only `steps[*]` would hold
# half of it, and a refusal has to say which it found.
Uses = collections.namedtuple("Uses", "where value")


def all_uses(doc):
    """Every `uses:` in `doc`, as `Uses` records.

    A job's `uses:` is a reusable workflow rather than an action, and the two
    are read together deliberately: both are `uses:` keys, both are the thing
    `unpinned-uses` audits, and reading only the step form is how a prepared
    file grows an unpinned reference in the one place this tool is not looking.
    """
    out = []
    jobs = doc.get("jobs") or {}
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if isinstance(job.get("uses"), str):
            out.append(Uses("job %r" % name, job["uses"]))
    for step in steps(doc):
        if isinstance(step.get("uses"), str):
            out.append(Uses("step %r" % (step.get("name") or step["uses"]),
                            step["uses"]))
    return out


def triggers_of(doc):
    """The workflow's `on:` mapping, whichever spelling the parser left it under.

    Returns `None` rather than a problem, so a caller can print what was found
    and the refusal can be worded once, here.
    """
    for key in ON_KEYS:
        if key in doc:
            value = doc[key]
            return value if isinstance(value, dict) else None
    return None


def trigger_problems(doc, triggers):
    """Hold 1: a `schedule:` of real `cron:`s, and `workflow_dispatch` beside it."""
    problems = []
    if triggers is None:
        return ["the file carries no readable `on:` block, so nothing says what "
                "triggers it. Under YAML 1.1 the bare word parses as the "
                "boolean true, which is why this looks for both spellings."]

    if "workflow_dispatch" not in triggers:
        problems.append(
            "there is no `workflow_dispatch`, so the nightly cannot be run on "
            "demand. GitHub delays and sometimes drops scheduled runs without "
            "telling anyone, and a manual run is what distinguishes \"the "
            "nightly did not run\" from \"the nightly found nothing\".")
    schedule = triggers.get("schedule")
    if schedule is None:
        problems.append(
            "there is no `schedule:`, so nothing has ever run this file: it is "
            "prepared, and only a human's `cp` puts it in `.github/workflows/`, "
            "where a `schedule:` is what starts it.")
    elif not isinstance(schedule, list) or not schedule:
        problems.append(
            "`schedule:` is %s and not a non-empty list, so GitHub reads no "
            "trigger from it." % (type(schedule).__name__,))
    else:
        for entry in schedule:
            if not isinstance(entry, dict) or not str(entry.get("cron", "")).strip():
                problems.append(
                    "a `schedule:` entry is %r with no `cron:`. GitHub reads "
                    "one entry per run time, so an entry without one is an "
                    "entry that never fires."
                    % (entry,))
    return problems


def gate_problems(doc):
    """Holds 2 and 3: one invocation, in the deep form, teed to `$RUNNER_TEMP`.

    Returns `(problems, gate_label, tee_dest)` because hold 3's target is only
    meaningful next to the step hold 2 found -- a `tee` in a step that is not
    the gate's says nothing about the gate's output.
    """
    problems = []
    calling = [(step, shell_code(step["run"]))
               for step in steps(doc)
               if isinstance(step.get("run"), str)
               and GATE in shell_code(step["run"])]
    mentions = sum(len(re.findall(re.escape(GATE), code)) for _s, code in calling)
    label = calling[0][0].get("name") if len(calling) == 1 else None
    tee_dest = None

    if not calling:
        problems.append(
            "no step runs %s, so a landed nightly would run no gate at all. "
            "The cheap tier is what `ci.yml` already runs per commit; this "
            "file exists to restore the re-encode on top of it."
            % GATE)
    elif mentions != 1:
        problems.append(
            "%s is named %d time(s) across %d step(s) (%s). One nightly that "
            "runs the gate once is a run whose log is a record; two are two "
            "gates that can disagree, and the artifact a reader joins is then "
            "ambiguous."
            % (GATE, mentions, len(calling), ", ".join(
                repr(s.get("name")) for s, _c in calling)))
    else:
        step, code = calling[0]
        label = step.get("name")
        if not GATE_CALL.search(code):
            problems.append(
                "the step %r runs %s without the `AGENT_GATES_DEEP=1` prefix. "
                "That prefix is the whole difference between this file and the "
                "cheap tier `ci.yml` runs on every commit: without it the "
                "nightly re-encodes nothing, and its log is shaped exactly like "
                "a pass."
                % (label, GATE))

        # Hold 3, as a coupling rather than a substring: the tee has to be on
        # this step's output and after the command. A `tee` elsewhere in the
        # block, or one that ran first, is not the gate's record.
        match = TEE.search(code)
        if match is None:
            problems.append(
                "the step %r does not pipe the gate's output through a `tee`. "
                "A run that happened leaves an artifact behind and a run that "
                "did not leaves none, and without the pipe the only way to tell "
                "them apart is to infer it from silence." % label)
        elif code.index(GATE) > match.start():
            problems.append(
                "the `tee` in the step %r comes before %s, so it cannot be "
                "recording the gate's output." % (label, GATE))
        else:
            tee_dest = match.group(1)
            if not tee_dest.startswith(RUNNER_TEMP_SHELL):
                problems.append(
                    "the gate's output is teed to `%s`, which is not under "
                    "$RUNNER_TEMP. A log written inside the repository is one "
                    "a later edit can point somewhere that matters, and the "
                    "schedule's own uploads read from runner.temp."
                    % tee_dest)
    return problems, label, tee_dest


def permission_problems(doc):
    """Hold 4: top-level `contents: read`, and no job wider than that."""
    problems = []
    permissions = doc.get("permissions")
    if permissions is None:
        problems.append(
            "there is no `permissions:` block, so the file runs on whatever "
            "the repository's default token allows. The deep gate reads the "
            "repository and runs an assembler, so it asks for `contents: read` "
            "and nothing else -- and saying so is what stops a default widening "
            "underneath it.")
    elif permissions != {"contents": "read"}:
        wider = {k: v for k, v in permissions.items()
                 if not (k == "contents" and v == "read")}
        problems.append(
            "the top-level `permissions:` is %r rather than `contents: read`%s. "
            "The gate reads the repository and runs an assembler; a token wider "
            "than that is a credential no step here has a use for."
            % (permissions,
               (" -- wider than `contents: read`: %s" % ", ".join(
                   sorted(wider))) if wider else ""))
    # Held over the file rather than over the top-level key, because a job's
    # own block overrides it and `contents: read` at the top of the file would
    # then still read correctly while saying something else.
    for name, job in (doc.get("jobs") or {}).items():
        if isinstance(job, dict) and job.get("permissions") is not None:
            problems.append(
                "the job %r declares its own `permissions: %r`, which overrides "
                "the file's. The claim being held is that the file asks for "
                "`contents: read` and nothing wider, and that is a claim about "
                "every job rather than about the top-level key alone."
                % (name, job["permissions"]))
    return problems


def uses_problems(uses, root=REPO):
    """Hold 5: a 40-hex SHA or a local `./` path that resolves."""
    problems = []
    for use in uses:
        value = use.value
        if value.startswith("./"):
            # A local reference is resolved against the repository root, which
            # is where `.github/actions/` lives; the path has to be there or the
            # step cannot run, and a renamed action is exactly the edit a
            # prepared file sits exposed to.
            target = (root / value[2:]) / "action.yml"
            if not target.is_file():
                problems.append(
                    "the local %s `%s` has no `action.yml` at %s. A local `uses:` "
                    "is exempt from the SHA pin precisely because it is in this "
                    "repository, so a path that stopped resolving is the only "
                    "thing that can catch it."
                    % (use.where, value, target))
            continue
        match = USES.match(value)
        if match is None:
            problems.append(
                "the %s `%s` is neither a local `./` path nor an "
                "`owner/repo@<sha>` reference." % (use.where, value))
            continue
        ref = match.group("ref")
        if SHA.match(ref):
            continue
        problems.append(
            "the %s `%s` is pinned to `%s` and not to a 40-character commit "
            "sha. A tag or a branch is a reference that moves, and this file "
            "is prepared precisely so a human can copy it into "
            "`.github/workflows/` without a review in between."
            % (use.where, value, ref))
    return problems


def scan(text, root=REPO):
    """`(Shape, [problem])` for one schedule file's text.

    The subject is the text rather than the file, so a case can point this at
    a few lines of fixture and read the finding. Every hold reports rather than
    raises: a file that does not parse is a problem this prints, not a
    traceback a gate turns into a confusing exit.
    """
    problems = []
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return Shape(None, None, [], None, None), [
            "the file does not parse as YAML: %s" % exc]
    if not isinstance(doc, dict):
        return Shape(None, None, [], None, None), [
            "the file parsed to %s, not a workflow mapping" % type(doc).__name__]

    triggers = triggers_of(doc)

    problems += trigger_problems(doc, triggers)
    permissions = doc.get("permissions")
    gate_problems_found, label, tee_dest = gate_problems(doc)
    problems += gate_problems_found
    problems += permission_problems(doc)
    uses = all_uses(doc)
    problems += uses_problems(uses, root=root)
    return Shape(triggers, permissions, uses, label, tee_dest), problems


def self_test():
    """The refusals, on typed schedule text and on the committed file.

    An oracle never recorded from this tool: a self-test that derives its
    expectation from the code under test asserts nothing. The schedules below
    are typed, not generated from the committed file, so a shape that stopped
    matching this checker would not be satisfied by the checker having been
    written to match it.
    """
    ok = True

    def assert_that(cond, what):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", what))
        ok = ok and bool(cond)

    def problems_for(**kw):
        return scan(schedule_text(**kw), root=REPO)[1]

    # The control: the shape the file has, held green. Without it, every
    # refusal below is a check that has stopped checking.
    assert_that(problems_for() == [],
                "the shape below is clean, so the refusals that follow are the "
                "refusals and not the baseline")

    # The committed file, so the self-test says something about the tree and
    # not only about a fixture. Held through the same five holds, and read with
    # `REPO` as the root so the local `uses:` has a real action.yml to resolve.
    _found, committed = scan(SCHEDULE.read_text(encoding="utf-8"), root=REPO)
    assert_that(committed == [],
                "the committed schedule is clean (%s)" % ("; ".join(committed)
                                                           or "no problem"))

    # Hold 1, both halves, and the YAML revision that hides one of them.
    found = problems_for(dispatch=False)
    assert_that(any("no `workflow_dispatch`" in p for p in found),
                "a schedule with no workflow_dispatch is refused: the nightly "
                "cannot be run on demand, which is what tells a dropped run "
                "from an empty one")
    found = problems_for(schedule=False)
    assert_that(any("no `schedule:`" in p for p in found),
                "and one with no schedule: is refused, because nothing would "
                "ever run it")
    found = problems_for(cron=False)
    assert_that(any("no `cron:`" in p for p in found),
                "and a schedule: entry carrying no cron: is refused, because "
                "GitHub reads one entry per run time")
    # `on:` is the boolean true under YAML 1.1, which is the revision PyYAML
    # implements and the one that reads the committed file. A checker written
    # against the string key alone would find no triggers at all and would be
    # refusing a correct file while believing it had read them.
    assert_that(True in yaml.safe_load(schedule_text()),
                "the fixture's `on:` parses to the boolean true, which is why "
                "the checker reads both that key and the string one")
    found, _problems = scan(schedule_text(), root=REPO)
    assert_that(found.triggers is not None and "schedule" in found.triggers,
                "and the triggers are read anyway, rather than the file being "
                "refused for carrying none")

    # Hold 2, both halves, and they are different mistakes.
    found = problems_for(deep_flag=False)
    assert_that(any("without the `AGENT_GATES_DEEP=1` prefix" in p for p in found),
                "the gate run without the deep flag is refused: it would "
                "re-encode nothing and its log would be shaped like a pass")
    found = problems_for(gate_twice=True)
    assert_that(any("named 2 time(s)" in p for p in found),
                "and so is a second invocation, which is two gates that can "
                "disagree rather than one run with a record")
    found = problems_for(gate=False)
    assert_that(any("no step runs" in p for p in found),
                "a file that runs no gate at all is refused for that, and the "
                "message says what is missing")

    # Hold 3, as a coupling: the tee has to be on the gate's output.
    found = problems_for(tee=False)
    assert_that(any("does not pipe" in p for p in found),
                "a gate step with no tee is refused: the only way to tell a run "
                "that happened from one that did not is the artifact")
    found = problems_for(tee_path="logs/deep-gates.log")
    assert_that(any("not under\n$RUNNER_TEMP" in p or "not under $RUNNER_TEMP" in p
                    for p in found),
                "and so is a tee into the repository, where a later edit can "
                "point it somewhere that matters")
    found = problems_for(tee_first=True)
    assert_that(any("comes before" in p for p in found),
                "and so is a tee that runs before the gate, which cannot be "
                "recording its output")

    # Hold 4, both halves.
    found = problems_for(permissions={"contents": "write"})
    assert_that(any("rather than `contents: read`" in p for p in found),
                "a `contents: write` token is refused: the gate reads the "
                "repository and runs an assembler, and needs nothing else")
    found = problems_for(permissions={"contents": "read", "actions": "write"})
    assert_that(any("wider than `contents: read`: actions" in p for p in found),
                "and so is an extra scope at the same width, which a `!=` on "
                "the mapping alone would catch without saying which")
    found = problems_for(permissions=None)
    assert_that(any("no `permissions:` block" in p for p in found),
                "and so is no block at all, which leaves the file on whatever "
                "the repository default allows")
    found = problems_for(job_permissions={"contents": "write"})
    assert_that(any("declares its own `permissions:" in p for p in found),
                "and so is a job that widens its own, because it overrides the "
                "top-level block the claim is read from")

    # Hold 5, all three refusals, and the two forms that are fine.
    found = problems_for(tag_pin="actions/upload-artifact@v7.0.1")
    assert_that(any("not to a 40-character commit sha" in p for p in found),
                "a tag rather than a sha is refused: it is a reference that "
                "moves, and a prepared file is copied without review")
    found = problems_for(sha_pin="not-a-sha-at-all")
    assert_that(any("not to a 40-character commit sha" in p for p in found),
                "and so is a ref that is not a sha in any form")
    found = problems_for(uses_extra="actions/setup-python")
    assert_that(any("neither a local `./` path" in p for p in found),
                "and so is a `uses:` carrying no `@` reference at all")
    found = problems_for(local_action="./.github/actions/no-such-action")
    assert_that(any("has no `action.yml`" in p for p in found),
                "a local `uses:` pointing at nothing is refused: it is exempt "
                "from the pin, so a path that stopped resolving is the only "
                "thing that catches it")
    clean = problems_for()
    assert_that(not any("action.yml" in p for p in clean),
                "and the local action the committed file names is one that "
                "resolves, so the refusal above is the rule and not a broken "
                "root")

    # The strip, from both sides, and it is the clause that decides whether this
    # tool survives a week: a rule that fires on the sentence stating it is a
    # rule everybody switches off. The committed schedule documents what it
    # does -- the deep flag, the tee, where the log lands -- and has to be able
    # to say so inside its own `run:` blocks.
    #
    # One fixture, three readings. The comment names the gate command in the
    # deep form and names $RUNNER_TEMP, and the step runs the gate with no tee,
    # so a strip that removed nothing would make all three fail: the gate would
    # read as named twice, and the comment's $RUNNER_TEMP would satisfy the tee.
    named = problems_for(
        comments="the same command is AGENT_GATES_DEEP=1 %s, and its output "
                 "is written under $RUNNER_TEMP" % GATE, tee=False)
    assert_that(not any("named 2 time(s)" in p for p in named),
                "a comment naming the gate command is not a second invocation")
    assert_that(any("does not pipe" in p for p in named),
                "and a comment naming $RUNNER_TEMP is not a tee, so the step is "
                "still refused for having none")
    assert_that("'Deep gates'" in "\n".join(named),
                "and the step that runs the gate is still the one named in the "
                "refusal, so the comment did not hide it either")

    # Unparseable text is a reported problem, not a traceback.
    _found, broken = scan("jobs: [\n  this is not: valid\n")
    assert_that(broken and "does not parse" in broken[0],
                "a schedule that does not parse is reported in words")
    _found, shape = scan("- a list\n- not a workflow\n")
    assert_that(shape and "not a workflow mapping" in shape[0],
                "and one that parses to the wrong shape too")
    _found, no_on = scan("name: x\njobs: {}\n")
    assert_that(any("no readable `on:` block" in p for p in no_on),
                "and a workflow with no triggers at all")

    print()
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def schedule_text(cron=True, schedule=True, dispatch=True, deep_flag=True,
                  gate=True, gate_twice=False, tee=True, tee_path=None,
                  tee_first=False, permissions=READ_ONLY, job_permissions=None,
                  uses_extra=None, tag_pin=False, sha_pin=False,
                  local_action=LOCAL_ACTION, comments="",
                  cron_value="23 4 * * *"):
    """A schedule carrying the shape `--check` holds, with a knob per refusal.

    Typed rather than derived from the committed file, so the cases above are
    comparing a hand-written control against a hand-written expectation rather
    than a file against itself.

    `permissions` is tri-state on purpose: a mapping is written out, and `None`
    means the block is *absent* rather than empty. "No `permissions:`" and "`permissions:`
    with nothing in it" are different findings, and a default of `None` could
    not tell the first from the second -- nor from the correct one.
    """
    body = []
    if comments:
        body.append("          # " + comments)
    if tee_first:
        # Piped, so `TEE` matches it: a bare `tee` is not the pipe the hold
        # looks for, and the case would then be testing the regex rather than
        # the ordering.
        body.append('          echo starting | tee "%s/early.log"'
                    % (tee_path or "$RUNNER_TEMP"))
    body.append("          set -o pipefail")
    if gate:
        body.append("          %s%s 2>&1 \\"
                    % ("AGENT_GATES_DEEP=1 " if deep_flag else "", GATE))
        if tee:
            body.append('            | tee "%s"'
                        % (tee_path or "$RUNNER_TEMP/deep-gates.log"))
    else:
        body.append('          echo "this workflow runs no gate"')
    text = "      - name: Deep gates\n        run: |\n" + "\n".join(body) + "\n"

    checkout = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7"
    if tag_pin:
        checkout = "actions/upload-artifact@v7.0.1"
    if sha_pin:
        checkout = "actions/checkout@not-a-sha-at-all"
    if uses_extra:
        checkout = uses_extra
    steps = ["      - name: Checkout\n        uses: %s\n" % checkout,
             "      - name: Set up the toolchain\n        uses: %s\n"
             % local_action,
             text]
    if gate_twice:
        steps.append("      - name: Deep gates again\n        run: |\n"
                     "          %s%s\n"
                     % ("AGENT_GATES_DEEP=1 " if deep_flag else "", GATE))

    job = ["  deep:\n    runs-on: ubuntu-latest\n"]
    if job_permissions is not None:
        job.append("    permissions:\n      %s\n"
                   % "\n      ".join("%s: %s" % kv
                                     for kv in job_permissions.items()))
    job.append("    steps:\n")

    on = []
    if dispatch:
        on.append("  workflow_dispatch:\n")
    if schedule:
        on.append("  schedule:\n")
        if cron:
            on.append("    - cron: '%s'\n" % cron_value)
        else:
            on.append("    - run: nightly\n")

    head = "name: Deep gates\n\non:\n" + "".join(on) + "\n"
    if permissions is not None:
        head += "permissions:\n" + "".join("  %s: %s\n" % kv
                                           for kv in permissions.items()) + "\n"
    return head + "jobs:\n" + "".join(job) + "".join(steps)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="hold the prepared schedule's workflow shape (the "
                         "default)")
    ap.add_argument("--schedule", metavar="PATH", default=None,
                    help="read this schedule instead of the committed one, "
                         "which is how a suite runs --check as a subprocess "
                         "over a mutated *copy* and sees the exit code a "
                         "consumer sees")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusals, on typed schedule text and on the "
                         "committed file")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    subject = Path(args.schedule) if args.schedule else SCHEDULE
    try:
        text = subject.read_text(encoding="utf-8")
    except OSError as exc:
        print("cannot read %s: %s" % (subject, exc), file=sys.stderr)
        return 1
    # The local `uses:` is resolved against the repository root, which is where
    # `.github/actions/` lives and is the same root the workflow runs in. A
    # `--schedule` copy under a tempdir is still read that way, because a
    # prepared file is copied *into* the repository rather than run where it
    # is prepared.
    found, problems = scan(text, root=REPO)

    # The scope prints whether or not anything was found, the way
    # `tools/check_deep_schedule_emit.py` does it: a reader holding only the
    # exit code should be able to tell a clean file from a discovery that
    # matched nothing. The counts are of this run, not of the tree.
    shown = (subject.relative_to(REPO) if subject.is_relative_to(REPO)
             else subject)
    print("the prepared schedule %s, read for the shape its sibling does not "
          "hold: the triggers, the one gate command, its tee, the permissions "
          "width, and the %d `uses:` pin(s)"
          % (shown, len(found.uses)))
    for problem in problems:
        print("  FAIL  %s" % problem)
    if not found.uses:
        print("  found no `uses:` at all, which is a broken discovery rather "
              "than a clean file: no step and no job references an action, so "
              "the pin rule has nothing to read", file=sys.stderr)
        return 1
    if problems:
        print("%d problem(s) with the prepared schedule's workflow shape"
              % len(problems), file=sys.stderr)
        return 1
    print("the shape is as documented: a cron schedule with workflow_dispatch, "
          "one AGENT_GATES_DEEP=1 gate invocation teed under $RUNNER_TEMP, "
          "contents: read at the top level and nowhere wider, and every `uses:` "
          "a commit sha or a local path that resolves")
    print("  not held here: `set -o pipefail` before the tee, and actionlint's "
          "two non-shellcheck checks and zizmor's remaining audits. See "
          "docs/findings/deep-schedule-lint-baseline.md for which of those "
          "were measured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
