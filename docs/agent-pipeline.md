# The automation pipeline

`.github/workflows/agent-*.yml`, `.github/actions/agent-stall/`,
`.github/actions/project-setup/`, `.github/scripts/agent-gates.sh`, and
`.github/ISSUE_TEMPLATE/` are copied from
[`ElDavoo/agent-pipeline`](https://github.com/ElDavoo/agent-pipeline)
(MIT licence — see that repository for the full text; not duplicated here
because a repo-root `LICENSE` file would read as covering everything in
this repo, including the `vendor/` binaries, which this project has no
right to license).

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
  firmware image (a smoke test, not just a syntax check); every `*.sh`
  passes `shellcheck`; every relative link between this repo's `.md` files
  resolves.
- **`.github/workflows/agent-plan.yml`**'s `CUSTOMISE` section — added the
  hardware/Windows-access constraint from `CLAUDE.md`, so the plan stage
  scopes issues needing the physical laptop or a Windows box down to
  prep-work-only rather than planning a live test it cannot run.
- **`.github/workflows/agent-review.yml`**'s blocking list — the template
  ships example invariants from another project; this copy blocks on
  `CLAUDE.md`'s rules instead (overclaiming, implied live tests,
  silent retractions, `registers.yaml` conventions, anything opened outside
  this repository, `vendor/` changes).
- **`.github/workflows/agent-followups.yml`** — its prompt reads
  `docs/MISSION.md`, and its label set is this repository's. Added here specifically so the issue queue doesn't dry up
  while `docs/MISSION.md`'s goal is nowhere near done; see its own header
  comment for what it does and why it uses `AGENT_PUSH_TOKEN` rather than
  the default `GITHUB_TOKEN` to open issues.

Everything else under `.github/workflows/agent-*.yml` is an unmodified
copy of the `agent-pipeline` template. If it fixes a bug in one of those
files, re-copy it rather than patching around it here.

## `claude.yml` — not from agent-pipeline, from `/install-github-app`

Anthropic's own Claude Code CLI has an `/install-github-app` setup command
that, independently of `agent-pipeline`, installs its standard quickstart
templates: an `@claude`-mention assistant (`claude.yml`) and an
automatic PR reviewer (`claude-code-review.yml`, since removed — see
`claude.yml`'s own header comment for why). Both use the same
`CLAUDE_CODE_OAUTH_TOKEN` secret `agent-pipeline` needs anyway, so running
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
