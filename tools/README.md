# Repository tools

One thing lives here, and it is the one command that runs this repository's
offline `unittest` suites:

```sh
bash tools/run-tests.sh
```

## What it runs

Every `test_*.py` under the repository, found by `find` — not a hardcoded list,
so a suite in a directory that does not exist yet is picked up by having its
file committed. There are four today, 40 tests in all, and each is a `unittest`
suite standing in for a tool's own behaviour:

| suite | what it stands in for |
|---|---|
| `ec/tools/test_grade_0751_isolation.py` | `ec/tools/grade_0751_isolation.py`, the §4 grader of the `0x0751` capture procedure, against the committed `testdata/` fixtures |
| `windows/tools/test_manual_fan_ctrl_probe.py` | the fan-mode probe's two-arm byte script |
| `windows/tools/test_ec_watch.py` | the mark-CSV sweep and the mark landing between two change rows |
| `linux/lightbar/test_probe_6005.py` | the lightbar probe's ioctl encoding, dry run, and off-after-failure |

`windows/tools/ecrw_fake.py` is a shared fixture rather than a suite — it is
the offline stand-in for the `ecrw` module both `windows/tools` suites import,
and the `test_*.py` pattern above does not pick it up, so it costs no suite
count.

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

Both `windows/tools` suites used to install a fake `ecrw` into `sys.modules`
with `setdefault`, and the two fakes were not the same shape: one exported `Ec`
only, the other exported `Ec` and `EcError`, and `ec_watch.py` imports both. In
one shared interpreter, whichever suite imported first won, and the other died
with `ImportError: cannot import name 'EcError' from 'ecrw'`. It passed only
because discovery sorted the two in a lucky order — an accident nothing
asserted. `docs/findings.md` §16 has the reproduction.

**Issue #186 reconciled the two fakes**, and the landmine is defused: there is
now one `windows/tools/ecrw_fake.py`, carrying `Ec` and `EcError` over the
real module's whole surface, and both suites `install()` it. Each still supplies
its own behaviour on top — a suite that needs bytes still writes its own class.
A single discovery run over `windows/tools` passes all 20 in any filename order
now, in both the shipped order and the two renames §16's reproduction uses.

The per-file loop therefore stays as belt-and-braces rather than as the thing
holding a red build away. That is a decision and not an oversight: the next
suite to reach for a fake of its own gets an interpreter to itself without
anyone having to notice the collision first, and the loop costs a fraction of a
second. Collapsing it into one discovery run is no longer dangerous here, but
it is also no longer a saving worth having.

## What it does not run

- **No gate, no workflow.** CI runs `.github/scripts/agent-gates.sh`, which is
  copied from [`ElDavoo/agent-pipeline`](../docs/agent-pipeline.md) and cannot
  be edited here. `docs/agent-pipeline.md` carries the one-line call for a human
  or an upstream change; until then these suites are not per-commit coverage.
  The runner prints that on every run, the way the cheap tier prints its own
  deferral.
- **No hardware, and no evidence of any.** Every suite is offline by
  construction: device discovery, file opening and ioctls are mocked against
  hand-built fixtures, and the two `windows/tools` suites fake `ecrw` precisely
  so no Windows box is needed. No EC is opened, no register is read back, and
  no HID node is touched. `linux/lightbar/README.md` and each suite's own
  docstring say the same thing where the tool is described.
- **Not the decompiler tooling.** Those tools' `--check` and `--self-test` runs
  are the gate's, and they are a different set of files; see
  `docs/agent-pipeline.md`.
