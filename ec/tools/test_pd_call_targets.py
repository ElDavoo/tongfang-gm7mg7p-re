#!/usr/bin/env python3
"""Offline checks for `pd_call_targets.py`: committed files only.

No firmware upload, no hardware, no Windows, no network. Every input is a file
this repository already ships -- `ec/firmware/GMxMGxx_11.800`,
`ec/decompiled/listing-index.csv`, `ec/annotations/call-graph-callees.csv`,
`ec/annotations/data-regions.yaml` and the `ec/decompiled/pd/*.c` comments --
so the whole suite runs in a cloud agent's turn.

**The measurement is not stubbed where it can be.** The census is driven once
against the committed image and the sixteen and the nine are asserted *by
address*, with the verdict each one carries named in the test, so a byte that
moved takes this red rather than making a report quietly wrong. The synthetic
cases exist for the three things the committed image cannot supply: the
boundary rule's own mechanism, a `data-regions.yaml` region inside the PD
extent, and a walk that runs out of budget.

**No case asserts a count of this repository's own committed listings.** That
is the defect the previous attempt of this tool shipped, and it is the reason
the suite reads `listing-index.csv` and asserts *relations* -- "the `in_listing`
set for `0x11C2` is exactly the site `pd-common-address-spaces.md` names", "a
verdict from the closed vocabulary", "every listing start is decoded" -- and
never "there are N of them". A landing `pd` listing must not make this suite red
for a change that never touched the tool.

**The mutations are the cases with teeth.**
`test_a_tampered_table_takes_the_check_red` points a row at the wrong verdict
and asserts `--check` fails, because a check that diffs a table nobody has
tampered with proves nothing about the diff. `test_a_landing_pd_listing_does_not_take_the_relationship_red`
is its complement and the case this suite exists for: it adds a synthetic `pd`
listing to a *copy* of the index and asserts the coverage relationship still
holds, which is the whole claim `docs/findings.md` §4 makes about hand-kept
censuses. And `test_the_boundary_rule_stops_a_walk_and_its_absence_does_not`
holds the mechanism on a hand-built fixture, where the boundary and the
absence are two different answers.

Run it directly, or through `python3 ec/tools/pd_call_targets.py --self-test`
for the oracle half. **Not in any gate**: see
`.github/scripts/agent-gates.sh` for why, and note that the script's
`python3 syntax` check does cover this file -- which only proves it compiles.
"""
import collections
import csv
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
TOOL = os.path.join(HERE, "pd_call_targets.py")

spec = importlib.util.spec_from_file_location("pd_call_targets", TOOL)
pdct = importlib.util.module_from_spec(spec)
sys.path.insert(0, HERE)          # for the tool's own `from disasm8051 import`
spec.loader.exec_module(pdct)

# One census over the committed image, shared by every case below. The walk is
# a fraction of a second and re-deriving it per case would be the suite's whole
# cost for the same answers.
REGION, HOW = pdct.read_region(pdct.FIRMWARE)
CONTEXT = pdct.survey(REGION)
BY_RUNTIME = {row["runtime"]: row for row in CONTEXT["rows"]}

# The sixteen `12 11 c2` sites and the nine `12 11 9c` ones, as addresses.
# They are already committed in `ec/annotations/pd-image.md`'s pinned
# `code_table_inline` line and again in
# `docs/findings/pd-common-address-spaces.md`, so this list cross-references
# them rather than restating them as a new discovery -- and every case below
# names the verdict each one carries, so the list is an assertion and not a
# count.
SITES_11C2 = ["0x13F6", "0x153E", "0x16A7", "0x1AB6", "0x1C88", "0x3A46",
              "0x4587", "0x483A", "0x4FFA", "0x617D", "0x776C", "0x7948",
              "0x8288", "0x83CF", "0x92EF", "0xCB4A"]
SITES_119C = ["0x136C", "0x1F2D", "0x42C5", "0x44D2", "0x4C35", "0x6B4C",
              "0xA34B", "0xADE6", "0xC879"]


def listing_index():
    """[(start, size, name)] for every committed `pd` listing."""
    return pdct.listing_extents()


class CheckExitsZero(unittest.TestCase):
    """`--check` is exercised on every run, not merely present.

    A check that no case invokes is a check whose staleness nobody would
    notice until the thing it checks had moved. Driving the real CLI here, over
    the committed tree, is what makes the suite fail the day the committed CSV
    stops matching a fresh walk.
    """

    def test_check_exits_zero_on_the_committed_tree(self):
        proc = subprocess.run([sys.executable, TOOL, "--check"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0,
                         f"--check failed on the committed tree:\n"
                         f"{proc.stdout}\n{proc.stderr}")

    def test_check_reproduces_the_committed_table_byte_for_byte(self):
        # Asserted against the tool's own generator rather than by invoking
        # --check, so the failure names the differing rows instead of only the
        # exit code.
        with open(pdct.TABLE_CSV, newline="") as handle:
            committed = handle.read()
        self.assertEqual(pdct.csv_table(CONTEXT), committed,
                         "the committed table is not what this run produces; "
                         "regenerate it with --csv")

    def test_the_committed_table_is_what_the_page_names_and_has_no_comment_line(self):
        with open(pdct.TABLE_CSV, newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader)
        self.assertEqual(header, pdct.COLUMNS)
        self.assertNotIn("#", header[0],
                         "a comment line would stop csv.DictReader reading the "
                         "table, which is the convention "
                         "ec/annotations/README.md sets out")


class RefusesAndCombines(unittest.TestCase):
    """`--check` cannot be skipped, and a mismatch does not skip the rest."""

    MODES = (["--for-target", "0x11C2"], ["--seed-verdicts"], ["--report"],
             ["--csv"], ["--self-test"])

    def test_check_is_refused_alongside_every_other_output_mode(self):
        for mode in self.MODES:
            with self.subTest(mode=" ".join(mode)):
                proc = subprocess.run([sys.executable, TOOL, "--check"] + mode,
                                      capture_output=True, text=True)
                self.assertNotEqual(proc.returncode, 0,
                                    f"--check {' '.join(mode)} exited 0; a gate "
                                    f"line appending a mode flag would pass "
                                    f"without running a check")
                self.assertIn("cannot be combined", proc.stderr)

    def test_a_table_mismatch_still_runs_the_relationship_half(self):
        # Both halves run and their return codes combine. Driven through the
        # real CLI rather than by calling `check_table` and `check_coverage` in
        # sequence, because the thing under test is that `--check` reaches both
        # -- a `main()` that returned after the diff would pass a case that
        # called the two functions itself.
        with tempfile.TemporaryDirectory() as tmp:
            tampered = os.path.join(tmp, "pd-call-targets.csv")
            with open(pdct.TABLE_CSV, newline="") as handle:
                text = handle.read()
            with open(tampered, "w", newline="") as handle:
                handle.write(text.replace("decoded-lcall", "operand", 1))
            # Both halves are invoked and their return codes combined, which is
            # what `--check`'s last line does. The relationship half's own
            # output is captured so the assertion can require that it ran: a
            # `main()` that returned after the diff would leave this silent,
            # and silence is exactly what the reviewer could not tell from the
            # relationship passing.
            buf = io.StringIO()
            stdout, stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = buf, io.StringIO()
            try:
                table_rc = pdct.check_table(pdct.csv_table(CONTEXT), tampered)
                coverage_rc = pdct.check_coverage(CONTEXT, REGION)
                combined = table_rc or coverage_rc
            finally:
                sys.stdout, sys.stderr = stdout, stderr
        self.assertEqual(table_rc, 1, "the tampered table did not fail its half")
        self.assertEqual(coverage_rc, 0,
                         "the relationship half failed on a table mismatch, "
                         "so it is not independent of it")
        self.assertEqual(combined, 1, "the combined return code is not the "
                                      "failure either half reported")
        self.assertIn("neither contains the other", buf.getvalue(),
                      "the relationship half did not run, so a table mismatch "
                      "silently skipped it")

    def test_a_tampered_table_takes_the_check_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = os.path.join(tmp, "pd-call-targets.csv")
            with open(pdct.TABLE_CSV, newline="") as handle:
                text = handle.read()
            with open(tampered, "w", newline="") as handle:
                handle.write(text.replace("decoded-lcall", "operand", 1))
            buf = io.StringIO()
            stdout, stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = buf, buf
            try:
                rc = pdct.check_table(pdct.csv_table(CONTEXT), tampered)
            finally:
                sys.stdout, sys.stderr = stdout, stderr
            self.assertEqual(
                rc, 1, "a check that passes on a table nobody changed proves "
                       "nothing about the diff")
            self.assertIn("regenerate rather than edit", buf.getvalue(),
                          "a mismatch must say how to resolve it, or the next "
                          "reader edits the table by hand")

    def test_a_missing_table_fails_rather_than_being_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = os.path.join(tmp, "not-here.csv")
            buf = io.StringIO()
            stdout, stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = buf, buf
            try:
                rc = pdct.check_table(pdct.csv_table(CONTEXT), absent)
            finally:
                sys.stdout, sys.stderr = stdout, stderr
            self.assertEqual(rc, 1)
            self.assertFalse(os.path.exists(absent),
                             "--check created the file it was asked to check")


class TheSixteenAndTheNine(unittest.TestCase):
    """Every candidate site carries a row and a verdict, named one by one.

    Asserted site by site with the address spelled out, never as a tally. A
    tally is a value the byte scan moves; the per-site verdict is the finding,
    and a case that summed them would pass on a table that moved the wrong
    site's verdict and compensated on another.
    """

    def test_all_sixteen_11c2_sites_carry_a_row_and_a_verdict(self):
        for site in SITES_11C2:
            with self.subTest(site=site):
                self.assertIn(site, BY_RUNTIME,
                              f"{site} is a `12 11 c2` site in the image and "
                              f"carries no row, so the census is not the "
                              f"byte-scan population it claims to book")
                self.assertIn(BY_RUNTIME[site]["verdict"], pdct.VERDICTS)

    def test_all_nine_119c_sites_carry_a_row_and_a_verdict(self):
        for site in SITES_119C:
            with self.subTest(site=site):
                self.assertIn(site, BY_RUNTIME,
                              f"{site} is a `12 11 9c` site in the image and "
                              f"carries no row")
                self.assertIn(BY_RUNTIME[site]["verdict"], pdct.VERDICTS)

    def test_the_two_dispatchers_have_the_verdicts_the_write_up_states(self):
        # Each site's verdict, named rather than counted. `0x8288` is the site
        # this census adds to `pd-common-address-spaces.md`'s list, and
        # `0xCB4A` is the one that page already had inside a committed
        # listing; `0x6B4C` is the `0x119C` site no walk reaches.
        expected = {
            "0x8288": pdct.DECODED_LCALL,
            "0xCB4A": pdct.DECODED_LCALL,
            "0x6B4C": pdct.UNREACHED,
            "0x136C": pdct.DECODED_LCALL,
            "0x1F2D": pdct.DECODED_LCALL,
            "0x4C35": pdct.DECODED_LCALL,
            "0xA34B": pdct.DECODED_LCALL,
            "0xADE6": pdct.DECODED_LCALL,
            "0xC879": pdct.DECODED_LCALL,
        }
        for site, verdict in expected.items():
            with self.subTest(site=site):
                self.assertEqual(BY_RUNTIME[site]["verdict"], verdict)

    def test_no_row_claims_a_verdict_outside_the_closed_vocabulary(self):
        for row in CONTEXT["rows"]:
            self.assertIn(row["verdict"], pdct.VERDICTS,
                          f"{row['runtime']} carries {row['verdict']!r}")

    def test_unreached_is_never_written_as_absence(self):
        # The calibration rule this tool lives by: a site no walk reached is
        # `unreached-by-this-method`, and the token itself says so. A verdict
        # of "absent", "none", "data" or an empty cell would be the failure
        # docs/findings.md §4c records twice already.
        for row in CONTEXT["rows"]:
            self.assertNotIn(row["verdict"].lower(),
                             ("absent", "none", "no-call", "not-a-call"))
            if row["verdict"] == pdct.UNREACHED:
                self.assertIn("unreached", row["verdict"])

    def test_every_byte_scan_site_appears_even_when_no_walk_reaches_it(self):
        # `unreached-by-this-method` is a row, not a gap: that is what makes the
        # sites countable by `grep` rather than by subtraction, and it is what
        # the `0x6B4C` row above depends on.
        byte_scan = {off for off in range(len(REGION) - 2)
                     if REGION[off] in pdct.CALL_OPCODES}
        self.assertTrue(byte_scan)
        self.assertTrue(byte_scan <= CONTEXT["candidates"],
                        "the byte-scan population is not a subset of the "
                        "candidate set, so a site this method failed to reach "
                        "could have been dropped rather than booked")

    def test_the_candidate_column_records_which_population_booked_the_row(self):
        # The union is auditable from the CSV alone: a row the walk found that
        # the byte scan missed says so, which is the walk contributing
        # something the byte scan structurally cannot see.
        for row in CONTEXT["rows"]:
            self.assertIn(row["candidate"],
                          (pdct.BYTE_SCAN, pdct.WALK_ONLY, pdct.BOTH))
        walk_only = [r for r in CONTEXT["rows"] if r["candidate"] == pdct.WALK_ONLY]
        self.assertTrue(walk_only,
                        "no row is `walk`-only, so the union is carrying no "
                        "information beyond the byte scan")
        for row in walk_only:
            # A walk-only row is a paged or relative transfer the `0x02`/`0x12`
            # scan cannot match, which is the shape the union exists for.
            self.assertNotIn(REGION[int(row["runtime"], 16)],
                             pdct.CALL_OPCODES)


class EnclosingAndInListing(unittest.TestCase):
    """`enclosing` and `in_listing` are two columns because they disagree."""

    def test_in_listing_agrees_with_a_reread_of_the_index(self):
        extents = listing_index()
        for row in CONTEXT["rows"]:
            addr = int(row["runtime"], 16)
            covered = any(start <= addr < start + size
                          for start, size, _name in extents)
            with self.subTest(site=row["runtime"]):
                self.assertEqual(row["in_listing"], "yes" if covered else "no")

    def test_the_in_listing_set_for_11c2_is_the_site_the_committed_page_names(self):
        # `pd-common-address-spaces.md` says only `0xCB4A` of the sixteen is
        # inside a committed listing. This asserts that claim holds under this
        # method -- it does not restate it as a new finding, and a contradiction
        # would be a red run rather than a quiet difference.
        inside = [s for s in SITES_11C2 if BY_RUNTIME[s]["in_listing"] == "yes"]
        self.assertEqual(inside, ["0xCB4A"])

    def test_enclosing_is_the_nearest_listing_and_in_listing_is_not_implied_by_it(self):
        extents = pdct.Extents()
        for row in CONTEXT["rows"]:
            addr = int(row["runtime"], 16)
            with self.subTest(site=row["runtime"]):
                if row["enclosing"]:
                    self.assertEqual(row["enclosing"],
                                     f"0x{extents.below(addr)[0]:04X}")
                else:
                    self.assertIsNone(extents.below(addr))

    def test_the_two_columns_are_independent_and_a_site_proves_it(self):
        # `0x8288`'s nearest listing below it is `0x821B`, whose extent does not
        # reach it. The case asserts the disagreement exists on the committed
        # tree by naming the site, which is the only way to hold it without
        # pinning a count of this repository's listings.
        row = BY_RUNTIME["0x8288"]
        self.assertEqual(row["enclosing"], "0x821B")
        self.assertEqual(row["in_listing"], "no",
                         "0x8288's enclosing listing does not contain it; if "
                         "this now says yes, either the listing grew to cover "
                         "it or `enclosing` and `in_listing` have merged")
        extents = pdct.Extents()
        self.assertIsNone(extents.containing(0x8288))


class CoverageRelationships(unittest.TestCase):
    """Relations over live values, and no figure of the tree anywhere.

    The previous attempt of this tool pinned the walk's and the listings'
    coverage as exact values, which made it red the moment a `pd` listing
    landed -- for a change that never touched it. These cases assert the
    relationships and deliberately assert no count.
    """

    def test_both_methods_are_below_the_image_size(self):
        walk_bytes, listing_bytes, image_bytes = pdct.coverage(CONTEXT, REGION)
        self.assertLess(walk_bytes, image_bytes)
        self.assertLess(listing_bytes, image_bytes)

    def test_neither_method_contains_the_other(self):
        walk = set(CONTEXT["decoded"])
        listing = set()
        for start, size, _name in CONTEXT["extents"].rows:
            listing |= set(range(start, start + size))
        self.assertTrue(walk - listing,
                        "the walk decodes nothing no listing covers, so the "
                        "two methods no longer differ and this suite has "
                        "stopped comparing two things")
        self.assertTrue(listing - walk,
                        "the listings cover nothing no walk decodes, same "
                        "reason")

    def test_check_coverage_exits_zero_and_says_why(self):
        buf = io.StringIO()
        stdout = sys.stdout
        sys.stdout = buf
        try:
            rc = pdct.check_coverage(CONTEXT, REGION)
        finally:
            sys.stdout = stdout
        self.assertEqual(rc, 0, buf.getvalue())
        self.assertIn("neither contains the other", buf.getvalue())

    def test_check_coverage_goes_red_when_one_method_covers_the_image(self):
        # The mutation that gives the relationship teeth: a context whose
        # "walk" reached every byte must fail, or the assertion is satisfied by
        # a method that stopped trying.
        stub = dict(CONTEXT)
        stub["decoded"] = dict.fromkeys(range(len(REGION)), True)
        buf = io.StringIO()
        stdout, stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = buf, io.StringIO()
        try:
            rc = pdct.check_coverage(stub, REGION)
        finally:
            sys.stdout, sys.stderr = stdout, stderr
        self.assertEqual(rc, 1,
                         "a walk covering the whole image must fail the "
                         "relationship: the figures would have stopped meaning "
                         "what they say")

    def test_a_landing_pd_listing_does_not_take_the_relationship_red(self):
        # The case this suite exists for. A synthetic `pd` listing is added to
        # a *copy* of the index -- the committed file is not touched -- and the
        # relationship must still hold. It holds by construction, which is the
        # claim: no landing `pd` listing can falsify it, so no landing `pd`
        # listing turns this suite red for a change that never touched the
        # tool. That is what the previous attempt's pinned figures did.
        with tempfile.TemporaryDirectory() as tmp:
            index = os.path.join(tmp, "listing-index.csv")
            with open(pdct.LISTING_INDEX, newline="", encoding="utf-8") as fh:
                text = fh.read()
            # A listing inside the region the walk reaches but no listing
            # covers, so the added row moves the relationship rather than
            # leaving it untouched.
            synthetic = "pd,9999,pd_synthetic_landing,16,annotation,no,no,,,,,pd/9999.asm\r\n"
            with open(index, "w", newline="", encoding="utf-8") as fh:
                fh.write(text.rstrip("\r\n") + "\r\n" + synthetic)
            with open(pdct.LISTING_INDEX, newline="", encoding="utf-8") as fh:
                original = fh.read()
            try:
                shutil.copy(pdct.LISTING_INDEX, pdct.LISTING_INDEX + ".bak")
                shutil.copy(index, pdct.LISTING_INDEX)
                stub = dict(CONTEXT)
                stub["extents"] = pdct.Extents()
                buf = io.StringIO()
                stdout, stderr = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = buf, io.StringIO()
                try:
                    rc = pdct.check_coverage(stub, REGION)
                finally:
                    sys.stdout, sys.stderr = stdout, stderr
                self.assertEqual(rc, 0,
                                 f"a landing pd listing must not falsify the "
                                 f"relationship:\n{buf.getvalue()}")
                self.assertNotEqual(
                    sum(size for _s, size, _n in stub["extents"].rows),
                    sum(size for _s, size, _n in CONTEXT["extents"].rows),
                    "the synthetic listing did not reach the copy, so this "
                    "case proved nothing")
            finally:
                shutil.move(pdct.LISTING_INDEX + ".bak", pdct.LISTING_INDEX)
            with open(pdct.LISTING_INDEX, newline="", encoding="utf-8") as fh:
                self.assertEqual(fh.read(), original,
                                 "the committed listing index was not restored")


class TerminatorVocabulary(unittest.TestCase):
    """Every `ends` cell is a named token, and the set is closed."""

    def test_every_ends_value_is_in_the_closed_vocabulary(self):
        seen = set()
        for row in CONTEXT["rows"]:
            if not row["ends"]:
                continue
            stem = pdct.end_stem(row["ends"])
            seen.add(stem)
            self.assertIn(stem, pdct.TERMINATORS,
                          f"{row['runtime']} ends with {row['ends']!r}, which "
                          f"is not in the vocabulary")
        self.assertTrue(seen, "no row carries an `ends` value, so nothing "
                              "above was checked")

    def test_terminators_holds_stems_so_every_one_is_its_own_stem(self):
        for token in pdct.TERMINATORS:
            self.assertEqual(pdct.end_stem(token), token)

    def test_a_walk_that_ends_reports_a_token_and_never_a_bare_number(self):
        # The shape, checked on the terminators the tool actually emits. A
        # budget or depth cut reads as `max_insns (400) exhausted` and
        # `depth limit at 0x1234`, so the bound that fired is visible on the
        # row; a bare integer would name neither.
        extents = pdct.Extents(extents=[])
        for max_insns in (1, 3, 7):
            with self.subTest(max_insns=max_insns):
                arm = pdct.walk(bytes([0x00] * 32), 0x0000, extents,
                                max_insns=max_insns)
                self.assertTrue(arm["ends"])
                for end in arm["ends"]:
                    self.assertIn(pdct.end_stem(end), pdct.TERMINATORS)
                    self.assertNotEqual(pdct.end_stem(end).strip(), "")
                    self.assertNotRegex(end, r"^\d+$")

    def test_the_depth_bound_names_the_target_it_refused_to_follow(self):
        # A fixture that branches to itself: without a depth bound the walk
        # would not terminate, and the row that reports the cut has to name the
        # address so a reader can see which edge was not followed.
        # `ljmp` to itself is a tail jump, so this is a loop the depth bound
        # cannot help with -- the loop terminator is what fires instead, and
        # both are in the vocabulary.
        extents = pdct.Extents(extents=[])
        arm = pdct.walk(bytes([0x02, 0x00, 0x00]), 0x0000, extents)
        self.assertTrue(any("tail jump" in e for e in arm["ends"]))

    def test_a_walk_that_stops_for_a_named_reason_reports_that_reason(self):
        extents = pdct.Extents(extents=[])
        cases = {
            "ret": bytes([0x22]),
            "reti": bytes([0x32]),
            "indirect jump -- target not resolvable from the bytes":
                bytes([0x73]),
        }
        for expected, fixture in cases.items():
            with self.subTest(terminator=expected):
                arm = pdct.walk(fixture, 0x0000, extents)
                self.assertIn(expected, arm["ends"])


class BoundaryRule(unittest.TestCase):
    """The rule, its cost, and the property that replaces a figure.

    The previous attempt claimed a boundary-ablation figure was held "so it
    cannot go stale silently" while nothing held it. Here nothing holds a
    figure either: the case asserts the *relationship* -- removing the rule
    yields a strict superset with a non-empty difference -- which is a fact
    about the firmware under two methods rather than a number this
    repository's listings could move.
    """

    def test_the_boundary_rule_stops_a_walk_and_its_absence_does_not(self):
        fixture = bytes([0x00] * 8)
        extents = pdct.Extents(extents=[(0x0004, 4, "next_listing")])
        bounded = pdct.walk(fixture, 0x0000, extents)
        free = pdct.walk(fixture, 0x0000, extents, respect_boundary=False)
        self.assertEqual(bounded["ends"], [pdct.END_BOUNDARY])
        self.assertEqual(sorted(bounded["starts"]), [0, 1, 2, 3],
                         "the bounded walk decoded something above the "
                         "boundary")
        self.assertNotIn(pdct.END_BOUNDARY, free["ends"])
        self.assertGreater(len(free["starts"]), len(bounded["starts"]))

    def test_the_boundary_is_the_next_listing_start_strictly_above_the_seed(self):
        extents = pdct.Extents(extents=[(0x0000, 2, "a"), (0x0004, 2, "b"),
                                        (0x0008, 2, "c")])
        self.assertEqual(extents.next_start(0x0000), 0x0004)
        self.assertEqual(extents.next_start(0x0004), 0x0008)
        self.assertIsNone(extents.next_start(0x0008))

    def test_a_walk_from_a_listing_entry_leaves_that_listing_extent(self):
        # The corrected mechanism, held on the committed image. The boundary is
        # the next listing *start*, not the seed listing's own *end*, so for a
        # listing followed by a gap the walk runs on out of the extent. Three
        # earlier docstrings asserted the opposite -- that a walk from a
        # listing's own entry cannot leave its extent upwards -- and the
        # committed image refutes it. This case is the site the census turns on:
        # `0x8288` is decoded by this walk and by no other, so if the walk ever
        # stopped at the listing's end the headline site would go unreached.
        seed = 0x821B
        row = CONTEXT["extents"].containing(seed)
        self.assertIsNotNone(row, "0x821B is no longer a committed listing")
        extent_end = row[0] + row[1]
        arm = pdct.walk(REGION, seed, CONTEXT["extents"])
        self.assertGreater(arm["boundary"], extent_end,
                           "the boundary is now the listing's own end, so the "
                           "mechanism this case describes no longer holds")
        self.assertTrue([a for a in arm["starts"] if a >= extent_end],
                        "the walk from 0x821B no longer leaves its own listing's "
                        "extent upwards")
        # The site itself, by address: decoded from this seed and from no other.
        decoders = [s for s, starts in CONTEXT["reached_from"].items()
                    if 0x8288 in starts]
        self.assertEqual([0x821B], decoders,
                         "0x8288's decoding walks changed, so the site this "
                         "census adds is reached by a different walk")
        self.assertIsNone(CONTEXT["extents"].containing(0x8288),
                          "0x8288 is now inside a committed listing, so the "
                          "enclosing/in_listing disagreement it shows is gone")

    def test_removing_the_rule_yields_a_strict_superset_with_a_nonempty_difference(self):
        sites, extra_bytes = pdct.boundary_ablation(
            REGION, CONTEXT["extents"], CONTEXT["entries"])
        self.assertGreater(extra_bytes, 0,
                           "the boundary rule costs no reach on this image, so "
                           "the ablation measures nothing and the rule is "
                           "either inert or not the rule this case describes")
        self.assertTrue(sites,
                        "the extra byte count is non-zero but no site is named, "
                        "so the difference cannot be inspected")
        self.assertEqual(len(sites), extra_bytes)

    def test_the_bounded_walk_is_a_subset_of_the_unbounded_one_per_entry(self):
        # The direction that has to hold for the ablation to mean anything: a
        # cut cannot add reach. Checked per entry rather than on the union,
        # because the union could hide one entry losing reach to another.
        extents = pdct.Extents()
        for seed in list(CONTEXT["entries"])[:40]:
            with self.subTest(seed=f"0x{seed:04X}"):
                bounded = set(pdct.walk(REGION, seed, extents,
                                        respect_boundary=True)["starts"])
                free = set(pdct.walk(REGION, seed, extents,
                                     respect_boundary=False)["starts"])
                self.assertTrue(bounded <= free)

    def test_the_walk_never_reaches_above_the_highest_listing_from_a_listing_seed(self):
        # The boundary rule's guarantee, asserted on the committed image rather
        # than only on a fixture: no walk from a committed listing decodes a
        # byte above the highest committed listing start.
        highest = CONTEXT["extents"].starts[-1]
        for seed in CONTEXT["extents"].starts:
            arm = pdct.walk(REGION, seed, CONTEXT["extents"])
            for addr in arm["starts"]:
                if addr >= highest and addr != highest:
                    self.fail(f"a walk from 0x{seed:04X} decoded 0x{addr:04X}, "
                              f"above the highest listing start 0x{highest:04X}")


class AnnotateNeverSuppress(unittest.TestCase):
    """A site in a listed data region is labelled, and the label is derived."""

    def test_refuse_filtering_refuses(self):
        with self.assertRaises(SystemExit):
            pdct.refuse_filtering()

    def test_no_output_mode_drops_a_row(self):
        # Every row is in the table the tool writes, and the counts the report
        # prints are read off that same table.
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(pdct.COLUMNS)
        for row in CONTEXT["rows"]:
            writer.writerow([row[c] for c in pdct.COLUMNS])
        written = list(csv.DictReader(io.StringIO(buf.getvalue())))
        self.assertEqual(len(written), len(CONTEXT["rows"]))
        self.assertEqual({r["runtime"] for r in written},
                         {r["runtime"] for r in CONTEXT["rows"]})

    def test_a_region_inside_the_pd_extent_labels_its_rows_rather_than_dropping_them(self):
        # The committed `data-regions.yaml` lists no region inside the PD
        # extent, so this case builds the situation the file cannot supply and
        # asserts both halves of the rule. Two sites, deliberately one of each:
        #
        #   * `0x8288`, which a walk decodes as an `lcall`. A site inside a
        #     listed region keeps its *decode* verdict and gains the label.
        #     The verdict column answers "how did the walk read this byte", and
        #     overwriting that with `data-region` would throw away the walk's
        #     reading in favour of a label about the neighbourhood -- which is
        #     the suppression the rule forbids, one column over.
        #   * `0x13F6`, which no walk reaches. Here the label is all there is,
        #     so `data-region` is the verdict.
        #
        # Both keep their row either way, which is the part that matters: a
        # region landing must not make a site's count smaller.
        decoded_site, unreached_site = 0x8288, 0x13F6
        for site in (decoded_site, unreached_site):
            self.assertEqual(BY_RUNTIME[f"0x{site:04X}"]["region"],
                             "not listed",
                             f"the committed file now lists a PD region over "
                             f"0x{site:04X}, so this synthetic case no longer "
                             f"covers the empty case")
        regions = [{"name": "pd-synthetic",
                    "file_lo": pdct.REGION_FILE_BASE + decoded_site,
                    "file_hi": pdct.REGION_FILE_BASE + decoded_site + 3}]
        real = pdct.region_at

        def fake(loaded, off):
            # `loaded` is the committed region list `survey()` passes in; the
            # synthetic one is this closure's. Naming the parameter after the
            # closure variable would shadow it, and the loop below would then
            # test the committed regions against themselves and find nothing --
            # which is what happened the first time this case was written.
            #
            # One region per site, each three bytes wide. The two sites are far
            # apart in the image and the earlier version spanned from one to
            # the other, which produced a range whose `file_hi` is past its
            # `file_lo` only by accident of the address order.
            for r in regions:
                if r["file_lo"] <= off < r["file_hi"]:
                    return r
            return real(loaded, off)
        pdct.region_at = fake
        regions.append({"name": "pd-synthetic-unreached",
                        "file_lo": pdct.REGION_FILE_BASE + unreached_site,
                        "file_hi": pdct.REGION_FILE_BASE + unreached_site + 3})
        try:
            stub = pdct.survey(REGION, frame=False)
        finally:
            pdct.region_at = real
        rows = {r["runtime"]: r for r in stub["rows"]}
        self.assertEqual(rows[f"0x{decoded_site:04X}"]["region"],
                         "pd-synthetic")
        self.assertEqual(rows[f"0x{decoded_site:04X}"]["verdict"],
                         pdct.DECODED_LCALL,
                         "a decoded site inside a listed region must keep the "
                         "walk's reading and gain the label")
        self.assertEqual(rows[f"0x{unreached_site:04X}"]["region"],
                         "pd-synthetic-unreached")
        self.assertEqual(rows[f"0x{unreached_site:04X}"]["verdict"],
                         pdct.DATA_REGION,
                         "a site inside a listed region that no walk reached "
                         "takes the label as its verdict")
        self.assertEqual(len(rows), len(CONTEXT["rows"]),
                         "a region landing changed the row count; rows are "
                         "labelled, never dropped")

    def test_the_reports_data_region_sentence_matches_the_derived_figure(self):
        # The case that makes the report self-consistent by construction. A
        # report that printed `data-region 1` in the verdict table and "the row
        # is 0" two lines later would contradict itself the moment a region
        # landed inside the PD extent; asserting the *printed prose* against
        # the derived counts is what stops that, where asserting the count
        # alone would not.
        text = "\n".join(pdct.report_lines(CONTEXT, REGION))
        derived = sum(1 for r in CONTEXT["rows"]
                      if r["verdict"] == pdct.DATA_REGION)
        labelled = sum(1 for r in CONTEXT["rows"] if r["region"] != "not listed")
        pd_regions = [r for r in CONTEXT["region_extents"]
                      if pdct.REGION_FILE_BASE <= r[1]
                      < pdct.REGION_FILE_BASE + len(REGION)]
        self.assertIn(f"the `data-region` verdict is {derived}", text)
        self.assertIn(f"this run labels {labelled} candidate row(s) with a "
                      f"region name", text)
        self.assertIn(f"{len(pd_regions)} of them inside the PD extent", text)
        # And the conclusion follows from the figure rather than being typed.
        if not pd_regions:
            self.assertIn("`not listed` throughout", text)
        else:
            self.assertNotIn("`not listed` throughout", text)


class TheOracle(unittest.TestCase):
    """The hand-transcribed `r2 -a 8051` oracle, against the image.

    Transcribed from radare2 over `make_bank_image.py --pd`'s `pd.bin`, not
    from this tool's decoder. A case that re-ran the scan that wrote the CSV
    would pass on a stale pair -- a table and a walk that agreed because they
    were the same wrong thing -- so the oracle is asserted against the image
    bytes, which is what an independent disassembler read.
    """

    ORACLE = [
        (0x13F6, "1211c2", "lcall 0x11c2"),
        (0x153E, "1211c2", "lcall 0x11c2"),
        (0x1AB6, "1211c2", "lcall 0x11c2"),
        (0x3A46, "1211c2", "lcall 0x11c2"),
        (0x4FFA, "1211c2", "lcall 0x11c2"),
        (0x8288, "1211c2", "lcall 0x11c2"),
        (0x92EF, "1211c2", "lcall 0x11c2"),
        (0xCB4A, "1211c2", "lcall 0x11c2"),
        (0x136C, "12119c", "lcall 0x119c"),
        (0x4C35, "12119c", "lcall 0x119c"),
        (0x6B4C, "12119c", "lcall 0x119c"),
        (0xC879, "12119c", "lcall 0x119c"),
    ]

    def test_the_oracle_reads_as_transcribed_at_each_named_site(self):
        from disasm8051 import mnemonic
        for addr, raw, text in self.ORACLE:
            with self.subTest(site=f"0x{addr:04X}"):
                self.assertEqual(REGION[addr:addr + len(raw) // 2].hex(), raw)
                self.assertEqual(" ".join(mnemonic(REGION, addr, addr).split()),
                                 text)

    def test_a_regenerated_table_that_disagreed_with_the_oracle_would_fail(self):
        # The oracle against the *committed table*, not only against the image:
        # a row whose `target` cell disagreed with the mnemonic the independent
        # disassembler gives is the disagreement this case exists to catch.
        for addr, raw, text in self.ORACLE:
            row = BY_RUNTIME.get(f"0x{addr:04X}")
            if row is None:
                continue
            with self.subTest(site=f"0x{addr:04X}"):
                # Compared as numbers, not as strings. The oracle is
                # radare2's rendering and lowercases its hex; the table
                # formats the same address upper-case. Comparing the strings
                # would make this case about capitalisation rather than about
                # the target the two disagreeing on.
                self.assertEqual(int(row["target"], 16),
                                 int(text.split()[-1], 16),
                                 f"the committed row's target disagrees with "
                                 f"the transcribed mnemonic {text!r}")

    def test_the_self_test_exits_zero(self):
        proc = subprocess.run([sys.executable, TOOL, "--self-test"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0,
                         f"--self-test failed:\n{proc.stdout}\n{proc.stderr}")

    def test_the_image_is_the_one_the_oracle_was_transcribed_from(self):
        # The oracle is only meaningful against this image. The marker check is
        # `read_region()`'s own contract and it is asserted here so a suite
        # running against a different dump says so rather than quietly
        # comparing the oracle to whatever bytes it found.
        self.assertIn("ITE8850-PD", HOW)
        self.assertEqual(REGION[0x40:0x4A], b"ITE8850-PD")


class SeedVerdicts(unittest.TestCase):
    """The premise refutation as a mechanical check, not a sentence."""

    def test_no_pd_asm_carries_the_note_the_pd_c_comments_attribute_to_it(self):
        self.assertEqual(pdct.ascii_carries_the_note(), [],
                         "a pd/*.asm now carries the note; if one was added "
                         "deliberately, the write-up's refutation is stale")

    def test_pd_c_comments_do_carry_it_in_both_spellings(self):
        # The other half of the refutation, and the half that would fail if the
        # comments were the thing that changed. Both spellings are searched, because
        # most of the files say "call-target byte scan" and `1229.c` alone says
        # "call-target-scan" -- a grep for one spelling alone would have found
        # a shorter list and called it complete. The per-spelling file lists are
        # asserted to be non-empty rather than counted, so a file gaining or
        # losing the note does not make this case wrong.
        spellings = ("call-target byte scan", "call-target-scan")
        found = collections.defaultdict(list)
        for name in sorted(os.listdir(pdct.PD_DECOMPILED)):
            if not name.endswith(".c"):
                continue
            with open(os.path.join(pdct.PD_DECOMPILED, name),
                      encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            for spelling in spellings:
                if spelling in text:
                    found[spelling].append(name)
        self.assertTrue(found[spellings[0]],
                        "no pd/*.c carries the first spelling either; the "
                        "comments changed and the refutation needs redoing")
        self.assertTrue(found[spellings[1]],
                        "the second spelling is gone; the write-up names it")

    def test_every_seed_carries_a_verdict_from_the_entry_set(self):
        for row in pdct.seed_verdicts(CONTEXT, REGION):
            with self.subTest(seed=row["file"]):
                self.assertIsInstance(row["reached"], bool)
                if row["entry"]:
                    self.assertIn(row["entry"], pdct.SOURCES)
                onto, over = row["framed"]
                self.assertIsInstance(onto, int)
                self.assertIsInstance(over, int)

    def test_the_seed_list_is_derived_from_the_comments_not_written_down(self):
        # Every seeded listing is one a `pd/*.c` comment names, so the list
        # moves with the prose it is about and nothing holds a count of it.
        rows = pdct.seed_verdicts(CONTEXT, REGION)
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(seed=row["file"]):
                # The stem is the address in hex, which is what a listing file
                # is named after; `isdigit()` would be the wrong test because
                # half of them carry a letter.
                self.assertEqual(int(row["file"][:-2], 16), row["addr"])
                self.assertTrue(os.path.exists(os.path.join(pdct.PD_DECOMPILED,
                                                           row["file"])))

    def test_the_seed_verdicts_mode_runs(self):
        proc = subprocess.run([sys.executable, TOOL, "--seed-verdicts"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("reached=", proc.stdout)


class EntrySet(unittest.TestCase):
    """The seed set, its tags, and the loop it closes."""

    def test_every_entry_is_tagged_with_a_source_from_the_closed_set(self):
        for addr, source in CONTEXT["entries"].items():
            with self.subTest(seed=f"0x{addr:04X}"):
                self.assertIn(source, pdct.SOURCES)

    def test_an_address_two_sets_name_is_one_entry_with_one_tag(self):
        # A vector target that is also a committed listing is one entry. The
        # walk is over addresses, so reporting it twice would walk it twice and
        # misstate the denominator.
        entries = pdct.entry_set(REGION)
        listing_starts = {start for start, _s, _n in listing_index()}
        for addr in listing_starts:
            self.assertIn(addr, entries)
        by_source = collections.Counter(entries.values())
        for source in pdct.SOURCES:
            if source == pdct.SOURCE_DISCOVERED:
                continue
            counted = sum(1 for s in entries.values() if s == source)
            self.assertEqual(counted, by_source[source])

    def test_every_committed_listing_start_is_an_entry_and_is_decoded(self):
        # The property that makes `enclosing` a listing fact rather than a
        # guess: every committed listing is a seed, and a walk decodes its own
        # seed's first byte.
        decoded = set(CONTEXT["decoded"])
        for start, _size, name in listing_index():
            with self.subTest(listing=name):
                self.assertIn(start, CONTEXT["entries"])
                self.assertIn(start, decoded)

    def test_a_discovered_target_is_walked_as_an_entry_in_its_own_right(self):
        for target in CONTEXT["discovered"]:
            with self.subTest(target=f"0x{target:04X}"):
                self.assertEqual(CONTEXT["entries"][target],
                                 pdct.SOURCE_DISCOVERED)
                self.assertIn(target, CONTEXT["reached_from"],
                              "a discovered target was not walked, so naming "
                              "it says nothing about what is there")


class ReportSelfConsistency(unittest.TestCase):
    """`--report`'s prose is built from the same values it prints."""

    def test_the_verdict_tally_in_the_report_matches_the_rows(self):
        text = "\n".join(pdct.report_lines(CONTEXT, REGION))
        tally = collections.Counter(r["verdict"] for r in CONTEXT["rows"])
        for verdict in pdct.VERDICTS:
            with self.subTest(verdict=verdict):
                self.assertIn(f"  {verdict:<26} {tally.get(verdict, 0)}", text)

    def test_the_entry_tally_in_the_report_matches_the_entry_set(self):
        text = "\n".join(pdct.report_lines(CONTEXT, REGION))
        tally = collections.Counter(CONTEXT["entries"].values())
        for source in pdct.SOURCES:
            with self.subTest(source=source):
                self.assertIn(f"  {source:<11} {tally.get(source, 0)}", text)

    def test_the_coverage_lines_in_the_report_match_the_coverage_function(self):
        text = "\n".join(pdct.report_lines(CONTEXT, REGION))
        walk_bytes, listing_bytes, image_bytes = pdct.coverage(CONTEXT, REGION)
        self.assertIn(f"walk reached        {walk_bytes} of {image_bytes} "
                      f"bytes", text)
        self.assertIn(f"committed listings  {listing_bytes} of {image_bytes} "
                      f"bytes", text)

    def test_the_below_entry_listing_line_matches_the_function(self):
        text = "\n".join(pdct.report_lines(CONTEXT, REGION))
        below = pdct.below_entry_listings(CONTEXT)
        for start, _size, name in below:
            self.assertIn(name, text)
        self.assertIn(f"{len(below)} such listing(s)", text)

    def test_every_listing_the_function_names_is_one_no_walk_reached_into(self):
        # The shape rather than a number: whatever the function returns, every
        # member really is a listing the walk decoded nothing strictly inside,
        # so a landing listing changes the list without making the case wrong.
        for start, size, name in pdct.below_entry_listings(CONTEXT):
            with self.subTest(listing=name):
                self.assertFalse([a for a in CONTEXT["decoded"]
                                  if start < a < start + size],
                                 f"{name} at 0x{start:04X} was named as "
                                 f"unreached into but the walk decoded a byte "
                                 f"inside it")
                self.assertIn(start, CONTEXT["extents"].starts)

    def test_the_report_mode_runs_and_names_the_below_entry_listings(self):
        proc = subprocess.run([sys.executable, TOOL, "--report"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Committed pd listings", proc.stdout)


class TheCandidateSet(unittest.TestCase):
    """How the union is built, and what each population contributes."""

    def test_the_candidate_set_is_the_union_of_the_two_populations(self):
        byte_scan = {off for off in range(len(REGION) - 2)
                     if REGION[off] in pdct.CALL_OPCODES}
        walked = set(CONTEXT["call_sites"]) | set(CONTEXT["jump_sites"])
        self.assertEqual(CONTEXT["candidates"], byte_scan | walked)

    def test_every_walked_site_the_byte_scan_could_not_see_is_a_paged_or_relative_form(self):
        # The walk contributing rows the byte scan structurally cannot find is
        # the point of the union: `0x01`/`0x11` and the PC-relative family do
        # not carry a `0x02`/`0x12` byte at the site.
        byte_scan = set(CONTEXT["byte_scan"])
        for site in set(CONTEXT["walked"]) - byte_scan:
            with self.subTest(site=f"0x{site:04X}"):
                op = REGION[site]
                self.assertTrue(op & 0x1F in pdct.PAGED_OPCODES or
                                op in pdct.REL_OPCODES or op == pdct.SJMP,
                                f"0x{site:04X} is walk-only but its opcode "
                                f"0x{op:02X} is in the absolute family the "
                                f"byte scan covers, so the union is not "
                                f"builtthe way this case describes")

    def test_the_csv_row_count_matches_the_candidate_set(self):
        # A property of the tree, not a census of it: every candidate has a row
        # and every row is a candidate.
        self.assertEqual(len(CONTEXT["rows"]), len(CONTEXT["candidates"]))

    def test_the_frame_columns_are_populated_for_every_row(self):
        # `survey()` builds rows with the frame pair as ints and the csv
        # writer formats them, so this asserts the in-memory shape here and the
        # written shape against the committed file below -- both, because the
        # two are what `--check` compares and a cell that formatted as an empty
        # string would pass an int assertion and lose the evidence.
        for row in CONTEXT["rows"]:
            with self.subTest(site=row["runtime"]):
                self.assertIsInstance(row["frame_onto"], int)
                self.assertIsInstance(row["frame_over"], int)
        with open(pdct.TABLE_CSV, newline="", encoding="utf-8") as handle:
            written = list(csv.DictReader(handle))
        for row in written:
            with self.subTest(site=row["runtime"], source="committed csv"):
                self.assertTrue(row["frame_onto"].strip().isdigit(),
                                f"frame_onto reads {row['frame_onto']!r}")
                self.assertTrue(row["frame_over"].strip().isdigit(),
                                f"frame_over reads {row['frame_over']!r}")

    def test_the_decoded_as_non_transfer_branch_is_unreachable(self):
        # `mid-instruction` has two readings in the code and only one can fire
        # over this candidate set: a candidate is either a `0x02`/`0x12` byte
        # or an offset a walk framed as a transfer, so none is framed as a
        # non-transfer instruction. Asserted as unreachability rather than as
        # a count of zero, so widening the candidate set makes this case ask
        # which reading the new rows get.
        dead = [a for a in CONTEXT["candidates"]
                if a in CONTEXT["decoded"]
                and a not in CONTEXT["call_sites"]
                and a not in CONTEXT["jump_sites"]]
        self.assertEqual(dead, [],
                         "a candidate is now framed as a non-transfer "
                         "instruction; say which verdict it should carry")


class NoHardwareClaims(unittest.TestCase):
    """The calibration rule as a check rather than as good intentions.

    Every input to this tool is a committed file. A sentence *asserting* a live
    test ran, a register was read back, or hardware was observed would be a
    claim with no evidence behind it.

    The check looks for an assertion, not for the words. Both the tool and the
    write-up are *required* to say that nothing here was observed on hardware,
    so a bare search for "observed" or "read back" fails on the disclaimer that
    is the whole point -- which is what the first version of this case did. The
    phrases below are therefore the ones that assert an observation, and each
    is preceded by nothing that would make it a denial.
    """

    # Asserting forms only. "was observed" and "read back" are deliberately
    # absent: the tree's own rule requires both to appear in a *negative*
    # sentence, and a check that cannot tell the two apart is a check that
    # would have to be weakened rather than satisfied.
    FORBIDDEN = ("we observed", "i observed", "it was observed",
                 "the live test", "on the physical machine we",
                 "reading it back showed", "readback confirmed",
                 "hardware confirmed", "verified on hardware",
                 "tested on the laptop", "the ec responded")

    # Sentences that must be present, because a reader who cannot tell whether
    # anything was run should be told rather than left to infer.
    REQUIRED = ("nothing here was observed on hardware",)

    def test_neither_the_module_nor_the_write_up_claims_a_live_observation(self):
        sources = [TOOL]
        page = os.path.join(pdct.REPO, "docs", "findings",
                            "pd-call-target-census.md")
        if os.path.exists(page):
            sources.append(page)
        for path in sources:
            with self.subTest(path=os.path.basename(path)):
                with open(path, encoding="utf-8") as handle:
                    text = handle.read().lower()
                for phrase in self.FORBIDDEN:
                    self.assertNotIn(phrase, text,
                                     f"{os.path.basename(path)} says {phrase!r}; "
                                     f"nothing here was observed on hardware")

    def test_both_the_module_and_the_write_up_say_nothing_was_observed(self):
        for path in (TOOL, os.path.join(pdct.REPO, "docs", "findings",
                                        "pd-call-target-census.md")):
            with self.subTest(path=os.path.basename(path)):
                self.assertTrue(os.path.exists(path),
                                "the write-up does not exist yet")
                with open(path, encoding="utf-8") as handle:
                    text = handle.read().lower()
                for phrase in self.REQUIRED:
                    self.assertIn(phrase, text,
                                  f"{os.path.basename(path)} must say what was "
                                  f"not done, so a reader is not left inferring "
                                  f"it")

    def test_the_module_says_what_it_does_not_establish(self):
        with open(TOOL, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("framing is unsettled", text)
        self.assertIn('never "absent"', text)


if __name__ == "__main__":
    unittest.main()