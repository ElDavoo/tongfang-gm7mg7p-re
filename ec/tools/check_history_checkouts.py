#!/usr/bin/env python3
"""Derive every workflow's checkout depth, and read the tools' sentences about it back.

Four sentences in two tools described what this repository's CI checkouts could
do, and all four were wrong: `ci.yml`'s `gates` job has checked out with
`fetch-depth: 0` since #407, and the sentence that named the shallow case was
naming `ci.yml`'s *other* job, which runs actionlint and zizmor and no history
reader at all. A contract paragraph that misdescribes the job it runs in is not
a cosmetic defect -- it is the paragraph the next tool's author copies -- so
this exists to make the paragraph re-derivable rather than remembered.

It is a **new file rather than a mode on either sibling**, per `CLAUDE.md`'s
rule, and the question is a different one: those two read git history, this
reads the workflows. What it asserts is *this* file's; nothing either sibling
does is changed by it.

**The measured half.** Every `actions/checkout` step under
`.github/workflows/`, with its effective depth -- the explicit `fetch-depth`,
or `actions/checkout`'s default of 1 where the step states none. Then the one
decidable invariant, which is the *inverse* of the claim that was stale: **every
job that runs a history reader has a full-depth checkout.** That is what fails
if a template re-copy from `ElDavoo/agent-pipeline` drops `fetch-depth: 0` from
`ci.yml`'s `gates` job, which would otherwise turn the cheap gate red with a
*history requirement* message that reads like a provenance failure rather than
like a workflow accident.

**What counts as a history reader** is decided from the committed files, never
from prose: a step whose `run:` names `.github/scripts/agent-gates.sh`,
`--verify-provenance`, or `measure_index_repair_visibility.py`. Naming
`verify_reassembly.py` on its own is deliberately *not* enough -- `--check` is
that tool's whole cheap tier and never touches history, so a step running only
that would be counted by a coarser rule than this one.

**The reported half.** Every sentence in those two tools that makes a depth
claim about a workflow, printed with its `file:line` and the derived fact the
sentence should have come from, so the next re-derivation starts from a list
rather than a grep. One rule is asserted there, and it is the only one that is
decidable without reading English meaning: **a sentence that asserts a
workflow's checkout depth names the job.** All four stale sentences fail it --
"ci.yml's checkouts", "ci.yml uses", "both of ci.yml's checkouts" and "The
agent stages and ci.yml both check out with" name no job -- and the corrected
ones pass. The rule is a floor and not a proof: a job id is a plain word
(`plan`, `fix`, `gates`), so a sentence that names one by accident passes.

**What is not found by this method, and is never reported as absent.** A
checkout behind a composite action, a checkout expressed through a `${{ }}`
rather than a literal, a workflow file that will not parse, a job that reaches
the gate from its prompt rather than from a `run:` step, and
`docs/ci/agent-gates-deep-schedule.yml` -- prepared rather than landed, and so
outside the glob. Each is reported as not found, per `CLAUDE.md`'s rule and
`ec/annotations/registers.yaml`'s own caveat. `agent-conflicts.yml`'s `resolve`
job is the case in point: it does run the gate, from the prompt at its `:248`,
and its checkout is `fetch-depth: 0` anyway -- this run does not count it, and
says so rather than deciding it.

Usage:
    python3 ec/tools/check_history_checkouts.py            # the committed tree
    python3 ec/tools/check_history_checkouts.py --repo DIR # a scratch tree
"""
import argparse
import bisect
import collections
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
# The relative form, so the same three calls read the same path whether the
# repository root is this one or the scratch tree a case points `--repo` at.
WORKFLOW_DIR = os.path.join(".github", "workflows")

# `actions/checkout`'s own default, which is what a step that states no
# `fetch-depth` gets. It is written here rather than treated as unknown because
# the whole question turns on it: a checkout with no `fetch-depth` is a
# shallow one, and a checker that answered "unspecified" for the three steps
# that omit it would answer the question this tool exists to ask by declining
# to. `0` is a full clone and every other value is a partial one.
DEFAULT_DEPTH = 1
FULL_DEPTH = 0

# A step whose `run:` contains one of these reaches git history. The first is
# the gate, whose `*verify_reassembly.py)` case is the branch that calls
# `--verify-provenance`; the second is the mode however it is spelled; the third
# is a tool every one of whose modes resolves named revisions. The gate is not
# followed into, deliberately: "does the gate script read history" is a question
# about `agent-gates.sh`, and this one is about the workflows.
HISTORY_READERS = (".github/scripts/agent-gates.sh",
                   "--verify-provenance",
                   "measure_index_repair_visibility.py")

# The two tools whose contract paragraphs make the claim, and the only files
# this reads prose from. Its own write-up quotes all three stale sentences and
# is not one of them: a correction that quoted the defect into a file this read
# would go red on its own fix.
PROSE_FILES = ("ec/tools/verify_reassembly.py",
               "ec/tools/measure_index_repair_visibility.py")

# A word that makes a sentence a claim about how deep a checkout is. It is a
# list rather than a phrase because the two tools spell the claim half a dozen
# ways between them, and the rule below only needs to know the sentence is
# *about* depth -- whether it is right is the workflows' business, not this
# regex's. `unshallow` is in it for the same reason `shallow` is: neither names a
# workflow on its own, so a sentence carrying one is not a claim about a job
# until it also says which file it means.
DEPTH_WORD = re.compile(r"fetch-depth|default-depth|full-depth|shallow|unshallow"
                        r"|full clone|full checkout")

# A sentence boundary, and the reason it is shaped this way: a terminator
# followed by whitespace and something that starts a sentence. `ci.yml` and
# `verify_reassembly.py` are full of periods that are not sentence ends, and a
# split on `.` alone would cut every one of those names in half -- which is how
# a checker that reads a claim ends up not knowing which file the claim is
# about.
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"'`*(A-Z])")

# The other boundary, because a sentence is not the only unit that runs past the
# end of its thought: the usage block at the foot of this module's own docstring
# ends mid-thought, and without these its last line would carry the closing
# `"""` and every import under it into the same "sentence" as the claim. A line
# that ends in a terminator ends its sentence whatever comes next, so that is
# one of them; a comment marker is deliberately not, for the opposite reason --
# a claim in these two files routinely wraps across three `#` lines, and cutting
# at each would report the halves and never the sentence.
CHUNK_END = re.compile(r"\n[ \t]*\n"
                       r"|(?<=[.!?])[ \t]*\n"
                       r"|\n(?=[ \t]*(?:\"\"\"|'''|def[ \t]|class[ \t]"
                       r"|import[ \t]|from[ \t]))")

# The source punctuation a sentence carries and a reader does not want: the
# quoting of a string literal, a comment's `#`, and a wrapped line's indent.
# Applied to the printed text only -- the rule below reads the sentence with
# these characters still on it, so that `names_job()` matches a backticked
# `` `gates` `` as readily as a bare one.
TRIM = "\"'`#* \t()"

Checkout = collections.namedtuple(
    "Checkout", "workflow job step depth stated")
Job = collections.namedtuple("Job", "job checkouts reader")


def effective_depth(with_block):
    """(depth, stated) for one checkout step's `with:` block.

    `None` for the depth when the value is not a literal integer -- a
    `${{ }}` expression, or a `fetch-depth` handed in from somewhere else.
    That is not a depth of 1 and not a depth of 0 either, and picking one would
    be the guess this repository's calibration rule is about; the caller reports
    it as not found by this method.
    """
    value = (with_block or {}).get("fetch-depth")
    if value is None:
        return DEFAULT_DEPTH, False
    if isinstance(value, bool) or not isinstance(value, int):
        return None, True
    return value, True


def is_checkout(uses):
    """Whether a step's `uses:` is actions/checkout, pinned or not."""
    return uses == "actions/checkout" or str(uses).startswith("actions/checkout@")


def history_reader(step):
    """The `run:` text of a step, or "" -- the only place a reader is looked for.

    Not the whole file and not `uses:`: a composite action that checked out
    would be a checkout this method cannot see, which is the caveat above rather
    than a reason to read `env:` and the job name as well.
    """
    run = step.get("run")
    return run if isinstance(run, str) else ""


def load_workflow(path):
    """(name, {job id: Job}, None) for one workflow file, or (None, None, why).

    The third element is why a file was not read, kept apart from an empty
    workflow because those are different answers: a workflow with no jobs is a
    fact about the file, and a file that will not parse is a fact about this
    tool meeting YAML it did not expect.
    """
    name = os.path.basename(path)
    try:
        with open(path, encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        return None, None, f"{name}: not read ({exc.__class__.__name__})"
    if not isinstance(doc, dict):
        return None, None, f"{name}: not a workflow mapping"
    jobs_block = doc.get("jobs")
    if jobs_block is None:
        jobs_block = {}
    elif not isinstance(jobs_block, dict):
        # A `jobs:` that is a list is a file this reader has no opinion about,
        # and reporting it as a workflow with no jobs would be a guess about
        # which half of it is true.
        return None, None, f"{name}: `jobs:` is not a mapping"

    jobs = {}
    for job_id, job in jobs_block.items():
        if not isinstance(job, dict):
            jobs[job_id] = Job(job_id, [], None)
            continue
        found, reader = [], None
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            if is_checkout(step.get("uses", "")):
                depth, stated = effective_depth(step.get("with"))
                found.append(Checkout(name, job_id,
                                      str(step.get("name", "")).strip() or "Checkout",
                                      depth, stated))
            run = history_reader(step)
            if reader is None and any(r in run for r in HISTORY_READERS):
                reader = next(r for r in HISTORY_READERS if r in run)
        jobs[job_id] = Job(job_id, found, reader)
    return name, jobs, None


def load_workflows(repo):
    """(workflows, unreadable) for every `*.yml` under the repository's own.

    `*.yml` and not `*.yaml` because that is what the directory holds, and a
    glob that quietly widened to both would report a file the pipeline does not
    read as one it does.
    """
    directory = os.path.join(repo, WORKFLOW_DIR)
    try:
        names = sorted(n for n in os.listdir(directory) if n.endswith(".yml"))
    except OSError as exc:
        return [], [f"{WORKFLOW_DIR}/: not listed ({exc.strerror})"]
    if not names:
        return [], [f"{WORKFLOW_DIR}/: no *.yml in it"]
    workflows, unreadable = {}, []
    for name in names:
        got, jobs, why = load_workflow(os.path.join(directory, name))
        if got is None:
            unreadable.append(why)
        else:
            workflows[got] = jobs
    return workflows, unreadable


def depth_problems(workflows):
    """The invariant: every job that runs a history reader is full-depth.

    -> a list of problem strings, empty when the tree holds. The reader's own
    name is in each message, so a failure says *which* step put the job on the
    list rather than only that some step did.
    """
    problems = []
    for name in sorted(workflows):
        for job in workflows[name].values():
            if job.reader is None:
                continue
            if not job.checkouts:
                # Not "shallow". A job with no checkout step is one this method
                # has not found, which is a different answer from a job whose
                # checkout is a default-depth one, and saying so here keeps the
                # two from being reported as the same finding.
                problems.append(
                    f"{name}/{job.job}: runs {job.reader!r} and has no "
                    f"`actions/checkout` step this method can see -- not found "
                    f"by this method, not measured as shallow")
                continue
            for checkout in job.checkouts:
                if checkout.depth is None:
                    problems.append(
                        f"{name}/{job.job}: runs {job.reader!r} and its "
                        f"checkout's `fetch-depth` is not a literal integer, so "
                        f"its depth is not found by this method")
                elif checkout.depth != FULL_DEPTH:
                    problems.append(
                        f"{name}/{job.job}: runs {job.reader!r} but its "
                        f"checkout is depth {checkout.depth}"
                        f"{' (stated)' if checkout.stated else ' (actions/checkout default)'}"
                        f", not `fetch-depth: {FULL_DEPTH}` -- the mode will "
                        f"report a history requirement rather than an answer")
    return problems


def line_offsets(text):
    """The character offset each line of `text` starts at, for locating prose."""
    offsets, pos = [], 0
    for line in text.splitlines(keepends=True):
        offsets.append(pos)
        pos += len(line)
    offsets.append(pos)
    return offsets


def line_of(offsets, offset):
    """The 1-based line number a character offset falls in."""
    return bisect.bisect_right(offsets, offset)


def pieces(text, pattern):
    """-> [(offset, chunk)] for `text` split on `pattern`, offsets exact.

    Not `re.split`, which returns the delimiters' text and not where they were,
    and a line number is the one thing a reader of this output has to be able to
    go and check.
    """
    found, last = [], 0
    for match in pattern.finditer(text):
        if match.start() > last:
            found.append((last, text[last:match.start()]))
        last = match.end()
    if last < len(text):
        found.append((last, text[last:]))
    return found


def sentences(text):
    """-> [(line number, sentence)] for each sentence of a source file.

    The whole file is one string, because a claim in these two tools routinely
    straddles a line break -- a docstring's usage comment runs four lines to
    finish a thought -- and a line-at-a-time reader would see two halves of a
    sentence, neither of which names a job, and report the sentence as fine
    twice over.

    **The line number is the depth word's, not the sentence's.** The sentence
    that carries `ci.yml`'s claim in the docstring's usage block begins on the
    `Usage:` line eleven lines above it, because a list of commands is not
    prose and nothing in it ends a sentence until the last comment does. A
    citation to where the sentence starts would send a reader to the wrong
    line; one to where the claim is written sends them to the claim. Where
    there is no depth word -- the rest of a file -- the sentence's own line is
    what is reported.
    """
    offsets = line_offsets(text)
    found = []
    for chunk_at, chunk in pieces(text, CHUNK_END):
        for piece_at, piece in pieces(chunk, SENTENCE_END):
            if not piece.strip():
                continue
            match = DEPTH_WORD.search(piece)
            at = chunk_at + piece_at + (match.start() if match else 0)
            found.append((line_of(offsets, at), " ".join(piece.split())))
    return found


def workflow_names(workflows, unreadable):
    """(matched, unread) -- which of these basenames a sentence can be about.

    A name this method could not read is kept in the second list so a sentence
    naming it is reported as unverifiable rather than as passing.
    """
    matched = {name: workflows[name] for name in workflows}
    unread = {why.split(":", 1)[0] for why in unreadable}
    return matched, unread


def names_job(sentence, jobs):
    """Whether a sentence names one of `jobs`, the job ids of one workflow.

    Matched on word boundaries with `-` outside them, so `agent-gates.sh` does
    not read as a job called `gates`. It is deliberately a loose test and the
    docstring says so: job ids here are ordinary English words, so the rule
    catches a sentence that names no job and not one that names the wrong one.
    """
    for job_id in jobs:
        if re.search(r"(?<![A-Za-z0-9_.-])%s(?![A-Za-z0-9_-])" % re.escape(job_id),
                     sentence):
            return job_id
    return None


def readable(sentence):
    """A sentence as a reader of the report wants it: source quoting stripped.

    The `\\n` unescaping is for the two string constants, which carry their own
    line breaks as the two characters a reader of the report would otherwise
    have to decode. The rule below reads the sentence before this is applied,
    so nothing is decided on the stripped text.
    """
    return (sentence.replace("\\n", " ")
            .replace(" # ", " ")         # a wrapped comment's own marker
            .replace('" "', " ")         # the seam between two string lines
            .strip(TRIM))


def prose_sites(repo, workflows, unreadable):
    """-> [(relpath, line, sentence, named workflows, job)] for each depth claim.

    `job` is the job id the sentence names, `None` when it names none, and
    `False` when the workflow it names could not be read -- three answers
    rather than two, because "this method has not read that file" and "this
    sentence names no job" are not the same finding and only the second one is
    a rule broken.
    """
    matched, unread = workflow_names(workflows, unreadable)
    sites = []
    for rel in PROSE_FILES:
        path = os.path.join(repo, rel)
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            continue
        for line, sentence in sentences(text):
            named = [n for n in matched
                     if re.search(r"(?<![A-Za-z0-9_.-])%s(?![A-Za-z0-9_-])" % re.escape(n),
                                  sentence)]
            named += [n for n in sorted(unread)
                      if re.search(r"(?<![A-Za-z0-9_.-])%s(?![A-Za-z0-9_-])" % re.escape(n),
                                   sentence)]
            if not named or not DEPTH_WORD.search(sentence):
                continue
            known = [n for n in named if n in matched]
            job = names_job(sentence, matched[known[0]]) if known else False
            sites.append((rel, line, sentence, named, job))
    return sites


def prose_problems(sites):
    """The one structural rule: a depth claim about a workflow names its job."""
    problems = []
    for rel, line, sentence, named, job in sites:
        if job is not None or job is False:
            continue
        problems.append(
            f"{rel}:{line}: a sentence asserting a checkout depth names "
            f"{'/'.join(named)} and no job of it -- {readable(sentence)!r}")
    return problems


def report(repo, stream=None):
    """Print the derivation, and return the two verdicts' problem lists.

    Order is the order a reader needs: the measured table first, because every
    sentence below it is supposed to have been written from it, and the prose
    sites last with the fact each should have come from beside them.

    `stream` is resolved inside rather than defaulted in the signature, so a
    caller that redirects `sys.stdout` -- the suite does, to read the report
    rather than let it print over the runner's own output -- redirects this too.
    A default bound at import time is the one a redirect cannot reach.
    """
    stream = sys.stdout if stream is None else stream

    def say(text=""):
        print(text, file=stream)

    workflows, unreadable = load_workflows(repo)
    say("check_history_checkouts.py: every actions/checkout under "
        f"{WORKFLOW_DIR}/.")
    if not workflows:
        say("  no workflow was read, so nothing below is a measurement of this "
            "tree -- that is a broken census, not an empty one")
    for name in sorted(workflows):
        for job in workflows[name].values():
            if not job.checkouts:
                continue
            for checkout in job.checkouts:
                if checkout.depth is None:
                    depth = "not found by this method"
                else:
                    depth = (f"fetch-depth: {checkout.depth}" if checkout.stated
                             else f"depth {checkout.depth} (the action's default)")
                full = "  full" if checkout.depth == FULL_DEPTH else ""
                say(f"  {name} / {checkout.job} / {checkout.step}: {depth}{full}")
    for why in unreadable:
        say(f"  {why}")

    jobs = [j for w in workflows.values() for j in w.values() if j.reader]
    say()
    if jobs:
        say(f"{len(jobs)} job(s) run a history reader: "
            + ", ".join(f"{j.job} ({j.reader})" for j in sorted(jobs, key=lambda j: j.job)))
    else:
        say("no job's `run:` names a history reader -- not found by this method, "
            "which is not the same as there being none")
    depth = depth_problems(workflows)
    say("  every job that runs a history reader has a full-depth checkout"
        if not depth else f"  {len(depth)} job(s) do not")

    sites = prose_sites(repo, workflows, unreadable)
    say()
    say(f"{len(sites)} sentence(s) in the two tools assert a checkout depth:")
    for rel, line, sentence, named, job in sites:
        say(f"  {rel}:{line}: {readable(sentence)}")
        for name in named:
            if name not in workflows:
                say(f"      {name}: jobs not found by this method, so the rule "
                    f"below is not applied to it")
                continue
            for entry in workflows[name].values():
                if not entry.checkouts:
                    continue
                for checkout in entry.checkouts:
                    depth_text = ("not found by this method" if checkout.depth is None
                                  else f"fetch-depth: {checkout.depth}"
                                  if checkout.stated else
                                  f"depth {checkout.depth} (the action's default)")
                    runs = (f", runs {entry.reader}" if entry.reader
                            else ", runs no history reader")
                    say(f"      {name}/{checkout.job}: {depth_text}{runs}")
    prose = prose_problems(sites)
    say("  every one of them names the job it is about"
        if not prose else f"  {len(prose)} of them name no job")
    return depth, prose


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # `--repo` rather than nothing, so a case can point the whole report at a
    # scratch tree and read the same output a human reads. The scratch tree is
    # where the failing invariant is demonstrated: nothing in this repository
    # makes the check red, by design.
    ap.add_argument("--repo", default=REPO,
                    help="repository root to read (default: this one)")
    args = ap.parse_args()

    depth, prose = report(args.repo)
    problems = depth + prose
    if problems:
        print(file=sys.stderr)
        for problem in problems:
            print(f"  FAIL {problem}", file=sys.stderr)
        print(f"check_history_checkouts.py: {len(problems)} problem(s). The "
              f"history requirement itself is unchanged by any of this; what is "
              f"at issue is the sentence describing which job needs it.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
