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
it after touching either.

Usage:
    python3 disasm8051.py --self-test
    python3 disasm8051.py ../firmware/GMxMGxx_11.800 --at 0x23478 -n 12
    python3 disasm8051.py ../firmware/GMxMGxx_11.800 --at 0x23478 --converge
"""
import argparse
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


def mnemonic(d: bytes, i: int, addr: int = None) -> str:
    """Render the instruction at d[i]. `addr` is that instruction's runtime
    address; supply it to get absolute branch targets, omit it to get the
    raw displacement byte."""
    op = d[i]

    def rel(n: int) -> str:
        if addr is None:
            return f"+0x{d[i + n]:02x}"
        disp = d[i + n] - 256 if d[i + n] > 127 else d[i + n]
        return f"0x{(addr + OPCODE_LEN[op] + disp) & 0xFFFF:04x}"

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
    if op in (0xD2, 0xC2, 0xB2):
        name = {0xD2: "setb", 0xC2: "clr", 0xB2: "cpl"}[op]
        return f"{name:<4} {bit_name(d[i + 1])}"
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
    `addr` is the runtime address of d[start], if it differs from start."""
    i = start
    for _ in range(count):
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
# listing.
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

DEFAULT_FIRMWARE = "../firmware/GMxMGxx_11.800"
BANK0_FILE_OFFSET = 0x08000


def self_test(fw_path: str) -> int:
    d = open(fw_path, "rb").read()
    # Same stitching make_bank_image.py does for bank 0, in memory.
    image = d[0:0x8000] + d[BANK0_FILE_OFFSET:BANK0_FILE_OFFSET + 0x8000]
    bad = 0
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
    if bad:
        print(f"self-test FAILED: {bad} instruction(s) disagree with "
              "ec/annotations/charge-profile-flow.md")
    else:
        print("self-test passed: both charge-profile-flow.md windows decode identically")
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
