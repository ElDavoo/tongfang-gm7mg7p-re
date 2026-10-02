#!/usr/bin/env python3
"""The two-byte key the PD image's `pd 0x11C2` dispatch is selected by, closed
form against instruction-by-instruction, and what each key pair selects.

`docs/findings/pd-common-address-spaces.md` left one thing open on purpose:
the table at `pd` 0xCB4D is scanned against a 16-bit pair, and "A here is
whatever `pd 0x38D3` returned, which the bytes do not fix." The bytes between
the store and the dispatch are all committed, and the arithmetic closes, so
that is answerable. This is the answer, and the machine that re-derives it.

**The chain, and what this simulates.** `pd 0xCB2A` stores the caller's R7 at
XDATA 0x0803, reads it back into R1, and calls four routines in sequence:
`pd 0x34EF` (which is one instruction and falls through into `pd 0x34F2`, which
is two more and tail-jumps to `pd 0x10BC`), `pd 0x349B`, `pd 0x38D3`, and
`pd 0x11C2`. Running that on a machine modelled instruction by instruction
gives

    key address = (0x0424 + 0x260 * R7)  mod 2**16

with the key *pair* read as `B = XDATA[addr]`, `A = XDATA[addr+1]` -- low byte
first, the opposite order from how the pair is printed. The closed form is
exact for all 256 values of the byte, which is the point of running it rather
than checking the 0..7 a reader would do by hand. It is a modular 16-bit add
and nothing in the chain is a branch on the byte's value, so no `R7` reaches a
different rule from another.

**What the machine is, and is not.** It executes the opcodes on this path out
of the committed image -- it fetches every byte at runtime address `pc` from
the PD region, so a listing that no longer matches the firmware fails here
rather than producing a confident wrong answer -- and it refuses on any opcode
outside the modelled set. That is a narrow machine, not an 8051: there is no
timing, no interrupt, no stack beyond what these calls push, and `mul AB` is
the only multiplication. The refusal is what keeps the claim honest, because a
silent no-op for an unmodelled opcode would let the tool report agreement
between two things that both ignored the byte in question.

**The precondition the chain has, which is not in the issue.** `pd 0xCB2A`
tests R3 against `0x0D` at 0xCB37 and **returns** on a match, before the key is
computed at all. So the selector runs only when R3 != 0x0D; the caller this
whole question is about is the one that does not take the early return. The
simulation sets R3 to `0x00` for that reason and says so rather than picking a
value silently.

**The record table is a function of the key pair, and that part is settled.**
Given the four records, `pd 0x11C2` selects a record by comparing `CODE[+2]`
against B and `CODE[+3]` against R0, four bytes at a time, and stops at the
first record whose `CODE[+0]` and `CODE[+1]` are both zero -- which takes its
target from `+2`/`+3` instead. So *which* record runs is determined by the pair
alone; `--select` is the exhaustive census of that function over all 65536
pairs, and the machine is checked against it on a named set of pairs that is
printed rather than summarised, so a reader can see which pairs were asked
about. `--select --verify-all` runs the machine over the whole space instead,
which is about a minute and says the same thing with nothing left out.

**What this does not settle, and cannot.**

  * *The value.* The key pair is a pair of XDATA *contents*, and XDATA is RAM:
    the image says what the key address *is*, never what is stored there. So
    "which record does a given execution select" is still open, and no output
    below pretends otherwise. A record key pair here is a number the PD program
    would have to have written.
  * *Whether `pd 0xCB2A` is reached at all.* Reachability is a different
    question and a different instrument.
  * *Where XDATA 0x0803's byte comes from.* It is written here from R7, but
    `ec/annotations/xdata-registers.csv` names `pd 0xB80E` as a second writer
    and `pd 0x1E4B` / `pd 0x1EFE` as further readers. This tool models one
    call site's round trip through the byte, not the byte's whole life.
  * *Nothing behavioural.* No hardware is reachable from a GitHub-hosted
    runner, no register is read back, and nothing here is evidence the EC or
    the PD program acts on any of these bytes. It is a static derivation over
    committed listings and the committed image, and that is the whole of it.
  * *The scan's own bound.* `pd 0x11C2` has no length check: what stops it on
    a table without a `00 00` record is that there is none. The table at
    0xCB4D has one, so *this* table cannot be overrun; the general question is
    untouched and stays where `pd-common-address-spaces.md` put it.

Read-only: it opens the firmware image for reading and writes nothing.

Not in `.github/scripts/agent-gates.sh`, and cannot be from an agent branch:
the plan stage's push token has no `workflow` scope, so a branch touching
`.github/` fails at the very end of the run rather than the start. It does run
under that gate's `python3 syntax` check, which only proves it compiles.

Usage:
    python3 pd_dispatch_key.py ../firmware/GMxMGxx_11.800
    python3 pd_dispatch_key.py ../firmware/GMxMGxx_11.800 --chain 0x03
    python3 pd_dispatch_key.py ../firmware/GMxMGxx_11.800 --select
    python3 pd_dispatch_key.py ../firmware/GMxMGxx_11.800 --select --verify-all
    python3 pd_dispatch_key.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import os
import re
import sys

from disasm8051 import OPCODE_LEN, mnemonic
from trace_xdata_refs import PD_MARKER, REGIONS

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")
PD_REGION = "pd-image"

# The chain, in the order `pd 0xCB2A` enters it. `pd 0x34EF` and `pd 0x34F2`
# are both here because the first does not return: `ghidra-functions.csv`'s
# row for it says "A single `mov DPTR,#0x424` with no ret", so the two
# instructions after it are reached by falling through, and a derivation that
# calls 0x34EF and then separately calls 0x34F2 describes a call that the
# bytes do not contain.
CHAIN = ((0xCB2A, "pd 0xCB2A"), (0x34EF, "pd 0x34EF"), (0x34F2, "pd 0x34F2"),
         (0x10BC, "pd 0x10BC"), (0x349B, "pd 0x349B"), (0x38D3, "pd 0x38D3"),
         (0x11C2, "pd 0x11C2"))

# The register the chain is written for, and the byte that becomes the key: the
# caller hands `pd 0xCB2A` a selector in R7, which is stored at XDATA 0x0803
# and read back, so the two are the same value by the time DPTR is built.
SELECTOR_REG = 7
XDATA_STORE = 0x0803

# `pd 0xCB2A` returns before computing anything when R3 == 0x0D, so the whole
# derivation is conditional on the caller not taking that branch.
R3_GUARD_VALUE = 0x0D
R3_SUBSTITUTE = 0x00

# The stride and the base, stated once. 0x60 is `pd 0x34F2`'s multiplier and
# 0x200 is `pd 0x349B`'s `DPH += 2*A`; the closed form is their sum, and the
# machine below is what says they add rather than one replacing the other.
BASE = 0x0424
STRIDE = 0x60
DPH_STEP = 0x200

# Where the record table starts, in PD runtime addresses. `pd 0x11C2` enters
# with DPTR here because the `lcall 0x11C2` at 0xCB4A pushed a return address
# of 0xCB4D, and its first two instructions pop it straight back.
TABLE_RUNTIME = 0xCB4D
RECORD = 4

# Where DPTR holds the key address. `pd 0x38D3` reads `XDATA[DPTR]` into B,
# runs `inc DPTR`, and reads `XDATA[DPTR]` into A, so the address of the *low*
# key byte is the DPTR in force at the call that starts it -- and one less
# than the DPTR the same routine leaves behind. Reading it from the wrong side
# of that `inc DPTR` is a one-byte disagreement that looks like a broken
# derivation, which is why it is a named constant rather than the machine's
# final DPTR.
KEY_ADDRESSED = 0xCB47

# The `lcall 0x11C2` that ends the chain. Kept because DPTR has been rebuilt
# by the time the run ends: `pd 0x11C2` overwrites DPTR with its own return
# address in its first two instructions, so a key address read off the machine
# after the run is the *table's* address and not an address into it.
DISPATCH_CALL = 0xCB4A

# Guard against a chain that does not terminate. The longest run observed is
# the record scan walking all four records; this is a stop that names a
# runaway rather than a bound anyone believes in.
MAX_STEPS = 512


class Refusal(Exception):
    """A dump or a byte sequence this tool will not describe, and why.

    Raised rather than returned, because every caller has nothing useful to say
    about an image without the marker or an opcode nobody modelled: there is no
    report to print and no table to check. The message names the offset or the
    address, so the refusal reads as a measurement rather than as an absence.
    """


def pd_region():
    """(file_lo, file_hi, runtime_base) for the PD image, off `REGIONS`.

    Read out of `trace_xdata_refs.REGIONS` rather than written as 0x20000, so
    this tool and the scan it borrows its image map from cannot disagree about
    where the second program starts. `pd_direct_offset_sites.py` and
    `pd_index_geometry.py` keep the same lookup separately, for the same
    reason neither imports the other.
    """
    return next((lo, hi, runtime) for name, lo, hi, runtime, _ in REGIONS
                if name == PD_REGION)


def to_file(addr: int) -> int:
    """File offset a PD runtime address sits at."""
    lo, _, runtime = pd_region()
    return lo + addr - runtime


def in_region(off: int) -> bool:
    lo, hi, _ = pd_region()
    return lo <= off < hi


def read_image(path: str) -> bytes:
    """The committed firmware, or raise Refusal if 0x20000 is not the PD image.

    The marker is checked rather than assumed, and a dump without it is refused
    rather than decoded as one: the whole tool is a reading of the *second*
    program in this dump, and running it against bytes that are not that
    program would produce a page of arithmetic about nothing.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    off, magic = PD_MARKER
    if data[off:off + len(magic)] != magic:
        raise Refusal(f"no {magic.decode()!r} marker at file 0x{off:05X} -- "
                      "0x20000-0x2FFFF is not the ITE8850-PD image this tool "
                      f"decodes ({path})")
    return data


def code(data: bytes, addr: int) -> int:
    """The CODE byte at PD runtime address `addr`.

    Refuses rather than returning 0 for an address outside the PD region: a
    `movc` that walked off the end of the program is a bug in this tool's
    model or a wrong premise about the table, and an out-of-range read that
    quietly returns a byte would let either of them look like agreement.
    """
    if not 0 <= addr < 0x10000:
        raise Refusal(f"CODE address 0x{addr:04X} is not a 16-bit PD address")
    off = to_file(addr)
    if not in_region(off):
        lo, hi, _ = pd_region()
        raise Refusal(f"CODE address 0x{addr:04X} is file 0x{off:05X}, outside "
                      f"the PD region 0x{lo:05X}-0x{hi:05X}")
    return data[off]


def records(data: bytes, count: int = 4):
    """The `count` four-byte records at `TABLE_RUNTIME`, read from the image.

    Read from file 0x2CB4D rather than transcribed, because only 0xCB4D..0xCB4F
    appear in any committed listing -- `ec/decompiled/pd/CB2A.asm` stops there,
    because those three bytes are data and the decompiler read them as
    instructions. The rest of the table is in no `.asm` at all, so a tool that
    read the listing would be reading half the answer and calling it the whole.
    """
    out = []
    for i in range(count):
        off = to_file(TABLE_RUNTIME + RECORD * i)
        out.append(tuple(data[off + j] for j in range(RECORD)))
    return out


def select_record(recs, low: int, high: int):
    """(index, target) the `pd 0x11C2` scan reaches for one key pair.

    A transcription of the scan's two branches, and deliberately a *separate*
    implementation of them: this is the census, the machine in `run()` is the
    check, and one function doing both would agree with itself.

    A record whose `+0` and `+1` are both zero takes its target from `+2`/`+3`
    and never compares the key, so it ends the scan whatever the pair is; every
    other record matches on `+2` == low and `+3` == high and jumps to
    (`+0` << 8) | `+1`. Returns None when no record claims the pair, which for
    a table with a zero pair is unreachable.
    """
    for i, rec in enumerate(recs):
        if rec[0] == 0 and rec[1] == 0:
            return i, (rec[2] << 8) | rec[3]
        if rec[2] == low and rec[3] == high:
            return i, (rec[0] << 8) | rec[1]
    return None


def closed_form(n: int) -> int:
    """The key address for selector byte `n`, as one modular 16-bit add."""
    return (BASE + (STRIDE + DPH_STEP) * n) & 0xFFFF


# The residue every reachable key address shares, and the modulus that makes
# it: the stride is 32 * 19, so `BASE + stride * n` is congruent to `BASE`
# modulo 32 for every `n`. A table keyed on a pair that can only be found at an
# address outside that residue cannot be reached through *this* call site. This
# is arithmetic on the stride and says nothing about the other fifteen `lcall
# 0x11C2` sites in the image, which build their own DPTR.
KEY_ADDR_MODULUS = 32


class Machine:
    """Just enough 8051 to run the chain, and no more.

    Fetches every byte from the image at execution time, so the model is held
    to the firmware rather than to a transcription of it: change a byte and
    either the run changes or the tool refuses, and neither outcome can be a
    clean pass on an unchanged derivation.

    Register file, A, B, DPTR, a carry flag and a stack, because those are what
    the opcodes on this path touch. There is no parity, no accumulator
    overflow, no timer and no interrupt: nothing in the chain reads them, and
    modelling what is not read would be a second claim to keep true.
    """

    def __init__(self, data: bytes, xdata=None):
        self.data = data
        self.xdata = bytearray(0x10000) if xdata is None else xdata
        self.r = [0] * 8
        self.a = 0
        self.b = 0
        self.carry = 0
        self.stack = []
        self.pc = 0
        self.dptr = 0
        # Call depth, so a `ret` knows whether it returns to a frame this
        # machine entered or to the caller of `pd 0xCB2A` itself. It is a
        # field rather than a local of `run()` because `_step()` is what
        # changes it, and a `depth += 1` inside `_step()` rebinding a
        # parameter would have made every frame look like the outermost one.
        self.depth = 0
        self.steps = []
        self.stop = None
        self.target = None

    # -- helpers ---------------------------------------------------------
    def state_at(self, addr: int):
        """(DPTR, A, B) as they stood once the instruction at `addr` had run.

        Read back out of the recorded trace rather than watched for while
        stepping, so a caller can ask for one of the chain's intermediate
        values by address instead of the tool having to know in advance which
        of them anybody wants -- and, more to the point, so that nothing is
        read off the machine at the *end* of a run whose last instructions
        rebuild the very registers being asked about. Both of the chain's
        call sites are named for this: an `lcall` touches neither DPTR nor A
        nor B, so reading either side of one gives the same answer, and
        naming the instruction says which side was asked for.
        """
        for at, _, _, after in self.steps:
            if at == addr:
                return after
        raise Refusal(f"0x{addr:04X} was not executed; the chain did not reach "
                      "it, so its state is not a value this run has")

    def _add(self, x: int, y: int, carry_in: int = 0) -> int:
        """`x + y (+ carry)`, leaving the carry-out in the flag.

        `carry_in` is the difference between the two opcodes this chain uses
        and the reason it matters here. `pd 0x10BC` adds DPL to the low half of
        the product with a plain `add A,DPL` and then folds the carry into DPH
        with `addc A,DPH`, so the 16-bit product lands whole. `pd 0x349B` adds
        A to itself with a plain `add A,A`, whose carry-out is *discarded* by
        the `add A,DPH` that follows, and leaves DPH holding `2*A` modulo 256.
        Both are exact, and they are exact for different reasons -- a model
        that added the carry to both would report a one-byte disagreement for
        every selector byte from 0x80 up, which is precisely the half of the
        range an eight-value spot check never reaches.
        """
        total = x + y + carry_in
        self.carry = 1 if total > 0xFF else 0
        return total & 0xFF

    def _push(self, value: int) -> None:
        self.stack.append(value & 0xFF)
        self.stack.append((value >> 8) & 0xFF)

    def _pop_direct(self) -> int:
        """The byte a `POP direct` takes: the most recently pushed one.

        `LCALL` pushes the low byte first, so the top of the stack is the high
        byte of the return address -- which is why `pd 0x11C2`'s first two
        instructions are `pop DPH` then `pop DPL` and leave DPTR pointing at
        the address the call came from, and not at one byte either side of it.
        """
        if not self.stack:
            raise Refusal(f"stack underflow at 0x{self.pc:04X}")
        return self.stack.pop()

    def _pop16(self) -> int:
        """The pair a `RET` takes, in the same push order."""
        if len(self.stack) < 2:
            raise Refusal(f"stack underflow at 0x{self.pc:04X}")
        high = self.stack.pop()
        low = self.stack.pop()
        return (high << 8) | low

    # -- execution -------------------------------------------------------
    def run(self, entry: int, limit: int = MAX_STEPS) -> None:
        """Execute from `entry` until the dispatch jump, a top-level return,
        or `limit` steps."""
        self.pc = entry
        self.depth = 0
        for _ in range(limit):
            at = self.pc
            op = code(self.data, at)
            n = OPCODE_LEN[op]
            raw = bytes(code(self.data, at + i) for i in range(n))
            text = mnemonic(self.data, to_file(at), at)
            before = (self.dptr, self.a, self.b)
            jump = self._step(op, raw)
            self.steps.append((at, text, before, (self.dptr, self.a, self.b)))
            if jump:
                self.stop = jump
                return
        raise Refusal(f"no dispatch within {limit} steps from "
                      f"0x{entry:04X}; the chain did not terminate")

    def _step(self, op: int, raw: bytes) -> str:
        """Execute one fetched instruction. Returns '', 'dispatch', 'top-ret'."""
        pc = self.pc
        at = pc                     # the instruction's own address, for the
                                    # refusal messages below
        pc = pc + len(raw)          # the fall-through case; branches below
                                    # overwrite it with their own target

        if op == 0x90:                                    # mov DPTR,#imm16
            self.dptr = (raw[1] << 8) | raw[2]
        elif op == 0xE4:                                  # clr A
            self.a = 0
        elif 0xE8 <= op <= 0xEF:                          # mov A,Rn
            self.a = self.r[op - 0xE8]
        elif 0xF8 <= op <= 0xFF:                          # mov Rn,A
            self.r[op - 0xF8] = self.a
        elif op == 0xF0:                                  # movx @DPTR,A
            self.xdata[self.dptr] = self.a
        elif op == 0xE0:                                  # movx A,@DPTR
            self.a = self.xdata[self.dptr]
        elif op == 0xA3:                                  # inc DPTR
            self.dptr = (self.dptr + 1) & 0xFFFF
        elif op == 0x25:                                  # add A,direct
            self.a = self._add(self.a, self._direct(raw[1]))
        elif op == 0x35:                                  # addc A,direct
            self.a = self._add(self.a, self._direct(raw[1]),
                               carry_in=self.carry)
        elif op == 0xE5:                                  # mov A,direct
            self.a = self._direct(raw[1])
        elif op == 0xF5:                                  # mov direct,A
            self._set_direct(raw[1], self.a)
        elif 0x88 <= op <= 0x8F:                          # mov direct,Rn
            self._set_direct(raw[1], self.r[op - 0x88])
        elif op == 0x75:                                  # mov direct,#imm
            self._set_direct(raw[1], raw[2])
        elif op == 0xA4:                                  # mul AB
            product = self.a * self.b
            self.a, self.b = product & 0xFF, (product >> 8) & 0xFF
            self.carry = 0
        elif op == 0x74:                                  # mov A,#imm
            self.a = raw[1]
        elif op == 0x93:                                  # movc A,@A+DPTR
            self.a = code(self.data, (self.a + self.dptr) & 0xFFFF)
        elif op == 0x68:                                  # xrl A,Rn
            self.a ^= self.r[op & 7]
        elif op == 0xB4:                                  # cjne A,#imm,rel
            if self.a != raw[1]:
                pc = (pc + _signed(raw[2])) & 0xFFFF
        elif op == 0xB5:                                  # cjne A,direct,rel
            # The record scan's key comparison. `direct` is 0xF0, B, which is
            # the low key byte `pd 0x38D3` left there; the high byte is
            # compared separately by the `xrl A,R0` that follows.
            if self.a != self._direct(raw[1]):
                pc = (pc + _signed(raw[2])) & 0xFFFF
        elif op == 0x70:                                  # jnz rel
            if self.a:
                pc = (pc + _signed(raw[1])) & 0xFFFF
        elif op == 0x60:                                  # jz rel
            if not self.a:
                pc = (pc + _signed(raw[1])) & 0xFFFF
        elif op == 0x80:                                  # sjmp rel
            pc = (pc + _signed(raw[1])) & 0xFFFF
        elif op == 0x02:                                  # ljmp addr
            pc = (raw[1] << 8) | raw[2]
        elif op == 0x73:                                  # jmp @A+DPTR
            # The dispatch exit. Nothing follows it in this routine and
            # nothing after it belongs to this chain, so the machine stops
            # here and reports the address rather than executing whatever the
            # target happens to contain -- which for three of the four records
            # is a table entry, not a routine.
            self.target = (self.dptr + self.a) & 0xFFFF
            return "dispatch"
        elif op == 0x12:                                  # lcall addr
            self._push(pc)
            self.depth += 1
            pc = (raw[1] << 8) | raw[2]
        elif op == 0x22:                                  # ret
            if self.depth == 0:
                # `pd 0xCB2A`'s own return: the R3 == 0x0D path, or the
                # return of a frame this tool did not enter. Either way the
                # chain is over and no key was computed.
                return "top-ret"
            self.depth -= 1
            pc = self._pop16()
        elif op == 0xD0:                                  # pop direct
            self._set_direct(raw[1], self._pop_direct())
        else:
            raise Refusal(f"unmodelled opcode 0x{op:02X} at 0x{at:04X} -- "
                          "this tool models the chain's own opcodes and refuses "
                          "rather than skips, so a disagreement between the "
                          "closed form and the machine is a disagreement about "
                          "a real instruction")
        self.pc = pc
        return ""

    # The direct byte space. Only 0x82 (DPL), 0x83 (DPH), 0xE0 (A) and 0xF0
    # (B) appear on this path; the four register banks do not, and the
    # internal RAM the other direct opcodes would address is not modelled
    # because nothing here touches it. An unmodelled direct address refuses
    # rather than reading zero, for the reason the opcode refusal above does.
    def _direct(self, addr: int) -> int:
        if addr == 0x82:
            return self.dptr & 0xFF
        if addr == 0x83:
            return (self.dptr >> 8) & 0xFF
        if addr == 0xE0:
            return self.a
        if addr == 0xF0:
            return self.b
        raise Refusal(f"unmodelled direct address 0x{addr:02X}; the chain "
                      "touches only 0x82, 0x83, 0xE0 and 0xF0")

    def _set_direct(self, addr: int, value: int) -> None:
        if addr == 0x82:
            self.dptr = (self.dptr & 0xFF00) | (value & 0xFF)
        elif addr == 0x83:
            self.dptr = (self.dptr & 0x00FF) | ((value & 0xFF) << 8)
        elif addr == 0xE0:
            self.a = value & 0xFF
        elif addr == 0xF0:
            self.b = value & 0xFF
        else:
            raise Refusal(f"unmodelled direct address 0x{addr:02X}; the chain "
                          "touches only 0x82, 0x83, 0xE0 and 0xF0")


def _signed(byte: int) -> int:
    return byte - 0x100 if byte > 0x7F else byte


def run(data: bytes, n: int, pair=(0, 0)):
    """Execute the chain for selector byte `n`, and report what it did.

    `pair` seeds the two XDATA bytes the key read will land on. The address it
    seeds them at is the *closed form*, so the machine arriving somewhere else
    reads zeros and the disagreement is visible rather than silent -- that is
    the cross-check, and it is why the seed is computed from the other half of
    the tool rather than from the machine's own output.
    """
    machine = Machine(data)
    seed = closed_form(n)
    machine.xdata[seed] = pair[0]
    machine.xdata[seed + 1] = pair[1]
    machine.r[SELECTOR_REG] = n
    machine.r[3] = R3_SUBSTITUTE
    machine.run(CHAIN[0][0])

    # The key address and the key pair, each read where the machine still
    # holds it. Taking either from the end of the run would not work: DPTR has
    # been popped back to the table and A has been cleared for the dispatch
    # jump, and taking the address from the closed form would make the
    # comparison below vacuous -- the machine would be agreeing with a value
    # it was handed.
    key_addr = machine.state_at(KEY_ADDRESSED)[0]
    _, high, low = machine.state_at(DISPATCH_CALL)
    return {
        "n": n,
        "closed": seed,
        "machine": key_addr,
        "stored": machine.xdata[XDATA_STORE],
        "low": low,
        "high": high,
        "target": machine.target,
        "steps": machine.steps,
        "machine_obj": machine,
    }


def agree(data: bytes, byte_range=range(0x100)):
    """Every selector byte whose machine and closed form name the same address.

    Returns the mismatches rather than a count, so a caller can print the one
    that failed instead of a number that moved.
    """
    return [(n, closed_form(n), run(data, n)["machine"])
            for n in byte_range
            if closed_form(n) != run(data, n)["machine"]]


def is_default(rec) -> bool:
    """Whether a record is the `00 00` one the scan stops at.

    Named rather than inlined because three places below need the same test --
    the table print, the census and the machine probe list -- and a table whose
    default record were not last would make "the last record" and "the default
    record" two different claims.
    """
    return rec[0] == 0 and rec[1] == 0


def print_records(data: bytes, recs) -> None:
    print(f"record table at PD runtime 0x{TABLE_RUNTIME:04X} "
          f"(file 0x{to_file(TABLE_RUNTIME):05X}), {len(recs)} records of "
          f"{RECORD} bytes")
    for i, rec in enumerate(recs):
        if is_default(rec):
            target = (rec[2] << 8) | rec[3]
            how = "default: CODE[+0] and CODE[+1] both 0, target from +2/+3"
        else:
            target = (rec[0] << 8) | rec[1]
            how = f"key (B, R0) = (0x{rec[2]:02X}, 0x{rec[3]:02X})"
        print(f"  0x{TABLE_RUNTIME + RECORD * i:04X}: "
              f"{' '.join('%02x' % b for b in rec)}  -> 0x{target:04X}  {how}")
    after = TABLE_RUNTIME + RECORD * len(recs)
    print(f"  first byte after the table, runtime 0x{after:04X} "
          f"(file 0x{to_file(after):05X}): "
          f"{' '.join('%02x' % data[to_file(after) + i] for i in range(3))}"
          " -- code, so the table is these four records and no more")


def print_chain(data: bytes, n: int) -> int:
    """Trace the chain for one selector byte. Returns 1 on disagreement."""
    result = run(data, n)
    print(f"selector byte R7 = 0x{n:02X}, R3 = 0x{R3_SUBSTITUTE:02X} "
          f"(R3 must not be 0x{R3_GUARD_VALUE:02X}; see the module docstring)")
    for addr, text, before, after in result["steps"]:
        dptr, a, b = after
        print(f"  0x{addr:04X}  {text:<22}"
              f"DPTR 0x{before[0]:04X}->0x{dptr:04X}"
              f"  A 0x{before[1]:02X}->0x{a:02X}"
              f"  B 0x{before[2]:02X}->0x{b:02X}")
    print(f"  key address: closed form 0x{result['closed']:04X}, machine "
          f"0x{result['machine']:04X}")
    print(f"  the selector round trip: R7 = 0x{n:02X} stored at XDATA "
          f"0x{XDATA_STORE:04X}, read back as 0x{result['stored']:02X} -- the "
          "same byte, so the address is a function of the caller's R7 and of "
          "nothing this routine recomputed")
    print(f"  key pair: B = 0x{result['low']:02X} "
          f"(XDATA[addr]), A = 0x{result['high']:02X} "
          f"(XDATA[addr+1]) -- high byte second in the pair")
    print(f"  dispatch target: 0x{result['target']:04X}")
    ok = result["closed"] == result["machine"]
    if not ok:
        print("  MISMATCH: the closed form and the machine disagree")
    return 0 if ok else 1


def print_keys(data: bytes, byte_range) -> int:
    """The closed form beside the machine for each selector byte."""
    recs = records(data)
    print("selector byte -> key address, closed form against the machine")
    print(f"  {'R7':>4}  {'closed':>8}  {'machine':>8}  "
          f"{'key pair':>10}  record selected")
    bad = []
    for n in byte_range:
        result = run(data, n)
        hit = select_record(recs, result["low"], result["high"])
        where = ("none" if hit is None
                 else f"#{hit[0]} -> 0x{hit[1]:04X}")
        agree_here = result["closed"] == result["machine"]
        if not agree_here:
            bad.append(n)
        print(f"  0x{n:02X}  0x{result['closed']:04X}  "
              f"0x{result['machine']:04X}{'' if agree_here else '  MISMATCH'}  "
              f"0x{result['high']:02X}{result['low']:02X}      {where}")
    print(f"  {len(byte_range)} selector bytes, "
          f"{len(byte_range) - len(bad)} agree, {len(bad)} disagree")
    print(f"  the key pair is XDATA *contents*, so the pair column is 0x0000 "
          "for every row here: the image fixes the address, not the bytes "
          "stored there")
    for n in bad:
        print(f"  MISMATCH at 0x{n:02X}: closed 0x{closed_form(n):04X}, "
              f"machine 0x{run(data, n)['machine']:04X}")
    return 1 if bad else 0


def print_select(data: bytes, recs) -> int:
    """The record table as a function of the key pair, exhaustively.

    Over all 65536 pairs, which is not a sample and not a claim about runtime:
    it is the table's own logic evaluated everywhere, and the answer is a
    property of the sixteen bytes read above.
    """
    counts = {i: 0 for i in range(len(recs))}
    keyed = []
    unclaimed = 0
    for low in range(0x100):
        for high in range(0x100):
            hit = select_record(recs, low, high)
            if hit is None:
                unclaimed += 1
                continue
            counts[hit[0]] += 1
            if not is_default(recs[hit[0]]):
                keyed.append((hit[0], low, high, hit[1]))

    print("which record each of the 65536 key pairs selects")
    for i, rec in enumerate(recs):
        target = (rec[2] << 8) | rec[3] if is_default(rec) \
            else (rec[0] << 8) | rec[1]
        print(f"  record #{i} at 0x{TABLE_RUNTIME + RECORD * i:04X} -> "
              f"0x{target:04X}: {counts[i]} of 65536 pairs")
    if unclaimed:
        print(f"  no record at all: {unclaimed} of 65536 pairs")
    print("  the pairs that select a keyed record:")
    for i, low, high, target in sorted(keyed):
        print(f"    (B, R0) = (0x{low:02X}, 0x{high:02X}) -> record #{i}, "
              f"0x{target:04X}")
    print(f"  every other pair -- {65536 - len(keyed)} of them -- selects the "
          "default record, so this table cannot be scanned past its end: the "
          "`00 00` record is what stops the scan, and it is inside the table")
    print(f"  a key address reachable through pd 0xCB2A is congruent to "
          f"0x{BASE:04X} == 0x{BASE % KEY_ADDR_MODULUS:02X} (mod "
          f"{KEY_ADDR_MODULUS}), because the stride {STRIDE + DPH_STEP:#05x} is "
          f"{KEY_ADDR_MODULUS} times an odd number; a pair only ever stored at "
          "an address outside that residue is unreachable through this call "
          "site, and says nothing about the other fifteen lcall 0x11C2 sites "
          "in the image, which build their own DPTR")
    return 0


def probe_pairs(recs):
    """The key pairs the machine is checked against, named rather than sampled.

    Four kinds, and the set is derived from the table rather than typed in: the
    pair each keyed record keys on, the pair the default record is reached
    with, both extremes, and -- from each keyed pair -- one byte off its low
    half, so the miss path that walks past a record and comes back is executed
    rather than only the path that stops on the first one.

    A named set rather than all 65536, because a full sweep is about a minute
    of Python and `--verify-all` runs it when that is wanted; what this set is
    for is being *printed*, so a reader can see which pairs the machine was
    asked about instead of taking a coverage figure on trust.
    """
    keyed = sorted((rec[2], rec[3]) for rec in recs if not is_default(rec))
    pairs = {(0x00, 0x00), (0xFF, 0xFF)}
    for low, high in keyed:
        pairs.add((low, high))
        pairs.add(((low + 1) & 0xFF, high))
        pairs.add((low, (high + 1) & 0xFF))
    return sorted(pairs)


def machine_agrees(data: bytes, recs, pairs):
    """The pairs where the machine and the census disagree, and how.

    The check is three-sided on purpose: the machine must read back the pair
    that was seeded, land on the record the census names, and jump where that
    record says. A machine that got the address right and the target wrong
    would still have agreed on the address, which is the part the closed form
    is about and not the part that picks the routine.
    """
    bad = []
    for low, high in pairs:
        result = run(data, 0x00, pair=(low, high))
        expected = select_record(recs, low, high)
        if (result["low"] != low or result["high"] != high
                or expected is None or result["target"] != expected[1]):
            bad.append((low, high, result, expected))
    return bad


def print_probes(data: bytes, recs, exhaustive: bool) -> int:
    """The machine against the census, and how much of the space was covered."""
    pairs = (all_pairs() if exhaustive else probe_pairs(recs))
    bad = machine_agrees(data, recs, pairs)
    scope = ("all 65536" if exhaustive
             else f"{len(pairs)} named")
    print(f"  the machine agrees with the census on {len(pairs) - len(bad)} of "
          f"{scope} pairs"
          + ("" if exhaustive else ": "
             + ", ".join(f"(0x{lo:02X},0x{hi:02X})" for lo, hi in pairs)))
    if not exhaustive:
        print("  --verify-all runs the machine over the whole space instead; "
              "this is a named set, printed rather than summarised, so a "
              "reader can see which pairs were asked about")
    for low, high, result, expected in bad:
        print(f"  MISMATCH for (B, R0) = (0x{low:02X}, 0x{high:02X}): machine "
              f"read (0x{result['low']:02X}, 0x{result['high']:02X}) and "
              f"reached 0x{result['target']:04X}, census says {expected}")
    return 1 if bad else 0


def all_pairs():
    """Every (low, high) pair, in the order `select_record` is swept over."""
    return [(low, high)
            for low in range(0x100) for high in range(0x100)]


def listing_mnemonic(line: str):
    """(address, mnemonic) for one `ec/decompiled/pd/*.asm` line, or None.

    The listings are `addr  <hex bytes>  <mnemonic>  <operands>`, with the
    byte column padded by `-` for the bytes an instruction does not use and
    three bytes wide for the ones that do, so the mnemonic's column moves from
    line to line. It is found as the first token that is not a two-digit hex
    byte and not a `-`, which is unambiguous here because no mnemonic in these
    listings is spelled like a byte: the shortest ones are `jz`, `mov` and
    `mul`, and none of those is a hex pair. Parsing by column instead would
    make this self-test's verdict a property of a field width rather than of
    the bytes, which is the opposite of what it is for.
    """
    parts = line.split()
    if len(parts) < 2 or len(parts[0]) != 4:
        return None
    try:
        addr = int(parts[0], 16)
    except ValueError:
        return None
    for token in parts[1:]:
        if re.fullmatch(r"[0-9a-f]{2}", token) or token == "-":
            continue
        return addr, token
    return None


def self_test(data: bytes) -> int:
    """Re-derive the chain against the committed listings and annotations.

    Three claims, none of which is a count: that the bytes this tool executes
    are the bytes `ec/decompiled/pd/*.asm` transcribes, that `pd 0x34EF` has
    no `ret` so the fall-through is a reading of the listing and not a guess,
    and that the closed form and the machine agree for every selector byte.
    """
    problems = 0
    decompiled = os.path.join(os.path.dirname(HERE), "decompiled")
    for addr, name in CHAIN:
        listing = os.path.join(decompiled, "pd", f"{addr:04X}.asm")
        if not os.path.exists(listing):
            print(f"self-test: no listing at {listing}", file=sys.stderr)
            problems += 1
            continue
        with open(listing, encoding="utf-8") as handle:
            text = handle.read()
        # Every mnemonic the listing prints, checked against what the image
        # decodes to at the same address. The listings carry their own banner
        # naming the image and its SHA-256, so a listing from a different dump
        # fails here rather than quietly agreeing with the wrong one.
        for line in text.splitlines():
            if not line or line.startswith(";"):
                continue
            parsed = listing_mnemonic(line)
            if parsed is None:
                continue
            at, printed = parsed
            decoded = mnemonic(data, to_file(at), at).split()[0]
            if decoded != printed:
                print(f"self-test: {name} listing says {printed} at "
                      f"0x{at:04X}, the image decodes {decoded}", file=sys.stderr)
                problems += 1
    # The no-`ret` claim, which is what makes 0x34F2 a fall-through rather
    # than a second call. A listing that grew one would make the derivation's
    # shape wrong while every address in it stayed right.
    with open(os.path.join(decompiled, "pd", "34EF.asm"),
              encoding="utf-8") as handle:
        if "ret" in handle.read():
            print("self-test: pd 0x34EF.asm now carries a ret; the fall-through "
                  "derivation in this tool has to be redone", file=sys.stderr)
            problems += 1
    for n, closed, machine in agree(data):
        print(f"self-test: selector 0x{n:02X} -- closed form 0x{closed:04X}, "
              f"machine 0x{machine:04X}", file=sys.stderr)
        problems += 1
    residues = {closed_form(n) % KEY_ADDR_MODULUS for n in range(0x100)}
    if len(residues) != 1:
        print(f"self-test: the key address takes {len(residues)} residues "
              f"mod {KEY_ADDR_MODULUS}, so the residue this tool prints does "
              "not hold", file=sys.stderr)
        problems += 1
    if problems:
        return 1
    print("self-test: chain listings, the 0x34EF fall-through, all 256 "
          "selector bytes and the key-address residue all re-derive")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="the 256 KiB flash dump; the PD image is at file "
                         "0x20000 in it (default: the one beside this tool)")
    ap.add_argument("--chain", type=lambda v: int(v, 0), metavar="N",
                    help="trace the chain for one selector byte, N = 0..255")
    ap.add_argument("--keys", nargs="?", type=lambda v: int(v, 0),
                    const=0x100, metavar="N",
                    help="closed form against the machine for selector bytes "
                         "0..N-1; N defaults to 256, the whole byte")
    ap.add_argument("--select", action="store_true",
                    help="the record table's selection census over all 65536 "
                         "key pairs, with the machine checked against it")
    ap.add_argument("--verify-all", action="store_true",
                    help="with --select, check the machine against the census "
                         "over every pair rather than the named set; about a "
                         "minute")
    ap.add_argument("--self-test", action="store_true",
                    help="re-derive the chain against the committed listings")
    args = ap.parse_args()

    try:
        data = read_image(args.firmware)
    except Refusal as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.self_test:
        return self_test(data)
    if args.verify_all and not args.select:
        ap.error("--verify-all widens the check --select makes; it does not "
                 "select anything on its own")

    rc = 0
    if args.chain is not None:
        if not 0 <= args.chain <= 0xFF:
            ap.error("--chain takes a selector byte, 0x00-0xFF")
        rc |= print_chain(data, args.chain)
    if args.keys is not None or args.chain is None:
        recs = records(data)
        if args.chain is None:
            print_records(data, recs)
        stop = min(max(args.keys if args.keys is not None else 0x100, 0), 0x100)
        rc |= print_keys(data, range(stop))
        print()
    if args.select:
        recs = records(data)
        rc |= print_select(data, recs)
        rc |= print_probes(data, recs, exhaustive=args.verify_all)
    return rc


if __name__ == "__main__":
    sys.exit(main())
