# CLAUDE.md

Reverse-engineering repo for a TongFang GM7MG7P / Uniwill GM5MG7Y laptop's
EC, BIOS, and Windows vendor stack. `docs/findings.md` is what's known so
far; the rest of this file is *how to work here*. First, what it's all for.

## The mission

`docs/MISSION.md` is the canonical copy. It's repeated here because every
agent stage reads this file and not always that one, and a stage that
doesn't know the goal optimises for closing its issue instead. If you change
the mission, change it in `docs/MISSION.md`, here, and in `README.md`
together.

**Functional goal.** Unlock everything the BIOS and the EC on this machine
have to offer, and write the Linux interface for it: a kernel driver, either
an addition to upstream `uniwill-laptop` or a new driver where that's the
wrong fit (e.g. `ite_8291_lb` for the lightbar). Where feasible, unlock
hidden/locked BIOS setup menus too.

**Technical goal.** That requires complete reverse engineering of all three
closed-source components in the stack: the Windows userspace driver/service
(`GCUService.exe` and friends), the BIOS/UEFI firmware, and the EC firmware.
For the EC, "complete" means **a C codebase that mirrors the EC firmware
function for function**, decompiled from the image, symbolized from
`registers.yaml`, and cited back to bank and address. The vendor's source
isn't available, so this is its reconstruction. Annotated disassembly is a
step towards it, not a substitute. Ghidra (installed by
`.github/actions/project-setup`) is the starting point; see issue #20 and
`ec/ghidra/README.md`.

**What progress looks like.** No single PR finishes this. Progress is one
more register's real behaviour confirmed, one more Windows class decrypted,
one more BIOS menu entry understood, one more upstream contribution
prepared. The issue tracker is the work queue, and it should not run dry
while the goal is open: every merge is read against the mission by
`agent-followups.yml`, and finishing an issue is expected to reveal zero or
more new ones.

**What this means for any single piece of work.**
- Judge it by whether it moves one of the three components closer to fully
  understood, or a feature closer to a Linux driver, not by whether the
  issue's literal wording was met.
- When a finding opens a new question (a register with a second writer, a
  second firmware image in the dump, a method that won't decompile), say so
  explicitly in the PR. That's what the follow-up pass turns into the next
  issue.
- The end product is upstream code, so evidence has to hold up to an
  upstream maintainer: cited, reproducible from committed inputs, and
  calibrated (next section).

## The rule that matters most: calibrate, don't overclaim

`docs/findings.md` §4 records two conclusions that were confidently wrong:
a charge-cap claim from a resting battery voltage, and a "this register
doesn't exist" claim from a static scan that turned out to have a blind
spot. Both were stated more strongly than the evidence supported, and both
had to be retracted in place rather than quietly fixed.

Apply the same standard to anything you write here:
- A static scan finding zero references means "not found by this method,"
  never "absent" — see `ec/annotations/registers.yaml`'s own caveat on
  this, and don't repeat it as settled fact elsewhere.
- A register write being accepted (readback matches) is not evidence the
  EC acts on it. Only a live behavioural test is.
- If a claim can't be traced to a specific file in `evidence/` or a
  specific decompiled source in `windows/decompiled/`, say what's actually
  known and what would need to be checked, rather than picking the more
  confident-sounding phrasing.
- If you retract something, leave the wrong version visible with a
  correction next to it (see `docs/findings.md` §4a-4d for the pattern),
  don't silently edit history.

## Nothing gets opened in another repository without explicit approval

The mission (`docs/MISSION.md`) eventually means a PR against
`Wer-Wolf/uniwill-laptop` or `tuxedo-drivers`, and issue #10 is tracking
that. Until a human explicitly says to submit it, **no stage opens an
issue or pull request anywhere other than this repository.** The
deliverable for that work is a prepared patch and PR description *in this
repo* (a file under a path like `upstream/`, or a diff attached to the
issue) — never an actual `gh pr create`/`gh issue create` against another
repository's slug, no matter how confident the plan or the CI-green PR is.

This is mechanically backstopped as long as `AGENT_PUSH_TOKEN` stays
scoped to this repository only, the way the setup docs ask for it — a
call against another repo's slug then fails outright rather than needing
the model to decline. Don't treat that as a substitute for the rule above;
a token re-scoped later (an org-wide PAT, a broader grant) would remove
the backstop silently, and the instruction needs to still hold on its own.

## Cloud agents cannot reach the hardware

This pipeline runs on GitHub-hosted runners. There is no physical laptop
and no Windows machine reachable from here — full stop, not a permissions
question.

An issue labelled `needs-hardware-test` is a live run, and the pipeline does
not pick it up at all: plan, implement and the retry sweeps skip it the way
they skip `no-agent`. A human at the machine (or a local session on it) does
that one. Preparing a run is its own issue without the label.

For any other issue whose work turns out to need the hardware or Windows
(often one labelled `windows`):
- The deliverable is preparation, not results: a test script, a documented
  step-by-step procedure, a static disassembly, a decrypted source file.
- Never write a sentence implying a live test ran, a register was read
  back, or hardware behaviour was observed, unless it's cited from a file
  already in `evidence/`. If the issue needs a *new* live observation to
  close it, the plan and the PR both say so explicitly and leave that step
  for a human with the physical machine.
- It's fine, and expected, for such a PR to add a script under
  `ec/tools/`, `linux/battery-trace/`, or similar that a human runs later —
  that's real progress, distinct from claiming the test itself happened.

## Other people's work on sibling boards

`docs/related-projects.md` lists other Uniwill EC reverse-engineering
projects (HydroControl, mech-forza-control, w568w's gists) and what each
found. Check it before re-deriving a register or mechanism, and before
trusting one of theirs: every row says whether it was verified against
*this* EC image. Add to it when you find another.

## Repository conventions

- **New work goes in new files; shared files get a pointer.** Several agent
  PRs are open at once, and every edit to a long shared file
  (`ec/README.md`, `ec/annotations/xdata-register-map.md`)
  is a likely merge conflict with one of them. Write a new investigation up
  in its own file under `docs/findings/` (one per topic or issue) — **and
  that is the whole of it; see the next bullet, which is why there is no
  longer a summary to add anywhere.** Retractions of an
  existing section still go in place, per the calibration rule above. The
  same applies to code: a new tool is a new file, not another mode bolted
  onto an existing one. Structured sources of truth (`registers.yaml`, the
  annotation CSVs) stay single files: edit the rows you need and nothing
  else.
- **No hand-kept totals in prose, and never a correction chain.**
  Adding a suite does not make you restate how many suites there are, and it
  certainly does not make you append a paragraph explaining the new
  arithmetic. `tools/README.md` carried "There are forty-nine today, 1561
  tests in all" for long enough to collect **3,522 lines and 22 supersession
  notes** under it — 40,240 words, every one appended at the same spot by a
  branch that had added a suite, which made it a merge conflict as well as a
  stale sentence, and the note ordinals disagree with each other because
  branches numbered their own without seeing the others'. The total is
  `bash tools/run-tests.sh`'s last line; the file now points at that instead,
  and `tools/test_readme_suite_table.py` fails if a total or a
  `*(Superseded …)*` note reappears in its lead. Per-suite counts *inside a
  table row* are fine and are not what that reads. This has now happened in
  three files, and `ec/tools/check_no_append_logs.py` fails a **heading that is
  a merge** or a supersession note outside `docs/findings/` — the shape, not the
  numerals, because a number in a document nobody can edit is harmless and it is
  the line every change has to touch that costs. The write-up is
  `docs/findings/no-append-logs.md`, and the same mistake killed
  `docs/findings.md`'s section counter, which is the next bullet. **A log is not
  a claim:** §4a-4d keeps a wrong *figure* visible beside its correction, and it
  does not ask you to keep a record of what each merge did — that is
  `git log -p`, and copying one into a live file is how the chain got to 3,522
  lines in the first place. The same lock exists in code and bit #1169 the
  fourth time: **a test that asserts a count of the tree is a value every
  merge has to edit**, and `ec/tools/test_check_pin_table_by_cited_file.py`
  held one that four concurrent branches each bumped from a different base.
  Assert the claim (`twelve suites are cited by line`), not the census
  (`fifty-nine suites exist`) — the second moves on every landing suite.
- **A merge conflict is never committed; it is resolved.**
  `ec/tools/check_no_conflict_markers.py` fails any committed file carrying
  `<<<<<<< ` or `>>>>>>> `, and a `=======` in a file that has one of those.
  The bare `=======` is deliberately not checked alone, because markdown
  spells a setext heading with it. This is not hypothetical: `tools/README.md`
  shipped a three-line block inside a table from `90287fec` (#1089) until
  #1163 removed it, and nothing noticed for the weeks between — not the
  review stage, not the gates, and not the suite-table check, which was
  satisfied throughout by a table row sitting inside the block. **Resolve by
  hand and check what the other side dropped**: the incoming side of that
  block had deleted a row the outgoing side kept, so `git checkout
  --theirs` would have removed a suite's entry and failed a suite nobody was
  watching.
- **`docs/findings.md` is closed, and this is enforced rather than
  advised.** A new finding is a new file under `docs/findings/`, and
  nothing else — no summary section, no pointer appended here.
  `ec/tools/check_findings_frozen.py` fails a change that adds a section,
  deletes one, renumbers one or reuses a number, and
  `gen_findings_index.py --check` fails a stale
  `docs/findings/INDEX.md`; the patch that puts both in the gate is
  `docs/ci/agent-gates-findings-frozen.patch`. The sections below §97 stay
  citable and stay put — the numbering is not what stopped, the *counter*
  is. **Do not "helpfully" add a summary section; that is the one edit to
  this file that a change is not allowed to make**, and the reason is
  mechanical rather than stylistic: it was the file every change had to
  append to, so seven branches in flight collided in the same hunk every
  time, and the resolutions were pages of prose about which section number
  was "the last section in the file" — a claim the next append falsifies,
  which the file made 51 times against a rule it had written down twice.
  Cite a finding by **file and heading**, not by a new `§N`.
- **`ec/annotations/registers.yaml`** is the source of truth for EC
  register status. Its `status:` vocabulary
  (`confirmed-working`, `confirmed-inert`, `present-untested`, `absent`,
  `unknown-not-absent`, ...) is deliberate — use the existing values rather
  than inventing new ones, and update this file whenever a register's
  status actually changes, in the same PR as the evidence for the change.
- **`windows/antitamper/README.md`** explains why most `GCUService.exe`
  method bodies don't decompile (ConfuserEx-style anti-tamper). Don't
  re-report "this method is empty" as a finding — check whether it's a
  known anti-tamper casualty first.
- **`vendor/`** holds vendor binaries as committed inputs, not build
  output. Don't regenerate or "clean up" anything there; if a new vendor
  artifact is needed, add it alongside the existing ones with the same
  version-directory convention (`vendor/control-center-<version>/`,
  `vendor/bios-<version>/`).
- **Blocked issues stay open, not closed.** If a plan finds the work it
  was asked to do depends on another open issue, say so and either scope
  down to whatever doesn't depend on it, or produce no diff and explain
  why in the PR description — don't close the issue as unfulfillable. See
  issue-tracker conventions in `docs/MISSION.md`.

## The Ghidra projects

There is a committed Ghidra project per component — `ec/ghidra/project/`,
`bios/ghidra/project/`, `windows/ghidra/project/` — and decompiled C under
`ec/decompiled/`, `bios/decompiled/` and `windows/decompiled/native/`.
`analyzeHeadless` is on `PATH` in the implement stage (see
`.github/actions/project-setup`).

**The editable surface is a CSV, not the project.** Where a component has
one, a function annotation is a row in
`<component>/annotations/ghidra-functions.csv`: a scope, an address, a
name, a comment, and an `evidence` path that is mandatory and non-empty.
The EC and BIOS have one; the Windows project does not yet. An agent or a
human improves a decompilation by adding that row and re-running the build.
Never hand-edit a `.gpr`, a `.rep`, or a generated `.c`: none of them
review in a diff, and the next export overwrites them.

The one hand-edited decompile is `*.annotated.c`, by long-standing
convention (`bios/README.md`): it is the readable restatement, where
`CpuSetup.OverclockingSupport = 0` replaces the pointer chase the raw
decompile spells out. It is transcribed *into* the annotations CSV, and a
check keeps the two from drifting — so edit the prose by hand and the
machine-readable layer with the CSV, not one instead of the other.

- An annotation row also **seeds a function entry**, which is how a routine
  reached by a branch or a function-pointer table — no `lcall`/`ljmp` names
  it — gets into the project at all. `0xB158` `charge_target_update` is the
  worked example.
- An annotation whose address has no function is reported and **fails** the
  build. That is either a typo or a sign the project needs
  `--mode rebuild-project`; say which, don't let it pass silently.
- `ec/ghidra/xdata-symbols.csv` is **generated** from
  `ec/annotations/registers.yaml` and must never be hand-edited. The
  generator reads `registers.yaml` and never writes it: a symbol rename must
  not be able to imply a `status:` change.
- The default build mode re-exports from the committed project by copying it
  to scratch, so an annotation change does not churn the database — 7 MB for
  the EC, 49 MB for the BIOS. Only `--mode rebuild-project` writes the
  project, and two branches that both rebuild one cannot merge: the
  `.gitattributes` entry makes git refuse rather than text-merge a database.

**Three failure modes to check before believing any decompile claim here.**
Ghidra's native decompiler can fail *silently* — `openProgram()` returns
false with an empty message — which is indistinguishable in the output from
"this function will not decompile". The exporters raise it as a loud
failure; if you see `DECOMPILER UNAVAILABLE`, the toolchain is broken, not
the code. A repeated `-scriptPath` flag *replaces* the first rather than
accumulating, so a second directory silently drops the shared scripts and
the post-scripts come back "not found" — join the directories with `;` in
one flag. And Ghidra cannot usefully decompile **.NET**: it reports success
and emits `halt_baddata()`. `ilspycmd` is the tool for managed code
(`windows/README.md`). `ghidra/README.md` has all three in full.


## Test that will prove it works

There's no build in the traditional sense. "The test" for a change here is
usually one of: `ec/tools/scan_refs.py` (or a new tool) producing the
claimed reference count against `ec/firmware/GMxMGxx_11.800`; a decompiled
`.cs` file actually containing the claimed symbol/constant (`grep` it,
don't take a summary's word for it); or, for anything hardware-bound, the
explicit human-runs-this-later framing above. `.github/scripts/agent-gates.sh`
runs the cheap, mechanical half of this (YAML/Python/link validity); it
cannot check whether a *claim* is calibrated — that's this file's job.

## This pipeline itself

The `.github/workflows/agent-*.yml` files, `.github/actions/agent-stall/`
and `.github/actions/project-setup/`, and `.github/scripts/agent-gates.sh`
are copied from the [`agent-pipeline`](https://github.com/ElDavoo/agent-pipeline)
template (MIT-licensed there; see `docs/agent-pipeline.md`). Its own
`CLAUDE.md` warns that a repository running it should not edit those files
casually — the plan stage's push token has no `workflow` scope and cannot
land such a change anyway, so an issue asking for one gets planned with
that piece explicitly out of scope. Pipeline behaviour changes go through
`ElDavoo/agent-pipeline` upstream, then get re-copied here.

What differs from the template on purpose (details in
`docs/agent-pipeline.md`): the plan prompt's hardware, Windows and upstream
constraints; the review stage's blocking list, which holds PRs to this
file's rules rather than the template's examples; `agent-followups.yml`'s
mission prompt and label set; and `claude.yml`, which isn't from the
template at all. Re-copying a template file means carrying those across.
