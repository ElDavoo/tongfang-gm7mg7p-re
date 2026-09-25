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
    python3 build_ec_decompile.py --work /tmp/ec --self-test --cross-decoder
    python3 build_ec_decompile.py --work /tmp/ec --report  # + cross-decoder.csv
    python3 build_ec_decompile.py --work /tmp/ec --write-digests
"""
import argparse
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys

# This repository's own linear 8051 decoder, imported rather than run as a
# subprocess per sampled function. It is import-safe -- everything it does
# hangs off main() and `if __name__ == "__main__"` -- and the two decoders stay
# independent either way, which is the whole of what the comparison rests on:
# Ghidra's SLEIGH and this file share no code.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import disasm8051

# The `name_basis` rules, imported rather than restated. One copy of the
# vocabulary and the four cross-field rules, so the tool that writes the
# column and the tools that check it cannot disagree about what the column
# means (issue #135). Import-safe for the same reason disasm8051 is.
import grade_name_basis

# The census that says where each of the 25 functions the ledger below reports
# as named-without-a-row got its name. Imported rather than restated, so the
# byte reads that decide it have one implementation; the import is one-way on
# purpose, because second_copy_census defers *its* import of this module and so
# each of the two can still be run on its own. Import-safe for the same reason
# the two above are.
import second_copy_census

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
# The cross-decoder comparison's recorded outcome, one row per sampled
# function. Generated and committed beside manifest.csv and reassembly.csv, and
# never hand-edited: --check recomputes every cell of it and fails on a
# difference, so an edit here re-arms the ratchet without comparing anything.
CROSS_DECODER = os.path.join(REPO, "ec", "ghidra", "cross-decoder.csv")
ANNOTATIONS = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
# The variable layer, over the same export. A separate file from the function
# layer because a function's row IS a function -- annotation_seeds() below
# reads every row's addr as a seed and join_index() keys one row per
# (scope, addr) -- and a function with eight parameters cannot be eight rows
# in that file. ec/annotations/README.md has the format.
VARIABLES = os.path.join(REPO, "ec", "annotations", "ghidra-variables.csv")
REGISTERS = os.path.join(REPO, "ec", "annotations", "registers.yaml")
CALL_TARGETS = os.path.join(REPO, "ec", "annotations", "bank-call-targets.csv")
# A committed SHA-256 of every .c this component's export produces, so a
# truncated, half-overwritten or hand-edited decompile is a red --check rather
# than a file that passes on its name. A SEPARATE file from the manifest on
# purpose: write_manifest() is only reached from a Ghidra run, and the EC
# manifest is written during --mode rebuild-project, which two branches cannot
# both do (.gitattributes -merge). A digest column there would make adding one
# require the merge-hostile operation this check exists to avoid needing.
C_DIGESTS = os.path.join(REPO, "ec", "ghidra", "c-digests.csv")
SUBSYSTEMS = os.path.join(REPO, "ec", "annotations", "subsystems.md")
GHIDRA_VERSION = "12.1.3"

# The Keil BL51 bank-switch stubs, from ec/tools/find_banks.py and ec/README.md.
BANK_STUBS = [0x1100, 0x1114, 0x1128, 0x113C]
COMMON_END = 0x8000
# Where each program lives in the one firmware file, so a runtime address can
# be read out of the raw image without a Ghidra run. make_bank_image.py's
# constants, which self-test them against the committed firmware. `common` is
# an export grouping rather than a program -- those functions were exported
# from bank0, so bank0's window is the one to read them at, and the common area
# is byte-identical in both banks anyway.
BANK_WINDOWS = {"bank0": 0x08000, "bank1": 0x10000, "common": 0x08000}
PD_WINDOW = 0x20000
# `mov dptr,#imm16`, the 8051's only way to name an XDATA address, and the one
# instruction the cross-decoder comparison looks for. The immediate is read from
# the encoding rather than from disasm8051's rendered text.
MOV_DPTR = 0x90
# How far into an image to look for its vector table. The EC's runs 0x0000-0x003C
# and the PD image's 0x0000-0x0020; 0x40 covers both with room to spare.
VECTOR_SCAN_LIMIT = 0x40

INDEX_COLUMNS = ["program", "addr", "name", "size", "seed_basis", "common",
                 "annotated", "type", "basis", "evidence", "also_in", "out_file"]
MANIFEST_COLUMNS = ["program", "source", "sha256", "loader", "ghidra_version",
                    "functions", "decompiled", "failed", "instruction_bytes",
                    "body_bytes", "seeds_applied", "seeds_rejected",
                    # The function layer, in the order the questions come: how
                    # many annotation rows the exporter applied, how many of them
                    # found no function, and -- a different question, kept apart
                    # because it is the one the old `annotations_applied` column
                    # was answering -- how many exported functions carry a symbol
                    # that is not a Ghidra placeholder (ExportDecompile.java:129).
                    "annotations_applied", "annotations_unmatched",
                    "functions_named",
                    "variables_functions", "variables_applied",
                    "variables_unmatched", "mode"]
# The counters ApplyAnnotations.java writes into apply-<program>.tsv, and the
# only keys of that report this driver reads. Kept as data, in one place, because
# a counter the writer emits and the reader does not accept is a number that
# looks measured and is not.
#
# The function layer is here for the same reason the variable layer was added
# (#238): the script has always computed `annotations_applied` and
# `annotations_unmatched` and written them to the report, and the driver used to
# write its own constant beside them. Read back rather than recomputed, because
# the script's count is the only one that knows what the decompiler actually
# found. bios/tools/bios_extract.py reaches the same two numbers a different way
# -- it derives them driver-side, from the index rows that carry an annotation
# and from the keys that resolved to nothing (bios_extract.py:895-896, 912-913,
# 940-941) -- and fails the build when the unmatched count is non-zero
# (bios_extract.py:1241), so no manifest in this repository carries a counter
# that was typed in as a constant. What the EC had not done was take the
# script's own figure.
APPLY_REPORT_KEYS = ("annotations_applied", "annotations_unmatched",
                     "variables_functions", "variables_applied",
                     "variables_unmatched")
# `common` is an export grouping, not a Ghidra program: ApplyAnnotations.java runs
# on the two bank programs and writes no apply-common.tsv, and the de-dup in
# join_index() renames a folded bank0 row to `common` after the fact. The
# manifest's `common` row therefore borrows bank0's counters, which is what the
# variable counters have always done. Named once, so the writer and the check
# cannot disagree about which row stands in for which.
MANIFEST_PROGRAM_SOURCE = {"common": "bank0"}
# c-digests.csv, beside the manifest rather than inside it. `path` is relative
# to the repo root so the file reads the same way a citation does, and `bytes`
# is carried alongside the hash so a truncation is named as one rather than
# having to be inferred from a hash that no longer matches.
C_DIGEST_COLUMNS = ["path", "sha256", "bytes"]
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
                      "evidence", "basis", "name_basis"]
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


def committed_c_files(decompiled_dir):
    """Every committed .c under `decompiled_dir`, as (abs, repo-relative) sorted
    by the relative path.

    Sorted because the digest file is a committed artefact and two runs over the
    same tree have to produce the same bytes; the order a directory walk happens
    to return is not that."""
    out = []
    for dp, _dns, fns in os.walk(decompiled_dir):
        for fn in fns:
            if not fn.endswith(".c"):
                continue
            abs_path = os.path.join(dp, fn)
            # posixpath, not os.path: the `path` column is a committed CSV read
            # by every platform's git, so a Windows contributor's --write-digests
            # must not rewrite 2,710 rows as "ec\decompiled\..." and leave the
            # Linux gate reporting every one of them as a missing file.
            rel = os.path.relpath(abs_path, REPO).replace(os.sep, "/")
            out.append((abs_path, rel))
    return sorted(out, key=lambda p: p[1])


def write_c_digests(path=C_DIGESTS, decompiled_dir=OUTDIR):
    """(Re)write the committed .c digest file from what is on disk now.

    Needs no Ghidra and no network, which is the whole point: regenerating it is
    a sub-second command an agent or a contributor runs after a re-export, and
    it never touches a Ghidra project -- so it cannot collide with another
    branch's --mode rebuild-project.

    Refuses to bless a zero-length .c, or one that is a symlink. A digest is a
    claim that a file is the export, and a truncated write's zero-length file is
    exactly the fault the file exists to catch; writing its hash would turn the
    check into a rubber stamp on the corruption. A symlink is the one
    substitution a hash cannot see at all, because hashing follows the link and
    records the TARGET's bytes -- so the repository could hold no decompile at
    that address and pass. Both are refused here rather than asserted later,
    because this is the only place a wrong file can be recorded.
    """
    rows, empty, links = [], [], []
    for abs_path, rel in committed_c_files(decompiled_dir):
        if os.path.islink(abs_path):
            links.append(rel)
            continue
        size = os.path.getsize(abs_path)
        if size == 0:
            empty.append(rel)
        rows.append({"path": rel, "sha256": sha256(abs_path), "bytes": str(size)})
    if links:
        raise SystemExit("error: refusing to write %s: %d .c under %s is a "
                         "symlink, e.g. %s. A digest follows the link and would "
                         "bless the TARGET's bytes, so the repository could hold "
                         "no decompile at that address and still pass -- the one "
                         "substitution a hash cannot see. Commit the file itself."
                         % (os.path.relpath(path, REPO), len(links),
                            os.path.relpath(decompiled_dir, REPO), links[0]))
    if empty:
        raise SystemExit("error: refusing to write %s: %d zero-length .c, e.g. %s. "
                         "A truncated export is what the digest exists to catch, so "
                         "it is not something to record a hash of -- re-run the "
                         "export first."
                         % (os.path.relpath(path, REPO), len(empty), empty[0]))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=C_DIGEST_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def verify_c_digests(path=C_DIGESTS, decompiled_dir=OUTDIR):
    """Every committed .c against the digest row that claims it.

    Four things are asserted, and the fourth is what makes the first three mean
    something: the row count has to equal the file count found, so a partial or
    filtered digest cannot pass by never being compared. A digest file covering
    two files when three are on disk is a check that has quietly stopped
    checking, which is the failure mode this repository keeps meeting the other
    way round.

    The calibration matters as much as the assertion. This catches accidental
    corruption, and it forces any accepted change to a decompile to be a visible
    committed diff. It is NOT an anti-tamper control and NOT proof that a
    decompile is a faithful reading of the firmware: --write-digests will happily
    re-bless a mangled file, and no hash says the C means what it claims. It is
    also not what verify_reassembly.py does -- that tool re-derives listing bytes
    from the firmware, a trusted input. The decompiled C has no such input to be
    re-derived from, which is why a committed digest is genuinely new here.
    """
    if not os.path.isfile(path):
        return ["no %s: every committed .c needs a digest, or a truncated or "
                "hand-edited export is a file that passes on its name alone. Run "
                "with --write-digests." % os.path.relpath(path, REPO)]
    with open(path, newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            header = None
        if header != C_DIGEST_COLUMNS:
            return ["%s: header is %r, not this tool's %d-column %s"
                    % (os.path.relpath(path, REPO), header, len(C_DIGEST_COLUMNS),
                       ",".join(C_DIGEST_COLUMNS))]
        rows = list(csv.DictReader(f, fieldnames=C_DIGEST_COLUMNS))

    on_disk = dict((rel, abs_path) for abs_path, rel in committed_c_files(decompiled_dir))
    if not on_disk:
        # The floor under every comparison below. Without it, a header-only
        # digest against a tree that is empty or absent produces zero problems
        # and zero comparisons -- a check that has read nothing and reports
        # nothing wrong, which is the shape §14b describes and the reason this
        # line exists rather than a comment saying it cannot happen.
        return ["no committed .c under %s: there is nothing for this digest to "
                "cover, so every assertion below would pass without comparing "
                "anything" % os.path.relpath(decompiled_dir, REPO)]
    seen, bad = set(), []
    for r in rows:
        rel = (r.get("path") or "").strip()
        if rel in seen:
            bad.append("%s: two digest rows for one file" % rel)
        seen.add(rel)
        abs_path = on_disk.get(rel)
        if abs_path is None:
            bad.append("%s: a digest row names a file that is not there" % rel)
            continue
        try:
            want_bytes = int(r["bytes"])
        except (TypeError, ValueError):
            bad.append("%s: bytes is %r, not a number" % (rel, r.get("bytes")))
            continue
        got_bytes = os.path.getsize(abs_path)
        if got_bytes != want_bytes:
            bad.append("%s: %d byte(s) committed, %d on disk. If this came from a "
                       "re-export, re-run --write-digests; if it did not, the file "
                       "was truncated, overwritten or hand-edited."
                       % (rel, want_bytes, got_bytes))
            continue
        got = sha256(abs_path)
        if got != r["sha256"]:
            bad.append("%s: committed digest %s, on disk %s. If this came from a "
                       "re-export, re-run --write-digests; if it did not, the file "
                       "was truncated, overwritten or hand-edited."
                       % (rel, r["sha256"], got))
    for rel in sorted(set(on_disk) - seen):
        bad.append("%s: a committed .c with no digest row" % rel)
    if len(rows) != len(on_disk):
        bad.append("%d digest row(s) for %d committed .c: a digest covering some "
                   "of the tree is a check that is not checking the rest"
                   % (len(rows), len(on_disk)))
    return bad


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
    """The counters ApplyAnnotations.java wrote, keyed by program.

    Both layers, for the same reason. Read back rather than recomputed, because
    the script's own count is the only one that knows what the decompiler
    actually found: a row whose key the decompiler no longer produces looks
    identical to a row that was never written, from out here. The driver could
    count the CSV's rows and would get that wrong the first time
    `--mode rebuild-project` consumed a key.

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
            if key in APPLY_REPORT_KEYS:
                try:
                    counts[key] = int(value.strip())
                except ValueError:
                    pass
        out[program] = counts
    return out


def write_outputs(raw, listing, work, digest, mode, seeds_info, apply_counts):
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
            # One dict, both layers. `common` is an export grouping with no
            # ApplyAnnotations report of its own, so it borrows bank0's -- the
            # same substitution the byte counts above make, and the one
            # MANIFEST_PROGRAM_SOURCE names for the check to reuse.
            a = apply_counts.get(MANIFEST_PROGRAM_SOURCE.get(program, program), {})
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
                "annotations_applied": a.get("annotations_applied", 0),
                "annotations_unmatched": a.get("annotations_unmatched", 0),
                # What the old `annotations_applied` column was actually
                # counting, kept under the name that says so:
                # ExportDecompile.java:129 asks whether the exported symbol is
                # still a Ghidra placeholder, which is not a question about the
                # annotation CSV at all. docs/findings.md §18 records why the
                # two are no longer summed into one figure.
                "functions_named": p["annotated"],
                "variables_functions": a.get("variables_functions", 0),
                "variables_applied": a.get("variables_applied", 0),
                "variables_unmatched": a.get("variables_unmatched", 0),
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
    ap.add_argument("--write-digests", action="store_true",
                    help="regenerate ec/ghidra/c-digests.csv from the committed "
                         ".c files; no Ghidra, no network, sub-second")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions against the committed inputs")
    ap.add_argument("--oracle", action="store_true",
                    help="with --self-test, also run Ghidra and check the export "
                         "against the hand reading in charge-target-derating.md")
    ap.add_argument("--cross-decoder", action="store_true",
                    help="with --self-test, also compare Ghidra's C against "
                         "ec/tools/disasm8051.py over each sampled function's "
                         "opening straight-line instructions, and print the "
                         "denominator. What it finds is committed by --report "
                         "and ratcheted by --check, so the run and the cheap "
                         "tier measure the same thing")
    ap.add_argument("--report", action="store_true",
                    help="(re)write ec/ghidra/cross-decoder.csv from the current "
                         "sample. No Ghidra and no network: the report is a pure "
                         "function of the committed inputs, so this is what "
                         "refreshes it after a re-export or an annotation")
    args = ap.parse_args(argv)
    work = os.path.abspath(args.work)
    os.makedirs(work, exist_ok=True)

    # --write-digests first of all, because it is the one mode that writes a
    # committed file and needs nothing else: no firmware read, no seeds, no
    # Ghidra, and no project touched.
    if args.write_digests:
        if args.check or args.self_test:
            # Refused rather than resolved in either direction. --write-digests
            # re-blesses the tree from what is on disk and returns 0, so a CI
            # invocation that ever grew the flag would overwrite the digests it
            # was meant to compare against and exit green -- which is the one
            # thing a digest must never be able to do.
            raise SystemExit("error: --write-digests regenerates %s from the "
                             "current tree; it cannot be combined with --check or "
                             "--self-test, which compare against it. Run them "
                             "separately."
                             % os.path.relpath(C_DIGESTS, REPO))
        n = write_c_digests()
        print("wrote %s: %d .c file(s)" % (os.path.relpath(C_DIGESTS, REPO), n))
        return 0

    # --check first, and ahead of the seed derivation, because it needs none of
    # it: a committed CSV that does not parse should be a failed check that
    # names the file, and running the build path first turned that into a
    # traceback out of a reader --check had not reached yet.
    if args.check:
        return check(work)

    # --report is the other one that needs no build, for the same reason and for
    # the reason it is a separate path rather than a flag on the Ghidra run: the
    # report is a function of the committed export, not of a run that produces
    # one. Refreshing it must not require the toolchain that made the export.
    if args.report:
        rows = cross_decoder_results(open(FIRMWARE, "rb").read())
        path = write_cross_decoder_report(rows)
        print("  wrote %s (%d row(s))" % (os.path.relpath(path, REPO), len(rows)))
        print("  " + denominator_line(cross_decoder_summary(rows)))
        return 0

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
    apply_counts = apply_report_counters(work)
    per_program = write_outputs(raw, listing, work, digest, args.mode, seeds_info,
                                apply_counts)
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


# --------------------------------------------------------------------------
# The function layer's three counters, checked offline.
#
# `annotations_applied` and `annotations_unmatched` are read back from
# apply-<program>.tsv, and `functions_named` is counted off the index. All three
# are the script's own arithmetic over the two committed CSVs, so --check can
# derive every one of them without Ghidra. That is the point: the manifest is
# only ever written by a Ghidra run, so a counter that quietly stopped
# describing the export had no other witness. docs/findings.md §18.
# --------------------------------------------------------------------------

def annotation_scopes_for(program):
    """The annotation scopes one Ghidra program consumes.

    This is ApplyAnnotations.java's own `mine()` (ApplyAnnotations.java:373-378):
    the rows of that program's scope, plus every `common`-scoped row for the two
    bank programs, because the common area is byte-identical in both and the
    script names the function in each. Restated rather than assumed, because
    `annotations_applied` IS this mapping -- a driver that counted one row per
    scope would report 691 for bank0 where the report says 769, and would be
    wrong for a reason invisible in the manifest."""
    return {program, "common"} if program in ("bank0", "bank1") else {program}


def index_scopes_for(program):
    """The annotation scopes that can back one index row.

    The same rule as above, differing in exactly one case: an index row the
    de-dup renamed to `common` (join_index) is bank0's export, so a
    `bank0`-scoped row is one of the things that could have named it."""
    if program in ("bank0", "bank1"):
        return {program, "common"}
    return {"bank0", "common"} if program == "common" else {program}


def exported_addrs(index_rows):
    """{program: {addr}} -- where each Ghidra program holds a function.

    A folded common-area function is one index row standing in for two
    programs' copies, and the bank1 row was dropped from the index along with
    it, so `common` counts for both banks. Leave that out and every
    `common`-scoped annotation counts as UNRESOLVED for both bank programs: all
    95 of them sit at a folded address today, so `annotations_unmatched` would
    read 95 for bank0 and 95 for bank1 where the real answer is 0 for both, and
    a red `--check` would point at rows that resolve perfectly well."""
    out = {}
    for r in index_rows:
        addr = norm_addr(r["addr"])
        out.setdefault(r["program"], set()).add(addr)
        if r["program"] == "common":
            out.setdefault("bank0", set()).add(addr)
            out.setdefault("bank1", set()).add(addr)
    return out


def annotation_ledger(index_rows, ann_rows):
    """The two-way gap between the annotation CSV and the exported index.

    Returns `(named_without_row, applied_but_unflagged, backed)`: index rows
    marked `annotated=yes` that no CSV row explains; CSV rows sitting behind an
    index row that says `annotated=no`; and every index row that does carry a
    CSV row. Pure, no I/O, one pass, so the numbers §18 quotes and the numbers
    `--check` acts on are the same lists.

    Two directions, because one is not enough. The old `annotations_applied`
    column was the index's `annotated=yes` count under a name that promised a
    count of CSV rows, and the gap that mismatch opened was read as stale
    annotations. It is not stale rows: every CSV row resolves, and the gap is
    names from somewhere else -- Ghidra's own `caseD_*` labels on switch
    dispatchers, and symbols that were already in the committed project
    database. A one-way count sees those and calls them drift. Counting only the
    other direction misses its own case: the `annotated` column answers "did
    Ghidra name this, or did a person", so a row can apply and still be reported
    unannotated, and the case is a row that took its name out of Ghidra's own
    reserved namespace. That is what the seven `thunk_`-prefixed rows were until
    #602 renamed them; nothing about the direction is route-specific, so the
    list stays a check rather than becoming a name filter. Both halves have to
    be counted for either to read correctly.

    The third list is the matched middle, and its length is what lets the two
    directions be added up rather than merely reported: it says how many index
    rows a CSV row is responsible for, so two rows naming one function shows up
    as a count that does not reconcile."""
    by_scope_addr = {}
    for r in ann_rows:
        by_scope_addr.setdefault((r["scope"], norm_addr(r["addr"])), []).append(r)
    named_without_row, applied_but_unflagged, backed = [], [], []
    for r in index_rows:
        program, addr = r["program"], norm_addr(r["addr"])
        backing = [a for s in index_scopes_for(program)
                   for a in by_scope_addr.get((s, addr), ())]
        if backing:
            backed.append((r, backing))
        if r.get("annotated") == "yes":
            if not backing:
                named_without_row.append(r)
        elif backing:
            applied_but_unflagged.append((r, backing))
    return named_without_row, applied_but_unflagged, backed


def annotation_ledger_mismatches(manifest_rows, index_rows, ann_rows):
    """Manifest rows whose three function-layer counters disagree with the
    committed files they summarise.

    Three expectations, each the script's own arithmetic rather than a re-run of
    it:

      annotations_applied     rows of a scope the program consumes that found a
                              function -- what ApplyAnnotations.java increments
                              `applied` for.
      annotations_unmatched   rows of a scope the program consumes that found
                              none. The script also counts an evidence-less row
                              as unmatched; check() refuses those earlier, so an
                              evidence-less row never reaches this function and
                              the count here is purely the unresolved-address
                              case.
      functions_named         the index's `annotated=yes` rows for the program.

    A `common` manifest row is checked against the expectations for bank0, whose
    report it borrows (MANIFEST_PROGRAM_SOURCE) -- while its `functions_named`
    is the common index row's own 80-ish, because that one was never read from a
    report at all. Two different questions, two different sources, and the
    separation is the change this function exists to pin."""
    out = []
    addrs = exported_addrs(index_rows)
    consumed = {}
    for program in {r.get("program") for r in index_rows} | {"bank0", "bank1", "pd"}:
        scopes = annotation_scopes_for(program)
        rows = [a for a in ann_rows if a["scope"] in scopes]
        consumed[program] = (
            sum(1 for a in rows if norm_addr(a["addr"]) in addrs.get(program, ())),
            sum(1 for a in rows if norm_addr(a["addr"]) not in addrs.get(program, ())))
    named = {}
    for r in index_rows:
        if r.get("annotated") == "yes":
            named[r["program"]] = named.get(r["program"], 0) + 1
    for r in manifest_rows:
        program = r.get("program", "?")
        source = MANIFEST_PROGRAM_SOURCE.get(program, program)
        want_applied, want_unmatched = consumed.get(source, (0, 0))
        for column, want in (("annotations_applied", want_applied),
                             ("annotations_unmatched", want_unmatched),
                             ("functions_named", named.get(program, 0))):
            try:
                got = int(r[column])
            except (KeyError, TypeError, ValueError):
                out.append("%s: %s is %r, not a number"
                           % (program, column, r.get(column)))
                continue
            if got != want:
                out.append(
                    "%s: manifest records %s=%d; the committed files give %d. %s"
                    % (program, column, got, want, _ledger_hint(column)))
    return out


def _ledger_hint(column):
    """What a disagreement in one counter means, in the words of the layer it
    belongs to. The three are kept apart because they are three different
    mistakes, and a bare "expected N got M" would read as one."""
    if column == "annotations_applied":
        return ("That figure came from a report, so this is a manifest no run "
                "produced -- re-run the build rather than editing it.")
    if column == "annotations_unmatched":
        return ("Either an annotation names an address with no function, or one "
                "lost its evidence citation; check() refuses the latter "
                "separately, so say which.")
    return ("This is the index's own `annotated=yes` count, so the two files are "
            "from different runs -- re-run the build.")


# A header the EC exporter writes as the first line of every .c: the program, the
# address, and the name, with a trailing "[named]" when the name is not a
# Ghidra placeholder. Parse it as a whole rather than by field offset, so a
# re-ordering of the three is a red check here instead of a silent
# name/address swap in 2,710 files.
EC_C_HEADER = re.compile(r"^// (\S+) @ ([0-9A-Fa-f]+)\s+(\S+)")


def c_presence_problems(index_rows, decompiled_dir):
    """Every index row's `.c` exists, is non-empty, and declares the address and
    the name the index gives it.

    Nothing anywhere paired a row to the function its `.c` actually contains.
    `check()` proved each `out_file` was a file; this proves it is the file the
    row claims, which is the pairing a truncated or half-overwritten export
    breaks without breaking. A zero-length file passes `os.path.isfile`, so
    non-empty is asserted rather than inferred from the stat.

    Each distinct `out_file` is read ONCE and the (addr, name) it declares
    remembered, then rows are compared against that. Not an optimisation: the
    index has one `.c` per function here, but the per-row containment test this
    replaces is the §14a defect at its next address, and the count of files read
    is returned so the caller can print it and `--self-test` can pin it.

    Pure: no globals, no I/O beyond the fixture directory it is handed.

    Returns (problems, n_files_read, n_rows_paired)."""
    out, read, declared, n_rows = [], set(), {}, 0
    for row in index_rows:
        rel = (row.get("out_file") or "").strip()
        if not rel or rel == "(failed)":
            continue
        # Counted here, not as len(index_rows) at the call site: a `(failed)`
        # row is a legitimate state the manifest permits (functions ==
        # decompiled + failed), and a check that prints the input length has
        # claimed to pair rows it stepped over.
        n_rows += 1
        if rel not in declared:
            path = os.path.join(decompiled_dir, rel)
            read.add(rel)
            try:
                with open(path, errors="replace") as f:
                    # The header is the first line by construction
                    # (ExportDecompile.writeFunctionFile), so one line is read
                    # rather than a file -- the body is the same for every row of
                    # one file and the marker is the only thing that differs.
                    head = f.readline()
            except OSError:
                declared[rel] = None
            else:
                m = EC_C_HEADER.match(head)
                declared[rel] = (m.group(2).upper(), m.group(3)) if m else None
        got = declared[rel]
        where = "index row %s %s" % (row.get("program", "?"), row.get("addr", "?"))
        if got is None:
            out.append("%s: %s is missing, empty, or carries no `// <program> @ "
                       "<addr> <name>` header naming %s" % (where, rel, rel))
            continue
        addr, name = got
        if addr != (row.get("addr") or "").strip().upper():
            out.append("%s: %s declares address %s, not %s -- a wrong-function "
                       "export, or a stale index" % (where, rel, addr, row.get("addr")))
        elif name != (row.get("name") or "").strip():
            out.append("%s: %s declares name %s, not %s -- a wrong-function "
                       "export, or a stale index" % (where, rel, name, row.get("name")))
    return out, len(read), n_rows


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


def xdata_address_names(path=XDATA):
    """{address: name} for the rows whose name spells the address itself.

    The subset of xdata-symbols.csv that the cross-decoder's vocabulary has to
    be able to read: `XDATA_1664` carries 0x1664 in its own text, `PROJECT_ID`
    does not. Computed from the committed CSV rather than listed here, so a row
    added to registers.yaml joins this set without anyone remembering to edit
    a regex beside it -- the failure mode this exists to stop.
    """
    if not os.path.isfile(path):
        return {}
    out = {}
    for r in csv.DictReader(open(path, newline="")):
        name = (r.get("name") or "").strip()
        m = re.search(r"(?:EXTMEM|XDATA)_([0-9a-fA-F]{4})\b", name)
        if m and (r.get("addr") or "").strip().lower() == "0x" + m.group(1).lower():
            out[m.group(1).upper()] = name
    return out


# The canonical `isPlaceholderName()` and the Python transcription of it in
# grade_name_basis.py, read against each other. The Java is what the exporters
# and the index actually call, so it is the source of truth and the Python set
# is the derivation; this is the pair TongFang.java:132 claims there is one of,
# and the claim had already stopped being true of the copy in
# ExportDecompile.java. Comparing the two is the point -- a Python list nobody
# checks against the Java is the same second derivation, free to drift again.
TONGFANG_JAVA = os.path.join(SCRIPTS, "TongFang.java")
_PLACEHOLDER_NAME = re.compile(
    r"public static boolean isPlaceholderName\(String name\)\s*\{(.*?)\n    \}",
    re.S)
_PLACEHOLDER_TEST = re.compile(r'name\.(startsWith|equals)\("([^"]*)"\)')


def placeholder_name_tests(java_path=TONGFANG_JAVA):
    """`(startsWith|equals, literal)` for every test in the canonical
    `isPlaceholderName()`, in source order.

    Parsed out of the Java rather than restated, so a new prefix added there
    cannot be quietly left out of the Python. A body that does not parse
    yields an empty list rather than raising, because a raise here would read
    as a broken build instead of as the drift it is -- and the caller asserts
    against an empty list, which fails. The method body is bounded on the
    closing `\\n    }` at the method's own indent, so `isVariablePlaceholder`
    and everything after it are not counted.
    """
    try:
        text = open(java_path, errors="replace").read()
    except OSError:
        return []
    m = _PLACEHOLDER_NAME.search(text)
    return _PLACEHOLDER_TEST.findall(m.group(1)) if m else []


def self_test(fw, pd, rows, b0, b1, pdseeds, unattributed, args, work):
    ok = True
    # One read of the annotations CSV, split by scope. The PD set used to be
    # built inside the generator of the check that uses it, so it re-read and
    # re-parsed the whole file once per seed row -- 1,790 times, which is where
    # this self-test's 18 s went. The EC-side set had been hoisted already; only
    # the PD one had not, and the two now read the file once between them.
    _ann = annotation_rows()
    _ct = call_target_rows()
    _XDATA_NAME_ADDR = xdata_address_names()
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
    _lr_keys = {(r["program"], r["addr"]) for r in _lr}
    for _p, _cols in ((INDEX, INDEX_COLUMNS), (LISTING_INDEX, INDEX_COLUMNS),
                      (MANIFEST, MANIFEST_COLUMNS),
                      (CROSS_DECODER, CROSS_DECODER_COLUMNS),
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

    # The function layer's three counters, on a fixture built to contain the
    # awkward case rather than to avoid it: a folded `common` row, which is one
    # index row standing for two programs' functions, and a bank0-scoped
    # annotation whose only visible index row is the common one. Clean first, for
    # the reason the structural cases above give.
    def _fidx(program, addr, annotated="yes", seed="annotation"):
        return {"program": program, "addr": addr, "annotated": annotated,
                "seed_basis": seed, "name": "n_" + addr}
    def _fann(scope, addr, name=None):
        return {"scope": scope, "addr": addr,
                "name": name if name is not None else "a_" + addr}
    _fi = [_fidx("bank0", "1000"), _fidx("bank0", "3000", seed="auto"),
           _fidx("bank1", "1000"), _fidx("common", "0500"),
           _fidx("pd", "2000"), _fidx("pd", "4000", "no", "auto")]
    _fa = [_fann("bank0", "0x1000"), _fann("bank1", "0x1000"),
           _fann("common", "0x0500"), _fann("pd", "0x2000")]
    # `common` borrows bank0's report, so the two carry the same applied figure
    # while functions_named counts the common index row on its own. `program`
    # names the one row an override touches, so a case asserts on a single
    # reported problem rather than on the same one four times.
    def _fman(program=None, **over):
        rows = [{"program": "bank0", "annotations_applied": "2",
                 "annotations_unmatched": "0", "functions_named": "2"},
                {"program": "bank1", "annotations_applied": "2",
                 "annotations_unmatched": "0", "functions_named": "1"},
                {"program": "common", "annotations_applied": "2",
                 "annotations_unmatched": "0", "functions_named": "1"},
                {"program": "pd", "annotations_applied": "1",
                 "annotations_unmatched": "0", "functions_named": "1"}]
        for r in rows:
            if program is None or r["program"] == program:
                r.update(over)
        return rows
    check("function layer: a manifest that agrees with both CSVs passes",
          not annotation_ledger_mismatches(_fman(), _fi, _fa),
          str(annotation_ledger_mismatches(_fman(), _fi, _fa)))
    # The trap this whole function is written around: 27 addresses are declared
    # under both bank scopes and the de-dup folds an identical common-area
    # function into one `common` row, so counting one row per scope and counting
    # rows per program are not the same arithmetic and only one of them is what
    # ApplyAnnotations.java did.
    _p = annotation_ledger_mismatches(_fman("bank0", annotations_applied="1"),
                                      _fi, _fa)
    check("function layer: a manifest whose annotations_applied disagrees with "
          "the CSV fails, naming both numbers",
          len(_p) == 1 and "=1;" in _p[0] and "give 2" in _p[0], str(_p))
    _p = annotation_ledger_mismatches(_fman("bank0", annotations_unmatched="1"),
                                      _fi, _fa)
    check("function layer: a manifest claiming an unmatched row the CSV cannot "
          "produce fails", len(_p) == 1 and "unmatched" in _p[0], str(_p))
    # A real unmatched row is legitimate data, not a fault: the script counts and
    # reports it, and the check's job is only to know that the manifest's figure
    # is the one the run produced. Whether a non-zero one should also fail the
    # build is ec/ghidra/README.md's open question, not this file's.
    _p = annotation_ledger_mismatches(
        _fman("pd", annotations_unmatched="1"), _fi, _fa + [_fann("pd", "0xDEAD")])
    check("function layer: a genuinely unresolvable row is counted, and the "
          "manifest recording that count passes",
          not _p, str(_p))
    _p = annotation_ledger_mismatches(_fman("bank0", functions_named="9"),
                                      _fi, _fa)
    check("function layer: a functions_named that disagrees with the index "
          "fails", len(_p) == 1 and "=9;" in _p[0] and "give 2" in _p[0],
          str(_p))
    _p = annotation_ledger_mismatches(_fman("bank0", annotations_applied=""),
                                      _fi, _fa)
    check("function layer: a counter that is not a number fails", len(_p) == 1,
          str(_p))
    # The ledger itself, both directions. bank0 0x3000 is marked `yes` with no
    # CSV row behind it; pd 0x4000 is `no` and has none either, so it is neither.
    _nwr, _abu, _bk = annotation_ledger(_fi, _fa)
    check("ledger: the export carries a non-placeholder name no CSV row wrote",
          [(r["program"], r["addr"]) for r in _nwr] == [("bank0", "3000")],
          str([(r["program"], r["addr"]) for r in _nwr]))
    check("ledger: an unannotated row with no CSV row is not a mismatch",
          _abu == [], str(_abu))
    # The opposite direction, which is why the ledger is two-way: a `thunk_`
    # name matches isPlaceholderName() (ExportDecompile.java:334-340) and the
    # row that wrote it applied anyway.
    _abu2 = annotation_ledger([_fidx("pd", "2000", "no")], _fa)[1]
    check("ledger: a CSV row that DID apply but is reported annotated=no is "
          "found, not passed over",
          len(_abu2) == 1 and _abu2[0][0]["addr"] == "2000", str(_abu2))
    # A common-scoped annotation and a bank0-scoped one are interchangeable for a
    # folded common row, and a check that joined the two indexes on (scope, addr)
    # would call this one unexplained.
    _nwr2 = annotation_ledger([_fidx("common", "0500")],
                              [_fann("bank0", "0x0500")])[0]
    check("ledger: a bank0-scoped row is accepted as backing a folded common "
          "index row", _nwr2 == [], str(_nwr2))
    # ... and the converse, which is the one an address-only join gets wrong.
    # The PD image is a separate 64 KiB program with its own address space
    # (ec/annotations/lightbar-bat-flow.md §2), so its 0x0000 is not the EC
    # common area's 0x0000 and a `common`-scoped row must not be handed to it --
    # which is exactly what ApplyAnnotations.mine() refuses to do, and what the
    # committed export shows: pd 0x0000 is `c_startup_idata_clear` with no CSV
    # row of its own, while the only annotation at 0x0000 is common-scoped.
    _nwr3 = annotation_ledger([_fidx("pd", "0000")],
                              [_fann("common", "0x0000")])[0]
    check("ledger: a common-scoped row is NOT accepted as backing a pd index "
          "row at the same address",
          [(r["program"], r["addr"]) for r in _nwr3] == [("pd", "0000")],
          str(_nwr3))
    # The matched middle, which is what lets the two directions be added up: on
    # this fixture each of the four CSV rows backs exactly one index row.
    check("ledger: the matched middle counts one index row per CSV row",
          len(_bk) == len(_fa) == 4
          and all(len(b) == 1 for _r, b in _bk),
          "%d backed, %d row(s)" % (len(_bk), len(_fa)))

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
    # (bank0 0xCC64), 1,782 -> 1,783 with issue #262's one bank1 0xC1E7,
    # 1,783 -> 1,804 with issue #136's 21 common-area interrupt-entry rows, then
    # 1,804 -> 1,848 with issue #134's 44 -- the call-graph tranche in
    # ec/annotations/call-graph.md, and 1,848 -> 1,851 with issue #250's three
    # (bank1 0x9CE8, 0x9D53 and 0xE2D3 -- the 0x1C12-trio seeds and the
    # 0x1C00-block dispatch its search turned on), then 1,851 -> 1,855 with
    # issue #558's four (common 0x07F0, 0x0F75, 0x158E and 0x1594 -- the top of
    # the corrected call-graph ranking, written up in
    # docs/findings/common-07f0-0f75-158e-1594-tranche.md), and 1,855 -> 1,872
    # with issue #561's seventeen common-area 0xFF fill rows
    # (docs/findings/ff-fill-census.md) -- both sets of rows are in this tree.
    check("EC: annotations/ghidra-functions.csv is 1,872 records, no short row "
          "and no duplicate (scope, addr)",
          len(_ann) == 1872 and not structure_problems("ghidra-functions.csv", _ann,
                                                       annotation_key, "(scope, addr)"),
          "%d record(s)" % len(_ann))
    # The function layer's three counters, on the committed files, which is where
    # docs/findings.md §18's corrected figures come from. The history of each
    # pin, because these are the numbers that move on purpose:
    #
    # annotations_applied 786 / 684 / 497, summing to 1,967 program-applications
    #   rather than 1,872 rows, because ApplyAnnotations.mine() hands a
    #   `common`-scoped row to BOTH bank programs and the 95 of them are counted
    #   once per program (691 + 95 = 786 for bank0, 589 + 95 = 684 for bank1).
    #   The manifest's `common` row borrows bank0's 786
    #   (MANIFEST_PROGRAM_SOURCE), and is excluded from the sum here for the
    #   same reason. This is not a pin that has moved on its own: it is the
    #   first run in which the number came from a report at all, and it has
    #   moved once since, 769 / 667 -> 786 / 684, when issue #561 added 17
    #   `common`-scoped 0xFF-fill rows that a bank consumes twice.
    # annotations_unmatched 0 / 0 / 0. Also the first run that could have
    #   reported otherwise -- the driver used to write a literal 0 here, so
    #   every manifest in the repository's history recorded a match it had not
    #   checked. 1,872 rows and zero unresolved is now a measurement.
    # functions_named 693 / 599 / 97 / 501, summing to 1,890. These are the
    #   figures the old `annotations_applied` column carried, unchanged: the
    #   number did not move, it acquired the name that describes it. It was
    #   1,787 when §18's drift paragraph was written and has grown with the
    #   annotation tranches since (1,866 at the time of the subsystems census,
    #   recorded in a later paragraph of §19, which also measured the gap at
    #   18); §18's correction quotes today's 1,890. Only `common` moved with
    #   #561 (80 -> 97): those 17 rows sit at addresses both banks carry, so the
    #   de-dup exports each one once, under `common`, and it lands there and
    #   nowhere else.
    _want_applied = {"bank0": 786, "bank1": 684, "pd": 497}
    check("EC: the manifest's annotations_applied is what the exporter's reports "
          "said -- 786 / 684 / 497 across the three programs, with `common` "
          "borrowing bank0's",
          {r["program"]: int(r["annotations_applied"]) for r in _mr
           if r["program"] in _want_applied} == _want_applied
          and next(int(r["annotations_applied"]) for r in _mr
                   if r["program"] == "common") == 786,
          str({r["program"]: r["annotations_applied"] for r in _mr}))
    check("EC: annotations_unmatched is 0 for all four programs, measured rather "
          "than written as a literal",
          all(int(r["annotations_unmatched"]) == 0 for r in _mr),
          str({r["program"]: r["annotations_unmatched"] for r in _mr}))
    _want_named = {"bank0": 693, "bank1": 605, "common": 97, "pd": 502}
    check("EC: functions_named is the index's own annotated=yes count per "
          "program, 693 / 605 / 97 / 502, summing to 1,897",
          {r["program"]: int(r["functions_named"]) for r in _mr} == _want_named
          and sum(_want_named.values()) == 1897
          and not annotation_ledger_mismatches(_mr, _ir, _ann),
          str(annotation_ledger_mismatches(_mr, _ir, _ann)[:2]))
    # The two-way ledger on the committed files, which is the whole substance of
    # the §18 correction. 25 and 0, and they close the arithmetic exactly:
    # 1,872 rows - 0 applied-but-unflagged + 25 named-without-a-row = 1,897.
    # The 25 is 15 `auto` (Ghidra's own caseD_* / default labels on switch
    # dispatchers, which isPlaceholderName() does not list among its placeholder
    # prefixes), 9 `call-target` and 1 `vector` -- pd 0x0000, where the only
    # annotation row at that address is `common`-scoped and the PD image has its
    # own separate function, so mine() correctly does not hand it over.
    #
    # The 0 is the seventh and last of what #602 renamed. The seven were
    # `thunk_to_*` / `thunk_call_*`: they applied, and isPlaceholderName()
    # matched the prefix they had chosen for themselves, because `thunk_` is
    # Ghidra's reserved prefix for an auto-thunk. Taking the name out of the
    # namespace -- `forward_to_*`, which eleven rows already used, and `call_*`
    # for the one forwarder that is a bare lcall -- is what moved them, and this
    # assertion is deliberately prefix-free: the fault was never "the name
    # starts with thunk_", it was "the index cannot see a row whose name reads
    # as Ghidra's", and an assertion naming the prefix would go green again the
    # moment a different reserved prefix was taken.
    #
    # That the count reached 0 rather than merely falling is the whole claim,
    # and it was not a short walk: issue #561's 17 `ff_filler_not_a_function_*`
    # rows were reported here too, on a stale export still carrying the
    # `FUN_CODE_*` placeholders Ghidra had given those addresses. Re-exporting
    # renamed them, and 24 became 7 -- not because 17 rows stopped applying, but
    # because the export that said they had not was itself older than they were.
    # Both rounds were the same fault seen at different ages, which is the
    # calibration this comment exists to keep.
    _nwr, _abu, _bk = annotation_ledger(_ir, _ann)
    _seed = {}
    for _r in _nwr:
        _seed[_r.get("seed_basis", "?")] = _seed.get(_r.get("seed_basis", "?"), 0) + 1
    check("EC: the ledger's 25 named-without-a-CSV-row split 15 auto / 9 "
          "call-target / 1 vector",
          len(_nwr) == 25 and _seed == {"auto": 15, "call-target": 9,
                                        "vector": 1},
          "%d row(s), %s" % (len(_nwr), _seed))
    check("EC: no index row a CSV row backs is reported annotated=no -- a row "
          "that applies and reads as unannotated is a name in Ghidra's reserved "
          "namespace, not a stale annotation",
          _abu == [],
          str([(r["program"], r["addr"]) for r, _bk in _abu]))
    check("EC: the two ledger directions close the arithmetic -- 1,872 - 0 + 25 "
          "= the 1,897 functions named",
          len(_ann) - len(_abu) + len(_nwr) == sum(_want_named.values()),
          "%d - %d + %d = %d, not %d"
          % (len(_ann), len(_abu), len(_nwr),
             len(_ann) - len(_abu) + len(_nwr), sum(_want_named.values())))
    # The reserved-namespace rule, and the two derivations of it. (a) is the
    # population claim and is the one that would have caught #602 before it was
    # opened: scanning the committed CSV for names the predicate matches needs
    # no Ghidra run at all, and it found exactly these seven. (b) and (c) are
    # what keep the rule from going stale -- the Java is what the exporters
    # call, the Python is what the check uses, and TongFang.java:132's "one
    # definition, used by every exporter" is only true while the two agree.
    _rp = grade_name_basis.reserved_prefix_problems(_ann)
    check("EC: no row in ghidra-functions.csv takes a name out of Ghidra's "
          "reserved namespace, so no row can apply and read as unannotated",
          not _rp, str(_rp[:3]))
    _want_literals = ([("startsWith", p)
                       for p in grade_name_basis.GHIDRA_RESERVED_PREFIXES]
                      + [("equals", x)
                         for x in grade_name_basis.GHIDRA_RESERVED_EXACT])
    _java = placeholder_name_tests()
    check("EC: every reserved prefix grade_name_basis.py knows is a literal in "
          "TongFang.java's isPlaceholderName()",
          all(lit in _java for lit in _want_literals),
          "%d of %d found; Java has %s"
          % (sum(1 for lit in _want_literals if lit in _java),
             len(_want_literals), _java))
    check("EC: isPlaceholderName() tests nothing grade_name_basis.py does not -- "
          "the two copies have not drifted apart",
          len(_java) == len(_want_literals),
          "%d test(s) in the Java, %d in the Python set; the extra is %s"
          % (len(_java), len(_want_literals),
             sorted(set(_java) - set(_want_literals)) or "none"))
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
          == len({annotation_key(r) for r in _ann}) == 1872
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

    # The decompile/index pairing, on a fixture. Presence was checked and the
    # content was not: `os.path.isfile` passes on a zero-length file, and a file
    # holding a different function entirely passes on having the right name on
    # disk. The known-good case is first, for the reason the structural faults
    # above are: a guard exercised only on known-bad input cannot tell "clean"
    # from "never ran".
    _d = _tf.mkdtemp()
    try:
        _rows = [{"program": "bank0", "addr": "0020", "name": "FUN_0020",
                  "out_file": "bank0/0020.c"}]
        _c = os.path.join(_d, "bank0", "0020.c")
        os.makedirs(os.path.dirname(_c))
        with open(_c, "w") as f:
            f.write("// bank0 @ 0020   FUN_0020   [named]\n"
                    "// Ghidra decompile, generated -- do not edit.\n\n"
                    "void FUN_0020(void)\n{\n}\n")
        _p, _r, _rn = c_presence_problems(_rows, _d)
        check("a .c that declares the address and name its index row gives it passes",
              not _p and _r == 1, str(_p))
        # A truncated write leaves a zero-length file, and isfile() passes on one.
        with open(_c, "w"):
            pass
        _p, _r, _rn = c_presence_problems(_rows, _d)
        check("a .c truncated to zero length is caught, and the file is named",
              len(_p) == 1 and "0020.c" in _p[0], str(_p))
        # The wrong function, in a file with the right name: the half-overwritten
        # export. An existence check cannot see this one.
        with open(_c, "w") as f:
            f.write("// bank0 @ 0020   FUN_0020   [named]\n\n"
                    "void FUN_0020(void)\n{\n}\n")
        _p, _r, _rn = c_presence_problems(_rows, _d)
        check("a .c declaring the function does pass again once it is restored",
              not _p, str(_p))
        with open(_c, "w") as f:
            f.write("// bank0 @ 0EA2   poll_d6c2   [named]\n\nvoid poll_d6c2(void) {}\n")
        _p, _r, _rn = c_presence_problems(_rows, _d)
        check("a .c carrying a different function's address is caught",
              len(_p) == 1 and "0EA2" in _p[0], str(_p))
        with open(_c, "w") as f:
            f.write("// bank0 @ 0020   poll_d6c2   [named]\n\nvoid poll_d6c2(void) {}\n")
        _p, _r, _rn = c_presence_problems(_rows, _d)
        check("a .c carrying a different function's name at the right address is "
              "caught too, so the name is checked and not only the address",
              len(_p) == 1 and "poll_d6c2" in _p[0], str(_p))
        os.remove(_c)
        _p, _r, _rn = c_presence_problems(_rows, _d)
        check("a .c removed is caught", len(_p) == 1 and "0020.c" in _p[0], str(_p))
        # One file, many rows, one read -- the shape §14a records, pinned here
        # too so the EC's copy of it cannot regress the same way the Windows
        # listing parse did.
        with open(_c, "w") as f:
            f.write("// bank0 @ 0020   FUN_0020   [named]\n\nvoid FUN_0020(void) {}\n")
        _many = _rows * 1000
        _p, _r, _rn = c_presence_problems(_many, _d)
        check("1,000 index rows naming one .c read it once, not 1,000 times",
              not _p and _r == 1, "%d read(s), %s" % (_r, _p[:1]))

        # The committed tree, so the coverage figure the check reports is
        # measured here and not only in --check's output.
        _p, _r, _rn = c_presence_problems(_ir, OUTDIR)
        check("EC: every one of the %d index rows' .c declares the address and "
              "name the row gives it" % len(_ir), not _p, "; ".join(_p[:3]))
        check("EC: that pairing cost %d file read(s) for %d row(s)"
              % (_r, len(_ir)), _r == len(_ir), "%d read(s)" % _r)
    finally:
        shutil.rmtree(_d, ignore_errors=True)

    # The committed .c digests. The known-good case is the committed tree
    # itself; the known-bad ones are a fixture, because corrupting the committed
    # .c to prove the check works is not a thing this self-test may do.
    if os.path.isfile(C_DIGESTS):
        _p = verify_c_digests()
        check("EC: every committed .c matches its digest row", not _p,
              "; ".join(_p[:3]))
        with open(C_DIGESTS, newline="") as _f:
            _rows_d = list(csv.DictReader(_f))
        check("EC: c-digests.csv carries this tool's own %d-column header"
              % len(C_DIGEST_COLUMNS),
              next(csv.reader(open(C_DIGESTS, newline="")), None) == C_DIGEST_COLUMNS)
        check("EC: one digest row per committed .c",
              len(_rows_d) == len(committed_c_files(OUTDIR)),
              "%d row(s), %d file(s)" % (len(_rows_d), len(committed_c_files(OUTDIR))))
    else:
        check("EC: c-digests.csv is committed", False, "not present")
    _d = _tf.mkdtemp()
    try:
        _c = os.path.join(_d, "bank0", "0020.c")
        os.makedirs(os.path.dirname(_c))
        with open(_c, "w") as f:
            f.write("// bank0 @ 0020   FUN_0020   [named]\n")
        _dg = os.path.join(_d, "c-digests.csv")
        n = write_c_digests(_dg, _d)
        check("EC: --write-digests records one row for the one .c", n == 1, str(n))
        check("EC: a freshly written digest verifies", not verify_c_digests(_dg, _d))
        # The row key is what write_c_digests wrote, not a hand-typed path: the
        # `path` column is repo-relative, so a fixture under /tmp is keyed by a
        # ../.. chain, and a hand-written "bank0/0020.c" would test the wrong
        # thing and pass for the wrong reason.
        _key = committed_c_files(_d)[0][1]
        # A digest that disagrees with the file it names.
        with open(_c, "a") as f:
            f.write("void FUN_0020(void) { /* a hand-mangled body */ }\n")
        _p = verify_c_digests(_dg, _d)
        check("EC: a .c that changed under its digest is caught, and the file is "
              "named", len(_p) == 1 and _key in _p[0], str(_p))
        # A row for a file that is not there.
        with open(_dg, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=C_DIGEST_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerow({"path": "bank0/9999.c", "sha256": "0" * 64, "bytes": "1"})
        _p = verify_c_digests(_dg, _d)
        check("EC: a digest row for a file that is not there is caught, on both "
              "halves -- the absent file and the undigested one",
              len(_p) == 2 and any("9999.c" in x for x in _p)
              and any("no digest row" in x for x in _p), str(_p))
        # A digest covering a strict subset of the tree: the vacuity guard.
        with open(_dg, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=C_DIGEST_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerow({"path": _key, "sha256": sha256(_c),
                        "bytes": str(os.path.getsize(_c))})
        # The digested file STAYS on disk and a second is added. Removing the
        # digested one instead -- which is what this first read like -- leaves
        # 1 row and 1 file, so the "N row(s) for M committed .c" guard never
        # fires and deleting it from the tool leaves every assertion here
        # passing. The guard is the one that stops a partial digest passing by
        # never being compared, so the fixture has to be the shape that trips it.
        with open(os.path.join(_d, "bank0", "0021.c"), "w") as f:
            f.write("// bank0 @ 0021   FUN_0021   [named]\n")
        _p = verify_c_digests(_dg, _d)
        check("EC: a digest covering some of the tree is caught by BOTH halves -- "
              "the undigested file and the row/file count",
              len(_p) == 2 and any("no digest row" in x for x in _p)
              and any("digest row(s) for" in x for x in _p), str(_p))
        # And the floor: a digest with nothing on disk to cover is a check that
        # has compared nothing, not a check that has passed.
        _p = verify_c_digests(_dg, os.path.join(_d, "gone"))
        check("EC: a digest against a tree with no .c at all is caught, rather "
              "than passing with nothing compared", len(_p) == 1
              and "nothing for this digest to cover" in _p[0], str(_p))
        # And the bootstrap's own refusal: --write-digests must not enshrine
        # the zero-length file it exists to catch.
        open(os.path.join(_d, "bank0", "0020.c"), "w").close()
        try:
            write_c_digests(_dg, _d)
            _refused = False
        except SystemExit as e:
            _refused = "zero-length" in str(e)
        check("EC: --write-digests refuses to bless a zero-length .c", _refused)
        # A symlink is the substitution a hash cannot see at all: hashing
        # follows the link, so the digest would record the TARGET's bytes and
        # the repository could hold no decompile at that address and pass.
        open(os.path.join(_d, "bank0", "0020.c"), "w").write(
            "// bank0 @ 0020   FUN_0020   [named]\n")
        _outside = os.path.join(_d, "outside.c")
        open(_outside, "w").write("// bank0 @ 9999   somewhere_else   [named]\n")
        os.remove(os.path.join(_d, "bank0", "0020.c"))
        os.symlink(_outside, os.path.join(_d, "bank0", "0020.c"))
        try:
            write_c_digests(_dg, _d)
            _refused = False
        except SystemExit as e:
            _refused = "symlink" in str(e)
        check("EC: --write-digests refuses to bless a .c that is a symlink, "
              "which is the one substitution a hash cannot see", _refused)
        # And the refusal happens BEFORE the file is opened for writing, so the
        # committed digest is not left half-rewritten. Asserted by content: the
        # digest on disk still names the .c as it was, with the symlink's target
        # nowhere in it.
        check("EC: the symlink refusal happens before the digest file is "
              "rewritten, so the committed digests are not left half-written",
              not os.path.isfile(_dg)
              or os.path.relpath(_outside, REPO) not in open(_dg).read())
    finally:
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

    # The per-program file-offset map, one known-answer anchor per program
    # against the committed listing at that address. One per program rather
    # than one in total because the failure this replaces -- bank 0's
    # subtraction applied to a bank-1 or PD address -- reads a different 32 KiB
    # and still produces a clean-looking comparison, so only an address that
    # lives in a program the map gets wrong can catch it.
    _anchors = (("bank0", 0xB158, b"\x90\x04\x39\xe0\xfc\x90"),
                # 0x806C is in bank 1's window, where the two banks hold
                # different code (make_bank_image.py --self-test), so this
                # anchor cannot pass read at bank 0's offset.
                ("bank1", 0x806C, b"\x90\x06\xd6\xe0\x60\x03"),
                # The common area is byte-identical in both banks, so this one
                # cannot tell bank0 from bank1 and is not asked to.
                ("common", 0x707D, b"\xef\x8d\xf0\xa4\xa8\xf0"),
                ("pd", 0xA678, b"\x90\x07\xd0\xe0\x04\xf0"))
    for _prog, _addr, _want in _anchors:
        _got = asm_opening_bytes(_prog, _addr, len(_want))
        check("file_offset: %s 0x%04X reads the bytes its own committed listing "
              "carries" % (_prog, _addr),
              _got == _want and fw[file_offset(_prog, _addr):
                                    file_offset(_prog, _addr) + len(_want)] == _want,
              "listing %s, firmware %s" % (_got.hex(" ") if _got else "(none)",
                                            fw[file_offset(_prog, _addr):
                                               file_offset(_prog, _addr)
                                               + len(_want)].hex(" ")))
    # And the negative half, which is what makes the four above mean anything:
    # no *other* offset may return the same six bytes, or a wrong mapping would
    # pass by coincidence. `common` and bank0 share an offset for the common
    # area and so are not a collision -- that is the fact the common anchor's
    # own comment gives, stated as a fact here rather than as a carve-out.
    _collide = [(p, "%04X" % a) for p, a, _ in _anchors
                for q in ("bank0", "bank1", "pd")
                if q != p and file_offset(q, a) != file_offset(p, a)
                and fw[file_offset(q, a):file_offset(q, a) + 6]
                == fw[file_offset(p, a):file_offset(p, a) + 6]]
    check("file_offset: no anchor is reachable at another bank's or the PD's "
          "offset, so the four above are not passing by coincidence",
          not _collide, str(_collide))

    # The sample, and the four fixtures inside it. The known answers are the
    # measured ones, and they moved when the terminator did: 0xB1F0's opening
    # names two addresses over seven instructions rather than six over forty,
    # because the old branch matcher never fired and every window ran to the
    # instruction cap with branches in it. 0xB158 still disagrees, on the byte
    # pair 0x0438/0x0439 -- the first fold the straight-line opening reaches,
    # where the forty-instruction window reached 0x04A6/0x04A7 further in.
    _sample = cross_decoder_sample()
    _sampled = {(r["program"], r["addr"]): kind for r, kind in _sample}
    check("the cross-decoder sample reaches all four programs, so a program "
          "cannot go unrepresented (%d function(s))" % len(_sample),
          {p for p, _ in _sampled} == {"bank0", "bank1", "common", "pd"},
          str(sorted({p for p, _ in _sampled})))
    check("every sampled address is one the listing index carries, and no "
          "address is sampled twice",
          len(_sampled) == len(_sample)
          and all((r["program"], r["addr"]) in _lr_keys for r, _ in _sample))
    check("every function the comparison was introduced on is still in the "
          "sample", all((p, "%04X" % a) in _sampled
                        for p, a in CROSS_DECODER_FIXTURES))
    _cd = {(r["program"], r["addr"]): r for r in cross_decoder_results(fw)}
    # The `sample` column is a controlled vocabulary too, and the reason a
    # reader can treat a `stride` row as "nobody has read this one" -- which is
    # what makes the stride worth having.
    check("every sampled row says how it was sampled, from the documented set",
          all(r["sample"] in CROSS_DECODER_SAMPLES for r in _cd.values())
          and all(k in CROSS_DECODER_SAMPLES for k in _sampled.values()),
          str(sorted({r["sample"] for r in _cd.values()})))
    check("every sampled row's outcome is one of the four",
          all(r["outcome"] in CROSS_DECODER_OUTCOMES for r in _cd.values()),
          str(sorted({r["outcome"] for r in _cd.values()})))
    _expect = {("bank0", "B1F0"): ("agree", "7", "0A4E 0A4F", "0A4E 0A4F", ""),
               ("bank0", "B158"): ("disagree", "6", "0438 0439 0A48", "0A48",
                                   "0438 0439"),
               ("bank0", "BAE5"): ("vacuous", "1", "", "", ""),
               ("common", "707D"): ("vacuous", "13", "", "", "")}
    for _key, (_outcome, _insns, _linear, _in_c, _missing) in _expect.items():
        # `.get`, so a fixture that has dropped out of the sample is a failed
        # assertion above and a failed assertion here, rather than a KeyError
        # out of the middle of the self-test.
        _row = _cd.get(_key)
        check("%s 0x%s: %d straight-line instruction(s), %s"
              % (_key[0], _key[1], int(_insns), _outcome),
              _row is not None
              and (_row["outcome"], _row["insns"], _row["linear"], _row["in_c"],
                   _row["missing"]) == (_outcome, _insns, _linear, _in_c, _missing),
              str({c: _row[c] for c in ("outcome", "insns", "linear", "in_c",
                                        "missing")} if _row else "not sampled"))

    # The vocabulary, against the names the export actually carries. Every
    # address in xdata-symbols.csv that is exported under a name spelling its
    # own address has to be readable by _EXTMEM, or the comparison reports
    # `disagree` for a C that names the address in so many words -- which is
    # what the XDATA_1664 row did to 0xC1E7, silently, and what
    # `build_ec_decompile.py --check` then recomputed and blessed. A name that
    # is a register's real name (PROJECT_ID) carries no address and is
    # deliberately out of the vocabulary; the assertion is about the two
    # spellings that do.
    _vocab_missed = sorted(addr for addr, name in _XDATA_NAME_ADDR.items()
                           if not _EXTMEM.search(name))
    check("every address xdata-symbols.csv exports under an address-carrying "
          "name is in the comparison's vocabulary (%d name(s))"
          % len(_XDATA_NAME_ADDR), not _vocab_missed, str(_vocab_missed[:4]))

    # The ratchet, exercised. A check that has never been seen to fail is an
    # absent one, which is §14b's own sentence and the reason these cases are
    # here at all: the report that matches first, then a verdict flipped, a row
    # in each direction, and a sample that compares nothing -- each of which has
    # to be reported.
    _rows_now = list(_cd.values())
    _p = cross_decoder_problems(_rows_now, _rows_now)[1]
    check("a report that matches this run has no problem", not _p, str(_p[:2]))
    _flipped = [dict(r) for r in _rows_now]
    _flipped[0]["outcome"] = ("disagree" if _flipped[0]["outcome"] == "agree"
                               else "agree")
    _p = cross_decoder_problems(_flipped, _rows_now)[1]
    check("a hand-flipped outcome is reported, naming the row and the column",
          len(_p) == 1 and "outcome" in _p[0] and _rows_now[0]["addr"] in _p[0],
          str(_p))
    _p = cross_decoder_problems(_rows_now, _rows_now[1:])[1]
    check("a report carrying a row the sample no longer has is reported stale",
          len(_p) == 1 and "not in the sample" in _p[0], str(_p))
    _p = cross_decoder_problems(_rows_now[1:], _rows_now)[1]
    check("a sampled row the report does not carry is reported as predating "
          "this export", len(_p) == 1 and "not in the report" in _p[0], str(_p))
    _p = degenerate_sample_problems({"agree": 0, "disagree": 0, "vacuous": 12,
                                     "no-export": 0})
    check("a wholly vacuous sample is a problem, not a pass",
          len(_p) == 1 and "ratchets on nothing" in _p[0], str(_p))
    _p = degenerate_sample_problems({"agree": 0, "disagree": 0, "vacuous": 0,
                                     "no-export": 12})
    # Both, and both true: nothing exported means nothing compared, so the
    # no-export guard and the compared-0 guard fire together here. Naming one
    # of them and not the other would be a summary that understates the sample.
    check("a sample with nothing exported to compare is reported as both "
          "unexported and vacuous", len(_p) == 2
          and any("no exported C" in m for m in _p)
          and any("compared 0 of" in m for m in _p), str(_p))
    _p = degenerate_sample_problems({"agree": 3, "disagree": 1, "vacuous": 2,
                                     "no-export": 0})
    check("a sample with rows in it is not a degenerate sample", not _p, str(_p))

    # The subsystems.md citation check, on synthetic fixtures. The known-good
    # case is first on purpose, for the reason the structural cases above are:
    # a guard exercised only on known-bad input cannot tell "clean" from
    # "never ran". Each bad case is then the good document with exactly one
    # thing wrong, so a failure names the guard that stopped rejecting.
    _sd = os.path.join(work, "subsystems-self-test")
    os.makedirs(_sd, exist_ok=True)
    _srows = [
        {"scope": "bank0", "addr": "0xB158", "name": "charge_target_update",
         "type": "charge-target", "evidence": "ev/ok.asm"},
        {"scope": "common", "addr": "0x052F", "name": "int0_target_is_one_byte_reti",
         "type": "unresolved", "evidence": "ev/ok.asm"},
    ]
    os.makedirs(os.path.join(_sd, "ev"), exist_ok=True)
    open(os.path.join(_sd, "ev", "ok.asm"), "w").write("; fixture\n")
    _good_doc = (
        "## 3. charge\n"
        "- `bank0` `0xB158` `charge_target_update` -- recomputes the target\n"
        "## 4. vectors\n"
        "- `common` `0x052F` `int0_target_is_one_byte_reti` [unresolved] -- one reti\n")
    _measured = {"exported functions": 10, "annotated function rows": 2,
                 "rows the index marks annotated": 3, "unresolved rows": 1}
    _census_doc = ("- `exported functions` — 10\n"
                   "- `annotated function rows` — 2\n"
                   "- `rows the index marks annotated` — 3\n"
                   "- `unresolved rows` — 1\n")

    def _sp(doc, measured=None):
        """The problems in `doc`, with its own census read out of its prose."""
        return subsystems_problems(doc, _srows, repo=_sd,
                                   stated=subsystems_stated_counts(doc),
                                   measured=measured)

    check("subsystems: a document whose citations all resolve passes",
          not _sp(_good_doc), "; ".join(_sp(_good_doc)))
    check("subsystems: the citation format is three backticked fields, and the "
          "known-good case really is read as two citations",
          len(subsystems_citations(_good_doc)) == 2)
    _p = _sp(_good_doc.replace("`bank0` `0xB158`", "`bank0` `0xB159`"))
    check("subsystems: a citation that resolves to no row is reported",
          len(_p) == 1 and "is not a row" in _p[0], str(_p))
    _p = _sp(_good_doc.replace("charge_target_update`", "charge_target_updateXX`"))
    check("subsystems: a cited name that disagrees with the CSV is reported",
          len(_p) == 1 and "is named charge_target_update in" in _p[0], str(_p))
    _p = _sp(_good_doc.replace(" [unresolved]", ""))
    check("subsystems: an unresolved row cited without the marker is reported",
          len(_p) == 1 and "without the [unresolved] marker" in _p[0], str(_p))
    _p = _sp(_good_doc.replace("`charge_target_update` --",
                               "`charge_target_update` [unresolved] --"))
    check("subsystems: the marker on a row that is not unresolved is reported",
          len(_p) == 1 and "is cited with the [unresolved] marker" in _p[0], str(_p))
    _bad_ev = [dict(_srows[0]), dict(_srows[1])]
    _bad_ev[0]["evidence"] = "ev/gone.asm; ev/ok.asm"
    _p = subsystems_problems(_good_doc, _bad_ev, repo=_sd)
    check("subsystems: an evidence path that is not on disk is reported",
          len(_p) == 1 and "does not exist on disk" in _p[0]
          and "ev/gone.asm" in _p[0], str(_p))
    # The existence check reaches every row of the CSV, not only the ones this
    # document quotes. Five of the eleven stale paths the map's check is
    # credited with finding sit on rows it never cites, which is what a guard
    # that stops at the citation list cannot see -- so the good uncited row and
    # the bad one are both here, and the assertion is that only the bad one is
    # reported.
    _uncited = [dict(r) for r in _srows] + [
        {"scope": "common", "addr": "0x0C7A", "name": "quoteless_helper",
         "type": "logic", "evidence": "ev/ok.asm"},
        {"scope": "common", "addr": "0x0EF3", "name": "quoteless_helper_2",
         "type": "logic", "evidence": "ev/gone.asm"}]
    _p = subsystems_problems(_good_doc, _uncited, repo=_sd)
    check("subsystems: a dead evidence path on a row the document never cites "
          "is reported, and an uncited row with a live path is not",
          len(_p) == 1 and "does not exist on disk" in _p[0]
          and "ev/gone.asm" in _p[0] and "0x0EF3" in _p[0], str(_p))
    _stated = subsystems_stated_counts(_census_doc)
    check("subsystems: the four census counts are read back out of the prose",
          {k: [v for _, v in vs] for k, vs in _stated.items()}
          == {k: [v] for k, v in _measured.items()}, str(_stated))
    # The document is the side that is wrong here: a number edited in the prose
    # without re-deriving it. The recount is the committed files, so the message
    # reads from the stated value to the measured one.
    _p = _sp(_census_doc.replace("`exported functions` — 10",
                                 "`exported functions` — 11") + _good_doc, _measured)
    check("subsystems: a census count that disagrees with the recount is reported",
          len(_p) == 1 and "states 11 exported functions" in _p[0], str(_p))
    # The document states each count more than once -- the census and the
    # measured remainder -- and every occurrence is compared, so a wrong number
    # in the *earlier* of the two is reported rather than overwritten by the
    # later one that agrees with the recount.
    _twice = (_census_doc.replace("`exported functions` — 10",
                                  "`exported functions` — 11")
              + _census_doc + _good_doc)
    _p = _sp(_twice, _measured)
    check("subsystems: a census count wrong in the earlier of two occurrences "
          "is reported",
          len(_p) == 1 and "line 1: the census states 11 exported functions" in _p[0],
          str(_p))
    _p = _sp(_census_doc + _census_doc.replace("`unresolved rows` — 1",
                                               "`unresolved rows` — 2")
             + _good_doc, _measured)
    check("subsystems: a census count wrong in the later of two occurrences "
          "is reported",
          len(_p) == 1 and "line 8: the census states 2 unresolved rows" in _p[0],
          str(_p))
    _p = _sp(_census_doc + _census_doc + _good_doc, _measured)
    check("subsystems: a count stated twice and right twice passes",
          not _p, "; ".join(_p))
    _p = _sp(_census_doc.replace("- `unresolved rows` — 1\n", "") + _good_doc,
             _measured)
    check("subsystems: a census count that is missing is reported",
          len(_p) == 1 and "states no `unresolved rows` count" in _p[0], str(_p))
    # The per-program table beside those four totals, which is the same claim
    # split by program and the one a check that reads only the bullets cannot
    # see. It gets its own fixture rather than riding inside _census_doc, so the
    # cases above keep the line numbers they assert on, and the four bullets
    # lead it because a table-only document would be reported for the counts it
    # never states.
    _table = {"bank0": (5, 4, 1), "bank1": (4, 3, 1),
              "pd": (3, 2, 1), "common": (6, 2, 4)}
    _table_rows = ("| program | exported | annotated | unannotated |\n"
                   "|---|---|---|---|\n"
                   "| `bank0` | 5 | 4 | 1 (20%) |\n"
                   "| `bank1` | 4 | 3 | 1 (25%) |\n"
                   "| `pd` | 3 | 2 | 1 (33%) |\n"
                   "| `common` | 6 | 2 | 4 (67%) |\n")
    _table_doc = _census_doc + "## 2. census\n" + _table_rows
    _measured_table = dict(_measured)
    _measured_table[SUBSYSTEM_TABLE_KEY] = _table
    _read_table = subsystems_stated_table(_table_doc)
    check("subsystems: the per-program table is read back out of the document",
          _read_table == {"bank0": [(8, 5, 4, 1, 20)], "bank1": [(9, 4, 3, 1, 25)],
                          "pd": [(10, 3, 2, 1, 33)], "common": [(11, 6, 2, 4, 67)]},
          str(_read_table))
    _p = _sp(_table_doc + _good_doc, _measured_table)
    check("subsystems: a per-program table that agrees with the recount passes",
          not _p, "; ".join(_p))
    # The fault this was extended over: the totals are right, the bullets are
    # right, and one program's split is left at the numbers a re-export moved.
    _p = _sp(_table_doc.replace("| `common` | 6 | 2 | 4 (67%) |",
                                "| `common` | 6 | 3 | 3 (50%) |") + _good_doc,
             _measured_table)
    check("subsystems: a per-program split that disagrees with the export is "
          "reported",
          len(_p) == 1 and "line 11: the census splits common as 6 exported, "
          "3 annotated, 3 unannotated" in _p[0], str(_p))
    _p = _sp(_table_doc.replace("| `pd` | 3 | 2 | 1 (33%) |",
                                "| `pd` | 3 | 2 | 1 (66%) |") + _good_doc,
             _measured_table)
    check("subsystems: a per-program share that disagrees with its own cells "
          "is reported",
          len(_p) == 1 and "line 10: the census states pd as 66% unannotated"
          in _p[0] and "1 of 3 is 33%" in _p[0], str(_p))
    _p = _sp(_table_doc.replace("| `pd` | 3 | 2 | 1 (33%) |\n", "")
             + _good_doc, _measured_table)
    check("subsystems: a per-program row that is missing is reported",
          len(_p) == 1 and "states no `pd` row" in _p[0], str(_p))
    _p = _sp(_table_doc.replace("`pd`", "`bank2`") + _good_doc, _measured_table)
    check("subsystems: a per-program row the export does not have is reported, "
          "and not raised",
          len(_p) == 2 and "line 10: the census's per-program table has a "
          "`bank2` row" in _p[0] and "states no `pd` row" in _p[1], str(_p))
    _p = _sp("## 3. a section that cites nothing at all\n")
    check("subsystems: a document that cites no function is reported",
          len(_p) == 1 and "cites no functions" in _p[0], str(_p))
    # And the committed document, read the way the gate reads it.
    if os.path.isfile(SUBSYSTEMS):
        _real, _n = check_subsystems(_ann, _ir)
        check("subsystems: the committed %s passes its own check"
              % os.path.relpath(SUBSYSTEMS, REPO), not _real, "; ".join(_real[:3]))
        check("subsystems: the committed map cites functions", _n > 0, "%d" % _n)

    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    if not ok:
        return 1
    # The cross-decoder comparison: Ghidra's C against disasm8051.py, over a
    # sample of the committed export. It runs only when asked for, which is
    # what .github/scripts/agent-gates-deep.sh does. What is no longer true of
    # it is that its result is read by nobody: the outcome is committed to
    # ec/ghidra/cross-decoder.csv and --check ratchets on it every commit, so
    # the printed run is the same measurement the cheap tier makes and the
    # difference between them is the tier, not the comparison.
    if args.cross_decoder:
        print_cross_decoder(cross_decoder_results(open(FIRMWARE, "rb").read()))
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
#
# It ends at the first flow instruction, taken from disasm8051.FLOW_OPCODES.
# The list of mnemonics this used to match on was a `re` against the rendered
# line, whose first column is the address, so it never fired and every sample
# decoded all CROSS_DECODER_WINDOW instructions with branches and all -- which
# is exactly the desync above, and the reason the recorded output said "40
# straight-line instruction(s)" for a function whose straight-line opening is
# seven. The opcode set is the decoder's own, and it also stops at the
# cjne/djnz/ajmp/acall forms that the list omitted.
CROSS_DECODER_COLUMNS = ["program", "addr", "name", "sample", "insns", "linear",
                         "in_c", "missing", "outcome"]
# The four outcomes, in the order the denominator reports them. A controlled
# vocabulary, like VARIABLE_KINDS, and `disagree` is one bucket on purpose:
# splitting it needs the byte-pair-folding case enumerated rather than
# described, and guessing which of a function's C reads is a fold would
# manufacture the very distinction the comparison is meant to measure. What
# `disagree` does contain is measured in docs/findings.md §14i, and the answer
# is not "the decompiler got it wrong".
CROSS_DECODER_OUTCOMES = ("agree", "disagree", "vacuous", "no-export")
CROSS_DECODER_SAMPLES = ("annotation", "stride")
# One in eight of the non-annotated remainder. 927 rows over four programs at
# this value, so each program is sampled rather than represented, and a tenth
# of what the stride covers.
CROSS_DECODER_STRIDE = 8
# The bound on a window, not its length: every function measured ends sooner,
# on a flow instruction or on its own size. Kept because the walk is linear
# and unbounded would be a whole-function comparison, which is the noise
# above.
CROSS_DECODER_WINDOW = 40
# The four functions the comparison was introduced on, kept in the sample as
# known answers rather than as a special case: all four are annotated, so the
# backbone below already carries them, and self_test() asserts what they now
# read. Two of the four compare nothing at all -- 0xBAE5 and 0x707D have no
# mov dptr,#imm in their opening -- which is the reason the denominator
# exists.
CROSS_DECODER_FIXTURES = [("bank0", 0xB1F0), ("bank0", 0xB158),
                          ("bank0", 0xBAE5), ("common", 0x707D)]
# How many disagreement rows a run prints before it points at the report. Same
# reason as verify_reassembly.MOVED_CAP: a reader acts on the first few, and
# the rest are a grep away in a file whose path is already on screen.
CROSS_DECODER_CAP = 20
# The XDATA addresses a decompiled C names. The comparison's whole vocabulary:
# an address registers.yaml does not name cannot appear as a symbol carrying
# its address, so it is reported `disagree` whether or not the C mentions it.
# Measured rather than argued in docs/findings.md §14i.
#
# Two spellings carry an address, and a row added to registers.yaml picks
# between them without saying so: Ghidra's own default is `DAT_EXTMEM_0a4e`
# (this matches the `EXTMEM_` inside it), while a register whose name is the
# address -- the `XDATA_1664` row issue #255 added -- is exported under that
# name by gen_xdata_symbols.py. Matching only the first emptied `in_c` for
# every such listing and reported `disagree` against a C that names the
# address in so many words, so both are in the vocabulary and self_test()
# pins that against the names xdata-symbols.csv actually carries.
#
# The class spans both cases because the two spellings do not agree on one:
# SLEIGH writes the hex lowercase and gen_xdata_symbols.py writes it
# uppercase, so a lowercase-only class matched every `EXTMEM_` and none of the
# `XDATA_` names carrying an A-F. compare_function() upper-cases `in_c` either
# way, so widening the class here changes no comparison -- it stops the
# uppercase names being invisible to it in the first place.
_EXTMEM = re.compile(r"(?:EXTMEM|XDATA)_([0-9a-fA-F]{4})")
# An address column in a committed .asm, and one slot of its byte column. Used
# only to prove the per-program file-offset map against the listings themselves,
# so both are anchored: a line whose shape is not the one the exporter writes is
# skipped rather than parsed as though it were.
_ASM_ADDR = re.compile(r"[0-9A-Fa-f]{4,8}")
_ASM_SLOT = re.compile(r"[0-9A-Fa-f]{2}")


def file_offset(program, addr):
    """Byte offset of a runtime address in ec/firmware/GMxMGxx_11.800.

    A lookup over the three windows, not `0x08000 + (addr - COMMON_END)`, which
    is bank 0's mapping and the other two wrong by a window: bank 1's CODE is
    at 0x10000 and the PD image is a separate 64 KiB program at 0x20000.
    Reading a bank-1 or PD address at bank 0's offset lands in a different
    32 KiB, and the comparison would go on reporting a clean result over the
    wrong bytes -- which is the shape of failure this returns rather than
    raises, and why self_test() pins one anchor per program against the
    committed .asm.

    verify_gap_text.py reaches the same bytes a different way, by building the
    flat per-bank images make_bank_image.py makes and reading address ==
    offset, so it needs no arithmetic here. This reads the firmware itself, so
    that the comparison and the manifest's SHA-256 are about one file.
    """
    if program == "pd":
        return PD_WINDOW + addr
    if addr < COMMON_END:
        return addr
    return BANK_WINDOWS[program] + (addr - COMMON_END)


def asm_opening_bytes(program, addr, count):
    """The first `count` bytes of the committed listing at `addr`, or None.

    Strict about the address, and the strictness is the point: the first
    instruction line of a committed .asm has to BE the function's entry, or a
    listing read from the wrong place would still hand back bytes and the
    mapping assertion would pass on them. The byte column is three fixed slots
    with `-` for an absent byte (ghidra/README.md, "The disassembly, and the
    1:1 property"), which is what makes `cols[1:4]` the encoding rather than
    part of the mnemonic.
    """
    path = os.path.join(OUTDIR, program, "%04X.asm" % addr)
    if not os.path.isfile(path):
        return None
    out = bytearray()
    seen = False
    for line in open(path, errors="replace"):
        if line.startswith(";") or not line.strip():
            continue
        cols = line.split()
        if len(cols) < 2 or not _ASM_ADDR.fullmatch(cols[0]):
            continue
        if not seen:
            seen = True
            if int(cols[0], 16) != addr:
                return None
        slots = cols[1:4]
        if any(s != "-" and not _ASM_SLOT.fullmatch(s) for s in slots):
            return None              # not the fixed three-slot byte column
        out += bytes(int(s, 16) for s in slots if s != "-")
        if len(out) >= count:
            break
    return bytes(out[:count]) if seen else None


def cross_decoder_sample():
    """The sampled functions, as [(listing row, how it was sampled), ...].

    Derived from two committed CSVs and nothing else, because a literal of four
    addresses said nothing about the 2,710 the export carries -- the
    denominator the issue asks for is only a denominator if M is a number this
    function produced from the tree rather than a number someone typed:

      backbone  every (scope, addr) in ec/annotations/ghidra-functions.csv
               that the listing index carries -- the functions a person or an
               agent has read and cited. All four programs are represented in
               it, so per-program coverage holds by construction; self_test()
               asserts that rather than assuming it.
      stride    every CROSS_DECODER_STRIDE-th of the rest in sorted
               (program, addr) order, plus each program's first non-annotated
               row, so coverage survives a program whose remainder is tiny.

    Sorted, and never ordered by a set or a hash, because --check compares the
    committed report's rows against this list: a sample that came out in a
    different order on a different run of the same inputs would fail the gate
    for no reason at all.
    """
    if not os.path.isfile(LISTING_INDEX):
        raise SystemExit("error: no listing index at %s; there is no export to "
                         "sample" % os.path.relpath(LISTING_INDEX, REPO))
    listing = {(r["program"], r["addr"]): r
               for r in read_index(LISTING_INDEX)}
    backbone = {annotation_key(r) for r in annotation_rows()} & set(listing)
    kind = {key: "annotation" for key in backbone}
    firsts = {}
    for key in sorted(listing):
        firsts.setdefault(key[0], key)
    rest = sorted(set(listing) - backbone)
    for key in rest[::CROSS_DECODER_STRIDE] + sorted(firsts.values()):
        kind.setdefault(key, "stride")
    return [(listing[key], kind[key]) for key in sorted(kind)]


def compare_function(program, addr, size, out_file, fw):
    """One function's straight-line opening against its committed C.

    -> (outcome, insns, linear, in_c, missing), the address sets upper-case hex
    and `missing` the one that decided the outcome.

    The window's own bound is `size` from the listing index -- the exporters
    count a function's bytes slightly differently, and the listing's extent is
    the one this walk is over.
    """
    if not out_file or out_file.startswith("("):
        return "no-export", 0, set(), set(), set()
    path = os.path.join(OUTDIR, out_file.replace(".asm", ".c"))
    if not os.path.isfile(path):
        return "no-export", 0, set(), set(), set()
    file_off = file_offset(program, addr)
    limit = file_off + size if size else None
    insns, linear = 0, set()
    for i, raw, _text in disasm8051.decode(fw, file_off, CROSS_DECODER_WINDOW,
                                          addr=addr, stop_at_flow=True):
        # decode() yields the instruction it stopped at and the count this
        # comparison has always reported excluded it, so it is dropped here
        # rather than counted and then subtracted. The second condition is the
        # function's own size, and is the one the first used to shadow by never
        # matching.
        if raw[0] in disasm8051.FLOW_OPCODES or (limit is not None and i >= limit):
            break
        insns += 1
        if raw[0] == MOV_DPTR:
            linear.add("%04X" % ((raw[1] << 8) | raw[2]))
    if not linear:
        return "vacuous", insns, set(), set(), set()
    in_c = {m.upper() for m in _EXTMEM.findall(open(path, errors="replace").read())}
    missing = linear - in_c
    return ("disagree" if missing else "agree"), insns, linear, in_c, missing


def cross_decoder_results(fw):
    """The whole comparison, once. -> [report row, ...] by (program, addr).

    One read of the listing index, one of the annotations, one of the firmware
    and one of each sampled `.c`. The first two used to sit inside the
    per-function path -- function_size() re-read all 2,710 listing rows for
    every sampled function, and one subprocess was spawned per function -- which
    at four functions was invisible and at 1,901 is the "loop over the wrong
    collection" shape docs/findings.md §14a and §14d exist to warn about.

    The rows carry string cells rather than Python values, so --report writes
    them verbatim and --check can compare a recomputed row against a committed
    one cell for cell. `in_c` is the intersection, not the C's whole symbol
    set: the column is "what both decoders saw", and a function can name twenty
    addresses of which the linear walk saw three.
    """
    rows = []
    for row, kind in cross_decoder_sample():
        program, addr = row["program"], int(row["addr"], 16)
        outcome, insns, linear, in_c, missing = compare_function(
            program, addr, int(row["size"]), row["out_file"], fw)
        rows.append({
            "program": program,
            "addr": row["addr"],
            "name": row["name"],
            "sample": kind,
            "insns": str(insns),
            "linear": " ".join(sorted(linear)),
            "in_c": " ".join(sorted(linear & in_c)),
            "missing": " ".join(sorted(missing)),
            "outcome": outcome,
        })
    return rows


def cross_decoder_summary(rows):
    """{outcome: n} over CROSS_DECODER_OUTCOMES, every key present."""
    counts = dict.fromkeys(CROSS_DECODER_OUTCOMES, 0)
    for row in rows:
        counts[row["outcome"]] += 1
    return counts


def denominator_line(counts):
    """The line that says how much of the sample was actually compared.

    Printed on every run, in the shape the issue named, because the failure
    this whole change exists to close is a vacuous sample printing in the same
    form as a real one: two of the original four functions compared nothing, and
    the run said nothing that a reader could tell apart from a pass.
    """
    total = sum(counts.values())
    return ("compared %d of %d function%s, %d vacuous; %d agreed, %d disagreed, "
            "%d no-export"
            % (counts["agree"] + counts["disagree"], total,
               "" if total == 1 else "s", counts["vacuous"], counts["agree"],
               counts["disagree"], counts["no-export"]))


def cross_decoder_line(row):
    """One function's line, in the shape the comparison has always printed."""
    head = "    %s %s 0x%s %s:" % (
        {"agree": "ok  ", "disagree": "note"}.get(row["outcome"], "--   "),
        row["program"], row["addr"], row["name"])
    if row["outcome"] == "no-export":
        return head + " no exported C committed, nothing to compare"
    if row["outcome"] == "vacuous":
        return head + (" no mov dptr,#imm in the opening %d instruction(s); "
                       "nothing to compare" % int(row["insns"]))
    linear = row["linear"].split()
    return head + (" %d straight-line instruction(s) name %d XDATA address(es) "
                   "linearly; the C names %d of them%s"
                   % (int(row["insns"]), len(linear), len(row["in_c"].split()),
                      "" if row["outcome"] == "agree"
                      else " -- not named in the C: " + row["missing"]))


def is_bank_switch_trampoline(row, span=8):
    """True when a row's function opens with `mov dptr,#imm` and an `ljmp` to a
    BL51 bank-switch stub.

    Not an outcome -- CROSS_DECODER_OUTCOMES is the vocabulary and this is not
    in it -- but a measured shape inside the `disagree` bucket, and worth
    naming on a run because it is what the first rows of that list are. A
    trampoline's C calls `bl51_bank_select_1(0x88f0)`, so the address is right
    there in the output as a literal argument; it is simply not an `EXTMEM_`
    symbol, and the comparison's vocabulary is `EXTMEM_`. Read without that,
    a list of twenty consecutive trampolines reads as twenty defects.

    Matched on the bytes rather than on the name: the names carry
    "trampoline" today and that is a reading, not a fact about the encoding.
    """
    opening = asm_opening_bytes(row["program"], int(row["addr"], 16), span)
    if not opening:
        return False
    return any(opening[i] == MOV_DPTR and opening[i + 3] == 0x02
               and ((opening[i + 4] << 8) | opening[i + 5]) in BANK_STUBS
               for i in range(len(opening) - 5))


def print_cross_decoder(rows):
    """The denominator, the per-program coverage, the fixtures, the misses.

    A per-line dump of 1,901 rows would be unreadable and would be read
    not at all, so the detail lives in the committed report and the run names
    where. What is printed is what cannot be got from the report by eye: the
    denominator, whether every program is still represented, and the four
    functions the comparison started on.
    """
    counts = cross_decoder_summary(rows)
    print("  cross-decoder agreement (Ghidra's C vs disasm8051.py, each sampled "
          "function's opening straight-line instructions):")
    per_program = {}
    for row in rows:
        bucket = per_program.setdefault(row["program"], dict.fromkeys(
            CROSS_DECODER_OUTCOMES, 0))
        bucket[row["outcome"]] += 1
    for program in sorted(per_program):
        c = per_program[program]
        print("    %-7s %4d sampled, %4d compared, %4d vacuous, %4d disagree, "
              "%d no-export" % (program, sum(c.values()), c["agree"]
                                + c["disagree"], c["vacuous"], c["disagree"],
                                c["no-export"]))
    print("    " + denominator_line(counts))
    print("    the %d function(s) the comparison was introduced on:"
          % len(CROSS_DECODER_FIXTURES))
    by_key = {(r["program"], r["addr"]): r for r in rows}
    for program, addr in CROSS_DECODER_FIXTURES:
        row = by_key.get((program, "%04X" % addr))
        print(cross_decoder_line(row) if row else
              "    FAIL  %s 0x%04X is no longer in the sample" % (program, addr))
    disagree = [r for r in rows if r["outcome"] == "disagree"]
    if disagree:
        where = os.path.relpath(CROSS_DECODER, REPO)
        print("    %d row(s) disagree; the first %d, the rest in %s:"
              % (len(disagree), min(len(disagree), CROSS_DECODER_CAP), where))
        for row in disagree[:CROSS_DECODER_CAP]:
            print(cross_decoder_line(row))
        if len(disagree) > CROSS_DECODER_CAP:
            print("    ... and %d more" % (len(disagree) - CROSS_DECODER_CAP))
        tramps = sum(1 for r in disagree if is_bank_switch_trampoline(r))
        print("    %d of the %d are the `mov dptr,#imm; ljmp <BL51 stub>` "
              "bank-switch trampoline, whose C passes the\n    address to "
              "bl51_bank_select_* as a literal rather than naming it as XDATA. "
              "A disagreement is not a\n    defect and not a decoder verdict: "
              "docs/findings.md §14i measures what this bucket holds."
              % (tramps, len(disagree)))


def write_cross_decoder_report(rows, path=CROSS_DECODER):
    """The rows, to the committed report. Its only writer.

    Safe to regenerate from committed inputs alone -- firmware, listings, C,
    disasm8051.py and the annotations -- so refreshing it needs python3 and no
    Ghidra run. That is what keeps the check honest: a row cannot be refreshed
    by copying a value across by hand, because --check recomputes it.
    """
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CROSS_DECODER_COLUMNS,
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path


def cross_decoder_problems(committed, current):
    """The committed report against this run's rows. -> (compared, problems).

    Three ways the report can stop describing the tree, and all three fail: a
    row it carries that the sample no longer does, a sampled row it does not
    carry, and a row whose recomputed cells differ from the committed ones.
    The third is the load-bearing one and it compares every column, not just
    `outcome`, so a drifted name or instruction count is caught as well as a
    changed verdict.

    This is a ratchet, not a gate on the comparison's result. A `disagree` or
    a `vacuous` row is recorded and passes; what fails is a change, or a sample
    that stopped comparing anything (degenerate_sample_problems). Promoting a
    folded case to a failure is issue #140's other option and is out of scope
    here: it needs the byte-pair-folding case enumerated rather than described,
    and no one has enumerated it.

    The firmware identity this rests on is the manifest's `sha256` column,
    which check() has already compared against the image on disk. The report
    carries no digest of its own on purpose -- a second committed record of one
    value is a second thing to keep in step, and this check's addition is the
    per-row recomputation, not the file's identity.
    """
    mine = {(r["program"], r["addr"]): r for r in current}
    theirs = {(r["program"], r["addr"]): r for r in committed}
    problems = []
    for key in sorted(set(theirs) - set(mine)):
        problems.append("%s %s is in the report and not in the sample: the "
                        "report is stale -- re-run --report" % key)
    for key in sorted(set(mine) - set(theirs)):
        problems.append("%s %s is in the sample and not in the report: the "
                        "report predates this export" % key)
    compared = 0
    for key in sorted(set(mine) & set(theirs)):
        compared += 1
        for column in CROSS_DECODER_COLUMNS:
            if theirs[key].get(column) != mine[key].get(column):
                problems.append(
                    "%s %s: %s is %r in the report and %r now -- the export or "
                    "the comparison moved, so regenerate the report"
                    % (key[0], key[1], column, theirs[key].get(column, ""),
                       mine[key].get(column, "")))
    return compared, problems


def degenerate_sample_problems(counts):
    """A sample that compared nothing, or that had nothing to compare. -> problems.

    The failure issue #140 reports, one level up from §14b's: a check that
    reads a fraction of its input and prints the result in the same form as a
    full pass. The denominator makes it visible to whoever is reading; this
    makes it red, because a report recording a wholly vacuous or wholly
    unexported sample is a ratchet on nothing at all.
    """
    total = sum(counts.values())
    compared = counts["agree"] + counts["disagree"]
    out = []
    if not total:
        out.append("the cross-decoder sample is empty, so the report records no "
                   "comparison: the listing index and the annotations share no "
                   "function")
    if total and not compared:
        out.append("compared 0 of %d function(s): no sampled function's opening "
                   "names an XDATA address, so this report ratchets on nothing"
                   % total)
    if total and counts["no-export"] == total:
        out.append("all %d sampled function(s) have no exported C, so this "
                   "report ratchets on nothing" % total)
    return out


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


# --------------------------------------------------------------------------
# ec/annotations/subsystems.md -- the map over ghidra-functions.csv
# --------------------------------------------------------------------------

# One line per cited function, in the only shape the document uses:
#
#     - `bank0` `0xB158` `charge_target_update` -- prose
#
# Three backticked fields, then prose. Deterministic to parse and greppable by
# hand, which matters because a map nobody can grep is a map that goes stale
# quietly. An `unresolved` citation is the same line with a fourth field:
#
#     - `common` `0x052F` `int0_target_is_one_byte_reti` [unresolved] -- prose
#
# The marker is required, not advisory. ghidra-functions.csv puts 134 rows at
# `type: unresolved`, and a map that cites one of them in the same tone as a
# decoded one is how "unresolved" stops meaning anything downstream.
SUBSYSTEM_CITE = re.compile(
    r"^(?P<bullet>- )?`(?P<scope>[a-z0-9]+)` `(?P<addr>0[xX][0-9A-Fa-f]+)` "
    r"`(?P<name>[A-Za-z0-9_]+)`(?P<flag> \[unresolved\])?(?P<rest> .*)?$")
# The census's counts, as the document states them: one bullet each, in the
# house list format, keyed on the label so the order is free. The document
# states the four twice -- once in the census and once in the measured
# remainder -- so every occurrence is collected, not just the last, and a
# wrong number in the first of the two is as wrong as one in the second.
#
#     - `exported functions` — 2710
#
# The value is compared against a recount, so editing a number in the prose
# without re-deriving it is a failed check rather than a claim nobody notices.
SUBSYSTEM_COUNT = re.compile(r"^- `(?P<label>[a-z][a-z0-9 ]+)`\s*[-—]\s*"
                            r"(?P<value>\d+)\s*$", re.M)
SUBSYSTEM_COUNTS = ("exported functions", "annotated function rows",
                    "rows the index marks annotated", "unresolved rows")
# The census's per-program table: the same split as the bullets, per program,
# with the share the document rounds it to.
#
#     | `common` | 753 | 97 | 656 (87%) |
#
# It is held to the same recount as the bullets beside it, and it has to be.
# The four totals are the whole export, so a tranche that re-exports moves them
# only if it moves everything; the table's rows move one program at a time, and
# a check that reads only the bullets leaves a table free to disagree with four
# counts that were corrected eleven lines above it. That is the drift this was
# extended over: a re-export moved the `common` split from 80 to 97, the four
# bullets were re-derived, and this table kept the old numbers in a green build.
# Every row is read, not the first: the document says the table once, but a
# copied table is as wrong as an edited one and the line number is what says
# which.
SUBSYSTEM_TABLE = re.compile(
    r"^\|\s*`(?P<program>[a-z0-9]+)`\s*\|\s*(?P<exported>\d+)\s*\|\s*"
    r"(?P<annotated>\d+)\s*\|\s*(?P<unannotated>\d+)\s*"
    r"\((?P<pct>\d+)%\)\s*\|[ \t]*$", re.M)
# The key the per-program recount travels under in `measured`. It is not a
# census label -- nothing in the prose states it by name -- so it sits beside
# the four rather than among them, which is why the loop over SUBSYSTEM_COUNTS
# does not see it.
SUBSYSTEM_TABLE_KEY = "per-program table"


def subsystems_citations(text):
    """The citation lines of a subsystems.md, as dicts.

    A line is a citation when it opens with a list bullet and its first three
    backticked fields are a scope, an address and a name. Anything else on a
    bullet line is prose the document wrote, and a section that cites nothing
    is caught by the count the caller compares against.
    """
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.startswith("- "):
            continue
        m = SUBSYSTEM_CITE.match(line)
        if m:
            d = m.groupdict()
            d["lineno"] = lineno
            d["line"] = line
            d["unresolved"] = bool(d["flag"])
            d["prose"] = (d["rest"] or "").lstrip(" -")
            out.append(d)
    return out


def subsystems_problems(text, ann_rows, repo=REPO, stated=None, measured=None):
    """What is wrong with a subsystems.md, given the CSV it is a view of.

    Four faults, all of them the kind a prose document accumulates silently:

    - a cited `(scope, addr)` that is not a row at all. A rename in
      ghidra-functions.csv would otherwise leave the map quoting a function
      that no longer exists, and the map is the thing a new reader trusts to
      find their way in.
    - a cited `name` that disagrees with the CSV's current name for that
      address. This is the one that actually bites, and it is why the check
      lives in the tool that owns the CSV.
    - a `type: unresolved` row cited without the `[unresolved]` marker.
    - an `evidence` path that does not exist on disk. This closes, for
      this document, the delete-the-row-and-the-file hole
      ec/annotations/README.md §"The checks" describes: a row that is gone
      cannot point at a file that is gone, so every other existence check
      still holds. It is checked over *every* row of the CSV rather than over
      the cited ones: the citation list is this document's selection, and a row
      it happens not to quote is exactly where a dead path can sit unseen.
      A cited row is reported with its line; an uncited one by its key alone.
    """
    problems = []
    by_key = {(r["scope"], norm_addr(r["addr"])): r for r in ann_rows}
    cites = subsystems_citations(text)
    if not cites:
        return ["the document cites no functions: the citation format is three "
                "backticked fields, a scope, an address and a name"]
    cited_keys = set()
    for c in cites:
        key = (c["scope"], norm_addr(c["addr"]))
        cited_keys.add(key)
        row = by_key.get(key)
        if row is None:
            problems.append("line %d: %s %s is not a row in %s -- a rename or a "
                            "typo; the map quotes a function that is not there"
                            % (c["lineno"], c["scope"], c["addr"],
                               os.path.relpath(ANNOTATIONS, repo)))
            continue
        if row["name"] != c["name"]:
            problems.append("line %d: %s %s is named %s in %s, not %s"
                            % (c["lineno"], c["scope"], c["addr"], row["name"],
                               os.path.relpath(ANNOTATIONS, repo), c["name"]))
        unresolved = row.get("type") == "unresolved"
        if unresolved and not c["unresolved"]:
            problems.append("line %d: %s %s is type=unresolved in %s and is cited "
                            "without the [unresolved] marker"
                            % (c["lineno"], c["scope"], c["addr"],
                               os.path.relpath(ANNOTATIONS, repo)))
        if not unresolved and c["unresolved"]:
            problems.append("line %d: %s %s is type=%s, not unresolved, and is cited "
                            "with the [unresolved] marker"
                            % (c["lineno"], c["scope"], c["addr"], row.get("type", "")))
        for path in (p.strip() for p in row.get("evidence", "").split(";")):
            if path and not os.path.exists(os.path.join(repo, path)):
                problems.append("line %d: the evidence %s cited for %s %s does not "
                                "exist on disk" % (c["lineno"], path, c["scope"],
                                                   c["addr"]))
    # ...and over the rows the document does not cite, so the existence check
    # is a property of the CSV rather than of the map's selection from it. The
    # cited rows are already reported above, with a line number, and reporting
    # them twice would make a count in the message mean nothing.
    for r in ann_rows:
        key = (r["scope"], norm_addr(r["addr"]))
        if key in cited_keys:
            continue
        for path in (p.strip() for p in r.get("evidence", "").split(";")):
            if path and not os.path.exists(os.path.join(repo, path)):
                problems.append("%s %s: the evidence %s does not exist on disk"
                                % (r["scope"], r["addr"], path))
    if stated and measured:
        for label in SUBSYSTEM_COUNTS:
            if label not in stated:
                problems.append("the census states no `%s` count; it is one of "
                                "%s and the recount cannot be compared"
                                % (label, ", ".join("`%s`" % c for c in SUBSYSTEM_COUNTS)))
            elif label not in measured:
                problems.append("nothing to recount `%s` against" % label)
            else:
                # Every occurrence, not just the last: the document states each
                # count twice and a wrong number in the first copy drifts from
                # the recount just as silently as one in the second.
                for lineno, value in stated[label]:
                    if value != measured[label]:
                        problems.append(
                            "line %d: the census states %d %s and the committed "
                            "files hold %d" % (lineno, value, label, measured[label]))
        # ...and the per-program table beside them, which is the same claim
        # split four ways and is read only when the caller brought a
        # per-program recount to hold it to.
        problems.extend(subsystems_table_problems(
            text, measured.get(SUBSYSTEM_TABLE_KEY)))
    return problems


def subsystems_stated_counts(text):
    """The census counts the document publishes, read back out of its prose.

    Every occurrence of a label, as a list of (line, value), because the
    document states each count more than once and the gate has to compare all
    of them against the recount: keying on the label alone would leave the
    earlier copy unchecked, which is exactly the drift the check exists to
    catch.
    """
    out = {}
    for m in SUBSYSTEM_COUNT.finditer(text):
        out.setdefault(m.group("label"), []).append(
            (text.count("\n", 0, m.start()) + 1, int(m.group("value"))))
    return out


def subsystems_stated_table(text):
    """The census's per-program table, read back out of its rows.

    {program: [(line, exported, annotated, unannotated, pct), ...]}, every
    occurrence rather than the last, for the reason
    `subsystems_stated_counts` collects every occurrence of a label. A row
    whose cells do not parse is not read as a row at all, so it is reported as
    the missing program it leaves behind rather than as a malformed cell --
    the same signal either way, and the one a reader can act on.
    """
    out = {}
    for m in SUBSYSTEM_TABLE.finditer(text):
        g = m.groupdict()
        out.setdefault(g["program"], []).append(
            (text.count("\n", 0, m.start()) + 1, int(g["exported"]),
             int(g["annotated"]), int(g["unannotated"]), int(g["pct"])))
    return out


def subsystems_table_problems(text, measured):
    """The census's per-program table, against a per-program recount.

    `measured` is {program: (exported, annotated, unannotated)} off
    index.csv, or None when the caller has no per-program recount -- in which
    case the table is not checked, rather than checked against nothing.

    Four faults, all of them the same fault at different strengths: a program
    with no row, a row for a program the export does not have, a row whose
    split disagrees with the export, and a row whose share disagrees with its
    own cells. The first is a dropped row, which the bullets cannot see because
    the four totals still add up without it. The second is a name that no
    recount can be made against -- a mistyped program, or one the index has not
    got -- and it is reported rather than raised, on this file's rule that a
    broken input is a failed check and not a traceback.
    """
    if not measured:
        return []
    out = []
    stated = subsystems_stated_table(text)
    for program in sorted(set(measured) | set(stated)):
        rows = stated.get(program)
        if not rows:
            out.append("the census's per-program table states no `%s` row; the "
                       "export holds %d functions there"
                       % (program, measured[program][0]))
            continue
        if program not in measured:
            out.append("line %d: the census's per-program table has a `%s` row "
                       "and the export holds no %s program"
                       % (rows[0][0], program, program))
            continue
        for lineno, exported, annotated, unannotated, pct in rows:
            if (exported, annotated, unannotated) != measured[program]:
                e, a, u = measured[program]
                out.append(
                    "line %d: the census splits %s as %d exported, %d annotated, "
                    "%d unannotated and the committed index holds %d, %d, %d"
                    % (lineno, program, exported, annotated, unannotated,
                       e, a, u))
                continue
            # The share is stated as a whole percent off the row's own cells,
            # so it is recounted from those cells and not from the export:
            # this is the cell disagreeing with the cell next to it.
            share = int(100.0 * unannotated / exported + 0.5) if exported else 0
            if share != pct:
                out.append("line %d: the census states %s as %d%% unannotated "
                           "and %d of %d is %d%%"
                           % (lineno, program, pct, unannotated, exported, share))
    return out


def check_subsystems(ann_rows, index_rows, repo=REPO, doc=SUBSYSTEMS):
    """The subsystems.md pass, over committed files only.

    Returns (problems, n_citations). Two of the four counts are properties of
    ec/decompiled/index.csv and two of ghidra-functions.csv, so both files are
    read and the recount is the union -- a count the document cannot derive
    from the two committed CSVs is not a count this check can hold it to.
    """
    if not os.path.isfile(doc):
        return ["no %s: the map from mechanism to function is the entry point "
                "this repository does not have"
                % os.path.relpath(doc, repo)], 0
    text = open(doc, errors="replace").read()
    counts = {
        "exported functions": len(index_rows),
        "annotated function rows": len(ann_rows),
        "rows the index marks annotated":
            sum(1 for r in index_rows if r.get("annotated") == "yes"),
        "unresolved rows": sum(1 for r in ann_rows if r.get("type") == "unresolved"),
    }
    # The census's per-program table is a split of the same index rows, so it
    # is recounted from the same file and carried beside the four totals rather
    # than in the prose's own labelled form.
    per_prog = {}
    for r in index_rows:
        slot = per_prog.setdefault(r["program"], [0, 0])
        slot[0] += 1
        if r.get("annotated") == "yes":
            slot[1] += 1
    counts[SUBSYSTEM_TABLE_KEY] = {p: (e, a, e - a)
                                   for p, (e, a) in per_prog.items()}
    return (subsystems_problems(text, ann_rows, repo=repo,
                                stated=subsystems_stated_counts(text),
                                measured=counts),
            len(subsystems_citations(text)))


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
    # The function layer's three counters, against the files they summarise, and
    # then the two-way gap printed for a reader rather than judged. The gap is
    # informational on purpose: a name the CSV never wrote is a real thing (see
    # the docstring) and neither direction of it is a fault. It is printed so the
    # figure docs/findings.md §18 quotes is regenerable with one command instead
    # of living only as prose.
    #
    # The annotations CSV is optional to the build, so its absence is reported
    # as its own thing. Derived against an empty row-list every counter would
    # read 0, and a manifest that recorded real figures would then produce a
    # dozen mismatches that all mean "the file you need is not here".
    _ann_rows = _read.get("ghidra-functions.csv")
    if _ann_rows is None:
        print("  annotation ledger: skipped, no ghidra-functions.csv to read it "
              "from, so the three function-layer counters cannot be derived")
    else:
        _alm = annotation_ledger_mismatches(manifest, rows, _ann_rows)
        for problem in _alm[:5]:
            fail(problem)
        if len(_alm) > 5:
            fail("... and %d more function-layer counter problem(s)"
                 % (len(_alm) - 5))
        _named_none, _unflagged, _backed = annotation_ledger(rows, _ann_rows)
        _basis = {}
        for _r in _named_none:
            _basis[_r.get("seed_basis", "?")] = _basis.get(_r.get("seed_basis", "?"), 0) + 1
        print("  annotation ledger: %d function-annotation row(s), %d "
              "program-application(s) of them (a `common` row applies to both bank "
              "programs, and the manifest's `common` row borrows bank0's), %d "
              "unmatched, %d function(s) named in the export"
              % (len(_ann_rows),
                 sum(int(r["annotations_applied"]) for r in manifest
                     if r.get("program") in ("bank0", "bank1", "pd")),
                 sum(int(r["annotations_unmatched"]) for r in manifest
                     if r.get("program") in ("bank0", "bank1", "pd")),
                 sum(int(r["functions_named"]) for r in manifest)))
        if _named_none:
            print("    %d exported function(s) carry a non-placeholder name that "
                  "no CSV row wrote (%s); not a fault, and the reason the two "
                  "counters are separate:"
                  % (len(_named_none),
                     ", ".join("%d %s" % (v, k) for k, v in sorted(_basis.items()))))
            # Where each of those names came from, read out of the bytes and the
            # committed .c by second_copy_census rather than transcribed here.
            # It is a check and not a printout: a row whose name this method
            # cannot account for fails the build, so the figure above can no
            # longer drift away from an explanation of what its members are.
            # The ledger above is untouched by it -- the count, the two
            # directions and the arithmetic all stay as they were.
            _verdicts = second_copy_census.census(_named_none, rows, _ann_rows)
            _tally = {}
            for _v in _verdicts:
                _tally[_v["bucket"]] = _tally.get(_v["bucket"], 0) + 1
            print("      of those, %s"
                  % ", ".join("%d %s" % (n, b) for b, n in sorted(_tally.items())))
            for _p in second_copy_census.problems(_verdicts):
                fail(_p)
            for _v in _verdicts:
                print("        %-6s %s %s (seed_basis=%s) -- %s: %s"
                      % (_v["program"], _v["addr"], _v["name"],
                         _v["seed_basis"], _v["bucket"], _v["why"]))
        if _unflagged:
            # The fact, and not a cause this loop has not checked. The obvious
            # cause -- a name out of Ghidra's reserved namespace, which is what
            # the seven `thunk_` rows were -- is checked once, over the whole
            # CSV, further down; asserting it here for these rows in particular
            # would be a claim the code had not made, and it would keep making
            # it after the next rename moved the ground under it. So the rows
            # are named and the reader is left the predicate.
            print("    %d annotation row(s) DID apply and are reported "
                  "annotated=no, so the index's `annotated` column disagrees "
                  "with the annotation layer for them:" % len(_unflagged))
            for _r, _backing in sorted(_unflagged, key=lambda p: (p[0]["program"],
                                                                   p[0]["addr"])):
                print("      %-6s %s %s"
                      % (_r["program"], _r["addr"],
                         ", ".join(a["name"] for a in _backing)))
        # The two directions close against the export, which is what makes "no
        # annotation has gone stale" a measurement rather than an absence of
        # evidence. It reconciles because every CSV row backs exactly one index
        # row; the count is reported rather than assumed, because two rows
        # naming one function would break the sum and mean something worth
        # knowing.
        print("    %d annotation row(s) - %d unflagged + %d unnamed-by-CSV = %d "
              "named function(s); the manifest's functions_named totals %d, and "
              "%d index row(s) carry a CSV row"
              % (len(_ann_rows), len(_unflagged), len(_named_none),
                 len(_ann_rows) - len(_unflagged) + len(_named_none),
                 sum(int(r["functions_named"]) for r in manifest), len(_backed)))
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
    # Existence is not content. The loop above proved each .c is a readable file
    # that does not carry the decompiler's own failure marker; this pairs every
    # index row to the function its .c actually declares, which is the property
    # a truncated or half-overwritten export breaks while leaving every file
    # present. The distinct-file count is printed because a per-row read would
    # look identical in the output and cost 100 GB.
    _pres, _c_read, _c_rows = c_presence_problems(rows, OUTDIR)
    for problem in _pres[:5]:
        fail(problem)
    if len(_pres) > 5:
        fail("... and %d more decompile(s) that do not declare the function their "
             "index row names" % (len(_pres) - 5))
    print("  presence: %d index row(s) paired to the function their .c declares, "
          "across %d distinct file(s)" % (_c_rows, _c_read))
    # `_cdig`, not `_cd`: the cross-decoder report below binds that name, and
    # one function's two unrelated locals should not share a spelling.
    _cdig = verify_c_digests()
    for problem in _cdig[:5]:
        fail(problem)
    if len(_cdig) > 5:
        # The count, not a silent cut. Someone who re-exported and forgot
        # --write-digests gets 2,710 problems here, and "5 shown" with no total
        # is the shape §14 warns about: a reader cannot tell a filtered
        # summary from a nearly-clean run.
        fail("... and %d more committed .c whose digest does not match (re-run "
             "--write-digests if this came from a re-export)" % (len(_cdig) - 5))
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
    # What the NAME asserts, and what that assertion rests on (issue #135). The
    # same discipline the `evidence` guard above applies to the comment, one
    # level across: a name that says a mechanism without saying whether it came
    # from a decoded register map, registers.yaml, an ABI symbol or the
    # instruction shape is a claim a reader cannot audit. Four cross-field
    # rules, imported from the grader so the two cannot drift; the one that
    # matters most here is the `pd` refusal, which keeps 497 rows of the
    # separate PD image off the EC's XDATA map.
    _basis = grade_name_basis.register_addresses()
    _bp = []
    for a in _read.get("ghidra-functions.csv", []):
        for problem in grade_name_basis.row_problems(a, _basis):
            _bp.append("annotation %s %s (%s) %s"
                       % (a["scope"], a["addr"], a.get("name", ""), problem))
    for problem in _bp[:5]:
        fail("name_basis: %s" % problem)
    if len(_bp) > 5:
        fail("name_basis: ... and %d more problem(s)" % (len(_bp) - 5))
    if not _bp:
        print("  name_basis: %d row(s), every one graded in the closed "
              "vocabulary and consistent with registers.yaml and the "
              "bit-addressable SFR map" % len(_read["ghidra-functions.csv"]))
    # A name out of Ghidra's own namespace, which is the other direction of the
    # ledger printed above and a different fault from a stale name: the row
    # resolves, applies, and is then reported unannotated, so the two layers
    # disagree about a function that is there. Five cross-field rules is the
    # wrong count above because this is not one -- it grades no column, and it
    # is the only rule here whose fault is in the NAME's namespace rather than
    # in what the name rests on. Scoped to the EC, and the scope is the honest
    # one: the same scan over the BIOS CSV finds two rows, and those belong to
    # the `equals("entry")` / `startsWith("entry")` divergence between the two
    # copies of isPlaceholderName(), which reconciling would need a BIOS
    # re-export. docs/findings/thunk-prefix-collision.md.
    _rp = grade_name_basis.reserved_prefix_problems(_read["ghidra-functions.csv"])
    for problem in _rp[:5]:
        fail("reserved name: %s" % problem)
    if len(_rp) > 5:
        fail("reserved name: ... and %d more problem(s)" % (len(_rp) - 5))
    if not _rp:
        print("  reserved names: %d row(s), none of them a name Ghidra could "
              "have produced itself" % len(_read["ghidra-functions.csv"]))
    # The map from mechanism to function, and the same discipline from the
    # reading side. Every citation in ec/annotations/subsystems.md is a
    # (scope, addr, name) triple this file owns, so a rename here has to reach
    # the map or the build fails -- which is the whole reason the check lives
    # in the tool that wrote the CSV rather than in a tool of its own.
    sp, ncites = check_subsystems(_read.get("ghidra-functions.csv", []), rows)
    for problem in sp[:5]:
        fail("subsystems.md: %s" % problem)
    if len(sp) > 5:
        fail("subsystems.md: ... and %d more problem(s)" % (len(sp) - 5))
    if not sp:
        print("  subsystems: %d citation(s) in %s, every one resolving against "
              "the committed CSV and the census recounted"
              % (ncites, os.path.relpath(SUBSYSTEMS, REPO)))
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

    # The cross-decoder report, and the cheap tier's ratchet on the comparison
    # docs/findings.md §14i describes. Until this existed the comparison was
    # advisory output that ran in a tier no workflow calls, and a branch that
    # re-exported ec/decompiled/ or edited an annotation moved it with nothing
    # to notice -- the gap issue #140 reports as "the result is printed and
    # nothing else". Recomputing every row here is what closes it, and it costs
    # one pass over the sampled `.c` files, which this check already walks for
    # DECOMPILER UNAVAILABLE.
    if not os.path.isfile(CROSS_DECODER):
        fail("no cross-decoder report at %s; run build_ec_decompile.py --report"
             % os.path.relpath(CROSS_DECODER, REPO))
    else:
        try:
            _cd = read_index(CROSS_DECODER)
        except (OSError, csv.Error) as e:
            _cd = None
            fail("cross-decoder.csv does not parse as strict CSV: %s" % e)
        if _cd is not None:
            _cd_rows = cross_decoder_results(open(FIRMWARE, "rb").read())
            _counts = cross_decoder_summary(_cd_rows)
            _compared, _problems = cross_decoder_problems(_cd, _cd_rows)
            for problem in _problems[:5]:
                fail(problem)
            if len(_problems) > 5:
                fail("... and %d more cross-decoder report problem(s)"
                     % (len(_problems) - 5))
            for problem in degenerate_sample_problems(_counts):
                fail(problem)
            print("  cross-decoder: %s" % denominator_line(_counts))
            # "recomputed against it", not "match this run": a count of matched
            # rows would read as a pass on the runs this whole check exists to
            # turn red, and the problem lines above it are the answer.
            print("  cross-decoder report: %d row(s) committed, %d recomputed "
                  "against them, %d problem(s) above"
                  % (len(_cd), _compared, len(_problems)))
    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
