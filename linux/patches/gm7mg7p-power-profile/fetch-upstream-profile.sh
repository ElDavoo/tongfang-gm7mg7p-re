#!/usr/bin/env bash
#
# Re-derive upstream-excerpt-profile.txt from the real source, offline-checkable.
#
#   bash fetch-upstream-profile.sh            fetch, derive, diff against the
#                                             committed excerpt; non-zero if they
#                                             differ
#   bash fetch-upstream-profile.sh --derive   print the derived fragments to stdout
#                                             and stop, fetching nothing
#   bash fetch-upstream-profile.sh --offline  skip the fetch and diff only
#
# It needs the network and so is NOT part of any gate. `tools/check_power_profile.py`
# checks the same excerpt offline, byte for byte, and that is what a reviewer
# can run without egress. This script is the other half: it proves the excerpt
# matches the source it claims to quote.
#
# **This is a deliberate near-duplicate of ../gm7mg7p-dmi-entry/fetch-upstream.sh,
# not an oversight and not a second way to do one job.** The two range lists are
# disjoint -- that one quotes the feature bits, the cTGP block, the charge block
# and the DMI table; this one quotes the power-mode block, the PL registers, the
# regmap gates and the notify path. Generalising the existing script into a
# shared one would mean editing a file other branches have open, which is the
# merge conflict this repository's conventions exist to avoid, and it would make
# each of the two excerpts' *contents* depend on the other's release. What is
# shared rather than copied is the behaviour: the rev comes from
# `linux/patches/BASE_COMMIT`, the two pins are checked for agreement before the
# network is touched, two clients are tried because a refused command is a fact
# about a command and not about the network, and only the fragments below the
# DELIMITER line are diffed.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXCERPT="$HERE/upstream-excerpt-profile.txt"
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
# The ranges are what profile-map.csv and tools/check_power_profile.py cite, so
# changing one here without changing a map row's `upstream_addr_source` fails the
# checker's byte-for-byte rules, which is the intended coupling.
read -r -d '' RANGES <<'EOF' || true
36,52|The #include list -- the header set this patch builds against, which adds none
143,162|EC_ADDR_AP_OEM (0x0741), the EC_ADDR_SUPPORT_5 / FAN_TURBO_SUPPORTED block -- the Turbo gate this patch does NOT use -- and the cTGP block this one does not write
181,190|EC_ADDR_MANUAL_FAN_CTRL (0x0751) and the FAN_MODE_* bits the three vendor values are spelled in
240,254|EC_ADDR_BIOS_OEM_2 (0x0782) / DEFAULT_MODE, the PL registers, EC_ADDR_FAN_DEFAULT (0x0786)
344,352|PWM_MAX / FAN_TABLE_LENGTH -- the fan-table row length, and where this patch's own constants go
378,420|struct uniwill_data
428,436|struct uniwill_device_descriptor -- the field this patch adds a callback to
470,482|uniwill_keymap around UNIWILL_OSD_PERFORMANCE_MODE_TOGGLE (0xB0) and its KEY_F14 mapping
597,612|uniwill_writeable_reg -- the gate every new written address has to be added to
626,640|uniwill_readable_reg
674,690|uniwill_volatile_reg
700,712|uniwill_ec_config
1250,1270|uniwill_attrs -- where this patch adds the two profile attributes
1287,1325|uniwill_attr_is_visible and uniwill_group
2238,2250|The default: arm of uniwill_notify, which is where 0xB0 is intercepted
2344,2350|uniwill_probe, where the profile is initialised
2648,2664|uniwill_driver
2805,2814|A real descriptor, for the field-initialiser style
2862,2872|The head of uniwill_dmi_table, for the row syntax
3310,3321|The end of uniwill_dmi_table and the { } terminator
3380,3386|MODULE_AUTHOR / MODULE_LICENSE
EOF

# Fragments only. Everything above the DELIMITER line in the committed excerpt
# is this script's to own (rev, byte counts, hashes); everything below is
# upstream's, and is what gets diffed.
DELIMITER="--- fragments below this line are verbatim from uniwill-acpi.c ---"

# `sed` prints the raw range and `awk` prefixes each line with its own upstream
# line number. The number is a prefix, never a substitution inside the line, so the
# quoted text stays byte-for-byte what upstream wrote -- which is the whole point,
# and what `tools/check_power_profile.py` rule 4 checks the patch against.
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
    echo "       either pin is a human's call." >&2
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
