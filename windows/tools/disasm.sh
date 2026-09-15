#!/usr/bin/env bash
# Linear disassembly of a native x86-64 PE (the vendor .sys/.dll under
# vendor/), for the port-I/O adjudication pe_triage.py --listing does.
#
# objdump's PE reader understands the section table, so `objdump -d` gives
# correct VAs and covers every executable section in one pass. radare2 is
# the fallback; its `pd` output is reformatted into objdump's
# "<va>:\t<bytes>\t<mnemonic>" shape so --listing parses either.
#
# Usage: windows/tools/disasm.sh <pefile> [outfile]
set -euo pipefail
PE="${1:?usage: disasm.sh <pefile> [outfile]}"
OUT="${2:--}"

emit() {
  if [ "$OUT" = "-" ]; then cat; else cat > "$OUT"; fi
}

if command -v objdump > /dev/null 2>&1; then
  # Section flags this driver sets (IMAGE_SCN_MEM_NOT_PAGED) make objdump
  # warn on stderr while disassembling correctly; the warnings are noise.
  objdump -d "$PE" 2> /dev/null | emit
elif command -v r2 > /dev/null 2>&1; then
  r2 -q -e scr.color=0 -e asm.bytes=true -c "s section..text" -c "pD \$SS" -- "$PE" \
    | sed -E 's/^0x0*([0-9a-f]+)[[:space:]]+([0-9a-f]+)[[:space:]]+/\1:\t\2\t/' \
    | emit
else
  echo "disasm.sh: no objdump and no r2 on this machine." >&2
  echo "The PE-level analysis in pe_triage.py does not depend on one; only" >&2
  echo "pe_triage.py --portio --listing does. Install binutils or radare2." >&2
  exit 1
fi
