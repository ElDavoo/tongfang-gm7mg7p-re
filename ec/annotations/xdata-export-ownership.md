# Export ownership: one routine, exported 42 ways

`xdata-06c2-06db-timers.md` §2 established that `bank1:0x8001`-`0x8189` is one
393-byte routine that the call-target scan exported 42 times, 16 of them a
single instruction, every one of their `.c` files decompiling that same routine
rather than its own bytes. It left the consequence unmeasured: §2a recorded the
size of the effect and §8 item 5 kept the open question. This page is that
measurement — which routine each decompiled `.c` actually decompiles — and it
is deliberately **not** the fix. The fix is the function boundary, and it needs
`--mode rebuild-project` and a 7 MB database write that cannot share a branch
(§8 item 7).

The tool is `ec/tools/export_ownership.py`; its committed output is
`xdata-export-ownership.csv`; `xdata_register_map.py` reads it behind
`--export-ownership`.

## 1. The mechanism

`scan()` walks `ec/decompiled/index.csv` one row at a time and adds
`entry["refs"] += 1` per address token per file. An `index.csv` row is an
*export*, not a routine, and the exporter cut one routine into 42 of them, so
the walk visits the same body 42 times:

| | reads | functions touching it |
|---|---:|---:|
| `0x0843` as the committed census has it | 168 | 42 |
| `0x0843` as the routine is read | 4 | 1 |
| `0x0844` as the committed census has it | 168 | 42 |
| `0x06D6` as the committed census has it | 148 | 37 |
| `0x0706` as the committed census has it | 160 | 40 |
| `0x08A8` as the committed census has it | 170 | 44 (42 of them in this run) |

`0x08A8` is the one row of that table whose touchers are not all in the run:
`bank0:0xA139=FUN_CODE_a139` and `bank0:0xA1A8=set_state_bytes_then_0xa1c8`
touch it too, which is why its `functions_touched` is 44 while the four rows
above it read 42, 42, 37 and 40. The figures are the `functions_touched` column
of `xdata-registers.csv`, which is the whole column, not the part of it the
42-file run accounts for.

This is why the `refs` column of `xdata-registers.csv` and `xdata-clusters.csv`
is an **upper bound on distinct references** rather than a count of them, and
why one 393-byte routine holds about a third of the census's 14,819 references.
Clusters rank by size, then references, then address
(`xdata_register_map.py:150`), so the inflation is not a column nobody reads —
it is the sort key of the whole worklist. §2a of the timers page drew the
consequence for the ten busiest addresses; this page puts a number on the
mechanism and a tool behind the number.

## 2. Two readings of "attribute a reference to the routine", and only one of
them is the defect

The issue's wording admits two readings, and they are not close. Both are
measured here with the committed tools; Reading A is 25 lines over the same
text `scan()` already reads, and is re-derivable from the table in §5.

| reading | total `refs` | the 43 addresses of `main-ec-002` | addresses whose `refs` move |
|---|---:|---:|---:|
| **A** — read all 42 files, re-point each reference's *function key* to the owning routine | 14,819 → **14,819** | 4,988 → **4,988** | **0 of 1,171** |
| **B** — read the routine once, from its owner export | 14,819 → **9,401** | 4,988 → **460** | **228 of 1,171** |

Reading A fixes the incidence matrix's function axis — `0x0843`'s touchers go
42 → 1, which is the "42×" the README bullet calls an upper bound — and **moves
not one `refs` total**, so it does not touch the symptom the issue is about:
the 42-fold `refs` inflation, the size→refs→address ranking, the 4,642-of-4,988
figure. Reading B is the only one under which the reported defect changes, so
`--export-ownership` implements B.

## 3. The detector, and the three choices in it

**Normalisation.** Strip the plate comment (the `//` banner and the `/* … */`
annotation block) and the signature — both are this repository's text, and the
signature differs between two exports of one body purely by parameter naming.
What is left between the outermost braces is split on `;` and each statement
whitespace-collapsed. The first `{` and last `}` are taken rather than matched,
because a body can carry a brace inside a character literal.

**Containment.** Two files in the same program are related when
`|A ∩ B| / |A| ≥ 0.90` with `A` the smaller body. This is directed, not
Jaccard: the question is whether *this* file's statements are the larger
body's, and a large body that is mostly another routine must not be penalised
for it. Jaccard would score the fragment-in-big case 2/5 and refuse to fold it,
which is the whole 42-file class.

**Classes and owners.** Classes are the *connected components* of that
relation, and each has one owner: its largest body, ties by the lowest
`index.csv` address. The component is the unit rather than each file's nearest
container because the nearest container fragments the 42-file class into a
chain of a dozen pairwise classes — every one of which still has to be read, so
the inflation survives the "fix" untouched. On this tree the 42-file class's
owner is **`bank1/8001.c`**, the run's own start address, which is what keeps
every `bank1:0x8001` citation in the tree true.

`--fold-equal` is the one other grouping measured — bodies that are exactly
equal, which strict containment cannot group because neither is strictly
larger. The committed map is the strict-subset derivation.

### The body floor, which is the load-bearing choice

At 0.90 a **one-statement** body is contained by any larger body that happens
to spell that one statement, and 1,276 of the tree's 2,714 bodies are two
statements or fewer — 495 of them a single statement, of which 427 name
`return` and 112 are exactly `return`. Unguarded, those fragments chain a
whole program together. Every cell below is at the committed 0.90, so the
three columns are one detector rather than two:

| body floor | containment classes | classes holding together only through a chain | largest class |
|---:|---:|---:|---:|
| 1 | 28 | 13 | **562** |
| 3 (committed) | 56 | 7 | 42 |

The floor-1 flood is not a slightly-wrong count. It is 562 `bank1` files, 155
of them the fragments above, and its two largest members — 78 and 67
statements — have a containment score of **1.5%** of the smaller: the score is
`|A ∩ B| / |A|` with `A` the smaller body, not a share of the larger, which is
the directed measure the **Containment** choice above defines. Folding that
class would silently drop 561 routines out of the census. Take the 155
fragments out of it first and what is left is 407 members in 17 classes whose
largest is 42 — the real 42-class, and the only structure underneath the flood.
The 42-class is unchanged by the floor; the floor exists to stop everything
*else* being dragged into it. `--self-test` re-derives every figure in the
table, so the cost is a measurement rather than a claim.

### Containment does not compose, so a member can be reachable only by a chain

A inside B and B inside C does not make A inside C once the relation is
*thresholded* rather than exact. Seven classes on this tree rest on such a
chain. The `containment` column is each member's own score **against its
owner**, so a member that is 0.43 similar to the 14-statement body it is
grouped with is visible in the committed CSV rather than hidden by the
grouping; 29 of the 146 non-owners are below the threshold for this reason.
`--self-test` reports the count, because a class that is a hypothesis about one
routine exported several times should be checkable without re-deriving the
grouping.

## 4. What the committed tool measures on this tree

`xdata-export-ownership.csv`, 2,714 rows — one per `index.csv` row — and
`--check` holds it to a fresh derivation:

| | |
|---|---:|
| containment classes | 56 |
| non-owner rows (`shared=yes`) | 146 |
| largest class | 42, owned by `bank1/8001.c` |
| bodies too short to compare | 1,276 |
| non-owners reaching their owner only by a chain | 29 |

And what the pass does to the census, measured with
`xdata_register_map.py --export-ownership --out-registers … --out-clusters …`:

| | default | `--export-ownership` |
|---|---:|---:|
| distinct addresses | 1,171 | 1,171 |
| total `refs` | 14,819 | **9,401** |
| main-EC `refs` | 13,961 | 8,543 |
| `read` | 8,341 | 4,920 |
| `write` | 3,195 | 2,707 |
| `read+write` | 2,482 | 1,018 |
| `passed-to-call` | 534 | 500 |
| `address-taken` | 267 | 256 |
| the 43 addresses of `main-ec-002` | 4,988 | 460 |
| `main-ec-002` cluster `refs` | 4,966 | 280 |
| clusters | 430 | 432 |
| addresses whose `refs` move | — | 228 |
| **addresses lost** | — | **0** |

The defect really is fixed by Reading B: `0x0843` and `0x0844` go 168 → 4 with
42 touchers → 1, `0x06D6` 148 → 4, `0x0706` 160 → 4, `0x08A8` 170 → 6.

### A correction to the plan stage's estimate, and why it happened

The plan stage measured this pass on a pre-tool detector and reported **9,112**
references with **0x05E0 dropping out of the census entirely** (1,171 → 1,170),
on the reasoning that `bank1/8E91.c` — the only export in the tree that spells
`DAT_EXTMEM_05e0` — was a non-owner in its class. The committed tool measures
**9,401 with nothing lost**. The premise was right and the grouping was not:
`8E91.c` owns its own two-file class, so the one file carrying 0x05E0 is read
and the address survives.

That difference is the point of committing the rule. "This pass loses an
address" was never a property of export ownership; it was a property of one
grouping, and a detector whose membership is a text heuristic is free to
produce a different one. The `lost` set is pinned in `xdata_register_map.py`'s
`OWNERSHIP` oracle precisely so that if a re-export ever does make it non-empty,
the failure is a failing check rather than a quietly short census.

## 5. Why the default does not flip

The pass ships measured and switchable; the default is unchanged, and that is
the calibrated answer rather than a cautious one. Measured on this tree, the
flip:

- moves `cluster_key` on **35 of the 430** clusters (395 survive; 37 keys are
  new),
- breaks **5 of the 10** hand names in `xdata-cluster-names.csv` — including
  `counter-sweep` (`k733222e83898`), which is `main-ec-002`'s own key and does
  not survive as a single cluster at all,
- takes `main-ec-002`'s `refs` from 4,966 to 280 and adds **2** clusters
  (430 → 432).

A tree-wide renumbering is not a diff, and every `cluster_key` citation in the
tree is keyed to a membership. Landing it on top of a detector that is a text
heuristic — with seven classes resting on a chain, and a floor that exists to
stop `return` from merging unrelated routines — would publish the
approximation as the census. The flip is its own PR, after the boundary fix.

Both halves of the before/after stay re-derivable forever:

```
python3 ec/tools/xdata_register_map.py --out-registers /tmp/before-registers.csv \
    --out-clusters /tmp/before-clusters.csv
python3 ec/tools/xdata_register_map.py --export-ownership \
    --out-registers /tmp/after-registers.csv --out-clusters /tmp/after-clusters.csv
```

`--export-ownership` is refused with `--check` and `--self-test`, and refused
without scratch `--out-registers`/`--out-clusters`, on the same two grounds as
`--no-eq-guard`: both are gates about the committed CSVs, and a flag that
re-buckets occurrences while writing nothing must not be answerable from a mode
whose claim is that the files already match.

## 6. What this does not establish

- **It is not a function boundary.** The root cause is that the exporter cut
  one routine into 42 functions, and only a project rebuild fixes that. This
  pass infers ownership from how two files' decompiled text compares; it never
  reads the `.asm`, the byte ranges, or a call graph.
- **It is a text heuristic, and its count depends on the choices.** The issue's
  159 was an ad-hoc containment scan at a "≥90% line threshold", and the plan
  stage's independent re-derivation of the same idea put the same figure at 144
  non-owner rows in 64 classes (strict subsets) and 233 in 74 (grouping equal
  bodies) — 159 sits between those and neither reproduces it. The committed
  tool's own 146 in 56 replaces all three rather than reconciling them. The
  spread is itself the finding: a threshold over statement text does not have
  one correct answer.
- **A fold is not proof of identity.** Two genuinely distinct routines can
  share most of their statements, and one routine split across exports can be
  missed where the decompiler re-spelled a line. The `containment` column is
  the per-row evidence and a reader is expected to look at it.
- **The `refs` figures are not behavioural claims.** A count of references in
  decompiled text is evidence about static shape, never about what the EC does
  with a byte. A `write` count is not evidence the EC acts on the value, and a
  zero is "not found by this method", never "absent" (`docs/findings.md` §4c).
- **Nothing here needed hardware or Windows.** The whole page is a property of
  committed text files, re-derivable by re-running the tool. No live
  observation is claimed, and none is needed to check any of it.
- **The boundary fix is out of scope here**, and this PR does not close it:
  §8 item 7 of the timers page remains open, and this page is the measurement
  that fix is argued from.
