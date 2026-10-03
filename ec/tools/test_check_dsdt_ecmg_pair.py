#!/usr/bin/env python3
"""Cases for `check_dsdt_ecmg_pair.py`.

The tool holds a census about three names in `evidence/acpi/dsdt.dsl`, and its
own `--self-test` already pins the refusals against constructed fixtures. What
this suite adds is everything that is a property *of the tree* rather than of
the tool: that the committed pair is clean, that the two parsers reconcile
with each other, and that the tool keeps the scope its own docstring claims.

What it deliberately does not do is restate the census. `check_dsdt_ecmg_pair.py`
holds the figures, in one place, because a figure duplicated into a second file
is a second line for every later DSDT revision to edit. So the assertions here
are relationships -- named plus unnamed is the total, the committed CSV agrees
with the parse, the spans are found rather than carried -- and the digits stay
where the issue's figures were corrected.

The negative half matters more than the positive one. A check that has quietly
stopped refusing looks exactly like a check that is working, so `--self-test`
is the part of the tool doing that work and this suite holds it to its exit
code; `TheRefusals` below drives the same paths through `census()` on
constructed fixtures, where a failure names the refusal rather than an exit
status. It goes through `census()` rather than `report()` because the two
answer different questions -- `report()` also holds the fixture to the
committed tree's figures, which no three-anchor stub can satisfy.
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, "ec", "tools"))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import check_dsdt_ecmg_pair as pair  # noqa: E402

DSDT = os.path.join(REPO, "evidence", "acpi", "dsdt.dsl")
CSV = os.path.join(REPO, "ec", "annotations", "dsdt-ecmg-fields.csv")


def _write(text):
    """`text` in a scratch `.dsl`, for the parse-level cases."""
    handle, path = tempfile.mkstemp(suffix=".dsl", text=True)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    return path


class TheCommittedPair(unittest.TestCase):
    """The census the tool holds, read off the committed inputs."""

    @classmethod
    def setUpClass(cls):
        cls.problems, cls.census = pair.report(DSDT, CSV)

    def test_the_committed_pair_is_clean(self):
        self.assertEqual(self.problems, [])

    def test_each_of_the_three_names_has_two_hits(self):
        for name in ("DBD1", "DBD2", "ECMG"):
            with self.subTest(name=name):
                self.assertEqual(len(self.census[name]["lines"]), 2)

    def test_dbd1_and_dbd2_are_each_one_store_and_one_declaration(self):
        for name in ("DBD1", "DBD2"):
            with self.subTest(name=name):
                self.assertEqual(self.census[name]["tally"],
                                 {"store": 1, "declaration": 1})

    def test_every_hit_falls_inside_a_named_span(self):
        # The span check is what makes "exactly twice" mean "twice, and both
        # accounted for" rather than "twice, somewhere". Asserting the spans
        # were found at all is the other half: a parser that stopped matching
        # the writer arm returns None here rather than an empty span that
        # would then reject every hit.
        span = self.census["span"]
        for part in span:
            self.assertIsNotNone(part)
        for name in ("DBD1", "DBD2"):
            for line in self.census[name]["lines"]:
                index = line - 1
                self.assertTrue(
                    pair.in_spans(index, (span[0], span[2])),
                    "%s at %d is outside both spans" % (name, line))

    def test_the_pair_is_declared_side_by_side_at_equal_width(self):
        positions = self.census["positions"]
        first, second = positions["DBD1"], positions["DBD2"]
        self.assertEqual(first[0], second[0], "one anchor, so one byte")
        self.assertEqual(first[2], second[2], "both the same width")
        self.assertEqual(first[1] + first[2], second[1],
                         "the second starts where the first ends, so the two "
                         "are disjoint ranges and not one field twice")

    def test_named_plus_unnamed_bits_is_the_declared_total(self):
        cover = self.census["coverage"]
        self.assertEqual(cover["named_bits"] + cover["unnamed_bits"],
                         cover["bits"])

    def test_the_committed_csv_reconciles_with_the_parse(self):
        # The trailing-comma bug dropped `MGOF` from the DSDT side while the
        # CSV kept it, so the two sides disagreed by exactly one element and
        # nothing failed. This is the assertion that would have turned it red.
        cover = self.census["coverage"]
        self.assertEqual(self.census["csv"]["widths"] + cover["unnamed_bits"],
                         cover["bits"])

    def test_the_coverage_denominator_is_read_from_the_declaration(self):
        # Not carried as a constant, so a region whose length changed cannot
        # be divided by the old one without this failing.
        cover = self.census["coverage"]
        self.assertIsNotNone(cover["region_bytes"])
        self.assertGreater(cover["region_bytes"], 0)

    def test_the_named_split_covers_exactly_the_named_elements(self):
        # The named/unnamed split has to come out of the walk rather than be
        # subtracted, because the reconciliation above only balances if both
        # sides are measured the same way.
        lines = pair.read_lines(DSDT)
        cover = self.census["coverage"]
        widths = pair.declared_widths(lines, self.census["span"])
        self.assertEqual(sum(widths.values()), cover["named_bits"])
        self.assertEqual(len(widths) + cover["unnamed_elements"],
                         cover["elements"])

    def test_the_gap_count_is_the_definition_it_names(self):
        # "Gaps" is only meaningful against its definition, so the census has
        # to carry the pairs it counted rather than the number alone -- a bare
        # gap count is a number nobody can check.
        cover = self.census["coverage"]
        self.assertEqual(len(cover["gap_pairs"]), cover["gaps"])
        for before, after in cover["gap_pairs"]:
            self.assertGreater(after - before, 1)

    def test_the_undeclared_count_is_bytes_and_not_the_gap_sum(self):
        # The gap count and the undeclared-byte count are different quantities
        # and only one of them is about bytes. Summing the anchor-to-anchor
        # gaps counts a multi-byte element's continuation bytes twice, because
        # they fall inside the gap after their own anchor -- so the sum comes
        # out above the complement. Asserting the two are different is what
        # keeps a future edit from quietly swapping one for the other, which
        # is how a write-up came to call a gap sum an undeclared-byte count.
        cover = self.census["coverage"]
        self.assertLess(cover["undeclared_bytes"],
                        sum(after - before for before, after
                            in cover["gap_pairs"]))

    def test_the_undeclared_stretch_excludes_allocated_continuation_bytes(self):
        # `Offset (0x7D4)` allocates four whole bytes, so the stretch that
        # follows it starts at `0x07D8` and not at the anchor's own byte. This
        # is derived from the field list rather than restated, so a `Field`
        # edit that widened the anchor moves the run with it.
        lines = pair.read_lines(DSDT)
        allocated = pair.allocated_bytes(lines, self.census["span"])
        start, end = self.census["coverage"]["longest_undeclared_run"]
        self.assertNotIn(start, allocated)
        self.assertNotIn(end, allocated)
        self.assertEqual(
            self.census["coverage"]["undeclared_bytes"],
            len([b for b in range(self.census["coverage"]["first_anchor"],
                                  self.census["coverage"]["last_anchor"] + 1)
                 if b not in allocated]))

    def test_the_computed_base_accessors_are_declared_and_uncalled(self):
        # The half of the corrected reason that has to hold, and the reason it
        # is a separate census: `ECRR`/`ECRW` reach the same window at a
        # computed base with no field name in the path, so their existing is
        # the counterexample to "these names are the only route". What saves
        # the conclusion is that neither is ever invoked, and that is the fact
        # asserted here rather than argued in prose.
        for name in pair.ACCESSORS:
            with self.subTest(name=name):
                entry = self.census["accessors"][name]
                self.assertEqual(len(entry["declarations"]), 1,
                                 "%s should be declared exactly once" % name)
                self.assertEqual(entry["calls"], [],
                                 "%s reads the ECMG window at a computed base; "
                                 "a call to it is a reader this census exists "
                                 "to refuse" % name)

    def test_no_computed_base_region_reaches_the_window_from_a_called_method(self):
        # The property the derived census exists to hold, asserted as a
        # property of the committed file rather than as a count of it: every
        # region in the file that lands inside the ECMG window sits in a method
        # nothing calls. A fourth computed-base method aimed at this window
        # makes this fail, and it fails whether or not any document names it --
        # which is what the hard-coded accessor list could not do.
        inside = [entry for entry in self.census["routes"]["invoked"]
                  if entry["state"] == "invoked-into-window"]
        self.assertEqual(
            inside, [],
            "these computed-base regions resolve into the ECMG window and "
            "their methods are called, so the DSDT reaches 0x07D0/0x07D1 by a "
            "route no field name appears in: %r" % (inside,))

    def test_a_route_the_scan_cannot_place_is_reported_not_cleared(self):
        # The limit, asserted so a later edit cannot quietly turn "unresolved"
        # into "safe". A base built from a runtime value or an `External` name
        # (`XBAS` builds `EMPC` in `DLLR`) has no committed bound, so it is
        # reported as unbounded and must not be filed among the routes that
        # were checked and missed.
        unbounded = self.census["routes"]["unbounded"]
        self.assertTrue(
            unbounded,
            "the committed DSDT has computed-base regions whose base is a "
            "runtime value; if this ever comes back empty the census is "
            "resolving bases it cannot actually resolve")
        for entry in unbounded:
            self.assertEqual(entry["state"], pair.UNBOUNDED)
            self.assertNotIn("resolves", entry,
                             "an unbounded route must carry no resolved "
                             "address, or it would read as a cleared one")


class TheToolOnItsOwn(unittest.TestCase):
    """The tool run the way a gate runs it."""

    def test_check_exits_zero_on_the_committed_tree(self):
        done = subprocess.run(
            [sys.executable, os.path.join(TOOLS, "check_dsdt_ecmg_pair.py"),
             "--check"],
            capture_output=True, text=True, cwd=REPO)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_self_test_exits_zero(self):
        done = subprocess.run(
            [sys.executable, os.path.join(TOOLS, "check_dsdt_ecmg_pair.py"),
             "--self-test"],
            capture_output=True, text=True, cwd=REPO)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_check_prints_the_census_it_measured(self):
        done = subprocess.run(
            [sys.executable, os.path.join(TOOLS, "check_dsdt_ecmg_pair.py"),
             "--check", "--print"],
            capture_output=True, text=True, cwd=REPO)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for name in ("DBD1", "DBD2", "ECMG"):
            self.assertIn(name, done.stdout)
        # The printed figures come from the census rather than from prose, so
        # the writer and the read-back agree without a human comparing them.
        cover = pair.report(DSDT, CSV)[1]["coverage"]
        self.assertIn("%d anchors" % cover["anchors"], done.stdout)
        self.assertIn("%d bits" % cover["bits"], done.stdout)


class TheRefusals(unittest.TestCase):
    """The check driven onto fixtures where it has to go red.

    Each case edits one thing in the tool's own `--self-test` fixture, so a
    failure here names the refusal rather than an exit status. The four that
    matter are the ones a later DSDT revision would trigger: a reader inside
    the writer arm, a third site outside it, a `Field` list that no longer
    reconciles with the CSV built from it, and a caller for one of the
    computed-base accessors. That last one is the only case the name census
    structurally cannot see -- it leaves both hit counts exactly where they
    are -- which is the whole reason it has a census of its own.
    """

    def report_on(self, text, widths):
        return self.census_on(text, widths)[0]

    def census_on(self, text, widths):
        """`census()` on a fixture, returning `(problems, measured)`.

        The measured half is what a refusal about the *route* census turns on:
        a region the check reports as unbounded raises no problem, so a test
        that only reads the problems cannot tell an honest refusal from a
        rule that quietly cleared the route.
        """
        handle, path = tempfile.mkstemp(suffix=".dsl", text=True)
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(text)
        rows = ["region,addr,bit,width,name,dsdt_line,static_refs,"
                "static_refs_main_ec,static_refs_pd_image,in_registers,grade,"
                "asl_refs,asl_sites"]
        for name, width in widths:
            rows.append("ECMG,0x0000,0,%d,%s,0,0,0,0,,present-untested,0," %
                        (width, name))
        csv_handle, csv_path = tempfile.mkstemp(suffix=".csv", text=True)
        with os.fdopen(csv_handle, "w", encoding="utf-8") as out:
            out.write("\n".join(rows) + "\n")
        try:
            return pair.census(path, csv_path)
        finally:
            os.unlink(path)
            os.unlink(csv_path)

    def widths_for(self, **overrides):
        spec = {"DBD1": 8, "DBD2": 8, "GFID": 3, "LASTF": 8}
        spec.update(overrides)
        return tuple(sorted(spec.items()))

    def test_the_unedited_fixture_is_clean(self):
        # Without this, a fixture that stopped parsing would make every case
        # below pass for the wrong reason.
        self.assertEqual(self.report_on(pair.FIXTURE,
                                        self.widths_for()), [])

    def test_a_reader_inside_the_writer_arm_is_refused(self):
        problems = self.report_on(
            pair.FIXTURE.replace(
                "                    ^^PCI0.LPCB.EC0.DBD1 = Local0\n",
                "                    ^^PCI0.LPCB.EC0.DBD1 = Local0\n"
                "                    If (^^PCI0.LPCB.EC0.DBD2 == 0)\n"
                "                    {\n"
                "                        Local2 = 1\n"
                "                    }\n"),
            self.widths_for())
        self.assertTrue(
            any("neither a store nor a declaration" in p for p in problems),
            "a load keeps the hit inside the named span, so only the "
            "classification refuses it: %s" % (problems or "nothing reported"))

    def test_a_third_site_outside_the_spans_is_refused(self):
        problems = self.report_on(
            pair.FIXTURE.replace(
                "                    Store (Arg1, DBAC)\n",
                "                    Store (Arg1, DBAC)\n"
                "                    ^^PCI0.LPCB.EC0.DBD2 = Arg2\n"),
            self.widths_for())
        self.assertTrue(
            any("outside both" in p for p in problems),
            "a store in a neighbouring T1WR arm is a third site: %s" %
            (problems or "nothing reported"))

    def test_a_width_column_that_disagrees_is_refused(self):
        problems = self.report_on(pair.FIXTURE,
                                  self.widths_for(LASTF=7))
        self.assertTrue(
            any("come to" in p for p in problems),
            "the DSDT parse and the CSV are two measurements of one list and "
            "have to agree: %s" % (problems or "nothing reported"))

    def test_a_missing_writer_arm_is_reported_not_crashed_on(self):
        problems = self.report_on(
            pair.FIXTURE.replace("ElseIf ((Arg0 == 0x1173))",
                                 "ElseIf ((Arg0 == 0x1174))"),
            self.widths_for())
        self.assertTrue(
            any("no T1WR Arg0 == %s arm" % pair.WRITER_ARG in p
                for p in problems),
            "a renamed arm is a missing span, and saying so is the whole of "
            "the answer: %s" % (problems or "nothing reported"))

    def test_the_last_element_is_counted_without_its_trailing_comma(self):
        # The regression this tool exists partly because of: `MGOF,   8`
        # carries no comma where every element above it carries one, so a
        # pattern that requires the comma drops it silently and the census
        # reads eight bits short with nothing failing. Asserted on the parse
        # rather than on the pattern's text, because the text is what a tidy
        # would change.
        path = _write(pair.FIXTURE)
        try:
            lines = pair.read_lines(path)
            cover = pair.coverage_census(lines, pair.spans(lines)[0])
        finally:
            os.unlink(path)
        self.assertEqual(cover["bits"], pair.FIXTURE_BITS)
        self.assertEqual(cover["whole_bytes"] * 8 +
                         cover["spare_bits"], cover["bits"])

    def test_a_caller_for_the_computed_base_accessor_is_refused(self):
        # The case the name census structurally cannot see. The fixture still
        # declares `DBD1` once and stores it once, so every assertion above
        # stays green -- and the DSDT now reads the byte, through a route with
        # no field name in it. Holding "nothing reads these bytes" means
        # holding this, not holding the two-hit count alone.
        problems = self.report_on(
            pair.FIXTURE.replace(
                "                    Local0 = (Arg1 * 0x08)\n",
                "                    Local3 = ECRR (0x07D0)\n"
                "                    Local0 = (Arg1 * 0x08)\n"),
            self.widths_for())
        self.assertTrue(
            any("ECRR is invoked" in p for p in problems),
            "a call to a computed-base accessor is a reader of 0x07D0 with no "
            "field name in it: %s" % (problems or "nothing reported"))

    def test_a_runtime_value_inside_an_arithmetic_base_is_not_cleared(self):
        # `(Arg0 + 0x84)` is a runtime value wearing a constant's clothes, and
        # it is the shape the committed file's `UPSC` region has. `re.sub`
        # reads a `None` return as "delete this match", so substituting an
        # unresolvable token as `None` deleted `Arg0` and left `( + 0x84)`,
        # which evaluates: the region was filed as a route to `0x84` in a
        # method `ECRR` calls, and cleared, on a base nothing places. The bare
        # `EMPB` case does not reach this path -- alone, the token is the whole
        # expression, and deleting it leaves nothing that evaluates.
        problems, measured = self.census_on(
            pair.FIXTURE.replace(
                "            Method (MMRW, 4, NotSerialized)\n"
                "            {\n",
                "            Method (MMRW, 4, NotSerialized)\n"
                "            {\n"
                "                OperationRegion (MRCF, SystemMemory, "
                "(Arg0 + 0x84), 0x04)\n"),
            self.widths_for())
        self.assertEqual(problems, [])
        routes = measured["routes"]
        unbounded = [e for e in routes["unbounded"] if e["region"] == "MRCF"]
        self.assertEqual(
            [e["region"] for e in unbounded], ["MRCF"],
            "ECRR calls MMRW, so this base is resolved, and a runtime value in "
            "an arithmetic expression has to come out unbounded: %r" % (
                routes,))
        self.assertNotIn(
            "resolves", unbounded[0],
            "an unbounded route must carry no address, or the invented one "
            "reads as a route that was checked and missed")
        self.assertEqual(
            [e["region"] for e in routes["invoked"]
             if e["region"] == "MRCF"], [],
            "MRCF resolved to 0x84 and was cleared, on a base no committed "
            "input places")


class WhatItDoesNotClaim(unittest.TestCase):
    """The scope the docstring promises, asserted rather than trusted.

    Every sentence this change makes about the writer is scoped to the ASL.
    That scope is not a stylistic choice -- `0x07D0` and `0x07D1` keep
    `unknown-not-absent-DO-NOT-WRITE-BLIND`, and a tool that could be read as
    grading them would undercut that -- so the two things worth holding are
    that it never opens an image, and that running it changes nothing on disk.
    The second is what makes "no `status:` moved" structural rather than a
    promise: measured on the tree after a run rather than grepped for a write
    mode, because `--self-test` writes scratch fixtures on purpose and a grep
    cannot tell one from a committed input.
    """

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(TOOLS, "check_dsdt_ecmg_pair.py"),
                  encoding="utf-8") as handle:
            cls.source = handle.read()

    def test_it_opens_no_firmware_image(self):
        for forbidden in ("GMxMGxx_11.800", "ec/firmware", "subprocess",
                          "urllib", "socket"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.source)

    def test_it_reads_only_the_two_committed_inputs(self):
        # `registers.yaml` is the file a status change would live in, so its
        # absence is what makes this a report rather than a grader.
        for forbidden in ("registers.yaml", "xdata-registers"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.source)

    def test_running_it_leaves_the_committed_inputs_untouched(self):
        # "No `status:` moved" is structural rather than a promise: the tool
        # opens its two inputs, reads them, and prints. Asserting that by
        # grepping its source for a write mode cannot work -- `--self-test`
        # writes scratch fixtures on purpose, and a check that cannot tell a
        # scratch file from a committed one would have to be deleted instead
        # of fixed. So the property is measured on the tree: run it, and
        # compare what it was given against what is there afterwards.
        watched = [DSDT, CSV, os.path.join(REPO, "ec", "annotations",
                                           "registers.yaml")]
        before = {path: hashlib.sha256(open(path, "rb").read()).hexdigest()
                  for path in watched}
        done = subprocess.run(
            [sys.executable, os.path.join(TOOLS, "check_dsdt_ecmg_pair.py"),
             "--check", "--print"],
            capture_output=True, text=True, cwd=REPO)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        after = {path: hashlib.sha256(open(path, "rb").read()).hexdigest()
                 for path in watched}
        self.assertEqual(before, after)

    def test_the_status_the_two_bytes_keep_is_named_in_the_docstring(self):
        # The scope statement is only worth anything if it says which status
        # is being left alone, so the docstring has to carry it by name.
        self.assertIn("unknown-not-absent-DO-NOT-WRITE-BLIND", self.source)


if __name__ == "__main__":
    unittest.main()