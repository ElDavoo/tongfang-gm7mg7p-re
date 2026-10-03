#!/usr/bin/env python3
"""Every destination the EC's CODE-table helpers write, including the ones no
`MOV DPTR` scan can see.

`ec/annotations/xdata-0440-readers.md` §5 records the discovery by hand:
`code_table_scatter_to_xdata` (bank1 `0xA530`) walks a table in CODE, and each
of its records names an XDATA destination and a value to store there, so the
destination address is *in the table* rather than in an instruction. A byte
scan for `mov DPTR,#addr` cannot see that class at all -- the pointer is
restored from two table bytes, not loaded -- which is why `0x0440` had 43
reader rows and no writer row. This makes the discovery a method: it walks the
helper's call sites, decodes the table each one names, and reports every record
with its destination.

**Where the call sites come from.** `../annotations/bank-call-targets.csv`, not
a byte scan. That file is a committed census of every direct call in the main
EC image, so the seven `lcall 0xA530` rows are a fact about the tree rather
than a threshold somebody chose, and a call added to the firmware is already
in the input when this runs. Sites the decoder cannot resolve are *reported*,
not skipped: a call this tool silently drops is indistinguishable from a call
the firmware does not have.

**The argument rule is a shape, and the tool asserts it rather than assuming
it.** Every `0xA530` call site is immediately preceded by
`mov DPTR,#imm16` (`90 hi lo`) then `mov R2,#imm8` (`7A nn`), and that pair is
the whole of the table's base and length. `decode_call_site()` checks all three
opcodes and refuses anything else rather than reading `imm16` out of whatever
happens to be five bytes back. A window guess would be the alternative, and it
would silently decode a table that is not there; the refusal is what lets a
caller tell "no table here" from "a table this tool cannot see".

**A record is not a writer the EC acts on.** Every row here is a *stored value*
read out of a committed table. It is not a readback, not a behavioural test,
and not evidence the firmware uses the byte afterwards -- CLAUDE.md's
readback-is-not-acting rule applies with the force of a dictionary here, and
the eight `0x00` seeds on the `0x0400`-`0x045F` page mean "the record stores
zero", never "the byte reads as zero" and never "inert". The four non-zero
seeds there are no stronger a claim: `0x043E`=`0x20` and `0x0457`=`0x83`,
`0x80` and `0x05` are what the records store, not what the bytes hold.
Nothing in this tool moves a `status:` in `../annotations/registers.yaml`, and
`static_refs*` does not move either: those keys are `MOV DPTR` counts recomputed
from the image by `check_register_counts.py`, and a record in CODE is not a
`MOV DPTR` site. That is the mechanism, not a discrepancy to explain away.

**The second helper is the same class in a different shape.**
`init_xdata_from_code_table_64fd` (bank0 `0xBFDE`) keeps its base and count
*inside* the routine -- a `mov DPTR,#0x64FD` and a `cjne A,#0x5a` loop bound --
rather than in the caller's arguments, so `HELPERS` dispatches on the shape and
a third helper is a new row rather than a rewrite of the decode. Its records
are all in `0x1600`-`0x16F0`, which is what `xdata-0440-readers.md` §7.3
already bounded; carrying it here makes the class one population instead of two
findings. **Its table belongs to the routine, not to the caller**, so its rows
are emitted once with the routine's own address in the `call_site` column, and
a second committed call site of `0xBFDE` would not duplicate them.

Usage:
    python3 code_table_records.py ../firmware/GMxMGxx_11.800
    python3 code_table_records.py ../firmware/GMxMGxx_11.800 --csv
    python3 code_table_records.py ../firmware/GMxMGxx_11.800 --csv --page 0x0400-0x045F
    python3 code_table_records.py ../firmware/GMxMGxx_11.800 --check
    python3 code_table_records.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import csv
import difflib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ANNOT = os.path.join(HERE, os.pardir, "annotations")
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")
CALL_TARGETS = os.path.join(ANNOT, "bank-call-targets.csv")
RECORDS_CSV = os.path.join(ANNOT, "xdata-code-table-records.csv")

# Read rather than restated, for the reason `inc_dptr_sites.py` gives: the bank
# windows are one table, and a tool that spelled out the ranges itself would be
# one edit away from reading every bank1 record out of bank0's bytes. A CODE
# address has the same runtime value in either bank image, so the *region* is
# what picks the file offset.
from disasm8051 import OPCODE_LEN  # noqa: E402
from trace_xdata_refs import REGIONS  # noqa: E402

MOV_DPTR = 0x90
MOV_R2_IMM = 0x7A
LCALL = 0x12
MOVC = 0x93
CJNE_A_IMM = 0xB4
RET = 0x22

# A record is a big-endian XDATA address and the value stored there, so the
# stride is fixed by the two helpers' own code -- `0xA530` pushes the two
# leading bytes and pops them into DPL/DPH, `0xBFDE` reads them with a `movc`
# at A=0 and A=1 and moves them into DPL/DPH the same way. `RECORD_LEN` is
# re-checked against the bytes in `--self-test` rather than trusted, because it
# is the one number here a different table shape would move.
RECORD_LEN = 3

COLUMNS = ("helper", "call_site", "record_index", "code_runtime",
           "code_file_offset", "xdata", "value")

# How far into a routine the in-routine shape looks for its base and its loop
# bound. A bound and not a parse: nothing here establishes where `0xBFDE`
# ends, so the scan stops at the routine's own `ret` and a base past that is
# reported as not found rather than assumed absent. That is the
# `registers.yaml` caveat again -- "not found by this method" is the strongest
# thing a scan of committed bytes may say.
ROUTINE_WINDOW = 128

# The helpers this class reaches, and where each keeps its table's base and
# count. Listed rather than globbed: a table walked by a helper nobody
# enumerated is exactly the exclusion `xdata-0440-readers.md` §7.3 ends on,
# and a reader has to be able to see what was left out.
#
# `base` and `count` are what `--self-test` re-derives from the image and
# compares against, so a stale constant here shows up as a self-test failure
# rather than quietly decoding some other table.
HELPERS = (
    {"name": "code_table_scatter_to_xdata", "region": "bank1",
     "target": 0xA530, "shape": "args_at_call_site"},
    {"name": "init_xdata_from_code_table_64fd", "region": "bank0",
     "target": 0xBFDE, "shape": "args_in_routine",
     "base": 0x64FD, "count": 0x5A},
)


class Undecodable(Exception):
    """A table this tool will not guess at, and why.

    Raised rather than returned so a caller cannot forget to handle it: the
    whole point of checking the `90`/`7A` shape is that a site the decoder
    skips is indistinguishable from a site the firmware does not have, and a
    return value that reads `None` is easy to drop on the floor. `main()`
    turns it into a stderr line and a non-zero exit.
    """


def file_offset_for(region: str, runtime: int):
    """File offset of a `region` runtime address, or None outside it."""
    for name, lo, hi, base, _ in REGIONS:
        if name == region and base is not None:
            off = lo + (runtime - base)
            if lo <= off < hi:
                return off
    return None


def file_region(off: int):
    """The region a file offset falls in, or None in an unmapped window."""
    for name, lo, hi, _, _ in REGIONS:
        if lo <= off < hi:
            return name
    return None


def decode_call_site(d: bytes, off: int):
    """(`base`, `count`) for a call site at file offset `off`, or raise.

    The rule is five bytes: `90 hi lo 7A nn` immediately before the `lcall`.
    The `lcall` itself is checked too, because a `file_offset` that had drifted
    off the instruction boundary would otherwise decode five bytes of *data* as
    an argument pair and report a table built out of a table's contents.

    Each refusal names the opcode actually found, because the alternative is a
    message that says only "undecodable" and leaves a reader to go looking for
    the reason: `mov R2,Rn` at the R2 slot (`0x8A`) is a real possibility for a
    helper that took its length from a register, and it should read as itself
    in the failure.
    """
    if off < 5 or off >= len(d):
        raise Undecodable(
            f"offset 0x{off:05X} is not inside the {len(d)}-byte image, so "
            f"there is no instruction at it to decode an argument pair from")
    if d[off] != LCALL:
        raise Undecodable(
            f"no `lcall` (0x{LCALL:02X}) at 0x{off:05X}, found 0x{d[off]:02X}: "
            f"the census row is not a call site")
    if d[off - 5] != MOV_DPTR:
        raise Undecodable(
            f"0x{off - 5:05X} is 0x{d[off - 5]:02X}, not `mov DPTR,#imm16` "
            f"(0x{MOV_DPTR:02X}): this call site does not pass a literal "
            f"table base")
    if d[off - 2] != MOV_R2_IMM:
        raise Undecodable(
            f"0x{off - 2:05X} is 0x{d[off - 2]:02X}, not `mov R2,#imm8` "
            f"(0x{MOV_R2_IMM:02X}): the record count is not a literal here, "
            f"so the table's length is not recoverable from the call site")
    return (d[off - 4] << 8) | d[off - 3], d[off - 1]


def routine_table(d: bytes, region: str, runtime: int):
    """(`base`, `count`) for a helper that keeps them in its own body.

    The in-routine shape: a `mov DPTR,#imm16` in the helper's own listing is
    the table's base and the `cjne A,#imm` that closes the loop is its length.
    Both are found by walking the routine's *instructions*, using
    `disasm8051.OPCODE_LEN` for the step, so an operand byte is never read as
    an opcode. A byte scan would not do: `0xBFDE` sets DPTR to `0x1674` for an
    unrelated store and then reaches a `movc` five instructions later, so a
    scan that asked "is there a `0x93` within 24 bytes of this `0x90`" would
    answer yes and pick the wrong base.

    The base is the `mov DPTR` whose following code reads **two** bytes before
    it sets DPTR again -- the two leading bytes that become the destination's
    high and low halves. `0xBFDE` also loads `0x64FF` and reads one byte from
    it, which is the *value* of the record at `0x64FD + 2`; taking the first
    qualifying `mov DPTR` instead of the one that reads the pair would land two
    bytes into every record.
    """
    start = file_offset_for(region, runtime)
    if start is None:
        raise Undecodable(
            f"{region} runtime address 0x{runtime:04X} is outside every "
            f"mapped region, so the routine cannot be located")
    if start >= len(d):
        # Distinct from the "no `mov DPTR`" answer below, and it has to be:
        # an address that maps cleanly onto a region past the end of the
        # buffer is a short image, not a routine whose table is absent.
        raise Undecodable(
            f"{region} runtime address 0x{runtime:04X} maps to file "
            f"0x{start:05X}, past the end of the {len(d)}-byte image, so "
            f"there are no bytes there to read the table's base from")
    end = min(start + ROUTINE_WINDOW, len(d))
    base = count = None
    # The DPTR currently in force, and how many bytes have been read through
    # it since. Reset at every `mov DPTR` so a count cannot carry across two
    # unrelated tables.
    current, reads = None, 0
    i = start
    while i < end:
        op = d[i]
        # An instruction that claims more bytes than remain is not one this
        # walk can read an operand out of. Stopping is the honest answer: the
        # routine's tail is truncated, so what is past here is not decoded,
        # and the refusal below already says which of the two the table was
        # missing.
        if i + OPCODE_LEN[op] > len(d):
            break
        if op == MOV_DPTR:
            current, reads = (d[i + 1] << 8) | d[i + 2], 0
        elif op == MOVC and current is not None:
            reads += 1
            if reads >= 2 and base is None:
                base = current
        elif op == CJNE_A_IMM and count is None:
            count = d[i + 1]
        i += OPCODE_LEN[op]
        if op == RET:
            break
    if base is None or count is None:
        missing = []
        if base is None:
            missing.append("a `mov DPTR` two bytes are read through")
        if count is None:
            missing.append("a `cjne A,#imm` loop bound")
        raise Undecodable(
            f"{region} 0x{runtime:04X} has no {' and no '.join(missing)} "
            f"within {ROUTINE_WINDOW} bytes of its entry (stopped at "
            f"0x{i:05X}), so its table is not recoverable by this method")
    return base, count


def table_for(d: bytes, helper, off: int, region: str):
    """(`base`, `count`, `region`) for one helper's table.

    `region` is where the *table* lives, which is not always the helper's own
    region: `0xBFDE` is bank0 code reading a table in the common area at
    `0x64FD`, and reading bank0's bytes at that address would decode `0x8FFD`
    instead. The two are equal for every in-bank table and differ for this
    one, so the shape decides.
    """
    shape = helper["shape"]
    if shape == "args_at_call_site":
        base, count = decode_call_site(d, off)
        table_region = region
    elif shape == "args_in_routine":
        base, count = routine_table(d, helper["region"], helper["target"])
        table_region = file_region(file_offset_for(helper["region"], base) or 0)
        table_region = table_region or helper["region"]
    else:
        raise ValueError(f"unknown helper shape {shape!r} for "
                         f"{helper['name']}: add it to HELPERS rather than "
                         f"letting it fall through")
    return base, count, table_region


def record_at(d: bytes, base: int, region: str, index: int):
    """(`xdata`, `value`, `code_runtime`, `code_file_offset`) for one record.

    The destination is big-endian -- the record's first byte is the high half
    and its second the low, which is what both helpers do with the two bytes
    they put back into `DPH` and `DPL`. The value is the third byte, stored to
    that address.

    A record whose bytes run past the end of the image is a truncation, and it
    is raised rather than padded: a partial record read as a whole one would
    put a destination in the table that no store ever reached.
    """
    runtime = base + RECORD_LEN * index
    off = file_offset_for(region, runtime)
    if off is None or off + RECORD_LEN > len(d):
        raise Undecodable(
            f"{region} record {index} at 0x{runtime:04X} runs past the end "
            f"of the image, so the table is truncated here rather than ending "
            f"where the count says")
    return (d[off] << 8) | d[off + 1], d[off + 2], runtime, off


def call_sites(helper, path: str = CALL_TARGETS):
    """Every committed `lcall` row naming `helper`'s target, in file order.

    Read from the committed census rather than found by scanning for the
    `12 lo hi` bytes, because a byte scan of an 8051 image counts operand
    bytes as opcodes -- `xdata-0440-readers.md` §7.3's own exclusion is
    written for that reason. A CSV without the columns this needs raises
    rather than matching nothing: a census that silently matches no rows
    reports zero records and reads as a clean sweep.
    """
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        needed = {"region", "runtime", "file_offset", "target"}
        if not reader.fieldnames or not needed.issubset(reader.fieldnames):
            raise ValueError(
                f"{os.path.relpath(path)} has no "
                f"{'/'.join(sorted(needed))} columns: it is not a bank "
                f"call-target census")
        # Compared as ints, not as strings. `target.upper()` looks like the
        # obvious spelling and is not: it uppercases the `x` too, so a helper
        # asked for `0xA530` matches nothing and `collect()` returns an empty
        # population that reads as a clean sweep. A numeric compare cannot
        # spell the target's `0x` half-width and miss on it.
        found = []
        for row in reader:
            try:
                target = int(row["target"], 16)
            except ValueError:
                continue
            if target == helper["target"] and row["region"] != "pd-image":
                found.append(row)
        return found


def rows_for(d: bytes, helper, site_label: str, base: int, count: int,
             region: str, bad: list):
    """One dict per record, appending a refusal to `bad` and stopping there.

    A truncated table is reported at the record it truncates and no further
    rows are emitted for it: emitting the rest would be decoding past a table
    that the image does not contain.
    """
    out = []
    for i in range(count):
        try:
            xdata, value, code_rt, code_off = record_at(d, base, region, i)
        except Undecodable as e:
            bad.append((helper["name"], site_label, str(e)))
            break
        out.append({"helper": helper["name"],
                    "call_site": site_label,
                    "record_index": i,
                    "code_runtime": f"0x{code_rt:04X}",
                    "code_file_offset": f"0x{code_off:05X}",
                    "xdata": f"0x{xdata:04X}",
                    "value": f"0x{value:02X}"})
    return out


def collect(d: bytes, path: str = CALL_TARGETS):
    """(rows, undecodable) for every record of every helper this tool knows.

    `rows` is a list of dicts in the shape `COLUMNS` names, sorted by helper
    then call site then record index so two runs cannot differ in order.
    `undecodable` is a list of `(helper, site, reason)`: tables that are in
    the census and this tool will not decode, kept rather than dropped so
    `main()` can fail on them and a reader can see what was left out.

    The two shapes are separate passes rather than one loop with a special
    case in it, because they do not mean the same thing by `call_site`: for
    `args_at_call_site` it is the call whose arguments name the table, and for
    `args_in_routine` the table belongs to the routine, so it is the routine's
    own address and one routine emits its table once however many callers it
    has.
    """
    rows, bad = [], []
    for helper in HELPERS:
        if helper["shape"] == "args_in_routine":
            label = f"0x{helper['target']:04X}"
            try:
                base, count, region = table_for(d, helper, None,
                                                helper["region"])
            except Undecodable as e:
                bad.append((helper["name"], label, str(e)))
                continue
            rows += rows_for(d, helper, label, base, count, region, bad)
            continue
        sites = call_sites(helper, path)
        if not sites:
            # A helper in HELPERS that the census names no call site for is a
            # question about the census, not an empty result. `0xA530` has
            # seven and `0xBFDE` one, so a zero here means the lookup broke
            # rather than that the firmware stopped calling it -- and it
            # broke silently once, when the target column was compared as an
            # uppercased *string* and `0xA530` matched no row at all.
            bad.append((helper["name"], f"0x{helper['target']:04X}",
                        f"no committed call site names 0x{helper['target']:04X}"
                        f" in {os.path.relpath(path)}: the census lookup found"
                        f" nothing, which is a question about the lookup"))
            continue
        for site in sites:
            try:
                base, count, region = table_for(d, helper,
                                                int(site["file_offset"], 16),
                                                site["region"])
            except Undecodable as e:
                bad.append((helper["name"], site["runtime"], str(e)))
                continue
            rows += rows_for(d, helper, site["runtime"], base, count, region,
                             bad)
    rows.sort(key=lambda r: (r["helper"], int(r["call_site"], 16),
                             r["record_index"]))
    return rows, bad


def parse_page(text: str):
    """(`lo`, `hi`) inclusive from a `0x0400-0x045F` argument, or raise.

    A range rather than a single address because the page is the unit
    `xdata-0400-045f.md` §6 is written in, and a filter taking one address
    would put one address's rows where a reader expects a page's.
    """
    parts = text.split("-")
    if len(parts) != 2:
        raise ValueError(
            f"--page {text!r} is not a RANGE like 0x0400-0x045F: the unit the "
            f"write-up filters on is a page, not an address")
    lo, hi = (int(p, 16) for p in parts)
    if hi < lo:
        raise ValueError(f"--page {text!r} ends before it starts")
    return lo, hi


def render(rows, page=None) -> str:
    """The committed table: a header and one line per record, CRLF.

    The csv module's own line terminator, because that is what every committed
    table in `../annotations/` carries and `check_table()` reads the file with
    `newline=""` to match -- universal-newline translation would report a
    difference on every run, which is `trace_xdata_refs`'s reason and this
    file's too.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    lo, hi = page if page else (None, None)
    for row in rows:
        if lo is not None and not lo <= int(row["xdata"], 16) <= hi:
            continue
        writer.writerow(row)
    return buf.getvalue()


def check_table(generated: str, path: str) -> int:
    """Exit code for `--check`: 0 when this run reproduces `path` exactly."""
    try:
        with open(path, newline="") as handle:
            on_disk = handle.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if generated == on_disk:
        print(f"{os.path.relpath(path)}: this run reproduces it byte for byte "
              f"({generated.count(chr(10))} lines)")
        return 0
    print(f"note: {os.path.relpath(path)} differs from what this run "
          f"produced; the file is the product of the command on the page that "
          f"names it, so regenerate rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(),
                                     generated.splitlines(),
                                     "committed", "generated", lineterm="",
                                     n=0):
        print(line, file=sys.stderr)
    return 1


def self_test(d: bytes) -> int:
    """The invariants `--check` cannot see, on the committed image.

    `--check` holds a *table* against a regeneration, and three things sit
    underneath it that a diff cannot catch. They are what this runs:

    - the in-routine helper's recorded base and count are re-derived from the
      image, so a stale constant in `HELPERS` cannot decode a different table
      and still reproduce the committed CSV;
    - every committed call site resolves, so a `file_offset` that has drifted
      off the instruction boundary is caught here rather than as a mysterious
      column change;
    - the fixture half: a hand-built buffer carrying each shape and each
      refusal, decoded on its own bytes. The committed image contains no
      `mov R2,Rn` at an `0xA530` site, so that case is only reachable from a
      fixture, and a refusal nothing reaches is a refusal nothing tests.
    """
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    for helper in HELPERS:
        if helper["shape"] != "args_in_routine":
            continue
        try:
            base, count = routine_table(d, helper["region"], helper["target"])
        except Undecodable as e:
            check(False, f"{helper['name']}: {e}")
            continue
        check(base == helper["base"] and count == helper["count"],
              f"{helper['name']} re-derives base 0x{base:04X} and count "
              f"{count} from the image (HELPERS records 0x"
              f"{helper['base']:04X} and {helper['count']})")

    rows, undecodable = collect(d)
    check(not undecodable,
          "every committed call site of a known helper decodes"
          + ("" if not undecodable else " -- refused: "
             + "; ".join(f"{h} {c}: {why}" for h, c, why in undecodable)))
    check(bool(rows) and all(len(r["value"]) == 4 for r in rows),
          f"every one of the {len(rows)} records carries a decoded value")

    # A literal `90 hi lo 7A nn` pair in front of an `lcall`, on a buffer of
    # its own, so the decode is shown to depend on the bytes and not on the
    # call site happening to sit at a bank boundary in the real image.
    fixture = bytearray(b"\x00" * 64)
    fixture[40:48] = bytes((MOV_DPTR, 0x84, 0x53, MOV_R2_IMM, 0x02,
                            LCALL, 0xA5, 0x30))
    try:
        got = decode_call_site(bytes(fixture), 45)
        check(got == (0x8453, 2),
              f"a literal argument pair decodes to (0x8453, 2), big-endian "
              f"with the count last (got (0x{got[0]:04X}, {got[1]}))")
    except Undecodable as e:
        check(False, f"a literal argument pair decodes: {e}")

    # Three refusals, each on bytes the fixture supplies, and each checked
    # against a fragment of the message rather than merely against an
    # exception: a decoder that raised for the wrong reason would satisfy a
    # bare `assertRaises`.
    for name, mutate, fragment in (
            ("no `lcall` at the offset",
             lambda b: b.__setitem__(45, MOV_DPTR), "no `lcall`"),
            ("a `mov DPTR` that is not immediately before it",
             lambda b: b.__setitem__(slice(40, 43), b"\x00\x00\x00"),
             "not `mov DPTR,#imm16`"),
            ("an R2 set from a register rather than an immediate",
             lambda b: b.__setitem__(43, 0x8A), "not `mov R2,#imm8`")):
        scratch = bytearray(fixture)
        mutate(scratch)
        try:
            decode_call_site(bytes(scratch), 45)
            check(False, f"{name} is refused (it decoded)")
        except Undecodable as e:
            check(fragment in str(e),
                  f"{name} is refused, naming the shape (got {str(e)!r})")

    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def print_summary(rows, bad) -> None:
    """The per-helper census, then the population the two of them make.

    The record count and the distinct-destination count are both printed and
    they are different claims: records over fewer destinations says a
    destination is named more than once, which is the part of the page's own
    numbers that is a finding rather than a restatement. The multi-named
    destinations are named, because a byte seeded four different ways is the
    sharpest thing this class reaches.
    """
    if bad:
        for name, site, why in bad:
            print(f"  refused  {name} {site}: {why}")
        print()
    by_helper = {}
    for row in rows:
        by_helper.setdefault(row["helper"], []).append(row)
    for name in sorted(by_helper):
        group = by_helper[name]
        print(f"{name}: {len(group)} records over "
              f"{len({r['xdata'] for r in group})} distinct destinations, "
              f"{len({r['value'] for r in group})} distinct stored values")
    if not rows:
        print("no records: no call site of a known helper decoded. That is "
              "not a clean sweep -- read the refusals above.")
        return
    dests = {r["xdata"] for r in rows}
    lo = min(int(d, 16) for d in dests)
    hi = max(int(d, 16) for d in dests)
    print(f"\n{len(rows)} records over {len(dests)} distinct destinations, "
          f"spanning 0x{lo:04X}-0x{hi:04X}.")
    tally = {}
    for row in rows:
        tally.setdefault(row["xdata"], []).append(row["value"])
    multi = {d: v for d, v in tally.items() if len(v) > 1}
    if multi:
        print(f"{len(multi)} destination(s) named by more than one record: "
              + ", ".join(f"{d} ({len(v)}: {', '.join(sorted(v))})"
                          for d, v in sorted(multi.items())))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("--csv", action="store_true",
                    help="write the records as CSV on stdout instead of the "
                         "census")
    ap.add_argument("--page", metavar="LO-HI",
                    help="with --csv, keep only the records whose destination "
                         "falls in this range (e.g. 0x0400-0x045F)")
    ap.add_argument("--check", nargs="?", const=RECORDS_CSV, metavar="PATH",
                    help="diff this run against the committed table and exit "
                         "non-zero on any difference (default: "
                         f"{os.path.relpath(RECORDS_CSV)})")
    ap.add_argument("--self-test", dest="self_test", action="store_true",
                    help="check the decoder's own invariants and its "
                         "hand-built fixtures, then exit")
    args = ap.parse_args()

    try:
        page = parse_page(args.page) if args.page else None
    except ValueError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if page is not None and args.check is not None:
        # A filtered table diffed against the unfiltered committed file would
        # report every filtered row as a deletion, which is a difference that
        # says nothing about the two runs. `walk_budget_census.py` refuses a
        # `--check` at a budget the file does not record for the same reason.
        print("note: --page filters what --csv writes and cannot be combined "
              "with --check, which reproduces the whole table", file=sys.stderr)
        return 1

    d = open(args.firmware, "rb").read()
    if args.self_test:
        return self_test(d)

    try:
        rows, bad = collect(d)
    except (OSError, ValueError) as e:
        print(f"note: {e}", file=sys.stderr)
        return 1

    if bad:
        for name, site, why in bad:
            print(f"note: {name} {site}: {why}", file=sys.stderr)
        print(f"note: {len(bad)} table(s) this tool will not decode were not "
              f"skipped silently: a site it drops is indistinguishable from a "
              f"call the firmware does not have", file=sys.stderr)
        return 1

    if args.check is not None:
        return check_table(render(rows), args.check)
    if args.csv:
        sys.stdout.write(render(rows, page))
        return 0
    print_summary(rows, bad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
