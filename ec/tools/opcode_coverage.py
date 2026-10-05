#!/usr/bin/env python3
"""How much of `disasm8051.OPCODE_LEN` the firmware exercises, and what
three routes that are *not* all independent say about every row of it.

`OPCODE_LEN` is the trust anchor under a pile of annotations:
`trace_xdata_refs.py` imports it, and `ec/annotations/ec-0x07d0-sites.md`
derives its classification, its helper-entry-point table and its `--converge`
framing evidence from the framing it produces. What pins it today is
`disasm8051.py --self-test`, and that pins **20 opcodes** -- two windows
transcribed from `r2` by hand, four branch sites, eleven bit-form sites and
the `0xC1`/`0xC2` pair from the manual. The other 236 rows were verified by
reading them one at a time, by whoever wrote them. This tool turns the gap
between "the table is 256 entries" and "the table is pinned" into numbers.

Two third-party oracles, and a third that is not third-party at all. They are
not the same measurement, and -- the point this tool was asked to make
measurable -- **the first two are not independent of each other**:

- **The committed Ghidra listings** (`--coverage`, `--divergence`) give a
  length for every instruction *start* Ghidra found: 45,661 rows across
  `common`, `bank0`, `bank1` and `pd`. Third-party, reproducible from
  committed files with nothing installed, and never having seen
  `disasm8051.py`. What it cannot see is an opcode that never appears at an
  instruction start -- 0xA5 and 0xC1 here, so it pins 254 of 256 rows.
  *(Corrected 2026-10-02, issue #775: this read 45,643, which is 18 instructions
  short of what the committed listings now hold, the growth of listings seeded
  since. The count is `parse_listing()`'s rows over the committed `.asm`
  files, and `listing_rows()` exists because a parser that quietly reads a
  third of a file reports no disagreement and looks like a pass --
  `verify_reassembly.parse_listing()` is a second implementation of the same
  rule, and `test_verify_gap_text.py` holds the two to identical addresses,
  bytes and order on every listing. `--coverage --summary` prints the figure
  for the tree as it is now; a seeded listing moves it, so read it there.)*
- **`r2 -a 8051`** (`--r2-diff`) linearly walks each whole 64 KiB program from
  its first byte, so it reaches opcodes the listings never place, and covers
  256 of 256 across the three images. It is the same disassembler the hand
  transcriptions came from, which is a reason to treat agreement as weak
  evidence rather than strong, and a reason the listings are the primary
  oracle and this the second one. It reaches more rows and is still the
  weaker of the two: coverage and evidence weight are different questions and
  this tool reports them separately rather than calling one "stronger".
- **The MCS-51 manual, transcribed into `MCS51_LEN`** (`--divergence`,
  `--coverage`'s `man` column) is the third route, and the only one that is not
  a decoder at all. It is what makes the other two's independence testable
  rather than assumed -- **on the rows where it is itself independent.** It was
  not, on `0xA8`-`0xAF`: the transcription had `2` across that block, copied
  from the `0x78` row, where the instruction set has `XCH A,Rn` at 1 -- the
  same instruction the table carries at 1 in the `0xC8` row, and the same two
  bytes `disasm8051.py` prints for `0x78` and `0xA8` alike. So the third oracle
  agreed with the two it exists to contradict, and `--divergence` now reports
  those eight rows rather than a zero. `SPOT_CHECKS` in the suite carries the
  block, which is what a 256-byte literal read by eye needs.

**Why the third one, given the repository already knows the two decoders share
a lineage.** Ghidra's SLEIGH, r2 and `sdas8051` all put `ORL C,/bit` at `0xA0`
and `ANL C,/bit` at `0xB0` where the manual has them the other way round
(`docs/findings.md`'s `0xA0`/`0xB0` entry). Three tools agreeing is why
`disasm8051.py` follows them, and none of them arbitrating the other two is why
that is a comment and not a correction. So "the two oracles agree" is one
decoder counted twice wherever the two share a departure from the manual, and
this tool's job is to say *which rows those are* rather than to report an
agreement count that cannot tell the difference. The manual is the route that
can say it, and at `0xA0`/`0xB0` it turns out to be blind in its own way --
both readings are 2 bytes -- which is a finding about length oracles in general,
and one this repository already leaves where `disasm8051.py:177-188` puts it.

The manual comparison therefore reports disagreement **per oracle**, and a row
the manual assigns nothing is a third state, not a green one: `None`, spelled
`man -` in the coverage table. On the committed tree the table and the manual
agree on all 255 rows the manual assigns, and the one row the manual leaves
unassigned (`0xA5`) is exactly a row the two decoders' agreement is not
evidence about.

Lengths only, and deliberately. r2 and `disasm8051` do not always agree on
which *instruction* a byte is -- r2 reads 0xC1 as `ajmp` and `disasm8051` as
`clr bit` -- but both call it 2 bytes, and framing rests on the length. A text
comparison over the same walks gives 2,214 first-token disagreements: 9 of them
the 0xC1 row, and 2,205 the 35 opcode values `disasm8051.mnemonic()` rendered
as `db 0x..` although `OPCODE_LEN` sized them correctly -- 34 of those 35 the
manual assigns, and `0xA5` the one it does not. That gap was measured
in `docs/findings/opcode-table-coverage.md` and was not this tool's to fix;
recording it here because a reader of this docstring is exactly the person who
would otherwise assume a text comparison is a near-miss.

*That gap is now closed, and the figures above are what the comparison measured
rather than what the tree holds.* `mnemonic()` names every opcode value the
manual assigns, so a `db` at an instruction start is `0xA5` alone. Nothing here
moved: this tool's output is lengths, and a name is not a length. What did move
is the second half of the sentence above -- `db 0x..` used to be a name, and a
cross-decode against one could only agree vacuously, which is why a reader of
this docstring should not have treated a first-token agreement as a near-miss.
The naming, and the oracle each name was decided from, are in
`docs/findings/mnemonic-db-fallthrough-coverage.md`.

What no measurement here can do is say the table is *correct*. A length is
about framing, and framing is about what Ghidra and r2 believe the bytes mean,
not about what the EC does with them. An opcode the firmware never executes is
outside all three, which is why it is its own column rather than folded into a
percentage. `ec/annotations/registers.yaml` states the same caveat for a
static scan, in the same words: not found by this method.

`OPCODE_LEN` is imported, never copied, so this cannot drift away from the
table it reports on and disagree with itself. `disasm8051.py` grows no mode
for any of this.

Usage:
    python3 opcode_coverage.py --summary
    python3 opcode_coverage.py --divergence
    python3 opcode_coverage.py --coverage
    python3 opcode_coverage.py --r2-diff
    python3 opcode_coverage.py --coverage --csv /tmp/opcodes.csv
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import disasm8051 as D

REPO = os.path.dirname(os.path.dirname(HERE))
FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
DECOMPILED = os.path.join(REPO, "ec", "decompiled")
LISTING_INDEX = os.path.join(DECOMPILED, "listing-index.csv")

# The three programs the listings are cut from, in the order the report prints
# them. `common` is not a fourth program: it is the 0x0000-0x7FFF half of
# bank0, and `make_bank_image.py` puts the same bytes in both images, so it
# reads against bank0's. That is why it is a *key* here and a *column* in
# coverage_rows(): the same listing address in `common` and `bank0` is the
# same byte of the same firmware, and collapsing the two would halve the
# instruction count for no new information.
PROGRAMS = ("common", "bank0", "bank1", "pd")

# The two file offsets disasm8051.py does not already carry, from
# make_bank_image.py's docstring. Kept as literals rather than imported from
# that script so this tool reads the committed firmware with no subprocess --
# the whole report is a static read of committed files, and a helper that
# shells out to another helper to build a bytearray is not that.
BANK1_FILE_OFFSET = 0x10000
PD_FILE_OFFSET = 0x20000
COMMON_SIZE = 0x8000

# The listing's own grammar, from build_ec_decompile.py's output. These two
# regexes are verify_reassembly.parse_listing's, restated rather than shared:
# that module is 2,268 lines with a heavy import graph, and this tool is
# supposed to be readable on its own. The duplication is pinned by
# test_opcode_coverage.py, which runs both parsers over one fixture and fails
# if they ever disagree -- so this is a copy with a test on it, not a copy that
# is free to drift.
LINE_RE = re.compile(r"^([0-9A-Fa-f]{1,8})\s+(\S.*)$")
ADDRESS_LINE = re.compile(r"^[0-9A-Fa-f]{4,8}\s+\S")
BYTE_SLOT = re.compile(r"^(?:[0-9A-Fa-f]{2}|-)$")

# The four tables `--self-test` checks, in the order self_test() checks them,
# and the column header each one's coverage is reported under. The self-test
# corpus is *derived* from these four rather than transcribed, so that adding a
# site to one of them moves this report with no second edit to remember.
SELF_TEST_TABLES = (
    ("SELF_TEST", "self-test windows"),
    ("REL_SITES", "branch sites"),
    ("BIT_SITES", "bit-form sites"),
    ("TEXTBOOK_BIT_SITES", "manual pair"),
)

# --- the third oracle: the MCS-51 manual, transcribed -----------------------

# Instruction length for every opcode value, from the MCS-51 instruction set
# rather than from any decoder, laid out like disasm8051.OPCODE_LEN above it:
# rows of 16, opcode 0x00 first. **0 means the manual assigns no instruction
# to this value** -- not "length zero", which no 8051 instruction has, and not
# a disagreement. One value is 0: 0xA5.
#
# This is the oracle that makes the other two's independence testable. Ghidra
# and r2 are not two independent readings of the opcode map: they share a
# lineage, and where that lineage departs from the manual their agreement is
# one decoder counted twice. docs/findings.md records that departure at
# 0xA0/0xB0, and the paragraph below says why this table cannot see it.
#
# An earlier transcription of this table also left 0x96 and 0x97 at 0, on the
# reading that the manual's `X a,@Ri` family stops after 0x26/0x46/0x56/0x66.
# It does not stop there: the 0x90-0x9F row carries all eight `SUBB A` forms,
# `0x94` `SUBB A,#data` (2), `0x95` `SUBB A,direct` (2), `0x96` `SUBB A,@R0`
# (1), `0x97` `SUBB A,@R1` (1) and `0x98`-0x9F `SUBB A,Rn` (1), which is the
# same +0x20 step the map already makes at 0x36/0x37 and every other row. On
# the corrected table the manual, Ghidra and r2 agree at both, and 0xA5 is the
# one row left on which a decoder's agreement is not evidence.
#
# Transcribed here rather than imported because there is nothing to import it
# from, and transcribed with the 0xA0/0xB0 row deliberately *not* resolved:
# the manual's `ANL C,/bit` at 0xA0 and `ORL C,/bit` at 0xB0 is a different
# length nowhere, both readings are 2 bytes, so the length comparison below
# is blind to that row by construction. That blindness is the point -- it is
# why this table cannot close the 0xA0/0xB0 question, only leave it where
# `disasm8051.py:177-188` already leaves it.
#
# `test_opcode_coverage.py` pins a set of rows against this transcription
# independently, because a 256-byte literal copied wrong is a length oracle
# that is wrong on the very rows it exists to check.
MCS51_LEN = (
    b"\x01\x02\x03\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x03\x02\x03\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x03\x02\x01\x01\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x03\x02\x01\x01\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x03\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x03\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x03\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x01\x02\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02"
    b"\x02\x02\x02\x01\x01\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02"
    b"\x03\x02\x02\x01\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x01\x01\x00\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x01\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03"
    b"\x02\x02\x02\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x02\x02\x02\x01\x01\x03\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02"
    b"\x01\x02\x01\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
    b"\x01\x02\x01\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
)

# The value MCS51_LEN leaves 0, and therefore the one row on which no
# decoder's agreement with `OPCODE_LEN` is evidence: the manual says nothing,
# so there is nothing for a decoder to corroborate.
MANUAL_UNASSIGNED = tuple(op for op in range(256) if MCS51_LEN[op] == 0)


def manual_divergences(opcode_len=None):
    """The rows the MCS-51 manual assigns and `opcode_len` disagrees with.

    -> [(opcode, table length, manual length)], ordered by opcode. Per row, not
    per instruction start, because this oracle has no corpus: it is a
    transcription of a table, not a walk over bytes, so there is no address to
    report and none should be invented.

    The rows the manual leaves unassigned are **not** in this list and are not
    an agreement either -- `manual_divergences()` reports what the manual
    contradicts, and `MANUAL_UNASSIGNED` reports what it cannot speak to. The
    two are the halves of the finding and folding the second into the first
    would turn "the manual says nothing here" into "the manual confirms this
    is right", which is the overclaim this oracle was added to prevent.
    """
    lens = D.OPCODE_LEN if opcode_len is None else opcode_len
    return [(op, lens[op], MCS51_LEN[op]) for op in range(256)
            if MCS51_LEN[op] and lens[op] != MCS51_LEN[op]]


class CoverageError(Exception):
    """Something the report cannot be computed from, as opposed to found.

    These are the conditions where reporting a number would be worse than
    failing: no listings at all, a listing file the index names and the tree
    does not have, a row whose bytes are not the image's. Each of them is a
    case where a naive implementation returns a confident-looking zero.
    `disasm8051_oracle._fenced()` is the precedent -- it raises on a file with
    no fence rather than parsing it as an empty listing, because an empty
    parse and a right answer have to be told apart before either is compared
    against anything."""


def parse_listing(path):
    """-> [(addr, bytes)], in file order, for the instruction rows of one .asm.

    The byte column is three fixed-width slots of two hex digits each, `-` for
    the slots an instruction does not fill, then the mnemonic. The padding is
    what makes the column parseable: the 8051's reserved `da` is a mnemonic
    that is also two hex digits, so a run of hex pairs would be ambiguous
    exactly where the table is most delicate.

    Rows with no bytes at all are skipped rather than yielded with an empty
    body. `verify_reassembly.parse_listing` skips them too (it `continue`s on
    an empty tail), and the byte column being empty is not something a length
    can be read out of.
    """
    out = []
    with open(path, errors="replace") as fh:
        for line in fh:
            if line.startswith(";") or not line.strip():
                continue
            m = LINE_RE.match(line.rstrip("\n"))
            if not m:
                continue
            addr, rest = m.groups()
            slots = rest.split()
            take = 0
            for i, tok in enumerate(slots):
                if tok == "-" or not BYTE_SLOT.match(tok):
                    take = i
                    break
                take = i + 1
            hexbytes = "".join(slots[:take])
            if not hexbytes:
                continue
            out.append((int(addr, 16), bytes.fromhex(hexbytes)))
    return out


def listing_rows(path):
    """parse_listing, plus a check that it read every address line there is.

    A parser that quietly reads a third of a file reports no disagreement and
    looks like a pass -- that is not hypothetical, it is what
    verify_reassembly.check_listing_bytes() guards against after the byte
    column changed shape. Here the number is the report, so a parse that
    misses rows would understate coverage rather than merely fail to check it.
    """
    rows = parse_listing(path)
    with open(path, errors="replace") as fh:
        text = fh.read()
    address_lines = sum(1 for line in text.splitlines() if ADDRESS_LINE.match(line))
    empty = address_lines - len(rows)
    if empty:
        # Not fatal on its own: a listing with an address line and no bytes is
        # a form this parser does not model, and the count is reported so the
        # reader can see how much of the corpus it is rather than being
        # quietly dropped.
        return rows, empty
    return rows, 0


def program_images(fw_path=FIRMWARE):
    """{program: 64 KiB image}, stitched in memory as make_bank_image.py does.

    In memory rather than through that script so the coverage modes are a
    static read of committed files with no subprocess, no temp directory and
    no image left behind. `disasm8051.self_test()` stitches bank0 the same way.
    """
    with open(fw_path, "rb") as fh:
        d = fh.read()
    common = d[:COMMON_SIZE]
    bank0 = common + d[D.BANK0_FILE_OFFSET:D.BANK0_FILE_OFFSET + COMMON_SIZE]
    bank1 = common + d[BANK1_FILE_OFFSET:BANK1_FILE_OFFSET + COMMON_SIZE]
    pd = d[PD_FILE_OFFSET:PD_FILE_OFFSET + 0x10000]
    if len(pd) != 0x10000:
        raise CoverageError(
            "the ITE8850-PD image at file 0x%05X is short (%d of %d bytes)"
            % (PD_FILE_OFFSET, len(pd), 0x10000))
    return {"common": bank0, "bank0": bank0, "bank1": bank1, "pd": pd}


def read_listings(index=LISTING_INDEX, decompiled=DECOMPILED, images=None):
    """The committed listing corpus -> ([(program, addr, bytes)], stats).

    Driven by `listing-index.csv` rather than by globbing `*.asm`, because the
    index is the committed inventory of which listings the project is supposed
    to have: a listing on disk that the index does not name is a listing no
    other check counts, and one the index names that is not on disk is a hole
    a glob would step straight over.

    Index rows whose `out_file` is `(no-instructions)` name no file and are
    counted as empty, not as missing. That is three rows on the committed tree
    and they are regions the project decided hold no instructions, which is a
    finding about the firmware rather than a broken pointer.

    `images` is a parameter so the test suite can drive the whole read against
    a hand-built fixture and never open the firmware.
    """
    if not os.path.isfile(index):
        raise CoverageError("no listing index at %s" % index)
    if images is None:
        images = program_images()
    rows = []
    stats = {"listings": 0, "empty": 0, "missing": [], "unparsed": 0}
    with open(index, newline="") as fh:
        index_rows = list(csv.DictReader(fh))
    for row in index_rows:
        rel = row["out_file"]
        prog = row["program"]
        if not rel:
            continue
        if rel.startswith("("):
            stats["empty"] += 1
            continue
        path = os.path.join(decompiled, rel)
        if not os.path.isfile(path):
            stats["missing"].append((prog, row["addr"], rel))
            continue
        stats["listings"] += 1
        parsed, unparsed = listing_rows(path)
        stats["unparsed"] += unparsed
        image = images[prog]
        for addr, raw in parsed:
            # A row whose bytes are not the image's is a disagreement with the
            # firmware, not a length to be counted. Reporting it as coverage
            # would let a stale export inflate a number about the firmware, so
            # it is held back and the caller is told about it instead.
            if image[addr:addr + len(raw)] != raw:
                stats["missing"].append(
                    (prog, "%04X" % addr,
                     "listing says %s, image has %s"
                     % (raw.hex(), image[addr:addr + len(raw)].hex())))
                continue
            rows.append((prog, addr, raw))
    if stats["missing"]:
        raise CoverageError(
            "%d listing row(s) the index names are not usable: %s%s"
            % (len(stats["missing"]),
               "; ".join("%s %s %s" % m for m in stats["missing"][:5]),
               " (and %d more)" % (len(stats["missing"]) - 5)
               if len(stats["missing"]) > 5 else ""))
    if not stats["listings"]:
        # The `_fenced()` case. An empty corpus must not become an empty
        # report that reads as "no disagreements": zero divergences from zero
        # listings is a sentence about nothing.
        raise CoverageError("no listings found under %s" % decompiled)
    if not rows:
        raise CoverageError("%d listing(s) read, 0 instruction rows in them"
                            % stats["listings"])
    return rows, stats


def coverage_rows(rows, opcode_len=None, corpus=None):
    """One row per opcode value: what the table says, what the listings say,
    and which of the four self-test tables reach it.

    `opcode_len` defaults to the real `D.OPCODE_LEN` and exists so a test can
    pass a deliberately wrong table and see the disagreement. It is a
    parameter rather than a module global precisely so the test cannot mutate
    the real one and leave it wrong. `corpus` is the same deal for
    self_test_corpus(), which would otherwise read the firmware to answer a
    question the caller may already have the answer to.
    """
    lens = D.OPCODE_LEN if opcode_len is None else opcode_len
    starts = {op: 0 for op in range(256)}
    where = {op: set() for op in range(256)}
    # A set, not a single value: the listings could in principle give one
    # opcode two different lengths at two addresses, and that is a finding
    # rather than a bookkeeping problem. Collapsing it to the last one seen
    # would hide it behind whichever row happened to be read last.
    listed = {op: set() for op in range(256)}
    for prog, _addr, raw in rows:
        op = raw[0]
        starts[op] += 1
        where[op].add(prog)
        listed[op].add(len(raw))
    corpus = self_test_corpus() if corpus is None else corpus
    out = []
    for op in range(256):
        tables = [name for name, _label in SELF_TEST_TABLES if op in corpus[name]]
        lens_here = listed[op]
        out.append({
            "opcode": op,
            "hex": "0x%02x" % op,
            "opcode_len": lens[op],
            "listing_len": lens[op] if len(lens_here) == 1 else None,
            "listing_starts": starts[op],
            "programs": ",".join(p for p in PROGRAMS if p in where[op]),
            # None where the listings have nothing to say, False where they
            # contradict the table, True where they back it. The three states
            # have to stay distinct: "not found by this method" and "found and
            # wrong" are the two halves of the finding, and a report that
            # folded the first into the second would be overclaiming.
            "agrees": None if not lens_here else lens[op] in lens_here,
            # The manual, reported beside the listing length rather than
            # folded into `agrees`. It is a third state and it has to stay
            # visible: `None` here means the MCS-51 map assigns no instruction
            # to this value at all, which is not the listings' `n/a` (nothing
            # to compare against) and emphatically not a `yes`. A reader of
            # the `man` column seeing `-` learns that the row below it is
            # uncorroborated by anything, which is the fact that was missing
            # when this table had no such column.
            "manual_len": MCS51_LEN[op] or None,
            "manual_agrees": (None if not MCS51_LEN[op]
                              else lens[op] == MCS51_LEN[op]),
            "selftest": ",".join(tables),
        })
    return out


def self_test_corpus(image=None):
    """{table name: {opcode, ...}} for the four tables --self-test checks.

    Derived, not transcribed, and that is the whole point: the coverage
    column has to move when those tables do or it is a second hand-kept copy
    of a first. `SELF_TEST`'s rows are decoded rather than read, because
    SELF_TEST holds `(address, text)` and the opcode is the first byte of what
    the decoder produces at that address -- which also means the corpus is
    stated by the *current* table's framing, so a wrong length changes the
    self-test column and says so.
    """
    img = program_images()["bank0"] if image is None else image
    out = {name: set() for name, _ in SELF_TEST_TABLES}
    for start, expected in D.SELF_TEST:
        for _i, raw, _t in D.decode(img, start, len(expected), start):
            out["SELF_TEST"].add(raw[0])
    for _foff, _rt, raw, _want in D.REL_SITES:
        out["REL_SITES"].add(raw[0])
    for _foff, _rt, raw, _want in D.BIT_SITES:
        out["BIT_SITES"].add(raw[0])
    for raw, _want, _what in D.TEXTBOOK_BIT_SITES:
        out["TEXTBOOK_BIT_SITES"].add(raw[0])
    return out


def divergences(rows, opcode_len=None):
    """The listing rows whose length `opcode_len` disagrees with. -> [...].

    One entry per *row*, not per opcode, because a wrong length is a wrong
    length at each address it is reached from and a reader chasing one wants
    the address. Per-opcode counts are in coverage_rows()'s `listing_starts`.
    """
    lens = D.OPCODE_LEN if opcode_len is None else opcode_len
    return [(prog, addr, raw[0], lens[raw[0]], len(raw), raw)
            for prog, addr, raw in rows if lens[raw[0]] != len(raw)]


# --- the r2 second opinion -------------------------------------------------

# The three flat images, and how to build each from the committed firmware.
# `make_bank_image.py --pd` takes `--pd` first and the bank forms take the
# firmware first; both spellings are in its docstring and both are load-bearing
# to get wrong, so they are written out per-image rather than shared.
R2_IMAGES = (
    ("bank0", ("0", "0x08000"), "common 0x0000-0x7FFF + bank 0"),
    ("bank1", ("0", "0x10000"), "common 0x0000-0x7FFF + bank 1"),
    ("pd", None, "the ITE8850-PD image, its own 64 KiB address space"),
)


def r2_walk(image_path, base=0, span=0x10000, r2="r2"):
    """-> [(addr, opcode, r2's size, raw)] from one linear `r2` walk.

    `pDj`, not `pD`: it is the same linear disassembly with the same framing
    and a machine-readable body, and on the committed bank0 image it is 0.24s
    against 29.8s -- the difference is that the JSON form does not spend the
    time drawing the flow arrows `pD` renders as box-drawing characters, which
    would also have to be stripped out of the text form's columns.

    `pDj` takes a *byte* count, not an instruction count, and walks linearly
    from the seek: it does not follow branches, which is what makes it
    comparable to `disasm8051.decode()`. Walking over data is expected and is
    the point -- a length disagreement is visible at any offset, and an opcode
    Ghidra never placed at an instruction start is placed here by chance.
    """
    r = subprocess.run(
        [r2, "-a", "8051", "-e", "scr.color=0", "-q",
         "-c", "s %d; pDj %d" % (base, span), image_path],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise CoverageError("r2 exited %d on %s: %s"
                            % (r.returncode, os.path.basename(image_path),
                               r.stderr.strip()[:200]))
    try:
        rows = json.loads(r.stdout)
    except ValueError:
        # Deliberately not a zero. A mode that cannot read its oracle must
        # say it did not run; `agent-gates.sh`'s own header warns about a
        # check that degrades to a passing shape on a runner missing a tool.
        raise CoverageError("r2's output on %s did not parse as JSON -- this "
                            "mode did not run, and is reporting no number"
                            % os.path.basename(image_path))
    if not isinstance(rows, list) or not rows:
        raise CoverageError("r2 returned no instruction rows for %s -- this "
                            "mode did not run, and is reporting no number"
                            % os.path.basename(image_path))
    out = []
    for row in rows:
        raw = bytes.fromhex(row["bytes"])
        if not raw:
            continue
        out.append((row["offset"], raw[0], row["size"], raw))
    return out


def walk_against(stream, lens):
    """Walk r2's stream from its first address against `lens`.

    -> (walked, hits, stopped_at). The walk advances by *our own* length while
    the two agree and re-anchors onto r2's framing at a disagreement, so what
    comes out is a count of divergence events rather than of one walk that
    lost its place and then disagreed about everything after it.
    `stopped_at` is the address the walk gave up at, or None if it ran the
    stream out -- and a walk that stops *without* a divergence to explain it
    is the one outcome this design can produce and not account for, so the
    caller reports it rather than counting the shorter walk as agreement.

    Split out from r2_diff so it is testable without r2, a subprocess or a
    64 KiB image: the arithmetic is the part that can be wrong.
    """
    addr, i, hits = 0, 0, []
    while i < len(stream) and stream[i][0] == addr:
        got, op, size, raw = stream[i]
        if lens[op] != size:
            hits.append((got, op, lens[op], size, raw))
            addr = got + size              # re-anchor on r2's own framing
        else:
            addr = got + lens[op]
        i += 1
    return i, hits, (stream[i][0] if i < len(stream) else None)


def r2_diff(r2="r2", firmware=FIRMWARE, work=None, opcode_len=None):
    """Walk each image with r2 and against `opcode_len`, event by event.

    Returns (per-image rows, total events, desyncs).
    """
    if not shutil.which(r2):
        raise CoverageError(
            "`%s` is not on PATH, so this mode did not run. It is not "
            "reporting a zero: the coverage and divergence modes above are "
            "static reads of committed files and need no r2." % r2)
    lens = D.OPCODE_LEN if opcode_len is None else opcode_len
    import tempfile
    tmp = work or tempfile.mkdtemp(prefix="opcode-coverage-")
    maker = os.path.join(HERE, "make_bank_image.py")
    per_image, events, desyncs, reached = [], 0, [], set()
    for name, args, what in R2_IMAGES:
        path = os.path.join(tmp, name + ".bin")
        cmd = ([sys.executable, maker, "--pd", firmware, path] if args is None
               else [sys.executable, maker, firmware] + list(args) + [path])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        stream = r2_walk(path, r2=r2)
        walked, hits, stopped = walk_against(stream, lens)
        if stopped is not None:
            desyncs.append((name, stopped, walked, len(stream)))
        # What the walk reached, as well as what it agreed about. A linear
        # walk over a whole image steps on opcodes the listings never place, so
        # this is the number that says which rows of the table have a second
        # opinion behind them -- and the two routes cover different ground: the
        # listings reach 254 opcode values, this reaches all 256.
        seen = {op for _a, op, _s, _r in stream}
        reached |= seen
        per_image.append((name, what, len(stream), walked, hits, seen))
        events += len(hits)
    return per_image, events, desyncs, reached


# --- reporting -------------------------------------------------------------

CSV_HEADER = ("opcode", "hex", "opcode_len", "listing_len", "listing_starts",
              "programs", "agrees", "manual_len", "manual_agrees", "selftest")


def _print_coverage(rows, stream=sys.stdout):
    # The last column is not padded: it is the only one whose width is not
    # fixed, and padding it would put trailing whitespace on 255 of the 256
    # lines of a table that gets pasted into a document and diffed. `man` is
    # the MCS-51 manual's length, `-` where the manual assigns no instruction,
    # which is the third state and the reason the column exists.
    print("%-6s %-4s %-5s %-4s %-6s %-6s %-9s %s"
          % ("opcode", "len", "list?", "man", "starts", "agree", "programs",
             "self-test tables"))
    for r in rows:
        if r["agrees"] is None:
            agree = "n/a"
        else:
            agree = "yes" if r["agrees"] else "NO"
        print("%-6s %-4d %-5s %-4s %-6d %-6s %-9s %s"
              % (r["hex"], r["opcode_len"],
                 r["listing_len"] if r["listing_len"] is not None else "-",
                 r["manual_len"] if r["manual_len"] is not None else "-",
                 r["listing_starts"], agree,
                 r["programs"] or "-", r["selftest"] or "-"), file=stream)


def print_summary(rows, stats, corpus):
    seen = [r for r in rows if r["listing_starts"]]
    absent = [r for r in rows if not r["listing_starts"]]
    div = divergences_from_coverage(rows)
    mdiv = manual_divergences()
    tested = [r for r in rows if r["selftest"]]
    starts = sum(r["listing_starts"] for r in rows)
    print("opcode table coverage, from the committed Ghidra listings")
    print()
    print("  listings read                   %d  (%d index rows name no file: "
          "a region with no instructions)" % (stats["listings"], stats["empty"]))
    print("  instruction starts              %d" % starts)
    print("  opcodes at an instruction start %d of 256" % len(seen))
    print("  opcodes the self-test corpus reaches %d of 256, of which %d also "
          "appear at an instruction start"
          % (len(tested), len([r for r in tested if r["listing_starts"]])))
    print("  length disagreements            %d" % len(div))
    print("  not found by this method        %d  (%s)"
          % (len(absent), ", ".join(r["hex"] for r in absent) or "none"))
    print()
    print("  against the MCS-51 manual, which is a third route and not a")
    print("  decoder: %d row(s) assigned and disagreed with, of %d assigned"
          % (len(mdiv), 256 - len(MANUAL_UNASSIGNED)))
    print("  the manual assigns nothing to   %d  (%s)  -- on these rows no "
          "decoder's agreement is evidence"
          % (len(MANUAL_UNASSIGNED),
             ", ".join("0x%02x" % op for op in MANUAL_UNASSIGNED)))
    if stats["unparsed"]:
        print("  listing rows not parsed         %d  -- these are NOT in the "
              "counts above" % stats["unparsed"])
    print()
    print("  'not found by this method' is a statement about these listings and")
    print("  the regions Ghidra decoded. It is not 'absent from the firmware',")
    print("  and an opcode the firmware never executes is outside this")
    print("  measurement entirely -- which is why it is a column and not a")
    print("  percentage. `r2 -a 8051`'s linear walk over all three images is a")
    print("  second route to the same rows and reaches both: --r2-diff.")
    print()
    print("  Ghidra and r2 are not independent decoders -- they share a map")
    print("  this repository already knows disagrees with the manual at")
    print("  0xA0/0xB0 -- so 0 disagreements against both is not 0 against")
    print("  two. The 'man' column of --coverage is the third oracle, and the")
    print("  rows it leaves at '-' are the rows nothing corroborates.")


def divergences_from_coverage(rows):
    """The coverage rows where the listings and the table disagree. -> [...]

    Derived from coverage_rows() rather than from a second walk over the raw
    rows, so `--divergence` and `--summary` cannot print different counts for
    the same tree. The test is on the tri-state `agrees` flag, not on a number:
    `None` (nothing to compare against) must not be counted as a disagreement
    or as an agreement.
    """
    return [r for r in rows if r["agrees"] is False]


def shared_map_rows(rows):
    """The rows no oracle can corroborate: the manual assigns nothing there.

    -> [{opcode, listing_starts, ...}], ordered by opcode. The listing-start
    count is what makes the row a *finding* rather than a footnote: it says how
    many instructions in the committed corpus are framed by a length that only
    the two decoders that share a lineage have an opinion about.

    This is the failure the tool exists to be able to see, so it is computed
    rather than asserted. A row here does not mean the length is wrong --
    0xA5 is the only row it can return on the committed tree, and it is
    already recorded as unresolved. It means the 0-disagreements figure is
    silent about it. 0xC1, the other row this repository records as
    unresolved, is not here: the manual does assign it a length (`CLR bit`,
    2 bytes) and it matches.
    """
    return [{"opcode": r["opcode"],
             "hex": r["hex"],
             "listing_starts": r["listing_starts"],
             "programs": r["programs"] or "-"}
            for r in rows if r["manual_agrees"] is None]


def write_csv(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER)
        for r in rows:
            w.writerow([r["opcode"], r["hex"], r["opcode_len"],
                        r["listing_len"] if r["listing_len"] else "",
                        r["listing_starts"], r["programs"],
                        "" if r["agrees"] is None else r["agrees"],
                        "" if r["manual_len"] is None else r["manual_len"],
                        "" if r["manual_agrees"] is None else r["manual_agrees"],
                        r["selftest"]])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--coverage", action="store_true",
                    help="one row per opcode: the table, the listings, and the "
                         "self-test corpus (the default)")
    ap.add_argument("--divergence", action="store_true",
                    help="only the rows where the two lengths disagree")
    ap.add_argument("--summary", action="store_true",
                    help="the headline figures alone")
    ap.add_argument("--r2-diff", action="store_true",
                    help="second opinion from `r2 -a 8051`, one linear walk per image")
    ap.add_argument("--r2", default="r2", metavar="PATH",
                    help="the r2 to use for --r2-diff (default: r2 on PATH)")
    ap.add_argument("--csv", metavar="PATH", help="write the 256-row table here")
    args = ap.parse_args(argv)

    try:
        if args.r2_diff:
            per_image, events, desyncs, reached = r2_diff(r2=args.r2)
            for name, what, total, walked, hits, seen in per_image:
                print("  %-6s %5d instruction(s) walked of %5d, %3d opcode "
                      "value(s) reached  (%s)"
                      % (name, walked, total, len(seen), what))
                for addr, op, ours, theirs, raw in hits:
                    print("  FAIL %s 0x%04X opcode 0x%02X: disasm8051 says %d, "
                          "r2 says %d (%s)" % (name, addr, op, ours, theirs,
                                               raw.hex()))
            for name, addr, walked, total in desyncs:
                print("  FAIL %s: the walk stopped at 0x%04X after %d of %d "
                      "instructions with no divergence recorded -- the two "
                      "framings are not comparable here and this is not a "
                      "green zero" % (name, addr, walked, total))
            print("r2 differential: %d divergence event(s) over %d image(s), "
                  "reaching %d of 256 opcode value(s)%s"
                  % (events, len(per_image), len(reached),
                     " (not reached: %s)"
                     % ", ".join("0x%02x" % o for o in range(256)
                                 if o not in reached) if len(reached) < 256
                     else ""))
            if events or desyncs:
                return 1
            return 0

        # Named rather than defaulted, so a test can point the module
        # globals at a tree that is not there and drive the failure path.
        rows, stats = read_listings(index=LISTING_INDEX,
                                    decompiled=DECOMPILED)
        table = coverage_rows(rows)
        corpus = self_test_corpus()
        if args.csv:
            write_csv(args.csv, table)
            print("wrote %s (%d rows)" % (args.csv, len(table)))
        if args.summary:
            print_summary(table, stats, corpus)
        if args.divergence:
            # A listing row the parser could not read is a row the count below
            # does not cover, and a divergence count over a corpus smaller
            # than the index names is a silent undercount. Reported as a
            # failure rather than folded into the number, which is the whole
            # point of carrying the counter this far.
            if stats["unparsed"]:
                print("  FAIL %d address line(s) in the listings could not be "
                      "parsed, so the count below does not cover them"
                      % stats["unparsed"])
            # Per oracle, and not one combined total. A combined number is what
            # this report was originally written with, and it cannot tell
            # "both decoders agree with the table" from "the two decoders share
            # a map that is wrong here", because both are a row where nothing
            # contradicted anything. Printing the two comparisons separately,
            # plus the rows no oracle can speak to, is the whole fix.
            print("vs the committed Ghidra listings:")
            div = divergences(rows)
            for prog, addr, op, ours, theirs, raw in div[:40]:
                print("  FAIL %s 0x%04X opcode 0x%02X: disasm8051 says %d, the "
                      "committed listing is %d (%s)"
                      % (prog, addr, op, ours, theirs, raw.hex()))
            if len(div) > 40:
                print("  ... and %d more" % (len(div) - 40))
            print("  %d row(s) of %d instruction start(s) in %d listing(s)"
                  % (len(div), len(rows), stats["listings"]))
            print()
            print("vs the MCS-51 manual (transcribed, not a decoder):")
            mdiv = manual_divergences()
            for op, ours, theirs in mdiv:
                print("  FAIL opcode 0x%02X: disasm8051 says %d, the manual "
                      "says %d" % (op, ours, theirs))
            print("  %d row(s) of %d the manual assigns"
                  % (len(mdiv), 256 - len(MANUAL_UNASSIGNED)))
            print()
            shared = shared_map_rows(table)
            print("rows no oracle can corroborate (the manual assigns no "
                  "instruction, so a decoder agreeing here is one decoder's "
                  "map rather than two readings that happen to meet):")
            for r in shared:
                if r["listing_starts"]:
                    # Measured from the listings themselves: this value is
                    # named at an instruction start, so Ghidra has an opinion
                    # about it and the manual does not. `--r2-diff` names it
                    # the same way, which is a shared lineage rather than a
                    # second opinion; the write-up quotes both.
                    print("  %s  %d instruction start(s) in %s -- the committed "
                          "listings name this value and the manual does not "
                          "have it, so its length rests on the decoders' map"
                          % (r["hex"], r["listing_starts"], r["programs"]))
                else:
                    # Not "the decoders agree here" -- nothing places it at
                    # all. 0xA5 is this row: r2 marks it `type: invalid`, the
                    # listings never place it, and the manual has nothing.
                    print("  %s  no listing start and no manual entry either "
                          "-- its length rests on the table alone"
                          % r["hex"])
            print("  %d row(s); 0 disagreements is not 0 against three oracles"
                  % len(shared))
            return 1 if div or mdiv or stats["unparsed"] else 0
        if not args.summary and not args.csv:
            _print_coverage(table)
        return 0
    except CoverageError as e:
        # A message and a non-zero exit, never a number. Every one of these is
        # a case where the honest output is "this did not run".
        print("opcode_coverage: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
