#!/usr/bin/env python3
"""Offline checks for check_doc_figure_pins.py: committed files only.

The tool is a checker whose failure mode is silence. It answers a question a
reader is supposed to trust — is this figure pinned, or do I have to re-derive
it by hand — and the worst thing it can do is answer it wrong while exiting 0.
So what is pinned here is the line between what the tool claims and what it
skips, one case per rule, and every case that makes it conservative gets a case
saying so. A skip that is not deliberate is the bug.

**The measurement itself is not stubbed.** Most suites of this shape would build
a fake tree and measure against it, which is what makes them cheap; this one
measures against the real `ec/tools/`, because the question the tool answers
*is* about that tree, and a fixture that invented its own oracles would test the
fixture. The cost is one parse of `ec/tools/` per case class, so `index()` is
built once at module scope and shared.

What that rules out is a case that pins a figure the tree no longer holds. Those
are the cases worth wanting — "`9320` used to be unheld" — and they are the ones
this suite cannot write without a fixture. So the tree's own figures are asserted
by value instead: each one is measured and the verdict is named, which is a case
that goes red the moment the tree changes under it, and which says on failure
which way.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    'check_doc_figure_pins', HERE / 'check_doc_figure_pins.py')
cdfp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdfp)

REPO = Path(cdfp.REPO)
CHECKLIST = REPO / "docs/findings/xdata-census-rederivation-checklist.md"

# One parse of the tree, shared by every case. `index()` is the expensive half
# and nothing here changes the tree, so paying for it once is the whole reason
# the real measurement is affordable.
FOUND = cdfp.index()


def section_body(text, token="2b"):
    """(the section's body lines) for a fragment of markdown."""
    return cdfp.section(text, token)[2]


def audit(text, token="2b"):
    """(results, declined, problems) for a fragment's section."""
    return cdfp.audit(section_body(text, token), FOUND)


def verdicts(text, token="2b"):
    """{figure: (claimed, verdict)} for a fragment's section."""
    return {value: (claimed, verdict)
            for value, claimed, verdict, _d in audit(text, token)[0]}


def measured(value, pins=()):
    """The measured verdict of one figure, with or without a row's own pins."""
    return cdfp.measure(value, list(pins), FOUND)[0]


TABLE = ("### 2b. a section\n\n"
         "| figure | line | verdict | pin |\n|---|---|---|---|\n")


class ClassifiesTheRealTree(unittest.TestCase):
    """The figures `xdata-census-rederivation-checklist.md` §2b lists, by value.

    This is the class that says the classification is a measurement. Each case
    names one figure and the verdict it has to have, so a tree that changes under
    any of them fails here rather than quietly changing what the page claims.
    """

    def assertVerdict(self, value, want, pins=()):
        self.assertEqual(measured(value, pins), want, f"figure {value}")

    def test_the_console_block_oracles_are_held_by_assertion(self):
        # The five §2a-adjacent console figures, each of which is a value in a
        # module-level constant in `xdata_register_map.py` that something reads.
        for value in (1326, 440, 1218, 157, 858):
            self.assertVerdict(value, cdfp.BY_ASSERTION)

    def test_main_refs_is_held_and_was_the_one_that_was_not(self):
        # Issue #849's subject. `OWNERSHIP["main_refs"]` is the per-program
        # reference count §6b's console block prints as `9320`, and until the
        # "and its main-EC half is" check was added no check read that key, so it
        # measured unheld. A case for it specifically, because it is the figure
        # whose pin was a promise rather than a check.
        self.assertVerdict(9320, cdfp.BY_ASSERTION)
        found = cdfp.index()
        oracle = found["oracles"][("xdata_register_map.py", "OWNERSHIP")]
        keys, lo, hi = oracle
        self.assertEqual(keys["main_refs"][0], 9320)
        read = cdfp.reads("xdata_register_map.py", "OWNERSHIP", "main_refs",
                          lo, hi, found["texts"], found["asserted"])
        self.assertIsNotNone(read, "OWNERSHIP['main_refs'] is read by nothing")
        # And the read is outside the constant's own span, which is the half of
        # the rule that separates a subscription from the literal defining one.
        self.assertFalse(lo <= read[1] <= hi)

    def test_the_residual_pair_is_unheld(self):
        # `390` and `50` are §6b's two cluster counts, and only their sum (the
        # pinned `440`) is held. This is the residual the write-up names as the
        # next pin rather than folding in here.
        for value in (390, 50):
            self.assertVerdict(value, cdfp.UNHELD)

    def test_the_sixa_subset_sums_are_unheld(self):
        # The four §6a rows whose per-subset sums are computed inline in the
        # heredoc and asserted nowhere, on either side of the guard-off split.
        for value in (3948, 3206, 7189, 7935, 193, 142, 279, 239):
            self.assertVerdict(value, cdfp.UNHELD)

    def test_the_cluster_refs_cell_is_held_through_the_line_the_row_cites(self):
        # `4,966` is the `refs` cell of `main-ec-003`, and `--check` compares
        # that whole file, so a re-derivation that moved it turns the cheap gate
        # red. It is held only because the row cites the line: searching all
        # 439 rows for "a cell equal to 4966" is not the same claim, and the next
        # case is what shows why that is not a distinction without a difference.
        pins = [("ec/annotations/xdata-clusters.csv", 4)]
        self.assertVerdict(4966, cdfp.BY_LITERAL, pins)
        self.assertVerdict(43, cdfp.BY_LITERAL, pins)

    def test_a_small_figure_is_not_pinned_by_an_unrelated_cell(self):
        # The over-match the cited-line rule exists to prevent. `50` is §6b's pd
        # cluster count and `50` is also a cell in some other cluster's row; with
        # no citation the measurement refuses to borrow the other one, and
        # `390` — which is in no cell at all — measures the same way. A tool that
        # called both of these held would be wrong about a figure a re-deriver
        # would then be told to skip.
        for value in (390, 50):
            self.assertVerdict(value, cdfp.UNHELD)


class TheCommittedChecklist(unittest.TestCase):
    """The real page: §2b's own marking agrees with measuring the real tree.

    This is the assertion that would have caught issue #849, and it is the one
    that goes red on any future edit that moves a figure between held and
    unheld. Running it the other way is the point too: see `RevertingIsRed`.
    """

    def test_committed_2b_marks_what_the_tree_measures(self):
        results, declined, problems = cdfp.audit(
            cdfp.section(CHECKLIST.read_text(encoding="utf-8"), "2b")[2], FOUND)
        self.assertEqual(problems, [])
        self.assertEqual(declined, [])
        # Eighteen figures: the six the console block's four held rows name, the
        # two it leaves unheld, the eight §6a subset sums, and the pair in the
        # `main-ec-003` row. Eight held, ten not, which is what the heading says.
        self.assertEqual(len(results), 18)
        held = [r for r in results if r[2] in cdfp.HELD_VERDICTS]
        self.assertEqual(len(held), 8)
        self.assertEqual(sorted(r[0] for r in held),
                         [43, 157, 440, 858, 1218, 1326, 4966, 9320])
        self.assertEqual(sorted(r[0] for r in results if r not in held),
                         [50, 142, 193, 239, 279, 390, 3206, 3948, 7189, 7935])

    def test_the_page_runs_green_end_to_end(self):
        # stdout too: the report is the point of the tool, and a runner that
        # interleaves eighteen figure lines with a test summary is unreadable.
        err, out = io.StringIO(), io.StringIO()
        argv = sys.argv
        sys.argv = ["check_doc_figure_pins.py", str(CHECKLIST), "--section", "2b"]
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = cdfp.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, err.getvalue())
        self.assertIn("agrees with the measurement", out.getvalue())
        self.assertIn("18 figure(s), 8 measured held, 10 measured unheld",
                      out.getvalue())


class RevertingIsRed(unittest.TestCase):
    """Both directions the correction depends on, each shown rather than asserted.

    A checker for held-versus-unheld that cannot go red when the classification
    is wrong is decoration, and the two ways to be wrong are opposite: marking a
    pinned figure unpinned, and dropping the marking altogether. The second is
    the one that is easy to do by accident — a page edit that merges a column
    away — and it is the one that silently measures nothing.
    """

    def test_marking_a_pinned_figure_unpinned_is_reported(self):
        results, _declined, _structural = audit(
            TABLE + "| `1326` | `:869` | unheld | `ec/tools/xdata_register_map.py:654` |\n")
        self.assertEqual(cdfp.disagreements(results),
                         ["the row marks 1326 'unheld'; measured "
                          f"{cdfp.BY_ASSERTION!r} ({results[0][3]})"])

    def test_a_row_that_marks_nothing_is_reported(self):
        _results, _declined, problems = audit(
            TABLE + "| `1326` | `:869` |  | `ec/tools/xdata_register_map.py:654` |\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("marks nothing", problems[0])

    def test_a_section_with_no_verdict_table_is_reported(self):
        # The shape §2b had before issue #849, and the one a merge away from
        # having again: two perfectly good tables, neither declaring a verdict.
        _results, _declined, problems = audit(
            "### 2b. a section\n\n"
            "| figure | line |\n|---|---|\n"
            "| `1326` | `:869` |\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("no table in this section has a column headed 'verdict'",
                      problems[0])

    def test_a_superseded_table_quoted_in_a_correction_is_not_measured(self):
        # The same no-verdict-column table, in a section that has a real verdict
        # table as well. This is what lets §2b keep the old classification
        # visible beside the correction without the tool auditing the wrong one:
        # only the tables that declare themselves are read, and the section-level
        # guard is satisfied by the one that does.
        results, _declined, problems = audit(
            TABLE + "| `1326` | `:869` | held | `ec/tools/xdata_register_map.py:654` |\n"
            + "\n*(Correction.) The old table read:*\n\n"
            "| figure | line |\n|---|---|\n| `9320` | `:871` |\n")
        self.assertEqual(problems, [])
        self.assertEqual([r[0] for r in results], [1326])


class ReadsTheFigure(unittest.TestCase):
    """What is a figure and what is not, one shape per case.

    Every one of these is a shape the committed corpus actually contains. A
    reader that is too eager turns a document's prose into a set of figures it
    then holds to a census, and the report becomes noise nobody reads.
    """

    def verdicts_of(self, figure_cell, rest=""):
        return verdicts(TABLE + f"| {figure_cell} | `:1` | unheld | |\n" + rest)

    def test_a_thousands_comma_is_one_figure(self):
        self.assertEqual(self.verdicts_of("`4,966`"), {4966: ("unheld", "unheld")})

    def test_two_figures_in_one_cell_are_both_read(self):
        self.assertEqual(self.verdicts_of("`3,948` / `3,206`"),
                         {3948: ("unheld", "unheld"),
                          3206: ("unheld", "unheld")})

    def test_a_count_with_a_noun_after_it_is_still_a_figure(self):
        # The `main-ec-003` row's own cell: two figures, two nouns, one row.
        self.assertEqual(sorted(self.verdicts_of("43 addresses, `4,966` refs")),
                         [43, 4966])

    def test_a_hex_address_is_not_a_figure_and_the_run_beside_it_is(self):
        self.assertEqual(self.verdicts_of("`0x08A8` `84/44`"), {84: ("unheld", "unheld"),
                                                                 44: ("unheld", "unheld")})

    def test_a_decimal_is_not_a_figure(self):
        # `at threshold 0.5` is a threshold, not a count, and `DEFAULT_THRESHOLD`
        # is 0.50. Reading the `5` or the `0` as a figure would put a pin on
        # nothing and inflate every total on the page.
        _results, declined, _problems = audit(
            TABLE + "| `390` clusters at threshold 0.5 | `:871` | unheld | |\n")
        self.assertEqual([r[0] for r in _results], [390])
        self.assertEqual(declined, [])

    def test_a_cell_with_no_number_is_declined_and_never_fails(self):
        # §2a's `set(off) == set(on)` row: a relation, and reading nothing from
        # it is the right answer rather than a miss.
        results, declined, problems = audit(
            TABLE + "| `set(off) == set(on)` | `:920` | held | |\n")
        self.assertEqual(results, [])
        self.assertEqual(declined, [("set(off) == set(on)", "no figure in the first cell")])
        self.assertEqual(problems, [])

    def test_a_section_reference_and_an_issue_number_are_not_figures(self):
        # `§2b` goes entirely and `issue #849` goes entirely -- the section
        # reference and not the `2` of it, and the issue number and not a
        # count. Both are stripped before the bare-number pass, so neither
        # reaches the measurement as a figure.
        self.assertEqual(self.verdicts_of("`§2b`, issue #849"), {})

    def test_a_file_path_in_the_cell_is_not_a_figure(self):
        self.assertEqual(self.verdicts_of("`xdata_register_map.py:1255`"),
                         {1255: ("unheld", "unheld")})

    def test_only_the_first_cell_is_a_figure_cell(self):
        # Bounding the reader is what keeps a prose cell's "1,169 addresses" out
        # of a count it was never making: §6a's own first cell carries one and is
        # quoted in the middle column here.
        self.assertEqual(verdicts(TABLE + "| `390` | main-EC `write` references "
                                  "(1,169 addresses) | unheld | |\n"),
                         {390: ("unheld", "unheld")})

    def test_a_row_with_no_verdict_cell_at_all_is_reported(self):
        # The shape an accidental merge leaves behind. Reporting it is the whole
        # point: a row that marks nothing used to be skipped, and a page whose
        # verdict column had been merged away measured nothing and exited 0.
        _r, _d, problems = audit(TABLE + "| `390` | `:871` |  | |\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("marks nothing", problems[0])


class PinsMustResolve(unittest.TestCase):
    """The `file:line` rules, which are the only ones of their kind in the tree.

    `check_doc_links` in `.github/scripts/agent-gates.sh` checks that a relative
    `.md` link exists; nothing checked a `file:line`, and these citations are the
    ones that move. A page whose pins have drifted is the defect issue #849 is
    about, one level up.
    """

    def held_row(self, pin):
        return audit(TABLE + f"| `1326` | `:869` | held | {pin} |\n")

    def test_a_pin_naming_a_file_that_is_not_in_the_tree_is_reported(self):
        _r, _d, problems = self.held_row("`ec/tools/no_such_tool.py:1`")
        self.assertEqual([p for p in problems if "is not in the tree" in p],
                         ["the row for 1326 names ec/tools/no_such_tool.py:1, "
                          "and ec/tools/no_such_tool.py is not in the tree"])

    def test_a_pin_past_the_end_of_the_file_is_reported(self):
        _r, _d, problems = self.held_row("`ec/tools/xdata_register_map.py:99999`")
        self.assertEqual(len(problems), 1)
        self.assertIn("has", problems[0])

    def test_a_held_row_naming_no_pin_is_reported(self):
        # "held" with nothing behind it is the claim the whole issue is about.
        _r, _d, problems = self.held_row("")
        self.assertEqual(len(problems), 1)
        self.assertIn("names no `file:line`", problems[0])

    def test_a_pin_into_the_wrong_file_is_reported(self):
        # The figure resolves to `ec/tools/xdata_register_map.py`; a row pinning
        # it in the checklist itself is a citation that drifted onto another
        # document, which is exactly what the sweep in #838 is about.
        _r, _d, problems = self.held_row(
            "`docs/findings/xdata-census-rederivation-checklist.md:1`")
        self.assertEqual(len(problems), 1)
        self.assertIn("the pin that measures it is in", problems[0])

    def test_an_unheld_row_naming_a_pin_is_reported(self):
        # The other direction: a citation claims something there holds the
        # figure, which is what `unheld` denies.
        results, _d, _s = audit(
            TABLE + "| `390` | `:871` | unheld | `ec/tools/xdata_register_map.py:1` |\n")
        self.assertEqual([r[0] for r in results], [390])
        self.assertEqual(cdfp.broken_pins(
            [("ec/tools/xdata_register_map.py", 1)], "`390`", cdfp.UNHELD, set()),
            ["the row for `390` is marked 'unheld' but names a pin"])

    def test_a_shorthand_citation_names_no_file_and_is_left_alone(self):
        # `:1255` is the page's own prose, and the reader that owns it does not
        # always say which file it means. Only the qualified spelling is a
        # citation this tool can resolve, and pretending otherwise would flag
        # every shorthand the corpus uses.
        self.assertEqual(cdfp.marking(["`1326`", "`:869`", "held", "`:1255`"], 2),
                         ("held", []))

    def test_the_committed_pins_all_resolve(self):
        # The assertion behind the numbers in §2b's pin column: every
        # `file:line` the page's held rows name is a line the tree has. If a
        # re-derivation moves one, this is what says so.
        text = CHECKLIST.read_text(encoding="utf-8")
        body = cdfp.section(text, "2b")[2]
        cited = set()
        for header, rows in cdfp.tables(body):
            column = cdfp.verdict_column(cdfp.cells(header))
            if column is None:
                continue
            for _offset, row in rows:
                if cdfp.marking(row, column)[0] != cdfp.HELD:
                    continue
                cited |= set(cdfp.marking(row, column)[1])
        self.assertTrue(cited, "§2b's held rows cite nothing to check")
        for name, line in sorted(cited):
            path = REPO / name
            self.assertTrue(path.exists(), f"{name} is not in the tree")
            with path.open(encoding="utf-8") as f:
                total = sum(1 for _ in f)
            self.assertLessEqual(line, total,
                                 f"{name}:{line} is past the end of {name}")


class TheOracleRule(unittest.TestCase):
    """Why a value in a constant is not a pin on its own, and what still is.

    `OWNERSHIP["main_refs"]` was the defect: a value with no reader. These cases
    pin the half of the rule that makes it a rule — that a key has to be
    *subscripted outside its own definition* — without a fixture tree, by reading
    constants that really are in `ec/tools/`.
    """

    def test_an_unread_constant_measures_unheld(self):
        # `BUCKET_TOTALS` is the one in this file that genuinely has no reader:
        # §3 of the checklist names its five figures, and the issue excluded them
        # (#838 owns the stale `:668` citation beside them). It is here as the
        # negative case for the oracle rule, and it is the reason the rule cannot
        # be "is it in a constant".
        self.assertEqual(measured(8826), cdfp.UNHELD)

    def test_a_read_constant_measures_held(self):
        # The control for the case above, and the same shape one dict over.
        self.assertEqual(measured(1326), cdfp.BY_ASSERTION)

    def test_the_two_oracles_of_one_name_are_not_credited_to_each_other(self):
        # `counter_sweep_entry.py` and `xdata_register_map.py` both define
        # `ORACLE`. A reader of one is not a reader of the other, and treating
        # them as one dictionary would pin a figure on the strength of an
        # unrelated file. The qualified spelling is the one that can say which.
        found = cdfp.index()
        self.assertIn(("counter_sweep_entry.py", "ORACLE"), found["oracles"])
        self.assertIn(("xdata_register_map.py", "ORACLE"), found["oracles"])
        self.assertNotIn("exports", found["oracles"][("xdata_register_map.py", "ORACLE")][0])
        # A qualified subscription is found from any module, which is what makes
        # `export_ownership.OWNERSHIP_ORACLE` reachable from the census tool.
        # Asserted through `where()`, because that is the string the report
        # prints and the span is part of it: the `check()` holding the constant
        # is written over seven lines, and the subscription is in the message
        # three lines above the `==` that uses it.
        #
        # The span is a line pin, so it moves with the tree: `:3902-3908` on the
        # tree this was written on, `:3981-3987` after #851's `census_shape` /
        # `carry_advice` landed above it in the same file. Re-measured, not
        # shifted by arithmetic.
        self.assertEqual(
            cdfp.where(cdfp.reads("export_ownership", "OWNERSHIP_ORACLE",
                                  "largest_class", 1, 2, found["texts"],
                                  found["asserted"])),
            "ec/tools/xdata_register_map.py:3981-3987")

    def test_the_census_csvs_are_read_from_the_tool_that_writes_them(self):
        # Derived from `OUT_REGISTERS`/`OUT_CLUSTERS` rather than named here, so
        # a census that grows a third generated file is covered without this file
        # knowing about it.
        paths = cdfp.census_csvs(FOUND["texts"])
        self.assertEqual([os.path.basename(p) for p in paths],
                         ["xdata-clusters.csv", "xdata-registers.csv"])
        self.assertTrue(all(os.path.exists(p) for p in paths), paths)

    def test_the_reported_line_is_the_check_and_not_the_arithmetic(self):
        # `ORACLE["extmem_pd_distinct"]` is first read at the `extmem_both` sum,
        # which is arithmetic on three constants. Citing that as the pin would
        # send a reader to an assignment and call it a check -- the same
        # "looks pinned and is not" defect one level down from #849's, and worth
        # a case so a rule change that drops the preference is visible.
        self.assertEqual(measured(157), cdfp.BY_ASSERTION)
        _v, detail = cdfp.measure(157, [], FOUND)
        # The two line pins are `#3260-3277` (was, on the tree this was written
        # on) and the `extmem_both` sum at `#3329` (was `:3250`), both moved by
        # #851's insertions above them in the same file; re-measured here.
        self.assertIn("3339-3356", detail)
        self.assertNotIn(":3329", detail)
        # The span opens on the `check(` and encloses the comparison, so a reader
        # following it lands on the call rather than on the sum above it.
        lines = FOUND["texts"]["xdata_register_map.py"].split("\n")
        self.assertIn("extmem_both", lines[3328])
        self.assertIn("check(", lines[3338])
        self.assertIn('(ORACLE["extmem_pd_distinct"], ORACLE["extmem_pd_refs"]',
                      lines[3355])


class SectionSelection(unittest.TestCase):
    """Which lines the run reads, and what it does when the token is unusable.

    A checker pointed at the wrong section and exiting 0 is worse than one that
    crashes, because the run looks like it did something. These cases are the
    refusal.
    """

    def test_a_section_runs_to_the_next_heading_of_the_same_or_lower_level(self):
        body = "".join(section_body(
            "### 2b. one\n\nSHALLOW\n\n#### the console block\n\nDEEPER\n\n"
            "## 3. next\n\nOUTSIDE\n"))
        self.assertIn("SHALLOW", body)
        self.assertIn("DEEPER", body)
        self.assertNotIn("OUTSIDE", body)

    def test_a_token_naming_no_heading_is_refused(self):
        with self.assertRaises(ValueError):
            cdfp.section("### 2b. one\n", "9z")

    def test_a_token_naming_two_headings_is_refused(self):
        # This is not hypothetical: the first draft of the §2 heading above §2b
        # carried "§2b" in its own text, and the run stopped rather than
        # measuring one of the two.
        with self.assertRaises(ValueError):
            cdfp.section("## 2. the groups, and §2b's split\n\na\n\n"
                         "### 2b. one\n\nb\n", "2b")

    def test_a_main_returns_two_for_a_missing_file_and_an_unusable_token(self):
        argv = sys.argv
        for args, want in ((["check_doc_figure_pins.py", "no/such/file.md",
                             "--section", "2b"], 2),
                           (["check_doc_figure_pins.py", str(CHECKLIST),
                             "--section", "9z"], 2)):
            err = io.StringIO()
            sys.argv = args
            try:
                with contextlib.redirect_stderr(err):
                    rc = cdfp.main()
            finally:
                sys.argv = argv
            self.assertEqual(rc, want, err.getvalue())


class MarkdownShapes(unittest.TestCase):
    """The table reader, on the shapes the committed corpus is written in."""

    def test_a_run_of_rows_without_a_delimiter_is_not_a_table(self):
        self.assertEqual(cdfp.tables(["| a | b |", "| c | d |"]), [])

    def test_a_header_with_no_body_is_a_table_with_nothing_in_it(self):
        self.assertEqual(cdfp.tables(["| a | b |", "|---|---|"]),
                         [("| a | b |", [])])

    def test_the_verdict_column_is_found_by_its_heading_not_its_contents(self):
        # A cell that happens to read `held` in a table about held things is not
        # a marking, and a row whose figures live in a table with no such column
        # is not a claim to compare.
        self.assertEqual(cdfp.verdict_column(["figure", "held", "pin"]), None)
        self.assertEqual(cdfp.verdict_column(["figure", "verdict", "pin"]), 1)
        self.assertEqual(cdfp.verdict_column(["figure", "`verdict`", "pin"]), 1)
        self.assertEqual(cdfp.verdict_column(["figure", "Verdict", "pin"]), 1)

    def test_a_row_claiming_a_mark_nobody_defines_is_not_a_mark(self):
        # `pinned` is the word a reader would reach for and the one the tool does
        # not accept, so a page written that way is reported rather than passing
        # on a value the tool never compared against anything.
        self.assertEqual(cdfp.marking(["`390`", "pinned"], 1)[0], None)


class TheToolRunsByHand(unittest.TestCase):
    """The standing the docstring states, asserted so it cannot quietly change.

    A checker nobody runs is the shape of defect issue #819 was. This tool is not
    in `.github/scripts/agent-gates.sh` and cannot be — the plan stage's token has
    no `workflow` scope, so a branch touching `.github/` fails at the very end.
    The prepared route is a human's change. Until then the tool runs by hand,
    exactly where `check_cluster_citations.py` stands today, and saying so is
    what keeps the branch honest about it.
    """

    def test_it_is_not_in_the_cheap_gate(self):
        gates = REPO / ".github/scripts/agent-gates.sh"
        self.assertTrue(gates.exists())
        self.assertNotIn("check_doc_figure_pins", gates.read_text(encoding="utf-8"))

    def test_its_docstring_says_so(self):
        self.assertIn("not in `.github/scripts/agent-gates.sh`", cdfp.__doc__)
        # And the caveat is load-bearing here rather than decorative: the verdict
        # on `390` and `50` is a fact about a search, not about the census.
        self.assertIn('never "absent"', cdfp.__doc__)


if __name__ == '__main__':
    unittest.main()
