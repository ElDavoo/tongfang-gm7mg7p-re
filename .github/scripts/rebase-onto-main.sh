#!/usr/bin/env bash
# LOCAL CHANGE (not in the agent-pipeline template): bring HEAD up to date with origin/main before
# a push, and settle the conflicts that are mechanical here: those in generated files, which
# regenerate-conflicted.sh rebuilds from the merged inputs. Any other conflicted path is a real
# conflict and fails the step.
#
# It merges, despite the name, which is kept because both stages call it by path. It used to
# rebase, and a rebase replays the branch's commits one by one and drops its merge commits. A
# branch that had ever been brought up to date by a merge (by agent-conflicts.yml, or by a human)
# therefore re-met every conflict that merge had resolved, on the first commit it replayed. The
# step failed and the fix round's work was thrown away. On 2026-10-02 that was most fix rounds on
# the open pull requests: #1608 went three reviews with "no commit at all since the third review"
# and was rejected as not converging, as were #1604, #1631 and #1653, whose fixes were written
# and never pushed. A merge only meets what changed since the last one. The pull request is
# squash-merged, so the branch's history shape costs nothing. The push stays legal for the same
# reason a rebase made it legal: after the merge, the branch's workflow files are main's.
set -euo pipefail

git fetch --quiet origin main
if git merge-base --is-ancestor origin/main HEAD; then
  exit 0
fi
if ! git merge --no-edit --quiet origin/main; then
  # From origin/main, not from the working tree: a branch cut before the helper landed lacks it.
  if ! bash <(git show origin/main:.github/scripts/regenerate-conflicted.sh); then
    echo "::error::merging main conflicts in files that are not generated (above)"
    git merge --abort
    exit 1
  fi
  GIT_EDITOR=true git commit --no-edit --quiet
fi

python3 ec/tools/gen_findings_index.py --check
