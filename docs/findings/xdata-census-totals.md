# The census totals: 1,171 addresses / 14,819 references, and how to re-derive them (issue #557)

`ec/annotations/xdata-register-map.md` is the canonical write-up of the XDATA
census. It was also the only file in the tree still carrying three mutually
inconsistent totals — 1,172 / 14,801 / 14,792 — with no statement of which one a
reader should use. This is the record of the measurement behind the correction
that landed in the same change, and the place a future census-dedup change
(#254/#256/#326) edits instead of re-deriving the page from scratch.

It is deliberately **not** a second copy of the census. The census is
`ec/annotations/xdata-registers.csv` and `ec/annotations/xdata-clusters.csv`; if
anything here disagrees with those two files, those two files are right.

## What the committed tree actually says

Re-derived with a real CSV parser from the committed tree, not from any prose
summary — and cross-checked against a fresh generation from the same tree:

| quantity | committed CSVs | fresh generation from the committed tree |
|---|---:|---:|
| `xdata-registers.csv` data rows | **1171** | **1171** |
| sum of `refs` | **14819** | **14819** |
| `xdata-clusters.csv` rows | **430** | **430** |
| sum of cluster `refs` | **14819** | **14819** |
| main-EC / PD distinct (the tool's own split) | — | 1062 / 157 |
| main-EC / PD references | — | 13961 / 858 |
| rows with a non-empty `name` | **162** | **162** |
| `read` / `write` / `read+write` / `passed-to-call` / `address-taken` | 8341 / 3195 / 2482 / 534 / 267 | same |

Every figure in that table agrees between the committed CSVs and a fresh
generation, and on the census proper the tool agrees with the committed CSVs:

```console
$ python3 ec/tools/xdata_register_map.py --out-registers /tmp/r.csv --out-clusters /tmp/c.csv
  names: seeded 10, exact 0, carried by overlap 0, tied, not carried 0, with no name 420
wrote /tmp/r.csv: 1171 rows
wrote /tmp/c.csv: 430 rows
  main-ec: 1062 distinct addresses, 13961 references, 380 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 50 clusters at threshold 0.5
```

`ec/tools/xdata_register_map.py`'s `ORACLE`
(`ec/tools/xdata_register_map.py:463`, whose dated comment above it runs from
issue #132 through #263) pins `distinct: 1171, refs: 14819`,
`named_in_tree: 162`, and its `BUCKET_TOTALS` (`:862`) reads
`read 8341 write 3195 read+write 2482 passed-to-call 534 address-taken 267`.
So the CSVs, the tool, `ec/annotations/xdata-06c2-06db-timers.md` §6a and
`ec/README.md` were all already consistent before this issue, and
**`xdata-register-map.md` was the only stale artifact among them.**

**The `name` row is the one figure here that moved after that was written, and
it moved up rather than being corrected in prose.** Measured on this issue's own
branch it read 153 committed against 162 from a fresh generation, with
`ORACLE['named_in_tree']` holding the CSV's 153 rather than corroborating it —
the pin-the-symbol-table-outran shape the walk below records, and one of the
four `--self-test` assertions red on that tree. Issue #256's regeneration
rewrote both CSVs from the committed tree, which filled the `name` column and
carried the pin to 162 with it, so the committed CSV, a fresh generation and
`--self-test` now agree on 162 and that assertion is green. It is still not a
census total, and the walk is still how it got there: 153 → 162 is the symbol
table growing 164 → 187 names with two of the new addresses (`0x07C7`,
`0x07C8`) *not* named in the tree, which is why the pin is `187 - 25` and not
187.

## The re-derivation, as a command a reader can paste

No tool needed, and no summary to trust:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | wc -l
1171
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{s+=$6} END{print s}'
14819
$ tail -n +2 ec/annotations/xdata-clusters.csv | wc -l
430
```

`tail -n +2` is there to skip the header, and it is the whole point: **`--check`
prints it in one message and not the other.** When the committed CSVs differ
from a fresh generation, `diff()` counts `len(splitlines())` on *both* sides, so
a 1,171-row file reads `1172 on disk vs 1172 generated`; when they agree, the
same command prints `1171 rows match a fresh generation`, which counts data
rows. Two conventions in one command, and a reader who has only ever seen the
first cannot compare a `--check` figure against a data-row count. It is a
one-line fix, carried as follow-up 1 below.

It is **not** how `1,172` reached the prose, and the superseded-figures table
below already has this right: `1,172` **was** a data-row count. At the census's
first commit, `a121ff63` (#163), `tail -n +2` over `xdata-registers.csv` gives
`1172` rows summing to `14801` refs, and it still gives `1172` / `14801` at
`6ff6c6d2`, the commit before #238's `1fcd5f1e`:

```console
$ git show a121ff63:ec/annotations/xdata-registers.csv | tail -n +2 | wc -l
1172
$ git show a121ff63:ec/annotations/xdata-registers.csv | tail -n +2 | awk -F, '{s+=$6} END{print s}'
14801
$ git show 6ff6c6d2:ec/annotations/xdata-registers.csv | tail -n +2 | wc -l
1172
```

The map's H1 `1,172` and its `14,801` tables were therefore true counts on the
tree they were written against, and #259 is what later took one address out —
so fixing `--check` is not what would have removed either figure.

**One trap in that block, and it is the reason the block is worth having.** The
`awk` condition is `{s+=$6}`, with no `NR` test. Writing `NR>1` — the reflex
after a `tail`, and what this file's plan proposed — silently drops the first
*data* row, because `tail -n +2` has already removed the header, and prints
`14806` rather than `14819`. Nothing about that failure looks like a failure.
Re-run it if you want to watch:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, 'NR>1{s+=$6} END{print s}'
14806
$ sed -n '2p' ec/annotations/xdata-registers.csv | cut -d, -f1,6
0x0004,13
```

Column 6 is `refs` and nothing before it can contain a comma (`addr`,
`program`, `spelled_as`, `span_group`, `cluster_id` are all comma-free), so
`-F,` with a fixed field is safe on this file — and is the one assumption here
worth stating, because it is the thing that would break first if a column were
added.

The same five direction buckets, which is what §4.1 of the map carries:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv \
    | awk -F, '{r+=$7;w+=$8;rw+=$9;p+=$10;a+=$11} END{print "read",r,"write",w,"read+write",rw,"passed-to-call",p,"address-taken",a}'
read 8341 write 3195 read+write 2482 passed-to-call 534 address-taken 267
```

## The rule

Stated once, at the top of `ec/annotations/xdata-register-map.md`, and repeated
here because this is the file a future change edits:

> A figure measured from the committed `xdata-registers.csv` /
> `xdata-clusters.csv` is the current one; any other figure in that file is
> historical and sits beside a correction naming the tree it was measured
> against. Re-measure rather than pin — census-dedup (#254/#256/#326) moves
> these — and re-measure the *table body*, not just its total row, because a
> total its own rows do not sum to is a worse error than a stale one.

Two clauses of it earned their place by being violated here:

- **The table body, not just the total.** §4.1's five bucket cells summed to
  14,801, §2's six `spelled_as` cells to 14,801, §3's rows to 14,801. Fixing
  the total row alone would have left three tables that do not sum to it, which
  reads as *more* authoritative than a plainly stale one.
- **Naming the tree, not the date.** "Corrected 2026-09-25" does not tell a
  reader in six months which merge a figure came from. "The tree #238 merged"
  does.

And what the rule is **not**: it is about agreement between the committed CSVs
and the page. The census is a lower bound on the machine code
(`ec/tools/xdata_register_map.py:409-411`), a zero in it is "not found by this
method" and never "absent", and no total here is a claim that the firmware
touches exactly this many addresses.

## Every superseded figure, and what superseded it

Kept visible rather than deleted, per `docs/findings.md` §4a. Each row names
the commit that made the old figure historical.

| superseded | by | why it moved |
|---|---|---|
| 1,172 addresses | 1,171 | #259 — `bank1/E100.c` stopped passing `DAT_EXTMEM_0390` at the `0x9EA1` call site once #238's committed signatures were applied. One address left the census; nothing was lost from the machine code. |
| 14,801 references | 14,792 | same nine C-level references, six addresses (§7.1) |
| **14,792 references** | **14,819** | **Two causes, and only one of them is #263's.** The pin said 14,792; a pristine checkout of #263's parent commit already read **14,818**, so **26 of the 27** were pre-existing drift on `main` that the pin never caught. #263's own 88 `ghidra-variables.csv` signature rows moved it the last **+1** (§7.2 records both halves separately, so the issue does not credit itself with the drift). This is the one the issue did not name: 14,792 **was** a real, checkable tree — it is what #238 (`1fcd5f1e`) pinned in `ORACLE` — so this row is drift past a pin, not a figure that never existed on a checkout, and `xdata-06c2-06db-timers.md` §6a and the tool have carried 14,819 since #263. |
| 13,931 main-EC / 861 PD | 13,961 / 858 | #263's +4 / −3, on top of the same pre-existing drift (the pin's 13,931 was already 26 behind `main` at 13,957) |
| 427 clusters | 430 | the 2026-09-24 re-derivation that closed the `--check` gap |
| `read` 8,319 / `write` 3,186 / `read+write` 2,476 / `passed-to-call` 549 / `address-taken` 271 | 8,341 / 3,195 / 2,482 / 534 / 267 | #263 and the pre-existing drift, by +22 / +9 / +6 / −15 / −4 — which sums to the same +18 the census moved. Not §4.3 again: `--no-eq-guard` changes the `refs` of 0 of 1,171 addresses on this tree. |
| 79 rows with a `name` | 162 | the symbol table grew under a pin that was never re-derived. The walk is the tool's own dated comment above `ORACLE`: 79 → 86 → 88 (#237's two fan bytes) → 131 (#179's 43) → 146 (#180's 15) → 150 (#183's four) → 153 (drift on `main` that no issue caused) → 162 (#256's re-derivation, the symbol table at 187 names with `0x07C7`/`0x07C8` not in the tree, so the pin is `187 - 25`). It was 153 when this table was written; #256's regeneration moved the CSV and the pin together, and 162 is what both read now |
| 41 symbol-spelled main-EC addresses | 147 | the re-exports behind the row above; §2's `spelled_as` table is a projection of the CSV and moved with them |
| 1,063 main-EC addresses / 13,937 references | 1,062 / 13,961 | #259 then #263 |

**Not superseded, and checked rather than assumed:** the 109 PD-only addresses,
the 48 touched by both programs, and the top two main-EC addresses by reference
count (`0x0440` 181, `0x08A8` 170) are all still what the committed CSVs say,
and are still pinned by the tool.

## What was deliberately left alone

- **The map's second-pass correction and §7.2's opening** — the record of how
  14,801 stopped being current, and the evidence this correction rests on.
  Editing them would destroy the correction's own citation. They are also the
  reason the superseded figures above can be trusted: each names a commit and a
  measurement rather than a date alone.
- **The self-test transcript** — it is a record of a run, and a rewritten
  transcript is not a run anyone can check. It prints the pre-#263 `ORACLE`
  values, and now says so beside itself.
- **The CSVs and `xdata_register_map.py`** — the CSVs are the *input* here; the
  tool's `ORACLE` and `BUCKET_TOTALS` were already correct. This change is
  documentation of them, not a regeneration. *(Issue #256 has since regenerated
  both CSVs from the committed tree and re-pinned `named_in_tree` 153 → 162, so
  the tree this issue measured has itself moved under one column; the census
  proper, which is every other row above, did not. The `--check` and
  `--self-test` readings it quotes are re-measured above rather than carried.)*
- **`.github/scripts/agent-gates.sh`** — see below.

## Follow-ups this measurement opened, and did not fix

Named rather than silently patched, in the order a reader is most likely to hit
them.

1. **`--check`'s two messages count rows two different ways.** The mismatch
   line goes through `diff()`, which counts `len(splitlines())` on both sides
   and so includes the header — `1172 on disk vs 1172 generated` for a
   1,171-row file — while the match line counts data rows (`1171 rows match a
   fresh generation`). One command, two conventions, so a `--check` figure off
   the failure path cannot be compared to the data-row counts this file is
   written in. It is a one-line fix in `ec/tools/xdata_register_map.py`, and it
   did **not** put `1,172` in the map's prose — the census really did hold 1,172
   data rows and 14,801 refs until #259 took one address out (see "Every
   superseded figure" above). Left out of this change because it is a tool
   change, not a documentation one. *(It was written when `--check` was also
   red on unrelated function-name drift; #256's regeneration cleared that, and
   `--check` is wired into `check_ghidra_tooling` in
   `.github/scripts/agent-gates.sh` as of the same change, so the fix now has a
   gate to land behind rather than a red one to work around.)*
2. **`--self-test` is still not in `agent-gates.sh`, and cannot be until the
   naming drift clears.** `--check` is wired (again, by #256); `--self-test` is
   deliberately not, because it is red on exactly one assertion — "the
   annotation CSV and index.csv agree on every address they share" — which is
   `ghidra-functions.csv` naming three `bank1` functions that `index.csv` still
   spells `FUN_CODE_*`. The gate script's own comment says why: wiring a red
   mode is the cheapest way to get a gate switched off. Clearing the assertion
   means re-running `build_ec_decompile.py` in its default export-only mode,
   which rewrites the generated `ec/decompiled/**` tree and belongs to whoever
   added the renames. When this was written both modes were unwired and four
   assertions were red; one assertion and one wired mode is the state since.
3. **The `&&` misfiling site's line number, corrected here rather than left.**
   `xdata-register-map.md` cited it as `bank0/A747.c:24` in three places (§4.3's
   correction, §6's bullet, §8's follow-up); re-running the census's own
   `classify()` logic over the committed `.c` files puts it at
   **`bank0/A747.c:25`**, and confirms the misfiling is still exactly one site
   (`DAT_EXTMEM_076a`, the second `&` of a `&&`). `:24` was right where it was
   written — at `c9e0c2c4` (#206) `grep -n` returns lines 24 and 26 there — and
   #432's re-export `20b48329` added a line above it, moving both to 25 and 27.
   §4.3's correction block keeps `:24` with this correction beside it (§4a
   shape); §6's bullet and §8's follow-up, whose text this change edited, now
   carry `:25`. Nothing about the site, the bucket, or the 838/837 arithmetic
   moved — only the line number.
4. **Figures this issue did not reach, still stale in the same file.** §4.2's
   threshold sweep and its "306 of the 1,063" are the pre-#263 sweep — a fresh
   `--threshold-sweep` reads 380 clusters with a largest of 109 at 0.50 (against
   the 376/108 in the table) and a largest of 302 at 0.30 (against the 306), and
   `--threshold-sweep --no-writer-axis` reads **481** against the 479 §4.2
   quotes for the `touching` row it offers as evidence the writer axis is not
   marginal. §4.4's
   `cluster_key` section still describes "its 427 keys", and §5's drift record
   still contrasts 430 against "the committed 427" where the committed CSV holds
   430, and still dates `xdata-symbols.csv` at 177 names where it holds 187
   (187 rows, 187 distinct `addr`/`name` pairs). All of these are historical
   blocks that name their tree, so none of them fails the rule above, and none is
   a census total. They are listed here so the next pass does not rediscover
   them. Two of those blocks have since been **overtaken** rather than
   contradicted: §4.4's gap paragraph and §5's drift record both say the
   committed CSV "is behind a fresh generation", and since #256's regeneration
   it is not — each now carries a correction beside it saying so, with its own
   427 and `main-ec-013` row kept as the pre-regeneration figures they are.
