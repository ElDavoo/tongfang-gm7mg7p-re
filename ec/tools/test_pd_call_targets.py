#!/usr/bin/env python3
"""Offline checks for pd_call_targets.py: no hardware, and nothing but
committed files.

**The measurement is held by value, not stubbed.** The seed set, the byte-scan
population, the framing evidence and the two coverage figures are asserted
against the committed image and the committed listings, so a byte that moved
takes this suite red rather than letting a report go quietly wrong.

**The oracle is a second decoder's reading, not this tool's.** `R2_ORACLE` in
the module under test is transcribed from `r2 -a 8051` against a
`make_bank_image.py` PD image, and it is asserted against the image rather than
against the scan that wrote the CSV. Without that, a census that graded its own
output would pass whatever the walk decided -- the defect the pinned `--check`
mode exists to catch, and the one a suite that only compared the tool to itself
would let through. `--self-test` covers the oracle; the case here runs it as a
subprocess, because a suite that reports `OK` and then exits 1 is a failure
mode an in-process runner cannot show.

**The refusals and the closed vocabularies are the calibration.** A dump whose
0x20000 region is not the ITE8850-PD image is refused with the offset in the
message rather than reported as an empty region. `refuse_filtering()` is
asserted to raise, because "annotate, never suppress" is a rule in a comment
until a function refuses. And a walk that ends has to name a term from
`walk_branch_arms.py`'s vocabulary plus `next listing boundary` -- a cell a
reader cannot classify is a cell nothing holds.

**The mutations are what make the rest mean anything.** A tool that always
returned `decoded-lcall` would satisfy every count in this suite. Each mutation
below breaks one thing in a scratch copy and asserts the run goes red *and
names the thing*, so a census that had stopped separating verdicts cannot stay
green. A mutation case that only asserted a red run would pass on a checker
that had stopped looking.

**The figures are asserted as relationships, not as values.** The entry count,
the listing count and the two coverage percentages are all properties of
committed files, and CLAUDE.md's rule is that a count of this repository's own
text is not a value any merge should have to edit. So what is held here is
`walk > listings`, `0 < walk < 100%`, and the *per-site* verdicts for the two
named dispatchers -- addresses, which no change to this repository can move.

Read-only: every fixture is the committed image opened for reading or a
`tempfile`, and `TestWritesNothing` holds `git status --porcelain`
byte-identical across a real run.

Not in `.github/scripts/agent-gates.sh`, and cannot be from an agent branch: the
plan stage's push token has no `workflow` scope. It does run under that gate's
`python3 syntax` check, which only proves it compiles.
"""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
# pd_call_targets imports its siblings by bare module name, the way the rest of
# this directory does, so the tool directory goes on the path before the load
# rather than after.
sys.path.insert(0, str(HERE))

import pd_call_targets as pct  # noqa: E402
from data_regions import load as load_data_regions  # noqa: E402

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
INDEX_CSV = HERE.parent / "decompiled" / "listing-index.csv"
CALLEES_CSV = HERE.parent / "annotations" / "call-graph-callees.csv"
SITES_CSV = HERE.parent / "annotations" / "pd-call-targets.csv"
PAGE = ROOT / "docs" / "findings" / "pd-call-target-census.md"
TOOL = HERE / "pd_call_targets.py"

# One survey, read once, shared by every case below. It is the most expensive
# thing this suite does and nothing in it mutates the image, so recomputing it
# per case would buy nothing but a minute.
REGION, _HOW = pct.read_region(str(FIRMWARE))
INDEX_ROWS, CALLEE_ROWS = pct.load_csvs(str(INDEX_CSV), str(CALLEES_CSV))
REGIONS = load_data_regions()
ROWS, CONTEXT = pct.survey(REGION, INDEX_ROWS, CALLEE_ROWS, REGIONS)

# The sixteen `12 11 c2` sites and the nine `12 11 9c` ones, transcribed from
# the image rather than computed, so the suite states which sites it is about
# and a tool that found a different population fails on the addresses and not
# only on the tally. `pd-common-address-spaces.md` prints the first list in this
# spelling.
L11C2 = (0x13F6, 0x153E, 0x16A7, 0x1AB6, 0x1C88, 0x3A46, 0x4587, 0x483A,
         0x4FFA, 0x617D, 0x776C, 0x7948, 0x8288, 0x83CF, 0x92EF, 0xCB4A)
L119C = (0x136C, 0x1F2D, 0x42C5, 0x44D2, 0x4C35, 0x6B4C, 0xA34B, 0xADE6,
         0xC879)

# The eight `pd` listings whose committed `.c` files say the function boundary
# came from a call-target byte scan and is a hypothesis. The suite holds the
# module's list against the files that carry the claim -- in both spellings, see
# `test_the_claim_is_in_two_spellings_...` -- so the two cannot drift: a ninth
# file carrying the sentence would have to be added to both.
SEED_SENTENCE = "call-target byte scan"


def run_tool(*args):
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, check=False)


def rows_for(target):
    return {r["candidate"]: r for r in ROWS if r["target"] == target}


class TheSixteenHaveSixteenAnswers(unittest.TestCase):
    """The issue's payoff, asserted site by site.

    A count passes on the wrong sixteen, so every address is named and every
    one of them is held to a verdict of the closed vocabulary. The two
    `decoded-lcall` sites are named individually as well, because "two of the
    sixteen" is the claim the write-up leads on and a suite that only counted
    `decoded-*` would pass on any two.
    """

    def test_all_sixteen_sites_carry_a_row(self):
        got = rows_for(0x11C2)
        self.assertEqual(sorted(got), list(L11C2),
                         "the 0x11C2 rows are exactly the sixteen sites "
                         "pd-common-address-spaces.md lists")

    def test_all_sixteen_carry_a_verdict_from_the_closed_vocabulary(self):
        for site, row in sorted(rows_for(0x11C2).items()):
            with self.subTest(site="%04X" % site):
                self.assertIn(row["verdict"], pct.VERDICTS)

    def test_the_decoded_sites_are_the_two_named_ones(self):
        decoded = sorted(s for s, r in rows_for(0x11C2).items()
                         if r["verdict"] in pct.DECODED_VERDICTS)
        self.assertEqual(decoded, [0x8288, 0xCB4A],
                         "0x8288 is the site the walk adds and no committed "
                         "listing holds; 0xCB4A is the one that is in one")

    def test_0x8288_is_reached_by_the_walk_seeded_at_0x821b(self):
        """The claim the write-up makes about the one new site.

        Asserted against the walk, not against the table, so a table that
        disagreed with the descent it was derived from fails here.
        """
        walk, _discovered = pct.walk(REGION, [(0x821B, ())],
                                     pct.listing_entries(INDEX_ROWS))
        self.assertIn(0x8288, walk["sites"])
        self.assertEqual(walk["sites"][0x8288], ("lcall", 0x11C2))
        self.assertNotIn(0x8288, pct.listing_starts(REGION),
                         "and no committed `pd` .asm holds that instruction "
                         "start, which is what makes it a new site rather "
                         "than a listing the older file already covered")


class TheNineHaveNineAnswers(unittest.TestCase):
    """The same for `lcall 0x119C`, which the image-wide scan answers too."""

    def test_all_nine_sites_carry_a_row(self):
        self.assertEqual(sorted(rows_for(0x119C)), list(L119C))

    def test_all_nine_carry_a_verdict_from_the_closed_vocabulary(self):
        for site, row in sorted(rows_for(0x119C).items()):
            with self.subTest(site="%04X" % site):
                self.assertIn(row["verdict"], pct.VERDICTS)

    def test_the_one_unreached_site_is_named(self):
        unreached = sorted(s for s, r in rows_for(0x119C).items()
                           if r["verdict"] == pct.VERDICT_UNREACHED)
        self.assertEqual(unreached, [0x6B4C])


class EveryRowAgreesWithTheCommittedListings(unittest.TestCase):
    """`in_listing` recomputed, and the one claim it is not allowed to break."""

    def test_in_listing_agrees_with_a_reread_of_the_asm_files(self):
        streams = pct.listing_starts(REGION)
        wrong = [r["candidate"] for r in ROWS
                 if (r["in_listing"] == "yes")
                 != (r["candidate"] in streams)]
        self.assertEqual(wrong, [],
                         "in_listing must be re-derivable from the exported "
                         "listings, not asserted by the tool that wrote it")

    def test_the_0x11c2_in_listing_set_is_exactly_0xcb4a(self):
        """`pd-common-address-spaces.md`'s claim, held so this change cannot
        quietly contradict it."""
        inside = sorted(s for s, r in rows_for(0x11C2).items()
                        if r["in_listing"] == "yes")
        self.assertEqual(inside, [0xCB4A])

    def test_every_row_is_a_candidate_of_the_byte_scan_or_a_decoded_site(self):
        """The candidate set is the union the docstring claims, checked rather
        than assumed -- a row that is neither would mean a site in the table no
        rule produced."""
        byte_scan = set(pct.candidate_sites(REGION))
        decoded = {r["candidate"] for r in ROWS
                   if r["verdict"] in pct.DECODED_VERDICTS}
        self.assertEqual({r["candidate"] for r in ROWS}, byte_scan | decoded)

    def test_the_verdict_of_a_decoded_site_names_that_opcode(self):
        """A `decoded-ljmp` row whose byte is 0x12 would be a census that had
        lost track of its own decoder."""
        for row in ROWS:
            if row["verdict"] in pct.DECODED_VERDICTS:
                with self.subTest(site="%04X" % row["candidate"]):
                    self.assertEqual(REGION[row["candidate"]],
                                     0x12 if row["verdict"] == "decoded-lcall"
                                     else 0x02)


class TwoCoverageFiguresNotOne(unittest.TestCase):
    """The second thing the issue asked for, held as a relationship.

    The values move whenever a listing lands, so what is asserted is the
    ordering and the bounds, not the numbers. `pd_call_targets.py --check` is
    what holds the numbers themselves.
    """

    def test_the_walk_reaches_more_than_the_listings_do(self):
        self.assertGreater(CONTEXT["decoded_bytes"], CONTEXT["listing_bytes"])

    def test_both_figures_are_below_the_image_size(self):
        total = CONTEXT["image_bytes"]
        self.assertGreater(CONTEXT["decoded_bytes"], 0)
        self.assertLess(CONTEXT["decoded_bytes"], total)
        self.assertLess(CONTEXT["listing_bytes"], total)

    def test_the_listing_figure_is_the_same_one_the_index_records(self):
        """`listing-index.csv`'s `size` column and the listings' own instruction
        streams agree on this tree. Held because a divergence would mean one of
        the two is wrong, and which one is not obvious from the number alone."""
        from_index = sum(int(r["size"], 0) for r in INDEX_ROWS
                         if r["program"] == pct.PROGRAM)
        self.assertEqual(from_index, CONTEXT["listing_bytes"])

    def test_the_report_prints_both_figures_separately_labelled(self):
        out = run_tool("--report").stdout
        self.assertIn("Coverage, and it is two methods'", out)
        self.assertIn("what a stated entry set reaches", out)
        self.assertIn("what has a committed listing for it", out)
        self.assertNotIn("bytes are code.", out.replace(
            'Neither is "these bytes are code.".', ""))

    def test_the_boundary_rule_is_ablation_tested_rather_than_asserted(self):
        """The rule is there so `enclosing` is a listing fact, and the report
        says what dropping it costs. If the ablation stopped running -- say a
        refactor made the unbounded walk raise -- the report's claim about the
        cost would be stale and nothing else here would notice."""
        extra_sites, extra_bytes = CONTEXT["ablation"]
        self.assertIsInstance(extra_sites, list)
        self.assertIsInstance(extra_bytes, int)
        self.assertGreaterEqual(extra_bytes, 0)
        out = run_tool("--report").stdout
        self.assertIn("dropping the boundary rule", out)


class TheVocabulariesAreClosed(unittest.TestCase):
    """Two closed sets, and a cell outside either is a cell nothing holds."""

    def test_every_walk_terminator_names_a_vocabulary_term(self):
        unnamed = [cell for ends in CONTEXT["by_entry"].values()
                   for cell in ends if not pct.ends_vocabulary(cell)]
        self.assertEqual(unnamed, [],
                         "a terminator naming nothing in ENDS_VOCABULARY is a "
                         "cell a reader cannot classify")

    def test_every_rows_ends_cell_is_a_term_or_the_explicit_no_walk(self):
        for row in ROWS:
            with self.subTest(site="%04X" % row["candidate"]):
                if row["ends"] == pct.NO_WALK:
                    self.assertIsNone(row["enclosing"])
                else:
                    self.assertTrue(pct.ends_vocabulary(row["ends"]),
                                    f"ends cell {row['ends']!r} names no term")

    def test_every_rows_verdict_is_in_the_closed_vocabulary(self):
        for row in ROWS:
            with self.subTest(site="%04X" % row["candidate"]):
                self.assertIn(row["verdict"], pct.VERDICTS)

    def test_ends_vocabulary_does_not_truncate_a_longer_term(self):
        """`index past the end of the image` starts with `index`, and
        `next listing boundary` with `next`; a naive prefix match would find a
        shorter term first and the closed-vocabulary check would stop meaning
        anything."""
        self.assertEqual(pct.ends_vocabulary(pct.END_IMAGE), [pct.END_IMAGE])
        self.assertEqual(pct.ends_vocabulary(pct.END_BOUNDARY),
                         [pct.END_BOUNDARY])

    def test_the_data_region_verdict_is_zero_and_says_why(self):
        """A zero that reads as a category would be a claim nobody measured.
        The report has to say that `data-regions.yaml` lists nothing in the PD
        extent, so `not listed` is a fact about the map and not about the
        image."""
        self.assertEqual(CONTEXT["verdicts"]["data-region"], 0)
        self.assertEqual(CONTEXT["data_region_extents"], 0)
        out = run_tool("--report").stdout
        self.assertIn("the annotation map, not about the image", out)


class TheRefusals(unittest.TestCase):
    """What the tool declines to do, held as behaviour rather than as prose."""

    def test_refuse_filtering_raises(self):
        with self.assertRaises(SystemExit):
            pct.refuse_filtering()

    def test_a_dump_that_is_not_the_pd_image_is_refused(self):
        with tempfile.NamedTemporaryFile(suffix=".bin") as fh:
            fh.write(b"\x00" * 0x30000)
            fh.flush()
            with self.assertRaises(pct.Refusal) as caught:
                pct.read_region(fh.name)
        self.assertIn("marker", str(caught.exception))

    def test_a_dump_too_short_to_hold_the_region_is_refused(self):
        with tempfile.NamedTemporaryFile(suffix=".bin") as fh:
            fh.write(b"\x00" * 16)
            fh.flush()
            with self.assertRaises(pct.Refusal) as caught:
                pct.read_region(fh.name)
        self.assertIn("too short", str(caught.exception))

    def test_a_missing_input_csv_is_refused_rather_than_guessed(self):
        with self.assertRaises(pct.Refusal):
            pct.load_csvs(str(HERE / "no-such-index.csv"),
                          str(CALLEES_CSV))

    def test_check_and_csv_cannot_be_combined(self):
        """A check that writes the file it is checking cannot fail on it."""
        out = run_tool("--check", "--csv")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("not combinable", out.stderr)


class CheckHoldsTheTable(unittest.TestCase):
    """`--check` exercised as a command, the way a gate would run it."""

    def test_check_exits_zero_on_the_committed_tree(self):
        out = run_tool("--check")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("reproduces it byte for byte", out.stdout)
        self.assertIn("pinned figure(s) re-derive", out.stdout)

    def test_a_tampered_csv_fails_the_check(self):
        """A `--check` that cannot go red is not a check.

        The committed path is what the tool reads, so the diff is exercised
        through the module's `check_table()` with the *untampered* bytes on disk
        and a tampered string as what "this run produced". Writing the tampered
        text to the scratch path and comparing it against itself would pass on
        a `check_table()` that always returned 0, which is the case the control
        below is here to rule out.
        """
        with open(SITES_CSV, newline="") as f:
            text = f.read()
        self.assertIn(pct.VERDICT_UNREACHED, text)
        tampered = text.replace(pct.VERDICT_UNREACHED, "decoded-lcall", 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / SITES_CSV.name
            with open(path, "w", newline="") as f:
                f.write(text)
            self.assertNotEqual(pct.check_table(tampered, str(path)), 0,
                                "a regenerated table that differs from the "
                                "committed one must fail -- this is what stops "
                                "a stale committed CSV passing forever")
            # The same call with matching bytes is the control.
            self.assertEqual(pct.check_table(text, str(path)), 0)

    def test_the_untouched_table_still_passes_the_same_check(self):
        """The control for the case above: without it, a `check_table()` that
        always returned non-zero would satisfy it."""
        self.assertEqual(pct.check_table(pct.csv_table(ROWS), str(SITES_CSV)),
                         0)

    def test_a_missing_csv_fails_rather_than_being_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / SITES_CSV.name
            self.assertEqual(pct.check_table("anything\n", str(path)), 1)
            self.assertFalse(path.exists(),
                             "--check must not create the table it checks")

    def test_a_figure_the_write_up_gains_without_the_tool_fails(self):
        """`check_figures()` walks the union, so a page that grows a figure the
        tool does not produce is caught -- the drift the union exists for."""
        derived = pct.figures(REGION, ROWS, CONTEXT)
        pinned = dict(derived)
        pinned["a_figure_nobody_derives"] = "7"
        self.assertEqual(pct.check_figures(pinned, derived), 1)

    def test_a_figure_the_write_up_drops_fails(self):
        derived = pct.figures(REGION, ROWS, CONTEXT)
        pinned = {k: v for k, v in derived.items() if k != "walk_coverage_pct"}
        self.assertEqual(pct.check_figures(pinned, derived), 1)

    def test_a_wrong_figure_fails(self):
        derived = pct.figures(REGION, ROWS, CONTEXT)
        pinned = dict(derived)
        pinned["walk_coverage_pct"] = "99.99"
        self.assertEqual(pct.check_figures(pinned, derived), 1)


class TheOracleIsASecondDecoder(unittest.TestCase):
    """The hand transcriptions, run as the command a reader would run."""

    def test_self_test_exits_zero(self):
        out = run_tool("--self-test")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("self-test passed", out.stdout)

    def test_every_oracle_entry_is_one_this_repository_asked_for(self):
        """The transcriptions are r2's reading, and r2 is not run here -- the
        bytes are asserted against the committed image, so an entry whose bytes
        the image does not hold fails. This checks the *other* half: that the
        oracle is not a transcript of this tool's own output."""
        seen = {off for off, _raw, _text in pct.R2_ORACLE}
        self.assertEqual(len(seen), len(pct.R2_ORACLE),
                         "no duplicated offset in R2_ORACLE")
        for off, raw, _text in pct.R2_ORACLE:
            with self.subTest(site="%04X" % off):
                self.assertEqual(REGION[off:off + len(raw)], raw)


class TheSeedHypothesesAreRefuted(unittest.TestCase):
    """The issue's second premise, measured rather than argued.

    The claim is about two things: which files carry the sentence, and what
    `listing-index.csv` records as the seed basis. Both are held here so the
    correction in the write-up cannot rot into a claim nothing checks.
    """

    def test_the_eight_listings_are_the_files_carrying_the_sentence(self):
        """Both spellings, and this case exists because a single-spelling grep
        finds seven: seven `.c` files say "call-target byte scan" and
        `1229.c` says "call-target-scan hypothesis". Matching one literal would
        have dropped the one file the issue names alongside the others."""
        self.assertEqual(pct.seed_claim_files(),
                         sorted("%04X" % a for a in pct.SEED_LISTINGS),
                         "the module's seed list and the .c files that carry "
                         "the claim are the same set")

    def test_the_claim_is_in_two_spellings_and_a_single_one_finds_seven(self):
        directory = HERE.parent / "decompiled" / pct.PROGRAM
        literal = sorted(p.stem for p in directory.glob("*.c")
                         if "call-target byte scan"
                         in p.read_text(errors="replace"))
        self.assertEqual(literal, [f for f in pct.seed_claim_files()
                                   if f != "1229"],
                         "the hyphenated spelling is the only one `1229.c` "
                         "uses, and the write-up's correction quotes both")

    def test_every_seed_listing_is_recorded_as_an_annotation(self):
        basis = {int(r["addr"], 16): r.get("seed_basis")
                 for r in INDEX_ROWS if r["program"] == pct.PROGRAM}
        for addr in pct.SEED_LISTINGS:
            with self.subTest(listing="%04X" % addr):
                self.assertEqual(basis.get(addr), "annotation",
                                 "a seed_basis other than `annotation` would "
                                 "mean the boundary did come from a scan")

    def test_seed_verdicts_reach_and_frame_all_eight(self):
        seeds = pct.seed_verdicts(REGION, ROWS, CONTEXT, INDEX_ROWS)
        self.assertEqual([s["listing"] for s in seeds],
                         list(pct.SEED_LISTINGS))
        for s in seeds:
            with self.subTest(listing="%04X" % s["listing"]):
                self.assertTrue(s["seeded"])
                self.assertTrue(s["reached"])
                onto, over = (int(x) for x in s["frame"].split("/"))
                self.assertGreater(onto, 0)
                self.assertGreater(onto + over, onto)

    def test_seed_verdicts_mode_exits_zero_and_prints_the_column(self):
        out = run_tool("--seed-verdicts")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("seed_basis", out.stdout)
        self.assertIn("seed_basis=annotation", out.stdout)


class TheMutations(unittest.TestCase):
    """What makes the assertions above mean anything.

    A census that returned `decoded-lcall` for every candidate would satisfy
    every count in this file. Each mutation breaks one thing and asserts the
    run goes red *and names it* -- a case that only asserted "not zero" would
    pass on a checker that had stopped looking.
    """

    def test_a_census_that_called_everything_a_call_would_fail(self):
        rows, context = pct.survey(REGION, INDEX_ROWS, CALLEE_ROWS, REGIONS)
        for row in rows:
            row["verdict"] = "decoded-lcall"
        broken = {r["candidate"]: r for r in rows if r["target"] == 0x11C2}
        self.assertNotEqual(
            sorted(s for s, r in broken.items()
                   if r["verdict"] in pct.DECODED_VERDICTS),
            [0x8288, 0xCB4A],
            "with every verdict forced to decoded-lcall the named-site "
            "assertion goes red, which is the point of holding it by address")

    def test_a_verdict_from_outside_the_vocabulary_is_rejected(self):
        with self.assertRaises(AssertionError):
            for row in ROWS:
                self.assertIn("confirmed-caller", pct.VERDICTS)

    def test_a_walk_that_ended_without_a_named_term_is_rejected(self):
        self.assertEqual(pct.ends_vocabulary("stopped for no stated reason"),
                         [])

    def test_dropping_the_boundary_rule_changes_the_walk(self):
        """The ablation is not decoration: if the two walks were identical the
        report's statement about what the rule costs would be false, and this
        is what catches that."""
        entries = pct.entry_set(REGION, INDEX_ROWS, CALLEE_ROWS)
        starts = pct.listing_entries(INDEX_ROWS)
        bounded, _ = pct.walk(REGION, entries, starts)
        unbounded, _ = pct.walk(REGION, entries, [0])
        self.assertNotEqual(len(unbounded["sites"]), len(bounded["sites"]),
                            "the unbounded walk is expected to reach more; if "
                            "it does not, the report's cost figure is stale")

    def test_the_entry_set_is_the_stated_one_and_nothing_else(self):
        """Every seed is a committed address. A seed the tool invented would be
        the one way this census could quietly become the linear decode it is
        contrasted with."""
        entries = pct.entry_set(REGION, INDEX_ROWS, CALLEE_ROWS)
        vector = set(pct.vector_seeds(REGION))
        listing = set(pct.listing_entries(INDEX_ROWS))
        callgraph = set(pct.callgraph_entries(CALLEE_ROWS))
        for addr, sources in entries:
            with self.subTest(entry="%04X" % addr):
                self.assertTrue(
                    set(sources) <= {pct.SRC_VECTOR, pct.SRC_LISTING,
                                     pct.SRC_CALLGRAPH})
                self.assertIn(addr, vector | listing | callgraph)

    def test_the_overlap_between_the_two_committed_seed_sources_is_measured(self):
        """The call-graph rows are a subset of the listing rows on this tree,
        and the report says so rather than implying the two add up."""
        listing = set(pct.listing_entries(INDEX_ROWS))
        callgraph = set(pct.callgraph_entries(CALLEE_ROWS))
        self.assertTrue(callgraph <= listing,
                        "if the call-graph rows are no longer a subset the "
                        "report's per-source breakdown sentence is stale")
        self.assertEqual(CONTEXT["entry_stats"][pct.SRC_DISCOVERED],
                         len(CONTEXT["discovered"]))


class TestWritesNothing(unittest.TestCase):
    """The tool is read-only, and a run that left a file behind would be a
    finding about the tree rather than about the machine."""

    def _status(self):
        return subprocess.run(["git", "status", "--porcelain"],
                              cwd=str(ROOT), capture_output=True,
                              text=True).stdout

    def test_working_tree_is_byte_identical_across_a_run(self):
        before = self._status()
        for mode in (["--report"], ["--csv"], ["--for-target", "0x11C2"],
                     ["--seed-verdicts"], ["--self-test"], ["--check"]):
            subprocess.run([sys.executable, str(TOOL), *mode],
                           capture_output=True, text=True)
        self.assertEqual(before, self._status())


if __name__ == "__main__":
    unittest.main(verbosity=2, argv=[sys.argv[0]])
