# A checker described in prose drifts; a sentence that points at its docstring does not

(2026-10-03, issue #307. Static reading of committed markdown under `ec/`,
`docs/` and `evidence/`, plus the runs of the two tools involved over the
committed tree. No hardware and no Windows machine is reachable from the
runner this was written on and none is needed: every claim below is a sentence
in a committed file, or the output of a check reading committed files.)

## What the sentences said, and what they say now

`ec/tools/check_cluster_citations.py` is what holds the prose's cluster
citations to the committed census. Its reach was described in the prose around
it, and the descriptions had come apart from the tool.

The sentence in question, in `docs/findings.md` §17,
`ec/annotations/xdata-06c2-06db-timers.md` and
`ec/annotations/xdata-086x-dispatch.md`, was
`../tools/check_cluster_citations.py is what holds the rest of the tree to the census`
— quoted here as a single code span with the path's own span dropped, because
markdown cannot nest them and `ec/tools/check_reach_deferrals.py` reads a
claim out of running prose only, so a nested span would leave half the sentence
asserted. `ec/README.md`'s description of the same tool was rewritten when the
tool grew a third citation form, and it carries the limits the others did not.
The others were not brought with it.

Each of them now reads `../tools/check_cluster_citations.py holds the rest of
the tree to the census, within the limits its docstring states` — the `docs/`
page naming `ec/tools/check_cluster_citations.py` and saying *its own*
docstring, since the two annotation pages write the path relative to themselves.
`docs/findings.md` §17 gained a sentence naming the one claim in the tree those
limits leave unchecked, which is the next heading.

Nothing else moved. `check_cluster_citations.py` is not edited: the sentences
now point at it instead of paraphrasing it, and that is the whole of the fix.

## Why a pointer and not a copy

The obvious alternative — copy the limit list into the sentences — is what the
tree already tried and it is why the drift went unnoticed. The limits are not
decidable: nothing can say whether a paraphrase is still true, so a list drifts
the first time the tool's own wording moves under it. The issue this implements
records that it did move: the merge that taught the tool the `cluster_key` and
`cluster_name` citation forms also reworded a limit in its docstring, and the
sentences beside it kept asserting the reach they had been written against.
Nothing read the two together, so the tree held a claim about the checker that
only the checker's own docstring could contradict, and it sat that way until the
issue asking for the counterexample was filed.

A pointer does not drift, because there is nothing in it to keep true. It says
where the list is, and the list is in the one place that edits it.

## The one claim in the tree that shape leaves unchecked

`docs/findings.md` §17's own reading of the block names the split with the
cluster ids first and the addresses in a trailing list, and that is the shape
`pairings()` cannot read. It asks for a preposition between an address and the
cluster the sentence pairs it with, with no clause boundary in between; the
parenthetical carrying the addresses is a boundary, so nothing pairs and both
addresses fall to the weaker "a member of some cluster this line names" rule,
which either id satisfies. Read straight off the committed text:

```console
$ cd ec/tools && python3 - <<'PY'
import re, sys
sys.path.insert(0, '.')
from check_cluster_citations import census, cited_clusters, name_re, pairings, units
members, known, counts, by_key, by_name = census()
unit = next(u for _, u in units(open('../../docs/findings.md').read())
            if 'cut into' in u)
addrs = sorted({"0x" + a.upper() for a in re.findall(r"0x([0-9A-Fa-f]{4})\b", unit)})
ids = cited_clusters(unit, by_key, by_name, name_re(by_name))
print("unit:", unit)
print("cited:", ids)
print("known addresses in the unit:", addrs)
print("pairings():", pairings(unit, addrs))
swapped = unit.replace("`main-ec-128` and `main-ec-214`", "`main-ec-214` and `main-ec-128`")
print("pairings() with the two ids exchanged:", pairings(swapped, addrs))
print("problems after the exchange:",
      [a for a in addrs if not any(a in members.get(i, ()) for i in ids)])
PY
unit: **The reading itself.** 37 of the 43 are countdowns the same twenty instructions walk over, 6 are what four of them do at zero, and the two the clustering cut into `main-ec-128` and `main-ec-214` (`0x06C6`, `0x06CD`) are countdowns the same routine decrements.
cited: ['main-ec-128', 'main-ec-214']
known addresses in the unit: ['0x06C6', '0x06CD']
pairings(): {}
pairings() with the two ids exchanged: {}
problems after the exchange: []
```

The unit is read out of `docs/findings.md` through the tool's own splitter rather
than transcribed here, so this block keeps reporting the committed sentence if
the sentence is ever rewrapped.

`pairings()` reads `main-ec-NNN` only, and reads it through a preposition, so
the two ids in that sentence are satisfied by either and the sentence survives
the exchange. It is a claim, it is in the tree, and the check that would read it
does not. That is "not found by this method" and not a disagreement — the
addresses really are members of the clusters really named, which is why the run
is green. The reach is narrower than "holds the tree" says, and that is what the
§17 sentence now says too.

The limit is in `check_cluster_citations.py`'s docstring, where it belongs. It
is not restated here beyond the shape, because a second copy is the disease
this page is about.

## What ran, before and after

The issue's done-when asks that `check_cluster_citations.py` still exit 0 over
the committed tree. It does, and it did before this change: the plan this
implements recorded a red baseline of standing disagreements, and that is no
longer what the tree carries — the corpus moved under the plan, and the suite
that would have been red on it is green. What matters is that the two runs
agree, and they agree on the line that says which units were passed over rather
than checked, which is the part a reworded sentence could have moved.

```console
$ python3 ec/tools/check_cluster_citations.py 2>&1 | head -1; echo "EXIT=${PIPESTATUS[0]}"
skipped: no membership claim 55, disclaims membership 15, census-regeneration transcript 1
EXIT=0
```

That line is byte-identical before and after, and the verdict line below it is
the same apart from the file and line counts, which are this page, the §17
sentence and this page's row in the generated index. A new sentence that made a
cluster claim would have been checked and could have disagreed; one that tripped
a skip would have moved a count on the line above. Neither happened.

## This page's name reddened a check, which is worth writing down

The first version of this file was `cluster-citation-reach-deferral.md`, and
regenerating the index with it turned `check_cluster_citations.py` red — every
address in every write-up title in `docs/findings/INDEX.md`, on one line. It is
named `checker-reach-deferral.md` instead, and the reason is not cosmetic.

`units()` joins a markdown list into one paragraph, so the index's whole list is
a single unit, and two things in it are read as claims about clusters that are
not claims about clusters. `counter-sweep` is a `cluster_name` in
`ec/annotations/xdata-clusters.csv`, and the index has rows for
`counter-sweep-entry-set.md` and `counter-sweep-gap-sites.md` — the name is
matched as a whole token inside a *filename*, and that is what made the unit
cite a cluster. What made the unit *claim* membership, and so get checked at
all, was the word `cluster` inside the new row's own filename. Both together:
every address in every title in the list, checked against one cluster that no
title was talking about.

The fix here was the file's name, not the tool's. The tool is right that a unit
naming a cluster and an address makes a claim, and the honest question it
raises is not "how do I stop this file turning red again" but "should a
generated index of filenames be read as prose about clusters at all". That is
not this issue's work, and `check_cluster_citations.py` is deliberately not
edited here. What a write-up author should know today is that **the name of a
write-up is read as prose by the checkers**, because it becomes a row in the
index, and a name carrying `cluster`, `member` or a cluster name will be
adjudicated as a claim about one.

## The check that keeps the fourth from being written

A rule nobody runs is a rule that has not been written, so
`ec/tools/check_reach_deferrals.py` holds the shape. Over the same roots the
cluster check walks, and through its own `units()` rather than a second
sentence splitter, it finds every unit that names the tool and asserts that
reach in running prose, and requires that unit to point at the docstring. It
asserts the property and names no file, so a document nobody was watching
carrying the old sentence is a red run rather than a fourth copy.

Two things it is careful about, both of which are ways a check of this shape
turns itself off:

- **It does not fire on a document quoting the sentence.** A code span is
  stripped before the claim is read, so this page can show the wording it
  replaced. A fenced block is *not* exempt: a sentence in a block is still a
  sentence the document makes, and the cluster check cuts its units inside
  fences for the same reason. The suite pins both, because "strip fences, the
  way the conflict-marker check does" is the obvious wrong fix and it reads
  like tidying.
- **A tree with no such unit fails.** A rule whose subject has been reworded
  out from under it matches nothing and would otherwise be green, and an empty
  set of problems is exactly what a satisfied check looks like.

The tool's own docstring does not enumerate the limits it defers about. That
would be the fifth restatement, and it is the same mistake one layer down.

`check_reach_deferrals.py` is not wired into `.github/scripts/agent-gates.sh`,
and neither is `check_cluster_citations.py`; `ec/README.md` records that
standing. Wiring a check into the pipeline is a change to files the plan
stage's push token cannot land, and one unwired check added on top of another
is more surface than the issue needs.

## What this opens

- **The tool still cannot read the trailing-list shape.** The live instance
  above is in `docs/findings.md` and stays unread; teaching `pairings()` the
  shape is its own piece of work, the issue this page implements names it as a
  separate question, and until it lands the §17 sentence is the only thing
  telling a reader so.
- **`check_cluster_citations.py`'s docstring illustrates the shape with ids
  that no longer hold the addresses it names.** Its example pairs the trailing
  list with `main-ec-121` and `main-ec-198`, and against the committed
  `ec/annotations/xdata-clusters.csv` neither of those contains `0x06C6` or
  `0x06CD`; the live instance's ids are `main-ec-128` and `main-ec-214`, and
  they do. Nothing checks it — the walk is markdown, and the example is a
  hypothetical in a `.py` — so it reads as a citation to anyone who takes it for
  one. Worth re-illustrating against the committed census, and worth deciding
  first whether the docstring's example should be held to the same rule as the
  prose it describes.
- **Whether a pointer at the docstring is a real deferral.** The rule matches a
  word, so it cuts both ways: a sentence naming the docstring in passing
  satisfies it without deferring, and one that says "subject to the exceptions
  noted below", or links a write-up paraphrasing the limits, defers to a person
  and not to the check. Only the tool's own docstring carries the list, which is
  why that is the one thing worth pointing at; whether a looser pointer is worth
  accepting is a judgement about how much prose this repository wants to write,
  not a mechanical one.
- **Whether a generated index of filenames should be walked as prose at all.**
  The heading above is the measurement; `docs/findings/INDEX.md` is machine-
  generated, every row is a link and a title, and `check_cluster_citations.py`
  reads all of it as one paragraph of claims. Excluding it, or teaching
  `units()` that a `- [file](file)` row is a link rather than a sentence, are
  both small changes to a tool this issue does not otherwise touch — and both
  would remove a class of failure that is currently paid for by choosing
  write-up names carefully.
