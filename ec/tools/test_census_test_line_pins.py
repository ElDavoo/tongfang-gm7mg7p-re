#!/usr/bin/env python3
"""Offline checks for census_test_line_pins.py: a scratch tree and the committed one.

The tool this suite covers is a census, not a check, so the failure mode it has
to not have is the one every other pointer-checker in this tree has: silence. A
`file:line` that names the wrong line of a test file produces no error, no wrong
count, and nothing for a reader to notice -- the page reads exactly as well with
`:355-370` as with `:459-473`. So the classes below are one case per way a pin
can be read wrongly, each asserting the *reading* rather than a count, plus the
cases a loosened version would let through: a resolver that quietly repaired a
wrong directory prefix, a fence rule that swallowed live prose, an ambiguous
module name resolved to whichever candidate sorted first, and a run that returned
clean having located nothing.

The last of those is the one that matters most, and the reason the committed-tree
class runs `main()` with argv rather than calling `census()` directly: a census
that finds nothing and a census that finds nothing *wrong* have to be
distinguishable from the exit code, and so does a census that found everything and
meant nothing by it -- which is why the class also holds the standing, that the
run exits 0 on a tree where a pin is wrong. That standing is the whole reason the
tool is a census, and a case that let it fail on drift would turn the tool into
the checker `docs/findings/test-line-pin-census.md` declines to ship.

The fixtures are small enough to write inline, so each case reads as the error it
is about rather than as a diff against a stored file. They are not the real pins,
but they are the real shapes -- the `windows/tools/` prefix, the span that opens
on a blank line, the fenced transcript, the wrong-directory pin. The last class
is the real thing, and it is what says the class's own size rather than leaving
the write-up's counts as another unpinned figure.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "census_test_line_pins", HERE / "census_test_line_pins.py")
census = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census)


def tree(files):
    """A scratch repository holding `files`, as {relpath: text}.

    Built per call rather than shared, so a case that mutates a file mutates
    its own tree. The census reads the tree it is handed rather than
    `git ls-files`, which is what makes this possible at all.
    """
    root = tempfile.mkdtemp(prefix="census-test-line-pins-")
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return root


def verdicts(records):
    """{verdict: count} over a `census()` result, every verdict present.

    The zeros are kept rather than dropped so a case can compare the whole
    vocabulary: a rule that stopped firing reads as a missing key, and a dict
    comprehension over the tool's own `VERDICTS` says so as a diff.
    """
    counted = census.tally(records, 3)
    return {verdict: counted.get(verdict, 0) for verdict in census.VERDICTS}


def shapes(records):
    """{shape: count} over the pins that resolved, every shape present."""
    counted = census.tally([r for r in records if r[3] == census.RESOLVES], 6)
    return {shape: counted.get(shape, 0) for shape in census.SHAPES}


def spellings(text):
    """The pins in `text`, as the strings a reader would copy out of it."""
    return [hit.group(0) for _at, hit, _fenced in census.pins(text)]


class ExtractTests(unittest.TestCase):
    """What counts as a pin, which is the reader's whole population.

    Without these the census is a regex with no stated scope, and the scope is
    the part a reader has to be able to check: what a pin is, and what one of
    those `xdata_register_map.py:NNN` pointers the same prose family is full of
    is not.
    """

    def test_a_directory_prefix_is_part_of_the_path_not_a_separate_token(self):
        # The one shape that decides whether the report is right. Read as a
        # `tools/` prefix with `windows/` left in front, this becomes a pin into
        # a path that does not exist, and four sound citations in the committed
        # tree are reported as broken.
        self.assertEqual(
            spellings("see `windows/tools/test_ec_watch.py:145` for the row\n"),
            ["windows/tools/test_ec_watch.py:145"])

    def test_a_bracket_a_backtick_and_a_space_all_open_a_citation(self):
        # The other half of the lookbehind: what a pin may start *after*. A
        # boundary that stopped at a backtick alone would miss the `(` this
        # corpus writes its pins in as often.
        self.assertEqual(
            spellings("(`ec/tools/test_a.py:1`) and `test_b.py:2` and "
                      "test_c.py:3\n"),
            ["ec/tools/test_a.py:1", "test_b.py:2", "test_c.py:3"])

    def test_a_range_is_one_pin_carrying_both_ends(self):
        self.assertEqual(spellings("`test_a.py:3-6`\n"), ["test_a.py:3-6"])

    def test_a_bare_line_number_is_not_a_pin(self):
        # The page's own shorthand, once the file is named in the sentence above
        # it. There is no file to resolve it against, so reading it would mean
        # guessing which of the twenty test files in the tree was meant.
        self.assertEqual(census.pins("the recipe's `:444-448` says so\n"), [])

    def test_a_pointer_into_a_tool_is_not_in_this_census(self):
        # The wider `.py:NNN` class is a different census with a different owner
        # (see the write-up's follow-ups), and reading it here would report
        # 180-odd pins this tool has no verdict for.
        self.assertEqual(census.pins("`xdata_register_map.py:9-12`\n"), [])

    def test_a_test_file_named_without_a_line_is_not_a_pin(self):
        self.assertEqual(census.pins("`ec/tools/test_a.py` was to hold it\n"), [])


class FenceTests(unittest.TestCase):
    """A pin inside a fenced block is a transcript, and the rule is a shape.

    Declining is not the same as not looking: the run counts what it passed over
    and prints it, so a fence rule that swallowed every citation in a file would
    show up as a fall in the count rather than as a clean run.
    """

    def test_a_pin_inside_a_fenced_block_is_declined(self):
        root = tree({"a.md": "```console\n$ grep -n x ec/tools/test_a.py:4\n```\n",
                     "ec/tools/test_a.py": "one\ntwo\nthree\nfour\n"})
        records, _files = census.census(root)
        self.assertEqual([r[3] for r in records], [census.DECLINED])
        self.assertEqual(records[0][2], "ec/tools/test_a.py:4")

    def test_the_same_pin_outside_the_fence_is_read(self):
        # The fence covers the transcript, not the sentence above and below it,
        # and a rule that closed over the paragraph instead would decline both
        # of these and report a page that cites the same line twice as citing it
        # zero times.
        root = tree({"a.md": "```\n`test_a.py:4`\n```\n\nand `test_a.py:4` again\n",
                     "ec/tools/test_a.py": "one\ntwo\nthree\nfour\n"})
        records, _files = census.census(root)
        self.assertEqual([r[3] for r in records], [census.DECLINED, census.RESOLVES])

    def test_the_fence_line_itself_is_inside_the_block(self):
        # An opening ``` is a fence, not a citation, and a toggle that started
        # *after* it would read the first line of every transcript in the tree.
        root = tree({"a.md": "```python\n`test_a.py:1`\n```\n",
                     "ec/tools/test_a.py": "one\n"})
        records, _files = census.census(root)
        self.assertEqual([r[3] for r in records], [census.DECLINED])

    def test_an_indented_fence_still_closes(self):
        root = tree({"a.md": "  ```\n  `test_a.py:1`\n  ```\n\n`test_a.py:1`\n",
                     "ec/tools/test_a.py": "one\n"})
        records, _files = census.census(root)
        self.assertEqual([r[3] for r in records], [census.DECLINED, census.RESOLVES])


class ResolveTests(unittest.TestCase):
    """The resolver, and the three ways it is tempted to guess.

    Each case below is a defect this corpus has actually had: a directory
    prefix that names a file somewhere else, a module name two files could
    answer to, and a line number that outran the file it is written into.
    """

    def test_a_bare_module_name_resolves_by_name_and_says_so(self):
        root = tree({"a.md": "`test_a.py:2`\n", "ec/tools/test_a.py": "one\ntwo\n"})
        records, _files = census.census(root)
        self.assertEqual((records[0][3], records[0][4]),
                         (census.RESOLVES, "ec/tools/test_a.py"))
        self.assertIn(census.BY_NAME, records[0][5])

    def test_a_named_path_resolves_by_path_even_when_another_file_has_the_name(self):
        # The deliberate asymmetry. A pin that says where the file is gets that
        # file or nothing; repairing it would make a wrong prefix unreadable as
        # a wrong prefix, which is the report a re-pointer needs.
        root = tree({"a.md": "`ec/tools/test_a.py:1`\n",
                     "ec/tools/test_a.py": "one\n",
                     "windows/tools/test_a.py": "different\n"})
        records, _files = census.census(root)
        self.assertEqual((records[0][3], records[0][4]),
                         (census.RESOLVES, "ec/tools/test_a.py"))

    def test_a_path_written_relative_to_the_citing_file_resolves_beside_it(self):
        # `ec/annotations/xdata-register-map.md` writes `../tools/…` and
        # `../../docs/findings/…` for its own neighbours, so a tree-only
        # reading reports two sound pins as broken paths. The report has to say
        # which of the two readings answered, because only one of them is what
        # the page wrote.
        root = tree({"ec/annotations/a.md": "`../tools/test_a.py:1`\n",
                     "ec/tools/test_a.py": "one\n"})
        records, _files = census.census(root)
        self.assertEqual((records[0][3], records[0][4]),
                         (census.RESOLVES, "ec/tools/test_a.py"))
        self.assertIn(census.BY_BESIDE, records[0][5])

    def test_the_tree_wins_when_both_readings_would_resolve(self):
        # Not a choice between two files. A page that wrote a path the tree has
        # meant that one, and the fallback is for the page that wrote a path the
        # tree does not have.
        root = tree({"d/a.md": "`ec/tools/test_a.py:1`\n",
                     "d/ec/tools/test_a.py": "beside\n",
                     "ec/tools/test_a.py": "in the tree\n"})
        records, _files = census.census(root)
        self.assertEqual(records[0][4], "ec/tools/test_a.py")
        self.assertIn(census.BY_PATH, records[0][5])

    def test_a_path_that_is_not_there_is_unresolved_and_names_the_one_file_that_is(self):
        # `tools/test_x.py` where the file is at `ec/tools/test_x.py` is a wrong
        # prefix, not a deleted file, and the two have opposite fixes. The hint
        # is what tells a reader which one this is, and the two readings the
        # resolver tried are both in the message so the reader can check them.
        root = tree({"d/a.md": "`tools/test_a.py:1`\n", "ec/tools/test_a.py": "one\n"})
        records, _files = census.census(root)
        self.assertEqual(records[0][3], census.UNRESOLVED)
        self.assertIn("ec/tools/test_a.py", records[0][5])
        self.assertIsNone(records[0][4])

    def test_a_path_with_no_file_of_that_name_anywhere_says_so(self):
        root = tree({"a.md": "`tools/test_gone.py:1`\n",
                     "ec/tools/test_a.py": "one\n"})
        records, _files = census.census(root)
        self.assertEqual(records[0][3], census.UNRESOLVED)
        self.assertIn("no file of that name is in the tree", records[0][5])

    def test_a_bare_module_name_two_files_share_is_ambiguous_and_not_guessed(self):
        # The case the committed tree does not have and this rule exists for: a
        # `test_export_*.py` rename leaves two files of one name, and a resolver
        # that took the first would report a pin as sound against the wrong file.
        root = tree({"a.md": "`test_a.py:1`\n", "ec/tools/test_a.py": "one\n",
                     "tools/test_a.py": "other\n"})
        records, _files = census.census(root)
        self.assertEqual(records[0][3], census.AMBIGUOUS)
        self.assertIn("not guessed", records[0][5])

    def test_a_line_past_the_end_of_the_file_is_out_of_range_and_counts_the_file(self):
        root = tree({"a.md": "`ec/tools/test_a.py:9`\n",
                     "ec/tools/test_a.py": "one\ntwo\n"})
        records, _files = census.census(root)
        self.assertEqual((records[0][3], records[0][5]),
                         (census.OUT_OF_RANGE, "the file has 2 line(s)"))

    def test_the_end_of_a_range_past_the_end_is_out_of_range_too(self):
        # The span is checked as a span: a range whose opening line is real and
        # whose closing line has moved is the common shape of a pin that drifted,
        # because the reader is sent to the range and the range is what went.
        root = tree({"a.md": "`ec/tools/test_a.py:1-9`\n",
                     "ec/tools/test_a.py": "one\ntwo\n"})
        records, _files = census.census(root)
        self.assertEqual(records[0][3], census.OUT_OF_RANGE)

    def test_a_span_within_the_file_resolves_and_keeps_both_ends(self):
        root = tree({"a.md": "`ec/tools/test_a.py:1-2`\n",
                     "ec/tools/test_a.py": "one\ntwo\nthree\n"})
        records, _files = census.census(root)
        self.assertEqual((records[0][3], records[0][2]),
                         (census.RESOLVES, "ec/tools/test_a.py:1-2"))


class ShapeTests(unittest.TestCase):
    """The landing shape, which is the distribution the verdict rests on.

    A rule for these pins has to know what a pin names, and the answer is that
    it names all five of these. `blank` is in the list because the house spelling
    for a span is to open it on the line above what it is about -- a census that
    counted those as unreadable would misreport its own corpus.
    """

    ONE = "one\ntwo\nthree\nfour\nfive\n"

    def shape_of_line(self, text):
        return census.shape_of(text)

    def test_each_shape_is_read_off_the_line_it_names(self):
        cases = [
            ("    def test_the_thing(self):", census.DEF_TEST),
            ("        self.assertEqual(a, b)", census.ASSERTION),
            ("        # the reason the case exists", census.COMMENT),
            ("", census.BLANK),
            ("        value = compute(a, b)", census.OTHER),
        ]
        for line, want in cases:
            with self.subTest(line=line or "<blank>"):
                self.assertEqual(self.shape_of_line(line), want)

    def test_a_check_call_counts_as_an_assertion_and_a_word_inside_a_string_does_not(self):
        # Read off the line rather than off the parse tree, so the two halves of
        # that are the same line here -- the shape is what the reader lands on,
        # and a `check(` call in a tool module is the census's own idiom.
        self.assertEqual(self.shape_of_line('        check("> 300")'),
                         census.ASSERTION)
        self.assertEqual(self.shape_of_line('        value = "assert"'),
                         census.OTHER)

    def test_a_def_that_is_not_a_test_is_not_the_def_shape(self):
        # `check_doc_figure_pins.py` measures shapes, so counting its own
        # `def measure(...)` as a test header would put a tool function in the
        # class this census is arguing about.
        self.assertEqual(self.shape_of_line("    def measure(value, pins):"),
                         census.OTHER)

    def test_a_span_is_shaped_by_its_opening_line(self):
        # What a reader is sent to is the start of the span, so that is the line
        # the shape is read off; the end bounds the claim and names nothing else.
        root = tree({"a.md": "`ec/tools/test_a.py:1-3`\n",
                     "ec/tools/test_a.py": "\ndef test_a(self):\n    self.assertEqual(1, 1)\n"})
        records, _files = census.census(root)
        self.assertEqual(records[0][6], census.BLANK)


class PopulationTests(unittest.TestCase):
    """What the census reads, and the two files it is not allowed to read.

    The population is the claim the write-up's counts rest on, so an exclusion
    that is not visible in the run would be an exclusion nobody could check. The
    run prints the count and names both exclusions on every run for that reason.
    """

    def test_the_censuss_own_write_up_is_excluded_from_its_own_census(self):
        # Its per-pin table is a *copy* of the pins, not a fifty-first use of
        # them, and counting it would make the class's size a function of the
        # report about the class. This is `check_doc_figure_pins.py`'s
        # `SELF_MODULES` rule applied to a document.
        root = tree({"a.md": "`test_a.py:1`\n", "ec/tools/test_a.py": "one\n",
                     census.SELF_DOC: "the table names `test_a.py:1` twice\n"})
        records, _files = census.census(root)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0][0], "a.md")

    def test_vendor_markdown_is_not_part_of_the_population(self):
        # Committed vendor material is not this repository's prose, and a pin
        # inside a third-party document is not a claim about this tree.
        root = tree({"a.md": "`test_a.py:1`\n", "ec/tools/test_a.py": "one\n",
                     "vendor/thing/README.md": "`test_a.py:1`\n"})
        records, _files = census.census(root)
        self.assertEqual([r[0] for r in records], ["a.md"])

    def test_the_walk_is_sorted_so_two_runs_print_the_same_report(self):
        root = tree({"b.md": "`test_b.py:1`\n", "a.md": "`test_a.py:1`\n",
                     "ec/tools/test_a.py": "one\n", "ec/tools/test_b.py": "one\n"})
        records, _files = census.census(root)
        self.assertEqual([r[0] for r in records], ["a.md", "b.md"])


class RunTests(unittest.TestCase):
    """The run's contract: exit 0 on drift, non-zero only on a broken census.

    These drive `main()` with argv against a scratch tree, because the exit code
    and the lines it prints are the tool's whole output surface -- a rule that
    located nothing has to be visible there and not in a return value nobody
    calls.
    """

    def run_main(self, root, *argv):
        """(exit code, stdout, stderr) for a run over `root`, streams captured."""
        err, out, saved = io.StringIO(), io.StringIO(), (census.REPO, sys.argv)
        census.REPO, sys.argv = str(root), ["census_test_line_pins.py", *argv]
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = census.main()
        finally:
            census.REPO, sys.argv = saved
        return rc, out.getvalue(), err.getvalue()

    def test_a_tree_with_no_pins_reports_that_rather_than_returning_clean(self):
        root = tree({"a.md": "no pins here at all\n",
                     "ec/tools/test_a.py": "one\n"})
        rc, _out, err = self.run_main(root)
        self.assertNotEqual(rc, 0)
        self.assertIn("nothing was censused", err)

    def test_a_tree_with_no_markdown_reports_that_rather_than_returning_clean(self):
        rc, _out, err = self.run_main(tree({"ec/tools/test_a.py": "one\n"}))
        self.assertNotEqual(rc, 0)
        self.assertIn("no markdown file was read at all", err)

    def test_a_run_whose_pins_are_all_broken_still_exits_zero(self):
        # The standing, and the reason this is a census. A tool that reddened on
        # drift here would be the checker the write-up declines to ship, and it
        # would redden on the tree those two pre-existing pins are recorded in --
        # which `prose-line-citations-held.md` calls the surest way to get a
        # check switched off.
        root = tree({"a.md": "`tools/test_gone.py:1` and `test_a.py:99`\n",
                     "ec/tools/test_a.py": "one\n"})
        rc, out, _err = self.run_main(root)
        self.assertEqual(rc, 0)
        self.assertIn("0 resolves", out)
        self.assertIn("1 unresolved-path", out)
        self.assertIn("1 out-of-range", out)

    def test_the_run_prints_every_figure_a_reader_would_re_derive(self):
        # The counts are the census's product, so all of them are printed on
        # every run: a reader re-deriving the write-up's numbers should not have
        # to ask the tool anything it did not volunteer.
        root = tree({"a.md": "`test_a.py:1` and `test_a.py:1` again\n",
                     "ec/tools/test_a.py": "one\n"})
        rc, out, _err = self.run_main(root)
        self.assertEqual(rc, 0)
        self.assertIn("2 pin(s) in 1 markdown file(s)", out)
        self.assertIn("1 distinct spelling(s)", out)
        self.assertIn("1 distinct resolved target(s)", out)
        for verdict in census.VERDICTS:
            with self.subTest(verdict=verdict):
                self.assertIn(verdict, out)

    def test_the_run_says_it_measured_no_claim(self):
        # Otherwise the counts read as a pass rate, and a reader who has not been
        # told the other half is a human reading takes "42 resolves" as 42 pins
        # that are right.
        root = tree({"a.md": "`test_a.py:1`\n", "ec/tools/test_a.py": "one\n"})
        _rc, out, _err = self.run_main(root)
        self.assertIn("no claim is measured here", out)

    def test_the_run_names_what_it_excluded(self):
        root = tree({"a.md": "`test_a.py:1`\n", "ec/tools/test_a.py": "one\n"})
        _rc, out, _err = self.run_main(root)
        self.assertIn(census.SELF_DOC, out)
        self.assertIn("vendor", out)

    def test_verbose_names_the_pin_the_resolution_and_the_target_line(self):
        root = tree({"a.md": "`test_a.py:2`\n",
                     "ec/tools/test_a.py": "one\n        self.assertEqual(1, 1)\n"})
        _rc, out, _err = self.run_main(root, "--verbose")
        self.assertIn("a.md:1", out)
        self.assertIn("ec/tools/test_a.py:2", out)
        self.assertIn(census.BY_NAME, out)
        self.assertIn("assertEqual", out)


class TheCommittedTree(unittest.TestCase):
    """The real thing: the committed markdown, censused, and its own size held.

    The counts below are the write-up's, and pinning them here is what stops
    this becoming another unpinned figure -- `doc-figure-pin-audit.md`'s "a pin is
    a check, not a promise" applied to the census about the pins. They are also
    the one thing here that a reader cannot re-derive without running the tool,
    which is why they are in a case and not only in the prose.
    """

    def run_main(self, *argv):
        """(exit code, stdout, stderr) the way a reader would run it."""
        err, out, saved = io.StringIO(), io.StringIO(), sys.argv
        sys.argv = ["census_test_line_pins.py", *argv]
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = census.main()
        finally:
            sys.argv = saved
        return rc, out.getvalue(), err.getvalue()

    def test_the_committed_run_exits_zero(self):
        rc, _out, err = self.run_main()
        self.assertEqual(rc, 0, err)

    def test_the_committed_census_locates_something(self):
        # The vacuous-pass guard. A census over a tree whose markdown it could
        # not read would print a clean run of zeroes, and that is the one outcome
        # a report of held-versus-not-held cannot produce.
        records, _files = census.census(census.REPO)
        self.assertTrue(records)
        self.assertGreater(len({r[0] for r in records}), 1)

    def test_the_committed_counts_are_the_ones_the_write_up_publishes(self):
        # Re-measured at issue #930, on top of the #885 x #771, #888 x #885,
        # #888 x #890, #850/#887 and #888 re-measurements these figures already
        # carried. Six moves, each recorded in the write-up beside the figures it
        # replaces, per §4a-4d:
        # #850 added nineteen `test_*.py:NNN` citations to the markdown and 239
        # lines to ec/tools/test_xdata_cluster_names.py, which is what took
        # 50/23/37/32 and the 44/6 and 5/15/5/8/11 splits to 69/24/44/53/16 and
        # 5/11/9/6/22; #888's write-up
        # (`docs/findings/xdata-moved-ranks-key-collision.md`) is one new file
        # and cites the `> 300` floor twice, taking those to 71/25/45/55/16 and
        # 5/13/9/6/22; #890's commit is what takes the last line below from
        # 40 to 41 and `assertion`/`other` from 13/22 to 11/24; the #888 x #885
        # merge added #885's own two citations of the same assertion, taking
        # those to 73/26/46/57/16, 42 targets and 5/11/9/6/26; the #885 x #771
        # merge added one new file carrying sixteen transcript pins and their
        # sixteen live-prose twins, taking those to 105/27/78/73/32, 58 targets
        # and 5/17/10/6/35; **and #930 repoints the two pins #888 wrote, which
        # takes the shape split back again.**
        # #890 added no pin and no markdown file, so it moved no figure #888
        # moved -- but it moved the line #888's two new pins name.
        # `assertGreater(len(moved), 300)` was at `test_xdata_cluster_names.py:563`
        # on #888's tree, and #890 put 25 lines into that file above it, so the
        # floor is at `:588` here and `:563` is now a fixture line. That is the
        # whole of the 40 -> 41 and the 13 -> 11 / 22 -> 24: `:563` is a
        # resolved target the branch introduced and `main` had never named, and
        # a cited line whose shape changed under a reader rather than a new
        # pin. It is a real defect of the kind the census exists to find, and
        # it was recorded in the write-up rather than repointed there, for the
        # write-up's own reason -- repointing the citing prose is a follow-up --
        # and #930 is that follow-up.
        #
        # Re-measured a fourth time, at the #888 x #885 merge, and this is the
        # one move where the two merges' additions are simply additive: each
        # added one new markdown file carrying two new occurrences of its own
        # spelling, on disjoint lines, so occurrences, files, `resolves`,
        # spellings and targets each go up by four/two/two/two/two over the
        # 71/25/45/55/41 above and `other` goes 24 -> 26. `declined` does not
        # move, because all four new pins are live prose rather than transcript.
        # The two that moved the shape split are #888's `:563` pair and #885's
        # `:392` pair, both `other` on that tree -- the second of them is
        # `decreased, {},`, the last line of the assertion holding that no
        # address's `write` decreases -- so `assertion` stayed at 11 for the
        # fourth time running. Measured with the tool, not derived.
        #
        # Re-measured a fifth time, at the #885 x #771 merge, and this is the
        # first move here that `declined` does *not* stay still on. #771's write-up
        # (`docs/findings/0751-path-taking-reader-fates.md`) is one new file
        # carrying sixteen `test_*.py:NNN` pins, and all sixteen sat inside two
        # fenced `grep` transcripts -- the one shape the fence rule declines --
        # with no live-prose twin, so each was a transcript-only citation of a
        # line the tree named nowhere else. That is the case
        # `test_every_declined_pin_is_also_cited_in_live_prose` exists to catch,
        # and it caught all sixteen. The fix is in the write-up rather than
        # here: it now names all sixteen in live prose as well, so each declined
        # pin is a *declined duplicate* of a citation that is present, which is
        # what the fence rule is safe on. So the sixteen transcript records stay
        # declined, the sixteen prose records are new and all resolve, and
        # occurrences go 73 -> 105, `resolves` 57 -> 73, `declined` 16 -> 32 and
        # targets 42 -> 58, over one new file.
        #
        # Spellings move 46 -> 78, by 32 and not by 16, and the reason is worth
        # stating because it is a property of the tool rather than of the tree:
        # `spellings` counts `r[2]`, the *matched* spelling, and `grep -rn`
        # prints `./ec/tools/...` where prose writes `ec/tools/...`. The
        # transcript's sixteen and the prose's sixteen are therefore two
        # spellings of one pin each, and a count of 62 would have meant editing
        # a verbatim transcript to drop a prefix the tool really did print.
        # `targets` is unaffected by the same prefix, because it keys on the
        # *resolved* path, which is why it moves by 16 rather than 32. The shape
        # split is the landing shape of the sixteen prose lines and nothing
        # else: `assertion` 11 -> 17, `comment` 9 -> 10, `other` 26 -> 35, and
        # `blank` and `def test_` do not move. Measured with the tool, not
        # derived.
        #
        # **Re-measured a sixth time, at issue #930, whose two repointed rows
        # reverse the whole of the shape movement and add nothing**: 58 -> 57
        # targets, 17 -> 19 assertions, 35 -> 33 other. #930 moved the two
        # by-name `test_xdata_cluster_names.py:563` rows of #888's own write-up
        # onto `:588`, the line the `> 300` floor is on, so `:588` rejoins a
        # target the checklist already carried by path and `:563` loses the last
        # name it had. It is measured on the tree the fifth re-measure produced,
        # so the three figures it reverses are that paragraph's 58, 17 and 35
        # rather than the 42, 11 and 26 the fourth measured. The headcount is
        # what says the correction did not smuggle a pin into the census it is
        # reporting on, so `105`, `27` and `78` are unmoved across the #885 x
        # #771 and #930 runs -- the last two of the six, and the only two that
        # carry those figures; the first four read 69/24/44, 71/25/45, 71/25/45
        # and 73/26/46, as the history above records. They are the figures to
        # read first if one of the four below ever disagrees with the run.
        #
        # **Re-measured a seventh time, at issue #778, and the first of the seven
        # to add a pin rather than move one**: 105 -> 106 records, 27 -> 28
        # files, 78 -> 79 spellings, 73 -> 74 resolves, 33 -> 34 other, 57 -> 58
        # targets. Its write-up cites the `--no-eq-guard` recipe at
        # `ec/tools/test_xdata_cluster_names.py:88`, which is one pin in a new
        # file, so every one of those moved by one and the verdicts did not --
        # `declined` is 32 for the fifth time running and the three zero verdicts
        # are zero for the sixth, which is the shape an *addition* has and the
        # opposite of #930's, where the movement was 58 -> 57 targets against a
        # headcount held still. It also repointed 33 occurrences across 11
        # files without moving the headcount, because a repoint changes the
        # target a spelling resolves to and not the number of spellings; the two
        # are separate measurements and both are below. #930's `105`, `27` and
        # `78` are the figures for the #885 x #771 and #930 runs and stay
        # readable above as the run they were measured on.
        #
        # **Re-run an eighth time on this same merged tree, and the eighth moved
        # nothing at all**: #946 and #944 landed between that re-measurement and
        # this merge, each adding a markdown write-up and a `test_*.py` suite,
        # and neither wrote a `test_*.py:NNN` into either -- so all six figures
        # above are unchanged and only the two denominators the census prints
        # beside them went on, `150` -> `152` markdown files read and `36` -> `38`
        # test files resolved against. A write-up and a suite that cite no pin of
        # this class are the cheapest merge in the series and the one most worth
        # recording, because a reader who sees the denominators move and the head
        # count not has the measurement rather than the guess.
        #
        # **Re-measured a ninth time on the `#778 × #780` tree, and the ninth is
        # the only one where the two sides' shape movements compose.** #780
        # repointed one stale line pin at the rule that replaced the code it
        # cited, which is a move from `assertion` to `other` -- 19 -> 18 and
        # 33 -> 34 on its own tree, against a headcount it held at 105. #778
        # moved `other` 33 -> 34 for the other reason, one *new* pin. Both
        # apply here, so the split reads **18 / 35 over 74**: five of the
        # movement are the new pin and the sixth is the repoint, and the six
        # headcount figures above are unchanged by either, which is the whole
        # of what a repoint is. The other denominator moved once more, `152` ->
        # `153` markdown files read, because this merge adds #780's write-up
        # beside #778's where each of them saw only its own.
        #
        # **Re-run a tenth time on the tree this lands in, where the two shape
        # movements above are no longer the whole story and the ninth paragraph's
        # `18 / 35` is not this tree's split.** #962 corrected a
        # `guard_off()` docstring and added a class, which moved every pin
        # landing inside `test_xdata_cluster_names.py` off a `def test_` header
        # onto prose or code -- the `0/16/22/5/31` the assertion below already
        # records as #962's own step -- and `main` then took the suite count to
        # 39. So the repoint composes on top of that rather than beside it, the
        # live split is `0/15/22/5/32`, and the ninth paragraph's `18 / 35` is
        # left written as the `#778 x #780` tree's figure rather than edited into
        # this one. The denominator is `160` markdown files read against `39` test
        # files, measured on the merged tree and on `origin/main` at `abfe76e6`
        # (which reads `159`), and the step between them is #780's own write-up
        # -- the eighth paragraph's `152 -> 153` is the `#778 x #780` tree's and
        # is left written in the same breath.
        #
        # The `carries` / `does not carry` counts (51 and 11 here, 50 and 11
        # before #778, 48 and 13 before that) are **not** here on purpose: they
        # are a reading of whether a
        # cited line still carries the claim it is cited for, and this suite
        # tests the mechanical half. They live in the write-up's table, and
        # #930's repoint is the reason to keep them there -- the tool printed
        # every number the repoint changed and none of them was a verdict.
        # #778's 33 repointed occurrences are the second reason: a repoint
        # moves a target and says nothing about whether the line it now names
        # carries the claim, so there is no count here that would have caught
        # the one that had stopped doing so. The `50` -> `51` is #778's one new
        # pin, read here and carrying; the eleven that do not carry are the same
        # eleven.
        records, _files = census.census(census.REPO)
        self.assertEqual(len(records), 106)
        self.assertEqual(len({r[0] for r in records}), 28)
        self.assertEqual(len({r[2] for r in records}), 79)
        self.assertEqual(verdicts(records), {
            census.RESOLVES: 74, census.OUT_OF_RANGE: 0,
            census.UNRESOLVED: 0, census.AMBIGUOUS: 0, census.DECLINED: 32})
        # Re-derived for #962, then again here, and not lowered either time.
        # #962's class and a docstring above it grew, so every pin into
        # `test_xdata_cluster_names.py` lands `N` lines lower than it did, and
        # the landing *shapes* follow: five pins that read a `def test_` header
        # now read prose or code, and the split moves from `5/19/10/6/34` to
        # `0/16/22/5/31`. The ninth paragraph above adds #780's own repoint on
        # top of that -- one assertion onto prose, `19` -> `18` and `34` -> `35`
        # -- and it is a different pin from any of the five, so the two
        # movements compose rather than one replacing the other and the merged
        # tree reads `0/15/22/5/32`. Nothing above this changed: 106 records
        # over 28 files and 79 spellings, the same 74 resolving and 32 declined,
        # the same 58 targets -- which is what makes the shape the one column a
        # line shift can move on its own.
        self.assertEqual(shapes(records), {
            census.DEF_TEST: 0, census.ASSERTION: 15, census.COMMENT: 22,
            census.BLANK: 5, census.OTHER: 32})
        self.assertEqual(
            len({(r[4], r[2].rsplit(":", 1)[1]) for r in records
                 if r[3] == census.RESOLVES}), 58)

    def test_the_committed_tree_exercises_more_than_one_verdict(self):
        # Each of these classes is non-zero on the real tree and not only on a
        # fixture, so a rule that had stopped firing would show up here rather
        # than in a case written for it. The other three are zero here, and that
        # is itself the measurement: every pin in the tree names a file that is
        # in it, no cited line has outrun its file, and no two test files share
        # a module name. A checker built on this class would have nothing to
        # redden on at the *file* level -- which is the write-up's first reason
        # the defective half is all that is there.
        records, _files = census.census(census.REPO)
        counts = verdicts(records)
        for verdict in (census.RESOLVES, census.DECLINED):
            with self.subTest(verdict=verdict):
                self.assertGreater(counts[verdict], 0)
        for verdict in (census.OUT_OF_RANGE, census.UNRESOLVED, census.AMBIGUOUS):
            with self.subTest(verdict=verdict):
                self.assertEqual(counts[verdict], 0)

    def test_every_declined_pin_is_also_cited_in_live_prose(self):
        # The fence rule is only safe while declining a pin that is not the only
        # place its line is named. If a transcript ever became the sole citation
        # of a line, the run would be declining the tree's only record of it, and
        # the count would be a quiet loss rather than a declined duplicate.
        records, _files = census.census(census.REPO)
        live = {(r[4], r[2].rsplit(":", 1)[1]) for r in records
                if r[3] == census.RESOLVES}
        declined = [r for r in records if r[3] == census.DECLINED]
        self.assertTrue(declined)
        for record in declined:
            with self.subTest(pin=record[2]):
                spelling = record[2].rsplit(":", 1)
                named = {r[2] for r in records
                         if r[3] == census.RESOLVES
                         and os.path.basename(r[2].rsplit(":", 1)[0])
                         == os.path.basename(spelling[0])
                         and r[2].rsplit(":", 1)[1] == spelling[1]}
                self.assertTrue(named, f"{record[2]} is only ever named inside "
                             "a fenced block, so declining it loses the tree's "
                             "only citation of that line")

    def test_no_test_file_in_the_tree_shares_a_module_name(self):
        # What makes `ambiguous-path` zero above, held from the other side: a
        # `test_export_*.py` rename would put two files of one name in the index
        # and every bare-name pin to that module would stop being decidable.
        _files, index = census.suites(census.REPO)
        shared = {base: paths for base, paths in index.items() if len(paths) > 1}
        self.assertEqual(shared, {})

    def test_the_tool_is_not_in_the_cheap_gate(self):
        # A census nobody runs is the shape of defect #819 was, so the standing
        # is held here rather than left for a reader to assume a gate exists.
        # `.github/` cannot be edited from an agent branch at all; the name
        # appearing there means somebody wired it without this being redone.
        gate = os.path.join(census.REPO, ".github", "scripts", "agent-gates.sh")
        with open(gate, encoding="utf-8") as f:
            self.assertNotIn("census_test_line_pins.py", f.read())


if __name__ == "__main__":
    unittest.main()
