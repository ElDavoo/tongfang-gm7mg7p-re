#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

gpu_block_watch.py imports ecrw, and `windows/tools/ecrw_fake.py` stands in
for the whole module so the sweep is scriptable byte by byte -- installed by
assignment, so this suite is not a party to the `setdefault` ordering accident
docs/findings.md §16 records. What the fake is for now is scriptability: the
module imports anywhere, which
`windows/tools/test_import_off_windows.py` holds for every tool in this
directory that wants no pip package. Deleting it, and having the suites import
the real `ecrw` and patch its `Ec` in the tool's own namespace, is the open
follow-up.

Unlike most of the `windows/tools` suites this one reads committed inputs,
`evidence/acpi/dsdt.dsl`, `ec/annotations/registers.yaml`,
`ec/annotations/ec-07c4-07d5-sites.csv`/`.md`,
`ec/annotations/ec-0x07c5-sites.csv`/`.md` and this procedure's own table
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
copy's EC-side cross-reference column for the rows the per-site censuses
cover, against the two site CSVs and their `.md`s: the doc
was free to credit `0x07C4` with one cross-reference where the walk had found
five, and a re-walk that finds a sixth would move the census the same way
without the doc moving with it.

There was once a fifth class here, holding `ec/tools/grade_gpu_door.py`'s
transcribed copy of this tool's bounds and DSDT names against the originals.
That copy is gone: the grader imports this module for them, so the table is
read once rather than transcribed twice. A hold comparing a value to a
comprehension over itself would be a tautology, and what replaced it is a
check with a subject of its own -- that the grader can *name* every address
its own bounds cover -- in `ec/tools/test_grade_gpu_door.py`. The remaining
class holds the two sections that tell a human's capture where to land and
what it is allowed to change: a procedure that is written but not followed is
the failure this suite can still catch before the machine.
"""
import csv
import contextlib
import importlib
import importlib.util
import io
from copy import deepcopy
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
# `0x07C5` is walked in its own per-register file rather than in the four-address
# one above: one CSV and one `.md` per register is the modular shape two single
# addresses already use, and it keeps this census from growing a file several
# open PRs are in. Both halves of the pairing are read, so neither direction
# below gets weaker for the split.
SITES_07C5 = REPO / "ec" / "annotations" / "ec-0x07c5-sites.csv"
SITES_07C5_MD = REPO / "ec" / "annotations" / "ec-0x07c5-sites.md"
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
# otherwise outside every import root this runner sets. The reverse direction
# needs no such help: the grader inserts this directory itself and does a
# plain `import gpu_block_watch`, so it gets the module object above rather
# than a second copy of it.
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
    """The site CSVs as {addr: {site address}}, `bank0` rows only.

    Reads `SITES` and `SITES_07C5` into one census. The `region` filter is
    load-bearing, not a tidiness choice: the first file's 102 `pd-image` rows
    are a *different* 8051 program's variables at its own `0x07C4` (sites
    `.md` §1), with its own XDATA map, and folding them into a main-EC
    census would credit the main EC with sites in an image it is not in.
    Keyed by the row's own `addr` and valued by `runtime`, the site address
    inside that region -- the two are the same sixteen-bit space for a
    `bank0` row, and the `pd-image` rows are the ones where the file offset
    and the runtime address part company.

    One address in two files is a merge here rather than a collision: the
    keys are register addresses and a register is walked in one file, so a
    second file carrying the same address is a second walk of it and the two
    walks' sites land in one set rather than one replacing the other.
    """
    out = {}
    for path in (SITES, SITES_07C5):
        for r in csv.DictReader(path.read_text(encoding="utf-8").splitlines()):
            if r["region"] == "bank0":
                out.setdefault(int(r["addr"], 16), set()).add(
                    int(r["runtime"], 16))
    return out


def read_site_walks():
    """The walk `.md`s direction A falls back on, as one text.

    Concatenated rather than searched one at a time so a citation either
    walk names is found, which is the whole of what the fallback is for:
    a routine entry the CSV has no row for (`bank0:0x94C0`) is named in
    prose by whichever file walked it.
    """
    return "\n".join(p.read_text(encoding="utf-8")
                     for p in (SITES_MD, SITES_07C5_MD))


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


# The addresses a §7 cell may cite that no census row covers, each with why it
# is not a site. A dictionary rather than a pattern over the walks' `.md`s
# because those documents are write-ups of the whole walks: they name every
# register address, every `MOV DPTR` operand and every byte of every listing in
# them, so a shape drawn from them admits a cell citing `0x0743` or `0x09E9`
# and calling it a site. Each entry is named individually so that another one
# has to be argued for. The allowance is held to the data by
# `test_the_fallback_is_exactly_the_addresses_the_census_does_not_carry`, so
# neither this list nor a cell can grow alone.
NON_SITE_CITATIONS = {
    # The routine entry of the eight-site chain: cited because it *contains* the
    # `0x07C4`/`0x07D4`/`0x07D5` sites rather than being one.
    0x83FF: "routine entry `sync_0788_and_07d4_from_09e9`",
    # A routine entry, and the window the 8-instruction walk stopped on -- the
    # `MOV DPTR,#0x07C4` it walks past is the site, this is the instruction
    # before it (sites `.md` §4.1).
    0x94C0: "routine entry `set_07c4_bit4_from_r7`",
    # The one `lcall 0x94C0` in the image: the caller, not an access at all.
    0x9711: "the single `lcall 0x94C0`",
    # A `movx @DPTR,A` against whatever `DPTR` the caller left, carrying
    # `xdata-registers.csv`'s `[writer]` tag for `0x07C5` and named
    # `store_a_then_read_07c5`. The cell cites it to *correct* that tag, and the
    # access of this byte is the `movx a,@dptr` that follows it at `0xBB81`,
    # which is a census row (0x07C5 walk §2.1). A tag the walk found to be wrong
    # is not a writer of the byte, so it is allowed here rather than in the CSV.
    0xBB80: "`store_a_then_read_07c5`, a store against an inherited `DPTR`",
}


def cited_addresses_not_in_census(census, door, xref_col):
    """The addresses a cell cites that no census row covers, as a set.

    The derived fall-through, deliberately unfiltered by `NON_SITE_CITATIONS`:
    the guard below compares this against that constant, and a helper that
    already applied it would be checking the constant against itself.
    """
    out = set()
    for addr, sites in census.items():
        out |= bank_addresses(door[addr][xref_col]) - sites
    return out


def unaccounted_citations(census, door, xref_col):
    """Direction A's failures as `[(cell address, cited address)]`, sorted.

    Factored out of the test below so that the perturbation test drives the
    check's own arithmetic rather than a second copy of it: a perturbation that
    recomputes the verdict proves the *copy* has teeth, and passes just as
    happily if the check itself is widened.
    """
    out = []
    for addr, sites in sorted(census.items()):
        allowed = sites | set(NON_SITE_CITATIONS)
        out += [(addr, site) for site
                in sorted(bank_addresses(door[addr][xref_col]) - allowed)]
    return out


def sites_missing_from_cells(census, door, xref_col):
    """Direction B's failures as `[(cell address, census site)]`, sorted.

    The converse of `unaccounted_citations`, and factored out for the same
    reason: the drop perturbation has to exercise the check rather than restate
    it, or reverting the check to a form that tolerates a dropped site would
    leave the perturbation green.
    """
    out = []
    for addr, sites in sorted(census.items()):
        cited = bank_addresses(door[addr][xref_col])
        out += [(addr, site) for site in sorted(sites - cited)]
    return out


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
    reader below and the note check read the same span.
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


def doc_subsection(text, heading):
    """The named `### ` section, bounded at the next heading of either level.

    `doc_section` above stops only at `## `, and this file's §4a is a `###`
    under §4 with a `### 4b` sibling, so asking it for `### 4a.` runs on
    through §4b and hands back 59 lines where §4a is 48. That is not a
    cosmetic difference where a check is about §4a: the negative below is on
    a filename, and a span that reaches into §4b is a span in which a `-marks`
    would pass for §4a saying nothing. Bounded at the next heading of either
    level instead, and a missing heading raises, as above.
    """
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(heading))
    body = lines[start + 1:]
    for i, l in enumerate(body):
        if re.match(r"^#{1,3} ", l):
            return "\n".join(body[:i])
    return "\n".join(body)


# Suffixes §4 saves by a step an operator performs in ProcMon's own UI rather
# than by anything the watcher writes. A set, and named for the step rather
# than for today's file: a second hand-saved artifact joins it by having a
# suffix here, and the step that justifies each is asserted against §4a in
# `test_every_artifact_section_8_names_has_a_producer`, so the allowance cannot
# sit here as a constant no section of the procedure backs.
HUMAN_SAVED_SUFFIXES = frozenset({".pml"})


def command_output_paths(cmd):
    """Every path-shaped argument in §3's command, whichever flag carries it.

    Not a list of known output flags, and that is deliberate: §3's command
    grows a `--dump` or a `--marks` and this picks the new one up with nothing
    edited. The discriminator is "carries a separator and is not the tool
    itself" — the tool path is the one path-shaped argument that is an input,
    and the `^` cmd line-continuation carries no separator, so both drop out
    without a rule naming either.
    """
    out = set()
    for token in cmd.split():
        if "/" in token or "\\" in token:
            path = token.replace("\\", "/")
            if not path.endswith(".py"):
                out.add(path)
    return out


def unaccounted_artifacts(listed, command_paths, human_suffixes):
    """The §8 entries neither §3's command writes nor a §4 step saves.

    Two producers and only two, because a run has two: an output path the
    command passes to the tool, or a suffix a human saves in ProcMon's UI. An
    entry matching neither is a file no run produces, which is the shape #402
    found — §8 named a `MARK` transcript that no flag in the tree writes, so
    the file an operator following the procedure by hand transcribed was not
    an artifact of the run at all. One direction only; the other, that every
    path the command writes is also listed, is a plain set comparison at the
    call site so this helper's contract stays one-directional.
    """
    suffixes = tuple(human_suffixes)
    return [p for p in listed
            if p not in command_paths and not p.lower().endswith(suffixes)]


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

    def test_the_door_no_row_note_states_its_scope_and_keeps_no_census(self):
        # The note once opened by counting its own table's rows, and it
        # outlived its own arithmetic when a row landed. Recomputing such a
        # count is not a fix: it is a value every merge that adds or
        # re-grades a row has to edit. What is worth holding is the sentence's
        # scope -- that a "no row" cell is about registers.yaml and not about
        # the address -- and the arithmetic staying out.
        self.assertIn("a statement about `registers.yaml`, not about the address",
                      self.section)
        self.assertEqual(re.findall(r"\b\d+ of the \d+\b", self.section), [],
                         "§7's note counts its own table again")


class SiteCensusTests(unittest.TestCase):
    """The census-covered cells are graded against the site census.

    `DoorTableTests` above holds the status column; this holds the other
    one, for the rows the per-register walks cover -- `0x07C4`, `0x07D3`,
    `0x07D4` and `0x07D5` from `ec-07c4-07d5-sites.md`, and `0x07C5` from
    `ec-0x07c5-sites.md`. Both directions, because the drift is symmetric: a
    cell crediting `0x07C4` with one cross-reference where the walk found
    five is a doc that has not caught up with a census, and a re-walk that
    finds a sixth is a census the doc has not caught up with. The other
    cells' `xdata-registers.csv` cluster citations and every `pd:` citation
    are #272's different census question and are not read here.
    """

    @classmethod
    def setUpClass(cls):
        cls.section = door_section(DOOR.read_text(encoding="utf-8"))
        cls.door = parse_door_table(cls.section)
        cls.census = read_site_census()
        cls.sites_md = read_site_walks()
        # Asked for by heading and found from the rows, the same way
        # DoorTableTests finds the status column.
        cls.xref_col = next((c for c in sorted({c for row in cls.door.values()
                                                for c in row})
                             if "cross-reference" in c), "")

    def test_the_census_the_cross_reference_column_is_checked_against_was_read(self):
        # The same vacuity guard the three parsers above get: a reader that
        # found nothing would leave both directions below passing on a table
        # that says nothing. Every census address present and carrying the
        # column, the split each walk's `.md` states in prose rather than
        # constants invented here, and a walk naming every one so direction
        # A's fallback is a real source and not an empty string everything
        # passes against.
        #
        # The per-address counts are the *claim* -- this census holds these
        # sites for these addresses -- and not a census of the tree: they are
        # what a re-walk of an address has to re-derive, so the next
        # legitimate re-walk edits this line, by design. What no re-walk
        # should be able to do is change one side and not the other, which
        # is what the two directions below are for.
        self.assertTrue(self.xref_col, "§7 has no cross-reference column")
        for addr in self.census:
            self.assertIn(addr, self.door, f"0x{addr:04X}")
            self.assertIn(self.xref_col, self.door[addr], f"0x{addr:04X}")
        self.assertEqual({a: len(s) for a, s in self.census.items()},
                         {0x07C4: 5, 0x07C5: 10, 0x07D3: 4,
                          0x07D4: 2, 0x07D5: 4})
        self.assertTrue(self.sites_md, "the walks read as empty text")
        for addr in self.census:
            self.assertRegex(self.sites_md, rf"0x{addr:04X}", f"0x{addr:04X}")

    def test_the_fallback_is_exactly_the_addresses_the_census_does_not_carry(self):
        # Direction A's allowance, held against the data it allows -- set
        # equality in both directions, so neither a cell citing a non-site
        # address the allowance does not name nor an entry nobody cites goes
        # unnoticed. Named for the fallback rather than for the census read
        # above because it is the fallback it holds; the same reason
        # `HUMAN_SAVED_SUFFIXES` is checked against the section behind it
        # rather than trusted as a constant.
        fallthrough = cited_addresses_not_in_census(self.census, self.door,
                                                    self.xref_col)
        self.assertEqual(
            fallthrough, set(NON_SITE_CITATIONS),
            "the addresses the census does not carry are not the ones the "
            f"allowance names. Data: "
            f"{sorted(f'0x{a:04X}' for a in fallthrough)}; allowance: "
            f"{sorted(f'0x{a:04X}' for a in NON_SITE_CITATIONS)}")
        # The walks are what back the allowance, checked here rather than on
        # every cited address in direction A: an entry that stops being named
        # in them is an allowlist entry with nothing behind it, and this is
        # the one place that shows which. Each entry is named by whichever walk
        # covered the row citing it -- `0xBB80` by the `0x07C5` walk, the
        # other three by the four-address one -- which is why this reads the
        # concatenated text rather than either file.
        for addr in sorted(NON_SITE_CITATIONS):
            self.assertRegex(self.sites_md, rf"0x{addr:04X}(?![0-9A-Fa-f])",
                             f"0x{addr:04X} is allowed but no walk names it")

    def test_a_cell_citing_an_address_only_the_walk_names_in_prose_is_rejected(self):
        # The tightening, shown by perturbing the table the check reads. The
        # second assertion is the one that makes this a demonstration rather
        # than a check that happens to fire: the same address against the
        # `re.search` this replaced passes, which is why the fallback could
        # not catch a citation that no longer resolves. `0x0743` is the
        # `CTGP_DB_CTRL` byte the walk's own listings name, so it is inside
        # the shape the old fallback matched on.
        mutated = deepcopy(self.door)
        cell = mutated[0x07C4][self.xref_col]
        self.assertIn("bank0:0x94C0", cell)
        mutated[0x07C4][self.xref_col] = cell.replace("bank0:0x94C0",
                                                       "bank0:0x0743")
        reported = unaccounted_citations(self.census, mutated, self.xref_col)
        self.assertEqual(reported, [(0x07C4, 0x0743)],
                         "the tightened direction A did not report the "
                         f"perturbed citation, or reported {reported}")
        self.assertTrue(
            re.search(r"0x0743(?![0-9A-Fa-f])", self.sites_md, re.I),
            "no walk names the address the tightened check rejected, so this "
            "demonstrates nothing: the old fallback would have rejected it "
            "too")
        # The allowance still passes against the same mutated table, which is
        # the other half of the narrowing: an allowance that survives only
        # while nothing perturbs it is not one.
        for addr in sorted(NON_SITE_CITATIONS):
            self.assertNotIn(
                addr, {site for _, site in reported},
                f"0x{addr:04X} is an allowed non-site citation and the "
                "tightened check reported it")

    def test_dropping_a_genuine_site_from_a_cell_is_reported(self):
        # The issue's requested perturbation, aimed at the direction that can
        # see it. It cannot be aimed at direction A: that asks whether a
        # *cited* address resolves, so removing a citation cannot fail it --
        # dropping `bank0:0x843D` leaves A passing by construction. Direction
        # B asks the converse and is the half that catches a census site the
        # cell stopped crediting, which is the drift this table has actually
        # shown (#266).
        mutated = deepcopy(self.door)
        cell = mutated[0x07C4][self.xref_col]
        self.assertIn("bank0:0x843D", cell)
        mutated[0x07C4][self.xref_col] = cell.replace("bank0:0x843D", "")
        self.assertNotIn("bank0:0x843D",
                         mutated[0x07C4][self.xref_col])
        # Driven through the helper direction B itself reads, so this asserts the
        # check's own arithmetic rather than a second copy of it. Compared as a
        # list rather than inside the loop the check runs, because a loop over
        # the missing sites asserts nothing at all when none is missing -- and
        # "the drop went unnoticed" is exactly the outcome being demonstrated.
        missing = sites_missing_from_cells(self.census, mutated, self.xref_col)
        self.assertEqual(
            missing, [(0x07C4, 0x843D)],
            "dropping bank0:0x843D from the 0x07C4 cell was not reported by "
            f"direction B; it saw {missing}")

    def test_every_bank_address_a_cell_cites_is_in_the_census_or_the_walk(self):
        # Direction A, doc -> census. What a citation carries here is that
        # the walk named that address, not that the walk was right about
        # it: `bank0:0x94C0` is a routine entry and `bank0:0x9711` its one
        # caller (sites `.md` §4.1), so both are named in prose and neither
        # is a `MOV DPTR` site the CSVs have a row for.
        #
        # The allowance is `NON_SITE_CITATIONS` and not "a walk's `.md` names
        # this address somewhere": those `.md`s are write-ups of the whole
        # walks, so a search over them admitted a cell citing `0x0743` or
        # `0x09E9` -- a register address and a source byte -- which is the
        # citation this direction exists to catch. The `.md`s still back the
        # allowance, but through the guard's set equality rather than on every
        # address.
        for addr, site in unaccounted_citations(self.census, self.door,
                                                self.xref_col):
            self.fail(
                f"0x{addr:04X} cites bank0:0x{site:04X}, which no site CSV "
                f"nor walk makes a site. If it is another routine entry or "
                f"caller, add it to NON_SITE_CITATIONS with the reason; if it "
                f"is not, the cell is citing an address this direction should "
                f"reject")

    def test_every_bank0_site_the_census_names_is_in_the_cell(self):
        # Direction B, census -> doc, and the one that fails first when a
        # re-walk lands: the census grows and the doc's credit for the row
        # stays what it was. `0x07C5` is the case that earned it -- the cell
        # credited one writer, `bank0:0xBB80`, which is not a writer of that
        # byte at all, and this direction is what makes that a failure rather
        # than a stale sentence. The two set sizes ride along in the message so
        # that failure says which side moved and by how much -- the citation
        # count itself is not pinned, because the two directions already pin
        # every address between them and a constant would only add an edit
        # to make on the next legitimate census change.
        for addr, site in sites_missing_from_cells(self.census, self.door,
                                                   self.xref_col):
            cited = bank_addresses(self.door[addr][self.xref_col])
            self.fail(
                f"0x{site:04X} is a bank0 site for 0x{addr:04X} in a site "
                f"census and is not in the cell "
                f"({len(cited)} cited, {len(self.census[addr])} in the "
                f"census)")


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
        cls.procmon = doc_subsection(cls.text, "### 4a. ProcMon, the primary route")
        cls.statuses, _ = read_registers()
        # §3's command with the `rem` lines dropped, and §8's file list read
        # out of its fenced block. The block rather than the prose around it,
        # because that prose counts the set ("the only one of the two") and a
        # check reading it would be holding a count against itself. Both raise
        # rather than yielding an empty list or an empty command, for the
        # vacuity reason `doc_section` gives.
        block = re.search(r"```console\n(.*?)```", cls.capture, re.S)
        if block is None:
            raise AssertionError("§3's console block is gone")
        cls.cmd = "\n".join(l for l in block.group(1).splitlines()
                            if not l.strip().startswith("rem"))
        files = re.search(r"```\n(.*?)```", cls.where, re.S)
        if files is None:
            raise AssertionError("§8's file list block is gone")
        cls.artifacts = [l.strip().replace("\\", "/")
                         for l in files.group(1).splitlines() if l.strip()]
        cls.cmd_paths = command_output_paths(cls.cmd)

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
        # runs in (`CsvSink.__init__` in windows/tools/ec_watch.py -- the
        # `open(path, "a", ...)` there, not a line number, so the next
        # reorganisation of that file cannot silently re-stale this), so a
        # command with no directory in it puts the capture wherever the
        # operator happened to be standing -- which is how a run that happened
        # ends up in a commit with no capture in it. Read out of the console
        # block rather than the section, because the prose around it talks
        # about `--csv` too.
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

    def test_every_artifact_section_8_names_has_a_producer(self):
        # The general form of #402. §8 named three artifacts and two had a
        # producer; the third was a marks transcript no flag in the tree
        # writes, so an operator following the procedure either hand-made it
        # or had nothing to hand in, and the run it named was not the run that
        # happened. Read as a rule about the whole set rather than a refusal
        # of that one filename, so the next artifact somebody adds without a
        # producer is caught here too.
        self.assertTrue(self.artifacts, "§8 names no artifacts at all")
        unaccounted = unaccounted_artifacts(self.artifacts, self.cmd_paths,
                                            HUMAN_SAVED_SUFFIXES)
        self.assertEqual(unaccounted, [],
                         f"§8 names artifacts no run produces: {unaccounted}")
        # The other direction, kept out of the helper so that one's contract
        # stays one: a path §3 writes that §8 does not list is a capture that
        # lands where the index will not find it.
        unlisted = self.cmd_paths - set(self.artifacts)
        self.assertEqual(unlisted, set(),
                         f"§3 writes artifacts §8 does not name: {unlisted}")
        # The `.pml` allowance is the only producer a run does not have a flag
        # for, so it is tied here to the step that earns it. Without this the
        # set above is a constant that would keep exempting a suffix after the
        # section behind it stopped saving one.
        self.assertIn("File ▸ Save As", self.procmon)
        self.assertIn(".pml", self.procmon.lower())
        # The negative, on the list §8 really carried. A loosening that let
        # the old `-marks.txt` through would be a green test; this is what
        # makes it red instead.
        marks_file = "evidence/ec-watch/<date>-gpu-door-07c4-07d7-marks.txt"
        self.assertEqual(
            unaccounted_artifacts(self.artifacts + [marks_file], self.cmd_paths,
                                  HUMAN_SAVED_SUFFIXES),
            [marks_file])

    def test_section_4a_and_section_8_agree_where_the_marks_live(self):
        # §4a.2 and §8 both answer "where are this run's marks", and they
        # answered differently for as long as §8's marks file was in the text
        # -- §4a said paper or a text file, §8 named a committed one, and
        # neither mentioned the other. Both now point at the CSV's `MARK`
        # rows, so neither can drift onto a second place alone.
        for name, section in (("§4a", self.procmon), ("§8", self.where)):
            self.assertIn("`MARK` rows", section,
                          f"{name} must name the CSV's MARK rows as where the "
                          "marks live")
        # The negative is on a filename shape and not on the word: both
        # sections say "marks" throughout, and so does the clause in §8 that
        # records why there is no marks file. What must not come back is a
        # marks *file*, which is the artifact with no producer.
        for name, section in (("§4a", self.procmon), ("§8", self.where)):
            self.assertNotIn("-marks", section, f"{name} names a marks file")
        self.assertFalse([p for p in self.artifacts if p.endswith(".txt")],
                         f"§8 lists a text artifact: {self.artifacts}")

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


class FailingEc(FakeEc):
    """`FakeEc`'s sweeps, with an EC read failing part way through.

    After the baseline and one sweep that moves a byte, so the capture holds
    real rows before the one that says the run stopped: a failure on the
    opening read would leave a capture with nothing in it and would say
    nothing about a run that stopped *part way through*, which is the shape
    the row exists for.
    """

    def read(self, addr):
        if self._reads >= len(ADDRS) * 2:
            raise watch.EcError("DeviceIoControl failed")
        return super().read(addr)


class EarlyExitRowTests(unittest.TestCase):
    """The `#` row this writes when a run stops, and the one it never writes.

    Two ends of one gap, and neither is worth anything alone: a capture that
    cannot carry the row is a row no reader will ever place, and a reader that
    cannot see it is a grader that grades every stopped run as a finished one.
    Both are exercised offline -- the writer against the same faked `ecrw`
    every other case in this suite uses -- so nothing here is a statement
    about the machine or about a laptop that has not been near it.
    """

    def run_watch(self, ec):
        """rc, and the rows of the file the run leaves behind.

        `marked` is set up front so `FakeEc`'s `at_last_sweep` wait is
        released at once: these cases pass no `--mark`, so nothing else would
        set it and every run would spend five seconds waiting for a mark that
        was never going to be typed.
        """
        ec.marked.set()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            with patch.object(watch, 'Ec', lambda: ec), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                rc = watch.main(['--interval', '0', '--csv', str(out)])
            # Read inside the directory, and after `main` has returned, so what
            # is checked is the file the run leaves rather than one this test
            # wrote: the sink is closed by the tool's own `finally` on this
            # path exactly as on the Ctrl-C one, and a row written after that
            # close would not be in it.
            return rc, out.read_text().splitlines()

    def test_the_tag_is_the_phrase_the_grader_reads(self):
        # The drift guard, and the twin of the one `manual_fan_ctrl_probe.py`'s
        # `--self-test` carries for its own copy of the same phrase. Two files
        # in different trees still cannot share a constant -- a tool that
        # imported the grader would import its whole capture reader with it --
        # so this equality is the only thing holding them together, and a
        # drifted tag is not a wrong-looking string: it is a reader that
        # matches no stopped capture, and a capture of a crashed run that
        # grades green. `grader.fan` is `grade_0751_isolation`, the module the
        # phrase was transcribed from.
        self.assertEqual(watch.EARLY_EXIT_TAG, grader.fan.EARLY_EXIT_TAG)

    def test_an_ec_error_mid_sweep_writes_the_row(self):
        rc, rows = self.run_watch(FailingEc())
        self.assertEqual(rc, 1)
        early = [r for r in rows if r.startswith(watch.EARLY_EXIT_TAG)]
        self.assertEqual(len(early), 1, rows)
        # Stamped, because a row that says *that* a run ended and not *when*
        # cannot be placed against a window; and naming the exception, because
        # that field is there for whoever opens the file. The tool's own name
        # rather than `__main__`, which is what the run an operator takes at
        # the box would otherwise write.
        self.assertIn(',gpu_block_watch: EcError: DeviceIoControl failed',
                      early[0])
        # And the rows the sweep really wrote are still in the file, ahead of
        # it: the row says the run stopped part way through, not that it never
        # ran. This is the control for a writer that got the tag right and
        # dropped everything else.
        self.assertIn(f'0x{ACPI:04X},0x00,0x37', '\n'.join(rows))

    def test_the_row_the_writer_writes_is_one_the_grader_reads(self):
        # The two ends of the tag in one run, which is the only assertion here
        # that covers a *row* rather than a constant: a writer and a reader
        # agreeing on the tag and disagreeing on the row -- the stamp in the
        # wrong field, a reason swallowed by the CSV quoting -- is the shape
        # this catches, and it is checked through the grader's own reader over
        # the file this writer actually produced.
        ec = FailingEc()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            ec.marked.set()
            with patch.object(watch, 'Ec', lambda: ec), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                watch.main(['--interval', '0', '--csv', str(out)])
            found = grader.fan.read_early_exits(str(out))
        self.assertEqual(len(found), 1, [r.source for r in found])
        # Carrying a timestamp this repository's own `parse_ts` reads, which
        # is the difference between a row that withholds a window and a row
        # that refuses the whole run. This capture has no marks, so an
        # unreadable stamp would come back refused rather than placed; the
        # timestamp is what separates the two, and the case below for a placed
        # row is where that is spent.
        self.assertIsNotNone(found[0].ts,
                             "the row carries no readable timestamp")
        self.assertIn('EcError: DeviceIoControl failed', found[0].reason)

    def test_a_keyboard_interrupt_writes_no_row(self):
        # `FakeEc` ends every run this suite drives with a `KeyboardInterrupt`,
        # so this is the case the capture an operator gets when they press
        # Ctrl-C after the last action has been marked -- which §3 calls the
        # right way to end a run that finished. A row here would put "the run
        # ended early" on every successful door capture, which is §4c's shape
        # with a different cause: a method reporting an absence as a fact.
        # Asserted so that a later "make it match the probe's BaseException"
        # fails here rather than passing for a fix.
        rc, rows = self.run_watch(FakeEc())
        self.assertEqual(rc, 0)
        self.assertEqual([r for r in rows if r.startswith('#')], [], rows)
        # Not absent because nothing was written at all: the change rows the
        # sweep did write are the control for that.
        self.assertIn(f'0x{ACPI:04X},0x00,0x37', '\n'.join(rows))


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
        # parser written for this file. The mark row's fifth field is
        # `ec_watch.Marker`'s provenance column, and this tool constructs
        # `Marker(sink)` with nothing to put in it, so it is present and empty:
        # "this process held no --label-vocab", which is not what a four-field
        # row would say.
        self.assertEqual(rows[0], 'ts,addr,old,new,provenance')
        self.assertEqual([r.split(',', 1)[1] for r in rows[1:]],
                         [f'0x{ACPI:04X},0x00,0x37',
                          'MARK,,gpu tgp 115W->130W,',
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
