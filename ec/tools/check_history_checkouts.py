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
from prose: a step whose `run:` or `prompt:` names `.github/scripts/agent-gates.sh`,
`--verify-provenance`, or `measure_index_repair_visibility.py`. Naming
`verify_reassembly.py` on its own is deliberately *not* enough -- `--check` is
that tool's whole cheap tier and never touches history, so a step running only
that would be counted by a coarser rule than this one.

**A `prompt:` is read as well, and only in command position.** A `run:` is
executed by the runner, so a marker anywhere in one is a run. A `prompt:` is
read by a model, so a marker in one is a run only where the *marker* is in
command position: the first non-whitespace text on its line, which is how an
indented block spells a shell line. That is what puts `agent-conflicts.yml`'s
`resolve` on the list, which reaches the gate from the prompt at its `:248` and
was therefore the one job of the four the corrected prose names that this tool
did not count -- a re-copy of that workflow dropping `fetch-depth: 0` from the
job would have broken no job and left this checker green. The test is on the
marker and not on the line, and the same rule leaves `agent-review.yml`'s
`review` off the list: its marker at `:169` is the fourth word of a bullet
beginning `- a gate weakened rather than satisfied --`. That is the rule being
right rather than lenient. `review` runs no gate, needs no clone, and putting a
job that runs none inside a full-depth invariant would be the rule being wrong.
A marker in a prompt in any other shape is **printed** beside the list with its
line, not counted and not dropped.

**The reported half.** Every sentence in the tree that makes a depth claim
about a workflow, printed with its `file:line` and the derived fact the
sentence should have come from, so the next re-derivation starts from a list
rather than a grep. One rule is asserted there, and it is the only one that is
decidable without reading English meaning: **a sentence that asserts a
workflow's checkout depth names the job of every workflow it names.** All four
stale sentences fail it -- "ci.yml's checkouts", "ci.yml uses", "both of
ci.yml's checkouts" and "The agent stages and ci.yml both check out with" name
no job -- and the corrected ones pass. The rule is per *workflow* rather than
per sentence, and one problem is reported per workflow for which the sentence
names no job, naming that workflow: a job of one of them silences the other
otherwise. **The first version of this paragraph stated the rule over the first
readable workflow a sentence named and no other** -- `known[0]`, the
alphabetically-first of them -- so a sentence that named a job of `ci.yml` and
nothing at all about `claude.yml` passed on the first. That was the rule this
one corrects, and it is the same defect the four stale sentences are: the report
printed both names all along and judged one.

**The population is derived, and used to be typed.** It was two paths in
`PROSE_FILES`, and #1031's own history is the argument against a typed one: #1009
corrected seven sentences, three of them in markdown, and the checker read none
of them; a second round found two more, and a third -- this one -- found a
fourth copy in a fifth file. A list of files is a list of the sites somebody
already found, so the next one is not in it. `PROSE_FILES` is gone: the reported
half walks the tree, reads every text file, and judges the sentences it finds.
`SCAN_EXTENSIONS` is what "text" means here, and `DECLINE_RULES` is what the walk
refuses and why. **The declined list is a *scope* list, and is kept in a
different vocabulary from "not found by this method"**, which stays reserved for
a claim inside a file that *was* read: `vendor/` was not scanned because it
holds committed binaries, and that is not a finding about a sentence. Nothing
here is ever reported as absent.

**A correction is a quotation, and no boundary rule can tell the two apart.** A
retraction *guarantees* to carry the sentence it retracts, verbatim, beside the
one that replaced it -- so reading the whole tree finds every correct site
red for the defect it corrects, which would make the check useless rather than
strict. `MARKED` finds the spans a reader would read as someone else's words:
a fenced block, a code span, a double-quoted string, strikethrough. A claim
whose depth word *and* one of the workflow names it carries both fall inside
one of them is **reported as quoted and not judged**, with its `file:line`
beside it, so it is visible rather than exempted. Both halves of that test are
load-bearing and `MARKED`'s own comment says why: the conjunction, because a
markdown sentence writes one term in backticks as a matter of course and
reading that as a quotation exempts every claim in every markdown file; and
the word rather than the sentence, because a correction paragraph carries the
retracted claim in one voice and its replacement in another. This is structural
on purpose: a hand-kept list of quoted spans would be the same defect one level
up, and would go stale silently.

**What is declined, and why.** Four rules, each reported with its paths:
`repository-internal` (`.git/`, `__pycache__/`) is not this repository's text;
`vendored-input` (`vendor/`) is committed binaries per `CLAUDE.md`; and
`generated-output` is a Ghidra project or an exported decompile tree, which is
machine output and where a "shallow" is a string somebody typed. The fourth,
`instrument-or-record`, is this check's own machinery -- the tool and every
suite written against it, whose whole job is to hold the retracted sentences
verbatim as controls -- and the #1009 write-up whose seven-site table quotes all
of them. Those are paths, not spans, and the reason is on this page rather than
in a list that could go quiet: a control that is judged is not a control.

**The second reading of that rule is the same judgement, and is not implemented
separately.** It reads as "a sentence must name a job of each workflow it makes
a depth claim about", and the two agree here because **this method cannot tell
a claim from a mention**: any workflow named in a sentence carrying a depth word
counts as one the sentence claims about. That coarseness is pre-existing -- the
first readable workflow alone was reached by a depth word anywhere in the
sentence paired with a name anywhere in it -- and it is now applied once per
workflow rather than once per sentence. So "`ci.yml`'s `gates` job is full-depth,
as `agent-fix.yml`'s is too" reports `agent-fix.yml`, which is a true positive
under the rule as stated: the sentence does assert a depth about that workflow
and names no job of it. Telling that sentence apart from one that mentions
`agent-fix.yml` in passing needs the depth word attached to a particular name at
clause level, and the whole design of this half is that one rule is asserted --
the one decidable without reading English meaning.

The rule is a floor and not a proof: a job id is a plain word (`plan`, `fix`,
`gates`), so a sentence that names one by accident passes, and **a job id two
workflows share satisfies the rule for both** -- `gates` in `ci.yml` and
`gates` in some other file is one word naming two jobs, and no defect is
reported. That is the same plain-word caveat and not a second one: the rule
cannot tell which of the two the sentence meant, so it declines to say that
either lacks one. **A job id is not read out of the workflow name beside it**,
which is the one accidental match that had to be closed rather than accepted:
`claude.yml`'s job is `claude`, so a matcher that read the raw sentence found
that job inside the filename the sentence was required to carry, and the
sentence the rule exists to report passed on its own name. The names are
blanked out before the job ids are looked for -- see `job_text()`.

A readable workflow with **no jobs at all** is a flag and not an excuse. The file
parsed, so "there is no job here to name" is a fact about the workflow rather
than a limit on what this method can see, which is the distinction
`load_workflow()`'s docstring above already draws between a workflow with no
jobs and a file this tool could not read. An unreadable one is never judged.

**What is not found by this method, and is never reported as absent.** A
checkout behind a composite action, a checkout expressed through a `${{ }}`
rather than a literal, a `prompt:` that is not a string, a workflow file that
will not parse, and `docs/ci/agent-gates-deep-schedule.yml` -- prepared rather
than landed, and so outside the glob. Each is reported as not found, per
`CLAUDE.md`'s rule and `ec/annotations/registers.yaml`'s own caveat. A `prompt:`
is no longer one of them: it is read, and the shape of the read is the command-
position rule above rather than a decision about English. Three things a
`prompt:` could carry are still not read, and each is a miss rather than a
verdict: a marker in an `env:`, an `if:`, a job name or a YAML comment, where
`ci.yml:11`'s hand-written comment about the gate is the committed case and
reading comments as prompts would put prose about the gate on a list of jobs
that run it; a marker behind another word on its line, so a prompt spelling the
command `bash .github/scripts/agent-gates.sh` is not counted, because where a
shell command ends inside a line of prose is not decidable mechanically and a
list of command prefixes would reintroduce the template-coupling the table
above exists to shed; and the line a marker in a *folded* prompt block is
reported on, which is the block's first rather than the marker's own, because
folding has already joined the lines by the time the text is a value.

**The census reads both spellings, and the reason it used to read one is a
correction rather than a rule.** `load_workflows()` matched `*.yml` on the
stated ground that *"a glob that quietly widened to both would report a file
the pipeline does not read as one it does"* -- which is not what Actions does,
which reads `.yml` and `.yaml` interchangeably, so there was no such file to
report. The argument was about the cost of an over-report and priced that cost
at silence, which it was while an unread workflow only went missing from the
table. It is not any more, now that `main()` refuses a census of zero
workflows: a tree whose workflows are spelled `.yaml` is told its census is
broken and exits 1, and that diagnosis points at the tree's files when the
fault is this glob. `SCAN_EXTENSIONS` below already read `.yaml`, so the prose
half was holding a `.yaml` file's sentences to a standard its own measured
half would not have applied to the workflow beside them. **The bound is the two
suffixes**: a `.txt` or a `.json` sitting in `.github/workflows/` is not a
workflow file, and a later reader widening this to everything YAML-ish is not
fixing the defect this paragraph records.

Usage:
    python3 ec/tools/check_history_checkouts.py            # the committed tree
    python3 ec/tools/check_history_checkouts.py --repo DIR # a scratch tree
"""
import argparse
import bisect
import collections
import fnmatch
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
# The relative form, so the same three calls read the same path whether the
# repository root is this one or the scratch tree a case points `--repo` at.
WORKFLOW_DIR = os.path.join(".github", "workflows")

# The two spellings a workflow file may carry, and `load_workflows()` reads
# both. A named pair rather than a second literal at the glob, because the
# empty-directory reason it prints has to name the same two and a reader
# comparing that line against the code above it should not be looking for a
# third place. `.yaml` is here because Actions reads it, not because the
# committed tree happens to hold one; nothing else is, and the bound is a test.
WORKFLOW_SUFFIXES = (".yml", ".yaml")

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

# A `run:` is executed by the runner, so a marker anywhere in one is a run and
# is matched as a plain substring. A `prompt:` is read by a model, so a marker
# in one is a run only where the marker itself is in command position: the
# first non-whitespace text on its line, which is how an indented block spells a
# shell line. The test is on the *marker* and not on the line, and that is the
# whole difference between the two committed cases. `agent-conflicts.yml`'s
# `resolve` carries the gate alone on an indented line and reaches it, and
# `agent-review.yml`'s `review` carries it inside a bullet whose line begins
# `- a gate weakened rather than satisfied --`, so its first non-whitespace text
# is a hyphen and the marker is the fourth word of the line. A rule that asked
# only whether the line had any text on it would count `review`, and `review`
# needs no clone: a prompt is not an execution.
#
# Built per marker from the tuple above, so the two lists cannot disagree about
# which strings are the readers.
COMMAND_POSITION = {marker: re.compile(r"^[ \t]*" + re.escape(marker))
                    for marker in HISTORY_READERS}

# The two block-scalar styles, and the only reason `first_line()` below has a
# term at all: a block scalar's node starts on the `|` that introduces it, so
# its text begins on the line below, while a plain or quoted scalar's node
# starts on its own text. PyYAML reports `|-` and `|+` as `|` and `>-` as `>`.
BLOCK_STYLES = ("|", ">")

# What the walk reads. The three that matter are `.md` (where every one of the
# seven corrected sites outside the two tools lives), `.py` (a tool's own
# contract paragraph) and `.yml`/`.sh` (a workflow's comment, and the gate
# script's). The rest are here so that a checkout claim written into a patch or
# a plain-text note is found rather than missed -- the whole point of deriving
# the population -- and none of them is a claim that the rest of the tree holds
# no prose: a file this does not read is a file the population does not hold,
# which is a scope fact and not a finding about a sentence.
SCAN_EXTENSIONS = (".md", ".py", ".sh", ".yml", ".yaml", ".patch", ".diff",
                   ".txt", ".json")

# The four rules the walk refuses by, each `(rule, matched, why)`. A rule that
# is not in this tuple is not applied, so a refusal always names itself: a
# report that said only "not read" would be a list nobody could argue with, and
# an argument nobody can have is a list that rots.
#
# `instrument-or-record` is the only one holding paths rather than directory
# names, and the reason is the docstring's: a control is judged by what it is
# for. This file and the suites written against it exist to hold the retracted
# sentences verbatim, and the #1009 write-up holds all four in a table whose
# subject *is* the retraction. They are excluded as paths and not by naming the
# spans, because a span list would have to be maintained against prose that is
# itself still being corrected.
DECLINE_RULES = (
    ("repository-internal", (".git", "__pycache__"),
     "version-control and byte-cache directories, which are not this "
     "repository's text"),
    ("vendored-input", ("vendor",),
     "`vendor/` holds committed binaries as inputs, not prose anyone cites"),
    ("generated-output", ("decompiled",),
     "a Ghidra project or an exported decompile tree is machine output, where "
     "a depth word is a string somebody typed rather than a claim"),
    ("instrument-or-record", (),
     "this check's own machinery and the write-up that quotes the retracted "
     "sentences; a control judged is not a control"),
)

# The paths the `instrument-or-record` rule matches, as `fnmatch` patterns over
# the repository-relative path. A glob rather than a list so that the next suite
# written against this tool is covered by the rule without an edit here, which
# is the same failure one level up that #1031 is about.
INSTRUMENT_PATTERNS = ("ec/tools/check_history_checkouts.py",
                       "ec/tools/test_check_history_checkouts*.py")
RECORD_PATTERNS = ("docs/findings/history-checkout-claims.md",)

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

# The spans a reader would take for someone else's words: a fenced code block,
# inline code, a double-quoted string, strikethrough. **Emphasis is
# deliberately not in it**, and that is a correction rather than an omission:
# bold and italic in this repository are how an author emphasises a sentence in
# their own voice, so reading them as quotation would both mislabel them in the
# report and excuse the very claims the rule exists for -- §86's
# "`ci.yml`'s `gates` job has been `fetch-depth: 0` since 2026-09-24" is bold,
# and an italic stray reached two paragraphs to excuse a fifth. Every
# retraction this corpus holds is quoted in a `"`, a fenced block or a code span,
# which is where a retraction belongs; the emphasis forms are how the correction
# next to it is written.
#
# The wrapping spans take a newline but never a blank line, so one cannot reach
# out of the paragraph it was written in -- the bound that matters, since
# `SENTENCE_END` will happily carry a "sentence" across a line and a reader
# would not. The double-quoted form is length-bounded for the same reason from
# the other side: an odd number of `"` on a page would otherwise pair with the
# next one and swallow the rest of the file.
MARKED = re.compile(
    r"```.*?```"                            # a fenced block, the shape a
                                            # pasted sentence takes
    r"|~~(?:[^\n]|\n(?!\n))*?~~"            # strikethrough
    r"|``[^`]*?``"                          # a code span holding backticks
    r"|`[^`\n]*?`"                          # inline code
    r'|"(?:[^"\n]|\n(?!\n)){0,600}?"',       # a double-quoted string
    re.DOTALL)

Checkout = collections.namedtuple(
    "Checkout", "workflow job step depth stated")
# `reader` is the bare marker, because `depth_problems()`'s messages are about
# the marker and their wording is held by the suite. `route` is which of the
# two places it was reached through, so the reader list beside the table can
# say *how* a job is on it rather than only that it is. `named` is every
# `(line, marker)` a job's prompt names in a shape this method does not count,
# which is a finding about the prompt rather than about the job.
Job = collections.namedtuple("Job", "job checkouts reader route named")


class _Line(str):
    """A `str` that remembers the line of the workflow it was read from.

    The prompt side has to say *where* in a workflow a marker sits, because
    "the job names the gate in guidance" is not something a reader can go and
    check without a line number. A parsed scalar has no position left in it,
    and this carries one for the price of a constructor.
    """

    def __new__(cls, value, line, style):
        made = super().__new__(cls, value)
        made.line, made.style = line, style
        return made


class _WorkflowLoader(yaml.SafeLoader):
    """`safe_load`'s loader, with the one constructor the line numbers need.

    A subclass rather than a call into `yaml.compose()`: the parse this tool
    already does is the parse it keeps doing, and a second walk of the same
    tree over the same file to recover positions would be a second thing to
    keep right. `SafeLoader` is not modified, so every other consumer of it
    reads the same document.
    """


def _construct_str(loader, node):
    return _Line(loader.construct_yaml_str(node), node.start_mark.line,
                 node.style)


_WorkflowLoader.add_constructor("tag:yaml.org,2002:str", _construct_str)


def first_line(text):
    """The 1-based workflow line `text`'s own first line is on, or None.

    A plain or quoted scalar's node starts on its text; a block scalar's node
    starts on the `|` or `>` introducing it and its text starts on the line
    below, which is the one adjustment `BLOCK_STYLES` exists for. `None` when
    the value is not one of the strings this loader decorated -- a `prompt:`
    that is a list or a number rather than prose -- so a caller reads it as
    not found by this method instead of a position of 0.
    """
    if not isinstance(text, _Line):
        return None
    return text.line + 1 + (text.style in BLOCK_STYLES)


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


def run_reader(step):
    """The `run:` text of a step, or "" -- a marker in it is a run outright.

    Not the whole file and not `uses:`: a composite action that checked out
    would be a checkout this method cannot see, which is the caveat above rather
    than a reason to read `env:` and the job name as well.
    """
    run = step.get("run")
    return run if isinstance(run, str) else ""


def prompt_text(step):
    """A step's `with: prompt:`, or "" -- and never a guess at a non-string one.

    A `prompt:` that is a list or a number rather than prose is not a prompt
    this method can read, and "" says so the same way a non-string `run:`
    does: the step is looked at and contributes nothing, rather than raising or
    being stringified into a line that reads like an instruction.
    """
    prompt = (step.get("with") or {}).get("prompt")
    return prompt if isinstance(prompt, str) else ""


def prompt_mentions(step):
    """-> [(line, marker, in command position)] for a step's prompt.

    The line is the workflow line the marker is written on, which is the whole
    reason the loader above keeps one: a report that says "named in guidance"
    without saying where is a claim a reader has to take on trust.

    Only a literal block resolves a marker to its own line exactly. A folded
    one (`>`) has had its lines joined with spaces by the time it is a value, so
    a marker in it is reported on the block's first line -- where the text
    begins -- rather than on a line it may not be on, which is a limitation of
    reading the value and not a position this method is claiming.
    """
    prompt = prompt_text(step)
    at = first_line(prompt)
    if not prompt or at is None:
        return []
    found = []
    for offset, line in enumerate(prompt.splitlines()):
        for marker in HISTORY_READERS:
            if marker in line:
                found.append((at + offset, marker,
                              COMMAND_POSITION[marker].match(line) is not None))
    return found


def job_routes(steps):
    """-> (reader, route, named) for one job's steps.

    `route` is `"a run: step"` or `"its prompt"`, and a `run:` outranks a
    prompt rather than going by whichever came first in the file. The reason
    is the same asymmetry `COMMAND_POSITION` rests on: a `run:` is executed and
    a prompt is read, so the step is the route a checkout depth can be held
    against. `agent-fix.yml`'s `fix` names the gate in both -- at its `:220`
    and its `:316` -- and belongs on the list for the one that does not depend
    on a model reading the sentence.

    `named` is every prompt mention that is not in command position, whether or
    not the job is a reader by some other route. It is a fact about that line
    of the prompt, and folding it into the job's own standing would report a
    job as reaching a gate it only describes. A line is listed once: a retry
    step that reuses its first attempt's `with:` through a YAML alias carries
    the same prompt, and the alias resolves to the anchor's lines.
    """
    stepped, prompted, named = [], [], []
    for step in steps:
        if not isinstance(step, dict):
            continue
        run = run_reader(step)
        for marker in HISTORY_READERS:
            if marker in run:
                stepped.append(marker)
        for line, marker, command in prompt_mentions(step):
            if command:
                prompted.append(marker)
            elif (line, marker) not in named:
                named.append((line, marker))
    if stepped:
        return stepped[0], "a run: step", named
    if prompted:
        return prompted[0], "its prompt", named
    return None, None, named


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
            doc = yaml.load(handle, Loader=_WorkflowLoader)
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
            jobs[job_id] = Job(job_id, [], None, None, [])
            continue
        found = []
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            if is_checkout(step.get("uses", "")):
                depth, stated = effective_depth(step.get("with"))
                found.append(Checkout(name, job_id,
                                      str(step.get("name", "")).strip() or "Checkout",
                                      depth, stated))
        reader, route, named = job_routes(job.get("steps") or [])
        jobs[job_id] = Job(job_id, found, reader, route, named)
    return name, jobs, None


def load_workflows(repo):
    """(workflows, unreadable) for every workflow under the repository's own.

    Both suffixes in `WORKFLOW_SUFFIXES`, because Actions reads both. **It read
    `*.yml` alone, and the reason it recorded for that is the correction rather
    than the rule:** *"a glob that quietly widened to both would report a file
    the pipeline does not read as one it does"* is not what Actions does with
    the two spellings, and while the consequence of the narrow glob was silence
    the argument held the cost at nothing. It stopped holding when `main()`
    began refusing a census of zero workflows, because a tree whose workflows
    are spelled `.yaml` is a tree this tool reads perfectly well and was told
    its census was broken. That is also what the empty-directory reason below
    has to stay true of: `ci.yaml` is a file the pipeline runs, so a directory
    holding one does not hold "no `*.yml`".
    """
    directory = os.path.join(repo, WORKFLOW_DIR)
    try:
        names = sorted(n for n in os.listdir(directory)
                       if n.endswith(WORKFLOW_SUFFIXES))
    except OSError as exc:
        # `{}` and not `[]`, and the same on the return below: the first element
        # is read as a mapping by every caller, so a list here crashed the run
        # on a tree it was asked to refuse.
        return {}, [f"{WORKFLOW_DIR}/: not listed ({exc.strerror})"]
    if not names:
        return {}, [f"{WORKFLOW_DIR}/: no "
                    f"{' or '.join('*' + s for s in WORKFLOW_SUFFIXES)} in it"]
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
    """-> [(line number, sentence, offset)] for each sentence of a source file.

    The whole file is one string, because a claim in these two tools routinely
    straddles a line break -- a docstring's usage comment runs four lines to
    finish a thought -- and a line-at-a-time reader would see two halves of a
    sentence, neither of which names a job, and report the sentence as fine
    twice over. A markdown sentence wraps the same way.

    **The line number is the depth word's, not the sentence's**, and the offset
    with it is that same position in the file's own string: `MARKED` matches
    against `text`, so the character the quotation test needs is the character
    the reported line is computed from. Deriving a second position for it would
    be a second thing to keep in step with the first.

    The sentence that carries `ci.yml`'s claim in the docstring's usage block
    begins on the `Usage:` line eleven lines above it, because a list of
    commands is not prose and nothing in it ends a sentence until the last
    comment does. A citation to where the sentence starts would send a reader to
    the wrong line; one to where the claim is written sends them to the claim.
    Where there is no depth word -- the rest of a file -- the sentence's own
    line is what is reported.
    """
    offsets = line_offsets(text)
    found = []
    for chunk_at, chunk in pieces(text, CHUNK_END):
        for piece_at, piece in pieces(chunk, SENTENCE_END):
            if not piece.strip():
                continue
            match = DEPTH_WORD.search(piece)
            at = chunk_at + piece_at + (match.start() if match else 0)
            found.append((line_of(offsets, at), " ".join(piece.split()), at))
    return found


def quoted_at(text, offset, named):
    """Whether the claim at `offset` is one `MARKED` reads as someone else's.

    **The span has to cover the whole claim**, the depth word *and* one of the
    workflow names the sentence carries -- and that conjunction is the whole
    design, because in this repository a markdown sentence writes a term in
    backticks as a matter of course. "the agent stages check out with
    `fetch-depth: 0`" has its depth word in a code span and its workflow names
    in three others, and reading any one code span as a quotation would exempt
    every claim in a markdown file and leave the rule asserting nothing. The
    retracted sentences that have to be exempt are exempt whole: the quoted
    string, the quoted bullet, the fenced block with the sentence pasted into it.

    `offset` is the *depth word's*, not the sentence's, and that is the second
    half. A correction paragraph carries the retracted sentence in quotation
    marks and then states what replaced it in its own voice; only the second
    half is a claim this rule has anything to say about. Testing the sentence
    would have to test its span, which for a wrapped sentence reaches past the
    quotation on both sides, and a sentence that both quotes a retracted claim
    and corrects it is the common case here rather than the rare one.

    A code span of a whole term is therefore *not* a quotation and an italic
    span around a half-sentence is. Nothing decides that by reading English: it
    is decided by where the workflow name sits, and that is stated here because
    it is a floor and not a proof -- a claim quoted in a span that happens to
    name no workflow is judged, and a claim naming a workflow in the author's
    own voice is not excused by another code span in the same paragraph.
    """
    for match in MARKED.finditer(text):
        if match.start() > offset:
            break
        if not match.start() <= offset < match.end():
            continue
        span = match.group()
        if any(re.search(r"(?<![A-Za-z0-9_.-])%s(?![A-Za-z0-9_-])" % re.escape(n),
                         span)
               for n in named):
            return True
    return False


def walk_prose_files(repo):
    """-> (relative paths to read, [(rule, relative path) declined by it]).

    `os.walk`, not `git ls-files`, for one reason: `--repo DIR` is pointed at a
    scratch tree that is not a checkout, and the cases that exercise the walk
    are the ones that build one. A reader of the walk's own output cannot tell
    the two apart, and a population that was a checkout on one day and a
    directory listing on the next would be a different set of sentences each.

    The two halves are returned apart, and that separation is the calibration
    rule: a declined path is a *scope* fact -- this walk did not read it, and
    why -- and is never a finding about a sentence, which is what "not found
    by this method" means everywhere else in this file.
    """
    skip = {}
    for rule, names, _why in DECLINE_RULES:
        for name in names:
            skip[name] = rule
    read, declined = [], []
    for dirpath, dirnames, filenames in os.walk(repo):
        rel_dir = os.path.relpath(dirpath, repo)
        held = []
        for name in sorted(dirnames):
            rule = skip.get(name)
            if rule is None:
                held.append(name)
                continue
            # Sorted, so a declined directory is listed in the order the walk
            # met it and the report is the same text on every run.
            declined.append((rule, os.path.normpath(
                os.path.join(rel_dir, name)).replace(os.sep, "/")))
        dirnames[:] = held
        for name in sorted(filenames):
            rel = os.path.normpath(os.path.join(rel_dir, name)).replace(os.sep, "/")
            rule = _file_rule(rel)
            if rule is not None:
                declined.append((rule, rel))
                continue
            if os.path.splitext(name)[1] in SCAN_EXTENSIONS:
                read.append(rel)
    return read, sorted(declined)


def _file_rule(rel):
    """The `instrument-or-record` rule for one path, or `None` for no rule.

    Named after the rules that are directory names, so `walk_prose_files()` has
    one place to ask and this file has one place to answer. A `None` is not an
    answer about the file -- it is the absence of one, and the caller falls
    through to the extension test, which is a different question again.
    """
    for pattern in INSTRUMENT_PATTERNS + RECORD_PATTERNS:
        if fnmatch.fnmatchcase(rel, pattern):
            return "instrument-or-record"
    return None


def workflow_names(workflows, unreadable):
    """(matched, unread) -- which of these basenames a sentence can be about.

    A name this method could not read is kept in the second list so a sentence
    naming it is reported as unverifiable rather than as passing.
    """
    matched = {name: workflows[name] for name in workflows}
    unread = {why.split(":", 1)[0] for why in unreadable}
    return matched, unread


def job_text(sentence, named):
    """`sentence` with the span of every workflow name it carries blanked out.

    This is the text a job id has to be found in, and the blanking is what
    keeps a job id that is its own workflow's filename stem from standing in
    for a mention of the job: `claude.yml` is a name the sentence has to
    carry anyway, so a matcher that read it would let the filename satisfy the
    rule for the `claude` job. That is not hypothetical -- the committed tree's
    `claude.yml` holds exactly that job -- and before this the sentence
    "`ci.yml`'s `gates` job is full-depth and claude.yml is shallow throughout"
    passed, which is the sentence the rule exists to report.

    **Blanking rather than tightening `names_job()`'s trailing boundary**, which
    would also stop the match, is the deliberate half of the choice: a job id
    at the end of a sentence is followed by a period, so excluding `.` would
    trade this false negative for a worse one, in a reword nobody would read as
    a change. Blanked spans are replaced by spaces, so the text either side
    keeps the boundaries it had.
    """
    for name in named:
        sentence = re.sub(
            r"(?<![A-Za-z0-9_.-])%s(?![A-Za-z0-9_-])" % re.escape(name),
            lambda blanked: " " * len(blanked.group()), sentence)
    return sentence


def names_job(sentence, jobs):
    """Whether a sentence names one of `jobs`, the job ids of one workflow.

    Matched on word boundaries with `-` outside them, so `agent-gates.sh` does
    not read as a job called `gates`. It is deliberately a loose test and the
    docstring says so: job ids here are ordinary English words, so the rule
    catches a sentence that names no job and not one that names the wrong one.

    `sentence` is the text `job_text()` blanks the workflow names out of, and
    that is what it has to be: read on the raw sentence, a job id spelled the
    same way as its own workflow's stem is found inside the filename.
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


def prose_sites(repo, workflows, unreadable, files=None, declined=None):
    """-> [(relpath, line, sentence, named workflows, jobs, quoted)].

    The last element is `{workflow: job id or None}` over the *readable* named
    workflows, so the rule below is judged once per workflow rather than once
    per sentence. **It was a scalar**, the job of the first readable workflow a
    sentence named, `None` when it named none, and `False` when the workflow it
    named could not be read -- three answers rather than two, because "this
    method has not read that file" and "this sentence names no job" are not the
    same finding and only the second one is a rule broken. The three collapse
    into the mapping without losing one, and a reader of the old code looking
    for the `False` will find it here as the empty mapping: a sentence whose
    every named workflow was unreadable has nothing to judge. Those names stay
    in the fourth element, where `report()` prints them as not found by this
    method.

    `files` and `declined` are the walk's two halves, taken as arguments rather
    than re-derived so that `report()` and a case reading the sites judge the
    same population. A file named here that will not read is skipped in silence,
    which is the one thing this half does not report: a file that is not UTF-8
    is a file with no prose in it for this method to have missed.
    """
    matched, unread = workflow_names(workflows, unreadable)
    if files is None:
        files, declined = walk_prose_files(repo)
    sites = []
    for rel in files:
        path = os.path.join(repo, rel)
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError):
            continue
        for line, sentence, at in sentences(text):
            named = [n for n in matched
                     if re.search(r"(?<![A-Za-z0-9_.-])%s(?![A-Za-z0-9_-])" % re.escape(n),
                                  sentence)]
            named += [n for n in sorted(unread)
                      if re.search(r"(?<![A-Za-z0-9_.-])%s(?![A-Za-z0-9_-])" % re.escape(n),
                                   sentence)]
            if not named or not DEPTH_WORD.search(sentence):
                continue
            # `named` is already in `matched`'s sorted order, so the mapping is
            # built in the order the report prints the names under, and the
            # problems below come out in that order too. The names are blanked
            # out of the text the job ids are looked for in, so that a job id
            # spelled like its own workflow's stem is not read off the filename.
            free = job_text(sentence, named)
            jobs = {name: names_job(free, matched[name])
                    for name in named if name in matched}
            sites.append((rel, line, sentence, named, jobs,
                          quoted_at(text, at, named)))
    return sites


def prose_problems(sites):
    """The one structural rule: a depth claim names the job of every workflow.

    One problem per *workflow*, naming it, rather than one per sentence: "the
    `gates` job is full-depth and claude.yml is shallow throughout" is broken
    once, by the half that names no job, and a report that only said "this
    sentence" would leave the reader to work out which half. A workflow that
    could not be read is not in the mapping and so is not judged here at all --
    `report()` prints it as not found by this method, which is a different
    finding from a rule broken.

    A **quoted** site is in neither list, and that is the one judgement this
    function makes that is not about the workflows at all. It is reported, by
    `report()`, with its `file:line` -- silently dropping it would be the same
    as dropping a file, and the reader of a report has no way to tell a
    quotation from a site nobody looked at.
    """
    problems = []
    for rel, line, sentence, _named, jobs, quoted in sites:
        if quoted:
            continue
        for name, job in jobs.items():
            if job is not None:
                continue
            problems.append(
                f"{rel}:{line}: a sentence asserting a checkout depth names "
                f"{name} and no job of it -- {readable(sentence)!r}")
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
    files, declined = walk_prose_files(repo)
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
            + ", ".join(f"{j.job} ({j.reader}, from {j.route})"
                        for j in sorted(jobs, key=lambda j: j.job)))
    else:
        say("no job's `run:` or `prompt:` names a history reader -- not found by "
            "this method, which is not the same as there being none")
    depth = depth_problems(workflows)
    say("  every job that runs a history reader has a full-depth checkout"
        if not depth else f"  {len(depth)} job(s) do not")

    # A marker in a prompt that is not in command position is the one shape
    # this method reads and declines, so it is printed rather than left in the
    # docstring: a rule whose misses are only written down where the rule is
    # defined is a rule whose misses nobody reads at the point they would have
    # caught one. `agent-review.yml`'s `review` is the committed case, and it is
    # correct to be absent from the list above -- a prompt is not an execution
    # and `review` needs no clone -- which is the reason this is a line of the
    # report and not a fifth job on it.
    not_counted = [(name, job) for name in sorted(workflows)
                   for job in workflows[name].values() if job.named]
    if not_counted:
        say()
        say("named in a `prompt:` but not read as a run, because the marker is "
            "not in command position:")
        for name, job in not_counted:
            for line, marker in job.named:
                say(f"  {name}:{line} {job.job}: {marker} -- in a sentence, not a "
                    f"command, so this method does not count it a reader")

    say()
    say("not found by this method, which is not the same as absent: a checkout "
        "behind a composite action; a `fetch-depth` that is a `${{ }}` rather "
        "than a literal; a `prompt:` that is not a string; a workflow file that "
        "will not parse; a marker in a prompt behind another word on its line, "
        "so `bash .github/scripts/agent-gates.sh` is not counted; a marker in an "
        "`env:`, an `if:` or a YAML comment, where `ci.yml:11` is the committed "
        "case; and `docs/ci/agent-gates-deep-schedule.yml`, which is prepared "
        "rather than landed and so outside the glob read above")

    sites = prose_sites(repo, workflows, unreadable, files, declined)
    carriers = len({rel for rel, *_rest in sites})
    quoted = [s for s in sites if s[5]]
    say()
    say(f"The prose population is derived, not listed: {len(files)} text file(s) "
        f"under this tree, of which {carriers} carry a depth claim naming a "
        f"workflow, in {len(sites)} sentence(s).")
    for rule, _names, why in DECLINE_RULES:
        paths = [rel for held, rel in declined if held == rule]
        if not paths:
            continue
        say(f"  declined by `{rule}` ({len(paths)}), because {why}:")
        for rel in paths:
            say(f"      {rel}")
    say(f"  a declined file is out of scope for this walk and is not a finding "
        f"about any sentence in it; a claim inside a file that *was* read and "
        f"is not found by this method is a different finding")
    say()
    say(f"{len(sites)} sentence(s) in the tree assert a checkout depth:")
    for rel, line, sentence, named, job, is_quoted in sites:
        if is_quoted:
            say(f"  {rel}:{line}: [quoted -- not judged] {readable(sentence)}")
            continue
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
    if quoted:
        say(f"  {len(quoted)} of the {len(sites)} sit inside a quoted span and "
            f"are reported rather than judged -- a correction quotes the "
            f"sentence it retracts, and no boundary rule tells that from a claim")
    # Claim(s), not sentence(s): one sentence naming two workflows and no job
    # of one of them is two problems, so the old count here read a half of
    # what the rule below has found.
    judged = [s for s in sites if not s[5]]
    say("  every one of them names the job of every workflow it names"
        if not prose else
        f"  {len(prose)} of the claims name no job, in {len(judged)} judged "
        f"sentence(s)")
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
    # The census is re-read here rather than handed back by `report()`, whose
    # return is the two verdicts and is unpacked by cases in the report-reading
    # suite. Eleven small YAML files parsed twice is nothing next to a run that
    # read no workflow at all and exited 0 having found nothing wrong.
    workflows, _unreadable = load_workflows(args.repo)
    if not workflows:
        # Keyed on zero workflows read and not on `unreadable` being non-empty:
        # one file that will not parse beside a conforming one is a tree that
        # is one bad file short of complete, and it still gets a measurement.
        print("check_history_checkouts.py: no workflow was read, so the report "
              "above is not a measurement of this tree -- that is a broken "
              "census, not an empty one, and a run that read nothing does not "
              "pass.", file=sys.stderr)
        return 1
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
