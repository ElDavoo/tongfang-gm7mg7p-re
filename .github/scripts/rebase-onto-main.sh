#!/usr/bin/env bash
# LOCAL CHANGE (not in the agent-pipeline template): rebase HEAD onto origin/main, and settle
# the one conflict that is mechanical here. Every pull request adds a row to
# docs/findings/INDEX.md and bumps its count line, so nearly any rebase across another merge
# conflicts in that generated file. The fix stage died on exactly that (#1371, #1374) and
# threw its round away. The file is generated, so the resolution is to regenerate it; any
# other conflicted path is a real conflict and fails the step as before.
set -euo pipefail

INDEX=docs/findings/INDEX.md

git fetch --quiet origin main
if git rebase origin/main; then
  exit 0
fi

while :; do
  conflicted=$(git diff --name-only --diff-filter=U)
  if [ "$conflicted" != "$INDEX" ]; then
    echo "::error::rebase onto main conflicts in files other than $INDEX:"
    printf '%s\n' "$conflicted"
    git rebase --abort
    exit 1
  fi
  python3 ec/tools/gen_findings_index.py > "$INDEX"
  git add "$INDEX"
  if GIT_EDITOR=true git rebase --continue; then
    break
  fi
  # --continue stops again on a later commit that conflicts, or leaves nothing to continue
  # if the regenerated file made that commit empty.
  if [ ! -d "$(git rev-parse --git-path rebase-merge)" ] && [ ! -d "$(git rev-parse --git-path rebase-apply)" ]; then
    break
  fi
  if [ -z "$(git diff --name-only --diff-filter=U)" ]; then
    # the commit became empty after regeneration; drop it rather than stop
    if git rebase --skip; then
      break
    fi
  fi
done

python3 ec/tools/gen_findings_index.py --check
