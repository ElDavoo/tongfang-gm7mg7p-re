#!/usr/bin/env python3
"""Offline checks for check_pin_table_by_cited_file.py: a scratch tree and the committed one.

The tool is a second axis on a census somebody else owns, and the failure modes
are the two halves of that sentence. The first is the census's: a pin that names
the wrong line of a test file produces no error, and this tool renders no verdict
on one either -- so the standing that it exits 0 on a tree where every pin is
wrong, and that its report never says `carries` or `does not carry`, is asserted
here from the output side rather than left in a docstring. The second is this
file's own: a breakdown nobody has read is one that reweights quietly, so the
class a read*ing* case is a reading and not a count, the committed table is held
as a `{path: (resolves, declined)}` dict rather than as a total, and the two
columns reconcile back to `census()`'s own `RESOLVES` and `DECLINED` on every
tree the fixtures build. Those two reconciliations are what make the breakdown
trustworthy as a breakdown rather than a second opinion: a second walk of the
markdown here would be a second set of numbers, and a headcount that cannot be
reconciled against itself is the failure `docs/findings/test-line-pin-census.md`
is about.

The interesting half is the declined records. `census()` returns a path for
every pin that resolves and `None` for every pin it declines -- the fence rule
declines before resolution runs -- so the declined column is the one file
`place()` has to do arithmetic for, and the cases below are that arithmetic: a
`grep -rn` transcript's `./` prefix normalised away, a bare module name answered
by the census's index, two files of one name refused, and a path nowhere in the
tree landing in a *named* bucket rather than being repaired into the file that
happens to share its base name. That last one is the case a basename fallback
would fail, and it is here because a fallback is the obvious way to make the
table's totals reconcile.

The fixtures are small enough to write inline, so each case reads as the reading
it is about. They are not the real pins, but they are the real shapes -- the
fenced transcript, the `./` prefix a real one of this corpus's write-ups carries,
the two `test_*.py` of one base name a rename would produce.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
# The tool imports `census_test_line_pins` by bare module name, so the directory
# has to be on the path before either is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    "check_pin_table_by_cited_file", HERE / "check_pin_table_by_cited_file.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
census = tool.census


def tree(files):
    """A scratch repository holding `files`, as {relpath: text}.

    Built per call rather than shared, so a case that mutates a file mutates its
    own tree. The census reads the tree it is handed rather than `git ls-files`,
    which is what makes this possible at all.
    """
    root = tempfile.mkdtemp(prefix="check-pin-table-")
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return root


def by_file(root):
    """({path: {verdict: count}}, [(bucket, spelling, where, how)]) for a tree.

    Every verdict present in every row, so a rule that stopped firing reads as a
    missing key rather than as a smaller number -- the census suite's
    `verdicts()` helper, over this tool's table rather than the census's tally.
    """
    records, _files = census.census(root)
    files, index = census.suites(root)
    table, buckets = tool.charged(records, files, index)
    return ({path: {verdict: charges.count(verdict) for verdict in tool.PLACED}
             for path, charges in table.items()}, buckets)


def run_tool(root, *argv):
    """(exit code, stdout, stderr) for a run over `root`, streams captured.

    The exit code and the lines the run prints are the tool's whole output
    surface -- a rule that located nothing has to be visible there and not in a
    return value nobody calls -- so `main()` is driven with argv rather than
    `report()` being read directly. `tool.REPO` is the one thing swapped, and it
    is restored in a `finally` so a failing assertion cannot leave the committed
    tree pointed at a scratch directory for the next case.
    """
    err, out, saved = io.StringIO(), io.StringIO(), (tool.REPO, sys.argv)
    tool.REPO, sys.argv = str(root), ["check_pin_table_by_cited_file.py", *argv]
    try:
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            rc = tool.main()
    finally:
        tool.REPO, sys.argv = saved
    return rc, out.getvalue(), err.getvalue()


class ChargeTests(unittest.TestCase):
    """Which file a record is charged to, one way a reading can be wrong each.

    Every case here is a *reading* -- which file a sentence is about -- rather
    than a count, because the count is what the reconciliation cases exist to
    check. A charge that is plausible and wrong is invisible in a total.
    """

    def test_a_resolving_pin_is_charged_to_the_file_it_names(self):
        root = tree({"a.md": "`ec/tools/test_a.py:1`\n",
                     "ec/tools/test_a.py": "one\n"})
        counted, _buckets = by_file(root)
        self.assertEqual(counted, {"ec/tools/test_a.py": {
            census.RESOLVES: 1, census.OUT_OF_RANGE: 0, census.DECLINED: 0}})

    def test_a_by_name_and_a_by_path_spelling_of_one_pin_share_a_bucket(self):
        # The spelling-vs-target distinction, and the census's own. Two ways of
        # writing one citation are two *spellings* and one target, so they are
        # one row here; a table that keyed on the spelling would give the same
        # suite two rows and the concentration figures would be unreadable.
        root = tree({"a.md": "`test_a.py:2` and `ec/tools/test_a.py:2`\n",
                     "ec/tools/test_a.py": "one\ntwo\n"})
        counted, _buckets = by_file(root)
        self.assertEqual(list(counted), ["ec/tools/test_a.py"])
        self.assertEqual(counted["ec/tools/test_a.py"][census.RESOLVES], 2)

    def test_a_line_past_the_end_is_charged_to_its_file_and_is_not_a_resolve(self):
        # `out-of-range` is a column of its own rather than folded into
        # `declined`, and it is zero on the committed tree -- which is why it has
        # to be printable, or a column that appears only when it is non-zero
        # cannot be told from one that stopped being measured.
        root = tree({"a.md": "`ec/tools/test_a.py:9`\n",
                     "ec/tools/test_a.py": "one\ntwo\n"})
        counted, _buckets = by_file(root)
        self.assertEqual(counted, {"ec/tools/test_a.py": {
            census.RESOLVES: 0, census.OUT_OF_RANGE: 1, census.DECLINED: 0}})

    def test_a_fenced_pin_is_charged_to_the_fence_and_not_to_a_resolution(self):
        # The fence rule is the census's, and the record carries its verdict
        # unchanged; this file reads a *spelling* for a target and does not
        # re-decide the record. So a transcript is charged under `declined`, and
        # the report says the fence is why it was not resolved by putting it
        # there and nowhere else -- it says nothing at all about the line.
        root = tree({"a.md": "```console\n$ grep -n x ec/tools/test_a.py:4\n```\n",
                     "ec/tools/test_a.py": "one\ntwo\nthree\nfour\n"})
        records, _files = census.census(root)
        counted, _buckets = by_file(root)
        self.assertEqual(records[0][3], census.DECLINED)
        self.assertEqual(counted, {"ec/tools/test_a.py": {
            census.RESOLVES: 0, census.OUT_OF_RANGE: 0, census.DECLINED: 1}})

    def test_a_grep_transcripts_leading_dot_is_a_spelling_and_not_a_wrong_path(self):
        # The measurement that shape of reading exists for, and the one the plan's
        # number did not reproduce: feeding a declined spelling back through the
        # census's own `resolve()` reports 16 unresolved on the committed tree,
        # not 32, because the `files` index is keyed on the unprefixed path, so
        # by-path misses and the beside-the-citing-file retry misses too. The
        # sixteen `grep -rn` pins are spelled `./ec/tools/…` and are the same
        # pins as sixteen live ones. A *spelling* normalisation answers all of
        # them; a repair would answer a wrong directory prefix as well, which is
        # the guess `resolve()` refuses.
        root = tree({"a.md": "```console\n$ grep -rn x ./ec/tools/test_a.py:4\n```\n",
                     "ec/tools/test_a.py": "one\ntwo\nthree\nfour\n"})
        counted, buckets = by_file(root)
        self.assertEqual(buckets, [])
        self.assertEqual(counted["ec/tools/test_a.py"][census.DECLINED], 1)

    def test_a_declined_bare_module_name_is_charged_by_name(self):
        # The counterpart of the ambiguity case below. Without it a resolver that
        # sent every bare name to `ambiguous-path` would pass that one, and the
        # committed table's `declined` column would be a row of zeroes.
        root = tree({"a.md": "```\n`test_a.py:1`\n```\n",
                     "ec/tools/test_a.py": "one\n"})
        counted, buckets = by_file(root)
        self.assertEqual(buckets, [])
        self.assertEqual(counted, {"ec/tools/test_a.py": {
            census.RESOLVES: 0, census.OUT_OF_RANGE: 0, census.DECLINED: 1}})

    def test_a_declined_bare_name_two_files_share_is_ambiguous_and_charged_to_neither(self):
        # A `test_export_*` rename leaves two files of one name, and a charge
        # that took the first would put a transcript on one of them and report
        # the other as cited by something it was never cited for. Neither file's
        # row moves, which is the whole of what the empty dict says.
        root = tree({"a.md": "```\n`test_a.py:1`\n```\n",
                     "ec/tools/test_a.py": "one\n",
                     "tools/test_a.py": "other\n"})
        counted, buckets = by_file(root)
        self.assertEqual(counted, {})
        self.assertEqual([b[0] for b in buckets], [census.AMBIGUOUS])
        self.assertIn("not guessed", buckets[0][3])

    def test_a_declined_path_no_file_answers_for_lands_in_a_named_bucket(self):
        # `tools/test_gone.py` where the file is at `ec/tools/test_gone.py` is a
        # wrong prefix, and repairing it into the file that *is* there is the
        # guess this tool must not make: the census's `unresolved-path` is that
        # guess declined, and a breakdown that made it here would report a
        # sentence as citing a file it never named. The bucket is named, counted
        # and printed rather than dropped -- a negative nobody can see is a
        # number that reads as zero when it is not.
        root = tree({"a.md": "```\n`tools/test_gone.py:1`\n```\n",
                     "ec/tools/test_a.py": "one\n"})
        counted, buckets = by_file(root)
        self.assertEqual(counted, {})
        self.assertEqual([b[0] for b in buckets], [census.UNRESOLVED])
        self.assertIn("not repaired", buckets[0][3])
        _rc, out, _err = run_tool(root)
        self.assertIn("1 unresolved-path", out)
        self.assertIn("tools/test_gone.py:1", out)

    def test_a_declined_path_naming_a_file_that_is_elsewhere_is_not_repaired(self):
        # The same rule from the other side, with the file that shares the base
        # name *present* in the tree. The census's own hint names it, so a reader
        # can see what the record would have been had it been repaired, and the
        # repair still does not happen: the census's standing is that a wrong
        # directory prefix and a deleted file have to stay distinguishable, and
        # the way to keep them distinguishable is to report neither as the other.
        root = tree({"a.md": "```\n`tools/test_a.py:1`\n```\n",
                     "ec/tools/test_a.py": "one\n"})
        counted, buckets = by_file(root)
        self.assertEqual(counted, {})
        self.assertEqual([b[0] for b in buckets], [census.UNRESOLVED])
        self.assertIn("ec/tools/test_a.py", buckets[0][3])


class TailTests(unittest.TestCase):
    """The other half of the axis: the indexed suites no pin names.

    This is the population the breakdown is a breakdown *of*, so the class that
    holds it is half of what makes table 1 readable -- a reader cannot weigh a
    count of 33 against nothing.
    """

    def test_an_unpinned_suite_is_in_the_tail_and_a_pinned_one_is_not(self):
        root = tree({"a.md": "`ec/tools/test_a.py:1`\n",
                     "ec/tools/test_a.py": "one\n",
                     "ec/tools/test_b.py": "one\n"})
        records, _files = census.census(root)
        files, _index = census.suites(root)
        self.assertEqual(tool.unpinned(records, files), ["ec/tools/test_b.py"])

    def test_a_suite_named_only_by_a_fence_stays_in_the_tail(self):
        # The definition, held because the two readings agree on the committed
        # tree and would not have to if this one changed. The fence rule declines
        # a record before resolution runs, and a transcript of a tool's output is
        # not a citation, so a suite named only inside a fenced block is not a
        # suite anything cites.
        root = tree({"a.md": "```\n`ec/tools/test_a.py:1`\n```\n",
                     "ec/tools/test_a.py": "one\n",
                     "ec/tools/test_b.py": "one\n"})
        records, _files = census.census(root)
        files, _index = census.suites(root)
        # Both, and that they are in the same list is the measurement. The one
        # record is fenced, so the census gave it no path; `test_a.py` is
        # therefore named by no *citation* and `test_b.py` by nothing at all,
        # and the tail does not distinguish them because the fence is not a
        # weaker kind of naming -- it is the tool declining to read the line as
        # a citation in the first place.
        self.assertEqual([r[4] for r in records], [None])
        self.assertEqual(tool.unpinned(records, files),
                         ["ec/tools/test_a.py", "ec/tools/test_b.py"])

    def test_the_tail_is_the_index_minus_the_files_a_pin_names(self):
        # Not a count, an identity: the population the census resolves against
        # less the files some pin in that population named. This holds as the
        # next suite is added, which is the property that makes the tail worth
        # printing -- a list frozen by name would be wrong the moment a suite
        # landed, and the axis is about what a landing does.
        records, _files = census.census(tool.REPO)
        files, _index = census.suites(tool.REPO)
        named = {record[4] for record in records if record[4] is not None}
        self.assertEqual(len(tool.unpinned(records, files)), len(files) - len(named))


class RunTests(unittest.TestCase):
    """The run's contract: exit 0 on drift, non-zero only on a broken census.

    These drive `main()` with argv against a scratch tree, because the exit code
    and the lines it prints are the tool's whole output surface -- a rule that
    located nothing has to be visible there and not in a return value nobody
    calls.
    """

    def test_a_tree_with_no_pins_reports_that_rather_than_returning_clean(self):
        # The vacuous-pass guard, and the shape of defect
        # `docs/findings.md` §14b records: a check reporting a pass over work it
        # could not have failed. A breakdown of nothing is a table of zeroes, and
        # zeroes read as an answer.
        root = tree({"a.md": "no pins here at all\n",
                     "ec/tools/test_a.py": "one\n"})
        rc, _out, err = run_tool(root)
        self.assertNotEqual(rc, 0)
        self.assertIn("nothing was charged", err)

    def test_a_tree_with_no_markdown_reports_that_rather_than_returning_clean(self):
        rc, _out, err = run_tool(tree({"ec/tools/test_a.py": "one\n"}))
        self.assertNotEqual(rc, 0)
        self.assertIn("no markdown file was read at all", err)

    def test_a_run_whose_every_pin_is_wrong_still_exits_zero(self):
        # The standing, and the reason the tool renders no verdict. A file
        # spelled to a path that is not there, and a line past the end of one
        # that is: both are chargeable, so both are reported and neither fails
        # the run. A tool that reddened here would be the checker the census
        # write-up declines to ship.
        root = tree({"a.md": "`tools/test_gone.py:1` and `test_a.py:99`\n",
                     "ec/tools/test_a.py": "one\n"})
        rc, out, _err = run_tool(root)
        self.assertEqual(rc, 0)
        self.assertIn("2 pin(s)", out)
        self.assertIn("out-of-range", out)
        self.assertIn("1 unresolved-path", out)

    def test_the_report_renders_no_verdict_vocabulary(self):
        # The half of the standing that is about the words rather than the exit
        # code, and the half a reader skims. `carries` and `does not carry` are
        # the census write-up's reading of whether a cited line still says what
        # it is cited for; a breakdown that printed either would be reporting a
        # verdict it has no measurement for, and a report whose column is a
        # verdict stops being a count without anything saying so.
        root = tree({"a.md": "`ec/tools/test_a.py:1`\n",
                     "ec/tools/test_a.py": "one\ntwo\n"})
        _rc, out, _err = run_tool(root)
        for word in ("carries", "does not carry"):
            with self.subTest(word=word):
                self.assertNotIn(word, out)

    def test_the_run_prints_both_tables_and_the_figures_beside_them(self):
        # Both tables on every run, for the reason the census prints its counts
        # on every run: a reader re-deriving the write-up's numbers should not
        # have to ask the tool anything it did not volunteer, and the
        # concentration is the figure the write-up's argument rests on.
        root = tree({"a.md": "`ec/tools/test_a.py:1` and `ec/tools/test_a.py:1`\n",
                     "ec/tools/test_a.py": "one\n",
                     "ec/tools/test_b.py": "one\n"})
        _rc, out, _err = run_tool(root)
        self.assertIn("cited test file", out)
        self.assertIn("indexed but named by no pin (1 of 2)", out)
        self.assertIn("2 of 2 occurrence(s) name one suite", out)
        self.assertIn("the cost of an edit to that file, not an accusation", out)

    def test_the_run_names_the_population_it_read(self):
        # An exclusion that is not visible in the run is an exclusion nobody
        # could check, so the census's own population statement is repeated
        # here rather than left in that tool's docstring.
        root = tree({"a.md": "`test_a.py:1`\n", "ec/tools/test_a.py": "one\n"})
        _rc, out, _err = run_tool(root)
        self.assertIn(census.SELF_DOC, out)
        self.assertIn("vendor", out)

    def test_the_run_says_it_measured_no_claim(self):
        # Otherwise the counts read as a pass rate, and a reader who has not been
        # told the other half is a human reading takes "33 resolves" as 33 pins
        # that are right on one file.
        root = tree({"a.md": "`test_a.py:1`\n", "ec/tools/test_a.py": "one\n"})
        _rc, out, _err = run_tool(root)
        self.assertIn("no verdict is rendered here", out)
        self.assertIn("never 'absent'", out)


class ReconcileTests(unittest.TestCase):
    """The table against the census it is a second axis of.

    Without these the breakdown is a second opinion with its own totals, and a
    second opinion is a second set of numbers -- which is the thing this tool
    exists not to be. Each column has to be the census's own count of the same
    thing, including on a tree where a declined record could be placed nowhere
    and the columns therefore do not add up to the census's `DECLINED` on their
    own.

    One tree per case and both calls handed it, because a reconciliation between
    numbers read off two different scratch directories is a reconciliation of
    two different trees.
    """

    # One resolving by-path pin, one out-of-range, two resolving by name, and
    # three fenced records: one whose `./` prefix normalises away, one whose path
    # is nowhere, and one bare name two files could answer to. Every column and
    # both buckets, in one tree.
    FIXTURE = {"a.md": "`ec/tools/test_a.py:1` and `ec/tools/test_b.py:9`\n"
                        "and `test_b.py:2` and `test_c.py:1`\n"
                        "```\n`./ec/tools/test_a.py:3`\n`tools/test_gone.py:1`\n"
                        "`test_d.py:1`\n```\n",
               "ec/tools/test_a.py": "one\ntwo\nthree\n",
               "ec/tools/test_b.py": "one\ntwo\n",
               "ec/tools/test_c.py": "one\n",
               "ec/tools/test_d.py": "one\n",
               "tools/test_d.py": "other\n"}

    def read(self, root):
        """({verdict: column total}, buckets, census counts, records) for `root`."""
        records, _files = census.census(root)
        files, index = census.suites(root)
        table, buckets = tool.charged(records, files, index)
        columns = {verdict: sum(charges.count(verdict)
                                for charges in table.values())
                   for verdict in tool.PLACED}
        return columns, buckets, census.tally(records, 3), records

    def test_the_fixture_exercises_every_column_and_both_buckets(self):
        # First, because the reconciliation below passes a table whose columns
        # are all zero and whose buckets hold every record: both halves have to
        # be non-empty before their sum means anything.
        columns, buckets, _counted, _records = self.read(tree(self.FIXTURE))
        for verdict in tool.PLACED:
            with self.subTest(verdict=verdict):
                self.assertGreater(columns[verdict], 0)
        self.assertEqual(sorted({b[0] for b in buckets}), sorted(tool.BUCKETS))

    def test_every_column_is_the_censuss_own_count_of_the_same_thing(self):
        columns, buckets, counted, records = self.read(tree(self.FIXTURE))
        self.assertEqual(columns[census.RESOLVES], counted[census.RESOLVES])
        self.assertEqual(columns[census.OUT_OF_RANGE], counted[census.OUT_OF_RANGE])
        # The declined column is the census's declined count less whatever this
        # file could not place, so the identity is the sum and not the column --
        # and on the committed tree the buckets are empty, so the column and the
        # census's count are the same number.
        self.assertEqual(columns[census.DECLINED] + len(buckets),
                         counted[census.DECLINED])
        # And the whole class adds up to the census's whole population, which is
        # what makes this a breakdown rather than a second count.
        self.assertEqual(sum(columns.values()) + len(buckets), len(records))


class TheCommittedTree(unittest.TestCase):
    """The real thing: the committed markdown, and the table it adds up to.

    The counts below are the write-up's, and pinning them here is what stops
    this becoming another breakdown nobody has read -- `doc-figure-pin-audit.md`'s
    "a pin is a check, not a promise" applied to a second axis on the census
    about the pins. They move at every merge that adds a citation, and when one
    does it should be a case failing rather than a weighting shifting.
    """

    def test_the_committed_run_exits_zero(self):
        err, out, saved = io.StringIO(), io.StringIO(), sys.argv
        sys.argv = ["check_pin_table_by_cited_file.py"]
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = tool.main()
        finally:
            sys.argv = saved
        self.assertEqual(rc, 0, err.getvalue())

    def test_the_committed_table_is_the_one_the_write_up_publishes(self):
        # As a `{path: (resolves, declined)}` dict rather than as a total, for
        # the reason the class docstring gives: a total moves when a pin is
        # added anywhere and says nothing about where, and a breakdown that
        # reweights quietly is the failure this axis exists to make visible.
        # `out-of-range` is not in the dict because it is 0 -- and it is 0 as a
        # measurement, which the census's own suite asserts on the other side of
        # the same population.
        #
        # The one row that moved under #778's merge is the first, `33` -> `34`:
        # that issue's write-up brings one pin, naming the `--no-eq-guard`
        # recipe by path, and its 33 repointed occurrences all name this same
        # file, so they cannot move a count that is a count of *files*. Every
        # other row is unchanged, which is the distinction
        # `test-line-pin-repoint-563.md` is about arriving from the other end --
        # a repoint moves a line, not a name.
        records, _files = census.census(tool.REPO)
        files, index = census.suites(tool.REPO)
        table, _buckets = tool.charged(records, files, index)
        self.assertEqual(
            {row[0]: (row[1], row[3]) for row in tool.rows(table)},
            {"ec/tools/test_xdata_cluster_names.py": (34, 10),
             "ec/tools/test_grade_0751_isolation.py": (21, 15),
             "windows/tools/test_manual_fan_ctrl_probe.py": (5, 3),
             "ec/tools/test_disasm8051.py": (4, 1),
             "windows/tools/test_ec_watch.py": (3, 2),
             "ec/tools/test_xdata_register_map.py": (2, 0),
             "windows/tools/test_system_id_probe.py": (1, 1),
             "ec/tools/test_check_site_census.py": (1, 0),
             "ec/tools/test_check_testdata_index.py": (1, 0),
             "ec/tools/test_citation_gap_scan.py": (1, 0),
             "tools/test_readme_suite_table.py": (1, 0)})

    def test_the_committed_concentration_is_the_figure_the_argument_rests_on(self):
        # 44 of 106 occurrences name one suite and 80 of 106 name the two, read
        # out of the committed table's own first two rows rather than re-typed,
        # so a merge that moved a pin from one file to another moves these and
        # nothing silently absorbs the move. The `106` is the denominator of a
        # figure this suite holds; the headcount itself is held in
        # `test_census_test_line_pins.py`, and it is the one to read first if
        # these ever disagree. Each of the three moved by exactly #778's one new
        # pin -- 43 -> 44, 79 -> 80, 105 -> 106 -- and the second row is held at
        # 36 because that file was not edited.
        records, _files = census.census(tool.REPO)
        files, index = census.suites(tool.REPO)
        table, _buckets = tool.charged(records, files, index)
        cited = tool.rows(table)
        self.assertEqual([row[4] for row in cited[:2]], [44, 36])
        self.assertEqual(cited[0][4] + cited[1][4], 80)
        self.assertEqual(len(records), 106)

    def test_the_committed_index_figures_are_the_ones_the_write_up_publishes(self):
        # 38 indexed, 11 named, 27 named by none -- the three figures that move
        # by construction the moment this suite itself lands, since `suites()`
        # indexes every `test_*.py` in the tree and this is one. The superseded
        # 36 / 11 / 25 and then 37 / 11 / 26 are the record of the trees this
        # branch's base and `main` were, per §4a-4d, and the first two are the
        # ones to read first if one of these ever disagrees with the run.
        #
        # **The 37 -> 38 step is one suite, and both sides of this merge name
        # the same one by a different number.** `tools/test_doc_patch_refs.py`
        # was landed by `24460001`, which is PR **#944** and is issue #777's
        # work -- `main`'s comment named the PR and the branch's named the
        # issue, and `git log --diff-filter=A -- tools/test_doc_patch_refs.py`
        # says `24460001` and settles it. Nothing else moved a `test_*.py` into
        # or out of the tree in this window, so the indexed count is **38** and
        # the tail **27** on any tree carrying `24460001`, and no pin anywhere
        # names the step.
        #
        # **`main` left this case red on purpose and this change is the one it
        # was waiting for.** The `37` was measured before `24460001` landed, so
        # on every tree since -- the tool's own header line has read
        # `38 indexed test file(s)` throughout -- these three asserts were the
        # only thing in the tree still saying `37`. `main`'s note deferred the
        # re-measurement to "whichever change next owns this file", the same way
        # the red sets in `runner-red-suite-set.md` are named and not quietly
        # fixed from a branch that did not cause them, and neither #778's merge
        # nor anything in it moved a `test_*.py`: this merge owns the file, so
        # the pin is re-set to the measured **38 / 11 / 27** here. The `37/11/26`
        # and the `36/11/25` stay written above, each true of the tree it was
        # measured on, per §4a-4d.
        records, _files = census.census(tool.REPO)
        files, _index = census.suites(tool.REPO)
        tail = tool.unpinned(records, files)
        self.assertEqual(len(files), 38)
        self.assertEqual(len(files) - len(tail), 11)
        self.assertEqual(len(tail), 27)

    def test_this_suite_is_one_of_the_files_the_tail_reports_as_unpinned(self):
        # The self-reference, held with its reason rather than left to be
        # mistaken for a miss. Nothing in the committed markdown cites a line of
        # this suite, because the suite was written with the tool and both are
        # new -- so it is in the tail, exactly as
        # `ec/tools/test_census_test_line_pins.py` and the six `test_check_*`
        # suites beside it are. If a later write-up cites it, this goes red and
        # the pair moves between the two tables, which is the axis working.
        records, _files = census.census(tool.REPO)
        files, _index = census.suites(tool.REPO)
        self.assertIn("ec/tools/test_check_pin_table_by_cited_file.py",
                      tool.unpinned(records, files))

    def test_the_tool_is_not_in_the_cheap_gate(self):
        # A census nobody runs is the shape of defect #819 was, so the standing
        # is held here rather than left for a reader to assume a gate exists.
        # `.github/` cannot be edited from an agent branch at all; the name
        # appearing there means somebody wired it without this being redone.
        gate = os.path.join(tool.REPO, ".github", "scripts", "agent-gates.sh")
        with open(gate, encoding="utf-8") as f:
            self.assertNotIn("check_pin_table_by_cited_file.py", f.read())


if __name__ == "__main__":
    unittest.main()
