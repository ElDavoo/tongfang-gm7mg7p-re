#!/usr/bin/env python3
"""Import the vendor's native (non-.NET) Windows binaries into one Ghidra
project and record what decompiled, as a machine-checkable manifest.

This is the Windows-side counterpart to `ec/tools/build_ec_decompile.py` (the
Ghidra pipeline towards a C codebase for the EC). Ghidra is the right tool
here because the targets are native x64 PE images: the hand-written radare2
write-ups in `windows/native/*.analysis.md` are the prose, this is the
reproducible decompile+count underneath them.

The decompilation itself is done by the SHARED exporter
`ghidra/scripts/ExportDecompile.java` (per-program mode: one .c per binary),
and the annotation pass by the shared `ghidra/scripts/ApplyAnnotations.java` --
the same scripts and the same provenance header every other component uses, so
there is one header convention and one decompiler-availability guard in the
repository, not one per component. This driver only decides WHAT to import,
stages the PDB, and rewrites the exporter's index into the committed manifest.

Scope, and why it is narrow:

* Only the native targets listed in `../ghidra/native-binaries.csv` are
  imported. Ghidra reads .NET *method names* from metadata and nothing more:
  on `GCUService.dumped.exe` it reports 400/400 "decompiled" while every body
  is `halt_baddata()` / "Unable to resolve constructor". Managed assemblies are
  the job of `ilspycmd` (`../tools/extract.sh`), not this.
* Third-party natives that ride along in the installer (DiskInfo64,
  NVControlSetting, GPUInfoDLL, Microsoft.Graphics.Canvas) are excluded: they
  are not the vendor's code, so decompiling them adds bulk without advancing
  the mission. The exclusion is spelled out in
  `../decompiled/native/README.md` rather than left implicit here.

Two committed PEs are read in place; the rest come out of the installers via
`../tools/extract.sh` into a scratch dir. Everything is static analysis of
committed or extracted files: no vendor code is executed.

Usage:
    python3 decompile_native.py --self-test
    python3 decompile_native.py --check
    python3 decompile_native.py                 # rebuild project + manifest
    python3 decompile_native.py --mode export-only
    python3 decompile_native.py --only ACPIDriver.sys --project-dir /tmp/p
"""
import argparse
import csv
import hashlib
import io
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOWS_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(WINDOWS_DIR)

TARGETS_CSV = os.path.join(WINDOWS_DIR, "ghidra", "native-binaries.csv")
MANIFEST_CSV = os.path.join(WINDOWS_DIR, "ghidra", "manifest.csv")

# Binaries deliberately NOT in the committed project, and why. The project is
# committed so an annotation change does not need a 30-minute re-analysis, and
# that only works while the project fits in a repository.
#
# Ghidra's analysis database for a 64 KB program runs to tens of megabytes --
# roughly 14x the image. GamingCenter3_Cross.dll is a 27 MB native image, and
# its buffer file alone is 337,182,720 bytes. GitHub rejects any file over
# 100 MB, so the push fails on it, and there is no way to commit it short of
# Git LFS, which this repository does not use and which a reviewer cloning it
# would then need.
#
# So the five that fit are committed and this one is not, and the manifest says
# so in a row of its own rather than leaving the export looking complete. The
# decompiled C for it is committed -- 56 MB of text, which does fit -- so the
# analysis is not lost, only the ability to re-derive it without an import.
PROJECT_EXCLUDED = {
    "GamingCenter3_Cross.dll":
        "analysis database is 337 MB (one Ghidra buffer file), over GitHub's "
        "100 MB per-file limit; re-import to re-export this one",
}
INDEX_CSV = os.path.join(WINDOWS_DIR, "ghidra", "index.csv")
PROJECT_DIR = os.path.join(WINDOWS_DIR, "ghidra", "project")
PROJECT_NAME = "uniwill_native"
DECOMPILED_DIR = os.path.join(WINDOWS_DIR, "decompiled", "native")
# The disassembly index, one row per function, out_file pointing at the .asm
# that sits beside each .c.
LISTING_INDEX = os.path.join(WINDOWS_DIR, "ghidra", "listing-index.csv")

# A disassembly line: an address, then the byte column, then the mnemonic. The
# byte column ends at the first `-` and is padded to the program's widest
# instruction (15 on x86-64), which is what keeps a hex-looking mnemonic out of
# it. See ghidra/scripts/ExportListing.java.
#
# The address width has to clear the component's widest address, and this one is
# 9: every image here is x86-64, and TongFang.addrKey() only strips the 0x and
# the space prefix, so 140001000 is nine hex digits. The old {4,8} ceiling
# matched no line in any of the five committed listings -- 0 of 2,875 in
# ACPIDriver.asm -- so `lines` came out empty and "0 parsed == 0 lines" was
# reported as a pass. That is the failure this check exists to catch: a parser
# that reads a fraction of a file and finds nothing wrong in it reports a pass.
# 16 is Ghidra's own widest address, so the ceiling is the format's, not a
# number picked to fit today's five files.
_ADDRESS_LINE = re.compile(r"^[0-9A-Fa-f]{4,16}\s+\S")
_BYTE_SLOT = re.compile(r"^(?:[0-9A-Fa-f]{2}|-)$")


def _parse_listing_lines(lines):
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
        if take:
            out.append((addr, "".join(parts[1:1 + take])))
    return out


def parse_listings(rows, outdir):
    """Parse each DISTINCT listing the index names, once each.

    The listing index has one row per function but, in per-program export mode,
    one out_file per program: listing-index.csv's 10,664 rows name 5 files, and
    10,141 of those rows name ACPIDriverDll.asm alone. Iterating rows re-read
    and re-scanned that 35 MB file ten thousand times -- 358 GB of text to
    re-derive what one pass already knows.

    Returns (instruction_count, [(file, n_lines, n_parsed)], n_files_read)."""
    insns, unparsed, seen, read = 0, [], set(), 0
    for r in rows:
        rel = (r.get("out_file") or "").strip()
        if not rel or rel.startswith("(") or rel in seen:
            continue
        seen.add(rel)
        path = os.path.join(outdir, rel)
        if not os.path.isfile(path):
            continue
        read += 1
        lines = [l for l in open(path, errors="replace").read().splitlines()
                 if _ADDRESS_LINE.match(l)]
        got = _parse_listing_lines(lines)
        insns += len(got)
        if len(got) != len(lines):
            unparsed.append((rel, len(lines), len(got)))
    return insns, unparsed, read

# Shared Ghidra scripts (exporter, annotation applier, seeder) and the
# Windows-only PDB pre-script. The seeder is not used here -- a PE has no
# hand-curated seed basis -- but the directory is the shared one.
SCRIPTS = os.path.join(REPO, "ghidra", "scripts")
WIN_SCRIPTS = os.path.join(WINDOWS_DIR, "ghidra", "scripts")

# The PDB-backed 27 MB import needs its own invocation and a generous overall
# timeout so a single pathological import can never hang a whole run. With the
# PDB analyzer disabled (windows/ghidra/scripts/DisablePdbAnalyzer.java) the
# grind that used to run 10+ minutes does not happen; the timeout is the
# belt-and-braces.
PDB_TIMEOUT_S = 1800
# The default batch carries GamingCenter3_Cross.dll, a 27 MB native image, and
# 30 minutes was not enough for it on this machine even without the PDB. The
# other five together are minutes. --timeout raises it rather than the default
# being raised, because a longer default makes a genuine hang look like a slow
# build.
FAST_TIMEOUT_S = 1800

MANIFEST_HEADER = [
    "program", "source", "sha256", "pdb_staged", "loader", "ghidra_version",
    "functions", "decompiled", "failed", "instruction_bytes", "body_bytes",
    "seeds_applied", "seeds_rejected", "annotations_applied",
    "annotations_unmatched", "mode", "notes",
]
# The raw index the shared exporter appends to: 10 tab-separated fields.
INDEX_HEADER = ["program", "addr", "name", "size", "seed_basis", "annotated",
                "type", "basis", "evidence", "out_file"]
# What the manifest's `mode` column may say. Kept as data because it is a
# controlled vocabulary and a vocabulary is only enforced if something reads it
# from one place: the three modes the driver can produce, and nothing else.
MANIFEST_MODES = ("rebuild-project", "export-only", "not-in-project")


def log(msg):
    print(msg, flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_ghidra():
    """Locate analyzeHeadless and a JDK. Returns (analyze_headless, java_home)."""
    root = os.environ.get("GHIDRA_INSTALL_DIR")
    if root and os.path.exists(os.path.join(root, "support", "analyzeHeadless")):
        return (os.path.join(root, "support", "analyzeHeadless"),
                os.environ.get("JAVA_HOME") or _find_local_jdk())
    ah = os.path.expanduser("~/.local/opt/ghidra/support/analyzeHeadless")
    if os.path.exists(ah):
        return ah, os.environ.get("JAVA_HOME") or os.path.expanduser("~/.local/opt/jdk")
    which = shutil.which("analyzeHeadless")
    if which:
        return which, os.environ.get("JAVA_HOME")
    return None, None


def _find_local_jdk():
    p = os.path.expanduser("~/.local/opt/jdk")
    return p if os.path.isdir(p) else None


def ghidra_version(analyze_headless):
    """Read the version from Ghidra's application.properties (no JVM launch)."""
    if not analyze_headless:
        return "unknown"
    ghidra_root = os.path.dirname(os.path.dirname(os.path.abspath(analyze_headless)))
    props = os.path.join(ghidra_root, "Ghidra", "application.properties")
    try:
        with open(props) as f:
            for line in f:
                if line.startswith("application.version="):
                    return line.strip().split("=", 1)[1]
    except OSError:
        pass
    return "unknown"


def decompiler_preflight(analyze_headless):
    """Ghidra's native decompiler can be present on disk and still be unusable,
    and it fails SILENTLY: openProgram() returns false with an empty message.
    The shared exporter turns that into a loud failure, but catching it here
    gives a clearer message. Same check and rationale as
    ec/tools/build_ec_decompile.py."""
    if not analyze_headless:
        return
    decomp = os.path.join(os.path.dirname(os.path.dirname(analyze_headless)),
                          "Ghidra", "Features", "Decompiler", "os", "linux_x86_64",
                          "decompile")
    if os.path.exists(decomp) and not os.access(decomp, os.X_OK):
        raise SystemExit(
            "error: Ghidra's native decompiler is not executable: %s\n"
            "  It fails SILENTLY (openProgram() returns false, empty message),\n"
            "  which reads like 'this code will not decompile'. It is not." % decomp)


def load_targets(path=TARGETS_CSV):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["sha256"] = (r.get("sha256") or "").strip()
        r["source"] = (r.get("source") or "").strip()
    return rows


def run_extract(outdir):
    """Run windows/tools/extract.sh into outdir. The Inno leg needs
    innoextract, not on PATH here, so go through nix-shell."""
    extract_sh = os.path.join(HERE, "extract.sh")
    cmd = ["nix-shell", "-p", "innoextract", "--run", f"bash {extract_sh} {outdir}"]
    log(f"extract: {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        return False
    return True


def resolve_sources(targets, scratch):
    """Map each target's `source` to a local path. Committed sources are used
    in place; `extract:` sources are materialised under scratch by
    extract.sh. Returns list of (target, local_path)."""
    if any(t["source"].startswith("extract:") for t in targets):
        outdir = os.path.join(scratch, "extracted")
        if not run_extract(outdir):
            raise SystemExit("error: extract.sh failed")
    else:
        outdir = os.path.join(scratch, "extracted")
    resolved = []
    for t in targets:
        src = t["source"]
        if src.startswith("extract:"):
            rest = src[len("extract:"):]
            _, _, inside = rest.partition("#")
            local = os.path.join(outdir, inside)
        else:
            local = os.path.join(REPO, src)
        if not os.path.exists(local):
            raise SystemExit(f"error: source for {t['binary']} not found: {local}")
        resolved.append((t, local))
    return resolved


def stage_pdb(target_local, scratch):
    """GamingCenter3_Cross.dll has a matching PDB in the committed .appxsym.
    Copy dll+pdb into a staging dir side by side, return the staged dll."""
    base = os.path.basename(target_local)
    if base != "GamingCenter3_Cross.dll":
        return target_local, False
    stage = os.path.join(scratch, "pdb-stage")
    os.makedirs(stage, exist_ok=True)
    staged = os.path.join(stage, base)
    shutil.copy2(target_local, staged)
    appxsym = os.path.join(REPO, "vendor/control-center-3.9.18.0",
                           "GamingCenter3_Cross.UWP_3.9.18.0_x64.appxsym")
    import zipfile
    with zipfile.ZipFile(appxsym) as z, \
            z.open("GamingCenter3_Cross.pdb") as src, \
            open(os.path.join(stage, "GamingCenter3_Cross.pdb"), "wb") as dst:
        shutil.copyfileobj(src, dst)
    return staged, True


# DOS header + "PE\0\0" + 20-byte COFF header + room for the 15th data
# directory. 256 bytes of optional header already covers the CLR entry on PE32
# and PE32+; 512 leaves room for an optional header carrying more than either.
_PE_HEADER_BYTES = 512


def _pe_is_managed(f):
    """True if the PE at the start of f has a CLR data directory (a COM
    descriptor).

    Reads the header, not the image. The CLR directory is number 14, so the last
    byte this looks at is inside the 256-byte optional header; what follows is
    the section table and then the code. The image behind that header is 27 MB
    for GamingCenter3_Cross.dll, and a gate that asks this question on every run
    should not pay to read the code with it."""
    f.seek(0)
    if f.read(2) != b"MZ":
        return False
    f.seek(0x3C)
    pe = int.from_bytes(f.read(4), "little")
    f.seek(pe)
    d = f.read(_PE_HEADER_BYTES)
    if len(d) < 26 or d[:4] != b"PE\0\0":
        return False
    opt = 24
    magic = int.from_bytes(d[opt:opt + 2], "little")
    ddoff = opt + (112 if magic == 0x20b else 96)
    clr_rva = int.from_bytes(d[ddoff + 14 * 8: ddoff + 14 * 8 + 4], "little")
    return clr_rva != 0


def is_managed_assembly(path):
    try:
        with open(path, "rb") as f:
            return _pe_is_managed(f)
    except OSError:
        return False


def msix_inner_bytes(repo):
    """The inner .msix out of the committed bundle, read whole.

    Three of the six targets live in it and it is 17 MB, so whoever asks about
    managed-ness reads this once, not once per target."""
    import zipfile
    bundle = os.path.join(repo, "vendor/control-center-3.9.18.0",
                          "GamingCenter3_Cross.UWP_3.9.18.0_x64.msixbundle")
    with zipfile.ZipFile(bundle) as zb:
        inner = [n for n in zb.namelist() if n.endswith("_x64.msix")][0]
        return zb.read(inner)


def managed_from_msix(inner, inside):
    """Managed-ness of a target that lives in the UWP msixbundle, read straight
    out of the committed zip (no extraction). Returns True/False, or None if the
    member cannot be located."""
    marker = "v3.9.18.0/msix/"
    if inner is None or marker not in inside:
        return None
    member = inside.split(marker, 1)[1]
    import zipfile
    with zipfile.ZipFile(io.BytesIO(inner)) as zi, zi.open(member) as f:
        return _pe_is_managed(f)


# The exporter's per-program export label (its .c filename and index key).
# Ghidra's program name is the imported file name; the label is what the .c is
# written as. Default = the file stem, except where two programs in this repo
# share a stem -- GamingCenter3_Cross.exe and .dll both stem to
# "GamingCenter3_Cross", so the .exe (a launcher stub) is labelled distinctly.
EXPORT_LABELS = {
    "GamingCenter3_Cross.exe": "GC3_launcher",
    "GamingCenter3_Cross.dll": "GamingCenter3_Cross",
}


def export_label(program_name):
    return EXPORT_LABELS.get(program_name, program_name.rsplit(".", 1)[0])


def write_context(path, batch, version, sha_by_binary):
    """The key=value context file the shared exporter reads for its provenance
    header and for export-label resolution. `batch` is the list of (target,
    local) actually in this invocation. Mirrors ec/tools/build_ec_decompile.py's
    write_context(): a base source/sha plus a per-program source line, a
    programs= list, and a label.<program> per program so the exporter can give
    same-stem programs distinct outputs (and throw EXPORT LABEL COLLISION rather
    than silently overwrite if two still collide)."""
    names = [os.path.basename(t["binary"]) for t, _ in batch]
    with open(path, "w") as f:
        f.write("source=%s\n" % ",".join(t["source"] for t, _ in batch))
        for t, _ in batch:
            f.write("source.%s=%s\n" % (os.path.basename(t["binary"]), t["source"]))
        f.write("programs=%s\n" % ",".join(names))
        for name in names:
            f.write("label.%s=%s\n" % (name, export_label(name)))
        f.write("sha256=%s\n" % ",".join(sha_by_binary[t["binary"]] for t, _ in batch))
        f.write("ghidra_version=%s\n" % version)
        f.write("generator=windows/tools/decompile_native.py\n")
    return path


def run_in_env(cmd, logfile, env, timeout_s=None):
    """Run analyzeHeadless in its OWN process group, streaming output to
    logfile. Returns the rc, or 124 on timeout.

    The process group matters: analyzeHeadless is a shell wrapper
    (support/analyzeHeadless -> launch.sh -> java), so subprocess.run's timeout
    only reaps the wrapper and leaves the java grandchild running. A timeout that
    does not actually stop the leg is worse than none -- the run looks bounded
    and is not -- so on timeout we SIGKILL the whole group."""
    with open(logfile, "w") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env,
                                start_new_session=True)
        try:
            return proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            log(f"headless TIMEOUT after {timeout_s}s; killing process group "
                f"{os.getpgid(proc.pid)}")
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            return 124


def export_batch(analyze_headless, project_dir, imports, work, index, context,
                 outdir, reports, use_pdb_script, timeout_s, java_home=None,
                 listing_index=None, listings_out=None):
    """One analyzeHeadless invocation running the shared ApplyAnnotations +
    ExportDecompile + ExportListing post-scripts (and the Windows PDB
    pre-script if asked)."""
    os.makedirs(project_dir, exist_ok=True)   # Ghidra aborts if it is missing
    env = dict(os.environ)
    if java_home:
        env["JAVA_HOME"] = java_home
    cmd = [analyze_headless, project_dir, PROJECT_NAME, "-import"]
    cmd += list(imports)
    # One -scriptPath, semicolon-joined: the shared exporter/applier live in
    # ghidra/scripts, the Windows-only PDB pre-script in windows/ghidra/scripts.
    # A repeated -scriptPath does NOT accumulate on this Ghidra (the last one
    # wins and the shared dir drops out, so the post-scripts are "not found"), and
    # a colon-joined single value is not split either -- ';' is the separator.
    cmd += ["-overwrite", "-scriptPath", SCRIPTS + ";" + WIN_SCRIPTS]
    if use_pdb_script:
        cmd += ["-preScript", "DisablePdbAnalyzer.java"]
    # ApplyAnnotations: "-" for both CSVs = no annotation layer yet (this is a
    # PE, not the EC: no XDATA space, no hand-maintained function CSV), plus a
    # report dir. ExportDecompile: per-program .c, index, context, seed basis
    # "-" (a PE has no curated seed basis).
    cmd += ["-postScript", "ApplyAnnotations.java", "-", "-", reports]
    cmd += ["-postScript", "ExportDecompile.java", outdir, index, "per-program",
            context, "-"]
    # The disassembly, beside the decompilation. A PE decompilation is a reading
    # of bytes the reader never sees, and the same reason the EC and the BIOS
    # ship one applies here: without it there is nothing to check a claim about
    # what the code does against the code it claims to describe.
    if listing_index:
        cmd += ["-postScript", "ExportListing.java", listings_out or outdir,
                listing_index, "per-program", context, "-"]
    rc = run_in_env(cmd, os.path.join(work, "ghidra.log"), env, timeout_s=timeout_s)
    return rc, cmd


def parse_index(index_path):
    rows = list(csv.DictReader(open(index_path, newline=""), delimiter="\t"))
    return rows


def parse_counts(work, program):
    """The exporter writes <index>.<program>.counts with the per-program totals."""
    path = os.path.join(work, os.path.basename(index_path_stub(work)) + "." + program + ".counts")
    if not os.path.isfile(path):
        return None
    lines = [l for l in open(path).read().splitlines() if l.strip()]
    if not lines:
        return None
    # program, functions, decompiled, failed, common_bytes, window_bytes, body_bytes
    parts = lines[-1].split("\t")
    if len(parts) < 7:
        return None
    return {"functions": int(parts[1]), "decompiled": int(parts[2]),
            "failed": int(parts[3]), "common_bytes": int(parts[4]),
            "window_bytes": int(parts[5]), "body_bytes": int(parts[6])}


def index_path_stub(work):
    # The exporter derives the .counts name from the index path it is given.
    return os.path.join(work, "index-raw.csv")


def build_manifest_rows(resolved, index_rows, work, version, mode, sha_by_binary,
                        pdb_labels=()):
    """Join the exporter's index rows + per-program counts into the committed
    manifest. The exporter keys the index on the export LABEL, so map each label
    back to its target's full binary name for the manifest program column.
    instruction_bytes is bytes actually disassembled (the coverage figure);
    body_bytes is the overlapping sum of function-body lengths (not coverage).
    Raises if functions != decompiled + failed for any program."""
    per_stem = {}
    for row in index_rows:
        p = per_stem.setdefault(row["program"], {"functions": 0, "failed": 0, "body": 0})
        p["functions"] += 1
        p["body"] += int(row["size"])
        if row["out_file"] == "(failed)":
            p["failed"] += 1
    # The exporter keys the index on the export LABEL (its .c filename), which
    # for same-stem programs is the distinct label the driver assigned. Map each
    # label back to its target so the manifest program column is the full binary
    # name and source/sha are per-file.
    by_label = {}
    for t, local in resolved:
        by_label[export_label(os.path.basename(t["binary"]))] = (t, local)
    rows, problems = [], []
    for label in sorted(per_stem):
        p = per_stem[label]
        counts = parse_counts(work, label) or {}
        functions = counts.get("functions", p["functions"])
        decompiled = counts.get("decompiled", functions - p["failed"])
        failed = counts.get("failed", p["failed"])
        # Two different byte figures. instruction_bytes = bytes actually
        # disassembled (the honest coverage number; for a high-loaded PE every
        # instruction lands in the exporter's window bucket, so common+window is
        # the whole program). body_bytes = the sum of function-body lengths, which
        # OVERLAPS and can exceed the image; it is what the decompiler walked, not
        # a coverage figure.
        instr = counts.get("common_bytes", 0) + counts.get("window_bytes", p["body"])
        body = counts.get("body_bytes", p["body"])
        if functions != decompiled + failed:
            problems.append(f"{label}: functions({functions}) != decompiled({decompiled}) + failed({failed})")
        t_local = by_label.get(label)
        full = t_local[0]["binary"] if t_local else label
        rows.append({
            "program": full,
            "source": t_local[0]["source"] if t_local else "unknown",
            "sha256": sha_by_binary.get(full, ""),
            "pdb_staged": "yes" if label in pdb_labels else "no",
            "loader": "Portable Executable (PE)",
            "ghidra_version": version,
            "functions": functions,
            "decompiled": decompiled,
            "failed": failed,
            "instruction_bytes": instr,
            "body_bytes": body,
            "seeds_applied": 0,
            "seeds_rejected": 0,
            "annotations_applied": 0,
            "annotations_unmatched": 0,
            "mode": mode,
        })
    if problems:
        raise SystemExit("error: manifest inconsistency:\n  " + "\n  ".join(problems))
    return rows


def write_manifest(rows, path=MANIFEST_CSV, excluded=()):
    """`rows` plus one row per deliberately-excluded binary.

    The excluded row carries no function count, because there is none: the
    program is not in the committed project. It is here so the manifest is a
    complete account of the target list rather than a list of whatever
    happened to fit, and `mode: not-in-project` with the reason in `notes` is
    what a reader sees instead of a gap."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    have = {r["program"] for r in rows}
    extra = []
    for name, why in sorted(excluded.items()):
        if name in have:
            continue
        row = {h: "" for h in MANIFEST_HEADER}
        row.update({"program": name, "source": "(not imported)", "sha256": "",
                    "pdb_staged": "no", "loader": "", "ghidra_version": "",
                    "functions": "0", "decompiled": "0", "failed": "0",
                    "instruction_bytes": "0", "body_bytes": "0",
                    "mode": "not-in-project", "notes": why})
        extra.append(row)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_HEADER, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        for r in rows + extra:
            w.writerow(r)


# --------------------------------------------------------------------------
# --check
# --------------------------------------------------------------------------

def read_index(path, delimiter=","):
    """Rows of a committed index CSV, read strictly.

    `strict=True` is the point. csv's default reader is forgiving about quoting
    in the one way that hides an error rather than raising it: a bad quote ends
    the row early, the row comes back with a missing field, and every count
    taken from it is then quietly smaller than the file. A quoting mistake in a
    committed index is exactly the kind of thing that should be loud, and it
    costs nothing to make it so."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter, strict=True))


def index_structure_problems(index_rows, listing_rows):
    """Structural faults in the two committed indexes: rows that did not come
    out with the full header, and `(program, addr)` keys that appear twice.

    A duplicate key is an export appended to twice, or a de-dup that missed one;
    either way the row count no longer means "number of functions", which is
    the only thing the counts around it are for."""
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


def coverage_mismatches(manifest_rows, count_for_label):
    """Manifest rows whose recorded `functions` is not the row count the index
    carries for that program's export label.

    This is the cheap half of coverage: two committed CSVs, each of them a few
    hundred KB, compared against each other, with no `.c` and no `.asm` opened.
    It catches the case that matters most -- an index that gained or lost rows
    without the manifest being regenerated, so a reader would take a function
    count that no longer describes the export. What the deep tier adds on top is
    the independent byte-level re-derivation (the sdas8051 re-encode), not
    another count of the same rows.

    `count_for_label` maps an export label to its row count in an index."""
    out = []
    for r in manifest_rows:
        program = r.get("program", "?")
        try:
            recorded = int(r["functions"])
        except (KeyError, TypeError, ValueError):
            out.append(f"{program}: functions is {r.get('functions')!r}, not a number")
            continue
        got = count_for_label(export_label(program))
        if got != recorded:
            out.append("%s: manifest records %d function(s), index carries %d "
                       "row(s) for export label %s"
                       % (program, recorded, got, export_label(program)))
    return out


def manifest_mode_problems(manifest_rows):
    """Manifest rows whose `mode` is outside the three the driver produces."""
    return ["%s: mode is %r, not one of %s"
            % (r.get("program", "?"), r.get("mode"), "|".join(MANIFEST_MODES))
            for r in manifest_rows if r.get("mode") not in MANIFEST_MODES]


def retained_decompilations():
    """The `.c` files kept for a program in PROJECT_EXCLUDED.

    Named by EXPORT LABEL, not by the binary's own file name: the exporter
    writes the .c under the label, so GamingCenter3_Cross.dll is retained as
    GamingCenter3_Cross.c. Building the name from the binary instead gives
    GamingCenter3_Cross.dll.c, which nothing in this repository can ever write
    -- so the carve-out never matched anything and the two checks that used it
    have been red since the retention landed."""
    return {export_label(name) + ".c" for name in PROJECT_EXCLUDED}


def do_check():
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"  ({detail})" if detail and not cond else ""))
        if not cond:
            ok = False

    print("decompile_native.py --check")
    targets = load_targets()

    names = [t["binary"] for t in targets]
    check("target list has no duplicate binary names", len(names) == len(set(names)))

    # The two committed indexes, read strictly once each and then used by every
    # check below. Read errors are reported as a failed check rather than a
    # traceback, so a broken index reads as a broken index.
    irows, lrows = [], []
    for _path, _name in ((INDEX_CSV, "index.csv"), (LISTING_INDEX, "listing-index.csv")):
        if not os.path.isfile(_path):
            print(f"  --    {_name} not present yet (run the tool to generate it)")
            continue
        try:
            _rows = read_index(_path)
        except (OSError, csv.Error) as e:
            check(f"{_name} parses as strict CSV", False, e)
            continue
        check(f"{_name} parses as strict CSV", True)
        if _name == "index.csv":
            irows = _rows
        else:
            lrows = _rows
    _struct = index_structure_problems(irows, lrows)
    check("neither index has a short row or a duplicate (program, addr) key",
          not _struct, "; ".join(_struct[:3]))

    # Every decompilation has its machine code beside it, and every listing row
    # names a file that exists. A .c with no .asm is a reading with nothing to
    # check it against; a listing row pointing at a missing file is an export
    # that has gone stale in a way the C index cannot see.
    if lrows and os.path.isdir(DECOMPILED_DIR):
        _missing = [r["out_file"] for r in lrows
                    if r.get("out_file") and not r["out_file"].startswith("(")
                    and not os.path.isfile(
                        os.path.join(DECOMPILED_DIR, r["out_file"]))]
        check("every listing row points at a file that exists",
              not _missing,
              "%d missing, e.g. %s" % (len(_missing), _missing[:3]))
        _noasm = [f for f in sorted(os.listdir(DECOMPILED_DIR))
                  if f.endswith(".c")
                  and not os.path.isfile(os.path.join(
                      DECOMPILED_DIR, f[:-2] + ".asm"))]
        # The one .c that may have no listing beside it is a retained decompile
        # of a program in PROJECT_EXCLUDED, which is not in the committed
        # project, so its .asm cannot be re-exported. That is a real gap rather
        # than a formality -- 56 MB of decompile with no machine code to check it
        # against -- and nothing in this repository can close it. It is named on
        # every run instead of being folded into a pass, because a carve-out
        # that prints nothing is how a check stops meaning anything.
        _retained_c = retained_decompilations()
        _gap = [f for f in _noasm if f in _retained_c]
        _noasm = [f for f in _noasm if f not in _retained_c]
        for f in _gap:
            print("  --    %s has no listing beside it: retained decompile of a "
                  "program not in the project (PROJECT_EXCLUDED)" % f)
        check("every decompilation this project can produce has a listing beside it",
              not _noasm,
              "%d without, e.g. %s" % (len(_noasm), _noasm[:3]))
        # Every line that starts with an address is an instruction, and the
        # parser has to get all of them: a parser that reads a fraction of a
        # file and finds nothing wrong in it reports a pass. One pass per
        # distinct file -- the index has a row per function and an out_file per
        # program, so iterating rows reads the 35 MB listing 10,141 times.
        insns, unparsed, read = parse_listings(lrows, DECOMPILED_DIR)
        print(f"  {'ok  ' if not unparsed else 'FAIL'}  "
              f"disassembly: {insns} instruction(s) parsed across "
              f"{read} distinct listing(s) of {len(lrows)} index row(s)")
        if unparsed:
            check("every listing line parses", False,
                  "%d file(s) do not, e.g. %s"
                  % (len(unparsed), ["%s: %d line(s), %d parsed" % u
                                     for u in unparsed[:3]]))

    # No managed assembly in the target list. Committed sources are read in
    # place; msix-sourced extract: targets are read straight out of the
    # committed .msixbundle. The one inno-sourced target is enforced at import.
    # Three targets live in the same inner .msix, and it is read whole, so it
    # is opened once here rather than once per target below. Each of those reads
    # the member's PE header rather than the member: 26 MB for the .dll.
    _msix = msix_inner_bytes(REPO) if any(
        "v3.9.18.0/msix/" in t["source"] for t in targets) else None
    for t in targets:
        src = t["source"]
        if not src.startswith("extract:"):
            check(f"{t['binary']} ({src}) is not a managed assembly",
                  not is_managed_assembly(os.path.join(REPO, src)))
            continue
        _, _, inside = src[len("extract:"):].partition("#")
        managed = managed_from_msix(_msix, inside)
        if managed is None:
            print(f"  --    {t['binary']}: managed-ness checked at import time (inno source)")
        else:
            check(f"{t['binary']} (msix) is not a managed assembly", not managed)

    for t in targets:
        if t["source"].startswith("extract:"):
            continue
        p = os.path.join(REPO, t["source"])
        if not os.path.exists(p):
            check(f"{t['binary']} committed source exists", False, p)
            continue
        check(f"{t['binary']} committed source sha256 matches",
              sha256_file(p) == t["sha256"])

    # Every target is either in the manifest with functions, or named in
    # PROJECT_EXCLUDED with a reason. A binary that is in neither is a target
    # that silently stopped being covered, which is the shape of failure this
    # manifest exists to make visible.
    _targets = {os.path.basename(t["binary"]) for t in load_targets()}
    mrows = []
    if os.path.exists(MANIFEST_CSV):
        mrows = list(csv.DictReader(open(MANIFEST_CSV, newline="")))
    _have = {r["program"] for r in mrows}
    check("every target is in the manifest or in PROJECT_EXCLUDED, with a reason",
          all(n in _have or (n in PROJECT_EXCLUDED and PROJECT_EXCLUDED[n].strip())
              for n in _targets),
          ", ".join(sorted(n for n in _targets
                           if n not in _have and n not in PROJECT_EXCLUDED)))
    for _n, _why in sorted(PROJECT_EXCLUDED.items()):
        check(f"{_n} is recorded in the manifest as not-in-project",
              _n in _have, "absent from the manifest, so the export looks complete")

    if mrows:
        for r in mrows:
            fn, dec, fail = int(r["functions"]), int(r["decompiled"]), int(r["failed"])
            check(f"manifest {r['program']}: functions == decompiled + failed",
                  fn == dec + fail, f"{fn} != {dec} + {fail}")
        _modes = manifest_mode_problems(mrows)
        check("every manifest mode is " + "|".join(MANIFEST_MODES),
              not _modes, "; ".join(_modes[:3]))
        # Coverage, the cheap version: the manifest's function count against the
        # two indexes' row counts for the same export label. Both are committed
        # CSVs, so this costs milliseconds and needs no artefact opened. What it
        # does not do is re-derive the counts from the .c files -- the deep tier
        # adds the byte-level re-derivation, not another count.
        for _name, _rows in (("index.csv", irows),
                             ("listing-index.csv", lrows)):
            _counts = {}
            for r in _rows:
                _counts[r.get("program")] = _counts.get(r.get("program"), 0) + 1
            _mm = coverage_mismatches(mrows, lambda label, c=_counts: c.get(label, 0))
            check(f"every manifest function count equals its {_name} row count",
                  not _mm, "; ".join(_mm[:3]))
    else:
        print("  --    manifest.csv not present yet (run the tool to generate it)")

    if irows:
        # Every program the index says decompiled must have its .c on disk, and
        # every .c on disk must be accounted for by the index -- so a .c the
        # index does not cover (or an index row with no .c) is caught here rather
        # than read as a complete export.
        labels = {r["program"] for r in irows if r["out_file"] != "(failed)"}
        expected = {label + ".c" for label in labels}
        have = {f for f in os.listdir(DECOMPILED_DIR) if f.endswith(".c")} \
            if os.path.isdir(DECOMPILED_DIR) else set()
        check("every decompiled program in the index has its .c on disk",
              not (expected - have), ", ".join(sorted(expected - have)[:3]))
        # A .c for a program in PROJECT_EXCLUDED is accounted for by name.
        # The default build cannot produce it -- the program is not in the
        # project -- but the decompile is 56 MB of real analysis and deleting it
        # because the database that produced it does not fit in git would throw
        # away the work rather than the redundancy. It is retained, it is
        # named in the manifest, and this line is what says so; what it is not
        # is regenerated by `decompile_native.py` without a re-import.
        retained = retained_decompilations()
        unexpected = have - expected - retained
        check("every .c on disk is accounted for by the index, or is a "
              "documented retention", not unexpected,
              ", ".join(sorted(unexpected)[:3]))
        # Retained and the index's own set must not overlap: a .c the index
        # claims to produce is one a default build would overwrite, which is the
        # opposite of retained. The membership test that used to be here asked
        # whether the .c's own name is a key in PROJECT_EXCLUDED, and it was
        # asking about a key that could never be in that set -- the loop it was
        # in never ran, because the retained set it iterated was spelled the
        # same wrong way.
        for n in sorted(retained & have):
            check(f"{n} is retained output, not something the default build "
                  f"regenerates", n not in expected,
                  "the index claims to produce it, so a default build would "
                  "overwrite it")

    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


# --------------------------------------------------------------------------
# --self-test
# --------------------------------------------------------------------------

def do_self_test():
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"  ({detail})" if detail and not cond else ""))
        if not cond:
            ok = False

    print("decompile_native.py --self-test")
    # 17 columns, not 16. `notes` was added when the manifest grew a row for the
    # binary that is deliberately not in the project, and this assertion was not
    # updated with it -- so it had been failing on every run since, which made
    # `agent-gates.sh` exit non-zero on main. The header and the committed
    # manifest both carry 17; the assertion is what was wrong.
    check("manifest header is the documented 17 columns",
          MANIFEST_HEADER == [
              "program", "source", "sha256", "pdb_staged", "loader",
              "ghidra_version", "functions", "decompiled", "failed",
              "instruction_bytes", "body_bytes", "seeds_applied",
              "seeds_rejected", "annotations_applied", "annotations_unmatched",
              "mode", "notes"])
    check("index header is the shared exporter's 10 columns",
          INDEX_HEADER == ["program", "addr", "name", "size", "seed_basis",
                           "annotated", "type", "basis", "evidence", "out_file"])

    with open(TARGETS_CSV) as f:
        check("target CSV header is binary,kind,source,sha256,notes",
              f.readline().strip() == "binary,kind,source,sha256,notes")

    # The shared exporter must exist -- the whole point is to not carry a
    # second copy of it here.
    for rel in ("ghidra/scripts/ExportDecompile.java",
                "ghidra/scripts/ApplyAnnotations.java",
                "windows/ghidra/scripts/DisablePdbAnalyzer.java"):
        check(f"shared script present: {rel}", os.path.isfile(os.path.join(REPO, rel)))

    # Known-answer: committed PE sha + native-ness + the 55/55 record.
    sysp = os.path.join(REPO, "vendor/control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys")
    check("ACPIDriver.sys sha256 is the known value",
          sha256_file(sysp) == "9749f1c57e37f4eb7ee53c41219f3f7a4922799fd1201ad38de41c625461edb3")
    check("ACPIDriver.sys is a native (non-managed) PE", not is_managed_assembly(sysp))
    check("ACPIDriverDll.dll sha256 is the known value",
          sha256_file(os.path.join(REPO, "vendor/control-center-3.9.18.0/ACPIDriverDll.dll"))
          == "345cff34994351e126c4a7ef9ffc8e09fde005951f1a63af50d1945f28961a33")

    recs = [{"functions": 55, "decompiled": 55, "failed": 0, "body": 11796}]
    check("known 55/55/0 record is self-consistent",
          recs[0]["functions"] == recs[0]["decompiled"] + recs[0]["failed"])

    targets = {t["binary"]: t for t in load_targets()}
    for name in ("ACPIDriver.sys", "ACPIDriverDll.dll", "clrcompression.dll",
                 "UEFI_Firmware.dll", "GamingCenter3_Cross.exe",
                 "GamingCenter3_Cross.dll"):
        check(f"{name} is a target", name in targets)
    # The two GamingCenter3_Cross programs share a file stem; their export
    # labels must differ or the exporter would overwrite one (it now throws).
    check("same-stem GamingCenter3_Cross .exe/.dll get distinct export labels",
          export_label("GamingCenter3_Cross.exe") != export_label("GamingCenter3_Cross.dll"),
          "labels collide")
    check("export labels are unique across the whole target list",
          len({export_label(n) for n in targets}) == len(targets))
    check("every target kind is 'native'",
          all(t["kind"] == "native" for t in targets.values()))
    check("every source is committed or extract:",
          all(t["source"].startswith("extract:") or t["source"].startswith("vendor/")
              for t in targets.values()))

    # The listing parser, against a listing of its own. The two properties below
    # are the ones --check depends on, and both were wrong until this change: a
    # 9-hex-digit address matched nothing, so the check was passing over a parse
    # that had read nothing, and the loop read one file once per index row.
    _d = tempfile.mkdtemp(prefix="decompile_native_selftest_")
    try:
        _asm = "synthetic.asm"
        with open(os.path.join(_d, _asm), "w") as f:
            f.write("; a synthetic listing: two x86-64 instructions\n"
                    ";\n"
                    "140001000 48 89 5c 24 08 - - - - -      mov      qword ptr [RSP + 0x8], RBX\n"
                    "140001005 48 89 74 24 10 - - - - -      mov      qword ptr [RSP + 0x10], RSI\n"
                    "14000100A 57 - - - - - - - - -          push     RDI\n")
        _lines = [l for l in open(os.path.join(_d, _asm)).read().splitlines()
                  if _ADDRESS_LINE.match(l)]
        _got = _parse_listing_lines(_lines)
        check("a 9-hex-digit x86-64 address line parses (the width every address "
              "in these five listings has)", len(_lines) == 3 and len(_got) == 3,
              "%d line(s) matched, %d parsed" % (len(_lines), len(_got)))
        check("the bytes of an instruction are taken, up to the first dash",
              [b for _, b in _got] == ["48895c2408", "4889742410", "57"],
              str([b for _, b in _got]))
        # Ten thousand index rows naming one file must read it once. The count
        # the caller reports is the number of files read, so this is what makes
        # a per-program export cost what it should.
        _rows = [{"out_file": _asm} for _ in range(10000)]
        _insns, _unparsed, _read = parse_listings(_rows, _d)
        check("a repeated out_file is read once, so 10,000 index rows cost one "
              "file read", _read == 1 and _insns == 3 and not _unparsed,
              "%d file(s) read, %d instruction(s)" % (_read, _insns))
    finally:
        shutil.rmtree(_d, ignore_errors=True)

    # The real listing, for the same reason: the synthetic one proves the regex
    # is wide enough, this proves it is wide enough for what is committed.
    _committed = os.path.join(DECOMPILED_DIR, "ACPIDriver.asm")
    if os.path.isfile(_committed):
        _hits = len([l for l in open(_committed, errors="replace").read().splitlines()
                     if _ADDRESS_LINE.match(l)])
        check("the committed ACPIDriver.asm has address lines this parser matches",
              _hits > 0, "0 matched, so the parse would be vacuously passing")

    # The coverage check, on a manifest that agrees and one that does not. An
    # index that gained or lost rows without the manifest being regenerated is
    # the case it exists for, and the not-in-project row (no functions, no index
    # rows) is the case that must NOT trip it.
    check("coverage: a manifest that agrees with the index passes",
          not coverage_mismatches([{"program": "ACPIDriver.sys", "functions": "55"}],
                                  lambda label: 55))
    check("coverage: a not-in-project row, which records no functions, passes",
          not coverage_mismatches(
              [{"program": "GamingCenter3_Cross.dll", "functions": "0"}],
              lambda label: 0))
    _mm = coverage_mismatches([{"program": "ACPIDriver.sys", "functions": "54"}],
                              lambda label: 55)
    check("coverage: a manifest whose functions disagrees with the index fails",
          len(_mm) == 1 and "54" in _mm[0] and "55" in _mm[0], str(_mm))
    _mm = coverage_mismatches([{"program": "ACPIDriver.sys", "functions": ""}],
                              lambda label: 55)
    check("coverage: a manifest whose functions is not a number fails",
          len(_mm) == 1, str(_mm))

    # Duplicate keys and short rows, on both indexes.
    _dup = [{"program": "a", "addr": "140001000", "out_file": "a.c"}] * 2
    _p = index_structure_problems(_dup, [])
    check("a duplicated (program, addr) key is reported", len(_p) == 1, str(_p))
    _p = index_structure_problems(_dup, _dup)
    check("a duplicated key is reported in each of the two indexes",
          len(_p) == 2, str(_p))
    _p = index_structure_problems([{"program": "a", "addr": "140001000",
                                    "out_file": None}], [])
    check("a row with fewer fields than the header is reported", len(_p) == 1, str(_p))
    # DictReader collects a row with too many fields under the None restkey.
    _p = index_structure_problems([{"program": "a", "addr": "140001000",
                                    "out_file": "a.c", None: ["surplus"]}], [])
    check("a row with more fields than the header is reported", len(_p) == 1, str(_p))
    _p = index_structure_problems(
        [{"program": "a", "addr": "140001000", "out_file": "a.c"},
         {"program": "a", "addr": "1400010D0", "out_file": "a.c"}], [])
    check("two different addresses in one program are not a duplicate",
          not _p, str(_p))

    # The mode vocabulary: documented, and enforced from one place.
    check("every mode in use today is in the documented set",
          not manifest_mode_problems([{"program": p, "mode": m} for p, m in
                                      (("a", "rebuild-project"),
                                       ("b", "export-only"),
                                       ("c", "not-in-project"))]))
    _p = manifest_mode_problems([{"program": "a", "mode": "rebuild"}])
    check("a mode outside the documented set is rejected", len(_p) == 1, str(_p))
    check("the committed manifest uses only documented modes",
          not manifest_mode_problems(
              list(csv.DictReader(open(MANIFEST_CSV, newline="")))),
          "")

    # A retained decompile is named by its export label, and the name it is
    # given has to be a file that exists -- that is the whole point of the
    # carve-out, and spelling it from the binary instead gave a .c nothing here
    # can ever write, which is how two checks sat red with no explanation.
    _ret = retained_decompilations()
    check("a retained decompile is named by export label, not by the binary",
          _ret == {"GamingCenter3_Cross.c"}, str(sorted(_ret)))
    for _f in sorted(_ret):
        check("the retained decompile %s is actually on disk" % _f,
              os.path.isfile(os.path.join(DECOMPILED_DIR, _f)))

    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


# --------------------------------------------------------------------------
# main rebuild
# --------------------------------------------------------------------------

def do_rebuild(args):
    analyze_headless, java_home = find_ghidra()
    if not analyze_headless:
        raise SystemExit("error: analyzeHeadless not found (set GHIDRA_INSTALL_DIR "
                         "or ~/.local/opt/ghidra)")
    decompiler_preflight(analyze_headless)
    version = ghidra_version(analyze_headless)
    log(f"ghidra {version}, java_home={java_home}")

    targets = load_targets()
    if args.only:
        pat = args.only.lower()
        targets = [t for t in targets if pat in t["binary"].lower()]
        if not targets:
            raise SystemExit(f"error: no target matches {args.only!r}")
        log(f"--only {args.only!r}: {len(targets)} target(s)")
    excluded = [t for t in targets
                if os.path.basename(t["binary"]) in PROJECT_EXCLUDED
                and args.mode == "rebuild-project"]
    if excluded:
        targets = [t for t in targets if t not in excluded]
        for t in excluded:
            log("not importing %s: %s"
                % (t["binary"], PROJECT_EXCLUDED[os.path.basename(t["binary"])]))

    project_dir = args.project_dir or PROJECT_DIR
    manifest_path = args.manifest or MANIFEST_CSV
    index_path = args.index or INDEX_CSV
    outdir = args.outdir or DECOMPILED_DIR
    if args.mode == "rebuild-project":
        if os.path.isdir(project_dir):
            shutil.rmtree(project_dir)
    elif not os.path.isdir(project_dir):
        # export-only reuses an existing project; nothing to reuse is an error.
        raise SystemExit("error: project %s does not exist; run with "
                         "--mode rebuild-project first" % project_dir)
    # Ghidra aborts with "Directory not found" if the project dir is absent.
    os.makedirs(project_dir, exist_ok=True)

    scratch = tempfile.mkdtemp(prefix="decompile_native_")
    try:
        resolved = resolve_sources(targets, scratch)
        sha_by_binary = {t["binary"]: sha256_file(local) for t, local in resolved}

        # Refuse to import a managed assembly that slipped into the list.
        for t, local in resolved:
            if is_managed_assembly(local):
                raise SystemExit(
                    f"error: {t['binary']} is a managed (.NET) assembly; Ghidra "
                    "cannot decompile it. Remove it from native-binaries.csv "
                    "(managed code is ilspycmd's job, see tools/extract.sh).")

        # Split into the fast batch and (only with --pdb) the PDB-backed leg.
        # By DEFAULT every native target goes in one batch and
        # GamingCenter3_Cross.dll is imported WITHOUT its PDB: the binary is
        # still decompiled, it just carries no PDB-derived type names. The PDB
        # leg is opt-in because a 27 MB image with a 144 MB matching PDB did not
        # finish in 30 min on this machine even with the analyzer disabled.
        fast, pdb_job, pdb_labels = [], None, set()
        for t, local in resolved:
            if args.pdb:
                staged, is_pdb = stage_pdb(local, scratch)
            else:
                staged, is_pdb = local, False
            if is_pdb:
                pdb_job = (t, staged)
                pdb_labels.add(export_label(os.path.basename(t["binary"])))
            else:
                fast.append((t, staged))
        if not args.pdb:
            log("PDB: not staged (default). GamingCenter3_Cross.dll is decompiled "
                "without PDB symbols; pass --pdb for the (slow, opt-in) PDB leg.")

        index = index_path_stub(scratch)
        with open(index, "w", newline="") as f:
            f.write("\t".join(INDEX_HEADER) + "\n")
        listing_index = os.path.join(scratch, "listing-raw.csv")
        with open(listing_index, "w", newline="") as f:
            f.write("\t".join(INDEX_HEADER) + "\n")
        reports = os.path.join(scratch, "reports")
        out_work = os.path.join(scratch, "out")
        os.makedirs(reports, exist_ok=True)

        if fast:
            # One context for the whole batch. These are different files with
            # different sources and two of them share the stem
            # "GamingCenter3_Cross", so the context carries a programs= list, a
            # per-program label.<name>, and a per-program source.<name>; the
            # exporter resolves distinct output names and refuses a collision.
            batch_ctx = write_context(os.path.join(scratch, "context.txt"),
                                      fast, version, sha_by_binary)
            log(f"headless: importing {len(fast)} file(s) in one batch")
            rc, _ = export_batch(analyze_headless, project_dir,
                                 [p for _, p in fast], scratch, index,
                                 batch_ctx, out_work, reports,
                                 use_pdb_script=False,
                                 timeout_s=args.timeout or FAST_TIMEOUT_S,
                                 java_home=java_home,
                                 listing_index=listing_index,
                                 listings_out=out_work)
            if rc != 0:
                sys.stderr.write(open(os.path.join(scratch, "ghidra.log")).read())
                raise SystemExit(f"error: headless failed (rc={rc}) on fast batch")

        if pdb_job:
            log("PDB-backed import: GamingCenter3_Cross.dll (PDB staged, "
                "'PDB Universal' analyzer disabled by DisablePdbAnalyzer.java)")
            ctx = write_context(os.path.join(scratch, "context-pdb.txt"),
                                [pdb_job], version, sha_by_binary)
            rc, _ = export_batch(analyze_headless, project_dir, [pdb_job[1]],
                                 scratch, index, ctx, out_work, reports,
                                 use_pdb_script=True, timeout_s=PDB_TIMEOUT_S,
                                 java_home=java_home,
                                 listing_index=listing_index,
                                 listings_out=out_work)
            if rc != 0:
                sys.stderr.write(open(os.path.join(scratch, "ghidra.log")).read())
                raise SystemExit(f"error: headless failed (rc={rc}) on PDB import")

        # Copy the exported .c files out of scratch into the committed tree.
        if os.path.isdir(outdir):
            for f in os.listdir(outdir):
                if f.endswith(".c"):
                    os.remove(os.path.join(outdir, f))
        os.makedirs(outdir, exist_ok=True)
        for src_dir, suffix in ((out_work, ".c"), (out_work, ".asm")):
            if not os.path.isdir(src_dir):
                continue
            for f in os.listdir(src_dir):
                if f.endswith(suffix):
                    dst = os.path.join(outdir, f)
                    if os.path.isfile(dst):
                        os.remove(dst)
                    shutil.copy2(os.path.join(src_dir, f), dst)

        # The disassembly index: the same rows, out_file pointing at the .asm
        # beside each .c. Written from the exporter's own tab-separated scratch
        # file, which is the only place the per-program listing records what it
        # wrote.
        if os.path.isfile(listing_index):
            _rows = list(csv.DictReader(open(listing_index, newline=""),
                                         delimiter="\t"))
            os.makedirs(os.path.dirname(LISTING_INDEX), exist_ok=True)
            with open(LISTING_INDEX, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=INDEX_HEADER,
                                   extrasaction="ignore", lineterminator="\n")
                w.writeheader()
                for r in sorted(_rows, key=lambda r: r["program"]):
                    w.writerow(r)

        index_rows = parse_index(index)
        # Completeness gate. In per-program mode the exporter writes ONE
        # <label>.c per program (index out_file is empty for a decompiled row,
        # "(failed)" for a failure), so a program counts as exported iff it has
        # at least one non-failed row, and its .c must be on disk. A run that
        # died partway leaves a program short; this turns that into a hard
        # failure BEFORE any manifest is written, so a missing .c can never be
        # read as "nothing there".
        exported_labels = {r["program"] for r in index_rows
                           if r["out_file"] != "(failed)"}
        expected = {label + ".c" for label in exported_labels}
        have = {f for f in os.listdir(outdir) if f.endswith(".c")}
        missing = expected - have
        if missing:
            raise SystemExit(
                "error: export incomplete: %d program(s) have decompiled "
                "functions but no .c on disk (e.g. %s). The manifest is NOT "
                "written; re-run." % (len(missing), ", ".join(sorted(missing)[:3])))
        extra = have - expected
        if extra:
            raise SystemExit(
                "error: %d .c file(s) in the output dir are not accounted for by "
                "the index (e.g. %s); refusing to write a manifest that could "
                "misreport the export." % (len(extra), ", ".join(sorted(extra)[:3])))

        rows = build_manifest_rows(resolved, index_rows, scratch, version,
                                   args.mode, sha_by_binary, pdb_labels)
        write_manifest(rows, manifest_path, excluded=PROJECT_EXCLUDED)
        # The committed index, rewritten as CSV from the exporter's TSV.
        with open(index_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=INDEX_HEADER, lineterminator="\n")
            w.writeheader()
            for r in index_rows:
                w.writerow(r)
        log(f"wrote {manifest_path}: {len(rows)} program(s) in the project, "
            "%d recorded as not-in-project" % len(PROJECT_EXCLUDED))
        for r in rows:
            log(f"  {r['program']}: {r['decompiled']}/{r['functions']} decompiled, "
                f"{r['failed']} failed, {r['instruction_bytes']} instruction bytes, "
                f"{r['body_bytes']} body bytes")
    finally:
        if args.keep_scratch:
            log(f"scratch kept at {scratch}")
        else:
            shutil.rmtree(scratch, ignore_errors=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true",
                   help="no Ghidra, no network: verify hashes, counters, index")
    p.add_argument("--self-test", action="store_true",
                   help="known-answer assertions, no Ghidra")
    p.add_argument("--only", metavar="SUBSTR",
                   help="only import targets whose name contains SUBSTR")
    p.add_argument("--project-dir", metavar="DIR",
                   help=f"Ghidra project directory (default {PROJECT_DIR})")
    p.add_argument("--manifest", metavar="CSV", help=f"manifest output (default {MANIFEST_CSV})")
    p.add_argument("--index", metavar="CSV", help=f"index output (default {INDEX_CSV})")
    p.add_argument("--outdir", metavar="DIR", help=f"decompiled .c output (default {DECOMPILED_DIR})")
    p.add_argument("--mode", choices=("rebuild-project", "export-only"),
                   default="rebuild-project",
                   help="rebuild-project wipes the project first; export-only reuses it")
    p.add_argument("--pdb", action="store_true",
                   help="also stage GamingCenter3_Cross.pdb and run the PDB-backed "
                        "import (slow; opt-in, see README)")
    p.add_argument("--timeout", type=int, metavar="S",
                   help="seconds for the main batch (default %d). The batch "
                        "carries the 27 MB GamingCenter3_Cross.dll, which "
                        "needs more than the default on a cold page cache"
                        % FAST_TIMEOUT_S)
    p.add_argument("--keep-scratch", action="store_true", help="do not delete the scratch dir")
    args = p.parse_args()
    if args.check:
        return do_check()
    if args.self_test:
        return do_self_test()
    return do_rebuild(args)


if __name__ == "__main__":
    sys.exit(main())
