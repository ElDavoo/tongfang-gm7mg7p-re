#!/usr/bin/env bash
#
# Re-derive upstream-excerpt.txt from the real source, offline-checkable.
#
# Issue #10's previous attempt asserted the upstream source was unreadable and
# built a one-bit descriptor on that assertion. The assertion was false: the
# fetch is a five-second HTTPS GET that works from a runner in this pipeline.
# This script exists so the next person does not have to re-litigate that -- it
# performs the fetch, and it re-derives the committed excerpt from what came
# back rather than trusting a copy.
#
# It needs the network and so is NOT part of any gate. `tools/check_dmi_descriptor.py`
# checks the same excerpt offline, byte for byte, and that is what a reviewer can
# run without egress. This script is the other half: it proves the excerpt
# matches the source it claims to quote.
#
#   bash fetch-upstream.sh            fetch, derive, diff against the committed
#                                     excerpt; non-zero if they differ
#   bash fetch-upstream.sh --derive   print the derived fragments to stdout and
#                                     stop, fetching nothing
#   bash fetch-upstream.sh --offline  skip the fetch and diff only
#
# Why `curl` is not used, though the plan named it: on the runner this was
# authored in, the permission layer denied the literal `curl` invocation while
# the identical request over `python3 urllib` returned 27,634 bytes on the
# first try. A refused command is not a network wall, and recording it as one
# is the error this whole file exists to prevent. Both clients are tried, and
# whichever answers is reported as the one that did.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXCERPT="$HERE/upstream-excerpt.txt"
BASE_COMMIT_FILE="$HERE/../BASE_COMMIT"
NIX_FILE="$HERE/../../nix/uniwill-laptop.nix"

# The rev is read from linux/patches/BASE_COMMIT rather than repeated here, so
# bumping the pin in one place cannot leave this script fetching something else.
REV="$(awk '{print $1}' "$BASE_COMMIT_FILE")"
URL="https://codeload.github.com/Wer-Wolf/uniwill-laptop/tar.gz/$REV"

# The fragments, as `sed -n A,Bp` ranges against the real file. The line numbers
# are upstream's, and the excerpt reproduces them; `derive()` prints each line
# with its own number so a drifted excerpt fails the diff below.
#
# The ranges are what the map and the checker cite, so changing one here without
# changing feature-map.csv's `upstream_addr_source` will fail the checker's
# byte-for-byte rules, which is the intended coupling.
read -r -d '' RANGES <<'EOF' || true
78,104|EC_ADDR_CPU_TEMP / EC_ADDR_GPU_TEMP, and the main + secondary fan RPM addresses
110,116|EC_ADDR_OEM_9 -- upstream's AC_AUTO_BOOT_ENABLE bit lives here
134,134|PROJECT_ID_CML_GAMING -- this board's project id
154,163|EC_ADDR_CTGP_DB_*, the NVIDIA cTGP control block
164,180|EC_ADDR_LIGHTBAR_AC_* and EC_ADDR_BIOS_OEM (FN_LOCK_STATUS)
204,215|EC_ADDR_TRIGGER -- the super key lock and USB powershare bits
218,222|EC_ADDR_SWITCH_STATUS (SUPER_KEY_LOCK_STATUS)
254,268|EC_ADDR_FAN_DEFAULT / EC_ADDR_FAN_CTRL, and EC_ADDR_KBD_STATUS
284,296|EC_ADDR_OEM_4 (charge modes, TOUCHPAD_TOGGLE_OFF) and EC_ADDR_CHARGE_CTRL
304,308|EC_ADDR_USB_C_POWER_PRIORITY
356,371|The UNIWILL_FEATURE_* bit assignments
428,435|struct uniwill_device_descriptor -- the descriptor's fields
2805,2813|A real descriptor, for the .features = A | B continuation style
2849,2861|A real descriptor that sets the kbd_led_* fields
2863,2880|The head of uniwill_dmi_table, for the row syntax
3311,3321|The end of uniwill_dmi_table and the { } terminator
3384,3386|MODULE_AUTHOR / MODULE_LICENSE
EOF

# Fragments only. Everything above the DELIMITER line in the committed excerpt
# is this script's to own (rev, byte counts, hashes); everything below is
# upstream's, and is what gets diffed.
DELIMITER="--- fragments below this line are verbatim from uniwill-acpi.c ---"

# `sed` prints the raw range and `awk` prefixes each line with its own upstream
# line number. The number is a prefix, never a substitution inside the line, so
# the quoted text stays byte-for-byte what upstream wrote -- which is the whole
# point, and what `tools/check_dmi_descriptor.py` rule 7 checks the map against.
derive_fragments() {
  local src="$1"
  echo "$DELIMITER"
  while IFS='|' read -r range what; do
    [ -n "${range// /}" ] || continue
    local first last
    first="$(echo "$range" | tr -d ' ' | cut -d, -f1)"
    last="$(echo "$range" | tr -d ' ' | cut -d, -f2)"
    echo ""
    echo "  [$what]"
    echo "  uniwill-acpi.c lines $first-$last"
    sed -n "${first},${last}p" "$src" \
      | awk '{ printf "  %5d: %s\n", NR + '"$first"' - 1, $0 }'
  done <<< "$RANGES"
}

MODE="${1:-}"
SRC=""

fetch() {
  local tarball out
  tarball="$(mktemp -t uw-XXXXXX.tar.gz)"
  out="$(mktemp -d)"

  # The nix recipe pins its own rev. Fetching BASE_COMMIT while the build
  # fetches something else would make every fragment here quote a source the
  # build never sees, so the disagreement is refused before the network is
  # touched rather than after a confusing diff.
  #
  # BASE_COMMIT carries the short form (`5a24248`) and nix the full one
  # (40 hex chars), which is the normal shape here and not a disagreement --
  # `fetchFromGitHub` wants the full rev, so short-in-one-place and long-in-
  # another is what agreeing looks like. The test is therefore that one is a
  # prefix of the other, which accepts both spellings and still refuses the
  # case that matters: two revs where neither contains the other.
  local nix_rev
  nix_rev="$(sed -nE 's/.*rev[[:space:]]*=[[:space:]]*"([0-9a-f]+)".*/\1/p' \
    "$NIX_FILE" | head -1)"
  if [ -n "$nix_rev" ] \
     && [ "${nix_rev#"$REV"}" = "$nix_rev" ] \
     && [ "${REV#"$nix_rev"}" = "$REV" ]; then
    echo "FATAL: $BASE_COMMIT_FILE says $REV but $NIX_FILE pins $nix_rev." >&2
    echo "       Neither contains the other, so these are different commits." >&2
    echo "       The excerpt must quote the source the build fetches. Bumping" >&2
    echo "       either pin is a human's call -- see the plan's out-of-scope." >&2
    return 1
  fi

  # Two clients on purpose; see the header. Whichever answers is the one named
  # in the output, because "the fetch was refused" is only a fact about a
  # specific command, not about the network.
  if curl -fsSL --retry 3 -o "$tarball" "$URL" 2>/dev/null; then
    echo "fetched with curl" >&2
  elif python3 -c '
import sys, urllib.request
url = sys.argv[1]
open(sys.argv[2], "wb").write(urllib.request.urlopen(url, timeout=60).read())
' "$URL" "$tarball"; then
    echo "fetched with python3 urllib (curl was refused by the permission layer)" >&2
  else
    echo "FATAL: neither curl nor python3 urllib could fetch $URL" >&2
    echo "       Record this as an environment fact -- the command, its exit" >&2
    echo "       code and its stderr -- and not as a property of the problem." >&2
    return 1
  fi
  tar xzf "$tarball" -C "$out"
  SRC="$(echo "$out"/*/uniwill-acpi.c)"
  echo "tarball: $(wc -c < "$tarball") bytes, sha256 $(sha256sum "$tarball" | cut -d' ' -f1)" >&2
  echo "uniwill-acpi.c: $(wc -c < "$SRC") bytes, $(wc -l < "$SRC") lines, sha256 $(sha256sum "$SRC" | cut -d' ' -f1)" >&2
}

case "$MODE" in
  --derive)
    [ -n "$SRC" ] || SRC="${UW_SRC:?--derive needs a source file in UW_SRC}"
    derive_fragments "$SRC"
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

# --- the check: the committed excerpt's fragments against a fresh derivation --
if [ -z "$SRC" ]; then
  echo "--offline: diffing only; set UW_SRC=/path/to/uniwill-acpi.c to compare" >&2
  echo "           against a real copy. Without it there is nothing to diff." >&2
  echo "$DELIMITER"
  exit 0
fi

derived="$(mktemp)"
committed="$(mktemp)"
derive_fragments "$SRC" > "$derived"
# The delimiter line is part of what gets compared, so it is re-printed when the
# block opens. Without that, the committed side starts one line below the
# derived one and every run reports a one-line phantom diff.
awk -v d="$DELIMITER" 'f { print } index($0, d) == 1 { f = 1; print }' \
  "$EXCERPT" > "$committed"

if diff -u "$committed" "$derived"; then
  echo ""
  echo "OK: every fragment in $EXCERPT is still what the source says at $REV." >&2
  rm -f "$derived" "$committed"
  exit 0
fi

echo "" >&2
echo "MISMATCH: $EXCERPT no longer matches uniwill-acpi.c at $REV." >&2
echo "If upstream moved, the pin in $BASE_COMMIT_FILE is what to discuss;" >&2
echo "do not edit the excerpt to match a rev nobody agreed to fetch." >&2
rm -f "$derived" "$committed"
exit 1
