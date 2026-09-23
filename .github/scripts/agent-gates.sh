#!/usr/bin/env bash
#
# The checks an agent must pass before its work is worth pushing. See
# docs/agent-pipeline.md for why these specific checks and not others —
# short version: these are the fast, mechanical half of correctness here;
# CLAUDE.md's "calibrate, don't overclaim" rule is the half no script can
# check, and is read separately by every stage.

set -uo pipefail

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
  scratch=$(mktemp -d)
  for tool in ec/tools/gen_xdata_symbols.py \
              ec/tools/build_ec_decompile.py \
              ec/tools/verify_reassembly.py \
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
      # The 1:1 check needs no Ghidra and no assembler for --check: it
      # confirms that the committed reassembly report still describes the
      # committed listings, and that nothing in it disagrees. The re-encode
      # itself needs sdas8051 and is a separate opt-in run.
      *verify_reassembly.py)
        python3 "$tool" --check || rc=1
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

if [ "$failed" -ne 0 ]; then
  printf '\nOne or more gates failed.\n'
  exit 1
fi

printf '\nAll gates passed.\n'
