# The xdata census re-derivation checklist: what a re-export moves, and what to do about it (issue #820)

Issue #753 added the first test in the tree that goes **red because the census
was re-derived**, and wrote the response down in a comment inside the test. The
three places the tree tells a person or an agent to re-derive that census did
not mention it — the issue's third is two sentences on one page, which is why
there are four pointers and not three. This file is the checklist, and the four
pages that carry the procedure now point at it, so a trip is a **known cost of
the procedure** rather than a surprise found halfway through it.

Nothing here is a hardware claim. No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved — same framing as
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):11.
Every figure below is the output of a command over committed text (`--check`,
`--self-test`, and the two suites that read these CSVs), all re-measured on this
tree at 1,326 register rows and 439 cluster rows.

## 1. The tripwire, and the response

`ec/tools/test_xdata_cluster_names.py:303`
`TheGuardOffRegeneration.test_the_census_is_the_one_6a_measured` compares the
guard-off census against **§6a's published figures** rather than against a fresh
run of the same recipe, which would agree with itself by construction. Its own
comment states the rule at `:342-344`:

> The denominators are pinned with the numerators because a re-derivation that
> changes them has changed what §6a measured, and the response to that is to
> re-derive §6a, not to move a number here.

**All seven of its figures are functions of `ec/decompiled/**` and
`ec/firmware/GMxMGxx_11.800`**, so a re-export moves all of them at once. The
precedent for what that costs is the #279 re-derivation note at
`ec/annotations/xdata-06c2-06db-timers.md:799-814`: a full paragraph of
superseded figures, kept visible, because that pass re-derived every *level* in
§6a's table and none of its *differences*.

## 2. The fifteen figures, in two groups

### 2a. Seven, pinned by the test — a trip here is the machine saying the census moved

| figure | what it is | where §6a prints it |
|---|---|---|
| `833` | references leaving `write`, all three programs | `xdata-06c2-06db-timers.md:785` |
| `210` of `1,326` | addresses whose `write` column changes | `:786` |
| `0` of `1,326` | addresses whose `refs` column changes | `:937` |
| `0x08A8` `84/44` guard-off, `126/2` committed | read / write | `:787` |
| `0x0843` `84/42` guard-off, `126/0` committed | read / write | `:788` |
| `394` guard-off, `389` committed | main-EC clusters at threshold 0.50 | `:789` |
| `set(off) == set(on)` | the 1,326-row address universe both runs are over | the heredoc's two `of 1326` denominators, `:920-937` |

### 2b. Eight, unpinned — these are the ones that decay silently

`ec/annotations/xdata-06c2-06db-timers.md:779-790`, §6a's table:

| figure | what it is | line |
|---|---|---|
| `3,948` / `3,206` | main-EC `write` references, guard removed / as committed | `:781` |
| `7,189` / `7,935` | main-EC `read` references | `:782` |
| `193` / `142` | PD-image `write` references | `:783` |
| `279` / `239` | references in `write` for the 49 addresses in both images | `:784` |
| 43 addresses, `4,966` refs | `main-ec-003` (this block), **identical either way** | `:790` |

And the console block at `:869-872` — **§6b's `--export-ownership` run, not
§6a's**, which is easy to misread as part of the table above:

| figure | what it is | line |
|---|---|---|
| `1326 rows` / `440 rows` | the two `wrote …` lines | `:869-870` |
| `1218` distinct addresses, `9320` references, `390` clusters | `main-ec` total at threshold 0.5 | `:871` |
| `157` distinct addresses, `858` references, `50` clusters | `pd` total at threshold 0.5 | `:872` |

**Read all eight off the page before quoting them; three of them are commonly
transcribed wrong.** `14,838` is *not* a per-program total — it is §6b's own
table cell (`main-EC refs | 14,838 | 9,320`, `:834`), and the per-program figure
beside it is `9320`. `394` is not unpinned at all: it is the guard-off main-EC
cluster count §2a already pins, and §6b's `390` is a *different* number that
looks like its predecessor. The cluster row here is `440`, not `445` (445 is the
guard-off census at
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):168,
a different run of a different flag). These are the figures a paste silently
gets wrong, and a checklist that carried the wrong one would be worse than no
checklist.

## 3. The other four items

**`BUCKET_TOTALS`, five figures** — `ec/tools/xdata_register_map.py:1212-1213`:
`read 8826`, `write 3587`, `read+write 2482`, `passed-to-call 534`,
`address-taken 267`. They cross-check by sum: `8826 + 3587 + 2482 + 534 + 267 =
15696 = ORACLE["refs"]`, which is the cross-check the comment above them states.
The page cites this oracle at `xdata-06c2-06db-timers.md:770-772`, but prints
the older `:668` in its prose; **cite the live line, `:1212`.**

**The two committed CSVs** — `ec/annotations/xdata-clusters.csv` at **439** rows
and `ec/annotations/xdata-registers.csv` at **1,326**. `--check`
(`ec/tools/xdata_register_map.py:2986`) compares every `read`, `write`, `refs`
and `addrs` cell against a fresh generation from the committed tree, cell for
cell. It is the only mode that does.

**The names-file re-key** — 9 keys in `ec/annotations/xdata-cluster-names.csv`.
The tool says so itself, once per name carried by overlap, **on stderr** so the
CSVs stay pipeable — the emitting function's own docstring opens with that reason
(`xdata_register_map.py:2960`, *"What happened to every hand name, on stderr so
the CSVs stay pipeable"*) and the print carries `file=sys.stderr` at `:2979`:
*"-- re-key annotations/xdata-cluster-names.csv if the name moved"* (`:2976-2979`).
**So read it off the terminal, not off a redirected `--check` pipe** — the pipe
that keeps the CSVs usable is the same pipe the hint is kept out of. A
re-derivation that moves a key leaves the names file attached to a membership
that has gone, which is what `--self-test`'s check at `:4030` exists to catch
("every key … names a cluster of the committed census"). **Re-key by hand; there
is no command that writes that file for you.**

**The `> 300` floor** — `ec/tools/test_xdata_cluster_names.py:387`,
`assertGreater(len(moved), 300)`, measured at **315** today: **15 of headroom**.
It is left there deliberately, and the argument is
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):170-175:
lowering the floor to buy room "would be the one change that makes the suite look
green while checking less". So read a trip as **"the floor is where it was left,
here is the new number"**, not as a discovery. The count has already fallen once,
**366 → 315** (`xdata-cluster-names-guard-off-recipe.md:345-352`, with the
earlier pairs kept beside it; not this test file, whose `:345-349` is the pointer
to this checklist). The tree records the fall without attributing a cause; a
re-derivation that lands addresses in already-large clusters would move fewer
membership sets, which is the obvious shape of it, but that is a guess and not a
measurement.

## 4. The order the work happens

1. **`python3 ec/tools/xdata_register_map.py --check` — first.** It is the only
   mode that compares the committed CSVs to a fresh generation, and
   `check_ghidra_tooling` has run it since #256. **Since #823 (`244c992b`) it runs
   step 2's mode as well** — the arm at
   `.github/scripts/agent-gates.sh:261-263` reads
   `*xdata_register_map.py) python3 "$tool" --check && python3 "$tool" --self-test || rc=1`,
   and the comment above it now ends "So the honest description of what is gated
   here is no longer the two CSVs" (`:253-254`). A re-deriver is therefore caught
   by the cheap gate itself, before the suites in step 3 are reached.
2. **`python3 ec/tools/xdata_register_map.py --self-test`.** The `BUCKET_TOTALS`
   and direction-invariant oracles behind §2b and §3.
3. **The two suites that read these CSVs** — `ec/tools/test_xdata_cluster_names.py`
   and `ec/tools/test_xdata_register_map.py`, both collected by
   `bash tools/run-tests.sh`. The first's `setUpClass` builds the guard-off census
   with `--no-eq-guard` and is the longest run in the tree; budget for it.
4. **Re-derive §6a's figures from the two scratch CSVs**, per its own printed
   heredoc (`:920-937`), which prints the 833 / 210 / 0 triple itself.
5. **Re-key `xdata-cluster-names.csv`** if step 1's *stderr* (§3) or a scratch run
   moved a key.
6. **Re-run `--check`** to confirm.

A `bash .github/scripts/agent-gates.sh` run covers **all of steps 1 and 2** —
that is what #823 added — and the cheap half of step 3 (`doc links` and `python
syntax` are what touch anything written by hand). So a re-derivation that moves
the committed CSVs now turns the cheap gate red on its own, and the runner in
step 3 is the second witness rather than the first.

## 5. What this checklist is not

**Every figure above is today's snapshot, the way §6a's re-derivation note is**
— a total pasted into a file is a snapshot of the merge it was measured on, and
this one has been overtaken before. Nothing here asserts what a re-derivation
*would* produce. §6b's own correction (`:885-896`) is the cautionary case, and
it is not a hypothetical one: a transcript there was written out in the
half-renumbered shape of a run that never happened, and the correction that
finally caught it came from noticing the ids and the counts disagreed. Re-derive
from the two scratch CSVs, print what the command printed, and correct beside
the wrong version if one slips in — do not hand up a block that reads like a run
nobody ran.

It is not a retraction and it corrects nothing. The #279 note's superseded
figures stay exactly where they are, per [`../findings.md`](../findings.md) §4d;
this file adds a pointer beside them, not a replacement for them.

And nothing in it needs hardware, Windows, an image, or a register read back —
the deliverable is this document and its four pointers, all of it unattended.
