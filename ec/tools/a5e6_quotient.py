#!/usr/bin/env python3
"""Execute mul_16_round_shift_subtract (bank1 0xA5E6) and say which register
holds which byte of its quotient.

Issue #358. PR #200 read 0xA5E6 as leaving "the quotient's high byte in R1,
its low byte in R2" and built `windows/tools/system_id_probe.py` on that
reading, while the listing says the other way round: the shift at 0xA5EE
touches R1 first, and the epilogue at 0xA613 copies R0 into R1.

**The point of this tool is that the roles are a consequence of the committed
bytes rather than a reading of them.** It parses ec/decompiled/bank1/A5E6.asm,
runs the instruction stream on a small 8051 core, and compares every register
against an independent Python model of shift-and-subtract written from the
algorithm rather than from the listing. Two implementations, one machine: a
disagreement is a red run, not a caveat. The opcodes are not arbitrated here --
`verify_reassembly.py --check` already holds them against the firmware, and
this file reads the listing that check arbitrates.

The core covers only what 0xA5E6 and the four functions in `FAMILIES` use. It
raises `Unsupported` on anything else rather than skipping, so a listing that
grows an instruction this core cannot execute is a loud failure and not a
silently short run.

Modes:
    python3 a5e6_quotient.py                    # reconcile, print the roles
    python3 a5e6_quotient.py --callers          # every lcall 0xA5E6 site
    python3 a5e6_quotient.py --capture PATH     # reachability against a capture

Standard library only, no Ghidra, no ecrw, nothing opened for writing.
"""
import argparse
import csv
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

LISTING = HERE.parent / "decompiled" / "bank1" / "A5E6.asm"
FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
CALL_TARGETS = HERE.parent / "annotations" / "bank-call-targets.csv"
INDEX = HERE.parent / "decompiled" / "index.csv"

# The runtime address whose operand roles this tool exists to settle, and the
# divisor/mask constants its callers are read through.
A5E6 = 0xA5E6
DIVISORS = (0x22, 0x44)

# The registers the helper writes its result into, by epilogue address. Both
# orders are stated rather than one, because the epilogue is the whole claim
# and a reader checking it wants both ends of it.
EPILOGUE = {0xA613: ("R2", "R5"), 0xA616: ("R1", "R0"),
            0xA619: ("R4", "R7"), 0xA61C: ("R3", "R6")}

# Where the quotient bit enters the accumulator, and which accumulator is
# low. 0xA60A shifts it into R0 and 0xA60D shifts R0's carry-out into R5, so
# the register touched first is the low half -- the same "first shifted is
# low" rule 0xA5E6's own dividend shift follows, and the one that made the
# high-byte reading look plausible in the first place.
ACCUMULATOR_STEP = {0xA60A: "R0", 0xA60D: "R5"}

# The 16-bit operand pair every helper in `FAMILIES` takes, named so the two
# places that ask which half is low read as a question about a pair rather
# than as a string comparison.
OPERAND_PAIR = ("R1", "R2")


class Unsupported(Exception):
    """An opcode this core does not execute. Raised, never skipped."""


class Core:
    """The 8051 subset 0xA5E6 and the families below need, and no more.

    `r` is the register file as R0..R7; direct addresses 0x00-0x07 are the same
    eight bytes, which is what makes `mov 0x02,0x05` at 0xA613 a move into R2
    without a special case. `dpl`/`dph` and `b` are the other direct addresses
    these listings touch (0x82, 0x83, 0xF0).
    """

    REGISTERS = ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7")

    def __init__(self, **kw):
        self.r = list(kw.pop("regs", [0] * 8))
        self.a = kw.pop("a", 0)
        self.b = kw.pop("b", 0)
        self.cy = kw.pop("cy", 0)
        self.dpl = kw.pop("dpl", 0)
        self.dph = kw.pop("dph", 0)
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


def step(core, addr, raw):
    """Execute one instruction. Returns the next runtime address.

    Only the opcodes 0xA5E6 and the functions in `FAMILIES` use are handled.
    Anything else raises, so an instruction this core cannot execute stops the
    run where it is rather than being treated as a no-op -- which would let the
    comparison below pass on a partial run.
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
    # add/adc/subb A,Rn and A,direct
    elif 0x28 <= op <= 0x2F:
        core.a, core.cy = _add(core.a, core.r[op - 0x28], core.cy)
    elif 0x38 <= op <= 0x3F:
        core.a, core.cy = _add(core.a, core.r[op - 0x38], core.cy)
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
    elif op == 0x22 or op == 0x32:         # ret / retl: the helper is a leaf
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


def run(rows, core=None, limit=100000):
    """Execute a parsed listing from its first instruction.

    `limit` is a backstop against a listing whose branches do not terminate.
    A run that hits it raises rather than returning a partial register state,
    because a partial state compared against a model would read as a
    disagreement rather than as the bug it is.
    """
    core = core if core is not None else Core()
    table = {addr: (text, raw) for addr, text, raw in rows}
    pc = rows[0][0]
    for _ in range(limit):
        if pc not in table:
            raise Unsupported(f"0x{pc:04X} is not an instruction in this "
                              f"listing")
        _, raw = table[pc]
        nxt = step(core, pc, raw)
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

    Returns (checked, disagreements). A disagreement is a list of
    (dividend, divisor, listing_regs, model_pair) rather than a count, so the
    caller can print the registers that differ instead of a total.
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


def roles(rows=None):
    """The operand roles, each one cited to the listing address that fixes it."""
    rows = rows if rows is not None else parse_listing()
    return {
        "dividend_shift": [(addr, text) for addr, text, _raw in rows
                           if 0xA5EE <= addr <= 0xA5F9],
        "accumulator": [(addr, ACCUMULATOR_STEP[addr])
                        for addr, _text, _raw in rows
                        if addr in ACCUMULATOR_STEP],
        "epilogue": [(addr, EPILOGUE[addr]) for addr, _text, _raw in rows
                     if addr in EPILOGUE],
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
          + ("they agree on every register" if not bad
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
