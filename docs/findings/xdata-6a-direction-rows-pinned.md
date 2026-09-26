# §6a's per-direction rows and §6b's cluster split are held now, and what is still not (issue #850)

Issue #820 wrote down what a re-export of the xdata census moves and what to do
about it, and its §2b named eight figures that no test held. Issue #850 asks for
the five of them §6a's table and §6b's console block print as *rows* to be held
to the page that prints them, so a re-export that moves a direction between the
PD set and the main-EC set — or that moves clusters between the two programs —
goes red instead of decaying silently. Those five are now held, and the count-
bearing sentences that called them unheld are corrected in place.

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved — same framing as
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):11.
Every figure below is a sum over committed text (`ec/decompiled/**` and
`ec/firmware/GMxMGxx_11.800`) taken from the tool's own two flags, with both
runs' scratch outputs under a temp dir and nothing written into the tree. The
change edits no tool, no CSV, no `registers.yaml` and no gate.

## The partition, which is the whole argument

The registers CSV's `program` column is not a label; it is a **partition**. Every
one of the 1,326 rows is `main-ec`, `pd` or `both`, and the three arms sum to the
same 1,326 in every census. That is the walk
[`xdata-no-eq-guard-refusal-contract.md`](xdata-no-eq-guard-refusal-contract.md):177-197
already prints, and it holds the same way in the export-ownership census — which
is the check that it is a property of the column and not an arithmetic accident
of one run:

| census | `write` by program | `main-ec write` | `main-ec read` | clusters by program |
|---|---|---|---|---|
| `--no-eq-guard` | 3948 / 193 / 279 | **3,948** | **7,189** | 394 / 51 |
| committed | 3206 / 142 / 239 | **3,206** | **7,935** | 389 / 50 |
| `--export-ownership` | 2712 / 142 / 189 | — | — | **390 / 50** |

The three `write` subsets sum to `4420` guard-off and `3587` committed, and
`3587` is `xdata_register_map.py:1362`'s `BUCKET_TOTALS["write"]`. The
export-ownership row's own subsets sum to `3043`, which is that census's
`OWNERSHIP["buckets"]["write"]`. So the partition is what the CSV's structure
says it is, checked against two independent oracles rather than one.

The three guard-off deltas are `742 + 51 + 40 = 833` — and **833 is the figure the
case already pinned.** The new pins are the *terms* of that sum, which is the
issue's "must be per-subset" requirement turned from a caution into a strength:
before this, a re-export that moved a direction from the main-EC arm to the PD arm
left the aggregate alone and moved nothing anyone could see.

## The derivation

The walk is §6a's own shape, four lines over two scratch CSVs. Nothing here
re-derives a census; it sums the two `--no-eq-guard` runs write and the one
`--export-ownership` run writes:

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/off-registers.csv --out-clusters /tmp/off-clusters.csv
$ python3 ec/tools/xdata_register_map.py --export-ownership \
    --out-registers /tmp/after-registers.csv --out-clusters /tmp/after-clusters.csv
$ python3 -c "
import csv, collections
for p in ('/tmp/off-registers.csv', 'ec/annotations/xdata-registers.csv',
          '/tmp/after-registers.csv'):
    d = collections.defaultdict(collections.Counter)
    for r in csv.DictReader(open(p)):
        for k in ('read', 'write', 'refs'):
            d[r['program']][k] += int(r[k])
        d[r['program']]['n'] += 1
    print('%-40s' % p, {k: dict(v) for k, v in d.items()})
"
/tmp/off-registers.csv                 {'main-ec': {'read': 7189, 'write': 3948, 'refs': 13891, 'n': 1169}, 'pd': {'read': 199, 'write': 193, 'refs': 603, 'n': 108}, 'both': {'read': 602, 'write': 279, 'refs': 1202, 'n': 49}}
ec/annotations/xdata-registers.csv     {'main-ec': {'read': 7935, 'write': 3206, 'refs': 13891, 'n': 1169}, 'pd': {'read': 250, 'write': 142, 'refs': 603, 'n': 108}, 'both': {'read': 641, 'write': 239, 'refs': 1202, 'n': 49}}
/tmp/after-registers.csv               {'main-ec': {'read': 4800, 'write': 2712, 'refs': 8914, 'n': 1169}, 'pd': {'read': 250, 'write': 142, 'refs': 603, 'n': 108}, 'both': {'read': 311, 'write': 189, 'refs': 661, 'n': 49}}
```

Two things to read off that before anything else. The three subset **sizes**
(1,169 / 108 / 49) and the three subset **`refs` sums** (13,891 / 603 / 1,202)
are **equal in the guard-off and committed censuses**, which is §6a's "0 of 1,326
addresses have a different `refs` total" localised to one arm at a time — the
guard re-buckets occurrences and moves no address. And the `program=both` arm is
where a shared address *number* is not a shared byte, which is the collision that
column exists to carry; §6a's table prints it as its own row rather than folding
it into the other two, and the new assertions keep it separate.

## What is held, and where

| assertion | file:line | the page line it names |
|---|---|---|
| `main-ec` `write`, guard-off / committed, with its `1,169` / `13,891` denominators in both censuses | `ec/tools/test_xdata_cluster_names.py:481` | `xdata-06c2-06db-timers.md:781` |
| `main-ec` `read`, same arm, denominators printed on the `write` row above | `:465` | `:782` |
| `pd` `write`, with `108` / `603`, both printed there | `:482` | `:783` |
| `both` `write`, with `49` printed there and the `1,202` added by the assertion | `:499` | `:784` |
| the three `write` deltas summing to the `833` already pinned | `:525` | `:785` |
| §6b's per-program cluster split `390` / `50`, summing to `OWNERSHIP["clusters"]` | `:706` | `:903-904` |
| the two `N clusters at threshold 0.5` figures §6b prints, against the CSV the same run wrote | `:724` | `:903-904` |

**The denominators are not all printed on the row they are cited to, and the
table above says which is which** rather than letting a re-deriver look for a
figure §6a does not print. `:781` carries `1,169 addresses, 13,891 refs` for the
`main-ec` arm as a whole, so the `read` row `:782` — which has no parenthetical
of its own — is served by it. `:783` prints both of the `pd` arm's. `:784` says
"the 49 addresses in both images" and **no** `refs` figure, so the `1,202` is
this suite's: the sum of `refs` over the `program=both` rows, which the
partition makes equal in both censuses and which the assertion adds rather than
transcribes. Each subTest's message says the same about itself, so a trip names a
figure the page does not print as the assertion's rather than the page's.

**The sixth is in its own class, `TheExportOwnershipClusters` (`:686`), not in
`TheGuardOffRegeneration`.** Two reasons, both about not falsifying something
this issue did not ask to touch: it is a *different flag's* census, so one class
would read as though the two regenerations were the same measurement; and
[`../findings.md`](../findings.md) §50 describes that other class as holding "a
seventh case", so an eighth case there would make a published sentence false.

**The seventh is the one beyond the issue's five, and it is droppable.** §6b's
console block is a *transcript*, and the correction at
`ec/annotations/xdata-06c2-06db-timers.md:917-931` exists because a transcript
there once carried ids and counts from two different runs. The two cluster
figures it prints are the run's own stdout, so they can be read back against the
CSV that same run wrote — which is the only way a half-renumbered transcript is
caught rather than believed. A reviewer who wants the diff to be exactly the
issue's five should drop `:724` and keep everything else; nothing else depends on
it.

## Each pin was checked for the ability to fail

A case that cannot fail has not been shown to check anything, and this one runs
in a suite a re-deriver will read after a trip. Each expected value below was set
wrong in turn, the one case run, the message captured, and the value reverted.
The `AssertionError` lines are the whole output worth keeping; each names the §6a
or §6b line and carries the figure actually measured, so a re-deriver reads a
page and a delta rather than a bare number. **What is kept is trimmed and what is
kept is stated:** an entry is the `AssertionError:` line and the message after
it, with the multi-line `difflib` block a dict comparison puts between them
dropped and its `" : "` separator reduced to a space — except #10, which is
pasted whole, because the paragraph below this block is about where the message
lands and that is the entry that shows it.

```console
$ # 1, main-ec `write` 3,948 -> 3,947
AssertionError: Tuples differ: (3948, 3206) != (3947, 3206) §6a 'main-ec `write` references', guard removed / as committed: measured 3948 / 3206 against the page's 3947 / 3206
$ # 2, main-ec `read` 7,935 -> 7,936
AssertionError: Tuples differ: (7189, 7935) != (7189, 7936) §6a 'main-ec `read` references', guard removed / as committed: measured 7189 / 7935 against the page's 7189 / 7936
$ # 3, pd `write` 193 -> 194
AssertionError: Tuples differ: (193, 142) != (194, 142) §6a 'pd `write` references', guard removed / as committed: measured 193 / 142 against the page's 194 / 142
$ # 4, `both` `write` 239 -> 238
AssertionError: Tuples differ: (279, 239) != (279, 238) §6a 'both `write` references', guard removed / as committed: measured 279 / 239 against the page's 279 / 238
$ # 5, the three deltas summing to the 833 -> 832
AssertionError: 833 != 832 : §6a 'references leaving `write`, all three programs' (`:785`): the three per-program deltas are [742, 51, 40], which sum to 833; the page prints that sum in bold, so a set that does not add up to it has a row transcribed from the wrong column rather than a total that moved. Re-derive §6a; do not move this number
$ # 6, the `main-ec` denominators' 13,891 -> 13,892
AssertionError: Tuples differ: (1169, 13891) != (1169, 13892) §6a 'main-ec' denominators (1169 addresses, 13892 refs): measured 1169 / 13891 in the guard-off census -- §6a:781 prints both, on the `write` row. The `0 of 1326` above is the same fact over all three arms, so this localises it to one
$ # 7, §6b's per-program cluster split 390 -> 391
AssertionError: {'main-ec': 390, 'pd': 50} != {'main-ec': 391, 'pd': 50} §6b: 'main-ec: 1218 distinct addresses, 9320 references, 390 clusters at threshold 0.5' and its `pd` line's 50 -- measured {'main-ec': 390, 'pd': 50} across the 440 cluster rows the run wrote
$ # 8, the same split's other half 50 -> 49
AssertionError: {'main-ec': 390, 'pd': 50} != {'main-ec': 390, 'pd': 49} §6b: 'main-ec: 1218 distinct addresses, 9320 references, 390 clusters at threshold 0.5' and its `pd` line's 50 -- measured {'main-ec': 390, 'pd': 50} across the 440 cluster rows the run wrote
$ # 9, the 440 as the sum of the split, via OWNERSHIP
AssertionError: 440 != 441 : §6b 'wrote ...: 440 rows' is the sum of those two console lines, and OWNERSHIP['clusters'] holds it (now 440); the split {'main-ec': 390, 'pd': 50} sums to 440, so the breakdown and the total have drifted apart. Re-derive §6b; do not move either number
$ # 10, §6b's console block against the CSV it wrote
AssertionError: {'main-ecx': 390, 'pdx': 50} != {'main-ec': 390, 'pd': 50}
- {'main-ecx': 390, 'pdx': 50}
?          -           -

+ {'main-ec': 390, 'pd': 50} : §6b's console block: the two 'N clusters at threshold 0.5' figures the run printed are {'main-ecx': 390, 'pdx': 50}, and the clusters CSV that run wrote splits {'main-ec': 390, 'pd': 50}
```

† **The one message above that names a direction word is a record of that run
and stays as written.** #5 reads §6a *'references leaving `write`, all three
programs'*, because that is the label the page carried when the case was run.
The tool's convention is committed → guard-off and the sum behind the figure is
`off − on`, so the references **enter** `write` and none leave; the `833`, the
`[742, 51, 40]` it decomposes into and every other part of the message are
unchanged. `test_xdata_cluster_names.py` now prints *entering* in that message,
**so this transcript can no longer be produced by the test it names** — which
is the reason it is a record and not a stale expectation, and why §4a-4d keeps
it visible rather than re-transcribing it. The measurement, the correction and
the per-address property behind it are in
[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md).

Two of those messages were **rewritten after seeing what they read like under
perturbation**, and that is worth recording because it is the failure mode this
class exists to prevent. The first draft of #5 and #9 said *"the deltas sum to
X, not to the 833 the page prints"* and *"...not to `OWNERSHIP['clusters']`"* —
which is fine on a real failure and **self-contradictory** the moment someone
"fixes" it by moving the number the message names, which is the exact response
the surrounding comment forbids. Both now report what was measured and point at
the page, without asserting that the page says something the perturbation removed.

Note also **where** the page line lands in the failure text. `assertEqual(msg=…)`
does not put the message where `msg=` suggests: with the default
`longMessage=True`, `unittest` prints its own got/want text first and appends
the message after a `" : "` separator
(`unittest.case.TestCase._formatMessage` returns
`'%s : %s' % (standardMsg, msg)`). So the first line of #1 is
`Tuples differ: (3948, 3206) != (3947, 3206)` and the page line arrives after
it. **A bare `AssertionError: 3948 != 3947` would send a re-deriver to a diff and
not to §6a**, which is the whole point the issue makes about the message — so
every new message carries the figure actually measured and the §6a/§6b line it
belongs to, rather than trusting the surrounding diff to name either.

## The §2b audit, which corrects the checklist

The issue is right that five figures were unheld, and it does not say the other
three were. **Before this change, on this tree, five of §2b's eight rows were
wholly unheld, two wholly held, and one — `157/858/50` — held for part of its
contents.** Split by figure, which is the count that differs:

| §2b row | figure | already held by |
|---|---|---|
| 1 | `3,948` / `3,206` | **nothing** |
| 2 | `7,189` / `7,935` | **nothing** |
| 3 | `193` / `142` | **nothing** |
| 4 | `279` / `239` | **nothing** |
| 5 | 43 addresses, `4,966` refs | a `refs` cell in the committed `xdata-clusters.csv`, compared cell for cell by `--check` (`xdata_register_map.py:3289`) — the issue says so too |
| 6 | `1326 rows` | `ORACLE["distinct"]` (`:743`), asserted at `:3864-3869`; also `OWNERSHIP["distinct"]` (`:1413`) and the case's own `(210, 1326)` denominator |
| 6 | `440 rows` | `OWNERSHIP["clusters"]` (`:1442`), asserted against the in-process after-census at `:4347-4354` |
| 7 | `1218` / `9320` | **nothing** — see the correction under the table: the `OWNERSHIP["main_distinct"]` / `["main_refs"]` pair this row first named is defined at `:1414` and read by no assertion |
| 7 | `390` | **nothing** — the first half of the issue's fifth |
| 8 | `157` / `858` | `ORACLE["extmem_pd_*"]` (`:738`), asserted at `:3555-3572` — **but for the *default* census**, so a partial hold at best |
| 8 | `50` | **nothing** — the other half of the issue's fifth |

*(Corrected at review, 2026-09-25. The seventh row's cell above first read
`OWNERSHIP["main_distinct"]` / `["main_refs"]` (`:1256`), "asserted at
`:3840-3842`", and the count below that table was built on it. **Both are wrong,
and the wrong version stays visible per [`../findings.md`](../findings.md)
§4a-4d.** The assertion at `xdata_register_map.py:4306-4308` reads
`OWNERSHIP["distinct"]` / `["refs"]` — `1326` / `10178`, the census-wide pair,
not the `main-ec` one — and `grep -n 'OWNERSHIP\[' ec/tools/xdata_register_map.py`
returns only `distinct`, `refs`, `buckets`, `lost`, `moved`, `clusters`,
`cluster_keys_kept` and `hand_names_kept`: **the `main_*` pair at `:1414` is
defined and read by nothing in the tree.** `1218` *is* asserted, but as
`ORACLE["main_distinct"]` (`:744`, read at `:3864-3869` and again at `:4347-4354`),
which is the **default** census's main-EC width — and its partner there is
`ORACLE["main_refs"]` = `14,838`, where §6b prints `9,320`. `9,320` is asserted
nowhere: `grep -rn 9320 ec/tools/*.py` returns a comment, this dict entry, and
the message string of the new assertion below. So the row is not a partial hold
at all — it is a missing one, and §6b's de-duplicated main-EC pair belongs on the
open list below beside `157`/`858`.)*

*(Corrected again at the merge, 2026-09-25, and the wrong version stays visible
per [`../findings.md`](../findings.md) §4a-4d. **The last sentence above is the
one that did not survive its own merge: §6b's de-duplicated main-EC pair is no
longer on the open list.** Issue #849 landed in the same window and added the
"and its main-EC half is" `check()` at `xdata_register_map.py:4315-4319`, which
reads `OWNERSHIP["main_distinct"]` and `["main_refs"]` and compares them against
the in-process export-ownership census — §6b's own run, so it is a whole hold
rather than a partial one, and the "read by nothing" above is no longer true of
this tree. Both issues reached the same conclusion about those two keys from
opposite ends, and both were right about the tree each was measured on: #849
from *"a value in a constant that no check reads is a promise wearing the costume
of a pin"*, this audit from the `grep` above. The `157`/`858` row and the
guard-off `51` are still open, and §2b of the checklist now reads **eighteen
figures, eighteen held and none unheld** with the two gaps named beside the
tables rather than in a column.)*

Counted by row and not by figure, because the two are not the same count here:
**before this change five rows were wholly unheld, two wholly held, and one —
`157/858/50` — held for part of its contents and not for the rest.** *(This
count, and the sentence above the table, first read four unheld, two wholly held
and two partly held. The seventh row has no hold at all, so the third of those
two is the eighth row alone and the count is five, two and one.)* So §2b's
heading, "**Eight, unpinned — these are the ones that decay silently**", was
itself an overclaim — **about three of the eight rows**, which is the `4,966` and
the `1326`/`440` held whole and the `157`/`858` held in part — in exactly the way
[`../findings.md`](../findings.md) §4 records twice. The checklist is corrected
in place per §4a-4d: the heading keeps its wrong count visible beside the
correction, both tables gain a "held by" column rather than losing rows, and the
§2a table gains the four rows this change moved from one to the other.

The two rows that stay open are open for different reasons, and it is worth
keeping them apart. The `157`/`858` half of the eighth row is a **partial** hold:
`ORACLE["extmem_pd_*"]` (`:738`, asserted at `:3555-3572`) does hold those two
numbers, but it measures the PD half of the **default** census's token
spellings, and `OWNERSHIP` carries no `pd_*` key at all. §6b prints them for the
**de-duplicated** run. Different measurement, same digits. The `1218`/`9320` half
of the seventh row is a **missing** hold: nothing reads either key, so the two
digits that do land in an assertion land there as a different pair in a different
census, per the correction under the table.

A by-product of the audit, since the checklist already flags `14,838` as
"commonly mis-transcribed": it is `ORACLE["main_refs"]` (`:744`) and it is
asserted, at `:3864-3869`. The correction can therefore say **where** the number
is held, which is more useful than saying only that it is dangerous. The same
line is what makes the seventh row's correction necessary rather than optional:
`1218` sits on it too, beside `14,838` where §6b prints `9,320`.

## Still unpinned after this

The issue enumerates its five, and pins beyond the ask are scope creep. Four
figures came up while re-deriving the table that are **not** among them; three
are named here and the fourth turned out to be closed already. **Two of the
three are still open on the merged tree** — the third was closed by #849's
`check()` in the same window, and its bullet says so rather than being deleted.
A list of what is still open is worth more than a diff that quietly closes
things nobody asked it to:

- **§6b's `157` / `858` for the de-duplicated census.** Held for the *default*
  census only, as `ORACLE["extmem_pd_distinct"]`/`extmem_pd_refs`
  (`xdata_register_map.py:738`). `OWNERSHIP` has no `pd_*` key, so nothing
  measures the after-census's pd width. This is the `pd_*` pair §2b's last row
  still needs, and it is a one-line addition to `OWNERSHIP` plus a self-test
  assertion. **Still open on the merged tree.**
- **§6b's `1218` / `9320` for the de-duplicated census**, which the §2b audit
  above first listed as held and does not: `OWNERSHIP["main_distinct"]` /
  `["main_refs"]` (`:1414`) hold exactly this pair and no assertion reads them,
  and the `1218` that *is* asserted is the default census's, beside `14,838`. It
  is the same shape as the `157`/`858` above — §6b prints a per-program total for
  a run nothing measures the per-program width of — and it is closed the same way,
  by a `check()` in `--self-test` reading the two keys that are already there.
  ***Closed at the merge, and by exactly the remedy this bullet names:** issue
  #849 added that `check()` (`xdata_register_map.py:4315-4319`) in the same
  window, so the two keys are read and the pair is a whole hold. The bullet
  stays visible as written above, per [`../findings.md`](../findings.md)
  §4a-4d.*
- **The guard-off pd cluster count `51`.** Printed by the run
  `TheGuardOffRegeneration` builds, on the same line as the `394` the case pins,
  and held by nothing — the missing other half of that pair. §6a does not print
  it in its table, so it is not one of the issue's five, but it is the same shape
  of gap and a `assertEqual` away. **Still open on the merged tree**, and the
  only one of these three that is: `check_doc_figure_pins.py` measures it
  `unheld`, and it is the case
  `test_a_small_figure_is_not_pinned_by_an_unrelated_cell` now uses as its
  real-tree witness for that verdict.
- **The three arms' `refs` totals.** *Closed by this change*, and this is the one
  item of the four that is not left open: `13,891` / `603` / `1,202` are asserted
  in the same subTest as the four numerators, by the same "denominators are pinned
  with the numerators" rule §6a's case already states for the `210` and the `0`.
  Asserting them is also what lets the new messages name a figure rather than a
  ratio, so it was not a separable addition. Two of the three are figures §6a
  prints and one — the `1,202` — is not: `1,169 addresses, 13,891 refs` and
  `108 addresses, 603 refs` are its parentheticals, while `:784` says only
  "the 49 addresses in both images". The `1,202` is the sum of `refs` over the
  `program=both` rows, a partition fact the assertion adds, and its failure
  message now says so rather than attributing it to the page.

Two further counts this change did **not** introduce and did not fix, recorded
because both are figures a reader of the same tree will trip over:

- `guard_off()`'s docstring says "six cases want the same regeneration"
  (`:81-82`); the class has held seven since #753 and holds seven still, because
  the new census went to a new class. Pre-existing, already wrong before this
  change, and left alone — it is a count in a file this change *does* edit, which
  is the only reason it is named here at all.
- `tools/README.md`'s runner total read 974 tests over 32 suites when this was
  written and this adds two cases; on the merged tree #849's
  `ec/tools/test_check_doc_figure_pins.py` at 44 cases is in as well, so the
  measured figure is **1020 over 33** on the tree this change was written on —
  **and 1035 over 34 here**, because #851 added a suite in the same window. Left
  alone on purpose:
  `tools/test_readme_suite_table.py` checks the suite *set* and never the counts
  — its own docstring says "an expected count turns every added test into a
  failure, which is the wrong trade" — and
  [`../findings.md`](../findings.md) §52 re-derives those totals only when the
  total is the subject. Rewriting a shared totals paragraph for a two-case delta
  is the conflict this repository's new-file convention exists to avoid.

**The runner is red on this tree, and this change did not make it so.** `bash
tools/run-tests.sh` last read `33 suite(s) run, 1020 tests; one or more FAILED`
on the tree this change was written on, and `34 suite(s) run, 1035 tests; one or
more FAILED` on the tree it lands in,
and the red suite is `ec/tools/test_check_cluster_citations.py`, on
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220` — a file and a line
this change does not touch. It is the same failure
[`../findings.md`](../findings.md) §46 and `tools/README.md`'s merged-tree notes
record against a clean `origin/main`, and it is named here rather than fixed here
because it belongs to #822's file. The other half of that run is the part that
bears on this change, and it is a smaller claim than it looks:
`ec/tools/test_check_cluster_citations.py` reads every committed `.md` file
against the committed census and **raised nothing about this one** — but this
file names no `main-ec-NNN` and no address, so that check had nothing here to
bind. The ids it would have bound are held by the census's own suite instead,
`test_the_counter_sweep_name_still_resolves_to_the_swept_block` for the 43
addresses §6a's `main-ec-003` row is about.

## What was not done, and what a re-deriver should know

- **The committed CSVs are untouched.** A default run still reproduces both with
  0 differences; no cluster id, name or key moves, so no citation anywhere in
  the tree is invalidated by this change.
- **The refusals are respected.** `--no-eq-guard` and `--export-ownership` both
  stay refused with `--check` and `--self-test` and refused without scratch
  `--out-` paths. Both test runs pass scratch paths into a `tempfile` dir
  (`export_ownership_census()`, `:110`, mirroring `guard_off()`), and neither
  writes a byte into the tree.
- **`.github/workflows/` and `.github/actions/` are untouched.** Nothing here
  needs them, and the pipeline token has no `workflow` scope. Recorded as a
  standing gap, not fixed here: `agent-gates.sh` runs `--check` and `--self-test`
  but not the unittest suites, so these new pins are not gated. That is the
  status quo for this suite, not something this change introduces.
- **Nothing was flipped, re-keyed or regenerated.** The `--export-ownership`
  default stays off, `xdata-cluster-names.csv` keeps its 9 keys, and neither
  committed CSV was rewritten. Those are all §8 item 7's, and they cannot share
  a branch with a diff like this one.
- **No live observation, and none is implied.** No laptop, no Windows, no image,
  no register read back. Every number above is a sum over committed text.
- **Nothing is submitted upstream.** No patch against `Wer-Wolf/uniwill-laptop` or
  `tuxedo-drivers` is proposed here, so there is nothing for a human to submit,
  and issue #10 is unaffected.
