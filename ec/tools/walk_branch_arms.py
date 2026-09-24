#!/usr/bin/env python3
"""Walk both arms of every conditional branch on a `MOV DPTR,#addr` site, and
say what each arm reaches.

trace_xdata_refs.py answers "what happens in an 8-instruction window around
this site", and it stops at the first control-flow instruction -- which, for a
site that branches on a bit of the byte it just loaded, *is* the branch. So the
two arms on either side of that branch have never been looked at, and ec/
annotations/manual-fan-ctrl-0751.md 4/5 conclude from the window alone that no
reference site copies a default into a PL register or loads a fan table. That
is a statement about the window. This walks the arms.

The descent is bounded and deliberately literal:

  * a conditional branch is followed on **both** sides, so the result is a
    "reachable from here" set rather than a guess about the hot path;
  * `ret`/`reti` ends an arm, `ljmp`/`ajmp` hands the arm to another routine
    (recorded as a callee, the arm ends), and `lcall`/`acall` is recorded and
    the walk continues past it;
  * an address the arm has already decoded is a loop, not more code -- and
    because the set covers every address rather than every block start, a
    branch back into the middle of a block is the same fact, not a second
    walk of the same `movx`;
  * a budget on nested control transfers and on decoded instructions stops
    anything that would otherwise not terminate, and every arm reports
    `complete` or the cuts that fired, so a negative is never confused with a
    walk that gave up.

Two things it refuses to guess, because guessing them is how a window scan
produces a confident wrong answer:

  * **DPTR is tracked, not assumed.** A `movx` is attributed to whatever
    `mov dptr,#imm16` last set, and to nothing before that. Any store to DPL
    (`0x82`) or DPH (`0x83`) -- from the accumulator or from a register --
    builds the pointer at run time, so after one the pointer is unknown and
    every later `movx` is counted `unattributed` rather than charged to the
    address that happened to be loaded earlier. That shape is not
    hypothetical: manual-fan-ctrl-0751.md 6 is eight sites that reach the fan
    table only because DPTR is built out of a sensor byte, and the `0x9432`
    arms below rebuild DPTR from `r2`/`r1` after loading a CODE pointer.
  * **A CODE access is not an XDATA access.** A `movc a,@a+dptr` or
    `jmp @a+dptr` is recorded against `code_pointers` whatever DPTR holds,
    because it reads CODE by definition; separately, an immediate at or above
    `0x8000` cannot be XDATA in the main EC's map at all, since the common
    area ends at `0x7FFF` and the bank windows start at `0x8000`, so it is
    recorded in `code_immediates`. Both are the blind spot
    trace_xdata_refs.classify() names, and both are labelled rather than
    folded into the XDATA column.

A branch target is derived from the decoded stream, never by adding a
displacement to the site address. The two differ: for the 16 bank0 sites the
branch sits at `site + 7` and the target is `site + 7 + 3 + rel`, but
`0x9432` is `90 07 51 e0 54 80 70 05` -- an `anl a,#0x80` puts the `jnz` at
`site + 6`, so the same arithmetic lands on `0x943E`, one byte inside the
`mov dptr` that follows. Every target in --self-test is hand-transcribed from
`r2 -a 8051` for that reason.

Nothing here measures the byte. A `write` verdict is an instruction storing to
an address, not evidence the EC acts on the value, and an empty arm is "no arm
found by this method reaches X", never "the EC does not".

`--callee-depth 1` follows one level into each `lcall`/`acall`/`ljmp`/`ajmp`
target, and reports `unresolved` for one that does not settle at that level
rather than dropping it. A callee starts with an unknown DPTR, because it
inherits the caller's and that value is not carried here.

Usage:
    python3 walk_branch_arms.py ../firmware/GMxMGxx_11.800 0x0751
    python3 walk_branch_arms.py ../firmware/GMxMGxx_11.800 0x0751 --callee-depth 1
    python3 walk_branch_arms.py ../firmware/GMxMGxx_11.800 0x0751 --callee-depth 1 --csv > arms.csv
    python3 walk_branch_arms.py --self-test ../firmware/GMxMGxx_11.800
"""
import argparse
import csv
import sys

from disasm8051 import (OPCODE_LEN, REL_OPCODES, mnemonic, paged_target,
                        relative_target)
from trace_xdata_refs import (MOV_DPTR, PD_MARKER, offset_for_runtime,
                              region_of, runtime_addr, sites_for)

# The branches that split a site into two arms. The bit tests (0x20/0x30/0x10)
# and the accumulator tests (0x40/0x50/0x60/0x70) are two shapes of the same
# question -- "is the bit I just masked set" -- and this image uses both: the
# bank0 sites are `jnb acc.N`, the bank1 site masks first and then `jnz`.
ACC_TESTS = (0x40, 0x50, 0x60, 0x70)
BIT_TESTS = (0x10, 0x20, 0x30)
CONDITIONAL = BIT_TESTS + ACC_TESTS

# Every PC-relative branch except `sjmp`, taken from disasm8051's own table
# rather than a range written here. Writing `0xB4 <= op <= 0xDF` looks
# equivalent and is not: the 8051 puts `clr c` (0xC3), `setb c` (0xD3) and the
# `clr`/`setb`/`cpl bit` forms (0xB2/0xC2/0xD2) in the middle of that range, and
# treating them as branches resolves a "target" out of the following byte. The
# result is a walk that decodes the rest of the routine as garbage -- which is
# exactly the shape of the mis-framing manual-fan-ctrl-0751.md 7 spot-checks
# exist to catch, so the table is shared rather than restated.
REL_BRANCHES = frozenset(REL_OPCODES) - {0x80}

# The three `anl/orl/xrl a,#imm` that set up an `acc` test. Recognising them is
# what lets the bank1 site report `anl a,#0x80 ; jnz` as the test it is,
# instead of a bare `jnz` whose operand the reader has to find for themselves.
MASK_OPS = {0x44: "orl", 0x54: "anl", 0x64: "xrl"}

# How far past a site to look for its branch. trace_xdata_refs.walk() stops at
# the first control-flow instruction; this only needs to get past the
# `mov dptr` / `movx a,@dptr` pair and any one masking instruction, and the
# budget stops a site with no branch from being walked into whatever follows.
SCAN_INSNS = 6

# Above this an immediate cannot be XDATA in the main EC's own address map: the
# common area ends at 0x7FFF and the bank windows start at 0x8000. See the
# module docstring for why the distinction is load-bearing.
CODE_FLOOR = 0x8000

# DPTR is DPL at 0x82 and DPH at 0x83. A direct write to either builds the
# pointer at run time, which is exactly the fan-table shape manual-fan-ctrl-
# 0751.md 6 documents; after one, the pointer is unknown.
DPTR_REGS = (0x82, 0x83)

# Stop reasons, as they read in a table cell. Kept as data rather than
# formatted at each site so a reader can grep for a specific one.
END_RET = "ret"
END_RETI = "reti"
END_TAIL = "tail jump to a callee"
END_INDIRECT = "indirect jump -- target not resolvable from the bytes"
END_DEPTH = "depth limit"
END_BUDGET = "instruction budget"
END_LOOP = "loop"

# Stop reasons that mean the walk gave up rather than finished. A `loop` is not
# one of them: an arm that cycles has been fully explored, it just comes back
# round, and saying `cut` there would understate what was read.
CUTS = (END_DEPTH, END_BUDGET, END_INDIRECT)


class Arm:
    """One side of one branch: where it starts, what it reaches, how it ends."""

    def __init__(self, kind, start, region):
        self.kind = kind                 # "taken" / "fall-through"
        self.start = start
        self.region = region
        self.xdata = {}                   # xdata addr -> {"r"} / {"w"} / both
        self.code_pointers = []           # DPTR values a movc/jmp @a+dptr used
        self.code_immediates = []         # DPTR immediates >= CODE_FLOOR
        self.callees = []                 # lcall/acall/ljmp/ajmp targets
        self.unattributed = 0             # movx with an unknown DPTR
        self.movx_ri = 0                  # movx @Ri -- indirect, never an address
        self.insns = 0
        self.blocks = []                  # (block start, [(runtime, text)])
        self.ends = []

    def end(self, why):
        if why not in self.ends:
            self.ends.append(why)

    def touch(self, addr, read=False, write=False):
        cur = self.xdata.setdefault(addr, set())
        if read:
            cur.add("r")
        if write:
            cur.add("w")

    @property
    def accesses(self):
        """`0x07C6 read ; 0x086B write` -- the column, sorted so two runs of
        the tool cannot disagree on row order. Membership, not an equality
        test: an arm that reads the same byte on both sides of an inner branch
        reads it, and a two-letter comparison would call that a write."""
        out = []
        for addr in sorted(self.xdata):
            d = self.xdata[addr]
            word = "r+w" if "w" in d and "r" in d else "read" if "r" in d else "write"
            out.append(f"0x{addr:04X} {word}")
        return " ; ".join(out)

    @property
    def window(self):
        """The decoded blocks, `|` between them. One flat list would read as
        a straight line through code that is not straight -- the whole point
        of recording the blocks is that a reader can see where the walk
        stopped following and started following again."""
        return " | ".join(" ; ".join(f"0x{pc:04X} {t}" for pc, t in insns)
                          for _, insns in self.blocks)

    def xdata_words(self):
        return set(self.xdata)

    def reads(self):
        return {a for a, d in self.xdata.items() if "r" in d}

    def writes(self):
        return {a for a, d in self.xdata.items() if "w" in d}


def test_site(d: bytes, region: str, off: int, rt: int, target: int, pd_verified: bool):
    """The conditional branch that splits this site into two arms, or None.

    The scan is bounded and stops at the first control-flow instruction, so a
    site with no branch after it gets None rather than a branch borrowed from
    the next routine. The branch has to be testing the accumulator the site
    just loaded -- otherwise it is somebody else's branch and the two arms
    would not be the mode-bit arms this tool is about."""
    dptr = None
    loaded_from = None       # xdata address `a` was last read from
    prev = None              # (opcode, immediate) of the instruction before
    pc = rt
    for _ in range(SCAN_INSNS):
        if off < 0 or off >= len(d):
            return None
        op = d[off]
        n = OPCODE_LEN[op]
        if op == MOV_DPTR:
            dptr = (d[off + 1] << 8) | d[off + 2]
            loaded_from = None
        elif op == 0xE0 and dptr is not None:
            loaded_from = dptr
        elif op in CONDITIONAL:
            if loaded_from != target:
                return None
            taken = relative_target(op, d[off + n - 1], pc)
            fall = (pc + n) & 0xFFFF
            desc = mnemonic(d, off, pc)
            if op in BIT_TESTS:
                bit = d[off + 1]
                # `jnb acc.6` encodes as `30 E6`, not `30 06`: the operand byte
                # is the bit-addressable *byte* acc (0xE0) offset by the bit
                # index, so the mode bit is 0xE0 + N and acc.7 is 0xE7.
                if not 0xE0 <= bit <= 0xE7:
                    return None      # a bit of some SFR, not of the mode byte
                bitn = bit & 0x07
                mode = {7: "USER", 6: "FAN BOOST", 5: "HIGH",
                        4: "TURBO"}.get(bitn, "?")
                test = f"{desc} -- {mode} (bit {bitn})"
            else:
                # A masked accumulator test: the mask is the previous
                # instruction, and the bit it names is the mode bit.
                if not prev or prev[0] not in MASK_OPS:
                    return None
                mask = prev[1]
                test = (f"{MASK_OPS[prev[0]]} a,#0x{mask:02x} ; {desc} -- "
                        f"USER (bit 7)" if mask == 0x80 else
                        f"{MASK_OPS[prev[0]]} a,#0x{mask:02x} ; {desc}")
            return {"branch": pc, "raw": d[off:off + n], "mnemonic": desc,
                    "test": test, "taken": taken, "fall": fall,
                    "dptr": dptr, "text": f"0x{pc:04X} {d[off:off + n].hex()} {desc}"}
        elif op in (0x22, 0x32, 0x02, 0x12) or op & 0x1F in (0x01, 0x11):
            return None              # ends before any branch
        if op in MASK_OPS:
            prev = (op, d[off + 1])
        else:
            prev = None
        off += n
        pc += n
    return None


def _dptr_write(op: int, imm, imm2) -> bool:
    """Does this instruction store into DPL (0x82) or DPH (0x83)?

    Four forms name the `direct` byte in the second position -- `mov direct,#imm`
    (0x75), `mov direct,Rn` (0x88-0x8F), `mov direct,@Ri` (0xA8-0xAF) and
    `mov direct,A` (0xF5) -- and `mov direct,direct` (0x85) in the third.
    Catching only `mov 0x82,A` is how a CODE pointer ends up read as an XDATA
    register: at 0x9444 the bank1 arms hand 0x93B6/0x93E6 to r2/r1 and rebuild
    DPTR from them with `mov dph,r2 ; mov dpl,r1`, so the register forms are
    exactly the ones this arm needs.

    Whatever the source register, DPTR becomes unknown rather than known. Two
    immediate `mov` forms could in principle be composed back into an address,
    and tracking that is more machinery than the error it would prevent is
    worth: "unattributed" is the safe direction, and a wrong address is not."""
    if op == 0x75 or 0x88 <= op <= 0x8F or 0xA8 <= op <= 0xAF or op == 0xF5:
        return imm in DPTR_REGS
    if op == 0x85:
        return imm2 in DPTR_REGS
    return False


def descend(d: bytes, region: str, start: int, dptr, max_depth: int, max_insns: int,
            pd_verified: bool) -> Arm:
    """Everything reachable from `start` in `region`, within the bounds.

    The unit is the *linear block*: decode forward from one address until a
    control-flow instruction, then start again wherever that instruction leads.
    A conditional branch contributes both sides, so the result is a
    "reachable from here" set; the fall-through side is walked before the taken
    side, which is what keeps the emitted listing in address order for the part
    a reader actually reads.

    A `lcall`/`acall` is recorded as a callee and the spine walks past it --
    the code after a call is still the arm's own. A `ljmp`/`ajmp` is a tail
    call: the arm ends there and the callee table is what covers the target,
    the same split `register_ref_table.py --callee-depth 1` makes. `dptr` is
    the pointer the branch left behind, so an arm that reads the mode byte
    again is credited to the mode byte rather than to nothing.

    The bounds are a transfer depth and an instruction budget, and both are
    reported on the row when they bite. Neither is a claim that the walk saw
    everything after the cut."""
    arm = Arm("", start, region)
    budget = max_insns
    # Explicit list rather than recursion: an arm can re-enter itself through a
    # routine, and a RecursionError there would be a crash on this image rather
    # than a reported result.
    pending = [(start, 0, dptr)]
    # Every address decoded, not just every block start: a branch target that
    # lands back inside a block the spine already crossed is the same fact as a
    # loop, and re-walking it would double-count every `movx` in the overlap.
    walked = set()
    while pending:
        pc, depth, dp = pending.pop(0)
        if pc in walked:
            arm.end(f"{END_LOOP} back to 0x{pc:04X}")
            continue
        walked.add(pc)
        block = []
        while True:
            off = offset_for_runtime(pc, region)
            if off is None:
                arm.end(f"0x{pc:04X} is not reachable from region {region}")
                break
            if budget <= 0:
                arm.end(f"{END_BUDGET} at 0x{pc:04X}")
                break
            op = d[off]
            n = OPCODE_LEN[op]
            if off + n > len(d):
                arm.end(f"0x{pc:04X} runs past the end of the image")
                break
            raw = d[off:off + n]
            arm.insns += 1
            budget -= 1
            walked.add(pc)
            block.append((pc, " ".join(mnemonic(d, off, pc).split())))
            # The operand bytes are only there when the instruction has them;
            # a one-byte opcode at the very end of the image has none, and
            # reading it anyway would be an IndexError rather than a verdict.
            imm = d[off + 1] if n > 1 and off + 1 < len(d) else None
            imm2 = d[off + 2] if n > 2 and off + 2 < len(d) else None

            if op == MOV_DPTR:
                dp = (d[off + 1] << 8) | d[off + 2]
                if dp >= CODE_FLOOR:
                    arm.code_immediates.append(dp)
            elif op in (0xE0, 0xF0):
                if dp is None:
                    arm.unattributed += 1
                else:
                    arm.touch(dp, read=op == 0xE0, write=op == 0xF0)
            elif op in (0xE2, 0xE3, 0xF2, 0xF3):
                arm.movx_ri += 1
            elif op in (0x93, 0x73) and dp is not None:
                # movc/jmp through DPTR reads CODE whatever the pointer's
                # value, so this is recorded whatever dp is -- recording it
                # only when dp >= CODE_FLOOR would drop a movc through a
                # low address, and the dropped case is the one that would
                # otherwise read as an XDATA access. trace_xdata_refs.
                # classify() names this as the CODE-pointer blind spot.
                if dp not in arm.code_pointers:
                    arm.code_pointers.append(dp)
            elif op == 0xA3 and dp is not None:
                arm.touch(dp, read=True)   # the walked byte is read too
                dp = None                   # and the next one is not knowable
            elif _dptr_write(op, imm, imm2):
                # DPTR built at run time. Everything after this is unattributed
                # on purpose -- see the module docstring and manual-fan-ctrl-
                # 0751.md 6, which is eight sites this tool must not mis-credit.
                dp = None
                arm.end("DPTR built at run time (a store to DPL/DPH)")

            if op in (0x22, 0x32):            # ret / reti
                arm.end(END_RET if op == 0x22 else END_RETI)
                break
            if op == 0x73:                    # jmp @a+dptr
                arm.end(END_INDIRECT)
                break

            if op in (0x02, 0x12) or op & 0x1F in (0x01, 0x11):
                target = ((raw[1] << 8) | raw[2]) if op in (0x02, 0x12) \
                    else paged_target(op, raw[1], pc)
                arm.callees.append(target)
                if op == 0x12 or op & 0x1F == 0x11:      # lcall / acall
                    pc += n
                    continue
                arm.end(END_TAIL)                        # ljmp / ajmp
                break

            if op in REL_BRANCHES or op == 0x80:
                # Every remaining flow opcode is PC-relative, so
                # relative_target() resolves it from OPCODE_LEN -- which is
                # the whole point of consulting that table rather than a
                # constant: the 2- and 3-byte forms take the displacement from
                # different offsets.
                target = relative_target(op, raw[-1], pc)
                if depth < max_depth:
                    pending.append((target, depth + 1, dp))
                else:
                    arm.end(f"{END_DEPTH} at 0x{target:04X}")
                if op not in REL_BRANCHES:      # sjmp: a transfer, not a split
                    arm.end(END_TAIL)
                    break
                pc = (pc + n) & 0xFFFF
                continue

            pc = (pc + n) & 0xFFFF
        if block:
            arm.blocks.append((block[0][0], block))
    return arm


def arms_for(d: bytes, addr: int, pd_verified: bool, max_depth: int, max_insns: int):
    """[(site offset, region, runtime, test-dict or None, [Arm, ...]), ...]

    A site with no branch after it yields an empty arm list rather than being
    dropped, so the caller can reconcile the site count against the 29 the
    rest of the repo quotes."""
    out = []
    for off in sites_for(d, addr):
        region, _, _, _ = region_of(off, pd_verified)
        rt = runtime_addr(off, pd_verified)
        test = test_site(d, region, off, rt, addr, pd_verified)
        arms = []
        if test is not None:
            for kind, start in (("taken", test["taken"]), ("fall-through", test["fall"])):
                arm = descend(d, region, start, test["dptr"], max_depth, max_insns,
                              pd_verified)
                arm.kind = kind
                arms.append(arm)
        out.append((off, region, rt, test, arms))
    return out


def no_claim(arm) -> str:
    """The wording for an arm that writes nothing. Never "the EC does not" --
    the walk is bounded, and manual-fan-ctrl-0751.md 6 is the worked
    counter-example of what reading a bounded scan's silence as absence costs.

    The list of what is outside the method is the claim, so it says which
    blind spots actually bit on *this* arm rather than a generic disclaimer."""
    if arm.writes():
        return ""
    if not arm.insns:
        return "no arm found by this method decodes to any instruction"
    blind = ["indirect access"]
    if arm.unattributed:
        blind.append("a DPTR built at run time")
    if arm.movx_ri:
        blind.append("a movx through a register")
    if arm.callees:
        blind.append("an unresolved callee")
    cuts = [e for e in arm.ends if e.startswith(CUTS)]
    if cuts:
        blind.append("a walk stopped at " + "; ".join(cuts))
    return ("no arm found by this method writes an XDATA address; "
            + " and ".join(blind) + " are all outside it")


def arm_status(arm) -> str:
    """`complete`, or the cuts that stopped the walk short. On every 0x0751 arm
    the answer is `complete` at the default bounds, which is the fact that
    lets the negative claims above be stated without a hedge."""
    cuts = [e for e in arm.ends if e.startswith(CUTS)]
    return "cut: " + "; ".join(cuts) if cuts else "complete"


# --- self-test ---------------------------------------------------------------
#
# Every entry is a branch encoding transcribed by hand from `r2 -a 8051`
# against a make_bank_image.py bank image, the way ec/annotations/
# manual-fan-ctrl-0751.md 7 does for its own listings. They are the oracle for
# find/split arithmetic: a change to the tables above that mis-frames one of
# these shows up here rather than as a wrong target in a generated CSV.
#
# The bank1 row is the one worth reading twice. `0x9432` is
# `90 07 51 e0 54 80 70 05` -- the `anl a,#0x80` puts the `jnz` at site + 6,
# so the target is site + 8 + rel = 0x943F. The same arithmetic the 16 bank0
# rows use gives 0x943E, one byte inside the `mov dptr` that follows, and
# would decode as a plausible-looking `mov dptr,#0x7F90`.

SELF_TEST_SITES = (
    # (file offset, region, runtime, branch runtime, branch bytes,
    #  taken target, fall-through start)
    (0x08942, "bank0", 0x8942, 0x8946, b"\x30\xe6\x4f", 0x8998, 0x8949),
    (0x0899D, "bank0", 0x899D, 0x89A1, b"\x30\xe6\x1e", 0x89C2, 0x89A4),
    (0x089EE, "bank0", 0x89EE, 0x89F2, b"\x30\xe7\x14", 0x8A09, 0x89F5),
    (0x08E8B, "bank0", 0x8E8B, 0x8E8F, b"\x30\xe7\x30", 0x8EC2, 0x8E92),
    (0x093CA, "bank0", 0x93CA, 0x93CE, b"\x30\xe7\x08", 0x93D9, 0x93D1),
    (0x09E2F, "bank0", 0x9E2F, 0x9E33, b"\x30\xe7\x17", 0x9E4D, 0x9E36),
    (0x09E4D, "bank0", 0x9E4D, 0x9E51, b"\x30\xe7\x17", 0x9E6B, 0x9E54),
    (0x09E6B, "bank0", 0x9E6B, 0x9E6F, b"\x30\xe7\x17", 0x9E89, 0x9E72),
    (0x09F18, "bank0", 0x9F18, 0x9F1C, b"\x30\xe7\x17", 0x9F36, 0x9F1F),
    (0x09F36, "bank0", 0x9F36, 0x9F3A, b"\x30\xe7\x17", 0x9F54, 0x9F3D),
    (0x09F54, "bank0", 0x9F54, 0x9F58, b"\x30\xe7\x1a", 0x9F75, 0x9F5B),
    (0x09F75, "bank0", 0x9F75, 0x9F79, b"\x30\xe7\x10", 0x9F8C, 0x9F7C),
    (0x0AC17, "bank0", 0xAC17, 0xAC1B, b"\x30\xe4\x0f", 0xAC2D, 0xAC1E),
    (0x0AC30, "bank0", 0xAC30, 0xAC34, b"\x30\xe7\x06", 0xAC3D, 0xAC37),
    (0x0B5EA, "bank0", 0xB5EA, 0xB5EE, b"\x30\xe7\x07", 0xB5F8, 0xB5F1),
    (0x0B73C, "bank0", 0xB73C, 0xB740, b"\x30\xe7\x15", 0xB758, 0xB743),
    (0x11432, "bank1", 0x9432, 0x9438, b"\x70\x05", 0x943F, 0x943A),
)

# The two encoding traps the hand transcriptions are here to catch, checked
# separately from the table so a failure names which one broke.
#
# 0x943F is `mov dptr,#0x93E6`. 0x93E6 is at or above CODE_FLOOR, so it is a
# CODE pointer and the arm's only XDATA claim is whatever the join at 0x9444
# does -- not 0x93E6 as a register. The second is a loop built for the test, so
# `loop` is exercised without depending on a shape this image happens to have.
SELF_TEST_CODE_POINTER = (0x943F, 0x93E6)
# A branch whose target is the branch itself (`jnb acc.7,0x10` at 0x10 is
# 0x13 - 3), immediately followed by a `ret`. The fixture is 0x20 bytes of
# zeros otherwise, so the fall-through terminates at once and the only way the
# descent can revisit 0x10 is the pushed target.
LOOP_FIXTURE = bytes(0x20)
LOOP_SITE = 0x10
LOOP_FIXTURE = (LOOP_FIXTURE[:LOOP_SITE] + bytes([0x30, 0xE7, 0xFD, 0x22])
                + LOOP_FIXTURE[LOOP_SITE + 4:])

# `clr c ; jc` and `setb c ; jnc`, each with a `ret` on both sides of the
# branch. Both carry-flag opcodes sit inside 0xB4-0xDF, and reading that range
# as "the PC-relative branches" turns each of them into a branch whose target
# is made of the next byte -- which then decodes the rest of the routine as
# garbage. This fixture is here because that mistake was made once already: it
# produced `dec r0` / `db 0x06` in the middle of the 0x8E92 block, which is not
# what the bytes there say. The carry-flag opcodes have to survive as ordinary
# instructions, and the branch after them as a branch.
CARRY_FIXTURE = bytearray(b"\x00" * 0x40)
CARRY_FIXTURE[0x10:0x14] = bytes([0xC3, 0x40, 0x03, 0x22])   # clr c ; jc +3 ; ret
CARRY_FIXTURE[0x16] = 0x22                                  # the jc target
CARRY_FIXTURE[0x20:0x24] = bytes([0xD3, 0x50, 0x03, 0x22])   # setb c ; jnc +3 ; ret
CARRY_FIXTURE[0x26] = 0x22                                  # the jnc target
CARRY_FIXTURE = bytes(CARRY_FIXTURE)
CARRY_SITES = ((0x10, b"\xc3\x40\x03\x22", 0x0016),
               (0x20, b"\xd3\x50\x03\x22", 0x0026))


def self_test(fw_path: str) -> int:
    d = open(fw_path, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the hand transcriptions were taken from", file=sys.stderr)
        return 1
    bad = 0
    print("walk_branch_arms.py --self-test")
    for foff, region, rt, want_branch, want_raw, want_taken, want_fall in SELF_TEST_SITES:
        found = test_site(d, region, foff, rt, 0x0751, pd_verified)
        if found is None:
            print(f"  FAIL  runtime 0x{rt:04X}: no branch found after the site")
            bad += 1
            continue
        got = (found["branch"], found["raw"], found["taken"], found["fall"])
        want = (want_branch, want_raw, want_taken, want_fall)
        ok = got == want
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  runtime 0x{rt:04X}  "
              f"`{found['raw'].hex(' ')}` at 0x{found['branch']:04X} -> "
              f"taken 0x{found['taken']:04X}, fall-through 0x{found['fall']:04X}")
        if not ok:
            print(f"        expected branch 0x{want_branch:04X} "
                  f"`{want_raw.hex(' ')}` -> taken 0x{want_taken:04X}, "
                  f"fall-through 0x{want_fall:04X}")

    # The CODE-pointer trap, through the whole path a reader would take it.
    pc, want = SELF_TEST_CODE_POINTER
    co = offset_for_runtime(pc, "bank1")
    got_dptr = (d[co + 1] << 8) | d[co + 2]
    ok = d[co] == MOV_DPTR and got_dptr == want and got_dptr >= CODE_FLOOR
    print(f"  {'ok  ' if ok else 'FAIL'}  0x{pc:04X} is `mov dptr,#0x{got_dptr:04X}`, "
          f"which is a CODE pointer (>= 0x{CODE_FLOOR:04X}), not an XDATA access")
    bad += 0 if ok else 1

    # Loop detection, on a fixture rather than on the image: the point is that
    # a self-referential arm terminates and says so, and that the run does not
    # have to depend on this firmware containing such a shape.
    arm = descend(LOOP_FIXTURE, "bank0", LOOP_SITE, 0x0751, 8, 64, True)
    ok = any(e.startswith(END_LOOP) for e in arm.ends) and arm.insns == 2
    print(f"  {'ok  ' if ok else 'FAIL'}  a self-referential arm stops at the "
          f"visited-address cut ({arm.insns} insn, ends {arm.ends})")
    bad += 0 if ok else 1

    for site, want_raw, want_target in CARRY_SITES:
        ok = CARRY_FIXTURE[site:site + len(want_raw)] == want_raw
        arm = descend(CARRY_FIXTURE, "bank0", site, None, 8, 64, True)
        # 4 insn and not more: the carry-flag opcode has to be decoded as an
        # instruction and the branch after it as a branch, or the walk stops in
        # the wrong place and reports a target nobody asked for.
        texts = [t for _, insns in arm.blocks for _, t in insns]
        ok = (ok and arm.insns == 4
              and any(f"0x{want_target:04X}" in t for t in texts))
        print(f"  {'ok  ' if ok else 'FAIL'}  0x{site:04X} `{want_raw.hex(' ')}` -- "
              f"the carry-flag opcode is an instruction and the branch after it "
              f"targets 0x{want_target:04X} ({arm.insns} insn)")
        bad += 0 if ok else 1

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the hand "
              "transcriptions in the SELF_TEST_SITES table")
        return 1
    print(f"self-test passed: all {len(SELF_TEST_SITES)} branch sites split as "
          "hand-decoded from r2, the 0x9432 off-by-one resolves to 0x943F, and "
          "a loop terminates")
    return 0


# One table, two row shapes. `kind` says which, and the columns that only
# apply to one of them are blank on the other -- a second file would drift from
# the first, and the .md table beside this one is re-derived from both shapes.
CSV_HEAD = ["addr", "kind", "site_runtime", "branch", "test", "arm",
            "arm_start", "callee", "region", "insns", "xdata",
            "code_pointers", "code_immediates", "callees", "unattributed",
            "ends", "status", "window"]

def _code_pointers(arm):
    return " ; ".join(f"0x{c:04X}" for c in sorted(set(arm.code_pointers)))


def _code_immediates(arm):
    return " ; ".join(f"0x{c:04X}" for c in sorted(set(arm.code_immediates)))


def write_csv(d, addrs, pd_verified, callee_depth, max_depth, max_insns) -> int:
    w = csv.writer(sys.stdout)
    w.writerow(CSV_HEAD)
    for text in addrs:
        addr = int(text, 16)
        for off, region, rt, test, arms in arms_for(d, addr, pd_verified,
                                                    max_depth, max_insns):
            for arm in arms:
                w.writerow([f"0x{addr:04X}", "arm", f"0x{rt:04X}",
                            f"0x{test['branch']:04X}", test["test"], arm.kind,
                            f"0x{arm.start:04X}", "", region,
                            arm.insns, arm.accesses, _code_pointers(arm),
                            _code_immediates(arm),
                            " ; ".join(f"0x{c:04X}" for c in arm.callees),
                            arm.unattributed, "; ".join(arm.ends),
                            arm_status(arm), arm.window])
            if callee_depth:
                for callee in dict.fromkeys(c for a in arms for c in a.callees):
                    w.writerow([f"0x{addr:04X}", "callee", f"0x{rt:04X}",
                                "", "", "", "", f"0x{callee:04X}", region]
                               + callee_row(d, region, callee, max_depth, max_insns))
    return 0


def callee_row(d, region, callee, max_depth, max_insns):
    """One level into a callee. `unresolved` is a verdict about this depth,
    not about the callee: it lands here when the callee's own entry point does
    not settle, exactly as register_ref_table.py's `handoff->unresolved` does.

    `dptr` starts None because a callee inherits the caller's DPTR and that
    value is not carried here; a callee opening with `movx a,@dptr` therefore
    lands in the `unattributed` count rather than being charged to whatever
    address the call site happened to have loaded."""
    def row(insns, xdata, codes, immcodes, unattributed, ends, status, window):
        return [insns, xdata, codes, immcodes, "", unattributed, ends,
                status, window]

    if offset_for_runtime(callee, region) is None:
        return row(0, "", "", "", 0, "",
                   f"unresolved: not reachable from region {region}", "")
    arm = descend(d, region, callee, None, max_depth, max_insns, True)
    ends = "; ".join(arm.ends)
    if not arm.insns:
        return row(0, "", "", "", 0, ends,
                   "unresolved: no instruction decodes at the entry point", "")
    cuts = [e for e in arm.ends if e.startswith(CUTS)]
    if cuts:
        status = "unresolved: " + "; ".join(cuts)
    elif arm.unattributed or arm.movx_ri:
        status = "partial: " + ("DPTR built at run time" if arm.unattributed
                                else "movx through a register")
    else:
        status = "resolved"
    return row(arm.insns, arm.accesses, _code_pointers(arm),
               _code_immediates(arm), arm.unattributed, ends, status,
               arm.window)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("addrs", nargs="*", help="hex addresses, e.g. 0x0751")
    ap.add_argument("--self-test", action="store_true",
                    help="check the branch split against hand transcriptions and exit")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per arm on stdout instead of the decode")
    ap.add_argument("--callee-depth", type=int, choices=(0, 1), default=0,
                    help="1: follow each arm's lcall/ljmp one level (default 0)")
    ap.add_argument("--max-depth", type=int, default=16,
                    help="nested control transfers to follow per arm (default 16, "
                         "which covers all 34 arms of 0x0751 without the limit "
                         "biting; 8 leaves three of them cut)")
    ap.add_argument("--max-insns", type=int, default=500,
                    help="instruction budget per arm (default 500, which covers "
                         "the largest of the 34 arms of 0x0751 whole)")
    args = ap.parse_args()

    if args.self_test:
        return self_test(args.firmware)

    if not args.addrs:
        ap.error("give a firmware image and at least one address, or --self-test")

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the annotations were written against", file=sys.stderr)
        return 1

    if args.csv:
        return write_csv(d, args.addrs, pd_verified, args.callee_depth,
                         args.max_depth, args.max_insns)

    branched = 0
    for text in args.addrs:
        addr = int(text, 16)
        print(f"0x{addr:04X}: walking both arms of every conditional branch on it\n")
        for off, region, rt, test, arms in arms_for(d, addr, pd_verified,
                                                    args.max_depth, args.max_insns):
            if test is None:
                print(f"  runtime 0x{rt:04X}  {region:<7} no conditional branch on a "
                      "mode bit follows the site in the decoded window")
                continue
            branched += 1
            print(f"  runtime 0x{rt:04X}  {region:<7} {test['test']}")
            for arm in arms:
                print(f"    {arm.kind:<12} 0x{arm.start:04X}  {arm.insns} insn in "
                      f"{len(arm.blocks)} block(s)")
                print(f"      reaches: {arm.accesses or 'no XDATA by this method'}")
                claim = no_claim(arm)
                if claim:
                    print(f"      {claim}")
                if arm.code_pointers or arm.code_immediates:
                    print(f"      CODE, not XDATA: movc/jmp through "
                          f"{_code_pointers(arm) or 'nothing'}; DPTR immediates "
                          f">= 0x{CODE_FLOOR:04X} at "
                          f"{_code_immediates(arm) or 'none'}")
                if arm.callees:
                    print("      callees: "
                          + " ; ".join(f"0x{c:04X}" for c in arm.callees))
                if arm.unattributed:
                    print(f"      {arm.unattributed} movx on a DPTR built at run "
                          "time -- unattributed on purpose")
                if arm.movx_ri:
                    print(f"      {arm.movx_ri} movx through a register -- no address")
                print(f"      ends: {'; '.join(arm.ends) or 'no control-flow instruction'}")
                print(f"      status: {arm_status(arm)}")
                for start, insns in arm.blocks:
                    print(f"      -- block 0x{start:04X}")
                    for pc, mn in insns:
                        print(f"        0x{pc:04X}  {mn}")
            if args.callee_depth:
                for callee in dict.fromkeys(c for a in arms for c in a.callees):
                    row = callee_row(d, region, callee, args.max_depth, args.max_insns)
                    print(f"    callee      0x{callee:04X}  "
                          f"{row[1] or 'no XDATA by this method'}  [{row[6]}]")
            print()
    return 0 if branched else 1


if __name__ == "__main__":
    sys.exit(main())
