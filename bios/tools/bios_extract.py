#!/usr/bin/env python3
r"""Regenerate bios/ifr/ and bios/decompiled/ from the committed BIOS package.

Input is only `vendor/bios-1.09/BIOS_1.09.zip`. The steps:

  1. take GM7MG7P/GMxMGxxN109A08.ROM out of the zip (SHA-256 checked),
  2. UEFIExtract it (`UEFIExtract rom all`),
  3. find the `Setup` DXE driver and run `ifrextractor <Setup.efi> verbose`,
     giving bios/ifr/Setup.en-US.ifr.txt,
  4. copy the PE32/TE bodies of the vendor modules named in MODULES,
  5. decompile each with Ghidra headless (bios/ghidra/DecompAll.java) into
     bios/decompiled/<Module>.c. PE32 (x64 DXE/SMM) images import normally.
     TE (IA32 PEI) images have no Ghidra loader, so they are loaded raw at
     their execute-in-place address, ImageBase + StrippedSize - sizeof(TE
     header), with bios/ghidra/TeEntry.java marking the entry point.

The tools are the ones .github/actions/project-setup installs (UEFIExtract,
ifrextractor, analyzeHeadless on PATH). Pass their paths explicitly where
they are not on PATH, e.g. on Windows:

  python bios/tools/bios_extract.py --work C:\tmp\bios ^
      --uefiextract %LOCALAPPDATA%\re-tools\uefiextract\UEFIExtract.exe ^
      --ifrextractor %LOCALAPPDATA%\re-tools\ifrextractor\ifrextractor.exe ^
      --ghidra %LOCALAPPDATA%\re-tools\ghidra_12.1.3_PUBLIC\support\analyzeHeadless.bat

The IFR and decompiles in bios/ were produced this way with UEFIExtract NE
A75, ifrextractor 1.6.1 and Ghidra 12.1.3.
"""
import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ZIP = os.path.join(REPO, "vendor", "bios-1.09", "BIOS_1.09.zip")
ROM_MEMBER = "GM7MG7P/GMxMGxxN109A08.ROM"
ROM_SHA256 = "dfe8047f35bb1125bbb45d69c96ad83d64e59dd5e50b8d88052c0db04a2d920e"

# Every vendor ("Oem*") module that references UniWillVariable by GUID, plus
# OemOcPei. The Intel/AMI modules are left out: they are reference code.
MODULES = [
    "OemOcDxe", "OemOcPei", "OemUniWillVariableDxe", "OemServiceDxe",
    "OemServiceSmm", "OemACRecoveryDxe", "OemDgpuBoardIDDxe",
    "OemDisplayModeDxe", "OemKbLightDxe", "OemUsbLightBarDxe",
    "OemTurboModeDxe", "OemPowerModeDxe",
]


def run(cmd, **kw):
    print("+", " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def extract_rom(work):
    rom = os.path.join(work, "rom.bin")
    data = zipfile.ZipFile(ZIP).read(ROM_MEMBER)
    digest = hashlib.sha256(data).hexdigest()
    if digest != ROM_SHA256:
        raise SystemExit(f"error: {ROM_MEMBER} SHA-256 {digest}, expected {ROM_SHA256}")
    with open(rom, "wb") as f:
        f.write(data)
    return rom


def image_body(module_dir):
    for sec in ("PE32 image section", "TE image section"):
        for name in sorted(os.listdir(module_dir)):
            if name.endswith(sec):
                body = os.path.join(module_dir, name, "body.bin")
                if os.path.isfile(body):
                    return body, sec.split()[0]
    return None, None


def find_module(dump, name):
    """First "<n> <name>" directory holding an image section. PEI modules
    appear twice (main and recovery volume); insist the copies match."""
    hits = []
    for dp, dns, _ in os.walk(dump):
        for d in sorted(dns):
            if d.split(" ", 1)[-1] == name:
                body, kind = image_body(os.path.join(dp, d))
                if body:
                    hits.append((body, kind))
    if not hits:
        raise SystemExit(f"error: module {name} not found in {dump}")
    first = open(hits[0][0], "rb").read()
    for body, _ in hits[1:]:
        if open(body, "rb").read() != first:
            raise SystemExit(f"error: {name} has differing copies; pick one by hand")
    return hits[0]


def te_layout(path):
    d = open(path, "rb").read(0x28)
    if d[:2] != b"VZ":
        raise SystemExit(f"error: {path} is not a TE image")
    stripped = struct.unpack_from("<H", d, 6)[0]
    entry = struct.unpack_from("<I", d, 8)[0]
    image_base = struct.unpack_from("<Q", d, 16)[0]
    return image_base + stripped - 0x28, image_base + entry


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True, help="scratch directory (created)")
    ap.add_argument("--out", default=os.path.join(REPO, "bios"))
    ap.add_argument("--uefiextract", default="UEFIExtract")
    ap.add_argument("--ifrextractor", default="ifrextractor")
    ap.add_argument("--ghidra", default="analyzeHeadless",
                    help="analyzeHeadless (or .bat) path; '' to skip decompiling")
    args = ap.parse_args(argv)

    work = os.path.abspath(args.work)
    os.makedirs(work, exist_ok=True)
    rom = extract_rom(work)
    dump = rom + ".dump"
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    run([args.uefiextract, rom, "all"], stdout=subprocess.DEVNULL)

    setup_body, _ = find_module(dump, "Setup")
    setup = os.path.join(work, "Setup.efi")
    shutil.copyfile(setup_body, setup)
    run([args.ifrextractor, setup, "verbose"], stdout=subprocess.DEVNULL)
    ifr_dir = os.path.join(args.out, "ifr")
    os.makedirs(ifr_dir, exist_ok=True)
    shutil.copyfile(setup + ".0.0.en-US.uefi.ifr.txt",
                    os.path.join(ifr_dir, "Setup.en-US.ifr.txt"))

    mod_dir = os.path.join(work, "modules")
    os.makedirs(mod_dir, exist_ok=True)
    found = {}
    for name in MODULES:
        body, kind = find_module(dump, name)
        dst = os.path.join(mod_dir, name + ".efi")
        shutil.copyfile(body, dst)
        found[name] = (dst, kind)
        print(f"{name}: {kind}, {os.path.getsize(dst)} bytes")

    if not args.ghidra:
        return 0
    out_c = os.path.join(args.out, "decompiled")
    os.makedirs(out_c, exist_ok=True)
    scripts = os.path.join(REPO, "bios", "ghidra")
    proj = os.path.join(work, "ghidra-project")
    os.makedirs(proj, exist_ok=True)
    for name, (path, kind) in found.items():
        cmd = [args.ghidra, proj, name, "-import", path, "-overwrite",
               "-scriptPath", scripts]
        if kind == "TE":
            load, entry = te_layout(path)
            cmd += ["-loader", "BinaryLoader", "-loader-baseAddr", hex(load),
                    "-processor", "x86:LE:32:default", "-cspec", "gcc",
                    "-preScript", "TeEntry.java", f"{entry:x}"]
        cmd += ["-postScript", "DecompAll.java", out_c]
        run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.isfile(os.path.join(out_c, name + ".c")):
            raise SystemExit(f"error: Ghidra produced no {name}.c")
    return 0


if __name__ == "__main__":
    sys.exit(main())
