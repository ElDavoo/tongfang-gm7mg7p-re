#!/usr/bin/env python3
"""Offline checks for check_census_figures.py: committed files only.

The tool is a checker whose failure mode is silence rather than a crash. Loosen
a key or a marker and it stops catching a drifted figure while still exiting 0,
and the only thing that notices is a reader who has already been misled. So what
is pinned here is the line between what the tool claims and what it skips, one
case per rule, and every rule that makes it conservative gets a case saying so.
A skip that is not deliberate is the bug.

**The distinction that carries most of the weight is declined against
unreadable.** A figure this method does not derive is reported with its reason
and never fails the run; a key the site names that does not exist is a problem,
because a site pointing at nothing is not making a claim anyone can check.
Collapsing the two into one "not found" would be the overclaim
`ec/annotations/registers.yaml` warns about, so the cases are written apart as
well as together.

The fixtures are small enough to write inline, which keeps each case readable as
the sentence it is about rather than as a diff against a stored file. The census
they check against is not the real one; the last case is, and it is what says
the tree's prose currently agrees with the CSVs beside it.

**No case pins a figure of the real census.** Each one asserts a relation -- the
written figure is the derived figure -- and the real-tree cases assert the same
relation over every declared site. A literal like 1326 in a test is a value every
census pass has to edit, which is the defect this tool exists to remove from the
pages; putting one here would move it rather than end it.
"""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    'check_census_figures', HERE / 'check_census_figures.py')
ccf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccf)

# A census small enough to add up by hand, and chosen so every rule has
# something to bite on: a `both` row whose two halves disagree, a row carrying
# two spellings inside one program, a row the symbol table names, a row reached
# only as a literal argument, and a row *both* programs spell `DAT_EXTMEM_`, so
# the union and the two halves are three different numbers.
#
#   addr    program  spelled_as            spells_by_program                    name  refs  main pd   r w
#   0x0402  main-ec  DAT_EXTMEM            main-ec=DAT_EXTMEM                    --    10   10  0    5 5
#   0x0403  main-ec  DAT_EXTMEM+pair-lit   main-ec=DAT_EXTMEM+pair-literal       --     3    3  0    3 0
#   0x0404  main-ec  pair-literal          main-ec=pair-literal                  --     1    1  0    1 0
#   0x0405  main-ec  symbol                main-ec=symbol                        MODE  2    2  0    1 1
#   0x0406  main-ec  symbol+pair-literal   main-ec=symbol+pair-literal           TCC   4    4  0    4 0
#   0x04A3  both     DAT_EXTMEM+pair-lit   main-ec=pair-literal;pd=DAT_EXTMEM    --     8    4  4    4 4
#   0x07D8  both     symbol+DAT_EXTMEM     main-ec=symbol;pd=DAT_EXTMEM          TCC6  6    2  4    6 0
#   0x0801  pd       DAT_EXTMEM            pd=DAT_EXTMEM                        --     2    0  2    1 1
#   0x0810  both     DAT_EXTMEM            main-ec=DAT_EXTMEM;pd=DAT_EXTMEM      --     1    1  0    1 0
REGISTERS = [
    {"addr": "0x0402", "program": "main-ec", "spelled_as": "DAT_EXTMEM",
     "spellings_by_program": "main-ec=DAT_EXTMEM", "name": "",
     "refs": "10", "refs_main_ec": "10", "refs_pd": "0",
     "read": "5", "write": "5", "read+write": "0", "passed-to-call": "0",
     "address-taken": "0"},
    {"addr": "0x0403", "program": "main-ec",
     "spelled_as": "DAT_EXTMEM+pair-literal",
     "spellings_by_program": "main-ec=DAT_EXTMEM+pair-literal", "name": "",
     "refs": "3", "refs_main_ec": "3", "refs_pd": "0",
     "read": "3", "write": "0", "read+write": "0", "passed-to-call": "0",
     "address-taken": "0"},
    {"addr": "0x0404", "program": "main-ec", "spelled_as": "pair-literal",
     "spellings_by_program": "main-ec=pair-literal", "name": "",
     "refs": "1", "refs_main_ec": "1", "refs_pd": "0",
     "read": "1", "write": "0", "read+write": "0", "passed-to-call": "0",
     "address-taken": "0"},
    {"addr": "0x0405", "program": "main-ec", "spelled_as": "symbol",
     "spellings_by_program": "main-ec=symbol", "name": "MODE",
     "refs": "2", "refs_main_ec": "2", "refs_pd": "0",
     "read": "1", "write": "1", "read+write": "0", "passed-to-call": "0",
     "address-taken": "0"},
    {"addr": "0x0406", "program": "main-ec", "spelled_as": "symbol+pair-literal",
     "spellings_by_program": "main-ec=symbol+pair-literal", "name": "TCC",
     "refs": "4", "refs_main_ec": "4", "refs_pd": "0",
     "read": "4", "write": "0", "read+write": "0", "passed-to-call": "0",
     "address-taken": "0"},
    {"addr": "0x04A3", "program": "both",
     "spelled_as": "DAT_EXTMEM+pair-literal",
     "spellings_by_program": "main-ec=pair-literal;pd=DAT_EXTMEM", "name": "",
     "refs": "8", "refs_main_ec": "4", "refs_pd": "4",
     "read": "4", "write": "4", "read+write": "0", "passed-to-call": "0",
     "address-taken": "0"},
    {"addr": "0x07D8", "program": "both", "spelled_as": "symbol+DAT_EXTMEM",
     "spellings_by_program": "main-ec=symbol;pd=DAT_EXTMEM", "name": "TCC_OFF",
     "refs": "6", "refs_main_ec": "2", "refs_pd": "4",
     "read": "6", "write": "0", "read+write": "0", "passed-to-call": "0",
     "address-taken": "0"},
    {"addr": "0x0801", "program": "pd", "spelled_as": "DAT_EXTMEM",
     "spellings_by_program": "pd=DAT_EXTMEM", "name": "",
     "refs": "2", "refs_main_ec": "0", "refs_pd": "2",
     "read": "1", "write": "1", "read+write": "0", "passed-to-call": "0",
     "address-taken": "0"},
    {"addr": "0x0810", "program": "both", "spelled_as": "DAT_EXTMEM",
     "spellings_by_program": "main-ec=DAT_EXTMEM;pd=DAT_EXTMEM", "name": "",
     "refs": "1", "refs_main_ec": "1", "refs_pd": "0",
     "read": "1", "write": "0", "read+write": "0", "passed-to-call": "0",
     "address-taken": "0"},
]

CLUSTERS = [
    {"cluster_id": "main-ec-001", "size": "5", "refs": "20",
     "functions_touched": "7", "named_addrs": "0x0405 0x0406"},
    {"cluster_id": "pd-001", "size": "4", "refs": "16",
     "functions_touched": "2", "named_addrs": ""},
]

# The pin this census is measured against, written by hand rather than derived,
# so a case that compares the two compares two independent statements of one
# census rather than a statement with itself. `extmem_raw` is a value no CSV
# decides and is here only so the DECLINED path has something to decline.
ORACLE = {
    "extmem_distinct": 6, "extmem_raw": 999, "extmem_commented": 1,
    "extmem_main_distinct": 3, "extmem_pd_distinct": 4, "extmem_pd_refs": 10,
    "symbol_main_distinct": 3, "symbol_pd_distinct": 0, "symbol_pd_refs": 0,
    "distinct": 9, "refs": 37, "main_distinct": 8, "main_refs": 27,
    "pd_only": 1, "both": 3, "named_in_tree": 3,
}

FIGURES = ccf.derive(REGISTERS, CLUSTERS)
BY_ID = ccf.clusters_by_id(CLUSTERS)

# One line per figure the cases address, because the tool reads a site's line
# rather than the paragraph around it. `## 1` holds the one line that disagrees
# with the census, so the drift case is the same page as the rest.
PAGE = """# A page

## 1. Numbers

the census is 9 addresses in 40 references

## 2. A transcript

```console
$ grep -c thing .
9
```

## 3. One figure per line

the census is 9 addresses
the census is 9 addresses in 37 references
the census is 9 addresses and the symbol half is 3
the symbol half is 3 and the rest is 5

## 4. A quote

the issue counted 37 references itself
"""


def _site(**kw):
    """One declared site row, carrying the columns the tool reads."""
    row = {"file": "page.md", "section": "", "marker": "", "lines_after": "0",
           "keys": "", "reading": "live"}
    row.update(kw)
    return row


class Derivation(unittest.TestCase):
    """What `derive()` says a census is, on one small enough to add up."""

    def test_row_counts(self):
        self.assertEqual(FIGURES["distinct"], 9)
        self.assertEqual(FIGURES["main_distinct"], 8)
        self.assertEqual(FIGURES["pd_only"], 1)
        self.assertEqual(FIGURES["both"], 3)
        self.assertEqual(FIGURES["pd_distinct"], 4)

    def test_main_distinct_is_the_union_not_the_main_program(self):
        # A `both` row is reached by the main EC, so counting `program ==
        # "main-ec"` alone would drop all three of this census's shared rows.
        self.assertNotEqual(FIGURES["main_distinct"],
                            sum(1 for r in REGISTERS
                                if r["program"] == "main-ec"))

    def test_reference_totals_come_from_the_per_program_columns(self):
        # `main_refs` is `refs_main_ec` summed and never `refs` summed over the
        # main rows: a `both` row's `refs` carries the PD program's references
        # too, and 0x04A3 is the row that would go wrong.
        self.assertEqual(FIGURES["refs"], 37)
        self.assertEqual(FIGURES["main_refs"], 27)
        self.assertEqual(FIGURES["pd_refs"], 10)
        self.assertEqual(FIGURES["main_refs"] + FIGURES["pd_refs"],
                         FIGURES["refs"])

    def test_spelling_split_is_per_program_not_per_row(self):
        # 0x04A3's `spelled_as` is the union of `DAT_EXTMEM+pair-literal` and it
        # is a pair-literal to the main EC alone. Reading the union would put it
        # in the main-EC `DAT_EXTMEM` half and out of the pair-literal one.
        self.assertEqual(FIGURES["extmem_main_distinct"], 3)
        self.assertEqual(FIGURES["symbol_main_distinct"], 3)
        self.assertEqual(FIGURES["symbol_pd_distinct"], 0)
        self.assertNotIn("0x04A3",
                         [r["addr"] for r in REGISTERS
                          if "DAT_EXTMEM" in ccf.spellings(r).get("main-ec", ())])

    def test_extmem_distinct_is_a_union_not_a_sum(self):
        # 0x0810 is a `DAT_EXTMEM_` token in both programs, so the two halves
        # count it twice and the union counts it once.
        self.assertEqual(FIGURES["extmem_pd_distinct"], 4)
        self.assertEqual(FIGURES["extmem_distinct"], 6)
        self.assertLess(FIGURES["extmem_distinct"],
                        FIGURES["extmem_main_distinct"]
                        + FIGURES["extmem_pd_distinct"])

    def test_named_in_tree_is_the_name_cell(self):
        self.assertEqual(FIGURES["named_in_tree"], 3)

    def test_naming_and_spelling_are_two_figures_and_a_pd_row_holds_both(self):
        # The distinction a page's "of which named" row turns on, and the reason
        # `named_main` / `named_pd_only` exist beside `symbol_*_distinct`: an
        # address can carry a name and still be written `DAT_EXTMEM_xxxx`, which
        # is what every address the PD image reaches is -- `gen_xdata_symbols.py`
        # refuses to name that program. So a named PD row has to move
        # `named_pd_only` and nothing at all in `symbol_pd_distinct`. Reading one
        # figure for the other puts a zero in a row labelled "named", and a
        # `--print` that published only the spelling half could not show it.
        named_pd = dict(REGISTERS[7], name="DBD1")  # 0x0801, program pd
        figures = ccf.derive([named_pd], [])
        self.assertEqual(
            (figures["named_in_tree"], figures["named_main"],
             figures["named_pd_only"]), (1, 0, 1))
        self.assertEqual(
            (figures["symbol_pd_distinct"], figures["symbol_pd_refs"]), (0, 0))

    def test_a_shared_named_row_is_in_the_main_ec_half_and_not_the_pd_one(self):
        # The partition, not two halves: `named_main` takes a `both` row because
        # the main EC reaches it, so `named_pd_only` is `pd` rows alone and the
        # two still add up to `named_in_tree`. Summing the halves the way the
        # distinct-address row does would double-count it.
        shared = dict(REGISTERS[6], name="TCC_OFF")  # 0x07D8, program both
        figures = ccf.derive([shared], [])
        self.assertEqual(
            (figures["named_main"], figures["named_pd_only"],
             figures["named_in_tree"]), (1, 0, 1))

    def test_buckets_are_column_sums_and_sum_to_the_reference_count(self):
        self.assertEqual(FIGURES["read"], 26)
        self.assertEqual(FIGURES["write"], 11)
        self.assertEqual(sum(FIGURES[b] for b in ccf.BUCKETS),
                         FIGURES["refs"])

    def test_clusters_is_a_row_count_not_a_constant(self):
        self.assertEqual(FIGURES["clusters"], 2)


class Spellings(unittest.TestCase):
    """`spellings_by_program`, which is a set per program rather than a column."""

    def test_union_row_splits_into_its_two_halves(self):
        self.assertEqual(ccf.spellings(REGISTERS[5]),
                         {"main-ec": {"pair-literal"}, "pd": {"DAT_EXTMEM"}})

    def test_an_empty_cell_is_no_programs_rather_than_a_crash(self):
        self.assertEqual(ccf.spellings({"spellings_by_program": ""}), {})
        self.assertEqual(ccf.spellings({}), {})


class FiguresOnALine(unittest.TestCase):
    """What counts as a figure on a site line, and what does not."""

    def test_thousands_comma(self):
        self.assertEqual(ccf.figures_on("| distinct addresses | 1,218 | 157 |"),
                         [1218, 157])

    def test_hex_address_and_file_path_are_stripped(self):
        line = ("`0x043E` and `DAT_EXTMEM_043e` in "
                "`ec/decompiled/bank0/8749.c` line 97")
        self.assertEqual(ccf.figures_on(line), [97])

    def test_threshold_is_not_a_figure(self):
        self.assertEqual(ccf.figures_on("439 rows match at threshold 0.5"), [439])

    def test_section_and_issue_references_are_stripped(self):
        self.assertEqual(ccf.figures_on("see §4.7 and issue #342 for it"), [])

    def test_a_digit_run_inside_a_longer_number_is_one_figure(self):
        self.assertEqual(ccf.figures_on("refs 13937 here"), [13937])

    def test_a_cluster_id_is_read_as_a_figure_and_so_has_to_be_claimed(self):
        # The limit, stated rather than papered over: `main-ec-002` is a set of
        # census identifiers rather than a count, and this reader does not know
        # that. The direction it fails in is the safe one -- the extra figure has
        # to be claimed with a key or `skip`, or the site is reported -- so the
        # cost is a red run on a reworded sentence, not a silent pass.
        self.assertEqual(ccf.figures_on("it is where main-ec-002 lands"), [2])


class Resolve(unittest.TestCase):
    """One site key, and the three answers it can have."""

    def resolve(self, spec, oracle=None):
        return ccf.resolve(spec, FIGURES, oracle or ORACLE, BY_ID)

    def test_oracle_key_reads_the_pin(self):
        self.assertEqual(self.resolve("ORACLE:distinct")[:1] + self.resolve("ORACLE:distinct")[2:], (9, "ok"))

    def test_census_key_reads_the_derivation(self):
        self.assertEqual(self.resolve("census:pd_refs")[:1] + self.resolve("census:pd_refs")[2:], (10, "ok"))

    def test_cluster_column_and_named_count(self):
        self.assertEqual(self.resolve("cluster:main-ec-001:size")[0], 5)
        self.assertEqual(self.resolve("cluster:main-ec-001:named")[0], 2)
        self.assertEqual(self.resolve("cluster:pd-001:named")[0], 0)

    def test_a_cluster_the_census_does_not_have_is_unreadable_not_declined(self):
        value, detail, kind = self.resolve("cluster:main-ec-999:size")
        self.assertEqual((value, kind), (None, "unreadable"))
        self.assertIn("main-ec-999", detail)

    def test_a_declined_oracle_key_is_declined_with_its_reason(self):
        value, detail, kind = self.resolve("ORACLE:symbol_main_refs")
        self.assertEqual((value, kind), (None, "declined"))
        self.assertEqual(detail, ccf.DECLINED["symbol_main_refs"])

    def test_a_key_nothing_defines_is_unreadable(self):
        self.assertEqual(self.resolve("ORACLE:no_such_key")[2], "unreadable")

    def test_skip_declines(self):
        self.assertEqual(self.resolve("skip")[2], "declined")

    def test_derived_sum_and_difference(self):
        self.assertEqual(
            self.resolve("derived:ORACLE:symbol_main_distinct+ORACLE:symbol_pd_distinct")[0], 3)
        self.assertEqual(
            self.resolve("derived:ORACLE:main_distinct-ORACLE:symbol_main_distinct")[0], 5)

    def test_derived_evaluates_over_the_csvs_not_over_the_pin(self):
        # A pin that disagrees with its own census is exactly the case this
        # catches: reading the pin side would report the page agreeing with a
        # stale figure, which is the defect the tool exists to find.
        value, _detail, kind = self.resolve(
            "derived:ORACLE:main_distinct-ORACLE:symbol_main_distinct",
            oracle=dict(ORACLE, main_distinct=999))
        self.assertEqual((value, kind), (5, "ok"))

    def test_a_malformed_expression_is_unreadable(self):
        self.assertEqual(self.resolve("derived:ORACLE:distinct+")[2], "unreadable")
        self.assertEqual(self.resolve("derived:distinct-1")[2], "unreadable")

    def test_a_declined_term_declines_the_whole_expression(self):
        self.assertEqual(
            self.resolve("derived:ORACLE:main_distinct-ORACLE:symbol_main_refs")[2],
            "declined")

    def test_something_that_is_not_a_key_at_all_is_unreadable(self):
        self.assertEqual(self.resolve("main_distinct")[2], "unreadable")


class SiteWalk(unittest.TestCase):
    """`check_sites` over a scratch page, one case per rule it enforces."""

    def walk(self, sites):
        """(results, declined, problems) for `sites` against `PAGE`."""
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "page.md"), "w",
                      encoding="utf-8") as f:
                f.write(PAGE)
            rows = [(i + 2, site) for i, site in enumerate(sites)]
            return ccf.check_sites(rows, FIGURES, ORACLE, BY_ID, root)

    def test_an_agreeing_site_is_a_result_and_no_problem(self):
        results, declined, problems = self.walk(
            [_site(section="3", marker="and the symbol half is",
                   keys="ORACLE:distinct|ORACLE:symbol_main_distinct")])
        self.assertEqual((declined, problems), ([], []))
        self.assertEqual([r[3] for r in results], [9, 3])

    def test_a_derived_key_is_held_too(self):
        results, _declined, problems = self.walk(
            [_site(section="3", marker="and the rest is",
                   keys="ORACLE:symbol_main_distinct"
                        "|derived:ORACLE:main_distinct-ORACLE:symbol_main_distinct")])
        self.assertEqual(problems, [])
        self.assertEqual([r[3] for r in results], [3, 5])

    def test_a_drifted_figure_is_reported_with_both_numbers(self):
        _results, _declined, problems = self.walk(
            [_site(section="1", marker="the census is",
                   keys="ORACLE:distinct|ORACLE:refs")])
        self.assertEqual(len(problems), 1)
        self.assertIn("the page writes 40", problems[0])
        self.assertIn("reads 37", problems[0])

    def test_a_marker_that_moved_is_a_problem_not_a_skip(self):
        _results, declined, problems = self.walk(
            [_site(section="1", marker="a sentence nobody wrote")])
        self.assertEqual(declined, [])
        self.assertEqual(len(problems), 1)
        self.assertIn("reworded", problems[0])

    def test_an_ambiguous_marker_is_a_problem_naming_the_lines(self):
        # Three lines in `## 3` open the same way, and a checker that silently
        # took the first would be green over text it was not asked about.
        _results, _declined, problems = self.walk(
            [_site(section="3", marker="the census is 9 addresses")])
        self.assertEqual(len(problems), 1)
        self.assertIn("so which one the site means is a guess", problems[0])

    def test_a_superseded_figure_is_declined_and_never_fails(self):
        # The `## 3` line is right by the fixture's own numbers, and the case
        # that matters is the reading: a page keeping its corrections must not be
        # compared, whatever the figure on the line happens to be.
        results, declined, problems = self.walk(
            [_site(section="3", marker="and the symbol half is",
                   keys="ORACLE:distinct|ORACLE:symbol_main_distinct",
                   reading="historical")])
        self.assertEqual((results, problems), ([], []))
        self.assertEqual(len(declined), 1)
        self.assertIn("kept visible", declined[0][3])

    def test_a_restated_measurement_is_declined_and_never_fails(self):
        results, declined, problems = self.walk(
            [_site(section="4", marker="the issue counted",
                   keys="ORACLE:refs", reading="attributed")])
        self.assertEqual((results, problems), ([], []))
        self.assertIn("someone else", declined[0][3])

    def test_lines_after_reads_the_output_line_under_the_command(self):
        results, _declined, problems = self.walk(
            [_site(section="2", marker="$ grep -c thing .", lines_after="1",
                   keys="ORACLE:distinct")])
        self.assertEqual(problems, [])
        self.assertEqual([r[3] for r in results], [9])

    def test_a_declined_key_on_a_live_line_is_a_decline_not_a_problem(self):
        _results, declined, problems = self.walk(
            [_site(section="2", marker="$ grep -c thing .", lines_after="1",
                   keys="ORACLE:extmem_raw")])
        self.assertEqual(problems, [])
        self.assertEqual(len(declined), 1)
        self.assertEqual(declined[0][3], ccf.DECLINED["extmem_raw"])

    def test_an_unclaimed_figure_is_declined_rather_than_guessed(self):
        _results, declined, problems = self.walk(
            [_site(section="3", marker="and the symbol half is",
                   keys="ORACLE:distinct|skip")])
        self.assertEqual(problems, [])
        self.assertEqual(len(declined), 1)
        self.assertIn("not claimed", declined[0][3])

    def test_a_figure_nobody_claimed_is_a_problem(self):
        # The point of the `skip` keyword: without it a line could grow a number
        # this tool silently declined to check while the site list still looked
        # complete.
        _results, _declined, problems = self.walk(
            [_site(section="1", marker="the census is",
                   keys="ORACLE:distinct")])
        self.assertEqual(len(problems), 1)
        self.assertIn("every figure on a live site", problems[0])

    def test_lines_after_past_the_end_of_the_section_is_a_problem(self):
        _results, _declined, problems = self.walk(
            [_site(section="2", marker="$ grep -c thing .", lines_after="9",
                   keys="ORACLE:distinct")])
        self.assertEqual(len(problems), 1)
        self.assertIn("nothing there", problems[0])

    def test_a_section_token_naming_no_heading_is_a_problem(self):
        _results, _declined, problems = self.walk(
            [_site(section="nope", marker="the census is")])
        self.assertEqual(len(problems), 1)
        self.assertIn("no single heading naming", problems[0])

    def test_an_unknown_reading_is_a_problem(self):
        _results, _declined, problems = self.walk(
            [_site(section="1", marker="the census is", reading="current")])
        self.assertEqual(len(problems), 1)
        self.assertIn("reading is 'current'", problems[0])

    def test_a_file_that_is_not_in_the_tree_is_a_problem(self):
        _results, _declined, problems = self.walk(
            [_site(section="1", file="nowhere.md", marker="x")])
        self.assertEqual(len(problems), 1)
        self.assertIn("is not in this tree", problems[0])


class SectionBody(unittest.TestCase):
    """The heading a site names, and the span it runs to."""

    def test_a_subsection_stops_at_the_next_lower_heading(self):
        self.assertEqual(ccf.section_body(["## 1", "### 1a", "x", "## 2", "y"],
                                          "1a"), (2, 3))

    def test_a_section_with_no_heading_of_that_name_is_none(self):
        self.assertIsNone(ccf.section_body(["## 1", "x"], "1b"))

    def test_an_ambiguous_token_is_none_rather_than_a_guess(self):
        self.assertIsNone(
            ccf.section_body(["## 1a", "x", "## 2", "## 3a"], "a"))


class Constants(unittest.TestCase):
    """`int_dict`, which reads one *named* dict out of the census tool."""

    def test_reads_oracle_by_name(self):
        read = ccf.int_dict(ccf.CENSUS_TOOL, "ORACLE")
        self.assertTrue(read)
        self.assertNotEqual(read["distinct"], read["refs"])

    def test_a_name_the_module_does_not_define_reads_as_empty(self):
        self.assertEqual(ccf.int_dict(ccf.CENSUS_TOOL, "NO_SUCH_TABLE"), {})


class TheCommittedTree(unittest.TestCase):
    """The cases that measure the real tree, and they measure a relation."""

    def setUp(self):
        self.figures = ccf.derive(ccf.read_csv(ccf.REGISTERS_CSV),
                                  ccf.read_csv(ccf.CLUSTERS_CSV))
        self.oracle = ccf.int_dict(ccf.CENSUS_TOOL, "ORACLE")
        self.buckets = ccf.int_dict(ccf.CENSUS_TOOL, "BUCKET_TOTALS")

    def test_every_oracle_key_is_derived_or_declined_with_a_reason(self):
        for key, reason in ccf.DECLINED.items():
            self.assertTrue(reason.strip(),
                            f"{key} is declined with no reason to read")
        self.assertEqual(
            set(self.oracle) - set(ccf.DECLINED) - set(self.figures), set())

    def test_every_derived_figure_that_oracle_pins_agrees_with_it(self):
        stale = {k: (self.oracle[k], self.figures[k])
                 for k in set(self.oracle) & set(self.figures)
                 if self.oracle[k] != self.figures[k]}
        self.assertEqual(stale, {})

    def test_every_bucket_total_agrees_with_its_column(self):
        self.assertEqual(set(self.buckets) - set(ccf.BUCKETS), set())
        for key, value in self.buckets.items():
            self.assertIn(key, self.figures)
            self.assertEqual(self.figures[key], value, key)

    def test_the_declined_keys_really_are_not_derivable(self):
        # Asserted from both sides: a key this tool lists as unreadable that it
        # turns out to derive is a decline a reader would have to discover by
        # hand, and the partition above would then be two overlapping halves.
        self.assertEqual(set(ccf.DECLINED) & set(self.figures), set())

    def test_every_declared_site_agrees_with_the_committed_census(self):
        rows = ccf.site_rows()
        self.assertTrue(rows, "an empty site list would report a clean run "
                              "having measured nothing")
        results, _declined, problems = ccf.check_sites(
            rows, self.figures, self.oracle,
            ccf.clusters_by_id(ccf.read_csv(ccf.CLUSTERS_CSV)))
        self.assertEqual(problems, [])
        self.assertEqual([r[3] for r in results if r[3] != r[4]], [])

    def test_the_site_list_has_nowhere_to_put_an_expected_value(self):
        # The rule that keeps this file from becoming the next hand-kept total:
        # the CSV says where a figure is and what it means, never what it is,
        # and the walk above is what proves it -- changing a page's figure with
        # this file untouched is what turns the run red. A column named for a
        # value is how that would stop being true.
        header = next(iter(ccf.site_rows()))[1].keys()
        self.assertEqual(set(header), {"file", "section", "marker",
                                       "lines_after", "keys", "reading", "note"})


class Fragment(unittest.TestCase):
    """`--print`, the half a page cites instead of transcribing a figure."""

    def test_every_declined_key_appears_and_is_not_called_absent(self):
        text = ccf.fragment(FIGURES, ORACLE)
        for key in ccf.DECLINED:
            self.assertIn(key, text)
        self.assertNotIn("absent", text)
        self.assertEqual(text.count("not read by this method"),
                         len(ccf.DECLINED))

    def test_it_marks_which_figures_oracle_pins_and_which_it_does_not(self):
        text = ccf.fragment(FIGURES, ORACLE)
        self.assertIn('`ORACLE["distinct"]`', text)
        self.assertIn('`BUCKET_TOTALS["read"]`', text)
        # `pd_distinct` is derived without a pin of its own name -- `OWNERSHIP`
        # has one, and it is a different census -- so the fragment has to say
        # so rather than leaving a reader to assume a pin exists.
        self.assertIn("| `pd_distinct` | 4 | -- |", text)

    def test_it_publishes_the_naming_halves_as_well_as_their_total(self):
        # `--print` is what a page cites instead of transcribing, so a figure a
        # declared site is held to and the fragment does not print is one a
        # reader cannot check without re-reading the CSVs. Both halves carry no
        # pin of their own name, which the `--` column has to say.
        text = ccf.fragment(FIGURES, ORACLE)
        self.assertIn("| `named_main` | 3 | -- |", text)
        self.assertIn("| `named_pd_only` | 0 | -- |", text)


if __name__ == "__main__":
    unittest.main()