#!/usr/bin/env python3
"""Cases for `xdata_frame_credit.py` (issue #1360).

The tool's own `--self-test` carries the named claims and the two refusals, and
this drives it. What is here is the half a self-test cannot be: the tool's
*shapes* held directly, so a collapse that had quietly stopped following a chain
to its outermost frame, a refusal that had started picking a container, or a
derivation that had begun reading the published `functions` column instead of
the census, is caught by a named case rather than by a figure moving.

**No count of the tree is asserted anywhere in this file.** The population moves
as the export moves, and a suite that pinned it would go red on a merge that
added a row and tell the implement stage to fix a correct tool. What is
asserted is the claim and the relation: these named rows collapse onto these
named frames, these two shapes are refused, a chain resolves to its *outermost*
frame rather than its direct container, the committed columns encode the stated
reading, and both modes write nothing.

**The refusals are held on a fixture as well as on the committed tree.** A case
that depends on the export still carrying the mutually nested pair is a case
that stops testing anything the day a rebuild drops it, and silently passes in
the meantime if the refusal is inverted. `TheFixtureTree` writes the edge sets
out by hand -- a one-step chain, a two-step chain, a three-row ring, a row held
by two, a self-loop -- and runs `frame_of()` over them, so each rule is held
where the whole shape is visible rather than only where the export happens to
exercise it. No `tempfile`: `frame_of()` takes an edge dict, so a fixture tree
would be a directory this suite would then have to keep in sync.

Everything here reads committed files. No Ghidra, no hardware, no Windows, no
network. No register was read and no machine was observed.
"""
import contextlib
import csv
import hashlib
import io
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import nested_frame_census  # noqa: E402
import xdata_frame_credit as xfc  # noqa: E402
import xdata_register_map as xrm  # noqa: E402

# The two committed CSVs a silent flip would change, and the index. Digests
# rather than mtimes: a write that restores the content would still be a write,
# and "writes nothing" is the claim.
GUARDED = (xrm.OUT_REGISTERS, xrm.OUT_CLUSTERS)


def digests():
    """{path: sha256} for the files the tool must not touch."""
    return {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
            for p in GUARDED}


def label(key):
    """A function key as the report prints it, for a failure message."""
    return f"{key[0]}:0x{key[1]}"


class TheSelfTest(unittest.TestCase):
    """The tool's own self-test, which is where the named claims live."""

    def test_it_passes(self):
        # The transcript goes to a buffer rather than to this suite's own
        # output: the exit code is the whole of the assertion, and a reader
        # running the suite should not have to find this suite's result
        # underneath the tool's.
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = xfc.self_test()
        self.assertEqual(rc, 0, buf.getvalue()[-2000:])


class TheRefusals(unittest.TestCase):
    """Two shapes have no outermost frame, and both are refused.

    The load-bearing negative case of the whole change: a collapse that picked
    *a* container where there is no single one would move real credit in the
    committed columns' direction while claiming a reading it cannot support.
    """

    def test_a_mutually_nested_pair_is_refused_rather_than_collapsed(self):
        # Each address falls inside the other's listing span and neither span
        # contains the other, so the chain 0x6A02 -> 0x6D46 -> 0x6A02 never
        # terminates. `frame_of` returns the reason rather than the row it
        # happened to be standing on.
        edges = {("common", "6A02"): [("common", "6D46")],
                 ("common", "6D46"): [("common", "6A02")]}
        for key in edges:
            frame, reason = xfc.frame_of(key, edges)
            self.assertIsNone(frame, label(key))
            self.assertEqual(reason, "mutual-nesting", label(key))

    def test_a_row_inside_two_containers_is_refused(self):
        # "Its container" is not one row. The census's own docstring says the
        # two fall in *different* buckets, so picking either would be wrong
        # about the other.
        edges = {("common", "6B94"): [("common", "6A02"), ("common", "6D46")]}
        frame, reason = xfc.frame_of(("common", "6B94"), edges)
        self.assertIsNone(frame)
        self.assertEqual(reason, "several-containers")

    def test_a_refusal_is_never_also_a_collapse(self):
        # The two outputs partition the nested rows. An overlap would mean a row
        # both keeps its own credit and has it moved, which is the failure mode
        # the split exists to make impossible.
        collapse, refused = xfc.collapse_map(xfc.census_edges())
        self.assertFalse(set(collapse) & set(refused))

    def test_the_vocabulary_is_closed(self):
        # A refusal outside REFUSALS would be a shape the docstring does not
        # name and this file cannot explain -- which is the same closed-split
        # argument `nested_frame_census`'s own buckets make.
        _collapse, refused = xfc.collapse_map(xfc.census_edges())
        self.assertTrue(refused)
        for key, reason in refused.items():
            self.assertIn(reason, xfc.REFUSALS, label(key))

    def test_a_row_at_the_top_of_its_own_chain_is_not_a_refusal(self):
        # The outcome that must not be filed as one of the two refusals: a row
        # already at the top of its chain is its own frame, so it collapses to
        # nothing. `collapse_map` drops it from `refused` on this reason alone,
        # and a tool that filed it under a refusal name would report a shape it
        # has not met.
        frame, reason = xfc.frame_of(("common", "65A6"), {})
        self.assertIsNone(frame)
        self.assertEqual(reason, "already-outermost")
        collapse, refused = xfc.collapse_map({})
        self.assertEqual((collapse, refused), ({}, {}))

    def test_a_one_step_chain_resolves_to_its_container(self):
        # The ordinary case, so the refusals above have something to be a
        # contrast to. Keys are spelled as `bare(addr)` spells them -- four hex
        # digits, upper -- because these are the strings the census really
        # produces and a fixture in another shape would not be the same test.
        edges = {("bank1", "BA43"): [("bank1", "B98D")]}
        frame, reason = xfc.frame_of(("bank1", "BA43"), edges)
        self.assertEqual(frame, ("bank1", "B98D"))
        self.assertIsNone(reason)


class TheFixtureTree(unittest.TestCase):
    """The refusal rules over a tree built for them, not over the export's.

    Every case above that depends on the committed tree depends on the export
    *keeping* the shape that produced it. These do not: the edges are written
    out, so the rule is held where a reader can see all of it, and a rebuild
    that dropped the mutual pair would not quietly turn these cases vacuous.
    """

    def check(self, edges, key, want_frame, want_reason):
        frame, reason = xfc.frame_of(key, edges)
        self.assertEqual(frame, want_frame, f"{label(key)}: frame")
        self.assertEqual(reason, want_reason, f"{label(key)}: reason")

    def test_a_chain_resolves_to_its_outermost_frame(self):
        # The distinction the walk exists for: 0x6811 -> 0x6D46 -> 0x6A02 with
        # 0x6A02 held by nothing, so the frame is 0x6A02 and *not* the direct
        # container. A tool that stopped after one step would return 0x6D46 and
        # be wrong about every row two levels down, and would still be right
        # about every row one level down -- which is why this case is here.
        edges = {("common", "6811"): [("common", "6D46")],
                 ("common", "6D46"): [("common", "6A02")]}
        self.check(edges, ("common", "6811"), ("common", "6A02"), None)

    def test_a_one_step_chain_resolves_to_its_container(self):
        edges = {("common", "6209"): [("common", "65A6")]}
        self.check(edges, ("common", "6209"), ("common", "65A6"), None)

    def test_a_longer_cycle_is_refused_and_does_not_hang(self):
        # Three rows in a ring. The visited-set is what terminates this; a
        # depth limit would return whichever row it stopped on, which is a
        # plausible-looking frame and a wrong one.
        edges = {("p", "0001"): [("p", "0002")],
                 ("p", "0002"): [("p", "0003")],
                 ("p", "0003"): [("p", "0001")]}
        for key in edges:
            self.check(edges, key, None, "mutual-nesting")

    def test_a_row_is_never_its_own_container(self):
        # A self-loop is a cycle of one and is refused the same way, so a
        # malformed edge cannot make a row its own frame.
        self.check({("p", "0001"): [("p", "0001")]}, ("p", "0001"),
                   None, "mutual-nesting")

    def test_the_collapse_map_keeps_only_real_edges(self):
        collapse, refused = xfc.collapse_map(
            {("p", "0001"): [("p", "0002")],
             ("p", "0002"): [("p", "0001")],
             ("p", "0003"): [("p", "0001"), ("p", "0004")]})
        self.assertEqual(collapse, {}, "nothing here has a single outermost frame")
        self.assertEqual(set(refused),
                         {("p", "0001"), ("p", "0002"), ("p", "0003")})


class TheStatedReading(unittest.TestCase):
    """The committed columns encode the reading the docstring states.

    This is the by-facto half of the ruling. `xdata_register_map.py --check`
    already holds that a fresh generation matches the committed CSVs; what it
    cannot say is *which* reading the columns encode, because a tool that
    derived both the same way would match itself either way. This asserts the
    stated one on the committed tree.
    """

    @classmethod
    def setUpClass(cls):
        cls.groups, _names = xfc.read_census()
        cls.stated = xfc.rows_for(cls.groups)
        cls.committed = xfc.committed_columns()

    def test_the_tool_check_mode_passes(self):
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = xfc.check()
        self.assertEqual(rc, 0, buf.getvalue()[-2000:])

    def test_every_row_matches_on_all_three_columns(self):
        # The population is the tool's, not a table's, so this cannot go stale
        # in the way a row count would.
        self.assertTrue(self.stated)
        mismatched = [
            (xrm.hexaddr(addr), name)
            for addr in sorted(self.stated)
            for derived, name in xfc.COLUMNS
            if len(self.stated[addr][derived]) != self.committed[addr][name]]
        self.assertEqual(mismatched, [], f"{len(mismatched)} cell(s) disagree")

    def test_the_columns_are_the_ones_named(self):
        # A derivation that checked `refs` instead of `writers` would pass every
        # case above on a tree where the two happened to agree, so both halves of
        # each pair in COLUMNS are held: the derived name must be a key
        # `credit_of()` actually produces, and the CSV header must be a column
        # the committed file actually carries.
        derived_names = {derived for derived, _name in xfc.COLUMNS}
        self.assertEqual(derived_names, set(self.stated[0x036C]),
                         "COLUMNS names a derived column credit_of() does not "
                         "produce")
        with open(xfc.REGISTERS_CSV, newline="") as f:
            header = next(csv.reader(f))
        for _derived, name in xfc.COLUMNS:
            self.assertIn(name, header,
                          f"xdata-registers.csv has no `{name}` column")

    def test_a_derived_column_is_a_set_of_function_keys_not_a_count(self):
        # The shape the whole tool rests on: the derived value is the *set*, and
        # the column is its `len()`. If this were ever a count, the frame
        # reading could not be computed by remapping keys at all.
        addr = 0x036C
        self.assertIsInstance(self.stated[addr]["writers"], set)
        self.assertEqual(len(self.stated[addr]["writers"]),
                         self.committed[addr]["writers"])


class TheWriterTagTrap(unittest.TestCase):
    """The `[writer]` tag in the `functions` column is a role, not a record.

    It is the shape of a derivation that looks supported by the committed CSV
    and is not: counting those tags is the obvious way to recover `writers`
    from the published column without re-running the census, and it is wrong.
    `0x0491` is where it shows, because every one of that row's writers reaches
    it as `read+write` on a row that reads `write 0`.
    """

    def test_the_tags_under_count_0x0491_s_writers(self):
        derived = len(xfc.rows_for(xfc.read_census()[0])[0x0491]["writers"])
        self.assertGreater(xfc.writer_tags(addr=0x0491), 0,
                           "0x0491 carries [writer] tags; if it stopped doing "
                           "so, this case would pass for the wrong reason")
        self.assertLess(xfc.writer_tags(addr=0x0491), derived)

    def test_the_tags_do_not_reproduce_the_column_on_every_row(self):
        # Row by row, which is the shape a reader would actually try: for each
        # register row, do the tagged names account for the `writers` cell?
        reproduced = 0
        stated = xfc.rows_for(xfc.read_census()[0])
        with open(xfc.REGISTERS_CSV, newline="") as f:
            rows = list(csv.DictReader(f, strict=True))
        for row in rows:
            tags = sum(1 for cell in row["functions"].split("; ")
                       if cell and cell.rstrip().endswith("[writer]"))
            addr = int(row["addr"], 16)
            if tags == len(stated[addr]["writers"]):
                reproduced += 1
        self.assertGreater(len(rows), reproduced,
                           "the [writer] tags reproduce `writers` on every "
                           "committed row, so they are not the trap this file "
                           "names; re-derive before trusting this case")

    def test_the_tags_are_a_role_from_the_annotation_csv(self):
        # What the tag actually is, checked against its source rather than
        # against its effect: `ghidra-functions.csv` carries a `type`, and the
        # census counts a bucket per *access*, so a role cannot stand in for one.
        derived = xfc.rows_for(xfc.read_census()[0])[0x0491]["writers"]
        with open(nested_frame_census.ANNOTATIONS, newline="") as f:
            ann = list(csv.DictReader(f, strict=True))
        writers_typed = {("bank1", row["addr"].upper().removeprefix("0X"))
                         for row in ann if row.get("type") == "writer"}
        self.assertTrue(writers_typed & set(derived),
                        "no annotated writer on this row; the case above would "
                        "then pass because the tags vanished, not because they "
                        "under-count")


class TheWritesNothing(unittest.TestCase):
    """Every mode leaves the committed census byte-identical.

    This tool's whole claim is that the question has an answer without the
    answer becoming the census -- the same contract
    `xdata_register_map.py --collapse-co-readings` keeps. Asserting the digests
    is the whole of it, because no mode here takes an output path: there is
    nothing to mock, and a mode that grew one would have to grow the guard with
    it. The modes are also driven through `main()` rather than called directly,
    so the argparse half is exercised and a flag that stopped dispatching is
    caught here rather than by whoever runs the command next.
    """

    def run_mode(self, argv):
        """`main(argv)` with both streams captured, as `(code, out, err)`."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = xfc.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_all_three_modes_leave_the_census_untouched(self):
        before = digests()
        for argv in ([], ["--check"], ["--self-test"]):
            with self.subTest(mode=argv or ["(default)"]):
                code, _out, _err = self.run_mode(argv)
                self.assertEqual(code, 0)
                self.assertEqual(digests(), before,
                                 f"{argv} changed a committed census CSV")

    def test_every_mode_exits_zero(self):
        # The default report is the one a reader runs first; a mode that failed
        # on the committed tree would leave the ruling looking unmeasured.
        for argv in ([], ["--check"], ["--self-test"]):
            with self.subTest(mode=argv or ["(default)"]):
                code, out, _err = self.run_mode(argv)
                self.assertEqual(code, 0)
                self.assertTrue(out.strip(), f"{argv} printed nothing on stdout")

    def test_the_report_says_on_stderr_that_it_wrote_nothing(self):
        # The claim has to be made where a reader running the command sees it,
        # and stderr is where `collapse_co_readings()` puts it.
        _code, _out, err = self.run_mode([])
        self.assertIn("was written", err)

    def test_no_mode_takes_an_output_path(self):
        # What makes the digest cases above the whole guard: there is no way to
        # point a mode at a scratch CSV, so "writes nothing" is a property of
        # the interface rather than of a check someone has to remember to add.
        # If this fails, the diff cases need a tripwire too.
        source = Path(xfc.__file__).read_text(encoding="utf-8")
        for flag in ("--out-registers", "--out-clusters", "--out"):
            self.assertNotIn(flag, source,
                             f"{flag} is a mode argument; the writes-nothing "
                             "cases assume no mode can be pointed at a file")


if __name__ == "__main__":
    unittest.main()