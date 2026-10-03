# The cluster-name citation sweep: how many `main-ec-NNN` are pointers, and how many are the rank

Issue #274 named `cluster_name` as the citation form that survives a census
reshuffle, shipped `annotations/xdata-cluster-names.csv` and the tool that
resolves it, and said three times that switching the prose over was a later
sweep. This is that sweep, and the finding is the size of the opportunity
rather than the sweep itself. Of the prose occurrences that cite a cluster the
names file names, **the ones doing pointer work are a small minority**: the
rest name the rank as the subject of the sentence — a census figure, a
`cluster_key`, a comparison between two generations — and a name in that
position is not a more durable citation, it is a sentence that no longer
parses. §"What the citations actually are" below says how that call was made,
per occurrence, and §"What was left" says where the judgement was not mine to
make.

The tool that produced this is `ec/tools/census_cluster_citations.py`; it is
new, and so is `ec/tools/test_census_cluster_citations.py`. Nothing here opens
an EC image, reads a register, or ran on hardware. Every figure below is the
output of a command over committed text.

## What the issue claimed, and what this tree holds

Issue #435 as filed carried a per-file table of citations to re-point. Measured
on this tree with the tool rather than taken from the table:

    $ python3 ec/tools/census_cluster_citations.py

The seven files it scopes to carry the `main-ec-NNN` form in every one of the
five classes below, and the occurrences naming a cluster the names file carries
are a minority of them. The class breakdown belongs to the command above, which
prints it on every run, rather than to a number kept here: any merge that
touches a `main-ec-NNN` moves it. Two of the issue's figures do not survive the
measurement, and both mattered:

- Its count of the named clusters is `xdata-cluster-names.csv`'s *line* count,
  which includes the header row. The issue built its sweep on that; the data
  rows are what a sweep has to walk.
- It reports **87 of 97** citations as membership claims about those clusters.
  The measurement runs the other way: there are more citations here than the
  issue counted, and — this is the part that matters — fewer of them are the
  pointers the sweep is for. §"What the citations actually are" below is what
  the issue's figure should have been measuring.

Its ordering argument also does not hold. It asks for this **before** the
committed census is regenerated, on the grounds that a fresh run moves at least
eight of the named clusters and breaks the citations when it lands. There is
nothing pending to land:

    $ python3 ec/tools/xdata_register_map.py --check
    ec/annotations/xdata-registers.csv: 1326 rows match a fresh generation from the committed tree at threshold 0.5
    ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5

The tree already carries the post-move ids. What remains true is the durable
hazard the sweep exists for, and this write-up does not claim the hazard has
gone away — only that re-pointing prose does not remove it.

The issue's Done criterion is also not reachable as written: a
`grep -ro "main-ec-[0-9]\{3\}"` over `ec/`, `docs/` and `evidence/` cannot
return only historical ids, because the two census CSVs hold the form as a data
column and the tools hold it in code and in fixtures. What this change actually
makes is narrower, and §"What is deliberately given up" says so.

## The five classes

The tool walks the markdown and files every `main-ec-NNN` under one of five
classes, each decided from the text, tested most specific first. The classes
exist because the five want opposite treatment and only one of them is a live
pointer.

| class | what it is | what a sweep does with it |
|---|---|---|
| `template` | the literal `main-ec-NNN`, three `N`s | nothing: it names the form |
| `fenced` | inside a paired fenced block | nothing: it is pasted output from a run the reader cannot open |
| `census-row` | a table row whose first cell is exactly one id | nothing, and it is not a style preference — see below |
| `quoted` | a blockquote line | nothing: a correction or a quote is the record |
| `prose` | running text | the only candidate, and not all of it |

`census-row` is the one that bites. `check_cluster_citations.py` reads a census
row **only** when the first cell is exactly one `main-ec-NNN`, and it holds that
row's size, reference count, address range and named count against
`xdata-clusters.csv`. Rewrite a first cell to a name and the row stops being a
census row entirely: the figures go unchecked and nothing anywhere reports it.
That is a coverage loss, and it is why the tool has a class for it rather than
leaving it to a reader to notice.

## What the citations actually are

Of the `prose` occurrences, the ones that are *pointers* — a reader following
the id into the census to find a membership — are a small minority. The rest
name the rank as the subject: `main-ec-003` **is** 4,966 references,
`main-ec-002` **is** `kefb63d82f8c7` on `main-ec-002`, the row **is** 43
addresses, `main-ec-003` **went** from 43 addresses to 44 in that generation.
A `cluster_name` in those positions reads as nonsense, because the claim being
made is about the number and not about the membership the number happens to
label.

This is not decidable by a predicate over the text, and the tool does not
pretend otherwise: it prints the class, and for every occurrence of a named
cluster it prints the name the id could carry and the `note` the names file
records for it — that note being the reason the name is that name, in the same
way `ghidra-functions.csv` makes an `evidence` column mandatory. The decision
is recorded below, per citation, so a reader can check it rather than take it.

## What was re-pointed

These are the occurrences that were doing pointer work, each a sentence whose
id names a cluster to go and look up. Each carries the names file's own reason
for the name it now reads as.

| where | was | now | why it is a pointer |
|---|---|---|---|
| `ec/README.md` | `main-ec-003` | `counter-sweep` | a cross-reference telling a reader which cluster the linked page read |
| `ec/annotations/xdata-086x-dispatch.md` | `main-ec-004` | `level-block-086x` | the page's own subject line, naming the run it answers for |
| `ec/annotations/manual-fan-ctrl-0751.md` | `main-ec-013` | `user-clear-bytes` | "the remaining four members of the … cluster", a pointer to a membership |
| `ec/annotations/xdata-06c2-06db-timers.md` | `main-ec-003` | `counter-sweep` | "`0x06C6` and `0x06CD` are not in …", a membership claim |
| `ec/annotations/xdata-register-map.md` | `main-ec-002` | `mode-oem-init` | the opening sentence of the paragraph that reads the cluster |
| `ec/annotations/xdata-register-map.md` | `main-ec-003` | `counter-sweep` | "nine of the ten are in …", a membership claim |
| `docs/findings.md` | `main-ec-128`, `main-ec-214` | `countdown-06c6`, `countdown-06cd` | the trailing-list split; see the note on it below |

Some of these are worth their own line.

**The `docs/findings.md` one is a trailing list**, the shape
`check_cluster_citations.py`'s docstring names as *not* pairing: the ids come
first and the addresses follow in parentheses, so `pairings()` pairs nothing
and the claim is held to by the weaker "a wrong id at all" rule either way.
Converting it loses no checking, and the names make the sentence self-describing
— `countdown-06c6` and `countdown-06cd` are the memberships of `0x06C6` and
`0x06CD`, which the parentheses then repeat.

**The `manual-fan-ctrl-0751.md` one sits directly above the correction block
that records which id that cluster is**, and stays an id. That is the
distinction the issue asks for and it is visible in the diff: the running
prose takes the name, the dated correction keeps the rank it was written
against. A correction is the record of what an id was said to be and when;
rewriting it destroys the only evidence that the id moved.

**The `xdata-086x-dispatch.md` one changed a quote.** `xdata-cluster-names.csv`
justified `level-block-086x` by quoting that file's opening sentence — but as it
read when the name was assigned, which is not how it read immediately before
this sweep. The quoted id is `main-ec-003`; #683 moved that same sentence to
`main-ec-004`, and `main-ec-004` is the sentence this change re-pointed. The
note now records the quote as the pre-#683 reading it was evidence for, #683's
move, and which sentence issue #435 re-pointed, leaving the original wording
visible — the §4a pattern applied to an evidence column rather than to a §4
figure. It is the only edit to a structured source of truth in this change.

## What was left, and which class decided it

Everything else in the seven files stays an id, and the class says why:

- **`census-row`** — every one keeps `main-ec-NNN` in its first cell, for the
  coverage reason above.
- **`quoted`** — every correction and quote block, byte-identical. This includes
  ids that a reader might reasonably call live pointers, such as `main-ec-292`
  inside the 2026-09-24 correction in `manual-fan-ctrl-0751.md`; the block's
  job is to say which id that was, and a name there answers a different
  question.
- **`fenced`** and **`template`** — not citations at all.
- **`prose`** — the rank as the subject, as above.

## What is deliberately given up

**One split sentence keeps its ids on purpose.** `xdata-06c2-06db-timers.md` §5
reads "`0x06C6` in `main-ec-128` and `0x06CD` in `main-ec-214`", and that is
the shape `pairings()` *does* read: a preposition joins each address to its id
and nothing else does, so the sentence is held to the split rather than to
either id. `pairings()` reads the `main-ec-NNN` token only — the preposition is
what makes a split a claim — so a name in either position falls back to the
weaker any-of rule and the two can be exchanged without anything noticing.
Trading a checked claim for a durable handle is the wrong trade, so the
sentence stays as it is. That is the place the sweep deliberately did not go,
and it is worth noting that the same split, written the other way round, *is*
in the converted set: the two spell one claim in the two shapes the gate
treats differently, and only one of them can afford a name.

**The `gpu-tgp-07c4-07d7-door.md` table is not swept at all**, which is a
departure from the issue's expectation and is worth being explicit about. Its
cells read `` `xdata-registers.csv`: `main-ec`, `main-ec-002`, no
`[writer]`-tagged site in the row `` — that is the `program` column and the
`cluster_id` column quoted verbatim, not a pointer into the census. Replacing
the id with `mode-oem-init` would make the page assert that the CSV's
`cluster_id` column contains `mode-oem-init`, which is false, in the one column
whose stated contract is to agree with the CSV. The issue lists those cells
among the citations to convert; they are quotations of a data column, the same
shape it correctly excludes for `xdata-clusters.csv` itself.

**A name becomes a citation only where the sentence also carries a membership
cue.** `check_cluster_citations.py` needs `clustering`, `cluster`, `members` or
`membering` in the unit before it checks anything, so a name in a sentence
without one resolves and is then skipped. The gate's closing line tallies what
it passed over, by reason, on every run, and over these seven files most of the
units that cite a cluster are passed over rather than checked. That is the real
ceiling on what converting prose buys: most of what this sweep makes durable
was never checked in the first place.

**Names match case-sensitively.** `name_re()` builds a word-bounded alternation
from the census's own names, so a page writing `Counter-Sweep` passes unchecked
rather than failing. `cluster_name_shape.py` holds the *shape* of a name and
catches a name that collides with an address, a function or a symbol; it cannot
catch a prose misspelling of one, and it does not read the corpus.

## The gate fix this change had to bring with it

Adding a write-up to this directory turned `check_cluster_citations.py` red,
and the cause is worth writing down because the gate had been passing for a
reason that was not a check.

`units()` splits a paragraph into sentences at a terminator followed by
something that starts a new sentence, so it separated list items only where an
entry happened to **end in a full stop**. `docs/findings/INDEX.md` is a
generated list of link titles and none of them ends in punctuation, so the
index arrived as units spanning many entries, attributed to the first entry's
line. Whether such a unit was checked at all came down to whether the word
`cluster` appeared anywhere in it: this write-up's title says "cluster", the
membership cue arrived, and the rule then held the addresses of unrelated
entries to a cluster named in a fifth.

`units()` now treats a list item as a unit boundary the way it already treats a
table row — one part of the item means something different from the next, so
one item's cluster id must not answer for the next item's addresses. An item's
wrapped continuation lines still join it, so a claim written across two lines
is still one paragraph and is still split into sentences, and a blockquoted
list is left alone because a correction is one quoted passage.

The measured effect, over the tree with this write-up in it, is that the index
is judged entry by entry and **no entry in it is a membership claim**: entries
name a cluster, and entries carry addresses, but none does both, so the file is
passed over rather than held to a cluster named in an unrelated entry. What the
old boundary checked there was the false positive this change removes — remove
this write-up's row from `docs/findings/INDEX.md` and the old boundary is green
over the same tree again. The same run is what says the fix costs no coverage:
measured per file, the checked citations are the same set everywhere except in
that one file. The suite pins both halves of the new boundary beside the one
already pinning list boundaries — adjacent entries do not bleed, and a wrapped
entry stays one paragraph.

**What this fix is not.** It is a boundary, not a new rule: it changes which
unit an id is judged in and nothing about what the rule then demands. It found
no disagreement in the corpus, and it was not looking for one.

## The residue, and how a follow-up measures it

The seven files were the issue's scope. The rest of the tree is not swept, and
most of it should not be: `docs/findings/*.md` write-ups are largely *about*
rank movement, so their ids are the record under the same rule the correction
blocks are. The tool is what makes that judgement checkable rather than a
judgement:

    $ python3 ec/tools/census_cluster_citations.py --all

That prints the same five classes over every committed `.md` under `ec/`,
`docs/` and `evidence/`, rolled up per directory. A residue issue cannot be
scoped without it: the judgement "is this id the record or a pointer" is the
one §"What the citations actually are" makes per occurrence, and doing that by
hand over `docs/findings/*.md` is the whole cost the tool removes. It exits 0
with findings in hand, like `census_evidence_citations.py`: a count of
occurrences is a value every merge that touches a `main-ec-NNN` moves, so the
breakdown is left to the command rather than asserted here.

## What this does not say

No negative printed by the tool is "absent": an occurrence it does not list is
one not found by this walk over the files named on the command line. A name
resolving today is not evidence that the sentence beside it is right — whether
a name was carried by an identical key or by a 0.51 Jaccard is
`xdata_register_map.py --map`'s to report, and a name that resolves is a
membership the census has, not a sentence the census has read. Nothing here
was measured on the machine: no register was read back, and per `CLAUDE.md` a
register write being accepted would not be evidence the EC acts on it anyway.
