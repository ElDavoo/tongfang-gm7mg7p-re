# Which census `xdata-cluster-names.csv` is anchored to, and what a carry line is a claim about (issue #851)

Issue [#851](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/851) was opened
by the follow-up pass off #824. It named a sentence the tool prints on itself:
`print_carry`'s overlap branch closed every carried name with *"-- re-key
`annotations/xdata-cluster-names.csv` if the name moved"*, in every mode, and one
of those modes is not the census the names file is anchored to. This file is the
decision and the fix; the tool's wording and the checklist's step 5 are the
deliverable.

**None of this is a live test, and none of it is evidence about the firmware.** No
EC is opened, no register is read back, no capture is taken, and no laptop, EC or
Windows machine is involved anywhere below. Every figure is arithmetic over
committed text and is re-derivable from the files this repository holds. No
register's `status:` moved, and neither census CSV nor the names file was edited.

## The anchor, stated as a rule

`ec/annotations/xdata-cluster-names.csv` is anchored to the **committed census**:
the two CSVs as committed, which is exactly the run `--check` reproduces — the
`==` guard on, no `--export-ownership`, `--threshold 0.5`. Four places in the tree
said so before this issue and **none of them named it as a mode or a flag
combination**:

| the statement | where |
|---|---|
| the comment scoping `--self-test`'s stale-key check | `ec/tools/xdata_register_map.py:4117-4132` |
| `TheNamesFile`'s class docstring, *"the editable surface, and it is anchored"* | `ec/tools/test_xdata_cluster_names.py:581` |
| §4.4's *"The names are anchored to the committed census"* paragraph | `ec/annotations/xdata-register-map.md:1255-1269` |
| the checklist's §3 bullet | [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md) §3 |

So the one sentence a reader needs in order to act was the sentence carrying no
such statement. The rule that closes it:

> **A carry is a statement about the run that printed it; only a run whose cluster
> keys are the committed ones can turn a carry into a re-key request.**

That makes the predicate exactly the flags that move the keys off the committed
ones — `--no-eq-guard`, `--export-ownership`, and a non-default `--threshold` —
which is now `census_shape(args)` in the tool and the clause it picks is
`carry_advice(shape)`.

**`--no-writer-axis` is deliberately not in that set.** `build()` calls
`components(groups[g], threshold)` with the writer axis unconditionally on
(`:2718`), and the flag's own help (`:4564-4567`) scopes it to `--threshold-sweep`,
so a census built with it clusters exactly as a default run does. Naming it would
put a flag on a carry line that never moved a key — the same overclaim in the
other direction, and one the test suite now pins.

## Why the notice was wrong, and not merely incomplete

`print_carry`'s docstring opens *"Printed by every mode that builds a census"*,
and that is true, and it is the reason the bug existed. Three shapes reach the
overlap branch: `--check` (`:3092`), a bare write (`:3111`), and every flag
combination that falls through to that write. The first is the anchor. The other
two are not.

For those shapes the overlap carries are **structural, not evidence of a moved
key** — and the tree already measures that, three times over:

- `ec/annotations/xdata-06c2-06db-timers.md:851-855` — 39 of the 439 committed
  `cluster_key`s do not survive into the `--export-ownership` pass, and it *breaks
  5 of the 9 hand names*;
- `ec/annotations/xdata-export-ownership.md:210` — the same cost, in the flag's
  own write-up;
- `.github/scripts/agent-gates.sh:250-251` — *"400 of the committed
  `cluster_key`s surviving, 4 of the 9 hand names"*.

A run measured to break five of nine names cannot also be reporting that three of
them moved. It was reporting that its own clustering is different, in a vocabulary
("carried by overlap") that the committed census also uses and means something
narrower by. Nothing in the old line distinguished the two readings, so a reader
following the re-derivation checklist literally — step 4, then step 5, exactly as
§6b's own recipe produces — re-keys the names file onto a census it is not
anchored to. One of the three is `mode-oem-init`, the name #840 is working on,
whose note records 33 addresses where the committed cluster holds 92, and whose
own re-key history (three times, at Jaccard 0.99 / 0.96 / 0.84) is precisely the
judgement a tool cannot make on a reader's behalf.

## Before and after, on this runner

Both runs are under two seconds over committed text. The counts are identical
before and after; only the tails differ. This runner is a GitHub-hosted x86-64
Linux container; the absolute times are its own, per the habit
[`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md) §"The cost, and
whose runner it was measured on" sets out.

| mode | time here |
|---|---|
| `--check` | 2.04 s |
| `--self-test` | 5.14 s |
| `--export-ownership` (a write) | 1.74 s |
| `test_xdata_carry_notice.py` (15 cases, in-process) | 0.06 s |

**The committed shape, byte-identical before and after** — this is the proof the
committed path was not touched, and it is the command the cheap gate runs:

```console
$ python3 ec/tools/xdata_register_map.py --check
  names: seeded 9, exact 0, carried by overlap 0, tied, not carried 0, with no name 430
```

**A non-committed shape, one tail in place of the other** (abbreviated to the
first carry line; the full blocks are in
`ec/annotations/xdata-06c2-06db-timers.md` §6b and
`ec/annotations/xdata-register-map.md` §4, both re-run rather than hand-edited):

```console
  names: seeded 4, exact 0, carried by overlap 3, tied, not carried 0, with no name 433
    main-ec-002 carries mode-oem-init by overlap, Jaccard 0.97 from kefb63d82f8c7 -- this run's ids are not the committed census's (--export-ownership), and annotations/xdata-cluster-names.csv is anchored to the committed one, so a carry here is arithmetic over a different clustering, not a re-key request
```

The `names:` tally line and the `tie` line are **mode-independent facts** and were
left exactly as they were: they are arithmetic over this run's own report, and
they do not stop being true because a flag was passed. Only the advice is split,
and the new test asserts the two shapes' stderr differ in the tails and nowhere
else.

## The part-2 decision, and its proof

The issue's second half is a separate question: *should a name whose membership
moved but whose key still resolves fail something?* Recorded, not built.

**Decision: no — and a membership that moved cannot keep resolving, so there is no
such case for something to fail.** Three parts, all already in the tree:

1. `cluster_key` is a content hash, `sha256(program + " " + sorted addresses)`
   (`xdata_register_map.py:2355-2365`). Not a rank, not an id: a function of the
   membership and of nothing else.
2. So *"the key still resolves"* and *"the membership is unchanged"* are the same
   statement. The tree already has the unit test for exactly that:
   `test_xdata_cluster_names.py:117-121`,
   `test_changed_membership_is_a_new_key_not_a_collision`.
3. And the committed CSV's `cluster_key` column really is that hash rather than a
   hand-written string, because `--check` re-derives the whole file cell for cell
   and the cheap gate runs it. **Re-derived independently while implementing:**
   recomputing `cluster_key(row.program, row.addrs)` over all 439 committed
   `xdata-clusters.csv` rows gives **439 matches, 0 mismatches**.

Therefore a moved membership always produces a key the committed census does not
have, and `--self-test`'s check at `:4128` fires on it. The names file can never
quietly end up attached to a membership that has gone. The issue's *"and nothing
reads a note"* half is the true part — but it is a **different question** from the
one the check answers, and this file says so rather than blurring the two.

**The residual, recorded rather than fixed.** The `note` column is the only record
of the membership judgements (`counter-sweep`'s *"43 addresses and 4,966
references"*, *"membership did not move in the 2026-09-24 re-derivation"*), and
nothing reads it. `test_xdata_cluster_names.py:592-598` requires the column
non-empty and checks nothing else in it, and `ec/tools/check_cluster_citations.py`
never opens the names file at all. A note checker cannot be key-anchored: it would
have to parse prose (*"43 addresses and 4,966 references"*), or the file would need
a new machine-readable column — a schema change to the one file a human edits by
hand. Both costs are named here for the follow-up pass to price.

## What was deliberately left alone

- **`ec/annotations/xdata-cluster-names.csv`** — no key moves; the nine rows stay
  byte-for-byte. The harm the issue describes *is* a name re-keyed onto a census
  it is not anchored to, so editing this file would be the failure, not the fix.
- **Four historical transcripts**, which are records of runs that happened:
  `docs/findings/xdata-export-ownership-page-census.md:64-83` (which says so
  itself), `docs/findings/xdata-4-4-identity-rederivation.md:196-233`,
  `docs/findings/xdata-census-totals.md:33-40` and
  `docs/findings/xdata-no-eq-guard-refusal-contract.md:47-59`. Re-printing them
  would re-date a past run. The first two still carry the pre-#851 clause, and
  that is left standing for the same reason: they are what a past run printed.
- **The 9-vs-10 stale counts**, at five sites including
  `xdata_register_map.py:4124` and `:4578-4579`. #833 owns that drift; naming it
  there is the right move and fixing it here would be a second issue's work.
- **`ec/tools/test_xdata_cluster_names.py` and
  `ec/tools/test_xdata_register_map.py`** — no case in either asserts on the carry
  line's text, and both call `carry_names()` in-process and assert on `how` and
  the Jaccard score, which this change does not touch. The new cases are in a new
  file, per the repository convention.
- **`.github/scripts/agent-gates.sh` and `tools/run-tests.sh`** — nothing to add.
  The runner discovers `test_*.py` by `find` (`tools/run-tests.sh:89`), so the new
  suite is collected with no runner edit, and the `--check`/`--self-test` arm is
  already in place from #823.

## Merged-tree note (2026-09-25)

This change lands beside #849, which added 19 lines to
`ec/tools/xdata_register_map.py` above the same `check()`s, so **every
`file:line` cited above was stale the moment the two landed together** —
#851's own 80 lines moved the anchors this page points at, and #849's 19 moved
the ones it pointed at in the other direction. All of them were re-measured
against the merged file rather than shifted by arithmetic: `:4098-4113` →
`:4117-4132`, `:2710` → `:2718`, `:4545-4548` → `:4564-4567`, `:3084`/`:3103` →
`:3092`/`:3111`, `:2347-2357` → `:2355-2365`, `:4109` → `:4128`, and
`:4105`/`:4559-4560` → `:4124`/`:4578-4579`. The same pass repointed six
citations in six other pages that this change edited, and #849's own pins in
`doc-figure-pin-audit.md` and the checklist's §2b.

**The two transcripts below are re-run on the merged tree, and they are
byte-identical to the ones this change wrote**: `--check` still prints
`seeded 9, … carried by overlap 0`, and the `--export-ownership` run still
prints `seeded 4, … carried by overlap 3` with the same three tails and the
same Jaccard scores. That is the point of the anchor rule rather than a
coincidence — neither side of this merge touched what the census reads.

The runner's figures move because of the merge rather than because of this
change, and are recorded in `tools/README.md`'s sixth note: thirty-four suites
and 1033 tests, the one addition being this change's
`ec/tools/test_xdata_carry_notice.py` at 15. The red set is unchanged by either
side — still `ec/tools/test_check_cluster_citations.py` alone, on `:220` of the
same #822 file, and still red on a clean `origin/main`.
