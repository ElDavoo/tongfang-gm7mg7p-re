# The `--export-ownership` refusal contract

**Issue #604, 2026-09-25.** `ec/tools/test_xdata_register_map.py` holds the two
refusals `--export-ownership` carries, so that neither can be moved, deleted or
reordered without a suite going red. This page is what that suite asserts, how
it was shown to actually fail when the guards are broken, and what it does not
cover. Its predecessor for the other flag is
[`xdata-no-eq-guard-refusal-contract.md`](xdata-no-eq-guard-refusal-contract.md);
the tripwire design is the same one and is argued there rather than restated
here, and this page names the symbols it holds rather than line numbers, for
the reason that page records about its own §6a recipe.

Nothing here is an EC finding. No register's `status:` changed, no register was
read back, no hardware or Windows machine was involved, and the two committed
census CSVs are byte-identical before and after this work. The census figures
quoted below are `xdata-export-ownership.md` §4-§5's, re-derivable by the two
commands that section prints, and re-measured on the tree this work lands on —
which is not the same pair any more; *Counts on this tree* at the foot says by
how much and why. The counts of suites, tests and CSV rows are this
repository's own, and they move whenever a commit adds one.

## What the flag claims, and where each claim is now held

`--export-ownership` re-runs the census reading each routine once, from the
export that owns it, so a routine the exporter cut 42 ways stops being counted 42
times. It carries three claims.

| | claim | held by |
|---|---|---|
| 1 | it reads each routine once, from its owning export, and drops nothing | the tool's own `--self-test`, against the `OWNERSHIP` oracle at `xdata_register_map.py:1006-1027`, and `ec/annotations/xdata-export-ownership.md` §4's measurement |
| 2 | it is refused with `--check` and with `--self-test` | `Refusals.test_it_is_refused_with_check`, `..._with_self_test` |
| 3 | it is refused unless given scratch `--out-registers` **and** `--out-clusters` | `Refusals.test_it_is_refused_bare_with_the_default_outputs`, `..._with_scratch_registers_only`, `..._with_scratch_clusters_only` |

Claims 2 and 3 were held by nothing before this work, and the gap was one flag
short by accident rather than by design: the tripwire that holds the other
flag's pair mocks all nine of `main()`'s mode entry points and does not read the
flag argument at all, so it covers a second flag for free.

**The hazard is the same one, and the consequence is the same file.** A bare
`--export-ownership` run writes the de-duplicated census over
`annotations/xdata-registers.csv` and `annotations/xdata-clusters.csv`, which is
what `check_cluster_citations.py` reads and what every `main-ec-NNN` citation in
the tree names. The damage lands in a different *shape* than the sibling flag's
— the sibling writes the pre-#178 census, this one writes a re-keyed census
whose `cluster_key` moves on 35 of the 430 clusters and breaks 5 of the 10 hand
names — but it lands in the same two files, and a `cluster_key` citation is
keyed to a membership, so a silent renumbering is not a cheap diff.

**The two flags' messages are byte-identical apart from the flag name.** Both
pairs read `"... cannot be combined with --check or --self-test ..."` and
`"... would overwrite the committed census ..."`, and `main()`'s own comment at
`:3687` says why: "The same two refusals, for the same two reasons." The suite
holds that as two shared module constants, `REFUSED_WITH_A_MODE` and
`REFUSED_AT_THE_DEFAULTS`, that both flags' cases assert against. A guard
rewritten to stop carrying one of them goes red rather than quietly becoming a
third spelling of a refusal the page has stopped describing.

## The two flags are one table, not one class per flag

`GUARDED_FLAGS` pairs each flag with nothing but its name, and the five
`Refusals` cases loop over it with a `self.subTest(flag=flag)`. A duplicated
class would have been the same five cases twice, and the second copy is the one
that stops being updated when a guard is rewritten — the whole failure the
`subTest` names are there to prevent. A failure now reads
`(flag='--export-ownership')` on the line, and the tripwire's own message
carries the whole argv besides.

**Each case gives the *other* guard nothing to fire on, for both flags.** The
`--check` and `--self-test` cases pass both scratch outputs, because at the
default outputs the `--export-ownership` scratch guard fires too: the case
would pass on either guard, and a `--check` guard moved below the dispatch would
go unnoticed behind whichever survived. The sibling write-up records the same
reason for `--no-eq-guard`, and the measurement below shows it holding here as
well — the `test_it_is_refused_with_check` failure under a moved guard A names
`['check']` and not `['write']`.

**The two half-scratch cases are here because the second guard is an `or`.** A
refactor that required *both* outputs to be scratch would still refuse every run
it refuses today, so the one-sided version would keep the suite green with the
half-scratch property gone. The existing suite splits the category into two
cases for that reason; both flags inherit the split.

## The tripwires are the design, and they were already flag-agnostic

Every refusal case replaces all nine of `main()`'s mode entry points with
recorders, then asserts three things: no mode ran, the exit was non-zero, and
both committed CSVs are byte-identical. `Refusals.refuse` is unchanged for this
work — it never read the flag — and neither is `MODES` or `TripwireCoverage`.
The list is still nine long and is still read out of `main()`'s own AST, so a
tenth mode fails there. The suite gains no entry-point knowledge of its own;
the new cases go through the same `refuse()`.

> **Corrected 2026-09-25, issue #608 (PR #675 review, round 3).** The sentence
> above over-claims, and it is left standing rather than rewritten, because it
> is the same promise this issue was opened to correct and the same one believed
> for the life of the suite — the two siblings that carried it are corrected in
> place at `xdata-no-eq-guard-refusal-contract.md` and in
> [`xdata-dispatch-tripwire-coverage.md`](xdata-dispatch-tripwire-coverage.md).
> The reader was a `visit_Return`, so it held for a mode dispatched as a
> `return` and for nothing else: a tenth mode reached as
> `demo_mode(args); return 0` recorded nothing, so it was in neither the
> recorded list nor `MODES`, the comparing case stayed green, and the mode ran
> unmocked. The reader now records a bare-name call in statement position as
> well as return position, and the boundary it cannot close — a mode dispatched
> through an attribute — is asserted by `mode_attributes` rather than assumed
> away. The claim is still bounded after that, and "a tenth mode fails there"
> does not survive it: a mode passed as *another call's argument* is recorded
> only as the outer call, and `mode_attributes` is empty, so
> `return check(demo_mode(args))` records `['check']` and reports by neither
> reader — measured on synthetic source. That is the documented edge of the
> positional rule (a call that is only another call's argument is that callee's
> business, not `main()`'s dispatch), not a gap in it: the entry point
> `main()` dispatches to has changed, so `MODES` has to change with it.

What that buys is the property rather than the consequence: the refusal happens
*before* any mode runs, so **a failing run of this suite cannot damage the
repository.** The new accepted run is the deliberate exception and is confined
to its own `tempfile.TemporaryDirectory()`, asserted byte-identical afterwards.

## Shown to fail, not merely shown to pass

A green suite proves nothing on its own, so each guard was broken in a scratch
copy of `ec/` — a copied `annotations/` with `decompiled/`, `firmware/`,
`ghidra/` and `datasheets/` symlinked back — and the suite re-run from the
mirror's own `ec/tools/`, which it finds from `__file__` and so does not have to
be told. Every mutation was reverted immediately, the working tree's
`xdata_register_map.py` was diffed back against the mirror's, and the mirror's
census CSVs were compared after each one. The five rows below are what that run
says **on the tree this work lands on**, with the suite at 20 tests. Every
failure is attributed to `--export-ownership` and only to it: the `--no-eq-guard`
half of each case stays green throughout, because the sibling's guards are not
what was broken.

| mutation | what the suite said | census CSVs after |
|---|---|---|
| guard B (`xdata_register_map.py:3703-3704`) moved past `return write(args)` | 3 failures, each `Lists differ: ['write'] != []` — the bare case and both half-scratch cases | byte-identical |
| guard B deleted outright | the same 3 failures, `['write']` each | byte-identical |
| guard B moved between the `if args.*` chain and the fallthrough | **20 tests, green** | byte-identical |
| guard A (`:3698`) moved past `return write(args)` | 2 failures: `Lists differ: ['check'] != []` and `Lists differ: ['self_test'] != []` | byte-identical |
| guard A deleted outright | the same 2 failures | byte-identical |

**"Below the dispatch" has to mean past the fallthrough, and row three is why
that is worth measuring rather than asserting.** A guard parked between the
`if args.*` chain and the trailing `return write(args)` is still, in every sense
the property cares about, *above* the dispatch: a bare `--export-ownership` run
is refused, no mode runs, and nothing is written. The suite is green on that
relocation, and it is right to be — the hazard does not exist there. Move the
same guard one line further down, past `return write(args)`, and the write has
already happened before the refusal is reached. That is the placement rows one
and four use, and it is the only one that damages anything.

The sibling page records the identical result for `--no-eq-guard`, on a
different tree. It is recorded here again because a summary's word is not a
measurement, and because the two flags share the property rather than the
observation: this row is what makes rows one and four mean what they say.

## The direction reverses, and that is why the sibling's assertion is not reused

`AcceptedWrite.test_the_guard_only_moves_references_into_write` asserts
`assertGreater`: the `==` guard *rejects* occurrences, so turning it off can only
add writes. `--export-ownership` is the other way round from that — it turns a
pass *on* and reads one routine once instead of 42 times, so it can only
*remove* references. The new
`AcceptedExportOwnershipWrite.test_the_pass_only_removes_references` asserts
`assertLess` on the same shape of relation, over `refs` rather than `write`.

Reusing the sibling's assertion verbatim would have asserted the wrong sign and
gone red against a correct run, which is the trade a copied test makes when the
claim under it is not the same claim. The case is named for the direction so the
sign is visible in a failure line, and its comment says why the sibling's is not
a template for it.

Measured on this tree, and re-derivable by the two commands
`xdata-export-ownership.md` §5 prints:

| | committed | `--export-ownership` |
|---|---:|---:|
| total `refs` | 14,822 | **9,404** |
| `read` | 8,344 | 4,923 |
| `write` | 3,195 | 2,707 |
| `read+write` | 2,482 | 1,018 |
| `passed-to-call` | 534 | 500 |
| `address-taken` | 267 | 256 |
| distinct addresses | 1,171 | 1,171 |
| clusters | 430 | 432 |

Every column moves down, which is the relation, and is §4's table re-measured
rather than a figure this suite pins.

### The two two-sided relations, and why they are not counts

`cluster_key` is the citation key, so a pass that renumbered the census without
a single committed key surviving would be a claim this suite could not
distinguish from a wholesale re-key, and a pass where every key survived would
be indistinguishable from a flag that did nothing. So
`test_cluster_keys_are_renumbered_rather_than_rekeyed` asserts **both** halves:
35 of the 430 committed keys are gone from the scratch clusters, and 395 of them
survive (37 new keys appear). The same two-sidedness over the hand names is
`test_some_hand_cluster_names_break_and_some_survive`: 5 of the 10 keys in
`xdata-cluster-names.csv` break and 5 survive.

**Neither count is pinned here, and the specific breakage is named rather than
asserted.** `xdata-export-ownership.md` §5 records that `counter-sweep`
(`k733222e83898`) is `main-ec-002`'s own key and "does not survive as a single
cluster at all" — and it does not, on this tree. But which of the ten break is a
*membership* claim about a detector that is explicitly a text heuristic (§3's
"Containment" choice, and §6's "a fold is not proof of identity"), so pinning it
would make this suite red for an unrelated re-derivation. That is the same trade
`test_the_scratch_census_is_not_a_copy_of_the_committed_one` makes against
`xdata-06c2-06db-timers.md` §6a's figures, and it is a calibration decision
rather than a coverage gap: the relation is what the pass claims, the membership
is a page's measurement.

`test_no_address_is_lost` is the one thing the pass must never do, and it is
`OWNERSHIP["lost"] == ()` restated as a relation between the two CSVs rather
than as a figure. It cannot be read back from `--self-test` for the same reason
the flag is refused with `--self-test` in the first place: the check and the
flag cannot be combined. That is worth stating rather than leaving as an
apparent gap, because §4's correction records a grouping that *did* lose
`0x05E0` — the plan stage's estimate, whose detector folded `bank1/8E91.c` into a
larger body — and losing an address would fail here.

## Calibration

- **Nothing is asserted as a count.** The sign of the `refs` relation, the
  presence of *both* a surviving and a broken `cluster_key`, the presence of
  both a surviving and a broken hand name, and the equality of the two address
  sets are all relations. 9,404 and 35-of-430 are §4-§5's figures on committed
  pages, and re-pinning them here would make a refusal-contract suite red for an
  unrelated re-derivation.
- **The exit code is pinned as zero or non-zero, never as a literal.** The
  refusals are pinned as non-zero and the accepted runs as zero; neither is
  pinned as `2` or `0` by spelling. `ap.error` raises `SystemExit(2)` today, and
  rewriting a refusal as `print(...); return 1` would still be a refusal.
- **The refusals are asserted to be a CLI contract, never anything about the
  EC.** The suite reads the same committed text files the tool reads. A `refs`
  count in decompiled text is evidence about static shape and never about what
  the EC does with a byte; a zero is "not found by this method", never "absent"
  (`docs/findings.md` §4c).
- **The accepted run has no tripwires, and that is a decision, not an
  oversight.** It is the case that has to really write, or the "wrote only into
  the tempdir" half would be vacuous. The safety comes from the ordering — the
  paths are the tempdir's, and the byte-identical case runs in the same class
  whatever order the runner collects it in — and from
  `test_the_committed_census_is_byte_identical_afterwards`, which is what makes
  the not-a-copy case a second opinion rather than a comparison of a file with
  itself.

## What this suite does not cover

- **Not a gate arm.** `.github/scripts/agent-gates.sh` compiles
  `ec/tools/*.py` and does not run this file. `tools/run-tests.sh` picks it up
  with no wiring edit, because it discovers by `find`. Wiring the runner into
  the gate is a `.github/` change the pipeline token has no `workflow` scope
  for, and it is **#512** in any case.
- **A third flag.** `main()` guards two flags and the suite covers two.
  `TripwireCoverage` reads the mode dispatch out of `main()`'s AST and says
  nothing about the guards, so a third flag added *without* its refusals would
  be a gap this suite could not see — which is the argument for the same
  instrumentation being added with the flag next time, not for a third flag
  being invented here.
- **`--check --self-test --export-ownership` together.** Refused, but by
  argparse's mutually-exclusive group. That is testing argparse, and its exit
  code is indistinguishable from a guard firing.
- **The committed census CSVs and `xdata-cluster-names.csv`.** Not regenerated,
  not re-keyed, not swept. They are what the refusal contract exists to
  protect, and this change does not move the default that would rewrite them —
  §5's flip is its own PR, after the function boundary.
- **`ec/tools/export_ownership.py` in no gate.** #591 owns that, it is a
  different file with its own refusals and its own committed-tree cases in
  `test_export_ownership.py`, and nothing here touches it.

## Counts on this tree, re-measured

`bash tools/run-tests.sh` is **21 of 23 suites passing** on this tree, and the
two failures are the pre-existing ones the sibling page names:
`test_check_site_census.py` (`D091.c` line-pin drift from #503) and
`test_xdata_cluster_names.py::TheGuardOffRegeneration` (the #528 recipe
regression, 6 cases that do not run). Both reproduce on a pristine `main`; this
work adds neither and absorbs neither.

**Two of the four failures this page first recorded are green on the tree it
now lands on, and that is `main`'s doing, not this work's.** The other two were
`test_check_cluster_citations.py` (main's own §26 prose) and
`test_export_ownership.py`, whose `owner_name` column was `FUN_CODE_7401` on
disk against `ff_filler_not_a_function_7401` derived — the same 17
`ff_filler_not_a_function_*` renames #561's byte scan made. `main` has since
re-exported the tree those two were reading, so both are green here and the
four-failure list this page first carried is a record of what was true when it
was written, not of this tree. The tool's own `--self-test` is green here for
the same reason.

`--check` is **green** on this tree, before and after this work: exit 0, 1,171
register rows and 430 cluster rows matching a fresh generation. The requirement
is *"this changed nothing about the verdict"*, not *"the verdict is green"*, and
it does not make the hazard sharper — `--check` is refused with
`--export-ownership`, so it regenerates the default census and goes red on a
de-duplicated file whether the check was red before or green.

This work takes the suite from 12 tests to 20, because the five refusal cases
loop over two flags as five `subTest` runs apiece rather than becoming ten
cases, and the new class adds eight. The suite count is unaffected by this: it
adds cases to an existing file, and `run-tests.sh` discovers by `find`. The
whole run is **609 tests** on this tree. The count is printed by the runner, so
it is a thing to re-measure rather than to maintain by hand — which is why
`tools/README.md` says the same and re-derives it the same way.

**The census figures moved under this work too, and none of it is this work's.**
The tool's `ORACLE` and `OWNERSHIP` oracles read `refs` 14,822 and 9,404 on this
tree, against the 14,819 and 9,401 quoted in §4-§5's tables: `main`'s #267 gave
`0x1665`, `0x1666` and `0x166A` their `registers.yaml` rows, which re-spells
three references as symbols and adds three more, moving `read` by three on both
sides and nothing else. The two-sided relations this suite asserts are
unmoved by that — 35 of the 430 committed `cluster_key`s still break with 395
surviving and 37 new, and 5 of the 10 hand names still break with 5 surviving —
which is the reason they are relations and not counts. The table under *The
direction reverses* is this tree's, re-measured from the two commands that
section prints; `ec/annotations/xdata-export-ownership.md` still quotes the
pre-#267 pair on its own pages, and correcting that page is #267's follow-up
rather than this work's.

**The deferral above is now discharged (issue #654), and the page it deferred
to carries this tree's figures.** `docs/findings/xdata-export-ownership-page-census.md`
re-derives every figure on `ec/annotations/xdata-export-ownership.md` from a
fresh run of the two commands that page's §5 prints, and the seven stale cells
are corrected: the census pair is 14,822 / 9,404 rather than 14,819 / 9,401,
main-EC `refs` is 13,964 / 8,546, and `read` is 8,344 / 4,923. The two
`main-ec-002` rows and the one column this page's own table omits — the
main-EC row — are derived rather than carried from the oracles, and all three
came out where the page already had them. The table under *The direction
reverses* and that page now agree on every column either of them prints.
