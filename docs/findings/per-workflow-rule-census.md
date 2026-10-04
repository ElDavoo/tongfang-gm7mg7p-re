# The per-workflow rule's over-reach, and what it costs over the population the sweep reads

**Issue #1046. Written 2026-10-04.** #1034 made the checkout-depth rule
*per workflow* rather than per sentence, and wrote down what that costs: a
sentence naming a job of `ci.yml` and nothing about `claude.yml` now reports
`claude.yml`, which the page calls a true positive under the rule as stated. It
then declined to put a number on it — *"No claim is made about how often the
over-reach would fire on a different tree"* — and that number was the thing
#1046 asked for. This page is it, and the short answer is that **the issue's own
census does not reproduce**: every site it named resolves to one of four
dispositions today, none of them `flagged`, and of the sites the rule flags
outside the derived population, every one that is not a deliberate control lives
in the one file the sweep declines to read.

Every figure below is **printed by
`ec/tools/test_check_history_checkouts_census.py`** when it runs, and none of
them is written down here. That is `CLAUDE.md`'s "No totals of the repository's
own text": a count of sentences in this repository's own prose is out of date at
the next merge, and `checkout-claim-corpus.md` records what becomes of one —
*"three different answers three weeks apart, none of them the published one."*
What is *held* is the per-site disposition, which is a property of a named
sentence and does not move when an unrelated write-up mentions a checkout.

## What was measured, and over what

The population is derived, not listed. `check_history_checkouts.py` walks the
tree, reads every text file `SCAN_EXTENSIONS` admits, and declines four
categories by rule — so there is no file list here to go stale, and the walk is
pointed at the repository root by the case below. The issue measured over
`docs/findings/*.md` plus four readmes; that set is named in the case as paths,
not as a count, and **`tools/README.md` and `ec/README.md` now carry no depth
claim at all** — theirs were in the per-suite table rows that `tools/README.md`
has since removed in favour of each suite's own docstring. Both files are still
*read* by the walk; they are read and found to carry nothing, which is a
different answer from being declined, and the case holds the two apart by name. A
file that stopped being prose about checkouts is not thereby a finding about it,
and a file that gains one is a claim nothing is holding — which is why the case
names that set instead of counting it.

Run the case for the numbers, and the tool itself for its own:

```console
$ python3 ec/tools/test_check_history_checkouts_census.py
  census[derived population]: … site(s) in … file(s); … quoted; … naming more
  than one readable workflow; … flagged
$ python3 ec/tools/check_history_checkouts.py
  … N sentence(s) in the tree assert a checkout depth: …
```

**The one sentence the answer rests on is a property, not a figure.** Of the sites
that name more than one readable workflow, every one either is quoted or names a
job of every workflow it names. That is asserted by
`test_no_multi_workflow_site_on_the_committed_tree_is_flagged`, and it is a claim
about *which* sentences — a new one that breaks it is named in the failure, so
adding a depth claim to a write-up turns a case red rather than moving a number.

## The accounting, site by site

The issue asked for each site it named to be accounted for. It named them by
`file:line`, and **most of those line numbers no longer describe the tree** —
`history-checkout-claims.md` has been amended since the issue was filed, above the
sentences it points at. So each is identified here by a fragment of the sentence
rather than by a line, which is the identity
`ec/tools/history_checkout_sites.py` already uses for the corrected sites and the
reason it uses it: a fragment survives a rewrap, and a line goes red for one.

There are four dispositions, and **the fourth is the finding**.

| disposition | what it is | sites |
|---|---|---|
| `quoted` | `MARKED` reads the claim as someone else's words, so it is reported with its `file:line` and not judged | `history-checkout-claim-per-workflow.md`'s two reproductions; both of `testdata-row-claims-repair-measurement.md`'s; both `docs/findings.md` sites |
| `names-a-job` | judged, and passes: every readable workflow the sentence names has a job of it named | `xdata-moved-ranks-pin-decisions.md` |
| `flagged` | judged, and the rule is broken | **none on the derived population** |
| `declined` | the file is held by the `instrument-or-record` rule, so the walk does not read it and reaches no verdict | the record file's rows |

**Three of the issue's predictions did not survive the tree it was measured on,
and two of them are the point of the issue.** Its headline — *"a rule that flags
its own write-up's reproductions"* — no longer holds: both reproductions in
`history-checkout-claim-per-workflow.md` are quoted, reported rather than judged,
which is the answer the question was asking for rather than a defect in the
sentence. Its claim that *"quotations #1031 cannot flag away"* is falsified the
other way: the two `testdata-row-claims-repair-measurement.md` sites and both
`docs/findings.md` sites are quotations, and the quotation rule reaches all four,
structurally and without a hand-kept span list. And its reading of
`xdata-moved-ranks-pin-decisions.md` — a site it had no category for — is now
`names-a-job`, because that sentence was corrected to name `implement`.

**What the issue could not have predicted is the fourth disposition.** It asks
what a widened `PROSE_FILES` needs to tell a live claim from a quoted one, and
that question was answered before this issue was planned: `PROSE_FILES` is gone,
`MARKED` and `quoted_at()` tell the two apart, and the population is derived. So
the widening is moot on this tree — not because the file limit was closed, but
because there is no file list left to widen. That is #1031's to own and this
change does not touch it; `check_history_checkouts.py` is unmodified, because
this is a measurement of the rule and editing the rule would make the page a
description of itself.

## The flags outside the population, and where they are

The census's zero has one cause, and it is a scope fact rather than a clean bill
of health. `history-checkout-claims.md` holds the retracted sentences verbatim —
it *is* the record — so `instrument-or-record` declines it, along with this
checker's own source and every suite written against it. The derived population
therefore does not read it, and the sentences #1034's rule would flag there are
not seen at all.

Read anyway, through the checker's own `prose_sites()` with the file named rather
than the walk's, every one of them is still flagged and none of them has changed
disposition. **Declining a file and clearing its sentences are different answers**,
and reading the zero as the second is how "the rule flags nothing" would come to
mean "the rule has nothing to say here". Whether that file should stay declined
now that they are live is a rule change with its own blast radius — lifting the
decline would judge the write-up that quotes the retracted sentences, which is
what the rule exists to prevent — so it is recorded here and handed to #1031
rather than resolved.

**The same force-read over every declined file finds the checker's own machinery
flagged too, and those are controls.** `check_history_checkouts.py`'s report text
and the pre-fix sentences the suite written against this tool holds verbatim are
judged the same way by the same rule — a control that is judged is not a control,
which is why `instrument-or-record` declines them in the first place. So "every
flagged site is in the record file" would be false: the rule flags that machinery
too, and only the *prose* sites outside the derived population are all in one
file. `test_every_declined_file_is_read_and_only_prose_carries_a_flag` walks the
whole declined set and holds that distinction, so a count read off this page
cannot be mistaken for a total.

The two directions that keep this from being vacuous:

- **The shape is still in the population.** A sentence naming more than one
  readable workflow exists, or the zero is about a population that no longer
  contains the case (`test_a_multi_workflow_site_still_exists_to_be_a_zero_about`).
- **The rule fires on that shape.** #1034's own sentence — `ci.yml`'s `gates` job
  full-depth, `claude.yml`'s `claude` job shallow — is pasted verbatim over a
  scratch tree and must be flagged, naming `claude.yml` and not `ci.yml`
  (`test_the_over_reach_case_flags_where_the_committed_tree_has_none`). A checker
  that had stopped judging anything prints the same zero this page reports.

  That control's own sentence is written the way this rule wants a claim written,
  and it took a rewrite to get there: the first draft of this bullet described the
  control in the shape it was pasted in, and the sweep flagged *this page* for it
  — a sentence naming `ci.yml`'s `gates` job and mentioning `claude.yml` without
  naming its job. The fix was to name the job in the prose describing the
  over-reach, not to exempt the page; `test_this_page_is_in_the_corpus_and_breaks_no_rule`
  is what said so.

## The blind spots, carried rather than assumed away

The issue asks for them and they are the method's, not the tree's:

- **The per-file `sentences()` splitter.** `SENTENCE_END` cuts on a terminator
  followed by whitespace and a sentence-opener, so a claim whose wrap puts the
  depth word and the workflow name in different chunks is two sites rather than
  one, and one that names two workflows across a boundary may be judged once
  rather than per workflow. `CHUNK_END` is the other boundary, and the reported
  line is the depth word's rather than the sentence's — a citation to where a
  sentence *starts* sends a reader to the wrong line.
- **The `DEPTH_WORD` vocabulary.** A claim spelled in a way the regex does not
  cover is not a site. "Shallow" and "fetch-depth: 0" are in it; a phrasing that
  says neither is not read, and that is a limit of the method, not a finding
  about the sentence.
- **A file outside the population is not counted, never absent.** `vendor/`,
  `decompiled/` trees, `.git/`, and `instrument-or-record`'s own paths are
  declined by rule, and the report prints each with the rule that held it. The
  flags above are the sharp case: a sentence this method does not read is
  not a sentence this method finds correct.
- **A mention is read as a claim.** The rule cannot tell that a depth word is
  attached to one workflow rather than another in the same sentence, so a
  sentence naming a job of `ci.yml` and mentioning `claude.yml` in passing is
  judged on both. That coarseness is the over-reach this page measures, and it is
  documented rather than fixed: telling the two apart needs the depth word
  attached to a name at clause level, which is not decidable without reading
  English.

## What is not claimed

- **No register status, no checkout depth, and nothing about the other two
  components.** The checker's only dependency is PyYAML and this change reads no
  register, no workflow's actual behaviour, and no Windows binary.
- **No live test ran.** Nothing here was observed on hardware; every figure is
  read out of committed files by running a tool against this tree.
- **No rate.** The claim is about this tree, and the tree moves — which is why
  the page holds dispositions and the case prints counts. A statement about how
  often the over-reach fires *in general* is not made, and neither is one about a
  different tree.
- **That the rule is right.** This is a measurement of what it costs. If the
  census says it is wrong, that is a follow-up for #1031, not an edit here; no
  line of `check_history_checkouts.py` changed.