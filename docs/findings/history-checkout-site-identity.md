# The four corrected sites are held by value, and the check is shown going red

**Issue #1030. Written 2026-09-26.** #1009 corrected four sentences in two
tools about this repository's CI checkouts and built
`ec/tools/check_history_checkouts.py` to re-derive them. What held the four
sites in that suite was a **count** and a **set**, and both were structural: they
were satisfied by construction on the very edit they most needed to catch. This
page keeps the old source, records what the tree holds, and states the
replacement — `ec/tools/history_checkout_sites.py`, a keyed table read by the
same suite — with the seven controls below: five of them name a row that goes
red, the other two show the hold surviving a rewrap and the phrase the two tools
share, and the seventh is the `PROSE_FILES` shrink the file-set comparison
could not see.
The finding #1009 made is not in question here and nothing here re-derives it:
**the five sentences the tool prints today all name a job, and
`prose_problems()` is empty on this tree.** What was wrong is the tripwire.

**What this is not.** It is not a change to `check_history_checkouts.py`, and it
is not a claim about the workflows. The tool is a *report* and is not in any
gate, so "goes red" throughout this page means `tools/run-tests.sh`, which is
where the suite lives. Nothing here is a hardware, Windows or CI observation, and
the whole change reads committed files and runs offline.

## The two tripwires, and why neither could fail

Verbatim from `ec/tools/test_check_history_checkouts.py` as #1013 landed it:

```python
    def test_the_two_tools_name_the_job_in_every_depth_claim_they_make(self):
        # The control that makes the rest of this suite mean something: on the
        # tree as it stands, the committed prose passes the rule. When a tool's
        # contract paragraph goes stale again, this is what goes red.
        workflows, unreadable = chc.load_workflows(str(REPO))
        sites = chc.prose_sites(str(REPO), workflows, unreadable)
        self.assertGreaterEqual(
            len(sites), 4,
            "fewer than four depth claims in the two tools. Each of the four "
            "sites #1009 corrected carries one, so fewer means a reader has "
            "quietly stopped finding them -- which reads exactly like a tool "
            "that is working.")
        self.assertFalse(chc.prose_problems(sites), chc.prose_problems(sites))

    def test_each_corrected_site_is_still_one_of_the_sites(self):
        # The four sites, named. A reader that found three of them would leave
        # this green, which is why the count above is a floor and this is a list.
        workflows, unreadable = chc.load_workflows(str(REPO))
        sites = chc.prose_sites(str(REPO), workflows, unreadable)
        found = {rel for rel, _line, _sentence, _named, _job in sites}
        self.assertEqual(found, set(chc.PROSE_FILES))
```

**The floor was satisfied by the wrong number, because there are two numbers in
this page's subject and they were being conflated.** #1009 corrected four
*sites*; those sites now occupy five *sentences*, because the sibling's
replacement comment is a depth claim about `ci.yml` in its own right. Run
`python3 ec/tools/check_history_checkouts.py` on this tree and the report prints
five:

| # | site | the report's `file:line` | what the sentence is |
|---|---|---|---|
| 1 | `ec/tools/verify_reassembly.py` | `:82` | the docstring's usage block, as a comment |
| 2 | same file | `:1317` | the comment above `HISTORY_REQUIREMENT` |
| 3 | same file | `:1324` | `HISTORY_REQUIREMENT` itself |
| 4 | `ec/tools/measure_index_repair_visibility.py` | `:116` | the sibling's comment — **two sentences, one site** |
| 4 | same file | `:128` | the sibling's `HISTORY_REQUIREMENT` |

*(The sibling's two are `:116` and `:128` **on this tree**. The issue carried
`:111`/`:123`, which is what the report gives at `d3304785`, the tree #1030
forked from; they were re-taken here rather than carried forward, and
`python3 ec/tools/history_checkout_sites.py` prints every row beside the line it
matched, which is how to re-derive them. **The figures in this table are a
reading of a tree, not part of the hold** — the *row* is what a line cannot be,
and that argument is under its own heading below.)*

Four sites, five sentences, and the floor says `>= 4`. **So 5 → 4 is green**: a
reader that quietly stops finding one corrected site is caught by neither case.
Only a drop to three is.

**And the second case was tautological in the direction that mattered.** Its
comment says the opposite of what the code does — *"this is a list"* — but
`found` is a set of **file paths**, and `verify_reassembly.py` carries three of
the four sites on its own. `chc.PROSE_FILES` is the same two-entry tuple
`check_history_checkouts.py:139` hands to `prose_sites()`, which iterates it at
`:479`, so `found ⊆ set(PROSE_FILES)` **by construction** and the assert could
only fire on an element that is not in `PROSE_FILES` — which cannot happen.
*(Those two pointers have been re-registered three times, and each reading is
left written where it was measured, per [`../findings.md`](../findings.md)
§4a-4d — the *hold the address* rule this paragraph argues for, applied to the
paragraph itself rather than excepted from it. They read `:98` and `:398` at
`d3304785`, the tree this issue forked from; `:139` and `:476` after #1034's
rule change, which expanded the tool's own docstring by forty-one lines above
`PROSE_FILES` and added `job_text()` below it; and `:139` and `:479` after
#1043's landing beside it, which moved the second by three more. **This merge's
step moved both, and the pair on the merged tree is `:189` and `:656`** — not by
#1030, which touched neither line, but by #1032's `:50` above `PROSE_FILES` and
its `:177` below the loop, both of which landed on `main` while this page was
being written. Re-run
`grep -n '^PROSE_FILES\|for rel in PROSE_FILES'
ec/tools/check_history_checkouts.py` to re-derive them, which is the same
"hold the address" rule the paragraph this sits in is arguing for.)*
**Deleting an entry from `PROSE_FILES` left this case green** — control G, on
the committed tree — and that is exactly the edit that takes a corrected site
out of the checker's reach: the tuple is the one `prose_sites()` iterates, so a
file leaves the set its found paths are compared against at the same moment it
leaves the set that is read, and both sides shrink together. What it
demonstrated is the shape
[`history-checkout-claims.md`](history-checkout-claims.md) §"The suite, and why
the checker needed one" exists against — *"a checker that has quietly stopped
finding anything is indistinguishable from one that is working"* — open in the
one place written to close it.

## The identity: a file and a fragment, and why not a line

`ec/tools/history_checkout_sites.py` holds one row per corrected site —
`(relpath, fragment, what it is)` — and matches each row's `fragment` against the
sentence the report prints, **within that row's file**. Three properties, each
load-bearing and each with a case:

- **File-scoped.** The two tools' `HISTORY_REQUIREMENT` sentences both carry the
  phrase *"which is what ci.yml's `workflows` job uses"* — one in each file. A
  fragment taken from that shared wording would match a site in each, and one row
  would end up covering a sentence in each file. Rows 3 and 4b are each written
  to start *after* the shared phrase, so the scope is what makes that necessary
  rather than lucky — and it is also what lets the two tools keep their own
  wording of one fact, which the claims page declines to unify with a reason.
- **Whitespace-normalised.** Two of the five sites are Python string constants,
  so the raw sentence carries `\n` escapes and a `" "` seam that leaves **three**
  spaces where two source lines meet. Every match is made against
  `" ".join(readable(sentence).split())` — the text the report prints, run
  together — so a rewrap of the comment around a claim is not a change to its
  row. Control C below is the executable form.
- **Not line-keyed.** A line-keyed identity needs a stated drift rule, and the
  comment above `HISTORY_REQUIREMENT` is the case in point: it has been
  repointed repeatedly this month, which is the reason the issue named it. A
  fragment-keyed one does not. The precedent is the repository's own:
  `ec/tools/check_citation_lines.py:18-22` — **hold the address, not the
  number** … a rank is not an identity.

**Three more directions than the count had, and none of them is free.** A site
that no row matches is also a failure: without it a *sixth* depth claim in either
tool is invisible, which is the same defect one row over. The cost is one row
when a claim legitimately grows, and the failure message says so. The other two
are the "more than one" cases, and they are transposes of one another: a row
matching more than one site, and a site matched by more than one row. **A first
pass judged only the first of those and named the second inside its message**,
which read as though the table could tell a reader that two of its rows had
landed on one sentence when it could not — the two conditions are independent,
and with rows `"alpha beta"` and `"beta gamma"` against one site
`"alpha beta gamma"` each row matches exactly one site, so neither fires and
`problems()` returns nothing. The issue's third direction is the second of the
two, and it is reachable rather than hypothetical: a rewrap that merged two
sentences of one file is the move control C exists to demonstrate, taken one
step further. Both are now judged, each naming only what it detected, and
control F is the case that reaches the second.

**Not-found is not absent.** The matcher cannot tell a sentence deleted from a
file from a reader that stopped finding one, so every message is worded *"not
found by this method"* and never *"removed"* or *"absent"*, per `CLAUDE.md`'s
rule and `ec/annotations/registers.yaml`'s own caveat.

## The five rows, by value

| row | file | fragment | what it is |
|---|---|---|---|
| 1 | `verify_reassembly.py` | `` ci.yml's `gates` job has one (`fetch-depth: 0`) and is the job that runs the gate `` | site 1, the docstring's usage block |
| 2 | `verify_reassembly.py` | `` the agent stages' `implement`, `fix` and `resolve` -- checks out with `fetch-depth: 0` `` | site 2, the comment above the constant |
| 3 | `verify_reassembly.py` | `` which is what ci.yml's `workflows` job uses, though that job runs no history reader `` | site 3, `HISTORY_REQUIREMENT` |
| 4a | `measure_index_repair_visibility.py` | `` has been `fetch-depth: 0` since #407 (`cc2ab10d`) while its `workflows` job is default-depth `` | site 4, the sibling's comment |
| 4b | `measure_index_repair_visibility.py` | `` has neither of them, and this tool would go on to report a count of zero over a tree it never read `` | site 4, the sibling's `HISTORY_REQUIREMENT` |

`python3 ec/tools/history_checkout_sites.py` prints this table beside the
committed tree with each row's matched `file:line`, and exits non-zero on any
problem. **That is also the regeneration path**: after editing either tool's
prose, run it, copy a fragment out of the output, add the row. A fragment
written from the source rather than from that output need not match —
`readable()` strips the source quoting and the comment marker off both ends of a
sentence — and the table therefore cannot go stale for want of a way to update
it.

## The controls, and what each one proves

Seven: six on the suite's existing `ScratchTree` fixture, and **G on the
committed tree**, which is the only place its edit can be shown. All of them
read the committed files through a `committed()` helper rather than a pasted
copy — the same reason the corrected sentences are read out of the tree rather
than carried as constants. **Each asserts which row is named, not that some list
is non-empty**, which is the argument this suite's own docstring makes about the
`STALE_*` paraphrases — with the two exceptions noted below, which demonstrate
that the hold *stays* green rather than that a row goes red.

**A — the 5 → 4.** `HISTORY_REQUIREMENT` replaced by a one-line version carrying
no depth word, so the report finds the other four sentences and not this one.
Four sites, `prose_problems()` empty, and `len(sites) >= 4` green by arithmetic.
The old pair is green; the keyed hold names row 3:

```
ec/tools/verify_reassembly.py: no site carries the fragment "which is what
ci.yml's `workflows` job uses, though that job runs no history reader" -- site 3
-- `HISTORY_REQUIREMENT` itself. 2 site(s) were found in that file. Not found by
this method: a reader that stopped finding this site and a sentence taken out of
the file are the same thing here, and neither is reported as absent
```

**B — the sibling gone.** The sibling absent from the tree, which is what a
prose file the reader cannot open looks like from in here. Three sites, and both
sibling rows named — one message each, each saying `0 site(s) were found in that
file`. Reached through a scratch tree rather than by rebinding
`chc.PROSE_FILES`, which reaches identical code and keeps the fixture the suite
already uses. **This is not the `PROSE_FILES` edit and is not claimed to be**:
with the sibling gone from the tree but still listed, the old file-set
comparison goes *red*, because a file the reader could not find is the one
direction it could see. The shrink that leaves it green is control G.

**C — the rewrap.** Site 2's comment at different line breaks, same words. The
report gives the sentence a **different line** (`:1317` → `:1318`) and the table
still holds it: five sites, `problems()` empty. The case asserts the squashed
sentence is character-for-character the committed one rather than assuming it,
so a rewrap that quietly edited a word could not pass as a demonstration of
rewrap-immunity.

**D — a sixth claim.** A true depth claim about the scratch tree's own `gates`
job, matching no row. Six sites, one message, and the other five rows still
matched — the direction a count cannot have, and the case that makes the
symmetry a check rather than a branch nothing reaches.

**E — the file scope.** The shared phrase above, as a row scoped to the sibling:
it matches the sibling's site and declines the first tool's, with the
counter-assertion that the phrase really is in **two** of the five sites, so
declining one is a decision rather than an accident. This case asserts through
`history_checkout_sites.match()` rather than through the suite's own helper,
because a case that used the helper's filter would be testing that filter: with
the matcher's scope dropped it stays green, and it does not.

**F — two rows, one sentence.** The sibling's site 4 merged back into a single
comment, carrying the committed words of both the row that names its comment and
the row that names its `HISTORY_REQUIREMENT`. Two of that file's rows land on one
site, and the case asserts the fourth direction fires, names both rows, and calls
it a bug in the table rather than a drift — nothing has gone missing here, the
site is still found. This is the issue's third direction by its own words
(*"a site matching two rows — reported as a bug in the table, not as a drift"*),
and **it is also the reachability argument for the fragment key**: control C's
rewrap is a merge in the other direction, and a rewrap that merged two sentences
of one file into one is a move a reader can make, so the condition had to be
judged rather than left as a message nobody could see.

**G — the `PROSE_FILES` shrink.** The edit the file-set comparison was blind to,
on the committed tree rather than a scratch one: `chc.PROSE_FILES` with the
sibling dropped from it, restored by the case's own cleanup. The old
`assertEqual(found, set(chc.PROSE_FILES))` runs verbatim and is **green** —
`prose_sites()` iterates the tuple, so the file leaves the set its found paths
are compared against at the same moment it leaves the set that is read — and on
that same read the keyed hold names both of the rows the file was carrying, each
by its own fragment rather than by a count. This is the case §"The two
tripwires" above rests the "deleting an entry left it green" sentence on, and
the committed tree is the only place it can be shown: the point is two rows that
really are in a file, and a scratch tree has to lose the file outright to make
the comparison see anything at all, which is control B and a different result.

**Falsifying the table itself**, which is the other half of the evidence: delete
one row, re-run the suite, and the committed-tree case goes red on
`matches no row in this table` with the file, the line and the whole sentence
named. The table does not pass by being unexercised.

## What is not claimed

- **Nothing about the workflows.** The five sentences are not re-derived here and
  the rule that each names a job is not in question; `prose_problems()` is empty
  on this tree. What was wrong is the tripwire, which is the issue's own
  calibration and is repeated here because the distinction is the whole page.
- **That the table is a check on the prose.** It is a check that a *set of named
  sites* is still being found. A corrected sentence that stops naming a job is
  caught by the tool's own rule, not by this table, and a sentence that is wrong
  in a way that keeps its words passes both.
- **Any gate wiring.** Neither the tool nor this table is in
  `.github/scripts/agent-gates.sh`, for the reason
  `history-checkout-claims.md` gives. "Goes red" means `tools/run-tests.sh`.
- **Any hardware, Windows or live CI fact.** None of this needs a laptop, and
  none of it produces one.
- **The shared-definition question.** Whether the two tools' copies of
  `HISTORY_REQUIREMENT` should be one constant is still declined on
  [`history-checkout-claims.md`](history-checkout-claims.md) with a reason, and
  is still open. Holding each copy by value does not resolve it and does not
  pretend to.
