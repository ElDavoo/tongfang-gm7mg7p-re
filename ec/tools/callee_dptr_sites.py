#!/usr/bin/env python3
"""Resolve the address behind every `movx` on the `0x0860`-`0x086E` page,
including the ones a `MOV DPTR,#imm16` in the same function cannot explain.

`trace_xdata_refs.py` finds a site by scanning for `MOV DPTR,#imm16` and then
reading the `movx` after it. That is the right rule for a page whose addresses
are all named in the function that touches them, and it is blind in one
specific shape: a routine that loads DPTR and **returns**, so the caller
dereferences a pointer the caller's own bytes never loaded. `0xD319`
(`mask_dp_byte_7c_reset_dptr_0860`) is that shape -- `movx A,@DPTR / anl
A,#0x7c / mov DPTR,#0x0860 / ret` -- and its callers store through it, so the
firmware has stores to `0x0860` that no `MOV DPTR` site accounts for.

The C-level census behind `xdata-registers.csv` does not see them either, and
for the opposite reason: it reads the decompiled text, where Ghidra bound DPTR
to its **pre-call** value. Both committed methods are therefore blind at the
same place, which is what `check_site_census.py` was reading as `agree`. This
tool exists to make the shape visible, by resolving DPTR from the `.asm`
listings rather than from either method's own assumption.

**The rule is a backward walk inside one listing, and every outcome is a named
token.** For each `movx @DPTR`, walk back through the rows above it until
something writes DPTR, and report where the value came from:

| `dptr_source` | what established DPTR |
|---|---|
| `literal` | a `mov DPTR,#imm16` earlier in the same listing |
| `callee` | a call or tail-call whose routine's own run ends on a `mov DPTR,#imm16` |
| `predecessor` | nothing in this listing, and the listing ending immediately below its entry does |
| `unresolved` | anything else, with the reason in `note` -- never a guess |

`predecessor` exists because `set_0860_ff_then_d284` at `0xD281` is three bytes
long and `write_ff_to_dptr_then_d28e` at `0xD284` begins where it ends: the
store of `0xFF` sits in the second listing and DPTR comes from the first. That
is the same blind spot as `callee` -- a transfer with no literal in the listing
holding the access -- and reporting it as `unresolved` would file a known
writer of `0x0860` in the not-found column.

**A backward walk through branches is a linear reading, and `note` is where
that shows.** A `ret` between the `movx` and the write it walked back to ends
the walk and the row is `unresolved`: past it the routine is handing DPTR back
to whoever called *it*, which is a question about that caller and not this one.
An `ljmp`/`ajmp` is chased like a call, because it carries DPTR on to its
target, unless the target lies inside the listing doing the jumping -- that is
a jump and not a tail call, and the next row is not the one that runs. A
*forward conditional* branch is stepped over, because the fall-through path it
guards is the one that reaches the `movx`: `0x0D18F jnz 0xD195` sits between
the `lcall 0xD319` and the `movx @DPTR,A` at `0x0D191`, and stepping over it is
what finds the store. The chase into a callee stops at `MAX_CHASE` and says so
rather than resolving one level deeper quietly.

**The population is the page, not the tree.** A `movx` row is emitted when the
resolved address is in `0x0860`-`0x086E`; a `movx` this tool resolved to no
address is counted on the summary line instead, because a row whose address is
unknown cannot be said to be on the page or off it, and a count of nothing
would read as a census. A second row kind comes from
`../annotations/bank-call-targets.csv`: a committed call site of a helper this
tool chased that **no committed listing covers**, whose `movx` and `listing`
cells are therefore empty. That is how `0x0D1E3` appears. The call-site table
books transfers by a byte scan of the image, so it records sites inside bytes
no export reaches. Only its `lcall` rows are read: a tail-call site transfers
into a routine rather than calling it and getting a return address, so the two
are different units, and the six case handlers on this page are reached by a
`ljmp @a+dptr` that this table does not book at all.

**Two counts, answering two questions, and the `0x0D1E3` row is not promoted
to a store by being in the table.** The `movx` rows are what the committed
listings resolve to; the call-site rows are what the image holds where no
listing reaches. The bytes behind `0x0D1E3` were decoded once, by hand, with
`disasm8051.py --at 0x0D1E3 --runtime 0xD1E3 --converge` and confirmed in
`r2`; that reading, with the anchor-relative-framing caveat `disasm8051.py`
asks to be quoted beside it, is in
`../../docs/findings/callee-set-dptr-census-blindspot.md`. No listing is
invented to hold it, and no sweep count moves because of it.

**The `.asm` is the evidence here and the decompiled `.c` is not.** Every value
this tool prints is read out of `../decompiled/**/*.asm` through
`xdata_register_map.read_asm`, whose own docstring says the framing of a row is
not checked. The census is not consulted, derived from or compared against; the
correspondence to it is `check_site_census.py`'s, over a table this tool does
not touch.

Usage:
    python3 callee_dptr_sites.py
    python3 callee_dptr_sites.py --csv > ../annotations/xdata-0860-callee-dptr-sites.csv
    python3 callee_dptr_sites.py --check
    python3 callee_dptr_sites.py --self-test
"""
import argparse
import collections
import csv
import io
import os
import sys

from trace_xdata_refs import check_table, offset_for_runtime, repo_path
from xdata_register_map import (DECOMPILED, DPTR_IMM, MAIN_PROGRAMS,
                                PD_PROGRAM, clobbers_dptr, load_index,
                                read_asm)

HERE = os.path.dirname(os.path.abspath(__file__))
ANNOT = os.path.join(HERE, os.pardir, "annotations")
CSV_PATH = os.path.join(ANNOT, "xdata-0860-callee-dptr-sites.csv")
CALL_TARGETS = os.path.join(ANNOT, "bank-call-targets.csv")

# The page, inclusive. A range rather than the fifteen addresses
# xdata-086x-dispatch.md §1 sweeps, because 0x0864 is in it and no committed
# table names it.
PAGE_LO, PAGE_HI = 0x0860, 0x086E

# The decompiled directories, in the order their rows are emitted. The PD image
# is swept for the same reason trace_xdata_refs.py sweeps it: a row in it is a
# different program's byte and the tool reports the region rather than deciding.
PROGRAMS = MAIN_PROGRAMS + (PD_PROGRAM,)

# Directory name to `trace_xdata_refs.REGIONS` region name. The two disagree on
# the PD image alone -- `xdata_register_map.PD_PROGRAM` is the directory and the
# sweep calls it `pd-image` -- and the mapping is spelled out here rather than
# derived, because guessing `region == program` is right for three of the four
# and wrong for the one that is a separate image.
REGION_OF = {"bank0": "bank0", "bank1": "bank1", "common": "common",
             PD_PROGRAM: "pd-image"}

# The four transfer forms that can carry DPTR out of a listing and back into
# the caller. `trace_xdata_refs.CALL_TAIL` is the same set spelled for a
# different predicate; a second import of it would tie this tool's chase to a
# name that means "this window ended here" over there.
CALLS = ("lcall", "acall", "ljmp", "ajmp")

# The transfers that end a backward walk rather than being chased. Only `ret`
# is here: `ljmp`/`ajmp` pass DPTR on to their target and are chased like a
# call, and a conditional forward branch leaves the fall-through path that
# reaches the `movx` intact. An `ljmp` whose target lies **inside** the listing
# doing the jumping is a different thing -- an intra-routine jump, where the
# next row is not the one that runs -- and `resolve()` refuses those.
BOUNDARY = ("ret",)

# The two of `CALLS` that can be either a tail call or a jump. `abs_target()`
# spells the target for both, so the difference is made here.
TAILCALLS = ("ljmp", "ajmp")


def _inside(rows: list, target):
    """Whether `target` falls within a listing's own address span."""
    return int(rows[0][0], 16) <= target <= int(rows[-1][0], 16)

# How deep the chase into a callee goes before it gives up and says so. The
# bound exists so a mutual recursion in the listings cannot make this loop, and
# a run that reaches it prints the bound rather than resolving one level deeper
# without saying so.
MAX_CHASE = 3

COLUMNS = ["file_offset", "region", "runtime", "listing", "movx",
           "dptr_source", "xdata_addr", "helper", "note"]


def in_page(addr) -> bool:
    return addr is not None and PAGE_LO <= addr <= PAGE_HI


def hexaddr(addr) -> str:
    return f"0x{addr:04X}"


def abs_target(mnem: str, oper: str):
    """The target of an `lcall`/`ljmp` operand, or None.

    None for a paged form and for anything that is not a plain address, which
    is the honest answer rather than a guess. `disasm8051.mnemonic()` resolves
    an `ajmp`/`acall` target from the address of the following instruction, so a
    listing row does spell it as an address -- but it spells it in the
    *executing* program, and this tool's chase is one program's listings deep,
    so refusing the two paged forms here keeps the answer to what the listing
    itself carries.
    """
    if mnem not in ("lcall", "ljmp"):
        return None
    try:
        return int(oper, 16)
    except ValueError:
        return None


class Tree:
    """The committed listings, indexed by entry address.

    `by_entry` is keyed on `(program, address)` because the same runtime address
    is different bytes in each bank, with a cross-program fallback because the
    8051 banking convention maps the common area into every bank: a caller in
    bank0 may call a common-area target whose listing is only exported once.
    The fallback is a lookup, never a claim that the bytes agree.
    """

    def __init__(self, listings=None):
        self.programs = listings
        if self.programs is None:
            self.programs = {}
            for name in PROGRAMS:
                path = os.path.join(DECOMPILED, name)
                if os.path.isdir(path):
                    self.programs[name] = read_asm(name)
        self.by_entry = {}
        self.covers_any = {}
        for name, stems in self.programs.items():
            for stem, rows in stems.items():
                if not rows:
                    continue
                self.by_entry.setdefault((name, int(stem, 16)), (stem, 0))
                for index, (at, _mnem, _oper) in enumerate(rows):
                    self.covers_any.setdefault((name, int(at, 16)),
                                               (stem, index))
        self.any_entry = {}
        for (name, entry), loc in self.by_entry.items():
            self.any_entry.setdefault(entry, (name, loc))
        # The exporter's own function extents, for `preceding()`: every address a
        # function's bytes end at, mapped back to the function's own name.
        self.extent = {}
        for (program, addr), row in load_index()[0].items():
            try:
                start, size = int(addr, 16), int(row["size"])
            except (TypeError, ValueError):
                continue
            self.extent.setdefault((program, start + size), addr)

    def rows(self, program: str, stem: str) -> list:
        return self.programs[program][stem]

    def at(self, program: str, target):
        """`(program, stem, index)` for a target address, or None."""
        found = self.by_entry.get((program, target))
        if found is not None:
            return program, found[0], found[1]
        anywhere = self.any_entry.get(target)
        if anywhere is None:
            return None
        return anywhere[0], anywhere[1][0], anywhere[1][1]

    def covered_by(self, program: str, addr: int) -> bool:
        """Whether any listing in `program` decodes a row at `addr`.

        Distinct from `at()`, which asks whether a listing *starts* there. A
        committed call site in the middle of an export is covered; one in the
        bytes between exports is not, and the difference is the whole of what
        the `0x0D1E3` row is about.
        """
        return (program, addr) in self.covers_any

    def preceding(self, program: str, stem: str):
        """The listing whose last byte is the byte below `stem`'s entry.

        Tested against the exporter's own function extent -- `index.csv`'s
        `size` column -- rather than against the listing's last row, because
        `read_asm()` consumes the opcode column and keeps neither the width of
        the final instruction nor the number of bytes the export covers. A
        listing with no `index.csv` row, or one whose size will not parse, is
        not a candidate; the test fails closed rather than guessing an extent
        and calling a fall-in that the bytes do not show.
        """
        rows = self.programs.get(program, {}).get(stem)
        if not rows:
            return None
        previous = self.extent.get((program, int(rows[0][0], 16)))
        return None if previous == stem else previous


def dptr_at_return(tree: Tree, program: str, stem: str, index: int,
                   depth: int = 0):
    """`(address, note)` for DPTR live at the `ret` of the run at an entry.

    Walks the routine's own straight-line run forward. `mov DPTR,#imm16` is the
    answer; a call inside the run hands the question to that routine and the
    chase stops at `MAX_CHASE`; a `ret` before any write, a one-byte `0x82`/
    `0x83` store and the end of the run are each `None` with a note naming
    which. `None` is never turned into an address.
    """
    if depth > MAX_CHASE:
        return None, f"chase stopped at depth {MAX_CHASE}"
    for _at, mnem, oper in tree.rows(program, stem)[index:]:
        if mnem == "mov" and DPTR_IMM.match(oper):
            return int(DPTR_IMM.match(oper).group(1), 16), "literal"
        if mnem in CALLS:
            target = abs_target(mnem, oper)
            if target is None:
                return None, "transfer target is not an address"
            found = tree.at(program, target)
            if found is None:
                return None, f"no committed listing for {hexaddr(target)}"
            return dptr_at_return(tree, *found, depth + 1)
        if mnem == "ret":
            return None, "returns without writing DPTR"
        if clobbers_dptr(mnem, oper):
            return None, f"moves DPTR without naming it ({mnem} {oper})"
    return None, "run ends without writing DPTR"


def resolve(tree: Tree, program: str, stem: str, index: int) -> dict:
    """One `movx` row's `dptr_source`, `xdata_addr`, `helper` and `note`."""
    rows = tree.rows(program, stem)
    got = {"dptr_source": "unresolved", "xdata_addr": None, "helper": None,
           "note": "listing entry; DPTR is whatever the caller left"}
    for back in range(index - 1, -1, -1):
        at, mnem, oper = rows[back]
        if mnem == "mov" and DPTR_IMM.match(oper):
            got.update(dptr_source="literal",
                       xdata_addr=int(DPTR_IMM.match(oper).group(1), 16),
                       note=f"mov DPTR at {hexaddr(int(at, 16))}, same listing")
            return got
        if mnem in CALLS:
            target = abs_target(mnem, oper)
            if target is None:
                got["note"] = f"reached by {mnem} to a target not in the instruction"
                return got
            if mnem in TAILCALLS and _inside(rows, target):
                got["note"] = (f"{mnem} to {hexaddr(target)}, inside this listing, "
                               "so it is a jump and not a tail call")
                return got
            got.update(dptr_source="callee", helper=target)
            found = tree.at(program, target)
            if found is None:
                got["note"] = f"no committed listing for {hexaddr(target)}"
                return got
            addr, why = dptr_at_return(tree, *found)
            got["xdata_addr"] = addr
            got["note"] = (f"{hexaddr(target)} loads DPTR before returning"
                           if why == "literal"
                           else f"{hexaddr(target)} {why}")
            return got
        if mnem in BOUNDARY:
            got["note"] = f"walk crosses {mnem} at {hexaddr(int(at, 16))}"
            return got
        if clobbers_dptr(mnem, oper):
            got["note"] = (f"{mnem} {oper} at {hexaddr(int(at, 16))} moves DPTR "
                           "without naming an address")
            return got
    previous = tree.preceding(program, stem)
    if previous is not None:
        got.update(dptr_source="predecessor", helper=int(previous, 16))
        addr, why = dptr_at_return(tree, *tree.at(program, int(previous, 16)))
        got["xdata_addr"] = addr
        got["note"] = (f"{previous} falls into this listing with DPTR loaded"
                       if why == "literal" else f"{previous} {why}")
    return got


def site_rows(tree: Tree) -> list:
    """Every committed `movx` this tool resolves onto the page."""
    out = []
    for program in sorted(tree.programs):
        for stem in sorted(tree.programs[program]):
            seq = tree.programs[program][stem]
            for index, (at, mnem, oper) in enumerate(seq):
                if mnem != "movx" or "@DPTR" not in oper:
                    continue
                got = resolve(tree, program, stem, index)
                if not in_page(got["xdata_addr"]):
                    continue
                out.append(_movx_row(program, stem, at, oper, got))
    return out


def unplaced(tree: Tree) -> int:
    """`movx` in the listings that resolved to no address at all.

    Reported rather than dropped, for the reason the module docstring gives:
    a number here is what keeps the emitted set from reading as a census of
    the page.
    """
    n = 0
    for program in sorted(tree.programs):
        for stem in sorted(tree.programs[program]):
            seq = tree.programs[program][stem]
            for index, (at, mnem, oper) in enumerate(seq):
                if mnem != "movx" or "@DPTR" not in oper:
                    continue
                if not in_page(resolve(tree, program, stem, index)["xdata_addr"]):
                    n += 1
    return n


def call_site_rows(tree: Tree, helpers) -> list:
    """One row per committed call site of a chased helper no listing covers.

    A site a listing *does* cover was already emitted as a `callee` row, so
    only the gaps land here. The table is read for its target column only; the
    `movx` behind such a site is not decoded here and its cell is empty.
    """
    out = []
    wanted = set(helpers)
    if not wanted:
        return out
    try:
        with open(CALL_TARGETS, newline="") as f:
            committed = [r for r in csv.DictReader(f) if r["opcode"] == "lcall"]
    except OSError:
        return out
    for row in committed:
        if row["target"] not in wanted or row["region"] not in tree.programs:
            continue
        if tree.covered_by(row["region"], int(row["runtime"], 16)):
            continue
        out.append({
            "file_offset": row["file_offset"], "region": row["region"],
            "runtime": row["runtime"], "listing": "", "movx": "",
            "dptr_source": "unresolved", "xdata_addr": "",
            "helper": row["target"],
            "note": (f"{row['opcode']} booked at this file offset; no listing "
                     f"covers it, so no movx here is decoded"),
        })
    return out


def rows(tree: Tree):
    """`(emitted, unplaced)` -- the table and the count it is not a census of.

    Sorted by file offset so the `0x0D1E3` call-site row lands between its two
    neighbours in the run rather than at the end of the file, which is where a
    reader looking for the shape expects to find it.
    """
    emitted = site_rows(tree)
    helpers = {r["helper"] for r in emitted if r["helper"] is not None}
    emitted += call_site_rows(tree, helpers)
    emitted.sort(key=lambda r: (r["region"], int(r["file_offset"], 16)))
    return emitted, unplaced(tree)


def _movx_row(program: str, stem: str, at: str, oper: str, got: dict) -> dict:
    addr = int(at, 16)
    offset = offset_for_runtime(addr, REGION_OF[program])
    return {
        "file_offset": f"0x{offset:05X}" if offset is not None else "",
        "region": program, "runtime": hexaddr(addr), "listing": stem,
        "movx": "read" if oper.split(",")[0].strip() == "A" else "write",
        "dptr_source": got["dptr_source"],
        "xdata_addr": (hexaddr(got["xdata_addr"])
                       if got["xdata_addr"] is not None else ""),
        "helper": hexaddr(got["helper"]) if got["helper"] is not None else "",
        "note": got["note"],
    }


def csv_table(tree: Tree) -> str:
    """The `--csv` table, as a string, so `--check` diffs the same bytes.

    The CRLF terminator is the csv module's own, matching every committed table
    this repository holds; `check_table()`'s own docstring says why reading one
    with universal newlines would make a check red on committed data.
    """
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\r\n")
    w.writeheader()
    for row in rows(tree)[0]:
        w.writerow(row)
    return buf.getvalue()


def summary(tree: Tree) -> str:
    emitted, unplaced_count = rows(tree)
    by_source = collections.Counter(r["dptr_source"] for r in emitted)
    movers = sum(1 for r in emitted if r["movx"])
    chased = sorted({r["helper"] for r in emitted if r["helper"]})
    return (f"{hexaddr(PAGE_LO)}-{hexaddr(PAGE_HI)}: {movers} movx resolved onto "
            f"the page in the committed listings -- "
            + " ".join(f"{s} {by_source[s]}" for s in sorted(by_source))
            + f" -- plus {len(emitted) - movers} committed call site(s) of a "
              f"chased helper in bytes no listing covers; {unplaced_count} movx "
              f"elsewhere in the tree resolved to no address by this method"
            + (f". Helpers chased: {', '.join(chased)}" if chased else ""))


def check(path: str = CSV_PATH, tree: Tree = None) -> int:
    return check_table(csv_table(tree if tree is not None else Tree()), path)


def _fixture(rows_by_stem) -> Tree:
    """A `Tree` over hand-written listings, for the walk's own cases.

    Built through `__new__` rather than by pointing a `Tree` at a directory,
    so a case can be written as three instructions rather than as three files
    on disk that a later run would have to keep.
    """
    tree = Tree.__new__(Tree)
    tree.programs = {"bank0": rows_by_stem}
    tree.by_entry = {("bank0", int(rows[0][0], 16)): (stem, 0)
                     for stem, rows in rows_by_stem.items() if rows}
    tree.covers_any = {("bank0", int(at, 16)): (stem, index)
                       for stem, rows in rows_by_stem.items()
                       for index, (at, _mnem, _oper) in enumerate(rows)}
    tree.extent = {}
    tree.any_entry = {entry: (name, loc)
                      for (name, entry), loc in tree.by_entry.items()}
    return tree


def self_test() -> int:
    """The walk's own cases: four fixtures for what it must refuse, and the
    four shapes of the committed tree it has to get right.

    The fixtures are inline rather than drawn from the tree because a walk that
    is wrong on a hand-written listing and right on bank0 for the same reason
    is not a walk that can be trusted on bank0 tomorrow. The committed cases are
    still there, because the question the issue asks -- does `0xD319` really
    leave DPTR at `0x0860` for its callers -- is about these bytes.
    """
    failures = []

    def want(label, got, expected):
        if got != expected:
            failures.append(f"{label}: got {got!r}, want {expected!r}")

    tree = Tree()

    def at(stem, addr):
        return next(i for i, row in enumerate(tree.rows("bank0", stem))
                    if row[0] == addr)

    got = resolve(tree, "bank0", "D091", at("D091", "D191"))
    want("the store behind `lcall 0xD319` resolves to 0x0860",
         (got["dptr_source"], got["xdata_addr"], got["helper"]),
         ("callee", 0x0860, 0xD319))
    want("and the listing's own operands make it a write",
         _movx_row("bank0", "D091", "D191", "@DPTR, A", got)["movx"], "write")

    got = resolve(tree, "bank0", "D236", at("D236", "D249"))
    want("the second store behind `lcall 0xD319` resolves the same way",
         (got["dptr_source"], got["xdata_addr"]), ("callee", 0x0860))

    got = resolve(tree, "bank0", "D284", at("D284", "D286"))
    want("a fall-in from the listing above is `predecessor`",
         (got["dptr_source"], got["xdata_addr"], got["helper"]),
         ("predecessor", 0x0860, 0xD281))

    got = resolve(tree, "bank0", "D091", at("D091", "D094"))
    want("a literal in the same listing is `literal`",
         (got["dptr_source"], got["xdata_addr"]), ("literal", 0x0860))

    entry = _fixture({"T": [("8000", "movx", "A, @DPTR")]})
    want("a listing whose entry is the `movx` is unresolved",
         resolve(entry, "bank0", "T", 0)["dptr_source"], "unresolved")

    tail = _fixture({"T": [("8000", "ljmp", "0x8100"),
                           ("8003", "movx", "A, @DPTR")],
                     "U": [("8100", "mov", "DPTR, #0x861"), ("8103", "ret", "")]})
    want("an `ljmp` out of the listing is a tail call and is chased",
         (resolve(tail, "bank0", "T", 1)["dptr_source"],
          resolve(tail, "bank0", "T", 1)["xdata_addr"]),
         ("callee", 0x0861))

    internal = _fixture({"T": [("8000", "ljmp", "0x8003"),
                               ("8003", "movx", "A, @DPTR")]})
    want("an `ljmp` back inside the same listing is a jump, not a tail call",
         (resolve(internal, "bank0", "T", 1)["dptr_source"],
          resolve(internal, "bank0", "T", 1)["xdata_addr"]),
         ("unresolved", None))

    partial = _fixture({"T": [("8000", "mov", "0x83, A"),
                              ("8002", "movx", "A, @DPTR")]})
    want("a one-byte DPTR write establishes no address",
         (resolve(partial, "bank0", "T", 1)["dptr_source"],
          resolve(partial, "bank0", "T", 1)["xdata_addr"]),
         ("unresolved", None))

    recursive = _fixture({"T": [("8000", "lcall", "0x8000"),
                                ("8003", "movx", "A, @DPTR")]})
    got = resolve(recursive, "bank0", "T", 1)
    want("a self-calling callee stops at the chase bound instead of looping",
         (got["dptr_source"], got["xdata_addr"]), ("callee", None))
    if str(MAX_CHASE) not in got["note"]:
        failures.append(f"the chase bound is named in the note: {got['note']!r}")

    for failure in failures:
        print(f"callee_dptr_sites.py --self-test: {failure}", file=sys.stderr)
    if failures:
        print(f"{len(failures)} self-test failure(s)", file=sys.stderr)
        return 1
    print("callee_dptr_sites.py --self-test: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout")
    ap.add_argument("--check", nargs="?", const=CSV_PATH, metavar="PATH",
                    help="diff this run against a committed table and exit "
                         "non-zero on any difference")
    ap.add_argument("--self-test", action="store_true",
                    help="run the walk's own cases over inline fixtures and "
                         "the committed listings")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.csv and args.check is not None:
        ap.error("--csv and --check are the same output two ways; pass one")
    tree = Tree()
    if args.check is not None:
        return check(args.check, tree)
    if args.csv:
        sys.stdout.write(csv_table(tree))
        return 0
    print(summary(tree))
    for row in rows(tree)[0]:
        if row["movx"] and row["dptr_source"] == "literal":
            continue
        print(f"  {row['file_offset']} {row['runtime']} {row['listing'] or '-':<5} "
              f"{row['movx'] or '-':<5} -> {row['xdata_addr'] or '?':<7} "
              f"{row['dptr_source']:<11} {row['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())