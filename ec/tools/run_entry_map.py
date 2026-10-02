#!/usr/bin/env python3
"""Decode the `run=0x8518` block slot by slot: what each entry does, what it
writes, and which stub reaches it.

`docs/findings/charge-target-caller-chain.md` established that bank0
`0x8518`-`0x8559` is one stride-3 run and characterised two of its targets. It
left the rest as "a periodic task that looks like one `lcall`", because the
issue that asked how `0xB158` is reached found a single path and stopped there.
The same stub table that path runs through names seven entries of this block,
not one, and the run itself is not a single walk. Both facts are re-derived here
from the committed image rather than taken from either file.

**The block is seven segments, and the seven stub immediates are their heads.**
An `lcall` slot returns into the next slot; an `ljmp` slot leaves the block. A
segment therefore starts at each `ljmp` and at whatever enters the block, and
runs to the next `ljmp`. Everything about the tool's central claim is computed
off the run's own opcodes and the stub table's own immediates; `--csv` carries
the segment and head flags per slot and `--self-test` pins that each stub's
index is its own segment's head, which is the claim rather than the count of
stubs.

**The reachability premise is pinned from bytes, because the whole table rests
on it.** That a tail-jumped slot's target returns to the entry's caller instead
of resuming the block is not a reading of the run; it is a property of the
`0x1100` bank-select trampoline every one of the seven stubs goes through. The
trampoline pushes a saved byte, a marker and DPTR, then `ret`s -- and that
`ret` consumes the DPTR, so what the far routine's own `ret` pops is the
marker, not the caller's return address. The marker's *high* byte is the
trampoline's own `mov a,#0x11`, a constant in these bytes, so a far routine
returns somewhere in 0x1100-0x11FF whatever the low byte is. `--self-test`
derives that window from the stub's own bytes and checks it is disjoint from
every address in the run; if any of that fails the tool prints `reach
unsettled` in place of the reachability column rather than publishing a table
built on the assumption.

**The host window is the split that makes a live capture gradeable.**
`ec_timer_capture.HOST_WINDOW` is imported, never restated, and every XDATA in
every slot's write set is classified against it. `evidence/ec-watch/
2026-09-24-host-window-page-census.txt` measures the pages at 0/256 non-`0xFF`,
so a byte the block writes in one of those pages reads `0xFF` to the host
whatever the EC holds. Those slots are reported as wholly or partly invisible
so a future capture that watches one and sees nothing does not read it as a
stalled counter. A read-only EC window means this is a preparation for a run
somebody makes at the machine, not a result: nothing here has been observed.

**What it will not say.** The block walk is `walk_branch_arms.descend()` used
unchanged, and its refusals are its refusals: a DPTR built at run time and a
`movx @Ri` are `unattributed` rather than charged to the last `mov dptr`, a
callee is followed only to `--callee-depth` and reports `unresolved` past it,
and a slot with no attributed write is "no arm found by this method writes an
XDATA address" -- never "the EC does not". The whole-image transfer scan is
unaligned and covers two opcodes, so its zero is "not found by this method".
A `write` is an instruction storing to an address, not evidence the EC acts on
it.

`task-call-table.csv` is read and never written: it is `task_call_table.py`'s
output, and `--check` there still holds it to the image.

Usage:
    python3 run_entry_map.py ../firmware/GMxMGxx_11.800
    python3 run_entry_map.py ../firmware/GMxMGxx_11.800 --csv > run.csv
    python3 run_entry_map.py ../firmware/GMxMGxx_11.800 --writes-csv > writes.csv
    python3 run_entry_map.py ../firmware/GMxMGxx_11.800 --callee-depth 1
    python3 run_entry_map.py --self-test ../firmware/GMxMGxx_11.800
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from disasm8051 import decode                                    # noqa: E402
from ec_timer_capture import HOST_WINDOW                          # noqa: E402
from trace_xdata_refs import PD_MARKER, offset_for_runtime        # noqa: E402
from walk_branch_arms import CUTS, descend                        # noqa: E402

DEFAULT_FIRMWARE = os.path.join("ec", "firmware", "GMxMGxx_11.800")
TASK_TABLE = os.path.join(HERE, os.pardir, "annotations", "task-call-table.csv")
FUNCTIONS = os.path.join(HERE, os.pardir, "annotations", "ghidra-functions.csv")

# The run this tool decodes, and the `table`/`run` pair that names it in
# task-call-table.csv. The run value is what the CSV carries, not a default:
# `0x8518` is the base `task_call_table.py` calls a run by, and the rows are
# read out of the committed file rather than re-scanned, so a table that had
# been regenerated against a different image would name no run at all and say
# so instead of quietly decoding somewhere else.
RUN = "0x8518"
RUN_TABLE = "bank0-transfer-run"

# The region the run's runtime addresses resolve against, and the CSV's own
# `bank` column spells it. `descend()` needs a region name to turn a runtime
# address into a file offset, and a slot and its target are both in it -- an
# `lcall 0x3AD6` out of a bank0 slot crosses into the common area, which is
# why descend() says a callee starts with an unknown DPTR.
RUN_REGION = "bank0"

# The three bytes every entry of a stride-3 run occupies, and the two opcodes
# that can start one. `is_transfer()` in task_call_table.py is the authority on
# which bytes these are and why `02 93` is excluded; this module reads the
# opcodes the CSV already committed rather than re-deciding the question, and
# `--self-test` holds the two readings against each other.
STRIDE = 3

# The bank-select trampoline the seven stubs share, and the shape of it. The
# stub is `mov dptr,#target ; ljmp 0x1100`, so it is the *stub* that must be
# shown to establish the marker, and 0x1100 is the one every stub in this run
# routes through (`via` in the CSV says 0x1100 for all seven). Its bytes are
# pinned in --self-test rather than quoted here, because what matters is that
# the shape is `push <marker> ... ret` and not what the marker is.
SELECT_STUB = 0x1100
# The stub's own extent. `find_banks.py` puts the four bank-select stubs 20
# bytes apart with no gap between them, so this is both the bound on decoding
# one and the reason a longer instruction count would read the *next* stub.
SELECT_STUB_LENGTH = 20
# All four, because the marker's low byte is written by whichever of them ran
# last. The last two are absent from this image as bank selects -- 350 of the
# 403 stubs route through the first and 53 through the second -- so their tails
# are read for completeness rather than as reachable landings, which is why the
# claim is held against the window and not against any one of the four.
BANK_SELECT_STUBS = (0x1100, 0x1114, 0x1128, 0x113C)

# Bounds, per slot, as recorded constants rather than flags, and walk_branch_
# arms.py's own defaults for the 0x0751 arms so a number from this tool is
# comparable with a number from that one rather than tuned until it looked
# better (../../docs/findings/count-bounded-walk-invariant.md).
MAX_DEPTH = 16
MAX_INSNS = 500

# How the two reachability verdicts read. The first is what the bytes say; the
# second is what the tool says when it cannot say the first, and it is a
# placeholder in the reachability column rather than a silent absence.
REACH_SETTLED = "settled from the 0x1100 trampoline bytes"
REACH_UNSETTLED = "reach unsettled"

# A slot with no committed name gets this, rather than a blank cell: a blank
# would read as "not applicable" and as "the name exists and says nothing".
NO_NAME = "no committed name"


class Slot:
    """One entry of the run: where it is, what it transfers, and where it lands.

    `segment` is the index of the maximal lcall run this entry is part of, and
    `head` is whether a stub's immediate names it. Both are computed from the
    run's own opcodes in `segments()`; neither is read from a literal.
    """

    def __init__(self, index, address, opcode, target):
        self.index = index
        self.address = address
        self.opcode = opcode            # "lcall" / "ljmp"
        self.target = target
        self.segment = None
        self.head = False
        self.stub = None                # the far-call stub that names it
        self.name = NO_NAME
        self.arm = None

    @property
    def tail_jump(self):
        """Does this entry leave the block rather than return into it?"""
        return self.opcode == "ljmp"

    def __repr__(self):
        return f"Slot({self.index}, 0x{self.address:04X}, {self.opcode})"


def read_run(path=os.path.join(REPO, TASK_TABLE), run=RUN):
    """The run's rows out of the committed table, as a list of `Slot`.

    Read rather than re-scanned, and that is the point: `task_call_table.py`
    owns the question "where do the stride-3 runs start and stop" and holds it
    to the image with `--check`, and a second scan here could only drift from
    that answer. The stub table is read from the same file for the same reason.
    """
    slots = []
    stubs = {}
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            if row["table"] == RUN_TABLE and row["run"] == run:
                slots.append(Slot(int(row["index"]), int(row["address"], 16),
                                  row["opcode"], int(row["target"], 16)))
            elif row["table"] == "far-call-stub":
                stubs[int(row["target"], 16)] = int(row["address"], 16)
    slots.sort(key=lambda s: s.index)
    return slots, stubs


def segments(slots):
    """Label every slot with its segment index and mark the segment heads.

    A segment is a maximal run of slots from a head to the next `ljmp`; the
    `ljmp` itself is the last slot of its segment, because it is the entry that
    leaves. A slot is a head if it is the first of the run, or if the slot
    before it is an `ljmp` -- which makes the heads derivable from the opcodes
    alone, and the whole claim "the seven stubs name the seven heads" a
    comparison between two independently derived sets rather than a restatement
    of one.
    """
    segment = 0
    for i, slot in enumerate(slots):
        if i == 0 or slots[i - 1].tail_jump:
            slot.segment = segment
            slot.head = True
            segment += 1
        else:
            slot.segment = segment - 1
    return slots


def head_indices(slots):
    """The indices of the segment heads, in run order."""
    return [s.index for s in slots if s.head]


def index_of(slots):
    """{slot address: run index}, so a stub's immediate can name a slot.

    A stub names a slot when its immediate is that slot's own address. Matching
    on the address rather than looking the immediate up as a code target is
    deliberate: the stub sits in the common area and the run in bank 0, so the
    two are not comparable addresses and the comparison has to be against the
    run's own extent.
    """
    return {s.address: s.index for s in slots}


def committed_names(path=os.path.join(REPO, FUNCTIONS)):
    """`{(scope, address): name}` from ghidra-functions.csv, keyed by integer.

    Keyed on the parsed integer rather than on the cell's text because the
    `addr` column is spelled four different ways across the file -- `0B065`,
    `B065`, `0652` for the same address -- and a text key would silently miss
    every row that is not spelled the way the lookup happens to spell it. That
    failure is invisible: the row still prints, with `no committed name` in the
    column, which reads as a fact about the firmware rather than as a missed
    lookup. Parsing makes the spelling irrelevant.
    """
    out = {}
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                addr = int(row["addr"], 16)
            except ValueError:
                continue
            out[(row["scope"], addr)] = row["name"]
    return out


def name_for(names, region, addr):
    return names.get((region, addr), NO_NAME)


def host_visible(addr):
    """Is this XDATA inside the window this machine actually maps?

    `HOST_WINDOW` is imported from `ec_timer_capture.py` rather than restated,
    because the census behind it is a measurement of one machine's mapping and
    a second copy of the pair of ranges is a second thing to keep in step with
    it. The verdict is about the *host's* view: a byte outside the window reads
    `0xFF` however the EC holds it, which is the whole reason the classification
    is in the table.
    """
    return any(lo <= addr <= hi for lo, hi in HOST_WINDOW)


def host_page(addr):
    return f"0x{addr & 0xFF00:04X}"


def direction(dirs):
    """`read`, `write` or `r+w` for one address's set of access directions.

    Spelled here rather than taken from `walk_branch_arms.Arm.accesses`, because
    that property renders a whole arm's accesses in one string and this needs
    the one word for a single address in three different output modes.
    """
    return "r+w" if "w" in dirs and "r" in dirs else "write" if "w" in dirs else "read"


def walk_slot(d, region, slot, pd_verified, callee_depth, max_depth, max_insns):
    """The slot's own walk, and the one level below it when asked.

    `descend()` is used exactly as it stands, so the write set, the
    `unattributed` count and the `END_*` reasons are its own and a reader who
    knows `walk_branch_arms.py` needs nothing new to read a row here. A callee
    is descended one level because the run's entries are almost entirely calls
    into routines that write through a DPTR the callee builds for itself, and
    stopping at the call would leave nearly every slot's write set empty -- but
    it is a *declared* depth, and a callee that does not settle at that depth
    says `unresolved` instead of being dropped.
    """
    arm = descend(d, region, slot.target, None, max_depth, max_insns, pd_verified)
    slot.arm = arm
    if not callee_depth:
        return []
    out = []
    for callee in dict.fromkeys(arm.callees):
        if offset_for_runtime(callee, region) is None:
            out.append((callee, None, "unresolved: not reachable from region "
                                      f"{region}", set()))
            continue
        sub = descend(d, region, callee, None, max_depth, max_insns, pd_verified)
        cuts = [e for e in sub.ends if e.startswith(CUTS)]
        if not sub.insns:
            status = "unresolved: no instruction decodes at the entry point"
        elif cuts:
            status = "unresolved: " + "; ".join(cuts)
        elif sub.unattributed or sub.movx_ri:
            status = "partial: " + ("DPTR built at run time" if sub.unattributed
                                    else "movx through a register")
        else:
            status = "resolved"
        out.append((callee, sub, status, sub.writes()))
    return out


def slot_writes(slot, callees):
    """The slot's attributed XDATA writes, its own walk plus any callee's.

    The callee's writes are included because the question is what the *pass*
    writes, not what the entry point's first block writes: an entry that is a
    single `lcall` writes whatever its callee writes. Callees at an unresolved
    depth contribute nothing, which is the safe direction and is why the
    per-slot status column says so.
    """
    out = dict(slot.arm.xdata) if slot.arm else {}
    for _callee, sub, _status, writes in callees:
        if sub is None:
            continue
        for addr, dirs in sub.xdata.items():
            cur = out.setdefault(addr, set())
            cur |= dirs
    return out


def slot_status(slot, callees):
    """`complete`, or what stopped the walk short -- the slot's and the
    callees' cuts together, so a slot whose entry point settled but whose
    callee did not is not reported as whole."""
    ends = list(slot.arm.ends) if slot.arm else []
    for _callee, sub, _status, _w in callees:
        if sub is not None:
            ends += sub.ends
    cuts = [e for e in ends if e.startswith(CUTS)]
    return "cut: " + "; ".join(dict.fromkeys(cuts)) if cuts else "complete"


def no_claim(slot, callees):
    """The wording for a slot with no attributed write.

    `walk_branch_arms.no_claim()` states the same refusal for one arm, and the
    first three clauses below are its vocabulary unchanged. The two that are
    specific to a slot are the callees: a slot is usually a single `lcall`, so
    an empty write set most often means the *callee* was not followed far
    enough, and saying so is the difference between a bounded walk and an
    absence. A callee that did not settle at the declared depth is named.
    """
    if not slot.arm:
        return "no arm found by this method decodes to any instruction"
    if slot.arm.writes():
        return ""
    blind = ["indirect access"]
    if slot.arm.unattributed:
        blind.append("a DPTR built at run time")
    if slot.arm.movx_ri:
        blind.append("a movx through a register")
    if slot.arm.callees:
        blind.append("an unresolved callee")
    unsettled = [f"0x{callee:04X} ({status.split(':')[0]})"
                 for callee, _sub, status, _w in callees
                 if status.startswith(("unresolved", "partial"))]
    if unsettled:
        blind.append("a callee followed only to the declared depth: "
                     + ", ".join(unsettled))
    cuts = [e for e in slot.arm.ends if e.startswith(CUTS)]
    if cuts:
        blind.append("a walk stopped at " + "; ".join(cuts))
    return ("no arm found by this method writes an XDATA address; "
            + " and ".join(blind) + " are all outside it")


def transfer_hits(d, addrs):
    """Whole-image, unaligned, for `lcall`/`ljmp` naming any of `addrs`.

    Unaligned on purpose and reported as such: a hit inside a data table reads
    as a call, which is the over-count `bank-call-audit.md` 1 already measures,
    and the alternative -- aligning first -- would miss the very thing the scan
    is for. A zero is "not found by this method, over these regions", which is
    the phrase the table and the write-up both use.
    """
    hits = {}
    for addr in addrs:
        found = []
        for op in (0x12, 0x02):
            pat = bytes([op, addr >> 8, addr & 0xFF])
            found += [o for o in range(len(d) - 2) if d[o:o + 3] == pat]
        if found:
            hits[addr] = sorted(found)
    return hits


# --- the 0x1100 trampoline, and the marker it pushes --------------------------

def decode_select_stub(d, stub=SELECT_STUB, length=SELECT_STUB_LENGTH):
    """The stub's instructions, as [(file offset, bytes, text)].

    Decoded rather than pattern-matched because the claim is about the
    *sequence* -- pushes, a bank write, then a `ret` -- and a byte comparison
    would pass against a decoder that had learned to mis-render the same bytes
    in a self-consistent way, which is the failure `walk_branch_arms.py`'s own
    `--self-test` exists to catch.

    Bounded at the stub's own 20 bytes rather than at a fixed instruction
    count: the four stubs sit back to back with no gap, so a count long enough
    to reach a later stub's `ret` would decode past this one and the predicate
    "ends in ret" would then be reading the *next* stub. `find_banks.py` puts
    the stubs 20 bytes apart, and that spacing is the bound.
    """
    end = stub + length
    out = []
    for off, raw, text in decode(d, stub, count=20, addr=stub):
        if off >= end:
            break
        out.append((off, raw, text))
    return out


def marker_landing(d, stub=SELECT_STUB):
    """Where a far routine's own `ret` lands: `(window, evidence)`, or
    `(None, evidence)` when the stub does not have the shape the claim needs.

    The trampoline pushes three things and then `ret`s. The `ret` consumes the
    two DPTR bytes and jumps to the target, so the *marker* is what the far
    routine's own `ret` will pop -- and it is not the caller's return address,
    which is what makes a tail-jumped slot leave the block rather than resume
    it. That is the whole premise the reachability table rests on, so it is
    read off the stack shape here rather than assumed.

    The marker's **high** byte is the stub's own `mov a,#0x11`, a constant in
    these bytes, so the landing is inside 0x1100-0x11FF whatever the low byte
    is. Its **low** byte is the value internal-RAM byte 0x08 held at entry,
    which is *not* a constant and is not guessed at: the four stubs each write
    their own value into 0x08 (`mov 0x08,#imm`), and on a call through a given
    stub that value is the one its own previous call left. The four candidate
    tails are reported as the four, each of them inside the window, and the
    claim published rests on the window rather than on a single address.

    Returns `(window, evidence)` where `window` is an inclusive
    `(low, high)` address pair; it is None when the premise cannot be settled
    from the bytes, and the caller then prints `REACH_UNSETTLED` in place of
    the reachability column rather than publishing a table built on the
    assumption.
    """
    insns = decode_select_stub(d, stub)
    if not insns:
        return None, [("stub", f"nothing decodes at 0x{stub:04X}")]
    texts = [t.split()[0].lower() for _, _, t in insns]
    evidence = [("stub", f"{len(insns)} instructions, "
                         f"{sum(1 for t in texts if t == 'push')} of them pushes, "
                         f"ending {texts[-1]}")]

    # The DPTR pair has to be the top two pushes, or the stub's own `ret` is not
    # jumping to the target and the whole far-call shape is something else.
    pushes = [(addr, raw) for (addr, raw, t) in insns
              if t.split()[0].lower() == "push"]
    if len(pushes) < 3:
        evidence.append(("stub shape", "fewer than three pushes; the marker "
                                       "premise needs the saved byte, the marker "
                                       "and DPTR"))
        return None, evidence
    if texts[-1] != "ret":
        evidence.append(("stub shape", f"the stub ends in {texts[-1]}, not ret, so "
                                       "the marker is never popped"))
        return None, evidence
    dpl, dph = pushes[-2][1][1], pushes[-1][1][1]
    if (dpl, dph) != (0x82, 0x83):
        evidence.append(("stub shape", f"the top two pushes are direct "
                                       f"0x{dpl:02X} and 0x{dph:02X}, not DPL and "
                                       "DPH, so the ret is not jumping to DPTR"))
        return None, evidence
    evidence.append(("stub shape", "the top two pushes are DPL and DPH, so the "
                                   "stub's own ret pops them and jumps to the "
                                   "far address it was handed"))

    # The marker's high byte: the accumulator between the saved byte and DPL.
    high = None
    for addr, raw, text in insns:
        head = text.split()[0].lower()
        if head == "mov" and raw[0] == 0x74:
            high = raw[1]
            evidence.append(("marker", f"the stub's `mov a,#0x{high:02X}` at "
                                       f"0x{addr:04X} is the byte a later ret "
                                       "pops into PCH, so every far routine "
                                       f"returns inside 0x{high:02X}00-0x{high:02X}FF"))
            break
    if high is None:
        evidence.append(("marker", "no `mov a,#imm` between the saved byte and "
                                   "DPL, so the marker's high byte is not a "
                                   "constant this method can read"))
        return None, evidence

    # The low byte is the value of direct 0x08 at entry, which is a runtime
    # value. The four stubs' own writes are what the landing can be, and each
    # is inside the window; that is the claim, not a single address.
    tails = []
    for base in BANK_SELECT_STUBS:
        off = offset_for_runtime(base, "common")
        if off is None:
            continue
        for i in range(off, off + 32):
            if d[i] == 0x75 and d[i + 1] == 0x08:
                tails.append((base, d[i + 2], (high << 8) | d[i + 2]))
                break
    if tails:
        evidence.append(("low byte", "the marker's low byte is direct 0x08's "
                                     "value at entry, which is a runtime value "
                                     "rather than a constant: "
                                     + ", ".join(
                                         f"stub 0x{base:04X} writes "
                                         f"0x{val:02X} -> 0x{land:04X}"
                                         for base, val, land in tails)
                                     + ". Every one is inside the window above "
                                       "and none is a slot of the run."))
    # A plain (lo, hi) pair rather than a range: every use is a bound or
    # a set membership test, and `range` supports neither indexing nor a
    # half-open upper bound that reads as a closed one at the call site.
    window = ((high << 8), (high << 8) | 0xFF)
    return window, evidence


def reach_settled(d, window, run_addrs):
    """Does the marker's landing window keep a far routine out of the run?

    The claim is only worth publishing if no address a far routine can return to
    is a slot of the block, so the two are compared as sets: the window against
    the run's own addresses. That holds whatever the marker's low byte is, which
    is the point -- the low byte is a runtime value and the reachability claim
    must not depend on which of the four the EC happened to take.
    """
    if window is None:
        return False, "the marker's high byte is not a constant in the bytes"
    low, high = window
    clash = sorted(a for a in run_addrs if low <= a <= high)
    if clash:
        return False, ("the landing window and the run's own addresses overlap at "
                       + ", ".join(f"0x{a:04X}" for a in clash))
    return True, (f"the marker's landing window 0x{low:04X}-0x{high:04X} is "
                  "disjoint from every address in the run")


# --- self-test ----------------------------------------------------------------

# The trampoline's own bytes, transcribed by hand against the image rather than
# read out of a decode this tool then checked against itself. `walk_branch_arms.
# SELF_TEST_SITES` is the same arrangement and for the same reason.
SELECT_STUB_BYTES = "c0 08 74 11 c0 e0 c0 82 c0 83 75 08 0a c2 90 c2 91 c2 92 22"
# The marker's high byte, transcribed by hand against the image: the stub's
# `mov a,#0x11` at +2, which is the byte a later `ret` pops into PCH. The low
# byte is deliberately *not* pinned to a literal here, because it is the value
# internal-RAM byte 0x08 held at entry and that is a runtime value -- the four
# stubs' own writes are enumerated in marker_landing() instead, and the claim
# published rests on the window.
MARKER_HIGH_VALUE = 0x11
MARKER_WINDOW = (0x1100, 0x11FF)


def self_test(fw_path: str) -> int:
    d = open(fw_path, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the annotations were written against", file=sys.stderr)
        return 1
    bad = 0
    print("run_entry_map.py --self-test")

    ok = d[SELECT_STUB:SELECT_STUB + SELECT_STUB_LENGTH].hex(" ") == SELECT_STUB_BYTES
    print(f"  {'ok  ' if ok else 'FAIL'}  0x{SELECT_STUB:04X} is `{SELECT_STUB_BYTES}`")
    bad += 0 if ok else 1

    # The stub is a push/marker/bank-write/ret shape, and each of the four is
    # checked against the decode rather than against a byte pattern: a pattern
    # would pass on a decoder that renders the same bytes consistently wrongly.
    texts = [t.split()[0].lower() for _, _, t in decode_select_stub(d)]
    for want, why in (("push", "pushes the saved byte, the marker and DPTR"),
                      ("mov", "loads the marker's high byte"),
                      ("clr", "writes the bank-select port"),
                      ("ret", "pops the DPTR it was handed")):
        got = want in texts
        print(f"  {'ok  ' if got else 'FAIL'}  the stub {why} (`{want}`): "
              f"{' '.join(texts)}")
        bad += 0 if got else 1

    window, evidence = marker_landing(d)
    for what, detail in evidence:
        print(f"        {what}: {detail}")
    ok = window == MARKER_WINDOW
    print(f"  {'ok  ' if ok else 'FAIL'}  the marker's landing window is "
          f"0x{MARKER_WINDOW[0]:04X}-0x{MARKER_WINDOW[1]:04X} -- the high byte is "
          f"the stub's `mov a,#0x{MARKER_HIGH_VALUE:02X}` and the low byte is "
          f"direct 0x08's runtime value, so the claim rests on the window")
    bad += 0 if ok else 1

    slots, stubs = read_run()
    settled, why = reach_settled(d, window, [s.address for s in slots])
    print(f"  {'ok  ' if settled else 'FAIL'}  {why}")
    bad += 0 if settled else 1

    # The run's own shape: the opcodes are read from the committed CSV and
    # re-decoded from the image, and the two have to agree, because a CSV that
    # had drifted is exactly what `task_call_table.py --check` is for and this
    # tool must not be the one that hides it.
    ok = bool(slots)
    print(f"  {'ok  ' if ok else 'FAIL'}  the committed table carries the "
          f"run={RUN} rows ({len(slots)} read)")
    bad += 0 if ok else 1

    decoded_ok = True
    for slot in slots:
        fo = offset_for_runtime(slot.address, RUN_REGION)
        op = d[fo]
        mnemonic_name = "lcall" if op == 0x12 else "ljmp" if op == 0x02 else "?"
        target = (d[fo + 1] << 8) | d[fo + 2]
        if mnemonic_name != slot.opcode or target != slot.target:
            decoded_ok = False
            print(f"        FAIL  index {slot.index} at 0x{slot.address:04X}: "
                  f"CSV says {slot.opcode} 0x{slot.target:04X}, image decodes "
                  f"{mnemonic_name} 0x{target:04X}")
    print(f"  {'ok  ' if decoded_ok else 'FAIL'}  every row's opcode and immediate "
          f"re-decode from the image")
    bad += 0 if decoded_ok else 1

    # The stride, asserted as arithmetic on the committed addresses rather than
    # as a literal, because a lost slot moves the spacing and not the count.
    strides = {slots[i + 1].address - slots[i].address
               for i in range(len(slots) - 1)}
    ok = strides == {STRIDE}
    print(f"  {'ok  ' if ok else 'FAIL'}  every entry is {STRIDE} bytes after the "
          f"one before (observed strides: {sorted(strides)})")
    bad += 0 if ok else 1

    segments(slots)
    idx = index_of(slots)
    named = sorted(idx[t] for t in stubs if t in idx)
    heads = head_indices(slots)
    # The claim, not the census: each stub's run index is its own segment's head.
    ok = named == heads
    print(f"  {'ok  ' if ok else 'FAIL'}  each stub's run index is its own "
          f"segment's head (stubs name {named}; heads are {heads})")
    bad += 0 if ok else 1

    # And the opposite reading, pinned so a decoder that made every slot a head
    # would fail here rather than passing the comparison above by accident.
    ok = len(heads) < len(slots)
    print(f"  {'ok  ' if ok else 'FAIL'}  not every entry is a head, so the "
          f"comparison above is not vacuous ({len(heads)} of {len(slots)})")
    bad += 0 if ok else 1

    # The segment shape itself, which is what makes the head a head. A segment
    # is a head plus the run of non-head slots after it, up to the next head.
    # Within one, the ljmp can only be the *last* slot -- an ljmp earlier would
    # have ended the segment there -- and a head may itself be that ljmp, which
    # is a one-slot segment and three of the seven here are.
    shape_bad = []
    for i, slot in enumerate(slots):
        if slot.head and i and not slots[i - 1].tail_jump:
            shape_bad.append(f"index {slot.index} is a head but the slot before "
                             f"it, 0x{slots[i - 1].address:04X}, is an "
                             f"{slots[i - 1].opcode}")
    for i, slot in enumerate(slots):
        if not slot.head:
            continue
        segment = [slot]
        for slot2 in slots[i + 1:]:
            if slot2.head:
                break
            segment.append(slot2)
        for slot2 in segment[:-1]:
            if slot2.tail_jump:
                shape_bad.append(f"index {slot2.index} is an ljmp but is not the "
                                 f"last slot of the segment starting at "
                                 f"{slot.index}")
        if not segment[-1].tail_jump:
            shape_bad.append(f"the segment starting at index {slot.index} does "
                             f"not end at an ljmp")
    ok = not shape_bad
    for line in shape_bad:
        print(f"        FAIL  {line}")
    print(f"  {'ok  ' if ok else 'FAIL'}  every segment ends at an ljmp and an ljmp "
          f"is only ever a segment's last slot -- so a head may itself be the ljmp "
          f"that ends its own one-slot segment")
    bad += 0 if ok else 1

    hits = transfer_hits(d, {s.address for s in slots})
    ok = not hits
    print(f"  {'ok  ' if ok else 'FAIL'}  an unaligned whole-image scan for "
          f"`12 xx xx` / `02 xx xx` naming any of the run's own addresses finds "
          f"{len(hits)} such address(es) -- not found by this method, not absent")
    bad += 0 if ok else 1

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the bytes")
        return 1
    print("self-test passed: the trampoline's marker window is derived from the "
          "stub's own bytes, each stub names a segment head, and the run "
          "re-decodes from the image")
    return 0


# --- output -------------------------------------------------------------------

def collect(d, pd_verified, callee_depth, max_depth, max_insns):
    """The whole table, as `[Slot]` with the walks and the callee rows filled in."""
    slots, stubs = read_run()
    segments(slots)
    idx = index_of(slots)
    names = committed_names()
    for target, stub_addr in stubs.items():
        if target in idx:
            slots[idx[target]].stub = stub_addr
    for slot in slots:
        slot.name = name_for(names, RUN_REGION, slot.target)
        walk_slot(d, RUN_REGION, slot, pd_verified, callee_depth,
                  max_depth, max_insns)
    return slots


CSV_HEAD = ["index", "address", "opcode", "target", "segment", "head_of_segment",
            "reached_from_stub", "committed_name", "region", "insns", "xdata",
            "callees", "unattributed", "ends", "status", "reach", "window"]

WRITES_HEAD = ["index", "address", "opcode", "target", "segment", "xdata",
               "direction", "page", "host_visible", "status"]

# The two reachability columns' shared value, kept here so the report, the CSVs
# and the write-up cannot quote three different phrasings of one verdict.
REACH_NOTE = ("a slot's transfer is reachable from its segment head; a tail "
              "jumped slot's target returns to the 0x1100 marker's landing, "
              "which is outside the block")


def write_csv(d, pd_verified, callee_depth, max_depth, max_insns, out=sys.stdout):
    w = csv.writer(out)
    w.writerow(CSV_HEAD)
    slots = collect(d, pd_verified, callee_depth, max_depth, max_insns)
    window, _evidence = marker_landing(d)
    settled, _why = reach_settled(d, window, [s.address for s in slots])
    reach = REACH_NOTE if settled else REACH_UNSETTLED
    for slot in slots:
        arm = slot.arm
        # Walked as `write_writes_csv` and `report` both do, rather than with an
        # empty callee list: `slot_status()` reads the callees' cuts as well as
        # the slot's, so passing none reported a slot cut inside a callee as
        # `complete` here while the other two modes of this one tool said
        # `cut`.
        callees = walk_slot(d, RUN_REGION, slot, pd_verified, callee_depth,
                            max_depth, max_insns)
        w.writerow([slot.index, f"0x{slot.address:04X}", slot.opcode,
                    f"0x{slot.target:04X}", slot.segment,
                    "yes" if slot.head else "no",
                    f"0x{slot.stub:04X}" if slot.stub is not None else "",
                    slot.name, RUN_REGION, arm.insns if arm else 0,
                    arm.accesses if arm else "",
                    " ; ".join(f"0x{c:04X}" for c in dict.fromkeys(arm.callees)) if arm else "",
                    arm.unattributed if arm else 0,
                    "; ".join(arm.ends) if arm else "",
                    slot_status(slot, callees), reach,
                    arm.window if arm else ""])
    return 0


def write_writes_csv(d, pd_verified, callee_depth, max_depth, max_insns,
                     out=sys.stdout):
    """Per-slot per-XDATA rows, each carrying the host-window verdict.

    One row per (slot, address) rather than a list in a cell, because the
    question this table answers -- which bytes a capture of the dispatch period
    can actually observe -- is a per-address one, and a list makes a reader
    re-split it by hand to get there.
    """
    w = csv.writer(out)
    w.writerow(WRITES_HEAD)
    for slot in collect(d, pd_verified, callee_depth, max_depth, max_insns):
        callees = walk_slot(d, RUN_REGION, slot, pd_verified, callee_depth,
                            max_depth, max_insns)
        writes = slot_writes(slot, callees)
        status = slot_status(slot, callees)
        for addr in sorted(writes):
            w.writerow([slot.index, f"0x{slot.address:04X}", slot.opcode,
                        f"0x{slot.target:04X}", slot.segment, f"0x{addr:04X}",
                        direction(writes[addr]), host_page(addr),
                        "host-visible" if host_visible(addr) else "not host-visible",
                        status])
    return 0


def report(d, pd_verified, callee_depth, max_depth, max_insns, out=sys.stdout):
    slots, stubs = read_run()
    segments(slots)
    idx = index_of(slots)
    for target, stub_addr in stubs.items():
        if target in idx:
            slots[idx[target]].stub = stub_addr
    window, evidence = marker_landing(d)
    settled, why = reach_settled(d, window, [s.address for s in slots])
    reach = REACH_SETTLED if settled else REACH_UNSETTLED
    # The name lookup belongs here rather than being left to collect(), which
    # this function does not call: without it every row would print `no
    # committed name`, which reads as a fact about the firmware rather than as
    # a lookup that never ran.
    names = committed_names()
    for slot in slots:
        slot.name = name_for(names, RUN_REGION, slot.target)

    print(f"the {RUN} run in bank 0, decoded from {os.path.basename(DEFAULT_FIRMWARE)}")
    print()
    print("The premise the reachability column rests on, from the bytes of the "
          f"0x{SELECT_STUB:04X} stub:")
    print(f"  0x{SELECT_STUB:04X}  {d[SELECT_STUB:SELECT_STUB + SELECT_STUB_LENGTH].hex(' ')}")
    for what, detail in evidence:
        print(f"    {what}: {detail}")
    print(f"    verdict: {why}")
    print(f"  reach: {reach}")
    print()
    print(f"{len(slots)} slots, {len([s for s in slots if s.head])} segments. A "
          "segment is a maximal lcall run ending at an ljmp; a stub's immediate "
          "names a segment head.")
    print()
    for slot in slots:
        marker = " <- stub 0x%04X" % slot.stub if slot.stub is not None else ""
        print(f"  [{slot.index:2d}] 0x{slot.address:04X}  {slot.opcode} "
              f"0x{slot.target:04X}  segment {slot.segment}"
              f"{'  (head)' if slot.head else ''}{marker}")
        print(f"       name: {slot.name}")
        callees = walk_slot(d, RUN_REGION, slot, pd_verified, callee_depth,
                            max_depth, max_insns)
        arm = slot.arm
        if arm:
            print(f"       {arm.insns} insn in {len(arm.blocks)} block(s); "
                  f"writes: {arm.accesses or 'none attributed'}")
            claim = no_claim(slot, callees)
            if claim:
                print(f"       {claim}")
            if arm.unattributed:
                print(f"       {arm.unattributed} movx on a DPTR built at run time "
                      "-- unattributed on purpose")
            if arm.movx_ri:
                print(f"       {arm.movx_ri} movx through a register -- no address")
        writes = slot_writes(slot, callees)
        mine = sorted(a for a, dirs in writes.items() if "w" in dirs)
        visible = [a for a in mine if host_visible(a)]
        invisible = [a for a in mine if not host_visible(a)]
        if mine:
            print(f"       writes per pass, host window "
                  f"(ec_timer_capture.HOST_WINDOW): "
                  f"{' '.join(f'0x{a:04X}' for a in visible) or 'none'} visible; "
                  f"{' '.join(f'0x{a:04X}' for a in invisible) or 'none'} not")
            if not visible:
                print("       this slot's whole write set is outside the host "
                      "window: a capture of the dispatch period cannot observe "
                      "any of it")
        else:
            print("       writes per pass: none attributed by this method")
        if callees:
            for callee, sub, status, _cwrites in callees:
                shown = (" ; ".join(f"0x{a:04X} {direction(dirs)}"
                                    for a, dirs in sorted(sub.xdata.items()))
                         if sub else "")
                print(f"       callee 0x{callee:04X}  [{status}]  "
                      f"{shown or 'no XDATA by this method'}")
        print(f"       status: {slot_status(slot, callees)}")
        print()

    hits = transfer_hits(d, {s.address for s in slots})
    print(f"Whole-image unaligned scan for `12 xx xx` / `02 xx xx` naming any of "
          f"the run's own addresses: {len(hits)} address(es) hit. Not found by "
          "this method, not absent -- the scan is two opcodes over the whole "
          f"{len(d)}-byte image and a hit inside a data table would read as a call.")
    for addr, where in sorted(hits.items()):
        print(f"  0x{addr:04X} named at {', '.join(f'0x{o:05X}' for o in where)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("--self-test", action="store_true",
                    help="check the run, the stub mapping and the marker landing "
                         "against the image, and exit")
    ap.add_argument("--csv", action="store_true",
                    help="one row per slot, with the segment and head flags")
    ap.add_argument("--writes-csv", action="store_true",
                    help="one row per slot per XDATA, with the host-window verdict")
    ap.add_argument("--callee-depth", type=int, choices=(0, 1), default=0,
                    help="1: follow each slot's lcall/ljmp target one level "
                         "(default 0)")
    ap.add_argument("--max-depth", type=int, default=MAX_DEPTH,
                    help=f"nested control transfers to follow per slot (default {MAX_DEPTH})")
    ap.add_argument("--max-insns", type=int, default=MAX_INSNS,
                    help=f"instruction budget per slot (default {MAX_INSNS})")
    args = ap.parse_args()

    if args.self_test:
        return self_test(args.firmware)

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the annotations were written against", file=sys.stderr)
        return 1

    if args.csv:
        return write_csv(d, pd_verified, args.callee_depth, args.max_depth,
                         args.max_insns)
    if args.writes_csv:
        return write_writes_csv(d, pd_verified, args.callee_depth, args.max_depth,
                                args.max_insns)
    return report(d, pd_verified, args.callee_depth, args.max_depth, args.max_insns)


if __name__ == "__main__":
    sys.exit(main())
