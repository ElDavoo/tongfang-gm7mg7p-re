#!/usr/bin/env python3
"""Re-assemble the committed disassembly and compare it to the firmware bytes.

Two tiers of checks, and the difference between them is the point.

**`--check`, no assembler needed.** Three assertions. Every byte of every
committed listing is compared against the firmware image. The committed report
is confirmed to still describe those listings. And every row's `listing_digest`
is recomputed from the listing it names and compared. The first covers 100% of
the instructions, including the 2.2% the assembler below cannot express, and
all three run anywhere.

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

**`listing_digest` closes the per-commit half of that gap, as change detection
and nothing more.** It is a hash of the parsed instruction stream, so a
mnemonic or operand edited in a committed `.asm` fails the cheap gate with no
assembler, which it did not do before. A digest that agrees says the listing
text has not moved since the report was measured; it does not say the text is
right. A wrong mnemonic committed together with a re-reported digest is caught
by nothing automated here, because the only thing that would catch it is the
re-encode, and that still has no schedule (`docs/findings.md` §14e). Detecting
a change is not verifying it, and the column's name invites the second reading
more than the first.

**`--verify-provenance` is what anchors that column to the text it covers.**
`add_digest_column()` digests the listings on disk without re-encoding, so it
cannot say they are the listings the report measured -- `docs/findings.md` §14f
answers that from the repository's own history instead: the migration changed
the column and nothing beneath it, and no listing text moved under it. This
mode runs §14f's method rather than describing it. What it establishes is that
the committed digests cover the text the last full `--report` measured; it says
nothing about whether that text is right, which is the re-encode above, and it
needs a full git history to resolve the revisions it names.

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
    python3 ec/tools/verify_reassembly.py --add-digest-column       # one-shot
    python3 ec/tools/verify_reassembly.py --verify-provenance \\
        --base 08b72e2 --migration a56b3bb --listings-from 8c7985e
        # audit a digest migration against history; needs a full clone,
        # so ci.yml's default-depth checkouts cannot run it
"""
import argparse
import csv
import hashlib
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

# Opcodes sdas8051 cannot express, measured by trying each one against it.
#   0x92 MOV bit,C   -- no output, "Invalid Addressing Mode"
#   0xB2 CPL bit     -- no output
#   0xC1 CLR bit     -- assembles, but as CLR *direct* (0xC2), which is a
#                       different instruction that happens to be the right
#                       length. The dangerous one: it does not fail, it
#                       produces a plausible wrong answer.
#
# The opcode is the discriminator, not the mnemonic or the operand text, and
# that is not a stylistic choice. `clr 0x8e` is both CLR direct (0xC2) and CLR
# bit (0xC1) depending on the byte in front of it, and a text matcher has to
# guess.
#
# Four entries this list carried on the first pass were wrong, and 712 of the
# 1,004 instructions it excluded were not gaps at all: 0xC0 is PUSH direct
# (not SETB bit), 0xC3 is CLR C (not CLR bit), 0x93 is MOVC A,@A+PC (not
# MOVC A,bit) and 0x82 is ANL C,bit, which sdas8051 encodes without a `/`. All
# four assemble correctly here, and the `clr CY` and `movc A, @A+DPTR` forms
# the report called gaps were simply sdas8051 doing its job.
BIT_UNSUPPORTED = {0x92, 0xB2, 0xC1}

# Opcodes whose bit operand sdas8051 spells with a leading `/`.
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


def canonical(ops):
    """An operand list with the formatting decisions taken out.

    Case and internal whitespace -- including the space after a comma, which
    Ghidra and a hand-edit disagree about -- are folded, and nothing else is.
    A comment or a re-wrap is not a change to the disassembly, and a digest
    that moved for one would mean a cosmetic fix needed the assembler to
    resolve before the cheap gate could be green again.
    """
    return re.sub(r"\s*,\s*", ",", re.sub(r"\s+", " ", ops).strip()).lower()


def digest_of(insns):
    """-> 16 hex chars identifying the parsed instruction stream.

    One instruction canonicalises to `ADDR:hexbytes:mnemonic:operands`; the
    joined text, prefixed with the instruction count, is hashed. 64 bits over
    2,705 rows is a birthday bound of about 2e-13, which is a change detector
    on files this repository controls rather than a collision-resistant
    commitment, and a wider digest would imply a guarantee the check does not
    make.

    The input is the parsed stream, not the file's bytes, so a comment-only or
    whitespace-only edit is deliberately outside it. What the digest answers is
    "has the instruction stream changed", which is the question `--check` needs;
    it does not answer "is the instruction stream right" -- see the module
    docstring.
    """
    lines = ["%04X:%s:%s:%s" % (addr, hexbytes.lower(), mnem.lower(),
                               canonical(ops))
             for addr, hexbytes, mnem, ops in insns]
    blob = "%d\n%s" % (len(insns), "\n".join(lines))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


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

    Returns (outcome, detail, n_checked, n_skipped, digest). The digest is
    computed here, off the listing this call has already parsed, rather than by
    a second parse in write_report: #138 made this parse-once, and reading it
    twice to add a column would give the saving back. It is empty for the two
    outcomes that never reach a listing, because there is nothing to digest."""
    rel = row["out_file"]
    if not rel or rel.startswith("("):
        return "skipped", rel, 0, 0, ""
    path = os.path.join(DECOMPILED, rel)
    if not os.path.isfile(path):
        return "missing-listing", rel, 0, 0, ""
    insns = parse_listing(path)
    digest = digest_of(insns)
    if not insns:
        return "empty-listing", rel, 0, 0, digest

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
        return "assembler-gap", (skipped[0][2] if skipped else ""), 0, len(skipped), digest

    start = insns[0][0]
    end = insns[-1][0] + len(insns[-1][1]) // 2
    stem = os.path.join(work, "f")
    src = stem + ".s51"
    with open(src, "w") as f:
        f.write("\n".join(lines) + "\n")
    r = subprocess.run([sdas, "-lxosgff", src], capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()
        return "assembler-error", (tail[-1] if tail else "failed"), len(checked), len(skipped), digest
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
                return "assembler-gap", "no bytes emitted at %04X" % a, len(checked), len(skipped), digest
            if got != want:
                return "mismatch", "%04X: assembled %02X, firmware %02X" % (a, got, want), len(checked), len(skipped), digest
    if skipped:
        return "partial", "%d of %d instruction(s) unchecked, first: %s" % (
            len(skipped), len(checked) + len(skipped), skipped[0][2]), len(checked), len(skipped), digest
    return "match", "", len(checked), 0, digest


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
            return row, "error", "%s: %s" % (type(exc).__name__, exc), 0, 0, ""

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for result in pool.map(job_threaded, list(enumerate(rows))):
            results.append(tuple(result))

    tally = {}
    for _row, outcome, _detail, _c, _s, _d in results:
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
        w.writerow(["program", "addr", "name", "outcome", "listing_digest",
                    "instructions_checked", "instructions_unchecked", "detail",
                    "assembler"])
        for row, outcome, detail, checked, skipped, digest in results:
            w.writerow([row["program"], row["addr"], row["name"], outcome,
                        digest, checked, skipped, detail,
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

    It also returns the per-listing digest, keyed the way the report keys its
    rows, computed from the `insns` this loop has already parsed. That is
    deliberate rather than incidental: #138 made the cheap path parse each
    listing once, and a second pass here to collect a hash would give it back.

    Returns (ok, checked, bad, digests), digests being {addr|program: digest}."""
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
    digests = {}
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
            # No digest: a stream this parse is known to have mis-read is not
            # one to hand a column that reads as a check. check() reports the
            # row against the absent digest rather than skipping it.
            continue
        digests[row["addr"] + "|" + prog] = digest_of(insns)
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
    return ok, checked, len(bad), digests


def compare_digests(report, digests, live):
    """Every report row's committed digest against the one recomputed from the
    listing it names. -> (compared, bad).

    This is the check, and the hash is not the check. A row whose digest
    disagrees has had its disassembly edited since the report was measured; a
    row with no digest at all is a report from before the column existed. Both
    fail, neither is skipped: a row quietly treated as "nothing to compare"
    would be a checker that stops checking, which is the failure mode this
    repository keeps finding the other way round.

    `report` is {addr|program: row}, `digests` is {addr|program: digest} and
    `live` is {addr|program: out_file}. Returned rows are
    (key, program, addr, name, out_file, why)."""
    compared, bad = 0, []
    for key, r in sorted(report.items()):
        got = r.get("listing_digest")
        rel = live.get(key, "(not in the listing index)")
        where = (r.get("program", "?"), r.get("addr", "?"),
                 r.get("name", "?"), rel)
        if not got:
            bad.append((key,) + where +
                       ("no listing_digest: the report predates the column",))
            continue
        want = digests.get(key)
        if want is None:
            bad.append((key,) + where +
                       ("no digest to compare against: %s was not parsed" % rel,))
            continue
        compared += 1
        if got != want:
            bad.append((key,) + where +
                       ("report says %s, %s now digests to %s -- the listing "
                        "text changed after the report measured it"
                        % (got, rel, want),))
    return compared, bad


# The one command that resolves a digest disagreement: a changed listing has to
# be re-reported, and re-reporting is the re-encode. Named once so the failure
# message and --add-digest-column cannot drift into pointing at different things.
REPORT_COMMAND = (
    "SDAS8051=$(nix build nixpkgs#sdcc && echo $out/bin/sdas8051) "
    "python3 ec/tools/verify_reassembly.py --work /tmp/ec --report")


def check():
    """No assembler required.

    Three things. First, every byte of every listing against the firmware
    image, which covers the 2.2% of instructions the assembler cannot express
    and runs anywhere. Second, that the committed reassembly report still
    describes the committed listings: same functions, same outcomes. Third,
    that no listing's text has moved since the report measured it, which is
    what a mnemonic or operand edit leaves the byte column unable to see.

    The first two are about the claim on file agreeing with the export; the
    third is about the export not having changed underneath it. What none of
    them can do is verify the disassembly, and this function does not say it
    does: verifying is the re-encode, and that is the deep tier."""
    ok = True
    bytes_ok, n_insns, n_bad, digests = check_listing_bytes()
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
    # The listing text, against the digest the report carries for it. A text
    # edit with a correct byte column gets past both assertions above and
    # fails here, which is the whole reason the column exists.
    compared, dig_bad = compare_digests(report, digests, live)
    print("  listing digests: %d compared against the committed report, "
          "%d disagreement(s)" % (compared, len(dig_bad)))
    for _key, prog, addr, name, rel, why in dig_bad[:20]:
        print("  FAIL %s %s %s (%s): %s" % (prog, addr, name, rel, why))
    if len(dig_bad) > 20:
        print("  ... and %d more" % (len(dig_bad) - 20))
    if dig_bad:
        print("       A changed listing has to be re-reported, which needs the "
              "assembler the report was made with:\n"
              "         %s\n"
              "       Re-reporting is what verifies the new text. Copying the "
              "new digest into the CSV by\n"
              "       hand re-arms this check and verifies nothing, which is "
              "why --check reports a\n"
              "       disagreement here rather than a diff the reader has to "
              "interpret." % REPORT_COMMAND)
        ok = False
    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def add_digest_column(path=REPORT):
    """One-shot: add `listing_digest` to an existing report, no re-encode.

    It exists for one migration and refuses to run twice, because after the
    column is in place the only writer of a digest must be the full --report
    run. That is what keeps the column from turning into a bypass for the check
    it provides: refreshing a digest by hand re-arms the detector without
    anyone checking the new text, and a one-shot flag that said so on the
    command line is a weaker version of the same problem.

    What it asserts, and it is worth being exact about this because the command
    looks like a measurement: the digests are those of the listings on disk
    right now, and the report's outcomes are whatever they were. It cannot
    prove that these are the listings the report measured -- the re-encode
    against the report's own assembler would, and that is the thing this path
    deliberately does not run, because the one available here is a different
    and older ASxxxx and a full report against it would rewrite every
    `assembler` cell and could move the gap tallies. For the committed column
    that proof comes out of the history instead, and `--verify-provenance` is
    what runs it. See `ec/ghidra/README.md`."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "listing_digest" in fieldnames:
        print("  %s already has a listing_digest column; refusing to run.\n"
              "     A digest is written by the full --report run and by this "
              "one migration, and by\n     nothing else." % os.path.relpath(path, REPO))
        return 1
    ok, _checked, bad, digests = check_listing_bytes()
    if not ok or bad:
        print("  refusing to add a column to a report whose listings do not "
              "match the\n  firmware (%d disagreement(s) above). Fix those "
              "first: a digest computed\n  now would pin a listing the byte "
              "check has just rejected." % bad)
        return 1
    missing = [r for r in rows
               if r.get("addr") + "|" + r.get("program") not in digests]
    if missing:
        print("  refusing to add the column: %d report row(s) name a listing "
              "this run could\n  not digest (first: %s %s). An empty digest is "
              "not a weaker check, it is a\n  check that has stopped running."
              % (len(missing), missing[0].get("program"),
                 missing[0].get("addr")))
        return 1
    at = fieldnames.index("outcome") + 1
    fieldnames.insert(at, "listing_digest")
    for r in rows:
        r["listing_digest"] = digests[r["addr"] + "|" + r["program"]]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n",
                           restval="")
        w.writeheader()
        w.writerows(rows)
    print("  added listing_digest to %d row(s) of %s.\n"
          "  Asserting: these listings are the ones the report describes, and "
          "their text is now\n  pinned per row. Not asserting: that the text is "
          "correct -- a digest detects change, it does\n  not verify the "
          "disassembly. Refreshing one after a deliberate edit means running\n"
          "  %s\n"
          "  which re-encodes with the assembler, rather than editing the CSV."
          % (len(rows), os.path.relpath(path, REPO), REPORT_COMMAND))
    return 0


# §14f's pathspec, as the one spelling of it. The negative check and the
# positive control have to use the same string, or a control that matched
# something says nothing about a negative that matched nothing.
LISTING_PATHSPEC = "ec/decompiled/**/*.asm"
REPORT_REL = "ec/ghidra/reassembly.csv"
# What identifies a row. --check keys the same rows `addr|program`; a tuple is
# that same identity without a separator, so nothing inside an address can
# join two rows into one.
PROVENANCE_KEY = ("program", "addr")

# The mode reads two revisions out of the repository's own history, so how deep
# the clone is is part of its contract the way the assembler is part of
# --report's. The agent stages check out with `fetch-depth: 0` and can run it;
# both of ci.yml's checkouts are default-depth and cannot resolve the
# revisions §14f names at all. See docs/agent-pipeline.md.
HISTORY_REQUIREMENT = (
    "  This mode answers from the repository's history, so it needs a full\n"
    "  clone: `git clone` without --depth, or `git fetch --unshallow` in one\n"
    "  that is shallow. A default-depth checkout -- actions/checkout's default,\n"
    "  which is what ci.yml uses -- has neither revision, and a mode that\n"
    "  carried on anyway would be auditing whatever happened to be checked out.")


def _git(*args):
    """git, run against the repository whatever the cwd is."""
    return subprocess.run(["git", "-C", REPO] + list(args),
                          capture_output=True, text=True)


def git_lines(*args):
    """-> (lines, None) for git's non-empty output lines, or (None, why).

    None rather than an empty list because an empty answer and a command that
    did not run are the two things this mode most needs to tell apart: every
    check it makes is "git said nothing", so a git that failed would read as a
    pass on all of them.
    """
    try:
        r = _git(*args)
    except OSError as exc:
        return None, "git could not be run: %s" % exc
    if r.returncode != 0:
        return None, r.stderr.strip() or ("git exited %d" % r.returncode)
    return [ln for ln in r.stdout.splitlines() if ln.strip()], None


def resolve_revision(rev):
    """-> the commit sha `rev` names in this clone, or None if it has no such
    commit. `^{commit}` so a tag or a branch name is measured, not a path."""
    lines, _why = git_lines("rev-parse", "--verify", "--quiet", rev + "^{commit}")
    return lines[0] if lines else None


def compare_provenance(base_text, migration_text):
    """Two revisions' reports, `listing_digest` dropped from both.
    -> (rows identical, rows in the base, column (base, migration), problems).

    This is the comparison inside `--verify-provenance` with no git in it, so it
    is written to be exercised on its own: a comparison that compared nothing,
    or that dropped one column too many, looks exactly like a working one on any
    pair that agrees, and the committed pair is a pair that agrees.

    The column is dropped rather than compared because that is the shape of a
    migration -- the base predates it, so `listing_digest` is absent on that
    side entirely -- and because the digests are *meant* to be new: comparing
    them would fail every correct run. What has to hold is that nothing else
    moved. Rows are keyed by (program, addr) so a re-order is not a change, and
    anything that is, is named rather than skipped: a column added, renamed or
    reordered beneath the digest, a row that is missing or extra, a key that
    appears twice, or one differing cell. A repeated key is refused rather than
    collapsed, because a dict that keeps one of the two says the two are equal.
    """
    import io

    def read(text):
        reader = csv.DictReader(io.StringIO(text), strict=True)
        rows = list(reader)
        fields = [f for f in (reader.fieldnames or [])
                  if f != "listing_digest"]
        return fields, rows, "listing_digest" in (reader.fieldnames or [])

    problems = []
    try:
        base_fields, base_rows, base_has = read(base_text)
        mig_fields, mig_rows, mig_has = read(migration_text)
    except csv.Error as exc:
        return 0, 0, (False, False), ["a report does not parse as strict CSV: %s"
                                      % exc]
    if not base_rows or not mig_rows:
        problems.append("a report has no rows in it: %d in the base, %d in the "
                        "migration" % (len(base_rows), len(mig_rows)))
        return 0, len(base_rows), (base_has, mig_has), problems

    headers_differ = base_fields != mig_fields
    if headers_differ:
        only_base = [f for f in base_fields if f not in mig_fields]
        only_mig = [f for f in mig_fields if f not in base_fields]
        detail = []
        if only_base:
            detail.append("only in the base: %s" % ", ".join(only_base))
        if only_mig:
            detail.append("only in the migration: %s" % ", ".join(only_mig))
        if not detail:
            detail.append("the same columns in a different order: %s vs %s"
                          % (",".join(base_fields), ",".join(mig_fields)))
        problems.append("the two headers differ beyond listing_digest -- %s"
                        % "; ".join(detail))

    def key_by(rows, which):
        keyed = {}
        for row in rows:
            k = tuple(row.get(f, "") for f in PROVENANCE_KEY)
            if k in keyed:
                problems.append("%s %s appears more than once in the %s: a "
                                "repeated key cannot be compared, and taking one "
                                "of the two would report them as equal"
                                % (k[0], k[1], which))
            keyed[k] = row
        return keyed

    base_keyed = key_by(base_rows, "base")
    mig_keyed = key_by(mig_rows, "migration")
    for k in sorted(set(base_keyed) - set(mig_keyed)):
        problems.append("%s %s is in the base and not in the migration"
                        % (k[0], k[1]))
    for k in sorted(set(mig_keyed) - set(base_keyed)):
        problems.append("%s %s is in the migration and not in the base"
                        % (k[0], k[1]))

    # Compared over the columns both sides have. With a header difference that
    # is only the overlap, and no row counts as identical: it would be saying
    # a row matched when a column of it was never compared at all.
    fields = [f for f in base_fields if f in mig_fields]
    identical = 0
    for k in sorted(set(base_keyed) & set(mig_keyed)):
        diffs = [f for f in fields
                 if base_keyed[k].get(f, "") != mig_keyed[k].get(f, "")]
        for f in diffs:
            problems.append("%s %s: %s is %r in the base and %r in the migration"
                            % (k[0], k[1], f, base_keyed[k].get(f, ""),
                               mig_keyed[k].get(f, "")))
        if not diffs and not headers_differ:
            identical += 1
    return identical, len(base_rows), (base_has, mig_has), problems


def verify_provenance(base, migration, listings_from=None):
    """Audit a `listing_digest` migration against the history it sits in.
    -> exit status. 0 means every check below measured what it claims to.

    §14f answered, by hand, that the migration added the column and changed
    nothing beneath it, and that no listing text moved while it did. This runs
    that, and refuses to answer anything it cannot measure:

      1. both revisions resolve in this clone, and so does the one the listings
         were last written in;
      2. the listings' pathspec matches something over that window, so the empty
         answer over the migration is a measurement and not a pathspec quietly
         matching nothing;
      3. no `.asm` under the two revisions' window changed;
      4. the two reports, `listing_digest` dropped, differ by nothing;
      5. what the migration's window did touch, printed as a supporting view.

    (2) is checked before (3) rather than after it, which is the one place this
    departs from the order §14f presents them in: an empty diff printed as a
    result and only then contradicted by the control is exactly the reading the
    control exists to prevent. Both numbers are printed together either way.
    """
    base_sha = resolve_revision(base)
    mig_sha = resolve_revision(migration)
    for label, rev, sha in (("base", base, base_sha),
                            ("migration", migration, mig_sha)):
        if not sha:
            print("  FAIL cannot resolve the %s revision %r in this clone."
                  % (label, rev))
            print(HISTORY_REQUIREMENT)
            return 1
    # Defaulted rather than required, but the default is resolved the same way
    # a named revision is, so a window whose start is missing fails with the
    # history requirement rather than as a control of zero.
    from_rev = listings_from or (base + "^")
    from_sha = resolve_revision(from_rev)
    if not from_sha:
        print("  FAIL cannot resolve --listings-from %r in this clone."
              % from_rev)
        print(HISTORY_REQUIREMENT)
        return 1
    print("  revisions: listings written %s..%s, migration %s..%s"
          % (from_sha[:7], base_sha[:7], base_sha[:7], mig_sha[:7]))

    control, why = git_lines("diff", "--name-only",
                             "%s..%s" % (from_sha, base_sha), "--",
                             LISTING_PATHSPEC)
    if control is None:
        print("  FAIL the control diff did not run: %s" % why)
        return 1
    moved, why = git_lines("diff", "--name-only",
                           "%s..%s" % (base_sha, mig_sha), "--",
                           LISTING_PATHSPEC)
    if moved is None:
        print("  FAIL the listing diff did not run: %s" % why)
        return 1
    if not control:
        print("  FAIL the control returned 0 file(s) over %s..%s, so the pathspec"
              "\n  is matching nothing and the empty answer below is not a "
              "measurement." % (from_sha[:7], base_sha[:7]))
        print("  Pass --listings-from the revision before the window that last "
              "wrote\n  the listings, and check that the window is not empty.")
        return 1
    # One line for both, because either answer is only a measurement next to the
    # control: "none moved" over a pathspec that matches nothing is the failure
    # this is shaped to prevent, and "2,705 moved" beside a control of 0 would
    # be a different one.
    print("  listing text: %d of them changed over %s..%s; the same pathspec "
          "returns %d file(s)\n  over %s..%s, the window that last wrote them, "
          "so the first number is a measurement"
          % (len(moved), base_sha[:7], mig_sha[:7], len(control), from_sha[:7],
             base_sha[:7]))
    if moved:
        print("  FAIL %d listing(s) changed under the migration:" % len(moved))
        for path in moved[:20]:
            print("    %s" % path)
        if len(moved) > 20:
            print("    ... and %d more" % (len(moved) - 20))
        print("  The digests were computed from the listings at HEAD, not from "
              "the ones the\n  report measured. Re-report, or re-run this "
              "against the migration that did not move\n  a listing.")
        return 1

    reports = {}
    for label, sha in (("base", base_sha), ("migration", mig_sha)):
        lines, why = git_lines("show", "%s:%s" % (sha, REPORT_REL))
        if lines is None:
            print("  FAIL cannot read %s at the %s revision: %s"
                  % (REPORT_REL, label, why))
            return 1
        reports[label] = "\n".join(lines) + "\n"
    identical, n_base, has_digest, problems = compare_provenance(
        reports["base"], reports["migration"])
    if problems:
        print("  FAIL the two reports differ by more than the column "
              "(%d problem(s)):" % len(problems))
        for p in problems[:20]:
            print("    %s" % p)
        if len(problems) > 20:
            print("    ... and %d more" % (len(problems) - 20))
        return 1
    print("  report: %d of %d row(s) identical once listing_digest is dropped "
          "(present in the\n  base: %s; in the migration: %s)"
          % (identical, n_base, "yes" if has_digest[0] else "no",
             "yes" if has_digest[1] else "no"))

    touched, why = git_lines("log", "--name-only", "--format=",
                             "%s..%s" % (base_sha, mig_sha), "--",
                             "ec/decompiled")
    if touched is None:
        print("  (the supporting view did not run: %s)" % why)
    else:
        # Supporting, not a gate: a `.c` re-export is a normal thing for a
        # window to contain, and the digest is over the parsed `.asm`
        # instruction stream, so it cannot move one. Deduped because --log
        # names a path once per commit that touched it, and a count that moves
        # with how the window happened to be split is not worth printing.
        touched = list(dict.fromkeys(touched))
        print("  the window touched %d path(s) under ec/decompiled:"
              % len(touched))
        for path in touched[:10]:
            print("    %s" % path)
        if len(touched) > 10:
            print("    ... and %d more" % (len(touched) - 10))

    print("  PASS  the migration changed the column and nothing beneath it, and "
          "no listing text\n  moved while it did.")
    print("  What that establishes: the committed digests are of the listings "
          "the last full --report\n  measured. What it does not: that those "
          "listings are right. The digests were taken\n  without a "
          "re-encode, so they attest to the measured text and not to its\n  "
          "correctness -- that is the re-encode's job (docs/findings.md §14e), "
          "and it\n  still has no schedule.")
    return 0


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
    assert_that(BIT_UNSUPPORTED == {0x92, 0xB2, 0xC1},
                "the unsupported-opcode set is the three forms sdas8051 "
                "really cannot encode, measured rather than recalled")
    assert_that(0xC0 not in BIT_UNSUPPORTED and 0xC3 not in BIT_UNSUPPORTED
                and 0x93 not in BIT_UNSUPPORTED,
                "PUSH direct, CLR C and MOVC A,@A+PC are not in the gap set")
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
    assert_that(to_sdas("clr", "CY", opcode=0xC3) == "\tclr\tc",
                "CLR C is assembled, not mistaken for a bit instruction: 0xC3 "
                "is CLR C, which is 325 of the instructions an earlier opcode "
                "table wrongly called a gap")
    assert_that(to_sdas("clr", "0x8e", opcode=0xC1) is None,
                "CLR bit is a gap: sdas8051 assembles the operand as CLR "
                "*direct* and does not fail, which is worse than refusing")
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
    assert_that(to_sdas("mov", "CY, 0x57", opcode=0xA2) == "\tmov\tc,0x57",
                "MOV C,bit is assembled: 0xA2 is not a gap")
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

    # The digest, which is what makes a text-only edit fail the cheap gate. The
    # expected value is a known answer, not a recorded one: if the canonical
    # form is changed deliberately, changing this string is the visible act that
    # goes with it, and every row of reassembly.csv has to be re-reported after
    # it.
    listed = ("0040  74 12 -     mov   a,#0x12\n"
              "0042  02 00 45    ljmp  0x0045\n"
              "0045  22  -  -    ret\n")
    listed_digest = digest_of(parse_listing_str(listed))
    assert_that(listed_digest == "b926d09ec5434581",
                "a fixed three-instruction listing digests to %s"
                % listed_digest)
    # The failure the column exists for: byte column identical, one character of
    # mnemonic different. Both assertions above pass on this listing, which is
    # why the re-encode could not be dropped for a cheaper check.
    assert_that(digest_of(parse_listing_str(listed.replace("mov   a", "movx  a")))
                != listed_digest,
                "a changed mnemonic with an unchanged byte column changes the "
                "digest")
    assert_that(digest_of(parse_listing_str(listed.replace("ret", "nop")))
                != listed_digest,
                "a changed mnemonic in the last instruction changes the digest "
                "too, so the count prefix is not doing the work alone")
    # Deliberate non-coverage, asserted so it reads as a decision: case and
    # internal whitespace do not change the claim a listing makes, and folding
    # them in would mean a re-wrap needed the assembler to resolve.
    assert_that(digest_of([(0x0040, "7412", "MOV", "a, #0x12"),
                           (0x0042, "020045", "ljmp", " 0x0045 "),
                           (0x0045, "22", "RET", "  ")]) == listed_digest,
                "case, padding and the space after a comma are folded away")
    assert_that(digest_of([(0x0040, "7413", "mov", "a,#0x12"),
                           (0x0042, "020045", "ljmp", "0x0045"),
                           (0x0045, "22", "ret", "")]) != listed_digest,
                "a changed byte column changes the digest, which is what keeps "
                "this independent of the byte check rather than a copy of it")

    # The comparison, not the hash: a check that cannot fail is not a check.
    # Written to a temporary report and read back through the same DictReader
    # check() uses, so a misspelled column name shows up here rather than as a
    # digest that quietly compares nothing.
    fd, rpath = tempfile.mkstemp(prefix="digest-selftest-", suffix=".csv")
    with os.fdopen(fd, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["program", "addr", "name", "outcome", "listing_digest"])
        w.writerow(["bank0", "0040", "agrees", "match", listed_digest])
        w.writerow(["bank0", "0042", "edited", "match", "0123456789abcdef"])
        w.writerow(["bank0", "0045", "predates", "match", ""])
    try:
        probe = {r["addr"] + "|" + r["program"]: r
                 for r in csv.DictReader(open(rpath, newline=""))}
        live = {k: "bank0/%s.asm" % k.split("|")[0] for k in probe}
        compared, bad = compare_digests(
            probe, {k: listed_digest for k in probe}, live)
        assert_that(compared == 2 and len(bad) == 2,
                    "one agreeing row passes, one edited row and one "
                    "undigested row fail (compared %d, failed %d)"
                    % (compared, len(bad)))
        assert_that([r[3] for r in bad] == ["edited", "predates"],
                    "the edited row and the row from before the column are "
                    "both named")
        assert_that(listed_digest in bad[0][5] and "0123456789abcdef" in bad[0][5]
                    and "0042.asm" in bad[0][5],
                    "a disagreement names both digests and the listing they "
                    "were computed from")
        assert_that("predates" in bad[1][5],
                    "a row with no digest fails as predating the column rather "
                    "than being skipped")
    finally:
        os.remove(rpath)

    # The provenance comparison, which is the part of --verify-provenance with
    # no git in it and so the part that can quietly start passing everything.
    # A comparison that compares nothing, or that drops one column too many, is
    # indistinguishable from a correct one on any pair that agrees -- and the
    # committed pair is a pair that agrees. No history needed, so these run
    # wherever the rest of this file runs.
    def as_csv(rows, fieldnames):
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        return buf.getvalue()

    base_fields = ["program", "addr", "name", "outcome", "instructions_checked"]
    mig_fields = ["program", "addr", "name", "outcome", "listing_digest",
                  "instructions_checked"]
    # The base rows have no listing_digest key at all, not an empty one: a
    # migration is the column being absent on one side, and a comparison that
    # had only ever seen an empty cell would not have been tested for that.
    before = [{"program": "bank0", "addr": "0040", "name": "a",
               "outcome": "match", "instructions_checked": "2"},
              {"program": "bank0", "addr": "0042", "name": "b",
               "outcome": "partial", "instructions_checked": "3"}]
    # A migration's column: new on every row, and different from row to row, so
    # comparing it -- or dropping only the first row's -- fails here.
    after = [dict(before[0], listing_digest="38b4854aff7d69ca"),
             dict(before[1], listing_digest="180ddaa4dd467c12")]
    identical, n_base, has_digest, bad = compare_provenance(
        as_csv(before, base_fields), as_csv(after, mig_fields))
    assert_that(identical == 2 and n_base == 2 and not bad,
                "a migration that adds the column and nothing else compares "
                "equal (%d of %d row(s), %d problem(s))"
                % (identical, n_base, len(bad)))
    assert_that(has_digest == (False, True),
                "the column is reported absent on the base and present on the "
                "migration, which is the shape a migration has")
    # The failure the comparison exists to catch: the migration that also
    # touched a cell under the column. Byte-identical digests would not catch
    # this; the rows underneath them do.
    edited = [dict(after[0], instructions_checked="1"), after[1]]
    identical, _n, _d, bad = compare_provenance(
        as_csv(before, base_fields), as_csv(edited, mig_fields))
    assert_that(identical == 1 and len(bad) == 1
                and "instructions_checked" in bad[0] and "0040" in bad[0],
                "one cell changed beneath the column fails, naming the row and "
                "the cell (compared %d of 2, %d problem(s)%s)"
                % (identical, len(bad), ": " + bad[0] if bad else ""))
    # A row-count change. A row only one side has is not "nothing to differ".
    identical, n_base, _d, bad = compare_provenance(
        as_csv(before, base_fields), as_csv(after[:1], mig_fields))
    assert_that(identical == 1 and n_base == 2 and len(bad) == 1
                and "0042" in bad[0],
                "a row missing from the migration fails and is named, rather "
                "than compared as two rows that agree")
    # And a column the migration also renamed, which a comparison that only
    # walked the rows would never see: the renamed field matches nothing, so
    # every row looks unchanged unless the header is compared too.
    renamed = ["program", "addr", "name", "outcome", "listing_digest", "checked"]
    identical, _n, _d, bad = compare_provenance(
        as_csv(before, base_fields),
        as_csv([{f: r["instructions_checked"] if f == "checked" else r[f]
                 for f in renamed} for r in after], renamed))
    assert_that(identical == 0 and len(bad) == 1 and "header" in bad[0],
                "a column the migration also renamed fails as a header "
                "difference, and no row counts as identical (%d identical%s)"
                % (identical, ": " + bad[0] if bad else ""))
    # An empty side is not a pass either. A reader that has compared no rows
    # has compared nothing.
    identical, n_base, _d, bad = compare_provenance(
        as_csv(before, base_fields), "program,addr\n")
    assert_that(identical == 0 and len(bad) == 1 and "no rows" in bad[0],
                "an empty report fails rather than comparing zero rows to zero "
                "and agreeing")

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
        outcome, detail, nchk, nskip, digest = check_one(row, bytes(img), work, sdas)
        assert_that(outcome == "match",
                    "a correct listing re-encodes to the image bytes (%s %s)"
                    % (outcome, detail))
        assert_that(digest == digest_of(parse_listing_str(
                        "0040  74 12 -     mov   a,#0x12\n"
                        "0042  02 00 45    ljmp  0x0045\n"
                        "0045  22  -  -    ret\n"
                        "0046  00  -  -    nop\n")),
                    "check_one returns the digest of the listing it parsed, so "
                    "the report is written without a second parse")
        # Corrupt one byte of the image: the check must notice.
        img[0x41] = 0x13
        outcome = check_one(row, bytes(img), work, sdas)[0]
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
    ap.add_argument("--add-digest-column", action="store_true",
                    help="one-shot: add listing_digest to the existing report, "
                         "without re-encoding (refuses to run twice)")
    ap.add_argument("--verify-provenance", action="store_true",
                    help="audit a listing_digest migration against the history "
                         "it sits in; needs --base and --migration, and a full "
                         "git history")
    ap.add_argument("--base", help="last full --report revision")
    ap.add_argument("--migration", help="the revision that added listing_digest")
    ap.add_argument("--listings-from",
                    help="revision before the window that last wrote the "
                         "listings, for the positive control (default: <base>^)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.verify_provenance:
        if not args.base or not args.migration:
            ap.error("--verify-provenance needs --base and --migration")
        return verify_provenance(args.base, args.migration, args.listings_from)
    if args.add_digest_column:
        return add_digest_column()
    if args.check:
        return check()
    results, tally, sdas = verify(limit=args.limit, jobs=args.jobs,
                                  work=args.work, sdas=args.assembler)
    if args.report:
        print("\n  wrote %s" % os.path.relpath(write_report(results, sdas), REPO))
    return 0 if tally.get("mismatch", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
