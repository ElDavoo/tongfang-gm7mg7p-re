#!/usr/bin/env python3
"""The `addc A,#imm ; mov DPH,A` sites whose `DPH` is not the immediate, and
what each one's accumulator and carry make of it.

`computed_dptr_sites.py` finds the `mov 0x83,a` a `DPH` build ends in and
resolves the high byte from the one instruction in front of the `add`/`addc`.
That works for `clr a ; addc a,#0x0f`, where the instruction in front pins `A`
to `0`, and it refuses the rest -- an `lcall` in front leaves `A` at whatever
the callee returned, so it prints `not established; the
instruction before it is `lcall 0x2a7b` and moves on. This tool is the other
half of that refusal: it splits the population on whether the instruction
before the `addc` is `clr a` at all, and for the ones that are not it decodes
the predecessor far enough to name **what shape of value the accumulator is
carrying** -- a call target to chase, or a register to read.

**The split is the finding, and it is a split of the scan, not of the
firmware.** Every `34 xx f5 83` triple in the EC window is a site whether or
not `A` happens to be zero in front of it; what the `clr a` predecessors give
is a way of pinning `A` without reading the bytes before the `addc`. So
`clr-a` and `non-clr-a` are two populations over one census, and the census is
the thing both are counted from.

**`clr a` settles `A`, and it does not settle the carry.** It clears the
accumulator only; `CY` survives it, which this repository states twice, in
`docs/findings/pd-index-low8-propagation.md` ("`clr a` does not touch the
carry flag on an 8051 and neither does `mov a,#hi`") and in
`docs/findings.md` §96 ("`clr a` leaves the carry out of `add a,#0x9B` live
into `addc a,#0x08`"). So a `clr a` site builds `imm` **or** `imm+1`, and
**no** site in either population is a single established page on this tool's
evidence alone. Every `dph_set` here is a two-element set for that reason, and
the `0x08`/`0x1C` columns are asked of the set rather than of the immediate.

**Deliberately mechanical: this tool does not decide what a callee returns.**
Reading `clr a ; ret` at a call target and concluding `A` is `0` afterwards is
a *semantic* claim about an export boundary, and the export boundary is a
hypothesis (`bank-call-audit.md` §1: the call-target census is an upper bound).
This tool therefore reports the call **target** and the byte the `addc`
carries, and stops. `docs/findings/addc-dph-residual-six.md` is where the
argument that all three of these targets return `A=0` is made, against the raw
bytes with `disasm8051.py` as the oracle, which is where a semantic claim about
an export belongs rather than in a census a reader re-runs.

**Two encodings carry the accumulator into a non-`clr a` `addc`, and they are
kept apart.** A three-byte `lcall` leaves `A` at the callee's return value; a
one-byte `mov A,Rn` leaves it at a register the tool can name but not read. The
second is what makes the `0x2A` sites decidable from the tool's own output: the
register is named, and a reader who wants the value looks at the instruction
that last wrote it. Collapsing the two into one `not clr a` bucket would hide
which of the two a reader has to chase.

**What the tool will not claim.** `reaches_0x08` and `reaches_1c` are columns
naming whether page `0x08` / page `0x1C` is in the row's *candidate* set, and
they are computed from the immediate and the accumulator alone. A `no` there is
"this construction cannot build that page", never "no writer exists" and never
"the byte is never written" -- the other three spellings of an XDATA address
(`mov DPTR,#imm16`, `movx @Ri`, and a `DPTR` handed in through a subroutine)
are outside the pattern, and `computed_dptr_sites.py`'s own docstring is the
list. The page-`0x08` store that *does* exist -- bank0 `0x8365` -- is a
`clr a` site, which is the other half of why the split matters.

Reads the committed image and writes nothing but stdout.
`ec/annotations/xdata-addc-dph-residual-sites.csv` is the table this
reproduces and `docs/findings/addc-dph-residual-six.md` is the write-up.

Usage:
    python3 addc_dph_sites.py ../firmware/GMxMGxx_11.800
    python3 addc_dph_sites.py ../firmware/GMxMGxx_11.800 --csv \\
            > ../annotations/xdata-addc-dph-residual-sites.csv
    python3 addc_dph_sites.py ../firmware/GMxMGxx_11.800 --check
    python3 addc_dph_sites.py ../firmware/GMxMGxx_11.800 --residual-only
"""
import argparse
import collections
import csv
import io
import os
import sys

from disasm8051 import OPCODE_LEN, inline_arg_len, mnemonic
from trace_xdata_refs import (PD_MARKER, REGIONS, check_table, region_of,
                              repo_path, runtime_addr)

SITES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "annotations",
                         "xdata-addc-dph-residual-sites.csv")

# The scan, as three byte constants rather than as a slice comparison: the
# opcode, the immediate byte that carries the page half, and the `mov DPH,A`
# that follows it. Spelled this way so a reader can see the exact triple the
# population is and not have to reconstruct it from the prose above.
ADDC_IMM = 0x34
MOV_DIRECT_ACC = 0xF5
DPH = 0x83

# The main EC's three regions, and the PD image excluded beside them.
# `computed_dptr_sites.py` names the same three, and the reason is the same:
# a `DPTR` in the PD image is **another program's** byte, so folding it into a
# census of "the EC window" would state a total about two firmwares. The
# issue's census is `GMxMGxx_11.800[0:0x18000]`, which is exactly these three.
MAIN_EC_REGIONS = ("common", "bank0", "bank1")

# The instruction that pins the accumulator without reading anything else:
# `clr a` clears the accumulator, and on an 8051 that is *all* it clears --
# `CY` survives it (`docs/findings/pd-index-low8-propagation.md`, and
# `docs/findings.md` §96). So this is what makes `A` known for the
# `clr-a` population, not what makes the high byte a single page: `imm + CY`
# is still two candidates.
CLR_A = 0xE4

# `mov A,Rn` is the eight opcodes `0xE8`-`0xEF`, one byte, with the register in
# the low three bits -- so the test below is a range and not an equality. The
# one-byte `mov a,r6` (`0xEE`) at `0x28EE` is what makes the `0x2A` sites
# decidable, so the register has to be named rather than the whole instruction
# being refused as "not clr a".
MOV_A_REG = 0xE8
MOV_A_REG_MAX = 0xEF
# The three-byte `lcall`. Its operand is the whole routine, which is why the
# cell carries a target this tool does not follow.
LCALL = 0x12

# The register-name table `disasm8051.mnemonic()` itself renders from, as a
# prefix so a cell reads `mov a,r6` the way the listing it is checked against
# does. Kept local rather than imported because the tool must not grow a
# dependency on another tool's private table for one word.
REG_NAMES = ("r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7")

# The two states a site's predecessor can leave the accumulator in, and the
# tokens their cells carry. `CARRY_UNKNOWN` is named here rather than at the
# one call site so a reader of a cell can tell which of the two produced it,
# which is the whole difference between the two `0x0D` and `0x2A` stories.
CLR_A_SHAPE = "clr a"
CARRY_UNKNOWN = "carry not established by this tool"
# The token for a predecessor this tool does not model. It is a *limit on the
# look*, not a claim about the accumulator -- the same distinction
# `computed_dptr_sites.accum_before()` draws between a refusal and a fact.
NOT_MODELLED = "not modelled by this scan"
# The `window` cell for a site the anchored walk never reaches as an
# instruction start. A byte scan finds such a site and an anchored one cannot,
# so this is a real state and not a defensive branch; naming it keeps the cell
# from carrying a decode of the wrong bytes.
UNFRAMED = ("no window; the anchored walk does not reach this offset as an "
            "instruction start")
# The cell a `mov A,Rn` gets, which is deliberately **not** the generic refusal
# above. Both say the accumulator is not established, but they say it about
# different things: this one names a register that carries `A`, and that is
# what tells a reader the `0x2A` sites are settled by the instruction that
# last wrote the register rather than by anything at the `addc`.
REG_CARRIES = "a register this scan does not model"


def norm(d: bytes, at: int) -> str:
    """`mnemonic()`'s text, whitespace-normalised.

    Its own docstring's reason, from `find_indirect_xdata.py`: the renderer
    pads operands to a column, so the same instruction reads `mov a,r6` in one
    cell and `mov  a,r6` in another, and a cell a reader compares against a
    listing does not match.
    """
    return " ".join(mnemonic(d, at).split())


def window(d: bytes, lo: int, hi: int, at: int, back: int = 4) -> str:
    """The `back` instructions before `at` and `at` itself, as a decode.

    Framed by a linear walk over the region rather than by slicing bytes
    backwards, because the predecessor is read as an *instruction*: a three-byte
    `lcall` and a one-byte `mov a,r6` are both "the instruction before the
    `addc`" and only the framing tells them apart. `OPCODE_LEN` is the length
    table `computed_dptr_sites.anchored_starts()` walks with, for the reason
    its docstring gives -- one definition of the framing, or two decisions.

    A site the walk never reaches as an instruction start -- which a byte scan
    can find and an anchored one cannot, since the population is "a three-byte
    pattern somewhere" -- gets `UNFRAMED` rather than a window. Falling back to
    the last instructions of the region would put a decode in the cell that has
    nothing to do with the site, and that is the confident-wrong-answer shape
    this whole column exists to avoid.
    """
    starts, i = [], lo
    while i < hi and i < len(d):
        n = OPCODE_LEN[d[i]]
        if i + n > hi or i + n > len(d):
            i += 1
            continue
        starts.append(i)
        i += n + inline_arg_len(d, i)
    if at not in starts:
        return UNFRAMED
    k = starts.index(at)
    return " ; ".join(norm(d, s) for s in starts[max(0, k - back):k + 1])


def predecessor(d: bytes, at):
    """(the `preceded_by` cell, the accumulator's value or None) at `at`.

    `at` is the `addc`. The value is the accumulator as the *predecessor*
    establishes it, and None where the predecessor is a call -- which is a
    refusal naming the encoding rather than an assertion that the accumulator
    held anything. The call's target is carried in the cell rather than
    returned beside it, because the target is what a reader has to go and read.

    Only `clr a` establishes a value here. `mov A,Rn` names the register but
    does not read it: the tool has no register model, so claiming `A` is `R6`
    would be a fact about a register nobody has read. The cell names `R6` and
    says that a register is what carries `A`, which is the fact a reader acts
    on -- the two `0x2A` sites are settled in the write-up by reading the one
    `mov R6,#0x00` three instructions earlier, and this cell is what points
    them at it. Every other encoding gets the bare refusal, because for those
    the tool does not know what carries `A` at all.
    """
    prev = None
    for b in range(at - 1, max(-1, at - 4), -1):
        if b >= 0 and OPCODE_LEN[d[b]] == at - b:
            prev = b
            break
    if prev is None:
        return NOT_MODELLED, None
    if d[prev] == CLR_A:
        return CLR_A_SHAPE, 0
    if MOV_A_REG <= d[prev] <= MOV_A_REG_MAX:
        reg = REG_NAMES[d[prev] & 0x07]
        return (f"`mov a,{reg}` at 0x{prev:05X} -- `A` carries {reg}, "
                f"{REG_CARRIES}"), None
    if d[prev] == LCALL and prev + 2 < len(d):
        target = (d[prev + 1] << 8) | d[prev + 2]
        return f"`lcall 0x{target:04x}`", None
    return f"`{norm(d, prev)}` at 0x{prev:05X} -- {NOT_MODELLED}", None


def access_of(d: bytes, after: int, budget: int = 3):
    """(the `access` cell, the detail cell) for the access at or after `after`.

    A **short forward walk**, not the single opcode at `after`, and the reason
    is the shape of the two spellings: the store at `0x2266` is
    `mov DPH,A ; mov A,0x66 ; movx @DPTR,A`, where the byte being stored is
    loaded from a direct address *between* the pointer build and the store. An
    implementation that looked at the one instruction after `mov DPH,A` would
    find `mov A,0x66` at every store and call the population reads.

    The budget is three because that is the width of the idiom these sites use
    -- `mov A,imm` is two bytes and the store is one past it -- and the walk
    stops at the first `movx`, `movc` or control-flow opcode it reaches, so a
    site whose pointer is used later is reported as "no access in the next
    three instructions" rather than as a read or a store nobody saw. The
    budget is a **reported limit**, not a filter, and no site is dropped for
    exceeding it.
    """
    at = after
    for _ in range(budget):
        if at >= len(d):
            return "no access found; end of image", ""
        op = d[at]
        if op == 0xF0:
            return "store via `movx @dptr,a`", f"`{norm(d, at)}` at 0x{at:05X}"
        if op == 0xE0:
            return "read via `movx a,@dptr`", f"`{norm(d, at)}` at 0x{at:05X}"
        if op == 0x93:
            return ("CODE read via `movc a,@a+dptr`, not an XDATA access",
                    f"`{norm(d, at)}` at 0x{at:05X}")
        if op in (0x22, 0x02, 0x12):
            return ("DPTR handed to a subroutine",
                    f"`{norm(d, at)}` at 0x{at:05X}")
        at += OPCODE_LEN[op]
    return (f"no `movx`/`movc` within {budget} instructions",
            f"from 0x{after:05X}")


def site_row(d: bytes, at: int, pd_verified: bool) -> dict:
    """The row for one `34 xx f5 83` at `at`.

    The candidate page set is `A + imm [+ carry]` and it is **always a
    two-element set**, because `addc` reads the carry and this tool never
    establishes it -- `clr a` included, since `clr a` clears the accumulator
    and leaves `CY` alone. `acc` is what the predecessor pins `A` to (`0` for
    `clr a`, `None` where nothing pins it), so a `clr a` site is the one case
    where the low member is known and the high one is not. Collapsing any of
    this to its low member is the §4d shape -- a claim as though the method
    had established something it had not -- so the column is printed as a set
    and the two reach columns are asked of the set rather than of the
    immediate.

    `access` is a **reported column, not a filter**: the population is every
    `34 xx f5 83` whose predecessor is not `clr a`, and dropping the sites
    with no `movx` would have found four of the six and looked like a clean
    run.
    """
    imm = d[at + 1]
    store = at + 2
    prev, acc = predecessor(d, at)
    low = (acc + imm) & 0xFF if acc is not None else imm
    pages = frozenset({low, (low + 1) & 0xFF})
    access, detail = access_of(d, store + 2)
    return {
        "offset": at,
        "runtime": runtime_addr(at, pd_verified),
        "region": region_of(at, pd_verified)[0],
        "imm": imm,
        "preceded_by": prev,
        "a_on_entry": ("0" if prev == CLR_A_SHAPE
                       else "not established by this tool"),
        "dph_set": "{" + ", ".join(f"0x{p:02X}" for p in sorted(pages)) + "}",
        "pages": pages,
        "access": access,
        "access_detail": detail,
        "reaches_0x08": "yes" if 0x08 in pages else "no",
        "reaches_0x1c": "yes" if 0x1C in pages else "no",
        "window": window(d, *_span(at), at),
    }


def _span(at: int):
    """(lo, hi) the region `at` is in, for `window()`'s linear walk.

    The span rather than a fixed width, so the walk is framed over the same
    region the site is in and a predecessor is never read across a region
    boundary -- which on a banked image would be a different program's byte.
    """
    for _name, lo, hi, base, _how in REGIONS:
        if lo <= at < hi and base is not None:
            return lo, hi
    return max(0, at - 0x100), at + 0x100


def census(d: bytes) -> list:
    """Every `34 xx f5 83` in the main EC's three regions, in address order.

    A byte scan rather than an anchored one, and the reason is the shape of the
    question: the population is "a three-byte opcode pattern somewhere", the
    same population `computed_dptr_sites.py` takes with a byte scan in
    `raw_sites()` before anchoring it. A byte that is *not* an instruction
    start is still a candidate, and whether it is one is the question the
    `preceded_by` cell answers -- dropping the unframed bytes first would
    decide the census by the framing and leave nothing to report.

    The two `erased` rows of REGIONS are skipped for the reason
    `computed_dptr_sites.stores()` gives: no runtime base, and `0xFF` is
    `mov r7,direct` on a 8051, so a walk through filler would decode it as
    instructions. The PD image is skipped for the reason `MAIN_EC_REGIONS`
    gives, and unlike those two rows it *is* a program -- excluding it is a
    decision about the census's scope rather than a refusal to decode it.
    """
    out = []
    for name, lo, hi, base, _how in REGIONS:
        if base is None or name not in MAIN_EC_REGIONS:
            continue
        i = lo
        while i + 3 < hi and i + 3 < len(d):
            if (d[i] == ADDC_IMM and d[i + 2] == MOV_DIRECT_ACC
                    and d[i + 3] == DPH):
                out.append(i)
            i += 1
    return sorted(out)


def residual(d: bytes, pd_verified: bool) -> list:
    """The rows for the sites whose predecessor is **not** `clr a`.

    This is the population `xdata-1c3x-consumers.md` §6.2 names as its
    residual, and the one this pass settles. A function rather than a filter in
    `main()` because the CSV is this population and the summary prints both
    halves of the census beside it -- a table of the residual with no count of
    what it was residual *to* is the shape of a claim that reads as a total.
    """
    out = []
    for at in census(d):
        row = site_row(d, at, pd_verified)
        if row["preceded_by"] != CLR_A_SHAPE:
            out.append(row)
    return out


def csv_table(rows: list) -> str:
    """The `--csv` table, as a string rather than a write.

    `--check` diffs the same bytes this prints, and the tool's contract is that
    it writes nothing but stdout. The columns are the site's identity, the
    immediate, where the accumulator came from, the page set, what the pointer
    is then used for, and the two reach columns -- in that order, so the last
    four together let a reader re-derive the conclusion from the row rather
    than take it on trust.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["addr", "region", "imm", "preceded_by", "a_on_entry",
                "dph_set", "access", "access_detail", "reaches_0x08",
                "reaches_0x1c", "evidence", "window"])
    for r in rows:
        w.writerow([
            f"0x{r['offset']:04X}", r["region"], f"0x{r['imm']:02X}",
            r["preceded_by"], r["a_on_entry"], r["dph_set"], r["access"],
            r["access_detail"], r["reaches_0x08"], r["reaches_0x1c"],
            "ec/firmware/GMxMGxx_11.800", r["window"]])
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware",
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="print the per-site table as CSV")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="exit non-zero unless PATH is byte for byte what "
                         "this run produces (default: the committed table)")
    ap.add_argument("--residual-only", action="store_true",
                    help="print the per-site table for the sites whose "
                         "predecessor is not `clr a`, and nothing else")
    args = ap.parse_args()

    try:
        with open(args.firmware, "rb") as f:
            d = f.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    pd_verified = d[PD_MARKER[0]:PD_MARKER[0] + len(PD_MARKER[1])] == PD_MARKER[1]

    rows = residual(d, pd_verified)
    if args.csv or args.residual_only:
        print(csv_table(rows), end="")
        return 0
    if args.check:
        return check_table(csv_table(rows), args.check)

    every = census(d)
    print(f"Scanning the EC window for `addc A,#imm ; mov DPH,A` "
          f"(`34 xx f5 83`):\n\n  {len(every)} site(s) in total.\n")

    shapes = collections.Counter(
        "preceded by `clr a` -- `A` is 0, so the high byte is `imm` or `imm+1`"
        if at - 1 >= 0 and d[at - 1] == CLR_A
        else "not preceded by `clr a` -- the high byte is `A + imm + carry`"
        for at in every)
    for what, count in sorted(shapes.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>4}  {what}")
    print("\n  This is a split of one scan, not two populations: every site is a\n"
          "  site, and what `clr a` supplies is a way to pin `A` without reading\n"
          "  anything in front of the `addc`. It does not supply the carry --\n"
          "  `clr a` clears the accumulator and leaves `CY` alone -- so **no**\n"
          "  site here is a single established page; each builds `imm` or\n"
          "  `imm+1`.")

    # What the immediates settle for the `clr a` half, since `clr a` does not
    # make its page exact. Printed rather than asserted, because a reader
    # checking either page has to be able to see the set that settles it.
    #
    # The rule is `P` **or** `P-1`, not `P-1` alone: a site whose immediate is
    # the page itself reaches that page with the carry clear, which is as much a
    # part of the set as the member one page up. Getting this wrong does not
    # merely misdescribe the population, it would report the page-`0x08` store
    # at `0x8360` as unreachable.
    #
    # Both pages are then asked of `site_row()`, the same function the CSV and
    # the residual table come from, rather than of a set rebuilt here. A second
    # copy of the `{imm, imm+1}` rule in the printer is a second thing to get
    # wrong, and this is the line where it was last got wrong.
    clr_rows = [site_row(d, at, pd_verified) for at in every
                if at - 1 >= 0 and d[at - 1] == CLR_A]
    clr_imms = {r["imm"] for r in clr_rows}
    print("\n  What the immediates settle for the `clr a` half. A two-element\n"
          "  set holds a page `P` when the immediate is `P` **or** `P-1` --\n"
          "  both, so a site carrying `P` itself is not ruled out by the\n"
          "  set's other member. The immediates in this scan are\n  "
          + ", ".join(f"`0x{i:02X}`" for i in sorted(clr_imms))
          + ",\n  and each page reads off that list:")
    for page, name in ((0x08, "`0x0862`/`0x086D`"), (0x1C, "`0x1Cxx`")):
        hit = [r for r in clr_rows if page in r["pages"]]
        if hit:
            for r in hit:
                print(f"    page 0x{page:02X}  reached by 0x{r['offset']:04X}, "
                      f"set {r['dph_set']}, {r['access_detail']} --\n"
                      f"               the store {name} names, not a new "
                      "finding")
        else:
            need = [f"0x{p:02X}" for p in (page, (page - 1) & 0xFF)
                    if p not in clr_imms]
            print(f"    page 0x{page:02X}  no `clr a` site reaches it: "
                  f"{' and '.join(need)} "
                  f"{'is' if len(need) == 1 else 'are'}\n"
                  "               not among the immediates, and the set is "
                  "the whole of the\n"
                  "               reading for this population")

    print("\nThe sites this scan does not resolve, which is the population "
          "`xdata-1c3x-consumers.md`\n§6.2 names as its residual:\n")
    print("  addr    xx    preceded_by                       pages        "
          "access")
    for r in rows:
        print(f"  0x{r['offset']:04X}  0x{r['imm']:02X}  {r['preceded_by']:<34}"
              f" {r['dph_set']:<12} {r['access']}")
    print("\n  `pages` is a set and stays one: `addc` reads the carry, and "
          "nothing establishes it\n  here -- `clr a` included, since it leaves "
          "`CY` alone. A site whose set\n  does not hold `0x08` cannot build "
          "page `0x08` **by this construction**, which\n  is not the same "
          "claim as having no writer.")

    print("\nWhat DPTR is used for at each site, from the opcode after the "
          "`mov DPH,A`.\nA reported column, not a filter -- a population "
          "filtered on `movx` would drop the two\n`movc` sites and find "
          "four of the six:\n")
    uses = collections.Counter(r["access"] for r in rows)
    for what, count in sorted(uses.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {count:>4}  {what}")

    print("\nThe two pages the residual is about, asked of each site's page "
          "set. `no` means\nthis construction cannot build it -- the other "
          "spellings of an XDATA address are outside\nthe pattern, and "
          "`computed_dptr_sites.py`'s docstring is the list of them:\n")
    for page, name in ((0x08, "0x08 (`0x0862`/`0x086D`)"), (0x1C, "0x1C")):
        hit = [f"0x{r['offset']:04X}" for r in rows if page in r["pages"]]
        verdict = ", ".join(hit) if hit else "no site"
        print(f"  page {name:<24} reached by {verdict}")

    print(f"\n{repo_path(SITES_CSV)} is the per-site table; `--csv` prints it "
          f"and `--check` diffs\nthis run against it. "
          "docs/findings/addc-dph-residual-six.md is the write-up, and it\n"
          "is where the claim about what each call target *returns* is made -- "
          "this tool\nreports the target and stops.")
    return 0


if __name__ == "__main__":
    sys.exit(main())