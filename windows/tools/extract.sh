#!/usr/bin/env bash
# Reproducible extraction pipeline: vendor installers -> decompilable .NET
# assemblies. Run from repo root. Requires: innoextract, unzip/python3
# zipfile, ilspycmd (all available via `nix shell nixpkgs#<pkg>`).
#
# Usage: windows/tools/extract.sh <outdir>
set -euo pipefail
OUT="${1:?usage: extract.sh <outdir>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mkdir -p "$OUT"

echo "== v3.9.18.0 (UWP + Win32 bridge, Inno installer) =="
mkdir -p "$OUT/v3.9.18.0/msix" "$OUT/v3.9.18.0/inno"
python3 - "$ROOT/vendor/control-center-3.9.18.0/GamingCenter3_Cross.UWP_3.9.18.0_x64.msixbundle" "$OUT/v3.9.18.0/msix" <<'PY'
import sys, zipfile
bundle, outdir = sys.argv[1], sys.argv[2]
zb = zipfile.ZipFile(bundle)
inner = [n for n in zb.namelist() if n.endswith("_x64.msix")][0]
zb.extract(inner, outdir)
zi = zipfile.ZipFile(f"{outdir}/{inner}")
zi.extractall(outdir)
print(f"extracted {inner} -> {outdir}")
PY
innoextract -s -e -d "$OUT/v3.9.18.0/inno" "$ROOT/vendor/control-center-3.9.18.0/setup.exe"
echo "  UWP native+managed DLL: $OUT/v3.9.18.0/msix/GamingCenter3_Cross.{dll,exe}"
echo "  Win32 service (the one with EC access): $OUT/v3.9.18.0/inno/app/UniwillService/MyControlCenter/GCUService.exe"

echo "== v3.1.6.0 (older Inno installer, less/differently obfuscated) =="
mkdir -p "$OUT/v3.1.6.0/inno"
python3 - "$ROOT/vendor/control-center-3.1.6.0" "$OUT/v3.1.6.0" <<'PY'
import sys, zipfile, pathlib
# The v3.1.6.0 installer only exists inside the original vendor driver zip in
# this repo's source tree; if you only have the files under vendor/
# control-center-3.1.6.0/, the .exe is already extracted there.
PY
if [ -f "$ROOT/vendor/control-center-3.1.6.0/UniwillService_3.1.6.0_STD.exe" ]; then
  innoextract -s -e -d "$OUT/v3.1.6.0/inno" "$ROOT/vendor/control-center-3.1.6.0/UniwillService_3.1.6.0_STD.exe"
  echo "  service: $OUT/v3.1.6.0/inno/app/UniwillService/MyControlCenter/GCUService.exe"
fi

echo
echo "== decompile with ilspycmd =="
echo "ConfuserEx-style anti-tamper (see ../antitamper/README.md) makes -p"
echo "(whole-project) decompile crash on Object/record types added in newer"
echo "SDK output. Two workarounds, in order of preference:"
echo "  1. -lv CSharp8_0   (avoids the C#9 record-decompiler crash entirely)"
echo "  2. -t <FullTypeName>   (decompile one type at a time; slower but survives"
echo "                          individual method-body decrypt failures)"
echo
echo "Example:"
echo "  ilspycmd -lv CSharp8_0 -t GCUService.MySystem.BatteryProtection2 \\"
echo "    $OUT/v3.9.18.0/inno/app/UniwillService/MyControlCenter/GCUService.exe"
echo
echo "== other vendor-managed assemblies (v3.9.18.0, never decompiled until now) =="
echo "Same ilspycmd caveats as GCUService above. Three decompile clean as a"
echo "single file; one (SystrayComponent) does not -- see the note at the end."
echo
echo "  clean single-file decompiles (no -p needed; measured with ilspycmd 9.1):"
echo "    ilspycmd -lv CSharp8_0 -o $OUT/managed/M2Mqtt.Net \\"
echo "      $OUT/v3.9.18.0/inno/app/UniwillService/MyControlCenter/M2Mqtt.Net.dll"
echo "    ilspycmd -lv CSharp8_0 -o $OUT/managed/EnableTray \\"
echo "      $OUT/v3.9.18.0/inno/app/UniwillService/MyControlCenter/EnableTray.exe"
echo "    ilspycmd -lv CSharp8_0 -o $OUT/managed/Colourful \\"
echo "      $OUT/v3.9.18.0/inno/app/UniwillService/MyControlCenter/Colourful.dll"
echo
echo "  SystrayComponent.exe ships in the UWP msix, not the Inno tree:"
echo "    ilspycmd -lv CSharp8_0 -p -o $OUT/managed/SystrayComponent \\"
echo "      $OUT/v3.9.18.0/msix/Win32/SystrayComponent.exe"
echo
echo "  NOTE (SystrayComponent): the main type SystrayComponent."
echo "  SystrayApplicationContext makes ilspycmd 9.1 itself throw"
echo "  'System.BadImageFormatException: Read out of bounds' while reading a"
echo "  method-body signature, under -p, whole-file and -t alike; -p writes"
echo "  SystrayApplicationContext.cs as 0 bytes. The smaller types (Form1,"
echo "  MyRamFan1p5, Program) decompile fine. That type's code was NOT"
echo "  obtained by this method -- try a newer ilspycmd (11.x) or a different"
echo "  decompiler before concluding anything about it. Do not add it to the"
echo "  Ghidra native list: it is managed, and Ghidra cannot decompile it."
