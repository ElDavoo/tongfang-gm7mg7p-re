#!/usr/bin/env python3
"""Minimal linear 8051 decoder: enough to read a window of instructions
around an address of interest, and no more.

This is deliberately *not* a disassembler. It decodes forward from an
address you give it, one instruction after another, and prints what it
finds. It does not follow branches, does not recover function boundaries,
does not know where code ends and a jump table begins, and cannot tell you
that the byte you pointed it at is the start of an instruction -- if you
anchor it mid-instruction it will happily decode the garbage that follows.
Alignment is therefore always anchor-relative: `--converge` measures how
many nearby anchors a linear walk syncs onto a given offset from, which is
evidence about framing, not proof of it. Confirm anything load-bearing in
`r2 -a 8051` (make_bank_image.py builds it an image; trace_xdata_refs.py
--r2-commands prints the seek lines).

The opcode length table covers the full 8051 map, because mis-framing one
instruction corrupts every instruction after it. The mnemonic table covers
the subset this firmware actually uses; anything else prints as `db`.

`--self-test` decodes the two windows that ec/annotations/charge-profile-flow.md
transcribed by hand from `r2 -a 8051` and requires a byte-for-byte match
against those listings -- that is the oracle for the tables above, so run
it after touching either. It then checks relative_target() against four more
hand decodes (ec/annotations/bank-call-audit.md 8), because both windows
branch forward only and a sign-extension bug would survive them, and mnemonics
against BIT_SITES, which covers the bit-addressable carry forms the windows
above contain none of.

Usage:
    python3 disasm8051.py --self-test
    python3 disasm8051.py ../firmware/GMxMGxx_11.800 --at 0x23478 -n 12
    python3 disasm8051.py ../firmware/GMxMGxx_11.800 --at 0x23478 --converge
"""
import argparse
from pathlib import Path
import sys

# Instruction length for every opcode. Rows of 16, opcode 0x00 first.
OPCODE_LEN = (
    b"\x01\x02\x03\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x03\x02\x03\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x03\x02\x01\x01\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x03\x02\x01\x01\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x03\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x03\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x03\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x01\x02\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02"
    b"\x02\x02\x02\x01\x01\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02"
    b"\x03\x02\x02\x01\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02"
    b"\x02\x02\x02\x01\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03"
    b"\x02\x02\x02\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x01\x01\x03\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02"
    b"\x01\x02\x01\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x01\x02\x01\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
)

# Opcodes past which the next bytes are not necessarily what executes.
FLOW_OPCODES = {0x02, 0x12, 0x22, 0x32, 0x40, 0x50, 0x60, 0x70, 0x80,
                0x10, 0x20, 0x30, 0xB4, 0xB5, 0xD5, 0x73}
FLOW_OPCODES |= set(range(0x01, 0x100, 0x20))  # AJMP
FLOW_OPCODES |= set(range(0x11, 0x100, 0x20))  # ACALL
FLOW_OPCODES |= set(range(0xB6, 0xC0))         # CJNE @Ri/Rn
FLOW_OPCODES |= set(range(0xD8, 0xE0))         # DJNZ Rn

# The PC-relative branch family, mapped to the mnemonic a caller would group
# by. These are the opcodes whose *last* byte is a signed 8-bit displacement;
# it is the second byte for the 2-byte forms and the third for the 3-byte ones,
# which is why relative_target() consults OPCODE_LEN rather than a constant.
# 29 of the 256 byte values, against 16 for the paged forms and 2 for the
# absolute ones -- a byte scan for these over-counts correspondingly harder.
REL_OPCODES = {0x80: "sjmp", 0x40: "jc", 0x50: "jnc", 0x60: "jz", 0x70: "jnz",
               0x10: "jbc", 0x20: "jb", 0x30: "jnb",
               0xB4: "cjne", 0xB5: "cjne", 0xD5: "djnz"}
REL_OPCODES.update({op: "cjne" for op in range(0xB6, 0xC0)})  # CJNE @Ri/Rn
REL_OPCODES.update({op: "djnz" for op in range(0xD8, 0xE0)})  # DJNZ Rn

# Bit-addressable SFRs, for rendering the bit operand of JB/JNB/JBC/SETB
# the way r2 prints it (`acc.0`, not `0xe0`).
BIT_SFR = {0x80: "p0", 0x88: "tcon", 0x90: "p1", 0x98: "scon", 0xA0: "p2",
           0xA8: "ie", 0xB0: "p3", 0xB8: "ip", 0xD0: "psw", 0xE0: "acc",
           0xF0: "b"}


def bit_name(b: int) -> str:
    if b >= 0x80:
        base = BIT_SFR.get(b & 0xF8)
        if base:
            return f"{base}.{b & 0x07}"
        return f"0x{b & 0xF8:02x}.{b & 0x07}"
    return f"0x{0x20 + (b >> 3):02x}.{b & 0x07}"


def paged_target(op: int, operand: int, addr: int) -> int:
    """Absolute target of the 2-byte `ajmp`/`acall` at runtime address `addr`.

    The page comes from the address of the *next* instruction, not from the
    opcode's own -- so a site in the last two bytes of a page targets the
    following page. Target bits are that next-PC's top 5, the opcode's high
    3, and the operand byte, which puts the target inside one fixed 2 KiB
    page for any given site."""
    return ((addr + 2) & 0xF800) | ((op & 0xE0) << 3) | operand


def relative_target(op: int, disp: int, addr: int) -> int:
    """Absolute target of the PC-relative branch at runtime address `addr`.

    `disp` is the instruction's *last* byte -- `d[i + OPCODE_LEN[op] - 1]`, not
    `d[i + 1]`: the 3-byte forms (`jb`/`jnb`/`jbc`, `cjne`, `djnz direct`) put a
    bit or operand byte in between, so handing this the second byte silently
    resolves those to the wrong target. It is signed, and it is added to the
    address of the *next* instruction, which is why OPCODE_LEN is consulted
    rather than a constant that would only suit one of the two lengths."""
    return (addr + OPCODE_LEN[op] + (disp - 256 if disp > 127 else disp)) & 0xFFFF


def mnemonic(d: bytes, i: int, addr: int = None) -> str:
    """Render the instruction at d[i]. `addr` is that instruction's runtime
    address; supply it to get absolute branch targets, omit it to get the
    raw displacement byte."""
    op = d[i]

    def rel(n: int) -> str:
        if addr is None:
            return f"+0x{d[i + n]:02x}"
        return f"0x{relative_target(op, d[i + n], addr):04x}"

    if op == 0x90:
        return f"mov  dptr,#0x{(d[i + 1] << 8) | d[i + 2]:04x}"
    if op == 0xE0:
        return "movx a,@dptr"
    if op == 0xF0:
        return "movx @dptr,a"
    if op == 0xA3:
        return "inc  dptr"
    if op == 0xE4:
        return "clr  a"
    if op == 0x04:
        return "inc  a"
    if op == 0x14:
        return "dec  a"
    if op == 0xA4:
        return "mul  ab"
    if op == 0x84:
        return "div  ab"
    if op in (0x54, 0x44, 0x64, 0x74, 0x24, 0x34, 0x94):
        name = {0x54: "anl", 0x44: "orl", 0x64: "xrl",
                0x74: "mov", 0x24: "add", 0x34: "addc", 0x94: "subb"}[op]
        return f"{name:<4} a,#0x{d[i + 1]:02x}"
    if op in (0x55, 0x45, 0x65, 0x25, 0x35, 0x95):
        name = {0x55: "anl", 0x45: "orl", 0x65: "xrl",
                0x25: "add", 0x35: "addc", 0x95: "subb"}[op]
        return f"{name:<4} a,0x{d[i + 1]:02x}"
    if 0x28 <= op <= 0x9F and (op & 0x0F) >= 0x08 and (op & 0xF0) in (0x20, 0x30, 0x40, 0x50, 0x60, 0x90):
        name = {0x20: "add", 0x30: "addc", 0x40: "orl",
                0x50: "anl", 0x60: "xrl", 0x90: "subb"}[op & 0xF0]
        return f"{name:<4} a,r{op & 0x07}"
    if op in (0x40, 0x50, 0x60, 0x70, 0x80):
        name = {0x40: "jc", 0x50: "jnc", 0x60: "jz", 0x70: "jnz", 0x80: "sjmp"}[op]
        return f"{name:<4} {rel(1)}"
    if op in (0x20, 0x30, 0x10):
        name = {0x20: "jb", 0x30: "jnb", 0x10: "jbc"}[op]
        return f"{name:<4} {bit_name(d[i + 1])},{rel(2)}"
    if op in (0xD2, 0xB2):
        name = {0xD2: "setb", 0xB2: "cpl"}[op]
        return f"{name:<4} {bit_name(d[i + 1])}"
    # The carry forms. 0x92 was the one opcode missing from this table that a
    # committed listing actually uses, so `mov 0xd5,CY` decoded as `db 0x92` --
    # and a cross-decode can only "agree" with a `db` vacuously.
    if op in (0x92, 0xA2):
        # The same two bytes read in either order: 0x92 writes the bit, 0xA2
        # reads it. They are the only such pair in the map.
        if op == 0x92:
            return f"mov  {bit_name(d[i + 1])},c"
        return f"mov  c,{bit_name(d[i + 1])}"
    if op in (0xA0, 0xB0):
        # ANL C,/bit and ORL C,/bit -- and which opcode is which is *not*
        # settled in this repository. Ghidra's SLEIGH, r2 and sdas8051 all put
        # ORL at 0xA0 and ANL at 0xB0; the MCS-51 manual as reproduced in
        # common references has them the other way round. Three decoders
        # agreeing is why this table follows them and not the manual, and none
        # of the three arbitrating the other two is why that is a comment and
        # not a correction. No committed instruction is affected either way:
        # 0xA0/0xB0 are the bit forms sdas8051 *does* express, so all 12
        # occurrences sit inside the 45,394 the re-encode covers.
        name = {0xA0: "orl", 0xB0: "anl"}[op]
        return f"{name:<4} c,/{bit_name(d[i + 1])}"
    if op == 0xC1:
        # CLR bit, kept out of the 0xD2/0xB2 tuple above because 0xC2 is CLR
        # *direct*: the two are the same length and differ only in what the
        # byte means, which is the form sdas8051 assembles to a plausible
        # wrong instruction without complaining (see
        # verify_reassembly.BIT_UNSUPPORTED).
        return f"clr  {bit_name(d[i + 1])}"
    if op == 0xC2:
        # CLR direct, and the operand is a byte address: `clr 0x7f` clears all
        # eight bits of 0x7F. This was grouped with the bit forms above, which
        # printed it as `clr 0x2f.7` -- a different instruction, for all 180
        # committed CLR direct instructions. Found by the TEXTBOOK_BIT_SITES
        # pair that keeps 0xC1 and 0xC2 apart.
        return f"clr  0x{d[i + 1]:02x}"
    if op == 0xB4:
        return f"cjne a,#0x{d[i + 1]:02x},{rel(2)}"
    if op == 0xB5:
        return f"cjne a,0x{d[i + 1]:02x},{rel(2)}"
    if 0xB8 <= op <= 0xBF:
        return f"cjne r{op - 0xB8},#0x{d[i + 1]:02x},{rel(2)}"
    if 0xD8 <= op <= 0xDF:
        return f"djnz r{op - 0xD8},{rel(1)}"
    if op == 0xD5:
        return f"djnz 0x{d[i + 1]:02x},{rel(2)}"
    if op in (0x02, 0x12):
        return f"{'ljmp' if op == 0x02 else 'lcall'} 0x{(d[i + 1] << 8) | d[i + 2]:04x}"
    if op & 0x1F in (0x01, 0x11):
        name = "ajmp" if op & 0x1F == 0x01 else "acall"
        if addr is None:
            # `page+0x53` rather than `0x0053`, because without an address the
            # 11 target bits are not knowable and a bare hex number here would
            # read like one of the absolute forms above.
            return f"{name:<4} page+0x{d[i + 1]:02x}"
        return f"{name:<4} 0x{paged_target(op, d[i + 1], addr):04x}"
    if 0xE8 <= op <= 0xEF:
        return f"mov  a,r{op - 0xE8}"
    if 0xF8 <= op <= 0xFF:
        return f"mov  r{op - 0xF8},a"
    if 0x78 <= op <= 0x7F:
        return f"mov  r{op - 0x78},#0x{d[i + 1]:02x}"
    if 0x08 <= op <= 0x0F:
        return f"inc  r{op - 0x08}"
    if 0xA8 <= op <= 0xAF:
        return f"mov  r{op - 0xA8},0x{d[i + 1]:02x}"
    if 0x88 <= op <= 0x8F:
        return f"mov  0x{d[i + 1]:02x},r{op - 0x88}"
    if op == 0xE5:
        return f"mov  a,0x{d[i + 1]:02x}"
    if op == 0xF5:
        return f"mov  0x{d[i + 1]:02x},a"
    if op == 0x75:
        return f"mov  0x{d[i + 1]:02x},#0x{d[i + 2]:02x}"
    if op == 0x85:
        return f"mov  0x{d[i + 2]:02x},0x{d[i + 1]:02x}"
    if op in (0xE6, 0xE7):
        return f"mov  a,@r{op - 0xE6}"
    if op in (0xF6, 0xF7):
        return f"mov  @r{op - 0xF6},a"
    if op in (0xE2, 0xE3):
        return f"movx a,@r{op - 0xE2}"
    if op in (0xF2, 0xF3):
        return f"movx @r{op - 0xF2},a"
    if op == 0x05:
        return f"inc  0x{d[i + 1]:02x}"
    if op == 0x15:
        return f"dec  0x{d[i + 1]:02x}"
    if 0x18 <= op <= 0x1F:
        return f"dec  r{op - 0x18}"
    if op == 0xC0:
        return f"push 0x{d[i + 1]:02x}"
    if op == 0xD0:
        return f"pop  0x{d[i + 1]:02x}"
    if op == 0xC5:
        return f"xch  a,0x{d[i + 1]:02x}"
    if 0xC8 <= op <= 0xCF:
        return f"xch  a,r{op - 0xC8}"
    if op in (0xC6, 0xC7):
        return f"xch  a,@r{op - 0xC6}"
    if op in (0xD6, 0xD7):
        return f"xchd a,@r{op - 0xD6}"
    if op == 0x73:
        return "jmp  @a+dptr"
    if op == 0x00:
        return "nop"
    if op == 0x33:
        return "rlc  a"
    if op == 0x23:
        return "rl   a"
    if op == 0x13:
        return "rrc  a"
    if op == 0x03:
        return "rr   a"
    if op == 0xC3:
        return "clr  c"
    if op == 0xD3:
        return "setb c"
    if op == 0xB3:
        return "cpl  c"
    if op == 0xC4:
        return "swap a"
    if op == 0x22:
        return "ret"
    if op == 0x32:
        return "reti"
    if op == 0x93:
        return "movc a,@a+dptr"
    if op == 0x83:
        return "movc a,@a+pc"
    return f"db   0x{op:02x}"


def decode(d: bytes, start: int, count: int, addr: int = None, stop_at_flow: bool = False):
    """Decode `count` instructions from d[start]. Yields (offset, raw, text).
    `addr` is the runtime address of d[start], if it differs from start.

    Stops cleanly rather than raising: the end-of-buffer check runs before the
    index it guards, so a caller asking for more instructions than the buffer
    holds gets what fitted, and an instruction that does not fit is not decoded
    out of bytes that are not there. `count` is a request, not a promise."""
    i = start
    for _ in range(count):
        if i >= len(d):
            return
        n = OPCODE_LEN[d[i]]
        if i + n > len(d):
            return
        here = None if addr is None else addr + (i - start)
        yield i, d[i:i + n], mnemonic(d, i, here)
        if stop_at_flow and d[i] in FLOW_OPCODES:
            return
        i += n


def converges_from(d: bytes, off: int, back: int = 24) -> tuple:
    """Frame evidence for `off`: decode linearly from each of the `back`
    preceding bytes and count how many walks land exactly on `off` versus
    stepping over it. A site nobody syncs onto is not thereby misframed --
    it may simply be preceded by data (a dispatch table, padding) that no
    linear walk can decode into alignment. Read the pair, not either half."""
    onto = over = 0
    for b in range(1, back + 1):
        i = off - b
        if i < 0:
            continue
        while i < off:
            i += OPCODE_LEN[d[i]]
        if i == off:
            onto += 1
        else:
            over += 1
    return onto, over


# Transcribed from ec/annotations/charge-profile-flow.md, which took them
# from `r2 -a 8051` against a make_bank_image.py bank-0 image. If a change
# to the tables above breaks one of these, the tables are wrong, not the
# listing -- and that listing is re-read on every run rather than only
# cited here, so a corrected one fails the mode instead of outliving it.
SELF_TEST = [
    (0xB12C, [
        (0xB12C, "mov  dptr,#0x078e"),
        (0xB12F, "movx a,@dptr"),
        (0xB130, "orl  a,#0x08"),
        (0xB132, "movx @dptr,a"),
        (0xB133, "mov  dptr,#0x0741"),
        (0xB136, "movx a,@dptr"),
        (0xB137, "jb   acc.0,0xb141"),
        (0xB13A, "mov  dptr,#0x07a6"),
        (0xB13D, "movx a,@dptr"),
        (0xB13E, "anl  a,#0xcf"),
        (0xB140, "movx @dptr,a"),
    ]),
    (0xB2E2, [
        (0xB2E2, "mov  dptr,#0x07a6"),
        (0xB2E5, "movx a,@dptr"),
        (0xB2E6, "anl  a,#0x30"),
        (0xB2E8, "mov  r7,a"),
        (0xB2E9, "cjne r7,#0x20,0xb2f0"),
        (0xB2EC, "mov  r3,#0xc8"),
        (0xB2EE, "sjmp 0xb35e"),
    ]),
]

# Relative-branch sites hand-decoded with `r2 -a 8051` against a
# make_bank_image.py bank-0 image, as (file offset, runtime address, bytes,
# target); the transcripts are in ../annotations/bank-call-audit.md 8, and
# that section is re-read on every run too -- on bytes and target, never on
# the text, because §8 quotes r2 verbatim where charge-profile-flow.md writes
# in this module's own style. Two are from the SELF_TEST windows above and two
# are backward branches, which those windows do not contain -- 0xFE24 doubles
# as the last-byte check, since reading its displacement from d[i + 1] would
# give 0xFE08 rather than 0xFE0F.
REL_SITES = (
    (0x0B2EE, 0xB2EE, b"\x80\x6e", 0xB35E),
    (0x0B137, 0xB137, b"\x20\xe0\x07", 0xB141),
    (0x0F1B0, 0xF1B0, b"\xdf\xe6", 0xF198),
    (0x0FE24, 0xFE24, b"\x30\xe1\xe8", 0xFE0F),
)

# The bit-addressed carry forms, as (file offset, runtime address, bytes,
# expected text). The expected text is transcribed from `r2 -a 8051` against a
# make_bank_image.py bank-0 image, and every site is in bank 0 or the common
# area, where the runtime address and the file offset are the same number --
# which is what lets the bytes be read out of the raw image the way REL_SITES
# does, and is why a bank-1 site (the `djnz` at 0xA599) is not here.
#
# These are the opcodes the two windows above do not contain, and the ones
# verify_gap_text.py needs to judge: `cpl bit` and `mov bit,c` are 32 of the 143
# instructions sdas8051 cannot re-encode, and before the cases were added this
# table would print `db` for the 19 `mov bit,c` among them -- a comparison that
# can only agree vacuously. `0x8044` is the AJMP the 8051 manual's page rule is
# usually argued from (see GAP_MNEMONICS in verify_reassembly.py).
BIT_SITES = (
    (0x08044, 0x8044, b"\x81\x5d", "ajmp 0x845d"),
    (0x09287, 0x9287, b"\x92\xa0", "mov  p2.0,c"),
    (0x0D783, 0xD783, b"\x92\xe4", "mov  acc.4,c"),
    (0x03FED, 0x3FED, b"\x92\x48", "mov  0x29.0,c"),
    (0x0D77C, 0xD77C, b"\xa2\xe0", "mov  c,acc.0"),
    (0x0EDA4, 0xEDA4, b"\xa2\x22", "mov  c,0x24.2"),
    (0x0E064, 0xE064, b"\xa0\x05", "orl  c,/0x20.5"),
    (0x0D458, 0xD458, b"\xa0\xd4", "orl  c,/psw.4"),
    (0x0A354, 0xA354, b"\xb0\x02", "anl  c,/0x20.2"),
    (0x07251, 0x7251, b"\xb2\xd5", "cpl  psw.5"),
    (0x067F5, 0x67F5, b"\xb2\xb4", "cpl  p3.4"),
)

# CLR bit has no entry in BIT_SITES because this firmware contains no
# instruction-start byte 0xC1 at all (measured over every committed listing,
# and why verify_reassembly.BIT_UNSUPPORTED calls it a latent hole rather than
# a live one). Its encoding is therefore stated here from the 8051 manual
# rather than transcribed from the image, in the same spirit as
# verify_reassembly.self_test()'s textbook encodings: an oracle derived from
# the tool it is testing asserts nothing. The pairing below is what the
# assertion is for -- 0xC1 and 0xC2 differ only in the opcode, and a decoder
# that keyed on the operand text would collapse them.
TEXTBOOK_BIT_SITES = (
    (b"\xc1\xd0", "clr  psw.0", "CLR bit (0xC1)"),
    (b"\xc2\xd0", "clr  0xd0", "CLR direct (0xC2)"),
)

DEFAULT_FIRMWARE = "../firmware/GMxMGxx_11.800"
DEFAULT_ANNOTATIONS = "../annotations"
BANK0_FILE_OFFSET = 0x08000


def self_test(fw_path: str, annotations: str = None) -> int:
    d = open(fw_path, "rb").read()
    # Same stitching make_bank_image.py does for bank 0, in memory.
    image = d[0:0x8000] + d[BANK0_FILE_OFFSET:BANK0_FILE_OFFSET + 0x8000]
    bad = 0
    # The two files SELF_TEST and REL_SITES were transcribed out of, re-read
    # here, so an edit to either is a red run rather than a literal that has
    # quietly stopped matching its own provenance. The import is inside this
    # function because eleven tools under ec/tools/ import the module above for
    # its opcode tables and none of them wants a --self-test-only dependency on
    # a markdown parser; the sibling is resolved off __file__ rather than off
    # the cwd, so the gate's cwd is irrelevant here exactly as it is for
    # main()'s firmware default.
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    import disasm8051_oracle as oracle

    reconciled, drift, untranscribed = oracle.reconcile(
        annotations or here / DEFAULT_ANNOTATIONS, SELF_TEST, REL_SITES)
    for problem in drift:
        bad += 1
        print(f"  !   {problem}")
    if untranscribed:
        lo, hi, n = untranscribed
        # Reported, not a finding: a third block the table has never carried,
        # so nothing above checks it and the line says so rather than letting
        # "the two windows" read as "the file".
        print(f"  --  {n} rows at 0x{lo:04X}..0x{hi:04X} in "
              f"{oracle.CHARGE_PROFILE_FLOW} are transcribed and are not in "
              f"SELF_TEST, so nothing here checks them")
    print(f"  {'ok ' if not drift else '!  '} {reconciled} transcribed rows in "
          f"SELF_TEST and REL_SITES re-read from ec/annotations/ and reconciled")
    print()
    for start, expected in SELF_TEST:
        got = [(a, text) for a, _, text in
               decode(image, start, len(expected), start)]
        for (want_a, want_t), (got_a, got_t) in zip(expected, got):
            mark = " "
            if (want_a, want_t) != (got_a, got_t):
                mark = "!"
                bad += 1
            print(f"  {mark} 0x{got_a:04x}  {got_t:<24} expected 0x{want_a:04x}  {want_t}")
        print()
    for foff, rt, raw, want in REL_SITES:
        got = relative_target(raw[0], raw[-1], rt)
        ok = d[foff:foff + len(raw)] == raw and got == want
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else '!  '} file 0x{foff:05X} (runtime 0x{rt:04X}) is "
              f"`{raw.hex(' ')}` targeting 0x{want:04X} "
              f"(got `{d[foff:foff + len(raw)].hex(' ')}` -> 0x{got:04X})")
    print()
    for foff, rt, raw, want in BIT_SITES:
        got = mnemonic(image, rt, rt)
        ok = d[foff:foff + len(raw)] == raw and got == want
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else '!  '} file 0x{foff:05X} (runtime 0x{rt:04X}) is "
              f"`{raw.hex(' ')}` = `{got}`  (expected `{want}`, image has "
              f"`{d[foff:foff + len(raw)].hex(' ')}`)")
    for raw, want, what in TEXTBOOK_BIT_SITES:
        got = mnemonic(raw, 0, 0)
        ok = got == want
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else '!  '} `{raw.hex(' ')}` = `{got}`  ({what}, "
              f"expected `{want}`)")
    # The page rule's edge, stated rather than transcribed: this firmware has
    # no `ajmp`/`acall` in the last two bytes of a 2 KiB page, so there is no
    # site to hand-read. The arithmetic is the claim under test -- a site at
    # 0x07FE is followed by 0x0800, which is in the *next* page, so its target
    # takes A15-A11 from 0x0800 and lands at 0x08FF. Reading the page off the
    # site instead would give 0x00FF, a whole 2 KiB page away, and every
    # `ajmp` in the listing would still decode to something.
    edge = paged_target(0x01, 0xFF, 0x07FE)
    if edge != 0x08FF:
        bad += 1
    print(f"  {'ok ' if edge == 0x08FF else '!  '} `01 ff` at 0x07FE targets "
          f"0x{edge:04X}, the *following* page (expected 0x08FF)")
    print()
    if bad:
        print(f"self-test FAILED: {bad} instruction(s)/site(s) disagree with "
              "ec/annotations/charge-profile-flow.md, bank-call-audit.md 8 and "
              "the `r2 -a 8051` transcriptions in BIT_SITES")
    else:
        print("self-test passed: both charge-profile-flow.md windows decode "
              f"identically, all {len(REL_SITES)} relative-branch sites resolve "
              f"as hand-decoded, and all {len(BIT_SITES)} bit-form sites decode "
              "as transcribed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=None,
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--self-test", action="store_true",
                    help="decode the charge-profile-flow.md windows and diff against them")
    ap.add_argument("--at", help="file offset to decode from, e.g. 0x23478")
    ap.add_argument("-n", type=int, default=8, help="instructions to decode (default 8)")
    ap.add_argument("--runtime", help="runtime address of --at, for absolute branch targets")
    ap.add_argument("--converge", action="store_true",
                    help="report the frame evidence for --at instead of decoding")
    args = ap.parse_args()

    if args.self_test:
        here = __file__.rsplit("/", 1)[0]
        return self_test(args.firmware or f"{here}/{DEFAULT_FIRMWARE}")

    if not args.firmware or not args.at:
        ap.error("give a firmware image and --at OFFSET, or --self-test")

    d = open(args.firmware, "rb").read()
    off = int(args.at, 16)
    if args.converge:
        onto, over = converges_from(d, off)
        print(f"0x{off:05X}: {onto} of {onto + over} preceding anchors decode onto it, "
              f"{over} step over it")
        return 0

    rt = int(args.runtime, 16) if args.runtime else None
    for i, raw, text in decode(d, off, args.n, rt):
        shown = f"0x{rt + (i - off):04x}" if rt is not None else f"0x{i:05x}"
        print(f"{shown}  {raw.hex():<8} {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
