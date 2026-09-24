#!/usr/bin/env bash
#
# The checks an agent must pass before its work is worth pushing. See
# docs/agent-pipeline.md for why these specific checks and not others —
# short version: these are the fast, mechanical half of correctness here;
# CLAUDE.md's "calibrate, don't overclaim" rule is the half no script can
# check, and is read separately by every stage.
#
# Two tiers. This is the cheap one: no gate here turns on whether sdas8051 is
# installed, and nothing re-derives coverage from the decompiled C. What that
# leaves out lives in agent-gates-deep.sh, and AGENT_GATES_DEEP=1 runs the whole
# thing — the deep script calls this one first, so that one command checks
# everything and a scheduled workflow has something single to call.
#
# The split is printed, every run, whatever it did. A deferral nobody can see
# is a check that gets dropped, which is the failure this arrangement was made
# to avoid.

set -uo pipefail

if [ "${AGENT_GATES_DEEP:-0}" = "1" ]; then
  exec "$(dirname -- "$0")/agent-gates-deep.sh" "$@"
fi

started=$(date +%s)
failed=0

gate() {
  local name=$1; shift
  printf '\n=== %s ===\n' "$name"
  if "$@"; then
    printf '%s: passed\n' "$name"
  else
    printf '%s: FAILED\n' "$name"
    failed=1
  fi
}

# ec/annotations/registers.yaml is the source of truth CLAUDE.md points
# everyone at; a syntax error or a missing required key there is worse
# than the same mistake almost anywhere else in the repo.
check_registers_yaml() {
  python3 - <<'PY'
import sys
import yaml

with open("ec/annotations/registers.yaml") as f:
    data = yaml.safe_load(f)

regs = data.get("registers")
if not isinstance(regs, list) or not regs:
    print("registers.yaml: no 'registers' list found", file=sys.stderr)
    sys.exit(1)

required = {"name", "addr", "sources", "status"}
ok = True
for i, r in enumerate(regs):
    missing = required - r.keys()
    if missing:
        print(f"registers.yaml: entry {i} ({r.get('name', '?')}) missing {missing}", file=sys.stderr)
        ok = False

print(f"registers.yaml: {len(regs)} entries, all required keys present" if ok else "registers.yaml: FAILED")
sys.exit(0 if ok else 1)
PY
}

# Not a style check -- ec/tools/scan_refs.py producing the wrong count
# silently would mislead every future reference to it. Cross-checks
# against a value docs/findings.md and registers.yaml both cite, so a
# regression here is a regression a reader would also hit.
check_scan_refs_smoke_test() {
  local out
  out=$(python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x043E) || return 1
  echo "$out"
  echo "$out" | grep -q 'refs=15' && echo "$out" | grep -q 'referenced'
}

# The per-image reference counts in registers.yaml are the evidence several
# statuses rest on, and a file-wide total hiding PD-image references is the
# mistake docs/findings.md §3a had to correct. This recomputes every count
# from the committed image, so the audit stays checkable rather than trusted.
check_register_counts() {
  python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
}

check_python_syntax() {
  local f rc=0
  for f in ec/tools/*.py bios/tools/*.py windows/tools/*.py ghidra/tools/*.py; do
    [ -e "$f" ] || continue
    python3 -m py_compile "$f" || rc=1
  done
  return "$rc"
}

# The decompilation pipeline's own self-tests and staleness checks. Each of
# these runs with no Ghidra and no network, which is what lets them live in a
# gate: a full Ghidra rebuild is minutes, and this gate has to stay inside the
# agent's own turn budget as well as CI's. A full rebuild is a separate,
# opt-in step (build_ec_decompile.py --self-test --oracle).
check_ghidra_tooling() {
  local rc=0 scratch tool
  # Each decompiler tool checks its own output -- the tool that wrote a file is
  # the tool that checks it, so the self-test lives next to the code the review
  # stage reads. The scratch dir is only passed to the tools that take one;
  # --check and --self-test need no Ghidra and no network, which is what lets
  # them live in a gate at all. A full rebuild does not, and is not here.
  #
  # Nothing in this loop turns on whether sdas8051 is installed, which is the
  # other half of the split. The sdas8051 re-encode used to run from here
  # whenever `command -v sdas8051` found the tool, and that made the gate's
  # contents a function of the runner: CI installed sdcc and a developer might
  # not, so what got checked was whichever machine happened to be running, with
  # nothing recording the difference. It is in agent-gates-deep.sh now, where
  # asking for it is the thing that turns it on. verify_reassembly.py's
  # self-test does assemble a four-instruction fixture, and does it after every
  # assertion, so it cannot change the verdict either way -- see the case below.
  scratch=$(mktemp -d)
  for tool in ec/tools/gen_xdata_symbols.py \
              ec/tools/build_ec_decompile.py \
              ec/tools/verify_reassembly.py \
              ec/tools/merge_annotation_shards.py \
              bios/tools/bios_extract.py \
              windows/tools/decompile_native.py; do
    [ -f "$tool" ] || continue
    case "$tool" in
      # The symbol generator takes no --work and has no --self-test; its
      # --check is the whole of it.
      *gen_xdata_symbols.py)
        python3 "$tool" --check || rc=1
        ;;
      *decompile_native.py)
        python3 "$tool" --check && python3 "$tool" --self-test || rc=1
        ;;
      # The annotation merge's refusals. It is what stands between a fan-out's
      # CSV and main, and a check that has quietly stopped rejecting anything
      # looks exactly like a check that is working.
      *merge_annotation_shards.py)
        python3 "$tool" --self-test || rc=1
        ;;
      # --check needs no Ghidra: it confirms that every byte of every committed
      # listing is the byte in the firmware, and that the committed reassembly
      # report still describes those listings with nothing in it disagreeing.
      # --self-test is the tool's own known answers -- the digest's canonical
      # form, the compare_digests() failure paths, GAP_FORMS and
      # BIT_UNSUPPORTED -- and they sit before the no-assembler early exit, so
      # they run here whether or not sdas8051 is installed. What needs an
      # assembler is the *re-encode*: an independent assembler encoding the
      # committed listing back to bytes, the stronger claim, and the deep
      # tier's. The self-test's own tail does invoke the assembler over a
      # four-instruction fixture when it is present; that is not the re-encode.
      # --verify-provenance audits the listing_digest migration against the
      # history (docs/findings.md §14f), so it needs a full clone: ci.yml's gates
      # checkout and the agent stages' all use fetch-depth: 0 for it.
      *verify_reassembly.py)
        python3 "$tool" --check && python3 "$tool" --self-test && \
        python3 "$tool" --verify-provenance \
          --base 08b72e2 --migration a56b3bb --listings-from 8c7985e || rc=1
        ;;
      *)
        # build_ec_decompile.py and bios_extract.py both take --work.
        python3 "$tool" --work "$scratch" --check && \
        python3 "$tool" --work "$scratch" --self-test || rc=1
        ;;
    esac
  done
  rm -rf "$scratch"
  return "$rc"
}

check_shellcheck() {
  local f rc=0
  while IFS= read -r -d '' f; do
    shellcheck "$f" || rc=1
  done < <(find . -name '*.sh' -not -path './.git/*' -not -path './.claude/*' -print0)
  return "$rc"
}

# A relative markdown link that 404s is a documentation bug that's
# otherwise invisible until someone clicks it -- and CLAUDE.md/findings.md
# cross-reference each other and ec/annotations/registers.yaml constantly.
check_doc_links() {
  local broken=0
  while IFS=: read -r file link; do
    local dir
    dir=$(dirname "$file")
    [ -f "$dir/$link" ] || { echo "BROKEN: $file -> $link"; broken=1; }
  done < <(grep -rEo '\]\(([^:)]+\.md)\)' --include='*.md' . 2>/dev/null \
            | sed -E 's/:\]\(([^)]+)\)/:\1/')
  return "$broken"
}

gate 'registers.yaml'  check_registers_yaml
gate 'scan_refs.py smoke test' check_scan_refs_smoke_test
gate 'register counts'  check_register_counts
gate 'ghidra tooling'  check_ghidra_tooling
gate 'python syntax'   check_python_syntax
gate 'shellcheck'      check_shellcheck
gate 'doc links'       check_doc_links

# What this tier does not run, and the one command that runs it. Printed
# unconditionally, including on a failing run, because the moment to notice
# that a check has stopped running is before it has stopped failing. Wording is
# "this tier" rather than "this run" so it stays true when the deep script
# re-runs this file and then does those two things itself.
printf '\nnote  this tier does not run: the sdas8051 re-encode of the committed\n'
printf '      listing, and the advisory cross-decoder comparison. Both are in\n'
printf '      agent-gates-deep.sh, which AGENT_GATES_DEEP=1\n'
printf '      .github/scripts/agent-gates.sh runs after this.\n'

# The elapsed line is printed, never asserted. A wall-clock budget in a gate is
# the flaky check that gets switched off after one bad afternoon on a shared
# runner, and deleting the assertion is the only fix anyone reaches for. The
# number is here to be read and to make a regression visible in a diff of two
# runs, not to fail a commit.
elapsed=$(( $(date +%s) - started ))

if [ "$failed" -ne 0 ]; then
  printf '\nOne or more gates failed (%ds elapsed).\n' "$elapsed"
  exit 1
fi

printf '\nAll gates passed (%ds elapsed).\n' "$elapsed"
