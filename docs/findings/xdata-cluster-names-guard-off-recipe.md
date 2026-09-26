# The guard-off census, built by the flag instead of by patching a copy of the tool (issue #753)

The write-up for [issue
#753](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/753), which is
about `ec/tools/test_xdata_cluster_names.py` erroring in `setUpClass` instead of
running the six cases of `TheGuardOffRegeneration`. What this branch changes is
that suite's recipe, the stale figures in its own class docstring, a correction
beside a sentence in a sibling write-up about who owned the failure, and this
file.

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure below is
the output of a command over committed text, run with its scratch outputs under
`/tmp`; `git status` was clean of untracked scratch afterwards. The one thing
this branch reads that the rest of the tree does not is `ec/firmware/**` and
`ec/decompiled/**`, and reading those is a file read, not an observation of a
machine.

## The diagnosis, which was exact

`guard_off()` built the guard-off census by copying the tool into a scratch
tree, asserting that the literal

```python
    if stripped.startswith("=="):
        return False
```

was in the copy, writing `source.replace(GUARD, "")` over it, symlinking the
four input directories back to this repository, and running *that*. #528
threaded `--no-eq-guard` through as a parameter, so the guard is now

```python
    if eq_guard and stripped.startswith("=="):
        return False
```

at `ec/tools/xdata_register_map.py:1595`. The guard did not move or vanish —
the *predicate text* acquired a conjunct, so the literal no longer occurs and
the replace is a no-op. The suite's own `GUARD in source` assertion caught it
and refused, which is the behaviour its comment at the old `:50-53` asks for.

```
AssertionError: the `==` guard is not where §6a's recipe deletes it; the
guard-off census this suite builds is not the one §6a measured
```

**That assertion is the failure mode the issue exists to stop, and it is worth
being exact about which one.** The loud refusal is the *good* outcome. The bad
outcome is the same `source.replace()` after the `GUARD in source` check is
removed or relaxed: a recipe that no longer finds its target, with nothing to
say so, regenerating the committed census twice and comparing the tool against
itself — which is the failure
`annotations/xdata-06c2-06db-timers.md` §6b already records the first version
of ("its two censuses came out byte-identical and it compared the tool against
itself"). Any repair that trades the assertion for a working suite walks into
that.

## Two repairs, and why the flag is the one that landed

The issue prescribes one and explicitly invites the choice: *"Say which you
chose and why."* Two were on the table.

**The issue's own repair** is to re-point `GUARD` at
`if eq_guard and stripped.startswith("=="):` and neutralise the conjunct, which
keeps the literal-text match and the loud refusal. It is correct, it is local to
`guard_off()`, and if a reviewer prefers it the new case below stands either
way.

**What landed instead is the second half of what the tree had already scoped.**
`docs/findings/xdata-no-eq-guard-refusal-contract.md:255-257` wrote the fix down
as *"delete the `==` branch from the `if eq_guard and …` line instead, or drop
the class in favour of this suite's run"* — and the second half of the first is
a third option the issue did not list: **build the census with the flag**, which
is `run_main("--no-eq-guard", …)` in that page's own `AcceptedWrite`.

The flag wins on four counts, all citable inside this tree:

- **It is the mechanism §6a measures with.** `xdata_register_map.py:263` says
  `--no-eq-guard` "re-runs the census with the `==` rejection turned off" and
  gives the reason it exists: that §6a's measurement "has to stay re-derivable
  from the committed tree forever." The page's own §6b adds why the copy-and-
  patch recipe could not be: `git log -S` reaches commits touching that string
  and **none** of them is the pre-#178 classifier. §6b wrote "two" for
  `origin/main` — #206, which added the guard, and #302 — and recorded a
  parenthetical for the third; on this tree the command returns **three** on
  `origin/main` as on the branch — `db6d7d2d` (#528) has merged since, and it
  added the docstring sentence at `xdata_register_map.py:273` that names the
  string, which is where §6b's count now sits out of date. The conclusion
  §6b's count supports is unchanged. "The numbers were right; the recipe was
  the defect."
- **The copy-and-patch recipe has been re-pointed three times.**
  `xdata-no-eq-guard-refusal-contract.md` counts them — #528 threaded the
  parameter, the flip moved from `generate()` into `census_and_groups()` when
  #566 added the co-reading relation — and calls that "itself the argument for
  the flag." A fourth re-point buys one more trip through the same trap, on the
  way to the same census.
- **The issue's own principle is satisfied more strictly this way.** The issue
  asks for the guard's *identity* to be asserted rather than one frozen
  spelling. The flag asserts it: the tool's `--self-test` pins that it flips
  exactly the `==` lines of `CLASSIFIER_SHAPE` and nothing else,
  `test_xdata_register_map.py::AcceptedWrite` pins that a run with the flag
  writes only into its `TemporaryDirectory` and comes back different from the
  committed census, and `Refusals` pins the flag's two refusals. Deleting the
  text surgery deletes the silent mode outright; keeping it keeps a third
  string that has to be re-pointed.
- **The scratch tree was doing no work the flag does not already do.** The copy
  existed to read the committed decompile and write nothing into it. Run in
  place, the tool reads the same committed decompile, and the flag's own second
  refusal (`xdata_register_map.py:4606`) will not let it be given the committed
  output paths — so the CSVs have to go somewhere scratch either way, and
  `setUpClass` already had that directory.

**What is deliberately *not* here is the literal text match the issue suggests.**
That is left out rather than forgotten, and the reason is above: the flag route
carries the same protection from a different, already-pinned mechanism, and
adding a frozen spelling alongside it would re-introduce the third copy this
removes.

## §6a needs no correction, and that is the finding

The issue's "done when" asks for the guard-off census to be *shown* to be the
one §6a measured. It is, on every figure, and that is why the diff stays off
that page: the numbers were right and the recipe was the only thing wrong.
Re-run on this tree, writing only to `/tmp`, `git status` clean afterwards:

| §6a row | guard-off | as committed |
|---|---:|---:|
| references leaving `write` | **833** | — |
| addresses whose `write` changes | — | **210 of 1,326** |
| addresses whose `refs` changes | — | **0 of 1,326** |
| `0x08A8` read / write | **84 / 44** | **126 / 2** |
| `0x0843` read / write | **84 / 42** | **126 / 0** |
| main-EC clusters at threshold 0.50 | **394** | **389** |
| cluster rows | 445 | 439 |

The first three are the page's own heredoc, printed at
`xdata-06c2-06db-timers.md:952` and reproduced here so the claim is a transcript
rather than a summary:

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/before-registers.csv \
    --out-clusters  /tmp/before-clusters.csv                  # the pre-#178 classifier
wrote /tmp/before-registers.csv: 1326 rows
wrote /tmp/before-clusters.csv: 445 rows
  main-ec: 1218 distinct addresses, 14838 references, 394 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5
$ python3 - <<'EOF'
import csv
u = {r['addr']: r for r in csv.DictReader(open('/tmp/before-registers.csv'))}
f = {r['addr']: r for r in csv.DictReader(open('ec/annotations/xdata-registers.csv'))}
print("references leaving 'write':",
      sum(int(u[k]['write']) - int(f[k]['write']) for k in u))
print("addresses whose 'write' changes:",
      sum(1 for k in u if u[k]['write'] != f[k]['write']), "of", len(u))
print("addresses whose 'refs' changes:",
      sum(1 for k in u if u[k]['refs'] != f[k]['refs']), "of", len(u))
EOF
references leaving 'write': 833
addresses whose 'write' changes: 210 of 1326
addresses whose 'refs' changes: 0 of 1326
```

## The six cases, which had never run, all hold

The class was not asking for much. Over the committed census (439) and the
guard-off one (445):

- **315 of 439 ranks change membership**, 124 survive intact. The floor the
  class has always asserted is `> 300`, and 315 is **15 of headroom** over it.
  Left as it is: a future re-derivation that trips it is the loud failure the
  floor exists for, and the new figure pin below is governed by the same rule.
  Lowering the floor to buy room would be the one change that makes the suite
  look green while checking less.
- **`counter-sweep` resolves to the 43 swept addresses** §1 names, so the issue's
  assertion — a cluster the prose names still resolves to the membership the
  sentence describes — holds under the route as well as in principle.
- **No name is lost.** 9 committed names, 9 in the guard-off census, none
  dropped. `mode-oem-init` is the one carried by overlap rather than by key,
  at Jaccard 0.97 from `kefb63d82f8c7`.
- **Six named clusters keep key *and* membership while their rank moves**, and
  two — `mode-oem-init` and `level-block-086x` — change both, which is the
  key-only design's failure case. Per name:

  | name | rank | key | membership |
  |---|---|---|---|
  | `countdown-06c6` | `main-ec-128` → `-125` | same | same |
  | `fan-step-08a0` | `main-ec-292` → `-297` | same | same |
  | `flag-pair-0442` | `main-ec-125` → `-122` | same | same |
  | `mode-oem-init` | `main-ec-002` → `-002` | **changed** | **changed** |
  | `level-block-086x` | `main-ec-004` → `-004` | **changed** | **changed** |

  *(Correction, 2026-09-25, issue #818. The bullet above used to read "**Six
  named clusters keep key *and* membership while their rank moves**, and two —
  `mode-oem-init` and `level-block-086x` — change both, which is the key-only
  design's failure case", over a table marking those two **changed** on both
  columns. **The run gives three movers, not six** — `countdown-06c6`,
  `fan-step-08a0` and `flag-pair-0442`, the first three rows of the table, each
  of whose `same`/`same` cells is correct. **Of the two rows the table marks
  changed/changed, `mode-oem-init`'s is confirmed by the run on all three
  columns; only `level-block-086x`'s is wrong, in both of its `changed` cells** —
  its key stays `ka39cda99615f` and its membership is unchanged, so both read
  `same`. That leaves two wrong cells, both in one row.

  Two further things about the old bullet are recorded rather than counted,
  because neither is evidence about either row. Its arithmetic does not close:
  six movers and two changers is eight, over a census of nine names and a table
  that listed five rows in all, so the six was a count nothing else was checked
  against. And its `rank` column reading `main-ec-002 → -002` and `main-ec-004 →
  -004` for the two rows it marks **changed** is what the run gives for both
  (`rank same`); the bullet never claimed those two rows moved rank, so that
  column is not a defect in them either. The wrong version is kept above rather
  than deleted, per `../findings.md` §4a-4d.)*

  **The derivation, printed rather than summarised** — this file's own form,
  §6a's heredoc is reproduced at `:141-163` for that reason. Both runs write
  only to `/tmp`; `git status --porcelain` prints nothing after them:

  ```console
  $ python3 ec/tools/xdata_register_map.py --no-eq-guard \
      --out-clusters /tmp/off-clusters.csv --out-registers /tmp/off-registers.csv
    names: seeded 8, exact 0, carried by overlap 1, tied, not carried 0, with no name 436
      main-ec-002 carries mode-oem-init by overlap, Jaccard 0.97 from kefb63d82f8c7 -- re-key annotations/xdata-cluster-names.csv if the name moved
  wrote /tmp/off-registers.csv: 1326 rows
  wrote /tmp/off-clusters.csv: 445 rows
    main-ec: 1218 distinct addresses, 14838 references, 394 clusters at threshold 0.5
    pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5
  $ python3 ec/tools/xdata_register_map.py \
      --out-clusters /tmp/on-clusters.csv --out-registers /tmp/on-registers.csv
    names: seeded 9, exact 0, carried by overlap 0, tied, not carried 0, with no name 430
  wrote /tmp/on-registers.csv: 1326 rows
  wrote /tmp/on-clusters.csv: 439 rows
    main-ec: 1218 distinct addresses, 14838 references, 389 clusters at threshold 0.5
    pd: 157 distinct addresses, 858 references, 50 clusters at threshold 0.5
  $ python3 - <<'EOF'
  import csv
  named = lambda p: {r["cluster_name"]: r
                     for r in csv.DictReader(open(p)) if r["cluster_name"]}
  committed, off = named("ec/annotations/xdata-clusters.csv"), named("/tmp/off-clusters.csv")
  movers, changed = [], []
  print(f"  {'name':<16} {'committed':<12} {'guard-off':<12} {'key':<8} {'membership':<11} rank")
  for name in sorted(committed):
      o, n = committed[name], off[name]
      a, b = set(o["addrs"].split()), set(n["addrs"].split())
      key = "same" if o["cluster_key"] == n["cluster_key"] else "changed"
      mem = "same" if a == b else "changed"
      rank = "same" if o["cluster_id"] == n["cluster_id"] else "moved"
      print(f"  {name:<16} {o['cluster_id']:<12} {n['cluster_id']:<12} {key:<8} {mem:<11} {rank}")
      (changed if "changed" in (key, mem) else movers if rank == "moved" else []).append(name)
  print("movers:", len(movers), "of", len(committed), sorted(movers))
  for name in changed:
      o, n = committed[name], off[name]
      a, b = set(o["addrs"].split()), set(n["addrs"].split())
      print(f"{name}: {o['cluster_key']} -> {n['cluster_key']}, {len(a)} -> {len(b)} "
            f"addrs, joined {sorted(b - a)}, left {sorted(a - b)}")
  EOF
    name             committed    guard-off    key      membership  rank
    countdown-06c6   main-ec-128  main-ec-125  same     same        moved
    countdown-06cd   main-ec-214  main-ec-214  same     same        same
    counter-sweep    main-ec-003  main-ec-003  same     same        same
    fan-step-08a0    main-ec-292  main-ec-297  same     same        moved
    ff-fill-stubs    main-ec-007  main-ec-007  same     same        same
    flag-pair-0442   main-ec-125  main-ec-122  same     same        moved
    level-block-086x main-ec-004  main-ec-004  same     same        same
    mode-oem-init    main-ec-002  main-ec-002  changed  changed     same
    user-clear-bytes main-ec-013  main-ec-013  same     same        same
  movers: 3 of 9 ['countdown-06c6', 'fan-step-08a0', 'flag-pair-0442']
  mode-oem-init: kefb63d82f8c7 -> kc0f2a0be0103, 92 -> 93 addrs, joined ['0x0464', '0x0465'], left ['0x1804']
  $ git status --porcelain
  ```

  The two `names:` lines are the part of the default run this claim rests on:
  `seeded 9` with nothing carried, against `seeded 8` with one, and that one is
  `mode-oem-init`. **Its changed key is the cell the corrected claim turns
  on** — `kefb63d82f8c7` to `kc0f2a0be0103` — and it is *why* the name arrives
  on overlap at all rather than by key: a key that no longer matches anything
  is found by membership instead. Its membership delta, 92 addresses to 93
  with `0x0464` and `0x0465` joining and `0x1804` leaving, is the second
  changed cell, and it is why that overlap reads 0.97 rather than the 1.00 a
  byte-identical membership would score — a key change alone would still have
  arrived on overlap, just at 1.00. So the argument against a key-only design
  is narrower than the bullet's and is still an argument: **one** name,
  changing both columns, which is the failure case a content hash alone does
  not cover. The cluster-level version of the same argument, over the 15
  changed-key clusters, is `annotations/xdata-register-map.md:1139-1146` and
  is unaffected by any of this.

  **Where the old table's two `changed` rows came from.**
  `annotations/xdata-06c2-06db-timers.md` §6b (`:858-870`) is an
  `--export-ownership` run — 440 cluster rows, 390 main-EC, `seeded 4, exact 0,
  carried by overlap 3` — and the table above read its two `changed` rows off
  that transcript's three carry lines: `mode-oem-init` at 0.97,
  `level-block-086x` at 0.75 and `ff-fill-stubs` at 0.60. **Of those three,
  only the `0.97` line also appears under `--no-eq-guard`, character for
  character** — which is why `mode-oem-init`'s row came out right on all three
  columns, since that one carry is real under this flag as well. The `0.75`
  line has no counterpart here: `level-block-086x` is `seeded` at
  `ka39cda99615f` under `--no-eq-guard`, because the two flags measure different
  classifiers, and those are the two cells the correction finds wrong. §6b is a
  correct record of a different run and is not to be re-imported here.

  **One observation, recorded rather than opened.** The corrected reading puts a
  *membership* change on `main-ec-002` — `annotations/xdata-register-map.md:1142`
  records it as the cluster `mode-oem-init` names, cited by seven pages of the
  tree. Whether a name cited that widely deserves its own finding for a
  membership that moves by one address is a question for the tracker, not for
  this issue.

- **`--map` emits 439 rows** keyed to the committed identifiers, plus the
  `whose cluster_key changed` line the case asserts on.

**One of these deserves a comment in the code rather than here, and has got
one.** The map carries a name on **10 rows over 9 distinct names**:
`mode-oem-init` appears twice, because the two old clusters the guard-off
generation merged into the new `main-ec-002` are both its sources. The existing
case compares *sets* and is right to — a reader who "fixes" it to compare counts
turns the case red over a correct report, and the merge is a fact about the
census rather than a bug. That is now written down at the assertion.

## The pin, and the rule it is held to

The new case is `test_the_census_is_the_one_6a_measured`. Every expected value
in it is a figure §6a publishes, each with a comment citing the row it comes
from, and none of them is a snapshot of a fresh run of the recipe this branch
changed — that is the issue's *"not against a fresh run of the same recipe"*,
stated as code, and it is the whole difference between this case and a
tautology.

**The rule for a future change to it is the one the denominators are there to
enforce.** A re-derivation that adds addresses makes `210 of 1,326` false; the
response is to re-derive §6a, not to move the number. This is what #279 did, and
it is why §6a already carries a 2026-09-25 re-derivation note with the wrong
figures kept beside the right ones.

**And it does not contradict `test_xdata_register_map.py::AcceptedWrite`**, which
holds the same flag and deliberately asserts *direction* rather than counts
("pinning them here would make this suite red for an unrelated change"). The two
suites have different jobs and both say so in their own comments: that one is the
flag's refusal contract and wants to keep passing through a re-derivation, this
one is the census-identity claim and wants to go red when the census it names has
moved. Asserting counts in *that* suite would have been the mistake; asserting
only direction in *this* one would have reproduced the original defect.

**The class docstring's own figures were corrected in place, not edited out.**
It said the same regeneration "now gives 430 → 439 with 64 ranks intact and 366
changed". That was true when written and is not now: the census has been
re-derived since, and the measured pair is **439 → 445 with 124 intact and 315
changed**. Both earlier pairs — #274's 427 → 439 and the intermediate 430 → 439 —
are kept in the docstring beside it, per `../findings.md` §4a-4d, because a total
pasted into a file is a snapshot of the merge it was measured on and this one has
been overtaken twice.

> **The fall from 366 to 315 is now measured, not just recorded** (issue #852).
> The intermediate pair is re-derivable from `e169a0e4` and reproduces
> 366 / 64 / 439 exactly, so the fall is a fall and not two different
> measurements; `docs/findings/xdata-moved-ranks-fall.md` names the 94 clusters
> whose guard-off membership delta opened or closed, and the write-up is where
> the `> 300` floor at `:170-175` above is argued from that measurement. The
> 15 ranks of headroom stay what they are, a snapshot of one merge.

## Superseded claims, recorded here rather than edited

Four sentences in the tree became false when this landed. Two are corrected in
place, because one is the issue's own "done when" and the other is a comment on
the suite this branch fixes; the other two are recorded here, because each is
in a long shared prose file that this branch has no business editing past the
point — **a reviewer can overrule that**, and the cost of doing so is one
sentence each:

| where | claim | now |
|---|---|---|
| `docs/findings/0751-grader-self-test-gate.md:109` | "#528's `==`-guard failure already has its own issue on `main` and needs nothing from here" | the sentence **stands as written** — `gh issue view 568` shows #568 **open** since `2026-09-25T03:03:44Z`, naming this defect and this flag, queued behind the open-PR cap rather than unowned — with a correction beside it. The issue cites this as `:76`, which is the pre-#751 line; the sentence is at `:109` both on `main` and here, and the correction quotes it rather than pinning a line that has already moved once |
| `ec/annotations/xdata-register-map.md:2610` | "`test_xdata_cluster_names.py` patches a literal `if stripped.startswith("==")`" | the suite no longer patches anything; it runs the committed tool with `--no-eq-guard` |
| `docs/findings/xdata-no-eq-guard-refusal-contract.md:250-252` | "the accepted run in `test_xdata_register_map.py` is the only working scripted route to a guard-off census from the committed tree" | it is now one of two, and the other is the census §6a measures |
| `ec/tools/test_xdata_register_map.py:9-12` | "it has raised in `setUpClass` since #528 without running any of its six cases" | **corrected in place** — a test file, and a direct description of the suite this branch fixes |

**And the fourth copy of the recipe is a historical transcript, in a different
file than the plan recorded.** The plan pointed at
`ec/annotations/xdata-register-map.md:1147-1160`; the executable
`assert guard in s` heredoc is not there any more. It was moved, verbatim and
deliberately, into
`docs/findings/xdata-4-4-identity-rederivation.md:213-220`, whose own heading
says so — *"The superseded one is reproduced here in full … because the
correction beside the map's block points here for it, and that record should
exist rather than sit in history."* That is the right home for it, and its
embedded `assert guard in s` would now fail, which is what a transcript of a
recipe that no longer works is supposed to look like. **Left alone on purpose**:
it is a record, not a procedure, nobody is asked to re-run it, and §6b already
explains at length why the recipe is superseded. A tree-wide
`grep -rn 'startswith("==")' --include=*.md` finds five files and thirteen
occurrences; **four files and eight** of those are other than this one (three in
`xdata-4-4-identity-rederivation.md`, two in
`xdata-no-eq-guard-refusal-contract.md`, one in `xdata-06c2-06db-timers.md`, two
in `xdata-register-map.md`), and the `xdata-4-4-identity-rederivation.md:215`
copy is the only executable one left.

> **Closed 2026-09-25, issue #816 — rows 2 and 3 are corrected in place, and
> they cost more than the two sentences this table priced them at.** The offer
> above — *a reviewer can overrule that, and the cost of doing so is one
> sentence each* — was taken up, and the count came out at six. Not because
> either sentence was expensive to edit, but because neither stood alone:
> `xdata-no-eq-guard-refusal-contract.md`'s measured-state section is one claim
> spread over a heading, an opening paragraph and three suite paragraphs, and
> `docs/findings.md` §29 restates the same "only working route" sentence as the
> summary of that page. The corrections are dated blocks beside the sentences
> they belong to, in `xdata-no-eq-guard-refusal-contract.md`,
> `../ec/annotations/xdata-register-map.md`, `docs/findings.md` §29 and `§59`,
> `tools/README.md` and
> [`runner-red-suite-set.md`](runner-red-suite-set.md). **Row 1 still stands as
> written** and row 4 was already corrected in place here, so nothing in this
> table is a promise any more, and a reader does not need to go looking. The
> write-up is
> [`xdata-no-eq-guard-measured-state-correction.md`](xdata-no-eq-guard-measured-state-correction.md),
> and the one thing worth keeping from this table is its own reason for
> existing: a correction recorded in a sibling file is a promise, and the cost of
> not keeping it falls on whoever notices.
>
> **Not this issue's, and recorded here because a reader of this file is the
> likeliest to want it: this file's `:220` paragraph is the one red case in the
> tree.** #822's addition put a pasted `xdata_register_map.py` transcript — which
> prints cluster ids of its own — in the same paragraph as the addresses a later
> sentence of it discusses, and `check_cluster_citations.py` reads that pairing as
> a membership claim. It is the reason `bash tools/run-tests.sh` exits 1 on this
> tree, it reproduces on a clean `origin/main`, and `docs/findings.md` §52 names
> it to this file's owner rather than fixing it in a correction sweep. The
> mechanism is the one the write-up measures: a unit naming an address, a cluster
> id and a membership word reads as a claim, whatever sits between them.

## What this does not do

- **`xdata_register_map.py` is not touched at all.** That is the point of the
  flag route, and it puts the tool's refusal contract and the census out of
  reach of this change.
- **No CSV or YAML is edited.** `xdata-registers.csv`, `xdata-clusters.csv`,
  `xdata-cluster-names.csv` and `registers.yaml` are byte-untouched: the
  committed census is post-guard and the committed tool reproduces it, which is
  why the guard-off run has to go to scratch. `AcceptedWrite` already pins that
  the committed CSVs come back byte-identical, and `--no-eq-guard` is refused at
  the default paths.
- **The other red suite is not touched.**
  `test_check_site_census.py`'s 14 `D091.c` line disagreements are #180's
  correction and a judgement about the decompile;
  `xdata-no-eq-guard-refusal-contract.md:261-269` records them and says so.
- **No gate is wired.** `tools/run-tests.sh` is not in CI, and closing that gap
  — along with the cheap tier not running the tool's `--check`/`--self-test`,
  which are red on `main` — is an `ElDavoo/agent-pipeline` change and a
  re-copy, not a line here.
- **No live hardware or Windows step**, because nothing here needs one. No live
  run is planned, claimed or implied, and none is needed to close this issue.
- **Nothing is opened in another repository.** No driver or firmware change is
  proposed here, so there is nothing to send to `Wer-Wolf/uniwill-laptop` or
  `tuxedo-drivers`.

## The test that proves it

```console
$ python3 -m unittest discover -s ec/tools -p 'test_xdata_cluster_names.py'
............................
Ran 28 tests in 15.8s

OK
```

Before, on this tree and with no other change, the same discovery ends:

```
ERROR: setUpClass (test_xdata_cluster_names.TheGuardOffRegeneration)
AssertionError: the `==` guard is not where §6a's recipe deletes it; the
guard-off census this suite builds is not the one §6a measured
Ran 21 tests
FAILED (errors=1)
```

21 → 28: the six cases the error kept out now run, and the new one is the
seventh. The count is reported as the run prints it and is a property of this
merge, not a claim about any suite.

**The new case was checked for the ability to fail.** Three of its expected
figures were perturbed in turn — `833` → `832`, `(210, 1326)` → `(211, 1326)`,
`394` → `393` — and each was confirmed to turn the case red on its own
assertion before being reverted. A case that cannot fail has not been shown to
check anything.
