#!/usr/bin/env python3
"""Report the last definition of DPH and of DPL on each path that reaches a
runtime address, crossing `lcall` into the callee.

**What the question is.** A `movx @DPTR,A` whose DPTR was assembled out of a
register pair names no XDATA address, so every `MOV DPTR,#imm16` scan in this
repository is blind to it: `trace_xdata_refs.py` sees only the sites that
build the pointer inside the instruction, and the store at `bank1:0xDE96`
builds it in the two instructions before it. The question is what the pointer
holds *there*, and the only way to answer it without running the EC is to
walk back.

**This is not the other two scanners, and the difference is the point.**

  * `find_indirect_xdata.py` covers `movx @Ri`, whose page is in `P2` and
    whose low byte is in the register. A pointer assembled from `R2:R1` and
    read through `@DPTR` is the *other* 8051 XDATA addressing mode, so that
    sweep's population does not contain this question and its zero is not an
    answer to it.
  * `trace_xdata_refs.py`'s `walk()` is a **linear** decode: it stops at the
    first control-flow instruction, so it cannot leave a frame and come back.
    The clobber this tool exists to find lives in a *callee*, which is
    exactly the edge a linear window cannot cross.
    `../../docs/findings/dptr-rebuild-walk-guard.md` is what that blindness
    cost, and `../../docs/findings/de3c-1c04-to-0563.md` is what this tool
    found when it was pointed at the same site.

**Crossing the call is sound here for a reason worth naming.** The 8051 has no
calling convention: `lcall` pushes a return address and nothing else, `R0`-`R7`
belong to whichever frame is running, and a callee that writes them has
changed the caller's registers by the time it returns. A backward walk that
stepped from a call's fall-through to the call's *own* predecessors would be
assuming a callee-saved register set this architecture does not have. This
walk steps instead to every `ret` in the callee, which is the only sound
choice, and it is what makes the `bank1:0xB6DE` clobber visible at all.

**One condition is tracked, and it is the one the answer turns on: `CY`.**
`jc`/`jnc` add `CY=1`/`CY=0` to a path, a definition that contradicts one
prunes the path, and a definition whose value this tool does not carry
*releases* the condition rather than pruning it. No other condition is
modelled -- not `A`, not the bit forms -- so `jz`, `jnz` and `cjne`
contribute control flow but no predicate. That direction is deliberate: an
untracked condition can only leave **extra** paths in the answer, never remove
a real one, so the reported set of definitions is a superset and every "not
written on this path" is a statement about the paths followed rather than
about the program. A tight answer would need a real symbolic executor and
would be worth less than a loose one that says where it is loose.

**A path this tool could not follow is printed, not dropped.** Every one of:
an address with no decoded instruction, a branch or call out of the region, a
callee with no decoded `ret` in its extent, a byte that reads as a `ret` the
flow decode never reached, an opcode with no writer model, and the step
budget. A pointer this tool cannot resolve is reported as unresolved, which is
this repository's standing answer for a static method that cannot close a
question -- never as an address nobody chose.

**What it does not establish.** Two committed inputs and nothing else: the
firmware image, for every value, and `ec/decompiled/index.csv`, for where the
functions start. No capture, no EC, no Windows. A resolved pointer says what
the bytes assemble, not what the EC does with the byte written through it.
A routine `index.csv` does not list is not walked at all -- "not found by this
method", the caveat `trace_xdata_refs.py` and `find_indirect_xdata.py` both
carry. Only `CY` is carried as a condition, so the path set is a superset of
the real one and the write-up says which reading the extra paths could change.
No hardware is reachable from a GitHub-hosted runner and none of this claims
otherwise.

Usage:
    python3 r1r2_predecessor.py ../firmware/GMxMGxx_11.800 --at 0x15E96
    python3 r1r2_predecessor.py ../firmware/GMxMGxx_11.800 --at bank1:0xDE96 --csv
    python3 r1r2_predecessor.py ../firmware/GMxMGxx_11.800 --at 0x15E96 --max-steps 500
"""
import argparse
import bisect
import collections
import csv
import io
import os
import sys

from disasm8051 import (OPCODE_LEN, REL_OPCODES, inline_arg_len, mnemonic,
                        paged_target, relative_target)
from trace_xdata_refs import PD_MARKER, REGIONS, region_of

# The bytes this tool tracks. DPL and DPH are the question; R0-R7 and A are
# what a pointer is usually assembled from, and CY is the one predicate (see
# the module docstring). `P2` is deliberately absent: it is the `movx @Ri`
# page, and this tool is not that addressing mode.
A, CY, DPL, DPH = "A", "CY", "DPL", "DPH"
REGS = tuple(f"R{n}" for n in range(8))

# The recipe a definition carries: `(kind, note)`. `CONST` is an answer, `FROM`
# and `XDATA` name the symbols whose own definitions the walk then follows,
# and `UNKNOWN` is terminal -- "an instruction this tool does not model wrote
# it". A chain that reaches one has no answer, and a cell that said "unknown"
# without saying which instruction gave up would read as a verdict on the byte.
CONST, FROM, XDATA, UNKNOWN = "const", "from", "xdata", "unknown"

# The tokens for "no answer", kept apart because they are different claims.
# UNMODELLED is a gap in this file's table; UNRESOLVED is the walk reaching a
# point where the wanted symbol's value is carried by something it cannot
# follow. Merging them would make a table gap look like a property of the code.
UNMODELLED = "no writer model for opcode 0x%02x"
UNRESOLVED = "value not carried by this walk"
# Two ways a wanted symbol can come back with fewer definitions than there were
# paths, and they are different claims. The first is a property of the code:
# on some path the walk followed, nothing wrote it. The second is a limit on
# the method: a path was cut, so the answer says so instead of reading as
# complete. Rendering neither would make a partial answer indistinguishable
# from a total one, which is the overclaim this repository's calibration rule
# is about.
UNWRITTEN_SOME = "not written on some path followed"
UNWRITTEN_NONE = "not written on any path followed"
CUT_PATH = "no definition on a path this tool could not follow"
NO_INSN = "no instruction decoded at 0x%04x"
NO_RETURN = "no decoded ret in 0x%04X's extent"
UNREACHED_RET = "0x%04X reads as a ret but the flow decode never reached it"
OUT_OF_REGION = "branch target 0x%04x is outside the region"
BUDGET = "step budget (%d) exhausted"

# The two words the report uses for a path the walk dropped, which are also
# two different things: a contradiction (a definition that cannot hold under
# the path's own condition) and an admission (no way to continue).
PRUNED, UNFOLLOWED = "pruned", "not followed"

# `0xA1` (anl c,/bit), `0xB1` (cpl bit) and `0xC1` (clr bit) collide with the
# 2-byte paged `ajmp`/`acall` test -- `0xA1 & 0x1F == 0x01` and
# `0xB1 & 0x1F == 0x11` -- because the bit forms and the page jumps share the
# encoding. `trace_xdata_refs.call_target()` reads those three as branches and
# this tool does not, deliberately: a fabricated edge here is a fabricated
# *predecessor*, and a predecessor is where definitions come from. Excluding
# them costs a branch this walk will not follow, which the report says.
NOT_PAGED = frozenset((0xA1, 0xB1, 0xC1))

RET_OPCODES = (0x22, 0x32)
CALL_OPCODES = (0x12,)


def writers(d: bytes, i: int):
    """-> ({symbol: (kind, note)},) for the instruction at `d[i]`, or `None`
    when this table has no model for the opcode.

    `None` means **unmodelled**, and the walk treats it as writing every
    tracked symbol with a value it cannot carry, which stops that path and
    says so. That is the safe direction: an opcode missing from this table
    costs recall (a path that stops early and is reported as not followed) and
    never precision (a definition reported that is not one). The alternative,
    treating an unlisted opcode as writing nothing, is the direction that
    overclaims.

    **Keyed on bytes, never on `mnemonic()`.** `disasm8051.mnemonic()` prints
    the A-operand half of the `0x44`/`0x45`/`0x54`/`0x55`/`0x64`/`0x65` group
    and renders the direct half -- `0x43`/`0x53`/`0x63` -- as `db`, so a
    text-matching writer table would be blind on exactly the opcodes that
    write a direct byte, which is where DPTR is written from.
    `trace_xdata_refs.is_dptr_rebuild()` keys on bytes for the same reason,
    and §1 of `../../docs/findings/dptr-rebuild-walk-guard.md` is what that
    defect costs elsewhere.
    """
    op = d[i]
    n = OPCODE_LEN[op]
    if i + n > len(d):
        return None
    unres = (UNKNOWN, UNRESOLVED)

    def direct(off):
        """The symbol a direct-byte *address* operand names, or None."""
        if off >= n:
            return None
        return {0x82: DPL, 0x83: DPH}.get(d[i + off])

    def bit(off):
        """The symbol a bit-addressable operand names, or None.

        Carry is bit address `0xD3`, which is the encoding `setb C` also has;
        that is not an ambiguity here because both spellings reach this
        function and both mean the same byte.
        """
        if off >= n:
            return None
        return {0x82: DPL, 0x83: DPH, 0xD3: CY}.get(d[i + off])

    def reg(nr):
        return REGS[nr & 0x07]

    # -- control flow -------------------------------------------------------
    if op in (0x01, 0x02, 0x11, 0x12, 0x22, 0x32):
        return {}
    if op == 0x73:
        return {}                                     # jmp @a+dptr, computed
    if op in (0x40, 0x50, 0x60, 0x70, 0x80, 0x20, 0x30, 0xB4, 0xB5, 0xD5) \
            or 0xB6 <= op <= 0xBF or 0xD8 <= op <= 0xDF:
        # `jbc` (0x10) clears the bit it tests, so it writes it, and `cjne`
        # and `djnz` set carry -- which is what releases a carried `CY`
        # condition rather than pruning the path. **`jc` and `jnc` are not in
        # that list**: they branch *on* carry and leave it alone, and
        # modelling them as writers released every condition at the branch
        # that created it, which is the whole mechanism.
        out = {}
        if op == 0x10:
            b = bit(1)
            if b:
                out[b] = unres
        if 0xB4 <= op <= 0xBF or 0xD5 <= op <= 0xDF:
            out[CY] = unres
        return out
    if op == 0x90:                                    # mov DPTR,#imm16
        val = (d[i + 1] << 8) | d[i + 2]
        return {DPH: (CONST, val >> 8), DPL: (CONST, val & 0xFF)}
    if op == 0xA3:                                    # inc dptr
        return {DPH: unres, DPL: unres}
    if op == 0xE0:                                    # movx A,@DPTR
        return {A: (XDATA, None)}
    if op in (0xE2, 0xE3, 0x93):                      # movx A,@Ri ; movc
        return {A: unres}
    if op == 0x74:                                    # mov A,#imm
        return {A: (CONST, d[i + 1])}
    if op == 0xE4:                                    # clr A
        return {A: (CONST, 0)}
    if 0x78 <= op <= 0x7F:                            # mov Rn,#imm
        return {reg(op - 0x78): (CONST, d[i + 1])}
    if 0xE8 <= op <= 0xEF:                            # mov A,Rn
        return {A: (FROM, reg(op - 0xE8))}
    if 0xF8 <= op <= 0xFF:                            # mov Rn,A
        return {reg(op - 0xF8): (FROM, A)}
    if 0xA8 <= op <= 0xAF:                            # mov Rn,direct
        src = direct(1)
        return {reg(op - 0xA8): (FROM, src)} if src else {}
    if 0x88 <= op <= 0x8F:                            # mov direct,Rn
        dst = direct(1)
        return {dst: (FROM, reg(op - 0x88))} if dst else {}
    if op == 0xE5:                                    # mov A,direct
        src = direct(1)
        return {A: (FROM, src)} if src else {}
    if op == 0xF5:                                    # mov direct,A
        dst = direct(1)
        return {dst: (FROM, A)} if dst else {}
    if op == 0x75:                                    # mov direct,#imm
        dst = direct(1)
        return {dst: (CONST, d[i + 2])} if dst else {}
    if op == 0x85:                                    # mov direct,direct
        # The one form whose destination is the *third* byte, the reason
        # is_dptr_rebuild()'s own, and the same trap.
        dst, src = direct(2), direct(1)
        return {dst: (FROM, src)} if dst and src else {}
    if op == 0xC2:                                    # clr direct
        dst = direct(1)
        return {dst: (CONST, 0)} if dst else {}
    if op == 0xC3:                                    # clr C
        return {CY: (CONST, 0)}
    if op == 0xD3:                                    # setb C
        return {CY: (CONST, 1)}
    if op == 0xD2:                                    # setb bit
        b = bit(1)
        return {b: (CONST, 1)} if b else {}
    if op == 0xC1:                                    # clr bit
        b = bit(1)
        return {b: (CONST, 0)} if b else {}
    if op in (0xB3, 0xB2):                            # cpl C ; cpl bit
        b = bit(1) if op == 0xB2 else CY
        return {b: unres} if b else {}
    if op in (0x05, 0x15, 0xD0, 0x42, 0x43, 0x52, 0x53, 0x62, 0x63):
        # inc/dec/pop direct, and the orl/anl/xrl direct half of each group.
        dst = direct(1)
        return {dst: unres} if dst else {}
    if op in (0x04, 0x14, 0x03, 0x13, 0x23, 0x33, 0xC4, 0xE6, 0xE7,
              0xD6, 0xD7, 0xD4, 0x84, 0xA4):
        return {A: unres}
    if op == 0xC5:                                    # xch A,direct
        out = {A: unres}
        dst = direct(1)
        if dst:
            out[dst] = unres
        return out
    if 0xC8 <= op <= 0xCF:                            # xch A,Rn
        return {A: unres, reg(op - 0xC8): unres}
    if op == 0x92:                                    # mov bit,C
        out = {CY: unres}
        b = bit(1)
        if b:
            out[b] = (FROM, CY)
        return out
    if op in (0xA0, 0xA1, 0xB0):                      # orl/anl C,/bit
        return {CY: unres}
    if op in (0x24, 0x25, 0x26, 0x27, 0x34, 0x35, 0x36, 0x37, 0x94, 0x95,
              0x96, 0x97) or 0x28 <= op <= 0x2F or 0x38 <= op <= 0x3F \
            or 0x98 <= op <= 0x9F:
        return {A: unres, CY: unres}
    if 0x08 <= op <= 0x0F or 0x18 <= op <= 0x1F or 0xD8 <= op <= 0xDF:
        return {reg(op): unres}
    if 0x44 <= op <= 0x4F or 0x54 <= op <= 0x5F or 0x64 <= op <= 0x6F:
        return {A: unres}
    if op in (0x00, 0x76, 0x77, 0x86, 0x87, 0xA2, 0xA6, 0xA7, 0xC0, 0xF0,
              0xF2, 0xF3, 0xF6, 0xF7):
        return {}                                     # writes nothing tracked
    return None


HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_CSV = os.path.join(HERE, os.pardir, "decompiled", "index.csv")
_ENTRY_CACHE = {}


def entry_addresses(region, path=INDEX_CSV):
    """File offsets of the function entries `ec/decompiled/index.csv` records
    for `region`, cached per (region, path) so a caller driving several
    addresses through one region reads the table once.

    The `program` column is `trace_xdata_refs.REGIONS`' own vocabulary, so
    the two agree by construction rather than by a mapping kept here, and the
    `addr` column is a **runtime** address -- which is not the same as a file
    offset for either bank, since a bank's runtime base is `0x8000` and its
    file base is `0x08000`/`0x10000`. The conversion is the one
    `trace_xdata_refs.offset_for_runtime()` performs, done here over the same
    `REGIONS` table so the two cannot drift. An `addr` the file does not hold
    is skipped rather than clamped.
    """
    key = (region, path)
    if key not in _ENTRY_CACHE:
        lo, hi, base = next((lo, hi, base) for n, lo, hi, base, _ in REGIONS
                            if n == region and base is not None)
        out = set()
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["program"] != region:
                    continue
                off = lo + (int(row["addr"], 16) - base)
                if lo <= off < hi:
                    out.add(off)
        _ENTRY_CACHE[key] = out
    return _ENTRY_CACHE[key]


class Walk:
    """One backward walk over one region, and what it recorded about it."""

    def __init__(self, d, lo, hi, base, region, max_steps):
        self.d, self.lo, self.hi, self.base = d, lo, hi, base
        self.region, self.max_steps = region, max_steps
        # (use site, symbol) -> [(defining site, kind, note)], one entry per
        # distinct definition the walk found. Keyed by the site rather than
        # by the symbol alone because a def-use chain is anchored at a
        # program point: the DPH a `movx` reads is not the DPH the target
        # leaves behind, and a map keyed only by symbol would answer the
        # wrong one of those two questions.
        self.defs = collections.defaultdict(list)
        # Two ways a wanted symbol can come back with fewer definitions than
        # there were paths, kept apart because they are different claims and
        # one of them is a fact about the firmware. `ran_out`: a branch reached
        # the end of the code with the symbol still wanted, so nothing wrote
        # it there. `cut`: a branch this tool could not follow, which is a
        # limit on the method. Collapsing them is how a partial answer comes
        # to read as a total one.
        self.ran_out = set()
        self.cut = set()
        self.starts = set()
        self.pruned = []               # (site, text)
        self.unfollowed = []           # (site, text)
        self.unwritten = set()         # (origin, symbol) not written on a path
        self.paths = 0

    # -- addresses ----------------------------------------------------------
    def addr(self, i):
        return self.base + (i - self.lo)

    def off(self, runtime):
        """File offset of a runtime address, or None when it leaves the
        region -- a target in the 8051's common area is the same runtime
        address in every bank, and this tool decodes one of them."""
        if runtime is None or not self.base <= runtime < self.base + (self.hi - self.lo):
            return None
        return self.lo + (runtime - self.base)

    def target(self, i):
        """Absolute runtime target of the branch or call at `d[i]`, or None."""
        op = self.d[i]
        if op in (0x02, 0x12):
            return (self.d[i + 1] << 8) | self.d[i + 2]
        if op in REL_OPCODES:
            return relative_target(op, self.d[i + OPCODE_LEN[op] - 1], self.addr(i))
        if op not in NOT_PAGED and op & 0x1F in (0x01, 0x11):
            return paged_target(op, self.d[i + 1], self.addr(i))
        return None

    # -- the graph ----------------------------------------------------------
    def _decode_flow(self, entry):
        """Instruction starts reachable from `entry`, decoding along control
        flow rather than in a straight line.

        The straight line is not enough, and `bank1:0xB6DE` is the worked
        example: the `sjmp 0xB70C` at `0xB6F4` steps a linear decode over
        `0xB6F6`-`0xB70B`, so every instruction of the comparison chain
        behind it -- and two of that routine's three `ret`s, the one the whole
        answer rests on -- is outside the map. The committed `.asm` listings
        have the same gap, for the same reason, which is why this is a
        property of linear decoding rather than of any one tool.

        Targets are decoded too, so a routine entered only by a tail-jump is
        in the map; which routine a byte belongs to is settled by the entry
        interval in `rets_in()`, not by which decode reached it first.
        """
        seen, todo = set(), [entry]
        while todo:
            i = todo.pop()
            while i is not None and i not in seen and self.lo <= i < self.hi:
                n = OPCODE_LEN[self.d[i]]
                if i + n > self.hi:
                    break
                seen.add(i)
                op = self.d[i]
                step = n + inline_arg_len(self.d, i)
                tgt = self.off(self.target(i))
                if tgt is not None and tgt not in seen:
                    todo.append(tgt)
                if op in RET_OPCODES or op == 0x73 or op in (0x02, 0x80) \
                        or (op & 0x1F in (0x01, 0x11) and op not in NOT_PAGED):
                    break                              # no fall-through
                i += step
        return seen

    def seed(self, entries=None):
        """Build the instruction map and the predecessor relation.

        The seeds are the function entries `ec/decompiled/index.csv` records
        for this region, plus the region's base. **The table supplies framing
        and the image supplies every value**: this tool has no opinion about
        where a function starts, and taking the repository's own answer is
        what puts its instruction map in step with the `.asm` listings a
        reader checks the report against. A whole-region linear decode was the
        first thing tried here and it does not work -- one mis-framing
        anywhere shifts every address behind it, and the call-target set that
        seeds the walk comes out wrong, which is the failure
        `find_indirect_xdata.py` documents for the same method.

        The table's `size` column is *not* used, and cannot be: `bank1:0xB6DE`
        is recorded as 52 bytes while the comparison chain behind its `sjmp`
        runs to `0xB727`, 74 bytes in. `_decode_flow()` establishes each
        entry's real extent by following control flow, which is why the two
        of that routine's three `ret`s are in the map at all.

        A routine the table does not list is not walked. That is a limit on
        what this tool can report, not a claim about the firmware.

        `entries` overrides the table, and exists for the suite: a hand-built
        fixture has no `index.csv` row and a test that could only reach this
        through the real table would be testing the table.
        """
        self.entries = sorted(
            {self.lo, *entries} if entries is not None
            else set(entry_addresses(self.region)) | {self.lo})
        for e in self.entries:
            self.starts |= self._decode_flow(e)
        self.pred = collections.defaultdict(set)
        for i in sorted(self.starts):
            op = self.d[i]
            if op in RET_OPCODES or op == 0x73:
                continue
            step = OPCODE_LEN[op] + inline_arg_len(self.d, i)
            edges = []
            tgt = self.off(self.target(i))
            if tgt is not None and op not in CALL_OPCODES \
                    and not (op & 0x1F == 0x11 and op not in NOT_PAGED):
                edges.append(tgt)
                if op not in (0x02, 0x80):            # ljmp/sjmp have no fall-through
                    edges.append(i + step)
            else:
                edges.append(i + step)
            for j in edges:
                if j in self.starts:
                    self.pred[j].add(i)
        return self

    def rets_in(self, entry):
        """The `ret`s belonging to `entry`, which is what a backward walk past
        a call has to choose between.

        **By the entry interval, not by who reached the byte.** An earlier
        entry's `lcall` walks straight through this one's body, so "first
        decode to touch it" makes `write_1c00_ff_and_0680_04` the owner of
        everything `0xDE3C` and `0xB6DE` contain -- which is how this was
        first written, and it lost two of `0xB6DE`'s three returns. The
        interval from this entry to the next is the call-target framing the
        rest of the repository uses, and it is a property of the table rather
        than of the order the decodes happened to run in.

        Scanned by byte across the whole interval and then **narrowed to the
        decoded map**, which is two decisions. The scan finds the operand
        bytes that happen to equal `0x22`/`0x32` as well as the real
        returns, and offering one of those as a predecessor is how this first
        reported a `ret` at `bank1:0xB6F3` that is the displacement of the
        `jc` at `0xB6F2`. Narrowing costs the case the scan was for -- a
        return the flow decode never reached -- so that one is recorded as
        unfollowable here rather than dropped, which is the whole of what
        `not followed` is for.
        """
        nxt = bisect.bisect_right(self.entries, entry)
        end = self.entries[nxt] if nxt < len(self.entries) else self.hi
        out = []
        for i in range(entry, end):
            if self.d[i] not in RET_OPCODES or inline_arg_len(self.d, i):
                continue
            if i in self.starts:
                out.append(i)
            else:
                self.unfollowed.append((i, UNREACHED_RET % self.addr(i)))
        return out

    # -- the walk -----------------------------------------------------------
    def run(self, at, wanted):
        # Each wanted symbol is a `(program point, symbol)` pair, and one work
        # item can hold several: `DPH` is still wanted where the store is
        # while `R1` is wanted at the `mov DPL,R1` that made it. The point
        # travels per symbol, not per item, and it is the same order
        # `self.defs` and `self.ran_out` are keyed in.
        work = [(at, frozenset((at, sym) for sym in wanted), ())]
        seen = set()
        while work:
            site, want, cond = work.pop()
            key = (site, want, cond)
            if key in seen:
                continue
            seen.add(key)
            if len(seen) > self.max_steps:
                self.unfollowed.append((site, BUDGET % self.max_steps))
                self.cut |= want
                break
            self.paths += 1
            if site not in self.starts:
                self.unfollowed.append((site, NO_INSN % self.addr(site)))
                self.cut |= want
                continue
            got = writers(self.d, site)
            if got is None:
                if want:
                    self.unfollowed.append((site, UNMODELLED % self.d[site]))
                    self.cut |= want
                continue
            still, carried = self._apply(want, got, cond, site)
            if not still:
                continue
            preds = self.predecessors(site, carried)
            if not preds:
                # The branch ran out of predecessors with these symbols still
                # wanted, which is the one way a wanted symbol comes back with
                # no definition and no excuse: a fact about the code, not a
                # limit on this tool. `cut` is excluded so a path that *was*
                # reported stays a different claim in _render().
                self.ran_out |= {k for k in still if k not in self.cut}
                continue
            work.extend((p, frozenset(still), c) for p, c in preds)
        self.unwritten = self.ran_out - self.cut
        return self

    def _apply(self, want, got, cond, site):
        """Record the definitions `got` supplies for `want`, follow their
        sources, and drop or contradict the path's own conditions.

        A condition on a symbol this instruction defines is checked rather
        than carried: a constant that disagrees prunes the path, and a value
        this tool cannot carry releases the condition, because from that
        point the definition is the condition's own answer.

        Records land under `origin` -- the program point whose value is being
        resolved -- and not under `site`. That is the whole of a def-use
        chain: `DPH` at the store is not the `DPH` the `movx` reads, and a
        map keyed by whichever site happened to define a symbol would answer
        the second question when asked the first.
        """
        still, carried = set(), []
        for sym, value in cond:
            if sym not in got:
                carried.append((sym, value))
                continue
            kind, note = got[sym]
            if kind == CONST and note != value:
                self.pruned.append(
                    (site, f"0x{self.addr(site):04X} sets {sym}=0x{note:02x}, "
                           f"but this path carries {sym}={value}"))
                return set(), ()
        for origin, sym in want:
            if sym not in got:
                still.add((origin, sym))
                continue
            record = (site,) + got[sym]
            if record not in self.defs[(origin, sym)]:
                self.defs[(origin, sym)].append(record)
            # The sources a definition reads are wanted *at that definition*:
            # a `mov DPL,R1` copies the R1 as it stood at its own address, not
            # the R1 the routine ends with.
            kind, note = got[sym]
            if kind == FROM and note:
                still.add((site, note))
            elif kind == XDATA:
                still |= {(site, DPH), (site, DPL)}
        return still, tuple(sorted(carried))

    def predecessors(self, site, cond):
        """Every way control can arrive at `site`, each with the condition
        that arrival imposes.

        A call is the one substitution. Its fall-through is reached with
        whatever the callee left, and the 8051 saves no registers across one,
        so the call's own predecessors are *not* predecessors of the
        fall-through -- the callee's returns are, and there is no sound way
        to skip them. A callee with no `ret` in its extent is reported and
        the path ends, rather than falling back to the unsound edge.
        """
        out = []
        for p in sorted(self.pred.get(site, ())):
            op = self.d[p]
            branch = self.target(p)
            if branch is not None and self.off(branch) is None:
                # The edge that got us here is the fall-through -- an
                # unresolvable target contributes no edge at all -- so the
                # path continues, and the half of the branch that leaves the
                # region is reported rather than dropped.
                self.unfollowed.append((p, OUT_OF_REGION % branch))
            taken = self.off(branch)
            here = cond
            if op in (0x40, 0x50):
                here = _with(cond, CY, 1 if op == 0x40 else 0) if site == taken \
                    else _with(cond, CY, 0 if op == 0x40 else 1)
                if here is None:
                    self.pruned.append(
                        (p, f"0x{self.addr(p):04X} {mnemonic(self.d, p, self.addr(p))}"
                            f" branches on the other carry value"))
                    continue
            if op in CALL_OPCODES or (op & 0x1F == 0x11 and op not in NOT_PAGED):
                j = self.off(self.target(p))
                rets = [] if j is None else self.rets_in(j)
                if not rets:
                    self.unfollowed.append(
                        (p, NO_RETURN % (self.addr(j) if j is not None else 0)))
                    continue
                out.extend((r, here) for r in rets)
                continue
            out.append((p, here))
        return out


def _with(cond, sym, value):
    """`cond` plus `sym=value`, or None when it already says otherwise."""
    for s, v in cond:
        if s == sym and v != value:
            return None
    return tuple(sorted(set(cond) | {(sym, value)}))


def _render(walk, site, sym, depth=0):
    """What `sym` holds at `site`, in words, over every definition found.

    `from` and an `xdata` over an unresolved pointer both recurse, and the
    recursion moves *back to the defining site* rather than staying put: the
    R1 a `mov DPL,R1` copies is the R1 as it stood at that instruction, not
    the R1 the routine ends with. A symbol defined at more than one site
    renders as all of them, because "the last definition on each path" is a
    question about paths and collapsing it to the first one found would be
    the answer the issue was warned against picking.
    """
    found = walk.defs.get((site, sym)) or []
    if depth > 8:
        return "..."
    out = []
    for dsite, kind, note in found:
        if kind == CONST:
            out.append(f"0x{note:02X}")
        elif kind == XDATA:
            out.append(_render_xdata(walk, dsite))
        elif kind == FROM and note:
            out.append(_render(walk, dsite, note, depth + 1))
        else:
            out.append(str(note))
    if (site, sym) in walk.cut:
        # The path that would have carried the answer was cut, so the honest
        # statement is the limit and not the absence -- "nothing wrote it here"
        # would be a claim about code the tool never looked at.
        if not out:
            return CUT_PATH
        out.append(CUT_PATH)
    elif not out:
        out.append(UNWRITTEN_NONE)
    elif (site, sym) in walk.unwritten:
        # Defined on the paths that found a definition and *not* on one that
        # did not. Printing the value alone would read as a total answer.
        out.append(UNWRITTEN_SOME)
    return " or ".join(dict.fromkeys(out))


def _render_xdata(walk, site):
    """The address an `xdata` read at `site` reaches, when DPH and DPL are
    both constants there. Anything else says so rather than guessing, which
    is the whole point: a pointer the walk could not close is a limit on the
    method and not an address."""
    hi = [r for r in walk.defs.get((site, DPH), ()) if r[1] == CONST]
    lo = [r for r in walk.defs.get((site, DPL), ()) if r[1] == CONST]
    if len(hi) == 1 and len(lo) == 1:
        return f"XDATA 0x{hi[0][2] << 8 | lo[0][2]:04X}"
    return "XDATA at a pointer this walk did not resolve to one constant"


def _chain(walk, site, sym, depth=0):
    """`sym <- ...` down to the definition that carries a value, for the
    report's second line. Same recursion as _render(), printed as a path."""
    found = walk.defs.get((site, sym))
    if depth > 8 or not found:
        return f"{sym} (no definition found)"
    dsite, kind, note = found[0]
    if kind == CONST or kind == XDATA or kind == UNKNOWN or not note:
        return f"{sym} @ 0x{walk.addr(dsite):04X}"
    return f"{sym} <- " + _chain(walk, dsite, note, depth + 1)


def parse_target(raw, pd):
    """-> (region, file offset, runtime address) for a `--at` argument.

    A bare number is a **file offset**, which is what `disasm8051.py --at`
    takes and what a reader who has just been reading a listing has; a
    `region:0xaddr` pair is a runtime address, and says which bank it is in
    rather than leaving the file offset to imply it.
    """
    if ":" in raw:
        name, _, value = raw.partition(":")
        region = name
        runtime = int(value, 0)
        for n, lo, hi, base, _ in REGIONS:
            if n == region and base is not None and base <= runtime < base + (hi - lo):
                return region, lo + (runtime - base), runtime
        raise SystemExit(f"{raw}: {region} does not hold 0x{runtime:04X}")
    off = int(raw, 0)
    region = region_of(off, pd)[0]
    for n, lo, hi, base, _ in REGIONS:
        if n == region and base is not None and lo <= off < hi:
            return region, off, base + (off - lo)
    raise SystemExit(f"{raw}: file offset 0x{off:X} is in no decoded region")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="last definition of DPH/DPL reaching an address")
    ap.add_argument("firmware")
    ap.add_argument("--at", action="append", required=True, metavar="ADDR",
                    help="file offset, or REGION:0xRUNTIME. Repeatable.")
    ap.add_argument("--csv", action="store_true",
                    help="one row per definition instead of the prose report")
    ap.add_argument("--max-steps", type=int, default=20000,
                    help="ceiling on backward steps per address (default 20000)")
    args = ap.parse_args(argv)

    with open(args.firmware, "rb") as handle:
        d = handle.read()
    pd = d[PD_MARKER[0]:PD_MARKER[0] + len(PD_MARKER[1])] == PD_MARKER[1]

    walks = []
    for raw in args.at:
        region, off, runtime = parse_target(raw, pd)
        lo, hi, base = next((lo, hi, base) for n, lo, hi, base, _ in REGIONS
                            if n == region and base is not None)
        walk = Walk(d, lo, hi, base, region, args.max_steps).seed().run(
            off, (DPH, DPL))
        walks.append((region, runtime, walk))

    if args.csv:
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(("region", "at", "symbol", "value",
                         "defined_at", "defined_by"))
        for region, runtime, walk in walks:
            for sym in (DPH, DPL):
                for dsite, kind, _ in walk.defs.get((walk.off(runtime), sym), ()):
                    writer.writerow(
                        (region, f"0x{runtime:04X}", sym,
                         _render(walk, walk.off(runtime), sym),
                         f"0x{walk.addr(dsite):04X}",
                         mnemonic(walk.d, dsite, walk.addr(dsite))))
        sys.stdout.write(out.getvalue())
        return 0

    for region, runtime, walk in walks:
        at = walk.off(runtime)
        print(f"{region}:0x{runtime:04X}   {mnemonic(walk.d, at, runtime)}")
        for sym in (DPH, DPL):
            print(f"  {sym:<4} = {_render(walk, at, sym)}")
            print(f"        {_chain(walk, at, sym)}")
        print(f"\n  paths walked {walk.paths}, pruned {len(walk.pruned)}, "
              f"not followed {len(walk.unfollowed)}")
        for label, items in ((PRUNED, walk.pruned), (UNFOLLOWED, walk.unfollowed)):
            for site, text in sorted(set(items)):
                where = f"{region}:0x{walk.addr(site):04X}" if site is not None else "-"
                print(f"  {label:<13} {where}  {text}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
