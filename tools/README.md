# Repository tools

One thing lives here, and it is the one command that runs this repository's
offline `unittest` suites:

```sh
bash tools/run-tests.sh
```

## What it runs

Every `test_*.py` under the repository, found by `find` — not a hardcoded list,
so a suite in a directory that does not exist yet is picked up by having its
file committed. There are eight today, 138 tests in all, and each is a `unittest`
suite standing in for a tool's own behaviour:

| suite | what it stands in for |
|---|---|
| `ec/tools/test_grade_0751_isolation.py` | `ec/tools/grade_0751_isolation.py`, the §4 grader of the `0x0751` capture procedure, against the committed `testdata/` fixtures |
| `ec/tools/test_walk_branch_arms.py` | `ec/tools/walk_branch_arms.py`'s direction classification, bounds, refusals, and negative-result wording |
| `windows/tools/test_manual_fan_ctrl_probe.py` | the fan-mode probe's two-arm byte script |
| `windows/tools/test_ec_watch.py` | the mark-CSV sweep and the mark landing between two change rows |
| `windows/tools/test_ec_validate.py` | the `ec_validate.py` `0x0436` capacity arm's exact-copy scoring, full-capacity bound, CSV, and `0x0400-0x045F` page assertion |
| `windows/tools/test_system_id_probe.py` | the `0x0456` probe's `store_scaled_quotient_0449` arithmetic, its branch labels, its address guard, and that it has no write path |
| `windows/tools/test_charge_target_test.py` | the charge-target tool's three refusals, the restore in its `finally`, and its CSV column set |
| `linux/lightbar/test_probe_6005.py` | the lightbar probe's ioctl encoding, dry run, and off-after-failure |

Named directories run alone, which is what to reach for when editing one tool:

```sh
bash tools/run-tests.sh windows/tools
```

The exit status is non-zero if any suite failed, and the runner's per-file
output lines each carry what that suite ran. It prints what ran; it does not
assert a count, because an expected count turns every added test into a
failure. A run that finds no suite at all is a failure too, not a silent pass —
the vacuous check is the same defect the gate's listing parse had in
`docs/findings.md` §14b.

## One interpreter per file, and why that is not a preference

The `windows/tools` suites install a fake `ecrw` into `sys.modules` with
`setdefault`, and the fakes are not all the same shape: two export `Ec` only
(`test_manual_fan_ctrl_probe.py`, `test_ec_validate.py`), three export `Ec` and
`EcError` (`test_ec_watch.py`, `test_system_id_probe.py`,
`test_charge_target_test.py`), and `ec_watch.py` imports both. In one shared
interpreter, whichever suite imports first wins, and a tool that imports a name
the winner lacks dies with `ImportError: cannot import name 'EcError' from
'ecrw'`. A combined discovery survives only by sort-order accident, which
nothing asserts. `docs/findings.md` §16 has the reproduction. The runner's
per-file isolation is what keeps a rename from turning that accident into a red
build; the fix that would retire the question entirely is to reconcile the
fakes into one shared module, which is a follow-up rather than part of this.

## What it does not run

- **No gate, no workflow.** CI runs `.github/scripts/agent-gates.sh`, which is
  copied from [`ElDavoo/agent-pipeline`](../docs/agent-pipeline.md) and cannot
  be edited here. `docs/agent-pipeline.md` carries the one-line call for a human
  or an upstream change; until then these suites are not per-commit coverage.
  The runner prints that on every run, the way the cheap tier prints its own
  deferral.
- **No hardware, and no evidence of any.** Every suite is offline by
  construction: device discovery, file opening and ioctls are mocked against
  hand-built fixtures, and the three `windows/tools` suites fake `ecrw` — and,
  for the charge-target tool, the `powershell` call behind its WMI line —
  precisely so no Windows box is needed. No EC is opened, no register is read
  back, and no HID node is touched. `linux/lightbar/README.md` and each suite's
  own docstring say the same thing where the tool is described.
- **Not the decompiler tooling.** Those tools' `--check` and `--self-test` runs
  are the gate's, and they are a different set of files; see
  `docs/agent-pipeline.md`.
