# The region label as data: `bank-call-regions.csv`, and `entry_aligned` for the whole population (issue #1146)

The data-region label has been available to the tools since issue #50 and to
nobody else. `scan_refs.py` prints a trailing `in_data_region=N`,
`audit_call_targets.py` prints `in listed region` for bucket B and for the ten
highest-scoring bucket-C sites, and `bucket-c-codemap.csv` carries the label as a
column over bucket C. Every one of those is console output or a column on
another census, so a consumer that wants to ask the question has to re-run a
scan, and — the sharper half — **there was no way to ask the second question at
all**.

`docs/findings/ec-data-regions.md` §"The payoff" distinguishes *in a region*
from *on an entry boundary*, and argues the distinction from two named sites:
`0x06952` scores 24 of 24 anchors and sits 71 bytes into a stride-3 region,
`0x00381` scores 15 of 24 and sits 82 bytes into another. Neither is on its
grid. `data_regions.py --for-offset` computed the second question for one
address on demand and nothing computed it for a population, so the argument
could not be checked against the sites it is about.

`ec/annotations/bank-call-regions.csv` is that population, committed and
generated. `ec/tools/bank_call_regions.py` writes it, `--check` re-derives every
cell of every row from the committed image and `data-regions.yaml` and fails on
any mismatch, and `--self-test` holds the refusals.

## What is in the file

One row per **bucket-C** site and one per **paged `ajmp`/`acall`** site — the
two populations the issue names, both carried whole rather than sampled. `family`
says which, and `file_offset` alone is the key: a byte in `(0x02, 0x12)` has low
five bits `0x02`/`0x12`, neither of which is a paged opcode, so the two sets are
disjoint by construction and one sort key has no tie to break. That is what lets
two branches that both regenerate the file produce the same bytes.

Every figure below is a property of `ec/firmware/GMxMGxx_11.800` and the byte
scan over it, re-derivable with the commands in §"Re-deriving":

| population | sites | inside a listed region | entry-aligned | inside but off the grid | cell left undefined |
|---|---:|---:|---:|---:|---:|
| bucket C | 140 | 35 | 11 | 22 | 2 |
| paged `ajmp`/`acall` | 3,481 | 66 | 29 | 15 | 22 |

Bucket C's 35 split 21 into `common-032f-ljmp-table`, 10 into
`common-055a8-be-words`, 2 into `common-0656-address-table`, 1 into
`common-690b-ff-triples` (`0x06952`) and 1 into `common-6e7d-be-words`. The
`140 − 35 = 105` agrees with the 105 `data-regions.yaml`'s own header and
`ec-data-regions.md` §Limits already record, which is a cross-check that the two
walks are describing the same 140 rather than each finding their own.

**The two numbers worth reading together are the third and fourth columns.**
Of the 35 bucket-C sites the map places, **22 are inside a region and off its
grid** — nearly two to one against the 11 that are on it. A region label alone
would have called all 35 the same thing.

**In bucket C the answer is decided entirely by the region's stride.** All 22
`no` sit in a stride-3 region — 21 in `common-032f-ljmp-table` and `0x06952` in
`common-690b-ff-triples` — and all 11 `yes` sit in a stride-2 word table, 10 in
`common-055a8-be-words` and one in `common-6e7d-be-words`. No bucket-C site in a
stride-3 table is on its grid and no site in a stride-2 table is off it. That is
the phantom reading made mechanical: the bucket-C population concentrates on the
`ljmp` dispatch table, and a 3-byte grid is what a walk one byte out of frame
misses every time.

**The paged family does not split that way, and the contrast is the useful
part.** Its answer varies *within* a region: `common-055a8-be-words` holds 27
`yes` and 4 `no`, and `common-6e7d-be-words` holds 2 of each, while the three
regions whose stride is 3 or 6 — `common-032f-ljmp-table`,
`common-219c-ff-triples` and `common-6e65-repeat-bytes` — contribute only `no`.
So the stride is not the whole story there, and a reader who carried bucket C's
arithmetic over would be wrong. What the two populations share is the shape of
the question: for both, a region label on its own cannot tell a table entry from
a misframed one, and only the grid can.

## `entry_aligned`: three values, keyed on `confidence`

The issue asks for the meaning stated per shape and offers "leave the cell empty
and say why" for `common-0656-address-table`. The rule here keys on the YAML's
`confidence` field instead, which is the one design call worth arguing:

- **`read-by-hand`** → the extent was read, so `stride` is a claim about a
  uniform entry grid, and `yes`/`no` answers a real question. For a
  `repeat-bytes` region the stride is the *pattern length*, so "aligned" there
  means on a pattern boundary — defined, different, and the header says so. All
  four `repeat-bytes` sites in the file come out `no`, and each sits 3 bytes into
  `common-6e65-repeat-bytes`'s 6-byte pattern — which is what being a misframed
  read of a repeating byte pattern looks like.
- **`inferred`** → the extent was extended by pattern.
  `common-0656-address-table`'s own `note` says the stride is not uniform: 121
  of its 176 words are `0x032F + 3k` and the rest are not on that progression.
  A modulo test there answers a question the file does not pose, so the cell is
  **empty** and `region_confidence` says why in the row itself. This is not
  hypothetical: **all 24 undefined cells in the file are
  `common-0656-address-table` sites** — 2 bucket-C, 22 paged.

  **This supersedes a `yes`, it does not reverse one.** `ec-data-regions.md`
  §"The payoff" records `0x00686` and `0x0067E` as entry-aligned `yes` in this
  same region, and this file leaves both cells empty. The two answers are not in
  conflict: the table's `yes` is the answer to `entry_offset % 2 == 0` for a
  region whose `note` declines to claim a stride of 2, and the entry offsets
  happen to be even (48 and 40). The cell here is undefined because the grid is
  not a claim, so this file answers nothing rather than the weaker thing — and
  the table carries the same note beside those two rows.
- **`inferred-unchecked`** → empty for the same reason, with no new list: it is
  the tier `--check` cannot reach, so the grid is not a claim either. No entry
  carries it today.

Keying on `confidence` rather than on `shape` because it is a field the source
of truth already carries, that `data_regions.py`'s `load()` already validates
against a closed vocabulary and `unchecked()` already filters by, and that a
future `inferred-unchecked` entry reaches with no edit here. A shape-keyed rule
would hardcode a list into a *new* tool and need editing whenever a shape is
added — the shape-vocabulary coupling
`test_data_regions.py::test_vocabularies_are_the_ones_the_header_documents`
exists to prevent, and re-creating it one file over would be the same mistake
twice.

**The two empties are distinguishable from the row alone**, which is what
`in_data_region` earns its place for: `no` means no region was found and the
question does not arise; `yes` with an empty `entry_aligned` means a region was
found and the question is undefined *for it*. `--check` refuses either
conflation rather than tolerating it.

**The honest boundary of the rule.** A future `read-by-hand` region with a
genuinely non-uniform grid would get a `no` where the right answer is undefined.
That is the weaker of the two possible failures — the reverse would silently
assert an alignment the file does not claim — and `--check` re-deriving the
stride from the image is what catches such an entry when it is added. It is
written down here and in the CSV's own header rather than left implicit.

`region_stride` and `entry_offset` are columns for the same reason: they make
`entry_aligned` **re-derivable from one row and no YAML**
(`entry_offset % region_stride == 0`), so the cell cannot be a hand-written
value that happens to agree. The suite re-derives every populated cell that way.

## Why a sibling and not another column

`bank-call-targets.csv` and its sibling per-site tables are unchanged, as is
`build_ec_decompile.py`'s `CALL_TARGET_COLUMNS`. The reason is already in the
tree: that list is marked *asserted rather than assumed* and its `--self-test`
runs in the cheap gate, so one more column turns a gate assertion red for an
unrelated cause — the cheapest way to get a gate switched off.
`audit_call_targets.py`'s `write_paged_csv()` docstring sets the precedent
("a sibling of `write_csv()` rather than more columns on it"); a committed
sibling is that one step further.

`ec/tools/test_data_regions.py` is **not edited** by this work. Its
`test_audit_call_targets_leaves_write_csv_untouched` asserts `write_csv()`
carries no region string, and the new suite asserts the same contract from this
side, so the sibling's obligation is stated without touching a shared suite.
Leaving that file byte-identical is the strongest available statement that the
existing test stays green.

## `--check`, and why this is not a hand-kept artefact

`--check` never writes, and a **missing** file fails rather than being created —
`bucket_c_codemap.py`'s arrangement, whose `check_csv()` records why: writing it
would make `--check` the thing that decides what the committed table is. It has
two halves:

1. **Re-derive every cell of every row** from the image and the YAML and diff,
   naming the first differing `file_offset` and both values rather than
   printing a count. A dropped or re-ordered row names the offset that moved.
2. **Validate every committed row** against the refusals — the regenerated
   rows rather than the committed ones would only prove the writer agrees with
   itself.

The population is pinned as a **join, not a census**: this file's `bucket-c`
`file_offset` set must equal the set in `bank-call-targets.csv` whose `bucket` is
`C`, and its `paged` set must equal the set in `bank-paged-call-targets.csv`.
That is a relation that moves when those files move. **Nothing in `--check`
asserts a figure.** The audit's own 140 / 83 and 3,481 are held as assertions in
`--self-test`, transcribed from `bank-call-audit.md`'s headline on
`bucket_c_codemap.py`'s stated ground — a committed document's figure, not a
count of the tree.

The `--self-test` refusals — an unknown region name, a `file_offset` outside the
image (both `< 0` and past the end), a cell outside its closed vocabulary, the
`in_data_region`/`region_name` conflation in both directions, and an
`entry_aligned` computed against a null stride — were each **run once with the
mutation in place** to confirm they go red, which is the discipline
`data_regions.py`'s shifted-span mutations follow. The oracle beside them is
transcribed from `ec-data-regions.md` §"The payoff", not from this tool:
`0x055DC` and `0x06E83` entry-aligned, `0x06952` inside
`common-690b-ff-triples` at 71 bytes of a stride-3 region and **not**
entry-aligned, `0x00381` likewise at 82, `0x021C6` outside every region, and
`0x00686` inside `common-0656-address-table` with an empty cell for the third
answer. A tool that graded its own map against itself would pass whatever the
map said.

## What this does not settle

- **Nothing here is a behavioural claim.** No register was read back, no EC was
  opened, no capture was read. Both inputs are committed files, which is why the
  gate wiring below is in the cheap tier and not the deep one.
- **No `status:` in `registers.yaml` moves.** These are addresses in a code
  image, not XDATA registers.
- **A site inside a listed region is not thereby a table entry, and
  `entry_aligned=no` is not a verdict.** It says a byte is not on the grid a
  `read-by-hand` region claims. The phantom reading is a strong prior —
  `ec-data-regions.md` §"The payoff" argues exactly this for `0x06952` and
  `0x00381` — and it stays a reading. `converges_from()` measures framing, not
  meaning, and `0x021C6` is the standing reminder: 24 of 24 anchors, no region,
  still unexplained.
- **`in_data_region=no` never means "a call".** A zero is "not found by this
  method", never "absent" — `docs/findings.md` §4c, and this file's entire
  subject is one method's blind spots.
- **The relative-branch family is absent**, and the reason is scope rather than
  oversight: the issue named these two populations,
  `bank-relative-branch-targets.csv` is already a further sibling, and nothing
  about the argument above is specific to it. It is a one-line extension of the
  same walk when it is wanted.
- **It does not settle bucket C.** The 140 sites, 83 anchored, stay `None` from
  `offset_for_runtime()`, and "no direct common-to-bank `lcall`/`ljmp` was found
  by this method" remains the whole claim. What this adds is that 35 of them now
  carry a name for what would have to be found next, and which of those 35 are
  on a grid rather than merely inside a span.

## Gate wiring: the fold

A seventh `ec/tools/` entry has no free line left in
`agent-gates.sh`'s tool list — `prepared-gate-patches.md`'s collision table says
so, and the header of the patch below records the same for the fold that came
after. So **`--check` and `--self-test` fold into
[`../ci/agent-gates-disasm8051-self-test.patch`](../ci/agent-gates-disasm8051-self-test.patch)
as its fourth tool**, rather than shipping a standalone seventh file that would
have to cut the same `windows/tools/decompile_native.py; do` line and would then
fail only `CompositionTests`, having applied cleanly alone. The arm runs
`--check` **and** `--self-test`, on `data_regions.py`'s reason: `--check` is the
mode that holds the file to the image, and the arm is what keeps the tool off the
`*)` default, which passes `--work "$scratch"` and a flag this tool does not take.

`ArmRetentionTests.REQUIRED` gains both halves — the extended `\`-continued list
entry and the new arm — because a re-cut that lands three of the four tools'
halves still applies, still composes, and still passes every other case in that
suite. That is the whole reason the class exists.

`.github/scripts/agent-gates.sh` itself is **not** edited: a branch touching
`.github/` cannot be pushed (the pipeline's push token has no `workflow`
scope), so it would fail at the very end of the PR rather than the start. A
human lands the prepared patch. **Until they do, the file can drift from the
image in an otherwise-green PR**, and nothing here is gated either way. What
landing it would buy is that the committed table cannot drift; what it would not
buy is anything about the table being *right*, which is the `read-by-hand` tier
and a human's.

**The suite runs ungated either way**, and that is a real loss worth naming: it
is collected by `bash tools/run-tests.sh` and by nothing in `.github/`. Its
absence from a gate is the same absence `test_earlier_record_column.py` records
for the `earlier_record` column, and the same reason the patch exists.

## Re-deriving

```console
$ python3 ec/tools/bank_call_regions.py ec/firmware/GMxMGxx_11.800 --write
$ python3 ec/tools/bank_call_regions.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/bank_call_regions.py ec/firmware/GMxMGxx_11.800 --self-test
$ bash tools/run-tests.sh ec/tools                # collects this file's suite
```

Nothing in that list needs Ghidra, the network, an assembler, `r2`, a capture or
hardware — two committed files, which is why the cheap tier is the right tier
for the fold.
