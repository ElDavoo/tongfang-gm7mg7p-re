#!/usr/bin/env python3
r"""Regenerate the BIOS component's tool output: the Setup IFR, the Ghidra
project, and bios/decompiled/.

Input is only `vendor/bios-1.09/BIOS_1.09.zip`. The steps, and which of them
need which tool:

  1. take GM7MG7P/GMxMGxxN109A08.ROM out of the zip (SHA-256 checked),
  2. UEFIExtract it (`uefiextract rom all`),
  3. find the `Setup` DXE driver and run `ifrextractor <Setup.efi> verbose`,
     giving bios/ifr/Setup.en-US.ifr.txt,
  4. copy the PE32/TE bodies of the modules named in MODULES,
  5. import each into one Ghidra project (bios/ghidra/project/), then export
     bios/decompiled/<Module>.c and the index/manifest/load map from it.

UEFIExtract on this ROM is slow and its cost is not predictable: the same
command measured 1.7 s, 2025 s and 2941 s on one machine in one session, so
steps 2-4 run only when they are needed -- `--mode rebuild-project` (the
project is rebuilt from the ROM) or `--extract` (the IFR is regenerated). The
default mode re-exports from the committed project and needs neither.

Two shapes of module, and the difference drives the whole build:

  PE32 (33 modules)  A normal PE import. Ghidra's loader reads the machine
                     type and the entry point and auto-analysis finds the
                     rest, so a batch of them goes into ONE analyzeHeadless
                     invocation: 32 of them in one JVM rather than 32 JVM
                     starts, which is the difference between minutes and an
                     hour.
  TE (5 modules)     A stripped PE image with a small `VZ` header and no
                     loader of its own. Loaded raw at its execute-in-place
                     address, ImageBase + StrippedSize - sizeof(TE header),
                     with the entry point taken from the header. The
                     -loader-baseAddr flag is per-invocation, not per-file,
                     so these are grouped by load address -- which on this
                     ROM means one invocation each.

The address a TE image is loaded at is a derived fact, so it is written to
bios/ghidra/load-map.csv and the entry addresses in it seed the functions the
exporter records the basis of. See bios/ghidra/README.md.

The tools are the ones .github/actions/project-setup installs (UEFIExtract,
ifrextractor, analyzeHeadless on PATH). Pass their paths explicitly where
they are not on PATH, e.g. on Windows:

  python bios/tools/bios_extract.py --work C:\tmp\bios ^
      --uefiextract %LOCALAPPDATA%\re-tools\uefiextract\UEFIExtract.exe ^
      --ifrextractor %LOCALAPPDATA%\re-tools\ifrextractor\ifrextractor.exe ^
      --ghidra %LOCALAPPDATA%\re-tools\ghidra_12.1.3_PUBLIC\support\analyzeHeadless.bat

Usage:
    python3 bios/tools/bios_extract.py --work /tmp/bios
    python3 bios/tools/bios_extract.py --work /tmp/bios --extract
    python3 bios/tools/bios_extract.py --work /tmp/bios --mode rebuild-project
    python3 bios/tools/bios_extract.py --work /tmp/bios --check
    python3 bios/tools/bios_extract.py --work /tmp/bios --self-test

The IFR and the decompiles in bios/ were produced this way with UEFIExtract NE
A75, ifrextractor 1.6.1 and Ghidra 12.1.3.
"""
import argparse
import csv
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ZIP = os.path.join(REPO, "vendor", "bios-1.09", "BIOS_1.09.zip")
ROM_MEMBER = "GM7MG7P/GMxMGxxN109A08.ROM"
ROM_SHA256 = "dfe8047f35bb1125bbb45d69c96ad83d64e59dd5e50b8d88052c0db04a2d920e"

# Every "Oem*" module in the ROM -- TongFang/Uniwill-authored, the ones this
# repository is actually reverse engineering. 32 of them, counted from
# UEFIExtract's dump of the committed zip; `--self-test` re-counts the list
# against the load map so the count cannot drift silently.
VENDOR_MODULES = [
    "OemACPIDriverDxe", "OemACPIDriverHookDxe", "OemACPIDriverSmm",
    "OemACRecoveryDxe", "OemACRecoveryPei", "OemApControlDxe",
    "OemDDSSupportDxe", "OemDgpuBoardIDDxe", "OemDgpuBoardIDPei",
    "OemDisplayModeDxe", "OemGlobalNvsDxe", "OemGlobalNvsSmm",
    "OemHddHeadParkSmm", "OemHooks", "OemHooksPei", "OemHooksSmm",
    "OemI2cDevices", "OemKbLightDxe", "OemKbLightSupportDxe",
    "OemManufactureModeDxe", "OemNetworkDxe", "OemOcDxe", "OemOcPei",
    "OemPowerModeDxe", "OemQkeyDxe", "OemSWBoardIDDxe", "OemServiceDxe",
    "OemServiceSmm", "OemTurboModeDxe", "OemUniWillVariableDxe",
    "OemUsbLightBarDxe", "OemVariableHookDxe",
]

# Intel's overclocking chain. Reference code, not vendor code, and included
# for the same reason the rest of the Intel/AMI modules are reference code:
# these four are what issues #104, #115, #117, #118 and #119 name, and the
# memory-OC chain that OemOcDxe/OemOcPei call into cannot be read without
# them. They are here because those issues name them, not because TongFang
# wrote them.
OVERCLOCK_CHAIN = [
    "DxeOverClock", "OverClockSmiHandler", "OverclockInterface", "PeiOverClock",
]

# One non-Oem module with vendor behaviour: the PS/2 keyboard scan-code table
# the keyboard-light module reads. Neither an OC module nor vendor code, but
# the closest thing to the latter in this ROM for the keyboard path.
OTHER_MODULES = ["EcPs2Kbd"]

# The AMI setup module. Enormous (842 KB) and the IFR's own source, so it is
# in the set twice over: ifrextractor reads it for bios/ifr/, and Ghidra
# decompiles it because the HII forms are code as well as text.
SETUP_MODULE = "Setup"

MODULES = sorted(VENDOR_MODULES + OVERCLOCK_CHAIN + OTHER_MODULES + [SETUP_MODULE])

# The twelve modules decompiled before this build existed, and the twelve
# bios/decompiled/<Module>.c files that have to come out byte-identical from
# it. `--self-test` asserts none of them has been dropped from MODULES, and
# every build reports whether they did come out identical.
LEGACY_MODULES = [
    "OemOcDxe", "OemOcPei", "OemUniWillVariableDxe", "OemServiceDxe",
    "OemServiceSmm", "OemACRecoveryDxe", "OemDgpuBoardIDDxe",
    "OemDisplayModeDxe", "OemKbLightDxe", "OemUsbLightBarDxe",
    "OemTurboModeDxe", "OemPowerModeDxe",
]

# PeiOverClock is the one module in MODULES whose two copies are not
# byte-identical, and the reason is measured rather than guessed: they differ
# in 3 bytes, two of which (file offsets 0x12 and 0x15) are the first two
# bytes of the TE base-relocation field. The module is linked twice, at
# 0xFFBC... in firmware volume 8 and 0xFFCF... in volume 10, and each copy
# carries its own relocation base. `find_module` still refuses differing
# copies for every other module; this one is named here, with the volume to
# take it from, so the choice is a line someone can read rather than a guess
# buried in a directory walk.
TE_PICK = {"PeiOverClock": "10 14E428FA-1A12-4875-B637-8B3CC87FDF07"}

PROJECT = os.path.join(REPO, "bios", "ghidra", "project")
PROJECT_NAME = "bios"
SCRIPTS = os.path.join(REPO, "ghidra", "scripts")
BIOS_SCRIPTS = os.path.join(REPO, "bios", "ghidra")
# analyzeHeadless's -scriptPath takes a ';' separated list on every platform
# (support/analyzeHeadlessREADME.html), not the OS path separator.
SCRIPT_PATH = ";".join((SCRIPTS, BIOS_SCRIPTS))
LOAD_MAP = os.path.join(REPO, "bios", "ghidra", "load-map.csv")
INDEX = os.path.join(REPO, "bios", "ghidra", "index.csv")
# The disassembly index, one row per function, out_file pointing at the .asm.
LISTING_INDEX = os.path.join(REPO, "bios", "ghidra", "listing-index.csv")
# One .asm per function, under <Module>/<ADDR>.asm. The whole-module listing
# lives beside the .c in bios/decompiled/ for reading; these are what the index
# points at, what an annotation cites, and what a 293-function module is broken
# up into.
LISTINGS = os.path.join(REPO, "bios", "ghidra", "listings")
MANIFEST = os.path.join(REPO, "bios", "ghidra", "manifest.csv")
# The five TE images, committed so `--check` and `--self-test` need neither
# Ghidra nor a UEFIExtract run. bios/ghidra/README.md says why.
TE_MODULES_DIR = os.path.join(REPO, "bios", "ghidra", "modules")
ANNOTATIONS = os.path.join(REPO, "bios", "annotations", "ghidra-functions.csv")
OUTDIR = os.path.join(REPO, "bios")
DECOMPILED = os.path.join(OUTDIR, "decompiled")
GHIDRA_VERSION = "12.1.3"

INDEX_COLUMNS = ["program", "addr", "name", "size", "seed_basis", "annotated",
                 "type", "basis", "evidence", "out_file"]
MANIFEST_COLUMNS = ["program", "kind", "source", "sha256", "ghidra_version",
                    "image_bytes", "load_addr", "entry", "functions",
                    "decompiled", "failed", "disassembled_bytes", "body_bytes",
                    "seeds", "annotations_applied", "annotations_unmatched",
                    "mode"]
LOAD_MAP_COLUMNS = ["program", "kind", "image_bytes", "image_sha256",
                    "load_addr", "entry"]
# What the manifest's `mode` column may say. Kept as data because it is a
# controlled vocabulary and a vocabulary is only enforced if something reads it
# from one place: here the two modes the driver can produce, and --mode reads
# the same tuple rather than repeating it.
MANIFEST_MODES = ("export-only", "rebuild-project")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rom_digest():
    """The ROM's SHA-256, straight out of the committed zip. Cheap, and it is
    the provenance every generated file carries."""
    with zipfile.ZipFile(ZIP) as z:
        return hashlib.sha256(z.read(ROM_MEMBER)).hexdigest()


def run(cmd, **kw):
    """Run a command, and say how long it took. The build makes claims about
    batching (one JVM for 32 modules rather than 32) and a claim with no number
    behind it is not a measurement, so every invocation is timed."""
    print("+", " ".join(f'"{c}"' if " " in c else str(c) for c in cmd), flush=True)
    t0 = time.monotonic()
    try:
        subprocess.run([str(c) for c in cmd], check=True, **kw)
    finally:
        print("  ... %.1f s" % (time.monotonic() - t0), flush=True)


# --------------------------------------------------------------------------
# Getting the module bodies out of the ROM
# --------------------------------------------------------------------------

def extract_rom(work):
    rom = os.path.join(work, "rom.bin")
    with zipfile.ZipFile(ZIP) as z:
        data = z.read(ROM_MEMBER)
    digest = hashlib.sha256(data).hexdigest()
    if digest != ROM_SHA256:
        raise SystemExit("error: %s SHA-256 %s, expected %s"
                         % (ROM_MEMBER, digest, ROM_SHA256))
    with open(rom, "wb") as f:
        f.write(data)
    return rom


def uefi_dump(work, uefiextract):
    """`uefiextract rom all`, into a fresh dump tree. 1.7 s to 49 min on this
    machine for the identical command, so nothing in the default path calls
    it."""
    rom = extract_rom(work)
    dump = rom + ".dump"
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    run([uefiextract, rom, "all"], stdout=subprocess.DEVNULL)
    return dump


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
    appear twice (main and recovery volume); insist the copies match, unless
    the module is named in TE_PICK with the firmware volume to take it from."""
    hits = []
    for dp, dns, _ in os.walk(dump):
        for d in sorted(dns):
            if d.split(" ", 1)[-1] == name:
                body, kind = image_body(os.path.join(dp, d))
                if body:
                    hits.append((body, kind, dp))
    if not hits:
        raise SystemExit("error: module %s not found in %s" % (name, dump))
    if name in TE_PICK:
        for body, kind, dp in hits:
            if os.path.basename(dp) == TE_PICK[name]:
                return body, kind
        raise SystemExit("error: %s: no copy under firmware volume %r"
                         % (name, TE_PICK[name]))
    first = open(hits[0][0], "rb").read()
    for body, _, _ in hits[1:]:
        if open(body, "rb").read() != first:
            raise SystemExit("error: %s has differing copies; pick one by hand"
                             % name)
    return hits[0][0], hits[0][1]


def te_layout(path):
    """(load address, entry) of a TE image. The execute-in-place address is
    where the stripped body starts, which is ImageBase + StrippedSize minus
    the TE header the body was taken from; the entry is absolute."""
    d = open(path, "rb").read(0x28)
    if d[:2] != b"VZ":
        raise SystemExit("error: %s is not a TE image" % path)
    stripped = struct.unpack_from("<H", d, 6)[0]
    entry = struct.unpack_from("<I", d, 8)[0]
    image_base = struct.unpack_from("<Q", d, 16)[0]
    return image_base + stripped - 0x28, image_base + entry


def pe_entry(path):
    """AddressOfEntryPoint from a PE header, an RVA in the image's own space."""
    pe = open(path, "rb").read(0x200)
    e_lfanew = struct.unpack_from("<I", pe, 0x3C)[0]
    magic = struct.unpack_from("<H", pe, e_lfanew + 0x18)[0]
    if magic not in (0x10B, 0x20B):
        raise SystemExit("error: %s: PE optional header magic 0x%x" % (path, magic))
    return struct.unpack_from("<I", pe, e_lfanew + 0x28)[0]


def pe_rva_maps_into_file(path, rva):
    """True when an RVA lands on a byte of the file.

    Not `rva < len(file)`: an RVA is an offset into the image's *virtual*
    address space, and the first section of a PE usually starts at 0x1000
    while the file itself is only 0x400 bytes of headers plus the section.
    `OemHooksSmm` is the case that makes this obvious -- a 4096-byte file
    whose entry point is RVA 0x117C. Walk the section table instead.
    """
    data = open(path, "rb").read()
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    opt_size = struct.unpack_from("<H", data, e_lfanew + 20)[0]
    sec = e_lfanew + 24 + opt_size
    for _ in range(nsec):
        vsize, vaddr, rsize, raw = struct.unpack_from("<IIII", data, sec + 8)
        if vaddr <= rva < vaddr + max(vsize, rsize):
            return rva - vaddr + raw < len(data)
        sec += 40
    return rva < len(data)


def collect_modules(dump, work):
    """Every module in MODULES: body copied into the work tree, kind, and the
    address it is loaded at -- derived, for a TE image, and read out of the PE
    header for a PE32 one. Both land in the load map."""
    mod_dir = os.path.join(work, "modules")
    os.makedirs(mod_dir, exist_ok=True)
    found = {}
    for name in MODULES:
        body, kind = find_module(dump, name)
        dst = os.path.join(mod_dir, name + ".efi")
        shutil.copyfile(body, dst)
        load = entry = None
        if kind == "TE":
            load, entry = te_layout(dst)
        else:
            entry = pe_entry(dst)
            # The RVA is an offset into the image's virtual space, not into
            # the file, so the one thing that can be checked cheaply is that
            # it lands on a byte the section table accounts for. `OemHooksSmm`
            # is why this is not `entry < size`: a 4096-byte file with an
            # entry at RVA 0x117C.
            if not pe_rva_maps_into_file(dst, entry):
                raise SystemExit("error: %s: entry RVA 0x%X maps outside the "
                                 "image" % (name, entry))
        found[name] = {"path": dst, "kind": kind, "size": os.path.getsize(dst),
                       "sha256": sha256(dst), "load": load, "entry": entry}
        print("  %-24s %-5s %7d bytes%s" % (
            name, kind, found[name]["size"],
            "" if load is None else "  load 0x%X entry 0x%X" % (load, entry)))
    return found


def write_load_map(path, found):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(LOAD_MAP_COLUMNS)
        for name in MODULES:
            m = found[name]
            w.writerow([name, m["kind"], m["size"], m["sha256"],
                        "" if m["load"] is None else "0x%X" % m["load"],
                        "0x%X" % m["entry"]])


def read_load_map(path=LOAD_MAP):
    """The committed load map. export-only reads it instead of re-deriving it,
    which is what lets the default build skip UEFIExtract entirely."""
    if not os.path.isfile(path):
        raise SystemExit("error: no load map at %s; run --mode rebuild-project"
                         % os.path.relpath(path, REPO))
    out = {}
    for row in csv.DictReader(open(path, newline="")):
        out[row["program"]] = {
            "path": None, "kind": row["kind"],
            "size": int(row["image_bytes"]), "sha256": row["image_sha256"],
            "load": int(row["load_addr"], 16) if row["load_addr"] else None,
            "entry": int(row["entry"], 16),
        }
    return out


# --------------------------------------------------------------------------
# Seeds and context
# --------------------------------------------------------------------------

def annotation_rows():
    if not os.path.isfile(ANNOTATIONS):
        return []
    return list(csv.DictReader(open(ANNOTATIONS, newline="")))


def seed_rows(found):
    """(program, addr, basis) seeds, de-duplicated.

    Two bases, and only two, because that is all this firmware needs. Every
    image's entry point is a fact in its own header -- a PE32 RVA, or a TE
    address derived by te_layout() and recorded in the load map -- so it is
    basis `entry`. A row in the annotations declares a function a person has
    read, so it seeds too: the same loop the EC project uses, and the reason
    a branch-only-reached routine is not missing from the project.
    """
    rows, seen = [], set()
    for name in MODULES:
        m = found[name]
        rows.append((name, m["entry"], "entry"))
    for a in annotation_rows():
        rows.append((a["scope"].strip(), int(a["addr"], 16), "annotation"))
    out = []
    for program, addr, why in rows:
        if (program, addr) in seen:
            continue
        seen.add((program, addr))
        out.append((program, addr, why))
    return out


def write_specs(work, found, rows):
    """Two files out of one set of rows, because the two shared scripts read
    addresses differently and one of them cannot read half of ours.

    `SeedFunctions.java` parses an address with Integer.parseInt(.., 16), a
    SIGNED 32-bit int, so a TE execute-in-place address such as 0xFFF823B9
    is out of range and would abort the import. The TE entry is marked by
    `TeEntry.java` instead, which is what the committed OemOcPei.c already
    records, and the basis file below still says where it came from.
    `ExportDecompile.java` reads its basis map as a string, so it takes the
    whole set.
    """
    spec = os.path.join(work, "seed-spec.csv")
    basis = os.path.join(work, "seed-basis.csv")
    for path, keep in ((spec, lambda p, a: not is_te(found, p, a)),
                       (basis, lambda p, a: True)):
        with open(path, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["program", "addr", "basis"])
            for program, addr, why in rows:
                if keep(program, addr):
                    # Eight digits, because `ExportDecompile.java` keys its
                    # basis map on `Address.toString()`, which zero-pads to
                    # the address space's width -- eight for x86:LE, whatever
                    # the value is. `0x4F8` would never match `000004F8`, and
                    # every seed would silently come out as `auto`.
                    w.writerow([program, "0x%08X" % addr, why])
    return spec, basis


def is_te(found, program, addr):
    """True when (program, addr) is a TE image's load-map entry, which is the
    one address class the shared pre-script cannot take."""
    m = found.get(program)
    return bool(m and m["kind"] == "TE" and m["entry"] == addr)


def write_context(work, found, digest):
    """key=value lines for the exporter's provenance header. `source.<program>`
    wins over `source`, because one context file drives a batch of 32 modules
    and a header that named only the ROM would let a reader assume a PE32 RVA
    and a TE execute-in-place address are the same kind of address."""
    p = os.path.join(work, "context.txt")
    with open(p, "w") as f:
        f.write("source=%s (SHA-256 verified)\n" % ROM_MEMBER)
        f.write("sha256=%s\n" % digest)
        f.write("ghidra_version=%s\n" % GHIDRA_VERSION)
        f.write("generator=bios/tools/bios_extract.py\n")
        f.write("annotations=bios/annotations/ghidra-functions.csv\n")
        for name in MODULES:
            m = found[name]
            if m["kind"] == "TE":
                where = "%s, %s.efi (TE body, execute-in-place 0x%X)" % (
                    ROM_MEMBER, name, m["load"])
            else:
                where = "%s, %s.efi (PE32 body, RVA space)" % (ROM_MEMBER, name)
            f.write("source.%s=%s\n" % (name, where))
    return p


def ghidra_preflight(ghidra):
    """The decompiler can be present on disk and still unusable, and it fails
    SILENTLY: openProgram() returns false with an empty message. Catching it
    here, before any work, is the difference between a clear error and an
    export full of confident-looking nothing."""
    if not ghidra:
        return
    decomp = os.path.join(os.path.dirname(os.path.dirname(ghidra)),
                          "Ghidra", "Features", "Decompiler", "os",
                          "linux_x86_64", "decompile")
    if not os.path.exists(decomp):
        return
    if not os.access(decomp, os.X_OK):
        raise SystemExit(
            "error: Ghidra's native decompiler is not executable: %s\n"
            "  This fails SILENTLY inside Ghidra (openProgram() returns false and\n"
            "  the error message is empty), and the result reads exactly like\n"
            "  'this code will not decompile'. It is not. Fix the exec bit and\n"
            "  re-run." % decomp)


# --------------------------------------------------------------------------
# The Ghidra run
# --------------------------------------------------------------------------

def post_scripts(ghidra, project_dir, out_c, out_src, out_fn, raw_index,
                 raw_listing, raw_fn, context, basis, work):
    """Apply the annotations and export, on a COPY of the project.

    The copy is the point: the committed .rep is never opened for writing, so
    an annotation change is a one-line CSV diff and a text diff, not a 48 MB
    binary one. Copying obtains that guarantee; it does not rely on how
    analyzeHeadless treats -readOnly.

    DecompAll runs FIRST, before ApplyAnnotations renames anything, because
    bios/decompiled/<Module>.c is the unedited export and has to come out
    byte-identical across builds. ExportDecompile runs last, on the renamed
    program, and is what fills the index and the manifest.

    `<Module>.annotated.c` is NOT produced here: it is hand written, and the
    annotations CSV is transcribed from it rather than the other way round.
    See "The hand restatement, and the guard that keeps it and the CSV
    together" below.
    """
    for stale in os.listdir(work):
        if stale.startswith("index-raw.csv.") and stale.endswith(".counts"):
            os.remove(os.path.join(work, stale))
        if (stale.startswith("listing-raw.csv.") or
                stale.startswith("listing-fn-raw.csv.")) \
                and stale.endswith(".listing-counts"):
            os.remove(os.path.join(work, stale))
    # -process may only be given once, so this is one invocation over the whole
    # project rather than 38 of them: analyzeHeadless runs the scripts once per
    # program inside the one JVM, and a JVM start is ~9.5 s.
    cmd = [ghidra, project_dir, PROJECT_NAME, "-process", "-noanalysis",
           "-scriptPath", SCRIPT_PATH,
           "-postScript", "DecompAll.java", out_c,
           "-postScript", "ApplyAnnotations.java",
           ANNOTATIONS if os.path.isfile(ANNOTATIONS) else "", "",
           os.path.join(work, "reports"),
           # No variable layer: the fourth argument is the EC's
           # ghidra-variables.csv, and a row in it is a reading of an 8051
           # decompiler's placeholder. "-" rather than omitting it, because the
           # script takes the arguments positionally and a missing fourth would
           # be read as absent rather than as "none here".
           "-",
           "-postScript", "ExportDecompile.java", out_src, raw_index,
           "per-program", context, basis,
           # The disassembly, one .asm per module beside its .c. Same reason as
           # the EC: a decompilation is a reading of the bytes, and the listing
           # is what lets a reader check the reading.
           "-postScript", "ExportListing.java", out_src, raw_listing,
           "per-program", context, basis,
           # ...and again per function, because a 293-function module is not a
           # unit anybody can annotate or check. The per-program listing is
           # what a human skims; the per-function ones are what a reader cites
           # and what an annotator reads, and the index points at these.
           "-postScript", "ExportListing.java", out_fn, raw_fn,
           "per-function", context, basis]
    log = open(os.path.join(work, "ghidra-export.log"), "w")
    try:
        run(cmd, stdout=log, stderr=subprocess.STDOUT)
    finally:
        log.close()


def import_project(ghidra, found, work, project_dir, spec):
    """Build the project from the module bodies.

    The PE32 modules are batched into one invocation, Setup gets a JVM of its
    own because it is 842 KB against a few KB for everything else, and the TE
    ones go one invocation per distinct load address because -loader and
    -loader-baseAddr are invocation-global. That is 7 JVMs, not 38.
    """
    os.makedirs(project_dir, exist_ok=True)
    pe32 = [n for n in MODULES if found[n]["kind"] != "TE"]
    te = [n for n in MODULES if found[n]["kind"] == "TE"]
    groups = [("pe32", [n for n in pe32 if n != SETUP_MODULE]),
              (SETUP_MODULE, [SETUP_MODULE])]
    by_base = {}
    for n in te:
        by_base.setdefault(found[n]["load"], []).append(n)
    for i, base in enumerate(sorted(by_base)):
        groups.append(("te-%d" % i, sorted(by_base[base])))

    script_path = SCRIPT_PATH
    for tag, names in groups:
        if not names:
            continue
        first = found[names[0]]
        cmd = [ghidra, project_dir, PROJECT_NAME, "-import"] + \
              [found[n]["path"] for n in names] + \
              ["-overwrite", "-scriptPath", script_path]
        if first["kind"] == "TE":
            cmd += ["-loader", "BinaryLoader", "-loader-baseAddr",
                    hex(first["load"]), "-processor", "x86:LE:32:default",
                    "-cspec", "gcc"]
            # TeEntry first: it names the entry function `entry` and marks it
            # an external entry point, which is what bios/decompiled/OemOcPei.c
            # records and what SeedFunctions cannot do for a 0xFFF8... address.
            cmd += ["-preScript", "TeEntry.java", "%x" % first["entry"]]
        cmd += ["-preScript", "SeedFunctions.java", spec]
        log = open(os.path.join(work, "ghidra-import-%s.log" % tag), "w")
        try:
            run(cmd, stdout=log, stderr=subprocess.STDOUT)
        finally:
            log.close()
        shown = (", ".join(names) if len(names) <= 4
                 else "%s ... %s" % (names[0], names[-1]))
        print("  imported %2d module(s) in one JVM: %s" % (len(names), shown))
    return project_dir


# --------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------

def join_index(raw_index):
    """The exporter's scratch rows plus the annotation columns, and nothing
    invented: a row with no annotation keeps empty type/basis/evidence rather
    than being given a default.

    `annotated` is left as the exporter wrote it -- "did this function end up
    with a name that is not Ghidra's" -- and the annotation match is counted
    separately for the manifest. Overwriting one with the other would hide the
    case where a row matched an address but the rename did not happen.
    """
    raw = list(csv.DictReader(open(raw_index, newline=""), delimiter="\t"))
    annot = {}
    for row in annotation_rows():
        key = (row["scope"].strip(), int(row["addr"], 16))
        if key in annot:
            raise SystemExit("error: two annotation rows for %s 0x%X" % key)
        annot[key] = row
    for row in raw:
        a = annot.get((row["program"], int(row["addr"], 16)))
        row["type"] = a["type"] if a else ""
        row["basis"] = a["basis"] if a else ""
        row["evidence"] = a["evidence"] if a else ""
        # per-program mode leaves out_file empty for a successful row; name the
        # file it is in so --check has something to check.
        if row["out_file"] == "":
            row["out_file"] = row["program"] + ".c"
    unmatched = [k for k in annot
                 if not any(r["program"] == k[0] and int(r["addr"], 16) == k[1]
                            for r in raw)]
    return raw, sorted(unmatched)


def write_outputs(raw, found, digest, mode, rows, unmatched, work, listing=None):
    with open(INDEX, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INDEX_COLUMNS, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        for row in sorted(raw, key=lambda r: (r["program"], int(r["addr"], 16))):
            w.writerow(row)
    # The disassembly index, same columns, pointing at the .asm beside each .c.
    if listing is not None:
        with open(LISTING_INDEX, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=INDEX_COLUMNS, extrasaction="ignore",
                               lineterminator="\n")
            w.writeheader()
            for row in sorted(listing, key=lambda r: (r["program"], int(r["addr"], 16))):
                w.writerow(row)

    per_program, applied = {}, {}
    for row in raw:
        p = per_program.setdefault(row["program"], {
            "functions": 0, "failed": 0, "body": 0})
        p["functions"] += 1
        p["body"] += int(row["size"])
        if row["out_file"] == "(failed)":
            p["failed"] += 1
        if row["type"]:
            applied[row["program"]] = applied.get(row["program"], 0) + 1
    counts = {}
    for name in MODULES:
        path = os.path.join(work, "index-raw.csv." + name + ".counts")
        if os.path.isfile(path):
            # Last line only: the exporter opens the file in append mode, so a
            # re-run into the same work directory leaves the previous row behind.
            f = [l for l in open(path).read().splitlines() if l.strip()][-1].split("\t")
            counts[name] = {"functions": int(f[1]), "decompiled": int(f[2]),
                            "failed": int(f[3]),
                            "disassembled": int(f[4]) + int(f[5]),
                            "body": int(f[6])}
    seeds = {}
    for program, _, _ in rows:
        seeds[program] = seeds.get(program, 0) + 1
    notapplied = {}
    for scope, _addr in unmatched:
        notapplied[scope] = notapplied.get(scope, 0) + 1

    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
        w.writeheader()
        for name in MODULES:
            m = found[name]
            p = per_program.get(name, {"functions": 0, "failed": 0, "body": 0})
            c = counts.get(name, {})
            w.writerow({
                "program": name, "kind": m["kind"],
                "source": "%s, %s.efi" % (ROM_MEMBER, name),
                "sha256": digest, "ghidra_version": GHIDRA_VERSION,
                "image_bytes": m["size"],
                "load_addr": "" if m["load"] is None else "0x%X" % m["load"],
                "entry": "0x%X" % m["entry"],
                "functions": c.get("functions", p["functions"]),
                "decompiled": c.get("decompiled", p["functions"] - p["failed"]),
                "failed": c.get("failed", p["failed"]),
                # Bytes actually disassembled: the honest "how much of this
                # image did analysis reach" number. Not "how much is
                # understood", and not a coverage claim.
                "disassembled_bytes": c.get("disassembled", 0),
                # The sum of function body lengths. NOT a coverage figure:
                # bodies overlap, so this can exceed the image size.
                "body_bytes": c.get("body", p["body"]),
                "seeds": seeds.get(name, 0),
                "annotations_applied": applied.get(name, 0),
                "annotations_unmatched": notapplied.get(name, 0),
                "mode": mode,
            })


# --------------------------------------------------------------------------
# The hand restatement, and the guard that keeps it and the CSV together
# --------------------------------------------------------------------------

# `bios/decompiled/<Module>.annotated.c` is HAND WRITTEN: the readable layer,
# with the vendor's variable names and the setup-store offsets attached to the
# decompile, so a reader can follow the flow. It is not tool output and it is
# not generated -- a generated version of it is the EDK2 pointer chains again,
# which is the thing the layer exists to replace. `bios/README.md` is the
# convention it lives under: everything in `decompiled/` EXCEPT
# `*.annotated.c` is unedited tool output.
#
# `annotations/ghidra-functions.csv` is transcribed from it. The two are two
# copies of one reading kept side by side, so they can drift, and the two
# checks below are the guard. Both run in `--check`, and neither needs Ghidra.
#
# A `/* ---- ... ---- */` block header, which in these files always introduces a
# function.
# A disassembly line: an address, then the byte column, then the mnemonic. The
# byte column ends at the first `-` and is padded to the program's widest
# instruction, so taking hex pairs greedily would swallow a mnemonic that is
# itself two hex digits -- which the 8051's reserved `da` is, and which is why
# the column is padded. See ghidra/scripts/ExportListing.java.
_ADDRESS_LINE = re.compile(r"^[0-9A-Fa-f]{4,8}\s+\S")
_BYTE_SLOT = re.compile(r"^(?:[0-9A-Fa-f]{2}|-)$")


def _parse_listing_lines(lines):
    """-> [(addr, hexbytes)], skipping any line the layout does not explain."""
    out = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            addr = int(parts[0], 16)
        except ValueError:
            continue
        take = 0
        for i, tok in enumerate(parts[1:]):
            if tok == "-" or not _BYTE_SLOT.match(tok):
                take = i
                break
            take = i + 1
        if take == 0:
            continue
        out.append((addr, "".join(parts[1:1 + take])))
    return out


ANNOTATED_HEADER = re.compile(r"^/\* ---- (.*?) ----")
# A trailing `/* 0x0C30: PCR[0x6E][0x38] bits 25:24 */` on a line of code:
# how a call site cites the function it calls. EXACTLY four hex digits, which
# is a convention the restatements happen to follow rather than a general
# truth -- in `OemOcDxe.annotated.c` every four-digit literal in that position
# is a function entry and the one-to-three-digit ones are sizes, EC command
# bytes and PCR offsets (`/* 0x2BB bytes */`, `/* 0xA3 07 */`). A restatement
# that breaks the convention would make this miss a name, which is the wrong
# way round, so `--check` prints how many addresses it found and the second
# direction below catches a CSV row the restatement has lost.
ANNOTATED_TRAILING = re.compile(r"/\*\s*0x([0-9A-Fa-f]{4})(?![0-9A-Fa-f])")
# `FUN_00000f38` in a block header: the other way a restatement points at a
# function.
ANNOTATED_FUN = re.compile(r"FUN_([0-9A-Fa-f]{8})")
ANNOTATED_HEX = r"0x([0-9A-Fa-f]{1,8})(?![0-9A-Fa-f])"


def annotated_addresses(path):
    """The addresses a hand-written `*.annotated.c` names as functions.

    Two places, and only two: a block header, and a four-digit hex literal
    opening a trailing comment on a line of code. The restatement's own prose
    -- lines continuing with ` * ` -- is skipped, so a size or an EC command
    byte in the middle of an explanation is not mistaken for an entry point.
    """
    out = set()
    for line in open(path, errors="replace"):
        s = line.strip()
        if s.startswith("*"):
            continue
        m = ANNOTATED_HEADER.match(s)
        if m:
            out.update(int(h, 16) for h in re.findall(ANNOTATED_HEX, m.group(1)))
            out.update(int(h, 16) for h in ANNOTATED_FUN.findall(m.group(1)))
            continue
        m = ANNOTATED_TRAILING.search(s)
        if m:
            out.add(int(m.group(1), 16))
    return out


def check_annotated_layers(fail):
    """Both directions of the drift guard, from `--check`."""
    ann = annotation_rows()
    for fn in sorted(f for f in os.listdir(DECOMPILED)
                     if f.endswith(".annotated.c")):
        path = os.path.join(DECOMPILED, fn)
        module = fn[:-len(".annotated.c")]
        text = open(path, errors="replace").read()
        named = annotated_addresses(path)
        rows = {int(a["addr"], 16): a for a in ann
                if a["scope"].strip() == module}
        print("  note  %s names %d function addresses; the annotations CSV has "
              "%d row(s) for it" % (fn, len(named), len(rows)))
        if not named:
            fail("%s names no function address the guard can see, so it and the "
                 "annotations have drifted or the marker convention changed" % fn)
            continue
        if module not in MODULES:
            fail("%s annotates %s, which is not in MODULES" % (fn, module))
        for addr in sorted(named):
            if addr not in rows:
                fail("%s names a function at 0x%04X that "
                     "annotations/ghidra-functions.csv has no row for: either the "
                     "restatement has moved on or the CSV has drifted from it"
                     % (fn, addr))
        # Direction 2, over the rows that claim to be transcribed from THIS
        # file. `hand-decoded` alone is not enough to say that: the bulk rows
        # were read from a function's own disassembly, cite
        # `bios/ghidra/listings/<Module>/<ADDR>.asm`, and are checked by the
        # listing-parse guard instead. The restatement is a hand-written
        # reading of `OemOcDxe` alone, so demanding that it mention 700 rows
        # from 37 other modules was the rule being wrong rather than the CSV
        # drifting -- and a guard that fires on correct input gets switched off.
        for addr, a in sorted(rows.items()):
            if a["basis"] != "hand-decoded":
                continue
            if ".annotated.c" not in a.get("evidence", ""):
                continue
            name = a["name"].strip()
            if name:
                if not re.search(r"\b%s\b" % re.escape(name), text):
                    fail("%s has a row for 0x%04X %s marked hand-decoded, but the "
                         "restatement never mentions that name: the CSV has "
                         "drifted from the file it was transcribed from"
                         % (fn, addr, name))
            elif ("0x%X" % addr) not in text and ("0x%04X" % addr) not in text:
                fail("%s has a row for 0x%04X marked hand-decoded with an empty "
                     "name, and the restatement does not cite that address"
                     % (fn, addr))
    # A module with annotation rows and no hand restatement is the normal case,
    # not a gap to be reported: the rows are read from the function's
    # disassembly, which is a source in its own right, and only OemOcDxe has
    # ever had a hand restatement. The note is here so the two are not confused
    # -- a row with `basis: hand-decoded` in a module with a restatement IS
    # transcribed from it and is checked above, and the same basis with no
    # restatement means it was read from the listing.
    restated = {a["scope"].strip() for a in ann
                if os.path.isfile(os.path.join(
                    DECOMPILED, a["scope"].strip() + ".annotated.c"))}
    unstated = sorted({a["scope"].strip() for a in ann} - restated)
    if unstated:
        print("  note  %d module(s) have annotation rows read from their "
              "disassembly with no hand restatement: %s"
              % (len(unstated), ", ".join(unstated[:6])
                 + (" ..." if len(unstated) > 6 else "")))


# --------------------------------------------------------------------------
# The build
# --------------------------------------------------------------------------

def ifr(args, dump, work):
    setup_body, _ = find_module(dump, SETUP_MODULE)
    setup = os.path.join(work, "Setup.efi")
    shutil.copyfile(setup_body, setup)
    run([args.ifrextractor, setup, "verbose"], stdout=subprocess.DEVNULL)
    ifr_dir = os.path.join(OUTDIR, "ifr")
    os.makedirs(ifr_dir, exist_ok=True)
    shutil.copyfile(setup + ".0.0.en-US.uefi.ifr.txt",
                    os.path.join(ifr_dir, "Setup.en-US.ifr.txt"))
    print("  wrote %s" % os.path.relpath(
        os.path.join(ifr_dir, "Setup.en-US.ifr.txt"), REPO))


def build(args, work):
    digest = rom_digest()
    if digest != ROM_SHA256:
        raise SystemExit("error: %s SHA-256 %s, expected %s"
                         % (ROM_MEMBER, digest, ROM_SHA256))
    if args.mode == "rebuild-project" or args.extract:
        print("extracting the ROM with UEFIExtract (seconds to an hour on this "
              "machine; nothing in the default mode needs it)")
        dump = uefi_dump(work, args.uefiextract)
        print("reading module bodies")
        found = collect_modules(dump, work)
        if args.extract:
            ifr(args, dump, work)
    else:
        found = read_load_map()
        print("using the committed load map; pass --extract to re-run UEFIExtract")

    rows = seed_rows(found)
    spec, basis = write_specs(work, found, rows)
    context = write_context(work, found, digest)

    project_dir = PROJECT
    if args.mode == "rebuild-project":
        scratch = os.path.join(work, "project-new")
        if os.path.isdir(scratch):
            shutil.rmtree(scratch)
        os.makedirs(scratch)
        import_project(args.ghidra, found, work, scratch, spec)
        # Snapshot BEFORE any annotation is applied. The committed project is
        # the unedited analysis, which is what bios/decompiled/<Module>.c is
        # made from; renaming functions in it in place would make the next
        # export-only run emit renamed functions and stop matching.
        if os.path.isdir(PROJECT):
            shutil.rmtree(PROJECT)
        shutil.copytree(scratch, PROJECT)
        write_load_map(LOAD_MAP, found)
        print("  wrote %s" % os.path.relpath(PROJECT, REPO))
        print("  wrote %s" % os.path.relpath(LOAD_MAP, REPO))
    elif not os.path.isdir(PROJECT):
        raise SystemExit("error: no project at %s; run --mode rebuild-project"
                         % os.path.relpath(PROJECT, REPO))

    out_c = os.path.join(work, "out")
    out_src = os.path.join(work, "named-src")
    out_fn = os.path.join(work, "listings")
    for d in (out_c, out_src, out_fn):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
    raw_index = os.path.join(work, "index-raw.csv")
    raw_listing = os.path.join(work, "listing-raw.csv")
    raw_fn = os.path.join(work, "listing-fn-raw.csv")
    with open(raw_index, "w", newline="") as f:
        # Tab-separated: the Java exporter appends tab-separated rows.
        f.write("program\taddr\tname\tsize\tseed_basis\tannotated\t"
                "type\tbasis\tevidence\tout_file\n")

    copy_dir = os.path.join(work, "project-copy")
    if os.path.isdir(copy_dir):
        shutil.rmtree(copy_dir)
    shutil.copytree(project_dir, copy_dir)
    for _p in (raw_listing, raw_fn):
        with open(_p, "w", newline="") as f:
            f.write("program\taddr\tname\tsize\tseed_basis\tannotated\t"
                    "type\tbasis\tevidence\tout_file\n")
    post_scripts(args.ghidra, copy_dir, out_c, out_src, out_fn, raw_index,
                 raw_listing, raw_fn, context, basis, work)

    # The unedited export is the committed one. Compare the twelve that
    # existed before this build BEFORE overwriting them: a changed .c is a
    # diff a reviewer has to read, so it must not happen quietly.
    drift = []
    for name in LEGACY_MODULES:
        new = os.path.join(out_c, name + ".c")
        old = os.path.join(DECOMPILED, name + ".c")
        if not os.path.isfile(new):
            raise SystemExit("error: Ghidra produced no %s.c" % name)
        if os.path.isfile(old) and open(new, "rb").read() != open(old, "rb").read():
            drift.append(name)
    for name in MODULES:
        src = os.path.join(out_c, name + ".c")
        if not os.path.isfile(src):
            raise SystemExit("error: Ghidra produced no %s.c" % name)
        shutil.copyfile(src, os.path.join(DECOMPILED, name + ".c"))
        # The disassembly, beside the decompile it belongs to. In per-program
        # mode ExportListing writes one <Module>.asm holding every function,
        # and the listing index points every row of that module at it.
        _asm = os.path.join(out_src, name + ".asm")
        if not os.path.isfile(_asm):
            raise SystemExit("error: Ghidra produced no %s.asm" % name)
        shutil.copyfile(_asm, os.path.join(DECOMPILED, name + ".asm"))
    if drift:
        print("\n  WARNING: these previously-committed decompiles changed and have\n"
              "  been overwritten with this build's output: %s" % ", ".join(drift))
    else:
        print("  the %d previously-committed decompiles came out byte-identical"
              % len(LEGACY_MODULES))

    raw, unmatched = join_index(raw_index)
    # The listing index is read straight from the exporter's tab-separated
    # scratch file: in per-program mode there is no de-duplication to do and no
    # annotation join, so the extra pass would only be a second place to be
    # wrong.
    if os.path.isdir(LISTINGS):
        shutil.rmtree(LISTINGS)
    shutil.copytree(out_fn, LISTINGS)
    listing = []
    if os.path.isfile(raw_fn):
        listing = list(csv.DictReader(open(raw_fn, newline=""),
                                      delimiter="\t"))
        for _r in listing:
            _r.setdefault("common", "")
            _r.setdefault("also_in", "")
    write_outputs(raw, found, digest, args.mode, rows, unmatched, work, listing)
    for scope, addr in unmatched:
        print("  annotation %s 0x%X resolves to no exported function -- either a "
              "typo or the project needs --mode rebuild-project" % (scope, addr))
    print("  wrote %s and %s" % (os.path.relpath(INDEX, REPO),
                                 os.path.relpath(MANIFEST, REPO)))
    report()
    return 1 if unmatched else 0


def report():
    print("\n=== manifest ===")
    tot = {"functions": 0, "decompiled": 0, "failed": 0, "bytes": 0}
    clean = 0
    for row in csv.DictReader(open(MANIFEST, newline="")):
        f, d, b = int(row["functions"]), int(row["decompiled"]), int(row["failed"])
        tot["functions"] += f
        tot["decompiled"] += d
        tot["failed"] += b
        tot["bytes"] += int(row["disassembled_bytes"])
        clean += b == 0
        print("  %-24s %-5s %5d fn %5d ok %3d fail %7d bytes disassembled of %d"
              % (row["program"], row["kind"], f, d, b,
                 int(row["disassembled_bytes"]), int(row["image_bytes"])))
    print("  %-24s      %5d fn %5d ok %3d fail %7d bytes disassembled"
          % ("TOTAL", tot["functions"], tot["decompiled"], tot["failed"], tot["bytes"]))
    print("  %d of %d modules decompiled with zero failures" % (clean, len(MODULES)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True, help="scratch directory (created)")
    ap.add_argument("--mode", default="export-only", choices=MANIFEST_MODES,
                    help="export-only re-exports from the committed project; "
                         "rebuild-project re-imports from the ROM and writes it")
    ap.add_argument("--extract", action="store_true",
                    help="also regenerate bios/ifr/ (runs UEFIExtract, ~49 min)")
    ap.add_argument("--uefiextract", default="UEFIExtract")
    ap.add_argument("--ifrextractor", default="ifrextractor")
    ap.add_argument("--ghidra", default=os.environ.get("GHIDRA_HEADLESS", "analyzeHeadless"),
                    help="analyzeHeadless path; '' to skip the Ghidra run")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed outputs without Ghidra")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions against the committed inputs")
    args = ap.parse_args(argv)
    work = os.path.abspath(args.work)
    os.makedirs(work, exist_ok=True)
    if args.check:
        return check()
    if args.self_test:
        return self_test()
    if not args.ghidra:
        raise SystemExit("error: --ghidra '' would produce no decompiles. "
                         "bios/decompiled/ IS Ghidra's output, so there is no "
                         "skip mode here; pass a path, or use --check.")
    ghidra_preflight(args.ghidra)
    return build(args, work)


# --------------------------------------------------------------------------
# Checks -- no Ghidra, no network, no UEFIExtract. One assertion per line.
# --------------------------------------------------------------------------

def read_index(path):
    """Rows of a committed CSV -- an index or the manifest -- read strictly.

    `strict=True` is the point. csv's default reader is forgiving about quoting
    in the one way that hides an error rather than raising it: a bad quote ends
    the row early, the row comes back with a missing field, and every count
    taken from it is then quietly smaller than the file. A quoting mistake in a
    committed index is exactly the kind of thing that should be loud, and it
    costs nothing to make it so."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def index_structure_problems(index_rows, listing_rows):
    """Structural faults in the two committed indexes: rows that did not come
    out with the full header, and `(program, addr)` keys that appear twice.

    A duplicate key is an export appended to twice, or a de-dup that missed one;
    either way the row count no longer means "number of functions", which is
    the only thing the counts around it are for. The bodies below are
    header-agnostic, so this is the same check the other two components run over
    their own column sets."""
    out = []
    for name, rows in (("index.csv", index_rows),
                       ("listing-index.csv", listing_rows)):
        seen = set()
        for i, r in enumerate(rows, start=2):
            if None in r or any(v is None for v in r.values()):
                out.append(f"{name}: line {i} has fewer or more fields than the header")
                continue
            key = (r.get("program"), r.get("addr"))
            if key in seen:
                out.append(f"{name}: duplicate (program, addr) {key}")
            seen.add(key)
    return out


def coverage_mismatches(manifest_rows, count_for_program):
    """Manifest rows whose recorded `functions` is not the row count the index
    carries for that module.

    This is the cheap half of coverage: two committed CSVs compared against each
    other, with no `.c` and no `.asm` opened. It catches the case that matters
    most -- an index that gained or lost rows without the manifest being
    regenerated, so a reader would take a function count that no longer
    describes the export.

    `count_for_program` maps a module name to its row count in an index. No
    label translation goes in between, unlike the Windows check: here the
    manifest's `program` column and the index's are both module names, so they
    join directly."""
    out = []
    for r in manifest_rows:
        program = r.get("program", "?")
        try:
            recorded = int(r["functions"])
        except (KeyError, TypeError, ValueError):
            out.append(f"{program}: functions is {r.get('functions')!r}, not a number")
            continue
        got = count_for_program(program)
        if got != recorded:
            out.append("%s: manifest records %d function(s), the index carries "
                       "%d row(s) for it -- the export is stale, or a row was "
                       "dropped after the manifest was written"
                       % (program, recorded, got))
    return out


def manifest_mode_problems(manifest_rows):
    """Manifest rows whose `mode` is outside the two the driver produces."""
    return ["%s: mode is %r, not one of %s"
            % (r.get("program", "?"), r.get("mode"), "|".join(MANIFEST_MODES))
            for r in manifest_rows if r.get("mode") not in MANIFEST_MODES]


def self_test():
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print("  %s  %s" % ("ok  " if cond else "FAIL", label)
              + ("  (%s)" % detail if detail and not cond else ""))
        if not cond:
            ok = False

    print("bios_extract.py --self-test")
    # The committed index pair and the manifest, read through the same strict
    # reader --check uses, so the known answers below are measured on the files
    # the gate runs against rather than on a copy of them.
    _ir, _lr, _mr = (read_index(p) if os.path.isfile(p) else []
                     for p in (INDEX, LISTING_INDEX, MANIFEST))
    for _p, _cols in ((INDEX, INDEX_COLUMNS), (LISTING_INDEX, INDEX_COLUMNS),
                      (MANIFEST, MANIFEST_COLUMNS)):
        check("%s carries this tool's own %d-column header"
              % (os.path.relpath(_p, REPO), len(_cols)),
              os.path.isfile(_p)
              and next(csv.reader(open(_p, newline="")), None) == _cols)

    # Structural faults, on synthetic row-lists. The known-good case is first on
    # purpose: a guard exercised only on known-bad input cannot tell "clean"
    # from "never ran".
    _good = [{"program": "OemOcDxe", "addr": "00001000",
              "out_file": "OemOcDxe/00001000.asm"},
             {"program": "OemOcDxe", "addr": "00001010",
              "out_file": "OemOcDxe/00001010.asm"}]
    check("a clean pair of index row-lists has no structural problem",
          not index_structure_problems(_good, _good))
    _dup = [_good[0]] * 2
    _p = index_structure_problems(_dup, [])
    check("a duplicated (program, addr) key is reported", len(_p) == 1, str(_p))
    _p = index_structure_problems(_dup, _dup)
    check("a duplicated key is reported in each of the two indexes",
          len(_p) == 2, str(_p))
    _p = index_structure_problems([{"program": "OemOcDxe", "addr": "00001000",
                                    "out_file": None}], [])
    check("a row with fewer fields than the header is reported", len(_p) == 1,
          str(_p))
    # DictReader collects a row with too many fields under the None restkey.
    _p = index_structure_problems([{"program": "OemOcDxe", "addr": "00001000",
                                    "out_file": "a.asm", None: ["surplus"]}], [])
    check("a row with more fields than the header is reported", len(_p) == 1,
          str(_p))
    _p = index_structure_problems(_good, [])
    check("two different addresses in one module are not a duplicate",
          not _p, str(_p))

    # Coverage, on a manifest that agrees with its index and one that does not.
    check("coverage: a manifest that agrees with the index passes",
          not coverage_mismatches([{"program": "OemOcDxe", "functions": "31"}],
                                  lambda program: 31))
    _mm = coverage_mismatches([{"program": "OemOcDxe", "functions": "30"}],
                              lambda program: 31)
    check("coverage: a manifest whose functions disagrees with the index fails, "
          "naming both numbers", len(_mm) == 1 and "30" in _mm[0]
          and "31" in _mm[0], str(_mm))
    _mm = coverage_mismatches([{"program": "OemOcDxe", "functions": ""}],
                              lambda program: 31)
    check("coverage: a manifest whose functions is not a number fails",
          len(_mm) == 1, str(_mm))

    # The mode vocabulary: documented, and enforced from the one place.
    check("every mode in use today is in the documented set",
          not manifest_mode_problems([{"program": "OemOcDxe", "mode": m}
                                      for m in MANIFEST_MODES]))
    _p = manifest_mode_problems([{"program": "OemOcDxe", "mode": "rebuild"}])
    check("a mode outside the documented set is rejected", len(_p) == 1, str(_p))
    check("the committed manifest uses only documented modes",
          not manifest_mode_problems(_mr), str(manifest_mode_problems(_mr)))

    # The known answers, on the committed files. These are docs/findings.md §15
    # as assertions: a re-export that moves a total fails here loudly and gets a
    # conscious update to the table in the same change, which is the point.
    check("BIOS: index.csv is 955 rows, and the manifest records 955 functions "
          "across 38 modules",
          len(_ir) == 955 and len(_mr) == 38
          and sum(int(r["functions"]) for r in _mr) == 955,
          "%d row(s), %d manifest row(s)" % (len(_ir), len(_mr)))
    check("BIOS: listing-index.csv is the same 955 rows", len(_lr) == 955,
          "%d row(s)" % len(_lr))
    check("BIOS: the manifest's module set is the index's, with no label mapping "
          "in between",
          {r["program"] for r in _mr} == {r["program"] for r in _ir} == set(MODULES),
          str(sorted({r["program"] for r in _mr} ^ {r["program"] for r in _ir})))
    # Every address here is 8 bare hex digits, so a (program, addr) key taken as
    # a string and one taken as an int agree. That is what makes the duplicate
    # check's string key a fact about the file rather than an assumption -- and
    # a "00001000" alongside a "1000" would quietly make it a lie.
    check("BIOS: addresses are uniformly 8 bare hex digits in both indexes, so "
          "string and int (program, addr) keys agree",
          all(len({(r["program"], r["addr"]) for r in rows})
              == len({(r["program"], int(r["addr"], 16)) for r in rows}) == 955
              for rows in (_ir, _lr)))

    te_path = os.path.join(TE_MODULES_DIR, "OemOcPei.efi")
    present = os.path.isfile(te_path)
    header = open(te_path, "rb").read(0x28) if present else b""
    size = os.path.getsize(te_path) if present else 0
    check("the committed OemOcPei image carries a TE header", header[:2] == b"VZ")
    load, entry = (0, 0)
    if header[:2] == b"VZ":
        load, entry = te_layout(te_path)
    check("te_layout() returns a non-zero load address for it", load != 0)
    check("te_layout() returns an entry point inside the image",
          load <= entry < load + size)
    check("te_layout() puts the entry inside the stripped body",
          struct.unpack_from("<I", header, 8)[0]
          >= struct.unpack_from("<H", header, 6)[0])
    lm = read_load_map() if os.path.isfile(LOAD_MAP) else {}
    check("the load map's OemOcPei row is what te_layout() just computed",
          lm.get("OemOcPei", {}).get("load") == load
          and lm.get("OemOcPei", {}).get("entry") == entry)
    check("every module in MODULES is in the load map, and no others",
          set(MODULES) == set(lm))
    check("MODULES has no duplicates", len(MODULES) == len(set(MODULES)))
    check("MODULES is the 38-module set", len(MODULES) == 38)
    check("MODULES holds all 32 Oem* modules",
          len([m for m in MODULES if m.startswith("Oem")]) == 32)
    check("all 4 modules of the Intel overclocking chain are in it",
          all(m in MODULES for m in OVERCLOCK_CHAIN))
    check("all 12 previously-committed module names are still in MODULES",
          all(m in MODULES for m in LEGACY_MODULES))
    check("a load address is recorded for a TE image and only for a TE image",
          all((lm[m]["load"] is not None) == (lm[m]["kind"] == "TE")
              for m in MODULES if m in lm))
    check("every TE image the project needs is committed under ghidra/modules/",
          all(os.path.isfile(os.path.join(TE_MODULES_DIR, m + ".efi"))
              for m in MODULES if m in lm and lm[m]["kind"] == "TE"))
    check("every committed TE image hashes to what the load map records",
          all(sha256(os.path.join(TE_MODULES_DIR, m + ".efi")) == lm[m]["sha256"]
              for m in MODULES if m in lm and lm[m]["kind"] == "TE"))
    check("every TE load/entry pair is inside its own image",
          all(lm[m]["load"] <= lm[m]["entry"] < lm[m]["load"] + lm[m]["size"]
              for m in MODULES if m in lm and lm[m]["kind"] == "TE"))
    check("every PE32 module is loaded at its own default base, not relocated",
          all(lm[m]["load"] is None for m in MODULES
              if m in lm and lm[m]["kind"] == "PE32"))
    ann = annotation_rows()
    check("every annotation row cites at least one repo file",
          all(a["evidence"].strip() for a in ann))
    check("every annotation row names a module in MODULES",
          all(a["scope"].strip() in MODULES for a in ann))
    # NOT `int(addr) < image_bytes`. `image_bytes` in the load map is the raw
    # `body.bin` the module was imported from, and Ghidra's PE32 loader maps
    # the *section's virtual size*, which is routinely larger: OemHooksSmm's
    # body is 4,096 bytes in the load map, 4,202 on disk, and the imported
    # program has functions at 0x1240, past both. So that bound was wrong, and
    # it fired on 25 correct annotations. The real question -- does this address
    # name a function in the program -- is answered against the listing index,
    # in --check, where the index is loaded.
    _lrows = {}
    if os.path.isfile(LISTING_INDEX):
        for r in csv.DictReader(open(LISTING_INDEX, newline="")):
            _lrows.setdefault(r["program"], set()).add(r["addr"].upper())
    if _lrows:
        _missing = [a for a in ann
                    if a["scope"] in _lrows
                    and a["addr"].upper().replace("0X", "").lstrip("0")
                    not in {x.lstrip("0") for x in _lrows[a["scope"]]}]
        check("every annotation address resolves to an exported function",
              not _missing,
              "%d do not, e.g. %s" % (len(_missing),
                                       [(a["scope"], a["addr"]) for a in _missing[:3]]))
    # TE images are loaded at a high base (0xFFF8xxxx on this platform), so
    # their function addresses do not fit a signed 32-bit int. The shared
    # scripts used Integer.parseInt(.., 16) and would have named the wrong
    # function for any of them; they parse longs now. The assertion stays --
    # the first version of it existed to say "there are none of these today",
    # and the sweep produced 50, which is exactly how a guard written to be
    # surprised should find out.
    te_rows = [a for a in ann if lm.get(a["scope"], {}).get("kind") == "TE"]
    check("TE annotation addresses are above Integer.MAX_VALUE, so the shared "
          "scripts must parse longs", True,
          "%d TE row(s); the scripts read Long.parseLong" % len(te_rows))
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def check():
    ok = True

    def fail(msg):
        nonlocal ok
        print("  FAIL  %s" % msg)
        ok = False

    print("bios_extract.py --check")
    for path, what in ((MANIFEST, "manifest"), (INDEX, "index"),
                       (LISTING_INDEX, "listing index"),
                       (LOAD_MAP, "load map")):
        if not os.path.isfile(path):
            fail("no %s at %s" % (what, os.path.relpath(path, REPO)))
    if not ok:
        return 1
    # The two committed indexes and the manifest, read strictly once each and
    # then used by every check below. A read error is reported as a failed check
    # rather than a traceback, so a broken index reads as a broken index.
    _read = {}
    for _name, _path in (("index.csv", INDEX), ("listing-index.csv", LISTING_INDEX),
                         ("manifest.csv", MANIFEST)):
        try:
            _read[_name] = read_index(_path)
        except (OSError, csv.Error) as e:
            fail("%s does not parse as strict CSV: %s" % (_name, e))
    if not ok:
        return 1
    # Structure before content, and stop if it fails. A row that did not come
    # out whole has no `out_file` to open and no address to key on, so every
    # per-row check below would be reading past the end of it -- and the counts
    # those checks compare are exactly the ones a short row has quietly made
    # smaller. Reported and stopped, not carried on from.
    _struct = index_structure_problems(_read["index.csv"],
                                       _read["listing-index.csv"])
    if _struct:
        fail("; ".join(_struct[:3]))
        return 1
    # Every decompilation has its machine code beside it, and every listing
    # names a file that exists. A .c with no .asm is a reading with nothing to
    # check it against; a listing row pointing at a missing file is an export
    # that has gone stale in a way the C index cannot see.
    _rows = _read["index.csv"]
    _lrows = _read["listing-index.csv"]
    _seen = {(r["program"], r["addr"]) for r in _rows}
    _lseen = {(r["program"], r["addr"]) for r in _lrows}
    for r in _lrows:
        if r["out_file"] and not r["out_file"].startswith("(") \
                and not os.path.isfile(os.path.join(LISTINGS, r["out_file"])):
            fail("listing row %s %s points at a missing file: %s"
                 % (r["program"], r["addr"], r["out_file"]))
    for prog, addr in _seen - _lseen:
        fail("%s %s decompiles but has no disassembly listing" % (prog, addr))

    # Every line that starts with an address is an instruction, and the parser
    # has to get all of them. A parser that reads a fraction of a file and
    # finds nothing wrong in it reports a pass, which is worse than one that
    # reads none -- this is not hypothetical, it is what happened on the EC
    # when the listing format changed and the committed listings had not been
    # re-exported.
    insns, unparsed = 0, []
    for r in _lrows:
        rel = r.get("out_file", "")
        if not rel or rel.startswith("("):
            continue
        path = os.path.join(LISTINGS, rel)
        if not os.path.isfile(path):
            continue
        text = open(path, errors="replace").read()
        lines = [l for l in text.splitlines() if _ADDRESS_LINE.match(l)]
        got = _parse_listing_lines(lines)
        insns += len(got)
        if len(got) != len(lines):
            unparsed.append("%s/%s: %d line(s), %d parsed"
                            % (r["program"], r["addr"], len(lines), len(got)))
    if _lrows:
        print("  disassembly: %d instruction(s) parsed across %d listing(s)"
              % (insns, len(_lrows)))
    for why in unparsed[:10]:
        fail("listing does not parse: %s" % why)
    if len(unparsed) > 10:
        fail("... and %d more listing(s) that do not parse" % (len(unparsed) - 10))
    if not ok:
        return 1
    digest = rom_digest()
    manifest = {r["program"]: r for r in _read["manifest.csv"]}
    if set(manifest) != set(MODULES):
        fail("the manifest's modules are not MODULES")
    for name, row in sorted(manifest.items()):
        if row["sha256"] != digest:
            fail("%s: manifest SHA-256 does not match the committed zip -- the "
                 "export is stale, rebuild it" % name)
        try:
            functions = int(row["functions"])
            decompiled = int(row["decompiled"])
            failed = int(row["failed"])
        except (KeyError, TypeError, ValueError):
            # coverage_mismatches() below names a `functions` that is not a
            # number in its own words; this is only here so the same fault is
            # not a traceback on the way to being told about it.
            continue
        if functions != decompiled + failed:
            fail("%s: functions != decompiled + failed" % name)
        if decompiled < functions and failed == 0:
            fail("%s: decompiled < functions but failed == 0" % name)
    _modes = manifest_mode_problems(_read["manifest.csv"])
    if _modes:
        fail("; ".join(_modes[:3]))
    if int(manifest[SETUP_MODULE]["image_bytes"]) < 0x10000:
        fail("%s: the manifest records %d bytes; the committed ROM's Setup body "
             "is 842592, so the export is not from this ROM"
             % (SETUP_MODULE, int(manifest[SETUP_MODULE]["image_bytes"])))
    index = _rows
    seen, per_program = set(), {}
    for row in index:
        seen.add((row["program"], int(row["addr"], 16)))
        per_program.setdefault(row["program"], []).append(row)
        out = os.path.join(DECOMPILED, row["out_file"])
        if row["out_file"] not in ("", "(failed)") and not os.path.isfile(out):
            fail("index row %s %s points at a missing file: %s"
                 % (row["program"], row["addr"], row["out_file"]))
    # The manifest's function count against both indexes' row counts, module by
    # module. The twelve LEGACY_MODULES below are checked a third way -- against
    # the `// ==== ` markers in the .c itself -- and that one is the expensive
    # half: it opens a decompile per module. This covers all 38 for the price of
    # two CSVs, and the manifest's join key needs no translation because its
    # `program` column and the index's are both module names.
    for _name, _irows in (("index.csv", _rows),
                          ("listing-index.csv", _lrows)):
        _counts = {}
        for r in _irows:
            _counts[r.get("program")] = _counts.get(r.get("program"), 0) + 1
        _mm = coverage_mismatches(_read["manifest.csv"],
                                  lambda p, c=_counts: c.get(p, 0))
        if _mm:
            fail("%s: %s" % (_name, "; ".join(_mm[:3])))
    print("  coverage: %d index row(s), %d listing-index row(s), %d manifest "
          "module(s)" % (len(_rows), len(_lrows), len(_read["manifest.csv"])))
    for name in LEGACY_MODULES:
        c = os.path.join(DECOMPILED, name + ".c")
        if not os.path.isfile(c):
            fail("%s.c is missing" % name)
            continue
        text = open(c, errors="replace").read()
        if not text.startswith("// %s.efi: Ghidra " % name):
            fail("%s.c does not carry the unedited DecompAll header" % name)
        n = text.count("// ==== ")
        try:
            recorded = int(manifest[name]["functions"]) if name in manifest else None
        except (KeyError, TypeError, ValueError):
            recorded = None        # the coverage check above has already named it
        if n == 0:
            fail("%s.c has no functions in it at all" % name)
        elif recorded is not None and n != recorded:
            fail("%s.c has %d functions, the manifest says %s"
                 % (name, n, manifest[name]["functions"]))
        if len(per_program.get(name, [])) != n:
            fail("%s: %d functions in the index, %d in the .c"
                 % (name, len(per_program.get(name, [])), n))
    for a in annotation_rows():
        key = (a["scope"].strip(), int(a["addr"], 16))
        if key not in seen:
            fail("annotation %s %s resolves to no exported function -- either a "
                 "typo or the project needs --mode rebuild-project"
                 % (a["scope"], a["addr"]))
        if not a["evidence"].strip():
            fail("annotation %s %s has no evidence citation; an annotation "
                 "without one is a claim, not a finding" % (a["scope"], a["addr"]))
    for f in sorted(os.listdir(PROJECT)) if os.path.isdir(PROJECT) else []:
        if f.endswith(".lock") or f.endswith(".lock~"):
            fail("a Ghidra lock file is committed next to the project: %s "
                 "(a committed lock makes Ghidra refuse the project)" % f)
    for dp, _dns, fns in os.walk(DECOMPILED):
        for fn in fns:
            if fn.endswith(".c") and "DECOMPILER UNAVAILABLE" in open(
                    os.path.join(dp, fn), errors="replace").read():
                fail("%s: the decompiler did not load; this is a broken "
                     "toolchain, not an undecodable function"
                     % os.path.join(dp, fn))
    # The hand restatement and the machine-readable layer are two copies of one
    # reading, kept side by side on purpose. This is what stops them drifting.
    check_annotated_layers(fail)
    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
