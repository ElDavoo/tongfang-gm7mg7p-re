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

For an issue labelled `needs-hardware-test` or `windows`:
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
