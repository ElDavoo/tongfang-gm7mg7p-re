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

**The `asl_refs` / `asl_sites` columns ask the other half of the question:
does the ASL that declares a name ever use it?** Everything above is about the
EC image; a name in a field list says what the firmware called a byte, and
whether the ASL ever reaches for that name is a separate fact this file now
measures. The rules, so a count here is the same count next time:

  * A **reference** is an occurrence of a field name in ASL **outside its own
    declaring list's line span**. Comments are stripped before matching, so
    iasl's own `\\SB_.PCI0.LPCB.EC0_.CTWA` alias comments are never counted as
    code -- and they are not needed, because they are the third independent
    attribution the self-test cross-checks the first two against.
  * Two forms count. The **qualified** form, a path component written as
    `^^PCI0.LPCB.EC0.<name>` (or `EC0_.<name>` in an alias), counts anywhere in
    the file. The **bare** form, a whole-word occurrence, counts only inside
    the scope brace-enclosing the list, because ASL resolves a bare name to the
    nearest enclosing declaration and that is the same reference written
    shorter. `Method (UCEV, 0)` at dsdt.dsl:52943 reads `MGI0`-`MGIF` and
    `CCI0`-`CCI3` by bare name, and a qualified-only scan calls all twenty
    declared-only.
  * A name preceded by any `.` is **not** bare: it is a field of whatever
    object the path names. `^^^^UBTC.MGI0` on the left of the `UCEV` line is a
    write to an `External (_SB_.UBTC.MGI0, IntObj)` (dsdt.dsl:264, declared
    just after its `External (_SB_.UBTC, DeviceObj)` parent at :259) that
    merely shares a spelling with ECMG's `MGI0`, and counting it would put
    twenty phantom references on the same byte the right-hand side legitimately
    reads.
  * A reference is attributed to the region that **declares the name**, not to
    the path it was reached through. `Device (EC0)` declares four operation
    regions, and the `^^PCI0.LPCB.EC0.` prefix reaches three of them --
    `ECMG` (98 names, dsdt.dsl:52193), `ECMP` (1, :52330) and `ECXP` (94,
    :52337) -- so a prefix-keyed count silently merges those three. The fourth,
    the `IO` port region at :52163, the prefix does not reach. A name no field
    list declares is reported separately as unplaceable rather than dropped;
    the `Name (THOT, Zero)` at dsdt.dsl:52190 is the case in the committed
    file.
  * `asl_refs` is the **occurrence count** and `asl_sites` the set of
  `dsdt.dsl` lines, so two references on one line (`PDIN` at :50774 is read in
    three `||` branches, :50828-50829 twice) are not lost, and the site list
  stays deduplicated per line.
  * A zero reads **`not-referenced-by-this-method`**, for the reason
    `NO_SITE` exists. It is not a `status:` value, it cannot be lifted into
    one, and no static method can tell a name nothing uses from a name this
    method cannot see.

**A reference is evidence about the ASL.** It is not evidence that the EC acts
on the byte, and a `Notify` firing on a field says nothing about what the field
does. A name the ASL reaches for and the EC image never names is not a
contradiction -- it is the shape an indirect-addressing blind spot produces,
and the two columns are kept apart for that reason rather than joined into one
grade.

**A reference has no direction.** The count is an occurrence: a name the ASL
loads, a name it stores and a name it tests are one reference each, and the
columns do not say which. Of the 35 ECMG names the ASL reaches for, eight --
`APL1`, `APL2`, `APL4`, `APTN`, `APTC`, `DBD1`, `DBD2` and `CGCT` -- are
written by `T1WR`'s `Arg0` arms and read nowhere, and `DBD1`'s entry in
`registers.yaml` says so from the other end (`unknown-not-absent-
DO-NOT-WRITE-BLIND`, dsdt.dsl:50687 `^^PCI0.LPCB.EC0.DBD1 = Local0`). Reading
the column as a read/write split is the mistake this paragraph exists to stop;
the direction is on the line, and the split itself is not measured here.

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

Both `--csv --check` and `--self-test` are prepared in
`../../docs/ci/agent-gates-disasm8051-self-test.patch` rather than run from
`.github/scripts/agent-gates.sh`: that file lives under `.github/`, which this
repository's pipeline push token cannot write, so wiring the modes into the
gate's tool loop is a human's change to a template file and the prepared patch
is the deliverable. **Until a human lands it, both modes run by hand**, and a
CSV that has drifted from `registers.yaml` merges green.
`ec/tools/test_dsdt_ec_fields.py` holds the parser's edge cases and is runnable
standalone the same way.

Usage:
    python3 dsdt_ec_fields.py ../firmware/GMxMGxx_11.800
    python3 dsdt_ec_fields.py --region gnvs
    python3 dsdt_ec_fields.py ../firmware/GMxMGxx_11.800 --csv > fields.csv
    python3 dsdt_ec_fields.py ../firmware/GMxMGxx_11.800 --csv --check
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
           "in_registers", "grade", "asl_refs", "asl_sites"]

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

# What the ASL columns say for a name nothing outside its own field list reads.
# Not a `status:` value either, and for the same reason plus one of its own: a
# static method cannot distinguish a name the firmware never uses from a name
# it cannot see, so the cell says what was measured rather than proposing a
# status. The docstring's rule is that a blank reads as "measured, found
# nothing", which is the one reading this token exists to stop.
NOT_REFERENCED = "not-referenced-by-this-method"

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

# An ASL identifier, and a `Name (X, ...)` declaration. The identifier pattern
# starts at a letter or `_` so it never matches the `x1171` inside `0x1171`,
# and `Name` matches `Name (X, ...)` and `Name (\X, ...)` alike: iasl writes
# the leading `\` on a name that shadows an argument.
IDENT = re.compile(r"[A-Za-z_]\w*")
NAME_DECL = re.compile(r"^\s*Name\s*\(\s*\\?(\w+)\s*,")
# A `Method (NAME, n, flags)` header. The trailing comment is why this is
# matched against comment-stripped lines: `_WED` and `_REG` both carry one
# (dsdt.dsl:51439, 52522), and a method whose header does not match is a
# method this file silently stops counting Arg0 dispatches in.
METHOD = re.compile(r"^\s*Method\s*\(\s*(\w+)\s*,\s*\d+\s*,\s*\w+\s*\)\s*$")
# `Arg0 == 0x…`. A name and the symbolic constants (`Zero`, `One`) are
# deliberately not matched: only the vendor command protocol is counted here,
# because that is the thing a caller passes an argument to.
ARG0_EQ = re.compile(r"Arg0\s*==\s*(0x[0-9A-Fa-f]+)")
# An `If ((Arg0 == 0x…))` / `ElseIf ((Arg0 == 0x…))` header, with the
# optional `{}` an empty arm is written as (dsdt.dsl:50645) carried in the
# group so a header and the two tokens after it are told apart.
ARG0_ARM = re.compile(r"^\s*(?:If|ElseIf)\s*\(\(\s*Arg0\s*==\s*(0x[0-9A-Fa-f]+)"
                      r"\s*\)\)(\s*\{\s*\}\s*)?$")
# `Switch (Arg0)` and one `Case (…)` arm of it. The other spelling of the same
# dispatch, which `ARG0_EQ` does not match -- so a total read off `ARG0_EQ` is
# a total of the `==` spelling and not of the file, and saying otherwise is the
# mistake this pair of patterns exists to keep visible. `D3CS`, `RSON` and
# `RSOF` (dsdt.dsl:17262, 17342, 17420) dispatch this way over a hex literal;
# `CLKC` and `CLKF` (:6219, :6237) this way over the symbolic `Zero`/`One`,
# which is the exclusion `ARG0_EQ`'s own comment records, so the symbolic arms
# are collected rather than counted as nothing.
ARG0_SWITCH = re.compile(r"^\s*Switch\s*\(\s*Arg0\s*\)\s*$")
ARG0_CASE = re.compile(r"^\s*Case\s*\(\s*([^()]+?)\s*\)\s*$")
ARG0_CASE_HEX = re.compile(r"0x[0-9A-Fa-f]+")
# The comment forms iasl writes, and the string form. Blanking a string rather
# than deleting it keeps the offsets of everything after it, and a `{` inside
# a `NameTable` string would otherwise move the scope arithmetic.
BLOCK_COMMENT = re.compile(r"/\*.*?\*/")
LINE_COMMENT = re.compile(r"//.*$")
STRING = re.compile(r'"[^"]*"')


def strip_comments(lines) -> list:
    """`lines` with `/* */`, `//` and string bodies blanked, one line in, one out.

    Every count and every brace below is computed on this, not on the raw
    .dsl: the `NameTable` blocks at the end of the file are dense with `;` and
    `//` hex dumps, and an iasl alias comment is a *restatement* of the field
    it sits next to, so matching either would count one reference twice."""
    out = []
    for line in lines:
        stripped = LINE_COMMENT.sub("", BLOCK_COMMENT.sub(" ", line))
        out.append(STRING.sub('""', stripped))
    return out


def brace_span(code, start: int) -> tuple:
    """(`lines between the braces`, line the closing brace is on) from `start`.

    Braces are counted per line rather than by comparing against a bare `}`,
    because 2,335 lines of this file close a `NameTable` block with a `},` or
    a `})` on the same line as other tokens and a strict matcher would run
    every scope in the file to the end of it. A `}` seen before the block has
    opened is skipped rather than counted: that is the stray brace
    `parse_lists()` refuses a whole list over, and here it would drive the
    depth negative and swallow the rest of the file. Returns a `None` end
    line for a block that never closes."""
    depth = 0
    started = False
    body = []
    for j in range(start, len(code)):
        s = code[j].strip()
        opens, closes = s.count("{"), s.count("}")
        if opens:
            depth += opens
            started = True
        elif closes and not started:
            continue
        if closes:
            depth -= closes
            if depth <= 0:
                return body, j + 1
        if started:
            body.append((j + 1, code[j]))
    return body, None


def scope_of(code, lineno: int) -> tuple:
    """(first, last, node name) of the scope brace-enclosing `lineno`.

    Found by walking back out, not by hardcoding `Device (EC0)`'s two lines:
    a name's bare form is legal anywhere ASL would resolve it, and a rule that
    named one device's extent would silently undercount every other scope this
    file is pointed at. The node name is read off the header above the brace
    because it is the object the qualified form ends at --
    `^^PCI0.LPCB.EC0.CTWA` reaches CTWA through EC0 -- so a pattern keyed on a
    name typed in here would be one more thing to keep correct by hand.

    The first and last lines are the `{` and the `}`, so a name declared in a
    nested scope is attributed to the nested one and the outer one sees only
    what is left of it."""
    depth = 0
    for j in range(lineno - 2, -1, -1):
        s = code[j].strip()
        closes = s.count("}")
        if closes:
            depth += closes
        if s.count("{"):
            if depth < 1:
                return (j + 1, brace_span(code, j)[1],
                        scope_name(header_above(code, j)))
            depth -= s.count("{")
    raise FieldError(f"line {lineno} is not inside any scope; every bare "
                     "reference would be unattributable, so the name is "
                     "refused rather than counted against a guess")


def header_above(code, brace_index: int) -> str:
    """The nearest non-blank line above a `{`, which is what opens a scope.

    iasl writes `Device (EC0)` and its `{` on consecutive lines, but a
    `Name (X, Package (...) {` opens with the package's `{` and the header is
    a line further back -- so this walks rather than stepping once."""
    for j in range(brace_index - 1, -1, -1):
        if code[j].strip():
            return code[j]
    return ""


def scope_name(line: str) -> str:
    """The object name a `Device (X)`/`Scope (X)`/`Method (X, ...)` header
    declares, without the `^` that marks a relative path segment."""
    m = re.search(r"\(\s*(\^?\w+)\s*[,)]", line)
    return m.group(1).lstrip("^") if m else ""


def declarations(code) -> dict:
    """name -> (region, list line, list end, scope start, scope end, node).

    Every `Field` list in the file, not only the one being reported: a
    reference has to be attributed to the region that *declares* the name, and
    three of the four regions `Device (EC0)` declares sit behind one shared
    `^^PCI0.LPCB.EC0.` path -- `ECMG` (98 names, dsdt.dsl:52193), `ECMP` (1,
    :52330) and `ECXP` (94, :52337), the fourth being the `IO` port region at
    :52163. A count keyed on the path would merge the three into one region of
    193.

    Deliberately more forgiving than `extract()`. This asks only *which list
    declares a name*, and that survives an `Access` keyword or a computed
    `Offset` in a region this tool was not pointed at; refusing the whole file
    over another region's element widths would make the count depend on a list
    nobody is reporting. First declaration wins, as in `parse_regions()`, and
    ASL does not forbid one name in two lists: `PBSS` is declared in `PMIO`
    (:7950) before ECMG declares it, and `WUSB` in `OGNV` (:1493) before
    ECXP. The row for the later declaration therefore reports the earlier
    one's references rather than its own -- `WUSB` is reached for once, at
    :8163, and not at the `ECXP` element line that redeclares it at :52417,
    which `list_spans()` excludes. `--self-test` names both."""
    out = {}
    for i, line in enumerate(code):
        m = FIELD_OPEN.match(line)
        if not m:
            continue
        body, end = brace_span(code, i)
        if end is None:
            continue
        s_start, s_end, node = scope_of(code, i + 1)
        for _lineno, raw in body:
            t = raw.strip().rstrip(",").strip()
            n = NAMED.match(t)
            if n and n.group(1) not in out:
                out[n.group(1)] = (m.group(1), i + 1, end, s_start, s_end, node)
    return out


def list_spans(code) -> dict:
    """name -> [(list line, list end)] for *every* list that declares it.

    `declarations()` keeps the first declaration and drops the rest, but a
    dropped one is still a `Field` list, and a line inside a list is that
    name's declaration rather than a reference to it. `WUSB` is the live case:
    it is declared in `OGNV` (:1493) and again in `ECXP` (:52417), and OGNV's
    scope runs to :53348 -- so the ECXP element line falls inside the scope
    the *first* declaration resolves in, is not covered by the list the first
    declaration is written in, and came back as a reference. No ECMG name has
    a site inside a `Field` element line, so the committed table does not move;
    this is what `references()` needs and does not otherwise have."""
    out = {}
    for i, line in enumerate(code):
        m = FIELD_OPEN.match(line)
        if not m:
            continue
        body, end = brace_span(code, i)
        if end is None:
            continue
        for _lineno, raw in body:
            n = NAMED.match(raw.strip().rstrip(",").strip())
            if n:
                out.setdefault(n.group(1), []).append((i + 1, end))
    return out


def unplaceable(code, decls: dict, s_start: int, s_end: int) -> list:
    """[(line, name)] for a `Name (...)` in the scope that no list declares.

    Reported rather than dropped, and never attached to a field. `Name (THOT,
    Zero)` at dsdt.dsl:52190 is a live example: it sits under the same
    `^^PCI0.LPCB.EC0.` path every ECMG name is reached through, so a
    path-keyed scan files it as a reference, and there is no field for it to
    be a reference *to*. `_HID` and `_CRS` are the same shape and are as much
    a fact about the file as THOT is."""
    out = []
    for i in range(s_start, s_end + 1):
        m = NAME_DECL.match(code[i - 1])
        if m and m.group(1) not in decls:
            out.append((i, m.group(1)))
    return out


def scan_line(text: str) -> list:
    """[(name, kind, qualifier)] for one line -- the ASL reference candidates.

    `kind` is `bare` for an identifier no path separator precedes and
    `qualified` for one that has, with `qualifier` the object the path names.
    The two cannot be told apart by a pattern alone, because the same spelling
    is a reference or is not depending on the identifier in front of it:
    `EC0.CTWA` reads ECMG's CTWA, `UBTC.CTWA` is a field of an object this file
    only declares `External`, and in both lines the word is spelled the same.
    Marking the identifier after every separator keeps each occurrence in
    exactly one bucket, so nothing is counted twice."""
    ids = list(IDENT.finditer(text))
    out = []
    seen = set()
    for k, m in enumerate(ids):
        if k in seen:
            continue
        if text[m.end():].startswith((".", "_.")) and k + 1 < len(ids):
            seen.add(k + 1)
            out.append((ids[k + 1].group(0), "qualified",
                        m.group(0).rstrip("_")))
            continue
        out.append((m.group(0), "bare", None))
    return out


def references(code, decls: dict) -> dict:
    """name -> (occurrence count, sorted list of `dsdt.dsl` lines).

    A name is counted when it is reached for outside every `Field` list that
    declares it, and the *direction* is not measured: an occurrence of the name
    in a load, a store or a test is one reference either way, so a name the ASL
    only writes is as referenced as one it only reads. A qualified occurrence
    counts anywhere in the file, because the path names the object the field
    belongs to; a bare one counts only inside the scope that declares it,
    because that is where ASL would resolve it. Occurrences are matched per
    line against the whole file once, not once per name, so a 1,746-name
    declaration table costs one walk rather than 1,746."""
    counts = {name: 0 for name in decls}
    sites = {name: set() for name in decls}
    spans = list_spans(code)
    for i, text in enumerate(code, 1):
        for name, kind, qualifier in scan_line(text):
            d = decls.get(name)
            if d is None:
                continue
            _region, _ls, _le, s_start, s_end, node = d
            if any(a <= i <= b for a, b in spans.get(name, ())):
                continue
            if kind == "qualified":
                if qualifier != node:
                    continue
            elif not (s_start <= i <= s_end):
                continue
            counts[name] += 1
            sites[name].add(i)
    return {n: (counts[n], sorted(sites[n])) for n in decls}


def arg0_arms(code, first: int, last: int, decls: dict) -> list:
    """[(arg0, dsdt line, [field names])] for an `Arg0`-dispatching method.

    One tuple per `If`/`ElseIf` header, in source order, so the two arms on the
    same value stay two rows. A field is attributed the same way as anywhere
    else -- by the region that declares it -- and an arm that reaches a field
    through a path this file does not know comes back empty rather than
    borrowed. That is why `T1WR_ARMS`'s `0x1172` row is empty: the arm reads
    `NPCF.DBAC`, which no `Field` list in this file declares. That is the
    answer for that arm, not a gap in the scan."""
    arms = []
    for i in range(first, last + 1):
        m = ARG0_ARM.match(code[i - 1])
        if m:
            arms.append([int(m.group(1), 16), i, []])
            continue
        if not arms:
            continue
        for name, kind, qualifier in scan_line(code[i - 1]):
            if kind != "qualified" or name not in decls:
                continue
            if decls[name][5] == qualifier and name not in arms[-1][2]:
                arms[-1][2].append(name)
    return [tuple(a) for a in arms]


def arg0_dispatch(code) -> dict:
    """{method name: [arg0, ...]} for every method comparing `Arg0` to `0x…`.

    The population `T1WR` is a subset of, and it is a population of *this
    spelling*: `ARG0_EQ` matches `Arg0 == 0x…` and nothing else, so the
    thirty distinct values this returns are the thirty over the fourteen
    methods written that way, not the file's `Arg0` population. Three more
    methods dispatch on `Arg0` with `Switch (Arg0)` / `Case (0x…)` —
    `arg0_switch_dispatch` below — and seven of their values are not among
    these, which is why no total here may be written up as the file's.
    (The sweep doc `dsdt-ecmg-field-sweep.md` §1 commits to the thirty, so
    `--self-test` re-derives *that* figure rather than leaving a number in
    prose that nothing checks: thirteen other methods carry eleven further
    values between them, none of them one of T1WR's nineteen, and the two
    together are the thirty.)"""
    out = {}
    for i, line in enumerate(code):
        m = METHOD.match(line)
        if not m:
            continue
        body, end = brace_span(code, i)
        if end is None:
            continue
        values = [int(x.group(1), 16)
                  for j in range(i, end)
                  for x in ARG0_EQ.finditer(code[j])]
        if values:
            out[m.group(1)] = values
    return out


def arg0_switch_dispatch(code) -> tuple:
    """({name: [0x… value]}, {name: [symbol]}) over `Switch (Arg0)` methods.

    The other spelling of the same dispatch, kept apart from
    `arg0_dispatch` rather than merged into it: a merged total would read as
    a census of the file's `Arg0` population when it is a census of two
    spellings put together, which is a claim this file does not make and
    cannot check. The two buckets are the reason the population is stated
    where it is stated. The symbolic bucket is the `Zero`/`One` pair of
    `CLKC` and `CLKF` — deliberately not counted as command-protocol
    arguments, for the reason `ARG0_EQ`'s comment gives, and named here so
    that exclusion is a measurement rather than an omission."""
    hexed, symbolic = {}, {}
    name = None
    for i, line in enumerate(code):
        m = METHOD.match(line)
        if m:
            name = m.group(1)
            continue
        if name is None or not ARG0_SWITCH.match(line):
            continue
        body, end = brace_span(code, i)
        if end is None:
            continue
        for j in range(i, end):
            c = ARG0_CASE.match(code[j])
            if not c:
                continue
            token = c.group(1)
            if ARG0_CASE_HEX.fullmatch(token):
                hexed.setdefault(name, []).append(int(token, 16))
            else:
                symbolic.setdefault(name, []).append(token)
    return hexed, symbolic


def t1wr_table(arms: list, addrs: dict, registers: dict) -> list:
    """`T1WR_ARMS`'s own shape, rebuilt from the .dsl and registers.yaml.

    `addrs` is every name in `Device (EC0)` to its byte, from all four of its
    operation regions -- five `Field` lists, the `IO` port region carrying two
    of them -- and a name in one region and an arm reaching it from the other
    is the case the two-region correction is about, so the table resolves
    addresses across the device rather than within one region. A name no list
    declares has no entry and comes back as two empty strings, which is the
    table saying nothing rather than the table failing."""
    out = []
    for arg0, line, fields in arms:
        cells = []
        for f in fields:
            entry = registers.get(addrs.get(f))
            cells.append((f, entry["name"] if entry else "",
                          str(entry["status"]) if entry else ""))
        out.append((arg0, line, tuple(cells)))
    return out


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


def build_rows(fields: dict, counts, registers: dict, refs: dict) -> list:
    """One row per named element, in the order the .dsl declares them.

    `counts` is None for a region whose offsets are not XDATA addresses, and
    the three count cells say so rather than carrying a number. The two ASL
    columns take the same token for the same reason and not out of symmetry
    with the counts: this tool does not report about a NVS block, and a row
    that answered half its columns would invite reading the half it answered
    as a register map."""
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
        n, sites = refs.get(name, (0, []))
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
            "asl_refs": n if joinable else NOT_JOINED,
            "asl_sites": " ".join(str(s) for s in sites) if joinable and sites
            else (NOT_JOINED if not joinable else NOT_REFERENCED),
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
    joinable = fields["region"] in XDATA_REGIONS
    if joinable:
        used = [r for r in rows if r["asl_refs"]]
        sites = sum(len(r["asl_sites"].split()) for r in used)
        # The two halves are reported side by side and not joined, because
        # they are two questions. A name the ASL reaches for and the EC image
        # never names is the shape an indirect-addressing blind spot produces;
        # a name the EC image names and the ASL never reaches for is a byte the
        # firmware touches by an address the ASL does not spell. Which of the
        # 98 are which is the table's row, not a grade on the row. `used` is
        # every name the ASL reaches for, not only the ones it reads: the
        # direction is not a column, and eight of ECMG's referenced names are
        # written by `T1WR` and read nowhere.
        print(f"  {len(used)} of {named} name(s) are referenced by the ASL "
              f"outside their own field list, over {sites} (name, line) site(s)")
        both = [r for r in used if r["static_refs"]]
        print(f"  of those, {len(both)} have a site in the EC image as well; "
              f"{len(used) - len(both)} do not, which is a question about the "
              "EC's addressing and not about the ASL")
    print()
    if joinable:
        print(f"  {'addr':<8} {'bit':>3} {'w':>3} {'ec':>4} {'pd':>4} "
              f"{'asl':>4} {'name':<6} {'dsdt':>7}  held / grade")
        for r in rows:
            print(f"  {r['addr']:<8} {r['bit']:>3} {r['width']:>3} "
                  f"{r['static_refs_main_ec']:>4} {r['static_refs_pd_image']:>4} "
                  f"{r['asl_refs']:>4} "
                  f"{r['name']:<6} {r['dsdt_line']:>7}  "
                  f"{r['in_registers'] or '-'} / {r['grade']}")
        print("  (asl sites, for a row that has any:")
        for r in used:
            print(f"    {r['name']:<6} {r['asl_sites']}")
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

# Every `Arg0` arm of `Method (T1WR, 3, NotSerialized)` (dsdt.dsl:50635), as
# (arg0, header line, ((field, registers.yaml name, status), ...)).
#
# `--self-test` re-derives all three from source -- the fields from the parsed
# body, the lines from where the headers are, the entry and status from
# registers.yaml -- and compares. A row that drifts is red, so the table
# `docs/findings/ecmg-asl-references.md` quotes cannot survive a .dsl or a
# registers.yaml change without this going with it.
#
# Two rows carry the same arg0 and that is not a duplicate: the arm at :50657
# is the `0x1171` branch's immediate neighbour and reads nothing, the one at
# :50667 reads `CTWA`. A single dict keyed on arg0 would have dropped one of
# them, and the empty one is the half of that pair the reachability claim
# rests on.
T1WR_ARMS = [
    (0x81, 50637, (("APL1", "CPU_PL1 / PL2 / PL4 (APL1/APL2/APL4)",
                    "present-untested"),)),
    (0x82, 50641, (("APL2", "CPU_PL1 / PL2 / PL4 (APL1/APL2/APL4)",
                    "present-untested"),)),
    (0x83, 50645, ()),
    (0x84, 50646, (("APL4", "CPU_PL1 / PL2 / PL4 (APL1/APL2/APL4)",
                    "present-untested"),)),
    (0x85, 50650, (("APTN", "CPU_TCC_OFFSET (APTC/APTN)", "present-untested"),
                   ("APTC", "CPU_TCC_OFFSET (APTC/APTN)", "present-untested"))),
    (0x86, 50655, ()),
    (0x87, 50656, ()),
    (0x71, 50657, ()),
    (0x1171, 50658, (("CTWA", "CTWA", "present-untested"),)),
    (0x71, 50667, (("CTWA", "CTWA", "present-untested"),)),
    (0x1172, 50675, ()),
    (0x1173, 50680, (("DBD1", "DBD1 (DSDT name; ECSpec calls the same byte "
                      "BATTERY_CHARGE_LIMIT_DOWN)",
                      "unknown-not-absent-DO-NOT-WRITE-BLIND"),
                     ("DBD2", "DBD2 (DSDT name; no vendor constant, no "
                      "committed Windows writer)",
                      "unknown-not-absent-DO-NOT-WRITE-BLIND"))),
    (0x2273, 50693, ()),
    (0x73, 50700, (("DBEN", "GPU_DYNAMIC_BOOST_STATUS (DSDT DBEN bit 3, "
                      "DBST bit 5)", "present-untested"),
                   ("CPUA", "CPUA (DSDT)", "present-untested"),
                   ("DBAP", "DBAP (DSDT)", "present-untested"))),
    (0x74, 50719, ()),
    (0x1175, 50720, ()),
    (0x75, 50725, (("WHMS", "WHMS", "present-untested"),)),
    (0x1176, 50730, (("CGCT", "CGCT (DSDT)", "unknown-not-absent"),)),
    (0x76, 50735, ()),
    (0x61, 50739, ()),
]

# The two `0x71` arms, as (line, reads a field). Kept beside the table so the
# reachability claim in the write-up is a pair of numbers here rather than a
# sentence there. :50657 is matched by any caller passing 0x71 and so leaves
# the chain before :50658 matches 0x1171; :50667 therefore has no caller that
# can reach it. Checked by the self-test against every other method that
# dispatches on `Arg0` in the file -- the thirteen `==` ones and the three
# `Switch` ones, and none of the sixteen carries 0x71 -- for a chain is only
# unreachable within this method unless a second one says so too. The
# `CLKC`/`CLKF` pair is symbolic and cannot carry it.
T1WR_REDUNDANT = (50657, 50667)

# The `Case` arms of the three `Switch (Arg0)` methods that dispatch over a hex
# literal, pinned for the same reason `T1WR_ARMS` is: the population they
# complete is the file's `Arg0` population, and a number in prose about it is
# worth nothing. Ten values each, of which three (0x04, 0x06, 0x08) are
# already among the thirty the `==` methods carry, so seven are further and
# the two spellings together come to 37.
SWITCH_ARMS = {
    "D3CS": [0x04, 0x06, 0x08, 0x0a, 0x0c, 0x0e, 0x10, 0x12, 0x14, 0x16],
    "RSON": [0x04, 0x06, 0x08, 0x0a, 0x0c, 0x0e, 0x10, 0x12, 0x14, 0x16],
    "RSOF": [0x04, 0x06, 0x08, 0x0a, 0x0c, 0x0e, 0x10, 0x12, 0x14, 0x16],
}


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

    # -- the ASL half -------------------------------------------------------
    code = strip_comments(lines)
    decls = declarations(code)
    refs = references(code, decls)
    node, s_start, s_end = decls["CTWA"][5], decls["CTWA"][3], decls["CTWA"][4]
    used = [e for e in ecmg["elements"] if refs[e[0]][0]]
    site_pairs = sum(len(refs[e[0]][1]) for e in used)
    check(f"ECMG's list is declared in Device ({node}) at dsdt.dsl:52161, "
          f"braces {s_start}-{s_end}, found by walking out of them rather than "
          "written down here",
          (node, s_start, s_end) == ("EC0", 52162, 52985))
    check(f"{len(used)} of the {len(ecmg['elements'])} ECMG names are "
          f"referenced by the ASL outside their own field list, over "
          f"{site_pairs} (name, line) site(s)",
          len(used) == 35 and site_pairs == 52)
    # Spot-checks on three different shapes. The three rules that would each
    # be wrong about the 35-over-52 above do not agree on a wrong answer --
    # against the committed .dsl a qualified-only scan gives 15 names over 27
    # sites, a bare scan with no scope bound 27 over 49, and one that drops
    # the scope and qualifier attribution 37 over 76 -- so the total
    # discriminates between them. These cases pin each rule on its own
    # anyway, which a total cannot: two rules can produce the same number by
    # accident, and a rule relaxed later is the one a count would not catch.
    check("CTWA is reached for 4 times over 4 lines -- the 0x1171 arm writes "
          "it at :50662 and reads it back at :50663, the 0x71 arm reads it at "
          ":50670, and _Q83 reads it bare at :52787, which a qualified-only "
          "scan misses. It is the one ECMG name the ASL both writes and reads",
          refs["CTWA"] == (4, [50662, 50663, 50670, 52787]))
    check("MGI8 is reached for once, by the bare form at :52955; the twenty "
          "other MGI/CCI names ride the same line shape and the `UBTC.` on the "
          "left of each is a write to another object, not one of them",
          refs["MGI8"] == (1, [52955]) and refs["CCI0"] == (1, [52963]))
    check("CTL0 is declared and never reached for, which is the split the "
          "finding is about: an EC-side site at 0x0EA8 and no ASL reference "
          "at all",
          refs["CTL0"] == (0, []))
    check("PDIN is 18 occurrences over 8 lines -- three in one `||` chain at "
          ":50774, two split across :50828-50829 -- so the count and the site "
          "list are not the same measurement",
          refs["PDIN"] == (18, [50774, 50786, 50801, 50813, 50828, 50829,
                                50841, 50856]))
    # The two corrections the finding rests on, pinned here so a change to the
    # .dsl that moves either turns this red rather than leaving the prose to
    # be the only place it is written down.
    sixteen = ["PDIN", "CTWA", "GC6S", "WHMS", "AP01", "AP02", "AP10",
               "MGI8"] + [f"CTL{i}" for i in range(8)]
    live = [n for n in sixteen if refs[n][0]]
    check(f"{len(live)} of the {len(sixteen)} names registers.yaml took in "
          f"the field sweep are referenced by the ASL -- {', '.join(live)} -- "
          f"and {len(sixteen) - len(live)} are declared only",
          sorted(live) == ["CTWA", "MGI8", "PDIN", "WHMS"]
          and all(n in {e[0] for e in ecmg["elements"]} for n in sixteen))
    page = [e for e in ecmg["elements"] if 0x0E00 <= e[1] <= 0x0EFC]
    check(f"{sum(1 for e in page if refs[e[0]][0])} of the {len(page)} names on "
          "the 0x0Exx page are referenced by the ASL, and they are CCI0-CCI3 "
          "and MGI0-MGIF reached for as one run -- so the sweep's §5 question "
          "is about bytes the ASL uses and the static scan cannot see, not "
          "about bytes nothing declares",
          len(page) == 59
          and sum(1 for e in page if refs[e[0]][0]) == 20
          and [e[0] for e in page if refs[e[0]][0]][:4] == ["CCI0", "CCI1",
                                                            "CCI2", "CCI3"])
    # The two names ASL declares twice, first in an earlier region. Not a
    # refusal -- first declaration wins is the same rule `parse_regions()` uses
    # -- but the later row reports the earlier declaration's references, and
    # the element line that redeclares the name is a declaration rather than
    # one more reference: WUSB is in `OGNV` (:1493) and again in `ECXP`
    # (:52417), and OGNV's scope runs to :53348, so :52417 is inside the scope
    # the first declaration resolves in and outside the list it is written in.
    check("one ECMG name and one ECXP name are declared in an earlier list "
          "first -- PBSS in PMIO (:7950), WUSB in OGNV (:1493) -- so those "
          "two rows report the earlier declaration's references: WUSB's one "
          "read at :8163, and not the ECXP element line at :52417",
          decls["PBSS"][:2] == ("PMIO", 7950)
          and decls["WUSB"][:2] == ("OGNV", 1493)
          and refs["PBSS"] == (0, [])
          and refs["WUSB"] == (1, [8163]))
    # Three regions behind one path prefix: attributing a reference to the path
    # rather than to the declaring region merges ECMG's 98 with ECXP's 94.
    ecxp = extract(lines, DEFAULT_DSDT, "ECXP")
    check(f"Device (EC0) declares ECMG, ECMP and ECXP, and a reference to an "
          f"ECXP name does not land on an ECMG row: {len(ecxp['elements'])} "
          "ECXP names, none of them an ECMG one",
          {e[0] for e in ecxp["elements"]}.isdisjoint(
              {e[0] for e in ecmg["elements"]})
          and decls["BFLG"][0] == "ECXP" and refs["BFLG"][0] == 10)
    # ECXP's half of the same measurement, pinned because the WUSB correction
    # above moves it: 35 of 94 names over 66 occurrences on 65 lines, of which
    # 14 are inside `Device (EC0)`'s own braces and 51 are in methods defined
    # outside it. Written into the finding's follow-up, so a rule change that
    # moved either half would otherwise leave a number in prose nothing checks.
    ecxp_used = [e[0] for e in ecxp["elements"] if refs[e[0]][0]]
    ecxp_lines = {i for n in ecxp_used for i in refs[n][1]}
    inside = [i for i in ecxp_lines if s_start <= i <= s_end]
    check(f"{len(ecxp_used)} of the {len(ecxp['elements'])} ECXP names are "
          f"referenced by the ASL, over "
          f"{sum(refs[n][0] for n in ecxp_used)} occurrences on "
          f"{len(ecxp_lines)} lines, of which {len(inside)} are inside "
          f"Device ({node}) and {len(ecxp_lines) - len(inside)} are not",
          len(ecxp_used) == 35
          and sum(refs[n][0] for n in ecxp_used) == 66
          and len(ecxp_lines) == 65 and len(inside) == 14)
    stranded = unplaceable(code, decls, s_start, s_end)
    check("`Name (THOT, Zero)` at dsdt.dsl:52190 is under the EC0 path with no "
          "field list declaring it, so it is reported unplaceable rather than "
          "attached to a field: " + ", ".join(f"{n}:{l}" for l, n in stranded),
          (52190, "THOT") in stranded)
    # The iasl alias comment is a third, independent attribution: iasl wrote
    # it, from the resolved path, and the count above came from the code. If a
    # scope rule were subtly too narrow this is the check that says so.
    alias = re.compile(r"/\*\s*\\_SB_\.PCI0\.LPCB\.EC0_\.(\w+)\s*\*/")
    checked, agree, unplaceable_alias = 0, True, []
    for i, raw in enumerate(lines, 1):
        for m in alias.finditer(raw):
            name = m.group(1)
            checked += 1
            if name in decls:
                agree = agree and i in refs[name][1]
            else:
                unplaceable_alias.append((i, name))
    check(f"all {checked - len(unplaceable_alias)} of iasl's own `EC0_.NAME` "
          "alias comments that name a field agree with the count above, site "
          "for site",
          checked == 52 and agree and len(unplaceable_alias) == 2)
    check("the two that name OSEC are references to a `Name` no field list "
          "declares, which is the unplaceable case and not a reference to "
          f"nothing: the declaration is at dsdt.dsl:"
          f"{[l for l, n in stranded if n == 'OSEC']}",
          unplaceable_alias == [(52543, "OSEC"), (52983, "OSEC")]
          and [l for l, n in stranded if n == "OSEC"] == [52189])

    # -- T1WR ---------------------------------------------------------------
    # Every region in Device (EC0), not ECMG alone: an arm reaching an ECXP
    # name has to report that name's address, and a table that quietly left it
    # out would read as an arm that touches nothing.
    addrs = {e[0]: e[1] for e in ecmg["elements"]}
    for other in ("ECXP", "ECMP", "IO"):
        addrs.update({e[0]: e[1] for e in
                      extract(lines, DEFAULT_DSDT, other)["elements"]})
    check(f"all {len(T1WR_ARMS)} of T1WR's Arg0 arms re-derive from the "
          "committed .dsl and registers.yaml -- value, header line, the field "
          "each reaches, and that field's entry and status",
          t1wr_table(arg0_arms(code, 50636, 50746, decls), addrs, registers)
          == T1WR_ARMS)
    values = arg0_dispatch(code)
    t1wr = values.get("T1WR", [])
    eq_values = {v for vs in values.values() for v in vs}
    check(f"T1WR dispatches on {len(t1wr)} comparisons over "
          f"{len(set(t1wr))} distinct values, and the {len(eq_values)} "
          f"distinct values carried by the {len(values)} method(s) that "
          "compare Arg0 against a 0x.. literal with == are the total "
          "dsdt-ecmg-field-sweep.md §1 commits to",
          len(t1wr) == 20 and len(set(t1wr)) == 19 and len(eq_values) == 30)
    sw_hex, sw_sym = arg0_switch_dispatch(code)
    sw_values = {v for vs in sw_hex.values() for v in vs}
    further = sw_values - eq_values
    check(f"that == spelling is not the whole file: {sorted(sw_hex)} dispatch "
          f"on Arg0 with Switch (Arg0) / Case (0x..) over "
          f"{len(sw_values)} values, {len(further)} of them outside the "
          f"{len(eq_values)} above, so the file's Arg0 population is "
          f"{len(eq_values | sw_values)} over "
          f"{len(values) + len(sw_hex)} method(s) and the 30 is a count of "
          "one spelling",
          sw_hex == SWITCH_ARMS
          and len(eq_values | sw_values) == 37
          and sorted(further) == [0x0a, 0x0c, 0x0e, 0x10, 0x12, 0x14, 0x16])
    check(f"{sorted(sw_sym)} dispatch on Arg0 too, but over the symbolic "
          "Zero/One that ARG0_EQ excludes by design, so they are named as "
          "excluded rather than left uncounted and unmentioned",
          sw_sym == {"CLKC": ["Zero", "One"], "CLKF": ["Zero", "One"]})
    first_71, second_71 = T1WR_REDUNDANT
    empty = [a for a in T1WR_ARMS if a[0] == 0x71]
    check(f"the two 0x71 arms are ten lines apart, not consecutive: the one at "
          f"dsdt.dsl:{first_71} reads nothing and is the 0x1171 arm's "
          f"immediate neighbour, so the arm at :{second_71} that reads CTWA "
          "has no Arg0 that can reach it -- and none of the thirteen == "
          "methods or the three Switch ones carries 0x71 either, so the "
          "conclusion is not resting on a spelling the scan did not read",
          [a[1] for a in empty] == [first_71, second_71]
          and empty[0][2] == () and len(empty[1][2]) == 1
          and not any(0x71 == v for m, vs in values.items() if m != "T1WR"
                      for v in vs)
          and 0x71 not in sw_values)

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
    code = strip_comments(lines)
    decls = declarations(code)
    try:
        refs = references(code, decls)
    except FieldError as e:
        print(f"note: {repo_path(args.dsdt)}: {e}", file=sys.stderr)
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

    rows = build_rows(fields, counts, load_registers(args.registers), refs)

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
