#!/usr/bin/env bash
# LOCAL CHANGE (not in the agent-pipeline template): settle a merge or rebase conflict in files
# that are generated from other committed files, by regenerating them from the merged inputs.
# Hand-merging a generated file is never right: both sides are stale against the merged tree.
#
# Usage: regenerate-conflicted.sh            (acts on `git diff --diff-filter=U`)
# Exits 0 when every conflicted path was a generated one and has been regenerated and staged;
# exits 1, naming them, when any conflicted path is not, so the caller can stop.
#
# The list is the files `--check` gates hold to a generator. A path belongs here only when
# its generator reads committed inputs alone (no Ghidra, no network) and writes the file.
set -euo pipefail

declare -A REGEN=(
  [docs/findings/INDEX.md]='python3 ec/tools/gen_findings_index.py > docs/findings/INDEX.md'
  [ec/annotations/xdata-registers.csv]='python3 ec/tools/xdata_register_map.py'
  [ec/annotations/xdata-clusters.csv]='python3 ec/tools/xdata_register_map.py'
  [ec/ghidra/xdata-symbols.csv]='python3 ec/tools/gen_xdata_symbols.py'
)

mapfile -t conflicted < <(git diff --name-only --diff-filter=U)
[ "${#conflicted[@]}" -eq 0 ] && exit 0

other=()
for path in "${conflicted[@]}"; do
  [ -n "${REGEN[$path]:-}" ] || other+=("$path")
done
if [ "${#other[@]}" -gt 0 ]; then
  echo "conflicts in files that are not generated:" >&2
  printf '  %s\n' "${other[@]}" >&2
  exit 1
fi

# Inputs before outputs: the symbol table is read by nothing here, the census reads
# registers.yaml, and the index reads only docs/findings/. One run per distinct command.
declare -A ran=()
for path in "${conflicted[@]}"; do
  cmd=${REGEN[$path]}
  if [ -z "${ran[$cmd]:-}" ]; then
    echo "regenerating with: $cmd"
    git checkout --theirs -- "$path" 2>/dev/null || true
    bash -c "$cmd" >/dev/null
    ran[$cmd]=1
  fi
done
# Stage every file a generator that ran owns, not only the conflicted one: the census writes
# both CSVs, and leaving the unconflicted half unstaged would commit a pair that disagrees.
for path in "${!REGEN[@]}"; do
  if [ -n "${ran[${REGEN[$path]}]:-}" ] && [ -e "$path" ]; then
    git add -- "$path"
  fi
done
