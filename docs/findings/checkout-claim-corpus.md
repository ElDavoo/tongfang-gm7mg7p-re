# The checkout-depth sweep derived its own population, and a retraction quotes the sentence it retracts

**Issue #1031. Written 2026-09-26.** #1009 corrected seven sentences that
described what this repository's checkouts can do, three of them in markdown,
and the checker it wrote read **two files, listed by hand**, and neither was
one of the three. A second round, at that change's review, found two more. A
third round is what this page is, and the reason it exists is one sentence long:
**a list of files is a list of the sites somebody already found, so the next
one is not in it.** `PROSE_FILES` is gone. The reported half of
`ec/tools/check_history_checkouts.py` walks the tree, reads every text file, and
judges the sentences it finds. The rule is unchanged — *a sentence asserting a
workflow's checkout depth names the job of every workflow it names* — and
applying it to markdown is what found the sixteen sites below.

The tool's own write-up is
[`history-checkout-claims.md`](history-checkout-claims.md); nothing on that page
is retracted, and the sentence it uses to record what a correction costs is
quoted below rather than paraphrased.

## What was measured, on this tree

**The figures below are measured on a named tree and are not held.** That is a
change from the first version of this page, which presented them as "a
transcription of one run of the tool" on this tree — and no run produced them.
The reviewer re-measured and found `13 / 46 / 13` true of no tree it could
construct; the first re-measurement here found `16 / 62 / 17` on the branch's
base and `19 / 66 / 19` on the merged tree, **three different answers three
weeks apart, none of them the published one.** A figure written beside the
sentences is the thing this page exists to stop, and writing four of them was
doing it. So each is now stated against the commit it was measured on, and what
is *held* is stated as a held thing: the file set as a pinned list, and the
counts as floors.

| | before | after |
|---|---|---|
| files read for prose | 2, named in a constant | every text file in the tree, derived — printed on every run and **not written down here** |
| files carrying a depth claim | 2 | **19** |
| sites | 5 | **66** |
| sites reported as a quotation, not judged | 0 | **19** |
| claims naming no job | 0 | **0** — the run prints *"every one of them names the job of every workflow it names"* |

**The "before" column is `origin/main` at `e6c95b8c`, read by this change's
checker, and the "after" is this branch.** They are not two states of one tree
read at two times, which is the reading a before/after table invites: the
"before" is main's prose under this PR's tool, extracted to a scratch tree,
because the tool this page is about does not exist on main. A reader can
reproduce it —

```console
$ git archive origin/main | tar -x -C /tmp/before
$ cp ec/tools/check_history_checkouts.py ec/tools/history_checkout_sites.py /tmp/before/ec/tools/
$ cd /tmp/before && python3 ec/tools/check_history_checkouts.py
  … 19 problem(s)
  17 of the 61 sit inside a quoted span and are reported rather than judged
  19 of the claims name no job, in 44 judged sentence(s)
```

— and that run is where the sixteen sites and nineteen claims below come from.

**What is held, and how.** The file set is pinned as an exact list in
`ec/tools/test_check_history_checkouts_corpus.py`, which a file entering or
leaving turns red *by name*; the count is a floor beneath it, and
`test_the_quotations_are_reported_rather_than_dropped` holds the quotation
count as a floor for the same reason. **Floors rather than figures, because a
figure here is stale by the time the page is merged** — this page's own creation
moved the walk, the rebase onto `main` moved it again, and a reader running the
tool on a tree that also holds an untracked file sees a different one again. The
tool prints every one of them on every run.

**The 19 claims are 16 sentences, not 19.** One sentence — the pre-fix
`docs/agent-pipeline.md` item 3 — names four agent workflows and no job of any
of them, and the rule is per workflow, so it is reported once for each; a
report that printed one row for it would understate its own finding by three.
**One of the 66 is this page**: it is a `.md` under `docs/findings/`, it is in
the population, and it is held there by the case named at the foot of this page
rather than by an exemption.

## The sixteen sites, and what each said

**None of the sixteen was false.** **Rows 14 and 15 were corrected by this
change and had no row until review found them**, which is the same failure as
the figures above: something corrected is not thereby counted. **Row 16
entered the population after this branch forked** —
`testdata-index-repair-census.md` is not in the branch's base — and is
corrected here rather than in the sweep, with a marker of its own. Every one names a file where the sentence
should name a job, which is the same defect the seven were and a milder one: a
reader checking one of them has to open the workflow to learn which job it
meant. Each is corrected, and a `*(Corrected 2026-09-26, issue #1031)*` marker
stands at every one of the sixteen sites — the two bullets at sites 9 and 10
share one note — because a correction that leaves no trace of which sentence it
is correcting leaves no way to tell a correction from a change of mind. **The
old wording is in the *what it said* column below for all sixteen**, and six of
the markers carry it in the file beside the sentence as well — sites 1, 3, 5, 9,
10 and 12, which is `../findings.md` §4a-4d's pattern. **The other seven name
what changed and point here.** §4a-4d asks for a retracted claim's wrong version
to stay visible, and none of these sixteen was retracted, so there is no wrong
version for the other seven to leave behind.

| # | file | what it said | what it says now |
|---|---|---|---|
| 1 | `docs/agent-pipeline.md` item 3 | "the agent stages check out with `fetch-depth: 0`" — four workflows, no job | each of the four jobs by name, with its line |
| 2 | `docs/agent-pipeline.md` item 3 | "both of its checkouts … were default-depth", the 2026-09-23 record | the `gates` job at `:39` and the `workflows` job at `:66-69`; the record survives, the ambiguity goes |
| 3 | `docs/findings.md` §86 | "Three said the whole of `ci.yml` was default-depth" | names the `gates` job, which is the one the three wrongly covered |
| 4 | `docs/findings.md` §86 | "a re-copy … that drops the `fetch-depth: 0`" | drops it *from the `gates` job* — it is the only one of the two that states a depth at all |
| 5 | `docs/findings.md` §86 | "`claude.yml:72`'s `fetch-depth: 1`" | the `claude` job, and `:72` is where it is |
| 6 | `committed-checkout-triples-held.md` | "`claude.yml` losing its `fetch-depth: 1` leaves its depth at 1" | the `claude` job's |
| 7 | same | "the issue called `claude.yml`'s `fetch-depth: 1` 'the only shallow checkout'" | the `claude` job's |
| 8 | same | "**`claude.yml` losing its `fetch-depth: 1` line.**" | the `claude` job's |
| 9 | same | "that `claude.yml` is 'the only one that *states* a depth other than 0'" | the `claude` job's |
| 10 | same | "**`claude.yml` losing its line**" | the `claude` job's |
| 11 | `history-checkout-claim-per-workflow.md` | "`claude.yml:72`'s `fetch-depth: 1` is the one checkout …" | the `claude` job at `:72`, and what it states |
| 12 | `testdata-row-claims-repair-measurement.md` | "`ci.yml:39` is `fetch-depth: 0` now" | the `gates` job, which `:39` is |
| 13 | `xdata-moved-ranks-pin-decisions.md` | "`agent-implement.yml` checks out with `fetch-depth: 0`" | the `implement` job's |
| 14 | `docs/ci/agent-gates-capture-claims.patch:119` | "Note the `fetch-depth: 0` `ci.yml:39` carries" and "**`ci.yml:39` is the `fetch-depth: 0`**" | both name `ci.yml`'s `gates` job, which `:39` is |
| 15 | `history-checkouts-gate-wiring.md:272` | "**`ci.yml:39` is the `fetch-depth: 0`**, and the note above it is at **`:33-34`**" | the `gates` job's, and the note's line is corrected with it |
| 16 | `testdata-index-repair-census.md:669` | "`ci.yml:39` and every `agent-*.yml` stage are `fetch-depth: 0`" | the `gates` job's, and every `agent-*.yml` stage's |

**Site 13 is the clearest return, and it is the issue's own prediction.** A
*fourth* copy of the claim, in a *fifth* file, that no earlier sweep looked at
and that #1009 never corrected. **Six** of the other twelve are in the two
write-ups that had landed on `main` *after* the plan for this issue was written
— five in `committed-checkout-triples-held.md` and one in
`history-checkout-claim-per-workflow.md` — which is the same failure arriving
later rather than sooner.

**Where the plan's figures went, and where two of its premises did not.** The
plan measured at `d330478` and predicted six correctable sites; this tree has
sixteen. **The ten extras are not all one kind, and the page that counted seven
of them was itself already short by three**, which is the same defect it
describes:

- **seven** in the two write-ups that had landed since `d330478`, and in
`docs/findings.md` §86 — a site `d330478` itself added and the plan's
prototype did not reach;
- **two** found by review after the table above was written —
  `docs/ci/agent-gates-capture-claims.patch:119` and
  `docs/findings/history-checkouts-gate-wiring.md:272`, both carrying a
  `*(Corrected 2026-09-27 …)*` marker and **neither ever given a row**, so they
  were corrected and then uncounted;
- **one** that entered the population after this branch forked:
  `docs/findings/testdata-index-repair-census.md:669`, corrected here.

The first version of this page said "thirteen" and listed thirteen rows, which
is how two of its own corrections went missing from it.
The count is the tool's, printed on every run and pinned in
`ec/tools/test_check_history_checkouts_corpus.py` rather than written down here
as a constant beside the sentences. Three things the plan asserted about the
*code* turned out to be about an older shape, and each is measured here rather
than repeated:

- **There is no `names_job()` widening left to do.** The plan called for it and
  verified that the tool needed it, but the tool #1034 landed already judges
  once per workflow — `prose_sites()` maps every readable named workflow to its
  own `names_job()` result. The plan measured against the pre-#1034 code, and
  `docs/findings.md` §86 records the widening as landed.
- **The "`claude` job id is its own filename's stem" floor is not a live one**,
  for the reason in *What is not claimed* below. The plan carried it forward
  from a shape `job_text()` had already closed.
- **The sentence boundaries did not need changing**, as the plan's narrow
  reading predicted, and that stands — see the *What is not claimed* entry for
  the one way they are still wrong.

## A correction is a quotation, and no boundary rule tells them apart

This is the finding that made the sweep possible at all, and it is the one the
typed list had been hiding: **a retraction *guarantees* to carry the sentence it
retracts, verbatim, beside the sentence that replaced it.** Read the whole tree
with a rule that only knows about structure and you get every correct site red
for the defect it corrects — including the four the sibling suite pastes as
*controls*, deliberately, because they have to be found and flagged. A check
like that is not strict. It is off.

So the sweep reports a quoted span and does not judge it, with its `file:line`
beside it. Thirteen of the forty-six sites are that: §14f's `*(Corrected …)*`
block, `ec/ghidra/README.md`'s and `testdata`'s quoted sentences, the fenced
blocks in `committed-checkout-triples-held.md` and
`history-checkout-claim-per-workflow.md` where a *run* is pasted, §86's own
`*(Corrected …)*` block, and the held case in `tools/README.md`. **Reported,
not dropped** — silently exempting them would be the same as dropping a file
from the walk, and a reader of the report has no way to tell a quotation from a
site nobody looked at. The enumeration above is a reading aid and not the pin —
the report names all sixteen on every run, and
`test_the_quotations_are_reported_rather_than_dropped` holds the count as a
floor.

**Two refinements, both of which were wrong the first time and are recorded
because both would have made the rule assert nothing.**

- **The span has to cover the whole claim** — the depth word *and* one of the
  workflow names the sentence carries. In a repository where a markdown
  sentence writes `fetch-depth: 0` in backticks as a matter of course, reading
  any code span as someone else's words exempts every claim in every markdown
  file. The retracted sentences are exempt whole; a code span around one term
  is not a quotation.
- **Emphasis is not quotation.** Bold and italic are how this repository
  emphasises a sentence in the author's own voice, and §86's corrected claim is
  one. With them in the rule, §86's sentence is both mislabelled *and* excused,
  and a single stray `*` two paragraphs earlier reaches far enough to excuse a
  fifth claim that is not a quotation at all. That second half is the one the
  plan did not predict: **the failure was not the span list, it was a runaway
  `*`.**

**A hand-kept list of quoted spans was the alternative and was declined.** It is
the same defect one level up, and it would go stale silently: a retraction
rewritten in a new shape would be judged, and nothing would say so. A list of
*paths* was accepted instead, for the files whose purpose is to hold these
sentences verbatim, and only four exist.

## What the walk declines, and why

Four rules, each printed with its resolved paths on every run. **A declined file
is a scope fact and not a finding about a sentence in it**, and it is kept in a
different vocabulary from "not found by this method", which stays reserved for a
claim inside a file that *was* read. Nothing here is ever reported as absent.

| rule | what it refuses | why |
|---|---|---|
| `repository-internal` | `.git/`, `__pycache__/` | not this repository's text |
| `vendored-input` | `vendor/` | committed binaries as inputs, per `CLAUDE.md`, not prose anyone cites |
| `generated-output` | any `decompiled/` tree, the four this tree holds | machine output, where a depth word is a string somebody typed rather than a claim |
| `instrument-or-record` | the checker, the three suites written against it, and the #1009 write-up | a control judged is not a control; a write-up whose seven-site table *is* the retraction |

**`instrument-or-record` is a glob, not a list, and that is the point.** The
suites are matched by `ec/tools/test_check_history_checkouts*.py`, so the
fourth one written against this tool next year is covered without an edit here —
and this change's own suite is named to fall under it for exactly that reason,
rather than being added as a hand-kept fourth entry. A list of this checker's
own suites would be the defect one level up, and it would fail *open*: a suite
nobody remembered to add would be judged on the sentences it holds as controls.

**The write-up you are reading needs no exclusion, and that is a claim the
tool's own output makes.** Every sentence above that carries a workflow name and
a depth word either quotes it or names the job, so this file passes the rule it
describes. It did not, at first: the draft said that `claude.yml`'s job id is
its own filename's stem, and the sentence naming that named the file and no job
— the very defect, one level down, in the page about the defect. The correction
was to stop using a depth word there, not to add this file to the exclusion
list. `test_the_changes_own_write_up_is_in_the_corpus_and_is_not_flagged` holds
it, and a fourth suite is not needed to hold it.

## What is not claimed

- **That the sixteen are the claim's complete blast radius.** They are what a
  walk of this tree found by this method on 2026-09-26, and the declined list
  above is a scope list — not a claim that nothing was in the paths it left
  alone. A new file, a new workflow, or a copy in a language `SCAN_EXTENSIONS`
  does not name would all be outside it.
- **That the walk is exhaustive of the *tree*.** It reads what
  `SCAN_EXTENSIONS` calls text; a claim written into a file this does not read
  is not found by this method and is not reported as absent.
- **That the rule is a proof.** It is a floor, and one floor is live *in this
  tree*: `testdata-row-claims-repair-measurement.md`'s fourth limit passes it
  because the sentence contains the word "workflows" in ordinary English — "from
  what the workflows say today" — and `workflows` is a job id of `ci.yml`.
  The rule cannot tell which of the two the sentence meant, so it declines to
  say that either lacks one. A job id is an ordinary word, and this is the case
  the docstring's plain-word caveat predicts landing in the wild.
- **That a claim quoted in a span is true, or that a claim outside one is.** The
  quote rule decides *whether to judge*, not *what is true*; the judgement that
  follows is still the rule above and still a floor.
- **That the sentence boundaries are right.** They are unchanged from #1009 and
  the plan's narrow reading held for this corpus: §14f's parenthesised italic
  correction comes out as one sentence naming both jobs, and the same is true of
  `ec/ghidra/README.md`'s. But `SENTENCE_END` splits on a terminator followed by
  a capital **without regard to a quotation**, so a retracted sentence carrying
  a `.` and a capital inside its own quotes is split in two, and neither half
  names a workflow — which makes it not a site at all. That is a false negative
  in the direction of staying quiet, no case in this tree needs it, and it is
  recorded rather than fixed: the plan scoped boundary surgery out, and
  reworking `pieces()` to respect `MARKED` is a larger change than the eleven
  defects this issue asked for.
- **That `claude.yml`'s job id being its own filename's stem is a live floor.**
  The plan flagged it as one, and it is not: `job_text()` blanks the workflow
  names before the job ids are looked for, so a sentence about that file's
  line `:72` and a sentence about its checkout both measure as naming no job.
  Measured on this tree, not assumed from the older shape.
- **Anything about a verdict, a register status, a hardware fact, or a CI run.**
  None of this needs a laptop and none of it produces a hardware claim.

## The general question, still open

`history-checkout-claims.md` left this open and declining the two fixes that
would not have worked did not close it: **a prose contract duplicated across
tools has no mechanism holding the copies together.** A census is not that
mechanism. What this adds is that a census is *maintainable* — the population
is derived, so it does not need anyone to remember to extend it, and a fourth
copy is a row rather than a sentence. That is a weaker property than the
underlying one, and this page does not claim to have delivered it.

The two options that were declined stay declined, with the reasons on that page:
generating the sentence from the workflows at run time (it puts a YAML parse
inside a failure path whose entire job is to be readable when git has just
failed), and a shared constant between the two tools (a second import edge into
a directory whose files deliberately do not have one). Neither is what failed
here.

## The suite

`ec/tools/test_check_history_checkouts_corpus.py`, picked up by
`tools/run-tests.sh` by `find` with no edit to it, and named to fall under the
`instrument-or-record` glob. **Testing a census matters more than usual here,
because a census that had quietly stopped finding anything is indistinguishable
from one that is working** — the same failure `tools/run-tests.sh:97-102`
refuses to accept for an empty glob, one level up. So the committed cases pin the
derived file set as a *list* rather than a count (a count is satisfied by any
twelve files), pin the three #1009 markdown sites by file and by the job id
their corrected sentence carries, and pin the quotation count as a floor. The
scratch-tree cases paste the pre-fix `docs/agent-pipeline.md` sentence **verbatim
from the source as it stood**, into a fifth file, and watch it fail once per
workflow.

**Two small edits landed outside it.** `test_check_history_checkouts.py` loses
its `chc.PROSE_FILES` assertion — the constant is gone — and keeps the half that
says the two tools are still read, since their own five sentences are what that
suite is about. `test_check_history_checkouts_run.py` pins the report's verdict
line verbatim and the line now reads "in 4 **judged** sentence(s)", because a
quoted site is reported beside these and not counted among them. Both are the
minimum the change forces; neither grows its file.

**Not in any gate**, for the reason `agent-gates.sh` is copied from
`ElDavoo/agent-pipeline`: a gate call is an upstream change and a re-copy, and
this branch's token has no `workflow` scope. It runs under `tools/run-tests.sh`,
where its siblings already live.
