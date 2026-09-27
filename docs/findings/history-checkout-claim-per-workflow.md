# A depth claim is judged per workflow, not per sentence

**Issue #1034. Written 2026-09-26.** `ec/tools/check_history_checkouts.py`'s
reported half asserted one rule — *a sentence that asserts a workflow's checkout
depth names the job* — and applied it to the **first** readable workflow a
sentence named and to no other. A sentence naming `ci.yml` and `claude.yml`, and
a job of `ci.yml` only, passed. The rule now judges every readable workflow the
sentence names and reports one problem per workflow it names no job of, naming
which. This page holds the defect, the reading taken, and the two limits that
remain — one of them this change introduced, on purpose and with a case saying
so.

**What this is not.** It is a correction to a checker, not to a workflow, not to
a checkout, and not to what `--verify-provenance` requires. The history
requirement is unchanged by any of it; what was wrong was the sentence
describing which job needs it, and which sentence gets judged. **Nothing here
is a claim about how deep any checkout is.** Every fact below is read out of
committed files or reproduced by a scratch tree, and no hardware or Windows
machine is involved: the tool's only dependency is PyYAML.

## The defect

`prose_sites()` collected every workflow a sentence named, then threw all but
one of them away:

```python
known = [n for n in named if n in matched]
job = names_job(sentence, matched[known[0]]) if known else False
```

`prose_problems()` then skipped any site whose `job` was not `None`, so a job
found for one workflow silenced the whole site. `matched` is built in
`load_workflows()`'s `sorted()` filename order (`ec/tools/check_history_checkouts.py:273`),
so `known[0]` was the **alphabetically-first** named workflow that parsed, and
the verdict followed the alphabet rather than the sentence.

On a scratch tree holding a `ci.yml` with `gates`/`workflows` and a `claude.yml`
with a `claude` job, this sentence returned no problem:

```
# ci.yml's `gates` job is full-depth and claude.yml is shallow throughout
```

It names a workflow, asserts a depth, and names a job — of the *other* one. The
same sentence with both job ids dropped was flagged, so the rule was live; it
was blind to the second name. Split the claim over two sentences and only the
first was flagged, which is why a reword that merged two claims into one bought
a pass.

**The report printed both names all along.** `report()` has always looped over
every `named` workflow and printed its checkouts. Only the *verdict* was
first-only, so this change aligns the verdict with what the report was already
showing rather than adding a second reading of the tree.

## Why it matters here

`claude.yml`'s `claude` job at `:72`, which states `fetch-depth: 1`, is the one
checkout in `.github/workflows/`
that *states* a depth other than 0, and it is the punchline of
[`history-checkout-claims.md`](history-checkout-claims.md) — "the difference is
the whole reason the word `stated` is in the table". *(Corrected 2026-09-26,
issue #1031: this named the line and not the job on it. Nothing in it was false;
the old wording is in
[`checkout-claim-corpus.md`](checkout-claim-corpus.md)'s thirteen-site table, row
11.)* A sentence that says the
right thing about `ci.yml` and the wrong thing about `claude.yml` is exactly the
shape the seven-site correction was about, and the checker could not see it. The
same holds for any second workflow: `agent-plan.yml`/`plan` and
`agent-followups.yml`/`followups` both resolve to depth 1.

## The reading taken, and why the second is the same judgement

The issue offered two. **Taken: judge every readable workflow the sentence
names, and flag once per workflow for which no job id is named, naming that
workflow in the message.**

The second — *require the sentence to name a job of each workflow it makes a
depth claim about* — reads as a different rule and is not a separate
implementation, because **this method cannot tell a claim from a mention.** Any
workflow named in a sentence carrying a depth word is treated as one the
sentence claims about. That coarseness is pre-existing: the single-workflow rule
already fired on a depth word anywhere in a sentence paired with a name anywhere
in it. This change applies the same test once per workflow rather than once per
sentence.

The consequence is worth stating plainly rather than leaving a reader to trip
over it. A sentence like *"`ci.yml`'s `gates` job is full-depth, as
`agent-fix.yml`'s is too"* now reports `agent-fix.yml`. That is a **true
positive** under the rule as stated — the sentence does assert a depth about
`agent-fix.yml` and names no job of it — and it is the same defect shape #1009
corrected at seven sites. Separating it from a sentence that merely *mentions*
`agent-fix.yml` in passing needs the depth word attached to a particular name at
clause level, and the whole design of this half is that **one rule is asserted,
the one decidable without reading English meaning**. The module docstring records
this as the rule's known over-reach, not as a bug.

**A readable workflow with no jobs at all is a flag and not an excuse.** The file
parsed, so "there is no job here to name" is a fact about the workflow, which is
the distinction `load_workflow()`'s own docstring draws between a workflow with
no jobs and a file this tool could not read. An unreadable workflow is never
judged at all; it is reported as not found by this method, which is a different
finding from a rule broken.

## The floor is not a proof, and this change adds a second case to it

A job id is a plain word (`plan`, `fix`, `gates`), so a sentence that names one
by accident passes, and a sentence that names the *wrong* job also passes. Two
further consequences, both now demonstrated by a scratch case:

- **A job id two workflows share satisfies the rule for both.** Two scratch
  workflows each with a job `gates`, and a sentence naming both with one
  unattributed `gates`, reports nothing. The rule cannot tell which the sentence
  meant, so it declines to say that either lacks one. This is the sibling of the
  `agent-gates.sh`-is-not-`gates` case, and the same plain-word caveat rather
  than a second one.
- **A job id is not read out of the workflow name beside it.** `claude.yml`'s job
  *is* `claude`, so a matcher reading the raw sentence found that job inside the
  filename the sentence was required to carry, and the issue's own sentence
  passed on its own name. This is the one accidental match that had to be
  **closed** rather than accepted: the workflow names are now blanked out of the
  text the job ids are looked for in (`job_text()`).

  Blanking the span rather than tightening `names_job()`'s trailing boundary is
  the deliberate half of that choice. A job id at the end of a sentence is
  followed by a period; excluding `.` from the boundary would stop that match
  too, and trade this false negative for a worse one in a reword nobody would
  read as a change. Both directions have a case: a sentence whose only `claude`
  is the filename is flagged, and a sentence that names the job beside the
  filename is not.

## What is measured, and what is not

**No committed sentence names two workflows.** All five depth-claim sites in the
two prose files name `ci.yml` and no second workflow — `verify_reassembly.py`
at three sites and `measure_index_repair_visibility.py` at two — so the
strengthened rule flags nothing new on the tree as it stands, and the checker
still exits 0. That is a measurement of this tree, not a property of the rule.

The job ids `implement`, `fix` and `resolve` that appear beside some of those
sites belong to workflows their sentences do not name as files. Naming a job is
not naming a workflow, so they are not claims about `agent-implement.yml` and the
rule is not applied to those workflows at all.

Two committed-tree controls hold the change against regressions, and are the
*Done* condition's other half — a sentence naming one job across two workflows
must not satisfy the rule:
`test_the_two_tools_name_the_job_in_every_depth_claim_they_make` and
`test_each_corrected_site_is_still_one_of_the_sites`, both in
`ec/tools/test_check_history_checkouts.py`.

## Not in scope: the *file* limit, which is a different one

[`history-checkout-claims.md`](history-checkout-claims.md) disclaims that
`check_history_checkouts.py` reads prose from two files, so **a depth claim in a
third file is not found by this method**. That limit is about which *file* a
claim is in; this one was about a second *workflow* inside one sentence, and a
checker that widened `PROSE_FILES` would still have been blind to a sentence
naming two of the files it already read. **Open #1031 owns the file limit.** This
change does not widen `PROSE_FILES` and the two limits are not conflated.

## Two citing lines moved, and what that cost

`history-checkout-claims.md` carries a pin of its own — a citation of a
nineteen-line range in `ec/tools/test_measure_index_repair_visibility.py`, which
`census_test_line_pins.py` reconciles by line. The amendment above is eleven
lines above it, so the pin's citing line moved from `:252` to `:262` and its row
in `test-line-pin-census.md` was repointed to match. `tools/README.md` carries
a pin of its own, and the supersession note its test totals needed sat above
it, so that row moved from `:341` to `:370` — twice, because recording the
first move in that same note cost a second — **a note about a different suite's
figure, costing a row about this one.** **No pin was added and the reconciled
count did not move**: 107 rows answer 107 census records before and after, and
`check_pin_table_rows.py` reports every class 0.

Both old line numbers are recorded here rather than in place, per
[`../findings.md`](../findings.md) §4a-4d, because a row is an index of a moving
tree and a note is where the movement belongs. The alternative — shaping the
prose so a line number happened to stay put — is the kind of constraint that
makes the next writer's sentence worse.

**The line range is named by its file and its length here rather than written
out**, and that is the citation rule this page is under: a `test_*.py:NNN` in
committed prose becomes a census record, and a new one means a new hand-judged
row in a 9,200-line table plus a re-measurement of every figure on it. Naming
the test method instead costs nothing and says the same thing. **The first
draft of this paragraph wrote the range out**, which took the census to 108
records, the per-pin table to 107 rows against 108, and two more suites red;
`test_the_committed_counts_are_the_ones_the_write_up_publishes` and
`test_check_pin_table_by_cited_file.py`'s two committed-tree cases are what
caught it, in `ec/tools/test_census_test_line_pins.py` and
`ec/tools/test_check_pin_table_by_cited_file.py`.

## What is not claimed

- That any workflow's checkout depth changed, or that `--verify-provenance` has
  ever passed in CI. Neither is touched here; the rule is about the sentence, not
  the checkout.
- That the strengthened rule is satisfied by more sentences. It is stricter: it
  can flag a sentence the old one passed, and the over-reach above is what that
  costs. No claim is made about how often the over-reach would fire on a
  different tree.
- Any register status, any hardware fact, any Windows fact, and anything about
  the other two components. None of it is read by this change.
- That the citation shapes in this page are exhaustive of the tree. It is a
  write-up about a checker, and the checker is the thing that would say.
