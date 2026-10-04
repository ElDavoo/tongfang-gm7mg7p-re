# What an operand/bound exemption would admit, and why it is not adopted

Issue [#618](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/618) asked
for the set of units an operand/bound exemption would newly admit to be made
enumerable from the committed tree, and for a yes/no to follow from the
enumeration. This is both. The answer is **no**, and the reason is measured
rather than preferred.

**Nothing here is a live test, and nothing is evidence about the firmware.** No
EC image is opened, no register is read back, no capture is taken, and no
laptop, EC or Windows machine is involved. Every input is committed prose and two
committed CSVs, and every claim below is a claim about those.

The **census** changes no rule and no verdict. `check_cluster_citations.py` is
modified in exactly two places: one docstring bullet recording the decision
beside the `charge-target` limit, and `units()`, which now reads a tight list as
one unit per item. That second one is a **walk** change, not a rule change — no
citation is admitted or exempted and `SKIPS` is untouched — and it is here
because the census found a live defect in the walk while measuring, reproduced
and then fixed rather than written up. It is described under
[A trap this page's own name walked into](#a-trap-this-pages-own-name-walked-into--and-the-fix).

## The measurement

```
python3 ec/tools/census_citation_exemptions.py
```

The figures this decision turns on, on the tree this page was written against:

| | |
|---|---|
| addresses that fail today | **0** — the checker exits 0 on the committed tree |
| units a lexicon exemption would admit | **0** |
| units a `SPAN` exemption would admit | every one of them a membership claim, and none an operand — see below |

The population counts are deliberately not tabulated here. They are printed by
the run above, they move with every write-up that cites a cluster, and this page
adding one moved them; a figure in a table that the next merge edits is the
conflict site `CLAUDE.md` warns about. What does not move is the shape of the
result: nothing fails, and no unit is admitted by the lexicon.

The disagreement count is **not** the evidence in either direction, for the
reason the issue gives: a lower count is equally consistent with the rule being
right and with drift being newly admitted. What the decision turns on is the
admitted set, and it is empty on the side the issue is about.

## Why the census is not a second walk

The tool **calls** `check_cluster_citations.py`'s own `census()`, `units()`,
`skip_reason()`, `cited_clusters()`, `pairings()`, `name_re()` and `clean()`
rather than reimplementing any of them. This is the load-bearing decision in the
whole change. A tool that repeated the walk or the skip rules would be a second
census, free to disagree with the rule it is meant to bound — and a disagreement
between the two would be uninterpretable, because nothing in the output would say
whether the checker is wrong or the census is. Sharing the functions is what
makes "the set an exemption would admit" a statement about the actual rule.

The suite holds the population to `check()`'s own view of the same files rather
than trusting the sharing: every unit the checker reads a membership claim in is
classified here, carrying the same address set. The direction is one-way on
purpose — the census reads all three roots and the case names three files — but
it is the direction that matters, since a missing unit would be one the admitted
set was computed without.

## Every membership-checked unit, not only the failing ones

The issue asks for units "carrying an address which is not a member of any
cluster the unit names". That set is **empty**, and a census printing only those
rows would print nothing and measure the wrong thing — an empty result that
reads as "no problem here" rather than as "no current failures, and here is what
would newly go unreported".

So the census reports all of them, and separates two figures that a single
"admitted" count would have merged:

- **`admitted`** — every address the checker reads in the unit is exempt, so an
  exemption leaves the unit nothing to fail on and future drift in it goes
  silent. This is the only verdict that silences anything.
- **`partly`** — some addresses are exempt and some are not. An exemption would
  narrow the check without silencing it, which is a different proposal.

`admitted` is also reported **by the signal that admits it**, because `range` and
`lexicon` are two different exemptions with two different failure modes, and a
single count would let a decision be taken on one while the prose argued about
the other.

## The role lexicon, at two scopes

The lexicon the issue names is `bound`, `immediate`, `operand`, `target`. It is
applied twice per address: within the address's own clause, and anywhere in the
unit. Across the committed corpus:

- **No** address carries a role word in its own clause.
- A number of them carry one somewhere in their unit — the run prints both, and
  the loose figure is strictly the larger one.
- The difference is the gap, and it is the `charge-target` false positive the
  checker's docstring already records — a word matched in a sentence that only
  means the words — reproduced here as a measured result instead of an
  assumption. `prose-line-citations-held.md`'s rows match `target` inside
  `reset-vector-dptr-targets.md`, a filename; `test-line-pin-census.md` matches
  it in "the *cited* targets are this branch's". Neither introduces an address
  as a target.

This is why the two figures are reported rather than one. A census that printed
only the looser figure would make the re-packed §26 sentence below look like an
admitted unit — the word `bound` is in it — which is exactly the confusion the
split exists to prevent.

## The decisive case: the sentence the exemption is for

`test_check_cluster_citations.py`'s `OneAttributionPerUnit` holds §26's re-packed
summary as **expected to report** `0x0800`. Running the census over that exact
sentence gives `(admitted, lexicon)`:

- `0x0800` fails today — it is in `main-ec-104` and not in the `main-ec-081` the
  unit names — so the disagreement is real and open.
- It is **exempt** under the proposed rule, because its clause carries `bound`.
- Every other census-known address in the unit is exempt too, so the unit is
  `admitted`, not `partly`.

So a lexicon exemption's first and only demonstration in this corpus is the one
sentence the checker deliberately keeps reporting, and adopting it would silence
precisely the `0x0800` disagreement that case exists to hold. That is the
half-measure `reset-vector-dptr-targets.md` declines, arrived at by measurement
rather than by argument. The suite pins both halves:
`test_admitting_it_would_silence_the_disagreement_that_control_pins` and the
checker's own case, which is unmodified and still reports.

## The `SPAN` units are membership claims, not operands

Every unit the structural signal admits is a **membership claim about a
cluster** — and that is a weaker and more accurate statement than the one this
page carried when it was first written, which was that every one of them is a
cluster's *extent*. Reading them is what settles that this is not the better
half of the exemption either. The run names them; they fall into three shapes:

- **A cluster's `addr_range`, or that column reproduced.** `docs/findings.md`
  and `xdata-086x-dispatch.md` name `0x0460`-`0x09CE` as the counter block,
  which is `main-ec-0460`'s `addr_range`.
  `xdata-register-map.md`'s rows carry the range as the census's own column,
  `main-ec-001`'s `0x0300`-`0x097B` and `main-ec-013`'s `0x0875`-`0x09E7`
  among them.
- **A span group of named members, which is not the extent.**
  `call-graph-unresolved.md` names `0x3000-0x3008` as members of
  `main-ec-043E`; that cluster's `addr_range` is the wider `0x043E`-`0x300E`,
  so the range is a claim about which addresses the cluster holds, not about
  where it begins and ends.
- **A page in a console transcript.** `xdata-moved-ranks-collision-scope.md`
  carries `page 0x0300-0x05FF` from a `xdata_moved_ranks.py cause` run. No
  cluster has that `addr_range` — `main-ec-001`'s is the wider `0x0300`-`0x097B`
  — so this is a claim about the page the re-keying counted over.

`xdata-page-cluster-count.md` sits with the first: it quotes `main-ec-043E`'s
`0x043E`-`0x300E` to argue that `addr_range` is a min-max span, so counting
over it *would invent every address in between as a member*.

A range written this way is a **membership claim**, not an operand claim —
exempting one would drop a real check on a real claim. That is the property all
of them share, and it is why the wordless signal and the lexicon signal do not
merely disagree about the same set: they admit different sets, and the wordless
one admits the claims the check is most worth making. This is also why the two
are reported apart — folding them into one `admitted` count would have shown a
non-empty set and invited the conclusion that the exemption has something to
gain.

(The set moves as the corpus does — this page quotes a range itself and is
therefore in the set — so the claim here is the shape, not the enumeration.
`test_every_committed_admitted_unit_is_admitted_structurally` holds the shape:
every admitted unit is admitted structurally, never on the lexicon.)

## The criterion, pre-committed, and where it landed

The plan fixed the criterion before the tool was written, so the decision could
not be fitted to the result:

> If the enumeration shows the exemption would silence **no** currently-passing
> checked unit, the answer is no, recorded beside the `charge-target` limit.

It lands on **no**, and the corpus had moved since the plan was written — the
checked population and the skip counts are larger now — so the criterion, not
the plan's figures, decided it.

Three reasons, in the order that decided:

1. **Nothing to gain.** The lexicon admits no unit in the committed corpus.
2. **A check to give up.** The sentence it was proposed for *is* admitted, and
   admitting it silences the one disagreement the checker pins on purpose. A
   rule whose only demonstration is its own motivating sentence buys nothing and
   costs the control.
3. **The wordless alternative is worse, not better.** Every `SPAN` unit it
   would admit is a membership claim about a cluster — an `addr_range`, a §5
   row's own range column, a named span group of members, or a page a
   re-keying counted over — whose exemption would remove a real check.

What is *not* claimed: that an exemption would be wrong in general, or that no
future sentence could justify one. The census is over committed prose and the
committed census, and the lexicon is word-based, so "no address here is
introduced as a bound" is **not found by this method**, never *absent* — the same
caveat `ec/annotations/registers.yaml` carries for a static scan, and the tool
prints it on every run. A later sentence that genuinely needs the exemption is a
corpus-wide re-run and its own decision, with both directions pinned; the suite
holds `test_every_committed_admitted_unit_is_admitted_structurally` so that such
a sentence fails visibly here rather than silently contradicting this page.

## A trap this page's own name walked into — and the fix

Worth recording, because it was a live landmine in the generated index rather
than a bug anyone had fixed, and because the fix is a change to how the corpus
is walked that the decision above does not rest on.

`gen_findings_index.py` renders every write-up's `# ` title into one tight list,
and `units()` read that list as a *single* unit. An index row is a link, an em
dash and a title, with no full stop, so `TERMINATOR` had nothing to split on
either. So whether the whole index was membership-checked turned on whether
**any** title anywhere in it contained `cluster`, `clustering`, `member` or
`members`. It did not: on the committed tree every one of those words sat past
the first unit's end, so the index was skipped for "no membership claim" and
never checked.

Naming this page `cluster-citation-operand-exemption.md` moved the word
`cluster` — in the **filename**, quoted into the index row — inside the first
unit. The whole index flipped from skipped to checked, and addresses belonging
to a dozen unrelated write-ups (`0x1C04`, `0x044B`, `0x0751`, …) came back as
disagreements against whatever cluster the paragraph happened to name.
`check_cluster_citations.py` went from exit 0 to exit 1 on a tree whose prose
had not changed. **Reproduced, not inferred:** rename the write-up under
`docs/findings/`, regenerate the index, and run the checker.

**Fixed here.** `units()` now treats a list item as its own unit, for the same
reason a table row already was: the items mean different things, and joining
them lets one item's cluster id govern the next item's addresses. A
continuation line carries no marker, so a wrapped item stays whole. With the
split, the rename above leaves the checker at exit 0.

The split is coverage-preserving on the committed tree, and that was measured
rather than assumed: walking the corpus under the old rule and the new one and
comparing unit by unit, **no unit is checked under one rule and not the other**,
in either direction. It changes which units are *census* rows for
`census_citation_exemptions.py` — a tight list is now several units where it
was one — which is why the population that tool prints is larger than it was
under the joined walk. The decision is unmoved by it: the lexicon figure is
still zero, before and after.

`ec/tools/test_check_cluster_citations_list_units.py` holds it in both
directions, and holds it against the *unfixed* walk: its fixtures are index
rows without a trailing full stop, because a list written as full sentences was
already being split by `TERMINATOR` and would have passed against the defect.
The suite is red on the pre-split code and green on this.

This is the one thing in this change that alters how the checker reads the
corpus, and it is a walk fix rather than a rule change: no citation is admitted
or exempted, `SKIPS` is untouched, and the checker still exits 0 on the
committed tree.

## What is where

| | |
|---|---|
| the enumeration | `ec/tools/census_citation_exemptions.py` |
| its cases | `ec/tools/test_census_citation_exemptions.py` |
| the decision | `check_cluster_citations.py`'s docstring, beside the `charge-target` limit |
| the walk fix | `check_cluster_citations.py`'s `units()`, and `test_check_cluster_citations_list_units.py` |
| the open question it closes | follow-up 5 of `reset-vector-dptr-targets.md` |

`ec/tools/test_check_cluster_citations.py` is **unmodified**. Its
`OneAttributionPerUnit` is the control this decision is measured against, and
editing it would have destroyed the measurement.

The tool is not in `.github/scripts/agent-gates.sh` and cannot be added from an
agent branch — the plan stage's push token has no `workflow` scope. It runs by
hand, beside the other censuses in `ec/tools/`.