#!/usr/bin/env bash
# LOCAL CHANGE (not in the agent-pipeline template): rebase HEAD onto origin/main, and settle
# the conflicts that are mechanical here: those in generated files, which
# regenerate-conflicted.sh rebuilds from the merged inputs. The fix stage died on exactly
# that (#1371, #1374) and threw its round away. Any other conflicted path is a real conflict
# and fails the step as before.
set -euo pipefail

git fetch --quiet origin main
if git rebase origin/main; then
  exit 0
fi

while :; do
  # From origin/main, not from the tree being rebased: mid-rebase the working tree is an
  # older commit of the branch, which may predate the script.
  if ! bash <(git show origin/main:.github/scripts/regenerate-conflicted.sh); then
    echo "::error::rebase onto main conflicts in files that are not generated (above)"
    git rebase --abort
    exit 1
  fi
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
