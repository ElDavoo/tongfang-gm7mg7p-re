#!/usr/bin/env python3
"""Census the `ITE8850-PD` image at file `0x20000`-`0x2FFFF` of
`ec/firmware/GMxMGxx_11.800`: its layout, its vector table, its string pool
and what references it, its host-facing dispatch surface, and where the image
came from.

`trace_xdata_refs.py` already knows this region, and what it knows it is
deliberately narrow: it treats `0x20000`-`0x2FFFF` as an XDATA *site-labelling
region*, a `region` cell in a row about a `MOV DPTR` site in the main EC. That
is the right question for it and the wrong one for this. This tool asks what
the region *is* -- it is a program, so the questions are a program's questions:
where is its code, what does its reset vector reach, what does it say, what
dispatches on a host-supplied byte, and does the vendor ship it twice.

**The region is not the EC and its addresses are not the EC's.** Every number
here is an address in the PD image's own 64 KiB space, and none of it is
evidence about the EC's XDATA at the same number. `lightbar-bat-flow.md` §2
carries the four independent facts that make it a separate program, and this
tool cross-references them rather than re-deriving them. `discover_vector_table()`
in `build_ec_decompile.py` finds the same six slots this tool reports, and
`ec/ghidra/manifest.csv`'s `pd` row is the committed record that the program is
already the third program of the existing `ec.gpr` -- so the question issue #26
asked about giving it its own project is answered by a census of what is
already there, not by a decision.

**The vector table is read, and the read is not the textbook one.** A
hardcoded list of standard 8051 offsets would produce a table that looks
plausible and is wrong. This image puts the reset vector at `0x00` and then
pads each of the five interrupt entries to an 8-byte stride, so the entries are
at `0x00` and `0x03 + n * 8` -- six of them, with `0x2B`-`0x3F` erased. The
3-byte `LJMP` is what makes each a real entry; a `0xFF` byte is not an entry and
the walk stops there.

**A null in this tool is a statement about a search, never about the firmware.**
Every census below is a byte scan or a read of a committed file, and each one
reports what it looked for and where. `unreferenced by this method` is the
token, `absent` never is, and `read_region()` refuses a dump whose marker is not
where this one is rather than reporting an empty region -- the same contract
`trace_xdata_refs.py:region_of()` implements when `PD_MARKER` fails. The
string-pool result is the one that needs it most: 43 NUL-terminated printable
candidates, **zero** of them named by a `MOV DPTR` + `MOVC` pair, and a byte
pair that does not appear anywhere in the image for any of them. That is a
finding about a method, and it is worth exactly what the method is worth.

**What the string-pool null does *not* say.** It does not say the strings are
unreachable. `MOV DPTR,#imm16` is a literal load, and this firmware computes
pointers into its own CODE in at least three other ways that this scan cannot
see -- a `DPTR` carried in from a caller, a `DPTR` built arithmetically, and a
`jmp @a+dptr` through a table whose address is a caller's return address
(`0x119C dispatch_code_table` and `0x11C2 dispatch_code_table_2byte_key`).
`pd-0x38-consumers.md` already records the second for this program. The third
is the most plausible route from a literal in the image to a string, so it is
**measured** rather than only listed: all 25 `lcall` sites of the two
dispatchers, and 0 of their inline tables opens a pool entry
(`code_table_inline_tables()`). The count is an upper bound on the literal
form, not a bound on the references.

**The provenance half is a positive result and is stated as one.** A grep over
`vendor/bios-1.09/` returns nothing, and *that* is an artefact: every member
large enough to hold the marker is DEFLATE, so the bytes are not in the
container. Inflating the members says the same 64 KiB region ships twice -- once
in `GMxMGxx_11.800`, which is byte-identical to the committed
`ec/firmware/GMxMGxx_11.800`, and five times inside the 13 MiB SPI image
`GMxMGxxN109A08.ROM` -- and that `ecflash.nsh` is a 29-byte line writing the
whole 256 KiB, so the PD firmware ships with the **EC update**, not only with
the BIOS. A compression artefact read as an absence is the exact failure
`docs/findings.md` §4 records twice, so the inflation is what the answer rests
on and `provenance()` says so.

Usage:
    python3 ec/tools/pd_image_census.py
    python3 ec/tools/pd_image_census.py --section vector
    python3 ec/tools/pd_image_census.py --csv > ec/annotations/pd-image-strings.csv
    python3 ec/tools/pd_image_census.py --check
    python3 ec/tools/pd_image_census.py --self-test

`--check` regenerates `../annotations/pd-image-strings.csv` and diffs it, then
re-derives every figure `../annotations/pd-image.md` states in its pinned
figures block and exits non-zero on any difference. Nothing here needs Ghidra,
a network, or hardware: every input is a committed file.
"""
import argparse
import collections
import csv
import difflib
import hashlib
import io
import os
import re
import sys
import zipfile

from disasm8051 import OPCODE_LEN, mnemonic

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
ANNOT = os.path.join(HERE, os.pardir, "annotations")
DECOMPILED = os.path.join(HERE, os.pardir, "decompiled", "pd")
FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")
VENDOR_ZIP = os.path.join(REPO, "vendor", "bios-1.09", "BIOS_1.09.zip")
FUNCTIONS_CSV = os.path.join(ANNOT, "ghidra-functions.csv")
STRINGS_CSV = os.path.join(ANNOT, "pd-image-strings.csv")
PAGE = os.path.join(ANNOT, "pd-image.md")

# The region, and the marker that says what is in it. Both from
# trace_xdata_refs.py's REGIONS/PD_MARKER, restated rather than imported: that
# tool is not grown for this, and its numbers are the ones
# lightbar-bat-flow.md §2 and findings.md §3a already cite. A dump that does
# not carry the marker is a different dump, and read_region() refuses it.
REGION_OFF = 0x20000
REGION_LEN = 0x10000
PD_MARKER_OFF = 0x20040
PD_MARKER = b"ITE8850-PD"

# The vector table's own geometry, discovered rather than assumed. `0x00` holds
# the reset `LJMP`; the five interrupt entries follow at an 8-byte stride from
# `0x03`, so `0x03 + n * 8`. 8-aligning the whole table instead reads the
# padding between entries, and on this image that leaves the reset vector as the
# only entry it recovers -- the other five come back as 0xFF runs. The test
# pins those wrong answers, so an edit that "fixed" the walk to be 8-aligned
# goes red rather than producing a table that looks plausible.
VECTOR_RESET = 0x00
VECTOR_STRIDE = 8
VECTOR_FIRST = 0x03
VECTOR_SCAN_END = 0x40

# The token for a null. Spelled out because the word is the whole point: a byte
# scan that found nothing has found nothing *about itself*, and every cell fed
# by one of them carries this instead of an empty string that would read as an
# answer.
NOT_FOUND = "not found by this method"

# 0x22 is `RET` and is also the printable character `"`, which is why three
# pool candidates in this image start with one. The scan treats it as a
# character and the `after_nul` column is what tells a reader which boundary a
# candidate starts on, rather than the scan guessing on its behalf.
PRINTABLE = frozenset(range(0x20, 0x7F))
MIN_STRING = 4

# The three vendor members the provenance half reads. Named rather than found
# by a glob so a kit with a different layout is *refused* with the member it
# wanted, instead of quietly reporting on whichever file happened to sort
# first -- the refusal is `provenance()`'s job and a name it has to be given.
EC_MEMBER = "GM7MG7P/GMxMGxx_11.800"
ROM_MEMBER = "GM7MG7P/GMxMGxxN109A08.ROM"
NSH_MEMBER = "GM7MG7P/ecflash.nsh"

# Where the embedded EC image sits in the 13 MiB SPI image. A constant, and the
# only one in this file: `provenance()` searches for it and *checks* the search
# against this, because "the whole 256 KiB EC image occurs at `0x43CA2C`" is a
# claim worth a red if the search ever stops agreeing with it. The five region
# copies are deliberately **not** pinned here -- they are a search result, at a
# `0x40020` stride, and a re-cut ROM that moved them should be reported rather
# than rejected. The suite pins their offsets by value instead, which is where
# a pin belongs when the value is not something the tool needs.
EC_IN_ROM = 0x43CA2C

# The XDATA addresses the host-facing half looks for, and what they are. Not
# names: the region is a separate program, so nothing here may be labelled from
# the EC's register map, and a name in this file would be a claim about a
# program this tool only knows the bytes of.
HOST_BLOCK = (0xFF80, 0xFFE0, 0xFFE1, 0xFFE2, 0xFFE3, 0xFFD0, 0xFFD1, 0xFFD5)

MOV_DPTR = 0x90
MOVC_ABS = 0x93
LJMP = 0x02
LCALL = 0x12
PUSH_DIRECT = 0xC0
ERASED = 0xFF

# Unconditional transfers that end a linear walk. `lcall` is deliberately not
# in it: interrupt_handover() steps over the wrapper's `lcall 0x0050` to reach
# the `reti` past it, which is the whole reason that walk exists.
TRANSFER_END = frozenset((0x02, 0x22, 0x32, 0x73))

# How far past a `MOV DPTR,#imm16` a `MOVC` still counts as mediated by it.
# Four instructions is the shape Keil and SDCC both emit for a string copy
# (`mov dptr,#str` / `clr a` / `movc a,@a+dptr` / ...), and the window is
# reported alongside every count so a reader can widen it.
MOVC_WINDOW = 4


class Refusal(Exception):
    """A dump that this tool will not describe, and why.

    Raised rather than returned, because every caller of `read_region()` has
    nothing useful to say about a dump without the marker: there is no report
    to print and no table to check. The message is the reason, and it names
    the offset, so the refusal reads as a measurement.
    """


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below."""
    return os.path.relpath(path, REPO)


# --------------------------------------------------------------------------
# The region


def read_region(firmware: str = FIRMWARE):
    """(the 64 KiB PD image, how it was identified) or raise Refusal.

    The marker is *checked*, not assumed, and a dump without it is refused
    rather than reported as an empty region: a refusal that names the offset
    is a measurement, and an empty table is not. This is the same contract
    `trace_xdata_refs.py:region_of()` implements when `PD_MARKER` fails, and
    the suite pins it as a case rather than trusting it to hold.
    """
    with open(firmware, "rb") as f:
        dump = f.read()
    if len(dump) < REGION_OFF + REGION_LEN:
        raise Refusal(f"{repo_path(firmware)} is {len(dump)} bytes, too short "
                      f"to hold a region at 0x{REGION_OFF:05X}-"
                      f"0x{REGION_OFF + REGION_LEN - 1:05X}; not described")
    found = dump[PD_MARKER_OFF:PD_MARKER_OFF + len(PD_MARKER)]
    if found != PD_MARKER:
        raise Refusal(
            f"no {PD_MARKER.decode()!r} marker at file 0x{PD_MARKER_OFF:05X} in "
            f"{repo_path(firmware)} -- found {found!r} there. Whatever is at "
            f"0x{REGION_OFF:05X} in that dump is not this image, and this tool "
            f"describes only this one; it will not report the region as empty")
    return dump[REGION_OFF:REGION_OFF + REGION_LEN], (
        f"marker {PD_MARKER.decode()!r} read at file 0x{PD_MARKER_OFF:05X}")


def digest(data: bytes) -> str:
    """The full sha256 hex of `data`.

    A wrapper rather than a bare call so `--check` pins one spelling: the
    abbreviated `158d1c64...` the documents quote is a truncation, and a
    truncated digest in a check is a digest that cannot fail.
    """
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# Vector table


def vector_table(region: bytes):
    """[(entry offset, target)] for the whole table, reset vector first.

    Walked, not looked up. `0x00` is the reset entry; the interrupt entries
    follow at `VECTOR_FIRST + n * VECTOR_STRIDE` and the walk stops at the
    first byte that is not `LJMP` -- here the erased `0xFF` padding at `0x2B`,
    which is why the table is six entries and not the eight a stride-8 walk
    from `0x00` would print.

    8-aligning the *whole* table is the error worth naming, because it does not
    look like one: it reads `0x00`, `0x08`, `0x10`, ..., and on these bytes that
    finds an `LJMP` at `0x00` and nothing at the other five. The result is a
    one-entry table -- a plausible-looking answer to the question, from a table
    that is not this table.
    """
    out = []
    if len(region) < 3 or region[VECTOR_RESET] != LJMP:
        return out
    out.append((VECTOR_RESET, (region[1] << 8) | region[2]))
    off = VECTOR_FIRST
    while off + 2 < VECTOR_SCAN_END and region[off] == LJMP:
        out.append((off, (region[off + 1] << 8) | region[off + 2]))
        off += VECTOR_STRIDE
    return out


def erased_after_table(region: bytes, table) -> str:
    """What lies between the last vector entry and the first code, as a phrase.

    A reader who has been told the table stops somewhere wants to know what is
    in the gap, and "0xFF padding" is the answer this returns -- or, on a
    region whose gap is not erased, the bytes that are there instead.
    """
    if not table:
        return "no vector table read"
    last = table[-1][0] + 3
    gap = region[last:VECTOR_SCAN_END]
    if gap and all(b == ERASED for b in gap):
        return f"0x{last:02X}-0x{VECTOR_SCAN_END - 1:02X} erased (0xFF)"
    return f"0x{last:02X}-0x{VECTOR_SCAN_END - 1:02X} not wholly 0xFF: {gap.hex(' ')}"


# --------------------------------------------------------------------------
# The committed program: which function owns an address
#
# The extent map is read from ec/decompiled/pd/*.asm rather than from the
# annotations CSV, and the reason is a disagreement worth having rather than
# papering over: the CSV carries 498 pd rows and the export has 535 functions.
# An address inside a function with no row would be attributed to nothing by a
# CSV-keyed lookup and to the wrong function by a nearest-preceding-start
# lookup, so the listings -- which say which addresses each function actually
# holds -- are the authority, and a site no listing holds is reported as
# outside the committed listings rather than guessed at.


_EXTENTS = None


def function_extents():
    """{entry address: frozenset(addresses)} over `ec/decompiled/pd/*.asm`.

    Parsed once per process and cached, because every referrer attribution in
    the report goes through it and 535 files is not a per-site cost. The
    address pattern is the listing's own column, anchored to the start of a
    line so a `0x1234` inside a comment is not read as an address.
    """
    global _EXTENTS
    if _EXTENTS is not None:
        return _EXTENTS
    out = {}
    try:
        listing_names = sorted(os.listdir(DECOMPILED))
    except OSError as e:
        raise Refusal(f"cannot read {repo_path(DECOMPILED)}: {e}")
    for name in listing_names:
        if not name.endswith(".asm"):
            continue
        try:
            entry = int(name[:-4], 16)
        except ValueError:
            continue
        with open(os.path.join(DECOMPILED, name), encoding="utf-8",
                  errors="replace") as f:
            body = f.read()
        addrs = frozenset(int(m.group(1), 16)
                          for m in re.finditer(r"^([0-9A-Fa-f]{4})\s", body,
                                                re.M))
        if addrs:
            out[entry] = addrs
    _EXTENTS = out
    return out


def address_owners(extents):
    """{address: entry} built from every listing, for a one-lookup attribution.

    The export's bodies can overlap -- `pd,0xC873` in `ghidra-functions.csv`
    says so in its own comment, and `pd,0x0180` in the same file records a
    `0x104D` that "is not in this listing" -- so an address can be in more than
    one listing and a plain dict would keep whichever it saw last. The rule is
    stated rather than accidental: **the latest-starting owner wins**, because
    a listing that begins at or below an address is the one whose body the
    export meant to be reading there, and the earlier-starting listing is
    holding bytes as spillover.

    Returning the winner alone would hide the overlap, so `overlaps()` is the
    way to see it, and the test suite pins the rule rather than the winner.

    **No module-level cache here, deliberately.** A cached map keyed on nothing
    is a function of its first call rather than of its argument, so a caller
    passing a different `extents` -- a test, or a future second program -- gets
    the first answer back with no complaint. The cost of rebuilding is one pass
    over 535 small frozensets, paid once in `main()`; `owning_function()` is
    the per-site hot path and it reads the map it is handed.
    """
    owners = {}
    for entry, addrs in extents.items():
        for addr in addrs:
            held = owners.get(addr)
            if held is None or entry > held:
                owners[addr] = entry
    return owners


def overlaps(extents):
    """{address: sorted(entries)} for the addresses two or more listings hold.

    The census that makes the "latest-starting owner wins" rule in
    `address_owners()` checkable rather than asserted, and it is cheap because
    it shares the parsed extents.
    """
    seen = collections.defaultdict(list)
    for entry, addrs in extents.items():
        for addr in addrs:
            seen[addr].append(entry)
    return {a: sorted(v) for a, v in seen.items() if len(v) > 1}


def function_names():
    """{address: name} for the pd-scoped rows of `ghidra-functions.csv`.

    Read separately from the extents on purpose -- 498 of the 535 -- so a
    function the export has and the CSV does not is *named* by its listing
    header rather than left anonymous. `function_name()` does the fallback.
    """
    with open(FUNCTIONS_CSV, newline="") as f:
        return {int(r["addr"], 16): r["name"]
                for r in csv.DictReader(f) if r["scope"] == "pd"}


def listing_name(entry: int):
    """The name in a function's own `.asm` header, or None."""
    path = os.path.join(DECOMPILED, f"{entry:04X}.asm")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = f.readline()
    except OSError:
        return None
    m = re.match(r"^;\s*pd\s*@\s*[0-9A-Fa-f]{4}\s+(\S+)", head)
    return m.group(1) if m else None


def function_name(entry: int, names) -> str:
    """The best name for a function entry: the CSV row, else its own header."""
    return names.get(entry) or listing_name(entry) or f"unnamed_{entry:04X}"


def owning_function(addr: int, owners, names):
    """(entry, name) of the listing that holds `addr`, or a reason.

    Membership in a listing's own address set, and not "the nearest function
    start at or below it": the export's bodies overlap, so the nearest-start
    rule attributes a site to a function that demonstrably does not contain it.
    The third return value is what to print when no listing holds the address,
    and it is a real answer rather than a gap -- the export's coverage is 535
    functions, not the whole 64 KiB.
    """
    entry = owners.get(addr)
    if entry is None:
        return None, None, "outside the committed pd listings"
    return entry, function_name(entry, names), None


# --------------------------------------------------------------------------
# String pool


def string_candidates(region: bytes):
    """[(start, text, run_head, after_nul)] for every pool candidate.

    Mechanical, and the docstring says what mechanical means: a candidate is a
    run of printable-or-NUL bytes containing a NUL-terminated piece of at least
    `MIN_STRING` printable characters. A region that is mostly code produces
    false candidates from code that happens to be printable -- this image has
    three (`"NaN`, `+INF`, `-INF`, which are float-formatting fragments whose
    bytes collide with XDATA addresses -- see #181) and they are *kept*, because
    a filter that guessed which candidates were real would be the tool making
    the finding.

    `after_nul` is the column that lets a reader tell the two apart without the
    tool ruling on it: a candidate starting right after a NUL is a genuine
    pool entry whatever it says, and one starting at the head of a run may have
    swallowed an opcode.
    """
    out = []
    i = 0
    while i < len(region):
        if region[i] in PRINTABLE or region[i] == 0:
            j = i
            while j < len(region) and (region[j] in PRINTABLE
                                       or region[j] == 0):
                j += 1
            k = i
            after_nul = False
            for part in region[i:j].split(b"\x00"):
                n = len(part)
                if (n >= MIN_STRING and all(c in PRINTABLE for c in part)
                        and k + n < len(region) and region[k + n] == 0):
                    out.append((k, part.decode("ascii"), i, after_nul))
                k += n + 1
                after_nul = True
            i = j
        else:
            i += 1
    return out


def dptr_sites(region: bytes, addr: int):
    """Every `MOV DPTR,#imm16` in `region` whose immediate is `addr`.

    The one shape this census is built on, and the reason for the report's
    whole vocabulary of careful phrasing: on an 8051 this instruction is
    byte-identical whether the pointer is going to be used for `MOVX` or for
    `MOVC`, and nothing in the instruction says which. #181 makes the point for
    this repository. So a site here is a *candidate* and only the `MOVC` in
    the following window turns it into a reference.
    """
    hi, lo = addr >> 8, addr & 0xFF
    return [i for i in range(len(region) - 2)
            if region[i] == MOV_DPTR and region[i + 1] == hi
            and region[i + 2] == lo]


def movc_follows(region: bytes, site: int, window: int = MOVC_WINDOW) -> bool:
    """Whether a `MOVC` appears within `window` bytes after a `MOV DPTR` site.

    A linear forward walk, not a decode: it reads instruction lengths from
    `disasm8051.py`'s table and stops at the first control-flow opcode, so a
    `MOVC` reached only by falling into it from elsewhere does not count. That
    makes the count an upper bound on the mediated form and the doc says so
    where it quotes the number.
    """
    i = site + 3
    end = min(len(region), site + 3 + window)
    while i < end:
        n = OPCODE_LEN[region[i]]
        if i + n > len(region):
            return False
        if region[i] == MOVC_ABS:
            return True
        if region[i] in TRANSFER_END or region[i] & 0x1F in (0x01, 0x11):
            return False
        i += n
    return False


def string_rows(region: bytes, owners, names):
    """The whole pool census, one dict per candidate.

    `movc_referrers` and `dptr_sites` are the two halves of the #181
    collision, kept apart for that reason. A `dptr_sites` count with no
    `movc_referrers` is a DPTR load of a number that happens to equal a
    string's address, and the report says that in words rather than leaving the
    two columns to be read as one.
    """
    rows = []
    for start, text, run_head, after_nul in string_candidates(region):
        sites = dptr_sites(region, start)
        referrers = [s for s in sites if movc_follows(region, s)]
        cells = []
        for s in referrers:
            entry, name, why = owning_function(s, owners, names)
            cells.append(f"0x{s:04X}@{name}" if entry
                         else f"0x{s:04X}@{why}")
        rows.append({
            "string": text,
            "region_offset": f"0x{start:04X}",
            "file_offset": f"0x{REGION_OFF + start:05X}",
            "run_head": f"0x{run_head:04X}",
            "after_nul": "yes" if after_nul else "no",
            "movc_referrers": " ".join(cells) if cells else NOT_FOUND,
            "dptr_sites": str(len(sites)),
            "verdict": "referenced by this method" if referrers else NOT_FOUND,
        })
    return rows


COLUMNS = ["string", "region_offset", "file_offset", "run_head", "after_nul",
           "movc_referrers", "dptr_sites", "verdict"]


def csv_table(region: bytes, owners, names) -> str:
    """The `pd-image-strings.csv` table as a string, for `--check` to diff.

    A string rather than a write to stdout, for the reason
    `trace_xdata_refs.py:csv_table()` gives: `--check` compares the same bytes
    this prints, and the committed file is the product of the command the page
    names. Written with the csv module's own dialect, so the committed file
    carries its CRLF terminator and `--check` reads it with `newline=""` --
    universal-newline translation would rewrite every row and report a
    difference on every run, which is a check nobody trusts.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for row in string_rows(region, owners, names):
        w.writerow([row[c] for c in COLUMNS])
    return buf.getvalue()


# --------------------------------------------------------------------------
# Layout


def layout(region: bytes):
    """(used_end, ff_total, longest_ff_run) for the 64 KiB region.

    Three numbers and no interpretation, because the interpretation is the
    page's job and this is the measurement the page quotes. `used_end` is the
    highest offset that is not `0xFF`, which is the one number a reader wants
    and the one a "size" figure would blur.
    """
    ff_total = sum(1 for b in region if b == ERASED)
    used_end = max((i for i, b in enumerate(region) if b != ERASED), default=-1)
    longest = run = 0
    for b in region:
        run = run + 1 if b == ERASED else 0
        longest = max(longest, run)
    return used_end, ff_total, longest


def interrupt_handover(region: bytes, target: int):
    """(dptr_immediate, callee, push_count) for a vector's target routine.

    A vector entry on this image is a wrapper: save the register file, load
    DPTR with a per-vector CODE address, `lcall` one shared body, restore,
    `reti`. Reading the DPTR immediate out of the wrapper is what turns six
    near-identical rows into a table, and it is a walk over
    `disasm8051.py`'s lengths rather than a hardcoded offset into the body --
    the same reason the vector table itself is walked.

    A linear fall-through walk, so an `lcall` is stepped *over* (recording the
    callee) rather than followed, and an unconditional transfer ends it.
    Conditional branches are stepped over too, which is the linear reading and
    not a control-flow claim: the number is what the straight line at the
    vector's head says, and the page says so where it quotes it.

    None for a target that is not that shape, which is a real answer: the reset
    vector's target is the C startup stub and offers no DPTR.
    """
    i = target
    dptr = callee = None
    pushes = 0
    seen = set()
    while i < len(region) and i not in seen and len(seen) < 128:
        seen.add(i)
        n = OPCODE_LEN[region[i]]
        if i + n > len(region):
            break
        op = region[i]
        if op == MOV_DPTR and dptr is None:
            dptr = (region[i + 1] << 8) | region[i + 2]
        elif op == LCALL and callee is None:
            callee = (region[i + 1] << 8) | region[i + 2]
        elif op == PUSH_DIRECT:
            pushes += 1
        elif op in TRANSFER_END:
            break
        i += n
    if dptr is None or callee is None:
        return None
    return dptr, callee, pushes


def vector_pointer_table(region: bytes, owners, names):
    """[(vector, code, sites, (entry, name) per site)] for the interrupt vectors.

    The half of §2 the vector table alone does not say, and the one positive
    referrer result in this tool: each of the five interrupt entries is a
    wrapper that loads DPTR with its own CODE address and calls one shared
    body, `0x0050 call_10f1_then_jmp_1229`, which reads three CODE bytes at
    that address and jumps to them. So the five wrappers dispatch through a
    table of CODE constants, and the CODE address is the per-vector selector.
    The wrapper names in `ghidra-functions.csv` already say "the CODE address
    0x0151"; this is the census's reading of the same bytes, and the two agree.

    `pd-base-strides.csv` already lists `0x0151`/`0x0154`/`0x0157`/`0x015A`/
    `0x015D` among its 448 `unresolved` XDATA bases and says what they are not
    -- that CSV is a scan of `MOV DPTR` immediates and cannot know which space
    the program means by one, so it is not contradicted here. The site count is
    the checkable part: one site each, and the same one, so "the vector table is
    a table" is a measurement rather than a shape someone saw.
    """
    out = []
    for off, target in vector_table(region):
        hand = interrupt_handover(region, target)
        if hand is None:
            continue
        dptr = hand[0]
        sites = dptr_sites(region, dptr)
        readers = []
        for s in sites:
            entry, name, why = owning_function(s, owners, names)
            readers.append((entry, name or why))
        out.append((off, dptr, len(sites), readers))
    return out


# The two CODE-table dispatchers, and why this file searches for their call
# sites. Both take DPTR from the *popped return address*, so the table they
# walk is the caller's inline argument bytes -- which means every table in the
# program is a literal in the image, and a string pointer would be a literal
# too. That makes these the most plausible remaining route from a call site to
# a string, and a route worth *measuring* rather than only listing: 25 sites,
# and the count of how many of their inline bytes are printable.
CODE_TABLE_DISPATCHERS = (0x119C, 0x11C2)
INLINE_TABLE_BYTES = 4


def code_table_inline_tables(region: bytes, width: int = INLINE_TABLE_BYTES):
    """[(dispatcher, site, inline bytes, opens_a_pool_entry)] for both.

    The bytes immediately after a `lcall` are what the dispatcher reads — it
    pops the return address into DPTR and starts `movc a,@a+dptr` at
    `site + 3` — so those bytes are the table, and a table that began with a
    NUL-terminated printable run would be a string.

    That last column is the measurement, and it is **0 for all 25 sites**.
    Counting *printable bytes* instead would be the wrong test and reads 8 of
    9 and 11 of 16 on this image, because a structured record
    (`01 20 4c 1f`, `02 07 54 17`) is mostly bytes that happen to be printable.
    The question is not "are these bytes printable" but "does the dispatcher's
    first `movc` read text", and the way to answer that is to ask
    `string_candidates()` whether `site + 3` opens a pool entry.

    **A statement about these 25 sites and these 4 bytes.** A wider window, or
    a table reached by a `jmp @a+dptr` from somewhere else, is a different
    measurement, and the page quotes this one rather than the generalisation.
    """
    pool_starts = {start for start, _, _, _ in string_candidates(region)}
    out = []
    for target in CODE_TABLE_DISPATCHERS:
        pat = bytes([LCALL, target >> 8, target & 0xFF])
        i = region.find(pat)
        while i != -1:
            tail = region[i + 3:i + 3 + width]
            out.append((target, i, tail, (i + 3) in pool_starts))
            i = region.find(pat, i + 1)
    return out


# --------------------------------------------------------------------------
# Host-facing surface

def command_surface(names):
    """(by type, dispatch rows) over the pd-scoped annotation rows.

    Read from `ghidra-functions.csv` rather than derived from the bytes, and
    the two are kept visibly apart: this is a census of *what has already been
    decoded and annotated*, so a row that is not there is a gap in the
    annotation layer, not a gap in the firmware. The report says which of the
    two a number is.
    """
    with open(FUNCTIONS_CSV, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["scope"] == "pd"]
    by_type = collections.Counter(r["type"] for r in rows)
    dispatch = [(int(r["addr"], 16), r["name"]) for r in rows
                if r["type"] == "dispatch"]
    dispatch.sort()
    return len(rows), by_type, dispatch


def host_block_sites(region: bytes):
    """{XDATA address: number of `MOV DPTR` sites} for `HOST_BLOCK`.

    The host-facing question the issue asked -- an I2C/SMBus or EC-mailbox
    dispatch table -- reduces, on static evidence, to "which XDATA addresses
    does this program read and write". These eight are the ones this
    repository's committed annotations already point at (`0xA8AE`
    `event_dispatch_ff80_ffe0` and `0xF477`, `0xF5D1`), and the count is a
    `MOV DPTR` census, not an access census: it says where the program names
    the address, and `trace_xdata_refs.py` is the tool that says what it does
    with it. **Not found by this method** is the token for a zero, and it is
    what a zero prints.
    """
    return {a: len(dptr_sites(region, a)) for a in HOST_BLOCK}


# --------------------------------------------------------------------------
# Provenance


def provenance(zip_path: str = VENDOR_ZIP):
    """The vendor-side question, answered by inflating rather than grepping.

    Returns a dict of the findings and the numbers `pd-image.md` pins. Every
    one is measured here rather than transcribed.

    The container is the first trap and it is worth being exact about, because
    the first draft of this was not: a `grep` over the zip finds nothing, and
    the reason is compression, not absence. **Every member large enough to
    hold the marker is DEFLATE** -- the 64 KiB EC image, the 13 MiB ROM, the
    three EFI binaries, `bootX64.efi` and `flashme.nsh`. The one member stored
    uncompressed is `GM7MG7P/ecflash.nsh`, 29 bytes of plaintext, and it does
    not contain the marker either. So "every non-empty member is DEFLATE" is
    the wrong sentence and this function does not say it; the load-bearing half
    is that a reader has to inflate the members before the question has an
    answer, which is one step different from a grep and changes the result.
    """
    try:
        z = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as e:
        raise Refusal(f"cannot read {repo_path(zip_path)}: {e}")
    try:
        ec_member = z.read(EC_MEMBER)
        rom = z.read(ROM_MEMBER)
        nsh = z.read(NSH_MEMBER)
    except KeyError as e:
        raise Refusal(f"{repo_path(zip_path)} has no member {e}, so the "
                      f"provenance question is not answerable from it")

    with open(FIRMWARE, "rb") as f:
        committed = f.read()

    region = ec_member[REGION_OFF:REGION_OFF + REGION_LEN]
    copies = find_all(rom, region)
    ec_in_rom = find_all(rom, ec_member)
    return {
        "zip": repo_path(zip_path),
        "ec_member": EC_MEMBER,
        "ec_member_sha256": digest(ec_member),
        "ec_member_is_committed": ec_member == committed,
        "committed_sha256": digest(committed),
        "region_sha256": digest(region),
        "region_in_ec_member": ec_member[PD_MARKER_OFF:
                                         PD_MARKER_OFF + len(PD_MARKER)]
                                == PD_MARKER,
        "rom_member": ROM_MEMBER,
        "rom_size": len(rom),
        "rom_region_copies": [f"0x{o:06X}" for o in copies],
        "rom_region_copy_count": len(copies),
        "rom_ec_image_at": [f"0x{o:06X}" for o in ec_in_rom],
        "rom_ec_image_is_committed": ec_in_rom == [EC_IN_ROM]
                                      and rom[ec_in_rom[0]:
                                              ec_in_rom[0] + len(ec_member)]
                                      == committed,
        "nsh_member": NSH_MEMBER,
        "nsh_text": nsh.decode("ascii", "replace").strip(),
        # The provenance table's "the other N members" row is a count, and a
        # count written in prose is a count that drifts. It is derived here
        # instead: every non-empty member the container holds, less the two the
        # table names. `infolist()` already enumerates them, so this costs
        # nothing and cannot fall behind the zip.
        "zip_member_count": sum(1 for i in z.infolist() if i.file_size),
        "zip_other_members": sum(1 for i in z.infolist() if i.file_size
                                 and i.filename not in (EC_MEMBER, ROM_MEMBER)),
    }


def find_all(haystack: bytes, needle: bytes):
    """Every offset `needle` occurs at in `haystack`, ascending.

    `bytes.find` in a loop rather than a single `in` test, because the number
    of copies *is* the finding: one copy in the SPI image would say something
    different from five, and a tool that reported only the first would make
    those two the same result.
    """
    out = []
    i = haystack.find(needle)
    while i != -1:
        out.append(i)
        i = haystack.find(needle, i + 1)
    return out


# --------------------------------------------------------------------------
# The page's pinned figures


def pinned_figures(path: str = PAGE):
    """{key: value} from the page's pinned figures block.

    A fenced block of `key = value` lines that `--check` re-derives. The block
    exists because a figure written down in prose is not a figure anything
    holds: `docs/findings/xdata-census-rederivation-checklist.md` §2b is the
    argument, and `check_doc_figure_pins.py` the measurement of how much of the
    tree is unpinned. Pinning the page's numbers to a table this tool rebuilds
    from the bytes is the cheap half of the answer.
    """
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise Refusal(f"cannot read {repo_path(path)}: {e}")
    m = re.search(r"```text\n# pd-image-census pinned figures\n(.*?)```",
                  text, re.S)
    if m is None:
        raise Refusal(f"{repo_path(path)} has no `pd-image-census pinned "
                      f"figures` block for --check to read")
    out = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def figures(region: bytes, owners, names, prov, extents=None) -> dict:
    """Every figure `pd-image.md` states, re-derived from the bytes.

    Keys are the page's, not this tool's, and the page is written against
    them. A key the page pins and this does not produce is a missing figure,
    and a key this produces and the page does not pin is a figure the page
    could drift on -- both are failures, because a `--check` that only walks
    the page's keys cannot notice the second kind.
    """
    used_end, ff_total, longest_ff = layout(region)
    table = vector_table(region)
    rows, by_type, dispatch = command_surface(names)
    pool = string_rows(region, owners, names)
    vectors = []
    for off, target in table:
        hand = interrupt_handover(region, target)
        vectors.append(f"0x{off:02X}->0x{target:04X}"
                       + (f"@dptr0x{hand[0]:04X},lcall0x{hand[1]:04X}"
                          f",pushes{hand[2]}" if hand else "@c_startup"))
    host = host_block_sites(region)
    # The identity strings as the page spells them, which is trimmed: the
    # image's own `ProtoVer:01.00 ` carries a trailing space before its NUL,
    # and the page quotes the version and not the padding. The CSV keeps the
    # byte, so both spellings are on the record.
    identity = " ".join(
        f"{r['string'].strip()}@{r['region_offset']}" for r in pool
        if r["region_offset"] in ("0x0040", "0x0160", "0x0170", "0xE1C0"))
    return {
        "region_offset": f"0x{REGION_OFF:05X}",
        "region_length": str(REGION_LEN),
        "region_sha256": digest(region),
        "firmware_sha256": digest(open(FIRMWARE, "rb").read()),
        "used_end": f"0x{used_end:04X}",
        "erased_tail": f"0x{used_end + 1:04X}-0x{REGION_LEN - 1:04X}",
        "ff_bytes": str(ff_total),
        "longest_ff_run": str(longest_ff),
        "vector_entries": str(len(table)),
        "vectors": " ".join(vectors),
        "vector_gap": erased_after_table(region, table),
        "vector_code": " ".join(
            f"0x{dptr:04X}={n}site"
            + ("" if n else f"({NOT_FOUND})")
            + ("@" + ",".join(name for _, name in readers) if readers else "")
            for _, dptr, n, readers in vector_pointer_table(region, owners,
                                                             names)),
        "pool_candidates": str(len(pool)),
        "pool_referrers": str(sum(1 for r in pool
                                  if r["verdict"] == "referenced by this method")),
        "code_table_inline": " ".join(
            f"0x{target:04X}={sum(1 for r in tables if r[0] == target)}site/"
            f"{sum(1 for r in tables if r[0] == target and r[3])}open_a_string"
            for target in CODE_TABLE_DISPATCHERS
            for tables in [code_table_inline_tables(region)]),
        "identity_strings": identity,
        "pd_listings": str(len(extents if extents is not None
                               else function_extents())),
        "pd_listing_overlaps": str(len(overlaps(extents
                                                if extents is not None
                                                else function_extents()))),
        "pd_annotation_rows": str(rows),
        "pd_dispatch_rows": str(len(dispatch)),
        "host_block": " ".join(f"0x{a:04X}={host[a]}" for a in HOST_BLOCK),
        "prov_ec_member_sha256": prov["ec_member_sha256"],
        "prov_ec_member_is_committed": str(prov["ec_member_is_committed"]),
        "prov_region_in_ec_member": str(prov["region_in_ec_member"]),
        "prov_rom_size": str(prov["rom_size"]),
        "prov_rom_region_copies": " ".join(prov["rom_region_copies"]),
        "prov_rom_region_copy_count": str(prov["rom_region_copy_count"]),
        "prov_rom_ec_image_at": " ".join(prov["rom_ec_image_at"]),
        "prov_rom_ec_image_is_committed":
            str(prov["rom_ec_image_is_committed"]),
        "prov_nsh": prov["nsh_text"],
        "prov_zip_members": str(prov["zip_member_count"]),
        "prov_zip_other_members": str(prov["zip_other_members"]),
    }


# --------------------------------------------------------------------------
# --check


def check_table(generated: str, path: str) -> int:
    """Exit code for the CSV half of `--check`: 0 when this run reproduces it.

    Read with `newline=""` so the comparison is the bytes on disk -- see
    `csv_table()`'s note on the CRLF terminator.
    """
    try:
        with open(path, newline="") as f:
            on_disk = f.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if generated == on_disk:
        print(f"{repo_path(path)}: this run reproduces it byte for byte "
              f"({generated.count(chr(10))} lines)")
        return 0
    print(f"note: {repo_path(path)} differs from what this run produced; the "
          f"file is the product of the command on the page that names it, so "
          f"regenerate rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(),
                                     generated.splitlines(),
                                     "committed", "generated", lineterm="",
                                     n=0):
        print(line, file=sys.stderr)
    return 1


def check_figures(pinned, derived) -> int:
    """Exit code for the page's figures: 0 when every one re-derives.

    Walks the *union* of both key sets, and that is the half that matters. A
    check that only walked the page's keys would report clean on a page that
    had gained a figure, which is exactly the drift it exists to catch.
    """
    rc = 0
    for key in sorted(set(pinned) | set(derived)):
        if key not in pinned:
            print(f"  {key} = {derived[key]}  <- not pinned by the page",
                  file=sys.stderr)
            rc = 1
        elif key not in derived:
            print(f"  {key} = {pinned[key]}  <- the page pins it and this "
                  f"tool does not re-derive it", file=sys.stderr)
            rc = 1
        elif pinned[key] != derived[key]:
            print(f"  {key}: page says {pinned[key]!r}, the bytes say "
                  f"{derived[key]!r}", file=sys.stderr)
            rc = 1
    if rc == 0:
        print(f"pd-image.md: all {len(pinned)} pinned figure(s) re-derive")
    return rc


# --------------------------------------------------------------------------
# The report


def report(region: bytes, how: str, owners, names, prov) -> str:
    """The human-readable census.

    Every number here is measured by the call above it, and every zero is
    printed with the token that says a search ran -- which is why this returns
    one string rather than a dict: a report that reads as a claim is the thing
    the calibration rule is about, and the wording is load-bearing, not
    decoration.
    """
    out = []
    w = out.append
    used_end, ff_total, longest_ff = layout(region)
    table = vector_table(region)

    w(f"pd_image_census.py -- the ITE8850-PD image at file "
      f"0x{REGION_OFF:05X}-0x{REGION_OFF + REGION_LEN - 1:05X}")
    w(f"  identified by: {how}")
    w(f"  {REGION_LEN // 1024} KiB, sha256 {digest(region)}")
    w("")
    w("1. Layout")
    w(f"  in use to 0x{used_end:04X}; 0x{used_end + 1:04X}-"
      f"0x{REGION_LEN - 1:04X} erased")
    w(f"  {ff_total} byte(s) of 0xFF, longest run {longest_ff}")
    w("  the region is a program in its own 64 KiB space, not a bank of the "
      "EC; lightbar-bat-flow.md §2 carries the four facts")
    w("")
    w("2. Vector table")
    w(f"  {len(table)} entries, read at 0x{VECTOR_RESET:02X} and "
      f"0x{VECTOR_FIRST:02X} + n*{VECTOR_STRIDE}")
    for off, target in table:
        hand = interrupt_handover(region, target)
        w(f"    0x{off:02X} -> ljmp 0x{target:04X}   "
          f"{function_name(target, names)}")
        if hand:
            w(f"        mov dptr,#0x{hand[0]:04X}; lcall 0x{hand[1]:04X}; "
              f"{hand[2]} push(es) before it")
    w(f"  then: {erased_after_table(region, table)}")
    w("  the five interrupt entries are one wrapper each, and the CODE "
      "address it loads is the per-vector selector:")
    for off, dptr, n, readers in vector_pointer_table(region, owners, names):
        who = ",".join(name for _, name in readers) or NOT_FOUND
        w(f"    0x{off:02X} -> code 0x{dptr:04X}  {n} site(s)  read by {who}")
    w("")
    w("3. String pool")
    pool = string_rows(region, owners, names)
    found = [r for r in pool if r["verdict"] == "referenced by this method"]
    w(f"  {len(pool)} candidate(s): a NUL-terminated run of at least "
      f"{MIN_STRING} printable bytes")
    w(f"  {len(found)} of them named by a MOV DPTR + MOVC pair")
    for off in ("0x0040", "0x0160", "0x0170", "0xE1C0"):
        for r in pool:
            if r["region_offset"] == off:
                w(f"    identity  {r['region_offset']}  {r['string']!r}")
    for name in ("PR Swap", "Error Recovery", "Set VBUS 5V", "DR Swap",
                 "FR Swap", "SRC Negotiate done", "SINK Negotiate done",
                 "VCONN On"):
        for r in pool:
            if r["string"] == name:
                w(f"    protocol  {r['region_offset']}  {r['string']!r}"
                  f"  (mov dptr x{r['dptr_sites']}, {r['verdict']})")
    w("  not an absence: the scan sees a literal DPTR load only, and this "
      "program also reaches CODE by table and by arithmetic")
    w("  the two CODE-table dispatchers take their table from the caller's "
      "inline bytes, so a string pointer would be a literal at a call site; "
      "measured over the sites:")
    for target in CODE_TABLE_DISPATCHERS:
        rows = [r for r in code_table_inline_tables(region) if r[0] == target]
        hits = [r for r in rows if r[3]]
        w(f"    0x{target:04X}  {len(rows)} call site(s), "
          f"{len(hits)} whose table opens a string"
          + ("" if hits else f"  ({NOT_FOUND})"))
    w("")
    w("4. Host-facing command surface")
    total, by_type, dispatch = command_surface(names)
    w(f"  {total} pd-scoped annotation row(s); by type: "
      + ", ".join(f"{k}={v}" for k, v in sorted(by_type.items())))
    w(f"  {len(dispatch)} row(s) typed 'dispatch':")
    for addr, name in dispatch:
        w(f"    0x{addr:04X}  {name}")
    w("  XDATA addresses the host block census named, by MOV DPTR site count:")
    for a, n in host_block_sites(region).items():
        w(f"    0x{a:04X}  {n if n else NOT_FOUND}")
    w("  what a site *does* is trace_xdata_refs.py's question, not this one's")
    w("")
    w("5. Provenance")
    w(f"  {prov['zip']}, member {prov['ec_member']}")
    w(f"    sha256 {prov['ec_member_sha256']}")
    w(f"    byte-identical to ec/firmware/GMxMGxx_11.800: "
      f"{prov['ec_member_is_committed']}")
    w(f"    carries the region marker: {prov['region_in_ec_member']}")
    w(f"  {prov['rom_member']} ({prov['rom_size']} bytes)")
    w(f"    the 64 KiB region occurs {prov['rom_region_copy_count']} time(s): "
      + " ".join(prov["rom_region_copies"]))
    w(f"    the whole 256 KiB EC image occurs at "
      + " ".join(prov["rom_ec_image_at"])
      + f", byte-identical to the committed file: "
        f"{prov['rom_ec_image_is_committed']}")
    w(f"  {prov['nsh_member']}: {prov['nsh_text']!r}")
    w("    that one write covers the whole 256 KiB, the 0x20000 region "
      "included: the PD firmware ships with the EC update, not only with the "
      "BIOS")
    w("    a grep over the container finds nothing and that is a DEFLATE "
      "artefact, not an absence")
    return "\n".join(out)


# --------------------------------------------------------------------------
# --self-test


def self_test(suite: str = None) -> int:
    """Run the suite, and hand back its exit code. Not in any gate -- see
    `docs/findings/pd-image-census.md`.

    `subprocess` rather than an import, so the suite exercises the command the
    page tells a reader to run and its exit code, which an in-process call to
    `unittest.main()` cannot -- a suite that reports `OK` and then has its
    process exit 1 is a failure mode an in-process runner cannot show.

    `suite` is a parameter for exactly one reason: the suite has a case that
    runs this function, and a fixed path would make that case recurse until
    the machine ran out of patience. The parameter is the way to break the
    cycle without an environment variable, whose scope is inherited wholesale
    and therefore fires one level too early -- a guard that stops the *direct*
    child stops the case that was trying to reach the second one.
    """
    import subprocess
    path = suite or os.path.join(HERE, "test_pd_image_census.py")
    return subprocess.call([sys.executable, path])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--firmware", default=FIRMWARE,
                    help=f"raw EC firmware image (default: {repo_path(FIRMWARE)})")
    ap.add_argument("--zip", default=VENDOR_ZIP,
                    help="vendor BIOS zip for the provenance half")
    ap.add_argument("--page", default=PAGE,
                    help=f"the page whose pinned figures --check re-derives "
                         f"(default: {repo_path(PAGE)})")
    ap.add_argument("--csv", action="store_true",
                    help="write the string-pool census as CSV on stdout")
    ap.add_argument("--check", action="store_true",
                    help="diff the generated CSV against the committed table "
                         "and re-derive every figure pd-image.md pins; "
                         "non-zero on any difference")
    ap.add_argument("--self-test", action="store_true",
                    help="run ec/tools/test_pd_image_census.py")
    ap.add_argument("--section", default="all",
                    choices=["all", "layout", "vector", "strings", "command",
                             "provenance"],
                    help="with --check, which figures to re-derive; 'all' is "
                         "what the page's pinned block is written against")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    try:
        region, how = read_region(args.firmware)
        extents = function_extents()
        owners = address_owners(extents)
        names = function_names()
        if args.csv:
            sys.stdout.write(csv_table(region, owners, names))
            return 0
        if args.check:
            rc = check_table(csv_table(region, owners, names), STRINGS_CSV)
            prov = provenance(args.zip)
            derived = figures(region, owners, names, prov, extents)
            pinned = pinned_figures(args.page)
            if args.section != "all":
                keep = {k for k in derived if args.section in k}
                derived = {k: v for k, v in derived.items() if k in keep}
                pinned = {k: v for k, v in pinned.items() if k in keep}
            return rc or check_figures(pinned, derived)
        prov = provenance(args.zip)
        print(report(region, how, owners, names, prov))
        return 0
    except Refusal as e:
        print(f"note: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
