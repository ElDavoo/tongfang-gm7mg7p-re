# The automation pipeline

`.github/workflows/agent-*.yml`, `.github/actions/agent-stall/`,
`.github/actions/project-setup/`, `.github/scripts/agent-gates.sh`, and
`.github/ISSUE_TEMPLATE/` are copied from
[`ElDavoo/agent-pipeline`](https://github.com/ElDavoo/agent-pipeline)
(MIT licence — see that repository for the full text; not duplicated here
because a repo-root `LICENSE` file would read as covering everything in
this repo, including the `vendor/` binaries, which this project has no
right to license).

`.github/scripts/agent-gates-deep.sh` is **not** from the template — it is
this repository's own, added when the gate was split into two tiers (see
"What was customised for this repo" below). It is the one file under
`.github/scripts/` that a re-copy of the template would not bring back, so it
is the one to look for first when the upstream half of that change is done.

Read that repository's own `README.md` for how the pipeline works — issue
in, plan, implement, review, fix-loop against CI, squash-merge — and its
`CLAUDE.md` for what must not drift if it's ever re-copied. This document
only covers what's specific to *this* copy.

## What was customised for this repo

- **`.github/actions/project-setup/action.yml`** — installs the tools
  `ec/tools/` and the gates need: Python 3 + PyYAML, `radare2` (EC firmware
  disassembly), `sdcc`/`sdas8051` (round-trip-tested against the EC's 8051
  opcodes, see `ec/README.md`), `innoextract` (Windows installer
  extraction), and Ubuntu's preinstalled `shellcheck`.
- **`.github/scripts/agent-gates.sh`** — the cheap, mechanical checks:
  `ec/annotations/registers.yaml` parses and every entry has the required
  keys; every `ec/tools/*.py` at least imports cleanly and
  `scan_refs.py` reproduces one known reference count against the real
  firmware image (a smoke test, not just a syntax check); every decompiler
  tool's `--check` and `--self-test` pass, which is what stops the committed
  Ghidra exports going stale without a Ghidra run in the gate; every `*.sh`
  passes `shellcheck`; every relative link between this repo's `.md` files
  resolves. It also prints, on every run, the two checks it does **not** run
  and the one command that does — see the tier split below.
- **`.github/scripts/agent-gates.sh` + `agent-gates-deep.sh`, the two tiers**
  (2026-09-23, issue #137) — the gate is split by cost, and the split is
  `AGENT_GATES_DEEP=1` plus one extra script. The cheap tier
  (`agent-gates.sh`, what CI runs) is everything that is sub-second per step
  and every check that opens a `.c` or an `.asm`: measured at **5.9 s** for the
  whole script on a GitHub-hosted runner. The deep tier
  (`.github/scripts/agent-gates-deep.sh`) is a **superset** — it runs the cheap
  tier first, then the `sdas8051` re-encode and the advisory cross-decoder
  comparison — so `AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh` is the
  single command that checks everything, and the cheap tier's closing note
  names that command on every run.
  Two things to carry across if this file is ever re-copied from the template:
  1. **The deep tier needs a schedule, and it does not have one.** Nothing in
     `.github/workflows/` calls it, because the pipeline token has no
     `workflow` scope. Until a human adds one, per-commit CI checks less than
     it did before this split: the EC listing is no longer re-encoded from
     bytes on every run. The intended schedule is a nightly or weekly
     `schedule:` job that runs
     `AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh`; the reason it is
     opt-in rather than dropped is in `docs/findings.md`.
  2. **The cheap tier's checks were strengthened, not moved.** The Windows
     tool gained duplicate-key, strict-CSV, coverage and controlled-vocabulary
     checks; nothing that catches a stale or silently-failed export was
     deferred. The deep tier adds an independent re-derivation, it does not
     substitute for anything.
- **`.github/workflows/agent-plan.yml`**'s `CUSTOMISE` section — added the
  hardware/Windows-access constraint from `CLAUDE.md`, so the plan stage
  scopes issues needing the physical laptop or a Windows box down to
  prep-work-only rather than planning a live test it cannot run.
- **`.github/workflows/agent-review.yml`**'s blocking list — the template
  ships example invariants from another project; this copy blocks on
  `CLAUDE.md`'s rules instead (overclaiming, implied live tests,
  silent retractions, `registers.yaml` conventions, anything opened outside
  this repository, `vendor/` changes). Extended for the decompilation work
  with: a hand-edit to generated decompile output or a committed Ghidra
  project where the change belongs in an annotations CSV (with
  `bios/decompiled/*.annotated.c` named as the hand-restated exception, whose
  machine-readable counterpart is `bios/annotations/ghidra-functions.csv`);
  an annotation row with no `evidence`; a decompile failure read as a
  statement about the firmware when Ghidra's decompiler can fail silently
  instead; and `ec/decompiled/` and `bios/decompiled/` added to the
  citable-evidence list, which `docs/findings.md` already cited.
- **`.github/workflows/agent-followups.yml`** — its prompt reads
  `docs/MISSION.md`, and its label set is this repository's. Added here specifically so the issue queue doesn't dry up
  while `docs/MISSION.md`'s goal is nowhere near done; see its own header
  comment for what it does and why it uses `AGENT_PUSH_TOKEN` rather than
  the default `GITHUB_TOKEN` to open issues.

Apart from the provider override below, everything else under
`.github/workflows/agent-*.yml` is an unmodified copy of the `agent-pipeline`
template. If it fixes a bug in one of those
files, re-copy it rather than patching around it here.

## Model provider (local override, 2026-09-17; re-applied with a new model 2026-09-23)

All eight `claude-code-action` steps use OpenRouter's Anthropic-compatible
endpoint (`https://openrouter.ai/api`), `--model stealth/space-bunny-alpha`,
and `--effort max`. Each step passes `secrets.OPENROUTER_API_KEY` as both the
`anthropic_api_key` input and `ANTHROPIC_AUTH_TOKEN`; the OAuth input is no
longer used. Both callers of the reusable `agent-fix.yml` forward the new
secret, and that workflow requires it.

The Opus/Sonnet/Haiku default-model environment variables and
`CLAUDE_CODE_SUBAGENT_MODEL` also select `stealth/space-bunny-alpha`, so the
review plugin's model aliases do not select other models.
`CLAUDE_CODE_EFFORT_LEVEL` is set to `max` for inherited configuration as well
as the explicit CLI flag, and `CLAUDE_CODE_MAX_CONTEXT_TOKENS` is set to
`950000`. These are requested settings; provider-side reasoning behaviour and
the actual context-window size are not verified by the local YAML checks — if
the endpoint advertises a smaller window than 950000 tokens, the larger value
is what the CLI is told to assume.

The model was `stealth/union-alpha` when this override was first committed on
2026-09-17, and `0bf971c` was reverted in full by `4bec8e4` on 2026-09-18
without replacing it. The 2026-09-23 re-application is the same change with
`stealth/space-bunny-alpha` in place of `stealth/union-alpha` and the context
token setting added.

Why the revert is not repeated: the model is rotated, and `union-alpha`'s
turn was simply over — the revert was routine re-pointing at a current
stealth model, not a diagnosis of a failure. As of 2026-09-23, a check of
OpenRouter's public model list (`GET https://openrouter.ai/api/v1/models`, no
auth needed) finds `stealth/space-bunny-alpha` and no entry containing
"union" among the 456 models returned, which is consistent with a retired
slug rather than a broken one. When the next stealth model is rotated in,
this section is what changes: the `--model` flag, the four
`ANTHROPIC_DEFAULT_*_MODEL` variables, `CLAUDE_CODE_SUBAGENT_MODEL`, and the
`docs/agent-pipeline.md` text here.

The same listing gives `stealth/space-bunny-alpha` a `context_length` of
1000000, so `CLAUDE_CODE_MAX_CONTEXT_TOKENS: 950000` leaves headroom under the
real window rather than exceeding it, and it advertises `reasoning_effort`
among its supported parameters, so `--effort max` maps to something the
endpoint accepts. Pricing is listed as zero for both prompt and completion.
Re-check the listing before assuming any of this still holds: these slugs
turn over, which is the whole reason the revert exists.

All eight steps also pass `--dangerously-skip-permissions`, as explicitly
requested for unattended CI. This bypasses Claude Code permission prompts;
`--allowedTools` is no longer a default-deny boundary. The existing explicit
`--disallowedTools` lists remain, but are not a sandbox or a guarantee that
shell commands cannot perform equivalent operations. Earlier workflow
comments describing the allowlist as the safety boundary predate this
override and no longer describe the effective configuration.

These are human-requested provider and CLI-permission overrides. GitHub
job permissions, approval gates, triggers, prompts and action pins are
unchanged. Preserve the overrides when re-copying the template. The
repository Actions secret `OPENROUTER_API_KEY` is set (added 2026-09-17);
the old `CLAUDE_CODE_OAUTH_TOKEN` is still present but is not a fallback.
No live OpenRouter workflow run was performed for this change to validate
the credentials or the model's availability on the endpoint.

## `claude.yml` — not from agent-pipeline, from `/install-github-app`

Anthropic's own Claude Code CLI has an `/install-github-app` setup command
that, independently of `agent-pipeline`, installs its standard quickstart
templates: an `@claude`-mention assistant (`claude.yml`) and an
automatic PR reviewer (`claude-code-review.yml`, since removed — see
`claude.yml`'s own header comment for why). Both originally used the same
`CLAUDE_CODE_OAUTH_TOKEN` secret that `agent-pipeline` needed, so running
that command was a reasonable way to get the secret set — but as shipped,
neither template knows `agent-pipeline` exists: `claude-code-review.yml`
duplicated `agent-review.yml`'s job outright, and `claude.yml` shared no
concurrency group with anything, so an `@claude` mention on an
agent-authored pull request would have run a second, fully independent
session in parallel with whatever the pipeline was doing on it.

`claude.yml` was kept — a mention-triggered conversation is a real
capability the autonomous pipeline doesn't have — but joined to the shared
`agent-pipeline` concurrency group (on the job, not the workflow), and
since the repository went public it only runs for a mention by the owner,
a member or a collaborator. The reasoning for both is in the comment at the
top of that file; don't restate it here where it can drift out of sync.

## Setup state

Everything the upstream README's setup section asks for is in place, as of
2026-09-15, when the repository went public:

- Both secrets (`CLAUDE_CODE_OAUTH_TOKEN`, `AGENT_PUSH_TOKEN`). The PAT is
  fine-grained, scoped to this repository only, with Contents, Pull
  requests, Issues and Actions write, and no `workflow` scope. Actions
  write is what `gh workflow run` needs; without it every hand-over from
  plan to implement fails with `HTTP 403: Resource not accessible by
  personal access token`.
- The labels, including `agent:queued`.
- The `agent-approval` environment, with the owner as required reviewer.
- A ruleset on `main`: pull request with one approval (stale approvals
  dismissed on push), required checks `gates` and `workflows`, no deletion
  or force-push, repository admins as bypass actors.
- Actions settings: default `GITHUB_TOKEN` read-only (every workflow
  declares its own permissions), Actions allowed to approve pull requests,
  approval required for workflow runs from any outside contributor's
  fork, auto-merge on, merged branches deleted.
- Issue and pull request creation limited to collaborators. The pipeline
  is unaffected: it creates issues and pull requests with
  `AGENT_PUSH_TOKEN`, which is the owner's.

While the repository was private, required environment reviewers and
rulesets were both unavailable on its billing plan, so the approval gate
enforced nothing and PR #21 merged without a completed review. Going
public is what closed both gaps.
