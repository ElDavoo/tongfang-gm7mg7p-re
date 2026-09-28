# The most-cited-cluster count, and the claim that does not need one (issue #842)

Issue [#842](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/842) was
opened by the follow-up pass off #822. It named a numeral and the command that
numeral is supposed to come from. The mover-ordering comment in
`ec/tools/test_xdata_cluster_names.py`, added by #822, argues at length that
pinning a count into a file is the hazard the class's own docstring exists to
record — and then pastes a count into the same comment, quoting one `grep` and
two figures the `grep` does not return. The same pair sits at
`ec/annotations/xdata-register-map.md` §4.4, in the very sentence the comment
cites.

This file is the measurement, kept where a reader can re-run it, because the
comment and the correction only carry a pointer to it. **None of this is a live
test and none of it is evidence about the firmware.** No EC is opened, no
register is read back, no capture is taken, and no laptop, EC or Windows machine
is involved anywhere below. Every figure below is re-derivable from committed
inputs in this repository — a `grep`, a `git grep` over markdown, or a run of
one of the tools cited here. Neither census CSV, the names file, nor any
`registers.yaml` row was edited, and no `status:` moved.

## The three numeral sites

| site | what it said | what it is now |
|---|---|---|
| `ec/tools/test_xdata_cluster_names.py`, the comment on `test_and_the_tool_says_what_moved_about_it` | *"It is the most-cited cluster in the tree all the same … `grep -rl 'main-ec-003\b' --include=*.md .` naming nine files, against seven for `main-ec-002` — and the tenth is `xdata-cluster-names-guard-off-recipe.md` …"* | the clause is gone; the paragraph keeps the mover ordering and points at the transcript and at the census row |
| `ec/annotations/xdata-register-map.md` §4.4, inside the `*(Correction, 2026-09-25, issue #582's re-run …)*` block | *"… and it is the most-cited cluster in the tree (`grep -rl 'main-ec-003\b' --include=*.md .` names nine files, against seven for `main-ec-002`) …"* | **kept, unedited**, with a second dated `*(Correction, 2026-09-28, issue #842 …)*` paragraph directly beneath it |
| `ec/annotations/xdata-register-map.md` §4.4, immediately above that block | *"`main-ec-002` … is the cluster `mode-oem-init` names, cited by seven pages of the tree for a membership it holds."* | the same numeral, from the same measurement, in the same section, and **live prose** rather than a quoted correction — the page tally is dropped and the claim becomes the census row |

The third site was not in the issue's stated scope and is in the diff anyway.
Leaving it would have meant the new correction retracting a "seven" that the
same page still asserts four lines later, which is the incoherence the issue is
about reproduced one paragraph down.

## Why nine and seven cannot come from one file set

Measured at `2ed6f030^` — the commit #822 landed on top of — with `git grep`
over every `*.md` in the tree, so nothing depends on what this runner's working
copy happens to hold:

```console
$ git grep -lE 'main-ec-003\b' 2ed6f030^ -- '*.md' | wc -l      # 9
$ git grep -lE 'main-ec-002\b' 2ed6f030^ -- '*.md' | wc -l      # 8
$ git grep -lE 'main-ec-002\b' 2ed6f030^ -- '*.md' \
    | grep -v 'xdata-cluster-names-guard-off-recipe.md' | wc -l  # 7
```

Nine is the **whole** file set for `main-ec-003`, and seven is that file set for
`main-ec-002` **with the recipe page removed**. One quoted `grep`, two different
answers to "which files are in the set".

The asymmetry is the recipe page, and it is not a coincidence of the merge —
it is the direction each id travels in it:

- **`main-ec-003`** — the recipe page had never cited it. Its pre-merge text
  carries **0** occurrences (`2ed6f030^:docs/findings/xdata-cluster-names-guard-off-recipe.md`),
  so excluding the page moved nothing and the figure was 9 whether the page was
  in the set or not. #822's transcript row at `:261` is what added the tenth.
- **`main-ec-002`** — the recipe page had cited it since the file was written:
  **2** occurrences, at `:191` and `:200`, both pre-merge text. So the whole set
  was already 8, and 7 is only reachable by taking the page out.

So the comment's parenthetical — *"and the tenth is `…-guard-off-recipe.md`,
whose comparison transcript names `counter-sweep` on both sides, so the numeral
is that line's figure rather than a current one"* — accounts for the tenth of
the nine and says nothing about the eighth of the seven, in a clause whose own
subject is the file that moved the first one. On the tree the comment was
written against the `grep` gave **10 and 8**; the sentence in the tree gave
**9 and 7**.

## The two greps at the base, and once more since

```console
$ grep -rlE 'main-ec-003\b' --include=*.md . | wc -l    # 18
$ grep -rlE 'main-ec-002\b' --include=*.md . | wc -l    # 18
$ grep -ro 'main-ec-003\b' --include=*.md . | wc -l    # 141
$ grep -ro 'main-ec-002\b' --include=*.md . | wc -l    # 196
```

**These four figures are a dated measurement of one named tree state** —
`4e697871`, this change's base — and they are not a standing total to
be copied forward. Every one of them has already moved, and the superlative has
been false on one reading since the day it was written: at `2ed6f030^` the file
counts were 9 against 8 in `main-ec-003`'s favour, and the occurrence counts
were **76 against 93** the other way. The file counts have since tied at 18
each, so "the most-cited cluster in the tree" is now false on both readings.
That is why the clause is deleted rather than re-measured: a re-measurement is
another numeral the next write-up moves, which is the hazard the comment is
arguing against two paragraphs above it. The change you are reading adds
occurrences of both ids to the tree, so a re-run today gives a fifth and sixth
figure, and that is the point rather than a wrinkle in it.

*(Correction, 2026-09-28, at the merge with `main`: the four figures above are
`4e697871`'s and the tree now reads **`19` and `19` files, `158` and `210`
occurrences**. The tie is still the tie — the file counts are equal, and the
occurrence counts still favour `main-ec-002` by a wide margin — so the
superlative is false on both readings exactly as it was at the base, and the
clause is still deleted rather than re-measured. Only the numerals moved, which
is the paragraph's own point landing a second time: this is the fifth and sixth
figure the section has produced, a seventh would mean no more than the sixth
did, and the correction you are reading is itself inside the count it
re-meports.)*

The one thing this does **not** say is that no cluster is more cited than
another. It says the tree does not currently license the claim either way, and
that the claim was never about the thing the comment needs it for.

## The claim that survives without a count

The comment's actual argument is about **ordering**, and the ordering is not a
tally — it is a row in a table a run already printed, committed at
`xdata-cluster-names-guard-off-recipe.md:258-268`:

```console
    name             committed    guard-off    key      membership  rank
    counter-sweep    main-ec-003  main-ec-003  same     same        same
    …
  movers: 3 of 9 ['countdown-06c6', 'fan-step-08a0', 'flag-pair-0442']
```

`counter-sweep` reads `main-ec-003` in both columns with `same same same` — key,
membership and rank — while three of the nine named clusters moved rank with key
and membership intact. The exhibit the case fell back on is the one the ranking
happens to spare, and that is legible in the table without counting a single file.
This is what the comment now cites, and it does not move when a write-up
mentions an id.

What the cluster **is** is a question a file answers too, and the answer is
three committed facts rather than a grep:

| fact | where |
|---|---|
| `main-ec-003` carries `cluster_name=counter-sweep` at `cluster_key=k733222e83898`, 43 addresses | `ec/annotations/xdata-clusters.csv` |
| the name, and the evidence for it, is a hand-edited row | `ec/annotations/xdata-cluster-names.csv` |
| a page makes a membership claim about that block, and §1 sweeps exactly those 43 addresses | `ec/annotations/xdata-06c2-06db-timers.md` §1 — re-derived for this file: the command's 43 `0x…` arguments are the census row's 43 `addrs`, as sets, with no address on either side unaccounted for |

"A cluster the tree leans on" is what that is: a cluster with a committed name,
a committed key and a page that spends 43 addresses on it. None of the three
needs re-measuring.

## The pin surface, which the census's silence does not cover

`ec/tools/census_test_line_pins.py` reported **128 pins, 95 resolves, 0
out-of-range, 33 declined** on `origin/main` and on this branch alike, because
the retraction adds no `test_*.py:NNN` pin to the corpus. That delta being zero
is a fact about the corpus of pins, not about what those pins point at, and a
second tool reads the same surface and does render a verdict.

*(Correction, 2026-09-28, at the merge with `main`. The pair above is what
`4e697871` read, and `main` has since gained a write-up carrying a pin of its
own, so **the merged tree reads `129` pins, `96` resolves, `0` out-of-range,
`33` declined** — one pin and one resolve, and nothing else, against the
`4e697871` pair above. The `origin/main` half of "alike" is what the sentence
measured when written; it is not what that ref reads now. The retraction's own
contribution is unmoved, which is the only part of the sentence this correction
is about.)*

`ec/tools/check_pin_table_rows.py` reconciles
`docs/findings/test-line-pin-census.md`'s per-pin table against that same run
and exits non-zero on a row the run does not describe. The verdict it renders is
about the *table* describing the run — never about whether a pin carries its
claim, which stays a reading somebody looked at — and this change moved four of
its rows. Its class counts, over one table that is 128 rows at `4e697871` and
129 on the merged tree:

| | `origin/main` at `4e697871` | this branch, before re-deriving | after | the merged tree |
|---|---|---|---|---|
| placed | 127 | 125 | 127 | 127 |
| `unplaced-row` | 1 | 3 | 1 | 2 |
| `row-without-record` | 1 | 3 | 1 | 2 |
| `shape-differs` | 0 | 2 | 0 | 0 |

All four rows are this change's, and all four were re-derived from the merged
tree's own run so rows and records move together. Two of them are
`ec/annotations/xdata-register-map.md`'s own two rows, whose citing lines the
insert under `§4.4` moved — `:1340` → `:1362` and `:2665` → `:2687`, byte-identical
at both ends, so the table named the right sentences at the wrong addresses. The
other two are pins *into* `test_xdata_cluster_names.py` below the comment this
change edited, so the edit's own line shift changed the shape they land on
(`comment` ⇄ `other`) without either cited line number moving. The verdicts on
those two rows are marked as readings recorded before the shift and not re-read,
which is the table's own convention and not a new claim.

The merged tree's two extra `unplaced-row`/`row-without-record` pairs are
`main`'s and not this change's: the table names `0751-append-unchecked-marks.md:221`
against a record `main` moved to `:246` with 25 lines inserted above it, so the
write-up itself is older than the drift. **`shape-differs` stays `0` in the last
column, and that is the load-bearing cell**: it is the reconciler's own verdict
that the four re-derivations above still describe the run on the tree that
carries both sides' work, re-measured rather than assumed.

**The disagreements left are not this change's.** At `4e697871` there was one,
the `docs/agent-pipeline.md:409/410` pair: the table names `:409` against a
record the run reads at `:410`. It reproduces on a clean `origin/main` —
measured, not assumed — which is why the reconciler still exits 1 here and why
`ec/tools/test_check_pin_table_rows.py`'s `TheCommittedTree` is two failures red
on this branch, against a `main` that read two at this change's base and reads
three now. *(On the merged tree the reconciler names **two** pairs: the
`agent-pipeline.md:409/410` one above, and
`0751-append-unchecked-marks.md:221/246`, the second a line `main` shifted
rather than a row this change or that one added. `TheCommittedTree` is
therefore three failures red rather than two. Measured on each tree rather than
inferred — the branch reads two, `main` reads three — and neither pair is in a
region this change edits.)* `placed` is a re-derivation and not a lowering: the
rows that fail to place are the ones the tool names, and the other 127 are held
by the two assertions beside it.

## What was deliberately not done

- **No check on the number.** The issue forbids it and the argument forbids it
  twice over: pinning a tree-wide tally is the same hazard the comment is
  making. The assertion meant to survive a re-derivation stays the census-wide
  floor `assertGreater(len(moved), 300)` in
  `test_the_regeneration_really_moves_the_ranks`; the case under repair keeps
  `assertTrue(movers, …)`, which is what makes it a statement about the design
  rather than about a merge.
- **No re-pointing of the `test_xdata_cluster_names.py:NNN` line pins** the
  comment edit shifts. `ec/tools/census_test_line_pins.py` reports them and
  renders no verdict by design — whether a cited line still carries the claim it
  is cited for is a reading, and that is the pin census table's job. Re-pointing
  them is a different issue with its own write-up. **The census's silence is
  not every gate's:** a second tool reads the same surface, does render a
  verdict, and had to be answered — see the section above.
- **`docs/findings.md` is untouched.** It is frozen, `check_findings_frozen.py`
  holds its section count, and a summary section is the one edit a change is not
  allowed to make. This file and the regenerated `INDEX.md` are the whole of
  the registration.
- **No census CSV, names file, annotation CSV or `registers.yaml` edit.** Nothing
  here changes a key, a name, a membership or a `status:`, so
  `gen_xdata_symbols.py` has nothing to regenerate and no symbol rename can
  imply a `status:` change.
- **The 2026-09-25 correction block is kept as it is.** §4a-4d is the reason:
  the wrong figure stays visible with a correction beside it rather than being
  edited away. The new note is a `Correction`, not a `Superseded`, because
  `ec/tools/check_no_append_logs.py` holds the supersession marker out of every
  document outside `docs/findings/` — it is the shape, not the numeral, that
  makes a file an append log.
- **The `check_cluster_citations.py` red is not this change's.** Three
  disagreements pre-date it — two in `xdata-cluster-names-guard-off-recipe.md:220`,
  and one census-count disagreement on the `main-ec-002` row of
  `xdata-register-map.md`'s §5 worklist table — and none is in a region this
  change edits. Named by what it is rather than by a line number, because the
  insert below `§4.4` is exactly the kind of edit that moves one, and a
  locator that this very change invalidates is the failure this file is about.
  The before and after output is the same three, which is the claim worth
  making, since the rewrite keeps `main-ec-002`, `main-ec-003`, `mode-oem-init`
  and `counter-sweep` in running prose and the checker holds exactly those
  against `xdata-clusters.csv`.
