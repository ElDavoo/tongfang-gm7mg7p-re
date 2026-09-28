#!/usr/bin/env python3
"""Every writer of the PD image's direct `0x0D`/`0x0E`, every caller of the
`0x1253` pointer add, and what `0x9A71` stores through and leaves behind.

`ec/annotations/pd-index-geometry.md` 2.2 removed `0x9A71` from the index-helper
family and left the seven instructions it tail-calls undecoded beyond showing
them: `0x1253` adds the 16-bit pair in direct `0x0D`/`0x0E` to DPTR, and
`../../docs/findings/pd-direct-offset-pointer-add.md` is the write-up that
settles who fills that pair. This is the measurement it rests on.

The census has to keep two forms apart, and that is the reason it is a separate
file rather than another mode on pd_index_geometry.py. In the 8051 direct space
`0x00`-`0x1F` is the four register banks, so `0x0D` and `0x0E` are R5 and R6
*of bank 1*:

  * A **direct-form** writer -- `75 0D nn`, `F5 0D`, `85 nn 0D` and the rest of
    the opcodes whose destination byte is `0x0D`/`0x0E`, including the
    `8D 0D` (`mov 0x0d,r5`) family that reaches a register *from* one -- always
    means direct `0x0D`/`0x0E`, whatever PSW says. These are the rows
    `--writers` reports.
  * A **register-form** writer -- `7D`, `FD`, `AD`, `0D`, `1D`, `CD`, `DD` and
    the `r6` siblings, the seven opcodes whose destination is Rn -- means direct
    `0x0D`/`0x0E` **only under PSW.RS = 1**. PSW.4/PSW.3 hold RS, so a
    `mov psw,#imm` at a site is a *selection* this tool computes rather than an
    assumption it makes, and `--register-writers` reports the selection beside
    the site. A byte scan finds two orders of magnitude more register-form than
    direct-form candidates over the region, which is why folding the two into
    one grep for `0x0D` would produce an answer nobody could read.

What this cannot do, stated once so no output below has to repeat it:

  * It is not a call graph and not a decoder. Candidates come from a byte scan
    over the region, so the lists over-count -- a `75 0D` inside a data table
    looks exactly like `mov 0x0d,#imm` -- and simultaneously under-count, because
    a call reached through a dispatch table carries no target bytes at all. An
    empty caller list means "not found by this method", never "nothing calls
    it"; the blind spot that forced the 0x07B9 retraction in
    ../../docs/findings.md 4c.
  * **Nothing here observes hardware.** No register is read, written or read
    back, and the *value* `0x0D`/`0x0E` holds when `0x1253` runs is not knowable
    from these bytes. `--base` prints the arithmetic against a candidate the
    census found and names the condition under which it holds; it is not a
    claim that the candidate is what executes.
  * A phantom is **labelled, not filtered**. `converges_from()` says how many
    of the 24 preceding byte offsets a linear walk lands exactly on the site;
    a row scoring 0/24 is printed with that beside it and marked unsyncable,
    because dropping it on a threshold is the failure this tool exists to
    avoid. Read the pair, not either half: a site preceded by a dispatch table
    has no converging anchor and is not thereby misframed.

Every walk is bounded by the pd-image region on both ends, per
../../docs/findings/count-bounded-walk-invariant.md, so a run off the region end
is a named stop rather than a listing of the 0xFF fill past it. The census of
every function that discards that bound is in
../../docs/findings/pd-sites-address-range.md and this tool is not a row in it.

Read-only: it opens the firmware image for reading and writes nothing.

Usage:
    python3 pd_direct_offset_sites.py ../firmware/GMxMGxx_11.800
    python3 pd_direct_offset_sites.py ../firmware/GMxMGxx_11.800 --writers
    python3 pd_direct_offset_sites.py ../firmware/GMxMGxx_11.800 --register-writers
    python3 pd_direct_offset_sites.py ../firmware/GMxMGxx_11.800 --callers
    python3 pd_direct_offset_sites.py ../firmware/GMxMGxx_11.800 --base 0x9B76
    python3 pd_direct_offset_sites.py ../firmware/GMxMGxx_11.800 --csv \
            > ../annotations/pd-direct-offset-sites.csv
    python3 pd_direct_offset_sites.py ../firmware/GMxMGxx_11.800 --check
    python3 pd_direct_offset_sites.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import csv
import io
import os
import sys

from disasm8051 import (OPCODE_LEN, converges_from, decode, mnemonic,
                         paged_target)
from trace_xdata_refs import PD_MARKER, REGIONS, check_table, repo_path

PD_REGION = "pd-image"
# How a row spells its region in the `image` column. `pd` rather than the
# REGIONS name `pd-image`, because ec/annotations/README.md's own vocabulary
# for a scope is `bank0`/`bank1`/`pd`/`common` and a committed table is read
# against that; the two spellings name the same region and the column exists
# only to stop a row reading as a claim about the EC at the same number.
IMAGE_PD = "pd"

# The routine the issue is about: the 16-bit add whose addend lives in direct
# 0x0D/0x0E, and the only one this file names. The CSV, the --callers rows and
# --base all address this one constant, so a reader can tell at a glance which
# routine a row is about.
POINTER_ADD = 0x1253
# The tail-call site inside 0x9A71, and the immediate 0x9A71 loads immediately
# before the tail call. Both are addresses in *this image's* bytes rather than
# anything derived: a derived pair would print a confident wrong one if the
# entry ever moved, which is the one thing a report about the mechanism must
# not do.
STORE_ENTRY, STORE_TAIL = 0x9A71, 0x9A75
STORE_BASE = 0x0003
# The pair, in the order 0x1253 adds it: 0x0E is the low half, 0x0D the high
# half. The order is read off the routine's own body rather than assumed from
# the little-endian spelling of the two addresses.
PAIR_LOW, PAIR_HIGH = 0x0E, 0x0D
# The bank whose R5/R6 sit at direct 0x0D/0x0E, and the PSW whose RS bits name
# it. 0x00-0x07 bank 0, 0x08-0x0F bank 1, 0x10-0x17 bank 2, 0x18-0x1F bank 3,
# so R5 of bank 1 is 0x08 + 5 = 0x0D and R6 is 0x0E.
ALIAS_BANK = 1
BANK_BASE = 0x08
PSW = 0xD0
RS1, RS0 = 0x03, 0x04   # PSW.3 and PSW.4, the two bits that make RS

# Opcodes whose *destination* is the direct byte at raw[1] (raw[2] for the
# direct-to-direct `mov`, whose operand order is source-then-destination), as
# {opcode: index of the destination operand}. Read-modify-write forms are in:
# `inc`/`dec`/`djnz`/`xch` and the ORL/ANL/XRL direct,@A trio all leave a new
# value there, and leaving them out would understate the population in the
# direction this tool exists to avoid.
#
# The `@A,direct` spellings (0x43, 0x53, 0x63) are deliberately absent: they
# read the direct byte and leave the result in A, so a row for one would be a
# reader filed as a writer. Same reason 0xE5 `mov a,direct` and the 0xA8-0xAF
# `mov rN,direct` forms are absent as *direct* writers -- though the `mov rN,
# direct` family is a register-form writer, because under RS = 1 its R5 is the
# very cell 0x0D.
DIRECT_DST = {0x05: 1, 0x15: 1, 0x42: 1, 0x52: 1, 0x62: 1, 0x75: 1,
               0xC2: 1, 0xC5: 1, 0xD0: 1, 0xD5: 1, 0xF5: 1,
               0x85: 2}
DIRECT_DST.update({op: 1 for op in range(0x86, 0x90)})
# Opcodes whose destination is Rn, for the register form. `add a,rN`, `orl a,rN`
# and their siblings are absent: those leave their result in A and read Rn, so
# including them would invert the question this mode asks.
REG_DST = set(range(0x78, 0x80)) | set(range(0xF8, 0x100)) \
    | set(range(0x08, 0x10)) | set(range(0x18, 0x20)) \
    | set(range(0xC8, 0xD0)) | set(range(0xD8, 0xE0)) \
    | set(range(0xA8, 0xB0))
# The two register *numbers* whose bank-1 cells are the pair, and so the only
# two a register-form row can be about. The opcode carries the number in its
# low three bits, so this is what a scan tests; `BANK_BASE + n` is where that
# register's cell sits in bank 1, and the pair's own check in --self-test is
# that the arithmetic comes out at 0x0D/0x0E. Spelled that way so the
# connection between "R5 of bank 1" and "direct 0x0D" is a line of arithmetic
# rather than a coincidence of two literals.
ALIAS_REGS = (5, 6)
# The nearest-preceding-window the two scans below look, and the two scans that
# use it. DPTR_SCAN is pd_inline_arg_sites.py's 32 for the same reason: wide
# enough to reach the load at every site, short enough that a `90 xx xx` in
# unrelated code is unlikely to be taken for one. PSW_SCAN is wider, because a
# bank selection can sit a whole `push`/`pop` bracket away from the site it
# covers, and the gap column is what a reader judges the lookup by.
DPTR_SCAN, PSW_SCAN = 32, 64
# The window and the instruction budget fold_back() uses to find the add that
# feeds the pair's stores. 32 bytes is six to eight instructions, which covers
# every add-then-store shape this image has; the budget is what bounds the
# forward walk once a start has been guessed.
FOLD_BACK_SCAN, FOLD_BACK_MAX_INSNS = 32, 24
# Where a `mov psw,#imm` byte pattern is, as (instruction start, text, RS).
FRAME_BACK = 24

COLUMNS = ["form", "image", "file_offset", "runtime", "opcodes", "immediate",
           "text", "frame_onto", "frame_over", "entry_pick", "note"]

# The `note` vocabulary. Each says what this method found about the row and
# nothing more; "unsyncable" is a framing verdict, never a claim that the bytes
# are data.
FRAMED = "framed by every anchor in range"
PARTIAL = "some anchors miss it; see frame_onto/frame_over"
UNSYNCABLE = "unsyncable: no anchor in range lands on it; may be data or preceded by a dispatch table"
# The rows that say the value cannot be settled here, so a reader is not left
# reading an empty cell as agreement.
NO_PSW = "no PSW write within {n} bytes; bank not found by this scan"
PSW_UNRESOLVED = "nearest PSW write does not fix RS"

DEFAULT_FIRMWARE = "../firmware/GMxMGxx_11.800"
SITES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                         "annotations", "pd-direct-offset-sites.csv")


def pd_verified(d: bytes) -> bool:
    off, magic = PD_MARKER
    return d[off:off + len(magic)] == magic


def pd_bounds():
    lo, hi = next((lo, hi) for name, lo, hi, _, _ in REGIONS if name == PD_REGION)
    return lo, hi


def pd_base(pd_ok: bool) -> int:
    """File offset the PD image's runtime 0x0000 sits at.

    Read off `trace_xdata_refs.REGIONS` rather than written as 0x20000, so the
    two PD tools cannot disagree about where the second program starts, and
    refused on an unverified marker rather than guessed: without the marker the
    region is unidentified and every runtime address below would be somebody
    else's. `pd_inline_arg_sites.pd_base()` is the same guard, kept separate
    because neither tool imports the other."""
    if not pd_ok:
        raise SystemExit("pd region unidentified; see main()")
    lo, base = next((lo, base) for name, lo, _, base, _ in REGIONS
                    if name == PD_REGION)
    return lo - base


def rs_of(psw: int) -> int:
    """The register bank a PSW value selects, from RS1=PSW.3 and RS0=PSW.4.

    Stated rather than inherited: getting these two the wrong way round turns
    every bank in this file upside down, and the two-bit arithmetic is small
    enough to be worth writing out once with its bit numbers beside it.

    This file had them the other way round once. RS0 is the *low-order* bit of
    the two-bit RS field, so it has to sit at the lower bit position: bit 4 is
    RS0 and bit 3 is RS1, and bank is RS1*2 + RS0. Three committed rows already
    said so -- `ghidra-functions.csv`'s `0x0094` and `0x00F0` forwarders and
    `pd-image.md:242` all read `mov psw,#0x10` as selecting bank 1, which is
    what it does. The transposition was in this tool and nowhere else, and
    because the self-test pinned the wrong values it could not catch itself.
    """
    return ((psw >> RS1) & 1) << 1 | ((psw >> RS0) & 1)


def destination_operand(op: int):
    """Index of the direct byte an opcode writes, or None if it writes none."""
    return DIRECT_DST.get(op)


def pair_text(low: int, high: int) -> str:
    """The 16-bit value `0x1253` adds, written the way it adds it."""
    return f"0x{high:02X}{low:02X}"


def resolved_base(low: int, high: int) -> int:
    """What `0x9A71` leaves in DPTR for a given pair, modulo 0x10000.

    The same wrap `pd_index_geometry.py` retains for every address it builds,
    because DPTR is 16 bits wide and a low half of 0xFF carrying into the high
    half is an ordinary event, not an overflow to be reported."""
    return (STORE_BASE + ((high << 8) | low)) & 0xFFFF


def frame_pair(onto: int, over: int) -> str:
    """The `note` a row carries from its framing counts alone."""
    if onto == 0:
        return UNSYNCABLE
    return FRAMED if over == 0 else PARTIAL


def entries(d: bytes) -> set:
    """Every absolute call/jump target in the region, by byte scan.

    A byte scan, and the second of the two ways this tool's rows can be wrong
    in the same direction: a `02 hi lo` inside a data table is
    indistinguishable from an `ljmp`. It is the `entry_pick` column's evidence
    and nothing more, which is why the column is one pick and not a function
    boundary."""
    out = set()
    for i in range(len(d) - 2):
        op = d[i]
        if op in (0x02, 0x12):
            out.add((d[i + 1] << 8) | d[i + 2])
        elif op & 0x1F in (0x01, 0x11):
            out.add(paged_target(op, d[i + 1], i))
    return out


def entry_pick(d: bytes, off: int, targets: set):
    """Nearest preceding call target, as (address, how far back) or (None, None).

    A heuristic and named as one. If a routine is only ever reached by falling
    through, or only through a computed jump, no target precedes it and the row
    reads "not found by this method" rather than a wrong boundary."""
    for back in range(1, off + 1):
        i = off - back
        op = d[i]
        n = OPCODE_LEN[op]
        if i + n > off:
            continue
        if op in (0x02, 0x12):
            tgt = (d[i + 1] << 8) | d[i + 2]
        elif op & 0x1F in (0x01, 0x11):
            tgt = paged_target(op, d[i + 1], i)
        else:
            continue
        if tgt in targets and tgt <= i:
            return tgt, back
    return None, None


def psw_writes(d: bytes, off: int, back: int = PSW_SCAN):
    """Nearest preceding byte pattern that writes PSW, as (distance, text, RS).

    `RS` is None when the write does not fix it -- a `pop psw` and a
    `mov psw,rN` both leave it whatever the stack or the register held, and
    printing a bank for either would be the fabrication this whole mode exists
    to avoid. A missing result is "not found by this scan", never "the bank is
    unchanged"."""
    for dist in range(2, back + 1):
        i = off - dist
        if i < 0:
            break
        op = d[i]
        if op == 0x75 and d[i + 1] == PSW:
            return dist, f"mov  psw,#0x{d[i + 2]:02x}", rs_of(d[i + 2])
        if op in (0xC2, 0xC5, 0xD0, 0xF5) and d[i + 1] == PSW:
            # `clr psw` and `pop psw` both zero or restore the whole byte, so
            # neither has a single value to report; the bank cell is None for
            # both, and only the former is known to be bank 0.
            return dist, f"{mnemonic(d, i, i)}", 0 if op == 0xC2 else None
        if op == 0x85 and d[i + 2] == PSW:
            return dist, f"mov  psw,0x{d[i + 1]:02x}", None
        if 0x86 <= op <= 0x8F and d[i + 1] == PSW:
            return dist, f"{mnemonic(d, i, i)}", None
        if op in (0x42, 0x52, 0x62) and d[i + 1] == PSW:
            return dist, f"{mnemonic(d, i, i)}", None
    return None, None, None


def dptr_before(d: bytes, site: int, back: int = DPTR_SCAN):
    """(the DPTR a caller loaded, how far back), by backward byte scan.

    The same honest description pd_inline_arg_sites.py gives its own
    `dptr_load`: it cannot tell a `mov dptr,#imm16` from the same three bytes
    inside another instruction, so the gap is the reader's evidence and a gap
    of 0 is as strong as a byte pattern gets."""
    for dist in range(3, back + 1):
        o = site - dist
        if o < 0:
            break
        if d[o] == 0x90:
            return (d[o + 1] << 8) | d[o + 2], dist
    return None, None


def decode_row(d: bytes, i: int, runtime: int):
    """(opcodes, immediate, text) for the instruction at region offset `i`.

    The `immediate` column is filled from the `mov direct,#imm` form alone, and
    empty for everything else. That is stricter than it looks: `clr direct` and
    the ORL/ANL/XRL-direct trio also have an operand byte at `raw[1]`, and
    putting it in a column named `immediate` would file a cell address as a
    value. A `mov 0x0d,a` row must acquire no fabricated zero either, which is
    the same rule stated for the other direction."""
    op = d[i]
    n = OPCODE_LEN[op]
    raw = d[i:i + n]
    imm = f"0x{raw[2]:02x}" if op == 0x75 and len(raw) > 2 else ""
    return raw.hex(" "), imm, mnemonic(d, i, runtime)


def direct_sites(d: bytes) -> list:
    """Every direct-form writer of `0x0D`/`0x0E` in the region, in offset order.

    Bank-independent by construction: these opcodes name the direct byte, so no
    PSW reading is consulted and none is reported. That is the whole reason
    they can be a census on their own."""
    out = []
    for i in range(len(d) - 2):
        pos = destination_operand(d[i])
        if pos is None or i + pos >= len(d):
            continue
        if d[i + pos] in (PAIR_HIGH, PAIR_LOW):
            out.append(i)
    return out


def register_sites(d: bytes) -> list:
    """Every register-form writer of R5/R6 in the region, in offset order.

    Two orders of magnitude more candidates than direct_sites() returns, and
    every one of them is conditional on PSW.RS. They are reported with the
    condition and not merged, because a count that mixed them would read as a
    census of the pair's writers and would be one."""
    out = []
    for i in range(len(d)):
        op = d[i]
        if op in REG_DST and (op & 0x07) in ALIAS_REGS:
            out.append(i)
    return out


def caller_sites(d: bytes) -> list:
    """Every `lcall`/`ljmp` of the pointer add, in offset order, kind apart.

    The two are counted and printed apart because a tail call is a different
    idiom from a call that returns, and the plan's `--base` arithmetic is only
    meaningful for the former. The `ljmp` at the store entry is one of them."""
    out = []
    for op, form in ((0x02, "ljmp"), (0x12, "lcall")):
        for i in range(len(d) - 2):
            if d[i] == op and (d[i + 1] << 8 | d[i + 2]) == POINTER_ADD:
                out.append((i, form))
    out.sort()
    return out


def psw_sites(d: bytes) -> list:
    """Every byte pattern in the region that writes PSW, as (offset, text, RS).

    The population `--register-writers` measures its bank column against. RS is
    None for the writes that do not fix it, and the count of those is reported
    rather than dropped, because "the alias holds only under RS = 1, and
    whether any write in this region fixes it" is the finding -- an empty cell
    would not be."""
    out = []
    for i in range(len(d) - 2):
        op = d[i]
        if op == 0x75 and d[i + 1] == PSW:
            out.append((i, f"mov  psw,#0x{d[i + 2]:02x}", rs_of(d[i + 2])))
        elif op in (0xC2, 0xC5, 0xD0, 0xF5) and d[i + 1] == PSW:
            out.append((i, f"{mnemonic(d, i, i)}", 0 if op == 0xC2 else None))
        elif op == 0x85 and d[i + 2] == PSW:
            out.append((i, f"mov  psw,0x{d[i + 1]:02x}", None))
        elif 0x86 <= op <= 0x8F and d[i + 1] == PSW:
            out.append((i, f"{mnemonic(d, i, i)}", None))
        elif op in (0x42, 0x52, 0x62) and d[i + 1] == PSW:
            out.append((i, f"{mnemonic(d, i, i)}", None))
    return out


def rows_for(d: bytes, base: int, targets: set, offs: list, form: str,
             notes=None) -> list:
    """One dict per candidate, keyed by `COLUMNS`.

    `notes` supplies the per-row verdict for the register form, where the
    framing verdict and the PSW verdict are two different things and a reader
    needs both; every other form leaves it to `frame_pair()`."""
    out = []
    for off in offs:
        # The PD region's runtime base is 0x0000 (`trace_xdata_refs.REGIONS`),
        # so a region-relative offset *is* the runtime address; `base` only
        # turns one into a file offset for the `file_offset` column.
        runtime = off
        onto, over = converges_from(d, off, FRAME_BACK)
        pick, gap = entry_pick(d, off, targets)
        opcodes, imm, text = decode_row(d, off, runtime)
        note = (notes or {}).get(off, frame_pair(onto, over))
        out.append({
            "form": form,
            # The region every row below was scanned in, and the reason the
            # column exists: a PD address is not evidence about the EC's XDATA
            # at the same number, and a row that forgot to say so would be read
            # as an EC claim. Constant by construction, not by omission.
            "image": IMAGE_PD,
            "file_offset": f"0x{base + off:05X}",
            "runtime": f"0x{runtime:04X}",
            "opcodes": opcodes,
            "immediate": imm,
            "text": text,
            "frame_onto": onto,
            "frame_over": over,
            "entry_pick": f"0x{pick:04X} (back {gap})" if pick is not None else "",
            "note": note,
        })
    return out


def register_notes(d: bytes) -> dict:
    """Per-offset verdict for the register form: framing *and* the bank.

    Two facts per row, kept as one string because a reader needs them together
    to decide anything: whether the site frames, and what the nearest PSW write
    within `PSW_SCAN` bytes selects. The bank sentence is present in every
    row, including the ones that settle the alias, so a row cannot be quoted
    without the condition it was found under."""
    out = {}
    for off in register_sites(d):
        dist, text, rs = psw_writes(d, off)
        onto, over = converges_from(d, off, FRAME_BACK)
        if rs is None:
            bank = PSW_UNRESOLVED if dist is not None else \
                NO_PSW.format(n=PSW_SCAN)
            if dist is not None:
                bank = f"{bank} (nearest is 0x{off - dist:04X} `{text}`)"
        elif rs == ALIAS_BANK:
            bank = f"nearest PSW write 0x{off - dist:04X} `{text}` selects " \
                   f"bank {rs}: R5/R6 are direct {PAIR_HIGH:02X}/{PAIR_LOW:02X}"
        else:
            bank = f"nearest PSW write 0x{off - dist:04X} `{text}` selects " \
                   f"bank {rs}, not {ALIAS_BANK}"
        out[off] = f"{frame_pair(onto, over)}; {bank}"
    return out


def caller_rows(d: bytes, base: int, targets: set) -> list:
    """One row per `lcall`/`ljmp` of the pointer add, kind named per row."""
    out = []
    for off, form in caller_sites(d):
        row = rows_for(d, base, targets, [off], form)[0]
        out.append(row)
    return out


def census(d: bytes, base: int, targets: set) -> list:
    """Every row the committed table holds, in one order.

    Direct form, then register form, then the calls -- the order the summary
    reads in and the order a reader wants them in, so the table is a census
    rather than three files that happen to share a schema."""
    return (rows_for(d, base, targets, direct_sites(d), "direct")
            + rows_for(d, base, targets, register_sites(d), "register",
                       register_notes(d))
            + caller_rows(d, base, targets))


def csv_table(rows: list) -> str:
    """The `--csv` table, as a string rather than a write.

    A string because `--check` diffs the same bytes this prints and the tool's
    contract is that it writes nothing but stdout."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for row in rows:
        w.writerow([row[c] for c in COLUMNS])
    return buf.getvalue()


def ec_image_counts(dump: bytes) -> dict:
    """The same three populations, in the main EC's three regions.

    Split by `REGIONS` rather than by an offset range spelled here, so the
    numbers are "the EC's own count" and not "whatever lies below 0x20000". The
    caller count is the one the write-up leans on: `0x1253` is a PD address, so
    a zero here is what says the helper belongs to the second program alone
    rather than to a shared runtime.

    Takes the whole dump and not the region slice every other mode here works
    on -- which is the mistake worth naming, because the region is a prefix-free
    offset of the same bytes and slicing it a second time by the EC's file
    offsets silently answers with the PD image's own numbers."""
    out = {}
    for name, rlo, rhi, _, _ in REGIONS:
        if name not in ("common", "bank0", "bank1"):
            continue
        seg = dump[rlo:rhi]
        out[name] = {
            "direct": len(direct_sites(seg)),
            "register": len(register_sites(seg)),
            "callers": len(caller_sites(seg)),
        }
    return out


def print_writers(d: bytes, base: int, targets: set) -> None:
    """The direct-form census, one line per site, framing beside it."""
    rows = rows_for(d, base, targets, direct_sites(d), "direct")
    print(f"Direct-form writers of {PAIR_HIGH:#04x}/{PAIR_LOW:#04x} in the "
          f"{PD_REGION}: {len(rows)} byte-pattern\ncandidate(s) over "
          f"0x0000-0x{len(d) - 1:04X}.  A direct-form writer names the cell, "
          "so it holds whatever\nPSW says; no bank is consulted for these "
          "rows.  `frame_onto/frame_over` is disasm8051's evidence\nthat a "
          "linear walk lands on the site, and the note is that verdict, not a "
          "filter.\n")
    for r in rows:
        imm = f" imm {r['immediate']}" if r["immediate"] else ""
        print(f"  {r['file_offset']}  {r['runtime']}  {r['opcodes']:<9} "
              f"{r['text']:<20}{imm:<10} frame {r['frame_onto']}/"
              f"{r['frame_onto'] + r['frame_over']}  pick {r['entry_pick'] or '-'}")
    if not rows:
        print("  none found by this method over this span")
    print()


def print_register_writers(d: bytes, base: int, targets: set) -> None:
    """The register-form census, and the PSW writes that decide its alias.

    The bank arithmetic is the point of the mode, so it is printed from the
    whole region's PSW population rather than per row: a reader wants to know
    which banks this image ever selects before reading 2,000 rows that are all
    conditional on the same fact."""
    offs = register_sites(d)
    psw = psw_sites(d)
    banks = collections.Counter(rs for _, _, rs in psw)
    # Sorted with the None key left out rather than ordered around: a bank
    # number and a `None` do not compare, and mixing them into one `sorted()`
    # is the sort that would fail here.
    named = ", ".join(f"bank {rs}: {banks[rs]}" for rs in sorted(
        rs for rs in banks if rs is not None)) or "no bank any of them fixes"
    print(f"Register-form writers of R5/R6 in the {PD_REGION}: "
          f"{len(offs)} byte-pattern candidate(s).\nThese mean direct "
          f"{PAIR_HIGH:#04x}/{PAIR_LOW:#04x} only under PSW.RS = "
          f"{ALIAS_BANK}, so none of them is a writer\nuntil the bank at the "
          "site is known.  Both distributions below are over the whole "
          "region.\n")
    print(f"  framing        {frame_distribution(d, offs)}")
    print(f"  PSW writes     {len(psw)} byte-pattern candidate(s) -- "
          f"{named}; RS not fixed: {banks[None]}")
    print(f"  alias bank     {ALIAS_BANK} is selected by "
          f"{banks[ALIAS_BANK]} of them\n")
    print("Every row below is a *candidate* for the pair, not a writer of it. "
          "The `note`\ncolumn carries the framing verdict and the nearest PSW "
          "write; a row whose note says the\nbank is not "
          f"{ALIAS_BANK} cannot alias {PAIR_HIGH:#04x}/{PAIR_LOW:#04x} at "
          "that site.\n")
    shown = [o for o in offs if converges_from(d, o, FRAME_BACK)[0] ==
             FRAME_BACK][:12]
    for off in shown:
        r = rows_for(d, base, targets, [off], "register", register_notes(d))[0]
        print(f"  {r['file_offset']}  {r['runtime']}  {r['opcodes']:<9} "
              f"{r['text']:<20} frame {r['frame_onto']}/"
              f"{r['frame_onto'] + r['frame_over']}")
        print(f"      {r['note']}")
    if len(offs) > len(shown):
        print(f"  ... {len(offs) - len(shown)} more, all of them in "
              f"{repo_path(SITES_CSV)}")
    print()


def frame_distribution(d: bytes, offs: list) -> str:
    """How the candidate offsets score, grouped into three bands.

    Banded rather than a pass rate and rather than a list of every count: the
    two numbers a reader needs are the ones that frame from every anchor and
    the one that no anchor reaches, and the middle is reported as a total so
    the three add to the population. The 0 is named because it is the one a
    filter would have removed."""
    full = partial = none = 0
    for o in offs:
        onto, _ = converges_from(d, o, FRAME_BACK)
        if onto == FRAME_BACK:
            full += 1
        elif onto == 0:
            none += 1
        else:
            partial += 1
    return (f"reached by all {FRAME_BACK} anchors: {full}, by some but not "
            f"all: {partial}, by none: {none}")


def print_callers(d: bytes, base: int, targets: set) -> None:
    """The caller census, `lcall` and `ljmp` counted apart."""
    rows = caller_rows(d, base, targets)
    kinds = collections.Counter(r["form"] for r in rows)
    print(f"Callers of {POINTER_ADD:#06x} in the {PD_REGION}: "
          f"{len(rows)} byte-pattern candidate(s) -- "
          + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) + ".\n"
          "Counted apart because a tail call is a different idiom from one "
          "that returns,\nand the\nstore entry is one of them.  "
          "`frame_onto/frame_over` is the framing evidence; a row scoring\n"
          "less than full is a candidate whose instruction start this method "
          "cannot confirm.\n")
    for r in rows:
        print(f"  {r['file_offset']}  {r['runtime']}  {r['form']:<5} "
              f"frame {r['frame_onto']}/{r['frame_onto'] + r['frame_over']}  "
              f"pick {r['entry_pick'] or '-'}")
    if not rows:
        print("  none found by this method over this span")
    print()


def fold_back(d: bytes) -> dict:
    """The block that rewrites the pair from DPTR, and who reaches it.

    This is what decides between the issue's surviving hypotheses, so it is
    derived rather than asserted. The definition, so a reader can check it:

      1. The *computed* candidates are the direct-form ones whose opcode is
         **not** `mov direct,#imm` -- a literal can be read off the bytes, a
         computed value cannot.
      2. The block's entry is the nearest `mov a,0x0E` at or above `max(0,
         first_computed - FOLD_BACK_SCAN)`. The add is what the stores fold, so
         the entry is the add's own first instruction and not the first store.
      3. The block ends at the last computed candidate a forward
         `disasm8051.decode()` from the entry reaches *on an instruction
         boundary* within `FOLD_BACK_MAX_INSNS`. Bounding the walk is what
         keeps the block contiguous: a fourth computed candidate three
         kilobytes away is a different routine, not the end of this one.
      4. The callers of the entry are counted with the same `12 hi lo`/`02 hi
         lo` byte scan `--callers` uses -- so the count over- and under-counts
         in exactly the way that mode documents and is labelled the same way. It
         is a number of byte-pattern candidates, not a number of executions.

    What comes back is what the block does with the pair, read off the two
    forms it uses: a `mov direct,0x82` takes the low half of DPTR and a
    `mov direct,a` takes whatever A holds, so a block that stores both after
    running the add has folded the add's *result* back into the pair."""
    add = direct_sites(d)
    runtime = [i for i in add if d[i] != 0x75]
    empty = {"entry": None, "sites": [], "stores_dpl": [], "stores_a": [],
             "adds": [], "callers": collections.Counter()}
    if not runtime:
        return empty
    first = runtime[0]
    start = next((i for i in range(first, max(-1, first - FOLD_BACK_SCAN), -1)
                  if d[i] == 0xE5 and d[i + 1] == PAIR_LOW), first)
    reached = {i for i, _, _ in decode(d, start, FOLD_BACK_MAX_INSNS, start)}
    end = max((i for i in runtime if i in reached), default=start)
    block = [i for i in add if start <= i <= end]
    n = OPCODE_LEN[0x12]
    callers = collections.Counter()
    for off in range(len(d) - n + 1):
        if d[off] in (0x02, 0x12) and (d[off + 1] << 8 | d[off + 2]) == start:
            callers["ljmp" if d[off] == 0x02 else "lcall"] += 1
    return {
        "entry": start,
        "sites": block,
        # The two stores that write the pair out of the add's own result.
        "stores_dpl": [i for i in block
                       if d[i] == 0x85 and d[i + 1] == 0x82 and d[i + 2] in
                       (PAIR_HIGH, PAIR_LOW)],
        "stores_a": [i for i in block if d[i] == 0xF5],
        # The add itself, named by its second instruction rather than its
        # first: `mov a,<pair low> ; add a,0x82` is the head of the add, where
        # the bare `mov a,0x0d` on the high half is not -- it is the same read
        # the store-back block and 0x1253 both open with.
        "adds": [i for i in sorted(reached) if d[i] == 0xE5
                 and d[i + 1] == PAIR_LOW and i + 2 < len(d)
                 and d[i + 2] == 0x25 and d[i + 3] == 0x82],
        "callers": callers,
    }


def print_base(d: bytes, base: int, sites: list) -> int:
    """For each named site: the DPTR before it, and the add's arithmetic.

    The pair's value is the missing term and it is *not* resolved here. What is
    printed is the arithmetic against each candidate the census found, with the
    condition that candidate holds under stated beside it, because a resolved
    base is the one thing this file must not imply it has."""
    add = direct_sites(d)
    lit = [i for i in add if d[i] == 0x75]
    print(f"Resolving what {STORE_ENTRY:#06x} leaves in DPTR, for the site(s) "
          f"named.  The routine loads\n`mov dptr,#{STORE_BASE:#06x}` and "
          f"tail-calls {POINTER_ADD:#06x}, which adds the pair's low half "
          f"{PAIR_LOW:#04x} first and its\nhigh half {PAIR_HIGH:#04x} with the "
          f"carry -- so the value added is {PAIR_HIGH:02x}{PAIR_LOW:02x} as "
          f"one 16-bit\nnumber, and the result is that plus "
          f"{STORE_BASE:#06x} modulo 0x10000.\n")
    for addr in sites:
        if not 0 <= addr < len(d):
            print(f"  {addr:#06x} is not a {PD_REGION} runtime address; that "
                  f"region is 0x0000-0x{len(d) - 1:04X} at run time")
            continue
        dptr, gap = dptr_before(d, addr)
        line = (f"  site {addr:#06x} (file 0x{base + addr:05X}): nearest "
                "`mov dptr` "
                + (f"= {dptr:#06x}, {gap} byte(s) back"
                   if dptr is not None else f"not found within {DPTR_SCAN} "
                   "bytes, which is 'not found by this scan'"))
        print(line)
        for i in lit:
            if d[i + 1] != PAIR_HIGH:
                continue
            low_off = next((j for j in add
                            if d[j] == 0x75 and d[j + 1] == PAIR_LOW), None)
            if low_off is None:
                continue
            low, high = d[low_off + 2], d[i + 2]
            print(f"      candidate: {pair_text(low, high)}, from the literal "
                  f"pair at 0x{i:04X} and 0x{low_off:04X}")
            print(f"        {STORE_BASE:#06x} + {pair_text(low, high)} = "
                  f"{resolved_base(low, high):#06x}")
            print("        under the condition that no other site has "
                  "written the pair since those two\n        loads ran; "
                  "nothing in these bytes says whether one has, so\n        "
                  "this is a candidate and not the value")
    if not lit:
        print("      no direct-form literal load of the pair is found by this "
              "method,\n      so the arithmetic above has no candidate to run "
              "against")
    fb = fold_back(d)
    if fb["entry"] is None:
        print("\nNo direct-form candidate stores a *computed* value into the "
              "pair, so the\nliteral above is the only writer this method "
              "finds and the pair is fixed at\ninit as far as these bytes go.")
        return 0
    kinds = ", ".join(f"{k} {v}" for k, v in sorted(fb["callers"].items()))
    outside = [i for i in direct_sites(d) if i not in fb["sites"]
               and d[i] != 0x75]
    dead = sum(1 for i in outside
               if converges_from(d, i, FRAME_BACK)[0] == 0)
    full = sum(1 for i in outside
               if converges_from(d, i, FRAME_BACK)[0] == FRAME_BACK)
    print(f"\nWhether that literal still holds when {POINTER_ADD:#06x} runs "
          f"is the other half, and it is a\nseparate question from the "
          f"arithmetic above.  The direct-form candidates\ndivide into "
          f"{len(lit)} literal load(s) and {len(direct_sites(d)) - len(lit)} "
          f"store(s) of a computed value.  The\n"
          + (f"{len(fb['sites'])} of those computed stores sit in one block, "
             f"{fb['entry']:#06x}-0x{fb['sites'][-1]:04X}, and the other "
             f"{len(outside)}\ndo not: no anchor in range walks onto "
             f"{dead} of those and only {full} onto every one, so\nthe "
             "block is where the framing evidence is and they are where it "
             "is not.\n" if outside else
             f"{len(fb['sites'])} of those computed stores sit in one block, "
             f"{fb['entry']:#06x}-0x{fb['sites'][-1]:04X}.\n"))
    print("  it runs the add at "
          + ", ".join(f"0x{a:04X}" for a in fb["adds"])
          + ", then stores the low half out of DPTR at "
          + ", ".join(f"0x{s:04X}" for s in fb["stores_dpl"])
          + " and the high half out of A at "
          + ", ".join(f"0x{s:04X}" for s in fb["stores_a"]))
    print(f"  so the block folds the add's own result back into the pair: it "
          f"rewrites the\n  value, it does not just read it.  "
          f"{fb['entry']:#06x} is called {kinds} -- {sum(fb['callers'].values())} "
          f"byte-pattern candidate(s),\n  counted the way "
          f"`--callers` counts and over- and under-counting the same way.\n")
    print("  Which is the answer to the issue's three-way question, at the "
          "strength the bytes\n  support: **not a fixed relocation constant, "
          "and not a per-call scratch pointer.** It is\n  a running 16-bit "
          "base in internal RAM -- a literal at init, then advanced by every\n  "
          "execution of the block above.  The register-bank hypothesis is the "
          "third option and\n  `--register-writers` is where it is tested; it "
          "does not survive there either.")
    return 0


def summary(dump: bytes, d: bytes, base: int, targets: set) -> int:
    """The default view: the shape of each population and where the table is."""
    direct, register = direct_sites(d), register_sites(d)
    rows = caller_rows(d, base, targets)
    ec = ec_image_counts(dump)
    print(f"{POINTER_ADD:#06x} adds the 16-bit pair in direct "
          f"{PAIR_HIGH:#04x}/{PAIR_LOW:#04x} to DPTR.  Over the "
          f"{PD_REGION} region\n0x0000-0x{len(d) - 1:04X}, by byte scan:\n")
    print(f"  direct-form writers    {len(direct):>5}  bank-independent; "
          "each names the cell")
    print(f"  register-form writers  {len(register):>5}  conditional on "
          f"PSW.RS = {ALIAS_BANK}")
    print(f"  lcall/ljmp callers     {len(rows):>5}  "
          + ", ".join(f"{k} {v}" for k, v in
                      sorted(collections.Counter(r['form'] for r in rows).items())))
    print("\nThe same three scans over the main EC, which is a different "
          "program with its\nown direct space -- so these numbers are not "
          "the PD image's and are not a\nextension of them:\n")
    for name, c in ec.items():
        print(f"  {name:<8} direct {c['direct']:>3}   register "
              f"{c['register']:>5}   callers {c['callers']:>3}")
    print(f"\n{repo_path(SITES_CSV)} holds one row per candidate above, with "
          "its framing counts\nand its note.  `--writers`, `--register-writers` "
          "and `--callers` print the three\ncensuses; `--base` runs the "
          "arithmetic `0x9A71` performs for a named site; and the\nwrite-up "
          "is ../../docs/findings/pd-direct-offset-pointer-add.md.")
    return 0


# --- self-test -------------------------------------------------------------
#
# Every expectation below is a number this repository already commits to, or a
# byte run transcribed from an `r2 -a 8051` listing, so the tool cannot drift
# from the prose that cites it without a red run here.

# The two decodes the write-up quotes, byte for byte, as
# `r2 -a 8051 -e scr.color=0 -q -c 's ADDR; pd N' /tmp/pd.bin` prints them with
# the trailing memory-hint column stripped, which is the same transcription
# ec/annotations/pd-index-geometry.md 2.2 already carries. The address add is
# the routine the whole tool is named for, and the second is the store entry
# whose returned DPTR is the open question.
R2_DECODES = (
    (POINTER_ADD, 7, (("mov  a,0x0e", "add  a,0x82", "mov  0x82,a",
                       "mov  a,0x0d", "addc a,0x83", "mov  0x83,a",
                       "ret"),)),
    (STORE_ENTRY, 3, (("movx @dptr,a", "mov  dptr,#0x0003", "ljmp 0x1253"),)),
    (0x0514, 2, (("mov  0x0d,#0x27", "mov  0x0e,#0xff"),)),
    (0x009E, 4, (("mov  0xd0,#0x10", "mov  dptr,#0x0154", "lcall 0x0050",
                 "pop  0xd0"),)),
)

# The populations the write-up's counts rest on, pinned so a decoder change
# that re-framed a site -- or a scan that quietly widened -- is a red run here
# rather than a revised paragraph. The register form is the one a reader is most
# likely to doubt, because it is the one whose meaning depends on PSW.
DIRECT_TOTAL, REGISTER_TOTAL = 11, 2572
CALLER_TOTALS = {"lcall": 30, "ljmp": 3}
# The two PSW writes that name a bank, and what they name. RS0 is PSW.4 and
# RS1 is PSW.3, so #0x10 sets RS0 and not RS1 -- bank 1, where R5 is 0x0D. That
# is the aliasing bank, which is why the two sites are the ones the whole
# register mode turns on. Pinning the *selected bank* rather than the
# immediate is what stops that slip from reaching the write-up; it is also what
# would have caught the transposition, had the pin been written from the 8051
# map rather than from this file's own arithmetic.
PSW_BANKS = {0x009E: 1, 0x00FA: 1, 0x0060: 0, 0x00BC: 0, 0x0118: 0}
# The site the write-up's `0x9A71` verdict rests on: `0x9DFE lcall 0x9a71` and
# the read of the returned DPTR on the very next instruction. This is the one
# place the returned pointer is shown to be consumed, and it is pinned as
# bytes rather than as prose so the claim cannot outlive them.
STORE_CALLER_RT, STORE_CONSUMER = 0x9DFE, 0x9E01
EXPECTED_STORE_CONSUMER = "movx a,@dptr"
# The arithmetic `0x9A71` performs, against the literal pair the init loads.
# 0x0003 + 0x27FF = 0x2802, and the sum carries because 0x03 + 0xFF overflows
# the low half -- which is the reason the routine is written as an add and not
# an or.
LITERAL_PAIR = (0xFF, 0x27)
EXPECTED_RESOLVED = 0x2802


def self_test(fw_path: str) -> int:
    from disasm8051 import decode
    d = open(fw_path, "rb").read()
    if not pd_verified(d):
        print("note: no ITE8850-PD marker; the region is unidentified, so "
              "there is nothing to check", file=sys.stderr)
        return 1
    lo, hi = pd_bounds()
    base = pd_base(True)
    region = d[lo:hi]
    targets = entries(region)
    bad = 0

    def check(ok, what):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else '!  '} {what}")

    print("Self-test: the decodes transcribed from `r2 -a 8051`")
    for addr, n, (expected,) in R2_DECODES:
        # `mnemonic` pads the mnemonic to four columns and r2 does not, so both
        # sides are compared with the padding collapsed. That is the only
        # reason a transcription taken from one and a decode produced by the
        # other can be equal, and it is why the transcriptions below are
        # written unpadded.
        got = [" ".join(text.split()) for _, _, text
               in decode(region, addr, n, addr)]
        want = [" ".join(t.split()) for t in expected]
        check(got == want, f"0x{addr:04X} decodes to {' / '.join(want)} "
                           f"(got {' / '.join(got)})")

    print("\nSelf-test: the populations, over the region and nothing else")
    direct, register = direct_sites(region), register_sites(region)
    check(len(direct) == DIRECT_TOTAL,
          f"{len(direct)} direct-form writer candidate(s) "
          f"(expected {DIRECT_TOTAL})")
    check(len(register) == REGISTER_TOTAL,
          f"{len(register)} register-form writer candidate(s) "
          f"(expected {REGISTER_TOTAL})")
    kinds = collections.Counter(form for _, form in caller_sites(region))
    check(dict(kinds) == CALLER_TOTALS,
          f"callers of {POINTER_ADD:#06x}: {dict(kinds)} (expected "
          f"{CALLER_TOTALS})")
    check(len([o for o in register if converges_from(region, o, FRAME_BACK)[0]
               == FRAME_BACK]) == 1251,
          "1251 register-form candidate(s) frame from every anchor in range")
    check(sum(1 for o in direct if converges_from(region, o, FRAME_BACK)[0]
              == FRAME_BACK) == 7,
          "7 of the direct-form candidates frame from every anchor in range; "
          "the other four are labelled, not dropped")

    print("\nSelf-test: the bank arithmetic, which the whole register mode "
          "rests on")
    check(rs_of(0x10) == 1 and rs_of(0x00) == 0 and rs_of(0x08) == 2,
          "rs_of(): RS0=PSW.4 and RS1=PSW.3 -- #0x10 is bank 1, #0x00 "
          "bank 0, #0x08 bank 2")
    check(BANK_BASE + 5 == PAIR_HIGH and BANK_BASE + 6 == PAIR_LOW,
          f"bank-{ALIAS_BANK} R5/R6 sit at direct {PAIR_HIGH:#04x}/"
          f"{PAIR_LOW:#04x}")
    for off, want in PSW_BANKS.items():
        got = next((rs for i, _, rs in psw_sites(region) if i == off), None)
        check(got == want,
              f"the `mov psw` at 0x{off:04X} selects bank {want} "
              f"(got {got})")
    aliased = sorted(i for i, _, rs in psw_sites(region) if rs == ALIAS_BANK)
    want_aliased = sorted(off for off, bank in PSW_BANKS.items()
                          if bank == ALIAS_BANK)
    check(aliased == want_aliased,
          f"the PSW writes selecting the aliasing bank {ALIAS_BANK} are "
          f"exactly {['0x%04X' % i for i in want_aliased]} (got "
          f"{['0x%04X' % i for i in aliased]}) -- so a register-form\n"
          f"      candidate running in that bank reads "
          f"{PAIR_HIGH:#04x}/{PAIR_LOW:#04x}, and its bank is what decides "
          f"whether it aliases")

    print("\nSelf-test: what the store entry leaves in DPTR")
    check(d[lo + STORE_TAIL] == 0x02 and
          (d[lo + STORE_TAIL + 1] << 8 | d[lo + STORE_TAIL + 2]) == POINTER_ADD,
          f"0x{STORE_TAIL:04X} is the `ljmp {POINTER_ADD:#06x}` the store "
          f"entry tail-calls")
    low, high = LITERAL_PAIR
    check(resolved_base(low, high) == EXPECTED_RESOLVED,
          f"{STORE_BASE:#06x} + {pair_text(low, high)} = "
          f"{resolved_base(low, high):#06x}")
    check(resolved_base(0xFF, 0xFF) == 0x0002,
          "the add wraps modulo 0x10000 rather than reporting an overflow")
    tail = region[STORE_CALLER_RT:STORE_CALLER_RT + 3]
    check(tail == bytes([0x12, STORE_ENTRY >> 8, STORE_ENTRY & 0xFF]),
          f"0x{STORE_CALLER_RT:04X} is the `lcall {STORE_ENTRY:#06x}` the "
          f"0x9DEC site ends its store with (got `{tail.hex(' ')}`)")
    got = next((text for i, _, text in
                decode(region, STORE_CONSUMER, 1, STORE_CONSUMER)), "")
    check(got.strip() == EXPECTED_STORE_CONSUMER,
          f"0x{STORE_CONSUMER:04X} is `{EXPECTED_STORE_CONSUMER}`, so the "
          f"returned DPTR is read\n      on the instruction after the call "
          f"(got `{got.strip()}`)")

    print("\nSelf-test: the committed table")
    rows = census(region, base, targets)
    check(sorted(set(r["form"] for r in rows)) ==
          ["direct", "lcall", "ljmp", "register"],
          "the census carries all four row forms")
    check(len(rows) == DIRECT_TOTAL + REGISTER_TOTAL +
          sum(CALLER_TOTALS.values()),
          f"{len(rows)} row(s) in the census, one per candidate")
    check(all(r["image"] == IMAGE_PD for r in rows),
          "every row names the region it was scanned in, so no row reads as an "
          "EC claim")
    print(f"\n  {repo_path(SITES_CSV)}: {len(rows)} row(s) + header")
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the committed "
              f"decodes and counts")
    else:
        print("self-test passed: the decodes match the `r2 -a 8051` "
              "transcriptions, the three\npopulations hold, the aliasing "
              "bank is selected by exactly the two PSW writes\nnamed above, "
              "and the store entry's returned DPTR is read on the next "
              "instruction")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=None,
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--writers", action="store_true",
                    help="every direct-form writer of 0x0D/0x0E, with framing")
    ap.add_argument("--register-writers", action="store_true",
                    help="every register-form writer of R5/R6, each row "
                         "stating the PSW condition its alias needs")
    ap.add_argument("--callers", action="store_true",
                    help="every lcall/ljmp of the pointer add, counted apart")
    ap.add_argument("--base", nargs="+", metavar="SITE",
                    help="run the store entry's DPTR arithmetic for a "
                         "PD runtime site")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout instead "
                         "of the summary")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="diff this run against the committed table and exit "
                         f"non-zero on any difference (default: "
                         f"{repo_path(SITES_CSV)})")
    ap.add_argument("--self-test", action="store_true",
                    help="check the decodes and the populations against the "
                         "committed transcripts and counts")
    args = ap.parse_args()

    if args.self_test:
        here = os.path.dirname(os.path.abspath(__file__))
        return self_test(args.firmware or os.path.join(here, DEFAULT_FIRMWARE))

    if not args.firmware:
        ap.error("give a firmware image, or --self-test")

    d = open(args.firmware, "rb").read()
    if not pd_verified(d):
        # stderr, so `--csv` redirected to a file stays a clean CSV, and
        # non-zero: without the marker the region is unidentified, so every
        # runtime address below would be somebody else's.
        off, magic = PD_MARKER
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "the pd region is unidentified, so this tool has no population "
              "to census\n", file=sys.stderr)
        return 1

    base = pd_base(True)
    lo, hi = pd_bounds()
    region = d[lo:hi]
    targets = entries(region)

    if args.check is not None or args.csv:
        generated = csv_table(census(region, base, targets))
        if args.check is not None:
            return check_table(generated, args.check)
        sys.stdout.write(generated)
        return 0

    if args.writers:
        print_writers(region, base, targets)
        return 0
    if args.register_writers:
        print_register_writers(region, base, targets)
        return 0
    if args.callers:
        print_callers(region, base, targets)
        return 0
    if args.base:
        try:
            return print_base(region, base, [int(a, 16) for a in args.base])
        except ValueError as exc:
            ap.error(str(exc))
    return summary(d, region, base, targets)


if __name__ == "__main__":
    sys.exit(main())
