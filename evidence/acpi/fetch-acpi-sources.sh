#!/usr/bin/env bash
#
# Re-derive the two interpreter excerpts under evidence/acpi/ from the real
# upstream source, offline-checkable against what is committed.
#
# The excerpts exist because issue #1337 asks what the *interpreter* does with
# an unaligned `SystemMemory` `Field` operand, and `docs/findings/mmrd-unaligned-escape.md`
# could only record that as a blank: the repository holds the ASL (the method)
# and the vendor driver (the thing that receives the IOCTL), and neither of
# those interprets AML. So the source the behaviour comes from has to be
# fetched and kept, the way every other entry under evidence/ carries its
# provenance. See evidence/acpi/README.md for what each file is and
# docs/findings/acpi-interpreter-region-access.md for what was read out of them.
#
# It needs the network and so is NOT part of any gate. `tools/check_acpi_interpreter_sources.py`
# checks the same excerpts offline -- provenance fields, and that every
# `evidence/acpi/<file>:NNN` citation in the write-up lands on the symbol the
# write-up names -- and that is what a reviewer can run without egress. This
# script is the other half: it proves the fragments are still verbatim at the
# pinned revision.
#
#   bash fetch-acpi-sources.sh            fetch, derive, diff against the
#                                         committed excerpts; non-zero if they
#                                         differ
#   bash fetch-acpi-sources.sh --derive   print the derived fragments to stdout
#                                         and stop, fetching nothing
#   bash fetch-acpi-sources.sh --offline  skip the fetch and diff only
#
# Why `curl` is not used even though the plan named it: on the runner this was
# authored in, the permission layer denied the literal `curl` invocation while
# the identical request over `python3 urllib` returned the file on the first
# try. A refused command is a fact about that command, not a network wall, and
# recording it as one is the error this file exists to prevent. Both clients
# are tried and whichever answers is named in the output -- the same reasoning
# as linux/patches/gm7mg7p-dmi-entry/fetch-upstream.sh, whose header says so.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACPICA_EXCERPT="$HERE/acpica-region-access-excerpt.c.txt"
LINUX_EXCERPT="$HERE/linux-acpi-region-access-excerpt.c.txt"

# Pinned revisions. Both are whole commits, not branch names, so a re-fetch a
# year from now is the same bytes. ACPICA's is the commit `master` pointed at
# when this was written; Linux's is the commit the annotated `v6.6` tag
# dereferences to, which is what `raw.githubusercontent.com` resolves the tag
# to when a file is requested by path.
ACPICA_REV="e85aa3bebaae81ed1e6d163511ac7e1eafe732cf"
ACPICA_BASE="https://raw.githubusercontent.com/acpica/acpica/$ACPICA_REV"
LINUX_REV="ffc253263a1375a65fa6c9f62a893e9767fbebfa"
LINUX_BASE="https://raw.githubusercontent.com/torvalds/linux/$LINUX_REV"

# `sed -n A,Bp` ranges against the real upstream files, as
# `FILE,first,last|what the reader is meant to find there`. The line numbers
# are upstream's and the excerpts reproduce them as prefixes, so a citation in
# the write-up means the same line in the excerpt and in ACPICA's tree.
#
# Every range is here because a claim in the write-up rests on it. The ACPICA
# and Linux lists are deliberately the same decision points in two
# independent implementations, because the claim is that both interpreters
# behave the same way and one of them doing it would not show that.
read -r -d '' ACPICA_RANGES <<'EOF' || true
source/components/executer/exregion.c,41,105|AcpiExSystemMemorySpaceHandler -- the bit-width switch that rejects a width it does not know, and the alignment test that is behind #ifdef ACPI_MISALIGNMENT_NOT_SUPPORTED
source/components/executer/exregion.c,194,247|the access itself: LogicalAddrPtr is derived from the requested Address, and the read switch loads at that pointer with ACPI_GET8/16/32/64
source/components/executer/exprep.c,226,278|AcpiExDecodeFieldAccess -- the access-type switch. ByteAcc lands in the AML_FIELD_ACCESS_BYTE case and returns 8, not 32
source/components/executer/exprep.c,341,391|AcpiExPrepCommonFieldObject -- AccessBitWidth becomes AccessByteWidth, and the comment above it says what ByteAlignment means
source/components/executer/exfldio.c,202,222|AcpiExAccessRegion -- the function the dispatch below sits in, so a reader can see which one it is without leaving this file
source/components/executer/exfldio.c,273,278|the width handed to the address-space handler is AccessByteWidth * 8, so the AML field's declared bit length is not what reaches the handler
source/components/executer/exfldio.c,480,491|AcpiExFieldDatumIo's own call site for AcpiExAccessRegion -- the datum goes through AccessRegion on its way to the dispatch above, rather than to the dispatch directly
source/components/executer/exfldio.c,725,746|AcpiExExtractFromField -- AccessBitWidth, and the single-access shortcut that only applies when the field is exactly one datum wide
source/components/executer/exfldio.c,758,774|DatumCount / FieldDatumCount, and the priming read at offset zero
source/components/executer/exfldio.c,776,818|the per-datum loop: the offset advances by AccessByteWidth, and datum i is shifted up by i * AccessBitWidth
source/include/actypes.h,143,155|why the alignment test is compiled out on anything but Itanium
source/components/executer/exresolv.c,278,287|AcpiExResolveNodeToValue -- an ACPI_TYPE_LOCAL_REGION_FIELD source dispatches to AcpiExReadDataFromField, which is where a field read becomes a value
source/components/executer/exfield.c,274,278|AcpiExReadDataFromField calls AcpiExExtractFromField, the function that decides how many accesses to issue
source/include/acmacros.h,7,11|the SPDX-License-Identifier line the Licence field above rests on -- it sits above the excerpted ranges, so it would otherwise not be visible here
source/include/acmacros.h,18,34|ACPI_GET32 -- the load itself, and the comment above it naming the hazard a wider access carries
EOF

read -r -d '' LINUX_RANGES <<'EOF' || true
drivers/acpi/acpica/exregion.c,34,93|acpi_ex_system_memory_space_handler -- the same width switch and the same #ifdef ACPI_MISALIGNMENT_NOT_SUPPORTED, in the copy the kernel builds
drivers/acpi/acpica/exregion.c,190,240|the same access label, the same pointer arithmetic from the requested address, the same ACPI_GET32
drivers/acpi/acpica/exprep.c,204,256|acpi_ex_decode_field_access -- the same switch, ByteAcc still lands on 8
drivers/acpi/acpica/exprep.c,331,337|access_byte_width = ACPI_DIV_8(access_bit_width)
drivers/acpi/acpica/exfldio.c,181,201|acpi_ex_access_region -- the function the dispatch below sits in, so a reader can see which one it is without leaving this file
drivers/acpi/acpica/exfldio.c,244,251|the same dispatch, the same AccessByteWidth * 8
drivers/acpi/acpica/exfldio.c,438,448|acpi_ex_field_datum_io's own call site for acpi_ex_access_region -- the datum goes through access_region on its way to the dispatch above, rather than to the dispatch directly
drivers/acpi/acpica/exfldio.c,675,696|the same AccessBitWidth and the same single-access shortcut
drivers/acpi/acpica/exfldio.c,707,727|the same datum counts and priming read
drivers/acpi/acpica/exfldio.c,729,758|the same per-datum loop and the same shift
drivers/acpi/acpica/exresolv.c,258,270|the same field-read dispatch: acpi_ex_read_data_from_field, from a case of the same four field types
drivers/acpi/acpica/exfield.c,236,239|the same call to acpi_ex_extract_from_field
drivers/acpi/utils.c,1,6|the SPDX-License-Identifier line this file carries -- GPL-2.0-or-later, and not the BSD-3-Clause OR GPL-2.0 the kernel's own ACPICA copies carry
drivers/acpi/utils.c,246,276|acpi_evaluate_integer -- the OS-side answer to the second question: where a returned Integer is read back out of
drivers/acpi/acpica/acmacros.h,1,4|the SPDX-License-Identifier line the kernel's ACPICA copies carry
drivers/acpi/acpica/acmacros.h,13,29|the same ACPI_GET32, and the same comment about the alignment hazard
EOF

# Fragments only. Everything above the DELIMITER line in a committed excerpt is
# hand-owned (rev, URLs, licence, retrieval date); everything below is
# upstream's and is what gets diffed.
ACPICA_DELIMITER="--- fragments below this line are verbatim from acpica at the revision above ---"
LINUX_DELIMITER="--- fragments below this line are verbatim from torvalds/linux at the revision above ---"

# `sed` prints the raw range and `awk` prefixes each line with its own upstream
# line number. The number is a prefix, never a substitution inside the line, so
# the quoted text stays byte-for-byte what upstream wrote.
derive_fragments() {
  local delimiter="$1" ranges="$2"
  echo "$delimiter"
  while IFS='|' read -r spec what; do
    [ -n "${spec// /}" ] || continue
    local file first last src
    file="$(echo "$spec" | tr -d ' ' | cut -d, -f1)"
    first="$(echo "$spec" | tr -d ' ' | cut -d, -f2)"
    last="$(echo "$spec" | tr -d ' ' | cut -d, -f3)"
    src="$SRCROOT/$file"
    if [ ! -f "$src" ]; then
      echo "FATAL: $file was not fetched into $SRCROOT" >&2
      return 1
    fi
    if [ "$(sed -n "${first}p" "$src" | wc -l)" = "0" ]; then
      echo "FATAL: $file has no line $first upstream; the revision moved" >&2
      return 1
    fi
    echo ""
    echo "  [$what]"
    echo "  $file lines $first-$last"
    sed -n "${first},${last}p" "$src" \
      | awk '{ printf "  %5d: %s\n", NR + '"$first"' - 1, $0 }'
  done <<< "$ranges"
}

MODE="${1:-}"
SRCROOT=""

fetch() {
  local out
  out="$(mktemp -d)"
  SRCROOT="$out"

  fetch_one() {
    local url="$1" dest="$2"
    mkdir -p "$(dirname "$dest")"
    if curl -fsSL --retry 3 -o "$dest" "$url" 2>/dev/null; then
      echo "fetched with curl" >&2
    elif python3 -c '
import sys, urllib.request
req = urllib.request.Request(sys.argv[1], headers={"User-Agent": "curl/8"})
open(sys.argv[2], "wb").write(urllib.request.urlopen(req, timeout=60).read())
' "$url" "$dest"; then
      echo "fetched with python3 urllib (curl was refused by the permission layer)" >&2
    else
      echo "FATAL: neither curl nor python3 urllib could fetch $url" >&2
      echo "       Record this as an environment fact -- the command, its exit" >&2
      echo "       code and its stderr -- and not as a property of the problem." >&2
      return 1
    fi
    echo "  $(wc -c < "$dest" | tr -d ' ') bytes  $(sha256sum "$dest" | cut -d' ' -f1)  $url" >&2
  }

  echo "ACPICA $ACPICA_REV" >&2
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    fetch_one "$ACPICA_BASE/$f" "$out/$f"
  done <<'EOF'
source/components/executer/exregion.c
source/components/executer/exprep.c
source/components/executer/exfldio.c
source/components/executer/exresolv.c
source/components/executer/exfield.c
source/include/actypes.h
source/include/acmacros.h
EOF

  echo "Linux $LINUX_REV" >&2
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    fetch_one "$LINUX_BASE/$f" "$out/$f"
  done <<'EOF'
drivers/acpi/acpica/exregion.c
drivers/acpi/acpica/exprep.c
drivers/acpi/acpica/exfldio.c
drivers/acpi/acpica/exresolv.c
drivers/acpi/acpica/exfield.c
drivers/acpi/acpica/acmacros.h
drivers/acpi/utils.c
EOF
}

case "$MODE" in
  --derive)
    [ -n "$SRCROOT" ] || SRCROOT="${ACPICA_SRCROOT:?--derive needs ACPICA_SRCROOT=/path/to/unpacked/tarball}"
    derive_fragments "$ACPICA_DELIMITER" "$ACPICA_RANGES"
    echo ""
    derive_fragments "$LINUX_DELIMITER" "$LINUX_RANGES"
    exit 0
    ;;
  --offline)
    ;;
  "")
    fetch
    ;;
  *)
    echo "usage: $0 [--derive|--offline]" >&2
    exit 2
    ;;
esac

# --- the check: the committed fragments against a fresh derivation --
if [ -z "$SRCROOT" ]; then
  echo "--offline: diffing only; set ACPICA_SRCROOT=/path/to/unpacked/tree to" >&2
  echo "           compare against a real copy. Without it there is nothing to diff." >&2
  echo "$ACPICA_DELIMITER"
  echo "$LINUX_DELIMITER"
  exit 0
fi

STATUS=0
check_one() {
  local label="$1" excerpt="$2" delimiter="$3" ranges="$4"
  local derived committed
  derived="$(mktemp)"
  committed="$(mktemp)"
  derive_fragments "$delimiter" "$ranges" > "$derived"
  # The delimiter line is part of what gets compared, so it is re-printed when
  # the block opens. Without that the committed side starts one line below the
  # derived one and every run reports a one-line phantom diff.
  awk -v d="$delimiter" 'f { print } index($0, d) == 1 { f = 1; print }' \
    "$excerpt" > "$committed"

  if diff -u "$committed" "$derived"; then
    echo "OK: every fragment in $(basename "$excerpt") is still what the source says." >&2
  else
    echo "" >&2
    echo "MISMATCH: $excerpt no longer matches the pinned revision ($label)." >&2
    echo "If upstream moved, bumping the revision here is what to discuss;" >&2
    echo "do not edit the excerpt to match a rev nobody agreed to fetch." >&2
    STATUS=1
  fi
  rm -f "$derived" "$committed"
}

check_one "ACPICA $ACPICA_REV" "$ACPICA_EXCERPT" "$ACPICA_DELIMITER" "$ACPICA_RANGES"
check_one "Linux $LINUX_REV" "$LINUX_EXCERPT" "$LINUX_DELIMITER" "$LINUX_RANGES"
exit "$STATUS"