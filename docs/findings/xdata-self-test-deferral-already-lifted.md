# The self-test deferral #628 was filed against had already been lifted, and one file still described it in the present tense (2026-10-03, issue #628)

[Issue
#628](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/628) was opened from
the third follow-up of [`thunk-prefix-collision.md`](thunk-prefix-collision.md),
on the strength of a measurement that was correct when it was filed and was
false by the time the issue reached implementation. Both of its deliverables had
already landed. This file re-measures against the committed tree, records which
clauses of the two tracker issues resting on the same premise the measurement
falsifies, and corrects in place the one file still describing the deferral as
live.

**Nothing here is a register behaviour, a live test, or evidence about the
laptop.** `xdata_register_map.py`'s two modes read committed text only — the
decompiled tree, two annotation CSVs, and the committed `ec/decompiled/*/*.asm`
that `--self-test` adds. No firmware image is opened, no Ghidra project is
touched, no register is read back, and no hardware or Windows step is needed to
close this issue.

## The measurement, re-run on this tree

From the repo root, 2026-10-03 at `f1256314`. The exit codes are the claim; the
timings are one runner's and are recorded so a later reader who re-derives them
knows the numbers are not expected to match.

```console
$ python3 ec/tools/xdata_register_map.py --check | tail -1 ; echo $?
.../ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5
0

$ python3 ec/tools/xdata_register_map.py --self-test | tail -1 ; echo $?
  all assertions passed
0

$ git status --porcelain | wc -l
0
```

Neither mode writes, which is what makes them safe in a per-commit gate and not
only locally. `--check` took 2.81 s and `--self-test` 7.08 s here; the existing
[`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md) records the
same shape across three runners, where the ratio rather than either absolute
figure is the durable part. **The census figures above, and the ones in that
file and in the issue, are a dated reading of a census that annotation tranches
keep moving.** The commands above are the way to re-derive them; none is a claim
that survives a later merge unchanged.

**The issue's own figures disagree with this tree, and the disagreement is the
census having grown, not the mode having changed.** Its cluster and main-EC
address counts are both lower than the block above's. Its load-bearing claim —
that the mode is green — is confirmed, so the work proceeds and this file cites
the fresh run rather than the issue's numbers.
[`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md) already
records that the issue's own cluster count "is long gone".

## Both of the issue's deliverables already existed

1. [`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md), filed
   under #815, already records the measurement, the three `index.csv` rows and
   their names, the comment, and the decision on which tier the mode belongs in.
2. `.github/scripts/agent-gates.sh`'s census arm already runs **both** modes —
   `python3 "$tool" --check && python3 "$tool" --self-test || rc=1` in the
   `*xdata_register_map.py)` case of `check_ghidra_tooling()` — and the comment
   above it already opens "**`--self-test` used to be deliberately not run, and
   the reason it gave is no longer true.**", keeping the stale claim visible
   beside the correction per [`../findings.md` §4a-4d](../findings.md).

So this is not a re-implementation, and re-preparing finished preparation would
be the no-diff case the repository warns against.

### The three rows the old comment blamed

The comment said the mode was red "for a reason no census change can clear"
because the annotation CSV named three functions that `index.csv` still spelt
`FUN_CODE_*`. Those rows, as committed, quoted by address and name rather than
by line:

| address | `ec/decompiled/index.csv` name |
|---|---|
| `bank1:0x9CE8` | `seed_1c12_trio_or_update_1c11_1c15_1c16` |
| `bank1:0x9D53` | `seed_1c12_trio_9f_or_run_0x9d7a_ladder` |
| `bank1:0xE2D3` | `dispatch_036c_low3_then_seed_1c00_block` |

```console
$ grep -c "FUN_CODE_9CE8\|FUN_CODE_9D53\|FUN_CODE_E2D3" ec/decompiled/index.csv
0
```

## The #512 and #576 clauses

Both are GitHub-tracker items rather than files, and this repository cannot
correct an issue body; that is a human's action. What can be recorded here is
the measurement that falsifies them, which is what #628 asks for.

- **#512**, first clause — "`xdata_register_map.py --self-test` exits 1 on the
  committed tree — `0x07C7` and `0x07C8` have no `NOT_IN_TREE` reason" — is
  false on two counts now. The mode exits 0, and the tool's `NOT_IN_TREE` dict
  carries a reason for each address, both opening "not found by this method",
  which is the calibrated phrasing rather than a claim the bytes are gone. Its
  second clause, "and no per-commit gate runs the tool that would have said so",
  is also false: the cheap tier runs `--self-test`.
- **#576**, "the one assertion left red in `xdata_register_map.py --self-test`".
  There is no assertion left red.

## The one false statement left in the tree

`thunk-prefix-collision.md` §"A gate comment that is wrong about a mode being
red", and its follow-up list item 3, still said in the **present tense** that the
cheap tier defers the mode, that it "is switched off for nothing", and that
"turning it on belongs to whoever owns the pipeline". #628 was filed *from* that
follow-up. The mode was turned on and the comment rewritten; the follow-up that
generated the issue was never closed against it. That is the one false sentence
a future reader still meets, and it is corrected in place in that file rather
than left for a reader to notice.

## A premise in the issue worth correcting here

The issue scopes the gate edit out because "the plan stage's push token has no
`workflow` scope". That is wrong *for this file*, and the repository has already
settled it: **`.github/scripts/` is pushable — only `.github/workflows/` and
`.github/actions/` are not**, recorded under "One clause in it is named rather
than answered" in [`xdata-green-set.md`](xdata-green-set.md). It changes nothing
here, because the gate needs no edit, but saying so keeps the next reader from
inheriting a wrong reason for a decision. The general constraint still stands
for the two directories that really are blocked.

## Named and deliberately not touched

- [`../findings.md`](../findings.md) — frozen; `check_findings_frozen.py` fails
  any addition.
- `.github/scripts/agent-gates.sh` — **nothing to change**: the comment is
  already corrected and the arm already runs both modes. Editing it is also what
  would invite a re-copy of the `agent-pipeline` template to revert #815's
  correction.
- `ec/annotations/xdata-register-map.md` — already carries #815's in-place
  `CORRECTION (2026-09-25, issue #815)` blockquote. Nothing to add.
- [`xdata-green-set.md`](xdata-green-set.md) — already carries the #836
  blockquote answering its own row, and records that the row is a dated
  measurement. Editing it would re-litigate a correction that landed.
- `ec/tools/xdata_register_map.py` — **not edited at all.** The assertions are
  unchanged; what this issue needed recorded is what runs them, and that already
  runs both.

## What this does not establish

Nothing about the firmware, and nothing about the laptop. A register write being
accepted is not evidence the EC acts on it, and none of the assertions the mode
runs is a behavioural claim: they are counts, names, bucket directions and
refusals, checked against committed text. Re-running them says the committed
CSVs and the committed export still describe each other; it says nothing about
whether any address in them does anything on the machine.

Nor does it close #512, #576 or #628. It records the measurement under which
each of their premises stops holding; correcting the issue bodies, and deciding
whether the mode's new coverage should reach a more expensive tier, are a human's
actions on the tracker.
