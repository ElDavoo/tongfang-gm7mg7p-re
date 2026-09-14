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
- **`.github/workflows/agent-followups.yml`** — not part of the upstream
  template. Added here specifically so the issue queue doesn't dry up
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
`agent-pipeline` concurrency group, and it doesn't check who wrote the
mention the way `agent-plan.yml`'s triage job checks who filed an issue.
Both points, and exactly what would need to change if either stops being
true, are in the comment at the top of that file now; don't restate them
here where they can drift out of sync with it.

## Setup steps still needed

Done from this session, against the GitHub API: the six labels, the
`agent-approval` environment (created, but see below), and the Actions
setting that lets `github-actions[bot]` approve pull requests
(`can_approve_pull_request_reviews`).

**Two setup steps are blocked by this account's billing plan, not by
anything this session could configure differently:**

- **Required reviewers on the `agent-approval` environment** — the API
  call to attach the protection rule failed: *"Please ensure the billing
  plan supports the required reviewers protection rule."* This is a known
  GitHub limitation: environment protection rules on a **private** repo
  need GitHub Team or Enterprise; they're free on a **public** repo at any
  plan. The environment exists but currently holds no reviewers and blocks
  nothing — every issue would sail through the gate the pipeline's README
  describes as its main defence against untrusted content.
- **The branch ruleset on `main`** — the API call failed with *"Upgrade to
  GitHub Pro or make this repository public to enable this feature."*
  Rulesets on a private repo need at least GitHub Pro. Without it, nothing
  stops a direct push to `main` bypassing review, and there's no
  server-side requirement that CI (`gates`, `workflows`) pass before merge.

**Why this is a live gap rather than latent**: `docs/MISSION.md`'s
"backlog should not run dry" premise means this repo runs on
`AGENT_PUSH_TOKEN` for both the plan stage's trust check and the
follow-ups workflow's issue creation, and the whole design leans on the
approval gate as the backstop for anything unattended. Right now that
backstop is unenforced.

Practical read for a single-owner private repo today: since nobody but
the owner can file an issue here at all, the trust check would resolve to
"trusted" regardless, so the missing gate doesn't currently let anything
through it wouldn't have let through anyway. That stops being true the
moment this repo gains a collaborator or goes public — do one of the
following *before* either happens:

- Upgrade to GitHub Pro (~$4/month at the time of writing) — unlocks both
  the ruleset and, since Pro repos can still be private, the environment
  protection rule stays gated on Team/Enterprise unless the repo goes
  public too. Check GitHub's current docs for which plan actually unlocks
  environment reviewers on a private repo before assuming Pro alone is
  enough.
- Or make the repository public — unlocks both features on any plan, at
  the cost the private-repo choice was made to avoid (see the top-level
  `README.md`'s note on `vendor/`).
- Or accept the gap deliberately while the repo stays private and
  single-owner, and revisit before either condition changes.

Two more setup steps need a human with credentials this session doesn't
have and shouldn't ask for in chat:

1. **`CLAUDE_CODE_OAUTH_TOKEN`** — run `claude setup-token` locally (it's
   an interactive OAuth flow) and add the result as a repository secret:
   `gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo ElDavoo/tongfang-gm7mg7p-re`.
2. **`AGENT_PUSH_TOKEN`** — create a fine-grained PAT at
   <https://github.com/settings/personal-access-tokens/new>, scoped to
   this repository only, with **Contents: write**, **Pull requests:
   write**, **Issues: write**, **Actions: write**, and explicitly
   *without* `workflow` scope (see the upstream README's "Who is trusted"
   section for why). Then:
   `gh secret set AGENT_PUSH_TOKEN --repo ElDavoo/tongfang-gm7mg7p-re`.

Until both secrets are set, every stage will run and stall (`agent:stalled`,
then `agent:stuck` after three retries) rather than silently doing nothing —
worth knowing so the first few issues filed don't look like they vanished.
