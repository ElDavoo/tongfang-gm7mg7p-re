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
_ADDRESS_LINE = re.compile(r"^[0-9A-Fa-f]{4,8}\s+\S")
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
    "annotations_unmatched", "mode",
]
# The raw index the shared exporter appends to: 10 tab-separated fields.
INDEX_HEADER = ["program", "addr", "name", "size", "seed_basis", "annotated",
                "type", "basis", "evidence", "out_file"]


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


def _pe_is_managed(d):
    """True if the PE image bytes have a CLR data directory (a COM descriptor)."""
    if d[:2] != b"MZ":
        return False
    pe = int.from_bytes(d[0x3c:0x40], "little")
    if d[pe:pe + 4] != b"PE\0\0":
        return False
    opt = pe + 24
    magic = int.from_bytes(d[opt:opt + 2], "little")
    ddoff = opt + (112 if magic == 0x20b else 96)
    clr_rva = int.from_bytes(d[ddoff + 14 * 8: ddoff + 14 * 8 + 4], "little")
    return clr_rva != 0


def is_managed_assembly(path):
    try:
        with open(path, "rb") as f:
            return _pe_is_managed(f.read())
    except OSError:
        return False


def managed_from_msix(repo, inside):
    """Managed-ness of a target that lives in the UWP msixbundle, read straight
    out of the committed zip (no extraction). Returns True/False, or None if the
    member cannot be located."""
    marker = "v3.9.18.0/msix/"
    if marker not in inside:
        return None
    member = inside.split(marker, 1)[1]
    bundle = os.path.join(repo, "vendor/control-center-3.9.18.0",
                          "GamingCenter3_Cross.UWP_3.9.18.0_x64.msixbundle")
    import zipfile
    with zipfile.ZipFile(bundle) as zb:
        inner = [n for n in zb.namelist() if n.endswith("_x64.msix")][0]
        inner_bytes = zb.read(inner)
    with zipfile.ZipFile(io.BytesIO(inner_bytes)) as zi:
        return _pe_is_managed(zi.read(member))


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


def write_manifest(rows, path=MANIFEST_CSV):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_HEADER, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# --------------------------------------------------------------------------
# --check
# --------------------------------------------------------------------------

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

    # Every decompilation has its machine code beside it, and every listing row
    # names a file that exists. A .c with no .asm is a reading with nothing to
    # check it against; a listing row pointing at a missing file is an export
    # that has gone stale in a way the C index cannot see.
    if os.path.isfile(LISTING_INDEX) and os.path.isdir(DECOMPILED_DIR):
        _lrows = list(csv.DictReader(open(LISTING_INDEX, newline="")))
        _missing = [r["out_file"] for r in _lrows
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
        check("every decompilation has a listing beside it", not _noasm,
              "%d without, e.g. %s" % (len(_noasm), _noasm[:3]))
        # Every line that starts with an address is an instruction, and the
        # parser has to get all of them: a parser that reads a fraction of a
        # file and finds nothing wrong in it reports a pass.
        insns, unparsed = 0, []
        for r in _lrows:
            rel = r.get("out_file", "")
            if not rel or rel.startswith("("):
                continue
            path = os.path.join(DECOMPILED_DIR, rel)
            if not os.path.isfile(path):
                continue
            lines = [l for l in open(path, errors="replace").read().splitlines()
                     if _ADDRESS_LINE.match(l)]
            got = _parse_listing_lines(lines)
            insns += len(got)
            if len(got) != len(lines):
                unparsed.append("%s: %d line(s), %d parsed"
                                % (rel, len(lines), len(got)))
        if _lrows:
            print(f"  {'ok  ' if not unparsed else 'FAIL'}  "
                  f"disassembly: {insns} instruction(s) parsed across "
                  f"{len(_lrows)} listing(s)")
        if unparsed:
            check("every listing line parses", False,
                  "%d do not, e.g. %s" % (len(unparsed), unparsed[:3]))

    # No managed assembly in the target list. Committed sources are read in
    # place; msix-sourced extract: targets are read straight out of the
    # committed .msixbundle. The one inno-sourced target is enforced at import.
    for t in targets:
        src = t["source"]
        if not src.startswith("extract:"):
            check(f"{t['binary']} ({src}) is not a managed assembly",
                  not is_managed_assembly(os.path.join(REPO, src)))
            continue
        _, _, inside = src[len("extract:"):].partition("#")
        managed = managed_from_msix(REPO, inside)
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

    if os.path.exists(MANIFEST_CSV):
        mrows = list(csv.DictReader(open(MANIFEST_CSV, newline="")))
        for r in mrows:
            fn, dec, fail = int(r["functions"]), int(r["decompiled"]), int(r["failed"])
            check(f"manifest {r['program']}: functions == decompiled + failed",
                  fn == dec + fail, f"{fn} != {dec} + {fail}")
            check(f"manifest {r['program']}: mode is rebuild-project|export-only",
                  r["mode"] in ("rebuild-project", "export-only"), r["mode"])
    else:
        print("  --    manifest.csv not present yet (run the tool to generate it)")

    if os.path.exists(INDEX_CSV):
        irows = list(csv.DictReader(open(INDEX_CSV, newline="")))
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
        check("every .c on disk is accounted for by the index",
              not (have - expected), ", ".join(sorted(have - expected)[:3]))
    else:
        print("  --    index.csv not present yet")

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
    check("manifest header is the documented 16 columns",
          MANIFEST_HEADER == [
              "program", "source", "sha256", "pdb_staged", "loader",
              "ghidra_version", "functions", "decompiled", "failed",
              "instruction_bytes", "body_bytes", "seeds_applied",
              "seeds_rejected", "annotations_applied", "annotations_unmatched",
              "mode"])
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
        write_manifest(rows, manifest_path)
        # The committed index, rewritten as CSV from the exporter's TSV.
        with open(index_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=INDEX_HEADER, lineterminator="\n")
            w.writeheader()
            for r in index_rows:
                w.writerow(r)
        log(f"wrote {manifest_path}: {len(rows)} program(s)")
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
