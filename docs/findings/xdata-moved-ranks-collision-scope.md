# The `cluster_key` collision check covered the moving part of each census, and `keyed_by`'s docstring said it covered all of it (issue #929)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every transcript below
is the output of a command over a synthetic fixture or over a committed CSV,
with every scratch output under `/tmp` and `git status --porcelain` printing
nothing after the runs. **The committed census files are the only real inputs
this reads** — `ec/annotations/xdata-clusters.csv`, `ec/annotations/xdata-registers.csv`
and the two guard-off regenerations of them, all of them files; the fixtures are
written by the tool's own `--self-test` and describe no cluster that exists.
Same framing as
[`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):3-11,
which this file is a follow-up to and whose §2, §3, §6 and §7 are corrected in
place by §6 below.

**The calibration comes first, and it is a narrower claim than the one it
replaces: no published figure moves.** §4 re-derives every figure the fall
measurement and the collision write-up publish and gets all of them back. What
is below is that the check printed over a *subset* of each census it re-keys —
the part that happened to be moving — and said nothing at all about the
guard-off census, so a report could read as a clean bill of health for a census
whose key-indexed counts were short. A latent defect in what a report *says*,
not a wrong figure found in the tree.

## 1. The claim, and which of the re-keying sites held it

`keyed_by()`'s docstring stated the property the whole `keyed_by` arrangement
rests on, and stated it about the file:

> every caller of this prints `duplicate_keys()` over what it re-keyed rather
> than relying on it

Measured, that was three of six census re-keyings, and the two that were printed
between them did not cover the population they were printed over:

| re-keying site | census re-keyed | printed the check, before | after |
|---|---|---|---|
| `flip_table` `:439` | both committed | the **moved** ranks of each, via `collapsed` `:455` | the whole committed census |
| `swept_report` `:733` | both committed | yes, hand-rolled at `31f683e5:ec/tools/xdata_moved_ranks.py:695-702`, over the whole census | yes, through `collision_line` |
| `pair_report` `:335` | the pair's committed | yes | yes, plus the guard-off `:339` |
| `holders_by_program` `:845` | a guard-off census | no | by the `cause` block above it `:963` |
| `cause_report` `:941` | both guard-off | no | yes, `:963` |
| `cause_report` `:1022-1024` | both committed, and the other generation's guard-off | by `collapse_line` `:1007`, over the moved ranks | by `collapse_line`, over the whole committed census |

`grep -n 'keyed_by(' ec/tools/xdata_moved_ranks.py` is the whole enumeration:
**seven call lines** — `:439`, `:733`, `:845`, `:941`, `:1022`, `:1023`, `:1024`,
with `:941` carrying two calls on one line and the per-cell lookup being three of
them. They are the six rows above less one, and the one they leave out is worth
naming: **`pair_report` re-keys through `collision_line` and never calls
`keyed_by` itself**, so its row is a census that is checked rather than a line
in this grep. Between them the seven reach **four distinct censuses**, the two
committed and the two guard-off, by more routes than four. That is why the unit
of the claim is the *view* and not the caller: `cause`'s per-cell lookup
re-keys the same committed censuses `flip_table` does, reached a second way, and
the check belongs to the census rather than to the function that happened to
reach it first.

`duplicate_keys()` itself had three call sites — `collision_line`, `collapsed`,
and `swept_report`'s own loop — and now has two, because the third was a
hand-rolled copy of the first.

## 2. The two measured cases

Both runs are over synthetic three-row fixtures written by the tool's own
`write_census()`, which already takes a key per row: an intact-only collision
was always expressible, and every earlier fixture just happened to pass a
distinct one. The pre-change column is the tool at `31f683e5` — this issue's
base, and the commit that *adds* `duplicate_keys()`, not the one before it —
materialised
with `git show 31f683e5:ec/tools/xdata_moved_ranks.py > /tmp/pre-change.py`.
It is a valid before because the tool is byte-identical at this issue's own
parent `24460001`, so it is the pre-change tool this edit started from.
`31f683e5^` is one commit too far back: `git show
31f683e5^:ec/tools/xdata_moved_ranks.py` has no `duplicate_keys()` and no
`collision_line()`, so it prints no collision line at all and cannot reproduce
the before column.
It is **not** `git show HEAD`: after this merges, `HEAD` names this same tree's
tool, and the diff would report no difference at all and an empty diff would
read as "nothing moved" when it means only that the recipe was wrong.

**1. A guard-off collision is reported as a clean bill of health.** `pair` reads
two censuses and printed the precondition for the committed one only. Two
guard-off ranks on one key, both intact, so nothing moved:

```console
$ python3 <PRE-CHANGE> pair --label intact \
    --old /tmp/intcoll/clean-committed.csv --new /tmp/intcoll/intact-off.csv
pair intact
  committed  /tmp/intcoll/clean-committed.csv: 3 rows
  guard-off  /tmp/intcoll/intact-off.csv: 3 rows
  moved      0  (main-ec 0, pd 0)
  intact     3
  committed ranks the guard-off census does not carry: 0
  cluster_key unique across the 3 committed row(s): 0 collision(s)
  of the moved ranks, 0 hold a guard-off row of the same size and 0 share no address with it
  guard-off membership delta over the 3 rank(s) the two censuses share: 0 address-slots

  cluster_key    name             committed    guard-off     size  delta  verdict
  k000000000001  -                main-ec-001  main-ec-001      2      0  intact
  k000000000002  -                main-ec-002  main-ec-002      1      0  intact
  k000000000003  -                pd-001       pd-001           2      0  intact

$ python3 ec/tools/xdata_moved_ranks.py pair --label intact \
    --old /tmp/intcoll/clean-committed.csv --new /tmp/intcoll/intact-off.csv
pair intact
  committed  /tmp/intcoll/clean-committed.csv: 3 rows
  guard-off  /tmp/intcoll/intact-off.csv: 3 rows
  moved      0  (main-ec 0, pd 0)
  intact     3
  committed ranks the guard-off census does not carry: 0
  cluster_key unique across the 3 committed row(s): 0 collision(s)
  cluster_key COLLISION: 1 of the 3 guard-off keys carried by more than one rank (k000000000009 on main-ec-001, main-ec-002) -- the moved and intact counts above are per rank and are unaffected; across and --swept do not read this census, but cause's population and its per-program holder index are over the key and are not
  of the moved ranks, 0 hold a guard-off row of the same size and 0 share no address with it
  guard-off membership delta over the 3 rank(s) the two censuses share: 0 address-slots

  cluster_key    name             committed    guard-off     size  delta  verdict
  k000000000001  -                main-ec-001  main-ec-001      2      0  intact
  k000000000002  -                main-ec-002  main-ec-002      1      0  intact
  k000000000003  -                pd-001       pd-001           2      0  intact
```

Both `pair` blocks above are complete as printed, down to the per-key table. The
`across` and `cause` blocks further down are **not** — each is cut at the end of
its counting section, and each says so with a `…` where the paste stops, so a
reader re-running one is not left expecting the block to end there.

The guard-off census is 3 rows under 2 distinct keys, and the only line a reader
can take for "this report looked and there is no collision" says the opposite
about the census `cause` reads by key. That line was printed **unconditionally**
precisely so that silence means clean — which is what makes checking one census
of the two a worse failure than printing nothing at all.

**2. An intact-rank collision prints nothing in `across`.** `collapsed` ran
`duplicate_keys` over the *moved* ranks, so `collapse_line` was silent whenever
the colliding ranks were not movers. Three committed rows, two of them sharing
`k9` and both intact:

```console
$ python3 <PRE-CHANGE> across --label-a A --label-b B \
    --old-a /tmp/intcoll/dup-committed.csv --new-a /tmp/intcoll/dup-off.csv \
    --old-b /tmp/intcoll/dup-committed.csv --new-b /tmp/intcoll/dup-off.csv
across A -> B
  keys in both committed censuses: 2; in one only: 0 / 0
     0  moved in A, intact in B
     0  moved in both
     0  intact in A, moved in B
     2  intact in both
  of the one-sided keys, 0 moved in A and 0 moved in B
  closes: 0 - 0 = 0, over the four terms: (0 - 0) + (0 - 0) = 0
…

$ python3 ec/tools/xdata_moved_ranks.py across --label-a A --label-b B \
    --old-a /tmp/intcoll/dup-committed.csv --new-a /tmp/intcoll/dup-off.csv \
    --old-b /tmp/intcoll/dup-committed.csv --new-b /tmp/intcoll/dup-off.csv
across A -> B
  keys in both committed censuses: 2; in one only: 0 / 0
     0  moved in A, intact in B
     0  moved in both
     0  intact in A, moved in B
     2  intact in both
  the counts below are keys, not the ranks `pair` counts: 4 committed rank(s) across 2 generation(s) share a key with another committed rank (A: k000000000009 on main-ec-001, main-ec-002; B: k000000000009 on main-ec-001, main-ec-002)
  of the one-sided keys, 0 moved in A and 0 moved in B
  closes: 0 - 0 = 0, over the four terms: (0 - 0) + (0 - 0) = 0
…
```

The `…` in each `across` block is this write-up's, not the tool's: both runs
continue past the count-close, through the deciles, the four mean-delta lines,
the rank-shift section and a per-key table, and neither is pasted whole. The
quoted part is every line of the counting section, which is where the collapse
either appears or does not.

No collision line anywhere in the before column. The write-up's own §2 argument
applies verbatim: a key count that reads as a population while a rank is hidden
is *"a false negative about the census, not a small number"*. The #888 fixture
cannot catch this — its third rank `main-ec-003` is intact but shares `k9` with
two *movers*, so `collapsed` is non-empty and the line prints for the wrong
reason.

**3. And the population of `cause`, which is the re-keying whose counts *are* a
population.** `keys_a`/`keys_b` are the denominators of every rate in the
report, and a collision made them come out short with nothing else looking
wrong — 3 rows over 2 keys, printed as `2 guard-off key(s) in A`:

```console
$ python3 ec/tools/xdata_moved_ranks.py cause --label-a A --label-b B \
    --old-a /tmp/intcoll/clean-committed.csv --new-a /tmp/intcoll/intact-off.csv \
    --old-b /tmp/intcoll/clean-committed.csv --new-b /tmp/intcoll/intact-off.csv \
    --old-a-registers /tmp/intcoll/regs/a-on.csv --new-a-registers /tmp/intcoll/regs/a-guard.csv \
    --old-b-registers /tmp/intcoll/regs/b-on.csv --new-b-registers /tmp/intcoll/regs/b-guard.csv
cause A -> B
  page 0x0300-0x05FF; the added set is 1 address(es)

  cluster_key COLLISION: 1 of the 3 guard-off keys carried by more than one rank (k000000000009 on main-ec-001, main-ec-002) -- the population and every rate's A column are over the key, so a shared key hides a rank
  cluster_key COLLISION: 1 of the 3 guard-off keys carried by more than one rank (k000000000009 on main-ec-001, main-ec-002) -- the population and every rate's B column are over the key, so a shared key hides a rank
  the population: 2 guard-off key(s) in A, 2 in B
    2 of the first reappear in the second under the same key, 0 only in the first, 0 only in the second
    the rank delta of those 2: 0 on 2, +/-1 on 0, +/-2 on 0, further on 0; mean +0.00, range +0..+0
    their members: 5 membership(s) over 5 distinct address(es); 0 of them in the page, held 0 time(s); B's holds 0
…
```

That `…` is this write-up's rather than the tool's, as in case 2: the run
continues past the population block through the per-cell section, the rates
table, the page-rate bands and a per-key table, and none of that is pasted. The
whole of the collision evidence is inside the quoted part — the two
`cluster_key COLLISION` lines the next paragraph is about.

The two lines sit **above** the block they qualify, not beside it, because the
figure two lines below them is the one that is short.

## 3. What changed, per site

- **`collision_line` `:170` grew a `label` and an `only_if_collision`.** The word
  `committed` was hardcoded in both f-strings, which is *why* the guard-off
  censuses could not be pointed at the helper at all and were carrying their own
  spelling. `label="committed"` reproduces today's two sentences **byte for
  byte** — the clean one is quoted in a fenced transcript in
  [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md)
  §2 and did not move — and `label="guard-off"` is the new census. The
  `only_if_collision` flag is what keeps the swept report's line conditional: it
  is the only call that passes it, and without it `--swept` would gain two lines
  on every clean run.
- **`pair_report` `:335-344` prints the line for both censuses it reads.** The
  committed line's text is unchanged; the guard-off line's consequence names the
  views that actually read *that* census, which are `cause`'s population and its
  `holders_by_program` index — `across` and `--swept` never see a guard-off
  census, and saying otherwise would be a second, wrong claim.
- **`collapsed` `:455` is the whole committed census, not its moved ranks.**
  `shared`, `only_a`, `only_b` and the four cells are all derived from `a` and
  `b`, which are the whole committed censuses, so a whole-census check is the
  population the claim needs. This is a strict widening: on a clean census both
  are empty. The `moved` local and a second `moved_ranks` call died with it.
- **`collapse_line` `:459` says "committed rank(s)", not "moved rank(s)".** The
  population is no longer the moved ranks, so the sentence could not keep
  describing them. The silence-on-clean property is kept, and is better
  supported now: the census in question is the same one `pair` checks
  unconditionally.
- **`swept_report` `:751-758` folded into `collision_line`.** Its hand-rolled
  sentence was the third spelling of the same fact — "N of the M committed
  keys" against "N of its M keys" — and it is what let the property end up
  checked at one site and not another. The `hides a rank` clause is kept
  verbatim; it is the sentence's actual content and a self-test case asserts it.
  **This is the one line whose text changes**, and the two transcripts quoting
  it are re-transcribed in place below.
- **`cause_report` `:963-967` gained the two guard-off lines**, and
  `keyed_by`'s docstring `:126-150` is narrowed from "every caller" to the unit
  that is actually enforced, and made checkable (§7's fourth case).

## 4. No published figure moves, re-derived rather than asserted

Both pairs were regenerated exactly as
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §1–§2 prescribes —
`xdata_register_map.py --no-eq-guard` writing to `/tmp` for both — and the
pre-change tool was diffed against this one. The 430-row half needs that commit's
decompiled tree, which was read out with `git archive e169a0e4 | tar -x -C
/tmp/old` rather than by adding a worktree; the archive is a read, and the tree
it produced reproduced the committed 430-row census and its 439-row guard-off
regeneration exactly, which is the check that the archive is the right input.

```console
$ diff <(python3 <PRE-CHANGE> pair --label 'the 430-row pair' ...) \
       <(python3 ec/tools/xdata_moved_ranks.py pair --label 'the 430-row pair' ...)
7a8
>   cluster_key unique across the 439 guard-off row(s): 0 collision(s)

$ diff <(python3 <PRE-CHANGE> pair --label 'the 439-row pair' ...) \
       <(python3 ec/tools/xdata_moved_ranks.py pair --label 'the 439-row pair' ...)
7a8
>   cluster_key unique across the 445 guard-off row(s): 0 collision(s)

$ diff <(python3 <PRE-CHANGE> across ...) <(python3 ec/tools/xdata_moved_ranks.py across ...)
$ diff <(python3 <PRE-CHANGE> across ... --swept 0x0460 0x0468 ... 0x09CE) \
       <(python3 ec/tools/xdata_moved_ranks.py across ... --swept 0x0460 0x0468 ... 0x09CE)
$ diff <(python3 <PRE-CHANGE> cause ...) <(python3 ec/tools/xdata_moved_ranks.py cause ...)
3a4,5
>   cluster_key unique across the 439 guard-off row(s): 0 collision(s)
>   cluster_key unique across the 445 guard-off row(s): 0 collision(s)
```

**`across` and `across --swept` diff empty; `pair` gains one line and `cause`
gains two, and every one of the three added lines reads 0 collisions.** The two
empty diffs are the load-bearing half: the whole-census check and the old
moved-subset check are *both* empty on a clean census, so widening the
population is a superset rather than a change of behaviour. The `cause` lines
are the two this change adds, which is why `cause` does not diff empty — the
check it was missing is the one it now prints.

The figures themselves come back unchanged: **366 / 64** and **315 / 124**, with
351-of-366 and 307-of-315 holding a same-sized row and 364 / 311 sharing no
address; the flip table **71 / 266 / 23 / 40**; `closes: 366 - 315 = 51, over
the four terms: (71 - 23) + (29 - 26) = 51` with no `MISMATCH`; and the `across`
and `cause` transcripts their pages publish.

**And all four censuses were checked, not just the two committed ones**, because
a precondition nobody has looked at is a precondition that has not been
measured — the same table
[`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md) §4
publishes, re-derived on this tree and measuring the same thing:

| census | rows | distinct `cluster_key` | collisions |
|---|---:|---:|---:|
| `ec/annotations/xdata-clusters.csv` | 439 | 439 | 0 |
| the 430-row census at `e169a0e4` | 430 | 430 | 0 |
| guard-off regeneration of the 430-row pair | 439 | 439 | 0 |
| guard-off regeneration of the 439-row pair | 445 | 445 | 0 |

The two guard-off CSVs are regenerations written to `/tmp` and are not committed
artifacts; they are listed because this run read them and the new lines are what
read them. `xdata_register_map.py --check` passes on the committed pair (1326
register rows, 439 cluster rows, both exit 0), and the CSVs are not touched.

## 5. Calibration: what is and is not claimed

- **This is not a claim that any census this tree holds collides.** They do not,
  and §4 measures all four. Nothing here refutes `TheContentKey`'s uniqueness
  assertion or `xdata_register_map.py`'s content hash, and nothing here is
  evidence about a real cluster.
- **"These four censuses do not collide" is a statement about four files**, and
  §4 names them. "The censuses cannot collide" would not be: the guard-off
  generation is written to scratch, nothing holds *its* key uniqueness between
  runs, and the next re-derivation is a file that does not exist yet. That is
  the whole reason the check is in the tool rather than in a note.
- **The fixtures are not evidence about any census.** A `cluster_key` is a
  content hash over the program and the sorted membership, so two ranks with
  different memberships carrying one key is a forgery the tool's own hash would
  never produce. The check has to hold for one anyway, because the census it is
  not guaranteed to receive is written by a regeneration, not by
  `xdata_register_map.py`'s hash of the same tree. `check_cluster_citations.py`
  reports nothing for this file, which is what the fixture keys being absent
  from the committed census buys.
- **A collision is still reported, not refused.** No `--strict` flag is added and
  none is wanted: the counts are correct under a collision, what is ambiguous is
  which rank a key names, and that is a caveat to state rather than a run to
  abort. [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md)
  §3 argued for that and this change does not reopen it.
- **No gate is wired.** The collision check is still outside
  `.github/scripts/agent-gates.sh`, for the reason
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §8 gives: the tool is
  a read-only investigation aid, and a collided *committed* census already fails
  `xdata_register_map.py --check`, which compares those CSVs cell for cell.
  Wiring `--self-test` into a gate at all is issue #921's, and is untouched here.
- **Two already-stale pins are left where they are.**
  `tools/README.md`'s `xdata_moved_ranks.py:243` and
  `xdata-write-direction-correction.md`'s `:181` name lines for `deciles()` and
  `write_movement()` that were already wrong on this issue's base `31f683e5`
  (`deciles()` was at `:436` and `write_movement()` at `:227`; they are at `:487`
  and `:257` here). Deciding what a drifted pin was meant to name is a next
  pass's call and not a merge's, per `tools/README.md`'s own rule and
  [`test-line-pin-census.md`](test-line-pin-census.md) §7. Those two are the
  ones this change can see; it is not a claim that the family has no others.
  The one pin this change *breaks* —
  [`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md)
  `:436`, which was correct before this and is not after it — is repointed to
  `:487`.
- **What this opens, and is not done here.** `--self-test` creates its scratch
  directory with `tempfile.mkdtemp(prefix="xdata-moved-ranks-")` and never removes
  it (`shutil` is not imported), so every run leaks a directory under `/tmp`.
  That is a separate defect, found while measuring this one, and it is not fixed
  by it.

## 6. The in-place amendments

Per [`../findings.md`](../findings.md) §4a-4d, the superseded text stays visible
and is corrected beside it rather than edited down. Three of the four are in
[`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md), which
is where the property was first argued:

- **§3's "at each of its three uses".** It was three of six, over three of the
  four censuses. The argument for checking at each view is unchanged and is now
  what the tool does.
- **§2's "a false negative about the census".** True, and it applied only to
  moved ranks: the argument was made over a fixture whose colliding ranks were
  movers, and the check could not reach a census whose colliding ranks were not.
  §2's first transcript above is that case.
- **§6's bullet on `holders_by_program()`.** It reads as though `cause` were
  covered; it was covered over the moved ranks alone, and `cause`'s guard-off
  population — the one place a re-keyed census *is* the denominator — had no
  check at all.
- **§2's two `--swept` transcripts.** The four collision lines in them change
  wording with the folding in §3, so the blocks are re-transcribed to this
  tree's run; the before-and-after they are arguing about is unchanged and is
  restated in §2 above.

The fourth is [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §9, whose
transcript publishes the `--self-test` headcount and its arithmetic, and
`docs/findings.md` §68 and `tools/README.md`, which publish the same figure. All
three are corrected to the figure §7 below measures, and the figures they
carried — 31, 36, 39, 45 and 49 — stay visible, because each is true of the tree
it was measured on.

## 7. The test that proves it

`--self-test` goes from **49 to 53**, and the four are the shape the six before
them could not express. The headcount is measured, not targeted: `diff` of the
`ok` lines of the pre-change run against this one appends exactly four checks and
changes exactly one earlier check's text, and that one is the widened
expectation below.

```console
$ python3 ec/tools/xdata_moved_ranks.py --self-test | grep -c '^  ok'
53
```

The four, in print order at 50–53:

1. **`pair` checks the census it did not check** — a clean committed census
   beside a guard-off one with two intact ranks on one key. Asserts both a clean
   line for the first and a `COLLISION` line naming the key and both ranks for
   the second, with `moved 0` and `intact 3` so the collision is visible as one
   that costs no count.
2. **`across` reports an intact-only collision** — a committed census with two
   ranks on one key and neither a mover. Asserts `collapsed` is non-empty, the
   line emits, `0` moved, and no `MISMATCH`. This is the case the six could not
   express, and it is the one that goes red without `moved_ranks`' re-keying.
3. **`cause` reports a guard-off collision** — case 1's fixture over the
   self-test's own `write_registers()` fixtures, so `cause_report` is callable.
   Asserts both guard-off lines appear, *above* the `the population:` line they
   qualify, and that the population reads 2 keys over 3 rows. This is a measured
   replacement for a static reading of the `cause` sites.
4. **The coverage claim itself.** One case running all four views —
   `pair`, `across`, `--swept`, `cause` — over one census that collides, and
   asserting a line for each of the **six** (view, census) pairs
   `keyed_by`'s docstring names. The wanted substring is always the line the
   check emits and never the cross-reference's own `cluster_key` column header,
   which every report printing a key-indexed table has and which says nothing
   about whether the check ran — a case that settled for the bare word would
   have passed with the check deleted. **This is the first case that holds the
   docstring's claim rather than restating it.**

**It can go red, and that was demonstrated rather than asserted**, by reverting
each edit in a scratch copy and re-running:

| revert | checks that go red |
|---|---|
| `collapsed` back to the moved subset | the widened expectation, case 2 |
| `cause`'s two guard-off lines | case 3, case 4 |
| `pair`'s guard-off line | case 1, case 4 |
| `swept_report`'s loop | the #888 swept case, case 4 |
| `collapse_line` returning `[]` | the widened expectation, case 2, case 4 |

**Four of the five reverts are red on the coverage case**, which is the case the
whole change exists to make checkable. **The fifth is not, and that is recorded
here rather than rounded off**: reverting the `collapsed` widening in a scratch
copy leaves the coverage case green, and the reason is the same one §2 uses
against the #888 fixture. The coverage case's census collides on a key two of
whose three ranks *moved*, so `collapsed` is non-empty over the moved subset and
over the whole census alike and `collapse_line` emits either way. The coverage
case holds the *views that reach a census*; which population `collapsed` draws
from is case 2's, and case 2 is what goes red. A `--self-test` that can only go
green is not a test, and
[`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md) §7
already uses those words; the new cases are chosen so they can go red.

**The one earlier check whose expectation moved is amended in place, with what
it was left visible beside it.** It asserted
`{key(9): ["main-ec-001", "main-ec-002"]}` and `"4 moved rank(s)"`; under the
whole-census population the key carries a third rank (`main-ec-003`, intact) and
the count is 6. The two movers, the four-term closure and the absence of a
`MISMATCH` are the same three assertions as before, which is what a widening is
supposed to look like from here.

`python3 -m unittest discover -s ec/tools -p 'test_census_test_line_pins.py'`
is green and the census is unmoved: **105 records in 27 files, 78 spellings, 57
targets, {73 resolves, 32 declined}** in the `5/19/10/6/33` shape split — before
and after this change, and after the new file and the amended key-collision
file. **The read denominator is the one figure here that does not hold on both
sides of that: 148 markdown files read on `main` at `271389d7` and 149 on the
merged tree**, and the extra one is this file's own existence. (A local checkout
carries the untracked `.claude-pr/CLAUDE.md` the tool's walk reads, so the same
run prints `150` there; the figures here are the clean tree's.)
**Two earlier passes of this paragraph read otherwise, each right about the tree
it was measured on, so both stay visible per
[`../findings.md`](../findings.md) §4a-4d.** The first gave `73 records in 26
files, 46 lines, {57 resolves, 16 declined}`, a pristine pre-`#771`
`origin/main` run. The second gave `58 targets` in a `5/17/10/6/35` split over
`148` read, and that is this branch's own tree at `13dfc146` — **a commit the
review round rewrote, so `git cat-file -t 13dfc146` does not resolve it** — the
run [`test-line-pin-census.md`](test-line-pin-census.md) records for it. The
shape split is reproducible without that commit: `git archive 84a89d9a`, then
that tree's own `python3 ec/tools/census_test_line_pins.py`, prints `58`
targets in `5/17/10/6/35` over its own `147`, which is where the `84a89d9a`
figure in the same sentence comes from. The `148` denominator is the branch
tree's own extra file, and **no commit in this repository reads `58` over
`148`** — `271389d7` is the next tree that reads `148` and it is already past
#930's repoint, at `57`/`5/19/10/6/33` — so it stands as a superseded branch
reading rather than a figure a reader can re-run. **Neither reading
is wrong about the tree it came from; what does not survive is carrying the
second into a tree `#930` had already moved**, its repoint of the two `:563` pins
being the whole of `58 → 57` and `5/17/10/6/35 → 5/19/10/6/33`, and its own new
write-up the one file that takes `main`'s read count from `147` to `148` — a
different file arriving at the number this branch reached by adding this one. The
reading that supersedes both is
[`test-line-pin-census.md`](test-line-pin-census.md)'s `#929` × `#930` merge
section, which is where these three figures are kept rather than restated a
third time; [`tools/README.md`](../../tools/README.md)'s sixteenth note carries
the same correction in prose.
**The `73` that appears in each of those and in the block above is a coincidence
of arithmetic and not a shared measurement**, being `resolves` in the block above
and `resolves + declined` in the first pass's and the fifteenth note's.

This write-up and its amendments add **zero** `test_*.py:NNN` spellings and
remove none, so they cite tests by class name —
`test_xdata_cluster_names.py::TheContentKey` — which is the form the census
declines. `python3 -m unittest discover -s ec/tools` is green except for
`test_check_cluster_citations`, which is red on the base `31f683e5` too with the
same single failure: **#822's** write-up at
`xdata-cluster-names-guard-off-recipe.md:220`, named in that file's own closing
note and in `tools/README.md`'s merged-tree note. This change neither fixes it
nor adds to it.
