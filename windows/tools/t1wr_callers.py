#!/usr/bin/env python3
r"""Census of every committed Windows input for a caller of ACPI T1WR(0x1173).

The DSDT's `T1WR` method (`evidence/acpi/dsdt.dsl:50635`) is the only thing
found so far that writes `0x07D0` for a reason that is not the vendor's
`ADDR_BATTERY_CHARGE_LIMIT_DOWN`: its `Arg0 == 0x1173` branch stores
`Arg1 * 8` into `DBD1` (0x07D0) and mirrors it to `\_SB.NPCF.AMAT`. Nothing
in the DSDT calls `T1WR`, so the caller is an external ACPI client. This
tool is the reproducible search for it, in the spirit of `ec_callsites.py`
next to it: regenerate the table rather than trust it.

What it searches, and why that is a fair test of each:

* `windows/decompiled/**` as text. The v3.1.39.0 tree is the whole service
  with every method body decrypted, so a negative there is a *closed*
  result for that binary rather than a search miss.
* Every committed vendor binary, by string table -- ASCII and UTF-16LE, the
  two encodings `windows/antitamper/README.md` already prescribes. A .NET
  P/Invoke carries its target name as a string whether it is declared
  directly or bound at run time by `GetProcAddress`, so a string-table miss
  excludes the name from that module. The .msixbundle and .appxsym are
  expanded in memory only: `vendor/` is committed input, never build output.
* The `.appxsym` PDB, which is a *name* source that survives method-body
  encryption -- the blind spot `windows/antitamper/README.md` describes.
* `evidence/acpi/dsdt.dsl` as a control. `T1WR` and `AMAT` are defined
  there, so a term set that found nothing anywhere would be a broken term
  set, not a clean tree.

A binary hit is only counted inside a run of printable characters, so it
means "this name is spelled in this file" rather than "these four bytes
turned up somewhere in 150 MB". A zero still means "not found by this
method", never "absent" -- the same caveat `ec/tools/scan_refs.py` and
`pe_triage.py` carry. The readability census is what says which inputs were
never searchable at all, and the caller could be an ACPI client that is in
none of these files.

One limit is worth naming rather than leaving to be discovered. A string
scan cannot see a four-character name stored as a four-byte immediate:
MSVC emits `mov dword ptr [rsp+N], 'ECRW'` and the operand bytes are
printable by accident, sitting inside a longer printable run, so the
whole-word guard rejects them. `ACPIDriver.sys` builds all 21 of its ACPI
method names that way, which is why its string table has no `T1WR` and its
Ghidra decompile does -- and why the decompiles are a separate input here
rather than a convenience.

Usage:
  t1wr_callers.py                     # the census, as a table
  t1wr_callers.py --verbose           # ...broken down per file and archive member
  t1wr_callers.py --self-check        # assert the census the docs quote
"""
import argparse
import io
import os
import re
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# IOCTL codes the ACPIDriverDll export table maps onto T1RD/T2RD/T3RD and
# T1WR/T2WR/T3WR (windows/native/ACPIDriverDll.dll.analysis.md:70-75), in
# both the hex the driver compares and the decimal a C# `const uint` carries.
# A caller that spells the IOCTL as a decimal is a caller this finds.
IOCTL_CODES = [0x9C40A4D0, 0x9C40A4D4, 0x9C40A4D8,
               0x9C40A4DC, 0x9C40A4E0, 0x9C40A4E4]

# The Arg0 values T1WR dispatches on for the GPU block (dsdt.dsl:50658-50718),
# as written in ASL and as they would appear as a decimal constant.
ACPI_ARGS = [0x1171, 0x1172, 0x1173, 0x2273]

# A hit must be a whole word, and -- for a number -- must not be a slice of
# a longer hex number. That last guard is what keeps a disassembly listing
# full of `0x180014465` from reading as four IOCTL codes; the trailing
# guard stays hex-only so a C# `2621482204u` literal still matches.
def _name(alt):
    return rf"(?<![A-Za-z0-9_])(?:{alt})(?![A-Za-z0-9_])"


def _num(literal):
    return rf"(?<![0-9A-Fa-f]){literal}(?![0-9A-Fa-f])"


def _terms():
    """[(label, prefilter cores, regex)] -- the one list the tool searches."""
    out = [
        ("TempWrite*", ["TempWrite"], _name(r"TempWrite\d?")),
        ("T[123]WR", ["T1WR", "T2WR", "T3WR"], _name(r"T[123]WR")),
        ("DBD1", ["DBD1"], _name("DBD1")),
        ("DBD2", ["DBD2"], _name("DBD2")),
        ("AMAT", ["AMAT"], _name("AMAT")),
        ("AMIT", ["AMIT"], _name("AMIT")),
        ("ATPP", ["ATPP"], _name("ATPP")),
        ("CTGP", ["CTGP"], _name("CTGP")),
        ("UOCT", ["UOCT"], _name("UOCT")),
        ("DBAC", ["DBAC"], _name("DBAC")),
        ("NPCF", ["NPCF"], _name("NPCF")),
    ]
    for code in IOCTL_CODES:
        out.append((f"0x{code:X}", [f"0x{code:X}"], _num(f"(?i:0x{code:X})")))
    for code in IOCTL_CODES:
        out.append((str(code), [str(code)], _num(str(code))))
    for arg in ACPI_ARGS:
        out.append((f"0x{arg:X}", [f"0x{arg:X}"], _num(f"(?i:0x{arg:X})")))
    for arg in ACPI_ARGS:
        out.append((str(arg), [str(arg)], _num(str(arg))))
    return out


# Not caller terms, and never counted as one. These are the names a
# readable name table is *known* to carry for the GPU feature area, and
# they are here so the negative for the PDB cannot be read as "the tool
# could not read the PDB": the same scan has to find these.
PROBES = [
    ("GpuDynamicBoost", ["GpuDynamicBoost"]),
    ("GpuConfigurableTGPTarget", ["GpuConfigurableTGPTarget"]),
    ("FanViewModel", ["FanViewModel"]),
    ("OverClock_SettingsView", ["OverClock_SettingsView"]),
    ("UWP_Refactor", ["UWP_Refactor"]),
    # Not a .NET name: the device path both native PEs open. It is here so
    # a native input's zero is also shown to be a read source.
    ("ACPIDriver", ["ACPIDriver"]),
]
PROBES = [(f"probe:{label}", cores, _name(label)) for label, cores in PROBES]


def _compile(terms):
    """The prefilter cores for a term list.

    The prefilter is a plain `in` test, which is memchr-fast over a 150 MB
    PDB; running a regex for a term that is not in the blob at all is the
    difference between a census that takes seconds and one that takes
    minutes. The regex still decides every count. The hex literals are
    matched case-insensitively -- the Ghidra listings write `0x9c40a4dc`
    where the ASL writes `0x9C40A4DC` -- so each core is also tested
    lowercased.
    """
    return ([(label, cores, [c.lower() for c in cores],
              [c.encode() for c in cores], [c.encode("utf-16-le") for c in cores])
             for label, cores, _ in terms],
            {label: re.compile(pat) for label, _, pat in terms})


TERMS = _terms()
# One walk over a 150 MB PDB has to answer both questions, so the probes
# ride in the same term list behind a `probe:` prefix and are split back out
# afterwards. They are never counted as caller terms.
PREFILTER, TEXT_RES = _compile(TERMS + PROBES)
PROBE_PREFIX = "probe:"


def split_probes(counts):
    """({caller terms}, {probe terms}) out of one combined count dict."""
    callers = {k: v for k, v in counts.items() if not k.startswith(PROBE_PREFIX)}
    probes = {k[len(PROBE_PREFIX):]: v for k, v in counts.items()
              if k.startswith(PROBE_PREFIX)}
    return callers, probes


# A string, in each of the two encodings a committed input can hold one in.
# Four characters is the shortest term (AMAT/AMIT/ATPP/DBAC/UOCT).
ASCII_RUN = re.compile(rb"[\x20-\x7e]{4,}")
UTF16_RUN = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")

# The text inputs. Each is a list of paths, each of which is a file or a
# directory walked in full; the native decompiles are split by program so
# a hit in the driver that *exports* TempWrite1 is not read as a hit in the
# UWP component that might *call* it.
TEXT_INPUTS = [
    ("decompiled/v3.1.39.0 (whole service, decrypted)",
     ["windows/decompiled/v3.1.39.0"]),
    ("decompiled/v3.1.6.0 (partial, anti-tamper)",
     ["windows/decompiled/v3.1.6.0"]),
    ("decompiled/v3.9.18.0 (partial, anti-tamper)",
     ["windows/decompiled/v3.9.18.0"]),
    ("decompiled/native ACPIDriver.sys + ACPIDriverDll.dll (exports TempWrite1)",
     ["windows/decompiled/native/ACPIDriver.c", "windows/decompiled/native/ACPIDriver.asm",
      "windows/decompiled/native/ACPIDriverDll.c", "windows/decompiled/native/ACPIDriverDll.asm"]),
    ("decompiled/native GamingCenter3_Cross + GC3_launcher (the UWP component)",
     ["windows/decompiled/native/GamingCenter3_Cross.c",
      "windows/decompiled/native/GC3_launcher.c", "windows/decompiled/native/GC3_launcher.asm"]),
    ("decompiled/native UEFI_Firmware + clrcompression",
     ["windows/decompiled/native/UEFI_Firmware.c", "windows/decompiled/native/UEFI_Firmware.asm",
      "windows/decompiled/native/clrcompression.c", "windows/decompiled/native/clrcompression.asm"]),
    ("CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)",
     ["evidence/acpi/dsdt.dsl"]),
]

# Every committed Windows binary that could host a caller, plus the two
# installer wrappers, which are scanned too so the negative can say what
# they actually are. Archive members are expanded in memory.
BINARY_INPUTS = [
    ("vendor 3.1.39.0 GCUService.exe (shipped, bodies encrypted)",
     "vendor/control-center-3.1.39.0/MyControlCenter/GCUService.exe"),
    ("decompiled GCUService.dumped.exe (bodies decrypted)",
     "windows/decompiled/v3.1.39.0/GCUService.dumped.exe"),
    ("vendor 3.1.6.0 UniwillService_3.1.6.0_STD.exe (installer)",
     "vendor/control-center-3.1.6.0/UniwillService_3.1.6.0_STD.exe"),
    ("vendor 3.9.18.0 setup.exe (installer)",
     "vendor/control-center-3.9.18.0/setup.exe"),
    ("vendor 3.9.18.0 ACPIDriver.sys",
     "vendor/control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys"),
    ("vendor 3.9.18.0 ACPIDriverDll.dll",
     "vendor/control-center-3.9.18.0/ACPIDriverDll.dll"),
    ("vendor 3.9.18.0 GamingCenter3_Cross .msixbundle (UWP front end)",
     "vendor/control-center-3.9.18.0/GamingCenter3_Cross.UWP_3.9.18.0_x64.msixbundle"),
    ("vendor 3.9.18.0 GamingCenter3_Cross .appxsym (PDB name table)",
     "vendor/control-center-3.9.18.0/GamingCenter3_Cross.UWP_3.9.18.0_x64.appxsym"),
]

# .NET binaries whose method-body headers can be classified. This is the
# readability census that decides whether a text-tree miss means anything.
DOTNET_INPUTS = [
    ("vendor 3.1.39.0 GCUService.exe (shipped)",
     "vendor/control-center-3.1.39.0/MyControlCenter/GCUService.exe"),
    ("decompiled GCUService.dumped.exe",
     "windows/decompiled/v3.1.39.0/GCUService.dumped.exe"),
]

# ILSpy's own account of the bodies it could not turn back into C#. The
# per-assembly body-header census above is the primary evidence; this is the
# decompiler saying the same thing from the other side.
DECOMPILER_MARKERS = ("Invalid MethodBodyBlock", "BadImageFormatException")

DLLIMPORT = re.compile(
    r"\[DllImport\(\s*\"(?P<dll>[^\"]+)\"[^\]]*\)\s*\](?P<decl>[^;{]*?)\b(?P<name>\w+)\s*\(")


def _match(text, live, pre, res):
    counts = {}
    for label, cores, cores_lc, _a, _w in pre:
        if label not in live:
            continue
        if not (any(c in text for c in cores)
                or any(c in text.lower() for c in cores_lc)):
            continue
        n = sum(1 for _ in res[label].finditer(text))
        if n:
            counts[label] = n
    return counts


def _merge(into, more):
    for label, n in more.items():
        into[label] = into.get(label, 0) + n
    return into


def scan_text(blob, pre=PREFILTER, res=TEXT_RES):
    """{label: count} over decoded text."""
    live = {label for label, cores, cores_lc, _a, _w in pre
            if any(c in blob for c in cores) or any(c in blob.lower()
                                                    for c in cores_lc)}
    return _match(blob, live, pre, res)


def scan_runs(blob, wide, pre, res):
    """Hits inside printable runs only, in one encoding.

    A term that straddles two unrelated byte sequences is not a string, so
    restricting to runs is what makes a binary hit a name and not a
    coincidence -- and it is what lets a PE export name count at all, since
    the byte after an export's last character is the NUL that ends it.
    """
    live = {label for label, _c, _lc, ascii_cores, wide_cores in pre
            if any(c in blob for c in (wide_cores if wide else ascii_cores))}
    counts = {}
    if not live:
        return counts
    for run in (UTF16_RUN if wide else ASCII_RUN).finditer(blob):
        _merge(counts, _match(
            run.group().decode("utf-16-le" if wide else "ascii"),
            live, pre, res))
    return counts


def scan_blob(blob, pre=PREFILTER, res=TEXT_RES):
    counts = scan_runs(blob, False, pre, res)
    return _merge(counts, scan_runs(blob, True, pre, res))


def scan_text_tree(paths, pre=PREFILTER, res=TEXT_RES):
    """({relpath: counts}, flat total) over files and directory trees."""
    per_file, total = {}, {}
    files = []
    for rel in paths:
        abs_ = os.path.join(REPO, rel)
        if os.path.isdir(abs_):
            for dirpath, dirnames, filenames in os.walk(abs_):
                dirnames.sort()
                files.extend(os.path.join(dirpath, n)
                             for n in sorted(filenames))
        else:
            files.append(abs_)
    for abs_ in files:
        with open(abs_, encoding="utf-8", errors="replace") as fh:
            counts = scan_text(fh.read(), pre, res)
        if counts:
            per_file[os.path.relpath(abs_, REPO).replace(os.sep, "/")] = counts
            _merge(total, counts)
    return per_file, total


def scan_binary(blob, label, report, pre, res):
    """Scan one binary or archive member, recursing into nested archives."""
    if blob[:4] == b"PK\x03\x04" and zipfile.is_zipfile(io.BytesIO(blob)):
        total = {}
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                sub = scan_binary(zf.read(info), label, report, pre, res)
                if sub:
                    report.append((f"{label}!{info.filename}", sub))
                _merge(total, sub)
        return total
    counts = scan_blob(blob, pre, res)
    if counts:
        report.append((label, counts))
    return counts


def scan_binary_file(path, label, report, pre=PREFILTER, res=TEXT_RES):
    with open(path, "rb") as fh:
        return scan_binary(fh.read(), label, report, pre, res)


def decompiler_census(root):
    """{relpath: marker count} for the .cs files ILSpy could not fully read."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            if not name.endswith(".cs"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            n = sum(text.count(m) for m in DECOMPILER_MARKERS)
            if n:
                out[os.path.relpath(path, root).replace(os.sep, "/")] = n
    return out


def body_census(path):
    """{tiny, fat, invalid, abstract/extern} for one .NET assembly.

    Reuses dotnet_bodies.py rather than re-deriving the ECMA-335 header
    rules, so "which bodies did the anti-tamper encrypt" has one answer in
    this repo and not two that can drift.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import dotnet_bodies
    except ImportError:
        return None
    counts = {"tiny": 0, "fat": 0, "invalid": 0, "abstract/extern": 0}
    for pe, _own, _name, rva in dotnet_bodies.methods(path):
        if not rva:
            counts["abstract/extern"] += 1
        else:
            counts[dotnet_bodies.classify(pe, rva)[0]] += 1
    return counts


def dllimports(root):
    """[(dll, extern, relpath:line)] over every [DllImport] in a tree.

    The managed side of a caller search: a .NET P/Invoke to TempWrite1
    would appear here, so a tree with no such row is a tree that cannot
    bind that export.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            if not name.endswith(".cs"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for m in DLLIMPORT.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                out.append((m.group("dll"), m.group("name"), f"{rel}:{line}"))
    return out


def census():
    """Everything docs/findings.md quotes, computed from the committed tree."""
    result = {"text": [], "binary": [], "bodies": [], "unreadable": [], "probes": []}
    for label, paths in TEXT_INPUTS:
        per_file, total = scan_text_tree(paths)
        callers, _probes = split_probes(total)
        result["text"].append((label, ", ".join(paths), callers,
                               [(f, split_probes(c)[0]) for f, c in per_file.items()]))
    for label, rel in BINARY_INPUTS:
        report = []
        combined = scan_binary_file(os.path.join(REPO, rel), label, report)
        callers, probes = split_probes(combined)
        result["binary"].append((label, rel, callers,
                                 [(m, split_probes(c)[0]) for m, c in report]))
        result["probes"].append((label, "binary", probes))
    for label, rel in DOTNET_INPUTS:
        result["bodies"].append((label, rel, body_census(os.path.join(REPO, rel))))
    for label, paths in TEXT_INPUTS[:3]:
        marks = {}
        for rel in paths:
            marks.update(decompiler_census(os.path.join(REPO, rel)))
        result["unreadable"].append((label, marks))
    result["dllimports"] = dllimports(os.path.join(REPO, "windows/decompiled/v3.1.39.0"))
    return result


# The census of the committed tree, as of 2026-09-23 when this tool was
# written and the section of docs/findings.md that quotes it. Only non-zero
# counts are stored -- a zero is the answer, and storing it would make every
# new file in the tree a self-check failure for no reason. The numbers
# docs/findings.md quotes are these; a drift means a committed input
# changed and the section has to be re-derived, not that the tool broke.
EXPECTED_TEXT = {
    # The six TMPREAD/TMPWRITE IOCTL codes, declared once each and never
    # passed to the only helper that could send one.
    "decompiled/v3.1.39.0 (whole service, decrypted)": {
        "2621482192": 1, "2621482196": 1, "2621482200": 1,
        "2621482204": 1, "2621482208": 1, "2621482212": 1},
    "decompiled/v3.1.6.0 (partial, anti-tamper)": {},
    "decompiled/v3.9.18.0 (partial, anti-tamper)": {},
    # The export and the IOCTL constants, in the two programs that define
    # them. Neither is a caller, which is why they are their own input.
    "decompiled/native ACPIDriver.sys + ACPIDriverDll.dll (exports TempWrite1)": {
        "TempWrite*": 12, "0x9C40A4D0": 4, "0x9C40A4D4": 4, "0x9C40A4D8": 4,
        "0x9C40A4DC": 4, "0x9C40A4E0": 4, "0x9C40A4E4": 4},
    "decompiled/native GamingCenter3_Cross + GC3_launcher (the UWP component)": {},
    "decompiled/native UEFI_Firmware + clrcompression": {},
    "CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)": {
        "T[123]WR": 3, "DBD1": 2, "DBD2": 2, "AMAT": 5, "AMIT": 2,
        "ATPP": 4, "CTGP": 2, "UOCT": 4, "DBAC": 7, "NPCF": 54,
        "0x1171": 1, "0x1172": 1, "0x1173": 1, "0x2273": 1},
}

EXPECTED_BINARY = {
    "vendor 3.1.39.0 GCUService.exe (shipped, bodies encrypted)": {},
    "decompiled GCUService.dumped.exe (bodies decrypted)": {},
    "vendor 3.1.6.0 UniwillService_3.1.6.0_STD.exe (installer)": {},
    "vendor 3.9.18.0 setup.exe (installer)": {},
    "vendor 3.9.18.0 ACPIDriver.sys": {},
    # The three export names, in the export directory. This is the positive
    # control on the binary string scan: the same scan that finds them finds
    # nothing of the sort a caller would have to spell.
    "vendor 3.9.18.0 ACPIDriverDll.dll": {"TempWrite*": 3},
    "vendor 3.9.18.0 GamingCenter3_Cross .msixbundle (UWP front end)": {},
    "vendor 3.9.18.0 GamingCenter3_Cross .appxsym (PDB name table)": {},
}

EXPECTED_BODIES = {
    "vendor 3.1.39.0 GCUService.exe (shipped)":
        {"tiny": 1191, "fat": 1, "invalid": 3759, "abstract/extern": 349},
    "decompiled GCUService.dumped.exe":
        {"tiny": 2630, "fat": 2321, "invalid": 0, "abstract/extern": 349},
}


def self_check(c):
    """The census docs/findings.md quotes, asserted against the tree."""
    drift = []
    for table, key, kind in ((EXPECTED_TEXT, c["text"], "text"),
                             (EXPECTED_BINARY, c["binary"], "binary")):
        for label, _paths, total, _rest in key:
            if label not in table:
                drift.append(f"unexpected {kind} input {label}")
            elif total != table[label]:
                drift.append(f"{kind} {label}\n     expected {table[label]}"
                             f"\n     got      {total}")
    for label, _rel, counts in c["bodies"]:
        if counts is None:
            drift.append(f"body census unavailable for {label}; "
                         f"pip install dnfile and re-run")
        elif counts != EXPECTED_BODIES.get(label):
            drift.append(f"bodies {label}\n     expected "
                         f"{EXPECTED_BODIES.get(label)}\n     got      {counts}")

    # The exclusion the finding rests on, as an assertion, so a future dump
    # that does bind TempWrite1 cannot pass unnoticed.
    acpi = sorted({(dll, extern) for dll, extern, _ in c["dllimports"]
                   if dll.lower() == "acpidriverdll.dll"})
    if acpi != [("ACPIDriverDll.dll", "SMAPCTable")]:
        drift.append(f"service ACPIDriverDll P/Invokes changed: {acpi}")

    # The PDB's negative is only worth anything if the PDB was read. These
    # are names it is known to carry, so a zero here would mean the scan
    # broke, not that the name table is empty.
    for label, _kind, probes in c["probes"]:
        if "appxsym" in label and not probes:
            drift.append(f"{label}: the readability probes all came back zero, "
                         f"so its caller-term zero cannot be trusted")

    if drift:
        print("t1wr_callers: the census has drifted from the committed tree",
              file=sys.stderr)
        for d in drift:
            print("  " + d, file=sys.stderr)
        print("\nIf a committed input genuinely changed, re-run the census, "
              "update docs/findings.md to match, and re-bake the EXPECTED_* "
              "tables here.", file=sys.stderr)
        return 1
    print("t1wr_callers: census matches the committed tree -- "
          f"{len(EXPECTED_TEXT)} text inputs, {len(EXPECTED_BINARY)} binary "
          f"inputs, {len(EXPECTED_BODIES)} body censuses, and the service's "
          f"only ACPIDriverDll P/Invoke is {acpi[0][1]}")
    return 0


def render(c, verbose):
    out = sys.stdout.write
    out("T1WR(Arg0=0x1173) caller census. Every number is a hit count, not\n"
        "an estimate. A zero means 'not found by this method'.\n\n")

    out("== text inputs: input | term | hits ==\n")
    width = max(len(label) for label, _, _, _ in c["text"])
    for label, _paths, total, per_file in c["text"]:
        if not total:
            out(f"{label:<{width}}  (no term hit anywhere in this input)\n")
            continue
        for term, n in sorted(total.items()):
            out(f"{label:<{width}}  {term:<12} {n}\n")
        if verbose:
            for f, counts in sorted(per_file):
                for term, n in sorted(counts.items()):
                    out(f"{'':<{width}}    {f}: {term} x{n}\n")

    out("\n== binary inputs: string table, ASCII and UTF-16LE ==\n")
    for label, _rel, total, report in c["binary"]:
        head = f"{label:<52}"
        if not total:
            out(f"{head}  (no term hit in any string)\n")
            continue
        for term, n in sorted(total.items()):
            out(f"{head}  {term:<12} {n}\n")
        if verbose:
            for member, counts in report:
                for term, n in sorted(counts.items()):
                    out(f"{'':<52}    {member}: {term} x{n}\n")

    out("\n== readability probes on the binary inputs (not caller terms) ==\n")
    out("A name these inputs are known to carry -- a .NET method name from the\n"
        "GPU feature area, or the driver device name for the native PEs. They\n"
        "are counted so that a zero in the caller table above reads as 'the\n"
        "name is not in there' rather than 'the scan did not reach the source'.\n"
        "The text inputs need no such check: the DSDT control above is the\n"
        "proof that the text scanner reaches a source that has the term.\n")
    for label, _kind, probes in c["probes"]:
        hits = ", ".join(f"{k} x{v}" for k, v in sorted(probes.items()))
        out(f"{label:<52}  {hits or '(no probe hit -- source may be unread)'}\n")

    out("\n== readability census: .NET method-body headers ==\n")
    for label, _rel, counts in c["bodies"]:
        if counts is None:
            out(f"{label:<52}  unavailable (pip install dnfile)\n")
            continue
        out(f"{label:<52}  "
            + "  ".join(f"{k} {v}" for k, v in counts.items()) + "\n")

    out("\n== readability census: ILSpy error markers in the .cs trees ==\n")
    for label, marks in c["unreadable"]:
        out(f"{label}: {sum(marks.values())} marker(s) in {len(marks)} "
            f"of the .cs files\n")
        if verbose:
            for name, n in sorted(marks.items(), key=lambda kv: (-kv[1], kv[0])):
                out(f"    {n:4d}  {name}\n")

    out("\n== [DllImport] surface of the decrypted service ==\n")
    for dll, extern, where in c["dllimports"]:
        if dll.lower() in ("acpidriverdll.dll", "gpuiinfodll.dll"):
            out(f"  {dll}!{extern}   {where}\n")

    out("\n== unreadable by this method ==\n")
    out("The negative above is only as good as this list. Everything named\n"
        "here is a place the search could not reach, not a place it looked\n"
        "and found nothing.\n")
    for label, marks in c["unreadable"]:
        total = sum(marks.values())
        if total:
            out(f"  {label}: {total} ILSpy error marker(s) across "
                f"{len(marks)} .cs file(s), so every method body under them\n"
                f"    is unsearched. windows/antitamper/README.md; issue #3.\n")
    for label, _kind, probes in c["probes"]:
        if not probes and "installer" in label:
            out(f"  {label}: no probe hit, because the payload is\n"
                f"    Inno-compressed inside the wrapper. What that payload\n"
                f"    contributes is already committed as the decompiled\n"
                f"    trees and the native decompiles; nothing else from the\n"
                f"    installer was read. windows/tools/extract.sh.\n")
    out("  vendor 3.9.18.0 ACPIDriver.sys: its string table has none of the\n"
        "    21 ACPI method names, because MSVC emits each one as a 4-byte\n"
        "    immediate rather than a terminated string. The Ghidra decompile\n"
        "    of the same file is a separate text input above and is where\n"
        "    its IOCTL constants are covered.\n")
    out("  Not in this repository at all, and therefore not searched by\n"
        "    anything above: firmware, including any ACPI component that\n"
        "    defines \\_SB.NPCF, which the DSDT only declares External\n"
        "    (evidence/acpi/dsdt.dsl:54-65). A caller there would be\n"
        "    invisible to every input in this table.\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="break the counts down per file and per archive member")
    ap.add_argument("--self-check", action="store_true",
                    help="assert the census docs/findings.md quotes")
    args = ap.parse_args(argv)

    c = census()
    if args.self_check:
        return self_check(c)
    return render(c, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
