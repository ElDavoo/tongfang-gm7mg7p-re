#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

gpu_block_watch.py imports ecrw, which binds kernel32 at import time and so
only loads on Windows -- windows/tools/ecrw_fake.py stands in for the whole
module, installed by assignment, so this suite is not a party to the
`setdefault` ordering accident docs/findings.md §16 records. The fake also makes
the sweep scriptable byte by byte.

Unlike most of the `windows/tools` suites this one reads committed inputs,
`evidence/acpi/dsdt.dsl`, `ec/annotations/registers.yaml`,
`ec/annotations/ec-07c4-07d5-sites.csv`/`.md` and this procedure's own table
in `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`, resolved relative to this
file. It therefore has to run from inside the repository, which
`tools/run-tests.sh` guarantees (it cds to the repo root), and a suite copied
to a scratch directory outside the tree will fail to find them.

The first two classes are the ones that matter: the tool's watch table is the
citation list docs/hardware-tests/gpu-tgp-07c4-07d7-door.md §7 is graded
against, so it is checked here against the two committed inputs it transcribes
-- the DSDT ECMG field list and ec/annotations/registers.yaml -- rather than
being a hand-typed table nothing holds still. That procedure prints a second
copy of the same table as prose, which is what drifted in #266 while the
tool's copy was held, so the third class checks the doc's copy against the
tool's rather than leaving the two to agree by hand. The fourth grades that
copy's EC-side cross-reference column for the four rows the per-site census
covers, against ec/annotations/ec-07c4-07d5-sites.csv and its `.md`: the doc
was free to credit `0x07C4` with one cross-reference where the walk had found
five, and a re-walk that finds a sixth would move the census the same way
without the doc moving with it. The fifth is the same hold one copy further
out, and the reason it exists at all: `ec/tools/grade_gpu_door.py` grades this
tool's captures and cannot import it -- the `ecrw` import below binds
kernel32 -- so it states its own two window bounds and its own 24 DSDT names.
A grader reading a capture against different bounds than the one that wrote it
would be grading one tool's watch set with another's, and would say so
nowhere. The sixth holds the two sections that tell a human's capture where to
land and what it is allowed to change, for the same reason: a procedure that
is written but not followed is the failure this suite can still catch before
the machine.
"""
import csv
import contextlib
import importlib
import importlib.util
import io
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import yaml

TOOLS = Path(__file__).parent
REPO = TOOLS.parent.parent
DSDT = REPO / "evidence" / "acpi" / "dsdt.dsl"
REGISTERS = REPO / "ec" / "annotations" / "registers.yaml"
SITES = REPO / "ec" / "annotations" / "ec-07c4-07d5-sites.csv"
SITES_MD = REPO / "ec" / "annotations" / "ec-07c4-07d5-sites.md"
DOOR = REPO / "docs" / "hardware-tests" / "gpu-tgp-07c4-07d7-door.md"

# The tool's own `from ec_watch import ...` has to resolve, and the directory
# is the import root whether or not the runner was started from here.
sys.path.insert(0, str(TOOLS))


# The shared offline stand-in for `ecrw` (windows/tools/ecrw_fake.py), installed
# by assignment like the probe and ec_watch suites do, so this suite cannot lose
# -- or win -- a `setdefault` race against them. `Ec` only has to exist as a
# name: every run rebinds the tool's own copy.
import ecrw_fake  # noqa: E402  (needs the sys.path entry above)
ecrw_fake.install()

watch = importlib.import_module('gpu_block_watch')

# The offline grader of this procedure's §3 capture. Loaded by path, and its
# own directory put on sys.path first, because the grader does `import
# grade_0751_isolation` for the CSV vocabulary and the two `ec/tools` files are
# otherwise outside every import root this runner sets. It cannot be imported
# the other way round: this module does `from ecrw import Ec, EcError`, and
# `ecrw` binds kernel32 at import time, so a grader that imported it would load
# only on Windows.
EC_TOOLS = REPO / "ec" / "tools"
sys.path.insert(0, str(EC_TOOLS))
_grader_spec = importlib.util.spec_from_file_location(
    'grade_gpu_door', EC_TOOLS / 'grade_gpu_door.py')
grader = importlib.util.module_from_spec(_grader_spec)
_grader_spec.loader.exec_module(grader)

# The watch set the change rows are keyed against, in the order a sweep reads
# them. Sweep 0 is the baseline the tool takes before its loop; 1 moves a byte
# in the 0x07C4 block and 2 a byte in the 0x0743 block, and the mark is forced
# to land between them -- one change from each window either side of it, which
# is the "both blocks, one capture" shape the procedure's result table reads.
ADDRS = [a for a, *_ in watch.WATCH]
ACPI, HOST = 0x07D0, 0x0745
SWEEPS = [
    dict.fromkeys(ADDRS, 0x00),
    {**dict.fromkeys(ADDRS, 0x00), ACPI: 0x37},
    {**dict.fromkeys(ADDRS, 0x00), ACPI: 0x37, HOST: 0x0A},
]


def parse_ecmg_fields(text):
    """The ECMG field list as {addr: [(name, first_bit, last_bit)]}.

    Translated out of the ASL rather than transcribed: an `Offset (0xNNN)`
    restarts the bit count at that byte, and every following `Name, width`
    (or unnamed `, width`) takes the next `width` bits of it. One Offset
    group spans as many bytes as its fields add up to, so each field is
    filed under every byte it covers -- a 16-bit field names each half, and
    the two windows this tool watches hold no field wider than a byte.
    """
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines)
                 if l.strip().startswith("Field (ECMG"))
    out, addr, bit = {}, None, 0
    for line in lines[start + 1:]:
        line = line.split("//")[0].strip()
        if line == "}":
            break
        m = re.fullmatch(r"Offset \((0x[0-9A-Fa-f]+)\),\s*", line)
        if m:
            addr, bit = int(m.group(1), 16), 0
            continue
        m = re.fullmatch(r"([A-Za-z0-9_]*)\s*,\s*(\d+),\s*", line)
        if m and addr is not None:
            name, width = m.group(1), int(m.group(2))
            if name:
                lo, hi = bit, bit + width - 1
                for b in range(lo // 8, hi // 8 + 1):
                    out.setdefault(addr + b, []).append(
                        (name, max(lo, b * 8) % 8, min(hi, b * 8 + 7) % 8))
            bit += width
    return out


def field_list_text(fields):
    """The tool's spelling of one byte's fields, formatted from the DSDT.

    An 8-bit field is its name alone and a sub-byte field carries its bit or
    bit span -- the tool's column, not a restatement of the ASL's order.
    """
    if not fields:
        return "(no DSDT field)"
    parts = []
    for name, lo, hi in fields:
        if lo == 0 and hi == 7:
            parts.append(name)
        elif lo == hi:
            parts.append(f"{name} b{lo}")
        else:
            parts.append(f"{name} b{lo}-{hi}")
    return ", ".join(parts)


def read_registers():
    """`registers.yaml` as ({addr: status}, {addr: name}), keyed by address.

    A row's `addr:` is a list when it covers a block, and not everything
    under one is an int, so both are handled once here rather than in each
    class that wants the mapping. `name` is the label behind the row: both
    copies of the table cite its leading token rather than the whole
    parenthesised label, so the doc-table check below matches on that.
    """
    statuses, names = {}, {}
    for r in yaml.safe_load(REGISTERS.read_text())["registers"]:
        addrs = r["addr"] if isinstance(r["addr"], list) else [r["addr"]]
        for a in addrs:
            if isinstance(a, int):
                statuses.setdefault(a, r["status"])
                names.setdefault(a, r["name"])
    return statuses, names


def read_site_census():
    """`ec-07c4-07d5-sites.csv` as {addr: {site address}}, `bank0` rows only.

    The `region` filter is load-bearing, not a tidiness choice: the same
    file's 102 `pd-image` rows are a *different* 8051 program's variables at
    its own `0x07C4` (sites `.md` §1), with its own XDATA map, and folding
    them into a main-EC census would credit the main EC with sites in an
    image it is not in. Keyed by the row's own `addr` and valued by
    `runtime`, the site address inside that region -- the two are the same
    sixteen-bit space for a `bank0` row, and the `pd-image` rows are the
    ones where the file offset and the runtime address part company.
    """
    out = {}
    for r in csv.DictReader(SITES.read_text(encoding="utf-8").splitlines()):
        if r["region"] == "bank0":
            out.setdefault(int(r["addr"], 16), set()).add(
                int(r["runtime"], 16))
    return out


def bank_addresses(cell):
    """The `bankN:0xNNNN` addresses one §7 cell cites, as ints.

    The address half only, anchored on the `bankN:` prefix, for two reasons
    that are not cosmetic. The census keys sites by a bare address, so
    matching a whole `bank0:0x94C0` token against one fails on every site;
    and the column's other prefix, `pd:`, is the PD image's own XDATA map
    (sites `.md` §1), for which this census holds no rows at all. Case is
    dropped by the parse rather than by a `.lower()` that would then have to
    be undone on the other side.
    """
    return {int(a, 16) for a in re.findall(r"bank\d+:(0x[0-9A-Fa-f]{4})", cell)}


def doc_section(text, heading):
    """The named `## ` section, from its heading up to the next one.

    A missing heading raises rather than returning an empty section: an empty
    span makes every check that uses it pass vacuously, which is the one
    outcome worse than a doc that says nothing at all.
    """
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(heading))
    body = lines[start + 1:]
    for i, l in enumerate(body):
        if l.startswith("## "):
            return "\n".join(body[:i])
    return "\n".join(body)


def door_section(text):
    """The procedure's §7, the section the tool's watch table is graded against.

    Everything from the `## 7.` heading up to the next one, so both the table
    reader below and the note-count check read the same span.
    """
    return doc_section(text, "## 7. The citation list")


def parse_door_table(section):
    """The procedure's §7 table as {addr: {column heading: cell}}.

    Hand-rolled in this file's idiom rather than taken from a markdown
    library, because `project-setup` installs none and one table does not
    need one. A row is keyed by its `0xNNNN` address cell and its cells are
    filed under the header row's headings, so a column added above the one
    being compared cannot silently shift what is read. Rows whose first cell
    is not an address literal are skipped, which drops the header and its
    `|---|` separator.
    """
    cols, out = None, {}
    for line in section.splitlines():
        if cols is None:
            if line.startswith("| addr |"):
                cols = [c.strip() for c in line.strip().strip("|").split("|")]
            continue
        m = re.match(r"\|\s*`(0x[0-9A-Fa-f]{4})`\s*\|", line)
        if m:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out[int(m.group(1), 16)] = dict(zip(cols, cells))
    return out


class FakeEc:
    """Returns SWEEPS[n] for sweep n, and stops the run after the last one.

    The two events pin the interleaving: without them "did the MARK row land
    between the two change rows" would be a race against the sweep timer, and
    the test would pass on a build where marks never reach the CSV at all.
    """

    def __init__(self):
        self.at_last_sweep = threading.Event()
        self.marked = threading.Event()
        self._reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        sweep, offset = divmod(self._reads, len(ADDRS))
        if sweep == len(SWEEPS) - 1 and offset == 0:
            self.at_last_sweep.set()
            self.marked.wait(5)
        if sweep >= len(SWEEPS):
            raise KeyboardInterrupt
        self._reads += 1
        return SWEEPS[sweep][addr]

    def write(self, addr, val):
        # The tool has no write path. A run that reached this would be a
        # regression against docs/findings.md §4o, which is why the refusal
        # is here and not left to review.
        raise AssertionError(f"gpu_block_watch wrote 0x{addr:04X}=0x{val:02X}")


class FakeStdin:
    """One mark, stamped once the sweep loop reaches the last sweep.

    The second readline() is the proof the mark is fully committed -- Marker
    only asks for another line after writing the previous one -- so that is
    where the sweep loop is released.
    """

    def __init__(self, ec, label):
        self._ec = ec
        self._label = label
        self._sent = False

    def readline(self):
        self._ec.at_last_sweep.wait(5)
        if not self._sent:
            self._sent = True
            return self._label + "\n"
        self._ec.marked.set()
        return ""


class CitationTableTests(unittest.TestCase):
    """The table is checked against the inputs it claims to transcribe."""

    @classmethod
    def setUpClass(cls):
        cls.fields = parse_ecmg_fields(DSDT.read_text(encoding="utf-8",
                                                      errors="replace"))
        cls.statuses, cls.names = read_registers()

    def test_the_dsdt_field_list_the_table_is_checked_against_was_parsed(self):
        # A parser that found nothing would make the check below vacuous, and
        # a vacuous drift test is the one thing worse than none. The two
        # offsets the tool watches are 60 entries apart, so reaching the
        # second of them is itself the proof the walk got past the first.
        self.assertIn(0x0743, self.fields)
        self.assertIn(0x07C4, self.fields)
        self.assertEqual(self.fields[0x07D0], [("DBD1", 0, 7)])
        self.assertEqual(self.fields[0x07D1], [("DBD2", 0, 7)])

    def test_every_dsdt_name_and_bit_matches_the_field_list(self):
        for addr, name, _, _ in watch.WATCH:
            self.assertEqual(name, field_list_text(self.fields.get(addr, [])),
                             f"0x{addr:04X}")

    def test_every_registers_yaml_status_is_verbatim(self):
        for addr, _, status, _ in watch.WATCH:
            expected = self.statuses.get(addr, watch.NO_ROW)
            self.assertEqual(status, expected, f"0x{addr:04X}")

    def test_no_row_is_never_spelled_as_absence(self):
        # docs/findings.md §4c retracted a "does not exist" reading of a
        # zero-reference scan, and the watch table is where that phrasing
        # would come back from: every cell saying "no row" is a chance to be
        # read back as a claim of absence. Each one here is checked to mean
        # what it says, both ways.
        rows = {addr for addr, _, status, _ in watch.WATCH
                if status == watch.NO_ROW}
        self.assertTrue(rows)
        for addr, _, status, _ in watch.WATCH:
            if addr in rows:
                self.assertNotIn(addr, self.statuses, f"0x{addr:04X}")
            else:
                self.assertIn(addr, self.statuses, f"0x{addr:04X}")
        self.assertIn("registers.yaml", watch.NO_ROW)

    def test_every_citation_names_the_file_it_comes_from(self):
        for addr, _, _, cite in watch.WATCH:
            self.assertIn("dsdt.dsl:", cite, f"0x{addr:04X}")
            if self.statuses.get(addr):
                self.assertIn("registers.yaml", cite, f"0x{addr:04X}")

    def test_the_watch_set_is_the_two_windows_and_nothing_else(self):
        # The check that stops the tool quietly growing into a third
        # full-range 0x0700-0x07FF sweep, which is #94's problem to own.
        self.assertEqual(set(ADDRS), set(range(0x0743, 0x0747))
                         | set(range(0x07C4, 0x07D8)))
        self.assertEqual(len(ADDRS), 24)
        self.assertEqual(len(set(ADDRS)), len(ADDRS))
        # Every address falls in exactly one declared window, so a change line
        # always carries a tag and window_of() can never fall off the end.
        for a in ADDRS:
            covering = [label for label, s, e in watch.WINDOWS if s <= a <= e]
            self.assertEqual(covering, [watch.window_of(a)], f"0x{a:04X}")


class DoorTableTests(unittest.TestCase):
    """The procedure prints the watch table a second time, as prose.

    #266 is what that duplication cost: a `registers.yaml` row landed, the
    tool's copy was held by the class above, and the doc's four stale cells
    survived a whole merge cycle. This class is the other half of the hold --
    the doc is checked against the tool rather than against a human's
    memory, in both directions, so absence phrasing cannot survive in the
    second copy either.
    """

    @classmethod
    def setUpClass(cls):
        cls.statuses, cls.names = read_registers()
        cls.section = door_section(DOOR.read_text(encoding="utf-8"))
        cls.door = parse_door_table(cls.section)
        # Asked for by heading rather than by position, and found from the
        # rows rather than from a header that may itself have moved.
        cls.status_col = next((c for c in sorted({c for row in cls.door.values()
                                                  for c in row})
                               if "status:" in c), "")

    def test_the_door_table_was_parsed_and_covers_every_watched_address(self):
        # The same vacuity guard the DSDT parser above gets: a reader that
        # found nothing would make the two checks below pass on a doc that
        # says nothing, and a vacuous drift test is the one thing worse than
        # none. Every watched address present, no unwatched one, and every
        # row carrying the column the status check reads.
        self.assertEqual(set(self.door), set(ADDRS))
        for addr, row in self.door.items():
            self.assertIn(self.status_col, row, f"0x{addr:04X}")
        self.assertTrue(self.status_col, "§7 has no `status:` column")

    def test_the_door_table_status_column_matches_the_tool_and_registers_yaml(self):
        for addr, _, status, _ in watch.WATCH:
            cell = self.door[addr][self.status_col]
            if status == watch.NO_ROW:
                # A "no row" cell that names an entry is the absence claim
                # §4c retracted, so the check is bidirectional: it has to say
                # "no row", and it has to name nothing that has a row.
                self.assertIn("no row", cell, f"0x{addr:04X}")
                for name in self.names.values():
                    self.assertNotIn(name.split()[0], cell, f"0x{addr:04X}")
            else:
                # Verbatim status, and the entry's leading name token -- the
                # spelling the tool's own citation column already uses, so a
                # row that lands in registers.yaml cannot leave the doc
                # reading "no row" for an address that now has one.
                token = self.names[addr].split()[0]
                self.assertIn(status, cell, f"0x{addr:04X}")
                self.assertIn(token, cell, f"0x{addr:04X}")

    def test_the_door_no_row_note_counts_what_the_table_holds(self):
        # "sixteen of the twenty-four" outlived its own arithmetic when four
        # rows landed. The count is recomputed from registers.yaml, so the
        # sentence is checked against the file it describes rather than
        # against the tool, which is the copy being corrected.
        expected = sum(1 for a in ADDRS if a not in self.statuses)
        found = re.findall(r"\b(\d+) of the (\d+)\b", self.section)
        self.assertEqual(len(found), 1,
                         "§7's 'no row' count is gone or spelled more "
                         "than once")
        self.assertEqual(int(found[0][0]), expected)
        self.assertEqual(int(found[0][1]), len(ADDRS))


class SiteCensusTests(unittest.TestCase):
    """The four census-covered cells are graded against the site census.

    `DoorTableTests` above holds the status column; this holds the other
    one, for the four rows `ec-07c4-07d5-sites.md` walks. Both directions,
    because the drift is symmetric: a cell crediting `0x07C4` with one
    cross-reference where the walk found five is a doc that has not caught
    up with a census, and a re-walk that finds a sixth is a census the doc
    has not caught up with. The other twenty cells' `xdata-registers.csv`
    cluster citations and every `pd:` citation are #272's different census
    question and are not read here.
    """

    @classmethod
    def setUpClass(cls):
        cls.section = door_section(DOOR.read_text(encoding="utf-8"))
        cls.door = parse_door_table(cls.section)
        cls.census = read_site_census()
        cls.sites_md = SITES_MD.read_text(encoding="utf-8")
        # Asked for by heading and found from the rows, the same way
        # DoorTableTests finds the status column.
        cls.xref_col = next((c for c in sorted({c for row in cls.door.values()
                                                for c in row})
                             if "cross-reference" in c), "")

    def test_the_census_the_cross_reference_column_is_checked_against_was_read(self):
        # The same vacuity guard the three parsers above get: a reader that
        # found nothing would leave both directions below passing on a table
        # that says nothing. Every census address present and carrying the
        # column, the split sites `.md` §2 states in prose ("The five
        # `0x07C4` sites, the two `0x07D4` and four `0x07D5` sites and the
        # four `0x07D3` sites") rather than constants invented here, and a
        # `.md` naming all four so direction A's fallback is a real source
        # and not an empty string everything passes against.
        self.assertTrue(self.xref_col, "§7 has no cross-reference column")
        for addr in self.census:
            self.assertIn(addr, self.door, f"0x{addr:04X}")
            self.assertIn(self.xref_col, self.door[addr], f"0x{addr:04X}")
        self.assertEqual({a: len(s) for a, s in self.census.items()},
                         {0x07C4: 5, 0x07D3: 4, 0x07D4: 2, 0x07D5: 4})
        self.assertTrue(self.sites_md, f"{SITES_MD.name} is empty")
        for addr in self.census:
            self.assertRegex(self.sites_md, rf"0x{addr:04X}", f"0x{addr:04X}")

    def test_every_bank_address_a_cell_cites_is_in_the_census_or_the_walk(self):
        # Direction A, doc -> census. What a citation carries here is that
        # the walk named that address, not that the walk was right about
        # it: `bank0:0x94C0` is a routine entry and `bank0:0x9711` its one
        # caller (sites `.md` §4.1), so both are named in prose and neither
        # is a `MOV DPTR` site the CSV has a row for. The `.md` half is a
        # fallback source, not a weaker census.
        for addr, sites in self.census.items():
            cell = self.door[addr][self.xref_col]
            for site in sorted(bank_addresses(cell)):
                if site in sites:
                    continue
                self.assertTrue(
                    re.search(rf"0x{site:04X}(?![0-9A-Fa-f])", self.sites_md,
                              re.I),
                    f"0x{addr:04X} cites bank0:0x{site:04X}, which neither "
                    f"{SITES.name} nor {SITES_MD.name} names")

    def test_every_bank0_site_the_census_names_is_in_the_cell(self):
        # Direction B, census -> doc, and the one that fails first when a
        # re-walk lands: the census grows and the doc's credit for the row
        # stays what it was. The two set sizes ride along in the message so
        # that failure says which side moved and by how much -- the citation
        # count itself is not pinned, because the two directions already pin
        # every address between them and a constant would only add an edit
        # to make on the next legitimate census change.
        for addr, sites in self.census.items():
            cited = bank_addresses(self.door[addr][self.xref_col])
            for site in sorted(sites):
                self.assertIn(
                    site, cited,
                    f"0x{site:04X} is a bank0 site for 0x{addr:04X} in "
                    f"{SITES.name} and is not in the cell "
                    f"({len(cited)} cited, {len(sites)} in the census)")


class GraderAgreementTests(unittest.TestCase):
    """The door grader's copy of the watch table, held against this one.

    `ec/tools/grade_gpu_door.py` grades the capture this tool writes and
    answers §5's ordering column from it. It cannot import this module -- the
    `ecrw` import above binds kernel32 -- so it states its own two window
    bounds and its own 24 ECMG field-list names, and this class is the hold.

    The same shape as DoorTableTests above, and for the same reason: #266 let
    a second copy of this table drift through a whole merge cycle. A grader
    that read a capture against different bounds than the one that wrote it
    would be grading one tool's watch set with another's, and would say so
    nowhere.
    """

    def test_the_grader_stated_a_table_at_all(self):
        # The vacuity guard, for the same reason the two parsers above have
        # one: a loader that found nothing would make every check below pass
        # on a grader that grades no addresses at all.
        self.assertTrue(grader.DS_NAMES, "the grader states no DSDT names")
        self.assertTrue(grader.WINDOWS, "the grader states no windows")
        self.assertEqual(len(grader.DS_NAMES), len(ADDRS))

    def test_the_window_bounds_are_the_watchers(self):
        # Equality on the tuples, labels included: §5's columns are headed with
        # the two ranges, so a label that disagreed would be visible in a
        # filled table and in this grader's own output.
        self.assertEqual(list(grader.WINDOWS), list(watch.WINDOWS))

    def test_the_dsdt_names_are_the_watchers(self):
        # Same order and same spelling, so a movement the grader prints under
        # §5's "DSDT name" column carries the name the watcher printed in the
        # capture's own header. CitationTableTests holds `watch.WATCH` against
        # evidence/acpi/dsdt.dsl, so the chain from the ASL to the grader's
        # column is checked at both ends rather than trusted in the middle.
        self.assertEqual(list(grader.DS_NAMES),
                         [(addr, name) for addr, name, _, _ in watch.WATCH])

    def test_the_two_bounds_cover_exactly_the_watch_set(self):
        # No watched address outside the grader's bounds, and none inside them
        # the watcher does not sweep. The second half matters because
        # `name_of` raises on an address with no name: a capture carrying a row
        # the grader bounds cover but its name table does not would fail its
        # own report rather than reading it.
        covered = {a for _, lo, hi in grader.WINDOWS for a in range(lo, hi + 1)}
        self.assertEqual(covered, set(ADDRS))
        self.assertEqual({addr for addr, _ in grader.DS_NAMES}, set(ADDRS))
        for addr in ADDRS:
            self.assertEqual(grader.window_of(addr), watch.window_of(addr),
                             f"0x{addr:04X}")


class CaptureHandoffTests(unittest.TestCase):
    """Where a returned capture lands, and what it is allowed to change.

    The procedure had neither half. §3 passed `--csv` a bare filename, so an
    operator running it from the repository root put the capture in the
    repository root rather than in `evidence/`; §3 and §4a.2 both depend on
    the run's marks, and neither gave them a committed name; and nothing told
    a person filling in `registers.yaml` afterwards what a capture is worth.
    #266 is what a duplicated table nobody holds costs -- four stale cells
    through a whole merge cycle -- and this is the same hold on the two
    sections that answer for an operator's file, before it exists.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = DOOR.read_text(encoding="utf-8")
        cls.capture = doc_section(cls.text, "## 3. The byte capture")
        cls.where = doc_section(cls.text, "## 8. Where the output goes")
        cls.result = doc_section(cls.text, "## 9. What a result has to say")
        cls.statuses, _ = read_registers()

    def test_the_output_destination_exists_and_is_named(self):
        # The section is read by heading and doc_section() raises on a
        # missing one, so the checks below cannot pass on a procedure that
        # has stopped saying this -- the vacuity guard §7's reader carries.
        # The directory itself is checked because the name is worth nothing
        # if it points at a place the tree does not have.
        self.assertIn("evidence/ec-watch/", self.where)
        # §8 is the section that tells the operator to index the files, so
        # that half of "where the output goes" is held here too -- a capture
        # that is committed and not indexed is cited by nothing.
        self.assertIn("evidence/README.md", self.where)
        self.assertTrue((REPO / "evidence" / "ec-watch").is_dir())

    def test_the_capture_command_writes_into_that_destination(self):
        # The check that stops §3's command drifting back to a bare filename.
        # `CsvSink` resolves its path against whatever directory the tool
        # runs in (windows/tools/ec_watch.py:56-57), so a command with no
        # directory in it puts the capture wherever the operator happened to
        # be standing -- which is how a run that happened ends up in a commit
        # with no capture in it. Read out of the console block rather than
        # the section, because the prose around it talks about `--csv` too.
        # Separators are normalised because a relative path is spelled with
        # either; the directory is not optional either way.
        block = re.search(r"```console\n(.*?)```", self.capture, re.S)
        self.assertIsNotNone(block, "§3's console block is gone")
        # The `rem` lines are cmd comments and the section's own prose
        # explains the flag by name, so neither is a command. Reading them
        # as one is what would make this check fail on the documentation
        # rather than on the command it is about.
        cmd = "\n".join(l for l in block.group(1).splitlines()
                        if not l.strip().startswith("rem"))
        found = re.findall(r"--csv\s+(\S+)", cmd)
        self.assertEqual(len(found), 1,
                         "§3's --csv argument is gone or spelled more than "
                         f"once: {found}")
        path = found[0].replace("\\", "/")
        self.assertTrue(path.startswith("evidence/ec-watch/"), path)

    def test_the_result_section_names_the_rows_a_returned_capture_updates(self):
        # The three notes that record only what the 2026-09-23 capture
        # showed, the file the section says to update them from, and the two
        # places the follow-up edit lands. Named here because §9 is a
        # promise to a person holding a laptop, and a promise that stops
        # naming its four destinations is not a promise anybody can act on.
        for token in ("0x07D0", "0x07D1", "0x07C4", "registers.yaml",
                      "evidence/README.md"):
            self.assertIn(token, self.result)

    def test_the_result_section_does_not_move_a_status(self):
        # §9's claim is negative, so it is checked both ways against
        # registers.yaml: each row §9 names a status for must carry the
        # status that file holds today, and no status a capture cannot earn
        # may appear. Either half alone is survivable -- a §9 that quietly
        # dropped the rule, or one that granted a capture `confirmed-*` --
        # and this is the one place a passive capture could be read as a
        # live test without a row moving with it.
        for addr in (0x07D0, 0x07D1, 0x07D4, 0x07D5):
            self.assertIn(self.statuses[addr], self.result,
                          f"0x{addr:04X}: §9 must carry the current status")
        # The negative half is matched as an assignment rather than as a bare
        # status value. §9 quoting the vocabulary to say a capture cannot
        # reach it is that section doing its job, and the value alone is not
        # the tell; a promoting word in front of one is. `to` and the arrow
        # are in the alternation because those are how a status move reads
        # in this repository's prose, and the leading \b keeps `to` out of
        # the middle of a longer word.
        promote = re.compile(r"\b(?:becomes?|status:\s*|moves? to|to|→)\s*"
                             r"`?confirmed-(?:working|inert)")
        self.assertIsNone(promote.search(self.result),
                          "§9 promotes a status a capture cannot earn")


class NamesOnlyTests(unittest.TestCase):
    def test_names_only_prints_the_table_and_opens_no_ec(self):
        out = io.StringIO()
        with patch.object(watch, 'Ec', lambda: self.fail("opened an EC")), \
             contextlib.redirect_stdout(out):
            rc = watch.main(['--names-only'])
        text = out.getvalue()
        self.assertEqual(rc, 0)
        for addr, name, status, cite in watch.WATCH:
            self.assertIn(f"0x{addr:04X}", text)
            self.assertIn(name, text)
            self.assertIn(status, text)
            self.assertIn(cite, text)
        self.assertIn("not about the address", text)

    def test_the_table_is_printed_before_a_run_starts_too(self):
        # A capture is evidence, and evidence that does not record what was
        # watched is a capture of nothing in particular.
        ec = FakeEc()
        ec.marked.set()
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(watch, 'Ec', lambda: ec), \
                 contextlib.redirect_stdout(out):
                watch.main(['--interval', '0', '--csv',
                            str(Path(tmp) / 'c.csv')])
        text = out.getvalue()
        for addr, name, _, cite in watch.WATCH:
            self.assertIn(f"0x{addr:04X}  {name}", text)
            self.assertIn(cite, text)
        self.assertIn("no interval here is validated", text)


class MarkCsvTests(unittest.TestCase):
    def run_watch(self, *extra):
        ec = FakeEc()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            with patch.object(watch, 'Ec', lambda: ec), \
                 patch.object(watch.sys, 'stdin',
                              FakeStdin(ec, 'gpu tgp 115W->130W')), \
                 contextlib.redirect_stdout(io.StringIO()):
                rc = watch.main(['--interval', '0', '--csv', str(out), *extra])
            return rc, out.read_text().splitlines()

    def test_mark_lands_in_the_csv_between_the_change_rows(self):
        rc, rows = self.run_watch('--mark')
        self.assertEqual(rc, 0)
        # ec_watch.py's schema exactly: a downstream reader of a mark-delimited
        # capture (ec/tools/grade_gpu_door.py, issue #283) must not need a
        # parser written for this file.
        self.assertEqual(rows[0], 'ts,addr,old,new')
        self.assertEqual([r.split(',', 1)[1] for r in rows[1:]],
                         [f'0x{ACPI:04X},0x00,0x37',
                          'MARK,,gpu tgp 115W->130W',
                          f'0x{HOST:04X},0x00,0x0A'])

    def test_both_windows_are_in_one_capture(self):
        _, rows = self.run_watch('--mark')
        addrs = [r.split(',', 1)[1].split(',')[0] for r in rows[1:]]
        self.assertIn(f"0x{ACPI:04X}", addrs)
        self.assertIn(f"0x{HOST:04X}", addrs)

    def test_the_summary_reports_both_windows_and_grades_neither(self):
        ec = FakeEc()
        ec.marked.set()
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(watch, 'Ec', lambda: ec), \
                 contextlib.redirect_stdout(out):
                watch.main(['--interval', '0', '--csv',
                            str(Path(tmp) / 'c.csv')])
        # The startup table prints the status column, so the grading words are
        # checked against the summary -- what the run concluded, not what it
        # was told to look at. A zero in a capture is "not moved by this
        # method under this action"; ec/tools/grade_gpu_door.py owns the
        # reading, and names itself in the summary below this one.
        summary = out.getvalue()[out.getvalue().index("=== "):]
        self.assertIn("window 0x07C4-0x07D7", summary)
        self.assertIn("window 0x0743-0x0746", summary)
        self.assertIn("not a verdict", summary)
        for word in ("absent", "confirmed-working", "confirmed-inert",
                     "unused", "unreferenced"):
            self.assertNotIn(word, summary)


if __name__ == '__main__':
    unittest.main()
