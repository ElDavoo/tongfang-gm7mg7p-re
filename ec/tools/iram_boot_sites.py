#!/usr/bin/env python3
"""The internal-RAM bytes in the boot path's `0x20`-`0xBF` clear, and the sites that name them.

**Why this survey exists, and why it is not the tool it looks like.** The issue
that asked for it (`docs/findings/reset-memory-lifetime.md`) also claimed no
tool surveys direct-byte operands in this address space. That is wrong about the
tool and right about the answer: `intmem_refs.py` *is* that tool, and its
`OPCODE_TABLE` covers the direct-addressing forms only. The internal-RAM
operands of the boot path's own IRAM loop are not direct-addressed at all --
`common 0x0F75` reaches `0x20`-`0xBF` through `mov @R0,A` at `0x0F91`, whose
pointer is a register. So the gap is a **method**: `@Ri` register-indirect
addressing, where the address is in a register rather than in the operand byte.
This tool adds that form beside the delegated one instead of re-listing the
direct opcodes.

**Three populations, and the third is why the first two can be trusted.**
Every `@Ri` site in the image is in exactly one of them:

  * `direct`         -- a site from `intmem_refs.OPCODE_TABLE`, so the address
    is the operand byte. Delegated, not re-listed: `intmem_refs.scan()` is the
    same measurement every committed direct-byte table in the tree is made of.
  * `ri`             -- an `@Ri` site whose register was loaded by a `mov
    Rn,#imm` **immediately before it**. The address is that immediate.
  * `ri-unresolved`  -- an `@Ri` site with no such load. Its address is not
    established by this method, and the row says so in the `addr` cell rather
    than carrying a guess.

The third population is not padding. It is what a pointer loaded three
instructions earlier looks like, and **the boot path's own IRAM clear is in
it**: at `0x0F91` the pointer is R0, and R0 got its value from the `xch a,R0`
pair at `0x0F8D`/`0x0F8F` driven by R7 -- not from a load this method follows.
So the range this tool is named for is established by *executing* `0x0F75`
(`boot_xdata_sites.py`) and by that routine's own annotation name, **not** by
scanning for the bytes it writes. A table carrying only the resolved rows would
let a reader conclude the boot path names the four bytes of `0x20`-`0xBF` that
`0x0070` and `0x110A` direct-name and does nothing to the rest of the range,
which is the opposite of what the bytes say.

**A site is labelled, never filtered.** Two labels ride on every row and
neither is a verdict:

  * `frame` is `disasm8051.converges_from`'s onto/over pair -- evidence about
    framing, not proof, and `intmem_refs.py`'s own header says to read the pair
    and not either half. The unframed byte scan that produces these rows cannot
    tell a misframed read from a real one, and a run of repeated single-byte
    values walks through cleanly (`intmem_refs.py`'s SELF_TEST pins `24/0` at
    one such site). Not filtered on: dropping the low-scoring rows would make a
    future run's zero look like absence.
  * `in_data_region` is the LABEL `annotations/data-regions.yaml` gives the
    offset. `not listed` means "no listed region contains this offset", never
    "there is nothing there".

**Not found by this method, never absent.** Indirect access the pairing does
not follow, a computed pointer, and every `@Ri` site whose register is loaded
further back than one instruction are invisible here. A zero is "this scan
found no encoding of the byte in these forms", never "the byte is untouched".
That is the caveat `intmem_refs.py` opens with, and this tool inherits it rather
than restating it as a new claim.

**Nothing here was observed on hardware.** Every row is a static byte scan of
`ec/firmware/GMxMGxx_11.800`. No EC was powered and no internal-RAM byte was
read back.

`--csv` writes `../annotations/iram-boot-sites.csv`; `--check` diffs against it
byte for byte through `trace_xdata_refs.check_table()`. `--self-test` holds known
answers transcribed from oracles outside this file -- the `0x0162`/`0x0164` and
`0x017E` pairs in `../decompiled/common/012F.asm`, the `0x0F91` store in
`../decompiled/common/0F75.asm` -- and then the refusals, each a buffer that
would yield a short plausible table if its guard were removed.

**Not in `.github/scripts/agent-gates.sh`, and cannot be from an agent branch.**
The plan-stage push token has no `workflow` scope, so a branch touching that
script fails at the end rather than the start; `docs/findings/` carries the
reason at greater length. Both modes are runnable from the repo root with no
arguments but this file's path.

Usage:
    python3 iram_boot_sites.py ../firmware/GMxMGxx_11.800
    python3 iram_boot_sites.py ../firmware/GMxMGxx_11.800 0x84 0xAA
    python3 iram_boot_sites.py --csv > ../annotations/iram-boot-sites.csv
    python3 iram_boot_sites.py --csv --check
    python3 iram_boot_sites.py --self-test
"""
import argparse
import collections
import csv
import io
import os
import sys

from data_regions import load as load_data_regions, region_at
from disasm8051 import converges_from
from intmem_refs import (OPCODE_TABLE, TEMPLATES, pd_verified,
                          scan as scan_direct)
from trace_xdata_refs import check_table, region_of, runtime_addr

HERE = os.path.dirname(os.path.abspath(__file__))
ANNOT = os.path.join(HERE, os.pardir, "annotations")
SITES_CSV = os.path.join(ANNOT, "iram-boot-sites.csv")
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")

# The range the boot path's IRAM loop clears: `common 0x0F75`'s second loop
# runs R7 from 0x20 up to 0xBF and zeroes through `mov @R0,A`, bounded by the
# `subb A,#0xC0` at 0x0F89. It is the range this tool is *about* -- the question
# being asked -- and not a filter on what the scans look at: both run over the
# whole image, so "no site anywhere" and "no site in the range" stay the same
# statement and a byte outside it is never dropped for being outside.
BOOT_IRAM = (0x20, 0xBF)

# (opcode, register index, direction, mnemonic template, operand byte count)
# for every opcode that reaches an internal-RAM byte **through a pointer
# register**.
#
# `intmem_refs.OPCODE_TABLE` covers the direct-addressing forms and this table
# must not overlap it: the same two bytes read as a direct operand and as an
# `@Ri` opcode name different bytes, which is the latent hole
# `disasm8051.py`'s TEXTBOOK_BIT_SITES pair exists to catch. `--self-test`
# asserts the disjointness rather than trusting it.
#
# `mov Rn,#imm` (0x78-0x7F) is the *load* half and is handled by
# `load_sites()`; on its own it names no byte, so a row for it would be a
# reference to something nobody reads.
#
# Deliberately absent, and each for a stated reason:
#   0xE2/0xE3 `movx a,@Ri` and 0xF2/0xF3 `movx @Ri,A` -- these are XDATA, in a
#     different address space. In this dump `movx @Ri` is how the ITE8850-PD
#     image reaches its own external RAM, and counting those as internal-RAM
#     byte references is the mistake `intmem_refs.py`'s header records for
#     `0x90`: `90 05 44` is a real instruction naming XDATA 0x0544, not an
#     `inc 0x44`. `--self-test` asserts these four stay out.
#   0x90 `mov dptr,#imm16`, and every other direct form -- `intmem_refs`' half.
RI_TABLE = (
    (0x76, 0, "write", "mov  @R0,#0x%02x", 1),
    (0x77, 1, "write", "mov  @R1,#0x%02x", 1),
    (0x86, 0, "read", "mov  0x%02x,@R0", 1),
    (0x87, 1, "read", "mov  0x%02x,@R1", 1),
    (0xA6, 0, "write", "mov  @R0,0x%02x", 1),
    (0xA7, 1, "write", "mov  @R1,0x%02x", 1),
    (0xC6, 0, "rmw", "xch  A,@R0", 0),
    (0xC7, 1, "rmw", "xch  A,@R1", 0),
    (0xD6, 0, "rmw", "xchd A,@R0", 0),
    (0xD7, 1, "rmw", "xchd A,@R1", 0),
    (0xE6, 0, "read", "mov  A,@R0", 0),
    (0xE7, 1, "read", "mov  A,@R1", 0),
    (0xF6, 0, "write", "mov  @R0,A", 0),
    (0xF7, 1, "write", "mov  @R1,A", 0),
)

# The same rows keyed by opcode, so the scanner and the renderer read one table
# rather than two that can disagree.
RI_BY_OPCODE = {op: (reg, direction, text, operands)
                for op, reg, direction, text, operands in RI_TABLE}

# The opcodes that load a pointer register, as a range test. `disasm8051`
# groups the same two arms, so the pairing follows the encoder's grouping rather
# than restating four opcodes as eight.
MOV_RN_IMM = range(0x78, 0x80)

# `ri-unresolved` rows have no address, and the cell says so rather than
# carrying a zero that would read as "byte 0x00".
UNRESOLVED = "unresolved"

CAVEAT = (
    "Direct internal-RAM byte census over 0x20-0xBF, in two forms: the\n"
    "direct-addressing opcodes (intmem_refs.OPCODE_TABLE, delegated) and the\n"
    "@Ri register-indirect pairing (mov Rn,#imm immediately followed by an @Ri\n"
    "instruction naming the same register). Unframed byte scan: a hit may be a\n"
    "misframed read, a table entry, or data. 'frame' is converges_from's\n"
    "onto/over pair -- evidence about framing, not proof; read the pair, not\n"
    "either half. 'in_data_region' is a LABEL from data-regions.yaml, never a\n"
    "filter. A row whose form is ri-unresolved is an @Ri site whose address\n"
    "this method does not establish; the boot path's own IRAM clear is one of\n"
    "them, which is why the range is taken from executing 0x0F75 rather than\n"
    "from scanning for the bytes it writes.\n"
    "Indirect access is invisible here. A zero means 'not found by this\n"
    "method', never 'absent' or 'private'. setb/clr/cpl/mov on 0xd2/0xb2/0xc1/\n"
    "0x92/0xa2 name a BIT address and are not counted as byte writes.\n"
)

CSV_COLUMNS = ["addr", "form", "file_offset", "region", "runtime",
               "frame_onto", "frame_over", "access", "text", "in_data_region"]


class Refusal(Exception):
    """A run this tool declines to finish, carrying the reason it names.

    Every way this can stop is the same shape of failure -- a table one row
    shorter than the truth, in a column that looks like an answer. A scan window
    that runs off the end of the buffer is the case: the last candidate in a
    fixture drops silently and the result reads as a complete census of a
    shorter image.
    """


def _operand(data: bytes, off: int, n: int) -> int:
    """The `n`-th operand byte of the instruction at `off`, bounds-checked.

    A refusal rather than an `IndexError`: the caller is about to report a
    table, and a truncated instruction is exactly the case where that table
    would be short by an unknown amount.
    """
    if off + n >= len(data):
        raise Refusal(
            f"the instruction at 0x{off:05X} runs off the end of a "
            f"{len(data)}-byte buffer; the scan window is incomplete, so the "
            "row it would have produced is not reported")
    return data[off + n]


def ri_sites(data: bytes) -> list:
    """Every `@Ri` site in the image, as (offset, opcode, reg, direction,
    text, operand count).

    The full population, in image order, with no pairing applied: the caller
    decides which of these are resolved. Reading it this way is what makes the
    three populations a **partition** rather than three scans that happen to
    agree -- a site nobody paired with is still a site, and dropping it is how a
    byte's row set would quietly come to read as complete.
    """
    out = []
    for off in range(len(data)):
        entry = RI_BY_OPCODE.get(data[off])
        if entry is None:
            continue
        reg, direction, text, operands = entry
        out.append((off, data[off], reg, direction, text, operands))
    return out


def load_sites(data: bytes) -> dict:
    """{offset: (register, immediate)} for every `mov Rn,#imm` in the image.

    Built as its own pass rather than found on demand, because the pairing only
    ever looks at the instruction two bytes back: a `mov Rn,#imm` sitting in the
    buffer's last byte would otherwise never be examined at all, and the pairing
    would report a census of a slightly shorter image without saying so. Building
    the index over the whole buffer is what puts that load in front of the
    bounds check instead of behind the pairing's reach.
    """
    out = {}
    for off in range(len(data)):
        if data[off] not in MOV_RN_IMM:
            continue
        out[off] = (data[off] - 0x78, _operand(data, off, 1))
    return out


def pair_sites(sites: list, loads: dict) -> dict:
    """{offset of the @Ri site: (load offset, address)} for the resolved pairs.

    **The pairing is adjacency, and adjacency is the whole soundness argument.**
    `mov Rn,#imm` is two bytes and the `@Ri` instruction that consumes it must
    start at the next byte, so nothing can sit between them and clobber Rn.
    That is what makes the address in the row established rather than plausible.

    Widening the window to "the last `mov Rn,#imm` before this site" would
    recover more rows and every one of them would be a guess: a register
    reloaded in between carries a different address, and nothing at the `@Ri`
    site tells the two apart. So the window stays one instruction, and what that
    costs -- every pointer built by arithmetic, and the seven parameterised
    clear helpers `../annotations/xdata-0440-readers.md` §7.5 names -- is stated
    rather than absorbed.
    """
    paired = {}
    for off, _opcode, reg, _direction, _text, _operands in sites:
        entry = loads.get(off - 2)
        if entry is None or entry[0] != reg:
            continue
        paired[off] = (off - 2, entry[1])
    return paired


def direct_text(opcode: int, addr: int) -> str:
    """`intmem_refs`' mnemonic template for `opcode`, with `addr` substituted.

    The `0xA5` row is the reason this is a function. `intmem_refs.OPCODE_TABLE`
    carries the reserved opcode with the mnemonic `reserved -- never an
    instruction`, which names no address and therefore has no `%02x` to fill --
    so `% addr` on it raises rather than rendering. Substituting only when the
    template carries a placeholder keeps every `0xA5` pair in the table, which
    `intmem_refs.scan()`'s own docstring requires of it -- "including the
    `0xa5` reserved opcode" -- and which its SELF_TEST's closed-list assertion
    depends on.
    """
    text = TEMPLATES[opcode]
    return text % addr if "%" in text else text


def _label(regions, off: int) -> str:
    """The `data-regions.yaml` label for `off`, or `not listed`.

    `not listed` is the honest spelling for "no listed region contains this
    offset". It is deliberately not an empty cell and not `none`, either of which
    a reader could take for an absence the file asserts.
    """
    region = region_at(regions, off)
    return region["name"] if region else "not listed"


def _runtime(off: int, verified: bool) -> str:
    """`runtime_addr()` rendered, or `unmapped` where the bytes have none.

    `unmapped` rather than an empty cell: the region column already says
    `erased` or `unknown` for those offsets, and a blank here would read as a
    runtime address of nothing rather than as one this table cannot name.
    """
    rt = runtime_addr(off, verified)
    return f"0x{rt:04X}" if rt is not None else "unmapped"


def build_rows(data: bytes, verified: bool, regions) -> list:
    """The `--csv` rows: one per site, across all three populations.

    Sorted with the direct rows first, then the resolved `@Ri` rows grouped by
    the byte they name, then the unresolved block as its own run -- so a reader
    asking "what touches 0x84" reads those together and a reader asking "what
    did this method fail to resolve" reads the rest without filtering anything
    out of the file to find it.
    """
    lo, hi = BOOT_IRAM
    rows = []

    for addr, sites in scan_direct(data, range(lo, hi + 1), verified).items():
        for off, opcode, direction, (onto, over) in sites:
            rows.append({
                "addr": f"0x{addr:02x}",
                "form": "direct",
                "file_offset": f"0x{off:05X}",
                "region": region_of(off, verified)[0],
                "runtime": _runtime(off, verified),
                "frame_onto": onto,
                "frame_over": over,
                "access": direction,
                "text": direct_text(opcode, addr),
                "in_data_region": _label(regions, off),
            })

    sites = ri_sites(data)
    paired = pair_sites(sites, load_sites(data))
    for off, _opcode, reg, direction, text, operands in sites:
        # The window's own bounds, refused rather than skipped: a site whose
        # operand byte is past the end of the buffer is a site this scan cannot
        # read, and reporting the table without it would be a census short by an
        # unknown amount.
        for n in range(operands):
            _operand(data, off, n + 1)
        name = region_of(off, verified)[0]
        onto, over = converges_from(data, off)
        row = {
            "form": "ri-unresolved",
            "file_offset": f"0x{off:05X}",
            "region": name,
            "runtime": _runtime(off, verified),
            "frame_onto": onto,
            "frame_over": over,
            "access": direction,
            "text": text % data[off + 1] if operands else text,
            "in_data_region": _label(regions, off),
        }
        load = paired.get(off)
        if load is not None:
            # A pair whose immediate names a byte outside the range is still
            # reported, as unresolved rather than dropped: the register was
            # loaded from a constant, the constant is not a byte of the range
            # this tool is about, and saying so is a different statement from
            # omitting the site.
            row["form"] = "ri"
            row["addr"] = f"0x{load[1]:02x}" if lo <= load[1] <= hi \
                else UNRESOLVED
            row["text"] = f"mov r{reg},#0x{load[1]:02x} ; " + row["text"]
        row.setdefault("addr", UNRESOLVED)
        rows.append(row)

    rows.sort(key=lambda r: (r["form"] != "direct", r["addr"] == UNRESOLVED,
                             r["addr"], r["file_offset"]))
    return rows


def render(rows: list) -> str:
    """The `--csv` table as a string, so `--check` diffs the same bytes."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def summarise(rows: list) -> str:
    """The default report: the named bytes, then the `@Ri` split.

    Printed as the two questions a reader actually has -- which bytes in the
    boot-cleared range are named at all, and how much of the `@Ri` population
    this method resolves -- because the per-site rows are the CSV's job and
    printing them here would bury both answers.
    """
    named = collections.defaultdict(collections.Counter)
    forms = collections.Counter()
    for row in rows:
        forms[row["form"]] += 1
        if row["addr"] != UNRESOLVED:
            named[row["addr"]][row["form"]] += 1

    lo, hi = BOOT_IRAM
    lines = [f"internal-RAM byte survey over 0x{lo:02X}-0x{hi:02X}, the range "
             "common 0x0F75's IRAM loop clears:"]
    for byte in range(lo, hi + 1):
        counts = named.get(f"0x{byte:02x}")
        if not counts:
            continue
        tally = "  ".join(f"{form}={counts[form]}"
                          for form in ("direct", "ri") if counts[form])
        lines.append(f"  0x{byte:02X}  {tally}")
    quiet = sum(1 for b in range(lo, hi + 1) if f"0x{b:02x}" not in named)
    lines.append("")
    lines.append(f"  {len(named)} bytes in the range are named by at least one "
                 "site this scan found;")
    lines.append(f"  the {quiet} it does not name are NOT FOUND BY THIS METHOD, "
                 "never 'absent'")
    lines.append("")
    lines.append(f"  @Ri sites in the image: {forms['ri']} resolved by the "
                 f"pairing, {forms['ri-unresolved']} unresolved")
    lines.append("  an unresolved @Ri site is one whose register this method "
                 "does not follow to a")
    lines.append("  load; 0x0F91, the boot path's own IRAM clear store, is one "
                 "of them, which is")
    lines.append("  why the range above comes from executing 0x0F75 and not "
                 "from scanning for the")
    lines.append("  bytes it writes.")
    return "\n".join(lines)


def self_test(data: bytes, verified: bool) -> int:
    """Known answers from outside this file, then the refusals.

    The known answers are transcribed from committed listings rather than from
    this module's own output, so a tool graded against itself is not being
    tested:

      * `../decompiled/common/012F.asm` at `0x0162`/`0x0164` -- `mov R0,#0x84`
        then `mov @R0,#0x2`, the `chan_init_170a` write to `0x84`;
      * the same file at `0x016D`/`0x016F` -- `mov R0,#0x99` then `mov @R0,A`,
        which stores the accumulator rather than an immediate;
      * the same file at `0x017E`/`0x0180` -- `mov R0,#0xAA` then
        `mov @R0,#0x2`;
      * `../decompiled/common/0F75.asm` at `0x0F91` -- `mov @R0,A`, whose R0
        came from the `xch a,R0` pair, so the pairing must leave it unresolved.

    None of these is a count of the tree, and none moves when a register is
    named elsewhere.
    """
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"  {label}: got {got!r}, want {want!r}")

    sites = ri_sites(data)
    loads = load_sites(data)
    paired = pair_sites(sites, loads)

    def resolved(off):
        """(address, direction, rendered text) for a paired site, else None."""
        if off not in paired:
            return None
        _load_off, addr = paired[off]
        _reg, direction, text, operands = RI_BY_OPCODE[data[off]]
        return addr, direction, (text % data[off + 1] if operands else text)

    check("012F.asm 0x0162/0x0164 pair to 0x84",
          resolved(0x0164), (0x84, "write", "mov  @R0,#0x02"))
    check("012F.asm 0x016D/0x016F pair to 0x99",
          resolved(0x016F), (0x99, "write", "mov  @R0,A"))
    check("012F.asm 0x017E/0x0180 pair to 0xAA",
          resolved(0x0180), (0xAA, "write", "mov  @R0,#0x02"))
    check("the pair's load is the two bytes immediately before the site",
          paired.get(0x0164, (None, None))[0], 0x0162)
    check("...and it is the `mov R0,#0x84` the listing shows",
          loads.get(0x0162), (0, 0x84))

    # The blind spot, pinned. `0x0F91` is `mov @R0,A` and the byte before it is
    # `clr A`, so no `mov Rn,#imm` loads the register this method follows. A
    # future widening of the pairing window that picked it up would be
    # reporting an address it cannot establish, and this is where that would
    # surface -- the same guard the `0x0162` cases are the other side of: the
    # tool finds what the bytes support and stops there.
    check("0x0F75.asm 0x0F91 is unresolved, not paired", 0x0F91 in paired, False)
    check("0x0F91 is still an @Ri site this scan found",
          any(site[0] == 0x0F91 for site in sites), True)
    check("the instruction before it is not a `mov Rn,#imm`",
          data[0x0F90] in MOV_RN_IMM, False)

    # The premise correction this tool rests on: the direct scan finds no
    # writer of 0x84 anywhere, and the pairing is what recovers the ones the
    # listing shows. Stated in this scan's own negative vocabulary.
    direct_84 = scan_direct(data, [0x84], verified).get(0x84, [])
    check("intmem_refs' direct table finds no write to 0x84 by this method",
          [d for _o, _op, d, _f in direct_84
           if d in ("write", "rmw")], [])
    check("...and the pairing does resolve 0x84",
          sorted({addr for _l, addr in paired.values() if addr == 0x84}),
          [0x84])

    # The partition. Every `@Ri` site is either paired or explicitly
    # unresolved, and the two sets do not overlap -- a site in both would make
    # the pairing look like it resolved more than it did.
    check("every @Ri site this scan found is one it also reports",
          set(paired) <= {site[0] for site in sites}, True)
    check("no @Ri site is both paired and unresolved",
          bool(set(paired) & {site[0] for site in sites
                              if site[0] not in paired}), False)

    # The two opcode tables must not overlap. The same two bytes read as a
    # direct operand and as an `@Ri` opcode name different bytes, and a scan
    # holding both would count one instruction twice under two answers.
    check("RI_TABLE and intmem_refs' OPCODE_TABLE are disjoint",
          sorted({op for op, _d, _t in OPCODE_TABLE} & set(RI_BY_OPCODE)), [])
    # `movx @Ri` is XDATA, a different address space from an internal-RAM byte.
    check("the `movx @Ri` forms are not counted as internal-RAM bytes",
          sorted({0xE2, 0xE3, 0xF2, 0xF3} & set(RI_BY_OPCODE)), [])
    check("every RI_TABLE row carries a direction the renderer knows",
          sorted({d for _o, _r, d, _t, _p in RI_TABLE}
                 - {"read", "write", "rmw"}), [])
    # The reserved opcode is carried, not dropped: `intmem_refs` keeps it in its
    # own census and a `0xA5` pair is a pair.
    check("the reserved 0xA5 row renders without a substitution",
          direct_text(0xA5, 0x2F), "reserved -- never an instruction")

    # The table's own shape. Every addressable row names a byte inside the
    # range, and every unresolved row says so rather than carrying a byte.
    lo, hi = BOOT_IRAM
    rows = build_rows(data, verified, load_data_regions())
    check("every row's form is one of the three populations",
          sorted({r["form"] for r in rows}), ["direct", "ri", "ri-unresolved"])
    addressable = {r["addr"] for r in rows if r["addr"] != UNRESOLVED}
    check("every addressable row names a byte inside the boot range",
          sorted(a for a in addressable if not lo <= int(a, 16) <= hi), [])
    check("every unresolved row spells its address unresolved",
          {r["addr"] for r in rows if r["form"] == "ri-unresolved"},
          {UNRESOLVED})
    check("no resolved @Ri row names a byte outside the range",
          [r for r in rows if r["form"] == "ri" and r["addr"] != UNRESOLVED
           and not lo <= int(r["addr"], 16) <= hi], [])
    check("the three populations partition the @Ri sites",
          len([r for r in rows if r["form"] != "direct"]), len(sites))

    # The refusals. Each buffer is one that would yield a short, plausible
    # table if its guard were removed.
    def refuses(label, buffer):
        try:
            loads = load_sites(buffer)
            sites = ri_sites(buffer)
            pair_sites(sites, loads)
            for _off, _op, _r, _d, _t, operands in sites:
                for n in range(operands):
                    _operand(buffer, _off, n + 1)
        except Refusal:
            return
        failures.append(f"  {label}: the scan completed instead of refusing")

    # A `mov R0,#` with the immediate byte missing: the pointer's value is not
    # in the buffer, so whether this names a byte at all is unknown.
    refuses("truncated pointer load", bytes([0x78]))
    # A `mov @R0,#` at the end of the buffer: the site is real and its operand
    # is not there to read.
    refuses("truncated @Ri immediate", bytes([0x76]))
    refuses("truncated `mov @R0,direct` operand", bytes([0xA6]))

    if failures:
        print("self-test FAILED:", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        return 1
    print("iram_boot_sites self-test: all assertions passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: the one beside this "
                         "tool's parent directory)")
    ap.add_argument("addrs", nargs="*",
                    help="hex direct byte addresses to list sites for")
    ap.add_argument("--regions", default=None,
                    help="data-regions.yaml (default: the committed one)")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="with --csv, diff this run against a committed table "
                         "and exit non-zero on any difference (default: "
                         "iram-boot-sites.csv)")
    ap.add_argument("--self-test", action="store_true",
                    help="known answers against the committed listings, and "
                         "the refusals")
    args = ap.parse_args(argv)

    if (args.check is not None) and not args.csv:
        ap.error("--check is about the --csv table; it needs --csv")

    try:
        with open(args.firmware, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        print(f"note: {exc}", file=sys.stderr)
        return 1
    verified = pd_verified(data)
    if not verified and not args.csv:
        # What *this* tool does about a missing marker, said without naming the
        # constant. Restating `intmem_refs`' own note would put the marker's
        # bytes into this module's output while nothing here compares them --
        # which is exactly the `unverified` contract
        # `check_pd_marker_contract.py` files a module under, and it files this
        # one correctly: the comparison belongs to `intmem_refs.pd_verified()`
        # and the boolean is handed to `region_of()`. stderr, and suppressed
        # under `--csv`, so the note cannot interleave into the table.
        print("note: the PD image's marker is not in this dump -- sites in "
              "0x20000-0x2FFFF belong to an unidentified region, so their "
              "`region` cell reads 'unknown' rather than a program name\n",
              file=sys.stderr)

    regions = load_data_regions(args.regions) if args.regions \
        else load_data_regions()
    try:
        if args.self_test:
            return self_test(data, verified)

        rows = build_rows(data, verified, regions)
        if args.csv:
            table = render(rows)
            if args.check is not None:
                return check_table(table, args.check)
            sys.stdout.write(table)
            return 0

        wanted = []
        for text in args.addrs:
            try:
                value = int(text, 16)
            except ValueError:
                raise Refusal(f"{text!r} is not a hex address")
            if not 0x00 <= value <= 0xFF:
                raise Refusal(f"0x{value:02X} is not a direct byte address "
                              "(0x00-0xFF)")
            wanted.append(value)

        if wanted:
            print(CAVEAT)
            for value in wanted:
                sites = [r for r in rows if r["addr"] == f"0x{value:02x}"]
                ec = sum(1 for r in sites
                         if r["region"] in ("common", "bank0", "bank1"))
                print(f"0x{value:02x}  refs={len(sites):<3} ec={ec:<3}")
                for row in sites:
                    print(f"    file {row['file_offset']}  {row['region']:<8} "
                          f"runtime {row['runtime']:<8} {row['form']:<13} "
                          f"{row['access']:<5} {row['text']:<30} "
                          f"frame={row['frame_onto']}/{row['frame_over']} "
                          f"in_data_region={row['in_data_region']}")
            print()
        print(summarise(rows))
        return 0
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())