#!/usr/bin/env python3
"""Which XDATA bytes the EC's reset path stores to, per address, and which
direct `MOV DPTR,#addr` sites touch each one.

Two questions about one address, which keep being confused for each other and
which this tool answers in the same row:

  * *Does the boot path clear it?* This is a property of a **loop with a DPTR
    built at run time**, so no `90 hi lo` scan can see it. `trace_xdata_refs.py`
    documents that blind spot in its own header -- it decodes what a direct
    site does and stops at every DPTR handoff, which is exactly the shape a
    range clear takes. This tool answers it by **executing** the boot path's
    instructions with 8051 semantics, the way
    `../../docs/findings/reset-vector-dptr-targets.md` checked its 3,837 by
    hand, and looking the address up in the store set that execution produces.
  * *What writes it directly?* Delegated to `trace_xdata_refs.sites_for()` and
    `region_of()` rather than re-derived, so the direct-site half of every row
    is the same measurement the committed XDATA tables are made of.

**The boot path is read off the vector's bytes, not listed.** `common 0x0000`
is the reset forwarder and `common 0x0070` is the vector; the vector `lcall`s
four routines, two of which are BL51 trampolines whose real target is a DPTR
immediate rather than a branch operand. Enumerating clearers by hand and
hardcoding their addresses is how this tool would have come to describe one
clear and call it the boot path -- `0x0F75` is a second XDATA clearer on the
same path, sweeping `0x0000`-`0x00FF` and `0x9000`-`0x97FF`, and nothing in the
reset vector's bytes points at it as one. So the routine set is whatever the
vector's own decode names, and `--report` prints it.

Each of those routines is then executed **on its own**, rather than the vector
being run as one call chain. That is forced by the firmware: `0x0F75` is
`clr_xdata_0000_00ff_iram_20_bf_xdata_9000_97ff`, and its IRAM loop zeroes
`0x20`-`0xBF` -- which includes `0x81`, the stack pointer. A single chain would
reach that routine's `ret` with no stack to unwind. The tool stops there, names
the reason, and reports the routine's stores, which are complete by then.

**The BL51 stub is a shape, not an execution.** A trampoline's `ljmp 0x1100`
reaches the routine named in DPTR. This tool takes that as the rule
`bl51_trampolines.stub_addresses()` already commits to -- the stub set read out
of `ghidra-functions.csv`, and the shape being `mov DPTR,#imm16` then `ljmp` to
one of them -- and models the pair as a call to DPTR. It does **not** run the
stub's bytes: this repository has no decoded body for `0x1100` past its entry
(`ghidra-functions.csv`'s own `0x1803` row says so), and a walk that executed
the stub's prologue would be reporting stack traffic it cannot establish. The
target address is therefore a rule applied here, not a measurement made here,
and the routine list in `--report` is what a reader checks it against.

**A `spared` byte is one the walk stepped over, and that is derived too.** The
walked set is every DPTR value an `inc dptr` advanced past; the stored set is
every DPTR a `movx @dptr,a` wrote. `spared` is walked minus stored, which for
`0x07FD`-`0x07FF` is the three-byte window
`../../docs/findings/reset-vector-dptr-targets.md` reports and
`../../docs/findings/xdata-07fd-07ff-witness-triple.md` is about -- and which
this tool reaches by executing the same instructions rather than by carrying
the number in.

**Refusals are the point, not a fallback.** An opcode the interpreter does not
model, a walk that leaves the buffer, or a step budget it exhausted each **stop
the run with a named reason and a non-zero exit**, rather than printing a short
store set that reads as complete. A range clear that half-executed is
indistinguishable from a smaller range clear once its addresses are in a table,
so the tool declines to produce one.

Two transfers are **stops with a reason** rather than refusals, because the
answer up to that point is the answer and both are printed on every `--report`:
the vector's tail-jump to `0x00CF`, which is the scheduler the reset hands
control to rather than an initialiser, and `0x0F75`'s `ret` with SP cleared.
Neither is a silent omission, and `--report`'s stop list is what makes them
checkable.

**What a verdict is not.** Five tokens, all read off the execution:
`cleared` (the boot path's last write to this byte stored `0x00`), `written`
(a known non-zero value), `written-unknown` (a value this walk could not
establish -- read from an XDATA address nothing here wrote), `spared` (walked,
stepped over) and `not-reached` (no boot-path instruction held it in DPTR).
`not-reached` is about *this walk*, not about the byte: it does not exclude an
indirect or DPTR-handed store from somewhere the walk never went, which is the
population `../../ec/annotations/xdata-0440-readers.md` §7.5 names and this
tool does not search.

**Nothing here was observed on hardware.** Every verdict is a static
execution of committed bytes. No EC was powered, no register was read back, and
no XDATA byte outside the walk's store set was seen in any state.

`--csv` is the table this tool's claims rest on and `--check` diffs it against
`../annotations/boot-xdata-sites.csv`, byte for byte, the way
`trace_xdata_refs.check_table()` does (with `newline=""`, because the
committed tables carry the csv module's own CRLF terminator). `--self-test`
holds the known answers, transcribed from oracles outside this file --
`../../docs/findings/reset-vector-dptr-targets.md`'s 3,837 and its three spared
bytes, and the committed listings -- and then the refusals, which are the half
that matters: a check that has quietly stopped refusing looks exactly like a
check that is working.

**Not in `.github/scripts/agent-gates.sh`, and cannot be from an agent branch.**
The plan-stage push token has no `workflow` scope, so a branch touching that
script fails at the end rather than the start. The house route for wiring it in
is a prepared patch under `docs/ci/`, and
`../../docs/findings/pd-image-census.md` §"Not in any gate, for the reason"
records that the prepared set rots and that a non-applying patch is worse than
none -- so the write-up
`../../docs/findings/charge-derating-counters-not-persisted.md` carries the
reason instead. `--self-test` and `--check` are runnable from the repo root
with no arguments but this file's path.

Usage:
    python3 boot_xdata_sites.py --report
    python3 boot_xdata_sites.py 0x09C7 0x09C8 0x09C9 0x09CA
    python3 boot_xdata_sites.py --lo 0x09C0 --hi 0x09D0
    python3 boot_xdata_sites.py --csv > ../annotations/boot-xdata-sites.csv
    python3 boot_xdata_sites.py --csv --check
    python3 boot_xdata_sites.py --self-test
"""
import argparse
import collections
import csv
import io
import os
import sys
import textwrap

from bl51_trampolines import norm_addr, stub_addresses
from disasm8051 import OPCODE_LEN, relative_target
from trace_xdata_refs import (MOV_DPTR, PD_MARKER, check_table, region_of)

HERE = os.path.dirname(os.path.abspath(__file__))
ANNOT = os.path.join(HERE, os.pardir, "annotations")
ANNOTATIONS = os.path.join(ANNOT, "ghidra-functions.csv")
SITES_CSV = os.path.join(ANNOT, "boot-xdata-sites.csv")
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")

# The reset vector, in the identity-mapped common area: file offset == runtime
# address, so the decode can index the image directly. 0x0000 is the hardware
# reset vector and holds a single `ljmp 0x0070`; 0x0070 is where the four calls
# and the tail-jump are.
RESET_VECTOR = 0x0000

# Where the stack sits when the vector makes its first call. `common 0x0070`
# opens with `mov 0x81,#0xc0` -- SP is direct address 0x81 -- so this is the
# vector's own value read off its bytes, and a `ret` that unwinds back to it
# is the outermost frame returning. A fresh `Machine` leaves SP at 0, which is
# the register's power-on state and the wrong depth to execute a called routine
# from; each walk sets it before its first instruction.
STACK_TOP = 0xC0

# The transfer this tool declines to follow, named so the refusal is a fact
# about the run rather than an absence of one. `common 0x0070` ends in
# `ljmp 0x00CF`, and `0x00CF` is the scheduler: a `movc` table walk driven by a
# flag the boot itself sets. Executing it would consume the step budget and
# report nothing about initialisation. It is a stop with this reason, printed
# on every run and in `--report`, not a routine quietly left out of the set.
TAIL_TARGET = 0x00CF

# A step budget, because the two clearers are loops: `0xD96C` alone is ~74,000
# steps and `0x0F75` ~21,000, so a budget has to be well above those to leave
# room for a walk that reaches both plus the vector. It is the backstop for a
# path this tool does not model rather than a way to end a walk early, and
# exhausting it is a refusal, not a result.
STEP_BUDGET = 400000


class Refusal(Exception):
    """A run this tool declines to finish, carrying the reason it names.

    An exception rather than a return value because every way this can stop is
    the same shape of failure -- the store set is short and reads as complete
    -- and a caller that forgot to check a return would print that short set
    into a table. The reasons are strings rather than codes so the message a
    reader sees is the message the run failed for.
    """


class Machine:
    """The slice of an 8051 this tool models, and nothing else.

    Direct addresses 0x00-0xFF are one 256-byte space with the four registers
    the boot path touches aliased into it -- `0x81` SP, `0x82` DPL, `0x83` DPH,
    `0xE0` ACC -- rather than separate variables with special cases. That is not
    tidiness: `0xD96F` is `mov r7,0x82`, and an interpreter that reads a `direct`
    operand as the literal byte instead of the byte *at* that address gets
    DPTR's low byte wrong and exits the loop on the first iteration. Modelling
    the direct space is what makes `mov Rn,direct` mean what it says.

    XDATA is a dict rather than an array so that "never written" is
    distinguishable from "written zero": a `movx a,@dptr` of an address no
    instruction in this walk stored loads `UNKNOWN` into the accumulator, which
    propagates into any value copied from it and reaches the verdict as
    `written-unknown` rather than as a zero this tool never observed.

    That unknown is a **flag on the accumulator**, not a value in it. ACC is a
    cell of the direct bytearray because `push 0xE0` and `mov direct,Rn` have
    to see the same byte, and a bytearray holds no sentinel. So `a_unknown`
    rides alongside: reading an unwritten XDATA byte sets it, and every write
    to ACC clears it, which is what makes `a_unknown` mean "the value in ACC is
    not a value" rather than "ACC is stale".
    """

    SP, DPL, DPH, ACC = 0x81, 0x82, 0x83, 0xE0

    # What a `movx a,@dptr` loads when nothing in this walk wrote the address.
    # A singleton rather than a value: it is never stored into a bytearray and
    # never compared as one, only recognised by identity.
    UNKNOWN = object()

    def __init__(self, image: bytes, budget: int = STEP_BUDGET, stubs=()):
        self.image = image
        self.budget = budget
        self.direct = bytearray(256)
        self.xdata = {}
        self.a_unknown = False
        self.walked = set()      # DPTR values an `inc dptr` advanced past
        self.writes = []         # (xdata address, value) in execution order
        self.stops = []          # (pc, kind, detail) for transfers not followed
        self.routines = []       # the entry each executed body came in at
        # The BL51 bank-select stub addresses, so `ljmp <stub>` is recognised
        # as "run the routine in DPTR". Read from `ghidra-functions.csv` by
        # `bl51_trampolines.stub_addresses()` rather than written out here.
        self.stubs = set(stubs)
        # Where the outermost call frame's stack top sits. The vector sets SP
        # itself on its first instruction, so this is only what an unbalanced
        # `ret` unwinds past, and it is captured rather than assumed so a
        # routine that leaves the stack deeper does not end the walk early.
        self.base_sp = 0xC0
        self.carry = 0
        # When set, a `lcall` or a trampoline records its target in `routines`
        # and is skipped rather than entered -- the walk continues along the
        # vector's own body. See `boot_routines()`.
        self.collect_only = False
        # Whether an executed instruction stored 0 into SP (0x81). Set by the
        # same direct-space write every other SP change goes through, because
        # `walk_routine()` needs to tell "SP reads 0 because the routine
        # cleared it" from "SP has not been set yet", which is the state every
        # routine starts in -- SP is 0 in a fresh Machine, so testing the
        # value alone would fire the SP-cleared stop on the first `ret` of
        # every routine, including the ones that never touch it.
        self.sp_written_to_zero = False

    # -- the register file, as named accessors so the interpreter below reads
    # like the disassembly rather than like array indexing ----------------

    @property
    def dptr(self):
        return (self.direct[self.DPH] << 8) | self.direct[self.DPL]

    @dptr.setter
    def dptr(self, value):
        self.direct[self.DPL] = value & 0xFF
        self.direct[self.DPH] = (value >> 8) & 0xFF

    @property
    def a(self):
        return Machine.UNKNOWN if self.a_unknown else self.direct[self.ACC]

    @a.setter
    def a(self, value):
        if value is Machine.UNKNOWN:
            self.a_unknown = True
        else:
            self.a_unknown = False
            self.direct[self.ACC] = value & 0xFF

    @property
    def sp(self):
        return self.direct[self.SP]

    @sp.setter
    def sp(self, value):
        self.direct[self.SP] = value & 0xFF

    # -- the store set, and what the walk saw ------------------------------

    def stored(self):
        """{xdata address: the last value the walk stored there}.

        Last-writer-wins because that is what a boot leaves behind: the vector
        clears `0x0000`-`0x00FF` through `0x0F75` and then copies a byte read
        from XDATA `0x2006` into `0x0004`, so the value at `0x0004` after boot
        is the copy, not the zero. Collapsing to a set would lose the
        difference between "the boot path zeroes this" and "the boot path
        writes this", which is the distinction the whole tool exists for.
        """
        out = {}
        for addr, value in self.writes:
            out[addr] = value
        return out

    def walked_set(self):
        """Every DPTR value an `inc dptr` advanced past -- the sweep, not the store.

        The gap between this and `stored()` is what `spared` is reported from.
        A clear that walks a range and stores every byte of it has no gap; a
        clear with a skip window has one, and the window's size falls out of the
        execution rather than being asserted.
        """
        return set(self.walked)


def _operand8(machine, pc, n):
    """The `n`-th operand byte of the instruction at `pc`, bounds-checked.

    A short window is a refusal rather than an `IndexError`: the caller is
    about to report a store set, and a truncated instruction is the case where
    that set would be short by an unknown amount.
    """
    if pc + n >= len(machine.image):
        raise Refusal(
            f"instruction at 0x{pc:04X} runs off the end of a "
            f"{len(machine.image)}-byte buffer")
    return machine.image[pc + n]


def _store(machine, addr: int, value: int) -> None:
    """One write into the direct space, with the two cells that need saying so.

    ACC and SP are cells of the same bytearray as everything else, and each has
    a side condition an ordinary assignment would drop: a known value landing
    in ACC retires the walk's "accumulator is unknown" flag, and a zero landing
    in SP is the fact `walk_routine()` needs to know it cannot follow a `ret`.
    Both are set here rather than at the call sites so an arm added later
    cannot write either cell and silently skip its condition.
    """
    machine.direct[addr] = value & 0xFF
    if addr == Machine.ACC:
        machine.a_unknown = False
    elif addr == Machine.SP:
        machine.sp_written_to_zero = value == 0


def _push_return(machine, address, target):
    """Push `address` as an 8051 return address and return `target`.

    Low byte first, then high -- the 8051's push order, and `ret` is written
    against it. Pushing high first still looks right while a call chain stays
    inside one routine, and only surfaces as a return address with its halves
    exchanged, which lands mid-instruction and reads as an unmodelled opcode
    somewhere unrelated.
    """
    machine.sp = (machine.sp + 1) & 0xFF
    machine.direct[machine.sp] = address & 0xFF
    machine.sp = (machine.sp + 1) & 0xFF
    machine.direct[machine.sp] = (address >> 8) & 0xFF
    return target


def _step(machine, pc):
    """Execute one instruction at `pc`; return the next pc, or None to stop.

    Each arm is one opcode this image's boot path uses, and the `else` is the
    refusal that keeps the set honest. The list is deliberately not derived from
    `OPCODE_LEN` -- that table says how long every opcode is, which is a
    different question from whether this tool knows what it *does*, and
    treating the length table as a semantics table is how a routine ends up
    executed with 256 opcodes half-modelled.

    The bounds test is first because a relative branch is free to leave the
    buffer: `sjmp -3` at offset 0 of a two-byte image computes a target of
    `0xFFFD`, which is a real 8051 address and not an index into this file. On
    the committed image nothing does that, so the test is here for the fixtures
    and for a different image, and it refuses rather than raising -- an
    `IndexError` out of the middle of a walk is a crash, and a crash is not a
    statement about the store set.
    """
    if not 0 <= pc < len(machine.image):
        raise Refusal(
            f"the walk left the {len(machine.image)}-byte buffer at "
            f"0x{pc:04X}; the store set reached so far is not reported")
    op = machine.image[pc]
    n = OPCODE_LEN[op]

    # `movx @dptr,a` and `inc dptr` are the two the store set is made of, so
    # they come first and are the two arms every comment below hangs off.
    if op == 0xF0:                                    # movx @dptr,a
        value = machine.a
        machine.xdata[machine.dptr] = value
        machine.writes.append((machine.dptr, value))
        return pc + 1
    if op == 0xA3:                                    # inc dptr
        machine.dptr = (machine.dptr + 1) & 0xFFFF
        machine.walked.add(machine.dptr - 1)
        return pc + 1
    if op == 0x90:                                    # mov dptr,#imm16
        machine.dptr = (_operand8(machine, pc, 1) << 8) | _operand8(machine, pc, 2)
        return pc + 3
    if op == 0xE0:                                    # movx a,@dptr
        machine.a = machine.xdata.get(machine.dptr, Machine.UNKNOWN)
        return pc + 1
    if op == 0xE4:                                    # clr a
        machine.a = 0
        return pc + 1
    if op == 0x74:                                    # mov a,#data
        machine.a = _operand8(machine, pc, 1)
        return pc + 2

    # Register/memory moves, all reading or writing the direct space or a
    # register by its encoded low three bits.
    if op in (0x75,):                                # mov direct,#data
        addr = _operand8(machine, pc, 1)
        _store(machine, addr, _operand8(machine, pc, 2))
        return pc + 3
    if 0xA8 <= op <= 0xAF:                           # mov Rn,direct
        machine.direct[op & 7] = machine.direct[_operand8(machine, pc, 1)]
        return pc + 2
    if 0xE8 <= op <= 0xEF:                           # mov a,Rn
        machine.a = machine.direct[op & 7]
        return pc + 1
    if 0x78 <= op <= 0x7F:                           # mov Rn,#data
        machine.direct[op & 7] = _operand8(machine, pc, 1)
        return pc + 2
    if 0x88 <= op <= 0x8F:                           # mov direct,Rn
        addr = _operand8(machine, pc, 1)
        value = machine.direct[op & 7]
        _store(machine, addr, 0 if value is Machine.UNKNOWN else value)
        return pc + 2
    if op == 0xC2:                                   # clr direct
        _store(machine, _operand8(machine, pc, 1), 0)
        return pc + 2
    if 0xC8 <= op <= 0xCF:                           # xch a,Rn
        # Through the `a` property both ways, so the unknown rides with the
        # accumulator rather than being dropped by a raw bytearray swap.
        reg = op & 7
        machine.a, machine.direct[reg] = machine.direct[reg], machine.a
        machine.sp_written_to_zero = machine.sp_written_to_zero or (
            reg == Machine.SP and machine.direct[reg] == 0)
        return pc + 1
    if op in (0xF6, 0xF7):                           # mov @Ri,a
        value = machine.a
        # An unknown cannot be a byte, so an UNKNOWN accumulator stores zero
        # rather than a value nobody established.
        _store(machine, machine.direct[op & 1],
               0 if value is Machine.UNKNOWN else value)
        return pc + 1
    if 0x08 <= op <= 0x0F:                           # inc Rn
        machine.direct[op & 7] = (machine.direct[op & 7] + 1) & 0xFF
        return pc + 1

    # Stack. `0x1100` pushes DPL and DPH and ends in `ret`, which is the whole
    # of how a BL51 trampoline reaches its target -- the return address the
    # `ret` pops is the DPTR the trampoline loaded. Modelling the stack is what
    # lets the stub be executed instead of interpreted.
    if op == 0xC0:                                   # push direct
        machine.sp = (machine.sp + 1) & 0xFF
        machine.direct[machine.sp] = machine.direct[_operand8(machine, pc, 1)]
        return pc + 2
    if op == 0xD0:                                   # pop direct
        addr = _operand8(machine, pc, 1)
        machine.direct[addr] = machine.direct[machine.sp]
        machine.sp = (machine.sp - 1) & 0xFF
        machine.sp_written_to_zero = machine.sp_written_to_zero or (
            addr == Machine.SP and machine.direct[addr] == 0)
        return pc + 2
    if op == 0xC5:                                   # push acc
        machine.sp = (machine.sp + 1) & 0xFF
        value = machine.a
        machine.direct[machine.sp] = 0 if value is Machine.UNKNOWN else value
        return pc + 1
    if op == 0xD5:                                   # pop acc
        machine.a = machine.direct[machine.sp]
        machine.sp = (machine.sp - 1) & 0xFF
        return pc + 1

    # Arithmetic and the carry. `subb` is the only one the boot path's bounds
    # tests use, and `setb c` at `0xD982` is what makes the second chain's
    # bound read `0x0800` rather than the `0x07FF` its own immediates spell --
    # a borrow is computed with the carry *in*, not cleared and re-applied.
    if op == 0xC3:                                   # clr c
        machine.carry = 0
        return pc + 1
    if op == 0xD3:                                   # setb c
        machine.carry = 1
        return pc + 1
    if op == 0x94:                                   # subb a,#data
        value = _operand8(machine, pc, 1)
        if machine.a_unknown:
            raise Refusal(
                f"`subb a,#0x{value:02X}` at 0x{pc:04X} operates on an "
                "accumulator this walk could not establish, because a "
                "`movx a,@dptr` loaded a byte no instruction here wrote; the "
                "walk stops rather than substitute a value")
        result = machine.a - value - machine.carry
        machine.carry = 1 if result < 0 else 0
        machine.a = result & 0xFF
        return pc + 2

    # Relative branches. The displacement is signed and relative to the byte
    # after the instruction; `reset-vector-dptr-targets.md` records that
    # reading these as absolute step-overs corrupts the carry into the first
    # `subb`, which is this loop's whole arithmetic.
    if op in (0x40, 0x50, 0x60, 0x70, 0x80):         # jc/jnc/jz/jnz/sjmp
        taken = relative_target(op, _operand8(machine, pc, 1), pc)
        if op == 0x80 or (op == 0x40 and machine.carry) \
                or (op == 0x50 and not machine.carry) \
                or (op == 0x60 and machine.a == 0) \
                or (op == 0x70 and machine.a != 0):
            return taken
        return pc + n

    # Control transfer. `lcall`/`acall` are followed and their targets recorded,
    # so the routine set is what the walk reached rather than a list written
    # here. An `ljmp` is followed too -- that is how the BL51 stub runs -- but
    # the one named transfer this tool will not follow stops the walk with its
    # reason, because the alternative is the step budget.
    if op in (0x12,):                                # lcall addr16
        target = (_operand8(machine, pc, 1) << 8) | _operand8(machine, pc, 2)
        machine.routines.append(target)
        if machine.collect_only:
            # Skipped, not entered: the walk continues along the vector's own
            # body, which is where `0x0004`'s second write comes from.
            return pc + n
        return _push_return(machine, pc + 3, target)
    if op == 0x02:                                   # ljmp addr16
        target = (_operand8(machine, pc, 1) << 8) | _operand8(machine, pc, 2)
        if target in machine.stubs:
            # A BL51 stub, reached by a trampoline: control passes to the
            # routine named in DPTR. **No return address is pushed** -- the
            # trampoline's `ljmp` is a tail transfer, and the frame the target
            # returns through is the `lcall` the vector made to reach the
            # trampoline. Pushing one here would return into the bytes after
            # the `ljmp` -- the next trampoline's operand -- and decode as
            # whatever that is, which is how this arm looked like an unmodelled
            # opcode three routines later. Modelled as a jump rather than by
            # running the stub's own bytes; see `Machine.stubs`.
            machine.routines.append(machine.dptr)
            if machine.collect_only:
                return pc + n
            return machine.dptr
        if target == TAIL_TARGET:
            raise StopWalk(pc, target,
                           f"the vector's tail-jump to 0x{target:04X}, the "
                           "scheduler the reset hands control to rather than "
                           "an initialiser")
        return target
    if op == 0x22:                                   # ret
        # An empty stack means the outermost frame returned; the walk is over.
        if machine.sp == machine.base_sp:
            return None
        high = machine.direct[machine.sp]
        machine.sp = (machine.sp - 1) & 0xFF
        low = machine.direct[machine.sp]
        machine.sp = (machine.sp - 1) & 0xFF
        return (high << 8) | low

    raise Refusal(
        f"opcode 0x{op:02X} at 0x{pc:04X} is not modelled by this tool, so "
        "the walk stops rather than skip an instruction and report the store "
        "set it reached as if it were the whole one")


class StopWalk(Exception):
    """A named, expected end to the walk -- carried, not raised as a failure.

    Distinct from `Refusal` because the two mean opposite things to a reader:
    a refusal says "this run's answer is not trustworthy", and a stop says
    "this run's answer is the walk up to here, and here is where it stopped".
    The `0x00CF` tail-jump is the case this exists for -- reported on every
    run so the exclusion is visible, and not treated as an error because the
    answer up to that point is the answer.

    `pc` and `target` are attributes rather than the positional arguments
    `Exception` would take and discard, so a handler can say where the walk
    stopped instead of re-deriving it from a message.
    """

    def __init__(self, pc, target, reason):
        super().__init__(reason)
        self.pc = pc
        self.target = target
        self.reason = reason


def boot_routines(image: bytes, stubs) -> list:
    """The boot path as an ordered list of steps: writes and routine entries.

    Each element is either `("writes", [(addr, value), ...])` for a stretch of
    the vector's own body, or `("routine", entry)` for a call it makes. The
    **order is the vector's**, and it is load-bearing: `0x0070` writes XDATA
    `0x1001`, calls `0x0F75` (which clears `0x0000`-`0x00FF`), and only then
    copies a byte from XDATA `0x2006` to `0x0004`. So what `0x0004` holds after
    boot is the copy, not the zero, and a reader that concatenated the vector's
    own stores before the routines' would report it cleared. Returning steps
    rather than two separate lists is what keeps that ordering visible.

    `common 0x0000` is a single `ljmp 0x0070`. Each `lcall` becomes a
    `routine` step, and each `mov DPTR,#imm16` followed by an `ljmp` to a BL51
    stub becomes a `routine` step naming the DPTR value -- the shape
    `bl51_trampolines` already owns, with the stub set read from
    `ghidra-functions.csv`.

    **The calls are recorded, not descended into**, and that is the load-bearing
    part. `0x0F75` is `clr_xdata_0000_00ff_iram_20_bf_xdata_9000_97ff`: its IRAM
    loop zeroes `0x20`-`0xBF`, and `0x81` is SP, so that routine zeroes the
    stack pointer the vector is standing on. A walk that executed the vector as
    one call chain would arrive at `0x0F75`'s `ret` with no stack to unwind and
    follow whatever the cleared IRAM made of the return address -- a number
    this tool would then report as a call target. Reading the calls off the
    vector's bytes and executing each routine on its own has no such failure,
    and is the more conservative shape besides: a routine's stores are what
    that routine does, not what its caller's stack state let it do.
    """
    machine = Machine(image, stubs)
    machine.collect_only = True
    machine.base_sp = STACK_TOP
    steps = []
    pending = []
    pc = RESET_VECTOR
    budget_steps = 64              # the vector is 0x22 bytes; a backstop
    for _ in range(budget_steps):
        machine.routines = []
        before = len(machine.writes)
        try:
            nxt = _step(machine, pc)
        except StopWalk as stop:
            machine.stops.append((pc, "not followed", stop.reason))
            break
        pending.extend(machine.writes[before:])
        for entry in machine.routines:
            if pending:
                steps.append(("writes", pending))
                pending = []
            steps.append(("routine", entry))
        if nxt is None:
            break
        pc = nxt
    else:
        raise Refusal(
            "the reset vector's decode did not reach its tail-jump within the "
            "instruction backstop; the routine list below would be incomplete")
    if pending:
        steps.append(("writes", pending))
    steps.append(("stops", machine.stops))
    return steps


def walk_routine(image: bytes, entry: int, budget: int = STEP_BUDGET,
                 stubs=()) -> Machine:
    """Execute one routine from `entry` to its `ret`; return the Machine.

    Each routine gets a fresh machine, which is what makes the answer a
    property of the routine rather than of where the walk happened to arrive
    from. SP starts at 0xC0 and a `ret` at that depth ends the walk.

    **A routine that clears SP ends the walk there, and says so.**
    `0x0F75` is `clr_xdata_0000_00ff_iram_20_bf_xdata_9000_97ff` -- its IRAM
    loop zeroes `0x20`-`0xBF`, and `0x81` is SP, so by the time its `ret` at
    `0x0FA5` executes the stack pointer reads 0. A faithful interpreter then
    pops the return address out of cleared IRAM and jumps into whatever those
    bytes decode as, which is not a call this vector made.

    That is a real property of the firmware and this tool reports it rather
    than working around it: the walk stops **on** that `ret`, which
    `0F75.asm` places after all three of the routine's clearing loops, and
    records a stop naming the address and the reason. Every store the routine
    makes is already recorded when the walk halts, so nothing this tool claims
    about its XDATA rests on the return address it cannot follow. The argument
    is where that `ret` sits, not the order of the loops -- which is not what
    the routine's name suggests, because the IRAM loop sits *between* the two
    XDATA loops (`0F77`-`0F85`, `0F87`-`0F93`, `0F95`-`0xFA3`), so
    `0x9000`-`0x97FF` is stored after SP has already been zeroed. What is *not*
    claimed is anything about what the EC does next, which is exactly what the
    follow-on control flow would have to establish.
    """
    machine = Machine(image, budget, stubs)
    machine.base_sp = STACK_TOP
    machine.sp = STACK_TOP     # the vector's `mov 0x81,#0xC0` before its calls
    machine.sp_written_to_zero = False
    pc = entry
    steps = 0
    while True:
        if steps >= budget:
            raise Refusal(
                f"the walk of 0x{entry:04X} used its whole budget of {budget} "
                "steps without reaching a `ret`; the store set reached so far "
                "is not reported")
        steps += 1
        if pc >= len(image):
            raise Refusal(
                f"the walk of 0x{entry:04X} left the {len(image)}-byte buffer "
                f"at 0x{pc:04X}; the store set reached so far is not reported")
        if op_is_ret(image, pc) and machine.sp_written_to_zero:
            machine.stops.append((
                pc, "return address not followed",
                f"0x{entry:04X} cleared SP (it zeroes IRAM 0x20-0xBF, which "
                "includes 0x81), so this `ret` pops the return address out of "
                "cleared IRAM; the stores above are complete, and where "
                "control goes next is not established here"))
            return machine
        pc = _step(machine, pc)
        if pc is None:
            return machine


def op_is_ret(image: bytes, pc: int) -> bool:
    """Whether the byte at `pc` is `ret`, for a check made before executing it."""
    return pc < len(image) and image[pc] == 0x22


def walk_boot(image: bytes, stubs=()) -> Machine:
    """Execute the boot path step by step; return the union of the stores.

    The steps run in the order `boot_routines()` returns them, and
    `Machine.stored()` is last-writer-wins over the whole sequence -- so the
    value an address holds at the end of boot is the last one written, in the
    order the vector writes it. That is the difference between `0x0004` being
    `cleared` and being `written-unknown`, and only the ordering distinguishes
    them.
    """
    combined = Machine(image, stubs)
    for kind, payload in boot_routines(image, set(stubs)):
        if kind == "writes":
            combined.writes.extend(payload)
        elif kind == "routine":
            combined.routines.append(payload)
            machine = walk_routine(image, payload, stubs=stubs)
            combined.walked |= machine.walked
            combined.writes.extend(machine.writes)
            combined.stops.extend(machine.stops)
        else:
            combined.stops.extend(payload)
    return combined


def verdict(addr: int, machine: Machine, stored) -> str:
    """The five-token verdict for `addr`, from what the walk did to it.

    `spared` is checked before `not-reached` because a byte the walk advanced
    past without storing is a more specific finding than one it never reached,
    and reporting the second for the first would lose the skip window the tool
    exists to show.
    """
    if addr in stored:
        value = stored[addr]
        if value is Machine.UNKNOWN:
            return "written-unknown"
        return "cleared" if value == 0 else "written"
    if addr in machine.walked_set():
        return "spared"
    return "not-reached"


def _ranges(addrs) -> list:
    """A set of addresses as inclusive (lo, hi) runs, for a summary line.

    A 6,141-byte store set printed as a list is unreadable, and a summary that
    only says the size cannot be checked against a claim about *which* bytes.
    The runs are the form both are readable in.
    """
    out = []
    for addr in sorted(addrs):
        if out and addr == out[-1][1] + 1:
            out[-1][1] = addr
        else:
            out.append([addr, addr])
    return [(lo, hi) for lo, hi in out]


VERDICTS = ("cleared", "written", "written-unknown", "spared", "not-reached")

# The CSV's columns. `boot_value` is spelled as the byte the walk left there --
# `0x00`, `0x3f`, `unknown`, or `none` -- so a row carrying `written-unknown`
# cannot be read as a row carrying a value this tool measured, and a `spared`
# byte cannot be read as one that was written at all. `direct_sites` and
# `regions` are the delegated half: the count from `trace_xdata_refs.sites_for`
# and its region split, which is what keeps a `MOV DPTR,#addr` in the separate
# PD image from reading as an EC reference to the same number.
CSV_COLUMNS = ["addr", "boot_verdict", "boot_value", "direct_sites", "regions"]


def boot_addresses(machine: Machine):
    """Every address the walk has something to say about, sorted.

    Walked, written or spared -- the union, so a byte the vector writes
    directly (`0x1001`) is in the table even though no loop walked it. A
    census and not a filtered view of one: filtering to "interesting" addresses
    is the move `code_pointer_sites.py` refuses in `refuse_filtering()`, because
    the smaller list is indistinguishable from one that found nothing.
    """
    addrs = set(machine.walked_set()) | set(machine.stored())
    return sorted(addrs)


def direct_index(image: bytes) -> dict:
    """{address: [file offsets of its direct MOV DPTR sites]}, one pass.

    `trace_xdata_refs.sites_for()` answers the same question for one address by
    rescanning the whole image, which is right for its own command line and far
    too slow here: a table over the boot path's 6,000-odd addresses would be
    6,000 scans of 256 KiB. One pass builds the same answer, and the per-address
    half is delegated rather than re-derived -- `MOV_DPTR` is
    `trace_xdata_refs`' own constant and the offsets it yields are the ones
    `sites_for()` returns, which `test_boot_xdata_sites.py` holds on fixtures.
    """
    out = {}
    for off in range(len(image) - 2):
        if image[off] == MOV_DPTR:
            out.setdefault((image[off + 1] << 8) | image[off + 2],
                           []).append(off)
    return out


def direct_report(index: dict, addr: int, pd_verified: bool):
    """(count, region split text) for `addr`, from `direct_index()`."""
    found = index.get(addr, [])
    tally = collections.Counter(region_of(o, pd_verified)[0] for o in found)
    return len(found), " ".join(f"{k}={v}" for k, v in sorted(tally.items()))


def boot_value(addr: int, machine: Machine, stored) -> str:
    """The `boot_value` cell: the byte the walk left there, spelled.

    Three spellings, because two different "no value" cases would otherwise
    share one. `unknown` is a byte the walk wrote and could not establish;
    `none` is a byte the walk did not write at all -- a `spared` one. Collapsing
    them would put `0x07FD` in a table as a value nobody stored.
    """
    if addr not in stored:
        return "none"
    value = stored[addr]
    return "unknown" if value is Machine.UNKNOWN else f"0x{value:02x}"


def csv_table(image: bytes, machine: Machine, pd_verified: bool) -> str:
    """The `--csv` table, as a string so `--check` diffs the same bytes."""
    stored = machine.stored()
    index = direct_index(image)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)
    for addr in boot_addresses(machine):
        count, regions = direct_report(index, addr, pd_verified)
        writer.writerow([
            f"0x{addr:04X}",
            verdict(addr, machine, stored),
            boot_value(addr, machine, stored),
            count,
            regions,
        ])
    return buf.getvalue()


def parse_addr(text: str) -> int:
    """One hex address, 0-0xFFFF, as an int. A range bound or a bad digit is a
    refusal naming the text rather than a `ValueError` traceback: the caller is
    a command line, and the reader who typed it is the one who can fix it."""
    try:
        value = int(text, 16)
    except ValueError:
        raise Refusal(f"{text!r} is not a hex address")
    if not 0 <= value <= 0xFFFF:
        raise Refusal(f"{text!r} is outside the 16-bit XDATA space")
    return value


def report(machine: Machine, image: bytes) -> str:
    """The `--report` block: what the walk reached, and where it stopped.

    The routine list is the tool's central claim about its own scope -- that the
    clearers are the ones the vector's own bytes name, not the ones someone
    enumerated -- so it is printed on every `--report` run rather than left to
    the code. The stops are printed beside it for the same reason: a reader who
    wants to know what this walk did not follow should not have to read the
    source to find out.
    """
    lines = [f"boot walk from the reset vector 0x{RESET_VECTOR:04X} over a "
             f"{len(image)}-byte image:",
             f"  routines reached: {len(machine.routines)}"]
    for target in machine.routines:
        lines.append(f"    0x{target:04X}")
    # Wrapped rather than one line per stop: these reasons are sentences, and a
    # single 160-column line is unreadable in a terminal and unreadable in a
    # diff. `textwrap` on the reason alone, so the `stopped at` prefix stays
    # greppable.
    for pc, kind, detail in machine.stops:
        head = f"  stopped at 0x{pc:04X}, {kind}: "
        wrapped = textwrap.wrap(detail, width=76,
                                initial_indent=head, subsequent_indent="    ")
        lines.extend(wrapped)
    return "\n".join(lines)


def self_test(image: bytes) -> int:
    """Known answers from outside this file, then the refusals.

    The known answers are transcribed from
    `../../docs/findings/reset-vector-dptr-targets.md` -- its 3,837 stored
    bytes and its three spared ones, both reached by executing the same
    committed instructions -- and from the committed listings for the routine
    set. A tool graded against its own output is not being tested, so none of
    these numbers is one this file computes elsewhere.

    The refusals are the half that matters. Each builds a buffer that would
    produce a plausible short store set if the guard were missing, and asserts
    that the run stops with its reason instead.
    """
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"  {label}: got {got!r}, want {want!r}")

    # The known answers, against the committed image. The routine set is the
    # four the vector's own bytes name: `0x110A`, the two trampolines `0x158E`
    # and `0x1594`, and `0x0F75`. The two XDATA clearers among them are
    # `0x0F75` and whatever `0x1594`'s DPTR names.
    stubs = boot_stubs()
    machine = walk_boot(image, stubs=stubs)
    check("routines the vector calls", sorted(set(machine.routines)),
          [0x0F75, 0x110A, 0x158E, 0x1594])
    check("XDATA bytes written", len(machine.stored()), 6142)
    check("XDATA bytes walked", len(machine.walked_set()), 6144)
    check("spared", sorted(machine.walked_set() - set(machine.stored())),
          [0x07FD, 0x07FE, 0x07FF])

    # The four counters, one row each -- the answer the write-up rests on.
    stored = machine.stored()
    for addr in (0x09C7, 0x09C8, 0x09C9, 0x09CA):
        check(f"verdict 0x{addr:04X}", verdict(addr, machine, stored), "cleared")
    check("verdict 0x07FD", verdict(0x07FD, machine, stored), "spared")
    check("verdict 0x07FF", verdict(0x07FF, machine, stored), "spared")
    check("verdict 0x1001", verdict(0x1001, machine, stored), "written")
    check("verdict 0x1000", verdict(0x1000, machine, stored), "not-reached")

    # The value left at 0x0004: the vector clears it through `0x0F75` and then
    # copies a byte read from XDATA `0x2006` over it, so it is neither zero nor
    # anything this walk can name. The `written-unknown` token exists for this
    # one address and would be dead weight without it.
    check("verdict 0x0004", verdict(0x0004, machine, stored), "written-unknown")
    check("value at 0x0004 is UNKNOWN",
          stored.get(0x0004) is Machine.UNKNOWN, True)
    # ... and last-writer-wins is what makes that true: the clear wrote 0 there
    # first and the copy overwrote it.
    check("0x0004 was written twice",
          [a for a, _ in machine.writes].count(0x0004), 2)

    # `0xD96C` on its own, as `reset-vector-dptr-targets.md` measured it. Run
    # directly rather than out of the full walk so this is an oracle rather
    # than a restatement of the run above.
    alone = walk_routine(image, 0xD96C, stubs=stubs)
    check("0xD96C stored", len(alone.stored()), 3837)
    check("0xD96C walked", len(alone.walked_set()), 3840)
    check("0xD96C spared",
          sorted(alone.walked_set() - set(alone.stored())),
          [0x07FD, 0x07FE, 0x07FF])

    # `0x0F75` on its own: the second boot-path clearer, and the one that makes
    # this a walk of the boot path rather than of one routine. Nothing in the
    # reset vector's bytes points at it as an XDATA clearer -- its own
    # annotation name is the only place the two ranges appear -- so a tool that
    # enumerated clearers by hand would have missed them.
    other = walk_routine(image, 0x0F75, stubs=stubs)
    check("0x0F75 stored", len(other.stored()), 2304)
    check("0x0F75 ranges", _ranges(other.stored()),
          [(0x0000, 0x00FF), (0x9000, 0x97FF)])

    # `0x0F75` clears SP -- IRAM 0x20-0xBF, and 0x81 is SP -- so its `ret`
    # cannot be followed. The stop is named and the stores are still reported,
    # which is the property the SP guard exists to preserve.
    check("0x0F75 stops on the cleared SP", len(other.stops), 1)
    check("0x0F75 stop names the ret",
          other.stops[0][2].startswith("0x0F75 cleared SP"), True)

    # `0x110A` and the trampolines write no XDATA at all, which is a result
    # rather than an absence of one: they were executed.
    for entry in (0x110A, 0x158E):
        leaf = walk_routine(image, entry, stubs=stubs)
        check(f"0x{entry:04X} writes no XDATA", len(leaf.stored()), 0)

    # The BL51 stub set, read rather than written out -- the rule the
    # trampoline pair is modelled with, and the one place a stub address
    # added to this file instead would go unnoticed.
    check("BL51 stub set", stubs, {0x1100, 0x1114, 0x1128, 0x113C})

    # The refusals. Each buffer is one that would yield a short, plausible
    # store set if its guard were removed.
    def refuses(label, buffer, start, budget=STEP_BUDGET):
        try:
            walk_routine(buffer, start, budget)
        except Refusal:
            return
        failures.append(f"  {label}: the walk completed instead of refusing")

    # An opcode with no arm. `0xFF` decodes as `mov r7,a`, which no boot-path
    # routine executes, and a byte scan that treated it as `nop` would produce a
    # store set one byte short of the truth and read as complete.
    refuses("unmodelled opcode", bytes([0x90, 0x01, 0x00, 0xFF, 0x22]), 0x0000)
    # A window that runs off the end. `mov dptr,#0x1234` with one operand byte
    # present: the immediate would be half a number and the store set empty.
    refuses("truncated immediate", bytes([0x90, 0x34]), 0x0000)
    # The budget. A `sjmp -2` is an infinite loop with no unmodelled opcode, so
    # only the budget can stop it.
    refuses("budget exhausted", bytes([0x80, 0xFD]), 0x0000, budget=64)
    # An entry past the end of the buffer, which is the truncation case from
    # the other direction.
    refuses("entry past the buffer", bytes([0x22]), 0x0100)
    # A `subb` on an accumulator no store established. `movx a,@dptr` of an
    # address nothing wrote, then `subb`: the arithmetic has no value to do,
    # and substituting zero would invent one.
    refuses("subb on an unknown accumulator",
            bytes([0x90, 0x34, 0x12, 0xE0, 0x94, 0x01, 0x22]), 0x0000)

    if failures:
        print("self-test FAILED:", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        return 1
    print("boot_xdata_sites self-test: all assertions passed")
    return 0


def _rows(path: str = ANNOTATIONS):
    """The annotation rows `stub_addresses()` reads, from the committed CSV.

    Rows go in as the committed CSV spells them, because
    `stub_addresses()` normalises the `addr` column itself and expects a
    string; it hands back strings too, so `boot_stubs()` is what parses them
    into the integers `ljmp` targets compare against. Splitting it that way
    keeps one spelling rule in the file that owns it.
    """
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, strict=True))


def boot_stubs(path: str = ANNOTATIONS) -> set:
    """The BL51 bank-select stub addresses as ints, for `Machine.stubs`.

    `stub_addresses()` returns normalised strings because it compares them
    against the `ljmp` operand text a listing carries; this walk compares
    against decoded integers. Both spellings are of one address, and a set of
    strings compared against a set of ints matches nothing -- which would leave
    every trampoline unrecognised and the walk reporting one clearer's stores
    as the boot path's.
    """
    return {int(norm_addr(addr), 16)
            for addr in stub_addresses(_rows(path))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("addrs", nargs="*",
                    help="hex XDATA addresses to report on")
    ap.add_argument("--firmware", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("--lo", help="low address of a range to report on")
    ap.add_argument("--hi", help="high address of a range to report on")
    ap.add_argument("--report", action="store_true",
                    help="print the routines the boot walk reached, the stop "
                         "that ended it, and the walked/written counts")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-address table as CSV on stdout")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="with --csv, diff this run against a committed table "
                         "and exit non-zero on any difference (default: "
                         "boot-xdata-sites.csv)")
    ap.add_argument("--self-test", action="store_true",
                    help="known answers against the committed image, and the "
                         "refusals")
    args = ap.parse_args(argv)

    if args.self_test:
        try:
            return self_test(open(args.firmware, "rb").read())
        except Refusal as exc:
            print(f"self-test refused: {exc}", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"note: {exc}", file=sys.stderr)
            return 1

    if (args.check is not None) and not args.csv:
        ap.error("--check is about the --csv table; it needs --csv")

    try:
        image = open(args.firmware, "rb").read()
    except OSError as exc:
        print(f"note: {exc}", file=sys.stderr)
        return 1

    off, magic = PD_MARKER
    pd_verified = image[off:off + len(magic)] == magic
    if not pd_verified:
        # stderr, so --csv output stays a clean CSV when redirected, and said
        # rather than assumed: without the marker the 0x20000 region is a
        # different program and its sites are not EC references.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "sites in 0x20000-0x2FFFF will be reported as region 'unknown'\n",
              file=sys.stderr)

    try:
        machine = walk_boot(image, stubs=boot_stubs())

        if args.report:
            print(report(machine, image))

        if args.csv:
            table = csv_table(image, machine, pd_verified)
            if args.check is not None:
                return check_table(table, args.check)
            sys.stdout.write(table)
            return 0

        wanted = []
        for text in args.addrs:
            wanted.append(parse_addr(text))
        if (args.lo is None) != (args.hi is None):
            raise Refusal("--lo and --hi are a range and are wanted together")
        if args.lo is not None:
            lo, hi = parse_addr(args.lo), parse_addr(args.hi)
            if lo > hi:
                raise Refusal(f"--lo 0x{lo:04X} is above --hi 0x{hi:04X}")
            wanted.extend(range(lo, hi + 1))

        stored = machine.stored()
        index = direct_index(image)
        tally = collections.Counter()
        for addr in wanted:
            state = verdict(addr, machine, stored)
            tally[state] += 1
            count, regions = direct_report(index, addr, pd_verified)
            print(f"0x{addr:04X}  {state:<16} direct sites: {count}"
                  + (f"  [{regions}]" if regions else ""))

        if wanted:
            print()
            print("  " + "  ".join(f"{k}={tally[k]}"
                                  for k in VERDICTS if tally[k]))
        else:
            # No address asked for, so the answer is the shape of the store set
            # rather than 6,144 rows of it. `--csv` is the row-per-address
            # form; printing one line per byte here would bury the runs that
            # make the set readable.
            print(f"  XDATA bytes written: {len(stored)}")
            for lo, hi in _ranges(stored):
                print(f"    0x{lo:04X}-0x{hi:04X}  ({hi - lo + 1} bytes)")
            spared = sorted(machine.walked_set() - set(stored))
            print(f"  walked but not written: {len(spared)}")
            for lo, hi in _ranges(spared):
                print(f"    0x{lo:04X}-0x{hi:04X}  spared")
            print("  ask for addresses to see one row each, or --csv for the "
                  "whole table")
        print("  a `spared` byte is one the walk advanced past without "
              "storing;\n  `not-reached` is about this walk only, and does "
              "not exclude an indirect\n  or DPTR-handed store from "
              "elsewhere -- xdata-0440-readers.md §7.5\n  names that "
              "population and this tool does not search it.")
        return 0
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except StopWalk as exc:
        # A stop that escaped `walk_boot` is a stop outside a walk, which no
        # current caller does; reported rather than swallowed so a future one
        # that does not expect it finds out.
        print(f"stopped at 0x{exc.pc:04X}: {exc.reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())