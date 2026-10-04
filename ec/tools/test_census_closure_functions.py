#!/usr/bin/env python3
"""Cases for `census_closure_functions.py`.

The tool's own `--self-test` carries the readings and the refusals, and this
drives it. What is here is the half a self-test cannot be: the tool's *shapes*
held directly, so a census that had quietly stopped being a partition, or a
`covering()` that answered differently under the two span readings, or a report
that had started printing one figure and describing another, is caught by a
named case rather than by a count moving.

**No count of the tree is asserted anywhere in this file.** Every population
this tool reports moves with both the walk's bounds and with inventory growth --
a merge that adds an annotation row is not a defect, and a suite that pinned
the figure would go red on one and tell the implement stage to fix a correct
tool. What is asserted is the claim and the relation: the three predicates are
computed and related correctly, the two span readings are both reported and
differ, section 4's instance is answered on instruction boundaries, and every
refusal still refuses.

Everything here reads committed files. No Ghidra, no hardware, no Windows, no
network.
"""
import ast
import collections
import contextlib
import inspect
import io
import os
import sys
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bank_attribution as ba  # noqa: E402
import census_closure_functions as census  # noqa: E402
from audit_call_targets import survey  # noqa: E402

FIRMWARE = os.path.join(census.EC, "firmware", "GMxMGxx_11.800")


def firmware():
    """The committed image, read fresh. `bank_attribution.py` opens it the same
    way, and a cached module-level read would mean this suite and the tool
    under test could not disagree about which image they saw."""
    with open(FIRMWARE, "rb") as f:
        return f.read()


def committed():
    """(firmware bytes, closures, pairs, index rows) over the committed tree.

    The walk is `bank_attribution.closure()` and it is run once per class that
    needs it: it is a bounded walk over the image, and running it per case
    would dominate the suite's time for no extra coverage.
    """
    d = firmware()
    rows, _stubs, tramp = survey(d)
    seeds = ba.seeds_for(tramp)
    closures = {b: ba.closure(d, b, seeds[b]) for b in (0, 1)}
    return d, closures, ba.pair_rows(rows, closures), census.read_csv(
        census.INDEX_CSV)


class TheSelfTest(unittest.TestCase):
    """The tool's own self-test, which is where the readings live."""

    def test_it_passes(self):
        # The transcript goes to a buffer rather than to this suite's own
        # output: the readings are two dozen lines, and a reader running the
        # suite would otherwise have to find this suite's own result underneath
        # them. The exit code is the whole of the assertion.
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = census.self_test(firmware())
        self.assertEqual(rc, 0, buf.getvalue()[-2000:])


class TheReportRuns(unittest.TestCase):
    """The census is a report: it exits 0 and prints, whatever it finds."""

    def test_the_default_run_exits_zero_and_prints_its_inputs(self):
        out = report()
        self.assertIn("no Ghidra", out)
        self.assertIn("no `status:` in", out)

    def test_the_report_names_both_span_readings_and_neither_as_the_population(self):
        out = report()
        self.assertIn("`size`", out)
        self.assertIn("`listing`", out)
        self.assertIn("neither is presented as the population", out)

    def test_every_negative_is_calibrated(self):
        """A negative says what the method did not find, never that a thing is
        absent. This is CLAUDE.md's rule and the one most likely to erode
        silently as the report is edited.

        Checked as a *discipline* rather than as a banned word: the report may
        say "absent" only inside a sentence that also says what the method did
        not do. Every line carrying the word is read here, so a future edit
        that writes "this address is absent" fails and one that writes "not
        found by this method, never absent" passes.
        """
        offenders = [line for line in report().splitlines()
                     if "absent" in line
                     and not any(phrase in line for phrase in
                                 ("not found by this method", "never",
                                  "not a statement"))]
        self.assertEqual(offenders, [],
                         "an uncalibrated use of 'absent' in the report")

    def test_the_three_predicates_are_each_named(self):
        out = report()
        for phrase in ("inside a row", "at a row's entry",
                       "at an instruction boundary"):
            self.assertIn(phrase, out)

    def test_the_report_carries_no_total_of_the_repository(self):
        """No hand-kept figure about the tree's own size: those lines are what
        every concurrent branch has to edit."""
        out = report()
        for phrase in ("write-ups", "suites", "tests in all"):
            self.assertNotIn(phrase, out)


class TheTwoSpanReadings(unittest.TestCase):
    """`size` and the committed listing disagree, and both are reported."""

    @classmethod
    def setUpClass(cls):
        _d, _c, _p, cls.index_rows = committed()
        cls.spans = census.spans_by_program(cls.index_rows)

    def test_both_readings_are_built_for_every_program(self):
        for reading in ("size", "listing"):
            for program in ("bank0", "bank1", "common", "pd"):
                self.assertIn(program, self.spans[reading])
                self.assertTrue(self.spans[reading][program],
                                f"{program} has no {reading} spans")

    def test_the_two_readings_are_not_the_same_list(self):
        """They disagree on this image, which is why printing one would be a
        choice rather than a reading. Asserted as a difference, not as a count:
        the direction and size of the gap are the export's business."""
        differs = [p for p in ("bank0", "bank1")
                   if [s[:2] for s in self.spans["size"][p]]
                   != [s[:2] for s in self.spans["listing"][p]]]
        self.assertTrue(differs, "the two readings agree everywhere, so printing "
                                 "both would be carrying a distinction that is "
                                 "not there")

    def test_a_listing_span_is_what_the_asm_holds(self):
        """The `listing` reading is read out of the committed `.asm` through
        `row_span()`, so it is the listing's own span rather than a second
        opinion about it. Checked against `row_span()` directly, which is what
        would catch a future edit computing it some other way."""
        for program in ("bank0", "bank1"):
            for first, last, addr, _basis in self.spans["listing"][program]:
                self.assertEqual((first, last),
                                 census.row_span(census.DECOMPILED, program,
                                                 addr))

    def test_covers_is_answered_per_reading(self):
        """A byte in a row's `size` span but past its listing must answer
        differently under each reading -- that is the whole reason for two.

        Probed over the union of both readings' span edges rather than at a
        named address, so this holds as the export changes.
        """
        size_rows = self.spans["size"]["bank0"]
        listing_rows = self.spans["listing"]["bank0"]
        probes = {edge for rows in (size_rows, listing_rows) for s in rows
                  for edge in (s[0], s[1])}
        disagreements = [addr for addr in probes
                         if (census.covering(size_rows, addr) is None
                             != (census.covering(listing_rows, addr) is None))]
        self.assertGreater(
            len(disagreements), 0,
            "no probed address answers differently under the two readings, so "
            "the distinction is untested here")


class ThePartition(unittest.TestCase):
    """`inside` / `at-entry` / `outside` are computed as documented."""

    @classmethod
    def setUpClass(cls):
        _d, cls.closures, _p, index_rows = committed()
        cls.spans = census.spans_by_program(index_rows)

    def test_inside_and_at_entry_agree_with_a_direct_count(self):
        rows = self.spans["size"]["bank0"]
        reached = self.closures[0][0]
        inside, at_entry, outside = census.partition(reached, rows)
        self.assertEqual(len(inside) + len(outside), len(reached))
        self.assertTrue(at_entry <= inside)
        self.assertEqual(len(inside & at_entry), len(at_entry))
        for addr in list(inside)[:200]:
            self.assertIsNotNone(census.covering(rows, addr))
        for addr in list(outside)[:200]:
            self.assertIsNone(census.covering(rows, addr))

    def test_at_entry_is_exactly_the_addresses_that_are_a_row_addr(self):
        rows = self.spans["size"]["bank1"]
        reached = self.closures[1][0]
        _inside, at_entry, _outside = census.partition(reached, rows)
        self.assertEqual(at_entry, set(reached) & {s[2] for s in rows})

    def test_dropping_call_target_rows_shrinks_the_population(self):
        rows = self.spans["size"]["bank0"]
        reached = self.closures[0][0]
        strict = census.bank_rows(rows, True)
        self.assertLess(len(census.partition(reached, strict)[0]),
                        len(census.partition(reached, rows)[0]))

    def test_runs_of_are_contiguous_and_ordered(self):
        got = census.runs_of([0x10, 0x11, 0x12, 0x20, 0x22, 0x23])
        self.assertEqual(got, [[0x10, 0x13], [0x20, 0x21], [0x22, 0x24]])


class TheInstructionBoundaryPredicate(unittest.TestCase):
    """The predicate that answers section 4's open question."""

    @classmethod
    def setUpClass(cls):
        cls.d, cls.closures, _p, index_rows = committed()
        cls.starts = census.starts_by_program()
        cls.index_rows = index_rows

    def test_it_reads_instruction_starts_out_of_the_listings(self):
        starts = self.starts["bank0"]
        self.assertTrue(starts)
        # A row's own address opens its listing, so this is a structural
        # property of the export rather than a figure: every bank0 row in
        # index.csv is an instruction start in the listing that holds it.
        rows = census.spans_by_program(self.index_rows)["listing"]["bank0"]
        for _first, _last, addr, _basis in rows:
            self.assertIn(addr, starts,
                          f"0x{addr:04X} is a row's own address and its listing "
                          f"does not start an instruction there")

    def test_the_lcall_over_the_misdecoded_target_is_a_firmware_fact(self):
        """The *reason* `0x808E` is no instruction start, asserted over the
        committed image rather than over the export.

        This is what replaced an assertion on the listing's instruction starts.
        Those read `ec/decompiled/*.asm`, which a later annotation regenerates,
        so pinning them turned a legitimate redraw into a red run over a
        correct tool. The three bytes here cannot move.
        """
        from trace_xdata_refs import offset_for_runtime
        off = offset_for_runtime(census.LCALL_SITE, "bank0")
        got = self.d[off:off + len(census.LCALL_BYTES)]
        self.assertEqual(got, census.LCALL_BYTES,
                         f"bank0 0x{census.LCALL_SITE:04X} is "
                         f"`{got.hex(' ')}`, expected "
                         f"`{census.LCALL_BYTES.hex(' ')}` (`lcall 0xbe7e`, "
                         f"three bytes over 0x{census.LCALL_SITE:04X}-"
                         f"0x{census.SJMP_TARGET:04X})")
        # And the instruction really does span the address in question, which
        # is what makes the byte fact an answer about boundaries.
        self.assertEqual(census.LCALL_SITE + len(census.LCALL_BYTES) - 1,
                         census.SJMP_TARGET)

    def test_the_misdecoded_target_is_inside_a_row(self):
        """The reason the issue's proposed test ("no row names 0x808E") is
        false here: a row's span does cover it."""
        rows = census.spans_by_program(self.index_rows)["size"]["bank0"]
        self.assertIsNotNone(census.covering(rows, census.SJMP_TARGET),
                             "0x808E is inside a row's span on this tree, so "
                             "'no row names it' would be false")

    def test_the_boundary_figure_is_reported_but_not_pinned(self):
        """The tool prints the boundary and deliberately asserts nothing about
        it, because both halves read the regenerable export.

        Checked two ways, because either alone is satisfiable by the wrong
        thing: the report has to carry the figure, and no `check()` in
        `self_test` may read the instruction-start set at all. The second half
        is the one that matters -- a transcript can print "not pinned" beside an
        assertion that pins it, which is the contradiction this case exists to
        keep out of the tree.
        """
        out = report()
        self.assertIn(f"| `0x{census.SJMP_TARGET:04X}` |", out)
        self.assertIn("starts an instruction in a listing", out)
        self.assertIn("not found by this\nmethod", out)

        # No assertion may read the export-derived predicate. `starts` is the
        # set `starts_by_program()` builds and `self_test` binds to `base`;
        # neither may appear anywhere inside a `check()` call's arguments. The
        # walk recurses, because `SJMP_TARGET not in base` is a Compare with the
        # name buried inside it rather than an argument in its own right.
        tree = ast.parse(textwrap.dedent(inspect.getsource(census.self_test)))
        banned = {"base", "starts"}
        offenders = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) == "check"):
                continue
            for arg in node.args:
                if any(isinstance(sub, ast.Name) and sub.id in banned
                       for sub in ast.walk(arg)):
                    offenders.append(ast.dump(node)[:100])
        self.assertEqual(offenders, [],
                         "self_test asserts on the instruction-start set, which "
                         "reads the regenerable .asm export; print it instead")

    def test_the_walk_still_reaches_it(self):
        """The census reports the framing risk; it does not fix it."""
        self.assertIn(census.SJMP_TARGET, self.closures[0][0])

    def test_the_table_base_and_its_handlers_are_named(self):
        by_addr = {(r["program"], int(r["addr"], 16)): r
                   for r in self.index_rows}
        for addr in (census.TABLE_BASE,) + census.HANDLERS:
            self.assertIn(("bank0", addr), by_addr)
            self.assertTrue(by_addr[("bank0", addr)]["name"])


class ThePathCountColumn(unittest.TestCase):
    """The `1 path` column of section 2, composed rather than assumed.

    The whole point of the section is the distinction between the *path* count
    and the *entry-point* count, which `closure()` reports as two different
    things over the same addresses. A section that quietly used the second would
    print a plausible, wrong figure against the table it claims to explain, so
    the predicates are held on a fixture where the answer is known.
    """

    def test_single_path_is_the_path_count_not_the_entry_point_count(self):
        """`reached` counts blocks per address; `who` holds the entry points.

        An address in two blocks of one entry point is two paths and one entry
        point, which is exactly where the two readings come apart.
        """
        reached = collections.Counter({0x10: 1, 0x11: 2, 0x12: 1})
        who = {0x10: {0x01}, 0x11: {0x01}, 0x12: {0x01, 0x02}}
        self.assertEqual(census.single_path(reached), {0x10, 0x12})
        # The entry-point reading over the same addresses, for contrast. It
        # differs in *both* directions -- it keeps 0x11, which one entry point
        # reaches across two blocks, and drops 0x12, which two reach at once --
        # so the two figures are not even nested, and using the wrong one is not
        # a rounding difference.
        self.assertEqual({a for a in reached if len(who[a]) == 1}, {0x10, 0x11})

    def test_path_census_counts_a_ret_run_and_a_lone_ret_apart(self):
        """`single_in_run` is the run; `single_ret` also catches the `ret` that
        ends some other block, which reads as one path for the same reason."""
        d = firmware()
        first, last = census.RET_RUNS[1]
        lone = 0xBF12  # the block before the run; not a `0x22` byte itself
        reached = collections.Counter({a: 1 for a in range(first, last + 1)})
        got = census.path_census(reached, d, 0)
        self.assertEqual(got["single"], last - first + 1)
        self.assertEqual(got["single_in_run"], got["single"],
                         "every byte of the run is in the run")
        self.assertEqual(got["single_ret"], got["single"],
                         "and every byte of it is a `0x22` byte")

        # A lone `ret`, outside any run: counted as `0x22` but not as in-run.
        from trace_xdata_refs import offset_for_runtime
        lone_ret = next(a for a in range(0x8000, 0xC000)
                        if d[offset_for_runtime(a, "bank0")] == census.RET_BYTE
                        and not any(f <= a <= l
                                    for f, l in census.ret_runs(d)))
        reached = collections.Counter({lone_ret: 1, lone: 1})
        got = census.path_census(reached, d, 0)
        self.assertEqual(got["single_in_run"], 0)
        self.assertEqual(got["single_ret"], 1)
        self.assertNotEqual(lone_ret, lone)

    def test_a_multi_path_address_is_not_counted_as_single(self):
        d = firmware()
        first, last = census.RET_RUNS[1]
        reached = collections.Counter({a: 1 for a in range(first, last + 1)})
        reached[first] = 2  # as if a second path wandered in
        got = census.path_census(reached, d, 0)
        self.assertEqual(got["single"], last - first)
        self.assertEqual(got["single_in_run"], got["single"])

    def test_a_bank_with_no_run_reports_a_zero_rather_than_failing(self):
        """bank1 has no `0x22` run of the threshold length at all.

        The shape matters because it is a real one on this image rather than a
        hypothetical: the in-run column has to come out a printed zero beside
        the `0x22` one, not a missing column and not a division by nothing.
        """
        d = firmware()
        self.assertEqual(census.ret_runs(d, 1), [],
                         "bank1 is expected to have no run of the threshold "
                         "length; if that changed, this case is testing the "
                         "wrong bank and the report needs a second run")
        got = census.path_census({0x9000: 1, 0x9001: 1}, d, 1)
        self.assertEqual(got["single"], 2)
        self.assertEqual(got["single_in_run"], 0)

    def test_an_empty_reached_set_is_all_zeroes(self):
        got = census.path_census({}, firmware(), 0)
        self.assertEqual(got, {"single": 0, "single_ret": 0, "single_in_run": 0})

    def test_the_report_distinguishes_the_path_count_from_the_entry_point_one(self):
        """Section 2's table tabulates the path count, so the report has to say
        which of the two it printed and why they differ."""
        out = report()
        self.assertIn("`1 path` means the path count, not the entry-point count",
                      out)
        self.assertIn("`len(who[addr]) == 1`", out)
        self.assertIn("reads as one path **by construction**", out)

    def test_the_path_count_column_is_reported_for_both_banks(self):
        out = report()
        self.assertIn("| bank | reached | 1 path |", out)
        for bank in ("bank0", "bank1"):
            self.assertIn(f"| `{bank}` |", out)


class TheRetRuns(unittest.TestCase):
    """The runs are re-derived from the firmware, and the attribution in them
    is the linker's rather than the walk's."""

    @classmethod
    def setUpClass(cls):
        cls.d, cls.closures, _p, _i = committed()
        cls.runs = census.ret_runs(cls.d)

    def test_every_byte_of_a_run_is_the_ret_byte(self):
        from trace_xdata_refs import offset_for_runtime
        for first, last in self.runs:
            for addr in range(first, last + 1):
                self.assertEqual(self.d[offset_for_runtime(addr, "bank0")],
                                 census.RET_BYTE,
                                 f"0x{addr:04X} is not a `0x22` byte inside a "
                                 f"run the tool reported")

    def test_the_runs_are_maximal(self):
        """A run that stopped early would be a run the walk could walk out of,
        which is the very thing the finding is about."""
        from trace_xdata_refs import offset_for_runtime
        for first, last in self.runs:
            self.assertNotEqual(self.d[offset_for_runtime(first - 1, "bank0")],
                                census.RET_BYTE)
            self.assertNotEqual(self.d[offset_for_runtime(last + 1, "bank0")],
                                census.RET_BYTE)

    def test_the_entry_points_in_a_run_are_all_trampoline_seeds(self):
        """The reframe: the issue read these bytes as walk-derived frames."""
        for first, last in self.runs:
            reached, _who, entries = self.closures[0][:3]
            here = [a for a in range(first, last + 1) if a in reached]
            self.assertTrue(here)
            for addr in here:
                kind = entries.get(addr, (None,))[0]
                self.assertIn(kind, ("trampoline", None),
                              f"0x{addr:04X} is entered as a {kind}, so the "
                              f"walk did derive a frame inside a `ret` run")

    def test_a_non_seed_byte_is_reached_from_outside_and_enters_nothing(self):
        for first, last in self.runs:
            reached, who, entries = self.closures[0][:3]
            here = [a for a in range(first, last + 1) if a in reached]
            rest = [a for a in here if a not in entries]
            for addr in rest:
                self.assertTrue(who[addr])
                self.assertNotIn(addr, who[addr],
                                 f"0x{addr:04X} is its own entry point, so the "
                                 f"walk did enter it")

    def test_every_reached_byte_of_a_run_carries_exactly_one_path(self):
        for first, last in self.runs:
            reached = self.closures[0][0]
            for addr in range(first, last + 1):
                if addr in reached:
                    self.assertEqual(reached[addr], 1)


class TheStubTable(unittest.TestCase):
    """The stub count is a count of the linker's own committed table."""

    @classmethod
    def setUpClass(cls):
        cls.d = firmware()
        cls.every, cls.in_run = census.stub_census(cls.d)

    def test_it_counts_only_far_call_stubs(self):
        rows = census.read_csv(census.STUB_TABLE)
        expected = len([r for r in rows if r["table"] == "far-call-stub"])
        self.assertEqual(self.every, expected)

    def test_every_target_it_reports_is_inside_a_run_and_is_a_ret_byte(self):
        from trace_xdata_refs import offset_for_runtime
        for (first, last), targets in self.in_run.items():
            for target in targets:
                self.assertTrue(first <= target <= last)
                self.assertEqual(
                    self.d[offset_for_runtime(target, "bank0")],
                    census.RET_BYTE)

    def test_no_run_is_silently_empty(self):
        """A run reported with no stub would make the "one stub per byte"
        reading untested rather than refuted, so the case is that they are not
        empty at all."""
        for run in census.RET_RUNS:
            self.assertTrue(self.in_run.get(tuple(run)),
                            f"no stub targets 0x{run[0]:04X}-0x{run[1]:04X}")


class ItWritesNothing(unittest.TestCase):
    """No CSV mode, no `--apply`, and a write path that refuses."""

    def test_the_flags_are_the_documented_two(self):
        flags = {opt for action in census._parser()._actions
                 for opt in action.option_strings}
        self.assertEqual(flags, {"-h", "--help", "--self-test"})

    def test_the_write_path_refuses(self):
        with self.assertRaises(NotImplementedError):
            census.write_runs_csv({}, {})


def report():
    """The default run's output, captured. Drives `main()` so the case covers
    the argument handling and not only the printing functions."""
    argv = sys.argv
    sys.argv = ["census_closure_functions.py", FIRMWARE]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            census.main()
    finally:
        sys.argv = argv
    return buf.getvalue()


def self_test_output():
    """The self-test's own transcript, captured.

    Separate from `report()` because the refusal the suite checks -- which
    predicate is printed rather than pinned -- is only visible on this side.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        census.self_test(firmware())
    return buf.getvalue()


if __name__ == "__main__":
    unittest.main()