#!/usr/bin/env python3
"""Re-assemble the committed disassembly and compare it to the firmware bytes.

Two tiers of checks, and the difference between them is the point.

**`--check`, no assembler needed.** Four assertions. Every byte of every
committed listing is compared against the firmware image. The committed report
is confirmed to still describe those listings. Every row's `listing_digest` is
recomputed from the listing it names and compared. And every row's `name` is
compared against the one the listing index carries for the same address. The
first covers 100% of the instructions, including the ones the assembler below
cannot express, and all four run anywhere.

**It also derives what is in the instructions the assembler cannot express.**
`refusal_reason()` replays `to_sdas()`'s decision order over the committed
listings and `--check` prints the composition -- which form, how many, and
which of the tool's refusal rules no instruction here reached -- beside the
count, and compares the total against the report's own `instructions_unchecked`
column. That comparison is the check; the composition is what it prints. Two
derivations of the same listings, one through the decision order and one
through the CSV written from it, that have to agree -- `docs/findings.md` §14g
named the absence of one as its closing question, and what is printed is not a
claim the 1:1 property needs: those instructions are still excluded from the
re-encode, which is why `verify_gap_text.py` exists.

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

**`name` is a copy rather than a measurement, and that is what decides how
`--check` holds it.** `write_report()` writes the name the listing index held at
report time, so the column restates a source of truth this repository already
checks rather than recording something a run observed; `outcome`,
`listing_digest`, `instructions_*` and `assembler` are the other kind, and
copying a value into one of those asserts an observation that was not made. So
the fourth assertion compares the report's copy against the index's, per
(program, addr), and names the rows that disagree.

**What that comparison establishes, exactly.** That the report and the index
still agree about what to call each function. Not that the name is a good one:
naming a function is a judgement about what it does, and the judgement belongs
to the annotation and the disassembly, not to this file. A name that agrees with
the index is a name the index wrote, exactly as a digest that agrees is a digest
the report was measured with -- neither is a claim that the thing is right, and
`--refresh-name-column` below is the deliberate, proved-one-column way to
re-copy it.

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

  match         every instruction re-encodes to the firmware bytes
  partial       some do; the rest use a form sdas8051 cannot express
  assembler-gap none of them do: no instruction in the function is a form
                sdas8051 can express
  listing-gap   every instruction translated, sdas8051 ran, and the listing it
                printed has no entry at an address the comparison reached. What
                was observed is the absence of an entry in read_lst()'s parse --
                not that the assembler refused the form, which is what
                assembler-gap above means, and not that it emitted nothing,
                which nothing here establishes.
  mismatch      sdas assembled something and it is not what the firmware holds.
                The only outcome that threatens the claim, and disasm8051.py is
                the tie-breaker.

Requires `sdas8051` (SDCC) for the full run. Without it the tool says so and
`--check` still runs.

Usage:
    python3 ec/tools/verify_reassembly.py --work /tmp/ec            # full run
    python3 ec/tools/verify_reassembly.py --work /tmp/ec --limit 40 # a sample
    python3 ec/tools/verify_reassembly.py --check                   # no assembler
    python3 ec/tools/verify_reassembly.py --emit-csv /tmp/reasm.csv  # per-row
    python3 ec/tools/verify_reassembly.py --self-test               # known answers,
        # and one per way --verify-provenance below can fail, each driven
        # against a throwaway repository rather than against this one
    python3 ec/tools/verify_reassembly.py --add-digest-column       # one-shot
    python3 ec/tools/verify_reassembly.py --refresh-name-column     # repeatable:
        # copy the listing index's names into the report's `name` column, and
        # prove from the written file that no other cell moved. A copy, not a
        # measurement, which is why this one is not one-shot
    python3 ec/tools/verify_reassembly.py --verify-provenance \\
        --base 08b72e2 --migration a56b3bb --listings-from 8c7985e
        # audit a digest migration against history; needs a full clone.
        # ci.yml's `gates` job has one (`fetch-depth: 0`) and is the job that
        # runs the gate; its `workflows` job is default-depth and runs no
        # history reader, so it never reaches this mode
    python3 ec/tools/verify_reassembly.py --verify-provenance \\
        --repo /path/to/other/clone --base BASE --migration MIG
        # the same audit against another clone -- a fork, or a worktree of
        # one -- so the revisions resolve there. Defaults to the repository
        # this script is in, which is every invocation above.
"""
import argparse
import collections
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

import disasm8051

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
DECOMPILED = os.path.join(REPO, "ec", "decompiled")
LISTING_INDEX = os.path.join(DECOMPILED, "listing-index.csv")
REPORT = os.path.join(REPO, "ec", "ghidra", "reassembly.csv")
# Where build_images() puts the flat per-bank images, so --check can compare a
# listing against the firmware without a full Ghidra run.
IMAGE_DIR = os.path.join(tempfile.gettempdir(), "ec-verify-images")

# The modes that answer without running the re-encode, so there are no per-row
# results for --emit-csv to write. `spelled` is what the refusal prints and what
# --help names, `dest` is what argparse calls it, and `remedy` is the other thing
# the user can type instead -- which is not the same sentence for all of them:
# --verify-provenance reads git history and has no verify path to be offered, so
# the "--work <dir>" tail the verify modes carry would name a flag that does
# nothing for it.
#
# A list rather than a condition in main() because the condition was written for
# the three modes that existed when it was added and a fourth early return was
# then added beside it, which is how --verify-provenance reached the emit path
# with --emit-csv set and honoured neither. --self-test's own completeness hold
# is what keeps the two equal. What is not a boolean mode is a different fact
# and is not in here: --limit re-encodes, and truncates, which
# refuses_emit_csv() asks about separately.
Mode = collections.namedtuple("Mode", "spelled dest remedy")
NO_RE_ENCODE = (
    Mode("--check", "check",
         "the read-only verify path is `--work <dir>`"),
    Mode("--self-test", "self_test",
         "the read-only verify path is `--work <dir>`"),
    Mode("--add-digest-column", "add_digest_column",
         "the read-only verify path is `--work <dir>`"),
    Mode("--refresh-name-column", "refresh_name_column",
         "the read-only verify path is `--work <dir>`"),
    Mode("--verify-provenance", "verify_provenance",
         "run it on its own, without --emit-csv; it reads git history and "
         "re-encodes nothing, so there is nothing to compare against"),
)

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
# cannot be used to judge a decode of them. AJMP and ACALL were previously in
# this set, but they are now arbitrated via disasm8051.py instead of dropped.
# See docs/findings/verify_reassembly_ajmp_acall.md for the analysis showing
# all 110 instances in the firmware satisfy the 8051 encoding formula.
GAP_MNEMONICS = set()

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
    # The handle is closed here rather than left to the garbage collector,
    # because this is called once per listing and a full run holds 2,717 of
    # them at once. That leaked silently -- CPython collects an unreferenced
    # file promptly, so no run ever complained -- until a unit test called it
    # under unittest's warning filters and printed one ResourceWarning per
    # listing. Three suites carry a comment about this and one reads listings
    # with its own reader to avoid it; #229's census cannot, since the claim it
    # makes is that this reader and check_one() agree on a listing's first
    # address. `out` already holds a tuple per instruction, so holding the
    # lines is not the part that costs.
    with open(path, errors="replace") as handle:
        lines = list(handle)
    for line in lines:
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


def _opcode_of(hexbytes):
    """The instruction's opcode, or None for a listing line with no byte column."""
    return int(hexbytes[:2], 16) if len(hexbytes) >= 2 else None


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
    # AJMP and ACALL: arbitrate via disasm8051.paged_target() instead of
    # dropping them. All 110 instances in the firmware satisfy the 8051 encoding
    # formula: ((addr + 2) & 0xF800) | ((opcode & 0xE0) << 3) | operand.
    if mnem in ("ajmp", "acall") and pc is not None and hexbytes and opcode is not None:
        parts = _operand_list(ops)
        if parts:
            try:
                operand = int(parts[0], 16)
                target = disasm8051.paged_target(opcode, operand, pc)
                parts[0] = "0x%04x" % target
            except (ValueError, IndexError):
                return None
        parts = [p.lower() for p in parts]
        return "\t%s\t%s" % (mnem, ",".join(parts))
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


# The two predicates to_sdas() applies inline rather than through a table, and
# the gap vocabulary this file therefore knows by name rather than by the
# collections above. Kept as the strings they are, because verify_gap_text.py
# writes them into a committed CSV's `reason` column and compares against it.
CJNE_DIRECT = "CJNE direct operand"
BRANCH_RANGE = "branch displacement out of range"
DA_A = "reserved `da A`"


def refusal_reason(mnem, ops, pc, size, opcode, hexbytes):
    """Which predicate in `to_sdas()` above declines this instruction, or None.

    The same order `to_sdas()` applies them in, for the same reasons, so the
    set of instructions it names is `to_sdas()`'s to decide and this only
    reports which rule declined one. A None here means either `to_sdas()`
    accepted the instruction or it declined one nothing here explains -- and
    the second is a form this file has not been taught, which is a failure for
    a caller that means to cross-decode every refusal rather than a footnote.

    `verify_gap_text.why()` is this function by delegation. It was written
    there first and drifted from here once; there is one decision order and it
    lives beside the function that applies it, so there is one enumerator of
    the vocabulary rather than two that can disagree.
    """
    key = re.sub(r"\s*,\s*", ",", ("%s %s" % (mnem, ops)).lower())
    for gap in sorted(GAP_FORMS):
        if key.startswith(gap):
            return 'GAP_FORMS "%s"' % gap
    if mnem in GAP_MNEMONICS:
        return "GAP_MNEMONICS %s" % mnem
    # Unreachable from a decline -- to_sdas() *translates* the reserved `da A`
    # rather than declining it -- but to_sdas() still applies it in this
    # position, so it is named in the same position.
    if mnem == "a" and not ops.strip():
        return DA_A
    if opcode is not None and opcode in BIT_UNSUPPORTED:
        return "BIT_UNSUPPORTED 0x%02X" % opcode
    parts = _operand_list(ops)
    if mnem == "cjne" and parts and parts[0].lower().startswith("0x"):
        return CJNE_DIRECT
    if mnem in RELATIVE_BRANCH and pc is not None and parts:
        try:
            rel = int(parts[-1], 16) - (pc + size)
        except ValueError:
            return None
        if not -128 <= rel <= 127:
            return BRANCH_RANGE
    return None


def refusal_rules():
    """Every predicate `refusal_reason()` can name, as the strings it names.

    Enumerated from the collections above rather than kept as a list beside
    them, so a form added to `GAP_FORMS` or an opcode to `BIT_UNSUPPORTED` is
    in here the moment it is there. `check()` prints the ones no instruction in
    the committed listings reached, which is what turns §11's sentence that
    `CLR bit` and `CJNE`-on-direct are in the vocabulary and in none of the
    image's refusals from a recollection into a reading.

    The reserved `da A` is not one of these: `to_sdas()` translates that form
    rather than declining it, so there is no refusal for it to name. It is a
    rule `refusal_reason()` can still return, and the two facts are different.
    """
    return (sorted('GAP_FORMS "%s"' % gap for gap in GAP_FORMS)
            + sorted("GAP_MNEMONICS %s" % m for m in GAP_MNEMONICS)
            + sorted("BIT_UNSUPPORTED 0x%02X" % op for op in BIT_UNSUPPORTED)
            + [BRANCH_RANGE, CJNE_DIRECT])


def refusal_composition(insns):
    """-> (composition, unexplained) over one listing's parsed instructions.

    `composition` is {(predicate, mnemonic): n} for the instructions
    `to_sdas()` declines, and `unexplained` is [(addr, hexbytes, mnem, ops)]
    for the ones `refusal_reason()` cannot name. The mnemonic is part of the
    key because a reader asking what the refusals *are* is asking for
    `ajmp`/`acall`/`mov`/`cpl`, while the rule is what the tool uses to decide
    -- `clr 0x8e` is `CLR direct` and `CLR bit` depending on the byte in front
    of it -- and one mnemonic can be refused by more than one rule.
    """
    composition = collections.Counter()
    unexplained = []
    for addr, hexbytes, mnem, ops in insns:
        size = len(hexbytes) // 2
        opcode = _opcode_of(hexbytes)
        if to_sdas(mnem, ops, pc=addr, size=size, opcode=opcode,
                   hexbytes=hexbytes) is not None:
            continue
        reason = refusal_reason(mnem, ops, addr, size, opcode, hexbytes)
        if reason is None:
            unexplained.append((addr, hexbytes, mnem, ops))
        else:
            composition[(reason, mnem)] += 1
    return composition, unexplained


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

    Returns (outcome, detail, n_compared, n_checked, n_skipped, digest,
    anchor). The digest is computed here, off the listing this call has already
    parsed, rather than by a second parse in write_report: #138 made this
    parse-once, and reading it twice to add a column would give the saving
    back. It is empty for the two outcomes that never reach a listing, because
    there is nothing to digest.

    `n_compared` is bytes, and it is the only one of the three counts that is a
    measurement of verification rather than of translation: it is accumulated
    inside the comparison loop, once per byte that reached the `got != want`
    test. A byte the listing has no entry for never reaches that test, so a
    function that translates everything and compares nothing counts zero -- which
    is what `assembler-gap` used to report as `len(checked)` instructions, and
    what made "45,394 of 45,537 re-encode to the firmware bytes" an
    overstatement rather than a bound (docs/findings/
    reassembly-checked-counts-comparisons.md).

    `n_checked` stays an instruction count, so `instructions_checked` keeps the
    meaning the committed report's column has always had and the rows above it
    keep their numbers. `anchor` is `insns[0][0]`, the address the `.org` is
    emitted at and therefore the first one a listing entry can be read at. It is
    not the row's own address for 14 rows, so a `listing-gap` detail that names
    an address below the row that reports it is this and not a mis-parse."""
    rel = row["out_file"]
    if not rel or rel.startswith("("):
        return "skipped", rel, 0, 0, 0, "", 0
    path = os.path.join(DECOMPILED, rel)
    if not os.path.isfile(path):
        return "missing-listing", rel, 0, 0, 0, "", 0
    insns = parse_listing(path)
    digest = digest_of(insns)
    if not insns:
        return "empty-listing", rel, 0, 0, 0, digest, 0

    lines = ["\t.area CODE (ABS)", "\t.org 0x%04x" % insns[0][0]]
    anchor = insns[0][0]
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
        # A genuine expressiveness gap, and the only place that gets the name:
        # nothing in this function translated, so there was never anything to
        # hand the assembler. The other case that used to answer to it -- a
        # listing with no entry where one was expected -- returns
        # `listing-gap` below.
        return ("assembler-gap", (skipped[0][2] if skipped else ""),
                0, 0, len(skipped), digest, anchor)

    start = insns[0][0]
    end = insns[-1][0] + len(insns[-1][1]) // 2
    stem = os.path.join(work, "f")
    src = stem + ".s51"
    with open(src, "w") as f:
        f.write("\n".join(lines) + "\n")
    r = subprocess.run([sdas, "-lxosgff", src], capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()
        return ("assembler-error", (tail[-1] if tail else "failed"),
                0, len(checked), len(skipped), digest, anchor)
    mem = read_lst(stem + ".lst")
    for addr, nbytes, _why in skipped:
        for i in range(max(1, nbytes)):
            if start <= addr + i < len(image) and addr + i in mem:
                # The assembler emitted something here after all, from a
                # neighbouring instruction. Not a reason to fail.
                pass
    compared = 0
    for addr, nbytes in checked:
        for i in range(max(1, nbytes)):
            a = addr + i
            want = image[a] if a < len(image) else None
            got = mem.get(a)
            if got is None:
                # Every instruction above translated and the assembler ran and
                # exited 0, so this is not a refusal: read_lst()'s parse of the
                # listing has no entry at an address the comparison reached.
                # Which of the three causes that is -- an expressiveness
                # refusal, a listing shape this build does not produce, or an
                # anchor read_lst()'s regex cannot see -- is not settled here and
                # is not settled by anything in this file; docs/findings/
                # reassembly-checked-counts-comparisons.md names all three.
                # The anchor is in the detail because a detail naming an
                # address below its own row is the anchor and not the failure:
                # 14 rows of the committed report anchor somewhere else.
                return ("listing-gap",
                        "no bytes emitted at %04X (anchored at %04X)"
                        % (a, anchor),
                        compared, len(checked), len(skipped), digest, anchor)
            compared += 1
            if got != want:
                return ("mismatch",
                        "%04X: assembled %02X, firmware %02X" % (a, got, want),
                        compared, len(checked), len(skipped), digest, anchor)
    if skipped:
        return ("partial", "%d of %d instruction(s) unchecked, first: %s" % (
            len(skipped), len(checked) + len(skipped), skipped[0][2]),
            compared, len(checked), len(skipped), digest, anchor)
    return "match", "", compared, len(checked), 0, digest, anchor


def scratch_dir(work, index):
    """One scratch directory per function, created on demand.

    Per *function* rather than per worker, and the difference is not cosmetic.
    A pool of `jobs` workers pulling from one queue holds whichever row indices
    happen to be in flight, and that set drifts as soon as one worker finishes
    early -- so handing out directories by `index % jobs` eventually hands two
    concurrent functions the same one, and they overwrite each other's `f.s51`
    and `f.lst`. The run then reports `assembler-error` and "no bytes emitted
    at ..." for functions that were never wrong. Measured on this repository's
    runner over the same committed inputs: 2,579, 2,588, 2,590 and 2,591
    `match` across four `--jobs 4` runs against 2,621 on every `--jobs 1` run,
    with `mismatch` 0 throughout and the instruction totals identical. That is
    not a property of the assembler, and a comparison against the committed
    report would have named the raced rows as rows that moved.
    """
    d = os.path.join(work, "f%05d" % index)
    os.makedirs(d, exist_ok=True)
    return d


def run_rows(rows, work, images, sdas, jobs, check=None):
    """check_one over `rows`, `jobs` at a time. -> results, in the order given.

    Each row gets `scratch_dir(work, index)`, its own directory, so no two rows
    in flight together can share one -- see scratch_dir() for the race that
    `dirs[idx % jobs]` produced and what it cost the outcome tallies
    (docs/findings.md §14g). An earlier fix on a parallel branch gave each
    *worker thread* its own directory instead; either closes the race, and
    this keeps the per-function one because it is the one the committed
    measurement in §14g was taken with.

    `check` defaults to check_one; the self-test substitutes a recorder,
    which is the only way to observe the dispatch without running 2,705
    assembles and hoping the race shows up.
    """
    check = check or check_one

    def one(item):
        idx, row = item
        try:
            return (row,) + check(
                row, images.get(row["program"]) or images["bank0"],
                scratch_dir(work, idx), sdas)
        except Exception as exc:                       # a crash is a result
            return row, "error", "%s: %s" % (type(exc).__name__, exc), 0, 0, 0, "", 0

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        return [tuple(r) for r in pool.map(one, list(enumerate(rows)))]


def verify(limit=None, jobs=8, work=None, sdas=None, quiet=False):
    sdas = find_assembler(sdas)
    if not sdas:
        print("verify_reassembly: sdas8051 not found.\n"
              "  This check is NOT skipped silently: it simply did not run.\n"
              "  Install SDCC, or set SDAS8051=/path/to/sdas8051, and re-run.")
        # None rather than an exit status: there is no tally here, and main()
        # used to unpack this answer as a result tuple and die with a TypeError
        # on exactly the path the message above tells the reader how to fix.
        return None
    rows = [r for r in csv.DictReader(open(LISTING_INDEX, newline=""))
            if r["out_file"] and not r["out_file"].startswith("(")]
    if limit:
        rows = rows[:limit]
    work = work or tempfile.mkdtemp(prefix="reassembly-")
    images = build_images(work)
    loaded = {p: open(path, "rb").read() for p, path in images.items()}

    results = run_rows(rows, work, loaded, sdas, jobs)

    tally = results_tally(results)
    compared = sum(r[3] for r in results)
    checked = sum(r[4] for r in results)
    skipped = sum(r[5] for r in results)
    insn_total = checked + skipped
    version = assembler_version(sdas)
    if not quiet:
        # Read here, once, and compared here rather than in main(): the report
        # is about to be overwritten by a --report run's write_report(), and a
        # comparison made afterwards would be a run against its own output.
        committed = committed_report()
        for line in compare_assembler(version, committed, sdas=sdas, path=REPORT)[0]:
            print(line)
        total = len(results)
        matched = tally.get("match", 0)
        partial = tally.get("partial", 0)
        print("\n  reassembly, by function (%d total):" % total)
        for outcome in sorted(tally, key=lambda o: -tally[o]):
            print("    %-16s %d" % (outcome, tally[outcome]))
        print("\n  reassembly, by instruction:")
        print("    translated into sdas8051 source : %d of %d (%.2f%%)"
              % (checked, insn_total, 100.0 * checked / insn_total if insn_total else 0))
        # The byte count is the one worth reading, because it is the one that
        # says how much was verified rather than how much was handed over. It
        # is short of the instruction count by whatever a `listing-gap` row
        # reached first and never got past.
        print("    bytes compared to the firmware  : %d" % compared)
        print("    unchecked (sdas8051 cannot express the form): %d" % skipped)
        print("\n  %d function(s) have every instruction re-encode byte-exactly; "
              "%d more have all but %d instruction(s) verified."
              % (matched, partial, skipped))
        # Last, so what a reader takes away from the bottom of the screen is the
        # disagreement rather than the reassuring number above it.
        for line in compare_tally(results, tally, committed,
                                  limited=bool(limit))[0]:
            print(line)
    return results, tally, sdas, version


def assembler_version(sdas):
    """The assembler's own version string, for the report and for the run's own
    output.

    The gap set is a property of the assembler as much as of the code, so a
    report that does not say which one produced it is not a measurement, and a
    reader comparing two reports needs to know whether they used the same tool.

    What moves with the version is the *split* -- which rows read `match` and
    which read `assembler-gap` or `listing-gap` -- because which of those three
    a row gets is decided by what the assembler emits rather than by the
    firmware. What does not move is `mismatch`: the firmware bytes are the
    arbiter there, and a different ASxxxx changing that number would be a
    finding. Measured between the committed report's
    `05.50.4+NoICE+SDCCmods-WIP-R14` and the Ubuntu `sdas8051 02.00` on this
    repository's runner: `match` 2,574 -> 2,621, `assembler-gap` 58 -> 6,
    `mismatch` 0 -> 0, and `instructions_checked` 45,394 -> 45,394. The match
    count is therefore not a fact about the firmware alone, and this file
    previously said it was.

    The figure quoted here is the one its run measured, on a report that has
    since grown; `reassembly_checked_bound.py --check` prints the census
    against the committed CSV, which is the one to read for the tree as it is
    now. The `instructions_checked` total being *identical* across the two
    builds is not a robustness result either -- it is that the column counts
    what was handed to sdas8051 rather than what was compared against the
    firmware. The 702 instructions in the 48 committed rows whose listing parse
    had no entry at their own anchor are inside the 45,394 both runs report, and
    the 02.00 run did compare and match every one of them --
    `evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv` is where.
    docs/findings/reassembly-checked-counts-comparisons.md."""
    try:
        r = subprocess.run([sdas], capture_output=True, text=True, timeout=20)
        for line in (r.stdout + r.stderr).splitlines():
            if "Assembler V" in line:
                return line.split("Assembler V", 1)[1].split()[0].strip()
    except Exception:
        pass
    return "unknown"


def write_report(results, sdas, path=REPORT, version=None):
    """Write a run's per-row results. -> the path written, or None if refused.

    # `version=None` falls back to reading the banner here, so this stays the
    # report's only writer and the `assembler` cell is still the version that
    # produced this run. verify() passes the one it already computed, so main()
    # does not shell out twice and the report and the run's own output cannot
    # disagree about which assembler answered.

    **A run carrying any outcome outside OUTCOMES is not written at all**, to
    any destination. The file's columns claim a measurement per row and the
    `assembler` cell says which run produced it, so a row labelled `error` in
    one is a claim about coverage that nothing established -- and a scratch
    `--emit-csv` carrying one is the same broken claim in a file nobody reads
    the `assembler` column of, which is why the refusal is here rather than in
    the `--report` branch of main().

    Refusing rather than writing-with-a-marker also leaves whatever file is
    already at `path` in place, and that file is still an honest description of
    the run that produced it. So `--check` stays green while the run that could
    not measure goes red, which is where the failure belongs: not on the
    artifact that was correct when it was written. Nothing is lost
    diagnostically, because the run's own output has already named these rows
    through compare_tally()'s `moved` list -- which carries a row whose outcome
    differs from the committed one and a row the committed report has no entry
    for, and the committed report holds no residual, so every one of these is on
    it.

    docs/findings/reassembly-unmeasured-row-policy.md has the settlement.
    """
    refused = unmeasured(results_tally(results))
    if refused:
        print("  not writing %s: %d row(s) carry an outcome outside OUTCOMES, "
              "and every column of a report claims a measurement."
              % (os.path.relpath(path, REPO),
                 sum(n for _o, n in refused)))
        for outcome, n in refused:
            print("    %d %s: %s" % (n, outcome, unmeasured_reason(outcome)))
        first = next(r for r in results if r[1] not in OUTCOMES)
        print("    first: %s %s %s" % (first[0].get("program"),
                                       first[0].get("addr"),
                                       first[0].get("name")))
        return None
    version = version if version is not None else assembler_version(sdas)
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        # The column set is the committed report's, byte for byte, and it is
        # the byte count that must stay that way rather than a preference:
        # tools/check_deep_schedule_emit.py holds emit_csv()'s header against
        # the first line of ec/ghidra/reassembly.csv, because a column on one
        # side only is how the (program, addr) join the nightly artifact exists
        # for stops working. `check_one()` returns the bytes it compared and the
        # address it anchored at; both belong in this header, and both wait for
        # the re-report that #157 owes, the same way listing_digest waited for
        # --add-digest-column. The anchor is in the `detail` of every
        # `listing-gap` row instead, so a report that has been re-run under this
        # code says where it looked without a column for it.
        w.writerow(["program", "addr", "name", "outcome", "listing_digest",
                    "instructions_checked", "instructions_unchecked", "detail",
                    "assembler"])
        for row, outcome, detail, _compared, checked, skipped, digest, _a in results:
            w.writerow([row["program"], row["addr"], row["name"], outcome,
                        digest, checked, skipped, detail,
                        "sdas8051 %s" % version])
    return path


def refuses_committed_report(path):
    """-> True, having said why, if `path` is the committed report.

    One predicate rather than a check per caller, because the invariant is one
    writer for one *result*: the rows of `reassembly.csv` are written by
    `--report` and by nothing else, and a second path to them is the hazard
    `--add-digest-column` needed its own guard for. `realpath` on both sides so
    a relative spelling or a symlink reaches the same verdict as the absolute
    one.

    (Corrected 2026-10-02, issue #627: this said the *file* was written by
    `--report` and by nothing else, which stopped being true when
    `refresh_name_column()` arrived. That function is a second writer of the
    file and not of any result -- it moves one copied cell and proves from the
    written file that it moved nothing else -- so the predicate below is
    unchanged and only the sentence it prints was wrong.)
    """
    if os.path.realpath(path) != os.path.realpath(REPORT):
        # realpath follows symlinks but not hardlinks, and a hardlink to the
        # report is the same inode under another name -- open(path, "w") on it
        # truncates the committed report exactly as writing REPORT would. So
        # the comparison is made on the inode where both files already exist.
        try:
            if os.path.exists(path) and os.path.samefile(path, REPORT):
                pass                      # same file, fall through to refuse
            else:
                return False
        except OSError:
            return False
    print("  %s is written from a re-encode: by --report, and by nothing else\n"
          "     that carries per-row results. A per-row comparison needs a "
          "second path,\n     not a second writer for the first one; write it "
          "somewhere else."
          % os.path.relpath(REPORT, REPO))
    return True


def refuses_emit_csv(args):
    """-> (Mode or "--limit", why) if --emit-csv cannot be honoured, else None.

    Two reasons, and they are different facts rather than one rule. A mode that
    does not re-encode has no per-row results to write at all. A `--limit` does
    re-encode, and writes a subset of the rows under the full report's header:
    a file a reader cannot tell from the whole thing by looking at it, and the
    one artefact a reader is likely to diff against the committed one, where
    every absent row would read as a disagreement rather than as the limit.

    Neither is written, because writing something that looks like a report and is
    not one is worse than the run having said so: the whole point of the flag
    is that two runs can be compared, and a comparison against a truncated file
    is not one. The refusal-over-marker choice is argued in
    docs/findings/emit-csv-flag-honesty.md, from the two tools that hold
    emit_csv()'s header byte-identical to the committed report's.

    One predicate rather than a check per caller, for the reason
    `refuses_committed_report` is one: which modes exist is a fact about main()'s
    dispatch, and a second copy of it would be a second answer to it. The set is
    NO_RE_ENCODE, and --self-test holds that set equal to the branches main()
    actually dispatches on.
    """
    if args.limit is not None:
        # is not None rather than truthiness: `--limit 0` is not a limit on
        # nothing, it is a request for zero rows, and it would write a header
        # with none of the report under it.
        return ("--limit", "truncates")
    for mode in NO_RE_ENCODE:
        if getattr(args, mode.dest):
            return (mode, "no-re-encode")
    return None


def emit_csv(results, sdas, path):
    """The per-row results, to a path that is not the committed report.

    Two runs of the re-encode cannot be compared without both of them on disk
    as files, and one of the two is the committed `reassembly.csv`. It is not
    re-written to get the other: `--report` is its single writer, because a
    report written by a second assembler is a different report, and one written
    by accident is a report nobody reads the `assembler` column of before
    citing its counts.
    """
    if refuses_committed_report(path):
        return 1
    try:
        wrote = write_report(results, sdas, path)
    except OSError as exc:
        # A mistyped or nested destination, said the way the rest of this tool
        # says it. A traceback through emit_csv for a path that does not exist
        # is a worse answer than the sentence, and this is the first flag here
        # that takes a path the user typed.
        print("  cannot write %s: %s" % (path, exc))
        return 1
    if wrote is None:
        # write_report() has said why. Printing "wrote" below would be the one
        # sentence this change exists to make impossible, so the refusal is
        # carried out as a status rather than as a flag to skip a print.
        return 1
    print("  wrote %s" % os.path.abspath(path))
    return 0


def check_listing_bytes():
    """Every byte in every listing, against the firmware image. No assembler.

    The re-encode above is the stronger claim but the weaker coverage: some
    instructions use forms sdas8051 cannot express, so 143 of them are
    unchecked in the committed report. This checks all of them and needs nothing
    but the firmware, so it runs in CI where the assembler does not. What is
    *in* those 143 is derived here rather than transcribed; `check()` prints it
    and compares its total against the report's own column.

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
    The composition is accumulated in that same loop for the same reason --
    `refusal_composition()` reads the parse this already has, and a second walk
    over the `.asm` files to collect a tally would give the saving back too.

    Returns (ok, checked, bad, digests, composition), digests being
    {addr|program: digest} and composition being {(predicate, mnemonic): n}
    over the instructions `to_sdas()` declines."""
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
    composition = collections.Counter()
    # A row that `continue`s above -- a missing listing, or a parse this file
    # knows to have mis-read -- is already in `bad`, so the tally's total falls
    # short of the report's and check()'s cross-check fails on it too rather
    # than letting the composition quietly cover fewer rows than the count it
    # is printed beside.
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
        # The tally, off the same `insns` the digest and the byte check above
        # were computed from. refusal_composition() re-runs to_sdas() over them
        # rather than reading the report's column, because the report is the
        # thing being checked: a tally summed from it could not disagree with
        # it and would assert nothing.
        here, unexplained = refusal_composition(insns)
        composition.update(here)
        for addr, hexbytes, mnem, ops in unexplained:
            bad.append((prog, "%04X" % addr,
                        "to_sdas() declines `%s %s` (%s) and no rule here "
                        "explains why -- teach refusal_reason() the form"
                        % (mnem, ops, hexbytes)))
    print("  listing bytes: %d instruction(s) checked against the firmware, "
          "%d disagreement(s)" % (checked, len(bad)))
    for prog, addr, why in bad[:20]:
        print("  FAIL %s %s: %s" % (prog, addr, why))
    if len(bad) > 20:
        print("  ... and %d more" % (len(bad) - 20))
    ok = not bad
    return ok, checked, len(bad), digests, composition


def report_composition(composition, report):
    """Print what is in the unchecked instructions, and check the total. -> ok.

    The composition itself is the derived number: `docs/findings.md` §14g names
    its own closing question as the fact that no committed check recomputes it,
    and this is the replay of `to_sdas()`'s decision order over
    `ec/decompiled/listing-index.csv` that answers it. It is printed rather
    than asserted against a literal, because the five forms and their counts
    move with a listing export and a hand-kept figure would be a value every
    merge has to touch.

    What *is* asserted is the total against the committed report's own
    `instructions_unchecked` column -- two derivations of the same listings,
    one through the decision order and one through the CSV that was written
    from it. They agree today; a listing edit that changes which forms are
    refused, a rule added to `GAP_FORMS`/`BIT_UNSUPPORTED`/the `CJNE` rule, and
    a stale report each move one and not the other. Without the comparison the
    composition above would be a plausible wrong number printed with a
    confident tone, which is the failure §4 is about rather than a fix for it.

    The rules with no instance are printed from `refusal_rules()` beside it, so
    §11's sentence that `CLR bit`, `CJNE` on a direct address and the
    carry-with-immediate forms are in the tool's refusal vocabulary and in none
    of this image's refusals is a reading rather than a recollection. They are
    the assembler's vocabulary, not the firmware's, and a form that has never
    been refused here says nothing about whether the firmware contains one.
    """
    total = sum(composition.values())
    print("  unchecked %d, by the rule that declined each:" % total)
    # Predicate first, then the mnemonic: the rule is the discriminator the
    # tool decides on, and a mnemonic alone reads as though the assembler
    # refused `ajmp` as a fact about `ajmp` rather than about sdas8051's
    # encoding of it.
    for (reason, mnem), n in sorted(composition.items(),
                                    key=lambda kv: (-kv[1], kv[0])):
        print("    %-28s %4d  %s" % (reason, n, mnem))
    named = {reason for reason, _mnem in composition}
    unused = [rule for rule in refusal_rules() if rule not in named]
    if unused:
        print("  and the refusal rules no instruction here reached: %s"
              % ", ".join(unused))
    cells = [int_cell(r, "instructions_unchecked") for r in report.values()]
    unreadable = sum(1 for c in cells if c is None)
    if unreadable:
        print("  FAIL %d report row(s) carry an instructions_unchecked that is "
              "not an integer, so the total below is over the rest of them"
              % unreadable)
        return False
    reported = sum(cells)
    if reported != total:
        print("  FAIL the replay refuses %d instruction(s) and the committed "
              "report sums to %d.\n"
              "       One of the two moved: the listings, the rules, or the "
              "report. The composition above\n       describes the replay, so "
              "do not read it as the report's." % (total, reported))
        return False
    print("  which is the same total as the report's instructions_unchecked")
    return True


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


def listing_index_keys(index_path=LISTING_INDEX):
    """The index's listing rows, keyed the way the report keys its own.

    -> (live, names): {addr|program: out_file} and {addr|program: name}, from
    one read of the file.

    Both come back from the same pass because the two callers need one of each
    and neither wants a second read: --check prints the path beside every row it
    names and compares the name against the same row, and a second read of one
    file is a second chance to compare against something that moved underneath
    the comparison. `addr|program` rather than `addr` for the reason
    committed_report() gives: 54 addresses carry a row in each bank window.

    A row with no `out_file`, or one that names something other than a listing,
    is not in the join at all and is skipped here exactly as it is everywhere
    else that reads the index.
    """
    live, names = {}, {}
    for r in csv.DictReader(open(index_path, newline="")):
        if r["out_file"] and not r["out_file"].startswith("("):
            key = r["addr"] + "|" + r["program"]
            live[key] = r["out_file"]
            names[key] = (r.get("name") or "").strip()
    return live, names


def compare_names(report, names, live):
    """Every report row's `name` against the listing index's, per (program, addr).

    -> (compared, bad). `report` is {addr|program: row}, `names` and `live` are
    listing_index_keys()'s two dicts. Returned rows are
    (key, program, addr, name, out_file, why), the same six fields
    compare_digests() returns, so check() prints one kind of failure the way it
    prints the other.

    A report row with no index row is named rather than skipped, and a blank
    `name` is named rather than read as agreement: both are the "nothing to
    compare, and treating that as a pass" shape compare_digests() is written
    against, and it is the one a checker fails in.

    It is a *copy* comparison and not a verification, and the difference is the
    whole argument for this being safe to re-run: the report's name was written
    from the index, so a disagreement is stale rather than wrong, and copying
    the index back establishes nothing and asserts nothing.
    """
    compared, bad = 0, []
    for key, r in sorted(report.items()):
        got = (r.get("name") or "").strip()
        rel = live.get(key, "(not in the listing index)")
        where = (r.get("program", "?"), r.get("addr", "?"),
                 r.get("name", "?"), rel)
        # The two rows with nothing to compare come before the count, as they do
        # in compare_digests(): "compared" has to mean two values were put
        # against each other, or the summary line is counting rows it skipped.
        want = names.get(key)
        if want is None:
            bad.append((key,) + where +
                       ("no name to compare against: %s has no row in the "
                        "listing index" % rel,))
            continue
        if not got:
            bad.append((key,) + where +
                       ("no name in the report: the listing index calls %s %s"
                        % (rel, want),))
            continue
        compared += 1
        if got != want:
            bad.append((key,) + where +
                       ("the report calls it %s, the listing index calls it "
                        "%s -- the report's copy of the name is stale"
                        % (got, want),))
    return compared, bad


# The outcomes `check()` and the report comparison both count, in this order, so
# the two lines read alike. A row carrying anything else is a residual, and is
# named rather than dropped: a summary that counted three of the categories and
# then printed "(of 2705)" is the arithmetic error this line exists to remove,
# and quietly leaving another category out would reintroduce it one row over.
#
# `assembler-gap` and `listing-gap` are one word apart because the distinction
# is the whole of issue #229. The first says the assembler cannot express the
# form and nothing was handed to it; the second says everything translated, the
# assembler ran and exited 0, and read_lst()'s parse of the listing it printed
# has no entry at an address the comparison reached. One used to answer to both,
# which made a measured `match` split look like a statement about what sdas8051
# can do.
OUTCOMES = ("match", "partial", "assembler-gap", "listing-gap", "mismatch")

# The most moved rows the comparison names before it says how many more. The cap
# compare_digests() uses, for the same reason: a reader acts on the first few,
# and the rest are a grep away in a file whose path is already on screen.
MOVED_CAP = 20


def split_tally(counts):
    """-> ([(outcome, n)] in OUTCOMES order, [(outcome, n)] for everything else).

    Two halves because both are needed. The ordered ones are this file's
    vocabulary for a re-encode, and a report that used another is describing a
    run in terms check_one() can produce: `assembler-error`, `error`,
    `missing-listing`, `empty-listing`, `skipped`. What the residual half *does*
    to a run is unmeasured()'s decision, one function down."""
    ordered = [(o, counts.get(o, 0)) for o in OUTCOMES]
    residual = sorted((o, n) for o, n in counts.items() if o not in OUTCOMES)
    return ordered, residual


# The residual vocabulary, and what each of these says about the run it came
# from. `unmeasured()` below decides by membership of OUTCOMES rather than by
# this table, so an outcome nobody has thought of yet fails too rather than
# passing by omission; the table is where the five this file can produce are
# written down, and its values are the sentence a failure prints. The policy and
# the argument for it: docs/findings/reassembly-unmeasured-row-policy.md.
UNMEASURED = {
    "assembler-error": "sdas8051 refused the listing; nothing was compared",
    "error": "a worker raised; nothing was compared",
    "missing-listing": "the row names a listing that is not on disk",
    "empty-listing": "the listing parsed to zero instructions, so there was "
                     "nothing to re-encode",
    "skipped": "the index row carries no listing to check",
}


def unmeasured(counts):
    """-> [(outcome, n)] for every outcome in `counts` that is not a
    measurement: everything outside OUTCOMES.

    The one predicate `run_status()`, `check()` and `write_report()` all read,
    which is what stops the three from drifting. The dividing line is measured
    against not measured rather than benign against serious: `mismatch`,
    `partial`, `assembler-gap` and `listing-gap` are all measurements and keep
    the policy `run_status()` gives, while everything here is one measurement
    absent. A version difference and a moved category are two measurements
    disagreeing, which the calibration in assembler_version() was written for;
    a report row claiming a re-encode that did not happen is a false claim about
    coverage, which is a different kind of defect and does not inherit it.

    Keyed on the `outcome` cell and on nothing else. The `detail` column cannot
    carry it: `no bytes emitted at ....` is a `listing-gap` detail and also the
    detail on most of the committed `assembler-gap` rows, so a policy read off
    `detail` would fail a measured outcome and turn `--check` red on a tree
    whose report is correct.
    """
    return split_tally(counts)[1]


def unmeasured_reason(outcome):
    """-> the sentence a failure prints for `outcome`.

    The fallback is for an outcome this file does not name, and it says so
    rather than going quiet: the row still fails, because `unmeasured()` decided
    that, and the one thing a reader must not conclude from an unnamed outcome
    is that this table is what let it through.
    """
    return UNMEASURED.get(
        outcome,
        "an outcome outside OUTCOMES that this file does not name, and so not "
        "a measurement either")


def status_for(counts):
    """-> the exit status one tally implies: 1 for a `mismatch` or for any row
    outside OUTCOMES, 0 for neither.

    The single answer two readers give, rather than two independent readings of
    `mismatch == 0` -- which is how a run and the report it wrote came to
    disagree about whether a row with no measurement behind it counted.
    """
    return 1 if (counts.get("mismatch", 0) or unmeasured(counts)) else 0


def report_tally(rows):
    """-> {outcome: n}, the tally of a report read as an iterable of rows."""
    counts = {}
    for row in rows:
        outcome = row.get("outcome") or "(blank)"
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts


def results_tally(results):
    """-> {outcome: n} over the result tuples verify() returns.

    The shape report_tally() gives for a report read back from disk, so one
    policy reads a run and the committed file the same way. verify() tallies
    with this rather than with a second copy of the loop, because a second copy
    of a tally is a second answer to the question the exit status asks.
    """
    counts = {}
    for _row, outcome, _detail, _compared, _checked, _skipped, _d, _a in results:
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts


def int_cell(row, column):
    """A report cell as an int, or None if it does not hold one.

    None rather than 0, deliberately. A cell that does not parse has to be
    named where it is summed rather than counted as nothing, because summing
    around one is §14b's shape: a check reporting a clean result over a third of
    its input, which is worse than one that reads nothing at all."""
    try:
        return int((row.get(column) or "").strip())
    except ValueError:
        return None


def committed_report(path=REPORT):
    """The committed report, read once, in the shape the comparisons need.

    -> {rows, tally, assemblers, checked, unchecked, by_key}, or None if the
    file is absent or holds no rows.

    Read once because the assembler comparison, the category comparison and the
    per-row comparison all read it, and three reads are three chances to compare
    against something that moved underneath the comparison. `by_key` is keyed
    `addr|program` and not `addr` alone: 54 addresses carry a row in each of the
    two bank windows, so a key of `addr` would leave one row of each of those
    108 with nothing to compare against and print the result as a category that
    had moved. Four of the 54 (0x031C, 0x3A60, 0x703A, 0xFF17) also share a
    listing_digest, which is what ec/ghidra/README.md's `listing_digest`
    section records; the count that makes the key necessary is 54, not four."""
    if not os.path.isfile(path):
        return None
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    assemblers = {}
    for r in rows:
        value = (r.get("assembler") or "").strip()
        assemblers[value] = assemblers.get(value, 0) + 1
    return {
        "rows": len(rows),
        "tally": report_tally(rows),
        "assemblers": assemblers,
        "checked": [int_cell(r, "instructions_checked") for r in rows],
        "unchecked": [int_cell(r, "instructions_unchecked") for r in rows],
        "by_key": {r["addr"] + "|" + r["program"]: r for r in rows},
    }


def compare_assembler(version, committed, sdas=None, path=REPORT):
    """The live assembler's version against the committed report's.
    -> (lines, warned).

    A line that does not identify one side or the other begins `NOTE`, and
    `warned` is true when there is one. That marker is for the self-test and for
    the reader, and deliberately not an exit status: a version difference is
    expected wherever the committed report was not measured, because
    project-setup installs Ubuntu's sdcc and does not install the nix shell the
    report was measured in, and a nightly that failed on it would be a nightly
    failing on the machine it ran on.

    The cases that are easy to get wrong are handled rather than guessed. A
    report with no assembler column, or with the cells left empty, is a report
    from before the column existed and agrees with nothing. A report holding more
    than one distinct value has no single answer to compare against, so all of
    them are named with their row counts and none is picked. And
    `version == "unknown"` is what assembler_version() returns when it cannot
    read the banner at all: a version that was not read has established nothing,
    and printing it as agreement would be the one answer that is certainly
    wrong."""
    where = os.path.relpath(path, REPO)
    bare = "sdas8051 %s" % version
    mine = bare + ("  (%s, this run)" % sdas if sdas else "")
    if committed is None:
        return ["  assembler: %s" % mine,
                "    NOTE there is no committed report at %s, so this run's "
                "assembler has nothing to be compared against." % where], True
    named = {v: n for v, n in committed["assemblers"].items() if v}
    plural = "" if committed["rows"] == 1 else "s"
    if not named:
        theirs = "(no assembler cell)"
    elif len(named) == 1:
        theirs = sorted(named)[0]
    else:
        theirs = ", ".join("%s: %d row%s" % (v, n, "" if n == 1 else "s")
                           for v, n in sorted(named.items()))
    lines = ["  assembler: %s" % mine,
             "  committed: %s  (%s, %d row%s)"
             % (theirs, where, committed["rows"], plural)]
    if not named:
        lines.append("    NOTE the committed report carries no assembler value, "
                     "which is a report from before the column existed. This run "
                     "used %s, and that agrees with nothing rather than with it."
                     % bare)
        return lines, True
    if len(named) > 1:
        lines.append("    NOTE the committed report names %d different assemblers, "
                     "so there is no single answer to compare against and no "
                     "agreement is established." % len(named))
        return lines, True
    empty = committed["assemblers"].get("", 0)
    if empty:
        lines.append("    NOTE %d committed row(s) carry an empty assembler cell, so "
                     "the value above does not describe the whole report." % empty)
    if version == "unknown":
        lines.append("    NOTE this run's version could not be read from sdas8051, so "
                     "the two are NOT known to agree: an unread version has "
                     "established nothing.")
        return lines, True
    theirs = sorted(named)[0]
    if bare == theirs:
        lines.append("    the committed report and this run used the same assembler")
        return lines, False
    lines.append("    NOTE the two differ: %s against %s." % (bare, theirs))
    lines.append("      Which forms an assembler can express decides the "
                 "match/partial/assembler-gap/listing-gap")
    lines.append("      split, so a different ASxxxx is expected to move it; "
                 "`mismatch` is the outcome")
    lines.append("      the firmware arbitrates and the one worth watching. "
                 "Reported, not failed on:")
    lines.append("      ec/ghidra/README.md has why.")
    return lines, True


def compare_tally(results, tally, committed, limited=False):
    """This run's tally beside the committed one. -> (lines, moved, deltas).

    `moved` is [(program, addr, name, this outcome, committed outcome)] and
    `deltas` is [(outcome, this, committed, signed)], both over every category
    either side has and neither capped. They come back alongside the lines so
    `--self-test` can assert on the comparison rather than on the wording a
    reader happens to be shown -- and the wording is asserted on too, because a
    line that fails to name the row it is about is the defect this block exists
    to prevent. `compare_digests()` is the in-repo shape for both halves.

    The lines say what differs and never why. "9 rows went from assembler-gap to
    match" is a measurement. "the assembler got better" is not, and nothing here
    can support it: two ASxxxx builds are two different things being measured,
    which of them is right is a question about the disassembly, and this
    function has the firmware bytes, two tallies and nothing else.

    `limited` is a `--limit` run. The committed tally is still printed, because
    it is what the reader came to see, but nothing is compared against it: 40
    rows are not a disagreement with 2,705, and a comparison that printed
    deltas for one would be forty lines of noise teaching the reader to skip the
    block."""
    if committed is None:
        return (["  nothing to compare against: there is no committed report at %s"
                 % os.path.relpath(REPORT, REPO)], [], [])
    where = os.path.relpath(REPORT, REPO)
    counts = committed["tally"]
    mine, mine_residual = split_tally(tally)
    categories = [o for o, _ in mine + mine_residual]
    categories += [o for o in sorted(counts) if o not in categories]
    deltas = [(o, tally.get(o, 0), counts.get(o, 0),
               tally.get(o, 0) - counts.get(o, 0)) for o in categories]

    if limited:
        theirs, residual = split_tally(counts)
        return (["  --limit: this run covered %d of the committed report's %d rows, so"
                 % (len(results), committed["rows"]),
                 "  the tally below is a reference and not a comparison, and a "
                 "difference here would not mean one.",
                 "    committed report: %s (of %d)"
                 % (", ".join("%d %s" % (n, o) for o, n in theirs + residual),
                    committed["rows"])], [], [])

    def cell_line(label, here, cells):
        there = sum(c for c in cells if c is not None)
        unreadable = sum(1 for c in cells if c is None)
        line = "    %-20s %9d %10d" % (label, here, there)
        if here != there:
            line += "  %+d" % (here - there)
        if unreadable:
            line += ("  (%d of %d committed cell(s) do not hold an integer; that "
                     "total is over the rest)" % (unreadable, len(cells)))
        return line

    lines = ["", "  compared against the committed report (%s):" % where,
             "    %-20s %9s %10s" % ("outcome", "this run", "committed")]
    for outcome, here, there, delta in deltas:
        line = "    %-20s %9d %10d" % (outcome, here, there)
        if delta:
            line += "  %+d" % delta
        lines.append(line)
    lines.append("    %-20s %9d %10d"
                 % ("rows", len(results), committed["rows"]))
    lines.append(cell_line("instructions checked",
                           sum(r[4] for r in results), committed["checked"]))
    lines.append(cell_line("instructions unchecked",
                           sum(r[5] for r in results), committed["unchecked"]))
    # The bytes this run actually compared, against the committed report's
    # instruction count. There is nothing to compare it *to* -- the column does
    # not exist yet, and reassembly_checked_bound.py derives the ceiling the
    # committed file does support -- so this prints the run's own figure beside
    # the number it is routinely mistaken for rather than diffing it.
    lines.append("    %-20s %9d %10s" % ("bytes compared", sum(r[3] for r in results),
                                         "no column"))

    moved = []
    for row, outcome, _detail, _b, _c, _s, _d, _a in results:
        was = committed["by_key"].get(row["addr"] + "|" + row["program"])
        if was is None:
            moved.append((row["program"], row["addr"], row["name"], outcome,
                          "no row in the committed report"))
        elif was.get("outcome") != outcome:
            moved.append((row["program"], row["addr"], row["name"], outcome,
                          was.get("outcome") or "(blank)"))
    if not moved:
        lines.append("\n  moved since the committed report: nothing")
    else:
        lines.append("\n  moved since the committed report: %d row(s)" % len(moved))
        for prog, addr, name, here, there in moved[:MOVED_CAP]:
            lines.append("    %s %s %s: %s here, %s in %s"
                         % (prog, addr, name, here, there, where))
        if len(moved) > MOVED_CAP:
            lines.append("    ... and %d more" % (len(moved) - MOVED_CAP))
    return lines, moved, deltas


# The one command that resolves a digest disagreement: a changed listing has to
# be re-reported, and re-reporting is the re-encode. Named once so the failure
# message and --add-digest-column cannot drift into pointing at different things.
REPORT_COMMAND = (
    "SDAS8051=$(nix build nixpkgs#sdcc && echo $out/bin/sdas8051) "
    "python3 ec/tools/verify_reassembly.py --work /tmp/ec --report")

# The other one, and the contrast with the line above is the whole of why a
# name may be re-copied when a digest may not. A digest disagreement means the
# listing text moved and the re-encode is the only thing that re-establishes it;
# a name disagreement means a copy of the index went stale, and the index is
# still there. Named once so the failure message and the flag that answers it
# cannot drift into pointing at different things.
NAME_COMMAND = "python3 ec/tools/verify_reassembly.py --refresh-name-column"


def run_status(tally):
    """The full run's exit status: status_for()'s answer, and nothing else.

    The measured half is unchanged and deliberate. Three things this run reports
    are not adjudicated here: a warning that its assembler differs from the one
    the committed report was measured with, a category that moved since, and a
    `listing-gap`. All three are measurements, and none is actionable by whoever
    is not watching -- a branch that re-reported the listings and has not
    committed its CSV yet moves the tally legitimately, and this tool cannot tell
    that from a regression. A `listing-gap` is the same shape: the row says the
    listing it read had no entry at an address, and what that is about -- a build
    that cannot express the form, a listing this build does not print, or a
    `read_lst` regex that cannot see what it did -- is settled by the pinned build
    rather than by any runner here. Failing a scheduled run on it would be noise,
    not a gate.

    The unmeasured half is the opposite of that, and it is the same for all five
    outcomes outside OUTCOMES: `assembler-error`, `error`, `missing-listing`,
    `empty-listing` and `skipped` all fail, because none of them is a
    measurement at all. `unmeasured()` is the one place that decision is
    written; `check()` reads the same predicate over a report, and
    `write_report()` refuses to write a run carrying one. The policy and the
    argument for it are in
    docs/findings/reassembly-unmeasured-row-policy.md.

    What fails is therefore the one outcome the firmware arbitrates, plus every
    row with nothing behind it.
    """
    return status_for(tally)


def check():
    """No assembler required.

    Four things. First, every byte of every listing against the firmware
    image, which covers the instructions the assembler cannot express and runs
    anywhere. Second, that the committed reassembly report still describes the
    committed listings: same functions, same outcomes. Third, that no listing's
    text has moved since the report measured it, which is what a mnemonic or
    operand edit leaves the byte column unable to see. Fourth, that the report's
    copy of each function's name still matches the one the listing index holds.
    `report_composition()` rides with the first of them and prints what the
    instructions the assembler cannot express are made of, beside the count;
    see the module docstring and that function for what it asserts.

    The first two are about the claim on file agreeing with the export; the
    third is about the export not having changed underneath it; the fourth is
    about a copied cell that nothing else in this file watches, and it is the
    weakest of the four because a name is a judgement rather than a
    measurement -- it holds the copy, not the judgement. What none of them can
    do is verify the disassembly, and this function does not say it does:
    verifying is the re-encode, and that is the deep tier.

    The summary it prints counts every outcome, and a row outside OUTCOMES fails
    here exactly as it fails a full run, because `unmeasured()` is the one
    predicate both read. A committed row saying `error` claims a re-encode that
    did not happen; that is a false claim about coverage, where a `mismatch` is
    a disagreement about bytes."""
    ok = True
    bytes_ok, n_insns, n_bad, digests, composition = check_listing_bytes()
    ok = ok and bytes_ok
    if not os.path.isfile(REPORT):
        print("  FAIL no reassembly report at %s; run verify_reassembly.py"
              % os.path.relpath(REPORT, REPO))
        return 1
    report = {r["addr"] + "|" + r["program"]: r
              for r in csv.DictReader(open(REPORT, newline=""))}
    ok = report_composition(composition, report) and ok
    live, names = listing_index_keys()
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
    # Every outcome, in one order, so the line adds up to the row count it
    # prints. It said 2,632 of 2,705 until `partial` was counted, which is the
    # whole defect: `partial` is an outcome this file's own check_one() returns
    # and §14e and §14f both quote, and a summary that omits it understates the
    # number of functions that are not fully verified.
    ordered, residual = split_tally(report_tally(report.values()))
    print("  reassembly report: %s (of %d)"
          % (", ".join("%d %s" % (n, o) for o, n in ordered), len(report)))
    if residual:
        # Named, and failed on. check_one() can return `assembler-error`,
        # `error`, `missing-listing`, `empty-listing` and `skipped`, and none of
        # them is a measurement: a committed row carrying one claims a re-encode
        # that did not happen, which is a false claim about coverage rather than
        # a disagreement about bytes. `unmeasured()` is the predicate run_status()
        # reads over the same tally, so a residual cannot mean one thing to a run
        # and another to the report it wrote; the settlement and the argument for
        # it are in docs/findings/reassembly-unmeasured-row-policy.md.
        print("  and %s, which are outside OUTCOMES"
              % ", ".join("%d %s" % (n, o) for o, n in residual))
        for outcome, n in residual:
            print("  FAIL %d %s row(s): %s"
                  % (n, outcome, unmeasured_reason(outcome)))
        ok = False
    mism = dict(ordered)["mismatch"]
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
    # The name, against the index it was copied from. Its own line rather than a
    # fifth clause of the digest line above, because the two need different
    # remedies and merging them would tell a reader to re-report for a stale
    # name, which is the one thing that cannot fix it here.
    n_compared, name_bad = compare_names(report, names, live)
    print("  listing names: %d compared against the listing index, "
          "%d disagreement(s)" % (n_compared, len(name_bad)))
    for _key, prog, addr, name, rel, why in name_bad[:MOVED_CAP]:
        print("  FAIL %s %s %s (%s): %s" % (prog, addr, name, rel, why))
    if len(name_bad) > MOVED_CAP:
        print("  ... and %d more" % (len(name_bad) - MOVED_CAP))
    if name_bad:
        print("       A name is a copy of what the listing index holds, so this "
              "is stale rather than\n       wrong, and copying it across is the "
              "whole repair:\n"
              "         %s\n"
              "       It rewrites that one column and proves from the written "
              "file that no other cell\n       moved, so it cannot be used to "
              "re-arm a digest, an outcome or an assembler\n       version. It "
              "asserts that the report and the index agree about the name; it "
              "does\n       not check the name is a good one."
              % NAME_COMMAND)
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
    ok, _checked, bad, digests, _composition = check_listing_bytes()
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


def read_report(path):
    """-> (raw bytes, fieldnames, rows) for a report, read once.

    The bytes as well as the rows because the caller needs something to put back
    if its own guard fails: a writer that has decided the file is worse than it
    found it has to be able to leave it exactly as it was, and a re-serialisation
    of the rows it read is not that.

    Not `committed_report()`, and the difference is what each is for. That one
    derives the tallies and the assembler census the run comparison prints, and
    answers None for a file that is not there; this one is the raw parse a writer
    needs before it has changed anything, so it has the header and the bytes.
    """
    with open(path, "rb") as f:
        raw = f.read()
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return raw, list(reader.fieldnames or []), list(reader)


def only_name_moved(before, after):
    """-> (True, "") if the second read of a report differs from the first in no
    cell but `name`. `before` and `after` are (fieldnames, rows) pairs.

    The header and the row order are compared too, because a writer that
    reordered rows, renamed a column or dropped one has changed the report even
    though no cell differs from the row it was read as.

    This is the guard, and it is the reason a second writer of the committed
    report is safe at all: the comparison is between two reads of the *file*, not
    between the rows that were about to be serialised and themselves, so a column
    that moved, a header that moved or a row that came back with a different set
    of columns fails here rather than agreeing with itself. It compares parsed
    cells, so it does not see a difference in how those cells were written: a
    quoting rule or a line terminator that parses to the same cells passes it.
    """
    was_header, was_rows = before
    now_header, now_rows = after
    if was_header != now_header:
        return False, ("the header moved: %r became %r"
                       % (was_header, now_header))
    if len(was_rows) != len(now_rows):
        return False, ("%d row(s) before, %d after"
                       % (len(was_rows), len(now_rows)))
    for i, (was, now) in enumerate(zip(was_rows, now_rows)):
        if list(was) != list(now):
            return False, ("row %d has a different set of columns" % i)
        for column in was:
            if column == "name":
                continue
            if was[column] != now[column]:
                return False, ("row %d, %s column: %r became %r"
                               % (i, column, was[column], now[column]))
    return True, ""


def refresh_name_column(path=REPORT, index_path=LISTING_INDEX):
    """Copy the listing index's `name` into the report, and touch nothing else.

    **Repeatable, where `--add-digest-column` is one-shot, and the difference is
    the argument rather than a convenience.** A digest records an observation; a
    re-copied one re-arms a detector while verifying nothing, so the only writer
    of a digest has to be the run that measures it. A name is a copy of a value
    the index holds and this file can read back, so re-copying it re-establishes
    agreement and asserts nothing -- which is exactly what the check is for.

    What it therefore cannot do, and does not try to: compute a measurement. No
    outcome, no digest, no instructions_* cell and no assembler version is
    recomputed here; they are read and copied through, and the read-back below
    fails the run if any of them moved. That is what keeps this path out of the
    hazard `refuses_committed_report()` names -- a report written by a different
    assembler -- and least of all out of the rows whose `assembler` cell
    `docs/findings/thunk-prefix-collision.md` says is already unexplained.

    The key sets have to be identical in both directions before anything is
    written. Copying by key is otherwise a way to invent a name for a row with no
    listing, and to leave an index row with no report row unmentioned, and both
    of those are things `--check` already reports -- this must not paper over.
    """
    rel = os.path.relpath(path, REPO)
    original, fieldnames, rows = read_report(path)
    # Copied before anything is changed, so the read-back below compares the file
    # as it was found against the file as it was left rather than against the
    # dicts in between -- which is the comparison that could agree with itself.
    before_rows = [dict(r) for r in rows]
    if "name" not in fieldnames:
        print("  %s has no name column; nothing to refresh.\n"
              "     A report from before the column existed is not something to "
              "add one to by\n     hand; re-report it instead:\n       %s"
              % (rel, REPORT_COMMAND))
        return 1
    live, names = listing_index_keys(index_path)
    keys = [r["addr"] + "|" + r["program"] for r in rows]
    have = set(keys)
    dupes = sorted(k for k, n in collections.Counter(keys).items() if n > 1)
    if dupes:
        # A duplicate would make "this row" ambiguous about which row a name is
        # for, and a dict built over the keys would keep one of the two silently.
        print("  refusing to refresh %s: %d (program, addr) appear more than "
              "once\n  (first: %s). Which row a name belongs to has to be "
              "unambiguous." % (rel, len(dupes), dupes[0]))
        return 1
    orphans = [k for k in keys if k not in names]
    if orphans:
        print("  refusing to refresh %s: %d report row(s) have no row in the\n"
              "  listing index (first: %s). A name cannot be copied for a "
              "function no\n  listing names, and --check has already said the "
              "report is stale." % (rel, len(orphans), orphans[0]))
        return 1
    unlisted = [k for k in names if k not in have]
    if unlisted:
        print("  refusing to refresh %s: %d listing(s) have no row in the report "
              "(first:\n  %s). --check has already said the report predates this "
              "export; a name\n  written now would leave it looking current."
              % (rel, len(unlisted), live.get(unlisted[0], unlisted[0])))
        return 1
    moved = []
    for r in rows:
        want = names[r["addr"] + "|" + r["program"]]
        if (r.get("name") or "").strip() != want:
            moved.append((r["program"], r["addr"], (r.get("name") or "").strip(),
                          want))
            r["name"] = want
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n",
                           restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    held, why = only_name_moved((fieldnames, before_rows), read_report(path)[1:])
    if not held:
        with open(path, "wb") as f:
            f.write(original)
        print("  restored %s: the rewrite changed more than the name column "
              "(%s).\n  A writer that cannot say which column it touched is not "
              "one to leave in place." % (rel, why))
        return 1
    print("  refreshed the name column of %d row(s) in %s." % (len(moved), rel))
    for prog, addr, was, want in moved[:MOVED_CAP]:
        print("    %s %s: %s -> %s" % (prog, addr, was, want))
    if len(moved) > MOVED_CAP:
        print("    ... and %d more" % (len(moved) - MOVED_CAP))
    print("\n  Every other cell was read back from the written file and is "
          "unchanged, so no\n  outcome, digest, instruction count or assembler "
          "version was touched. Asserting: the\n  report and the listing index "
          "now agree about what each function is called.\n  Not asserting: that "
          "the name is a good one -- a name that agrees with the index is a "
          "name\n  the index wrote. Re-reporting is what re-measures anything:\n"
          "    %s" % REPORT_COMMAND)
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
# --report's. Every job that runs `.github/scripts/agent-gates.sh` -- ci.yml's
# `gates` and the agent stages' `implement`, `fix` and `resolve` -- checks out
# with `fetch-depth: 0` and can run it. ci.yml's other checkout, its `workflows`
# job, is the default-depth one and runs actionlint and zizmor only, so it never
# reaches the mode. The four are re-derived from the committed workflows by
# `check_history_checkouts.py`, and see docs/agent-pipeline.md.
HISTORY_REQUIREMENT = (
    "  This mode answers from the repository's history, so it needs a full\n"
    "  clone: `git clone` without --depth, or `git fetch --unshallow` in one\n"
    "  that is shallow. A default-depth checkout -- actions/checkout's default,\n"
    "  which is what ci.yml's `workflows` job uses, though that job runs no\n"
    "  history reader -- has neither revision, and a mode that carried on\n"
    "  anyway would be auditing whatever happened to be checked out.")


def _git(*args, repo=REPO):
    """git, run against `repo` whatever the cwd is.

    The root is a parameter and not the constant so `--self-test` can drive the
    mode at a repository it builds, and so `--repo` can point it at a fork or a
    worktree. It is deliberately not an injected `git_lines`: a fake would have
    answered every known answer below, and the distinction that matters most
    here -- `None` (the command did not run) against `[]` (it ran and said
    nothing) -- is one only a real git can draw.
    """
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True)


def git_lines(*args, repo=REPO):
    """-> (lines, None) for git's non-empty output lines, or (None, why).

    None rather than an empty list because an empty answer and a command that
    did not run are the two things this mode most needs to tell apart: every
    check it makes is "git said nothing", so a git that failed would read as a
    pass on all of them.
    """
    try:
        r = _git(*args, repo=repo)
    except OSError as exc:
        return None, "git could not be run: %s" % exc
    if r.returncode != 0:
        return None, r.stderr.strip() or ("git exited %d" % r.returncode)
    return [ln for ln in r.stdout.splitlines() if ln.strip()], None


def resolve_revision(rev, repo=REPO):
    """-> the commit sha `rev` names in that clone, or None if it has no such
    commit. `^{commit}` so a tag or a branch name is measured, not a path."""
    lines, _why = git_lines("rev-parse", "--verify", "--quiet",
                            rev + "^{commit}", repo=repo)
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


def verify_provenance(base, migration, listings_from=None, repo=REPO):
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

    `repo` is the clone the revisions are resolved in, and every check below is
    a check against it: a window in one repository's history says nothing about
    another's. `--self-test` builds a small one and drives all of this at it, so
    each way out of here has an answer a change to the code above can be caught
    against.
    """
    base_sha = resolve_revision(base, repo=repo)
    mig_sha = resolve_revision(migration, repo=repo)
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
    from_sha = resolve_revision(from_rev, repo=repo)
    if not from_sha:
        print("  FAIL cannot resolve --listings-from %r in this clone."
              % from_rev)
        print(HISTORY_REQUIREMENT)
        return 1
    print("  revisions: listings written %s..%s, migration %s..%s"
          % (from_sha[:7], base_sha[:7], base_sha[:7], mig_sha[:7]))

    control, why = git_lines("diff", "--name-only",
                             "%s..%s" % (from_sha, base_sha), "--",
                             LISTING_PATHSPEC, repo=repo)
    if control is None:
        print("  FAIL the control diff did not run: %s" % why)
        return 1
    moved, why = git_lines("diff", "--name-only",
                           "%s..%s" % (base_sha, mig_sha), "--",
                           LISTING_PATHSPEC, repo=repo)
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
        lines, why = git_lines("show", "%s:%s" % (sha, REPORT_REL), repo=repo)
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

    # The migration must add the column, not drop it or leave it absent. The base
    # must not have it, and every digest cell in the migration must be non-empty.
    if has_digest[0]:
        print("  FAIL the base already has listing_digest: the column is not new, "
              "so this is not a migration that added it.")
        return 1
    if not has_digest[1]:
        print("  FAIL the migration does not have listing_digest: the column is "
              "absent or was removed.")
        return 1

    # Check that all digest cells are non-empty and valid in the migration report.
    # A valid digest is 16 hex characters (from digest_of() which returns
    # hexdigest()[:16]). Empty or non-hex cells fail.
    import io
    import re
    mig_reader = csv.DictReader(io.StringIO(reports["migration"]))
    invalid_digests = []
    for row in mig_reader:
        digest = row.get("listing_digest", "").strip()
        # Valid digest must be 16 hex characters.
        if not digest or not re.fullmatch(r"[0-9a-fA-F]{16}", digest):
            invalid_digests.append((row.get("program"), row.get("addr")))
    if invalid_digests:
        print("  FAIL the migration's listing_digest column is empty or invalid on "
              "%d row(s):" % len(invalid_digests))
        for prog, addr in invalid_digests[:20]:
            print("    %s %s" % (prog, addr))
        if len(invalid_digests) > 20:
            print("    ... and %d more" % (len(invalid_digests) - 20))
        return 1

    touched, why = git_lines("log", "--name-only", "--format=",
                             "%s..%s" % (base_sha, mig_sha), "--",
                             "ec/decompiled", repo=repo)
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


# The committed report's columns, less `listing_digest` -- the set
# `add_digest_column()` adds that one to and beside. Written out rather than
# read from `REPORT`, so the fixture below is a pair of small reports compared
# with `compare_provenance()` and nothing more: a fixture whose shape came from
# the committed file would make every case here depend on the corpus it is a
# check for.
FIXTURE_FIELDS = ["program", "addr", "name", "outcome", "instructions_checked",
                  "instructions_unchecked", "detail", "assembler"]


def build_provenance_fixture(root):
    """A small repository carrying one digest migration's shape.
    -> {commit name: sha}, in the order the commits are made.

    Each commit is named for what it *is* rather than for what it holds, so a
    case reads `--migration moved` and not a sha a reader has to look up.
    `seed` is a revision the `--listings-from` control can name that is not the
    base itself, `listings` is the window that last wrote them, `base` is the
    last full `--report`, `migration` adds the column and a `.c` beside it,
    `recounted` touches one cell under the column, `moved` edits a listing, and
    `gone` is the revision the report cannot be read at.

    Under `tempfile` and never in the working tree, for the reason
    `test_verify_provenance_clone_depth.py` gives: `run-tests.sh` prunes `.git/`,
    `.claude/` and `vendor/` when it counts, and `check_testdata_index.py` and
    `census_test_line_pins.py` walk the tree, so a repository in the working
    directory is a second checkout for all three to trip over.

    Three things in here are traps rather than decoration, and each one answers
    a case silently and wrongly if it is got wrong:

      - the listings sit one level under `ec/decompiled/`, as the committed
        ones do. `LISTING_PATHSPEC` is `ec/decompiled/**/*.asm`, and an `.asm`
        written directly in `ec/decompiled/` would fire the control branch for a
        reason that has nothing to do with the case under test;
      - the report's `listing_digest` cells are this tool's own `digest_of()`
        over this tool's own listings, so the fixture is the shape a real
        migration has rather than made-up hex. No cell is asserted by value
        anywhere; what is asserted is the exit status and the printed reason;
      - every commit carries its own identity and `commit.gpgsign=false`, so a
        runner with no global `user.name` and one that signs everything both
        work, and no config from the repository this runs in leaks into the
        fixture.
    """
    import io

    def git(*args):
        proc = subprocess.run(["git", "-C", root] + list(args),
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("fixture: `git %s` exited %d: %s"
                               % (" ".join(args), proc.returncode,
                                  proc.stderr.strip()))
        return proc.stdout

    def commit(message):
        git("add", "-A")
        git("-c", "user.name=verify_reassembly self-test",
            "-c", "user.email=self-test@example.invalid",
            "-c", "commit.gpgsign=false",
            "-c", "core.autocrlf=false", "commit", "-q", "-m", message)
        return git("rev-parse", "HEAD").strip()

    def write(rel, text):
        path = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as f:
            f.write(text)
        return path

    def report_text(rows, fields):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        return buf.getvalue()

    git("init", "-q")
    shas = {}
    # Not a listing and not the report, so the control has an ancestor to name
    # that is not the base itself -- which is the point of `--listings-from`
    # being a flag rather than a `^`.
    write("docs/seed.txt", "not a listing, and not the report.\n")
    shas["seed"] = commit("seed: a revision no pathspec in this mode matches")

    # The committed `.asm` layout, one level down, with disjoint addresses: the
    # mode compares paths and reports, never addresses, but a reader of this
    # function should not have to wonder.
    first = ("; bank0 0040 selftest_first  [named]\n"
             "0040  74 12 -     mov   a,#0x12\n"
             "0042  00  -  -    nop\n")
    second = ("; bank0 0042 selftest_second  [named]\n"
              "0042  90 00 47    mov   dptr,#0x0047\n"
              "0045  22  -  -    ret\n")
    first_path = write("ec/decompiled/bank0/0040.asm", first)
    second_path = write("ec/decompiled/bank0/0042.asm", second)
    shas["listings"] = commit("listings: the window that last wrote them")

    base_rows = [{"program": "bank0", "addr": "0040", "name": "selftest_first",
                  "outcome": "match", "instructions_checked": "2",
                  "instructions_unchecked": "0", "detail": "",
                  "assembler": "sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14"},
                 {"program": "bank0", "addr": "0042", "name": "selftest_second",
                  "outcome": "match", "instructions_checked": "2",
                  "instructions_unchecked": "0", "detail": "",
                  "assembler": "sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14"}]
    write(REPORT_REL, report_text(base_rows, FIXTURE_FIELDS))
    shas["base"] = commit("base: the last full --report")

    # The column where add_digest_column() puts it, and the cells its own
    # digest_of() computes over the two listings above.
    column_at = FIXTURE_FIELDS.index("outcome") + 1
    mig_fields = (FIXTURE_FIELDS[:column_at] + ["listing_digest"]
                  + FIXTURE_FIELDS[column_at:])
    mig_rows = [dict(r, listing_digest=digest_of(parse_listing(path)))
                for r, path in zip(base_rows, (first_path, second_path))]
    write(REPORT_REL, report_text(mig_rows, mig_fields))
    # A `.c` beside the column, because a migration window normally contains
    # one and the digest is over the parsed `.asm` stream, so it must not move
    # one. That is the supporting view, and the mode prints it as such.
    write("ec/decompiled/bank0/0EA2.c",
          "/* A decompiled C export. The digest is over the .asm instruction\n"
          "   stream, so a window that contains one of these has still moved no\n"
          "   listing. */\n")
    shas["migration"] = commit("migration: add listing_digest, and a .c beside it")

    # Four windows with broken migrations: column added but empty, column added
    # but garbage, column absent, or column removed from a base that had it.
    # These test the branch that refuses migrations that don't add the column
    # correctly.
    empty_col_rows = [dict(r, listing_digest="") for r in mig_rows]
    write(REPORT_REL, report_text(empty_col_rows, mig_fields))
    shas["empty-col"] = commit("empty-col: migration adds column but every cell empty")

    # Garbage that includes non-hex characters, so it's not a valid digest.
    garbage_col_rows = [dict(r, listing_digest="NOTAHEXDIGEST!")
                        for r in mig_rows]
    write(REPORT_REL, report_text(garbage_col_rows, mig_fields))
    shas["garbage-col"] = commit("garbage-col: migration adds column but every "
                                "cell garbage")

    # Migration skips the column entirely. Write rows without listing_digest.
    no_col_rows = [dict((k, v) for k, v in r.items() if k != "listing_digest")
                   for r in mig_rows]
    write(REPORT_REL, report_text(no_col_rows, FIXTURE_FIELDS))
    shas["no-col"] = commit("no-col: migration skips the listing_digest column")

    # Base has the column, migration removes it (reverting the migration).
    base_with_col_rows = [dict(r, listing_digest=digest_of(parse_listing(path)))
                          for r, path in zip(base_rows, (first_path, second_path))]
    write(REPORT_REL, report_text(base_with_col_rows, mig_fields))
    shas["base-has-col"] = commit("base-has-col: base has the column")
    # Now remove it in the next commit. Strip listing_digest from rows.
    no_digest_rows = [dict((k, v) for k, v in r.items() if k != "listing_digest")
                      for r in base_with_col_rows]
    write(REPORT_REL, report_text(no_digest_rows, FIXTURE_FIELDS))
    shas["base-has-col-remove"] = commit("base-has-col-remove: migration removes "
                                         "listing_digest")

    # The three windows that are wrong in different ways. They are one line
    # rather than three branches because each case names the window it reads,
    # and the two that would otherwise be caught by an earlier check say so by
    # naming a different base -- see the cases passing at("moved", "gone") and
    # at("listings", "migration").
    write(REPORT_REL, report_text([dict(mig_rows[0],
                                         instructions_checked="1"),
                                   mig_rows[1]], mig_fields))
    shas["recounted"] = commit("recounted: one cell under the column")

    # One mnemonic, same byte column, same length: an edit to the text rather
    # than to the bytes, which is the change the digest column exists to catch.
    write("ec/decompiled/bank0/0040.asm", first.replace("nop", "ret"))
    shas["moved"] = commit("moved: a listing moved under the migration")

    os.remove(os.path.join(root, *REPORT_REL.split("/")))
    shas["gone"] = commit("gone: the report is not in this revision")
    return shas


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
    assert_that("ajmp" not in GAP_MNEMONICS and "acall" not in GAP_MNEMONICS,
                "ajmp/acall are no longer gaps; they are arbitrated via disasm8051.py")
    assert_that(to_sdas("mov", "dptr,#0x1234", 0x0040) is not None,
                "mov dptr,#imm translates")
    assert_that(to_sdas("djnz", "a,0x0014", 0x0040) is None,
                "a known assembler gap returns None rather than a bad line")
    # The refusal composition, on a synthetic listing rather than on this
    # repository's own -- so what is asserted is the claim (one of each form
    # lands under its own rule, and the rules this listing does not exercise
    # are the ones with no entry) rather than a census that moves on the next
    # export. --check prints the live version beside the report's own total.
    # `clr bit` and `CJNE`-on-direct are here precisely because the committed
    # image exercises neither: a rule that cannot be exercised on the image is
    # still a rule, and a change to one of them has to move a test rather than
    # silently change which rows --check would say have no instance.
    # Note: ajmp and acall are no longer gaps; they are arbitrated via
    # disasm8051.py, so they should not appear in this composition.
    forms = parse_listing_str(
        "; forms to_sdas() declines (not including ajmp/acall which are now arbitrated)\n"
        "0044  92 d5 -     mov   0xd5, CY\n"
        "0046  b2 d5 -     cpl   0xd5\n"
        "0048  c1 d5 -     clr   0xd5\n"
        "004a  b5 30 10 08 cjne  0x30,#0x10,0x0054\n"
        "004e  d5 e0 e5    djnz  A, 0xa581\n"
        "0051  74 12 -     mov   a,#0x12\n"
        "0053  22  -  -    ret\n")
    got, unexplained = refusal_composition(forms)
    assert_that(got == {("BIT_UNSUPPORTED 0x92", "mov"): 1,
                        ("BIT_UNSUPPORTED 0xB2", "cpl"): 1,
                        ("BIT_UNSUPPORTED 0xC1", "clr"): 1,
                        ("CJNE direct operand", "cjne"): 1,
                        ('GAP_FORMS "djnz a,"', "djnz"): 1}
                and not unexplained,
                "the composition of a listing holding one of each remaining form: %r"
                % sorted(got.items()))
    # The complementary half: everything the tool can refuse and this listing
    # did not is exactly the carry-with-immediate forms and the out-of-range
    # branch, so a rule added to a collection and not taught here is visible as
    # a test failure rather than as a number --check prints.
    assert_that([rule for rule in refusal_rules()
                if rule not in {reason for reason, _mnem in got}]
                == ['GAP_FORMS "addc c,#"', 'GAP_FORMS "anl c,#"',
                    'GAP_FORMS "mov c,#"', 'GAP_FORMS "orl c,#"',
                    'GAP_FORMS "subb c,#"', 'GAP_FORMS "xrl c,#"',
                    BRANCH_RANGE],
                "and the refusal rules that listing does not reach are the "
                "carry-with-immediate forms and the branch range")
    # `da A` is translated rather than declined, so it is a rule
    # refusal_reason() can name and not one refusal_rules() enumerates. Both
    # halves are asserted, because conflating them would make the "rules with
    # no instance" line --check prints claim the reserved no-op is a gap.
    assert_that(refusal_reason("a", "", 0x0040, 1, 0xD4, "d4") == DA_A
                and to_sdas("a", "", pc=0x0040, size=1, opcode=0xD4,
                            hexbytes="d4") == "\tda\ta",
                "the reserved `da A` is named by refusal_reason() and "
                "translated by to_sdas(), which is why it is not a rule")
    # The one form refusal_reason() must not invent a reason for.
    assert_that(refusal_reason("sjmp", "label", 0x0040, 2, 0x80, "800a") is None,
                "an exclusion nothing explains returns None rather than a "
                "guess, so the caller fails instead of guessing")
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
    assert_that(to_sdas("ajmp", "0x845d", pc=0x8044, size=2, opcode=0x81, hexbytes="815d")
                == "\tajmp\t0x845d",
                "ajmp is decoded via disasm8051.paged_target(): 0x81 & 0xE0 = 0x80, "
                "(0x8044+2) & 0xF800 = 0x8000, so (0x8000 | 0x400 | 0x5D) = 0x845D")
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

    # The guard on the committed report's one writer. Asserted with a path
    # relative to the repo as well as the absolute one, because the two reach
    # the same file and a guard that only catches one of them catches neither
    # once someone types the other.
    #
    # Joined onto REPO rather than left relative, deliberately. A bare
    # "ec/ghidra/reassembly.csv" resolves against the *process* cwd, so from
    # anywhere but the repo root it names some other file -- and this
    # assertion, run from there, would write a header-only report to it
    # before failing. A test for "the guard stops the write" that performs the
    # write is worse than no test.
    for label, cand in (("absolute", REPORT),
                        ("repo-relative", os.path.join(REPO, "ec", "ghidra",
                                                       "reassembly.csv"))):
        assert_that(refuses_committed_report(cand) is True
                    and emit_csv([], "sdas8051", cand) == 1,
                    "--emit-csv refuses the committed report (%s)" % label)
    fd, epath = tempfile.mkstemp(prefix="emit-selftest-", suffix=".csv")
    os.close(fd)
    try:
        assert_that(emit_csv([], "sdas8051", epath) == 0
                    and os.path.getsize(epath) > 0,
                    "--emit-csv writes to any other path")
        # The hardlink, which is the case a realpath-only guard misses: same
        # inode under a different name, so open(path, "w") truncates the
        # committed report exactly as writing REPORT would. Linked to REPORT
        # rather than to two scratch files, or samefile would be true of any
        # pair and the assertion would prove nothing. The unlink in the
        # finally removes the link, not the report.
        os.remove(epath)
        os.link(REPORT, epath)
        assert_that(refuses_committed_report(epath) is True,
                    "--emit-csv refuses a hardlink to the committed report")
    finally:
        if os.path.exists(epath):
            os.remove(epath)

    # The flag combinations --emit-csv cannot be honoured with, driven through
    # main() rather than through refuses_emit_csv(), because main() is where the
    # flag combination is decided and a refusal the dispatch steps over is the
    # failure this is about. Three things per case, and each is load-bearing:
    #
    #   the status is 2, which the run could also reach by finding no assembler,
    #     so it is the sentence below that says which refusal answered;
    #   the destination does not exist afterwards -- a different one per case,
    #     under a scratch directory this loop owns and removes -- so the guard
    #     is observed to stop the write rather than to be believed to. A test
    #     that performs the write it is about is worse than no test;
    #   and the printed sentence names the offending flag, so a guard that fires
    #     for some other reason, or silently, is not what passes.
    #
    # argv is patched rather than main() given a list, because main() builds its
    # own parser from sys.argv and taking a list would be a second entry point.
    def main_says(argv):
        """-> (status, stdout) for one argument vector, argv[0] filled in."""
        import contextlib
        import io
        buf = io.StringIO()
        saved = sys.argv
        sys.argv = ["verify_reassembly.py"] + list(argv)
        try:
            with contextlib.redirect_stdout(buf):
                status = main()
        finally:
            sys.argv = saved
        return status, buf.getvalue()

    no_emit_dir = tempfile.mkdtemp(prefix="emit-refused-")
    try:
        for label, extra, named in (
                ("--check", ["--check"], "--check"),
                ("--self-test", ["--self-test"], "--self-test"),
                ("--add-digest-column", ["--add-digest-column"],
                 "--add-digest-column"),
                # Revisions that resolve to nothing, on purpose: this case must
                # be refused by the guard rather than run and reach its own
                # history failure, which is the status-1 path a reader would
                # otherwise be told to go and fix by fetching a full clone.
                ("--verify-provenance", ["--verify-provenance",
                                         "--base", "no-such-revision-a",
                                         "--migration", "no-such-revision-b"],
                 "--verify-provenance"),
                ("--limit", ["--limit", "40"], "--limit")):
            dest = os.path.join(no_emit_dir, "%s.csv" % label.strip("-"))
            status, said = main_says(["--emit-csv", dest] + extra)
            assert_that(status == 2 and not os.path.exists(dest)
                        and named in said,
                        "--emit-csv is refused with %s (status %r, wrote %s, "
                        "named it: %s)"
                        % (label, status, os.path.exists(dest), named in said))
    finally:
        shutil.rmtree(no_emit_dir, ignore_errors=True)

    # The control, so a guard that refuses everything passes nothing above: --emit-
    # csv set with every other mode off is the whole of what the flag is for, and
    # it must reach the write. The write itself is the case above this one.
    bare = argparse.Namespace(emit_csv="x.csv", limit=None, report=False,
                              work=None, assembler=None, jobs=8,
                              check=False, self_test=False,
                              add_digest_column=False, refresh_name_column=False,
                              verify_provenance=False,
                              base=None, migration=None, listings_from=None)
    assert_that(refuses_emit_csv(bare) is None,
                "--emit-csv alone is honoured: a guard that refuses everything "
                "would pass every case above")
    # --limit 0 is a request for no rows rather than for all of them, and it is
    # the spelling a truthiness test would wave through.
    assert_that(refuses_emit_csv(argparse.Namespace(**dict(
                vars(bare), limit=0))) == ("--limit", "truncates"),
                "--limit 0 is refused too: it is zero rows, not every row")

    # The completeness hold, and the one that matters: NO_RE_ENCODE must be the
    # set of flags main() actually dispatches on before the committed report's
    # own check, so the tuple cannot drift into being a hand-kept list again --
    # which is the shape the bug had. Set equality, both directions, so it can
    # neither miss a mode (one added beside the condition rather than into it)
    # nor name one that does not early-return (a flag listed and never
    # dispatched on).
    #
    # Read from main()'s own source rather than from its flags, because the
    # question is what the dispatch does and not what the parser accepts: a
    # boolean that is accepted and never consulted belongs in neither set.
    # Matched on the `if args.<dest>` token rather than on a line number, so a
    # rewrap does not redden this, and anchored on the `if` so a validation
    # clause that merely mentions a flag -- `if not args.base or not
    # args.migration:` -- is not counted as a mode. Its limit is the mirror:
    # a branch that leads with a negation, `if not args.check and args.report`,
    # is not counted either. That is a conjunction of a listed mode with
    # something else rather than a mode of its own, so nothing is lost here;
    # a branch written that way and needing to be listed wants rewriting.
    import inspect
    dispatch = inspect.getsource(main)
    dispatch = dispatch[:dispatch.index("refuses_committed_report(args.emit_csv)")]
    branches = set(re.findall(r"^\s*if\s+args\.(\w+)\b", dispatch, re.M))
    branches -= {"emit_csv"}
    assert_that(branches == {m.dest for m in NO_RE_ENCODE},
                "every mode main() dispatches on before the emit is in "
                "NO_RE_ENCODE and every entry in it is one main() dispatches "
                "on\n     (main() has %s; NO_RE_ENCODE has %s)"
                % (", ".join("--" + d.replace("_", "-") for d in sorted(branches)),
                   ", ".join(m.spelled for m in NO_RE_ENCODE)))

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


    # The dispatch must never hand two rows that are in flight at the same
    # time the same scratch directory, or they overwrite each other's source
    # and read back each other's listing (docs/findings.md §14g).
    #
    # A race cannot be provoked by running the tool repeatedly and hoping, so
    # the pickup order that provokes it is forced instead: the worker holding
    # the first row is held until the pool has run `jobs` rows past it. Under
    # `dirs[idx % jobs]` that first row and the fifth share a directory, both
    # in flight together; under a per-thread scratch dir they cannot.
    seen, lock, drained = [], threading.Lock(), threading.Event()

    def recording_check(row, image, workdir, sdas_arg):
        with lock:
            first = not seen
            seen.append((threading.current_thread().name, workdir))
            if len(seen) > 5:
                drained.set()
        if first:
            # Only the first row waits, and only until the pool has drained
            # past it, so a broken dispatch fails this rather than hanging it.
            drained.wait(30)
        return "match", "", 0, 0, ""

    probe = [{"program": "bank0", "addr": "%04X" % i, "name": "t",
              "out_file": "(not a listing)"} for i in range(8)]
    dwork = tempfile.mkdtemp(prefix="rasm-dispatch-")
    try:
        run_rows(probe, dwork, {"bank0": b""}, "unused", jobs=4,
                 check=recording_check)
    finally:
        shutil.rmtree(dwork, ignore_errors=True)
    holders = {}
    for name, d in seen:
        holders.setdefault(d, set()).add(name)
    shared = sum(1 for v in holders.values() if len(v) > 1)
    assert_that(len(seen) == 8 and drained.is_set() and shared == 0,
                "no two concurrently-running rows share a scratch directory "
                "(%d rows, %d directories, %d shared)"
                % (len(seen), len(holders), shared))

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

    # The outer function, over a repository this builds rather than over this
    # one. The cases above are the comparison, with no git in them; what they do
    # not reach is the part that runs git, refuses to answer, and returns 1. A
    # mode that returned 1 from everywhere satisfies every failure case above
    # and no verdict at all, so the `PASS` is in this list with them rather than
    # assumed from them.
    #
    # The repository root is threaded through as `--repo` rather than the git
    # callable injected, for the reason `_git()`'s own docstring gives: a fake
    # would have answered every case below, and `None` (the command did not run)
    # against `[]` (it ran and said nothing) is a distinction only a real git
    # draws. Two cases below do inject, and say so in the assertion.
    #
    # Before the find_assembler() early return for the reason agent-gates.sh
    # states when it runs this: the known answers sit there so they run whether
    # or not sdas8051 is installed, and nothing in this block needs an assembler.
    if not shutil.which("git"):
        print("  --   git absent: --verify-provenance's failure returns are not "
              "run here, because the mode reads every revision from git (the "
              "gate's own run of it needs git too, one line later)")
    else:
        fixture = tempfile.mkdtemp(prefix="rasm-provenance-")
        try:
            shas = build_provenance_fixture(fixture)
            # The read-back, and it is a control over a fixture rather than a
            # census: a builder that quietly stopped making commits -- or made
            # one and forgot to name it -- would leave a repository the cases
            # below cannot tell from the one they think they built, and an empty
            # `diff` over that is the one shape that cannot tell a working mode
            # from a matching-nothing one. Read back with git's own answer
            # rather than reconstructed from the builder: the same discipline
            # `test_verify_provenance_clone_depth.py` uses, reading
            # `--is-shallow-repository` back rather than inferring it from the
            # command that made the clone. Set equality, so a commit no case
            # names is as red as a name that is not a commit, and no size is
            # asserted anywhere.
            inside, _why = git_lines("rev-parse", "--is-inside-work-tree",
                                     repo=fixture)
            made, _why = git_lines("rev-list", "HEAD", repo=fixture)
            assert_that(
                inside == ["true"] and made
                and set(made) == set(shas.values())
                and len(set(shas.values())) == len(shas)
                and all(re.fullmatch("[0-9a-f]{40}", s or "")
                        for s in shas.values()),
                "the fixture is a repository whose %d named commit(s) are "
                "exactly the ones reachable from its HEAD (inside: %r, "
                "reachable: %d)" % (len(shas), inside, len(made or [])))

            # One argument vector over the fixture, by commit name, so a case
            # reads `at("base", "migration")` and the shas it stands for are the
            # ones the mode is given -- the shape the gate's own invocation
            # takes, where both revisions are shas too.
            def at(base, migration, listings_from="seed"):
                return ["--verify-provenance", "--repo", fixture,
                        "--base", shas[base], "--migration", shas[migration],
                        "--listings-from", shas[listings_from]]

            # The control, and the PASS. Everything below is read against this
            # one: a mode that fails at everything would satisfy five failure
            # cases and nothing here, which is the vacuity this block is the
            # answer to.
            status, said = main_says(at("base", "migration"))
            assert_that(
                status == 0 and "PASS" in said
                and "0 of them changed over" in said
                and "the same pathspec returns" in said
                and "once listing_digest is dropped" in said,
                "a migration that adds the column and nothing else reaches its "
                "verdict, with the control's count printed beside the zero it "
                "makes a measurement (status %r)" % status)
            # The supporting view is not a gate, and this says why: a `.c`
            # re-export is a normal thing for a window to contain, the digest is
            # over the parsed `.asm` stream, and the verdict is unchanged.
            assert_that(
                "the window touched" in said
                and "ec/decompiled/bank0/0EA2.c" in said and "PASS" in said,
                "and the window's .c re-export is named in the supporting view "
                "without moving the verdict: a C export is not a listing, so it "
                "cannot move a digest")

            # Each revision that does not resolve names its own label, and prints
            # the history requirement whole rather than a fragment of it. Three
            # copies of one case would be a control asserting nothing -- it would
            # go green on a mode that named the wrong flag -- so each names its
            # own.
            for label, argv, named_rev in (
                    ("base", ["--base", "no-such-base",
                              "--migration", shas["migration"]],
                     "cannot resolve the base revision 'no-such-base'"),
                    ("migration", ["--base", shas["base"],
                                   "--migration", "no-such-migration"],
                     "cannot resolve the migration revision "
                     "'no-such-migration'"),
                    ("--listings-from",
                     ["--base", shas["base"], "--migration", shas["migration"],
                      "--listings-from", "no-such-listings"],
                     "cannot resolve --listings-from 'no-such-listings'")):
                status, said = main_says(["--verify-provenance", "--repo",
                                          fixture] + argv)
                assert_that(
                    status == 1 and named_rev in said
                    and HISTORY_REQUIREMENT in said,
                    "an unresolvable %s fails with its own label and the "
                    "history requirement whole (status %r, requirement "
                    "printed: %s)"
                    % (label, status, HISTORY_REQUIREMENT in said))

            # The control that came back empty, which is the branch the whole
            # check is shaped around and the failure a wrong or stale
            # `--listings-from` produces: a control of zero over a window that
            # wrote nothing, printed as "the pathspec is matching nothing" --
            # indistinguishable from a working mode, on every commit, until
            # something says it is not one.
            status, said = main_says(at("base", "migration", listings_from="base"))
            assert_that(
                status == 1 and "the control returned 0 file(s)" in said
                and "Pass --listings-from the revision before the window that "
                    "last wrote" in said,
                "a deliberately wrong --listings-from fails at the control "
                "rather than passing as a diff that found nothing, and prints "
                "the remedy (status %r)" % status)

            # A listing that moved under the migration: the failure §14f exists
            # to close, and the one the gate's own --listings-from protects
            # against whenever it goes stale.
            status, said = main_says(at("base", "moved"))
            assert_that(
                status == 1 and "listing(s) changed under the migration" in said
                and "ec/decompiled/bank0/0040.asm" in said,
                "a listing that moved under the migration fails with the file "
                "named (status %r)" % status)

            # The report unreadable at the migration. The base is `moved` rather
            # than `base` so the window named is the deletion and nothing else:
            # a window that also moved a listing would be caught above and never
            # reach the report at all.
            status, said = main_says(at("moved", "gone"))
            assert_that(
                status == 1
                and "cannot read %s at the migration revision" % REPORT_REL
                in said,
                "a report that is not in the migration revision fails with the "
                "path and the side named (status %r)" % status)

            # And the same sentence naming the base. Reachable without a second
            # fixture because `listings` predates the report and its control
            # window still returns both listings -- which is the control doing
            # its job: it is what lets the run get as far as reading the report.
            status, said = main_says(at("listings", "migration"))
            assert_that(
                status == 1
                and "cannot read %s at the base revision" % REPORT_REL in said,
                "and the same sentence naming the base, with a control window "
                "that is not empty behind it (status %r)" % status)

            # Two reports differing beneath the column. compare_provenance()
            # holds this at the function level above; what is new here is the
            # outer function's print-and-return.
            status, said = main_says(at("base", "recounted"))
            assert_that(
                status == 1
                and "the two reports differ by more than the column" in said
                and "instructions_checked" in said and "0040" in said,
                "a cell changed under the column fails with the count, the cell "
                "and the row named (status %r)" % status)

            # Four broken migrations where the column is added but invalid.
            # Migration adds the column with all cells empty.
            status, said = main_says(at("base", "empty-col"))
            assert_that(
                status == 1 and "listing_digest column is empty" in said
                and "0040" in said,
                "a migration with an empty listing_digest column fails, naming the "
                "rows with empty cells (status %r)" % status)

            # Migration adds the column with all cells garbage.
            status, said = main_says(at("base", "garbage-col"))
            assert_that(
                status == 1 and "listing_digest column is empty" in said,
                "a migration with a garbage listing_digest column fails: "
                "non-hex is treated as empty (status %r)" % status)

            # Migration skips the column entirely.
            status, said = main_says(at("base", "no-col"))
            assert_that(
                status == 1 and "does not have listing_digest" in said,
                "a migration that skips the listing_digest column fails, saying "
                "the column is absent or was removed (status %r)" % status)

            # Base has the column, migration removes it.
            status, said = main_says(at("base-has-col", "base-has-col-remove"))
            assert_that(
                status == 1 and "already has listing_digest" in said,
                "a migration that removes the listing_digest column from a base "
                "that had it fails, saying the base already has the column "
                "(status %r)" % status)

            # The two `git_lines is None` branches, and the only cases here that
            # are not end-to-end: a commit that resolves cannot make `git diff`
            # fail over a fixed pathspec, so the failure is injected rather than
            # provoked. Everything outside the named window is the real git, so
            # each case reaches the branch it is about rather than failing to
            # resolve a revision in front of it.
            real_git = _git

            def with_git(shim, argv):
                """main_says() with `_git` replaced for the duration of the call."""
                global _git
                saved, _git = _git, shim
                try:
                    return main_says(argv)
                finally:
                    _git = saved

            def one_diff_answers(window, status=128, stderr="injected\n"):
                """`_git` with one diff window answering as it is told to.

                `stderr` is what `git_lines()` carries into the printed reason,
                so the cases below assert on it rather than on the shape of the
                message alone.
                """
                def shim(*args, repo=REPO):
                    if args[:1] == ("diff",) and any(window in str(a)
                                                     for a in args):
                        return subprocess.CompletedProcess(
                            args=["git", "-C", repo], returncode=status,
                            stdout="", stderr=stderr)
                    return real_git(*args, repo=repo)
                return shim

            control_window = "%s..%s" % (shas["seed"], shas["base"])
            listing_window = "%s..%s" % (shas["base"], shas["migration"])
            status, said = with_git(
                one_diff_answers(control_window, stderr="fatal: injected\n"),
                at("base", "migration"))
            assert_that(
                status == 1 and "the control diff did not run:" in said
                and "fatal: injected" in said,
                "INJECTED, not end-to-end: a control diff that did not run is "
                "refused and carries the reason out of git, rather than reading "
                "as a diff that found nothing (status %r)" % status)
            status, said = with_git(
                one_diff_answers(listing_window, stderr="fatal: injected\n"),
                at("base", "migration"))
            assert_that(
                status == 1 and "the listing diff did not run:" in said
                and "fatal: injected" in said,
                "INJECTED, not end-to-end: the same for the listing diff, which "
                "is the branch that would otherwise read a command that did not "
                "run as 'no listing moved' (status %r)" % status)
            # The non-vacuity of the pair: the same shim answering with no output
            # and a zero status is `[]` rather than `None`, and takes the
            # control-empty branch instead. Without this the two injected cases
            # would be one case written twice.
            status, said = with_git(
                one_diff_answers(control_window, status=0, stderr=""),
                at("base", "migration"))
            assert_that(
                status == 1 and "the control returned 0 file(s)" in said
                and "did not run" not in said,
                "and a diff that ran and said nothing is the other branch, not "
                "this one: `[]` is a measurement and `None` is not, which is "
                "the whole of what git_lines() exists to keep apart")
        finally:
            shutil.rmtree(fixture, ignore_errors=True)

    # What a run says about itself: the assembler it used, and its tally beside
    # the committed report's. Reported against synthetic reports rather than the
    # committed one, on the same principle as the digest probe above -- a
    # comparison that cannot be made to fail is not a comparison -- and through
    # committed_report()'s own DictReader, so a misspelled column name shows up
    # here rather than as a comparison that quietly matches nothing.
    #
    # Placed before the find_assembler() early return below, because the thing
    # under test is what a run claims about itself, and a machine with no
    # assembler is exactly the one whose "nothing to compare" claims matter most.
    NIX = "sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14"      # the report's
    NIXVER = "05.50.4+NoICE+SDCCmods-WIP-R14"
    HERE = "sdas8051 02.00"                              # this runner's
    COLUMNS = ["program", "addr", "name", "outcome",
               "instructions_checked", "instructions_unchecked", "assembler"]
    cmpdir = tempfile.TemporaryDirectory(prefix="compare-selftest-")
    written = []

    def synth(rows, fieldnames=None):
        """A report on disk, and committed_report()'s read of it."""
        path = os.path.join(cmpdir.name, "report%02d.csv" % len(written))
        written.append(path)
        with open(path, "w", newline="") as f:
            # extrasaction so the "no assembler column" case can be written from
            # the same row dicts as every other case, rather than from a second
            # copy of them that could drift.
            w = csv.DictWriter(f, fieldnames=fieldnames or COLUMNS,
                               lineterminator="\n", restval="",
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        return committed_report(path)

    def run_row(prog, addr, name, outcome, checked=0, unchecked=0):
        """One result in the shape verify() returns, so compare_tally() is
        handed the same tuple it gets in a real run: the bytes compared and the
        anchor are carried whether or not a caller here reads them."""
        return ({"program": prog, "addr": addr, "name": name},
                outcome, "", 0, checked, unchecked, "", 0)

    def note_text(lines):
        return " ".join(l for l in lines if l.strip().startswith("NOTE"))

    def plain_text(lines):
        return " ".join(l for l in lines if not l.strip().startswith("NOTE"))

    def row(checked, unchecked, outcome="match", prog="bank0", addr="0040",
            name="agrees", assembler=NIX):
        return {"program": prog, "addr": addr, "name": name,
                "outcome": outcome, "instructions_checked": str(checked),
                "instructions_unchecked": str(unchecked), "assembler": assembler}

    three = [row(10, 0), row(5, 0, addr="0042", name="also"),
             row(0, 2, outcome="assembler-gap", addr="0044", name="gappy")]
    same = [run_row("bank0", "0040", "agrees", "match", 10),
            run_row("bank0", "0042", "also", "match", 5),
            run_row("bank0", "0044", "gappy", "assembler-gap", 0, 2)]
    same_tally = {"match": 2, "assembler-gap": 1}
    base = synth(three)

    lines, warned = compare_assembler(NIXVER, base)
    assert_that(not warned and not note_text(lines)
                and "the same assembler" in plain_text(lines),
                "an identical assembler cell and tally report agreement, and "
                "raise no NOTE")
    lines, moved, deltas = compare_tally(same, same_tally, base)
    assert_that(moved == [] and all(d == 0 for _o, _a, _b, d in deltas)
                and any("moved since the committed report: nothing" in l
                        for l in lines),
                "a run that agrees with the committed report names nothing that "
                "moved")

    # One row crossing a category boundary. Both directions matter, so the
    # assertions are on the moved row and on each category's signed delta rather
    # than on the text alone.
    shifted = list(same)
    shifted[0] = run_row("bank0", "0040", "agrees", "partial", 10)
    shifted_tally = {"match": 1, "partial": 1, "assembler-gap": 1}
    lines, moved, deltas = compare_tally(shifted, shifted_tally, base)
    assert_that(moved == [("bank0", "0040", "agrees", "partial", "match")],
                "the one row that crossed a boundary is named with both "
                "outcomes")
    assert_that({o: d for o, _a, _b, d in deltas}
                == {"match": -1, "partial": 1, "assembler-gap": 0,
                    "listing-gap": 0, "mismatch": 0},
                "every category is compared, and only the two that moved carry "
                "a delta")
    named = [l for l in lines if "agrees" in l and " here, " in l]
    assert_that(len(named) == 1 and "partial here, match in " in named[0]
                and "reassembly.csv" in named[0],
                "the line names the row, both its outcomes, and the file the "
                "other outcome came from")
    assert_that([l for l in lines if l.strip().startswith("rows")][0].split()[-2:]
                == ["3", "3"],
                "a category that moved does not change the row count, and the "
                "line says so")

    # A version difference is the case this whole block was added for, and the
    # two halves of it are separate claims: the warning names both strings, and
    # the exit status does not move.
    lines, warned = compare_assembler("02.00", base)
    text = note_text(lines)
    assert_that(warned and text.count(HERE) == 1 and text.count(NIX) == 1,
                "a different assembler is one NOTE naming both version strings "
                "in full")
    assert_that(run_status(shifted_tally) == 0 and run_status({"mismatch": 1}) == 1,
                "a version difference and a moved category are reported and do "
                "not change the exit status, which is still mismatch == 0")

    # More than one committed value has no single answer to compare against.
    mixed = synth([row(10, 0, assembler=HERE), row(5, 0, addr="0042"),
                   row(0, 2, addr="0044", outcome="assembler-gap")])
    lines, warned = compare_assembler("02.00", mixed)
    assert_that(warned and "%s: 1 row" % HERE in plain_text(lines)
                and "%s: 2 rows" % NIX in plain_text(lines)
                and "no single answer to compare against" in note_text(lines)
                and "the same assembler" not in plain_text(lines),
                "two committed assemblers are both named with their row counts, "
                "and neither is picked as the one to compare against")

    # A report from before the column existed, in both of the shapes it can take.
    for label, committed in (
            ("with no assembler column",
             synth(three, fieldnames=COLUMNS[:-1])),
            ("with empty assembler cells",
             synth([dict(r, assembler="") for r in three]))):
        lines, warned = compare_assembler(NIXVER, committed)
        assert_that(warned and "before the column existed" in note_text(lines)
                    and "the same assembler" not in plain_text(lines),
                    "a report %s agrees with nothing, rather than being read as "
                    "agreement" % label)

    lines, warned = compare_assembler("unknown", base)
    assert_that(warned and "could not be read" in note_text(lines)
                and "the same assembler" not in plain_text(lines),
                "a version that could not be read is never reported as "
                "agreement: it established nothing")

    # An address in two bank windows is two rows, so the key has to be the
    # pair. 54 addresses in the committed report are like this; the two rows
    # here are given *different* committed outcomes on purpose: with identical
    # ones a key of addr alone collapses them and still happens to give the
    # right answer for this run, which is the case a weaker version of this
    # assertion would have passed.
    shared = synth([row(10, 0, prog="bank0", name="in_bank0"),
                    row(10, 0, prog="bank1", name="in_bank1",
                        outcome="partial")])
    _lines, moved, _deltas = compare_tally(
        [run_row("bank0", "0040", "in_bank0", "match", 10),
         run_row("bank1", "0040", "in_bank1", "match", 10)],
        {"match": 2}, shared)
    assert_that(moved == [("bank1", "0040", "in_bank1", "match", "partial")],
                "the same address in two programs is two rows, each compared "
                "against its own: the bank1 row moved, and the bank0 row, whose "
                "committed outcome differs, did not")

    # An outcome outside OUTCOMES is counted and named rather than dropped, and
    # the two halves still add up to the row count. check_one() can return every
    # one of the five, so this is the shape a real race or crash produces.
    odd = synth([row(10, 0), row(5, 0, addr="0042", outcome="assembler-error"),
                 row(0, 2, addr="0044", outcome="error")])
    ordered, residual = split_tally(odd["tally"])
    assert_that([o for o, _ in ordered] == list(OUTCOMES)
                and residual == [("assembler-error", 1), ("error", 1)]
                and sum(n for _o, n in ordered + residual) == 3,
                "an outcome outside OUTCOMES is named by the residual, and the "
                "two halves add up to the report's own row count")

    # The settled policy, one case per residual outcome. All five fail, and the
    # reason is that none of them is a measurement rather than that any of them
    # is serious: a run holding one cannot say which functions it checked. Both
    # readers are asserted here rather than only the exit status, because the two
    # were independent readings of `mismatch == 0` until unmeasured() became the
    # predicate they share, and that is the property this case exists to hold.
    for outcome in sorted(UNMEASURED):
        one = {outcome: 1}
        assert_that(run_status(one) == 1 and status_for(one) == 1
                    and unmeasured(one) == [(outcome, 1)]
                    and unmeasured_reason(outcome),
                    "a %s row carries no measurement, so a run holding one fails "
                    "and the predicate check() reads fails on the same tally: %s"
                    % (outcome, unmeasured_reason(outcome)))
    # And the direction that catches a fix which made everything fail, which the
    # cases above cannot: every outcome in OUTCOMES is a measurement, so a tally
    # of those with no mismatch is a run that did what it said.
    measured = {o: 1 for o in OUTCOMES if o != "mismatch"}
    assert_that(run_status(measured) == 0 and status_for(measured) == 0
                and unmeasured(measured) == [],
                "a tally of measured outcomes and no mismatch passes, so the "
                "cases above are the residual half of the policy and not a "
                "blanket failure")
    assert_that(run_status({"assembler-error": 1, "error": 2}) == 1,
                "a tally of nothing but unmeasured rows fails: these are the two "
                "§14g's race produced, on runs whose `mismatch` was 0 throughout "
                "and whose exit status was `mismatch` alone")
    # `listing-gap` is measured and not adjudicated, for the reason run_status()
    # gives: what it says is about the listing a run read, and the pinned build
    # settles it rather than whichever runner this is.
    assert_that(run_status({"listing-gap": 1}) == 0
                and run_status({"listing-gap": 1, "mismatch": 1}) == 1,
                "a listing-gap is counted and named, not failed on, and it does "
                "not stand in for the mismatch that is")

    # check()'s own half, against a synthetic report rather than the committed
    # one, because a comparison that cannot be made to fail is not a comparison.
    # What is asserted is the decision check() makes from a report's tally --
    # unmeasured() over report_tally()'s shape -- and not the whole of check(),
    # which also compares every listing byte against the firmware and both CSV
    # joins; none of those has anything to do with this question and all of them
    # need the committed report and the image.
    for outcome in sorted(UNMEASURED):
        tally = synth([row(10, 0), row(5, 0, addr="0042",
                                        outcome=outcome)])["tally"]
        assert_that(unmeasured(tally) == [(outcome, 1)]
                    and status_for(tally) == 1,
                    "a report carrying one %s row fails the predicate check() "
                    "reads, not only the run that produced it" % outcome)
    clean = synth([row(10, 0), row(5, 0, addr="0042"),
                   row(0, 2, addr="0044", outcome="assembler-gap")])["tally"]
    assert_that(unmeasured(clean) == [] and status_for(clean) == 0,
                "and a report of measured outcomes passes the same predicate, "
                "which is the control that keeps the case above honest")

    # check() itself, over the committed report with one row's `outcome` changed
    # and nothing else touched. The cases above are about the predicate check()
    # reads; this one is about check() using it, which is a separate thing and
    # the drift the shared predicate exists to stop -- a branch that prints a
    # FAIL and then forgets to set `ok` is the old defect with a new comment over
    # it. Only the one cell moves, so the byte check, the digest join and the
    # name join all still pass and the residual is the only thing that can turn
    # the status red. REPORT is repointed rather than the committed file touched,
    # and restored in the finally, so the tree is the same whichever way this
    # assertion goes.
    def checked_against(rows, fieldnames):
        """-> (status, stdout) for check() with `rows` standing in for REPORT."""
        global REPORT
        import contextlib
        import io
        buf = io.StringIO()
        path = os.path.join(cmpdir.name, "for-check%02d.csv" % len(written))
        written.append(path)
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n",
                               restval="")
            w.writeheader()
            w.writerows(rows)
        saved = REPORT
        REPORT = path
        try:
            with contextlib.redirect_stdout(buf):
                status = check()
        finally:
            REPORT = saved
        return status, buf.getvalue()

    with open(REPORT, newline="") as f:
        reader = csv.DictReader(f)
        report_columns = reader.fieldnames
        committed_rows = list(reader)
    spoiled = [dict(r) for r in committed_rows]
    spoiled[0]["outcome"] = "error"
    status, said = checked_against(spoiled, report_columns)
    assert_that(status == 1 and "outside OUTCOMES" in said
                and "a worker raised" in said,
                "check() fails a committed report carrying one residual row, "
                "and says which: status %r" % status)
    status, _said = checked_against(committed_rows, report_columns)
    assert_that(status == 0,
                "and the same report with that cell restored passes, so the "
                "residual is what failed it and nothing else (status %r)" % status)

    # write_report() refuses rather than writing a row that claims a re-encode
    # which did not happen, and refuses to every destination. The control is the
    # point of the second case: a measured run still writes, and its row is in
    # the file, so the refusal is this policy and not a writer that stopped.
    import contextlib
    import io

    def wrote_saying(results, path):
        """-> (write_report()'s return, what it printed)."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            returned = write_report(results, None, path, version=HERE)
        return returned, buf.getvalue()

    refused_path = os.path.join(cmpdir.name, "refused.csv")
    returned, said = wrote_saying(
        [run_row("bank0", "0040", "raced", "error"),
         run_row("bank0", "0042", "agrees", "match", 10)], refused_path)
    assert_that(returned is None and not os.path.exists(refused_path)
                and "error" in said and "raced" in said
                and unmeasured_reason("error") in said,
                "write_report() writes no report for a run carrying an `error` "
                "row, and says which outcome and which function: returned %r, "
                "file exists %s" % (returned, os.path.exists(refused_path)))
    clean_path = os.path.join(cmpdir.name, "clean.csv")
    returned, _said = wrote_saying(
        [run_row("bank0", "0040", "agrees", "match", 10)], clean_path)
    assert_that(returned == clean_path
                and [r["outcome"] for r in
                     csv.DictReader(open(clean_path, newline=""))] == ["match"],
                "and a run of measured outcomes is written, with its row")

    # `skipped` is settled to fail like the other four and cannot reach a report
    # through the full run: verify()'s filter drops exactly the index rows
    # check_one() answers `skipped` for. Asserted by calling check_one() on the
    # dropped rows rather than by restating the guard it reads -- the filter and
    # the outcome are two pieces of code and nothing else holds them together --
    # and answerable without an assembler because check_one() returns `skipped`
    # from `out_file` alone, before the image or the scratch directory is
    # touched. A policy for an unreachable outcome costs nothing, and leaving the
    # reachability as a measurement rather than as a claim is what makes that
    # safe to rely on.
    index_rows = list(csv.DictReader(open(LISTING_INDEX, newline="")))
    dropped = [r for r in index_rows
               if not (r["out_file"] and not r["out_file"].startswith("("))]
    assert_that(dropped and all(check_one(r, None, None, None)[0] == "skipped"
                                for r in dropped),
                "every listing-index row verify()'s filter drops is one "
                "check_one() answers `skipped` for, so `skipped` cannot reach a "
                "report through the full run -- and the filter drops some, so "
                "that relation is not vacuous")

    # Nothing to compare against is a reading, not a crash.
    absent = committed_report(os.path.join(cmpdir.name, "not-written.csv"))
    lines, warned = compare_assembler("02.00", absent)
    assert_that(absent is None and warned
                and "nothing to be compared against" in note_text(lines),
                "a missing report is one line saying there is nothing to "
                "compare against, not an exception")
    lines, moved, deltas = compare_tally(same, same_tally, absent)
    assert_that(moved == [] and deltas == []
                and any("nothing to compare against" in l for l in lines),
                "a missing report means the tally comparison returns no "
                "comparison, rather than an empty one that reads as agreement")

    # --limit: a 40-row run against 2,705 is not a disagreement, and printing
    # deltas for one would train the reader to skip the block.
    lines, moved, deltas = compare_tally(same[:1], {"match": 1}, base,
                                         limited=True)
    assert_that(moved == [] and deltas == []
                and any("1 of the committed report's 3 rows" in l for l in lines)
                and any("committed report: 2 match, 0 partial, 1 "
                        "assembler-gap, 0 listing-gap, 0 mismatch (of 3)"
                        in l for l in lines),
                "a --limit run prints the committed tally as a reference and "
                "compares nothing against it")

    # Two functions in flight at once must not share a scratch directory. 1, 2,
    # 3, 5 is the set a pool of four workers drifts into once one finishes
    # early, and it is the set that made four --jobs 4 runs of these same
    # committed inputs report 2,579, 2,588, 2,590 and 2,591 match.
    dirs = [scratch_dir(cmpdir.name, i) for i in (1, 2, 3, 5)]
    assert_that(len(set(dirs)) == 4 and all(os.path.isdir(d) for d in dirs)
                and scratch_dir(cmpdir.name, 1) == dirs[0],
                "every function gets its own scratch directory, and it is the "
                "same one when asked twice")

    # A listing that parses to nothing, with no assembler in the room. This is
    # the shape issue #229 is about -- every instruction translated, the
    # assembler run and exited 0, and the listing it printed carried no entry
    # at the address the comparison reached -- and it is reachable here with a
    # stub rather than a real sdas8051, so it runs in the cheap tier on every
    # commit instead of only where one is installed. What used to answer to it
    # was `assembler-gap`, which says the form is inexpressible, and it is not:
    # the fixture's four instructions are textbook forms and the image agrees
    # with every one of them.
    stub_dir = tempfile.mkdtemp(prefix="rasm-empty-lst-")
    stub = os.path.join(stub_dir, "sdas-empty-lst")
    with open(stub, "w") as f:
        f.write('#!/usr/bin/env python3\n'
                '"""Stand in for sdas8051: exit 0 having printed an empty listing.\n\n'
                "The committed `no bytes emitted at %04X` detail is written from\n"
                "inside check_one()'s comparison loop, so reproducing it needs an\n"
                "assembler that succeeds and a listing carrying no entry at the\n"
                "address the comparison reaches. Writing the file rather than\n"
                "skipping it is deliberate: read_lst() returns {} either way, and\n"
                "the case that is still open -- a listing this build prints in a\n"
                'shape the regex cannot see -- needs the file present."\n'
                '"""\n'
                "import os\n"
                "import sys\n\n"
                "src = sys.argv[-1]\n"
                "open(os.path.splitext(src)[0] + '.lst', 'w').close()\n")
    os.chmod(stub, 0o755)
    empty_img = bytearray(b"\x00" * 0x100)
    empty_img[0x40:0x48] = bytes.fromhex("7412 0200 4522 00".replace(" ", ""))
    empty_row = {"program": "bank0", "addr": "0040", "name": "t",
                 "out_file": "listing-index.csv.tmp-empty"}
    empty_real = os.path.join(DECOMPILED, "listing-index.csv.tmp-empty")
    with open(empty_real, "w") as f:
        f.write("0040  74 12 -     mov   a,#0x12\n"
                "0042  02 00 45    ljmp  0x0045\n"
                "0045  22  -  -    ret\n"
                "0046  00  -  -    nop\n")
    try:
        outcome, detail, compared, nchecked, nskip, _d, anchor = check_one(
            empty_row, bytes(empty_img), scratch_dir(stub_dir, 0), stub)
        assert_that(outcome == "listing-gap",
                    "an empty assembled listing is `listing-gap`, not "
                    "`assembler-gap`: nothing about it says the form is "
                    "inexpressible (%s)" % outcome)
        assert_that(compared == 0 and nchecked == 4 and nskip == 0,
                    "and it reports 0 bytes compared against %d instruction(s) "
                    "translated, so a row that compared nothing cannot report a "
                    "checked instruction" % nchecked)
        assert_that(detail.endswith("(anchored at 0040)")
                    and anchor == 0x0040,
                    "the detail names where the `.org` put the function, which "
                    "is not the row's own address for 14 rows of the committed "
                    "report (%r)" % detail)
        assert_that(run_status({"listing-gap": 1}) == 0,
                    "and a listing-gap run exits 0: it is measured, not "
                    "adjudicated, for the reason run_status() gives")
    finally:
        os.remove(empty_real)
        shutil.rmtree(stub_dir, ignore_errors=True)
    cmpdir.cleanup()

    # The name column, which is a copy and not a measurement, and so is both
    # checked and refreshed on a different argument from the digest above. The
    # scratch report and the scratch listing index are written here rather than
    # committed, for the reason the digest probe is: the thing under test is a
    # join between two CSVs this file can be handed, so a fixture row nobody
    # edits is a thing to keep in step for nothing.
    ndir = tempfile.TemporaryDirectory(prefix="name-selftest-")
    NAME_REPORT_COLUMNS = ["program", "addr", "name", "outcome",
                           "listing_digest", "detail", "assembler"]
    NAME_INDEX_COLUMNS = ["program", "addr", "name", "out_file"]

    def nrow(name, addr="0040", prog="bank0", assembler=NIX, detail=""):
        return {"program": prog, "addr": addr, "name": name, "outcome": "match",
                "listing_digest": "0123456789abcdef", "detail": detail,
                "assembler": assembler}

    def nrow_pair(report_rows, index_rows):
        """A report and a listing index on disk -> their two paths, then read."""
        rpath = os.path.join(ndir.name, "report.csv")
        ipath = os.path.join(ndir.name, "listing-index.csv")
        for path, columns, rows in ((rpath, NAME_REPORT_COLUMNS, report_rows),
                                    (ipath, NAME_INDEX_COLUMNS, index_rows)):
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n",
                                   restval="", extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
        with open(rpath, newline="") as f:
            report = {r["addr"] + "|" + r["program"]: r
                      for r in csv.DictReader(f)}
        return rpath, ipath, report, listing_index_keys(ipath)

    # A renamed listing has to fail, and the message has to carry both
    # spellings: "something moved" is not a thing the reader can act on.
    rpath, ipath, report, (live, names) = nrow_pair(
        [nrow("FUN_CODE_0012", addr="0012"),
         nrow("store_be16_b", addr="BD54")],
        [{"program": "bank0", "addr": "0012", "name": "ret_only_0012",
          "out_file": "bank0/0012.asm"},
         {"program": "bank0", "addr": "BD54", "name": "store_be16_b",
          "out_file": "bank0/BD54.asm"}])
    n_compared, n_bad = compare_names(report, names, live)
    assert_that(n_compared == 2 and len(n_bad) == 1
                and n_bad[0][0] == "0012|bank0",
                "a row whose name the index has renamed fails while the row "
                "beside it passes (%d compared, %d failed)"
                % (n_compared, len(n_bad)))
    assert_that(len(n_bad[0]) == 6 and n_bad[0][4] == "bank0/0012.asm"
                and "FUN_CODE_0012" in n_bad[0][5]
                and "ret_only_0012" in n_bad[0][5],
                "the failure carries the six fields check() already prints for a "
                "digest: both spellings in the why, the listing in the field the "
                "printer puts in parentheses")

    # The two rows that are not "nothing to compare", which is the shape a
    # checker fails in: one has no name to copy, the other has no listing to copy
    # from. Both are named, and neither is counted as compared.
    _rpath, _ipath, report, (live, names) = nrow_pair(
        [nrow("", addr="0040"), nrow("orphan", addr="0044")],
        [{"program": "bank0", "addr": "0040", "name": "refreshed",
          "out_file": "bank0/0040.asm"}])
    n_compared, n_bad = compare_names(report, names, live)
    assert_that(n_compared == 0 and len(n_bad) == 2
                and "no name in the report" in n_bad[0][5]
                and "no name to compare against" in n_bad[1][5],
                "a blank name and a row with no index row are both named and "
                "told apart, and neither is skipped as agreement (%d compared, "
                "%d failed)" % (n_compared, len(n_bad)))

    # The writer. It moves the name and nothing else, and it says so from the
    # file it wrote rather than from the rows it was about to write -- so the
    # row that changes is also the row carrying the other assembler's version
    # string, which is the one a writer computing a measurement would rewrite.
    rpath, ipath, _report, _keys = nrow_pair(
        [nrow("FUN_CODE_0012", addr="0012", assembler="sdas8051 02.00"),
         nrow("store_be16_b", addr="BD54", detail="a, b \"c\""),
         nrow("already", addr="0044")],
        [{"program": "bank0", "addr": "0012", "name": "ret_only_0012",
          "out_file": "bank0/0012.asm"},
         {"program": "bank0", "addr": "BD54", "name": "store_be16_b",
          "out_file": "bank0/BD54.asm"},
         {"program": "bank0", "addr": "0044", "name": "already",
          "out_file": "bank0/0044.asm"}])
    assert_that(refresh_name_column(rpath, ipath) == 0,
                "a report with one stale name refreshes and exits 0")
    _raw, after_header, after = read_report(rpath)
    assert_that(after_header == NAME_REPORT_COLUMNS
                and [r["name"] for r in after]
                == ["ret_only_0012", "store_be16_b", "already"]
                and [r["assembler"] for r in after]
                == ["sdas8051 02.00", NIX, NIX]
                and after[1]["detail"] == "a, b \"c\"",
                "the names become the index's and every other cell is the one "
                "that was there: a non-uniform assembler column, a detail cell "
                "holding a comma and a quote, the header and the row order")

    # The key sets, both directions, and before anything is written. A name
    # written across either of them would leave a stale report looking current.
    rpath, ipath, _report, _keys = nrow_pair(
        [nrow("agrees", addr="0040"), nrow("orphan", addr="0044")],
        [{"program": "bank0", "addr": "0040", "name": "agrees",
          "out_file": "bank0/0040.asm"},
         {"program": "bank0", "addr": "0046", "name": "unlisted",
          "out_file": "bank0/0046.asm"}])
    untouched = open(rpath, "rb").read()
    assert_that(refresh_name_column(rpath, ipath) == 1
                and open(rpath, "rb").read() == untouched,
                "a key set that disagrees in both directions is refused and the "
                "file is left byte for byte as it was")

    # A refresh with nothing to move. The one-column claim at its strongest: if
    # the writer touched quoting, the line terminator or the column order, this
    # is where it shows and nothing above it would.
    rpath, ipath, _report, _keys = nrow_pair(
        [nrow("agrees", addr="0040", detail="a, b \"c\"")],
        [{"program": "bank0", "addr": "0040", "name": "agrees",
          "out_file": "bank0/0040.asm"}])
    untouched = open(rpath, "rb").read()
    assert_that(refresh_name_column(rpath, ipath) == 0
                and open(rpath, "rb").read() == untouched,
                "a refresh with nothing to move leaves the file byte-identical")

    # The guard, on the writer's own path rather than only as a function. A row
    # with a missing trailing cell is the one a CSV round-trip genuinely
    # changes -- DictReader fills it with None and DictWriter writes it back as
    # "" -- so this is a case the writer reaches and not a fault injected for
    # it, and the file has to come back out of it untouched.
    short = os.path.join(ndir.name, "short.csv")
    short_index = os.path.join(ndir.name, "short-index.csv")
    with open(short, "w", newline="") as f:
        f.write("program,addr,name,outcome\n"
                "bank0,0040,stale,match\n"
                "bank0,0044,kept\n")
    with open(short_index, "w", newline="") as f:
        f.write("program,addr,name,out_file\n"
                "bank0,0040,refreshed,common/0040.asm\n"
                "bank0,0044,kept,common/0044.asm\n")
    untouched = open(short, "rb").read()
    assert_that(refresh_name_column(short, short_index) == 1
                and open(short, "rb").read() == untouched,
                "a report the writer cannot round-trip is restored byte for byte "
                "rather than left half rewritten")

    # The guard refusing both things a cell comparison cannot see on its own.
    held, why = only_name_moved(
        (["a", "name", "b"], [{"a": "1", "name": "x", "b": "2"}]),
        (["a", "name", "b"], [{"a": "9", "name": "y", "b": "2"}]))
    assert_that(not held and "a column" in why,
                "the guard fails on a cell that moved under a column other than "
                "name, and says which one (%r)" % why)
    held, why = only_name_moved(
        (["a", "name", "b"], [{"a": "1", "name": "x", "b": "2"}]),
        (["a", "name"], [{"a": "1", "name": "y"}]))
    assert_that(not held and "header" in why,
                "and on a header that moved, which comparing cells would never "
                "see (%r)" % why)
    ndir.cleanup()

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
        outcome, detail, compared, nchecked, nskip, digest, _a = check_one(
            row, bytes(img), work, sdas)
        assert_that(outcome == "match",
                    "a correct listing re-encodes to the image bytes (%s %s)"
                    % (outcome, detail))
        # The whole point of the byte count: on the agreeing path it is every
        # byte of every translated instruction, so it is not a column that only
        # reads sensibly when something is wrong.
        assert_that(compared == 7 and nchecked == 4,
                    "an agreeing row reports 7 bytes compared across 4 "
                    "instruction(s), so the two counts are not the same number "
                    "(%d, %d)" % (compared, nchecked))
        assert_that(digest == digest_of(parse_listing_str(
                        "0040  74 12 -     mov   a,#0x12\n"
                        "0042  02 00 45    ljmp  0x0045\n"
                        "0045  22  -  -    ret\n"
                        "0046  00  -  -    nop\n")),
                    "check_one returns the digest of the listing it parsed, so "
                    "the report is written without a second parse")
        # Corrupt one byte of the image: the check must notice.
        img[0x41] = 0x13
        outcome, _d, compared, _c, _s, _g, _an = check_one(
            row, bytes(img), work, sdas)
        assert_that(outcome == "mismatch" and compared == 2,
                    "a wrong image byte is reported as a mismatch, not a pass, "
                    "and the byte it disagreed on is counted as compared, "
                    "because it reached the comparison (%d)" % compared)
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
    ap.add_argument("--emit-csv", metavar="PATH",
                    help="write the per-row results to PATH, for comparing two "
                         "runs; refuses the committed report, and refuses --check, "
                         "--self-test, --add-digest-column, "
                         "--refresh-name-column, --verify-provenance "
                         "and --limit, none of which produce a full set of rows "
                         "to write")
    ap.add_argument("--check", action="store_true",
                    help="CI: the report still describes the listings (no assembler)")
    ap.add_argument("--add-digest-column", action="store_true",
                    help="one-shot: add listing_digest to the existing report, "
                         "without re-encoding (refuses to run twice)")
    ap.add_argument("--refresh-name-column", action="store_true",
                    help="copy the listing index's names into the report's name "
                         "column, no re-encode; repeatable, because a name is a "
                         "copy and not a measurement, and it proves from the "
                         "written file that no other cell moved")
    ap.add_argument("--verify-provenance", action="store_true",
                    help="audit a listing_digest migration against the history "
                         "it sits in; needs --base and --migration, and a full "
                         "git history")
    ap.add_argument("--base", help="last full --report revision")
    ap.add_argument("--migration", help="the revision that added listing_digest")
    ap.add_argument("--listings-from",
                    help="revision before the window that last wrote the "
                         "listings, for the positive control (default: <base>^)")
    ap.add_argument("--repo", metavar="ROOT", default=REPO,
                    help="the clone --verify-provenance reads its revisions "
                         "from (default: the repository this script is in)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.emit_csv:
        # Checked here rather than in emit_csv(), for the reason the committed
        # report's check below is: a refused combination should cost a
        # millisecond rather than the whole re-encode that follows, and --limit
        # is the expensive one to discover late.
        refused = refuses_emit_csv(args)
        if refused:
            flag, why = refused
            if why == "truncates":
                print("  --limit %d makes --emit-csv write part of a report "
                      "under the whole\n  report's header, and nothing in the "
                      "file says which part. Run it without\n  --limit, or read "
                      "the tally this run prints rather than a CSV."
                      % args.limit)
            else:
                print("  --emit-csv needs the full re-encode, and %s does not "
                      "run it.\n  Drop one of the two flags; %s."
                      % (flag.spelled, flag.remedy))
            return 2
    if args.self_test:
        return self_test()
    if args.verify_provenance:
        if not args.base or not args.migration:
            ap.error("--verify-provenance needs --base and --migration")
        return verify_provenance(args.base, args.migration, args.listings_from,
                                 repo=args.repo)
    if args.add_digest_column:
        return add_digest_column()
    if args.refresh_name_column:
        return refresh_name_column()
    if args.check:
        return check()
    # Checked here as well as in emit_csv(), so a refused path costs a
    # millisecond rather than the whole 2,705-row re-encode that follows.
    if args.emit_csv and refuses_committed_report(args.emit_csv):
        return 1
    verified = verify(limit=args.limit, jobs=args.jobs, work=args.work,
                      sdas=args.assembler)
    if verified is None:
        # verify() has already printed why there is no result; 2 is the status
        # for "the environment is missing the tool", which is what it has always
        # meant here and what the run would have exited with if main() had
        # handled the answer it was given.
        return 2
    results, tally, sdas, version = verified
    reported = 0
    if args.report:
        wrote = write_report(results, sdas, version=version)
        if wrote is None:
            # write_report() has said why, and run_status() is already 1 on the
            # same tally -- but a refused --report is this flag not being
            # honoured, which is counted here rather than left to two readers of
            # the policy happening to agree.
            reported = 1
        else:
            print("\n  wrote %s" % os.path.relpath(wrote, REPO))
    emitted = 0
    if args.emit_csv:
        emitted = emit_csv(results, sdas, args.emit_csv)
    # A refused --emit-csv is the user's flag not being honoured, so it is a
    # non-zero run whatever the tallies say; a run that quietly did not write
    # the file it was asked for is how a comparison ends up comparing nothing.
    return emitted or reported or run_status(tally)


if __name__ == "__main__":
    sys.exit(main() or 0)
