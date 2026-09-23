#!/usr/bin/env python3
"""Re-assemble the committed disassembly and compare it to the firmware bytes.

Two checks, and the difference between them is the point.

**`--check`, no assembler needed.** Every byte of every committed listing is
compared against the firmware image, and the committed report is confirmed to
still describe those listings. This covers 100% of the instructions, including
the 2.2% the assembler below cannot express, and it runs anywhere.

**The full run, `sdas8051` needed.** The committed listing is re-encoded with
`sdas8051` (SDCC's assembler, which never saw this firmware) and the result is
compared to `ec/firmware/GMxMGxx_11.800`. Ghidra's SLEIGH decodes, an
assembler that did not see the image encodes, and the firmware arbitrates.

Neither implies the other, and 1:1 needs both. The byte check asks "are these
the bytes in the image" -- it catches a stale listing, an export whose listing
belongs to a different firmware, a decoder reporting a length the image does
not have. The re-encode asks "does an independent assembler agree these bytes
mean this instruction" -- it catches a decode that is self-consistent and
wrong. A listing whose bytes are right and whose mnemonic is wrong passes the
first and fails the second.

Three decoders are in play and they are worth keeping distinct:

  Ghidra's SLEIGH      writes the .asm this script reads
  sdas8051 (SDCC)      encodes the .asm back to bytes   <- independent
  disasm8051.py        this repository's own decoder    <- used to arbitrate

The decompiler is not in the loop at all. It is not read, not compared. A C can
be wrong and this check still passes, which is correct: a decompilation is a
claim about what the machine code means, and the listing is the claim about the
machine code. Nor is this a claim that the C recompiles -- Keil C51 generated
these bytes and SDCC does not emit Keil's code generation. See
`ghidra/README.md` for what the 1:1 property does and does not mean here.

Outcomes per function, kept apart because they mean different things:

  match       every instruction re-encodes to the firmware bytes
  partial     some do; the rest use a form sdas8051 cannot express
  gap         none of them do
  mismatch    sdas assembled something and it is not what the firmware holds.
              The only outcome that threatens the claim, and disasm8051.py is
              the tie-breaker.

Requires `sdas8051` (SDCC) for the full run. Without it the tool says so and
`--check` still runs.

Usage:
    python3 ec/tools/verify_reassembly.py --work /tmp/ec            # full run
    python3 ec/tools/verify_reassembly.py --work /tmp/ec --limit 40 # a sample
    python3 ec/tools/verify_reassembly.py --check                   # no assembler
    python3 ec/tools/verify_reassembly.py --self-test               # known answers
"""
import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
DECOMPILED = os.path.join(REPO, "ec", "decompiled")
LISTING_INDEX = os.path.join(DECOMPILED, "listing-index.csv")
REPORT = os.path.join(REPO, "ec", "ghidra", "reassembly.csv")
# Where build_images() puts the flat per-bank images, so --check can compare a
# listing against the firmware without a full Ghidra run.
IMAGE_DIR = os.path.join(tempfile.gettempdir(), "ec-verify-images")

# Instruction layout: `addr  b1 b2 b3  mnemonic  operands`, `;` for comments.
# The byte slots are fixed width and an absent byte is `-`, because the 8051's
# reserved one-byte instruction is spelled `da A` and `da` is two hex digits --
# a variable-width byte column makes `d4  da  A` readable as the two-byte
# instruction `d4 da`, which is what it is not. `-` is not a hex digit, so the
# byte column cannot run into the mnemonic.
# A line that starts with an instruction address, whatever the rest of the
# format is. Used to notice when the parser stops understanding the file.
ADDRESS_LINE = re.compile(r"^[0-9A-Fa-f]{4,8}\s+\S")

LINE_RE = re.compile(r"^([0-9A-Fa-f]{1,8})\s+(\S.*)$")
# One token of the byte column: a hex pair, or the `-` that ends it.
BYTE_SLOT = re.compile(r"^(?:[0-9A-Fa-f]{2}|-)$")

# Forms sdas8051 (ASxxxx) cannot assemble. Measured, not guessed: each was
# tried against the assembler and produced "Invalid Addressing Mode". They are
# listed rather than filtered silently, because a filter that quietly drops
# 5% of the instruction stream turns a measured number into a flattering one.
#
# A leading hex operand means sdas read it as `direct` where the instruction is
# bit-addressed; a mnemonic-specific prefix is the cleaner discriminator, so
# the bit cases are handled by opcode in BIT_UNSUPPORTED below instead.
GAP_FORMS = {
    "djnz a,",
    "orl c,#",
    "anl c,#",
    "mov c,#",
    "xrl c,#",
    "addc c,#",
    "subb c,#",
}

# Opcodes whose operand is a bit address rather than a direct address, and that
# sdas8051 cannot express in any syntax. 0x92 MOV bit,C; 0xA2 MOV C,bit;
# 0x93 MOVC A,bit; 0xB2 CPL bit; 0xC0 SETB bit; 0xC3 CLR bit.
#
# The opcode is the discriminator, not the mnemonic or the operand text: `clr
# 0x8e` and `clr /0x8e` are the same three characters to a text matcher and
# different opcodes (0xC2 and 0xC3), so a matcher that guessed from the text
# would assemble the direct form and report a mismatch against a correct
# decode. Getting this wrong in the other direction is worse: it would hide a
# real disagreement behind a "gap".
BIT_UNSUPPORTED = {0x82, 0x92, 0x93, 0xA2, 0xB2, 0xC0, 0xC3}

# Opcodes sdas8051 *can* express in bit form, so the operand needs its `/`
# prefix and the register spelled the way sdas spells it.
BIT_SUPPORTED = {0xA0, 0xB0}

# Mnemonics sdas8051 encodes differently from the 8051 manual, so its output
# cannot be used to judge a decode of them.
#
# AJMP and ACALL are the interesting case, because they are how this firmware
# reaches code across a bank window. The manual's encoding takes A15-A11 from
# the *current PC* and A10-A8 from bits 7-5 of the opcode; sdas8051 encodes the
# target's own high byte instead. At PC 0x8044 the firmware and both decoders
# agree the instruction is `81 5D` = `ajmp 0x845D` (0x8044 & 0xF800 = 0x8000,
# 0x81 & 0xE0 = 0x80 -> 0x8400, | 0x5D); sdas8051 emits `84 5D`. That is a
# disagreement about the *assembler*, confirmed by arbitrating with
# disasm8051.py, so these are counted as gaps and not as decode failures.
GAP_MNEMONICS = {"ajmp", "acall"}

# Opcodes whose operand is a `direct` address, split by which operand it is.
#
# Ghidra renders a direct address by substituting the SFR name it belongs to, so
# direct 0xE0 prints as `A` and direct 0xF0 prints as `B`. sdas8051 reads `A` as
# the accumulator, so the same three characters encode two different
# instructions: `88 E0` is `MOV 0xE0,R0` in the firmware and sdas re-encodes
# Ghidra's rendering of it as `E8`, `MOV R0,A`. Likewise `25 E0` is `ADD A,0xE0`
# and comes back as `add a,a`, which sdas rejects outright.
#
# So for these opcodes the operand is replaced by the literal byte from the
# instruction's own encoding. The decode is not second-guessed -- the byte is
# what the decoder already reported, and the rendering is what is being
# corrected. In every case the direct operand is the second byte.
# opcode -> the operand positions that are `direct`. Their bytes are the
# encoding's second and third bytes in order, which is not the same as the
# operand index: `ADD A,direct` is operand 1 but byte 1.
# opcode -> ((operand position, byte position in the encoding), ...) for the
# operands that are `direct` addresses.
#
# Operand position and byte position are not the same thing, and assuming they
# are gets `MOV direct,direct` backwards: opcode 0x85 takes the SOURCE byte
# first, so `85 F0 00` is `MOV 0x00,0xF0` and not `MOV 0xF0,0x00`. Both
# decoders agree on that reading (Ghidra's operand text and disasm8051.py), and
# the firmware confirms it -- sdas8051 re-encodes `mov 0x00,0xf0` to 85 F0 00,
# which is the byte pair the firmware holds.
DIRECT_OPERANDS = {
    0x05: ((0, 1),), 0x15: ((0, 1),),                  # INC/DEC direct
    0x25: ((1, 1),), 0x35: ((1, 1),), 0x45: ((1, 1),),  # ADD/ADDC/ORL A,direct
    0x55: ((1, 1),), 0x65: ((1, 1),),                  # ANL/XRL A,direct
    0x75: ((0, 1),),                                   # MOV direct,#imm
    0x85: ((0, 2), (1, 1)),                            # MOV direct,direct
    0x88: ((0, 1),), 0x89: ((0, 1),),                  # MOV direct,Rn
    0x8A: ((0, 1),), 0x8B: ((0, 1),),
    0x8C: ((0, 1),), 0x8D: ((0, 1),),
    0x8E: ((0, 1),), 0x8F: ((0, 1),),
    0xA8: ((1, 1),), 0xA9: ((1, 1),),                  # MOV Rn,direct
    0xAA: ((1, 1),), 0xAB: ((1, 1),),
    0xAC: ((1, 1),), 0xAD: ((1, 1),),
    0xAE: ((1, 1),), 0xAF: ((1, 1),),
    0xC0: ((0, 1),), 0xC2: ((0, 1),),                  # PUSH/CLR direct
    0xD0: ((0, 1),), 0xD2: ((0, 1),),                  # POP/SETB direct
    0xE5: ((1, 1),), 0xE6: ((1, 1),), 0xE7: ((1, 1),),  # MOV A,direct / @Ri,direct
    0xF5: ((0, 1),), 0xF6: ((0, 1),), 0xF7: ((0, 1),),  # MOV direct,A / @Ri
}


def find_assembler(explicit=None):
    """sdas8051, however it is spelled here. The EC toolchain is SDCC's
    assembler; CI does not have it, and a missing assembler must read as
    'not verified here', never as 'verified'."""
    for cand in (explicit, os.environ.get("SDAS8051"), "sdas8051"):
        if cand and (os.path.isfile(cand) or shutil.which(cand)):
            return shutil.which(cand) or cand
    # The nix store path this was developed against, so a developer with nix
    # does not have to go find it again.
    import glob
    for pat in ("/nix/store/*-sdcc-*/bin/sdas8051",
                os.path.expanduser("~/.local/opt/sdcc/bin/sdas8051")):
        for hit in sorted(glob.glob(pat)):
            if os.access(hit, os.X_OK):
                return hit
    return None


def parse_listing(path):
    """-> [(addr, bytes_hex, mnemonic, operands)], in file order."""
    out = []
    for line in open(path, errors="replace"):
        if line.startswith(";") or not line.strip():
            continue
        m = LINE_RE.match(line.rstrip("\n"))
        if not m:
            continue
        addr, rest = m.groups()
        # The byte column ends at the first `-`, and the mnemonic is whatever
        # follows. Taking a run of hex pairs instead would be ambiguous the
        # moment the mnemonic is itself two hex digits -- which the 8051's
        # reserved `da` is, and which is the whole reason the column is padded.
        #
        # The one case the padding cannot cover is a maximum-length instruction
        # immediately followed by a two-hex-digit mnemonic: no `-` to stop at.
        # It cannot arise here. `da` is one byte against the 8051's maximum of
        # three, so it is always padded; and no x86-64 mnemonic is two hex
        # digits. If a future processor breaks that, this needs a real
        # delimiter rather than a wider assumption.
        slots = rest.split()
        take = 0
        for i, tok in enumerate(slots):
            if tok == "-":
                # Padding ends the byte column. Everything after it is the
                # mnemonic and operands, even if it looks like hex -- which it
                # does for the 8051's `da`, and which is the entire reason the
                # column is padded rather than variable width.
                take = i
                break
            if not BYTE_SLOT.match(tok):
                take = i
                break
            take = i + 1
        hexbytes = "".join(slots[:take])
        rest_at = take
        while rest_at < len(slots) and slots[rest_at] == "-":
            rest_at += 1          # skip the padding, not the mnemonic after it
        tail = " ".join(slots[rest_at:]).strip()
        if not tail:
            continue
        mnem, _, ops = tail.partition(" ")
        out.append((int(addr, 16), hexbytes, mnem.lower(), ops.strip()))
    return out


# Branch mnemonics whose operand is a *relative offset*, not an address. 8051
# has no relative-addressing mode -- every branch encodes a signed byte -- so
# these are the instructions where a listing's absolute target has to be turned
# back into the offset the firmware actually holds. sdas8051 does not do that
# conversion: handed `jz 0x0EC6` it emits the low byte of the address, which is
# a plausible-looking encoding of the wrong instruction, and a check that
# accepted it would be measuring the assembler rather than the decode.
RELATIVE_BRANCH = {"sjmp", "jc", "jnc", "jz", "jnz", "jb", "jnb", "djnz",
                   "cjne", "jbc"}


def _operand_list(ops):
    return [o.strip() for o in ops.split(",")] if ops.strip() else []


def to_sdas(mnem, ops, pc=None, size=1, opcode=None, hexbytes=""):
    """The listing's operand syntax is already sdas syntax for almost every
    form; what is left is the corrections below and the gap list.

    Returns None for a form sdas8051 cannot express, which the caller reports as
    an assembler gap rather than a disagreement about the code."""
    # Normalise before matching: Ghidra prints `djnz     A, 0xa581` and the
    # gap list says `djnz a,`, so without this the form sails past the check
    # and reaches the assembler, which then rejects it and makes a known gap
    # look like an assembler error.
    key = re.sub(r"\s*,\s*", ",", ("%s %s" % (mnem, ops)).lower())
    for gap in GAP_FORMS:
        if key.startswith(gap):
            return None
    if mnem in GAP_MNEMONICS:
        return None
    # The 8051's reserved no-op, DA A (opcode 0xD4), is rendered by Ghidra's
    # SLEIGH as a bare `A` with no operand -- a mnemonic that is also a register
    # name and an assembler error. sdas8051 spells it `da a` and emits D4.
    if mnem == "a" and not ops.strip():
        return "\tda\ta"
    if opcode is not None:
        if opcode in BIT_UNSUPPORTED:
            return None
    parts = _operand_list(ops)
    if opcode in DIRECT_OPERANDS and parts:
        for i, b in DIRECT_OPERANDS[opcode]:
            if i < len(parts) and 2 * b + 2 <= len(hexbytes):
                parts[i] = "0x" + hexbytes[2 * b:2 * b + 2]
    # Ghidra spells the carry `CY`; sdas spells it `c`. The 8051 register file
    # is the same either way, and a name it does not know is an assembler error
    # rather than a finding.
    parts = [p.replace("CY", "c") if p.strip() == "CY" else p for p in parts]
    if opcode in BIT_SUPPORTED:
        # sdas marks the bit form with `/`. Only the hex operand is the bit --
        # prefixing the register as well would turn `orl c,/0x2d` into
        # `orl /c,/0x2d`, which assembles to something else entirely.
        parts = [("/" + p.lstrip("/")) if re.fullmatch(r"0x[0-9a-fA-F]+", p)
                 else p for p in parts]
    # CJNE has no direct-addressing form in the base 8051, and sdas8051 rejects
    # it; a hex first operand here is a direct address it cannot encode.
    if mnem == "cjne" and parts and parts[0].lower().startswith("0x"):
        return None
    if mnem in RELATIVE_BRANCH and pc is not None and parts:
        target = parts[-1]
        try:
            addr = int(target, 16)
        except ValueError:
            return None
        # The encoded displacement is measured from the byte AFTER the
        # instruction, and the instruction is `size` bytes long.
        rel = addr - (pc + size)
        if not -128 <= rel <= 127:
            return None
        parts[-1] = str(rel)
    # sdas8051 is case-insensitive, but a reader diffing a generated .s51
    # against the listing should not have to wonder whether `A` and `a` are the
    # same register or two.
    parts = [p.lower() for p in parts]
    return "\t%s\t%s" % (mnem, ",".join(parts))


def read_lst(path):
    """ASxxxx listing -> {address: byte}.

    sdas8051 is a relocatable assembler: it emits a `.rel` object and never an
    Intel HEX file, so the bytes have to come from the listing it prints with
    `-l`. That is fine, and in fact better -- the listing shows the address, the
    bytes and the source line side by side, so a disagreement names itself.

        00BD57 E0               [24]    4   movx  a, @dptr

    The `[24]` is a relocation class, not part of the encoding, and a relative
    branch prints its computed offset as `80p61` -- the `p` marks the byte the
    assembler calculated, and dropping it is what makes the pair parseable.
    """
    mem = {}
    if not os.path.isfile(path):
        return mem
    pat = re.compile(r"^\s*([0-9A-Fa-f]{4,8})\s+([0-9A-Fa-fpP \t]+?)\s*\[\s*\d*\s*\]")
    for line in open(path, errors="replace"):
        m = pat.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        raw = m.group(2).replace("p", "").replace("P", "").replace(" ", "")
        if len(raw) % 2:
            continue
        for i in range(0, len(raw), 2):
            mem[addr + i // 2] = int(raw[i:i + 2], 16)
    return mem


def build_images(work):
    """The flat per-bank images the project was built from, rebuilt from the
    committed firmware. Address == image offset for all three programs, which
    is what make_bank_image.py arranges."""
    os.makedirs(work, exist_ok=True)
    maker = os.path.join(HERE, "make_bank_image.py")
    paths = {}
    for prog, arg in (("bank0", ("bank0", "0x8000")),
                      ("bank1", ("bank1", "0x10000"))):
        dst = os.path.join(work, prog + ".bin")
        subprocess.run([sys.executable, maker, FIRMWARE, arg[0], arg[1], dst],
                       check=True, stdout=subprocess.DEVNULL)
        paths[prog] = dst
    dst = os.path.join(work, "pd.bin")
    subprocess.run([sys.executable, maker, "--pd", FIRMWARE, dst],
                   check=True, stdout=subprocess.DEVNULL)
    paths["pd"] = dst
    return paths


def check_one(row, image, work, sdas):
    """Assemble one function's listing and compare it to the image bytes.

    Instructions sdas8051 cannot express are skipped rather than abandoned, and
    an `.org` re-anchors the next instruction at its true address, so a
    function with one `clr bit` in it still gets every other instruction
    checked. That is why the outcome is a pair (outcome, detail) plus counts:
    a function is only `match` when every instruction in it re-encoded.

    Returns (outcome, detail, n_checked, n_skipped)."""
    rel = row["out_file"]
    if not rel or rel.startswith("("):
        return "skipped", rel, 0, 0
    path = os.path.join(DECOMPILED, rel)
    if not os.path.isfile(path):
        return "missing-listing", rel, 0, 0
    insns = parse_listing(path)
    if not insns:
        return "empty-listing", rel, 0, 0

    lines = ["\t.area CODE (ABS)", "\t.org 0x%04x" % insns[0][0]]
    prev_end = None
    area = 0
    checked, skipped = [], []
    for addr, hexbytes, mnem, ops in insns:
        # Ghidra's function bodies are not contiguous: a 2-byte `jb` at 0x8058
        # is followed by a 3-byte `lcall` at 0x805E, with four bytes between
        # them that belong to no instruction in this function. sdas lays
        # instructions out densely, so without an .org at every gap it packs
        # the lcall up against the jb and every later address shifts -- which
        # reads as a decode failure at an address the decode never claimed.
        # Re-anchoring is what makes the re-encode a statement about the
        # instructions rather than about their spacing.
        if prev_end is not None and (addr != prev_end or skipped):
            # A fresh area, not a bare `.org`. Re-anchoring inside one area is
            # what sdas8051 answers with ".org in REL area" once the target
            # moves outside the area it opened, and a bank-window function
            # reaches 32 KiB easily.
            area += 1
            lines.append("\t.area C%d (ABS)" % area)
            lines.append("\t.org 0x%04x" % addr)
        s = to_sdas(mnem, ops, pc=addr, size=len(hexbytes) // 2,
                    opcode=int(hexbytes[:2], 16) if len(hexbytes) >= 2 else None,
                    hexbytes=hexbytes)
        if s is None:
            # Not expressible. Record the span so the comparison can say which
            # bytes went unchecked rather than quietly ignoring them.
            skipped.append((addr, len(hexbytes) // 2, "%s %s" % (mnem, ops)))
        else:
            lines.append(s)
            checked.append((addr, len(hexbytes) // 2))
        prev_end = addr + len(hexbytes) // 2
        if s is None:
            # sdas will place the NEXT instruction at prev_end because it does
            # not know these bytes were skipped, so the anchor above is not
            # optional here.
            pass
    if not checked:
        return "assembler-gap", (skipped[0][2] if skipped else ""), 0, len(skipped)

    start = insns[0][0]
    end = insns[-1][0] + len(insns[-1][1]) // 2
    stem = os.path.join(work, "f")
    src = stem + ".s51"
    with open(src, "w") as f:
        f.write("\n".join(lines) + "\n")
    r = subprocess.run([sdas, "-lxosgff", src], capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()
        return "assembler-error", (tail[-1] if tail else "failed"), len(checked), len(skipped)
    mem = read_lst(stem + ".lst")
    for addr, nbytes, _why in skipped:
        for i in range(max(1, nbytes)):
            if start <= addr + i < len(image) and addr + i in mem:
                # The assembler emitted something here after all, from a
                # neighbouring instruction. Not a reason to fail.
                pass
    for addr, nbytes in checked:
        for i in range(max(1, nbytes)):
            a = addr + i
            want = image[a] if a < len(image) else None
            got = mem.get(a)
            if got is None:
                return "assembler-gap", "no bytes emitted at %04X" % a, len(checked), len(skipped)
            if got != want:
                return "mismatch", "%04X: assembled %02X, firmware %02X" % (a, got, want), len(checked), len(skipped)
    if skipped:
        return "partial", "%d of %d instruction(s) unchecked, first: %s" % (
            len(skipped), len(checked) + len(skipped), skipped[0][2]), len(checked), len(skipped)
    return "match", "", len(checked), 0


def verify(limit=None, jobs=8, work=None, sdas=None, quiet=False):
    sdas = find_assembler(sdas)
    if not sdas:
        print("verify_reassembly: sdas8051 not found.\n"
              "  This check is NOT skipped silently: it simply did not run.\n"
              "  Install SDCC, or set SDAS8051=/path/to/sdas8051, and re-run.")
        return 2
    rows = [r for r in csv.DictReader(open(LISTING_INDEX, newline=""))
            if r["out_file"] and not r["out_file"].startswith("(")]
    if limit:
        rows = rows[:limit]
    work = work or tempfile.mkdtemp(prefix="reassembly-")
    images = build_images(work)
    loaded = {p: open(path, "rb").read() for p, path in images.items()}

    results = []
    # One scratch dir per thread: sdas8051 writes <stem>.ihx next to its input,
    # and two threads sharing a stem silently overwrite each other's output.
    dirs = [tempfile.mkdtemp(prefix="rasm-", dir=work) for _ in range(jobs)]

    def job_threaded(item):
        idx, row = item
        try:
            return (row,) + check_one(
                row, loaded.get(row["program"]) or loaded["bank0"],
                dirs[idx % jobs], sdas)
        except Exception as exc:                       # a crash is a result
            return row, "error", "%s: %s" % (type(exc).__name__, exc), 0, 0

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for result in pool.map(job_threaded, list(enumerate(rows))):
            results.append(tuple(result))

    tally = {}
    for _row, outcome, _detail, _c, _s in results:
        tally[outcome] = tally.get(outcome, 0) + 1
    checked = sum(r[3] for r in results)
    skipped = sum(r[4] for r in results)
    insn_total = checked + skipped
    if not quiet:
        total = len(results)
        matched = tally.get("match", 0)
        partial = tally.get("partial", 0)
        print("\n  reassembly, by function (%d total):" % total)
        for outcome in sorted(tally, key=lambda o: -tally[o]):
            print("    %-16s %d" % (outcome, tally[outcome]))
        print("\n  reassembly, by instruction:")
        print("    re-encode to the firmware bytes : %d of %d (%.2f%%)"
              % (checked, insn_total, 100.0 * checked / insn_total if insn_total else 0))
        print("    unchecked (sdas8051 cannot express the form): %d" % skipped)
        print("\n  %d function(s) have every instruction re-encode byte-exactly; "
              "%d more have all but %d instruction(s) verified."
              % (matched, partial, skipped))
    return results, tally, sdas


def assembler_version(sdas):
    """The assembler's own version string, for the report.

    The gap set is a property of the assembler as much as of the code, so a
    report that does not say which one produced it is not a measurement. The
    match count is not expected to move with the version -- the firmware bytes
    are the arbiter -- but the number of unchecked instructions is, and a reader
    comparing two reports needs to know whether they used the same tool."""
    try:
        r = subprocess.run([sdas], capture_output=True, text=True, timeout=20)
        for line in (r.stdout + r.stderr).splitlines():
            if "Assembler V" in line:
                return line.split("Assembler V", 1)[1].split()[0].strip()
    except Exception:
        pass
    return "unknown"


def write_report(results, sdas, path=REPORT):
    version = assembler_version(sdas)
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["program", "addr", "name", "outcome", "instructions_checked",
                    "instructions_unchecked", "detail", "assembler"])
        for row, outcome, detail, checked, skipped in results:
            w.writerow([row["program"], row["addr"], row["name"], outcome,
                        checked, skipped, detail,
                        "sdas8051 %s" % version])
    return path


def check_listing_bytes():
    """Every byte in every listing, against the firmware image. No assembler.

    The re-encode above is the stronger claim but the weaker coverage: 2.2% of
    the instructions use forms sdas8051 cannot express, so 1,004 of them are
    unchecked. This checks all of them and needs nothing but the firmware, so it
    runs in CI where the assembler does not.

    It is a different check rather than a weaker one. Re-encoding asks "does an
    independent assembler agree that these bytes mean this instruction"; this
    asks "are these the bytes in the image", which catches an export whose
    listing belongs to a different firmware, a stale .asm, and a decoder that
    reports a length the image does not have. Neither implies the other: the
    bytes can be right and the mnemonic wrong, and 1:1 needs both.

    Returns (checked, bad) where bad is a list of (program, addr, detail)."""
    ok = True
    images = {}
    for prog in ("bank0", "bank1", "pd"):
        path = os.path.join(IMAGE_DIR, prog + ".bin")
        if not os.path.isfile(path):
            path = os.path.join(tempfile.gettempdir(), prog + "-verify.bin")
        images[prog] = path
    if not all(os.path.isfile(p) for p in images.values()):
        # Rebuild them once; the EC driver makes these in seconds.
        images = {p: os.path.join(IMAGE_DIR, p + ".bin")
                  for p in ("bank0", "bank1", "pd")}
        build_images(IMAGE_DIR)
    loaded = {p: open(path, "rb").read() for p, path in images.items()}
    bad = []
    checked = 0
    for row in csv.DictReader(open(LISTING_INDEX, newline="")):
        rel = row["out_file"]
        if not rel or rel.startswith("("):
            continue
        path = os.path.join(DECOMPILED, rel)
        if not os.path.isfile(path):
            bad.append((row["program"], row["addr"], "listing file missing"))
            continue
        prog = row["program"]
        image = loaded.get(prog) or loaded["bank0"]
        insns = parse_listing(path)
        # Every line that starts with an address is an instruction, and the
        # parser is supposed to get all of them. If it does not, the listing
        # format and the parser have drifted apart -- and a parser that quietly
        # reads 30% of a file reports 0 disagreements and looks like a pass.
        # This is not hypothetical: it is what happened when the byte column
        # went from variable width to three fixed slots and the committed
        # listings had not been re-exported yet.
        text = open(path, errors="replace").read()
        address_lines = sum(1 for line in text.splitlines()
                            if ADDRESS_LINE.match(line))
        if len(insns) != address_lines:
            bad.append((prog, row["addr"],
                        "%d instruction line(s) but %d parsed -- the listing "
                        "format and this parser disagree; re-export the "
                        "listings" % (address_lines, len(insns))))
            continue
        for addr, hexbytes, _mnem, _ops in insns:
            want = bytes.fromhex(hexbytes) if hexbytes.isalnum() else b""
            if not want:
                continue
            checked += 1
            got = image[addr:addr + len(want)]
            if got != want:
                bad.append((prog, "%04X" % addr,
                            "listing says %s, image has %s"
                            % (want.hex(), got.hex())))
    print("  listing bytes: %d instruction(s) checked against the firmware, "
          "%d disagreement(s)" % (checked, len(bad)))
    for prog, addr, why in bad[:20]:
        print("  FAIL %s %s: %s" % (prog, addr, why))
    if len(bad) > 20:
        print("  ... and %d more" % (len(bad) - 20))
    ok = not bad
    return ok, checked, len(bad)


def check():
    """No assembler required.

    Two things. First, every byte of every listing against the firmware image,
    which covers the 2.2% of instructions the assembler cannot express and runs
    anywhere. Second, that the committed reassembly report still describes the
    committed listings: same functions, same outcomes. A report that has drifted
    from the listings it was measured against is the failure that catches --
    it cannot tell you the bytes match, only that the claim on file is the one
    the current export supports."""
    ok = True
    bytes_ok, n_insns, n_bad = check_listing_bytes()
    ok = ok and bytes_ok
    if not os.path.isfile(REPORT):
        print("  FAIL no reassembly report at %s; run verify_reassembly.py"
              % os.path.relpath(REPORT, REPO))
        return 1
    rows = {r["out_file"] for r in csv.DictReader(open(LISTING_INDEX, newline=""))
            if r["out_file"] and not r["out_file"].startswith("(")}
    report = {r["addr"] + "|" + r["program"]: r
              for r in csv.DictReader(open(REPORT, newline=""))}
    live = {}
    for r in csv.DictReader(open(LISTING_INDEX, newline="")):
        if r["out_file"] and not r["out_file"].startswith("("):
            live[r["addr"] + "|" + r["program"]] = r["out_file"]
    for key, rel in live.items():
        if key not in report:
            print("  FAIL %s is in the listing index but not in the reassembly "
                  "report: the report predates this export" % rel)
            ok = False
    for key in report:
        if key not in live:
            print("  FAIL %s is in the reassembly report but not in the listing "
                  "index: the report is stale" % key)
            ok = False
    mism = sum(1 for r in report.values() if r["outcome"] == "mismatch")
    gaps = sum(1 for r in report.values() if r["outcome"] == "assembler-gap")
    match = sum(1 for r in report.values() if r["outcome"] == "match")
    print("  reassembly report: %d match, %d assembler-gap, %d mismatch "
          "(of %d)" % (match, gaps, mism, len(report)))
    if mism:
        print("  FAIL %d function(s) re-encode to different bytes than the "
              "firmware holds. That is the 1:1 claim failing; see the detail "
              "column." % mism)
        ok = False
    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def self_test():
    """Known answers, so a change to the translation or the comparison cannot
    quietly start passing everything."""
    ok = True

    def assert_that(cond, what):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", what))
        ok = ok and cond

    assert_that(GAP_FORMS and "djnz a," in GAP_FORMS,
                "the sdas8051 gap list is populated, not empty")
    assert_that("ajmp" in GAP_MNEMONICS and "acall" in GAP_MNEMONICS,
                "ajmp/acall are a known gap, not an unfiltered mismatch")
    assert_that(to_sdas("mov", "dptr,#0x1234", 0x0040) is not None,
                "mov dptr,#imm translates")
    assert_that(to_sdas("djnz", "a,0x0014", 0x0040) is None,
                "a known assembler gap returns None rather than a bad line")
    # The relative-branch correction, which is the one that can silently encode
    # the wrong instruction: a target 2 bytes past a 2-byte jz at 0xEB2 is a
    # displacement of 0, and handing sdas the absolute address instead yields a
    # plausible-looking byte that is not the one the firmware holds.
    # 0x0EC6 is 0x12 bytes past the end of a 2-byte jz at 0x0EB2, and
    # 0x0EAE is 0x18 bytes *before* the end of a 2-byte sjmp at 0x0EC4.
    assert_that(to_sdas("jz", "0x0ec6", pc=0x0eb2, size=2) == "\tjz\t18",
                "an absolute branch target becomes a forward displacement")
    assert_that(to_sdas("sjmp", "0x0eae", pc=0x0ec4, size=2) == "\tsjmp\t-24",
                "a backwards target becomes a signed displacement")
    assert_that(to_sdas("jb", "0x8f,0x0eb7", pc=0x0eb7, size=3) == "\tjb\t0x8f,-3",
                "a bit-branch keeps its bit operand and shifts only the target")
    assert_that(to_sdas("sjmp", "0x5000", pc=0x0ec4, size=2) is None,
                "a displacement outside a signed byte is a gap, not a wrong line")
    assert_that(to_sdas("ljmp", "0x1100", pc=0x11a7, size=3) == "\tljmp\t0x1100",
                "an absolute branch target is left alone")
    # Opcode-driven, not text-driven: 0xC2 and 0xC3 render as the same `clr N`
    # but only one of them is a bit instruction.
    assert_that(to_sdas("clr", "0x8e", opcode=0xC2) == "\tclr\t0x8e",
                "CLR direct is passed through as direct")
    assert_that(to_sdas("clr", "0x8e", opcode=0xC3) is None,
                "CLR bit is a gap, not a direct CLR the firmware does not hold")
    assert_that(to_sdas("cpl", "0xb4", opcode=0xB2) is None,
                "CPL bit is a gap (0xB2, confirmed against disasm8051.py)")
    assert_that(to_sdas("cjne", "a,#0x10,0x0046", pc=0x0040, size=3)
                == "\tcjne\ta,#0x10,3",
                "CJNE A keeps its immediate and shifts only the target")
    assert_that(to_sdas("cjne", "r3,#0x10,0x0046", pc=0x0040, size=3)
                == "\tcjne\tr3,#0x10,3",
                "CJNE Rn is assembled, not skipped")
    assert_that(to_sdas("cjne", "0x30,#0x10,0x0046", pc=0x0040, size=3) is None,
                "CJNE with a direct operand is a gap")
    assert_that(to_sdas("mov", "CY, 0x2d", opcode=0xA2) is None,
                "MOV C,bit is a gap")
    assert_that(to_sdas("ajmp", "0x845d", pc=0x8044, size=2) is None,
                "ajmp is skipped rather than compared against sdas' encoding")
    # The SFR-name substitution: `mov A, R0` as Ghidra renders `88 E0` is
    # MOV direct,R0, and the byte column is what settles it.
    assert_that(to_sdas("mov", "A, R0", opcode=0x88, hexbytes="88e0")
                == "\tmov\t0xe0,r0",
                "a direct operand rendered as an SFR name becomes its address")
    assert_that(to_sdas("add", "A, A", opcode=0x25, hexbytes="25e0")
                == "\tadd\ta,0xe0",
                "ADD A,direct is not ADD A,A")
    assert_that(to_sdas("mov", "A, R0", opcode=0xE8, hexbytes="e809")
                == "\tmov\ta,r0",
                "a genuine MOV A,Rn keeps the register form")
    # 0x85 takes the source byte first: `85 F0 00` is MOV 0x00,0xF0.
    assert_that(to_sdas("mov", "0x00, B", opcode=0x85, hexbytes="85f000")
                == "\tmov\t0x00,0xf0",
                "MOV direct,direct keeps the source byte in operand 0")
    assert_that(to_sdas("mov", "R0, DPH", opcode=0xA8, hexbytes="a883")
                == "\tmov\tr0,0x83",
                "MOV Rn,direct fixes the second operand")
    assert_that(to_sdas("orl", "CY, /0x2d", opcode=0xA0) == "\torl\tc,/0x2d",
                "ORL C,/bit keeps its slash and gets sdas' spelling of carry")
    # A listing line written by ExportListing.java, parsed back.
    insns = parse_listing_str(
        "; bank0 @ BD54   store_be16_b   [named]\n"
        "BD54  74 09 -     mov   dptr,#0x09\n"
        "BD57  e0  -  -    movx  a,@dptr\n"
        "\n"
        "BD58  f0  -  -    movx  @dptr,a\n")
    assert_that(len(insns) == 3, "a comment line and a blank line are skipped")
    assert_that(insns[0] == (0xBD54, "7409", "mov", "dptr,#0x09"),
                "addr, bytes, mnemonic and operands parse apart")
    assert_that(insns[2][1] == "f0", "a one-byte instruction parses")
    # The ambiguity that made the byte column fixed width in the first place.
    amb = parse_listing_str(
        "D438  d4  -  -        da      A\n"
        "D439  84  -  -        div     AB\n")
    assert_that(len(amb) == 2 and amb[0][1] == "d4" and amb[0][2] == "da",
                "the reserved one-byte `da A` does not read as the two-byte "
                "`d4 da`")
    assert_that(amb[1][1] == "84" and amb[1][2] == "div",
                "the instruction after it still parses")
    # The x86-64 shape, which is why the column width is per-program rather
    # than a constant 3: a 7-byte instruction in a 15-slot column, and one
    # that fills the column with no padding to stop at.
    wide = parse_listing_str(
        "00000268  48 89 05 79 0a 00 00 - - - - - - - -"
        "  mov      qword ptr [0x00000ce8], RAX\n"
        "0000026f  48 89 15 6a 0a 00 00 - - - - - - - -"
        "  mov      qword ptr [0x00000ce0], RDX\n")
    assert_that(len(wide) == 2
                and wide[0][1] == "488905790a0000" and wide[0][2] == "mov",
                "a 7-byte x86-64 instruction in a 15-slot column parses whole")
    assert_that(wide[1][2] == "mov"
                and "0x00000ce0" in wide[1][3],
                "its operands are not mistaken for bytes")

    # The comparison itself, against a byte string we control. A check that
    # cannot fail on a wrong byte is not a check.
    sdas = find_assembler()
    if not sdas:
        print("  --   sdas8051 absent: the assemble-and-compare oracle is not "
              "run here (it is run by the full verify, and by --check against "
              "the committed report)")
        return 0 if ok else 1
    work = tempfile.mkdtemp(prefix="rasm-selftest-")
    # Textbook 8051 encodings, stated here rather than produced by the
    # assembler under test -- a self-test that derives its oracle from the tool
    # it is testing asserts nothing. `mov a,#0x12`=74 12, `ljmp 0045`=02 00 45,
    # `ret`=22, `nop`=00.
    img = bytearray(b"\x00" * 0x100)
    img[0x40:0x48] = bytes.fromhex("7412 0200 4522 00".replace(" ", ""))
    row = {"program": "bank0", "addr": "0040", "name": "t",
           "out_file": "listing-index.csv.tmp"}
    real = os.path.join(DECOMPILED, "listing-index.csv.tmp")
    with open(real, "w") as f:
        f.write("0040  74 12 -     mov   a,#0x12\n"
                "0042  02 00 45    ljmp  0x0045\n"
                "0045  22  -  -    ret\n"
                "0046  00  -  -    nop\n")
    try:
        outcome, detail, nchk, nskip = check_one(row, bytes(img), work, sdas)
        assert_that(outcome == "match",
                    "a correct listing re-encodes to the image bytes (%s %s)"
                    % (outcome, detail))
        # Corrupt one byte of the image: the check must notice.
        img[0x41] = 0x13
        outcome, _, _, _ = check_one(row, bytes(img), work, sdas)
        assert_that(outcome == "mismatch",
                    "a wrong image byte is reported as a mismatch, not a pass")
    finally:
        os.remove(real)
        shutil.rmtree(work, ignore_errors=True)
    return 0 if ok else 1


def parse_listing_str(text):
    import io
    import tempfile as tf
    fd, path = tf.mkstemp(suffix=".asm")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    try:
        return parse_listing(path)
    finally:
        os.remove(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", help="scratch directory for the rebuilt images")
    ap.add_argument("--as", dest="assembler", help="path to sdas8051")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--limit", type=int, help="only the first N functions")
    ap.add_argument("--report", action="store_true",
                    help="write ec/ghidra/reassembly.csv")
    ap.add_argument("--check", action="store_true",
                    help="CI: the report still describes the listings (no assembler)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.check:
        return check()
    results, tally, sdas = verify(limit=args.limit, jobs=args.jobs,
                                  work=args.work, sdas=args.assembler)
    if args.report:
        print("\n  wrote %s" % os.path.relpath(write_report(results, sdas), REPO))
    return 0 if tally.get("mismatch", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
