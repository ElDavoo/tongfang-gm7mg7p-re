# One fake for `ecrw`, one way to install it, and one interpreter that proves it

`docs/findings.md` §16 ("Offline suite runner") carries the history. Read that
for the reproduction; this is what closed the follow-up it named, and what the
claim now rests on instead of a warning in a script comment.

## What was wrong

`ecrw.py` binds kernel32 at import time, so it cannot be imported off Windows.
Every offline suite that exercises a tool importing it has to put a stand-in
module in `sys.modules` under the name `ecrw` before importing the tool — and
those stand-ins were written per suite, into three different shapes, and put
there with `sys.modules.setdefault`. Under one shared interpreter `setdefault`
is a race whose winner is decided by which module is imported first, and a tool
that binds a name the winner does not export dies on
`ImportError: cannot import name 'EcError' from 'ecrw'`.

Issue #186 reconciled the two suites that existed at the time into
`windows/tools/ecrw_fake.py`, installed by assignment. Three suites merged in
parallel with it — `test_ec_validate.py` (`Ec` only), `test_system_id_probe.py`
and `test_charge_target_test.py` (`Ec` plus a suite-local `EcError`) — kept the
`setdefault` shape, so the hazard was retired for two suites and left in place
for three.

**The failure the three actually produced was not the `ImportError`.** Measured
on this tree before the change: `python3 -m unittest discover -s windows/tools`
reported four `test_gpu_block_watch` failures *and* one error,
`test_charge_target_test.ChargeTargetTests.test_an_ec_error_partway_still_restores_the_target`,
with `test_charge_target_test.FakeEcError: WMI query failed` escaping `main()`.
`charge_target_test.py:59` binds `EcError` at import; by the time that suite ran,
`test_battery_trace.py` — which sorts ahead of it — had already installed the
shared fake by assignment (`ecrw_fake.install()`, which is the
`sys.modules['ecrw'] =` at `windows/tools/ecrw_fake.py:101`). No `setdefault` won
the name: that suite's own `setdefault` was the no-op, so the class the tool
bound was `ecrw_fake.EcError` and the one that went on to escape was the
suite-local `test_charge_target_test.FakeEcError`. The per-file runner never
showed this, because one file per process meant the tool always bound the
exception class from its own suite. The existing restore-on-injected-failure
case was already the thing that noticed: it is the one that raises.

So the divergence had two faces — a missing name, which dies at import, and a
*different* class object for a name that exists, which fails later and only
under sharing. Only the second was live here.

## What changed

Three suites, no signature changes and no new installer parameter:

- `windows/tools/test_ec_validate.py` — the `types.ModuleType` + `setdefault`
  block, and the now-dead `import types`, are gone; the local `FakeEc` stays,
  because that is the class patched over the tool's `Ec`.
- `windows/tools/test_system_id_probe.py` — same, plus its `FakeEcError`
  (`:52-53`), which was defined, installed, and never raised or referenced
  anywhere else in the file. Dead, so it went with the block.
- `windows/tools/test_charge_target_test.py` — same, plus the one behavioural
  edit in the change: `FakeWmi(boom_on=1, exc=FakeEcError(...))` becomes
  `ecrw_fake.EcError(...)`. The local `FakeEcError` is deleted. The raise has to
  be the class the tool bound, and `ecrw_fake.EcError` is that class; a second
  class of the same shape is not caught by `except EcError`.
  `test_ctgp_dben_probe.py`'s restore-on-injected-failure case already raises
  the shared one, which is why this was a one-line fix and not a judgement call.

Each keeps `import sys`: the `sys.path.insert(0, ...)` the shared fake needs is
a `sys` use, so the "drop `import sys`" that the shape-change suggests is not
available where a `sys.path` entry replaces the `setdefault`.

There is deliberately **no `install(Ec=...)` parameter**. Every suite that
installs the fake patches its byte-carrying class over the tool after import
(`patch.object(tool, 'Ec', lambda: ec)`), and that is the one way to do it; a
second way is how the three shapes came about.

`windows/tools/ecrw_fake.py` needed no code change — only two sentences that had
gone stale by counting. `Ec`'s said "both suites that exist replace `Ec`
wholesale", and `install()`'s said "Both suites install these same two class
objects"; both were true of two suites and are now true of every suite that
installs the fake, so they are reworded to the property rather than to a
number. Scoped that way rather than to "every suite in the directory" because
the directory also holds two non-installers: `test_census_native_c.py`, whose
subject never imports `ecrw`, and `test_ecrw.py`, which borrows the name to put
the real module in front of a fake `ctypes.WinDLL`. A census restated as
"every suite" is the stale figure again in new words.

## The negative control

The check that reads the sources is satisfied by any file that does not contain
the word, so the original shape is reproduced in a scratch directory and
asserted **red**: one suite `setdefault`-s an `Ec`-only fake, a second imports
`EcError`, and the discovery over the pair must fail with
`ImportError: cannot import name 'EcError'`. If that control ever went green,
the structural check would be asserting nothing and would have to be rewritten
rather than trusted.

## The mirror, and what it cannot show

`docs/findings.md` §16 and #186 both demonstrated order-insensitivity by
renaming a suite so it sorts first. `tools/test_windows_tools_shared_interpreter.py`
does the same as a live case: `windows/tools` is copied into a scratch root, the
three formerly-`setdefault` suites are renamed to sort first and last, and the
two runs are required to report the *same* problems.

The mirror has to preserve the repo-relative depth the suites read, because
most of them resolve the repository by walking up from `__file__` and then open
committed files under `ec/`, `evidence/`, `docs/` and `windows/decompiled/`. It
symlinks **every** other top-level entry in rather than a list of four: a list is
a guess about what the suites touch, and a guess that turns out short fails on a
missing directory, which reads as a broken mirror rather than as the property
under test. Measured with a four-entry list, the mirror produced 38 spurious
errors from `test_battery_trace.py` and `test_census_native_c.py`; with every
entry symlinked in, both orders report the same four `test_gpu_block_watch`
failures the committed tree reports and `Ran 335 tests` either way.

**Two renames are the honest bound of what a scratch copy can demonstrate.**
First and last are the extremes of the sort order and nothing between them is
claimed. A structural argument over the sources is what covers the middle, and it
is why the suite holds both rather than picking one.

## What this does not buy

- **It does not make `ecrw.py` importable.** The fake mirrors the real module's
  surface; it does not replace it, and `windows/tools/ecrw.py` is unchanged and
  stays the only thing that talks to `\\.\ACPIDriver`. `test_ecrw.py` loads the
  real module behind a fake `ctypes.WinDLL` and restores whatever was under the
  name in a `finally` — a borrow, not a third shape.
- **It does not retire the per-file loop**, and the comment at that loop says so
  explicitly. The issue asks that the isolation stop being load-bearing, not that
  it go away, and per-file isolation is still what contains a suite that leaves
  global state behind — a reason with nothing to do with `ecrw`.
- **It is not #353.** Making `ecrw.py` importable off Windows is the root fix and
  stays its own issue. This change does not depend on it, does not touch
  `ecrw.py`, and is still correct if #353 lands first.
  > **Corrected 2026-10-02 (issue #353):** `ecrw.py` binds kernel32 on its
  > first `Ec()` rather than at import, so it imports on a non-Windows
  > runner. `windows/tools/test_import_off_windows.py` holds that, and
  > `docs/findings/offline-import-ecrw.md` is the write-up. The rest of
  > this paragraph stands as it was written.
- **It is not in any gate.** `.github/scripts/agent-gates.sh` is copied from
  `agent-pipeline` and the pipeline token has no `workflow` scope.
  `check_python_syntax` globs the four component `tools/` directories and not
  `tools/*.py`, so `bash tools/run-tests.sh` is the only thing that runs this
  suite — or would catch a syntax error in it.

## What it costs

`tools/test_windows_tools_shared_interpreter.py` is the first suite in the tree
that runs other suites, so it is the first thing that adds a nested runner to
`bash tools/run-tests.sh`. Measured on this tree on 2026-09-30: the suite takes
**33 s** across three subprocess runs (one over `windows/tools`, two over the
mirror), against **10.7 s** for a single discovery of that directory, and a
full `bash tools/run-tests.sh` is **8m24s** — its suite and test totals are on
that run's own last line rather than here, because they are a census every
landing moves. These are observations of one run on one machine, not a figure
anything asserts or a budget anything checks. The cost is bounded rather than
open-ended because the baseline in the "no worse than per-file" case is only
paid when the shared run has something to explain, and because the two mirror
runs dominate — a suite added to `windows/tools` is paid for three times over.

## The "no worse than per-file" reading, and why it is not "green"

`docs/findings.md` §16's done condition reads as "a single-interpreter discovery
now passes". On this tree it does not, and the reason is not this change:
`windows/tools/test_gpu_block_watch.py` currently fails four cases reading
`ec/annotations/registers.yaml` and its own door procedure, **on its own and
identically under both runners** (`Ran 27 tests / FAILED (failures=4)` per file;
the same four under one interpreter). That is data drift in another suite — a
register row the suite's citation table has not caught up with — and nothing
about `ecrw`.

So the suite asserts the property and not the greenness: the shared run must
**fail nothing the per-file loop does not also fail**, with the baseline re-run
from the tree and only for the modules the shared run flagged. That is not a
weakening. It is the exact shape of the defect just fixed — a suite that passes
alone and fails in company — and it is the form the claim should take while any
suite in the directory is independently red. Asserting `rc == 0` would either
make this suite red for someone else's breakage or, once someone made it ignore
failures, teach a check to look away from exactly the thing it is for.

The consequence to carry forward is the same one §16 does: the failure was never
the shared interpreter, it was the *divergent shape*. One interpreter is the
condition that made it visible.

**No hardware, no Windows, no EC.** Every suite here is offline by construction —
device discovery, file opening and ioctls are mocked against hand-built
fixtures. Nothing in this change is evidence about the machine.
