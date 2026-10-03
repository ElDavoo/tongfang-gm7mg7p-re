# The two `--export-ownership` census arms partition their references but not their addresses, so `pd_distinct` has no identity to assert (issue #918)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure is a count
over committed text (`ec/decompiled/**`, `ec/annotations/xdata-registers.csv`)
taken from the census tool's own flags, with the scratch outputs under `/tmp` and
nothing written into the tree. The change adds two comments, and the assertions
in [`xdata-guard-off-pd-cluster-count-pinned.md`](xdata-guard-off-pd-cluster-count-pinned.md)
beside them; it touches no CSV, no `registers.yaml` row and no `status:` value.

## The sentence

**§6b's two per-program figures — `main-ec: 1218 distinct addresses, 9320
references` and `pd: 157 distinct addresses, 858 references` — are not two halves
of one whole, and only one of the two columns can be checked for having
partitioned it.** The *reference* counts do partition: `9320 + 858` is the `10178`
the census-wide check already asserts. The *address* counts do not: `1218 + 157`
is `1375`, against the `1326` addresses the run wrote. The excess is `49`, and it
is not a rounding or a stale figure — it is exactly the number of `program=both`
rows, each of which is one address counted in both arms.

## Why a shared address lands in both arms

`merge_group()` sums over a group's programs, and `GROUPS` is `("main-ec", "pd")`
over `PROGRAM_COL = {"main-ec": ("common", "bank0", "bank1"), "pd": ("pd",)}`. An
address the two programs share is therefore keyed under that one address number
in *both* groups — `merge_group` keys by address, so the second program cannot
tell it has already seen the first. For **references** this is harmless and is in
fact the design: a `both` row's references are attributed by *source* program, so
the main-EC arm takes its `refs_main_ec` and the pd arm its `refs_pd` and each
reference is counted once across the two. For **addresses** there is nothing to
attribute — an address is either in the program or it is not, and this one is in
both.

Measured on a fresh run, `program` against the two per-program columns:

| | rows | `refs` | `refs_main_ec` | `refs_pd` |
|---|---|---|---|---|
| `main-ec` only | 1169 | 8914 | — | — |
| `pd` only | 108 | 603 | — | — |
| `both` | 49 | 661 | 406 | 255 |

which is where the arms come from: main-EC is `1169 + 49 = 1218` addresses and
`8914 + 406 = 9320` references, pd is `108 + 49 = 157` and `603 + 255 = 858`, and
the row count is `1169 + 108 + 49 = 1326`. The 49 shared addresses are counted
once per arm and once overall; the 661 references they carry are counted once
each in total and once per arm on the side that owns them.

**The references partition per address, not just in the column totals**, which is
the stronger of the two claims and the one that makes the column arithmetic safe:
for all 49 `both` rows, `refs == refs_main_ec + refs_pd` individually. A row that
double-counted on one side and lost a reference on the other could still make the
columns sum — this is the shape the committed census's own reconciliation check
(`xdata_register_map.py`'s "and the split partitions the census rather than
re-counting it") is built to catch on the committed side.

## What was checked, and what was deliberately not

The "and its pd half is" `check()` already compares **both** keys against the
in-process de-duplicated census, so `pd_distinct` and `pd_refs` are measurements
rather than constants nothing reads. Issue #918 also asked for the `pd_refs`
identity — `refs - main_refs == pd_refs`, which holds as `10178 - 9320 == 858` —
as a cheap check that the arms partition the after-census.

**That identity is already implied by the three checks beside it, so it is not
asserted.** The census-wide check compares `refs` against a total that *is*
`main_refs + pd_refs` by construction; the main-EC check compares `main_refs`
against the main arm; the pd check compares `pd_refs` against the pd arm. If all
three pass then `refs - main_refs == pd_refs` necessarily does, and a fourth
`check()` on the constants would fire only if someone edited the constant block
into a state two of the existing checks already reject — with a message that says
"the constant is wrong" rather than naming the census. It would be a check that
cannot fail for the reason it was written for.

The distinct side has no such identity to assert, and that is the finding rather
than a gap in the tree: a sum check over the distinct arms *cannot* hold, so
adding one "for symmetry" would be red on the committed tree. Both facts are now
recorded where a reader reaches for them — on the `pd_*` keys in `OWNERSHIP`,
beside the note that `pd_refs` has no companion identity, and on the "and its pd
half is" check, beside the reason the two columns differ.

## The perturbation transcript

Each key perturbed in turn, against a copy of the tool restored afterwards, so
these are a record of a run rather than an expectation the tree can reproduce:

```
$ python3 ec/tools/xdata_register_map.py --self-test      # "pd_distinct": 156
  FAIL  and its pd half is 156 distinct / 858 references, the other half of that line (got 157/858)

$ python3 ec/tools/xdata_register_map.py --self-test      # "pd_refs": 857
  FAIL  and its pd half is 157 distinct / 857 references, the other half of that line (got 157/858)
```

Both name the perturbed value, the measured one, and the line the pair is printed
on — the `  FAIL  <label>` shape `--self-test`'s own `check()` produces, which is
not the `AssertionError:` shape the transcript in
[`xdata-6a-direction-rows-pinned.md`](xdata-6a-direction-rows-pinned.md) records.
A bare `157 != 156` would have sent a re-deriver to a diff rather than to §6b.

One thing to be careful of when re-running either of them, because it is how a
first attempt at this transcript went wrong: **`"pd_refs": 858` appears twice in
the tool.** `PER_PROGRAM["pd_refs"]` is the committed census's pd half and
`OWNERSHIP["pd_refs"]` is the de-duplicated run's, they agree today, and the
check that holds the second is the one whose message is above. Perturbing the
first instead is caught earlier, by the "and the split partitions the census
rather than re-counting it" reconciliation, so `--self-test` prints that message
and never reaches the pd-half check. Both are correct answers to different
questions; the transcript is about the `OWNERSHIP` pair.

## The corrections

Four prose files still called the `157`/`858` pair the open one, and this change
corrects all four. Each keeps its original text visible with a dated correction
beside it, per [`../findings.md`](../findings.md) §4a-4d, and the list is the one
`git diff origin/main --name-only` gives rather than the one the tree remembered:

- [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
  — the paragraph whose "**What is left is the `157`/`858` pair alone**" is the
  live statement of what remains unheld, and the `157`/`858` row's pin cell.
- [`xdata-6a-direction-rows-pinned.md`](xdata-6a-direction-rows-pinned.md) — the
  "The two rows that stay open are open for different reasons" paragraph, which
  is the claim in a second place rather than in the bullet §2b is read from. The
  "Still unpinned after this" bullet beside it was already closed by #1364.
- [`xdata-ownership-main-keys-pin.md`](xdata-ownership-main-keys-pin.md) — the
  closing "**Still unheld in that same table**" paragraph, which names this pair
  as the next pass's to rediscover.
- [`../findings.md`](../findings.md) — the §4a correction naming the `157`/`858`
  pair as the one still open. `check_findings_frozen.py` still reports its
  section count, because an in-place correction is not a section.

A fifth file carried the claim and is **not** in that list because this change
does not correct it:
[`xdata-export-ownership-page-census.md`](xdata-export-ownership-page-census.md)
was already corrected by #1364, in the same window that closed the pair. It is
named here because it is the file an auditor comparing this list against
`git diff --name-only` would otherwise find missing, and "already corrected by
#1364" is the reason.

The guard-off `51` needed correcting too, since the change pins it. It is
superseded in two more places: the checklist's own live prose, which names it as
the figure §2b cannot vouch for — that one is superseded by the checklist's
correction paragraph above rather than by a paragraph of its own — and the
"Still open on the merged tree" bullet in
[`xdata-6a-direction-rows-pinned.md`](xdata-6a-direction-rows-pinned.md), which
records its own closure the way the bullet beside it does.
[`xdata-guard-off-pd-cluster-count-pinned.md`](xdata-guard-off-pd-cluster-count-pinned.md)
is the write-up for the assertion that now holds it.

## What this does not establish

- **The `1375`/`1326` gap is arithmetic over the committed tree**, and a change to
  the decompiled exports or to the `both` classification moves it. It is not a
  property of the EC firmware and nothing here is evidence about any register's
  behaviour.
- **This does not re-derive the 49-address overlap.** Which addresses the two
  images share, and what that overlap means for the two XDATA maps, is
  [#899](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/899)'s and
  [#906](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/906)'s open work.
  This file uses the measured row count and stops there.
- **A shared address number is not a shared byte.** `program=both` exists to carry
  exactly that distinction, and nothing here is a claim that the two images'
  registers are the same register.
