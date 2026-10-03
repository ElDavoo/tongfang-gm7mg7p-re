# What a re-encode row outside `OUTCOMES` does to a run, to `--check`, and to the report (issue #230)

`ec/tools/verify_reassembly.py` has five outcomes a re-encode can attach to a
row that are not measurements of the firmware, and until now nothing said what
any of them did. `run_status()` returned 0 for anything that was not
`mismatch`; `check()` named a residual row and then passed it; and
`write_report()` wrote whatever came back, so one `error` row could be committed
and be named by that residual line on every per-commit run from then on. All
three read the same thing and none of them failed.

The answer is that **all five fail**, and the reason is not that they are
serious. It is that they are not measurements. `mismatch`, `partial`,
`assembler-gap` and `listing-gap` are all measurements of the firmware, and each
keeps the policy it had. The five residual outcomes are not measurements at all,
so the calibration the tool already runs on does not reach them — see [Why the
existing calibration does not stretch](#why-the-existing-calibration-does-not-stretch).

`docs/findings.md` §14g, "The nightly re-encode says which assembler answered
and what moved", is where the question was raised; this is the settlement.

## The policy, per outcome

| outcome | produced at | full run | `--check`, committed row | why it lands there |
|---|---|---|---|---|
| `mismatch` | `check_one()` | 1 | FAIL | unchanged; the firmware bytes are the arbiter, and it is the one outcome the tool's own assembler warning calls "worth watching" |
| `partial` | `check_one()` | 0 | 0 | unchanged; measured — the expressible instructions re-encoded and the rest are named in the row |
| `assembler-gap` | `check_one()` | 0 | 0 | unchanged; measured — `sdas8051` declined every form in the function |
| `listing-gap` | `check_one()` | 0 | 0 | unchanged; measured — the assembler ran and exited 0, and `read_lst()`'s parse had no entry where one was expected |
| `assembler-error` | `check_one()` | **1** | **FAIL** | `sdas8051` refused the listing; the comparison never happened |
| `error` | `run_rows()` | **1** | **FAIL** | a worker raised; the comparison never happened |
| `missing-listing` | `check_one()` | **1** | **FAIL** | the row names a listing that is not on disk |
| `empty-listing` | `check_one()` | **1** | **FAIL** | the listing parsed to zero instructions, so there was nothing to re-encode |
| `skipped` | `check_one()` | **1** | **FAIL** | the index row carries no listing to check; see [reachability](#skipped-is-unreachable-and-still-fails) |

`missing-listing` and `empty-listing` are corpus drift rather than a
disagreement about bytes, and `check()` already fails on drift of the same shape
one screen earlier: a key in the report that the listing index does not have is
`FAIL ... the report is stale`. A report row naming a listing that is gone is
the same defect wearing a different column.

## Why the existing calibration does not stretch

The tool has a deliberate, written-down calibration, and it is a good one. A
`NOTE` that the live assembler differs from the one the committed report was
measured with is a warning. A category that moved since the committed report is
reported. `--limit` compares nothing. All three stand, and this change does not
touch `compare_assembler()` or `compare_tally()`.

The reason a residual is not covered by that calibration is a difference in kind
rather than in severity. Every case the calibration was written for is **two
measurements that disagree**: this run's assembler against the committed one,
this run's tally against the committed tally. Both sides exist, both are
honest, and the disagreement is resolved by re-running under the pinned build or
re-reporting. A residual is **one measurement absent**. There is no second side
to disagree with, so none of the calibration's remedies applies to it — and the
thing it would leave behind is a report row asserting that a function was
re-encoded when no assembler ever saw it.

That is a false claim about coverage rather than a noisy one about a count.
It is why the answer is not "still passes".

## The policy is keyed on `outcome`, and why the `detail` column cannot carry it

§14g's race reported `assembler-error` **and** a `no bytes emitted at ....`
detail for the same functions. That second string is not a fingerprint of a
residual: it is a `listing-gap` detail, and it is also the detail on most of the
committed `assembler-gap` rows, because the committed report predates the split
that gave those two outcomes separate names.

Measured on the committed report:

```console
$ python3 - <<'PY'
import csv
rows = list(csv.DictReader(open("ec/ghidra/reassembly.csv", newline="")))
gap = [r for r in rows if r["outcome"] == "assembler-gap"]
fingerprint = [r for r in gap if "no bytes emitted" in r["detail"]]
print("%d of %d assembler-gap rows carry a `no bytes emitted` detail"
      % (len(fingerprint), len(gap)))
PY
52 of 58 assembler-gap rows carry a `no bytes emitted` detail
```

So a policy read off `detail` would take 52 measured rows with it and turn
`--check` red on a tree whose committed report is correct. `unmeasured()` reads
the `outcome` cell and nothing else, which is what leaves `assembler-gap` a
measurement and keeps the policy the tool already had for it.

## The committed report as committed today

The same file, tallied the same way, holds no residual at all — so the policy
that fails on one is green on this tree, and `--check` going red later means a
real defect rather than this change:

```console
$ python3 ec/tools/verify_reassembly.py --check
  reassembly report: 2586 match, 73 partial, 58 assembler-gap, 0 listing-gap, 0 mismatch (of 2717)
  listing digests: 2717 compared against the committed report, 0 disagreement(s)
  listing names: 2717 compared against the listing index, 0 disagreement(s)
  all checks passed
```

That is a measurement of *the file as committed today*, not a claim that this
tool cannot produce a residual. It can, and `run_rows()`'s wrapper turns any
exception into `error` on purpose.

## `skipped` is unreachable, and still fails

`verify()` filters its rows to `r["out_file"] and not r["out_file"].startswith("(")`,
which drops exactly the rows `check_one()` would have answered `skipped` for, so
today `skipped` cannot reach a report through the full run. It is settled to
fail anyway, on two grounds.

A policy that fails an unreachable outcome costs nothing, and a policy that
passes one is a trap for the next caller that skips the filter — the same trap
this write-up is closing, one outcome further out. And the reachability is a
*measurement* rather than a claim: `--self-test` reads the committed listing
index and calls `check_one()` on every row the filter drops, asserting each one
answers `skipped`. Asserting the relation rather than a population figure is
deliberate — the filter and the outcome are two pieces of code and nothing else
holds them together.

## `write_report()` refuses, and the old report survives

A run carrying any outcome outside `OUTCOMES` is not written at all, to any
destination. The file's columns claim a measurement per row and its `assembler`
cell says which run produced it, so a row labelled `error` in one is a claim
about coverage that nothing established. A scratch `--emit-csv` carrying one is
the same broken claim in a file nobody reads the `assembler` column of, which is
why the refusal sits in `write_report()` rather than in the `--report` branch of
`main()`.

Refusing rather than writing-with-a-marker has a property worth stating, because
it is the reason the failure lands where it does. The refusal leaves the
**previous** file at that path in place, and the previous file is still an
honest description of the run that produced it. So `--check` stays green while
the run that could not measure goes red: the failure lands on the run, not on
the artifact that was correct when it was written.

Nothing is lost diagnostically. The run's own stdout has already named these
rows, through `compare_tally()`'s `moved` list: it carries a row whose outcome
differs from the committed one, and a row the committed report has no entry for,
and the committed report holds no residual, so every one of these is on that
list.

## One predicate, three readers

The defect was structural before it was behavioural. `run_status()` and
`check()` were two independent readings of `mismatch == 0`, and nothing made
them agree, so nothing noticed when they did not. They now both read
`unmeasured()`, which decides by membership of `OUTCOMES` rather than by a list
of five names — so an outcome nobody has thought of yet fails too, rather than
passing by omission. `UNMEASURED` holds the five this file can produce and the
sentence each one prints; it is the documentation, not the gate.

## What this does not claim

- **No run was re-executed and no tally re-derived.** `REPORT_COMMAND` needs
  `nix build nixpkgs#sdcc`, and `project-setup` installs Ubuntu's `sdcc` rather
  than the shell the committed report was measured in. Every figure here is read
  out of the committed CSV by the commands shown beside it.
- **`ec/ghidra/reassembly.csv` was not regenerated,** and does not need to be —
  it holds no residual, which is the measurement above.
- **The self-test asserts the predicate and `check()`'s use of it, not the whole
  of `check()` against a synthetic report.** It does assert `check()` end to end
  over the committed report with one row's `outcome` changed and nothing else
  touched, which is what makes "the residual is the only thing that turned it
  red" a measurement rather than an inference; the byte check, the digest join
  and the name join all still pass in that case because only one cell moved.
- **`main()`'s `--report` branch is not exercised end to end.** It needs a
  re-encode, so there is no assembler-free way to drive it; what is tested is
  `write_report()`'s return value, which is the whole of what that branch reads.
- **Nothing was read from the EC, the BIOS or `GCUService.exe`.** The change is
  to a tool that reads committed files, and no hardware step is owed by it.