# The `--export-ownership` refusal's figures, and why they are no longer written down (issue #833)

`xdata_register_map.py` refuses `--export-ownership` against the committed
output paths, and the comment above that refusal argued the refusal from three
numbers and a fourth beside them. The tree had moved under all four, and two of
the sites that quoted them said "measured on this tree" while meaning a tree
several re-derivations back. This is the reconciliation, and it is also the
reason the fix was not a substitution.

**Nothing here is a live observation.** The census is a static measurement of
committed decompiled C, every figure below comes off the committed tree by a
command a reader can paste, and no register is read back. The refusal still
stands and the flag is still off; only the arithmetic the refusal quotes
changed.

## What the tree holds, and where the quoted figures came from

| figure | quoted by the refusal | on this tree | source |
| --- | --- | --- | --- |
| register rows | 1,171 | **1,326** | `ec/annotations/xdata-registers.csv`, and `OWNERSHIP["distinct"]` |
| clusters | 430 | **439** | `ec/annotations/xdata-clusters.csv` |
| hand cluster names | 10 | **9** | `ec/annotations/xdata-cluster-names.csv` |
| addresses `moved` | 228 | **296** | `OWNERSHIP["moved"]` |

The 1,171 → 1,326 step reconciles exactly rather than being a different
population: it is the pair-accessor pass issue #279 added, whose 155 new
addresses are `xdata_register_map.py`'s own `PAIR_ROWS_PAIR_ONLY_UNION` pin, and
`1171 + 155 = 1326`. The quoted figure is a dated measurement of the census
*before* that pass, not a census of something else. The 228 → 296 step is the
same mechanism on a different axis — `OWNERSHIP`'s own comment beside the pin
records it as "the same width argument as the 228 before it: the pass renumbers
every address whose references come from a shared export, and this one adds 68
more of them".

The measurement was re-derived on the implementing tree before any prose was
written, by the command that already re-derives it in-process:

```
$ python3 ec/tools/xdata_register_map.py --self-test
  ok   ... and it moves the reference count of 296 addresses, the width of the 6a before/after (got 296)
  ok   ... and the flip would renumber: 440 clusters against the committed 439, 400 of the
       committed cluster_keys surviving, 4 of the 9 hand names in
       annotations/xdata-cluster-names.csv (got 440/400/4)
```

A green `--self-test` **is** the measurement: the ownership block builds a fresh
de-duplicated census and asserts `OWNERSHIP` against it, so a moved pin is a
red line rather than a stale sentence. No scratch `--export-ownership` run was
needed, and the existing `AcceptedWrite` class in `test_xdata_register_map.py`
covers that shape if a pin ever has moved.

## The name count needed a decision, and the decision was 5 of 9

The issue asked which side of the question the removed name fell on: was it
among the five names that break, so the count is unchanged and only the
denominator moved, or not, so the count is 4 of 9? **The answer is that it was
not among the five**, and the tree already records why.

`xdata_register_map.py`'s `OWNERSHIP` comment beside the pin names the five that
break under the flip — `counter-sweep`, `level-block-086x`, `ff-fill-stubs`,
`countdown-06cd` and `mode-oem-init` — and separately explains why the
denominator fell. The tenth name, `page-0300`, named a nine-address cluster on
the 0x0300 page; after #279 that cluster is nine addresses inside a
152-address one, which is Jaccard 0.07 and **not carried by this method** rather
than gone. It was dropped from `xdata-cluster-names.csv` instead of being
re-keyed onto a membership seventeen times its size, because a re-keyed name
would have been a false description of what it pointed at. So the numerator is
unchanged and the denominator is not: **5 of 9**, costing one name in nine
rather than one in ten, and costing the same five either way.

That is the issue's "which is a fact about the `--export-ownership` regeneration,
not about the CSV, and it should be measured rather than picked" — and it had
been measured already, in three places, by the time the issue was filed.

## The defect was eight duplicated arguments, not four wrong numerals

A substitution would have fixed this tree and left the next re-derivation to do
it again. The refusal's argument was written out in full in eight places while
the tool already pinned the same measurement in `OWNERSHIP`, already derived one
message from it in `--self-test`, and already named the keys.

| site | what it became |
| --- | --- |
| module docstring | cites `annotations/xdata-export-ownership.md` §5 and `OWNERSHIP` |
| the `OWNERSHIP` comment | names the four keys it explains rather than their values |
| `--export-ownership` docstring | cites §5 and `OWNERSHIP` |
| the argparse `help=` string | cites §5 and `OWNERSHIP` |
| the refusal comment | **keeps** its figures, re-derived, and held to the pins by a suite |
| `export_ownership.py`'s docstring | cites §5 and `OWNERSHIP` |
| the refusal's test comment | cites §5 and points at the suite that holds it |
| `ec/README.md` | cites §5, in place, on all three of its figures |

Six of the eight cannot interpolate at all: only an f-string can read a pin, and
five of the six are comments or docstrings. The seventh — the `help=` string —
*could* interpolate, and does not, because a second interpolated figure would
have pushed its block past the line count that
`check_eq_guard_citations.py` resolves a committed citation against (see
below). The one site that keeps figures is the refusal comment itself, because
the sibling suite holds that comment to `FIGURE_IN_PROSE` and a citation cannot
satisfy a rule that wants a number in it.

`ec/README.md` was the one addition beyond the issue's list, and two earlier
issues had already deferred it in writing:
[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md)
lists its sentence among the drift "left as it is", and
[`name-shape.md`](name-shape.md) records that `ec/README.md` "keeps its 'ten'
and gets no edit". Both were right then — the sentence was about the census
rather than about that change's subject. This is the issue that fixes it, and
both records stand as the dated account of the deferral. The README also carried
the register-row and cluster figures from the same stale set, so all three were
corrected together rather than leaving the file half right.

## Line counts are part of the contract here, not an accident

Every hunk in `xdata_register_map.py` is line-count neutral, and that is
load-bearing rather than tidiness. `check_eq_guard_citations.py` resolves
`committed_output_refusal` out of that file *by the line it is on* —
`ec/tools/xdata_register_map.py:5250` — and
`docs/findings/xdata-4-4-identity-rederivation.md` cites it. A re-wrap that
gained one line anywhere above it would have turned four suites red for a change
that altered no claim. The same applies to `ap.add_argument("--no-eq-guard",…)`
at `:5212`, cited from `ec/annotations/xdata-register-map.md`.

So the fix is a substitution inside an existing span, and the new suite holds
both refusal blocks to their lengths for the same reason its sibling does.

## What is now held, and what deliberately is not

`ec/tools/test_export_ownership_refusal_figures.py` asserts **relations only** —
that the refusal's figures equal `OWNERSHIP` and the committed CSVs — and never
a figure of the tree. `39` is expected as
`len(committed cluster_keys) - OWNERSHIP["cluster_keys_kept"]`, computed at run
time; writing `39 of the 439` into an assertion would have made the suite red
for the next re-derivation, which is a change and not a defect. This is the rule
`CLAUDE.md` states as *assert the claim, not the census*, and it is only
available *because* the prose now cites rather than restates.

The one number the suite writes out is a comment's line count, which is not a
count of the tree.

Six mutations of the change were checked and all six are caught: a wrong cluster
figure, the refusal comment losing its figure, the comment gaining a line, the
module docstring regaining a literal, the sibling tool regaining one, and the
README regaining one.

Two items from the issue's own list are **not** edits here:

- **`check_cluster_citations.py`'s "ten committed names"** is already resolved.
  That sentence is no longer in the file; the `name-shape` change dropped the
  numeral deliberately and cited the check in its place, and
  [`name-shape.md`](name-shape.md) gives the reason — a check's output is not a
  hand-kept number. The old sentence survives only as a block quotation in that
  same page, and correcting a quotation would falsify it.
- **A summary link in `docs/findings.md`**, which the issue asked for, cannot be
  made. `ec/tools/check_findings_frozen.py` fails a change that adds, deletes,
  renumbers or reuses a section, and `CLAUDE.md` forbids it in capitals as the
  one edit that file is not allowed to make. The deliverable is this page plus a
  regenerated [`INDEX.md`](INDEX.md).

## Left for the next pass, with the figures measured

The module docstring's **direction-split** paragraph is stale in the same way and
is *not* part of this issue's measurement — it is `DIRECTION_INVARIANT`, not
`OWNERSHIP`, and it argues a different claim. It reads "**5,662 occurrences
across 1,008 distinct addresses** of the census's 1,171 … the second pass
accepts 5,664". The committed tree measures `write_like` **5,677**,
`assign_shaped` **5,679** and `distinct` **1,326**, all three re-derived by the
`--self-test` line that names them. Only the 1,008 is still right.

It is recorded here rather than fixed here, because a change that quietly
widens from one measurement to another is how a diff stops being reviewable.
`DIRECTION_INVARIANT`'s own comment carries the same supersession notes its
values do, so the paragraph is a two-sentence in-place correction once someone
takes it as their subject.

## Not touched

`docs/findings.md`, `ec/annotations/xdata-register-map.md` and
`ec/annotations/xdata-export-ownership.md` — dated records, and the last two
already carry the current figure beside the old one in the `docs/findings.md`
§4a-4d form. The three census CSVs, which are generated. `OWNERSHIP`'s values,
which are correct and are what `--self-test` asserts. The refusal itself: the
guards, the `ap.error` strings and the `--export-ownership` default are all
exactly as they were.