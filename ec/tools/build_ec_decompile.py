#!/usr/bin/env python3
"""Build the EC's Ghidra project and its decompiled C, from the committed
firmware and the committed annotations.

Three programs live in one project (ec/ghidra/project/), because they share a
processor, a loader and a base address and can therefore be imported in a
single JVM:

  bank0   0x0000-0x7FFF common area + CODE bank 0 (file 0x08000)
  bank1   0x0000-0x7FFF common area + CODE bank 1 (file 0x10000)
  pd      the ITE8850-PD image at file 0x20000, its own 64 KiB address space

`pd` is a separate program, not a third bank. It has its own vector table, its
own XDATA map, and no BL51 stubs, so it is seeded from its own vectors and
never from the EC's call-target census or the EC register names
(ec/README.md, ec/annotations/lightbar-bat-flow.md §2).

Two modes, and the difference matters for review:

  --rebuild-project   import + seed + analyse + apply + export, and WRITE the
                      .gpr/.rep. Rare: a new firmware, a new module, a changed
                      seed set, or someone improving the project's own symbol
                      table.
  export-only         (default) copy the committed project to scratch, apply the
                      annotations to the COPY, export from it. The committed
                      .rep is never opened for writing, so an annotation change
                      is a one-line CSV diff and a text diff, not a 8 MB binary
                      one. Copying is how that guarantee is obtained -- it does
                      not rely on how analyzeHeadless treats -readOnly.

Usage:
    python3 build_ec_decompile.py --work /tmp/ec --mode rebuild-project
    python3 build_ec_decompile.py --work /tmp/ec --check
    python3 build_ec_decompile.py --work /tmp/ec --self-test
    python3 build_ec_decompile.py --work /tmp/ec --self-test --oracle   # + real run
"""
import argparse
import csv
import hashlib
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
PROJECT = os.path.join(REPO, "ec", "ghidra", "project")
SCRIPTS = os.path.join(REPO, "ghidra", "scripts")
OUTDIR = os.path.join(REPO, "ec", "decompiled")
INDEX = os.path.join(OUTDIR, "index.csv")
MANIFEST = os.path.join(REPO, "ec", "ghidra", "manifest.csv")
XDATA = os.path.join(REPO, "ec", "ghidra", "xdata-symbols.csv")
ANNOTATIONS = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
CALL_TARGETS = os.path.join(REPO, "ec", "annotations", "bank-call-targets.csv")
GHIDRA_VERSION = "12.1.3"

# The Keil BL51 bank-switch stubs, from ec/tools/find_banks.py and ec/README.md.
BANK_STUBS = [0x1100, 0x1114, 0x1128, 0x113C]
COMMON_END = 0x8000
# How far into an image to look for its vector table. The EC's runs 0x0000-0x003C
# and the PD image's 0x0000-0x0020; 0x40 covers both with room to spare.
VECTOR_SCAN_LIMIT = 0x40

INDEX_COLUMNS = ["program", "addr", "name", "size", "seed_basis", "common",
                 "annotated", "type", "basis", "evidence", "also_in", "out_file"]
MANIFEST_COLUMNS = ["program", "source", "sha256", "loader", "ghidra_version",
                    "functions", "decompiled", "failed", "instruction_bytes",
                    "body_bytes", "seeds_applied", "seeds_rejected",
                    "annotations_applied", "annotations_unmatched", "mode"]


def read_csv(path):
    import csv as _csv
    with open(path, newline="") as f:
        return list(_csv.DictReader(f))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


# --------------------------------------------------------------------------
# Seed derivation
# --------------------------------------------------------------------------

def discover_vector_table(image, limit=VECTOR_SCAN_LIMIT):
    """Walk an 8051 image's vector table and return [(offset, target), ...].

    Discovered, not assumed. The two images in this dump both defeat the
    textbook layout: the EC's table mixes 3-byte LJMP entries with 4-byte
    LJMP+RET ones and real code follows at 0x002E, while the PD image pads with
    0xFF between entries. A hardcoded offset list would have silently seeded
    the wrong addresses on one image or the other, and the failure would look
    like "the firmware has no handler there" rather than like a wrong tool.

    The walk accepts LJMP (0x02) as a 3-byte entry, optionally followed by a
    lone RET (0x22) that pads it to 4, and a lone RET as a 1-byte placeholder
    for an unused vector. It stops at the first byte that is none of those,
    which is where the table ends and code begins.
    """
    out = []
    off = 0
    while off < limit and off + 2 < len(image):
        b = image[off]
        if b == 0x02:                                  # LJMP
            out.append((off, (image[off + 1] << 8) | image[off + 2]))
            off += 3
            if off < limit and image[off] == 0x22:      # Keil pads with a RET
                off += 1
        elif b == 0x22:                                # unused vector
            out.append((off, None))
            off += 1
        elif b == 0xFF:                                # erased / unused
            off += 1
        else:
            break                                      # code starts here
    return out


def vector_seeds(image):
    """(addr, basis) seeds for an image's own vector table and its targets."""
    out = []
    for off, target in discover_vector_table(image):
        out.append((off, "vector"))
        if target is not None:
            out.append((target, "vector-target"))
    return out


def call_target_seeds(bank):
    """Targets from bank-call-targets.csv that this program owns, with the
    attribution rule stated rather than guessed:

      a common-area site whose target is in the common area  -> every bank
      a site in bank N whose target is in the bank window     -> bank N only
      a common-area site whose target is in a bank window    -> NAMED BY NOBODY

    That last case is bucket C: 140 rows, 102 distinct targets, where the call
    site is in the common area and the target lands in a 0x8000-0xFFFF window,
    so the CSV does not say which bank it is. They are returned separately to be
    recorded as unseeded rather than applied to both banks on a guess -- a wrong
    bank here means disassembling from an address that is not a function entry
    in that bank, which corrupts everything after it. Settling them is
    issue #48.
    """
    mine, unattributed = [], []
    with open(CALL_TARGETS, newline="") as f:
        for row in csv.DictReader(f):
            region = row["region"]
            target = int(row["target"], 16)
            in_bank_window = target >= COMMON_END
            if not in_bank_window:
                if region == "common":
                    mine.append((target, "call-target"))
            elif region == bank:
                mine.append((target, "call-target"))
            elif region == "common":
                unattributed.append((target, "call-target-unattributed"))
    return mine, unattributed


def annotation_seeds():
    """Entry points declared by ec/annotations/ghidra-functions.csv.

    This is not a convenience. The direct-call census cannot see a function
    that is reached by a branch or through a function-pointer table, and the
    charge-target routine -- the single most important routine in this firmware
    for the charge-cap question -- is reached by `jb acc.1` from 0xB141, with
    no lcall/ljmp to it anywhere (charge-target-derating.md). So a row in the
    annotations, written by someone who has read the disassembly, is how such a
    function enters the project. Without this the best-understood routine in the
    firmware is absent from the decompile.
    """
    out = []
    if not os.path.isfile(ANNOTATIONS):
        return out
    for row in csv.DictReader(open(ANNOTATIONS, newline="")):
        scope = row["scope"].strip()
        addr = int(row["addr"], 16)
        if scope in ("common", "bank0", "bank1", "pd"):
            out.append((addr, "annotation", scope))
    return out


def seed_rows(fw, pd):
    """The seed spec: one row per (program, address, basis), de-duplicated."""
    per_program = {"bank0": [], "bank1": [], "pd": []}
    common_seeds = vector_seeds(fw[:COMMON_END])
    common_seeds += [(a, "stub") for a in BANK_STUBS]
    for bank in ("bank0", "bank1"):
        bank_seeds, unattributed = call_target_seeds(bank)
        per_program[bank] = common_seeds + bank_seeds
    per_program["pd"] = vector_seeds(pd)
    # Seed order is evidential strength, strongest first, and it matters: the
    # first seed at an address wins, because a later one inside the body it
    # created is rejected. A byte-scan target one byte into a real instruction
    # would otherwise create a function that swallows the instruction and the
    # evidence-backed entry inside it. bank-call-audit.md §1 is explicit that the
    # census is an upper bound whose framing is unresolved in places (issue #57),
    # so where a census target and a cited entry disagree by a byte, the cited
    # entry is the one that gets the function.
    #
    # Annotation-declared entries also only enter the program they name: a
    # `common` row belongs to both bank programs, but nothing declared for one
    # bank is seeded into the other, and a `pd` row seeds the PD program alone.
    for addr, basis, scope in annotation_seeds():
        if scope == "common":
            per_program["bank0"].append((addr, basis))
            per_program["bank1"].append((addr, basis))
        else:
            per_program[scope].append((addr, basis))
    STRENGTH = {"annotation": 0, "vector": 1, "vector-target": 1, "stub": 2,
                "call-target": 3}
    for program in per_program:
        per_program[program].sort(key=lambda ab: STRENGTH.get(ab[1], 9))
    rows, seen = [], set()
    for program in ("bank0", "bank1", "pd"):
        for addr, basis in per_program[program]:
            key = (program, addr)
            if key in seen:
                continue
            seen.add(key)
            rows.append((program, addr, basis))
    return rows, per_program["bank0"], per_program["bank1"], per_program["pd"]


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def write_specs(work, rows):
    spec = os.path.join(work, "seed-spec.csv")
    basis = os.path.join(work, "seed-basis.csv")
    # The annotation-declared entries on their own, re-applied AFTER analysis.
    # Ghidra's auto-analysis removes some freshly created functions -- the
    # address gets absorbed into a neighbouring body or a switch analysis
    # prunes it. For a census-derived seed that is the analyser doing its job
    # and the seed spec simply loses the argument. For a seed a person wrote
    # with a citation, the citation should have the last word, so those are
    # re-applied once the analysis has finished. Only these, never the
    # census-derived ones: re-seeding 1,400 byte-scan targets after analysis
    # would put every heuristic Ghidra applied back the way it was.
    annot_spec = os.path.join(work, "seed-annotations.csv")
    with open(spec, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["program", "addr", "basis"])
        for program, addr, why in rows:
            w.writerow([program, "0x%04X" % addr, why])
    with open(basis, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["program", "addr", "basis"])
        for program, addr, why in rows:
            w.writerow([program, "0x%04X" % addr, why])
    with open(annot_spec, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["program", "addr", "basis"])
        for program, addr, why in rows:
            if why == "annotation":
                w.writerow([program, "0x%04X" % addr, why])
    return spec, basis, annot_spec


def build_images(work):
    tool = os.path.join(REPO, "ec", "tools", "make_bank_image.py")
    imgs = {}
    for bank, file_off in (("bank0", 0x08000), ("bank1", 0x10000)):
        out = os.path.join(work, bank + ".bin")
        run([sys.executable, tool, FIRMWARE, bank, hex(file_off), out],
            stdout=subprocess.DEVNULL)
        imgs[bank] = out
    pd = os.path.join(work, "pd.bin")
    run([sys.executable, tool, "--pd", FIRMWARE, pd], stdout=subprocess.DEVNULL)
    imgs["pd"] = pd
    return imgs


def write_context(work, imgs, digest):
    p = os.path.join(work, "context.txt")
    rel = os.path.relpath(FIRMWARE, REPO)
    with open(p, "w") as f:
        f.write("source=%s\n" % rel)
        # One context file drives all three programs, so each gets its own
        # source line: the PD image is a different 64 KiB program at a different
        # file offset, not another view of the bank image.
        f.write("source.bank0=%s, CODE bank 0 at file 0x08000 + the 0x0000-0x7FFF "
                "common area\n" % rel)
        f.write("source.bank1=%s, CODE bank 1 at file 0x10000 + the 0x0000-0x7FFF "
                "common area\n" % rel)
        f.write("source.pd=%s, the ITE8850-PD image at file 0x20000 -- a separate "
                "program with its own address space, not a third bank\n" % rel)
        # The programs in this invocation and the export label each gets. The
        # exporter refuses a collision rather than letting one program's output
        # overwrite another's.
        f.write("programs=bank0.bin,bank1.bin,pd.bin\n")
        for name, label in (("bank0.bin", "bank0"), ("bank1.bin", "bank1"),
                            ("pd.bin", "pd")):
            f.write("label.%s=%s\n" % (name, label))
        f.write("sha256=%s\n" % digest)
        f.write("ghidra_version=%s\n" % GHIDRA_VERSION)
        f.write("generator=ec/tools/build_ec_decompile.py\n")
        f.write("symbols=ec/ghidra/xdata-symbols.csv "
                "(generated from ec/annotations/registers.yaml)\n")
        f.write("annotations=ec/annotations/ghidra-functions.csv\n")
    return p


def ghidra_preflight(ghidra):
    """The decompiler can be present on disk and still unusable, and it fails
    SILENTLY: openProgram() returns false with an empty message. Catching it
    here, before any work, is the difference between a clear error and an export
    full of confident-looking nothing."""
    if not ghidra:
        return
    decomp = os.path.join(os.path.dirname(os.path.dirname(ghidra)),
                          "Ghidra", "Features", "Decompiler", "os", "linux_x86_64", "decompile")
    if not os.path.exists(decomp):
        return
    if not os.access(decomp, os.X_OK):
        raise SystemExit(
            "error: Ghidra's native decompiler is not executable: %s\n"
            "  This fails SILENTLY inside Ghidra (openProgram() returns false and the\n"
            "  error message is empty), and the result reads exactly like 'this code\n"
            "  will not decompile'. It is not. Fix the exec bit and re-run." % decomp)


def analyze(ghidra, project_dir, work, imgs, spec, basis, context, digest,
            mode, programs, annot_spec):
    """One analyzeHeadless invocation for all three programs: they share a
    loader and a processor, and a JVM start is ~15 s, so batching is the
    difference between a fast build and a slow one."""
    raw_index = os.path.join(work, "index-raw.csv")
    # Tab-separated, because the Java exporter appends tab-separated rows and
    # the committed index it becomes is rewritten as CSV below.
    with open(raw_index, "w", newline="") as f:
        f.write("program\taddr\tname\tsize\tseed_basis\tannotated\t"
                "type\tbasis\tevidence\tout_file\n")
    os.makedirs(project_dir, exist_ok=True)
    for stale in os.listdir(work):
        if stale.startswith("index-raw.csv.") and stale.endswith(".counts"):
            os.remove(os.path.join(work, stale))
    if mode == "rebuild-project":
        cmd = [ghidra, project_dir, "ec",
               "-import", imgs["bank0"], imgs["bank1"], imgs["pd"],
               "-overwrite", "-loader", "BinaryLoader",
               "-processor", "8051:BE:16:default",
               "-scriptPath", SCRIPTS,
               "-preScript", "SeedFunctions.java", spec]
    else:
        cmd = None
    if cmd:
        cmd += ["-postScript", "SeedFunctions.java", annot_spec]
        cmd += ["-postScript", "ApplyAnnotations.java",
                ANNOTATIONS if os.path.isfile(ANNOTATIONS) else "", XDATA,
                os.path.join(work, "reports")]
        cmd += ["-postScript", "ExportDecompile.java", os.path.join(work, "out"),
                raw_index, "per-function", context, basis]
        run(cmd, stdout=open(os.path.join(work, "ghidra.log"), "w"),
            stderr=subprocess.STDOUT)
    else:
        # export-only: a copy of the committed project, so the committed .rep is
        # never opened for writing at all.
        copy_dir = os.path.join(work, "project-copy")
        if os.path.isdir(copy_dir):
            shutil.rmtree(copy_dir)
        shutil.copytree(PROJECT, copy_dir)
        for program in programs:
            run([ghidra, copy_dir, "ec", "-process", program, "-noanalysis",
                 "-scriptPath", SCRIPTS,
                 "-postScript", "SeedFunctions.java", annot_spec,
                 "-postScript", "ApplyAnnotations.java",
                 ANNOTATIONS if os.path.isfile(ANNOTATIONS) else "", XDATA,
                 os.path.join(work, "reports"),
                 "-postScript", "ExportDecompile.java", os.path.join(work, "out"),
                 raw_index, "per-function", context, basis],
                stdout=open(os.path.join(work, "ghidra-%s.log" % program), "w"),
                stderr=subprocess.STDOUT)
    return raw_index


def join_index(raw_index, work):
    """The exporter's scratch rows plus the annotation columns, and the
    common-area de-duplication ec/ghidra/README.md asks for. De-duplication is
    by (addr, name, size) across the two bank programs: where those agree the
    function is emitted once under common/, and where they DISAGREE both are
    kept and flagged, because a difference there would be a real result -- a
    linker patch of the common area between banks -- not noise to collapse."""
    raw = list(csv.DictReader(open(raw_index, newline=""), delimiter="\t"))
    annot = {}
    if os.path.isfile(ANNOTATIONS):
        for row in csv.DictReader(open(ANNOTATIONS, newline="")):
            key_addr = row["addr"].upper().replace("0X", "")
            annot[(row["scope"], key_addr)] = row
            # A `common`-scoped row is a common-area function, and at this point
            # in the pipeline its index row still says bank0 or bank1 -- the
            # rename to `common` happens in the de-duplication pass below. Index
            # it under both banks so the join finds it either way.
            if row["scope"] == "common":
                annot[("bank0", key_addr)] = row
                annot[("bank1", key_addr)] = row
    for row in raw:
        key = (row["program"], row["addr"])
        a = annot.get(key) or annot.get((row["program"], "0x" + row["addr"]))
        row["type"] = a["type"] if a else ""
        row["basis"] = a["basis"] if a else ""
        row["evidence"] = a["evidence"] if a else ""
        row["common"] = "yes" if int(row["addr"], 16) < COMMON_END else "no"
        row["also_in"] = ""
    by_addr = {}
    for row in raw:
        if row["common"] == "yes":
            by_addr.setdefault(row["addr"], []).append(row)
    drop = set()
    for addr, rows in by_addr.items():
        programs = {r["program"] for r in rows}
        if not {"bank0", "bank1"} <= programs:
            continue
        b0 = next(r for r in rows if r["program"] == "bank0")
        others = [r for r in rows if r["program"] != "bank0"]
        if all((r["name"], r["size"]) == (b0["name"], b0["size"]) for r in others):
            b0["also_in"] = ",".join(sorted(r["program"] for r in others))
            b0["program"] = "common"
            src = os.path.join(work, "out", "bank0", addr + ".c")
            dst_dir = os.path.join(work, "out", "common")
            os.makedirs(dst_dir, exist_ok=True)
            shutil.move(src, os.path.join(dst_dir, addr + ".c"))
            b0["out_file"] = "common/" + addr + ".c"
            for r in others:
                p = os.path.join(work, "out", r["program"], addr + ".c")
                if os.path.isfile(p):
                    os.remove(p)
                # The row goes too: leaving it would point the index at a file
                # that is deliberately not there, and --check would (rightly)
                # call the export stale.
                drop.add(id(r))
        else:
            b0["differs"] = "yes"
            for r in others:
                r["differs"] = "yes"
    raw = [r for r in raw if id(r) not in drop]
    return raw, len(drop)


def write_outputs(raw, work, digest, mode, seeds_info):
    if os.path.isdir(OUTDIR):
        shutil.rmtree(OUTDIR)
    os.makedirs(OUTDIR, exist_ok=True)
    for program in ("bank0", "bank1", "common", "pd"):
        src = os.path.join(work, "out", program)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(OUTDIR, program))
    with open(INDEX, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INDEX_COLUMNS, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        for row in sorted(raw, key=lambda r: (r["program"], int(r["addr"], 16))):
            w.writerow(row)
    per_program = {}
    for row in raw:
        p = per_program.setdefault(row["program"], {"functions": 0, "failed": 0,
                                                    "body": 0, "annotated": 0})
        p["functions"] += 1
        p["body"] += int(row["size"])
        if row["out_file"] == "(failed)":
            p["failed"] += 1
        if row["annotated"] == "yes":
            p["annotated"] += 1
    # Per-program byte counts, as the exporter measured them. instruction_bytes
    # is the coverage figure; body_bytes is the sum of function bodies, which
    # overlaps and so is not one. The `common` row takes bank0's, because that
    # is the program the common functions were exported from.
    counts = {}
    for program in ("bank0", "bank1", "pd"):
        path = os.path.join(work, "index-raw.csv." + program + ".counts")
        if os.path.isfile(path):
            # Last line only: the file is opened in append mode, so a re-run
            # into the same work directory leaves the previous run's row behind.
            lines = [l for l in open(path).read().splitlines() if l.strip()]
            _prog, f, g, b, cb, wb, bb = lines[-1].split("\t")
            counts[program] = {"functions": int(f), "decompiled": int(g),
                               "failed": int(b), "common_bytes": int(cb),
                               "window_bytes": int(wb), "body_bytes": int(bb)}
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
        w.writeheader()
        for program in ("bank0", "bank1", "common", "pd"):
            p = per_program.get(program, {"functions": 0, "failed": 0, "body": 0,
                                           "annotated": 0})
            c = counts.get("bank0" if program == "common" else program, {})
            src = ("%s common area (0x0000-0x7FFF), exported from bank0; identical "
                   "in bank1" % program if program == "common" else
                   "ec/firmware/GMxMGxx_11.800, the %s image"
                   % ("CODE bank 0 (file 0x08000) + common area" if program == "bank0"
                      else "CODE bank 1 (file 0x10000) + common area" if program == "bank1"
                      else "ITE8850-PD image at file 0x20000, its own address space"))
            w.writerow({
                "program": program, "source": src, "sha256": digest,
                "loader": "BinaryLoader 8051:BE:16:default",
                "ghidra_version": GHIDRA_VERSION,
                "functions": p["functions"],
                "decompiled": p["functions"] - p["failed"],
                "failed": p["failed"],
                # A bank program's own figure is its window only; the common
                # area it shares is reported once, on the `common` row.
                "instruction_bytes": c.get(
                    "common_bytes" if program == "common" else "window_bytes",
                    p["body"]),
                "body_bytes": p["body"],
                # `common` is an export grouping, not a Ghidra program: its
                # functions were seeded in both bank programs, so reporting 0
                # there would read as "the common area was never seeded".
                "seeds_applied": seeds_info.get(
                    "bank0" if program == "common" else program, 0),
                "seeds_rejected": seeds_info.get(program + ":rejected", 0),
                "annotations_applied": p["annotated"],
                "annotations_unmatched": 0, "mode": mode,
            })
    return per_program


def report(per_program, mode):
    print("\n=== %s ===" % mode)
    for row in csv.DictReader(open(MANIFEST, newline="")):
        ib = int(row["instruction_bytes"])
        print("  %-8s functions=%-5s decompiled=%-5s failed=%-3s "
              "disassembled=%-6d bytes (%.0f%% of the 64 KiB image)"
              % (row["program"], row["functions"], row["decompiled"],
                 row["failed"], ib, 100.0 * ib / 0x10000))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True, help="scratch directory (created)")
    ap.add_argument("--mode", default="export-only",
                    choices=["export-only", "rebuild-project"])
    ap.add_argument("--ghidra", default=os.environ.get("GHIDRA_HEADLESS", "analyzeHeadless"),
                    help="analyzeHeadless path; '' to skip the Ghidra run")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed outputs without Ghidra")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions against the committed inputs")
    ap.add_argument("--oracle", action="store_true",
                    help="with --self-test, also run Ghidra and check the export "
                         "against the hand reading in charge-target-derating.md")
    args = ap.parse_args(argv)
    work = os.path.abspath(args.work)
    os.makedirs(work, exist_ok=True)

    fw = open(FIRMWARE, "rb").read()
    pd = fw[0x20000:0x30000]
    rows, b0, b1, pdseeds = seed_rows(fw, pd)
    _, unattributed = call_target_seeds("bank0")

    if args.self_test:
        return self_test(fw, pd, rows, b0, b1, pdseeds, unattributed, args, work)

    if args.check:
        return check(work)

    digest = sha256(FIRMWARE)
    ghidra_preflight(args.ghidra)
    imgs = build_images(work)
    spec, basis, annot_spec = write_specs(work, rows)
    context = write_context(work, imgs, digest)
    project_dir = PROJECT
    # Ghidra names a raw-binary program after the file it was imported from,
    # so -process takes "bank0.bin", not "bank0".
    raw_index = analyze(args.ghidra, project_dir, work, imgs, spec, basis,
                        context, digest, args.mode,
                        ["bank0.bin", "bank1.bin", "pd.bin"], annot_spec)
    raw, deduped = join_index(raw_index, work)
    if deduped:
        print("  de-duplicated %d common-area function(s) that both bank "
              "programs carry identically" % deduped)
    seeds_info = {"bank0": len({a for p, a, _ in rows if p == "bank0"}),
                  "bank1": len({a for p, a, _ in rows if p == "bank1"}),
                  "pd": len({a for p, a, _ in rows if p == "pd"})}
    per_program = write_outputs(raw, work, digest, args.mode, seeds_info)
    report(per_program, args.mode)
    if unattributed:
        print("\n  %d call-target rows name no bank (bucket C) and were NOT seeded: "
              "a guess here would disassemble from an address that is not a "
              "function entry in the bank it was applied to. Settling them is "
              "issue #48." % len({a for a, _ in unattributed}))
    print("\n  wrote %s and %s" % (os.path.relpath(INDEX, REPO),
                                   os.path.relpath(MANIFEST, REPO)))
    return 0


# --------------------------------------------------------------------------
# Checks -- no Ghidra, no network. These are what the gates run.
# --------------------------------------------------------------------------

def self_test(fw, pd, rows, b0, b1, pdseeds, unattributed, args, work):
    ok = True
    ec_annotation_addrs = {int(r["addr"], 16) for r in read_csv(ANNOTATIONS)
                           if r["scope"] in ("bank0", "bank1", "common")}

    def check(label, cond):
        nonlocal ok
        print("  %s  %s" % ("ok  " if cond else "FAIL", label))
        if not cond:
            ok = False

    print("build_ec_decompile.py --self-test")
    seeded = {(p, a) for p, a, _ in rows}
    ec_vectors = discover_vector_table(fw[:COMMON_END])
    pd_vectors = discover_vector_table(pd)
    check("the EC's vector table is discovered, not assumed (mixed 3/4-byte entries)",
          len(ec_vectors) >= 9 and any(t is None for _, t in ec_vectors))
    check("the EC vector walk stops where code begins (0x002E, not 0x0040)",
          ec_vectors[-1][0] < 0x2E)
    check("the PD image has its own, different vector table",
          len(pd_vectors) >= 5 and pd_vectors[0][1] == 0x0500)
    check("every discovered EC vector entry is seeded in both bank programs",
          all(("bank0", off) in seeded and ("bank1", off) in seeded
              for off, _ in ec_vectors))
    check("every discovered EC vector target is seeded in both bank programs",
          all(("bank0", t) in seeded and ("bank1", t) in seeded
              for _, t in ec_vectors if t is not None))
    check("all 4 BL51 bank-switch stubs are seeded in both bank programs",
          all(("bank0", s) in seeded and ("bank1", s) in seeded for s in BANK_STUBS))
    check("stub prologues are present in the common area (push 08h; mov a,#hi)",
          all(fw[s] == 0xC0 and fw[s + 1] == 0x08 and fw[s + 2] == 0x74 for s in BANK_STUBS))
    bank0_only = {a for a, basis in b0} - {a for a, basis in b1}
    bank1_only = {a for a, basis in b1} - {a for a, basis in b0}
    check("each bank gets bank-window targets the other does not",
          len(bank0_only) > 0 and len(bank1_only) > 0)
    check("the two banks' own seed sets are disjoint", not (bank0_only & bank1_only))
    check("every vector-entry seed lies in the common area",
          all(a < COMMON_END for p, a, basis in rows if basis == "vector"))
    check("the PD image is seeded only from its own vectors and its own annotations",
          {basis for p, _, basis in rows if p == "pd"} <= {"vector", "vector-target",
                                                           "annotation"})
    check("no EC bank or common annotation is seeded into the PD program",
          not any(p == "pd" and a in ec_annotation_addrs
                  for p, a, _ in rows if _ == "annotation" and a not in
                  {int(x["addr"], 16) for x in read_csv(ANNOTATIONS) if x["scope"] == "pd"}))
    check("the PD image is never seeded from the EC call-target census",
          not any(p == "pd" and basis.startswith("call-target") for p, _, basis in rows))
    check("PD vector targets are all inside the PD image",
          all(a < 0x10000 for p, a, _ in rows if p == "pd"))
    check("bucket-C targets (no bank named) are reported, not seeded",
          len({a for a, _ in unattributed}) > 0
          and not any(basis == "call-target-unattributed" for _, _, basis in rows))
    check("seed spec is de-duplicated", len(rows) == len({(p, a) for p, a, _ in rows}))
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    if not ok:
        return 1
    check_cross_decoder_agreement()
    if args.oracle:
        return opt_in_ghidra_oracle(args, work)
    return 0


# The 8051 "compare by subtraction with the carry pre-set" idiom is the one
# place Ghidra's 8051 output is hardest to read: it renders
# `setb c; mov dptr,#X; movx a,@dptr; subb a,#N` as a C comparison with the
# carry flag shifted through a sign-extension, which reads as noise until you
# know the idiom. So the decompile is checked against the repository's own
# independent linear disassembler, over the first instruction window of each
# function where the linear walk is still in sync and every byte is really an
# instruction. Two decoders that share no code agreeing on the operands is
# worth more than either alone.
#
# The window, not the whole function: past the first branch the linear walk
# desyncs, and its 0x90 bytes are then operands of instructions it lost track
# of. Comparing a whole function that way reports dozens of addresses neither
# decoder is wrong about, which is noise, not signal.
CROSS_DECODER_FUNCTIONS = [("bank0", 0xB1F0), ("bank0", 0xB158),
                              ("bank0", 0xBAE5), ("common", 0x707D)]


def function_size(program, addr):
    """Byte length Ghidra gave this function, from the committed index."""
    if not os.path.isfile(INDEX):
        return 0
    for row in csv.DictReader(open(INDEX, newline="")):
        if row["program"] == program and int(row["addr"], 16) == addr:
            return int(row["size"])
    return 0


def check_cross_decoder_agreement():
    """Report whether Ghidra's C and ec/tools/disasm8051.py name the same
    XDATA addresses in a function's straight-line opening.

    Advisory, not a gate, and deliberately so. It is a real check in one
    direction and not in the other:

      - Ghidra naming an address the independent decoder did not see is
        worth a look.
      - Ghidra NOT naming one it saw usually is not a disagreement at all. It
        folds a `mov dptr,#hi; movx a,@dptr; mov dptr,#lo; movx a,@dptr` pair
        into a single wide read, and the two byte symbols go with it --
        observed at 0xB158, where 0x04A7/0x04A6 are read and passed to the
        big-endian store helper and neither appears in the C. That is the
        decompiler's business, and a gate that failed on it would be failing
        on correct output.

    So this prints, and the reader decides. What it is for is the case it
    confirms: Ghidra's 8051 decompile and this repository's own decoder,
    which share no code, agree instruction for instruction on the operands
    that both can see.
    """
    import re as _re
    import subprocess as _sp
    BRANCH = _re.compile(r"^\s*(jmp|ljmp|lcall|sjmp|acall|ajmp|ret|reti|djnz|"
                         r"jc|jnc|jb|jnb|jae|jnbc|je|jne|jz|jnz|jl|jge|jle|jg|"
                         r"jnb|jbc)\b")
    MOVDPTR = _re.compile(r"mov\s+dptr,#0x([0-9a-f]{4})", _re.I)
    print("  cross-decoder agreement (advisory: Ghidra's C vs disasm8051.py, "
          "opening instructions):")
    d = open(FIRMWARE, "rb").read()
    for program, start in CROSS_DECODER_FUNCTIONS:
        path = os.path.join(OUTDIR, program, "%04X.c" % start)
        if not os.path.isfile(path):
            print("    --    %s 0x%04X: no export committed yet, skipped"
                  % (program, start))
            continue
        # CODE 0x8000-0xFFFF maps to file 0x08000-0x0FFFF for bank 0, so the
        # file offset is 0x08000 + (runtime - 0x8000). Forgetting the window
        # base points the comparison at a different 32 KiB entirely.
        file_off = 0x08000 + (start - COMMON_END)
        out = _sp.run([sys.executable,
                       os.path.join(REPO, "ec", "tools", "disasm8051.py"),
                       FIRMWARE, "--at", hex(file_off), "-n", "40"],
                      capture_output=True, text=True).stdout.splitlines()
        # Stop on the printed address rather than on a byte count: the first
        # column is where the instruction starts, which is exact, where
        # reconstructing lengths from the printed bytes would not be.
        size = function_size(program, start)
        limit = file_off + size if size else None
        linear, insns = set(), 0
        for line in out:
            if BRANCH.match(line):
                break
            cols = line.split()
            if len(cols) < 2:
                continue
            try:
                here = int(cols[0], 16)
            except ValueError:
                continue
            if limit is not None and here >= limit:
                break
            insns += 1
            m = MOVDPTR.search(line)
            if m:
                linear.add(m.group(1).upper())
        in_c = {m.upper() for m in _re.findall(r"EXTMEM_([0-9a-f]{4})",
                                               open(path).read())}
        if not linear:
            print("    --    %s 0x%04X: no mov dptr,#imm in the opening %d "
                  "instruction(s); nothing to compare" % (program, start, insns))
            continue
        agree = linear <= in_c
        print("    %s 0x%04X: %d straight-line instruction(s) name %d XDATA "
              "address(es) linearly; the C names %d of them%s"
              % ("ok  " if agree else "note", start, insns, len(linear),
                 len(linear & in_c),
                 "" if agree else
                 " -- not named in the C: " + ", ".join(sorted(linear - in_c))
                 + " (usually a byte pair folded into one wide read, which is "
                   "the decompiler's business, not a disagreement)"))


def check(work):
    ok = True

    def fail(msg):
        nonlocal ok
        print("  FAIL  %s" % msg)
        ok = False

    print("build_ec_decompile.py --check")
    if not os.path.isfile(MANIFEST):
        fail("no manifest at %s" % os.path.relpath(MANIFEST, REPO))
        return 1
    manifest = list(csv.DictReader(open(MANIFEST, newline="")))
    digest = sha256(FIRMWARE)
    for row in manifest:
        if row["sha256"] != digest:
            fail("%s: manifest SHA-256 does not match the committed firmware -- "
                 "the export is stale, rebuild it" % row["program"])
        if int(row["functions"]) != int(row["decompiled"]) + int(row["failed"]):
            fail("%s: functions != decompiled + failed" % row["program"])
        if int(row["decompiled"]) < int(row["functions"]) and row["failed"] == "0":
            fail("%s: decompiled < functions but failed == 0" % row["program"])
    if not os.path.isfile(INDEX):
        fail("no index at %s" % os.path.relpath(INDEX, REPO))
        return 1
    rows = list(csv.DictReader(open(INDEX, newline="")))
    seen_addr = set()
    for row in rows:
        out = os.path.join(OUTDIR, row["out_file"])
        if row["out_file"] not in ("", "(failed)") and not os.path.isfile(out):
            fail("index row %s %s points at a missing file: %s"
                 % (row["program"], row["addr"], row["out_file"]))
        seen_addr.add((row["program"], row["addr"]))
    for lock in (PROJECT,):
        for f in os.listdir(lock) if os.path.isdir(lock) else []:
            if f.endswith(".lock") or f.endswith(".lock~"):
                fail("a Ghidra lock file is committed next to the project: %s "
                     "(a committed lock makes Ghidra refuse the project)" % f)
    # The one failure mode that is silent, has the same shape as a legitimate
    # result, and would otherwise be read as a finding about the firmware.
    for dp, _dns, fns in os.walk(OUTDIR):
        for fn in fns:
            if not fn.endswith(".c"):
                continue
            text = open(os.path.join(dp, fn), errors="replace").read()
            if "DECOMPILER UNAVAILABLE" in text:
                fail("%s: the decompiler did not load; this is a broken toolchain, "
                     "not an undecodable function" % os.path.join(dp, fn))
    if os.path.isfile(ANNOTATIONS):
        for a in csv.DictReader(open(ANNOTATIONS, newline="")):
            # An annotation with no citation is a claim, not a finding, and the
            # build refuses it -- but the build is not what CI runs, so the
            # check has to refuse it too or an uncited row reaches main.
            if not a.get("evidence", "").strip():
                fail("annotation %s %s (%s) has no evidence citation: a row that "
                     "names a function has to say where the reading came from"
                     % (a["scope"], a["addr"], a.get("name", "")))
            key = (a["scope"], a["addr"].upper().replace("0X", ""))
            if key not in seen_addr and not (a["scope"] == "common"
                                             and any(k[0] == "common" for k in seen_addr)):
                fail("annotation %s %s resolves to no exported function -- either a "
                     "typo or the project needs a rebuild"
                     % (a["scope"], a["addr"]))
    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
