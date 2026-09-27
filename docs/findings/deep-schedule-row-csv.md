# What a landed nightly would leave, and what its first reading is

`verify_reassembly.py` grew `--emit-csv` so a night could be compared with the
committed report row by row. Nothing passed it: `.github/scripts/agent-gates-deep.sh`
runs the re-encode with no such flag and removes its scratch directory on exit,
so the only per-row content of a run was `verify()`'s moved-row list, capped at
`MOVED_CAP` with an "and N more" after it. The flag existed, the schedule that
would have used it did not pass it, and the per-row evidence for
`docs/findings.md` §14h — `evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv`
— exists only because a person ran the command by hand.

This is what closing that gap looks like, and what the first reading of a
night's CSV against the committed report actually says.

## What changed

`docs/ci/agent-gates-deep-schedule.yml` — the prepared workflow, the one file
in this story an agent may edit, because landing it is a human's `cp` — gains a
step after `Deep gates` that re-runs the re-encode with `--emit-csv` to
`$RUNNER_TEMP/deep-gates-csv.csv`, and a second `upload-artifact` carrying it as
`deep-gates-csv-${{ github.run_id }}` beside the log. The step is `if: always()`
for the reason the log's own upload already carries, and it appends a delimited
section to the log naming both the artifact and the file, so a reader holding
only the log knows where the second half is.

`tools/check_deep_schedule_emit.py` holds the wiring's shape, and `--diff` is
the reader half: it joins two report CSVs on `(program, addr)` and prints every
row that moved, **uncapped**. The cap is the defect being fixed, so the tool
that fixes it does not have one.

`SDAS8051` is set empty on purpose. `find_assembler()` prefers it over `PATH`
and an empty value is the same instruction to it as an unset one, which is what
`evidence/ec-reencode/2026-09-23-sdas8051-versions.md` did deliberately. It
matters because the committed report was measured with a pinned nix build —
2,704 of its 2,711 rows, and the 7 exceptions are rows `d8525eae` added or
replaced later under apt without re-running the rest — and the runner installs
apt SDCC: a non-empty `SDAS8051` would put a *third* binary in the picture and
the CSV's `assembler` column would name something the schedule's own "Name the
assembler" step never printed. The 7 do not disturb the 52 below: all 58
`assembler-gap` rows are on the nix build and all 7 apt rows read `match`.

## The first reading, and the part that is not the assembler

Measured on this tree at `e38ee864` (2026-09-27), on the runner the schedule
targets — `sdas8051` from `project-setup`, SDCC 4.2.0 — with the schedule's own
command:

```sh
scratch=$(mktemp -d)
SDAS8051='' python3 ec/tools/verify_reassembly.py \
    --work "$scratch/reasm-csv" --jobs 4 --emit-csv "$scratch/night.csv"
python3 tools/check_deep_schedule_emit.py --diff "$scratch/night.csv" \
    ec/ghidra/reassembly.csv
```

The re-encode took **3.62 s** and wrote 2,711 rows. The join found both files
carrying 2,711, the key sets identical, no row on one side only, and the two
headers byte-identical. **190 rows moved**, and they are two different things:

- **52 rows moved on `outcome` and `detail`.** Every one of them reads
  `assembler-gap` on the committed side. This is §14h's difference, reproducing
  exactly and in the same direction: the apt ASxxxx places forms the nix one
  declines. Standing, documented, and not an alarm.
- **140 rows moved on `name`, 138 of them on `name` alone.** The other 2 are
  also among the 52 above — `common,0022` and `pd,EA67`, both in
  `evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv` — so the two classes
  overlap by 2 and 52 + 140 − 2 = the 190. The 2 are where a rename and the
  assembler difference land on one row, which is the case worth naming rather
  than rounding away: a row in both is a row whose `outcome` argument and whose
  `name` argument are the same row's story.

`listing_digest` — the column that says whether the *code* moved — is identical
on all 2,711 rows. So the second class is a label, not a measurement: a function
renamed after its row was written still shows the name it had then. The evidence
is in the history, not in the reading. `bank0,708F` is
`div_r6r4_by_r5_16bit` in `ec/annotations/ghidra-functions.csv` and in
`ec/decompiled/listing-index.csv` today, and `FUN_CODE_708f` in the report; the
rename landed at `37140548` (2026-09-25, #327), and the report's `name` cell
for that address was last written at `a56b3bbf` (2026-09-24) — before the
rename. `verify()` reads `name` out of the listing index at run time, so a fresh
run sees the new name and a `--report` rerun would write it; the report simply
has not been regenerated since, because re-reporting is a deliberate act tied to
a measurement changing and these were annotation changes with no measurement
behind them.

**Why the tool prints which column moved.** 190 rows with no breakdown reads
as "the re-encode disagrees with the report", which is the wrong conclusion and
would send a reader to a re-encode bug that is not there. Naming the column
turns one alarming number into a boring one and a real one, and it is the one
thing a capped list of twenty lines could not have done — a reader who saw the
first twenty rows of a 190-row diff would have seen only `name` changes and
concluded the assembler had nothing to do with it.

**`ec/ghidra/reassembly.csv` came back byte-identical**, which is
`refuses_committed_report()` holding from outside. That invariant is worth more
here than it first looks, and this reading is the argument: `--report` on this
runner would replace a report measured with the pinned nix build by one measured
with apt, wholesale, and the `assembler` column of every row would be the only
thing saying so. Writing to `runner.temp` is not tidiness; it is the only thing
between a nightly and a silently re-based report.

## What this is not

- **No nightly ran.** `docs/ci/agent-gates-deep-schedule.yml` is prepared, not
  landed, so nothing in this repository has ever executed it. Every claim above
  is about a file's shape, a tool's output over two CSVs, and one re-encode run
  on this runner — not about an artifact. "A landed nightly leaves two
  artifacts" is the acceptance criterion this prepares for and cannot
  demonstrate; landing it is one `cp` by a human, and the push token for this
  branch has no `workflow` scope, so `.github/` is out of scope entirely.
- **The 190 is not a finding about the EC.** It is 52 rows of a known assembler
  difference and 138 rows of a known annotation drift, both already accounted
  for. What moved in the firmware is nothing: `listing_digest` is unmoved
  everywhere and `mismatch` is 0 on both sides.
- **A moved row settles nothing.** 90-day retention, like the log beside it. A
  result that actually changed wants a re-report and a write-up here, not an
  artifact.
- **No EC, no BIOS, no Windows, no hardware.** Nothing in this change touches
  them, and nothing here is preparation for a hardware or Windows run.

## The durable fix, and the one question this opened

The standing 52 is an assembler version difference, and it would go away by
construction if `.github/actions/project-setup/action.yml` installed the same
pinned nix build the committed report was measured with. That file is
template-copied and out of scope for the same reason `.github/` is, so it is
named here rather than done. Until then the nightly's CSV disagrees with the
committed report every night, by a number that is known and documented, and the
value of the artifact is *which* rows, *which* night and *which* assembler.

The question this opened, for whoever picks it up: **should
`--emit-csv` refresh the `name` column of a row already in the report?** Today
it cannot — it writes to a different file, so the two never meet — and the
answer bears on whether a re-report is a wholesale replacement or a merge. It
is a question about `verify_reassembly.py`, which this change does not edit:
the invariant is re-asserted from `tools/check_deep_schedule_emit.py` instead,
which is why that file exists rather than a `--self-test` case inside a 2,268-
line tool other branches are near.

## Reproducing any of it

No assembler, no Ghidra, no network, no hardware:

```sh
python3 tools/check_deep_schedule_emit.py            # the wiring's shape
python3 tools/check_deep_schedule_emit.py --self-test
bash tools/run-tests.sh tools
```

The figures in "The first reading" want an `sdas8051` on `PATH`, which is what
`.github/actions/project-setup` installs. They are of the tree at `e38ee864`
and are reproduced, not carried forward: a tree with more renamed functions
would show a larger second class, and a tree whose report has been re-reported
with the nix build would show no first class at all.
