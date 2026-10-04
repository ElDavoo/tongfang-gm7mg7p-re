# Repository tools

Two things live here: the command that runs this repository's offline
`unittest` suites, and one checker that runs beside them.

```sh
bash tools/run-tests.sh
```

## What it runs

Every `test_*.py` under the repository, found by `find` — not a hardcoded list,
so a suite in a directory that does not exist yet is picked up by having its
file committed. **There is deliberately no total written here.** The runner
prints one: `bash tools/run-tests.sh`, whose last line reads
`N suite(s) run, M tests`, and that line *is* the total, on the tree you ran it
on. A total written in this file is a claim about a tree that stops being true
the moment a suite lands, and appending a paragraph to correct it is what turned
this section into 3,522 lines of supersession notes before 2026-09-27 — twenty-two
of them, appended at this one spot by every branch that added a suite, which is
what made it a conflict site as well as a stale one. They are kept verbatim,
with each figure's own tree named, in
[`tools-readme-totals.md`](../docs/findings/tools-readme-totals.md), which is
also the write-up for [#817](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/817).
`tools/test_readme_suite_table.py` fails if a spelled-out total comes back.

So: **run the runner, and do not edit this sentence.** Adding a suite needs
nothing but the file: the runner finds it by itself, and the suite's module
docstring is where it says what it stands in for. To see them all:

```sh
python3 tools/list_suites.py            # every suite, first line of its docstring
python3 tools/list_suites.py ec/tools   # one directory
python3 tools/list_suites.py --full     # whole docstrings
```

There is no table of suites in this file. One used to be here, with a
hand-written row per suite. Every branch that added a suite edited it, so it
was in about half of main's commits and conflicted whenever two branches' rows
landed next to each other. `git log -p -- tools/README.md` has it as it last
stood. `tools/test_readme_suite_table.py` fails if a suite has no docstring
or if the table comes back.

Committing a `test_*.py` with a module docstring is the whole of what it
takes to be run and described.

`windows/tools/ecrw_fake.py` is a shared fixture rather than a suite — it is
the offline stand-in for the `ecrw` module, and every suite in that directory
exercising a tool that imports `ecrw` installs it with `ecrw_fake.install()`
(the `test_*.py` pattern above does not pick the fixture up, so it costs no
suite count). `windows/tools/test_ecrw.py` is the one exception and installs
nothing: it puts a fake `ctypes.WinDLL` in front of the real `ecrw.py`, because
a suite that only ever exercises the fake
is not testing the file whose arithmetic #147 is about.
[`tools/test_windows_tools_shared_interpreter.py`](test_windows_tools_shared_interpreter.py)
holds that as a property — see the next section.
[`windows/tools/test_ecrw_fake.py`](../windows/tools/test_ecrw_fake.py) holds
the fixture to the real module, which is the other half of the same claim.

Named directories run alone, which is what to reach for when editing one tool:

```sh
bash tools/run-tests.sh windows/tools
```

The exit status is non-zero if any suite failed, and the runner's per-file
output lines each carry what that suite ran. It prints what ran; it does not
assert a count, the per-suite one or the total, because an expected count turns
every added test into a failure. That is the whole reason the two numbers
above are read off a run rather than kept by hand. A run that finds no suite
at all is a failure too, not a silent pass — the vacuous check is the same
defect the gate's listing parse had in `docs/findings.md` §14b.

A suite that runs other suites is the one case the per-file line has more to
say than a count. `unittest` prints a summary per *run*, so such a suite's
transcript carries several and only one of them is its own — which one is a
decision the runner records per suite (`ran_line_for` in `run-tests.sh`) and
names in the output on every run. A suite that prints several and has no
record is refused, with its own clause in the last line rather than the
`FAILED` one: it is a shape defect, not a red suite. Adding an ordinary suite
needs nothing; only a suite that starts running other suites does.
[`tools/test_run_tests_ran_lines.py`](test_run_tests_ran_lines.py) holds that,
and [`docs/findings/run-tests-ran-lines.md`](../docs/findings/run-tests-ran-lines.md)
is the write-up.

## One interpreter per file, and why that is not a preference

The `windows/tools` suites used to install a fake `ecrw` into `sys.modules`
with `setdefault`, and the fakes were not the same shape: some exported `Ec`
only, others `Ec` and `EcError`, and `ec_watch.py` imports both. In one shared
interpreter, whichever suite imported first won, and a tool that imports a name
the winner lacks died with `ImportError: cannot import name 'EcError' from
'ecrw'`. It passed only by sort-order accident, which nothing asserted.
`docs/findings.md` §16 has the reproduction.

**There is now one shape and one way to install it.**
`windows/tools/ecrw_fake.py` carries `Ec`, `EcError` and `block_runs` over every
part of the real module a tool in that directory reaches, and every suite
exercising a tool that imports `ecrw` calls `ecrw_fake.install()` — by
assignment, not `setdefault`. A suite with bytes of its own keeps its own class
and patches it over the tool after import, which is what every suite installing
the fake does. `test_ecrw.py` installs nothing, because it puts a fake
`ctypes.WinDLL` in front of the *real* `ecrw.py` and restores whatever was under
the name in a `finally`; that is a borrow, not a third shape.
**"Every part a tool reaches" is narrower than the whole surface, and on
purpose.** `_ioctl`, `read_dword` and `read_dword_unaligned` are the real
class's own interior, no tool here reaches them, and giving the fixture a dword
body would turn a loud `AttributeError` into a silent four-zero answer on the
MMRD path — the path `test_ecrw.py` guards hardest.
`windows/tools/test_ecrw_fake.py` holds the narrowed claim, by `ast`, and names
the three it omits.

**So the per-file loop is insurance, and
[`tools/test_windows_tools_shared_interpreter.py`](test_windows_tools_shared_interpreter.py)
is what holds it to that.** It runs `unittest discover -s windows/tools` in one
interpreter and requires that no suite fails there that does not also fail in
isolation, and it runs the same directory on a scratch mirror renamed to sort
both ways first and last. Those are the two directions that used to decide the
outcome. The isolation is deliberately kept anyway — per-file is what contains
a suite that leaves global state behind, which has nothing to do with `ecrw`.

## What it does not run

- **No gate, no workflow.** CI runs `.github/scripts/agent-gates.sh`, which is
  copied from [`ElDavoo/agent-pipeline`](../docs/agent-pipeline.md) and cannot
  be edited here. `docs/agent-pipeline.md` carries the one-line call for a human
  or an upstream change; until then these suites are not per-commit coverage.
  The runner prints that on every run, the way the cheap tier prints its own
  deferral.
- **No hardware, and no evidence of any.** Every suite is offline by
  construction: device discovery, file opening and ioctls are mocked against
  hand-built fixtures, and the `windows/tools` suites fake `ecrw` — and,
  for the charge-target tool, the `powershell` call behind its WMI line —
  precisely so no Windows box is needed. No EC is opened, no register is read
  back, and no HID node is touched. `linux/lightbar/README.md` and each suite's
  own docstring say the same thing where the tool is described.
- **Not the decompiler tooling.** Those tools' `--check` and `--self-test` runs
  are the gate's, and they are a different set of files; see
  `docs/agent-pipeline.md`.
- **The checker is not in the gate either.**
  `check_doc_patch_refs.py` is a `--check`/`--self-test` tool of their shape and
  it is **not** wired into `.github/scripts/agent-gates.sh`, for the same
  template-copied-file reason: `docs/agent-pipeline.md` item 13 carries the
  recipe, and no `docs/ci/agent-gates-*.patch` was added, for the reason
  [`findings/prose-line-citations-held.md`](../docs/findings/prose-line-citations-held.md)
  set out for `run-tests.sh`. Its **suite** needs no wiring to be run at all —
  `tools/run-tests.sh` finds it, which is the whole of what a suite takes. What
  the gate would add is per-commit coverage of the prose, and nothing here
  claims it until a human lands the patch.

