# A duplicated `cluster_key` was a quieter number, and the count that read it is now keyed on the rank (issue #888)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure below is
the output of a command over committed text or over a synthetic fixture, with
every scratch output under `/tmp` and `git status --porcelain` printing nothing
after the runs. The four inputs the real figures read are the two
`xdata-clusters.csv` generations and the two guard-off regenerations of them,
all of them files; the fixture is written by the tool's own `--self-test` and
describes no cluster that exists. Same framing as
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):3-11.

**The calibration comes first, because it is the whole limit of the claim: the
committed censuses do not collide, and this change moves no published number.**
§4 re-derives every figure the fall measurement publishes and gets all of them
back. What is below is that the tool's headline quantity was a dict length
whose precondition was documented in a sibling function and exercised by no
case — a latent defect, found by making the case reachable, not a wrong figure
found in the tree.

## 1. The mechanism: a map cannot report that it lost a row

`moved_ranks()` walked the committed census and stored each moved rank as
`out[row["cluster_key"]] = (row, other)`. `pair_report()` then reported
`len(moved)`. A `cluster_key` is a content hash over the program and the sorted
membership, so two ranks in one census carrying one key is not supposed to
happen — and a dict comprehension is the one place that would turn it into a
number rather than an error, because a map that already holds the key simply
overwrites the row it had.

Three things followed from that, and all three are quiet:

- **`len(moved)` was one short per collided pair.** Two ranks moved, one key,
  `moved 1`.
- **`intact` absorbed the same error.** It is computed as
  `len(common) - len(moved)`, so it went up by exactly what `moved` went down.
  `moved + intact == |common|` closed *because* both halves were computed from
  the one number that was wrong — which is the arithmetic
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §2 leans on to
  verify the count, so the check that would have caught it could not.
- **The intact listing lost a rank too, one line further down.** It tested
  `row["cluster_key"] not in moved`, so an *intact* rank sharing a key with a
  moved rank was dropped from a listing that was supposed to show it. The
  issue does not name this one; it is the same collision, and the same edit
  fixes it.

`keyed_by()`'s own docstring stated the precondition — "Keys are unique within
a census — `test_xdata_cluster_names.py::TheContentKey` holds that — so this is
a bijective re-keying and the last row wins for none" — and its output is used
as injective by `flip_table()` and `swept_report()`. The second clause is the
one that can fail, and `moved_ranks()` built the same shape one function away
from the function that documented the assumption.

## 2. Before and after, on a fixture the old `--self-test` could not express

Every fixture in the old suite gave each rank its own `cluster_key`, because
`write_census()` takes a key per row and every caller supplied a distinct one —
so the case was not merely untested, it was unreachable. Three ranks below share
one key and two of them change membership, which is the one shape that loses
from both listings at once. The before column is the **pre-change** tool —
`git show bdfddcfd:ec/tools/xdata_moved_ranks.py`, run from a scratch copy of
that file. `bdfddcfd` is this branch's base: it is `HEAD^1`, and `origin/main`
at this merge, so `git show HEAD^1:...` and `git show origin/main:...` name
these same bytes and either ref names the baseline. `HEAD` deliberately does
not: after this merges, `git show HEAD:ec/tools/xdata_moved_ranks.py` *is* the
post-change tool, so diffing it against the working tree reports no difference
at all and an empty diff would read as "no published figure moved" when it
means only that the recipe was wrong. The `<PRE-CHANGE>` placeholders below
stand for that scratch
path. Both columns run over the same two files:

```console
$ python3 <PRE-CHANGE> pair --label dup \
    --old /tmp/dupfix/dup-committed.csv --new /tmp/dupfix/dup-off.csv
pair dup
  committed  /tmp/dupfix/dup-committed.csv: 4 rows
  guard-off  /tmp/dupfix/dup-off.csv: 4 rows
  moved      1  (main-ec 1, pd 0)
  intact     3
  committed ranks the guard-off census does not carry: 0
  of the moved ranks, 1 hold a guard-off row of the same size and 0 share no address with it
  guard-off membership delta over the 4 rank(s) the two censuses share: 4 address-slots

  cluster_key    name             committed    guard-off     size  delta  verdict
  k000000000009  -                main-ec-002  main-ec-002      2      2  moved
  k000000000003  -                pd-001       pd-001           2      0  intact

$ python3 ec/tools/xdata_moved_ranks.py pair --label dup \
    --old /tmp/dupfix/dup-committed.csv --new /tmp/dupfix/dup-off.csv
pair dup
  committed  /tmp/dupfix/dup-committed.csv: 4 rows
  guard-off  /tmp/dupfix/dup-off.csv: 4 rows
  moved      2  (main-ec 2, pd 0)
  intact     2
  committed ranks the guard-off census does not carry: 0
  cluster_key COLLISION: 1 of the 4 committed keys carried by more than one rank (k000000000009 on main-ec-001, main-ec-002, main-ec-003) -- the moved and intact counts above are per rank and are unaffected; across and --swept join on the key and are not
  of the moved ranks, 2 hold a guard-off row of the same size and 0 share no address with it
  guard-off membership delta over the 4 rank(s) the two censuses share: 4 address-slots

  cluster_key    name             committed    guard-off     size  delta  verdict
  k000000000009  -                main-ec-001  main-ec-001      2      2  moved
  k000000000009  -                main-ec-002  main-ec-002      2      2  moved
  k000000000009  -                main-ec-003  main-ec-003      1      0  intact
  k000000000003  -                pd-001       pd-001           2      0  intact
```

**What the before column shows, which is worse than a count that is one
small.** It claimed `moved 1` and `intact 3` — four ranks, correctly summed,
from three wrong inputs — and printed **two** listing rows for it. The one
mover it named was whichever rank the dict happened to keep last, so
`main-ec-001` was not in the report at all, and the intact rank sharing the key
was not either. Nothing on that page is red: the arithmetic closes, the row
count is plausible, and the key in the first column is the key the CSV holds.

**The key-indexed half cannot be fixed the same way, and says so instead.**
`across` joins two censuses on the key by design — that is what makes a cluster
findable across a renumbering — so a collision there is a genuine ambiguity
about *which* rank a key names, not a corrupt measurement. The counts are
labelled as key counts and the loss is named:

```console
$ python3 ec/tools/xdata_moved_ranks.py across --label-a A --label-b B \
    --old-a /tmp/dupfix/dup-committed.csv --new-a /tmp/dupfix/dup-off.csv \
    --old-b /tmp/dupfix/dup-committed.csv --new-b /tmp/dupfix/dup-off.csv
across A -> B
  keys in both committed censuses: 2; in one only: 0 / 0
     0  moved in A, intact in B
     1  moved in both
     0  intact in A, moved in B
     1  intact in both
  the counts below are keys, not the ranks `pair` counts: 4 moved rank(s) across 2 generation(s) share a key with another moved rank (A: k000000000009 on main-ec-001, main-ec-002; B: k000000000009 on main-ec-001, main-ec-002)
  of the one-sided keys, 0 moved in A and 0 moved in B
  closes: 1 - 1 = 0, over the four terms: (0 - 0) + (0 - 0) = 0
  ...
```

**The four-term closure closes anyway**, which is the point: it is set algebra
over one key universe, so it cannot distinguish "two ranks moved" from "one
key that two ranks moved under". §3's `(71 − 23) + (29 − 26) = 51` would have
closed on a collapsed census exactly as it does now.

**`--swept` is where the collision stops being a smaller number.** Its holder
index is `keyed_by` over a whole census, so a key two ranks share survives
attached to whichever of the two rows was read last, and the other rank's row
is not in the index at all:

```console
$ python3 <PRE-CHANGE> across --label-a A --label-b B \
    --old-a /tmp/dupfix/dup-committed.csv --new-a /tmp/dupfix/dup-off.csv \
    --old-b /tmp/dupfix/dup-committed.csv --new-b /tmp/dupfix/dup-off.csv --swept 0x0E
  swept addresses: 1
  address  cluster_key    program  rank A       rank B       verdict
  0x0E     -              -        -            -            in no committed cluster
  0 committed cluster(s) hold at least one of the 1: 0 main-ec, 0 pd; 0 hold all of them; 0 address(es) have a second holder
  of those 0, 0 flipped; 0 moved in A and 0 moved in B

$ python3 ec/tools/xdata_moved_ranks.py across --label-a A --label-b B \
    --old-a /tmp/dupfix/dup-committed.csv --new-a /tmp/dupfix/dup-off.csv \
    --old-b /tmp/dupfix/dup-committed.csv --new-b /tmp/dupfix/dup-off.csv --swept 0x0E
  swept addresses: 1
  address  cluster_key    program  rank A       rank B       verdict
  generation A cluster_key COLLISION: 1 of its 4 keys carried by more than one rank (k000000000009 on main-ec-001, main-ec-002, main-ec-003) -- the rows below and the counts that follow them are over the key, so a shared key hides a rank
  generation B cluster_key COLLISION: 1 of its 4 keys carried by more than one rank (k000000000009 on main-ec-001, main-ec-002, main-ec-003) -- the rows below and the counts that follow them are over the key, so a shared key hides a rank
  0x0E     -              -        -            -            in no committed cluster
  0 committed cluster(s) hold at least one of the 1: 0 main-ec, 0 pd; 0 hold all of them; 0 address(es) have a second holder
  of those 0, 0 flipped; 0 moved in A and 0 moved in B
```

**"in no committed cluster" is a *false negative about the census*, not a small
number.** All three `main-ec` ranks of the fixture carry `k000000000009`, so the
key's row is `main-ec-003`'s by the time the index is built — and `0x0E` is held
by `main-ec-001` alone, so the sweep denies an address the census does hold.
Both columns print that denial, because the index was `keyed_by` before this
change too; what the change adds is the collision line above it, which says a
rank is hidden rather than letting the denial stand as a fact about the census.
The fixture key is also one the committed census does not carry.

**The other half of the same index is the quieter one, and it is absorbed
rather than printed wrong.** An address the two colliding ranks *both* hold is
not lost: the surviving rank's row carries it, so it is reported once, against
whichever rank was read last, and the summary's second-holder count counts that
one holder rather than disagreeing with the row above it. Two ranks on one key
(`k000000000009`), both carrying `0x0E` and unchanged between the two
generations, written by the same `write_census()` as the fixture above:

```console
$ python3 ec/tools/xdata_moved_ranks.py across --label-a A --label-b B \
    --old-a /tmp/dupfix/same-committed.csv --new-a /tmp/dupfix/same-off.csv \
    --old-b /tmp/dupfix/same-committed.csv --new-b /tmp/dupfix/same-off.csv --swept 0x0E
  swept addresses: 1
  address  cluster_key    program  rank A       rank B       verdict
  generation A cluster_key COLLISION: 1 of its 2 keys carried by more than one rank (k000000000009 on main-ec-001, main-ec-002) -- the rows below and the counts that follow them are over the key, so a shared key hides a rank
  generation B cluster_key COLLISION: 1 of its 2 keys carried by more than one rank (k000000000009 on main-ec-001, main-ec-002) -- the rows below and the counts that follow them are over the key, so a shared key hides a rank
  0x0E     k000000000009  main-ec  main-ec-002  main-ec-002  intact in both
  1 committed cluster(s) hold at least one of the 1: 1 main-ec, 0 pd; 1 hold all of them; 0 address(es) have a second holder
  of those 1, 0 flipped; 0 moved in A and 0 moved in B
```

Two holders read as one, and `0 address(es) have a second holder` is the number
that says so — the count is over the key's rows, so the collision costs it the
holder rather than producing a value that looks wrong. That is why this is a
reporting fix at the `keyed_by` sites and not only a re-keying of
`moved_ranks()`: the swept cross-reference is still built over the key, and what
the change buys is that the report says so instead of reading as a census that
does not hold the address.

## 3. What changed, in one helper checked at each of its three uses

- **`moved_ranks()` is keyed on `cluster_id`.** A rank is the key of the dict
  `clusters_of()` returns, so this join cannot collapse by construction, and
  the predicate is untouched — the suite's own two lines, string for string,
  which is what `test_xdata_cluster_names.py:588`'s `> 300` floor is applied
  to — `:563` until #890 moved it (§5). `len(moved)` is now the number of
  ranks that matched, and `intact`, which is derived from it, follows.
- **`duplicate_keys()` is the check**, over a `{cluster_id: row}` census, and
  `collision_line()` prints it. It runs **unconditionally in `pair`**, beside
  the two counts it qualifies: a run that reports nothing is then a run that
  looked and found nothing, which is a different claim from a run that never
  looked. `across` and `cause` print a line only when the key projection is not
  injective, because they are the key-indexed views and the cost is theirs; on
  any census whose keys are distinct the line is absent and `across`'s output
  is byte-for-byte what it was.
- **`swept_report()` names both generations** and says the holder count is over
  the key, for the reason §2's last transcript shows.
- **The intact-listing test is now `cid not in moved`.** Same collision, a
  different loss, fixed by the same edit.

**No refusal, and no `--strict` flag, and this is a decision rather than an
omission.** Once `moved_ranks()` is rank-keyed, `len(moved)`, the per-program
split and `intact` are all *correct* under a collision; refusing would reject a
run whose headline number is right. What remains ambiguous is the key-indexed
views, and that is a caveat to state. A `--strict` flag would add a second
answer to a question the reports now answer in the text, and the tree's habit
is the other one — [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §3
prints "0 of 400 … zero by construction and is printed rather than assumed"
rather than gating on it. The
collision check is deliberately **not** wired into a gate either, for the reason
`xdata-moved-ranks-fall.md` §8 gives: the tool is a read-only investigation aid,
and a census that collided would already be failing
`xdata_register_map.py --check`, which does compare the committed CSVs cell for
cell. Wiring it is a human's change if it is ever wanted.

## 4. No published figure moves, re-derived rather than asserted

Both pairs were regenerated exactly as
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §1–§2 prescribes — the
`e169a0e4` worktree for the 430-row half, `xdata_register_map.py --no-eq-guard`
writing to `/tmp` for both — and the tool was re-run over the result. The whole
of what changed between this tool and the one the fall measurement used. The
left column is `<PRE-CHANGE>` — the pre-change tool materialised with
`git show bdfddcfd:ec/tools/xdata_moved_ranks.py > /tmp/pre-change.py`, §2's
ref and the same one there, and **not** `git show HEAD`, which after this merge
resolves to this same tree's tool and would make both columns the after column:

```console
$ diff <(python3 <PRE-CHANGE> pair --label 'the 430-row pair' ...) \
       <(python3 ec/tools/xdata_moved_ranks.py pair --label 'the 430-row pair' ...)
6a7
>   cluster_key unique across the 430 committed row(s): 0 collision(s)

$ diff <(python3 <PRE-CHANGE> pair --label 'the 439-row pair' ...) \
       <(python3 ec/tools/xdata_moved_ranks.py pair --label 'the 439-row pair' ...)
6a7
>   cluster_key unique across the 439 committed row(s): 0 collision(s)
```

One added line each, and the figure on it is zero. `across`, `across --swept`
and `cause` diff **empty** over the same four files. The figures themselves
come back unchanged: **366 / 64** and **315 / 124**, with 351-of-366 and
307-of-315 holding a same-sized row and 364 / 311 sharing no address; the flip
table **71 / 266 / 23 / 40**; `closes: 366 - 315 = 51, over the four terms:
(71 - 23) + (29 - 26) = 51` with no `MISMATCH`; the §4 mean-delta cells
`7.66 / 0.00`, `3.14 / 3.04`, `0.00 / 3.65`, `0.00 / 0.00`; and the
`across` and `cause` transcripts their pages publish, byte for byte.

**Why nothing moved, stated rather than left to the diff.** The old `moved` map
was keyed on the *moved* rows' `cluster_key`s; with those distinct, one rank is
one key and the map's length is the number of ranks, which is the same number
the rank-keyed map holds. The intact listing's `row["cluster_key"] not in
moved` is likewise the same predicate as `cid not in moved` while the keys are
distinct. The figures read `len()` off a dict whose keys were 439 (or 430)
distinct strings, so re-keying it on the ranks that produced them returns the
same length. **This is a statement about the four files this run read, not a
proof that no census can collide** — see §5.

**And all four of them were checked, not just the two committed ones**, because
a precondition nobody has looked at is a precondition that has not been
measured. Over the same run:

| census | rows | distinct `cluster_key` | collisions |
|---|---:|---:|---:|
| `ec/annotations/xdata-clusters.csv` | 439 | 439 | 0 |
| the 430-row census at `e169a0e4` | 430 | 430 | 0 |
| guard-off regeneration of the 430-row pair | 439 | 439 | 0 |
| guard-off regeneration of the 439-row pair | 445 | 445 | 0 |

The two guard-off CSVs are a regeneration written to `/tmp` and are not
committed artifacts; they are listed because this run read them and the new
line is what read them. `git worktree remove /tmp/xdata-old` ran after, and
`git status --porcelain` prints nothing.

## 5. Calibration: what is and is not claimed

- **This is not a claim that the committed censuses have colliding keys.** They
  do not, and §4 measures it. Nothing here refutes `TheContentKey`'s
  uniqueness assertion or `xdata_register_map.py`'s content hash, and nothing
  here is evidence about a real cluster.
- **"The committed censuses do not collide" is a statement about a file**, and
  §4 lists which files. "The censuses cannot collide" would not be: the
  guard-off generation is written to scratch, nothing holds *its* key uniqueness
  between runs, and the *next* re-derivation is a file that does not exist yet.
  That is the whole reason the check is in the tool rather than in a note.
- **The fixture is not evidence about any census.** It is a synthetic
  four-row pair written by `--self-test`, and the keys in §2
  (`k000000000009`, `k000000000003`) resolve to no cluster in the committed
  census — which is also why `check_cluster_citations.py` reports nothing for
  this file.
- **A collision is reported, not refused**, and §3 says why, in the terms of
  what the tool can and cannot say about a run.
- **The `--swept` line does not repair the cross-reference.** Under a collision
  the holder index is still lossy; what changes is that the report says so
  instead of reading as a census that does not hold the address.
- **The `> 300` floor at `test_xdata_cluster_names.py:588` is untouched**, and
  `TheContentKey` is untouched. *(`:563` until #890 — see the amendment below.)*
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §5 argues for the
  floor staying where the recipe's argument put it, and one line in a report is
  not a reason to move a threshold.
- **The two citations of that floor in §3 and here are repointed, and the
  superseded spelling stays visible.** Both were written as `:392` of
  `ec/tools/test_xdata_cluster_names.py`, which is where the floor was on the
  tree this issue was written on. #850 put 239 lines into that file in the same
  window and moved the floor to **`:563`**, so on the tree this lands in `:392`
  is a comment about the checklist's §2b and names nothing here. The superseded
  number is written bare for the reason
  [`../findings.md`](../findings.md) §65 gives: *"This summary names them
  without a resolvable spelling on purpose — a correction that added a 53rd pin
  to the census it is correcting would move the figure it reports."* They are
  repointed rather than left to drift because they are *this issue's own* two
  citations in a file new to the census, not prose a merge shifted under
  somebody else's argument — a new file born citing a line that does not hold
  the claim is a wrong pin, not a superseded record. The four sibling
  citations #850 left where they were — in
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) and
  [`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) — are
  **not** repointed here, per
  [`test-line-pin-census.md`](test-line-pin-census.md)'s "no citing prose is
  repointed" rule, and they are named in that file's "does not carry" table
  with the line that moved. Both sides of that split are deliberate, and the
  census distinguishes them: these two **carry**, those four do not.

*(Re-measured at the #888 × #890 merge, 2026-09-26: **the clause above is wrong,
and the split it describes is no longer a split.** #890 put 25 lines into
`ec/tools/test_xdata_cluster_names.py` above the floor, which put
`assertGreater(len(moved), 300)` at **`:588`** and turned `:563` into a fixture
row, `("0x0843", ("84", "42"), ("126", "0"))):`. So §3's pin and the one in the
bullet above both now name a line carrying neither the floor nor anything else
of this issue's, and **neither carries**. The sentence stays as written per
`docs/findings.md` §4a-4d because it was true of the tree this issue was written
on and the line moved underneath it, not because it was re-checked and found
right. [`test-line-pin-census.md`](test-line-pin-census.md) measures the same two
rows the same way: both **does not carry** † at shape `other`, in its per-pin
table, in its finding 7 — "the pins were correct when written and the line moved
underneath them" — and in its follow-up 1, where they are "a third kind of
follow-up again": #850's four were already stale when that census found them,
whereas these two were **correct** when #888 wrote them and #890's repoint made
them stale in this very merge, so nothing in #888 could have known. **All six
read `does not carry`; the other four are just older.** Neither pair is
repointed here, and that is the census's decision rather than an omission: its
§7 rule is that the merge which makes citing prose stale does not repoint it, the
repointing lives in that file's follow-up list, and both pairs name the same
target, `:588`. That line number is written bare here for the reason
[`../findings.md`](../findings.md) §65 gives: a correction that added a 46th
spelling and a twelfth `assertion` to the census it is correcting would move two
of the very figures it is reporting.)*

*(**And again at issue #930, which takes the amendment above back — the second
correction in this section, and the first one to undo another.** The two
citations in §3 and in the bullet above are repointed to `:588`, where the floor
is, with the superseded `:563` written bare beside them. **So the split §5
describes is a split again**: both carry, `:588` is an `assertion` again, and
*"these two **carry**, those four do not"* is once more what this section says.
That is a reading of the two cited lines, not a verdict from a tool —
`census_test_line_pins.py` declines to render one. The four are still `does not
carry`, and are deliberately untouched in the same pass: they are #920's, a
different finding with a different provenance, and doing both at once would
collapse the distinction this section and the census between them exist to
record. The amendment above stays written as it stands, per §4a-4d: it was true
of the tree it was written on, and the two lines it describes went stale in a
merge and were then repointed in a follow-up rather than in the merge that broke
them — which is the follow-up list doing the work §7's rule assigns to it, and
not a licence to repoint anyone else's prose in the same pass. The argument, the
before-and-after run and the counts the repoint moved are
[`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md). Line numbers are
written bare here for the reason the clause above gives: spelled out, the
correction would be the 79th spelling in the census it is reporting on, and
would move two of the very figures it reports.)*

## 6. What this opens

- **`write_census()` could take an optional key per row it is told to repeat**,
  so the fixture above stops needing its CSV written by hand. Not done: the
  fixture is five lines in the tool's own `--self-test` and a second knob on a
  fixture writer is not worth the surface.
- **The other `keyed_by` consumer is `holders_by_program()`**, which the `cause`
  mode indexes with. `cause` now prints the same collapse line `across` prints,
  because it draws its cells from the same join; what is *not* done is teaching
  `destination()` to prefer a rank over a key, which would be a change of what
  the mode measures rather than a report of it.
- **The census's own `xdata_register_map.py --check` compares the committed CSVs
  cell for cell**, so a collided committed census fails there already. That is
  why no gate is added here, and it is the reason to leave it that way rather
  than a gap nobody has looked at.

## 7. The test that proves it

`--self-test` goes from 25 checks to 31, and the six new ones are the case the
old suite could not reach. The whole transcript is reproduced in
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §9, which keeps its own
14-line snapshot visible beside the correction.

*(Re-measured at the #888 merge, 2026-09-26, and the figure above is left as it
was written because it is true of the tree this issue was written on, per
`docs/findings.md` §4a-4d. On the merged tree the headcount is **30 to 36**, not
25 to 31: the five in between are #889/#917's five `deciles()` cases, which
landed in the same window, and the six are still this issue's. (`e611e065` is
the base as it stood on the day, which is why it is not the `bdfddcfd` §2 and
§4 diff against: #900 and #923 have landed on the tool since, so the two refs
name different revisions. §7's counts are the day's, and the later merges'
are recorded in the two blocks below.) Measured —
`git show e611e065:ec/tools/xdata_moved_ranks.py > /tmp/pre-888.py && python3
/tmp/pre-888.py --self-test | grep -c '^  ok'` is **30** and `python3
ec/tools/xdata_moved_ranks.py --self-test | grep -c '^ ok'` is **36**, and
diffing those two runs' `ok` lines appends exactly the six
checks transcribed below while changing no earlier check's text. §9's block was
re-transcribed to the same 36, which is why the cross-reference above no longer
counts its lines — it would otherwise send a reader to a 31-line transcript that
is now 36 lines. The same correction is carried in
[`../findings.md`](../findings.md) §68 and in the fall file's §9 note.)**

*(Re-measured once more at the #888 × #891 merge, and **36 becomes 45**, because
#891's nine-check rank-shift block landed beside this issue's after the
measurement above was taken — it prints at 31–39, ahead of this issue's six at
40–45. Measured on the merged tree:
`python3 ec/tools/xdata_moved_ranks.py --self-test | grep -c '^  ok'` is **45**
and the run ends `all checks passed`; the six lines transcribed below are the last
six it prints, unchanged. §9's block is re-transcribed to the same 45, its
arithmetic corrected to `14 + 10 + 1 + 5 + 9 + 6 = 45`, and
[`../findings.md`](../findings.md) §68 and §62 carry the same figure. Nothing
here about the *tool's behaviour* moves — the committed census still measures 439
rows over 439 distinct `cluster_key` values and 0 collisions, and §2's
before/after transcripts still diff as they did. The 31, 36 and 39 stay visible
per `docs/findings.md` §4a-4d, because each is true of the tree it was measured
on.)*

*(And once more at the **#888 × #890** merge, where the **45 becomes 49**:
#890's four `write_movement()` cases are already committed and print at
**21–24**, ahead of this issue's six, which move from 40–45 to **44–49**.
`python3 ec/tools/xdata_moved_ranks.py --self-test | grep -c '^  ok'` on the
merged tree is **49** and the run ends `all checks passed`; the six lines
transcribed in the block below are the last six it prints, unchanged, so that
block needs no edit — the `...` above them is what absorbs the four. §9's block
is re-transcribed to the same 49, its arithmetic corrected to
`14 + 10 + 1 + 5 + 9 + 4 + 6 = 49`, and
[`../findings.md`](../findings.md) §68 and §62 carry the same figure. The `31`,
`36`, `39` and `45` stay visible per `docs/findings.md` §4a-4d, because each is
true of the tree it was measured on.)*

```console
$ python3 ec/tools/xdata_moved_ranks.py --self-test
...
  ok    a duplicated cluster_key costs a moved rank nothing: both movers are counted, and the count is the suite's own two-line predicate's over the same pair, on a census where the two carry one key
  ok    the listing holds a row per rank rather than a row per key, and the counts still close over the ranks the two censuses share: 2 moved + 2 intact = 4 ranks, 4 rows
  ok    the collision is a line of its own, naming the key and every rank carrying it, rather than a count that came out smaller
  ok    a census whose keys are distinct reports no collision and says it looked, and a census that collides reports every rank on the key
  ok    the key-indexed half reports the collision it cannot absorb -- two moved ranks on one key -- and the closure closes anyway
  ok    the swept cross-reference says so too: both generations are named, and the holder count below is over the key rather than over the rank
  all checks passed

$ python3 -m unittest discover -s ec/tools -p 'test_xdata_cluster_names.py'
..............................
Ran 30 tests in 17.886s

OK

$ python3 ec/tools/check_cluster_citations.py
... 2 citation(s), both on xdata-cluster-names-guard-off-recipe.md:220, both #822's ...
```

The known-answer run is §4: both pairs regenerated from committed inputs, both
`pair` reports diffed against the pre-change tool, and `across`, `across
--swept` and `cause` re-run over the same four files. A `--self-test` that can
only go green is not a test, and the fixture here is chosen so it can go red —
it is the one shape that loses from the moved count, the intact listing and the
swept index at once. The 30-test suite is unchanged and is what says the floor
and `TheContentKey` were not touched.

`check_cluster_citations.py` is red on `xdata-cluster-names-guard-off-recipe.md:220`
and was red before this change: **#822's** write-up, named in that file's own
closing note, in `tools/README.md`'s merged-tree note and in
[`../findings.md`](../findings.md) §59. This change neither fixes it nor adds to
it, and the new file contributes nothing to it — which is what §2's transcripts
being kept in fenced blocks, and no table pairing a rank with an address, are
for.
