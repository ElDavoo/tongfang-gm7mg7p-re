# The four `0x0860` census citations move; the counts do not (issue #752)

The write-up for [issue
#752](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/752), which is
about `docs/findings/0751-grader-self-test-gate.md` promising a follow-up issue
for a red `test_check_site_census.py` and no such issue being filed. What this
branch changes is four `census_refs` cells in
`ec/annotations/xdata-0860-census-sites.csv`, the prose that quotes the same
line numbers in three other files, and this file.

**None of this is a live test, and none of it is evidence about the firmware.**
The failure is arithmetic over committed text: no EC is opened, no register is
read back, no capture is taken, and no laptop, EC or Windows machine is
involved anywhere below. `ec/decompiled/bank0/D091.c` is a file this repository
reads; a `read x14` census count over it is a statement about a decompilation,
not an observation of a byte. `XDATA_0860` stays `present-untested`, and the
"what this does not say" section below is not a formality.

## The failure, decomposed

`check_site_census.py` reads the census through its own
`census_occurrences()`, which borrows `load_index`, `load_symbols`,
`occurrence_re`, `strip_comments` and `classify` from
`xdata_register_map.py` and never re-greps, and `strip_comments()` keeps
every newline — so the line numbers it checks are the reader's own line
numbers in the committed `.c`. The 14 disagreements decompose as three
clauses firing on one cause, and the decomposition reproduces the issue's
figures exactly:

| source | count | which |
|---|---|---|
| cited line holds no occurrence | 5 | `D091.c:44`, `:48`, `:70`, `:74`, `:82` |
| occurrence no mapped site accounts for | 5 | `D091.c:45`, `:49`, `:72`, `:77`, `:84` |
| `census_count` disagrees with its own cited lines | 4 | `2 vs 0`, `6 vs 3`, `6 vs 3`, `1 vs 0` |

5 + 5 + 4 = 14. The per-bucket totals are *not* among them, and that absence is
load-bearing for the judgement below. The map already summed to `read 14 /
write 2 / passed-to-call 1`, which is what `xdata-registers.csv:817` says, so
from the very first failure only the citations were wrong.

One shape here is worth getting right rather than summarising. The `0x0D117` row
cited three lines, `74,75,76`, of which only two still held occurrences after
the move — `75` and `76` did. So its count clause read `6 vs 3` rather than
`6 vs 0`: a partial self-cancellation, not a pure renumber. A reader who
expects every wrong row to collapse to zero would find one that does not, and
would be right to wonder whether the arithmetic had been done by hand.

## The judgement: the counts move or they change

**The counts do not change. The line numbers move.** This was decided against
the committed C, and it is forced rather than chosen, by two constraints that
have nothing to do with the lines being moved.

**1. From the text.** Reading the occurrences off the committed `D091.c` through
the tool's own `census_occurrences()`:

| line | occurrences | the comparisons themselves |
|---|---|---|
| `:45` | 1 | `== '\0'` |
| `:49` | 1 | `== -1` |
| `:71` | 3 | `\x06`, `\x16`, `6` |
| `:72` | 3 | `\a`, `\x17`, `7` |
| `:75` | 2 | `\b`, `\x18` |
| `:76` | 1 | `8` |
| `:77` | 3 | `\t`, `\x19`, `9` |
| `:84` | 1 | `switch_case_dispatch(XDATA_0860)` → `passed-to-call` |

That is 14 read and 1 passed-to-call in `D091.c`. With the two writes at
`bank0/D281.c:19` and `bank0/D289.c:18` it is the 17 the generated row carries.

**2. From a generated artefact this change does not touch.**
`check_site_census.py` compares the mapping's per-bucket sums against
`xdata-registers.csv`'s `0x0860` row — `read 14 / write 2 / read+write 0 /
passed-to-call 1 / address-taken 0`, `refs 17` — and `HAND_CHECKED["0x0860"]`
in `xdata_register_map.py` pins the same buckets as a hand-read oracle, which
`--self-test` holds against a fresh generation of that row. Neither number
depends on a line number: they are counts of occurrences, and a line number is
not a number the census sums. **A count that changed would have meant
`ec/decompiled/` had changed.** It did not — and the direct evidence is that the
per-bucket-totals clause *never fired*, before this change or after it. The
`CORRECTION 2026-09-24, issue #180` header added **lines**; it added no
comparison, removed none, and reflowed none. So the count was never a free
parameter here, and what was left was a mechanical recompute, which is the
recipe `docs/findings/name-basis-and-groups.md` already records for #135's
one-line shift: recomputed from the tool's own `census_occurrences()` rather
than blanket-shifted.

So the corrected rows are these, and each is justified by the occurrences on the
lines it now cites rather than by being the old number plus one:

| site | `census_bucket` | `census_count` | `census_refs` | occurrences on those lines |
|---|---|---|---|---|
| `0x0D091` | `read` | 2 (unchanged) | `bank0/D091.c:45,49` | 1 + 1 |
| `0x0D0EF` | `read` | 6 (unchanged) | `bank0/D091.c:71,72` | 3 + 3 |
| `0x0D117` | `read` | 6 (unchanged) | `bank0/D091.c:75,76,77` | 2 + 1 + 3 |
| `0x0D144` | `passed-to-call` | 1 (unchanged) | `bank0/D091.c:84` | 1 |

**The shifts are not uniform** — 1, 1, 1 and **2** — because the #180 rewrite
also reflowed a closing paren out of the second boolean chain onto its own line,
which is the wrinkle #281 already recorded in the `HAND_CHECKED` correction. A
blanket `+1` would leave `0x0D144` citing `:83` and the suite still red, so this
is stated rather than left for a reader to infer a single offset from the three
rows that do happen to move by one.

Rows 6–10 of the CSV (`0x0D281`, `0x0D28A`, `0x0D31C` and the two `pd-image`
rows) were already correct and are **not** touched. `D281.c:19` and `D289.c:18`
were verified by reading the files, and the tool is green on them today.

## The prose twins, and what is not covered by any check

`ec/annotations/xdata-086x-dispatch.md`'s "The two methods, site by site" table
is the prose twin of these four rows, and it carried six stale references:
`D091.c:43,47`, `:69,70`, `:73,74,75`, `:81`, plus `D281.c:18` and `D289.c:17`.
Those became the CSV's new values and `:19`/`:18` respectively. Six cells are in
the one table and the two `D281`/`D289` cells are in the "What the census says"
paragraph above it — eight line-number cells in the file, still only cells: no
prose was rewritten. Fixing only the CSV would have left the page disagreeing
with the data it points at, which on `0x0D091` it already did by one line.

**Two of those cells were not stale from the #180 rewrite, and that is a
separate finding.** `D281.c:18` and `D289.c:17` were each one line low *before*
`#180` rewrote anything — a different and older drift, in a table that drifted
while the CSV was being maintained. The tool's docstring concedes it "cannot see
a sentence in `xdata-086x-dispatch.md`", but this is not prose: it is a table of
the same rows the CSV holds, and it had no check.

**Say plainly which of these a green suite does not cover.** The two `D281`/
`D289` cells, and the one line in `ec/annotations/xdata-register-map.md` that
repeats the same three numbers, are covered by **nothing** — the evidence for
them is a direct read of the committed `.c` files, and `test_check_site_census.py`
being green says nothing at all about whether they are right. Two edits in
`ec/tools/xdata_register_map.py` are the same: `HAND_CHECKED`'s *bucket values*
are checked by `--self-test`, and the stale line numbers in its comment are
checked by nothing at all. Anyone reading "the suite is green" as "the
documentation was verified" is reading in a check that does not exist.

## What this does not say

- **Nothing about what the EC does with `0x0860`.** This change moves a static
  count between two vocabularies of the same bytes. `XDATA_0860` is
  `present-untested` in `ec/annotations/registers.yaml` before and after, and a
  `write x2` census count is not evidence the EC acts on the value — it is
  evidence the decompile contains two stores, and the tool's own docstring says
  so about a bucket the census is blind to.
- **That the counts were re-verified against the firmware.** They were checked
  for *internal* consistency three ways — the census's own occurrence count, the
  generated row, and the hand-read oracle — all of which are statements about
  the committed decompilation. None of them is a statement about silicon.
- **That `refs 17` is a complete census.** It is a complete count *by this
  method*. The docstring's "what this does not check" list is unchanged: the 14
  other addresses, the two PD-image sites, and any byte reached through a
  computed DPTR or a table lookup.

## Reproducing it

From the repo root; `python3` 3.12 and the standard library only. No Ghidra, no
firmware image, no network, and no `--mode rebuild-project` — this is data, not
a decompilation.

```
$ python3 -m unittest discover -s ec/tools -p 'test_check_site_census.py'
OK

$ python3 ec/tools/check_site_census.py
0x0860: 7 site(s) agree across both methods, 2 unchecked (other program), 17
occurrence(s) accounted for once each -- read 14 write 2 read+write 0
passed-to-call 1 address-taken 0, refs 17

$ python3 ec/tools/xdata_register_map.py --self-test
all assertions passed
```

The suite's own count and elapsed line are left out for the reason
`docs/findings/runner-red-suite-set.md` gives: a total is a property of the
merge and re-stales with the next case to land. The tool's summary line *is*
quoted, because every number in it is the thing this branch is about and each is
pinned by the generated row rather than by a run.

The last command is the "the census totals are unmoved" evidence, and it matters
here specifically because two of this branch's edits are comments inside the file
that `HAND_CHECKED` lives in.

`tools/run-tests.sh` still ends `one or more FAILED`, on
`ec/tools/test_xdata_cluster_names.py` — that is #528's own `setUpClass`
failure, pre-existing, and untouched here. **This branch turns one of the
runner's two red suites green; it does not make the runner green**, and #162 is
still blocked by the one that is left. No suite or test total is quoted in
`docs/findings.md` either, for the same reason.

## Follow-ups this opens

1. **The prose table is unchecked and was already wrong independently.** The
   `D281.c:18` / `D289.c:17` cells were stale before the `#180` header rewrite.
   The tool's docstring concedes it "cannot see a sentence in
   `xdata-086x-dispatch.md`" — but a table of the same four rows the CSV holds
   is not a sentence, and it drifted while the CSV was being maintained. A check
   that the page's `D091.c`/`D281.c`/`D289.c` references resolve, or simply agree
   with the CSV, is the natural follow-up.
2. **`HAND_CHECKED`'s comment is correct for part of a day at a time.** #281
   corrected those line numbers on 2026-09-24; #180's header rewrite moved them
   again the same day, and this branch is the second correction. The CSV is
   machine-checked per site; that comment is not. Same class as (1), and the
   same check would take it.
3. **`ec/annotations/xdata-086x-dispatch.md`'s `xdata-registers.csv:662`
   pointer**, named in the "what the census says" paragraph and the last row of
   the table. The `0x0860` row is at **817**. A different cause — the generated
   register CSV has grown many rows since that pointer was written — so it is
   not this issue's drift and fixing it here would be scope creep into a
   different pin. Verified, so the next reader does not have to.
4. **`ec/annotations/xdata-register-map.md`'s "`--check` belongs in
   `check_ghidra_tooling`" bullet** already carries a dated correction beside the
   sentence that named two red suites, from this branch. It is the same
   prose-drift class once more, and there is now a third instance of it in three
   files — which is the argument for (1) and (2) as a single follow-up rather
   than three.
