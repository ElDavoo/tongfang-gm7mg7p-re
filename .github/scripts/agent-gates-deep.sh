#!/usr/bin/env bash
#
# The expensive half of the gate. See .github/scripts/agent-gates.sh for the
# cheap half and docs/agent-pipeline.md for why there are two, and for the
# schedule this is meant to be on.
#
# What lives here, and why it is not in the cheap tier:
#
#   * the sdas8051 re-encode, an independent assembler encoding the committed
#     listing back to bytes. That is the difference between checking the bytes
#     and checking the claim about them, and it is the strongest check the EC
#     has. It needs sdcc, it is about 90 s, and its result changes only when a
#     listing or the firmware changes -- so paying for it on every commit buys
#     nothing the byte-level --check does not already buy.
#   * the cross-decoder comparison, Ghidra's 8051 C against
#     ec/tools/disasm8051.py. It is advisory by its own docstring and its
#     result cannot fail the run either way; measured here at 0.13 s, so
#     deferring it is a statement about where advisory output belongs, not
#     about seconds.
#
# A superset, not a replacement: the cheap tier runs first, so
#
#     AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh
#
# is the single command that checks everything, which is what a scheduled
# workflow should call. Until a human adds that schedule this is opt-in, and
# the cheap tier says so on every run.

set -uo pipefail

started=$(date +%s)
here=$(cd -- "$(dirname -- "$0")" && pwd)

# The cheap tier, with the deep switch off so this is not a loop. Its closing
# note names the two steps below, which is true and worth reading anyway: it
# says which tier each check lives in, and this script is that other tier.
printf '\n--- cheap tier (agent-gates.sh) ---\n'
AGENT_GATES_DEEP=0 "$here/agent-gates.sh"
cheap_rc=$?

failed=$cheap_rc
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

printf '\n=== sdas8051 re-encode (EC) ===\n'
# Not keyed on whether the tool happens to be on PATH, and not quietly skipped
# when it is not: a deep tier that degrades to the cheap tier on a runner
# without sdcc is a gate that passes without having run.
if ! command -v sdas8051 >/dev/null 2>&1; then
  printf 'FAILED  sdas8051 is not on PATH, so the EC listing was NOT re-encoded\n'
  printf '        by an independent assembler. The deep tier needs it:\n'
  printf '        project-setup installs sdcc, and the nix dev shell has it.\n'
  failed=1
else
  python3 ec/tools/verify_reassembly.py --work "$scratch/reasm" --jobs 4 || failed=1
fi

printf '\n=== cross-decoder agreement (EC, advisory) ===\n'
# The self-test again, with the comparison this run is here for. Its assertions
# have already run above; the repeat is a tenth of a second and is what keeps
# this script honestly a superset rather than a guess at one.
python3 ec/tools/build_ec_decompile.py --work "$scratch" --self-test \
  --cross-decoder || failed=1

if [ "$cheap_rc" -eq 0 ]; then
  cheap_word='passed'
else
  cheap_word='failed'
fi
elapsed=$(( $(date +%s) - started ))
printf '\ndeep tier done in %ds; the cheap tier it re-ran %s.\n' \
  "$elapsed" "$cheap_word"

if [ "$failed" -ne 0 ]; then
  printf 'Deep tier failed.\n'
  exit 1
fi

printf 'Deep tier passed. Nothing is deferred any further.\n'
