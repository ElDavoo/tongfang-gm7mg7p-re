#!/usr/bin/env python3
"""Extract an ACPI `Field (...)` element list from a .dsl and join every
address it names to the per-image `MOV DPTR` site counts.

`ec/annotations/registers.yaml` has a name for an address because some other
source had one: `uniwill-laptop`, the ECSpec, the Windows service, a live
read. docs/findings.md 3c measures what that leaves out -- 1,022 of the 1,063
XDATA addresses the main EC touches carry no name at all. The DSDT is a second
source of names the firmware supplies about itself, and this is the sweep over
it: address, bit, width, name, and how many direct reference sites each
address has in each image.

**The list this reads is ECMG, and the offsets in it are EC XDATA
addresses.** `OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)`
at dsdt.dsl:52193 declares a SystemMemory window, and the field offsets
inside it (`Offset (0x43E)`, `Offset (0x0EA0)`, ...) are plainly not that
window's offsets -- read as ASL they would land at 0xFE41043E. They are read
here as XDATA addresses because two independent things say so, and neither is
this tool:

  * `ECRW`/`ECRR` (dsdt.dsl:50497, 50504) compute `0xFE410000 + Arg0` and
    MMRW it -- the ECMG `OperationRegion`'s own base, added to a caller's
    literal, so the accessor and the field list are two descriptions of one
    window. Nothing calls them: `grep -n "ECRW\\|ECRR\\|T1WR"
    evidence/acpi/dsdt.dsl` is the three `Method` declarations and an
    unrelated `CreateBitField` at dsdt.dsl:4437-4438. So this is the declared
    base agreeing, not the firmware observed reaching an EC byte through it.
  * Nine of the addresses ECMG names are ones `registers.yaml` holds under a
    name it got from somewhere else, and they land on the same bytes:
    `CPTM` 0x043E / `CPU_TEMP`, `VGAT` 0x044F / `GPU_TEMP`, `GNEN`+`ECDC`
    0x0743 / `CTGP_DB_CTRL`, `APL1`-`APL4` 0x0783-0x0785 /
    `CPU_PL1/PL2/PL4`, `APTC`+`APTN` 0x0786 / `CPU_TCC_OFFSET`, `WMS0`
    0x07C6 / `AP_OEM_6`, `DBD1` 0x07D0 / `BATTERY_CHARGE_LIMIT_DOWN`. Every
    one of those entries' `sources` carries a `uniwill-laptop`, `ecspec` or
    `live` tag of its own -- seven of the nine carry the `dsdt` one beside it,
    `CPU_TEMP` and `GPU_TEMP` do not -- which is what makes the agreement a
    measurement and not a restatement. `--self-test` checks the property each
    entry states (it carries such a tag) rather than trusting this list. Nine
    addresses a block would have to get right by chance is a better argument
    than any one of them.

    The other twelve addresses ECMG names that `registers.yaml` holds were
    named *from* the DSDT (`DBEN`/`DBST` 0x07C4, `GFID` 0x07D3, `CPUA`
    0x07D4, `DBAP` 0x07D5, `DBSP` 0x07D6, `CGCT` 0x07D7, and four more), so
    they are the same source twice and count for nothing here.

**The region the issue named is not this one.** `Field (GNVS, ...)`
(dsdt.dsl:415, over `OperationRegion (GNVS, SystemMemory, 0x98F57000,
0x07FA)`) is a 1,038-element UEFI NVS block, and `CTDB`, `PWRE`, `WIFC`,
`ODV0`-`ODV5` and the `TPL*` run are its fields. It opens with `OSYS` and no
`Offset` at all, so ASL's byte 0 is where the first field lands, and the 1,038
names come out at one per byte across `0x0000`-`0x07F9` -- the whole declared
`0x07FA` block, filled to its last byte. The issue read
`Offset (0x1F4)`-`Offset (0x7A7)` as the span of an EC map; it is the later
part of a NVS block, and a NVS block that happens to be large enough to cover
the `0x0400`-`0x07FF` XDATA range says nothing about what is in it.
`--region gnvs` extracts and reports the list, and **the count join is refused
for it** rather than performed and annotated: a `static_refs` column beside
1,038 NVS offsets would read as evidence about those bytes while measuring
something else. Two further measurements, taken rather than argued:

  * The DSDT contains no call site of `ECRW`, `ECRR` or `T1WR` at all. The
    three declarations at dsdt.dsl:50497, 50504 and 50635 are the whole of
    it, so no ASL path exists in this file by which an NVS-named field could
    be shown to reach an EC byte. That is the test the issue's reading would
    have needed to pass, and it is not close.
  * `T1WR`'s body dispatches on `Arg0` values that name fields rather than
    address them: `0x81` -> `APL1`, `0x84` -> `APL4`, `0x85` -> `APTN`/`APTC`
    (dsdt.dsl:50637-50653). Reading an `Arg0` as an address would be a
    category error. The accessor's dispatch table is its own question and is
    named as a follow-up, not swept here.

**A `0` in the count column is "not found by this method", never
"absent".** The scan is the same byte pattern `scan_refs.py` uses, so it
inherits its blind spot whole: indirect and computed DPTR are invisible to it,
and `0x07B9` is a byte Windows demonstrably writes with no direct reference
anywhere in the image (docs/findings.md 4c). This tool's own `grade` column
therefore emits the literal token `not-found-by-this-method` for an address
with no site at all, which is not a `registers.yaml` `status:` value and
cannot be lifted into one by accident.

**What a count is not.** It is a count of `MOV DPTR,#addr` byte patterns, not
of register accesses: a site can build a CODE pointer or hand DPTR to a
subroutine, and what each site *does* is classified per address by
`register_ref_table.py`, not here. The counts are also per byte, not per bit,
so two DSDT names sharing `0x07C4` carry the same number and nothing in it
distinguishes `DBEN` from `DBST`.

Read-only: it opens the .dsl, the firmware image and `registers.yaml` for
reading and writes nothing unless `--out` is given.

The refusals -- an `Offset (...)` that is not a literal byte offset, an
`Access (...)` keyword (whose element widths read as bits or bytes depending
on it), one name used at two addresses in the same region, a `Field` list
naming a region with no `OperationRegion`, a list that never opens, and a line
the grammar does not name -- are all `FieldError`s naming the line, and
`--self-test` holds each one. A parser that quietly skipped what it could not
place would put fields on the wrong address or leave a hole in the list, and a
hole here reads as "the DSDT does not name this", which is a claim about the
firmware made from a gap in a tool.

`--self-test` is run by hand rather than from `.github/scripts/agent-gates.sh`:
that file lives under `.github/`, which this repository's pipeline push token
cannot write, so wiring the mode into the gate's tool loop is a human's change
to a template file. `ec/tools/test_dsdt_ec_fields.py` holds the parser's edge
cases and is runnable standalone the same way.

Usage:
    python3 dsdt_ec_fields.py ../firmware/GMxMGxx_11.800
    python3 dsdt_ec_fields.py --region gnvs
    python3 dsdt_ec_fields.py ../firmware/GMxMGxx_11.800 --csv > fields.csv
    python3 dsdt_ec_fields.py ../firmware/GMxMGxx_11.800 --check
    python3 dsdt_ec_fields.py --self-test
"""
import argparse
import csv
import difflib
import io
import os
import re
import sys

import yaml

from trace_xdata_refs import PD_MARKER, REGIONS, region_of, sites_for

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
DEFAULT_DSDT = os.path.join(REPO, "evidence", "acpi", "dsdt.dsl")
DEFAULT_REGISTERS = os.path.join(HERE, os.pardir, "annotations",
                                 "registers.yaml")
# The committed table covers ECMG only. GNVS is 1,038 rows of a NVS block this
# file's own docstring says is not a register map, and committing it would
# invite exactly the misreading the --region gnvs correction exists to undo:
# a CSV of addresses beside a `static_refs` column reads as a register list
# whatever its header says. `--region gnvs` prints it on demand instead.
FIELDS_CSV = os.path.join(HERE, os.pardir, "annotations",
                          "dsdt-ecmg-fields.csv")

COLUMNS = ["region", "addr", "bit", "width", "name", "dsdt_line",
           "static_refs", "static_refs_main_ec", "static_refs_pd_image",
           "in_registers", "grade"]

# The images a count splits into. `IMAGES` is trace_xdata_refs.REGIONS with
# the unmapped stretches dropped, so a re-derived image map (find_banks.py
# against a different dump) carries through to this tool's output rather than
# being restated here; the split itself is the same two names
# check_register_counts.py uses, so the two agree by construction.
IMAGES = [name for name, *_ in REGIONS if name != "erased"]
MAIN_EC_IMAGES = ("common", "bank0", "bank1")
PD_IMAGE = "pd-image"

# What the grade column says for an address with no site in either image. Not
# a `status:` value: nothing is proposed for it, because a DSDT name next to a
# zero is the shape of claim docs/findings.md 4c had to retract. The token
# cannot be lifted into registers.yaml by accident because registers.yaml's
# vocabulary (see its own header) does not contain it.
NO_SITE = "not-found-by-this-method"

# The regions whose field offsets are EC XDATA addresses, and so may be
# joined to the EC image's site counts. ECMG is one: `ECRW`/`ECRR` compute
# `0xFE410000 + Arg0`, the same window its OperationRegion declares.
#
# GNVS is not, and the join is refused for it rather than performed and
# annotated. Its offsets run 0x0000-0x07F9 across a declared 0x07FA NVS
# block, so they *cover* the 0x0400-0x07FF XDATA range by accident of size
# rather than by meaning, and a count column beside them would read as
# evidence about those bytes while measuring a NVS offset. That is the same
# call this repo makes about the two 8051 programs sharing one dump (#21), and
# it is the reason the committed table covers ECMG alone.
XDATA_REGIONS = ("ECMG",)

# Rendered in the count columns when the join does not apply. Carrying the
# reason in the cell rather than leaving it blank, because a blank reads as
# "measured, found nothing" -- the one thing `NO_SITE` already exists to stop
# being mistaken for.
NOT_JOINED = "not-joined-nvs-offsets"

# `0x1F4`, `500`, `0x1f4` -- a literal byte offset and nothing else. An
# `Offset (CurrentTbStatus)` or `Offset (SBRG + 0x100)` is an expression over
# names resolved at ACPI-load time, and a parser that guessed one would place
# every following field on an address the firmware never wrote.
LITERAL = re.compile(r"0x[0-9A-Fa-f]+|[0-9]+")
REGION_OPEN = re.compile(r"^\s*OperationRegion\s*\(\s*(\w+)\s*,\s*(\w+)\s*,"
                         r"\s*([^,]*?)\s*,\s*([^)]*?)\s*\)")
FIELD_OPEN = re.compile(r"^\s*Field\s*\(\s*(\w+)\s*,\s*(\w+)")
OFFSET = re.compile(r"^Offset\s*\(\s*(.+?)\s*\)$")
ACCESS = re.compile(r"^Access\s*\(\s*(\w+)\s*\)$")
NAMED = re.compile(r"^(\w+)\s*,\s*(\d+)$")
# The unnamed gap between two named fields, written as a bare width: the
# `                    ,   1,` line. Those bits are declared and unallocated,
# and counting them is how a name ends up on the wrong byte.
RESERVED = re.compile(r"^,\s*(\d+)$")


class FieldError(ValueError):
    """A `Field` list this parser will not place. Carries the .dsl line."""


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below."""
    return os.path.relpath(path, REPO)


def parse_regions(lines) -> dict:
    """name -> (line, region_space, base, length) for every OperationRegion.

    The base and length are kept as written. Both can be ACPI-load-time
    expressions (`CNVB`, `SBRG + 0x00AD8000`, `Local2`) that only the
    interpreter can resolve, and this tool does not need them: it reports the
    offsets as the firmware wrote them and
    ec/annotations/dsdt-ecmg-field-sweep.md carries the argument for reading
    them as XDATA addresses. First declaration wins, so a region re-declared
    in a later scope keeps the address space it was introduced with."""
    out = {}
    for i, line in enumerate(lines, 1):
        m = REGION_OPEN.match(line)
        if m and m.group(1) not in out:
            out[m.group(1)] = (i, m.group(2), m.group(3), m.group(4))
    return out


def parse_lists(lines, path: str, region: str) -> list:
    """Every `Field (region, ...)` body in the file, as (access, line, [lines]).

    The list is found by brace matching rather than by looking for a line
    equal to `}`, because a field element list has no nesting in iasl output
    and a depth counter is the only thing here that cannot stop early on a
    stray brace. `line` is the `Field` line itself and the returned line list
    is 1-based, as the file counts."""
    out = []
    for i, line in enumerate(lines):
        m = FIELD_OPEN.match(line)
        if not m or m.group(1) != region:
            continue
        body = []
        depth = 0
        started = False
        for j in range(i, len(lines)):
            s = lines[j].strip()
            if s == "{":
                depth += 1
                started = True
                continue
            if s == "}":
                # Only counted once the list has opened. A `}` between the
                # `Field` line and its `{` would drive `depth` negative and the
                # list would then run to the end of the file, collecting every
                # element of every list after it into this one.
                if not started:
                    continue
                depth -= 1
                if depth == 0:
                    break
                continue
            if started:
                body.append((j + 1, lines[j]))
        if not started:
            raise FieldError(f"{repo_path(path)}:{i + 1}: Field ({region}, "
                             "...) has no '{' -- the list is unterminated")
        out.append((m.group(2), i + 1, body))
    return out


def parse_body(body, path: str, region: str) -> tuple:
    """(elements, reserved_bits) for one field-list body.

    The cursor is in bits from the start of the region, not in bytes: at
    `Offset (0x7C4)` the first three elements declare three unnamed bits, so
    `DBEN` is bit 3 of 0x07C4 and `DBST` is bit 5. A parser that rounded
    sub-byte widths to whole bytes would put both on 0x07C4 bit 0, and
    registers.yaml already records the corrected bits -- which is the
    disagreement this test is run to catch.

    Each element is (name, addr, bit, width, line). An element is keyed on the
    byte it *starts* in; a 16-bit element spans two and the width column says
    so. The count join is per byte, so a two-byte register is counted at its
    low byte, which is the address registers.yaml records it under."""
    elements = []
    reserved = 0
    # Zero, not None: a field list may open with fields and no `Offset`, and
    # ASL puts the first element at byte 0 of the region. GNVS does exactly
    # that (OSYS at :417), which is a large part of why its 1,038 names cover
    # 0x0000-0x07F9 -- the whole declared 0x07FA -- rather than the
    # 0x1F4-0x7A7 window the issue read them out of.
    cursor = 0
    for lineno, raw in body:
        t = raw.strip()
        if not t or t.startswith(";"):
            continue
        t = t.rstrip(",").strip()
        m = OFFSET.match(t)
        if m:
            expr = m.group(1)
            if not LITERAL.fullmatch(expr):
                raise FieldError(
                    f"{repo_path(path)}:{lineno}: Offset ({expr}) is not a "
                    f"literal byte offset; every field after it is unplaceable, "
                    f"so the {region} list is refused rather than guessed at")
            cursor = int(expr, 0) * 8
            continue
        m = ACCESS.match(t)
        if m:
            # An element's width means bits or bytes depending on this, and
            # the two field lists this tool is pointed at declare no keyword.
            # Refusing beats reporting a bit index computed under the wrong
            # assumption.
            raise FieldError(
                f"{repo_path(path)}:{lineno}: Access ({m.group(1)}) changes how "
                f"element widths are read; the {region} list is refused rather "
                "than placed under an unstated assumption")
        m = RESERVED.match(t)
        if m:
            reserved += int(m.group(1))
            cursor += int(m.group(1))
            continue
        m = NAMED.match(t)
        if m:
            width = int(m.group(2))
            elements.append((m.group(1), cursor // 8, cursor % 8, width, lineno))
            cursor += width
            continue
        raise FieldError(f"{repo_path(path)}:{lineno}: unrecognised line in the "
                         f"{region} field list: {t!r}")
    return elements, reserved


def extract(lines, path: str, region: str) -> dict:
    """name, region_space, region_line, lists, elements, reserved for `region`.

    Every `Field` list naming the region is pooled. A region with two lists
    gives two readings of one name, so the returned `lists` carries their
    line numbers and every element carries its own: which list a row came from
    is visible in the row, not implied."""
    regions = parse_regions(lines)
    lists = parse_lists(lines, path, region)
    if not lists:
        raise FieldError(f"{repo_path(path)}: no Field ({region}, ...) list")
    if region not in regions:
        raise FieldError(
            f"{repo_path(path)}: Field ({region}, ...) at line {lists[0][1]} has "
            "no OperationRegion of that name, so the offsets in it address "
            "nothing this file declares")
    elements = []
    reserved = 0
    for access, lineno, body in lists:
        found, gap = parse_body(body, path, region)
        elements.extend(found)
        reserved += gap
    seen = {}
    for name, addr, bit, width, lineno in elements:
        if name in seen:
            raise FieldError(
                f"{repo_path(path)}:{lineno}: field {name} is declared twice in "
                f"the {region} region (first at 0x{seen[name][0]:04X} bit "
                f"{seen[name][1]}, line {seen[name][2]}); one name at two "
                "addresses is not a register")
        seen[name] = (addr, bit, lineno)
    return {"region": region,
            "region_space": regions[region][1],
            "region_line": regions[region][0],
            "region_base": regions[region][2],
            "lists": [(a, l) for a, l, _ in lists],
            "elements": elements,
            "reserved": reserved}


def load_registers(path: str) -> dict:
    """byte address -> the `registers.yaml` entry naming it.

    First entry wins, so an address carried by two entries reports the one
    nearer the top of the file, which is where a reader looking for a name
    would land."""
    with open(path) as f:
        regs = yaml.safe_load(f)["registers"]
    out = {}
    for r in regs:
        addrs = r["addr"] if isinstance(r["addr"], list) else [r["addr"]]
        for a in addrs:
            out.setdefault(a, r)
    return out


class Counter:
    """(total, main-EC, PD-image) `MOV DPTR,#addr` site counts, per address.

    `sites_for` and `region_of` are trace_xdata_refs' own, called unchanged
    and not re-implemented: the join has to be the repo's per-image method or
    a count in this file and a count in `static-refs-audit.md` are two
    numbers that can disagree while both look right. They rescan the whole
    256 KiB per address, so a region's addresses are counted once each and
    cached -- a 1,038-address `--region gnvs` run is slow by that arithmetic,
    and the docstring says so rather than letting a reader time out and assume
    the tool hung."""
    def __init__(self, image: bytes, pd_verified: bool):
        self.d = image
        self.pd_verified = pd_verified
        self.cache = {}

    def __call__(self, addr: int) -> tuple:
        if addr not in self.cache:
            total = main = pd = 0
            for o in sites_for(self.d, addr):
                total += 1
                name = region_of(o, self.pd_verified)[0]
                if name in MAIN_EC_IMAGES:
                    main += 1
                elif name == PD_IMAGE:
                    pd += 1
            self.cache[addr] = (total, main, pd)
        return self.cache[addr]


def grade_for(total: int, main: int) -> str:
    """The registers.yaml `status:` a row at this count is a candidate for.

    Two rules and no third, because the ceiling this sweep can reach is
    `present-untested` and every row that reaches a name has to say why it
    stopped there. EC-side sites make it `present-untested`: the byte is
    referenced by the firmware, and nothing more -- a site can build a CODE
    pointer or hand DPTR on, and no reference count is behaviour. Sites that
    turned out to belong to the PD image are `unknown-not-absent`, the value
    this file's header already reserves for exactly that, and which is #21's
    conflation rather than a statement about the EC byte. No sites at all is
    no proposal."""
    if main:
        return "present-untested"
    if total:
        return "unknown-not-absent"
    return NO_SITE


def build_rows(fields: dict, counts, registers: dict) -> list:
    """One row per named element, in the order the .dsl declares them.

    `counts` is None for a region whose offsets are not XDATA addresses, and
    the three count cells say so rather than carrying a number."""
    joinable = fields["region"] in XDATA_REGIONS
    rows = []
    for name, addr, bit, width, lineno in fields["elements"]:
        total, main, pd = counts(addr) if joinable else (0, 0, 0)
        held = registers.get(addr)
        if not joinable:
            grade = NOT_JOINED
        elif held:
            grade = str(held["status"])
        else:
            grade = grade_for(total, main)
        rows.append({
            "region": fields["region"],
            "addr": f"0x{addr:04X}",
            "bit": bit,
            "width": width,
            "name": name,
            "dsdt_line": lineno,
            "static_refs": total if joinable else NOT_JOINED,
            "static_refs_main_ec": main if joinable else NOT_JOINED,
            "static_refs_pd_image": pd if joinable else NOT_JOINED,
            "in_registers": held["name"] if held else "",
            "grade": grade,
        })
    return rows


def render(rows) -> str:
    """The CSV text, `\\n` endings and no trailing blank line.

    A string rather than a write to stdout, because `--check` diffs the same
    bytes this returns."""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def check_table(generated: str, path: str) -> int:
    """Exit code for `--check`: 0 when this run reproduces `path` exactly.

    Read with `newline=""` so the comparison is the bytes on disk; universal
    newline translation would rewrite every line to LF and report a difference
    on every run, which is a check nobody trusts."""
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
          "file is the product of the command on the page that names it, so "
          "regenerate rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(), generated.splitlines(),
                                     "committed", "generated", lineterm="", n=0):
        print(line, file=sys.stderr)
    return 1


def report(fields: dict, rows: list) -> None:
    """The human table, for a reader deciding what to look at next."""
    addrs = sorted({a for _, a, _, _, _ in fields["elements"]})
    named = len(fields["elements"])
    lists = ", ".join(f":{line} ({access})" for access, line in fields["lists"])
    print(f"{fields['region']}  {lists}  over "
          f"OperationRegion :{fields['region_line']} "
          f"({fields['region_space']}, base {fields['region_base']})")
    print(f"  {named} named field(s) over {len(addrs)} distinct byte address(es), "
          f"0x{addrs[0]:04X}-0x{addrs[-1]:04X}, {fields['reserved']} unnamed "
          f"bit(s) declared and unallocated")
    if fields["region"] not in XDATA_REGIONS:
        print(f"  not joined to the EC image: {NOT_JOINED}. These are offsets in "
              f"a {fields['region']} block, not XDATA addresses, and a count "
              "column beside them would read as evidence about bytes it never "
              "measured. See the tool's docstring.")
    else:
        unseen = [r for r in rows if not r["in_registers"]]
        ec = [r for r in unseen if r["static_refs_main_ec"]]
        pd_only = [r for r in unseen
                   if r["static_refs"] and not r["static_refs_main_ec"]]
        quiet = [r for r in unseen if not r["static_refs"]]
        print(f"  {named - len(unseen)} start at an address registers.yaml "
              f"already holds; {len(unseen)} do not")
        print(f"  of those {len(unseen)}: {len(ec)} with EC-side site(s), "
              f"{len(pd_only)} PD-image only, {len(quiet)} with no site found "
              f"by this method")
    print()
    joinable = fields["region"] in XDATA_REGIONS
    if joinable:
        print(f"  {'addr':<8} {'bit':>3} {'w':>3} {'ec':>4} {'pd':>4} "
              f"{'name':<6} {'dsdt':>7}  held / grade")
        for r in rows:
            print(f"  {r['addr']:<8} {r['bit']:>3} {r['width']:>3} "
                  f"{r['static_refs_main_ec']:>4} {r['static_refs_pd_image']:>4} "
                  f"{r['name']:<6} {r['dsdt_line']:>7}  "
                  f"{r['in_registers'] or '-'} / {r['grade']}")
    else:
        # The count columns are not printed rather than printed as the
        # not-joined token 1,038 times: a column that is one constant is not a
        # column, and the sentence above already says what it would have held.
        print(f"  {'addr':<8} {'bit':>3} {'w':>3} {'name':<6} {'dsdt':>7}")
        for r in rows:
            print(f"  {r['addr']:<8} {r['bit']:>3} {r['width']:>3} "
                  f"{r['name']:<6} {r['dsdt_line']:>7}")


# The bit arithmetic, pinned against readings this tree already holds
# independently of this tool.
#
#   0x07C4: registers.yaml's `GPU_DYNAMIC_BOOST_STATUS (DSDT DBEN bit 3,
#            DBST bit 5)`, whose own note cites the field list at
#            dsdt.dsl:52238-52242 and records the correction of an earlier
#            bit-0 reading of the same list.
#   0x07C5: windows/tools/gpu_block_watch.py's row
#            `(0x07C5, "WHMS b5", NO_ROW, "dsdt.dsl:52243")` -- the tool the
#            Windows-side capture watches through, pinning the same byte and
#            bit from the other end of the stack.
#
# Two sources, two stacks, one bit index. If the arithmetic in parse_body()
# moved, both go red.
ORACLES = [
    (0x07C4, 3, 1, "DBEN", "registers.yaml: GPU_DYNAMIC_BOOST_STATUS"),
    (0x07C4, 5, 1, "DBST", "registers.yaml: GPU_DYNAMIC_BOOST_STATUS"),
    (0x07C5, 5, 1, "WHMS", "windows/tools/gpu_block_watch.py: (0x07C5, WHMS b5)"),
]

# The addresses ECMG names that registers.yaml holds under a name it reached
# from somewhere other than the DSDT. The docstring's argument that ECMG's
# offsets are XDATA addresses is these nine and nothing weaker, so they are
# asserted rather than asserted-about -- including the half of the claim that
# the entries were *not* named from the DSDT, which is the part that turns
# nine agreements into a measurement.
AGREEMENT = [0x043E, 0x044F, 0x0743, 0x0783, 0x0784, 0x0785, 0x0786,
             0x07C6, 0x07D0]

# A `sources` tag that does not name the DSDT and does not name this repo's
# own static scan either. The rest of the tag carries the qualifier -- the
# entries above spell it `uniwill-laptop(EC_ADDR_AP_OEM_6)`,
# `ecspec-3.1.6.0(ADDR_PL1/PL2/PL4_SETTING_VALUE)`, `live` -- so the prefix
# is what decides.
INDEPENDENT = ("uniwill-laptop", "ecspec", "live", "vendor-",
               "acpidriver")


def independent_source(entry) -> bool:
    """Whether `entry`'s sources name anything but the DSDT or a static scan."""
    return any(str(s).startswith(INDEPENDENT)
               for s in entry.get("sources", ()))

# One small field list per way parse_body() and extract() refuse, held as
# .dsl text rather than as assertions about a hand-built element tuple: a
# fixture that skips the parser proves nothing about the parser. Each is
# prefixed with its own OperationRegion so the refusal under test is the one
# named and not the "no OperationRegion" one, which is its own fixture.
PREFIX = ["OperationRegion (TST, SystemMemory, 0, 0x10000)",
          "Field (TST, ByteAcc, NoLock, Preserve)"]

FIXTURES = [
    ("an Offset that is not a literal byte offset",
     PREFIX + ["{", "    Offset (Base + 0x100),", "    NOPE,   8", "}"]),
    ("an Access keyword, whose element widths read differently",
     PREFIX + ["{", "    Offset (0x0040),", "    Access (ProcessLock),",
               "    NOPE,   8", "}"]),
    ("one name used at two addresses in the same region",
     PREFIX + ["{", "    Offset (0x0040),", "    DUP,    8,",
               "    Offset (0x0050),", "    DUP,    8", "}"]),
    ("a field list that never opens",
     ["OperationRegion (TST, SystemMemory, 0, 0x10000)",
      "Field (TST, ByteAcc, NoLock, Preserve)"]),
    ("a Field list naming a region with no OperationRegion",
     ["Field (TST, ByteAcc, NoLock, Preserve)", "{",
      "    Offset (0x0040),", "    NOPE,   8", "}"]),
    ("a line the grammar does not name",
     PREFIX + ["{", "    Offset (0x0040),", "    IndexField (IDX, 0)", "}"]),
]


def self_test(registers_path: str) -> int:
    """Known answers from the committed .dsl and the refusals, no image.

    Needs no firmware and no Ghidra, which is what lets it be run by hand from
    the implement stage: it reads two committed files and its own fixtures."""
    with open(DEFAULT_DSDT, errors="replace") as f:
        lines = f.read().split("\n")
    ecmg = extract(lines, DEFAULT_DSDT, "ECMG")
    gnvs = extract(lines, DEFAULT_DSDT, "GNVS")
    places = {(a, b, w, n): l for n, a, b, w, l in ecmg["elements"]}
    ok = True

    def check(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
        if not cond:
            ok = False

    print("dsdt_ec_fields.py --self-test")
    for addr, bit, width, name, why in ORACLES:
        line = places.get((addr, bit, width, name))
        check(f"{name} is bit {bit} of 0x{addr:04X}, width {width} "
              f"(dsdt.dsl:{line}) -- {why}", line is not None)
    registers = load_registers(registers_path)
    check(f"all {len(AGREEMENT)} of the addresses ECMG names that "
          "registers.yaml holds are still held",
          all(a in registers for a in AGREEMENT))
    check(f"and all {len(AGREEMENT)} of them were named from something other "
          "than the DSDT, which is what makes them independent agreement",
          all(a in registers and independent_source(registers[a])
              for a in AGREEMENT))
    check(f"ECMG names {len(ecmg['elements'])} fields over "
          f"{len({a for _, a, _, _, _ in ecmg['elements']})} byte addresses, "
          f"0x{ecmg['elements'][0][1]:04X}-0x{ecmg['elements'][-1][1]:04X}",
          len(ecmg["elements"]) == 98)
    check("ECMG declares one field list, at dsdt.dsl:52194",
          ecmg["lists"] == [("AnyAcc", 52194)])
    check(f"GNVS names {len(gnvs['elements'])} fields and the tool still says "
          "it is a NVS block, not a register map",
          len(gnvs["elements"]) == 1038
          and gnvs["region_line"] == 414
          and "GNVS" not in XDATA_REGIONS)
    check("GNVS opens with fields and no Offset, so ASL's byte 0 is where "
          "OSYS lands -- which is why its 1,038 names come out one per byte "
          "across 0x0000-0x07F9, filling the whole declared 0x07FA block, and "
          "not the 0x1F4-0x7A7 window the issue read them out of",
          gnvs["elements"][0][:4] == ("OSYS", 0, 0, 16)
          and gnvs["elements"][-1][1] == 0x07F9)
    check("the ECMG offsets reach past the block registers.yaml and "
          "xdata_span_survey.py already cover (0x0400-0x07FF), which is why "
          "the 0x0Exx page is new",
          max(a for _, a, _, _, _ in ecmg["elements"]) > 0x07FF)
    for label, fixture in FIXTURES:
        try:
            extract(fixture, "<self-test fixture>", "TST")
        except FieldError as e:
            check(f"refuses {label} -- {e}", True)
        else:
            check(f"refuses {label} -- accepted it instead", False)
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?",
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800); "
                         "not needed for --region GNVS, which is not joined "
                         "to the image")
    ap.add_argument("--dsdt", default=DEFAULT_DSDT,
                    help=f"ACPI .dsl to read (default: {repo_path(DEFAULT_DSDT)})")
    ap.add_argument("--registers", default=DEFAULT_REGISTERS,
                    help="registers.yaml to join (default: the one beside this tool)")
    ap.add_argument("--region", default="ECMG", type=str.upper,
                    choices=("ECMG", "GNVS"),
                    help="which Field list to sweep (default: ECMG, the EC one; "
                         "GNVS is a NVS block and is reported unjoined)")
    ap.add_argument("--csv", action="store_true",
                    help="write the row table as CSV on stdout instead of the table")
    ap.add_argument("--out", metavar="PATH",
                    help="write the CSV here instead of the committed path "
                         "(only with --csv)")
    ap.add_argument("--check", nargs="?", const=FIELDS_CSV, metavar="PATH",
                    help="regenerate in memory and diff against a committed "
                         f"table, exit non-zero on any difference (default: {repo_path(FIELDS_CSV)})")
    ap.add_argument("--self-test", action="store_true",
                    help="known answers from the committed .dsl plus this "
                         "tool's refusals; no image, no Ghidra, no network")
    args = ap.parse_args()

    if args.self_test:
        if args.csv or args.check is not None or args.firmware:
            ap.error("--self-test takes no firmware, --csv, --check or --out")
        return self_test(args.registers)

    if not args.firmware and args.region in XDATA_REGIONS:
        ap.error("--region ECMG needs a firmware image for the per-image site "
                 "counts (e.g. ec/firmware/GMxMGxx_11.800); --region GNVS "
                 "does not, because its offsets are not joined to the image")

    with open(args.dsdt, errors="replace") as f:
        lines = f.read().split("\n")
    try:
        fields = extract(lines, args.dsdt, args.region)
    except FieldError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if len(fields["lists"]) > 1:
        # Not fatal: the rows carry their own dsdt_line, so which list a row
        # came from is in the row. Silent would not be, because a name read
        # out of one list would look like the region's single reading.
        print(f"note: {len(fields['lists'])} Field lists name "
              f"{args.region} ({', '.join(':' + str(l) for _, l in fields['lists'])}); "
              "the rows are pooled and the dsdt_line column tells them apart\n",
              file=sys.stderr)

    counts = None
    if args.firmware and fields["region"] in XDATA_REGIONS:
        d = open(args.firmware, "rb").read()
        off, magic = PD_MARKER
        pd_verified = d[off:off + len(magic)] == magic
        if not pd_verified:
            print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
                  "sites in 0x20000-0x2FFFF will be reported as region "
                  "'unknown'\n", file=sys.stderr)
        counts = Counter(d, pd_verified)

    rows = build_rows(fields, counts, load_registers(args.registers))

    if args.csv:
        text = render(rows)
        if args.check is not None:
            return check_table(text, args.check)
        if args.out:
            with open(args.out, "w", newline="") as f:
                f.write(text)
            print(f"wrote {repo_path(args.out)}: {len(rows)} row(s)", file=sys.stderr)
            return 0
        sys.stdout.write(text)
        return 0
    if args.check is not None:
        ap.error("--check is about the --csv table; it needs --csv")
    report(fields, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
