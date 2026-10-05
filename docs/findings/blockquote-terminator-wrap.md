# A quoted paragraph's sentence boundary must not depend on where it was wrapped (issue #617)

`check_cluster_citations.py`'s `units()` joins a paragraph's stripped lines and
cuts the result into attribution-sized sentences at `TERMINATOR`. `line.strip()`
takes a blockquote's indentation but not its `>`, and `>` was not in that
regex's lookahead, so a sentence boundary inside a quoted paragraph was
recognised only where the marker did **not** fall between the period and the
next capital. The same words therefore read as one unit or two on the strength
of where an author had wrapped them.

The pair, from the issue, over committed inputs and writing no file:

```console
$ python3 -c "
import sys; sys.path.insert(0,'ec/tools')
import check_cluster_citations as c
a='> Those three are the whole of the \`main-ec-07FD\` cluster. The setb c at 0xD982\n> makes the second limit 0x07FE.\n'
b='> Those three are the whole of the \`main-ec-07FD\` cluster.\n> The setb c at 0xD982 makes the second limit 0x07FE.\n'
for t in (a,b): print(len([u for _,u in c.units(t)]), 'unit(s)')"
2 unit(s)      # period mid-line
1 unit(s)      # period at the wrap
```

Three substitutions from the issue's text, each forced by another gate in this
repository rather than by the wrap, and each caught by running them rather than
by reading the draft:

- The cluster is cited by the id the committed census gives it
  (`<program>-<lowest address>`), not its pre-2026-04-04 rank.
- The quoted address is one the named cluster holds. The issue's `0x0800` is
  held by a *different* cluster, so quoting the sentence unchanged put a live
  disagreement in this write-up — the gate working, on a sentence quoted as an
  example of the very wrapping defect it reports.
- "bound" became "limit", because `bound` is in
  `census_citation_exemptions.py`'s role lexicon, and the word in the address's
  own clause made this the one committed unit an operand/bound exemption would
  admit — which `test_census_citation_exemptions.py` holds empty, because
  `operand-bound-exemption-census.md` records the exemption as declined.

The wrapping under test is unaffected by any of the three: `units()` reads no
census and classifies nothing, and both substituted wrappings still yield two
units. The substitutions are recorded because a future reader restoring the
issue's wording would otherwise reintroduce all three, and would read the
resulting red as this fix misreading its own subject.

A walk whose population moves with a reflow is not one whose verdicts mean
anything, so this is a defect in the gate that holds published
cluster-membership findings about the EC against the committed census — not a
tidiness complaint about a quote.

## The decision: carry `>` in the lookahead

`TERMINATOR` is now `(?<=[.!?])\s+(?=[A-Z`*_|>-])`. Both wrappings of the pair
above yield two units, so the command printed above reports `2` for each rather
than `2` and `1`.

The alternative — strip the marker before the join, which also makes the wrap
irrelevant and reads better — was measured and **not adopted**. The rejection
and its evidence are below, because the interesting part of this issue is that
the obvious fix is the wrong one.

## Why the verdicts could not decide it

Stripping every line-leading `>` under the three `ROOTS` and re-running the
committed walk changes no verdict: **no disagreement either way**. That is the
whole of what a 0→0 run says, and it is true of *both* readings, which is
exactly why it cannot choose between them. It is reported here as the fact it
is and not as evidence the fix is right — a run that finds nothing is
consistent with a walk that checks more carefully and with one that has gone
quiet, and nothing in a 0→0 result tells them apart.

The measurement that decides it is coverage: what the walk still *checks* under
each reading, not what it reports.

## What decided it: coverage, not verdicts

Keying the walk's held attributions on `(file, address, cluster)` — and not on
the line a claim is reported against, which a split legitimately moves — the
committed corpus gives:

| | pair, period mid-line | pair, period at wrap | corpus disagreements | held attributions, against today's walk |
|---|---|---|---|---|
| before | 2 units | **1 unit** | 0 | — |
| strip the marker | 2 | 2 | 0 | **drops some of them** |
| carry `>` | 2 | 2 | 0 | **holds all of them** |

The last column is a relation and not a figure, because a figure there is a
count of this repository's own prose and the line carrying it is one every
branch that touches a blockquote has to edit. What the strip gives up prints
as:

```console
$ python3 -c "
import importlib.util
spec=importlib.util.spec_from_file_location('t','ec/tools/test_check_cluster_citations_blockquotes.py')
t=importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
held,stripped=t.TheStripWouldCostACoverage._over_committed_tree()
for path,h in held.items():
    for claim in sorted(h-stripped.get(path,set())): print(path, claim)"
ec/annotations/xdata-06c2-06db-timers.md ('0x06D6', ('main-ec-0460',))
ec/annotations/xdata-06c2-06db-timers.md ('0x0843', ('main-ec-0460',))
ec/annotations/xdata-06c2-06db-timers.md ('0x0844', ('main-ec-0460',))
ec/annotations/xdata-06c2-06db-timers.md ('0x08A8', ('main-ec-0460',))
```

Every one of those addresses is a member of `main-ec-0460`, so this is the
shape of the failure rather than an accident of one page: an address whose only
membership cue sat in the neighbouring list item.

Two measured facts decide it, and neither is a disagreement count:

1. **The strip costs coverage, and it does it through the list split.** Taking
   the marker off is not a neutral rewrite: with the `>` gone, `LIST_ITEM` can
   see the `-` of a quoted tight list, so a blockquote that was one paragraph
   becomes one unit per item. In
   `ec/annotations/xdata-06c2-06db-timers.md` that separates the item naming
   `main-ec-0460` from the item carrying the addresses it governs, and the
   address item makes no membership claim of its own — so it is passed over as
   `no membership claim`, and an attribution the walk holds today stops being
   held. That is the failure
   `test_check_cluster_citations_list_units.py`'s docstring already names for
   the list split ("one that split too eagerly would separate an address from
   the cluster id it belongs with, and that failure is silent in the same
   direction"). A claim nothing checks reads exactly like a claim that is not
   there.

   The strip therefore does not merely read differently; it turns on a *second*
   rule for a body of prose that rule was never applied to, and a blockquote is
   exactly where a quotation's own formatting is most likely to look like a
   list. `AQuotedListIsNotTheStrip` pins the difference on a fixture small
   enough to see.
2. **The narrow fix is coverage-preserving.** Keyed the same way, the set of
   held attributions is *identical* in both directions — nothing added, nothing
   dropped — and no verdict changes. What it changes besides that is not the
   same thing as "no effect", and the difference is worth stating here rather
   than rounding away, because rewrapping a quote is exactly what a future
   reader may do:

   * **A split can take a unit out of the skip tally altogether.** In
     `docs/findings/reset-vector-dptr-targets.md` a correction blockquote was
     one `cites a rank` skip and is now several units, of which the one
     carrying the known address names no cluster at all — so the walk does not
     reach the membership rule on it, rather than reaching it and passing it
     over. The membership claim and the address it governed were in one unit
     and are in two now, which is the separation the strip causes above; here it
     loses nothing, because that text is a correction the walk was not checking
     anyway.
   * **A split can narrow an any-of fallback**, which is a tightening of the
     membership rule and not a relabelling of it: an address left with fewer
     candidate clusters is one that fewer sentences satisfy.
     `ec/annotations/manual-fan-ctrl-0751.md` reaches that today — a wrapped
     sentence is tested against `main-ec-011`, `main-ec-012` and `main-ec-013`
     before the split and against `main-ec-013` alone after, and `0x089C` is
     held by `main-ec-0875` rather than by any of them, so both readings reach
     the same verdict on it. It stays silent because the units it shows in are
     passed over under `cites a rank` either way: a narrowing that turned a
     verdict red would need a live wrap separating a cluster id from an address
     it governs *on a unit the walk checks*, and today's corpus has none.

   `SKIPS`, `skip_reason()` and `census_row()` are untouched by this and the
   fix adds no skip reason, so the vocabulary of reasons is unchanged even
   though which units it is applied to is not.

Both directions of that comparison are cases in
`ec/tools/test_check_cluster_citations_blockquotes.py`, run over the committed
tree rather than asserted here, so a corpus change that reopened the question
fails the suite instead of leaving a stale decision in prose:

```console
$ python3 ec/tools/test_check_cluster_citations_blockquotes.py
```

`TheStripLosesAClaim` asserts the relation in both directions — that the strip
drops something the current walk holds, and that the current walk holds nothing
the strip does not. It asserts a relation over the tree and never a count of
it, so it stays true as write-ups land.

### A third claim that measurement did not support

The strip was also weighed on whether it would widen the **count** rule, since
quoted tables in the corpus are `>`-prefixed `|`-rows and would arrive as table
rows. They do: taking the markers off does make those lines into table-row
units. But no committed blockquoted table row is a row the count rule reads —
`census_row()` wants a first cell holding exactly one `main-ec-NNN` the census
knows, and none of them has that — so the count rule's reach widens over rows it
then declines, and the set of census rows it reads is the same either way. The
widening is real and the effect on this corpus is nothing. Recorded because the
argument was made before it was measured, and a rule change justified by an
unmeasured one is the half-measure `reset-vector-dptr-targets.md` declines.

## Two consequences worth stating rather than leaving to the diff

**The fix also splits `>`-prefixed lines inside fenced blocks.** A fenced block
is still cut into sentences inside itself and `>` is in the lookahead now, so a
`diff` transcript's `>` lines become units where they were one.
`docs/findings/testdata-row-claims-no-addr-column.md` carries such a
transcript, so this is a shape the corpus reaches. Those units name no cluster
and no XDATA address, so they are outside every rule; the corpus walk covers
them and reports no disagreement. `AQuoteInsideAFence` pins it, including that a
quoted membership claim inside an ordinary fence is still checked — the fence
scopes a regeneration transcript and nothing else — and that one inside a
transcript is still passed over under its named reason.

**The wrap-dependence was a property of the committed prose only.** One
rewrapped quote naming a cluster id was enough to move a published finding
across the gate's line, which is the failure this closes. Whether a blockquoted
correction should be a *unit of its own* — a quotation's membership claims
arguably belong to the quoted source rather than to this repository's prose — is
a different question, about what the gate is for rather than about wrapping. It
is not decided here and it is not what this issue asked; it would change which
findings are held to the census and wants its own issue.

## Scope

Every result above is from committed files walked offline. Nothing here was run
on the laptop or on Windows, no live register read is claimed, and nothing in
this change is hardware-bound. `OneAttributionPerUnit` in
`ec/tools/test_check_cluster_citations.py` is unmodified and remains the control
the re-packed form is measured against: a change that admitted `0x0800` in a
quoted sentence would be a corpus-wide loosening made against one sentence, and
`TheFixIsNotALoosening` holds that it still reports.
