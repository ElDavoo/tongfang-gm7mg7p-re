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
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
PROJECT = os.path.join(REPO, "ec", "ghidra", "project")
SCRIPTS = os.path.join(REPO, "ghidra", "scripts")
OUTDIR = os.path.join(REPO, "ec", "decompiled")
INDEX = os.path.join(OUTDIR, "index.csv")
# The disassembly index, one row per function, out_file pointing at the .asm
# that sits beside the .c of the same address. Same columns as INDEX on purpose:
# the two files describe the same functions, and a reader should be able to join
# them on (program, addr) without a translation table.
LISTING_INDEX = os.path.join(OUTDIR, "listing-index.csv")
MANIFEST = os.path.join(REPO, "ec", "ghidra", "manifest.csv")
XDATA = os.path.join(REPO, "ec", "ghidra", "xdata-symbols.csv")
ANNOTATIONS = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
# The variable layer, over the same export. A separate file from the function
# layer because a function's row IS a function -- annotation_seeds() below
# reads every row's addr as a seed and join_index() keys one row per
# (scope, addr) -- and a function with eight parameters cannot be eight rows
# in that file. ec/annotations/README.md has the format.
VARIABLES = os.path.join(REPO, "ec", "annotations", "ghidra-variables.csv")
REGISTERS = os.path.join(REPO, "ec", "annotations", "registers.yaml")
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
                    "annotations_applied", "annotations_unmatched",
                    "variables_functions", "variables_applied",
                    "variables_unmatched", "mode"]
# What the manifest's `mode` column may say. Kept as data because it is a
# controlled vocabulary and a vocabulary is only enforced if something reads it
# from one place: here the two modes the driver can produce, and --mode reads
# the same tuple rather than repeating it.
MANIFEST_MODES = ("export-only", "rebuild-project")

# The variable layer's `kind`, a closed vocabulary and not decoration. Most
# `param_N` in this export are not parameters at all: 45 rows of
# ghidra-functions.csv already say so about their own, and a sweep that gave
# every one of them a confident semantic name would manufacture false precision
# on exactly the rows this repository has flagged as misleading. `unresolved` is
# a result, not a failure, and mirrors how `type` treats it.
VARIABLE_KINDS = ("param", "local", "return", "artifact", "unresolved")


def read_csv(path):
    import csv as _csv
    with open(path, newline="") as f:
        return list(_csv.DictReader(f))

# The annotation layer's own header, transcribed from ec/ghidra/README.md's "The
# annotation layer" and tabulated in ec/annotations/README.md. Asserted rather
# than assumed, because this is the file a person or an agent edits to improve
# a decompile and the tool reads its rows by column name: a column that moves
# is a change in what every row means, and nothing else here would say so.
ANNOTATION_COLUMNS = ["scope", "addr", "name", "signature", "type", "comment",
                      "evidence", "basis"]
# bank-call-targets.csv, as ec/tools/audit_call_targets.py's write_csv() emits
# it. Also asserted rather than assumed, for the same reason with a sharper
# edge: `region` is the column that decides which bank a site belongs to, and a
# wrong bank here means disassembling from an address that is not a function
# entry there (call_target_seeds' docstring).
CALL_TARGET_COLUMNS = ["file_offset", "region", "runtime", "opcode", "target",
                       "bucket", "frame_onto", "frame_over", "calls_stub",
                       "calls_trampoline", "own_bank", "other_bank"]


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


def call_target_rows():
    """bank-call-targets.csv, read strictly and structurally validated once.

    Once per invocation, not once per bank: a short row and a duplicate
    `(file_offset, target)` are whole-file properties, so re-running the
    check for each of the two banks (and again for the bucket-C report) buys
    nothing -- it is a whole-file check paid a per-row price, the shape §14d
    found in the self-test."""
    rows = read_index(CALL_TARGETS)
    problems = structure_problems("bank-call-targets.csv", rows, call_target_key,
                                  "(file_offset, target)")
    if problems:
        raise SystemExit("error: bank-call-targets.csv is not sound: "
                         + "; ".join(problems[:3]))
    return rows


def call_target_seeds(bank, census):
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

    `census` is the validated read from call_target_rows(), passed in rather
    than re-read here, so the two banks and the bucket-C report below are three
    views of one parse."""
    mine, unattributed = [], []
    for row in census:
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


def annotation_rows():
    """ec/annotations/ghidra-functions.csv, read strictly and structurally
    validated, or [] when the file is not there.

    The empty case is the tool's long-standing one -- the build runs without the
    annotations -- so the file being absent is not an error here, while a file
    that is present and unsound is. A duplicate `(scope, addr)` is the case
    worth stopping for: join_index() below fills a dict keyed on it, so the
    second row would silently win, and which of the two is the better reading is
    not something a last-wins assignment can report."""
    if not os.path.isfile(ANNOTATIONS):
        return []
    rows = read_index(ANNOTATIONS)
    problems = structure_problems("ghidra-functions.csv", rows, annotation_key,
                                  "(scope, addr)")
    if problems:
        raise SystemExit("error: ghidra-functions.csv is not sound: "
                         + "; ".join(problems[:3]))
    return rows


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
    for row in annotation_rows():
        scope = row["scope"].strip()
        addr = int(row["addr"], 16)
        if scope in ("common", "bank0", "bank1", "pd"):
            out.append((addr, "annotation", scope))
    return out


def seed_rows(fw, pd, census):
    """The seed spec: one row per (program, address, basis), de-duplicated."""
    per_program = {"bank0": [], "bank1": [], "pd": []}
    common_seeds = vector_seeds(fw[:COMMON_END])
    common_seeds += [(a, "stub") for a in BANK_STUBS]
    for bank in ("bank0", "bank1"):
        bank_seeds, unattributed = call_target_seeds(bank, census)
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
        # Both annotation files, because the provenance header this key becomes
        # is read by someone asking "where did this identifier come from?" --
        # and a file that names only the function layer answers wrongly for every
        # variable name in it.
        f.write("annotations=ec/annotations/ghidra-functions.csv; "
                "ec/annotations/ghidra-variables.csv\n")
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
    # A second index for the disassembly, same columns, out_file pointing at the
    # .asm beside each .c. It is a separate file because the two answer different
    # questions -- one is a reading of the bytes, the other is the bytes -- and
    # merging them would invite a reader to take a decompiled line as if it were
    # an instruction.
    raw_listing = os.path.join(work, "listing-raw.csv")
    with open(raw_listing, "w", newline="") as f:
        f.write("program\taddr\tname\tsize\tseed_basis\tannotated\t"
                "type\tbasis\tevidence\tout_file\n")
    os.makedirs(project_dir, exist_ok=True)
    for stale in os.listdir(work):
        if stale.startswith("index-raw.csv.") and stale.endswith(".counts"):
            os.remove(os.path.join(work, stale))
        if stale.startswith("listing-raw.csv.") and stale.endswith(".listing-counts"):
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
                os.path.join(work, "reports"),
                VARIABLES if os.path.isfile(VARIABLES) else "-"]
        cmd += ["-postScript", "ExportDecompile.java", os.path.join(work, "out"),
                raw_index, "per-function", context, basis]
        cmd += ["-postScript", "ExportListing.java", os.path.join(work, "out"),
                raw_listing, "per-function", context, basis]
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
                 VARIABLES if os.path.isfile(VARIABLES) else "-",
                 "-postScript", "ExportDecompile.java", os.path.join(work, "out"),
                 raw_index, "per-function", context, basis,
                 "-postScript", "ExportListing.java", os.path.join(work, "out"),
                 raw_listing, "per-function", context, basis],
                stdout=open(os.path.join(work, "ghidra-%s.log" % program), "w"),
                stderr=subprocess.STDOUT)
    return raw_index, raw_listing


def join_index(raw_index, raw_listing, work):
    """The exporters' scratch rows plus the annotation columns, and the
    common-area de-duplication ec/ghidra/README.md asks for. De-duplication is
    by (addr, name, size) across the two bank programs: where those agree the
    function is emitted once under common/, and where they DISAGREE both are
    kept and flagged, because a difference there would be a real result -- a
    linker patch of the common area between banks -- not noise to collapse.

    Both indexes are de-duplicated in one pass, and the .c and .asm files move
    together: a decompiled C with no listing beside it, or a listing with no C,
    is the failure mode this pairing exists to prevent."""
    raw = list(csv.DictReader(open(raw_index, newline=""), delimiter="\t"))
    listing = list(csv.DictReader(open(raw_listing, newline=""), delimiter="\t"))
    annot = {}
    # Read through the validating reader, so the structural check has already
    # run before this dict assignment: a duplicate key used to be last-wins
    # here, and which of the two rows is the better reading is not a question
    # a dict can answer.
    for row in annotation_rows():
        key_addr = norm_addr(row["addr"])
        annot[annotation_key(row)] = row
        # A `common`-scoped row is a common-area function, and at this point
        # in the pipeline its index row still says bank0 or bank1 -- the
        # rename to `common` happens in the de-duplication pass below. Index
        # it under both banks so the join finds it either way.
        if row["scope"] == "common":
            annot[("bank0", key_addr)] = row
            annot[("bank1", key_addr)] = row
    for rows in (raw, listing):
        for row in rows:
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
    listing_drop = set()
    for addr, rows in by_addr.items():
        programs = {r["program"] for r in rows}
        if not {"bank0", "bank1"} <= programs:
            continue
        b0 = next(r for r in rows if r["program"] == "bank0")
        # bank1 and bank1 only. The PD image is a separate 64 KiB program with
        # its own address space (ec/README.md; ec/annotations/lightbar-bat-flow.md
        # §2), so its 0x0012 is not the EC's 0x0012 and must never be folded in
        # with it. It used to be: `others` was everything that was not bank0, so
        # a PD function that happened to share an address, a name and a size
        # with the common area was emitted once under common/ and its own
        # pd/<addr>.c and .asm were deleted. The index row disappeared with them
        # and every gate still passed, because a row that is gone cannot point
        # at a file that is gone.
        others = [r for r in rows if r["program"] == "bank1"]
        if all((r["name"], r["size"]) == (b0["name"], b0["size"]) for r in others):
            b0["also_in"] = "bank1"
            b0["program"] = "common"
            dst_dir = os.path.join(work, "out", "common")
            os.makedirs(dst_dir, exist_ok=True)
            for ext in (".c", ".asm"):
                src = os.path.join(work, "out", "bank0", addr + ext)
                if os.path.isfile(src):
                    shutil.move(src, os.path.join(dst_dir, addr + ext))
                if ext == ".c":
                    b0["out_file"] = "common/" + addr + ".c"
            for r in others:
                for ext in (".c", ".asm"):
                    p = os.path.join(work, "out", r["program"], addr + ext)
                    if os.path.isfile(p):
                        os.remove(p)
                # The row goes too: leaving it would point the index at a file
                # that is deliberately not there, and --check would (rightly)
                # call the export stale.
                drop.add(id(r))
            listing_drop.add(addr)
        else:
            b0["differs"] = "yes"
            for r in others:
                r["differs"] = "yes"
    # The listing's common rows are matched by address, not by identity with the
    # C index: the two exporters count a function's bytes slightly differently
    # (body vs. instruction extent), so keying the listing on the C's size
    # would drop listings that are perfectly good.
    for row in listing:
        if row["addr"] in listing_drop and row["program"] == "bank0":
            row["also_in"] = "bank1"
            row["program"] = "common"
            if row["out_file"] and not row["out_file"].startswith("("):
                row["out_file"] = "common/" + row["addr"] + ".asm"
    listing = [r for r in listing
               if not (r["addr"] in listing_drop and r["program"] == "bank1")]
    raw = [r for r in raw if id(r) not in drop]
    return raw, listing, len(drop)


def apply_report_counters(work):
    """The variable-layer counters ApplyAnnotations.java wrote, keyed by program.

    Read back rather than recomputed, because the script's own count is the
    only one that knows what the decompiler actually found: a row whose key the
    decompiler no longer produces looks identical to a row that was never
    written, from out here. The driver could count the CSV's rows and would get
    that wrong the first time `--mode rebuild-project` consumed a key.

    A program with no report file is a program the script never ran on, which
    is zero of everything rather than a missing entry.
    """
    out = {}
    reports = os.path.join(work, "reports")
    if not os.path.isdir(reports):
        return out
    for fn in sorted(os.listdir(reports)):
        if not (fn.startswith("apply-") and fn.endswith(".tsv")):
            continue
        program = fn[len("apply-"):-len(".tsv")]
        counts = {}
        for line in open(os.path.join(reports, fn), errors="replace"):
            key, _, value = line.partition("\t")
            if key in ("variables_functions", "variables_applied",
                       "variables_unmatched"):
                try:
                    counts[key] = int(value.strip())
                except ValueError:
                    pass
        out[program] = counts
    return out


def write_outputs(raw, listing, work, digest, mode, seeds_info, var_counts):
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
    # The disassembly index, same columns, pointing at the .asm beside each .c.
    with open(LISTING_INDEX, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INDEX_COLUMNS, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        for row in sorted(listing, key=lambda r: (r["program"], int(r["addr"], 16))):
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
            v = var_counts.get("bank0" if program == "common" else program, {})
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
                # Left at 0 and reconciled as separate work: this driver used to
                # write a constant here and never read the report back, which is
                # how 25 index rows came to claim an annotation that is no
                # longer in the CSV. The variable counters below are read back
                # from the start, so they do not start that way.
                "annotations_unmatched": 0,
                "variables_functions": v.get("variables_functions", 0),
                "variables_applied": v.get("variables_applied", 0),
                "variables_unmatched": v.get("variables_unmatched", 0),
                "mode": mode,
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
    ap.add_argument("--mode", default="export-only", choices=MANIFEST_MODES)
    ap.add_argument("--ghidra", default=os.environ.get("GHIDRA_HEADLESS", "analyzeHeadless"),
                    help="analyzeHeadless path; '' to skip the Ghidra run")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed outputs without Ghidra")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions against the committed inputs")
    ap.add_argument("--oracle", action="store_true",
                    help="with --self-test, also run Ghidra and check the export "
                         "against the hand reading in charge-target-derating.md")
    ap.add_argument("--cross-decoder", action="store_true",
                    help="with --self-test, also compare Ghidra's C against "
                         "ec/tools/disasm8051.py over each sampled function's "
                         "opening instructions. Advisory: it prints, it does not "
                         "fail the run, and it is what the deep gate tier runs "
                         "(.github/scripts/agent-gates-deep.sh)")
    args = ap.parse_args(argv)
    work = os.path.abspath(args.work)
    os.makedirs(work, exist_ok=True)

    # --check first, and ahead of the seed derivation, because it needs none of
    # it: a committed CSV that does not parse should be a failed check that
    # names the file, and running the build path first turned that into a
    # traceback out of a reader --check had not reached yet.
    if args.check:
        return check(work)

    fw = open(FIRMWARE, "rb").read()
    pd = fw[0x20000:0x30000]
    # One validated read of the census, shared by the seed set and the
    # bucket-C report below.
    census = call_target_rows()
    rows, b0, b1, pdseeds = seed_rows(fw, pd, census)
    _, unattributed = call_target_seeds("bank0", census)

    if args.self_test:
        return self_test(fw, pd, rows, b0, b1, pdseeds, unattributed, args, work)

    digest = sha256(FIRMWARE)
    ghidra_preflight(args.ghidra)
    imgs = build_images(work)
    spec, basis, annot_spec = write_specs(work, rows)
    context = write_context(work, imgs, digest)
    project_dir = PROJECT
    # Ghidra names a raw-binary program after the file it was imported from,
    # so -process takes "bank0.bin", not "bank0".
    raw_index, raw_listing = analyze(args.ghidra, project_dir, work, imgs, spec, basis,
                                     context, digest, args.mode,
                                     ["bank0.bin", "bank1.bin", "pd.bin"], annot_spec)
    raw, listing, deduped = join_index(raw_index, raw_listing, work)
    if deduped:
        print("  de-duplicated %d common-area function(s) that both bank "
              "programs carry identically" % deduped)
    seeds_info = {"bank0": len({a for p, a, _ in rows if p == "bank0"}),
                  "bank1": len({a for p, a, _ in rows if p == "bank1"}),
                  "pd": len({a for p, a, _ in rows if p == "pd"})}
    var_counts = apply_report_counters(work)
    per_program = write_outputs(raw, listing, work, digest, args.mode, seeds_info,
                                var_counts)
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

def read_index(path):
    """Rows of a committed CSV, read strictly.

    `strict=True` is the point. csv's default reader is forgiving about quoting
    in the one way that hides an error rather than raising it: a bad quote ends
    the row early, the row comes back with a missing field, and every count
    taken from it is then quietly smaller than the file. A quoting mistake in a
    committed CSV is exactly the kind of thing that should be loud, and it
    costs nothing to make it so."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def norm_addr(addr):
    """An address as a key: uppercase, `0x` prefix stripped.

    Both spellings are in the committed files and both are in use -- 1,039
    annotation rows carry a bare `0EA2` and 730 a `0x0B158` -- so a plain string
    key would call the two forms of one address two different functions and miss
    the duplicate that is the whole point of looking. --self-test asserts that
    the raw and the normalised key count agree over the committed file, which is
    what makes the normalisation a fact about the data rather than an assumption
    about it."""
    return addr.upper().replace("0X", "")


def index_key(row):
    return (row["program"], row["addr"])


def annotation_key(row):
    return (row["scope"], norm_addr(row["addr"]))


def call_target_key(row):
    return (norm_addr(row["file_offset"]), norm_addr(row["target"]))


def structure_problems(name, rows, key_of, key_label="key"):
    """Rows that did not come out whole, and a key that appears twice.

    The one copy of the rule, called once per committed file with that file's
    own `key_of`. It is header-agnostic on purpose: each file has its own
    column count, and a check written against one of them would call every row
    of the others short.

    A short row is a missing field and a surplus one is DictReader's `None`
    restkey; either leaves a dict without a value that a later check reads, so
    the row is reported and stepped over rather than keyed on. A duplicate key
    is a file appended to twice or a de-dup that missed one, and it stops the
    row count meaning what the counts around it are for."""
    out = []
    seen = set()
    for i, r in enumerate(rows, start=2):
        if None in r or any(v is None for v in r.values()):
            out.append(f"{name}: line {i} has fewer or more fields than the header")
            continue
        key = key_of(r)
        if key in seen:
            out.append(f"{name}: duplicate {key_label} {key}")
        seen.add(key)
    return out


def index_structure_problems(index_rows, listing_rows):
    """Structural faults in the two committed indexes: rows that did not come
    out with the full header, and `(program, addr)` keys that appear twice.

    A duplicate key is an export appended to twice, or a de-dup that missed one;
    either way the row count no longer means "number of functions", which is
    the only thing the counts around it are for. Two calls into the one keyed
    rule rather than a second copy of it."""
    return (structure_problems("index.csv", index_rows, index_key, "(program, addr)")
            + structure_problems("listing-index.csv", listing_rows, index_key,
                                 "(program, addr)"))


def coverage_mismatches(manifest_rows, count_for_program):
    """Manifest rows whose recorded `functions` is not the row count the index
    carries for that program.

    `count_for_program` maps a program name to its row count in an index. No
    label translation goes in between, unlike the Windows check: this manifest's
    `program` column and the index's are the same four strings (`bank0`,
    `bank1`, `common`, `pd`), so a `common` row is compared like any other
    rather than skipped as an export grouping. It is a grouping, and it is also
    753 of the index's 2,710 rows, which is more than a grouping may cost
    quietly."""
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
                       "%d row(s) for it. Something is dropping rows after the "
                       "export -- a de-duplication that spans programs, or a "
                       "filter that should not be there." % (program, recorded, got))
    return out


def manifest_mode_problems(manifest_rows):
    """Manifest rows whose `mode` is outside the two the driver produces."""
    return ["%s: mode is %r, not one of %s"
            % (r.get("program", "?"), r.get("mode"), "|".join(MANIFEST_MODES))
            for r in manifest_rows if r.get("mode") not in MANIFEST_MODES]


# "X has no entry in ec/annotations/registers.yaml" is a house idiom: a plate
# comment saying what a byte is *not* yet. It goes stale the moment the byte is
# entered, and a stale one is worse than a missing one -- it is a confident,
# checkable, wrong sentence sitting in the file a reader opens to find out what
# is known. The 0x0400-0x045F sweep left fifteen of them (issue #176).
#
# The check is address-scoped because most of those sentences also name addresses
# the YAML genuinely does not hold, and those claims are findings: "0x060C has
# no entry" is true, and dropping it to tidy a sentence would trade one
# overclaim for another.

# A 4-hex-digit address literal. Two of these in a row separated by a dash is
# the range notation ("0x0F60-0x0F63") and yields both ends, which is the
# claim's own reading of itself.
_XDATA_LITERAL = re.compile(r"0x([0-9A-Fa-f]{4})\b")
# Any address-shaped token, wildcards included. A subject written in this
# notation has named its targets in a form the scan below cannot enumerate.
_XDATA_SHAPED = re.compile(r"\b0x[0-9A-Fa-fxX*]*", re.I)
# Sentence boundaries *and* semicolons. The split is what clears the false
# positives: the sentences that need it are the ones that say both things in one
# breath -- "registers.yaml documents 0x044F as GPU_TEMP; 0x0A49, 0x0A4A and
# 0x098C have no entry there" -- and read as a single unit the first half looks
# like a claim about 0x044F, so the check would demand an edit that is not
# warranted. A guard that fires on correct prose is a guard that gets deleted.
#
# The period rule is `(?<!yaml)\.(?=\s)`: a period ends a sentence unless it is
# the dot in `registers.yaml`, the one dotted token these comments carry. A
# period after a hex literal does end one, and has to -- one comment's "these
# bytes" reaches back across exactly that boundary.
_CLAUSE_SPLIT = re.compile(r";|(?<!yaml)\.(?=\s)|(?<=[!?])\s")
# <verb> <no|an> entry, the determiner captured so a positive claim can be told
# from a negative one.
_ENTRY_IDIOM = re.compile(r"\b(?:has|have|is|are|was|were)\s+(no|an?)\s+entry\b",
                          re.I)
# The quantifiers that turn `has an entry` into a negative claim. `not` is
# deliberately not among them: "it is not an entry" in this tree is about a
# function entry point, and reading that as a claim about the YAML would police
# a sentence which says nothing of the kind.
_NEGATIVE_QUANT = re.compile(r"\b(?:none|neither|either)\b", re.I)


def comment_clauses(text):
    """The clauses of a plate comment -- the unit a 'has no entry' claim governs."""
    return [c for c in _CLAUSE_SPLIT.split(text) if c.strip()]


def registered_addresses(path=REGISTERS):
    """Every XDATA address ec/annotations/registers.yaml carries an entry for.

    Read from the YAML rather than from the generated `xdata-symbols.csv`
    because the claim being policed is a claim *about the YAML*: the two can
    disagree, and it is the YAML a reader opens. A file that will not parse
    raises rather than returning an empty set -- a check that could not run must
    not be indistinguishable from one that found nothing.
    """
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    out = set()
    for entry in (data or {}).get("registers") or []:
        addrs = entry.get("addr")
        for a in (addrs if isinstance(addrs, list) else [addrs]):
            if a is not None:
                out.add(int(a))
    return out


def stale_no_entry_claims(ann_rows, entered):
    """Annotation comments claiming registers.yaml holds no entry for an address
    it does hold. One message per (row, address), naming the address.

    The address is in the message on purpose: without it a false positive and a
    real finding look the same, and the reader's only recourse is to re-derive
    the whole scan by hand. With it, the claim that fired can be checked against
    the row in front of them.

    The five forms the idiom takes in this tree all resolve in three steps:

      1. find the idiom, and work within the clause that carries it;
      2. the claim's subject is the text between the clause start and the verb
         -- or, where a quantifier introduces it ("none of 0x0434 or 0x060C has
         an entry"), the text after the quantifier;
      3. a subject naming no address is a pronoun ("neither address", "none of
         these bytes"), and the addresses it refers to are the ones named in the
         text before the clause.

    Step 3 is what the two quantified forms need and why they need nothing else:
    their addresses are two or three sentences back, and the clause-local view
    would see a bare pronoun and stop there.
    """
    out = []
    for row in ann_rows:
        text = row.get("comment") or ""
        clauses = comment_clauses(text)
        for i, clause in enumerate(clauses):
            for m in _ENTRY_IDIOM.finditer(clause):
                # "0x06EB has an entry" is a positive claim and is not this
                # check's business. Only `no entry`, or a quantifier in front of
                # the verb, is the idiom.
                if m.group(1).lower() != "no" \
                        and not _NEGATIVE_QUANT.search(clause[:m.start()]):
                    continue
                subject = clause[:m.start()]
                quant = list(_NEGATIVE_QUANT.finditer(subject))
                if quant:
                    subject = subject[quant[-1].end():]
                if _XDATA_SHAPED.search(subject) \
                        and not _XDATA_LITERAL.search(subject):
                    # "none of the 0x08xx or 0x09xx destinations has an entry":
                    # the targets are named in a notation this scan cannot
                    # enumerate. Left alone rather than widened to a guess --
                    # a check that guesses here demands edits nobody can check.
                    continue
                if _XDATA_LITERAL.search(subject):
                    governed = {int(h, 16) for h in _XDATA_LITERAL.findall(subject)}
                else:
                    governed = set()
                    for prior in clauses[:i]:
                        governed |= {int(h, 16)
                                     for h in _XDATA_LITERAL.findall(prior)}
                for addr in sorted(governed & entered):
                    out.append("%s %s (%s) says an address has no entry in "
                               "ec/annotations/registers.yaml, but 0x%04X is in "
                               "it -- reword the clause, or correct the claim"
                               % (row["scope"], row["addr"],
                                  row.get("name", ""), addr))
    return out


def decompiled_code(path):
    """The C body of an exported function, with the plate comment removed.

    The plate comment is where a function's own annotation lives, and several
    of those comments DISCUSS their own `param_N` by name -- 0x901C's says
    "param_1 is a pointer the decompiler invented, not a 8051 calling
    convention". That sentence is the reading, and it stays. So the check that
    a renamed placeholder is GONE has to look at the code rather than the whole
    file, or it would refuse the very rows whose comments explain what the
    placeholder was.
    """
    try:
        text = open(path, errors="replace").read()
    except OSError:
        return None
    end = text.find("*/")
    return text[end + 2:] if end >= 0 else text


def variable_csv_problems(vrows, index_rows, xdata_names):
    """Faults in ec/annotations/ghidra-variables.csv, measured on the committed export.

    The load-bearing assertion is bidirectional: a NAMED row's `name` must
    appear in the committed `.c` and its `key` must not. A typo'd name is not
    in the output, and a key the build already consumed -- which is what
    `--mode rebuild-project` does to it, permanently -- is caught by the other
    half. Either alone would be satisfied by a file that had simply stopped
    being regenerated.

    The scope is the CODE, not the file: see decompiled_code(). A function's
    own plate comment is allowed to name the placeholder it is explaining.

    A `kind=unresolved` row is the one case where the key is supposed to
    survive, and it is checked as such rather than exempted: the row's content
    is its comment, and a comment about an unnamed variable is worth carrying.
    """
    out = []
    for row in vrows:
        scope = (row.get("scope") or "").strip()
        addr = (row.get("addr") or "").strip()
        key = (row.get("key") or "").strip()
        name = (row.get("name") or "").strip()
        kind = (row.get("kind") or "").strip()
        label = "variable %s %s %s" % (scope, addr, key or "(no key)")
        if kind not in VARIABLE_KINDS:
            out.append("%s: kind %r is outside the controlled vocabulary"
                       % (label, kind))
        if kind == "unresolved" and name:
            # unresolved means the listing does not say, and the placeholder
            # stays. A name on such a row is the whole failure this vocabulary
            # exists to prevent, so it is refused here as well as in
            # ApplyAnnotations.java -- the two layers must not disagree about
            # which rows are allowed.
            out.append("%s: kind=unresolved with the name %s; unresolved means "
                       "the placeholder stays in place" % (label, name))
        if not (row.get("evidence") or "").strip():
            out.append("%s: no evidence citation; a variable annotation without "
                       "one is a claim, not a finding" % label)
        if not key:
            out.append("%s: no key; a row has to name the placeholder it replaces"
                       % label)
        if name and name in xdata_names:
            msg = ("%s: name %s is an EC XDATA register name, and the variable "
                   "layer must not be a back door for register naming -- that "
                   "is registers.yaml's discipline, not this file's"
                   % (label, name))
            if scope == "pd":
                msg += ("; and the PD image has its own XDATA map, so an EC "
                        "register name there is an overclaim whatever the row "
                        "says about it")
            out.append(msg)
        norm = addr.upper().replace("0X", "")
        idx = index_rows.get((scope, norm))
        if idx is None:
            out.append("%s: resolves to no exported function -- a typo, or the "
                       "project needs --mode rebuild-project" % label)
            continue
        out_file = idx.get("out_file") or ""
        if not out_file or out_file == "(failed)":
            out.append("%s: index row for %s %s has no exported .c to check"
                       % (label, scope, addr))
            continue
        code = decompiled_code(os.path.join(OUTDIR, out_file))
        if code is None:
            out.append("%s: committed .c at %s is missing" % (label, out_file))
            continue
        if not name:
            # unresolved: the placeholder stays, and the row's content is its
            # comment. Asserted, not skipped -- a row that says "the listing
            # does not say" has to correspond to a placeholder that is there.
            if not re.search(r"\b%s\b" % re.escape(key), code):
                out.append("%s: kind=unresolved leaves %s in place, but the "
                           "committed .c does not contain it"
                           % (label, key or "(no key)"))
            continue
        if not re.search(r"\b%s\b" % re.escape(name), code):
            out.append("%s: the committed .c does not contain the name it asked "
                       "for -- a typo, or the export predates the row" % label)
        if key and re.search(r"\b%s\b" % re.escape(key), code):
            out.append("%s: the committed .c still contains the placeholder %s, "
                       "so the rename did not take" % (label, key))
    return out


def xdata_symbol_names(path=XDATA):
    """Every name ec/ghidra/xdata-symbols.csv carries, whatever program it names."""
    if not os.path.isfile(path):
        return set()
    return {r["name"].strip()
            for r in csv.DictReader(open(path, newline=""))
            if (r.get("name") or "").strip()}


def self_test(fw, pd, rows, b0, b1, pdseeds, unattributed, args, work):
    ok = True
    # One read of the annotations CSV, split by scope. The PD set used to be
    # built inside the generator of the check that uses it, so it re-read and
    # re-parsed the whole file once per seed row -- 1,790 times, which is where
    # this self-test's 18 s went. The EC-side set had been hoisted already; only
    # the PD one had not, and the two now read the file once between them.
    _ann = annotation_rows()
    _ct = call_target_rows()
    ec_annotation_addrs = {int(r["addr"], 16) for r in _ann
                           if r["scope"] in ("bank0", "bank1", "common")}
    pd_annotation_addrs = {int(r["addr"], 16) for r in _ann if r["scope"] == "pd"}

    def check(label, cond, detail=""):
        nonlocal ok
        print("  %s  %s" % ("ok  " if cond else "FAIL", label)
              + ("  (%s)" % detail if detail and not cond else ""))
        if not cond:
            ok = False

    print("build_ec_decompile.py --self-test")

    # The committed index pair and the manifest, read through the same strict
    # reader --check uses, so the known answers below are measured on the files
    # the gate runs against rather than on a copy of them.
    _ir, _lr, _mr = (read_index(p) if os.path.isfile(p) else []
                     for p in (INDEX, LISTING_INDEX, MANIFEST))
    for _p, _cols in ((INDEX, INDEX_COLUMNS), (LISTING_INDEX, INDEX_COLUMNS),
                      (MANIFEST, MANIFEST_COLUMNS),
                      (ANNOTATIONS, ANNOTATION_COLUMNS),
                      (CALL_TARGETS, CALL_TARGET_COLUMNS)):
        check("%s carries this tool's own %d-column header"
              % (os.path.relpath(_p, REPO), len(_cols)),
              os.path.isfile(_p)
              and next(csv.reader(open(_p, newline="")), None) == _cols)

    # Structural faults, on synthetic row-lists. The known-good case is first on
    # purpose: a guard exercised only on known-bad input cannot tell "clean"
    # from "never ran".
    _good = [{"program": "bank0", "addr": "0012", "out_file": "bank0/0012.c"},
             {"program": "bank0", "addr": "0020", "out_file": "bank0/0020.c"}]
    check("a clean pair of index row-lists has no structural problem",
          not index_structure_problems(_good, _good))
    _dup = [_good[0]] * 2
    _p = index_structure_problems(_dup, [])
    check("a duplicated (program, addr) key is reported", len(_p) == 1, str(_p))
    _p = index_structure_problems(_dup, _dup)
    check("a duplicated key is reported in each of the two indexes",
          len(_p) == 2, str(_p))
    _p = index_structure_problems([{"program": "bank0", "addr": "0012",
                                    "out_file": None}], [])
    check("a row with fewer fields than the header is reported", len(_p) == 1,
          str(_p))
    # DictReader collects a row with too many fields under the None restkey.
    _p = index_structure_problems([{"program": "bank0", "addr": "0012",
                                    "out_file": "a.c", None: ["surplus"]}], [])
    check("a row with more fields than the header is reported", len(_p) == 1,
          str(_p))
    _p = index_structure_problems(_good, [])
    check("two different addresses in one program are not a duplicate",
          not _p, str(_p))

    # The same four cases over the two annotation-side CSVs, which have their
    # own keys: (scope, addr) for the annotations, (file_offset, target) for
    # the census. Same order, same reason -- clean first.
    _agood = [{"scope": "bank0", "addr": "0EA2", "name": "a"},
              {"scope": "bank1", "addr": "0x0B158", "name": "b"}]
    check("a clean pair of annotation rows has no structural problem",
          not structure_problems("ghidra-functions.csv", _agood, annotation_key,
                                 "(scope, addr)"))
    _p = structure_problems("ghidra-functions.csv", [_agood[0]] * 2, annotation_key,
                            "(scope, addr)")
    check("a duplicated (scope, addr) key is reported", len(_p) == 1, str(_p))
    _p = structure_problems("ghidra-functions.csv",
                            [{"scope": "bank0", "addr": "0EA2", "name": None}],
                            annotation_key, "(scope, addr)")
    check("an annotation row with fewer fields than the header is reported",
          len(_p) == 1, str(_p))
    _p = structure_problems("ghidra-functions.csv",
                            [{"scope": "bank0", "addr": "0EA2", "name": "a",
                              None: ["surplus"]}], annotation_key, "(scope, addr)")
    check("an annotation row with more fields than the header is reported",
          len(_p) == 1, str(_p))
    # The one case the index cases have no analogue for: the two files spell an
    # address both ways, so the duplicate key has to be the normalised address.
    # With the raw string key these two rows are two different functions and the
    # check reports nothing at all.
    _p = structure_problems("ghidra-functions.csv",
                            [{"scope": "bank0", "addr": "0x0B158"},
                             {"scope": "bank0", "addr": "0B158"}],
                            annotation_key, "(scope, addr)")
    check("a 0x-prefixed and a bare address for one function are one key",
          len(_p) == 1, str(_p))
    _cgood = [{"file_offset": "0x0B000", "target": "0x04D5", "region": "common"},
              {"file_offset": "0x0B200", "target": "0x04D8", "region": "common"}]
    check("a clean pair of call-target rows has no structural problem",
          not structure_problems("bank-call-targets.csv", _cgood, call_target_key,
                                 "(file_offset, target)"))
    _p = structure_problems("bank-call-targets.csv", [_cgood[0]] * 2,
                            call_target_key, "(file_offset, target)")
    check("a duplicated (file_offset, target) key is reported", len(_p) == 1,
          str(_p))
    _p = structure_problems("bank-call-targets.csv",
                            [{"file_offset": "0x0B000", "region": None}],
                            call_target_key, "(file_offset, target)")
    check("a call-target row with fewer fields than the header is reported",
          len(_p) == 1, str(_p))
    _p = structure_problems("bank-call-targets.csv",
                            [{"file_offset": "0x0B000", "target": "0x04D5",
                              None: ["surplus"]}], call_target_key,
                            "(file_offset, target)")
    check("a call-target row with more fields than the header is reported",
          len(_p) == 1, str(_p))

    # Coverage, on a manifest that agrees with its index and one that does not.
    check("coverage: a manifest that agrees with the index passes",
          not coverage_mismatches([{"program": "bank0", "functions": "2"}],
                                  lambda program: 2))
    _mm = coverage_mismatches([{"program": "bank0", "functions": "1"}],
                              lambda program: 2)
    check("coverage: a manifest whose functions disagrees with the index fails, "
          "naming both numbers", len(_mm) == 1 and "1" in _mm[0]
          and "2" in _mm[0], str(_mm))
    _mm = coverage_mismatches([{"program": "bank0", "functions": ""}],
                              lambda program: 2)
    check("coverage: a manifest whose functions is not a number fails",
          len(_mm) == 1, str(_mm))

    # The mode vocabulary: documented, and enforced from the one place.
    check("every mode in use today is in the documented set",
          not manifest_mode_problems([{"program": "bank0", "mode": m}
                                      for m in MANIFEST_MODES]))
    _p = manifest_mode_problems([{"program": "bank0", "mode": "rebuild"}])
    check("a mode outside the documented set is rejected", len(_p) == 1, str(_p))
    check("the committed manifest uses only documented modes",
          not manifest_mode_problems(_mr), str(manifest_mode_problems(_mr)))

    # The "X has no entry in registers.yaml" idiom, which goes stale the moment
    # the byte it names is entered. Scoped to the addresses each clause governs,
    # so a sentence that also names addresses the YAML genuinely does not hold
    # keeps saying so.
    _claims = []
    try:
        _claims = stale_no_entry_claims(_ann, registered_addresses())
    except (OSError, TypeError, ValueError) as e:
        _claims = ["registers.yaml could not be read for the scan: %s" % e]
    check("no annotation comment claims registers.yaml has no entry for an "
          "address it holds (%d row(s) scanned)" % len(_ann),
          not _claims,
          "; ".join(_claims[:3])
          + (" (+%d more)" % (len(_claims) - 3) if len(_claims) > 3 else ""))
    # The guard itself, on synthetic comments. The known-good row comes first on
    # purpose, for the reason the structural checks above give: a guard
    # exercised only on known-bad input cannot tell "clean" from "never ran".
    _p = stale_no_entry_claims(
        [{"scope": "bank0", "addr": "0x93FF", "name": "positive_then_negative",
          "comment": "registers.yaml documents 0x044F as GPU_TEMP; 0x0A49, "
                     "0x0A4A and 0x098C have no entry there."}],
        {0x044F})
    check("a true 'no entry' claim about other addresses is not reported",
          not _p, str(_p))
    _p = stale_no_entry_claims(
        [{"scope": "bank1", "addr": "0xF3D7", "name": "stale_in_a_list",
          "comment": "reads 0x060C, and none of 0x0434 or 0x060C has an "
                     "entry"}],
        {0x0434, 0x0456})
    check("a stale claim is reported, naming the address and not the true ones "
          "beside it", len(_p) == 1 and "0x0434" in _p[0] and "0x060C" not in _p[0],
          str(_p))
    _p = stale_no_entry_claims(
        [{"scope": "bank0", "addr": "0xBE15", "name": "back_referenced",
          "comment": "Reads XDATA 0x08EA and XDATA 0x0449. Neither address has "
                     "an entry in ec/annotations/registers.yaml."}],
        {0x0449})
    check("a claim whose subject is a pronoun resolves to the addresses named "
          "before the clause", len(_p) == 1 and "0x0449" in _p[0], str(_p))
    _p = stale_no_entry_claims(
        [{"scope": "bank0", "addr": "0x96AD", "name": "wildcard_subject",
          "comment": "documents 0x0741; none of the 0x08xx or 0x09xx "
                     "destinations has an entry there."}],
        {0x0741})
    check("a claim about addresses named as a wildcard is left alone rather "
          "than widened to a guess", not _p, str(_p))

    # The variable layer, and the worked example the issue is built on.
    # ec/decompiled/bank0/0EA2.c is the file whose every identifier a reader
    # would follow was the wrong one, so it is the one place a regression in
    # this layer shows up as a name that stopped being there.
    _vrows = (list(csv.DictReader(open(VARIABLES, newline="")))
              if os.path.isfile(VARIABLES) else [])
    _xnames = xdata_symbol_names()
    _idx = {(r["program"], r["addr"]): r for r in _ir}
    _vproblems = variable_csv_problems(_vrows, _idx, _xnames)
    check("every variable row resolves against the committed export (%d row(s))"
          % len(_vrows), not _vproblems, "; ".join(_vproblems[:3]))
    _c0 = decompiled_code(os.path.join(OUTDIR, "bank0", "0EA2.c"))
    check("bank0 0x0EA2's param_1 is named in the committed export and the "
          "placeholder is gone",
          _c0 is not None and re.search(r"\bticks\b", _c0)
          and not re.search(r"\bparam_1\b", _c0), "")
    # The scope is the code, not the file: 0x901C's plate comment explains what
    # its own param_1 was, and that sentence has to survive the rename it
    # describes. A check on the whole file would refuse the row for saying what
    # the row is for.
    _c1 = decompiled_code(os.path.join(OUTDIR, "bank0", "901C.c"))
    _c1full = (open(os.path.join(OUTDIR, "bank0", "901C.c"), errors="replace").read()
               if os.path.isfile(os.path.join(OUTDIR, "bank0", "901C.c")) else "")
    check("a plate comment that names the placeholder it is explaining is not "
          "mistaken for the placeholder surviving",
          _c1full is not None and "param_1" in _c1full, "")
    # The guard itself, on synthetic rows against a real function. Known-good
    # first, for the reason the structural checks above give.
    def _vrow(**kw):
        base = dict(scope="bank0", addr="0x0EA2", key="param_1", name="ticks",
                    kind="param", comment="A count.", evidence="ec/x.asm",
                    basis="hand-decoded")
        base.update(kw)
        return base
    _p = variable_csv_problems([_vrow()], _idx, _xnames)
    check("a well-formed variable row passes", not _p, str(_p))
    _p = variable_csv_problems([_vrow(name="tikcs")], _idx, _xnames)
    check("a variable row whose name is a typo is caught against the export",
          len(_p) == 1 and "does not contain the name" in _p[0], str(_p))
    _p = variable_csv_problems([_vrow(kind="unresolved", name="ticks")], _idx, _xnames)
    check("a kind=unresolved row that also carries a name is refused, since "
          "unresolved means the placeholder stays",
          len(_p) == 1 and "the placeholder stays" in _p[0], str(_p))
    _p = variable_csv_problems([_vrow(kind="unresolved", name="")], _idx, _xnames)
    check("a kind=unresolved row with no name is checked for the placeholder it "
          "leaves behind, not skipped",
          any("leaves param_1 in place" in m for m in _p), str(_p))
    _p = variable_csv_problems(
        [dict(_vrow(), kind="parameter")], _idx, _xnames)
    check("a variable kind outside the vocabulary is rejected",
          len(_p) == 1 and "outside the controlled vocabulary" in _p[0], str(_p))
    _p = variable_csv_problems([_vrow(evidence="")], _idx, _xnames)
    check("a variable row with empty evidence is rejected",
          len(_p) == 1 and "no evidence citation" in _p[0], str(_p))
    _p = variable_csv_problems([_vrow(addr="0xABCD")], _idx, _xnames)
    check("a variable row at an address no function resolves to is rejected",
          len(_p) == 1 and "resolves to no exported function" in _p[0], str(_p))
    _p = variable_csv_problems([_vrow(name="XDATA_0440")], _idx, _xnames)
    check("a variable row naming an EC XDATA register is rejected -- the "
          "variable layer is not a back door for registers.yaml",
          any("XDATA register name" in m for m in _p), str(_p))
    # On a pd address that really exists, so the register lock is the only
    # thing this row can trip. The PD image has its own XDATA map, so an EC
    # register name there is an overclaim whatever else the row says.
    _pdrow = next((r for r in _ir if r["program"] == "pd"
                   and (r.get("out_file") or "") not in ("", "(failed)")), None)
    _p = (variable_csv_problems(
          [dict(_vrow(), scope="pd", addr=_pdrow["addr"], name="XDATA_0440")],
          _idx, _xnames) if _pdrow else ["no pd function found"])
    check("a pd row carrying an EC XDATA register name says so specifically",
          any("own XDATA map" in m for m in _p)
          and not any("resolves to no exported function" in m for m in _p), str(_p))
    # The other direction, on a function the layer has not touched: a row that
    # claims a rename the export does not show is reported on both counts --
    # the name is absent and the placeholder is still there. This is the
    # `--mode rebuild-project` case, and it is why the check is bidirectional
    # rather than just a search for the new name.
    _control = next((r for r in _ir
                     if r["program"] == "bank0"
                     and (r.get("out_file") or "") not in ("", "(failed)")
                     and re.search(r"\bparam_1\b",
                                   decompiled_code(os.path.join(
                                       OUTDIR, r["out_file"])) or "")), None)
    _p = (variable_csv_problems(
          [dict(_vrow(), addr=_control["addr"], name="a_name_no_export_has")],
          _idx, _xnames) if _control else ["no control function found"])
    check("a row claiming a rename the export does not show is caught in both "
          "directions (bank0 %s still carries param_1)"
          % (_control["addr"] if _control else "?"),
          len(_p) == 2 and "does not contain the name" in _p[0]
          and "still contains the placeholder" in _p[1], str(_p))

    # The known answers, on the committed files. These are docs/findings.md §15
    # as assertions: a re-export that moves a total fails here loudly and gets a
    # conscious update to the table in the same change, which is the point.
    # 2,708 -> 2,709 with issue #285's one seeded bank0 routine, 0xCC64, then
    # 2,709 -> 2,710 with issue #262's one seeded bank1 routine, 0xC1E7. Its
    # sibling 0xC118 could not be seeded -- it is the immediate byte of an
    # instruction inside FUN_CODE_c0a8, not an entry -- so that issue moves the
    # total by one, not two.
    check("EC: index.csv is 2,710 rows, and the manifest records 2,710 "
          "functions across 4 programs",
          len(_ir) == 2710 and len(_mr) == 4
          and sum(int(r["functions"]) for r in _mr) == 2710,
          "%d row(s), %d manifest row(s)" % (len(_ir), len(_mr)))
    check("EC: listing-index.csv is the same 2,710 rows", len(_lr) == 2710,
          "%d row(s)" % len(_lr))
    check("EC: the manifest's program set is the index's, with no label mapping "
          "in between",
          {r["program"] for r in _mr} == {r["program"] for r in _ir}
          == {"bank0", "bank1", "common", "pd"},
          str(sorted({r["program"] for r in _mr} ^ {r["program"] for r in _ir})))
    # Every address here is 4 bare hex digits, so a (program, addr) key taken as
    # a string and one taken as an int agree. That is what makes the duplicate
    # check's string key a fact about the file rather than an assumption -- and
    # a "0x0012" alongside a "0012" would quietly make it a lie.
    check("EC: addresses are uniformly 4 bare hex digits in both indexes, so "
          "string and int (program, addr) keys agree",
          all(len({(r["program"], r["addr"]) for r in rows})
              == len({(r["program"], int(r["addr"], 16)) for r in rows}) == 2710
              for rows in (_ir, _lr)))
    # The annotation layer's two committed CSVs, the same way. 1,769 records
    # and not the 1,771 the follow-up issue quoted: the file is 1,772 physical
    # lines, because one record's quoted `comment` (bank0 0x0EA2) spans three
    # of them, and a line count is not a record count. --check and this
    # self-test both read it with csv.DictReader, which returns the record.
    # A pin, so it moves with every annotation row a change adds on purpose:
    # 1,769 -> 1,772 with issue #181's three pd rows (0x7392, 0xEA67, 0xEFB9),
    # 1,772 -> 1,775 with issue #179's three, 1,775 -> 1,779 with issue #180's four,
    # 1,779 -> 1,781 with issue #183's two, 1,781 -> 1,782 with issue #285's one
    # (bank0 0xCC64), 1,782 -> 1,783 with issue #262's one bank1 0xC1E7.
    check("EC: annotations/ghidra-functions.csv is 1,783 records, no short row "
          "and no duplicate (scope, addr)",
          len(_ann) == 1783 and not structure_problems("ghidra-functions.csv", _ann,
                                                       annotation_key, "(scope, addr)"),
          "%d record(s)" % len(_ann))
    check("EC: bank-call-targets.csv is 5,998 records, no short row and no "
          "duplicate (file_offset, target)",
          len(_ct) == 5998 and not structure_problems("bank-call-targets.csv", _ct,
                                                      call_target_key,
                                                      "(file_offset, target)"),
          "%d record(s)" % len(_ct))
    # Neither file mixes the two spellings of an address today, so the raw
    # string key and the normalised key count the same. That equality is what
    # makes the normalised duplicate key sound over the real file, and it is the
    # claim that a file which has started mixing the two would break.
    check("EC: a raw and a normalised key count the same on both annotation "
          "CSVs, so normalising cannot merge two distinct keys",
          len({(r["scope"], r["addr"]) for r in _ann})
          == len({annotation_key(r) for r in _ann}) == 1783
          and len({(r["file_offset"], r["target"]) for r in _ct})
          == len({call_target_key(r) for r in _ct}) == 5998)

    # The common-area de-dup, on synthetic rows. A PD-image function that shares
    # an address, a name and a size with the EC's must survive it: the PD is a
    # separate 64 KiB program with its own address space, so the two 0x0012
    # bytes are unrelated and folding them together loses real code. It used to
    # lose exactly that row, and every gate still passed, because the row and
    # the files it named were deleted together.
    import tempfile as _tf
    _d = _tf.mkdtemp()
    _hdr = ("program\taddr\tname\tsize\tseed_basis\tannotated\t"
            "type\tbasis\tevidence\tout_file\n")
    _defs = [("bank0", "0012", "FUN_CODE_0012", 1),
             ("bank1", "0012", "FUN_CODE_0012", 1),
             ("pd", "0012", "FUN_CODE_0012", 1),
             ("bank0", "0020", "FUN_CODE_0020", 3),
             ("bank1", "0020", "FUN_CODE_0020", 3)]
    for _name, _lines in (("index-raw.csv", _hdr), ("listing-raw.csv", _hdr)):
        with open(os.path.join(_d, _name), "w") as f:
            f.write(_hdr)
            for _prog, _addr, _fn, _size in _defs:
                _ext = ".asm" if "listing" in _name else ".c"
                f.write("%s\t%s\t%s\t%d\tvector\tno\t\t\t\t%s/%s%s\n"
                        % (_prog, _addr, _fn, _size, _prog, _addr, _ext))
                os.makedirs(os.path.join(_d, "out", _prog), exist_ok=True)
                open(os.path.join(_d, "out", _prog, _addr + _ext), "w").write(";\n")
    _c, _l, _n = join_index(os.path.join(_d, "index-raw.csv"),
                            os.path.join(_d, "listing-raw.csv"), _d)
    _cprogs = sorted({r["program"] for r in _c})
    check("the common-area de-dup folds bank0 and bank1 together",
          ("common", "0020") in {(r["program"], r["addr"]) for r in _c})
    check("the de-dup does not touch the PD image, even at an identical "
          "address, name and size", ("pd", "0012") in
          {(r["program"], r["addr"]) for r in _c})
    check("the de-dup does not touch the PD image in the listing index either",
          ("pd", "0012") in {(r["program"], r["addr"]) for r in _l})
    shutil.rmtree(_d, ignore_errors=True)

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
                  pd_annotation_addrs))
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
    # The cross-decoder comparison spawns disasm8051.py per sampled function.
    # It is advisory -- its own docstring says so, and its result cannot fail
    # this run either way -- so it runs only when asked for, which is what
    # .github/scripts/agent-gates-deep.sh does. Worth being precise about what
    # that is and is not: measured at 0.13 s, so this is a decision about where
    # advisory output belongs, not a speed one. The self-test's actual 18 s was
    # the set comprehension above, which re-read the annotations CSV once per
    # seed row and is now 0.15 s in total.
    if args.cross_decoder:
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

    It runs on `--self-test --cross-decoder`, not on a bare `--self-test`.
    `.github/scripts/agent-gates-deep.sh` is what passes the flag; the cheap
    gate tier does not, and prints that it did not. Measured at 0.13 s, so
    moving it is a statement about where advisory output belongs -- not a
    speedup, and not a licence to assume the self-test's cost was here.
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


# The oracle's two facts, as (label, which export file, pattern), and the whole
# of what `--self-test --oracle` asserts. The label is what a reader sees in the
# report and what a negative case names, so it is a table field rather than a
# string assembled twice.
#
# The call is matched on the ADDRESS and the target, never on Ghidra's name for
# the callee. `FUN_CODE_bf08` is what 0xbf08 is called before an annotation
# renames it, and the committed export calls the same routine
# `sub_0a4e_against_4d_with_borrow` -- the machine fact is the address, and a
# check written against the name would fail on the rename rather than on
# anything about the code. Anchored to 0xB200 as well, so an `lcall 0xbf08` from
# somewhere else in the function is not what satisfies it.
ORACLE_FACTS = [
    ("an lcall to 0xbf08 at 0xB200", "asm",
     re.compile(r"^B200\b.*\blcall\s+0xbf08\b", re.M | re.I)),
    # The increment and the compare have to be adjacent, because that is what
    # the instructions at 0xB211..0xB283 are: read 0x09c7, inc it, store it,
    # read it back, subb #0x3c, branch. Either half alone would be satisfied by
    # an unrelated line, which is the failure a two-fact oracle cannot afford --
    # it would be a check that never fires.
    ("the DAT_EXTMEM 0x09c7 increment followed by its 0x3b compare", "c",
     re.compile(r"DAT_EXTMEM_09c7\s*=\s*DAT_EXTMEM_09c7\s*\+\s*1\s*;\s*"
                r"if\s*\(\s*0x3b\s*<\s*DAT_EXTMEM_09c7\s*\)", re.I)),
]


def charge_target_facts_problems(asm_text, c_text, only=None):
    """The two facts ec/annotations/charge-target-derating.md established by hand
    at bank0 0xB1F0, measured on an export's own .asm and .c.

    Returns a list of problem strings, empty when every fact holds -- the shape
    structure_problems() and variable_csv_problems() already use in this file.
    `only` narrows it to one label, so the oracle can report per fact without a
    second copy of the table.

    Pure, and deliberately so: it reads the two texts and nothing else, so
    opt_in_ghidra_oracle() can hand it a deliberately broken copy of this run's
    export and watch it object. An assertion nobody has ever seen fail is not an
    assertion, which is the same discipline variable_csv_problems() is exercised
    under in self_test().

    This is the whole of the oracle, and it is scoped to one address on purpose.
    What an acceptance check should assert about a whole export is a separate
    question that docs/findings.md §18 and ec/ghidra/README.md both leave open;
    a broader invariant invented here would look like coverage and be a guess.
    """
    out = []
    for label, which, pattern in ORACLE_FACTS:
        if only is not None and label != only:
            continue
        if not pattern.search(asm_text if which == "asm" else c_text):
            out.append("bank0 0xB1F0: the export does not contain %s" % label)
    return out


def opt_in_ghidra_oracle(args, work):
    """Run the export into scratch and assert charge-target-derating.md's two
    facts against it: Ghidra's output compared against a human reading, made
    mechanical.

    Everything the export touches is under `work`. It is deliberately NOT the
    main() path: write_outputs() opens with shutil.rmtree(OUTDIR) and would
    delete and regenerate all of ec/decompiled/ -- an acceptance check must not
    mutate the committed tree it is checking, and `git status` being empty after
    a run is the test for that. The mode is pinned to export-only for the same
    reason one clause further out: the committed .gpr/.rep is copied to scratch
    and never opened for writing, whichever way --mode was passed.

    Its own inputs are derived rather than passed in, because self_test() has
    already derived them from the same firmware and re-deriving is cheaper than
    widening the signature it is called through.

    A DECOMPILER UNAVAILABLE is loud already: TongFang.openDecompiler() throws in
    ExportDecompile.java, which fails the headless run, which run() surfaces
    through check=True. The oracle inherits that rather than adding a second
    Java-side guard, so what it adds is the guard the other side cannot have --
    a missing or empty export is a failure here, not a skip.
    """
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print("  %s  %s" % ("ok  " if cond else "FAIL", label)
              + ("  (%s)" % detail if detail and not cond else ""))
        if not cond:
            ok = False

    print("build_ec_decompile.py --self-test --oracle")
    if not args.ghidra:
        print("  FAIL  the oracle needs Ghidra, and --ghidra '' was passed. A "
              "check that skips itself and reports success is worse than no "
              "check.")
        print("  FAILURES ABOVE")
        return 1

    fw = open(FIRMWARE, "rb").read()
    pd = fw[0x20000:0x30000]
    census = call_target_rows()
    rows, _b0, _b1, _pdseeds = seed_rows(fw, pd, census)
    digest = sha256(FIRMWARE)
    ghidra_preflight(args.ghidra)
    imgs = build_images(work)
    spec, basis, annot_spec = write_specs(work, rows)
    context = write_context(work, imgs, digest)
    # Whatever an earlier run into this same work directory left in out/ would
    # otherwise be read as this run's export -- so a function that stopped being
    # exported entirely would still pass, which is one of the two states this
    # check exists to catch.
    stale = os.path.join(work, "out")
    if os.path.isdir(stale):
        shutil.rmtree(stale)
    analyze(args.ghidra, PROJECT, work, imgs, spec, basis, context, digest,
            "export-only", ["bank0.bin", "bank1.bin", "pd.bin"], annot_spec)

    srcs = {}
    for ext in ("c", "asm"):
        path = os.path.join(work, "out", "bank0", "B1F0." + ext)
        srcs[ext] = (open(path, errors="replace").read()
                     if os.path.isfile(path) else "")
        check("the export produced a non-empty bank0/B1F0.%s" % ext,
              srcs[ext].strip() != "")
    if not ok:
        print("  FAILURES ABOVE")
        return 1

    for label, _which, _pattern in ORACLE_FACTS:
        p = charge_target_facts_problems(srcs["asm"], srcs["c"], only=label)
        check("bank0 0xB1F0: the export contains %s" % label, not p,
              "; ".join(p))

    # Each fact, taken out of this run's own export, has to be reported -- and
    # the other one must not be, or the two are not being measured separately
    # and a passing oracle would only be evidence that it read the files.
    for label, which, pattern in ORACLE_FACTS:
        hits = len(pattern.findall(srcs[which]))
        check("the export contains %s exactly once, so taking it out is a "
              "deliberate break and not a no-op" % label, hits == 1,
              "%d match(es)" % hits)
        broken = dict(srcs)
        broken[which] = pattern.sub("", srcs[which], 1)
        p = charge_target_facts_problems(broken["asm"], broken["c"])
        check("taking it out of the %s is reported, and the other fact is not"
              % which, len(p) == 1 and label in p[0], str(p))

    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


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
    # The two committed indexes, the manifest and the two annotation-side CSVs,
    # read strictly once each and then used by every check below. A read error
    # is reported as a failed check rather than a traceback, so a broken CSV
    # reads as a broken CSV.
    _read = {}
    for _name, _path in (("manifest.csv", MANIFEST), ("index.csv", INDEX),
                         ("listing-index.csv", LISTING_INDEX),
                         ("ghidra-functions.csv", ANNOTATIONS),
                         ("bank-call-targets.csv", CALL_TARGETS)):
        if not os.path.isfile(_path):
            continue
        try:
            _read[_name] = read_index(_path)
        except (OSError, csv.Error) as e:
            fail("%s does not parse as strict CSV: %s" % (_name, e))
    if not ok:
        return 1
    # The census is the one of these the build cannot run without, so its
    # absence is a failed check. The annotations stay optional the way they have
    # always been -- the tool runs without them -- and the indexes and the
    # manifest each report their own absence further down.
    if "bank-call-targets.csv" not in _read:
        fail("no bank-call-targets.csv at %s; every seed set is built from it"
             % os.path.relpath(CALL_TARGETS, REPO))
        return 1
    manifest = _read.get("manifest.csv", [])
    # Structure before content, and stop if it fails. A row that did not come
    # out whole has no `out_file` to open and no address to key on, so every
    # per-row check below would be reading past the end of it -- and the counts
    # those checks compare are exactly the ones a short row has quietly made
    # smaller. Reported and stopped, not carried on from. The two annotation-side
    # CSVs get the same treatment, each on its own key: before this they had
    # content guards only (evidence non-empty, an address that resolves), and
    # neither of those notices a short row or a key that is written twice.
    _struct = (index_structure_problems(_read.get("index.csv", []),
                                        _read.get("listing-index.csv", []))
               + structure_problems("ghidra-functions.csv",
                                    _read.get("ghidra-functions.csv", []),
                                    annotation_key, "(scope, addr)")
               + structure_problems("bank-call-targets.csv",
                                    _read["bank-call-targets.csv"],
                                    call_target_key, "(file_offset, target)"))
    if _struct:
        fail("; ".join(_struct[:3]))
        return 1
    digest = sha256(FIRMWARE)
    for row in manifest:
        if row["sha256"] != digest:
            fail("%s: manifest SHA-256 does not match the committed firmware -- "
                 "the export is stale, rebuild it" % row["program"])
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
            fail("%s: functions != decompiled + failed" % row["program"])
        if decompiled < functions and failed == 0:
            fail("%s: decompiled < functions but failed == 0" % row["program"])
    if not os.path.isfile(INDEX):
        fail("no index at %s" % os.path.relpath(INDEX, REPO))
        return 1
    rows = _read.get("index.csv", [])
    seen_addr = set()
    for row in rows:
        out = os.path.join(OUTDIR, row["out_file"])
        if row["out_file"] not in ("", "(failed)") and not os.path.isfile(out):
            fail("index row %s %s points at a missing file: %s"
                 % (row["program"], row["addr"], row["out_file"]))
        seen_addr.add((row["program"], row["addr"]))
    # Every decompilation must have its machine code beside it, and vice versa.
    # This is the 1:1 property stated as a file-level invariant rather than a
    # claim: a reader who wants to check a decompiled C against the instructions
    # it came from can open <same address>.asm, and a listing with no C is
    # visible as a function nobody has read yet. Neither half can rot
    # unnoticed, which is the whole reason both are exported.
    if not os.path.isfile(LISTING_INDEX):
        fail("no listing index at %s: the export has no disassembly layer, so no "
             "decompilation can be checked against its instructions. Re-run the "
             "build." % os.path.relpath(LISTING_INDEX, REPO))
        return 1
    listing_rows = _read.get("listing-index.csv", [])
    listing_seen = set()
    for row in listing_rows:
        if row["out_file"] not in ("", "(no-instructions)") \
                and not os.path.isfile(os.path.join(OUTDIR, row["out_file"])):
            fail("listing row %s %s points at a missing file: %s"
                 % (row["program"], row["addr"], row["out_file"]))
        listing_seen.add((row["program"], row["addr"]))
    for program, addr in seen_addr:
        if (program, addr) not in listing_seen:
            fail("%s %s decompiles but has no disassembly listing" % (program, addr))
    # Every function the exporter reported must still be in the index --
    # `common` included, which the check this replaces skipped as "an export
    # grouping, not a program".
    #
    # The common-area de-dup once folded the PD image's 0x0012 into the common
    # group, because it shares an address, a name and a size with the EC's
    # 0x0012 -- and the PD image has its own address space, so those are two
    # different bytes. The row and both files were deleted together, so every
    # file-existence check below still passed: a row that is gone cannot point
    # at a file that is gone. The manifest is what breaks that, because it
    # carries the count the exporter measured before anything was de-duplicated.
    # It is a grouping, and it is also 753 of the index's 2,710 rows.
    for _name, _irows in (("index.csv", rows), ("listing-index.csv", listing_rows)):
        _counts = {}
        for r in _irows:
            _counts[r.get("program")] = _counts.get(r.get("program"), 0) + 1
        _mm = coverage_mismatches(manifest, lambda p, c=_counts: c.get(p, 0))
        if _mm:
            fail("%s: %s" % (_name, "; ".join(_mm[:3])))
    print("  coverage: %d index row(s), %d listing-index row(s), %d manifest "
          "program(s)" % (len(rows), len(listing_rows), len(manifest)))
    # `mode` is a controlled vocabulary, and it is the --mode argument's own.
    _modes = manifest_mode_problems(manifest)
    if _modes:
        fail("; ".join(_modes[:3]))
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
    # The content guards on the same rows the structural pass above read, not a
    # second read of the file: the two are different questions about one parse.
    for a in _read.get("ghidra-functions.csv", []):
        # An annotation with no citation is a claim, not a finding, and the
        # build refuses it -- but the build is not what CI runs, so the
        # check has to refuse it too or an uncited row reaches main.
        if not a.get("evidence", "").strip():
            fail("annotation %s %s (%s) has no evidence citation: a row that "
                 "names a function has to say where the reading came from"
                 % (a["scope"], a["addr"], a.get("name", "")))
        key = (a["scope"], norm_addr(a["addr"]))
        if key not in seen_addr and not (a["scope"] == "common"
                                         and any(k[0] == "common" for k in seen_addr)):
            fail("annotation %s %s resolves to no exported function -- either a "
                 "typo or the project needs a rebuild"
                 % (a["scope"], a["addr"]))
    # The variable layer, and the same discipline one level down. Its rows are
    # keyed on a decompiler placeholder rather than an address, so ApplyAnnotations
    # reports an unmatched one instead of failing the build -- the build itself
    # CONSUMES the key. This is where that is caught instead: the committed .c
    # has to carry the name the row asked for and must no longer carry the key.
    if os.path.isfile(VARIABLES):
        vrows = list(csv.DictReader(open(VARIABLES, newline="")))
        index_rows = {(r["program"], r["addr"]): r for r in rows}
        vproblems = variable_csv_problems(vrows, index_rows, xdata_symbol_names())
        for problem in vproblems[:5]:
            fail(problem)
        if len(vproblems) > 5:
            fail("... and %d more variable-annotation problem(s)" % (len(vproblems) - 5))
        print("  variables: %d row(s) in %s, all resolving against the committed "
              "export" % (len(vrows), os.path.relpath(VARIABLES, REPO)))
    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
