#!/usr/bin/env python3
"""Execute mul_16_round_shift_subtract (bank1 0xA5E6) and say which register
holds which byte of its quotient.

Issue #358. PR #200 read 0xA5E6 as leaving "the quotient's high byte in R1,
its low byte in R2" and built `windows/tools/system_id_probe.py` on that
reading, while the listing says the other way round: the shift at 0xA5EE
touches R1 first, and the epilogue at 0xA613 copies R0 into R1.

**The point of this tool is that the roles are a consequence of the committed
bytes rather than a reading of them.** It parses ec/decompiled/bank1/A5E6.asm,
runs the instruction stream on a small 8051 core, and compares the two result
pairs -- the quotient in R1:R2 and the remainder in R3:R4 -- against an
independent Python model of shift-and-subtract written from the algorithm
rather than from the listing. Two implementations, one machine: a disagreement
is a red run, not a caveat. The other four registers hold nothing this leaves
behind: the epilogue's own copies are what put them there, so a disagreement
about a result pair cannot be a disagreement about them. The opcodes are not
arbitrated here -- `verify_reassembly.py --check` already holds them against
the firmware, and this file reads the listing that check arbitrates.

The core covers only what 0xA5E6, the four functions in `FAMILIES`, and
`halve_sum_into_044c` (bank1 0xF436) use. It raises `Unsupported` on anything
else rather than skipping, so a listing that grows an instruction this core
cannot execute is a loud failure and not a silently short run.

Modes:
    python3 a5e6_quotient.py                    # reconcile, print the roles
    python3 a5e6_quotient.py --callers          # every lcall 0xA5E6 site
    python3 a5e6_quotient.py --capture PATH     # reachability against a capture,
                                                # then 0x044C through 0xF436

Standard library only, no Ghidra, no ecrw, nothing opened for writing.
"""
import argparse
import csv
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

LISTING = HERE.parent / "decompiled" / "bank1" / "A5E6.asm"
F436_LISTING = HERE.parent / "decompiled" / "bank1" / "F436.asm"
FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
CALL_TARGETS = HERE.parent / "annotations" / "bank-call-targets.csv"
INDEX = HERE.parent / "decompiled" / "index.csv"

# The runtime address whose operand roles this tool exists to settle, and the
# divisor/mask constants its callers are read through.
A5E6 = 0xA5E6
DIVISORS = (0x22, 0x44)

# `halve_sum_into_044c` (bank1 0xF436) is the one caller whose result is
# compared against another captured byte rather than against this tool's own
# inputs, so it gets its own listing: it multiplies 0x0449 by 0x0448, divides
# by the constant 100 its own 0xF444 row loads, and folds the clamped
# quotient's low byte into 0x044C. What 0x0448 holds is *not* read from the
# profile-switch capture -- that file carries no 0x0448 at all -- so it is an
# input, and 0xBE is the value `scale_0438_into_0448`'s other arm stores.
# 0xA0 is here as a second input so the conclusion can be seen not to be an
# artifact of the byte the constant happens to be.
F436_BODY = 0xF436
MULTIPLICANDS = (0xBE, 0xA0)
SRC_0449, SRC_0448, DST_044C = 0x0449, 0x0448, 0x044C

# Which rows settle the operand roles. The addresses are named so the report
# can cite them, but they select rows and say nothing about what those rows do:
# the direction comes out of the text, so a listing that swapped an operand
# would be reported as having swapped it rather than checked against a table
# written beside it. `0xA613`-`0xA61C` are the four `mov 0x0n,0x0m` copies and
# `0xA60A`/`0xA60D` the two `mov A,Rn` the quotient bit enters.
EPILOGUE_ADDRS = (0xA613, 0xA616, 0xA619, 0xA61C)
ACCUMULATOR_ADDRS = (0xA60A, 0xA60D)

# The 16-bit operand pair every helper in `FAMILIES` takes, named so the two
# places that ask which half is low read as a question about a pair rather
# than as a string comparison.
OPERAND_PAIR = ("R1", "R2")


class Unsupported(Exception):
    """An opcode this core does not execute. Raised, never skipped."""


def _direct(token):
    """A direct-address operand as its register number, rejecting anything else.

    Only 0x00-0x07 is a register of the file `Core` executes; a larger direct
    address is DPL, DPH or B and naming it "R130" would read as a finding.
    """
    n = int(token, 16)
    if not 0 <= n < 0x08:
        raise Unsupported(f"0x{token} is not one of R0-R7")
    return n


def _direct_move(text):
    """(destination, source) of a `mov 0x0n,0x0m` row, as register names."""
    parts = text.replace(",", " ").split()
    if len(parts) != 3 or parts[0] != "mov":
        raise Unsupported(f"{text!r} is not a direct-to-direct mov")
    dst, src = parts[1], parts[2]
    return f"R{_direct(dst)}", f"R{_direct(src)}"


def _into_a(text):
    """The register a `mov A, Rn` row reads."""
    parts = text.replace(",", " ").split()
    if len(parts) != 3 or parts[0] != "mov" or parts[1] != "A":
        raise Unsupported(f"{text!r} is not a mov into A")
    return parts[2]


class Core:
    """The 8051 subset 0xA5E6, the families below and 0xF436 need, and no more.

    `r` is the register file as R0..R7; direct addresses 0x00-0x07 are the same
    eight bytes, which is what makes `mov 0x02,0x05` at 0xA613 a move into R2
    without a special case. `dpl`/`dph` and `b` are the other direct addresses
    these listings touch (0x82, 0x83, 0xF0). `xdata` is a sparse external data
    space, held as a plain dict because only three addresses are ever read and
    written here and 0x00 is as good a stand-in for an unwritten byte as any:
    what the listings below do with 0x0448, 0x0449 and 0x044C does not depend
    on what any other address holds.
    """

    REGISTERS = ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7")

    def __init__(self, **kw):
        self.r = list(kw.pop("regs", [0] * 8))
        self.a = kw.pop("a", 0)
        self.b = kw.pop("b", 0)
        self.cy = kw.pop("cy", 0)
        self.dpl = kw.pop("dpl", 0)
        self.dph = kw.pop("dph", 0)
        self.xdata = dict(kw.pop("xdata", {}))
        if kw:
            raise TypeError(f"unexpected core state {sorted(kw)}")

    def read(self, addr):
        if addr < 0x08:
            return self.r[addr]
        return {0x82: self.dpl, 0x83: self.dph, 0xF0: self.b}.get(addr, 0)

    def write(self, addr, value):
        value &= 0xFF
        if addr < 0x08:
            self.r[addr] = value
            return
        if addr == 0x82:
            self.dpl = value
        elif addr == 0x83:
            self.dph = value
        elif addr == 0xF0:
            self.b = value
        # Anything else is scratch this helper never reads back; dropping the
        # write would be wrong and raising would be noise, so it is ignored.


def _is_byte(token):
    """A hex-column token: two hex digits. `-` is padding, not a byte."""
    return len(token) == 2 and all(c in "0123456789abcdefABCDEF" for c in token)


def parse_listing(path=None):
    """The listing's instructions as (address, mnemonic, operand-bytes) rows.

    The address column is what addresses are keyed by and the hex column is
    what is executed; both come out of the committed `.asm`, so a listing
    this tool cannot read is a build problem rather than a silent zero.
    """
    path = path or LISTING
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(";") or line[0] not in "0123456789ABCDEF":
            continue
        addr, _, rest = line.partition(" ")
        # "A5E6  7f 00 -  mov R7, #0x0": the hex column is padded to a fixed
        # width with `-`, and the mnemonic follows it with no separator of its
        # own. So the bytes are the leading two-hex-digit tokens and the text
        # is everything after the padding, which is found rather than assumed
        # -- a fixed column would put `-` in the mnemonic text.
        parts = rest.split()
        raw = []
        i = 0
        while i < len(parts) and _is_byte(parts[i]):
            raw.append(parts[i])
            i += 1
        while i < len(parts) and parts[i] == "-":
            i += 1
        text = " ".join(parts[i:])
        if not raw or not text:
            continue
        rows.append((int(addr, 16), text, bytes(int(b, 16) for b in raw)))
    if not rows:
        raise ValueError(f"no instructions parsed out of {path}")
    return rows


def step(core, addr, raw, stack=None):
    """Execute one instruction. Returns the next runtime address.

    Only the opcodes 0xA5E6, the functions in `FAMILIES`, and `F436_BODY`
    use are handled. Anything else raises, so an instruction this core cannot
    execute stops the run where it is rather than being treated as a no-op --
    which would let the comparison below pass on a partial run.

    `stack` is the call return stack `run()` threads through; without it an
    `lcall` has nowhere to come back to and raises rather than jumping into a
    listing that is not there.
    """
    op = raw[0]
    nxt = addr + len(raw)
    imm8 = raw[1] if len(raw) > 1 else 0
    imm16 = (raw[1] << 8 | raw[2]) if len(raw) > 2 else 0

    # mov A,Rn / mov Rn,A / mov A,#d / mov Rn,#d
    if 0xE8 <= op <= 0xEF:
        core.a = core.r[op - 0xE8]
    elif 0xF8 <= op <= 0xFF:
        core.r[op - 0xF8] = core.a
    elif op == 0x74:
        core.a = imm8
    elif 0x78 <= op <= 0x7F:
        core.r[op - 0x78] = imm8
    # mov direct,Rn / mov direct,A / mov direct,#d / mov direct,direct
    elif 0x88 <= op <= 0x8F:
        core.write(imm8, core.r[op - 0x88])
    elif op == 0xF5:
        core.write(imm8, core.a)
    elif op == 0x75:
        core.write(imm8, raw[2])
    elif op == 0x85:
        # MOV direct,direct encodes the SOURCE first: `85 07 04` is R4 <- R7.
        # The listing renders it the other way round as `mov 0x04, 0x07`, so
        # taking the bytes in the order the text reads them swaps the whole
        # epilogue and every result with it.
        core.write(raw[2], core.read(raw[1]))
    # mov Rn,direct / mov A,direct
    elif 0xA8 <= op <= 0xAF:
        core.r[op - 0xA8] = core.read(imm8)
    elif op == 0xE5:
        core.a = core.read(imm8)
    # movx A,@DPTR / movx @DPTR,A. DPTR is the whole operand, so it is
    # formed as it stands rather than tracked as a separate pointer.
    elif op == 0xE0:
        core.a = core.xdata.get(core.dpl | core.dph << 8, 0)
    elif op == 0xF0:
        core.xdata[core.dpl | core.dph << 8] = core.a
    # mul AB is B:A <- A*B, so A is the low half, B the high one, and it
    # clears CY. Reading it the other way round halves every product this
    # tool feeds it, and 0xF436's clamp cannot tell the difference.
    elif op == 0xA4:
        product = core.a * core.b
        core.a, core.b, core.cy = product & 0xFF, (product >> 8) & 0xFF, 0
    elif op == 0x12:                       # lcall addr16
        if stack is None:
            raise Unsupported(f"0x{addr:04X}: lcall with no return stack")
        stack.append(nxt)
        nxt = imm16
    # add/adc/subb A,Rn and A,direct
    elif 0x28 <= op <= 0x2F:
        core.a, core.cy = _add(core.a, core.r[op - 0x28], core.cy)
    elif 0x38 <= op <= 0x3F:
        core.a, core.cy = _add(core.a, core.r[op - 0x38], core.cy)
    elif op == 0x34:                       # addc A,#d
        core.a, core.cy = _add(core.a, imm8, core.cy)
    elif 0x94 <= op <= 0x97:
        core.a, core.cy = _sub(core.a, core.read(imm8), core.cy)
    elif 0x98 <= op <= 0x9F:
        core.a, core.cy = _sub(core.a, core.r[op - 0x98], core.cy)
    # rlc/rrc A, clr/cpl/setb CY. The carry direction is the whole of 0xA5E6's
    # dividend shift, so it is written out rather than folded: `rlc` puts the
    # old bit 7 into CY and CY into bit 0, and `rrc` is the mirror.
    elif op == 0x33:
        raw_carry = ((core.a << 1) | core.cy)
        core.a, core.cy = raw_carry & 0xFF, (raw_carry >> 8) & 1
    elif op == 0x13:
        raw_carry = (core.a >> 1) | (core.cy << 7)
        core.a, core.cy = raw_carry & 0xFF, core.a & 1
    elif op == 0xC3:
        core.cy = 0
    elif op == 0xB3:
        core.cy ^= 1
    elif op == 0xD3:
        core.cy = 1
    # inc A / inc direct
    elif op == 0x04:
        core.a = (core.a + 1) & 0xFF
    elif op == 0x05:
        core.write(imm8, (core.read(imm8) + 1) & 0xFF)
    # the PC-relative family: the displacement is signed and relative to the
    # *next* instruction, which is why nxt rather than addr is the base.
    elif op in (0x40, 0x50, 0x60, 0x70):
        take = {0x40: core.cy == 1, 0x50: core.cy == 0,
                0x60: core.a == 0, 0x70: core.a != 0}[op]
        if take:
            nxt = nxt + (imm8 - 256 if imm8 > 127 else imm8)
    elif op == 0x80:                       # sjmp
        nxt = nxt + (imm8 - 256 if imm8 > 127 else imm8)
    elif 0xD8 <= op <= 0xDF:               # djnz Rn,rel
        core.r[op - 0xD8] = (core.r[op - 0xD8] - 1) & 0xFF
        if core.r[op - 0xD8]:
            nxt = nxt + (imm8 - 256 if imm8 > 127 else imm8)
    elif op == 0xD5:                       # djnz direct,rel
        # Three bytes, and the displacement is the *third*: raw[1] is the
        # direct address being decremented. Reading it as the displacement
        # turns the loop's back-edge into a jump into the middle of the
        # subtract, which is a wrong answer rather than a crash.
        core.write(imm8, (core.read(imm8) - 1) & 0xFF)
        if core.read(imm8):
            nxt = nxt + (raw[2] - 256 if raw[2] > 127 else raw[2])
    elif 0xB8 <= op <= 0xBF:               # cjne Rn,#d,rel
        i = op - 0xB8
        if core.r[i] != imm8:
            nxt = nxt + (raw[2] - 256 if raw[2] > 127 else raw[2])
    elif op == 0x22 or op == 0x32:         # ret / retl
        # An empty stack means this run started at the function, so the ret
        # is the end of it. A non-empty one means it came back from an
        # `lcall` and there is an address to resume at.
        if stack:
            nxt = stack.pop()
        else:
            return None
    elif op == 0x90:                       # mov DPTR,#imm16
        core.dph, core.dpl = imm16 >> 8, imm16 & 0xFF
    else:
        raise Unsupported(f"0x{addr:04X}: opcode 0x{op:02X} is not executed "
                          f"by this core")
    return nxt


def _add(a, b, cy):
    """(value, carry-out) for the 8051's `add`. The carry out of bit 7 is CY."""
    raw = a + b + cy
    return raw & 0xFF, 1 if raw > 0xFF else 0


def _sub(a, b, cy):
    """(value, borrow) for `subb`. The borrow out of bit 7 is CY."""
    raw = a - b - cy
    return raw & 0xFF, 1 if raw < 0 else 0


def run(rows, core=None, limit=100000, extra=(), watch=None):
    """Execute a parsed listing from its first instruction.

    `limit` is a backstop against a listing whose branches do not terminate.
    A run that hits it raises rather than returning a partial register state,
    because a partial state compared against a model would read as a
    disagreement rather than as the bug it is.

    `extra` merges further listings into the same address table, which is how
    a `lcall` into a second committed listing is executed rather than
    modelled. An address two listings both claim raises, because a silent
    shadow would run one function's bytes under another's name and the whole
    point of this tool is that the bytes are what it ran.

    `watch` maps an address to a callable taking the core, invoked just
    before that address executes. It exists for the one thing committed bytes
    cannot produce -- the reading where 0xA5E6's epilogue assigned the halves
    of the quotient the other way round -- which is a different machine, not
    a different function.
    """
    core = core if core is not None else Core()
    table = {addr: (text, raw) for addr, text, raw in rows}
    for more in extra:
        clash = set(table) & {addr for addr, _, _ in more}
        if clash:
            raise Unsupported(
                f"{len(clash)} address(es) in two listings, first at "
                f"0x{min(clash):04X}")
        table.update({addr: (text, raw) for addr, text, raw in more})
    stack = []
    pc = rows[0][0]
    for _ in range(limit):
        if pc not in table:
            raise Unsupported(f"0x{pc:04X} is not an instruction in this "
                              f"listing")
        if watch and pc in watch:
            watch[pc](core)
        _, raw = table[pc]
        nxt = step(core, pc, raw, stack)
        if nxt is None:
            return core
        pc = nxt
    raise Unsupported(f"listing did not terminate within {limit} instructions")


def model(dividend, divisor):
    """Shift-and-subtract, written from the algorithm and not from the listing.

    Sixteen rounds; each shifts the 32-bit dividend left one bit, compares the
    high half against the divisor, subtracts it back when it fits, and shifts
    the compare's outcome into the low accumulator. Returns (quotient,
    remainder) as the 16-bit pair the helper leaves in R1:R2 and R3:R4 under
    the corrected reading -- which is the claim under test, so this function
    computes it the way the algorithm says rather than by reading registers.
    """
    high = 0                      # R6:R7, the growing half
    low = 0                       # R0:R5, the quotient accumulators
    for _ in range(16):
        bit = (dividend >> 15) & 1
        dividend = (dividend << 1) & 0xFFFF
        high = ((high << 1) | bit) & 0xFFFF
        if high >= divisor:
            high -= divisor
            low = ((low << 1) | 1) & 0xFFFF
        else:
            low = (low << 1) & 0xFFFF
    return low, high


def listing_quotient(dividend, divisor, rows=None):
    """The same quotient as the listing produces it, register for register."""
    core = Core(regs=[0, dividend & 0xFF, dividend >> 8, divisor & 0xFF,
                      divisor >> 8, 0, 0, 0])
    core = run(rows if rows is not None else parse_listing(), core)
    return core


def reconcile(rows=None, cases=None):
    """Run both implementations over `cases` and report every disagreement.

    What is compared is the two result pairs the helper returns -- the
    quotient in R1:R2 and the remainder in R3:R4 -- not all eight registers.
    R0, R5, R6 and R7 are not checked because they are not results: the
    epilogue's own copies are what leave them equal to these four, so
    comparing the pairs compares everything the helper hands back.

    Returns (checked, disagreements). A disagreement is a list of
    (dividend, divisor, listing_pairs, model_pairs) rather than a count, so
    the caller can print the bytes that differ instead of a total.
    """
    rows = rows if rows is not None else parse_listing()
    cases = cases if cases is not None else sweep()
    bad = []
    for dividend, divisor in cases:
        core = listing_quotient(dividend, divisor, rows)
        q, r = model(dividend, divisor)
        got = (core.r[1] | core.r[2] << 8, core.r[3] | core.r[4] << 8)
        if got != (q, r):
            bad.append((dividend, divisor, got, (q, r)))
    return len(cases), bad


def sweep():
    """Inputs that cross the byte boundary in both directions, both ways round.

    Dividends and divisors are swept across 0x100 and 0x10000 so a swapped
    result byte cannot pass, and both shift-out regimes are represented: a
    dividend whose top bit is clear (the quotient fits the low accumulator
    alone) and one where it is set (R5 has to take a carry). Values with
    interesting bit patterns are added by hand because a regular stride walks
    past them.
    """
    cases = set()
    for dividend in (0x0000, 0x0001, 0x00FF, 0x0100, 0x0101, 0x00FE, 0x7FFF,
                     0x8000, 0x8001, 0x00C8, 0x03F0, 0x7FFF, 0xFFFF, 0xABCD,
                     0x1234, 0x5678, 0xAAAA, 0x5555):
        for divisor in (0x0001, 0x0002, 0x0022, 0x0044, 0x0064, 0x00FF, 0x0100,
                        0x0101, 0x7FFF, 0x8000, 0xFFFF, 0x0100, 0x00C8):
            cases.add((dividend, divisor))
    for dividend in range(0x0000, 0x0200, 7):
        for divisor in (0x0022, 0x0044, 0x0064):
            cases.add((dividend, divisor))
    return sorted(cases)


# --- the two conventions, and which family a helper is in --------------------

# The helpers the write-up compares 0xA5E6 against, named only; what each one
# does with the order is read out of its listing by `family_low()` below rather
# than asserted here. A helper whose first-touched operand register is R1 is
# treating R1 as the low byte of a 16-bit value, and one that touches R2 first
# is not -- both readings are correct for their own helper, and that is the
# whole of the distinction `system_id_probe.py` lost.
FAMILIES = (0x8844, 0x8854, 0x885B)


def family_low(addr, rows=None):
    """Which register holds the low byte of a helper's 16-bit operand pair.

    Read off the listing rather than asserted, because the two families differ
    only in an order no prose can settle and a swapped byte cannot detect.

    Two shapes, and they need different questions:

      * A shifting helper (0x8844) shifts one register and then the other, so
        the one it shifts *first* is the low byte -- the carry propagates from
        it into the second.
      * An adding or subtracting helper (0x8854, 0x885B) reads its operand
        into R3:R4, so the first register it moves is the *accumulator's* low
        byte and says nothing about the addend. What decides the addend is
        which of R1/R2 is combined with it *without* a carry-in, since that is
        the low byte's position.

    `rows` is `parse_listing`'s output, so a caller (and the suite) can ask
    the question of a listing other than the one `addr` names.

    Returns "R1" or "R2", or None when the listing is not one of those two
    shapes -- which is a loud "this helper is a third kind" rather than a
    default the caller would report as a finding.
    """
    if rows is None:
        rows = parse_listing(
            HERE.parent / "decompiled" / "bank1" / f"{addr:04X}.asm")
    parsed = []
    for _addr, text, _raw in rows:
        parts = text.replace(",", " ").split()
        parsed.append(parts)

    def first_shifted():
        """The first R1/R2 the listing reads into A, for a shifting helper."""
        for parts in parsed:
            if len(parts) >= 3 and parts[0] == "mov" and parts[1] == "A" \
                    and parts[2] in OPERAND_PAIR:
                return parts[2]
        return None

    def first_added():
        """The R1/R2 combined without a carry-in, for an add/sub helper."""
        for parts in parsed:
            # `add A,Rn` has no carry-in and `addc A,Rn` has one, so the
            # mnemonic itself distinguishes the low byte from the high one.
            if len(parts) == 3 and parts[0] in ("add", "subb") \
                    and parts[2] in OPERAND_PAIR:
                return parts[2]
        return None

    shifted, added = first_shifted(), first_added()
    return shifted if shifted else added


def epilogue_moves(rows=None):
    """The epilogue's (destination, source) pairs, from the listing's own text.

    The four `mov 0x0n,0x0m` rows at 0xA613-0xA61C are what copy the
    accumulators out, and which is which is the whole claim, so both ends of
    every pair are parsed out of the row rather than written down beside it.
    The listing renders MOV direct,direct destination-first (`85 07 04` is
    R4 <- R7 and is printed `mov 0x04, 0x07`), so the first operand is the one
    that receives.

    Direct addresses 0x00-0x07 are R0-R7 -- the same identity `Core.read` and
    `Core.write` already hold them to, so there is no second mapping here to
    disagree with.
    """
    rows = rows if rows is not None else parse_listing()
    return [(addr, _direct_move(text)) for addr, text, _raw in rows
            if addr in EPILOGUE_ADDRS]


def accumulator_steps(rows=None):
    """Which accumulator each `mov A, Rn` of the quotient step feeds.

    0xA60A shifts the compare's outcome into R0 and 0xA60D shifts R0's
    carry-out into R5, so the register touched first is the low half -- the
    same "first shifted is low" rule 0xA5E6's own dividend shift follows, and
    the one that made the high-byte reading look plausible in the first place.

    The register is the operand of the row, not a constant beside it, so a
    listing that swapped the two accumulators would be reported as having
    swapped them.
    """
    rows = rows if rows is not None else parse_listing()
    return [(addr, _into_a(text)) for addr, text, _raw in rows
            if addr in ACCUMULATOR_ADDRS]


def roles(rows=None):
    """The operand roles, each one cited to the listing address that fixes it."""
    rows = rows if rows is not None else parse_listing()
    return {
        "dividend_shift": [(addr, text) for addr, text, _raw in rows
                           if 0xA5EE <= addr <= 0xA5F9],
        "accumulator": accumulator_steps(rows),
        "epilogue": epilogue_moves(rows),
    }


# --- --callers ---------------------------------------------------------------

def call_sites():
    """Every `lcall 0xA5E6` row bank-call-targets.csv holds.

    Read from the census rather than re-derived: that file is not regenerated
    by anything here (tools/README.md is explicit that re-running
    audit_call_targets.py to fix a finding asserts the tool against itself),
    so the census is the input and this tool only reports what it says.
    """
    with CALL_TARGETS.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["target"].lower() == f"0x{a5e6_hex()}":
                yield row


def a5e6_hex():
    return f"{A5E6:04X}".lower()


def enclosing(runtime):
    """The exported function a runtime address falls inside, from index.csv.

    `index.csv` is sorted by nothing this tool controls, so the match is the
    highest-addressed function that starts at or below `runtime` and whose
    size reaches it -- computed from the two columns together rather than
    from the row order.
    """
    best = None
    with INDEX.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["program"] != "bank1":
                continue
            addr = int(row["addr"], 16)
            size = int(row["size"] or 0)
            if addr <= runtime < addr + max(size, 1):
                if best is None or addr > int(best["addr"], 16):
                    best = row
    return best


def is_real_lcall(runtime):
    """Whether the image at `runtime` holds a real `lcall 0xA5E6`.

    Read out of the firmware rather than out of the census's `target` column,
    so a census row the image does not support is visible as such instead of
    passing through unexamined. The offset is bank1's own window (0x10000 for
    the 0x8000-0xFFFF bank area), which is `build_ec_decompile.py`'s
    BANK_WINDOWS and `make_bank_image.py`'s, not a constant invented here.
    """
    image = FIRMWARE.read_bytes()
    off = 0x10000 + runtime - 0x8000 if runtime >= 0x8000 else runtime
    if off < 0 or off + 3 > len(image):
        return False
    return image[off:off + 3] == bytes((0x12, A5E6 >> 8, A5E6 & 0xFF))


def r1_r2_after(addr):
    """What the listing at `addr` does with R1 and R2 after the call.

    The question the issue asks of every caller, asked mechanically: which
    bytes of the result reach a store. An instruction that mentions R1 after
    the `lcall` is reported with its address and text; nothing is inferred
    about what the value means, because that is what the annotation rows are
    for and this tool cannot adjudicate them.
    """
    path = HERE.parent / "decompiled" / "bank1" / f"{addr:04X}.asm"
    if not path.exists():
        return None, None
    rows = parse_listing(path)
    call = next((i for i, (a, _, raw) in enumerate(rows)
                 if raw[:1] == b"\x12" and raw[1:3] == bytes((A5E6 >> 8,
                                                             A5E6 & 0xFF))), None)
    if call is None:
        return rows, None
    tail = [(a, text) for a, text, _ in rows[call + 1:]
            if "R1" in text or "R2" in text or "0x01" in text or "0x02" in text]
    return rows, tail


def report_callers(out=None):
    """The census of 0xA5E6's callers, and what each does with R1 and R2.

    `out` is resolved on entry rather than bound as a default argument,
    because a default of `sys.stdout` captures the stream at import time and a
    caller that redirects stdout afterwards -- a test, mostly -- would have its
    output written to the real terminal instead.
    """
    out = out or sys.stdout
    sites = list(call_sites())
    functions = {}
    for row in sites:
        runtime = int(row["runtime"], 16)
        fn = enclosing(runtime)
        key = fn["addr"] if fn else None
        functions.setdefault(key, []).append((runtime, row))

    print(f"{A5E6:#06x} call sites in bank-call-targets.csv: {len(sites)}",
          file=out)
    unlisted = []
    for key in sorted(functions, key=lambda k: int(k, 16) if k else -1):
        entries = functions[key]
        runtimes = sorted(r for r, _ in entries)
        # Every site is checked against the image rather than the census's own
        # target column. All of them decode as the call they claim, and the
        # unlisted one is included in that check rather than skipped for
        # having no listing -- "no listing" is not "not in the image".
        confirmed = [r for r in runtimes if is_real_lcall(r)]
        if len(confirmed) != len(runtimes):
            missing = sorted(set(runtimes) - set(confirmed))
            print(f"  NOT a real lcall in the image at "
                  + ", ".join(f"0x{r:04X}" for r in missing), file=out)
        if key is None:
            for runtime in runtimes:
                unlisted.append(runtime)
                print(f"  0x{runtime:04X}  in no exported function, and in no "
                      f"listing: the image holds the call, this repository "
                      f"exports nothing there", file=out)
            continue
        rows, tail = r1_r2_after(int(key, 16))
        if rows is None:
            unlisted.extend(runtimes)
            name = "(no listing)"
        else:
            name = enclosing(runtimes[0])["name"]
        print(f"  {key} {name}  called from "
              + ", ".join(f"0x{r:04X}" for r in runtimes), file=out)
        if tail is None:
            print(f"      no lcall {A5E6:#06x} inside this listing", file=out)
            continue
        for a, text in tail:
            print(f"      0x{a:04X}  {text}", file=out)
    return sites, unlisted


# --- --capture ---------------------------------------------------------------

def capture_pairs(path, addr_lo=0x060C, addr_hi=0x060D, target=0x0449):
    """The capture's own (lo, hi) pairs and the set of `target` values seen.

    Pairing is nearest-in-time on the change log: each row of an ec-watch
    capture is a `ts,addr,old,new` transition, so a pair is the most recent
    value of each input address at or before a row's timestamp. That is *not*
    a per-sample alignment -- the two bytes were not necessarily written in the
    same instant -- and it is used here only to ask whether a byte is reachable
    at all from inputs this capture contains.
    """
    events = []
    observed = set()
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            addr = int(row["addr"], 16)
            events.append((row["ts"], addr, int(row["new"], 16)))
            if addr == target:
                observed.add(int(row["new"], 16))
    events.sort(key=lambda e: (e[0], e[1]))

    state = {addr_lo: 0, addr_hi: 0}
    pairs = []
    for _, addr, new in events:
        if addr in state:
            state[addr] = new
        elif addr == target:
            pairs.append((state[addr_lo], state[addr_hi]))
    return pairs, observed


def stored_byte(lo, hi, divisor, high_byte):
    """What an arm would store under either reading of 0xA5E6's epilogue.

    `high_byte` selects the reading rather than the arithmetic: the multiply
    is 0xF3D7's own two `mul AB`s and the division is the same call either
    way, so the only thing the two readings disagree about is which half of
    the quotient reaches the store.
    """
    hi &= 0x03
    product = (((hi * 10) & 0xFF) + ((lo * 10) >> 8)) << 8 | ((lo * 10) & 0xFF)
    quotient = product // divisor
    return (quotient >> 8) & 0xFF if high_byte else quotient & 0xFF


def capture_044c_rows(path, target=SRC_0449, accumulated=DST_044C):
    """Each `target` row paired with the `accumulated` byte standing at it.

    Nearest-in-time, and no stronger than that: the two bytes were not
    written at the same instant, so the second element is the byte 0xF436
    would have read had it run at that row's timestamp. It is a starting
    value for the fold and nothing more, which is why the comparison in
    `simulate_044c` is against a set rather than against a pairing.
    """
    events = []
    observed = set()
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            addr = int(row["addr"], 16)
            events.append((row["ts"], addr, int(row["new"], 16)))
            if addr == accumulated:
                observed.add(int(row["new"], 16))
    events.sort(key=lambda e: (e[0], e[1]))

    standing = 0
    rows = []
    for _, addr, new in events:
        if addr == accumulated:
            standing = new
        elif addr == target:
            rows.append((new, standing))
    return rows, observed


def _after_lcall(rows, target):
    """The address of the instruction following this listing's `lcall target`.

    Read out of the listing rather than written down beside it, so the point
    the readings part at moves with the listing instead of with this file.
    """
    for i, (_addr, text, _raw) in enumerate(rows):
        parts = text.split()
        if len(parts) != 2 or parts[0] != "lcall":
            continue
        if int(parts[1], 16) == target:
            if i + 1 == len(rows):
                raise Unsupported(f"the lcall {target:#06x} ends the listing")
            return rows[i + 1][0]
    raise Unsupported(f"no lcall {target:#06x} in this listing")


def f436_store(value_449, value_448, value_44c, high_byte, rows=None, a5e6=None):
    """What `halve_sum_into_044c` writes to 0x044C, executed from its listing.

    The whole body runs -- the `mul AB`, the `lcall 0xa5e6` into the committed
    listing, the clamp and the halving -- on the same core everything else in
    this tool uses, because the clamp is what the two readings disagree about
    and it is in the bytes rather than in the epilogue.

    `high_byte` again selects the reading rather than the arithmetic: the same
    committed bytes are executed either way, and the machines part only
    between the `lcall` returning and the clamp reading R2, so that is where
    R1 and R2 are exchanged. Everything else -- the product, the division, the
    `jz`, the `add A, R1`, the `rrc` -- is the firmware's own.
    """
    rows = rows if rows is not None else parse_listing(F436_LISTING)
    a5e6 = a5e6 if a5e6 is not None else parse_listing(LISTING)
    if rows[0][0] != F436_BODY:
        raise Unsupported(f"{F436_LISTING.name} does not start at "
                          f"0x{F436_BODY:04X}")

    def exchange(core):
        core.r[1], core.r[2] = core.r[2], core.r[1]

    watch = {_after_lcall(rows, A5E6): exchange} if high_byte else None
    core = Core(xdata={SRC_0449: value_449, SRC_0448: value_448,
                       DST_044C: value_44c})
    core = run(rows, core, extra=(a5e6,), watch=watch)
    return core.xdata[DST_044C]


def simulate_044c(path, multiplicand=0xBE, high_byte=False):
    """Every 0x044C write the committed 0xF436 body makes over a capture.

    Returns (values, observed, inside): the simulated writes in capture order,
    the set of 0x044C values the capture actually shows, and how many of the
    simulated writes land in that set. `multiplicand` is 0x0448's value --
    an input, because the profile-switch capture carries no 0x0448 at all.
    """
    pairs, observed = capture_044c_rows(path)
    rows = parse_listing(F436_LISTING)
    a5e6 = parse_listing(LISTING)
    values = [f436_store(v, multiplicand, standing, high_byte, rows, a5e6)
              for v, standing in pairs]
    return values, observed, sum(1 for v in values if v in observed)


def report_044c(path, out=None):
    """Replay a capture's 0x0449 rows through the committed 0xF436 body.

    A second discriminator, and a sharper one than the reachability above:
    where that asks whether 0x0449's own bytes can be produced at all, this
    asks whether the *other* byte 0xA5E6's result feeds lands where the
    capture says it did.
    """
    out = out or sys.stdout
    _pairs, observed = capture_044c_rows(path)
    print("", file=out)
    if not observed:
        print("  0x044C through the committed 0xF436 body: the capture "
              "carries no 0x044C, so it cannot discriminate", file=out)
        return
    print(f"  0x044C through the committed 0xF436 body, which multiplies "
          f"0x0449 by\n  0x0448, divides by the constant 100 its own 0xF444 "
          f"row loads, clamps and\n  halves the sum into this byte. The "
          f"capture spans "
          f"{min(observed):#04x}-{max(observed):#04x}.", file=out)
    print("  the input 0x0448 has no rows in this capture, so each value "
          "below is a", file=out)
    print("  separate evaluation conditional on it rather than one reading "
          "of the file.", file=out)
    for multiplicand in MULTIPLICANDS:
        for high_byte, name in ((True, "high-byte reading (R1)"),
                                (False, "low-byte reading (R1)")):
            values, _seen, inside = simulate_044c(path, multiplicand, high_byte)
            if not values:
                print(f"  0x0448 = {multiplicand:#04x} {name}: no 0x0449 rows "
                      "to replay", file=out)
                continue
            print(f"  0x0448 = {multiplicand:#04x}  {name}: {inside} of "
                  f"{len(values)} simulated writes inside", file=out)
            print(f"    the observed set; simulated spans "
                  f"{min(values):#04x}-{max(values):#04x}", file=out)
    print("  the clamp at 0xF44E is where the two part. R2 holds the "
          "quotient's high byte", file=out)
    print("  under the corrected reading and its low byte under the other, "
          "so it fires on", file=out)
    print("  every pass under the other -- R1 is 0xff every time, so 0x044C "
          "is driven toward", file=out)
    print("  0xff -- and on none under the corrected one.", file=out)


def report_capture(path, out=None):
    out = out or sys.stdout
    pairs, observed = capture_pairs(path)
    print(f"{path}", file=out)
    print(f"  pairs nearest-in-time: {len(pairs)}; distinct 0x0449 values "
          f"observed: {len(observed)}", file=out)
    if not observed:
        print("  the capture carries no 0x0449, so it cannot discriminate",
              file=out)
        return pairs, observed
    top, bottom = max(observed), min(observed)
    print(f"  0x0449 spans {bottom:#04x}-{top:#04x}", file=out)
    for divisor in DIVISORS:
        for high_byte, name in ((True, "high-byte reading (R1)"),
                                (False, "low-byte reading (R1)")):
            reachable = {stored_byte(lo, hi, divisor, high_byte)
                         for lo, hi in pairs}
            inside = reachable & observed
            print(f"  divisor {divisor:#04x} {name}: "
                  f"{len(reachable)} distinct byte(s) reachable, "
                  f"{len(inside)} of them in the observed set", file=out)

    report_044c(path, out)
    return pairs, observed


# --- default mode ------------------------------------------------------------

def report(rows=None, out=None):
    """Reconcile the two implementations, then print the roles they agree on."""
    out = out or sys.stdout
    rows = rows if rows is not None else parse_listing()
    checked, bad = reconcile(rows)
    print(f"listing {LISTING.relative_to(REPO)}: {len(rows)} instructions",
          file=out)
    print(f"two implementations over {checked} input pairs: "
          + ("they agree on both result pairs" if not bad
             else f"{len(bad)} DISAGREEMENT(S)"), file=out)
    for dividend, divisor, got, want in bad[:10]:
        print(f"  {dividend:#06x} / {divisor:#06x}: listing gave "
              f"{(got[0], got[1])}, model gave {want}", file=out)
    if bad:
        return 1

    print("\nThe dividend is R7:R6:R2:R1, shifted in this order:", file=out)
    for addr, text in roles(rows)["dividend_shift"]:
        if text.startswith("mov") and "A," in text:
            print(f"  0x{addr:04X}  {text}", file=out)
    print("  the register shifted first is the low byte, so R1 is the "
          "dividend's low byte", file=out)

    print("\nThe quotient bit enters the accumulator here:", file=out)
    for addr, reg in roles(rows)["accumulator"]:
        print(f"  0x{addr:04X}  into {reg}", file=out)
    print("  R0 is shifted first, so R0 is the low accumulator and R5 the "
          "high one", file=out)

    print("\nThe epilogue:", file=out)
    for addr, (dst, src) in roles(rows)["epilogue"]:
        print(f"  0x{addr:04X}  {dst} <- {src}", file=out)
    print("  so the quotient is returned low byte in R1 and high byte in R2, "
          "and R3:R4 is the remainder", file=out)

    print("\nThe two conventions, and why the swap was easy:", file=out)
    for addr in (*FAMILIES, A5E6):
        low = family_low(addr)
        other = "R2" if low == "R1" else "R1"
        print(f"  0x{addr:04X}  touches {low} first, so {low} is the low "
              f"byte and {other} the high one", file=out)
    print("  the rule is common -- whichever register a helper touches first "
          "is its low byte --\n  and the answers differ, which is what makes "
          "reading one helper as another wrong.", file=out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--callers", action="store_true",
                    help="every lcall 0xA5E6 site in bank-call-targets.csv, "
                         "what the image really holds there, and what the "
                         "enclosing function does with R1 and R2 after")
    ap.add_argument("--capture", metavar="PATH",
                    help="an ec-watch capture CSV; report which stored bytes "
                         "its own inputs can reach under each reading")
    args = ap.parse_args(argv)
    if args.callers and args.capture:
        ap.error("--callers and --capture are separate reports")
    if args.callers:
        report_callers()
        return 0
    if args.capture:
        report_capture(args.capture)
        return 0
    return report()


if __name__ == "__main__":
    sys.exit(main())
