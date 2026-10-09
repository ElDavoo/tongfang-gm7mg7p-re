# `--verify-provenance` had ten ways to fail and one committed answer to none of them

**Offline throughout.** No laptop, no Windows box, no EC register, no firmware
image, and no history beyond this checkout. Everything below was measured by
running the tool against committed inputs and against a repository the test
builds itself. Nothing here is a hardware or firmware observation, because there
is none.

## The gap

`ec/tools/verify_reassembly.py`'s `verify_provenance()` has **eight `return 1`
statements and one `return 0`**, reached over ten distinct failure conditions.
The issue filed from #411 enumerates five of the ten by what a reader sees in
the function's output; the rest were found by reading it. Nothing committed
exercised any of them.

What there *was* is one hand-run, recorded in `docs/findings.md` §14f: *"pointed
at the window that wrote the listings (`--base 8c7985e --migration 08b72e2`) it
reports 2,705 changed listings and exits non-zero, and a revision this clone does
not have reproduces the history requirement."* That is a real observation and
the right shape of one. It is also not a check: it does not repeat, it does not
run per commit, and there is nothing in the tree that would go red if any of
those branches changed.

`compare_provenance()` — the comparison inside the mode, with no git in it —
already had known answers in `--self-test`, and its own docstring says why they
matter: *"a comparison that compares nothing, or that dropped one column too
many, looks exactly like a working one on any pair that agrees — and the
committed pair is a pair that agrees."* The gate runs exactly that pair, per
commit. The same argument applies one level up and was not applied there.

## The ten rows, and which case reaches each

| return | case | how it is reached |
|---|---|---|
| `base` does not resolve | an unresolvable `--base` | a name no revision answers |
| `migration` does not resolve | an unresolvable `--migration` | a name no revision answers |
| `--listings-from` (or its `base^` default) does not resolve | an unresolvable `--listings-from` | a name no revision answers |
| `git_lines` returned `None` for the **control** diff | injected | **not reachable from a real fixture** |
| `git_lines` returned `None` for the **listing** diff | injected | **not reachable from a real fixture** |
| the control returned zero files | a `--listings-from` naming the base itself | `base..base` is empty |
| listings moved under the migration | `--migration moved` | a commit editing an `.asm` |
| `ec/ghidra/reassembly.csv` unreadable | `--migration gone`, and `--base listings` | a commit that `git rm`s the report; a base that predates it |
| the two reports differ by more than the column | `--migration recounted` | a commit editing one cell beneath the column |
| `PASS` | the control, first | a migration that changes the column and nothing else |

Two of the eight statements serve two conditions each, and the table prints
them as three rows. The report's `return 1` serves both sides of the pair, so
`--migration gone` and `--base listings` are two cases over one site; the `for
label, rev, sha in (("base", ...), ("migration", ...))` loop's serves an
unresolvable `--base` and an unresolvable `--migration`, the same shape. Each
is still two cases, because the sentence each prints names a different side.

Every one asserts **the exit status and a substring of the printed reason**, so a
guard that fires for the wrong reason is not what passes, and each of the three
unresolvable-revision cases names its own label rather than three copies of one
assertion. The `PASS` case is in the list because failure assertions with no
success assertion are satisfied by a mode that fails at everything — which is
the vacuity this whole issue is about.

Two of the ten conditions are not reachable from a real repository, and
the fixture does not pretend otherwise. A commit that resolves cannot make
`git diff` fail over a fixed pathspec, so those two cases replace
`verify_reassembly._git` for the duration of one call with a shim that returns a
non-zero status. Their assertion text says **INJECTED, not end-to-end**, and a
third case with the same shim answering `0` and no output asserts they are not
one case written twice: an empty answer is `[]` and takes the control-empty
branch, where a command that did not run is `None` and takes its own. That
distinction is the whole of what `git_lines()` exists to keep apart, and it is
why the rest are driven through real git.

## Why the root was parameterised and `git_lines` not injected

The issue offers both. Taking the first — `repo=REPO` threaded through
`_git()` → `git_lines()` → `resolve_revision()` → `verify_provenance()`, surfaced
as `--repo ROOT` — matches the default-parameter shape `add_digest_column()` and
`write_report()` already have in the same file, and it is also useful to a human
auditing a fork or a worktree.

Injecting `git_lines` would have had every case below answered by a hand-written
fake, which is §14f's argument one level further down: a comparison that
compares nothing looks exactly like a working one. Only a real git can tell a
command that did not run from one that ran and said nothing, and that is the
distinction two of these returns are about. The two cases that do inject replace
the *git runner*, not the answers, and say so.

`--repo` is added as an `ap.add_argument` and passed on the existing
`verify_provenance(...)` call. It is deliberately **not** written as
`if args.repo:` in `main()`: `self_test()`'s completeness hold reads `main()`'s
source, matches `^\s*if\s+args\.(\w+)\b` before
`refuses_committed_report(args.emit_csv)`, and asserts set equality with
`NO_RE_ENCODE` — so a new dispatch branch would redden it as a mode that does
not early-return. `--repo` is an argument, not a mode.

## The fixture

`build_provenance_fixture()` builds a throwaway repository in a directory the
caller made under `tempfile`, and returns its commits as shas, each named for
what it *is* so a case reads `at("base", "migration")` rather than a sha a
reader has to look up.

| name | what it writes | why it is there |
|---|---|---|
| `seed` | a file no pathspec in this mode matches | so `--listings-from` has an ancestor that is not the base |
| `listings` | `ec/decompiled/bank0/0040.asm`, `.../0042.asm` | the window that last wrote the listings |
| `base` | `ec/ghidra/reassembly.csv`, no `listing_digest` | the last full `--report` |
| `migration` | the column, plus `ec/decompiled/bank0/0EA2.c` | the migration, and a `.c` re-export beside it |
| `recounted` | one cell under the column | the reports-differ case |
| `moved` | an edit to `0040.asm` | the listings-moved case |
| `gone` | `git rm ec/ghidra/reassembly.csv` | the unreadable report |

Three things in it are traps rather than decoration. Each would leave a case
passing or failing for a reason that has nothing to do with what the case is
about, which is the only kind of wrong this repository's checks cannot be
trusted through:

- **The listings are nested one level.** `LISTING_PATHSPEC` is
  `ec/decompiled/**/*.asm`; an `.asm` written directly in `ec/decompiled/`
  would fire the control branch for a reason that has nothing to do with the
  case under test.
- **The digests are this tool's own.** `listing_digest` is computed by
  `digest_of()` over `parse_listing()`'s read of the two fixture listings, so
  the fixture is the shape a real migration has rather than made-up hex. **No
  digest value and no count is asserted anywhere** — what is asserted is the
  status and the printed reason.
- **Every commit carries its own identity** and `commit.gpgsign=false`, so a
  runner with no global `user.name` and a runner that signs everything both
  work, and no config from this repository leaks in.

**Under `tempfile`, never in the working tree**, for the reason
`test_verify_provenance_clone_depth.py` gives: `run-tests.sh` prunes `.git/`,
`.claude/` and `vendor/` when it counts, and `check_testdata_index.py` and
`census_test_line_pins.py` walk the tree.

### The read-back, and why it is a control rather than a census

The first assertion in the block is that the fixture really is the repository
the cases think it is: `git rev-parse --is-inside-work-tree` answers `true`,
`git rev-list HEAD` returns exactly the shas the builder named, all distinct and
all 40 hex. **No size is asserted** — the set comes from git and from the
builder, and neither is a literal, so adding a commit to the fixture does not
make this a number someone has to edit.

Without it, a builder that quietly stopped making commits would leave a
directory that answers every question, and the control-empty case would then be
reaching its verdict over a repository with no listings in it: the one shape that
cannot tell a working mode from a matching-nothing one. The same discipline
`test_verify_provenance_clone_depth.py` uses by reading
`--is-shallow-repository` back rather than inferring it from the command that
made the clone.

## Each mutation, and what went red

One scratch copy of the tool per mutation, `--self-test` run against each, and
the number of cases that went red counted from its output. This is the value of
the block; a table of pass marks is not.

| mutation | what went red |
|---|---|
| the control-empty guard (`if not control:`) disabled | 2: the wrong-`--listings-from` case, and the `[]`/`None` case beside it |
| the listings-moved guard (`if moved:`) disabled | 1: the listings-moved case |
| the reports-differ guard (`if problems:`) disabled | 1: the reports-differ case |
| `has_digest` validation disabled | 4: empty-col, garbage-col, no-col, base-has-col-remove |
| `git_lines` answering `[]` instead of `None` on a failed command | 4: both INJECTED cases and both unreadable-report cases |
| `repo=repo` dropped from the report's `git show` | 4: the PASS case, its supporting view, the unreadable-migration case, and the reports-differ case |
| `repo=repo` dropped from the control `git diff` | 8, including the PASS and the listing diff's INJECTED case; the control diff's own stays green, because that shim answers on the window string and never reaches the real git |
| `repo=repo` dropped from `resolve_revision()` | every case except the unresolvable `--base` one, which fails before any diff and so reads the same wrong clone |

The `git_lines` row is the one that matters most: it is the change that would
make a failed `git diff` read as "no listing moved", which is the exact
substitution `git_lines()` was written to prevent. The last three rows are what
the root parameterisation is for — before it, none of these regressions was
catchable, because no test could point the mode at a repository other than this
one. That the `git show` row leaves the *base*-side unreadable case green is the
same fact from the other end: with the clone ignored, both sides fail to read,
and a case that expects a failure cannot tell the wrong reason from the right
one.

## What it cost, measured rather than assumed

`--self-test` on this runner, five runs each: **0.073 s before, 0.233 s after**
— about 0.16 s for the whole block, `git init` and seven commits included. It
runs on every commit from `.github/scripts/agent-gates.sh` and from `ci.yml`'s
`gates` job with no wiring change, and `check_python_syntax` covers the new code
for free. The figure is reported here and asserted nowhere.

## Where the block sits, and what it does not touch

It goes immediately after the existing `compare_provenance()` cases and **before**
the `find_assembler()` early return, which is the placement `agent-gates.sh`'s
comment describes: the known answers sit there so they run whether or not
`sdas8051` is installed, and nothing in this block needs an assembler. The
supporting-view assertion inside the `PASS` case — that the window's `.c`
re-export is named and the verdict is unchanged — is part of that same case.

The block does not touch the existing `--emit-csv` refusal cases at
`self_test()`'s `--emit-csv` loop, and shares no line with them; **#415** is
theirs to change. **#408** covers `compare_provenance()`'s own uncovered
branches — same tool, same class of gap, different function — and this block
merges alongside it rather than re-deriving it; the reports-differ case is here
because the outer print-and-return was the uncovered half. **#406**, that the
fixed pair still never measures `a56b3bb..HEAD`, is untouched and is the bigger
live question.

`ec/tools/test_verify_provenance_clone_depth.py` is **not** extended. It holds
the *depth* claim over real clones of this repository at two depths; this holds
the *failure returns*, and a seven-commit fixture cannot stand in for a clone
depth. They are cross-referenced.

## The distinction between absent and empty

A migration can fail to add `listing_digest` in three ways: the column is
entirely absent from the CSV header, the column header is present but every
cell is empty, or the column header is present but every cell contains garbage
data. The first and third are refused explicitly (status 1); the second is
refused because a digest that would close the per-commit half of the gap has to
be present and meaningful, and an empty string is neither. The mode's docstring
says "*detecting a change is not verifying it*", and an empty cell is a cell
that was never written with a digest, so a migration that has the column but
never filled it in says nothing about whether the listing text moved.

The fixture cases test four validation scenarios: `empty-col` and `garbage-col`
both add the column but with invalid cells; `no-col` omits the column from the
header entirely; `base-has-col-remove` has the base carry the column and the
migration remove it. All four fail status 1, and the error message names which
condition was found. The distinction exists in the code path: one branch checks
the header presence (`has_digest` on each side), the other reads the cell
values. A migration that has the header but not the digests is caught by the
second check and printed as "the column is empty or invalid on N row(s)", while a
migration that lacks the header entirely is caught by the first and printed as
"does not have listing_digest". A base that already has the column is caught by
the header check and printed as "the base already has listing_digest".

## What is not claimed

- **That the mode is correct, or that it is red on no tree.** Exit 0 on the
  committed tree is what §14f recorded by hand and what the gate's own
  invocation still prints; nothing here re-derives that claim, and only this
  tree, at these fixture shapes, was run.
- **That `--verify-provenance` has ever passed in CI.**
  `history-checkout-claims.md` and `provenance-clone-depth-behaviour.md` already
  disclaim that reading and this page does not override it: what `ci.yml`'s
  `gates` job asks for is a fact about the workflow, not about a runner.
- **That the `PASS` case says anything about the committed migration.** It says
  the mode reaches its verdict on a seven-commit fixture. The committed pair's
  own answer is the one in the README, and what that answer does not establish
  — the digests attest to the measured text and not to its correctness, and the
  re-encode (`docs/findings.md` §14e) is still the open half — is the mode's own
  closing paragraph, not restated here as if it were more.
- **That the two INJECTED cases are end-to-end.** They are not, they are labelled
  as such in their assertion text and above, and no count of "fully end-to-end
  cases" is kept anywhere.
- **Anything about the machine.** No register, no firmware, no BIOS. This is
  `git` and Python 3 against a directory the test deletes.

## How to re-check this

```console
python3 ec/tools/verify_reassembly.py --self-test
python3 ec/tools/verify_reassembly.py --check
python3 ec/tools/verify_reassembly.py --verify-provenance \
    --base 08b72e2 --migration a56b3bb --listings-from 8c7985e
```

The third is the committed pair the gate runs, and it is what shows the
`repo=REPO` default did not change the real invocation.
