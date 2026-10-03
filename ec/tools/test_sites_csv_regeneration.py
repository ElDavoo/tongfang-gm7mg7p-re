#!/usr/bin/env python3
"""Whether each committed `*-sites.csv` is still what the firmware image says it is.

Every one of these tables is the product of one command over
`ec/firmware/GMxMGxx_11.800`, and the page above each one prints that command
so a reader can re-run it. What none of them did was re-run it in CI, so the
claim each page rests on -- that the table is the map of the addresses it says
it is -- rested on a transcript. This suite re-derives the tables from the
committed image and compares.

**The gap this closes, and the level it is at.** Other suites do read these
files, and they are worth naming so a reader does not take this suite for the
first: `test_walk_budget_census.py` walks every committed `access` cell of the
tables in `walk_budget_census.TABLES` back through `classify()`,
`test_dptr_rebuild_forms.py` does the same for `terminator` over its own `SIX`,
`check_site_census.py` holds the `census` column, and
`test_gpu_block_watch.py` reads a census of its own. What every one of those
does is iterate the rows **already in the file** and re-derive a cell of each,
so a row that is not there is not iterated. A few suites go further and
regenerate a table whole rather than re-derive a cell of it --
`test_trace_xdata_refs_usage.py`, `test_0741_bit7_chain.py` and
`test_walk_budget_census.py` each hold one by byte comparison, and the write-up
names the table each covers. Every other table was held, cell by cell, to a row
set nothing checked.

**`region` is the cell none of the cell-wise ones derives.** `classify()` says
what a window did and `walk_why()` says why the window ended; neither says
which image a site is in. Measured with this suite held out of the tree, a
relabelled `region` is therefore noticed only where it happens to move
something another check looks at -- a population that check counts, or, where a
suite regenerates that table, a difference among the compared bytes -- and in
`ec-0x07d1-sites.csv` by nothing at all. A deleted or added row is caught too,
but by a count and not by a re-derivation --
`test_walk_budget_census.py`'s `ReCutTests` compares the row count against a
pinned commit. `docs/findings/sites-csv-regeneration.md` carries the measured
matrix, per table and per mutation.

**Addresses are frozen here as test data, not read back from the file.** That
is the whole design, and it is not a detail. Deriving the address list from
the committed CSV would be circular: a row dropped from the file drops from
the regeneration too, and the comparison passes on the file with the row
missing. `TABLES` below is this suite's own statement of which addresses each
committed file is the map of, so "that file describes *these* addresses" is a
claim something checks rather than something the file says about itself.

**Order is load-bearing, and not only because the tool groups by it.**
`csv_table()` emits an address's sites in the order it gave them, so a
regenerated table is a function of the address list's order. `xdata-1c3x-` and
`xdata-086x-dispatch-sites.csv` are committed `0x1C39` before `0x1C12` /
`0x0860`, and reproduce in exactly that order and not in sorted order --
`xdata-1c3x-consumers-sites.csv` was checked both ways, and sorting its frozen
list turns that table red on arrival. So `TABLES` keeps the committed order and
a case asserts it, in both directions: sorted is not accepted as a synonym.

**`--check` is deliberately not what this calls.** `main()` loads the census
map whenever `--check` is given, which appends a `census` column none of these
tables but one carries, so a `--check` run is red on the committed data before
any real difference -- a check that is always red is one nobody reads, and
worse than none. `csv_table()` is the same comparison one function lower, with
the census map passed only for the table that has the column.

**What a green run means, and does not.** It means this method found the same
sites, in the same order, with the same cells, as the committed file records.
It does not mean the enumeration is complete: a site reached through a computed
DPTR, or through any form `scan_refs.py`'s blind spot covers, has no row here
and would have none in a regenerated table either. "Not found by this method,
never absent" is the phrasing in `trace_xdata_refs.py`'s module docstring and in
`ec/annotations/registers.yaml`, and it is the honest reading of a green run.

One table's `census` column is not image-derived at all -- it is a hand-typed
reading of the decompile, kept beside the sweep by
`../tools/check_site_census.py` -- so the byte comparison covers that column as
*rendered*, not as derived. A red run there is a disagreement about the
correspondence files first and only about the image second.

No hardware, no Ghidra, no network, no Windows: the firmware is the committed
256 KiB image and the tables are the committed `*.csv` files.
"""
import collections
import csv
import io
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# trace_xdata_refs imports disasm8051 and access_cell_corrections by bare
# module name, the way its sibling suites do.
sys.path.insert(0, str(HERE))
import trace_xdata_refs as T          # noqa: E402

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
ANNOT = HERE.parent / "annotations"

# Which committed table is the map of which addresses, in the order the
# committed file uses them, and the two optional columns it was cut with.
#
# `census` is `load_census_map()`'s dict rather than a derivation from the
# image, so it is passed for the one table that carries the column and omitted
# for the rest -- passing it anywhere else appends a column the committed file
# does not have and the comparison is red for a reason that has nothing to do
# with the firmware. Both flags are here rather than read off the committed
# header because reading them off the file would let a file that lost its
# `terminator` column decide that it no longer needs one; `OptionalColumnsTests`
# is what holds them, in the other direction.
TABLES = {
    "ec-07c4-07d5-sites.csv": (
        ["0x07C4", "0x07D3", "0x07D4", "0x07D5"], True, False),
    "ec-07d6-07d7-sites.csv": (
        ["0x07D6", "0x07D7"], True, False),
    "ec-09e9-09eb-sites.csv": (
        ["0x09E9", "0x09EA", "0x09EB"], False, False),
    "ec-0x07c5-sites.csv": (
        ["0x07C5"], True, False),
    "ec-0x07d0-sites.csv": (
        ["0x07D0"], True, False),
    "ec-0x07d1-sites.csv": (
        ["0x07D1"], True, False),
    "ap-oem-0741-bit7-sites.csv": (
        ["0x0741"], True, False),
    "manual-fan-ctrl-0751-sites.csv": (
        ["0x0751"], True, False),
    "xdata-0400-045f-sites.csv": (
        ["0x%04X" % a for a in (
            0x0400, 0x0401, 0x0402, 0x0403, 0x0404, 0x0408, 0x040A, 0x040C,
            0x040E, 0x0410, 0x0418, 0x041C, 0x0420, 0x0424, 0x0426, 0x0428,
            0x0429, 0x042A, 0x042C, 0x042F, 0x0432, 0x0433, 0x0434, 0x0435,
            0x0436, 0x0437, 0x0438, 0x0439, 0x043A, 0x043B, 0x043C, 0x043D,
            0x043E, 0x043F, 0x0440, 0x0442, 0x0443, 0x0448, 0x0449, 0x044B,
            0x044C, 0x044F, 0x0450, 0x0451, 0x0452, 0x0454, 0x0455, 0x0456,
            0x0457, 0x0458, 0x0459, 0x045A, 0x045B, 0x045C, 0x045D, 0x045E,
            0x045F)], True, False),
    "xdata-086x-dispatch-sites.csv": (
        ["0x0860", "0x0862", "0x0865", "0x0866", "0x0867", "0x0868", "0x0869",
         "0x086A", "0x086B", "0x086D", "0x086E", "0x1C39", "0x1C3A", "0x1F01",
         "0x1F07"], False, True),
    # Committed order, and deliberately not sorted: `csv_table()` emits each
    # address's sites where the caller put the address, so this table is
    # 0x1C39's rows, then 0x1C3A's, then 0x1C12's, and a sorted list produces
    # a different table. `AddressOrderTests` holds the difference rather than
    # leaving it in a comment.
    "xdata-1c3x-consumers-sites.csv": (
        ["0x1C39", "0x1C3A", "0x1C12", "0x1C13", "0x1C14", "0x1C36", "0x1C37",
         "0x1C38", "0x1C01", "0x1C02", "0x1C03"], False, False),
}

OPTIONAL_COLUMNS = ("census", "terminator")


def firmware():
    """The image, read once and kept.

    `Path.read_bytes()` and cached, for `test_walk_budget_census.py`'s reason:
    each case re-walks a few thousand sites, and re-reading the file per case
    would be the slowest thing in the suite for no gain.
    """
    if not firmware._cached:
        firmware._cached = FIRMWARE.read_bytes()
    return firmware._cached


firmware._cached = None


def census_map():
    """The hand-typed correspondence map, read once.

    Loaded lazily rather than at import because only one of the tables asks
    for it, and a suite that reads a directory of correspondence files to check
    the tables that have no `census` column is doing work whose failure would
    name a file that has nothing to do with any of them.
    """
    if not census_map._cached:
        census_map._cached = T.load_census_map()
    return census_map._cached


census_map._cached = None


def pd_verified():
    """Whether the dump still carries the PD image's marker, as `main()` asks.

    Read through `T.PD_MARKER` rather than with a literal of its own, and
    checked rather than assumed: a dump whose `0x20000` region is something
    else labels those sites `unknown`, every `pd-image` row becomes `unknown`,
    and four of the tables below go red for a reason that is about the image
    the file was cut from and not about the committed one.
    """
    off, magic = T.PD_MARKER
    image = firmware()
    return image[off:off + len(magic)] == magic


def base_columns():
    """The header `csv_table()` writes before either optional column.

    Read out of a real regeneration rather than written out as a literal here,
    so the schema this suite recognises as `trace_xdata_refs.py`'s cannot drift
    from the tool. A literal would be a second copy of a list the tool already
    owns, and a tool that grew a column would leave the scan below quietly
    matching less and less.
    """
    if not base_columns._cached:
        table, _ = T.csv_table(firmware(), ["0x07D0"], pd_verified())
        base_columns._cached = next(csv.reader(io.StringIO(table, newline="")))
    return base_columns._cached


base_columns._cached = None


def text_of(name):
    """A committed table's bytes as text, newlines untranslated.

    `newline=""` and not `read_text()`, for `check_table()`'s reason: these
    files carry the csv module's own CRLF terminator, and universal-newline
    translation would hand back different bytes from the ones `--check` and this
    suite compare, reporting a difference on every row of every run.
    """
    with open(ANNOT / name, newline="") as f:
        return f.read()


def regenerate(name):
    """`(generated table, census offsets with no correspondence row)`, for the
    committed table `name` and the frozen addresses above it.

    Cached per table, because five of the cases below want the same
    regeneration and the walk behind it is the suite's cost: `0x07D6`-`0x07D7`
    and `xdata-0400-045f` are a few hundred sites each, re-walked once per
    case. The cache is keyed on the file name and nothing else, so a case that
    mutates the *committed* file still compares against a freshly derived
    table -- which is the whole point of the mutation cases.
    """
    if name not in regenerate._cached:
        addrs, terminator, census = TABLES[name]
        regenerate._cached[name] = T.csv_table(
            firmware(), addrs, pd_verified(),
            census_map() if census else None, terminator=terminator)
    return regenerate._cached[name]


regenerate._cached = {}


def rows_of(text):
    """A CSV table's text as a list of row tuples, header first.

    Tuples rather than lists because `describe_difference()` counts rows, and
    `collections.Counter` needs them hashable. The order is the file's and is
    not touched: this is a faithful parse, and the order is one of the things
    under test.
    """
    return [tuple(row) for row in csv.reader(io.StringIO(text, newline=""))]


def offset_of(row) -> str:
    """A row's `file_offset` cell, or the whole row if it has no such cell.

    The `file_offset` is what names a site, so it is what a failure message
    quotes. A row too short to have one is itself the difference being
    reported, and indexing it blindly would raise `IndexError` from inside the
    function that exists to explain the failure -- so a short row falls back to
    its own text rather than taking the report down with it.
    """
    return row[1] if len(row) > 1 else f"(short row: {list(row)})"


def describe_difference(committed: str, generated: str) -> str:
    """One line saying how the committed table and this run's differ.

    **Order against content, because they are different failures.** `csv_table()`
    emits rows grouped by address and in address order, so a regenerated table
    that holds the same rows in a different order is a re-cut with the address
    list in a different order, while a table missing a row is a site that is no
    longer there or was never there. Both are red; they are not the same red,
    and a reader who is told "the tables differ" has to diff them to learn
    which. The multiset test is over parsed rows rather than over text, so a
    quoting or line-terminator difference is not mistaken for a content one.
    """
    if committed == generated:
        return ""
    want, got = rows_of(committed), rows_of(generated)
    if want == got:
        return ("the rows parse the same but the bytes differ -- a line "
                "terminator or quoting difference, not a content one")
    if collections.Counter(want) == collections.Counter(got):
        return ("the same rows in a different order (an ordering artefact, not "
                "a site that moved): committed order starts "
                f"{[offset_of(r) for r in want[1:3]]}, this run's "
                f"{[offset_of(r) for r in got[1:3]]}")
    missing = collections.Counter(want) - collections.Counter(got)
    extra = collections.Counter(got) - collections.Counter(want)
    parts = []
    for label, delta in (("only in the committed file", missing),
                         ("only in this run", extra)):
        for row, n in sorted(delta.items()):
            parts.append(f"{label}: {offset_of(row)} x{n}" if n > 1
                         else f"{label}: {offset_of(row)}")
    if len(parts) > 6:
        parts = parts[:6] + [f"... and {len(parts) - 6} more"]
    return ("the row sets differ -- " + "; ".join(parts))


def committed_sites_tables():
    """Every `*.csv` under `ec/annotations` whose header is this tool's schema.

    The scan, rather than `TABLES` alone, because the claim a reader wants from
    this suite is "the tables `trace_xdata_refs.py` produced are held", and a
    hand-kept list cannot say what it does not know about: a table cut by
    another issue with `--csv` and committed under the same header would simply
    not be checked. Matching on the base columns `csv_table()` writes plus a
    subset of the two optional ones is what tells `flow-follow-none-sites.csv`
    (a `walk_flow_follow.py` schema) and `boot-xdata-sites.csv` (a
    `scan_refs.py` one) apart from a table this tool wrote. A file that cannot
    be read is skipped rather than raised on, the same way
    `trace_xdata_refs.py`'s own `committed_terminator_tables()` treats it: this
    is a coverage claim, and a coverage claim must not be what fails a run for
    an unrelated reason.
    """
    found = {}
    base = base_columns()
    for path in sorted(ANNOT.glob("*.csv")):
        try:
            with open(path, newline="") as f:
                header = next(csv.reader(f), None)
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
        if not header or header[:len(base)] != base:
            continue
        if set(header[len(base):]) - set(OPTIONAL_COLUMNS):
            continue
        found[path.name] = header[len(base):]
    return found


class RegenerationTests(unittest.TestCase):
    """Each committed table, byte for byte, from the committed image.

    One `subTest` per table so a failure names the file rather than stopping
    the run at the first: a re-cut that moved two tables should say so twice.
    """

    def test_every_committed_table_regenerates_from_the_firmware(self):
        for name, (addrs, terminator, census) in sorted(TABLES.items()):
            with self.subTest(table=name):
                self.assertTrue(
                    addrs,
                    f"{name} has no frozen address list, so this case would "
                    "pass on an empty regeneration")
                generated, _ = regenerate(name)
                committed = text_of(name)
                difference = describe_difference(committed, generated)
                self.assertEqual(
                    difference, "",
                    f"{name} does not reproduce from {FIRMWARE.name} for "
                    f"{', '.join(addrs)}"
                    + (" --terminator-column" if terminator else "")
                    + (" --census-column" if census else "")
                    + f": {difference}\n"
                    "the file is the product of the command its own page "
                    "prints, so regenerate rather than edit; if the site is "
                    "really gone, say so in the write-up that says so")


class NonVacuousTests(unittest.TestCase):
    """The comparisons above have to be able to fail, and to fail on content.

    A regeneration that produced nothing would fail the byte comparison for the
    wrong reason -- it would look like a disagreement between two files when it
    is the tool that produced neither. So the population is stated from the
    tool's side here, and the two mutations that no other suite notices are run
    against the comparison itself, so the predicate is not merely present but
    known to reject.
    """

    def test_no_table_regenerates_to_nothing(self):
        for name in sorted(TABLES):
            with self.subTest(table=name):
                rows = rows_of(regenerate(name)[0])
                self.assertGreater(len(rows), 1,
                                   f"{name} regenerated with no data rows")
                self.assertTrue(all(row and row[0] for row in rows[1:]),
                                f"{name} regenerated a row with no addr cell")

    def test_every_frozen_address_has_at_least_one_row(self):
        # The frozen list is a claim about which addresses a file maps, so an
        # address in it that produces no row is a claim this run cannot
        # support -- a typo in the list, or an address whose sites the walk
        # stopped reaching. Either way it is not something to discover from a
        # passing byte comparison.
        for name, (addrs, _, _) in sorted(TABLES.items()):
            with self.subTest(table=name):
                seen = {row[0] for row in rows_of(regenerate(name)[0])[1:]}
                self.assertEqual(
                    sorted(set(addrs) - seen), [],
                    f"{name}: frozen address(es) with no regenerated row")

    def test_a_deleted_row_is_caught_by_this_comparison(self):
        # The teeth, on the committed data rather than a fixture. A copy of a
        # real table with one data row taken out has to be reported as
        # differing, and by the content branch of `describe_difference()`
        # rather than the ordering one -- a row that is gone is not an
        # artefact, and a reader told it was an artefact would go looking in
        # the wrong place.
        #
        # Re-emitted through the csv writer rather than spliced as text, so
        # the mutated copy differs from the committed file in exactly the one
        # row and not in quoting: a splice on `,` would also mangle every
        # `window` cell that holds a comma, and the case would then be
        # asserting that a mangled file is caught, which is a different claim.
        name = "ec-0x07d1-sites.csv"
        rows = rows_of(text_of(name))
        dropped = rows[1][1]
        buf = io.StringIO(newline="")
        csv.writer(buf).writerows(rows[:1] + rows[2:])
        mutated = buf.getvalue()
        self.assertNotEqual(mutated, text_of(name))
        difference = describe_difference(mutated, regenerate(name)[0])
        self.assertIn("row sets differ", difference)
        self.assertIn("only in this run", difference)
        self.assertIn(dropped, difference)
        self.assertNotIn("ordering artefact", difference)

    def test_a_relabelled_region_is_caught_by_this_comparison(self):
        # The quiet one the issue names: a `pd-image` row read as `bank0`
        # credits the main EC with a site it does not have. Every other suite
        # re-derives a cell from a row that is still there -- `classify()` and
        # `walk_why()` say nothing about which image a site is in, so a
        # `region` cell is exactly the cell none of them can check.
        #
        # **This table, and not `ec-0x07d0-sites.csv`.** A `region` relabel in
        # the `0x07D0` table is caught, but by `test_pd_site_clusters.py` and
        # only because the cluster populations stop matching; nothing read the
        # cell. `docs/findings/sites-csv-regeneration.md` carries the measured
        # matrix, and this row is the one it marks as caught by nothing.
        name = "ec-0x07d1-sites.csv"
        rows = rows_of(text_of(name))
        at = next(i for i, row in enumerate(rows[1:], 1) if row[2] == "pd-image")
        region = rows[0].index("region")
        buf = io.StringIO(newline="")
        writer = csv.writer(buf)
        for i, row in enumerate(rows):
            writer.writerow([*row[:region], "bank0", *row[region + 1:]]
                            if i == at else row)
        mutated = buf.getvalue()
        self.assertNotEqual(mutated, text_of(name))
        difference = describe_difference(mutated, regenerate(name)[0])
        self.assertIn("row sets differ", difference)
        self.assertIn(rows[at][1], difference)


class AddressOrderTests(unittest.TestCase):
    """The frozen order is the committed order, and it is not interchangeable.

    `csv_table()` groups by the order the addresses were given, so a sorted
    list is a different table rather than a tidier one. These cases say so
    against a real table, because a comment claiming it is a comment.
    """

    def test_a_sorted_address_list_is_not_accepted_for_a_committed_table(self):
        name = "xdata-1c3x-consumers-sites.csv"
        addrs, terminator, census = TABLES[name]
        self.assertNotEqual(addrs, sorted(addrs),
                            f"{name} is no longer committed out of order, so "
                            "the frozen list and this case's claim are both "
                            "out of date")
        sorted_table, _ = T.csv_table(firmware(), sorted(addrs), pd_verified(),
                                      census_map() if census else None,
                                      terminator=terminator)
        self.assertNotEqual(sorted_table, text_of(name))
        self.assertIn("ordering artefact",
                      describe_difference(text_of(name), sorted_table))

    def test_the_committed_tables_address_order_is_the_one_the_file_uses(self):
        # The same claim from the other side: the regeneration's own `addr`
        # column has to run in the frozen order, grouped, with no address
        # appearing after one that follows it. A frozen list that had been
        # sorted -- or that had gained an address in the wrong place -- fails
        # here rather than only in the byte comparison, where the failure text
        # would be a diff to read.
        for name, (addrs, _, _) in sorted(TABLES.items()):
            with self.subTest(table=name):
                seen = []
                for row in rows_of(regenerate(name)[0])[1:]:
                    if not seen or seen[-1] != row[0]:
                        seen.append(row[0])
                self.assertEqual(
                    seen, addrs,
                    f"{name}: this run's addr column runs {seen}, not the "
                    f"frozen order {addrs}")


class OptionalColumnsTests(unittest.TestCase):
    """The two optional columns are held to what the committed header carries.

    `TABLES` says which table was cut with `--terminator-column` and which with
    `--census-column`. If a committed header changed, the frozen flags and the
    file would disagree, and the byte comparison would report it as a wall of
    `-`/`+` lines with nothing saying which column moved. These cases name it.
    """

    def test_each_frozen_flag_matches_the_committed_header(self):
        for name, (_, terminator, census) in sorted(TABLES.items()):
            with self.subTest(table=name):
                header = T.committed_columns(str(ANNOT / name)) or []
                self.assertEqual("terminator" in header, terminator, name)
                self.assertEqual("census" in header, census, name)

    def test_every_committed_table_of_this_schema_is_covered(self):
        # The coverage direction `TABLES` alone cannot state. A table cut by
        # another issue with `--csv` and committed under this header would
        # otherwise be silently unchecked, which is the gap this suite exists
        # to close applied to itself.
        found = committed_sites_tables()
        uncovered = sorted(set(found) - set(TABLES))
        self.assertEqual(
            uncovered, [],
            f"{len(uncovered)} committed table(s) carry trace_xdata_refs.py's "
            f"schema and are not in TABLES: {uncovered}. Add the address list "
            "they were cut with, or say in a write-up why they are not "
            "reproducible this way.")
        # And the other direction: a frozen entry with no file is a typo, not a
        # case that silently passes by finding nothing to compare.
        self.assertEqual(sorted(set(TABLES) - set(found)), [])


class CensusColumnTests(unittest.TestCase):
    """The one table whose `census` column is a reading, not a derivation.

    `xdata-086x-dispatch-sites.csv`'s `census` column is typed by hand from
    the decompiled C and held by `../tools/check_site_census.py`; it is not
    image-derived and this tool never derives it. So the byte comparison over
    that table covers the column as rendered, and this case says which map it
    was rendered from, so a red run there is read as what it is.
    """

    def test_the_census_column_comes_from_the_committed_correspondence_files(self):
        name = "xdata-086x-dispatch-sites.csv"
        addrs, terminator, census = TABLES[name]
        self.assertTrue(census, f"{name} is expected to carry a census column")
        self.assertFalse(terminator)
        _, unmapped = regenerate(name)
        # Every cell came from a file, not from the `not recorded` fallback.
        # A site with no correspondence row renders that token, which is a
        # fact about the map rather than about the image, so a table full of
        # them would pass the byte comparison while asserting nothing.
        self.assertEqual(dict(unmapped), {},
                         f"{name} has sites with no row in the correspondence "
                         "files, so its census column is the fallback token "
                         "rather than a reading")
        rows = rows_of(text_of(name))
        column = rows[0].index("census")
        self.assertEqual(column, len(rows[0]) - 1,
                         f"{name}: the census column is no longer last, so the "
                         "cell read below would be the wrong one")
        cells = {row[column] for row in rows[1:]}
        self.assertNotIn("not recorded", cells)

    def test_passing_the_map_appends_a_column_the_other_tables_do_not_carry(self):
        # The reason the flag is per-table rather than global, stated against
        # the tool: hand `csv_table()` the map for a table whose committed file
        # has no `census` column and the header grows one, so the comparison
        # goes red on a column the file has no room for. Asserted rather than
        # assumed, because the failure it prevents is the exact one this suite
        # would otherwise be reporting against itself.
        for name, (addrs, terminator, census) in sorted(TABLES.items()):
            if census:
                continue
            with self.subTest(table=name):
                # `without` is the cached regeneration -- the same one
                # `RegenerationTests` compares against the file -- so the two
                # cases cannot disagree about what the table is.
                without, _ = regenerate(name)
                with_map, _ = T.csv_table(firmware(), addrs, pd_verified(),
                                          census_map(), terminator=terminator)
                self.assertNotIn("census", rows_of(without)[0])
                self.assertIn("census", rows_of(with_map)[0])
                # And the row that reproduces the file is the one without it,
                # which is what makes the flag load-bearing rather than tidy.
                self.assertEqual(without, text_of(name))


if __name__ == '__main__':
    unittest.main()