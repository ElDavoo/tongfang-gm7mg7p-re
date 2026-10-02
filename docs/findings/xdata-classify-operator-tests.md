# `classify()`'s two operator tests: `&&` is not address-of, and `&=` reads what it writes

**Issue #424, 2026-10-02.** `ec/tools/xdata_register_map.py`'s `classify()`
tested whether the text before an address token ends in `&`, and tested it
before `store_target()`, so the second `&` of a boolean `&&` filed a plain
comparison under `address-taken`. One clause fixes it. The same mistake one
level down — `read+write` was decided by whether the right-hand side of the `=`
names the address, and `&=` compresses the self-reference out of the
right-hand side — is a second clause. Each is one line, both are in the same
function, and both have a literal shape added to `CLASSIFIER_SHAPE` so the fix
survives a tree that no longer contains the shape.

**Nothing here is a finding about the EC.** No register's `status:` moved, no
register was read back, no hardware or Windows machine was involved, and no
decompiled file changed — this is how committed text is *classified*, and the
two addresses it moves a label on (`0x076A`, and `0x0026` below) are untouched
as facts about the machine. `0x076A` keeps its real store and both of its
references; nothing is removed from the corpus.

The issue asked for the compound-assignment reasoning to land in
`docs/findings.md`. That file is frozen to new sections by
`check_findings_frozen.py`, so the reasoning lands here instead — the same
requirement at the only destination the repository's rules allow. This is a
deliberate deviation from the issue's wording.

## The two fixes, and what each one moves

**1. `&&` is not address-of.** `classify()` asked only `left.endswith("&")`,
before it reached the store rule. In

```c
if (DAT_EXTMEM_076b == '\0' && (DAT_EXTMEM_0769 == '\0' && DAT_EXTMEM_076a == '\0')) {
```

the `DAT_EXTMEM_076a` token is preceded by the **second** `&` of a `&&`, so a
comparison was filed `address-taken`. The fix is `left.endswith("&") and not
left.endswith("&&")`. One reference moves from `address-taken` to `read`; no
other bucket moves.

The site is `bank0/A747.c` and it is the `&&` test, not the store — `grep -n
'DAT_EXTMEM_076a'` over that file returns the `&&` line and the
`DAT_EXTMEM_076a = DAT_EXTMEM_076d;` store below it, in that order. §4.3's
correction block in `ec/annotations/xdata-register-map.md` records the line-number
history and is cited here by file and content rather than by a bare `:NNN`,
because #432's re-export moved both lines and the pre-#432 numbers are what the
issue quoted.

**2. A compound assignment is a read-modify-write by definition.** `read+write`
was decided syntactically — "the right-hand side of the `=` names this
address" — and `DAT_EXTMEM_0440 &= 0x0f;` compresses the self-reference into the
operator, so the right-hand side is `0x0f` and the occurrence read as a plain
`write`. It now reads `read+write`, tested from `ASSIGN` rather than from a
second list of operators so the two cannot drift apart.

## The measurements, re-derived rather than copied

Every figure below was measured on the tree this change lands on, walking the
committed `.c` files with the tool's own `strip_comments()` and
`occurrence_re()`. The issue's own figures are stale and are not carried into
the diff: it says the fix moves `271 / 8,319 → 270 / 8,320`, which is the
superseded §4.1 row that `xdata-register-map.md`'s drift record preserves. The
committed cells before this change were `267 / 8,826`.

**The `&`-population, 267 / 1 / 266.** Of the 267 occurrences whose preceding
text ends in `&` — the whole `address-taken` bucket — exactly **one** is
preceded by `&&`, and the other **266** are a genuine `= &` (253), a cast to
pointer followed by `&` (9), or the four binary-`&` sites named below. Reproduce
with the tool's own readers:

```python
import os, sys; sys.path.insert(0, "ec/tools")
import xdata_register_map as M
_, by_file = M.load_index(); pattern = M.occurrence_re(M.load_symbols())
amp = []
for f in by_file:
    t = M.strip_comments(open(os.path.join(M.DECOMPILED, f)).read())
    amp += [t[:m.start()].rstrip() for m in pattern.finditer(t)
            if t[:m.start()].rstrip().endswith("&")]
print(len(amp), sum(l.endswith("&&") for l in amp),
      sum(not l.endswith("&&") for l in amp))   # 267 1 266
```

**Compound assignments after an address token: zero.** Over the same walk, no
member of `ASSIGN` other than `=` follows a `DAT_EXTMEM_xxxx` or symbol token
anywhere in the committed tree, in either spelling. So fix 2 costs no bucket
today: the two `CLASSIFIER_SHAPE` literals move from pinning a *known
misclassification* to pinning the *right* one, and the reason is not a defect in
this tree. That is a statement about this tree by this method — if a future
export emits `&=`, the literal still holds it, and the census would then count
the read half. It is not a claim that no export can spell one.

**The counterfactual, 837 → 838 and 210 → 211.** The module docstring's
present-tense claim is that re-introducing the pre-fix classifier makes the two
code paths disagree on N occurrences across M distinct addresses. Before this
change that reproduced at 837 / 210; it now reproduces at **838 / 211**, because
the one `==` site that was `address-taken` rather than `read` is itself
corrected, so it disagrees like the other 837 rather than being the exception to
them. Measured by running `classify()` over the same walk twice, once with the
guard on and once with it off:

```python
for m in pattern.finditer(t):
    g = M.classify(t, m.start(), m.end(), m.group(0), fn, True)
    n = M.classify(t, m.start(), m.end(), m.group(0), fn, False)
```

`--no-eq-guard` is refused without scratch outputs, and that refusal is itself
under test, so the CLI form of this recipe needs a temporary directory and never
the committed CSV paths: pass `--out-registers` and `--out-clusters` into one.
Note that the refusal covers the *default* case only — passing the committed
paths explicitly is accepted and overwrites them, which is worth knowing before
running it by hand.

## What moved, and what did not

| | before | after |
|---|---:|---:|
| `BUCKET_TOTALS` `read` | 8,826 | **8,827** |
| `BUCKET_TOTALS` `address-taken` | 267 | **266** |
| `OWNERSHIP["buckets"]` `read` | 5,361 | **5,362** |
| `OWNERSHIP["buckets"]` `address-taken` | 256 | **255** |
| `refs` / total | 15,696 | 15,696 |

Under `--no-eq-guard` — the guard-off run that §6a publishes — the same
reference moves the other way, because the corrected site is a comparison that
the guard-off classifier files as a store: references entering `write` 833 →
834, addresses whose `write` column changes 210 → 211, main-EC `write` 3,948 →
3,949 and main-EC `read` 7,935 → 7,936. Addresses whose `refs` column changes
stays 0, which is the figure that says the guard moves references between
direction buckets and out of none of them.

The issue misses the `OWNERSHIP` pair: `--export-ownership` re-reads the same
occurrences from each routine's owning export, and `bank0/A747.c` is not one of
the 42 `shared` counter-sweep exports, so the same reference moves in that
census too. `--self-test` asserts both pins, so a change that re-pinned only
`BUCKET_TOTALS` would leave it red twice over.

Unmoved, each verified rather than assumed: `DIRECTION_INVARIANT` in every key
(`write_like` counts only `write` and `read+write`, and the site is in neither
before or after; `eq_after` is 838 either way); every `ORACLE` key, because
membership and count do not change; `HAND_CHECKED`, none of whose five
addresses is `0x076A`; `NOT_IN_TREE`; and `xdata-clusters.csv`, which carries no
direction column and whose writer-axis Jaccard for `main-ec-035` does not move
because `0x076A` had a writer before this change. The clusters CSV was
regenerated and is byte-identical; if a future change to this classifier makes
it differ, that is a finding to report rather than a diff to accept quietly.

**The `0x076A` row before and after**, so the fix is not read as removing an
address from the corpus:

| | `refs` | `read` | `write` | `address-taken` | `readers` | `writers` |
|---|---:|---:|---:|---:|---:|---:|
| before | 2 | 0 | 1 | 1 | 0 | 1 |
| after | 2 | 1 | 1 | 0 | 1 | 1 |

`cluster_id` `main-ec-035`, `cluster_key`, `write` and `writers` are unchanged.
The row simply acquires the first reader its two siblings at `0x0769` and
`0x076B` already had, and `0x076A`'s own store is untouched.

## The residual this change does not fix — and it is not hypothetical

The `&` test is still one character deep. A **binary** `&` immediately before an
address — `x & DAT_EXTMEM_0026` — satisfies it just as `&&` did, and that
occurrence is an ordinary read.

The plan for this issue recorded the residual as latent, on the grounds that
none of the 267 `&`-preceded occurrences was a binary `&`. **That is wrong, and
the measurement below is what corrected it.** There are **four**, all of
`DAT_EXTMEM_0026`, all reads, all currently filed `address-taken`:

| site | line |
|---|---|
| `common/223F.c` | 146 |
| `common/2275.c` | 119 |
| `common/2290.c` | 85 |
| `common/22EF.c` | 79 |

Each is `DAT_INTMEM_65 = bVar5 & DAT_EXTMEM_0026;`. The four are separate
`common` exports, each its own owner in `xdata-export-ownership.csv` and none a
`shared` copy, so all four are counted in the default census *and* in the
`--export-ownership` one. `0x0026` therefore carries two misbucketed reads
today, one per census.

Finding this is not a reason to fix it here. The `&&` fix is one clause and this
is a wider one — distinguishing `&x` from `x & y` needs the token *after* the
address, not just the text before it, which is a second predicate and a third
shape to pin. It also moves two cells in each of two censuses and needs its own
re-derivation, so it is follow-up work, named here and in
`ec/annotations/xdata-register-map.md` §6's bullet rather than folded silently
into a change about `&&`.

## Figures elsewhere that this change makes stale

**Four pages had to be edited, not listed, because a suite holds each of them
to the run.** `test_xdata_guard_off_row_join.py`, `test_xdata_cluster_names.py`,
`test_xdata_program_keyed_table.py` and `test_check_doc_figure_pins.py` all
compare a *published* figure against a fresh regeneration — the last by way of
the §2b verdict column of `xdata-census-rederivation-checklist.md` — so leaving
a page stale leaves the suite red rather than merely out of date. Their
edits are figure corrections in place, and the tests' typed constants moved
with the pages they quote. That accounts for
`ec/annotations/xdata-06c2-06db-timers.md` (its §6a heredoc's four
figures, its main-EC `write`/`read` arms and its default/`--export-ownership`
table), `docs/findings/xdata-register-map-per-program-keying.md` (its console
transcript), and the two `§2a`/`§2b` tables of
`docs/findings/xdata-census-rederivation-checklist.md`. The checklist's own
§2b *quotation block*, which reproduces a superseded classification verbatim,
was left exactly as it is, per §4a-4d.

**These were left stale, deliberately.** The repository has already made this
call twice for the same figure — `docs/findings.md` §64 and
`xdata-per-program-counts.md` each found a stale page, left it, and wrote down
that they had — and two of these are console transcripts of runs on earlier
trees, which are falsified by editing rather than corrected by it. Each row is
a decision for a human, not a task this change owes.

| page | figure it now carries | re-derive with |
|---|---|---|
| `ec/annotations/xdata-export-ownership.md` | `read 8,826 / 5,361`, `address-taken 267 / 256` | `python3 ec/tools/xdata_register_map.py --export-ownership --out-registers … --out-clusters …` into scratch outputs |
| `docs/findings/xdata-per-program-counts.md` | a console transcript reading `8826 … address-taken 267` | the `awk -F,` reader its own block prints, or `--self-test` |
| `docs/findings/xdata-census-self-test-gate.md` | quotes the five-cell pin, and a `xdata_register_map.py` line that has itself moved | `--self-test` |
| `docs/findings/xdata-census-rederivation-checklist.md` §3 | names the five `BUCKET_TOTALS` values in prose and their sum | `--self-test` |
| `docs/findings.md` §64 | prints `read 8826 … address-taken 267` as what a past merge's write-up said | leave; it is a record |

Two further pages are stale in this way *today* and are listed for the same
reason, not because this change introduced it: `xdata-census-totals.md` carries
the `8341 / 3195 / 2,482 / 534 / 267` row (already superseded twice) and records
the `:24`→`:25` correction, and `xdata-write-direction-correction.md` quotes the
"837 references" figure. Both are snapshot pages whose own text says so.

## Calibration

- The two fixes are corrections to a *label*, not to a reading of the firmware.
  `0x076A` and `0x0443` keep their stores, their references and their
  `writers`; only the bucket one reference of each sits in is corrected.
- "Zero compound-assignment sites" is a finding of this method over this tree,
  not an assertion that the exporter cannot emit one.
- "Four binary-`&` sites" is the same kind of statement, in the other direction:
  four occurrences were found by this method, and the point of naming them is
  that the method *can* find them — so a later claim that no such site exists
  is a claim to re-measure, not to inherit.
- The historical 838/837 arithmetic in §4.3 is a true measurement of the `==`
  fix alone and is left standing, with a dated correction beside it rather than
  edited into it, per `CLAUDE.md`'s §4a-4d pattern.