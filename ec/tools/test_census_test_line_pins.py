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
on a blank line, the fenced transcript, the wrong-directory pin. The
committed-tree class is the real thing, and it is what says the class's own size
rather than leaving the write-up's counts as another unpinned figure.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import re
import subprocess
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
    its own tree. It is deliberately *not* a work tree, which is the fallback
    reading's fixture; `work_tree()` is the other one.
    """
    root = tempfile.mkdtemp(prefix="census-test-line-pins-")
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return root


def git(root, *args):
    """`git <args>` in `root`, its output discarded, raising if it fails."""
    subprocess.run(["git", "-C", root, *args], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def work_tree(files):
    """A scratch *work tree* holding `files` and committed; its path.

    A commit rather than an `add`, so the fixture is what the committed reading
    claims to be measuring, and `-c user.*` so a case does not inherit a git
    identity -- or the absence of one -- from whatever machine runs it. `git` is
    shelled out to by other suites in this tree and is on `PATH` in the
    pipeline's own checkout, so this is house practice rather than a new
    dependency.
    """
    root = tree(files)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "-c", "user.name=census", "-c", "user.email=census@example.invalid",
        "commit", "-q", "-m", "fixture")
    return root


def drop(root, rel, text):
    """Write `text` to `rel` under `root` without telling git about it."""
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


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

    # LOCAL CHANGE (2026-10-02): the cases that held this tool's run on the committed tree
    # to the write-up's figures are gone. They counted the repository's own markdown, so
    # every merge that added or moved a citation had to bump them, and two branches bumping
    # them from different bases is a merge conflict -- this family of files was in 85 of
    # the 305 commits to main from 2026-09-24 to 2026-10-02. What is held on the tree now
    # is a property (exits zero, locates something), never a total. CLAUDE.md, "No totals
    # of the repository's own text".

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


class PopulationSourceTests(unittest.TestCase):
    """Which of the two readings a run got, and what each one is answerable to.

    The run's figures are published as measurements of *this repository*, and a
    walk counts whatever is in the directory it stands in: an untracked scratch
    page, a `git worktree` of this repository under a dot-directory, another
    clone's checkout. On a clean checkout the two readings agree exactly, which
    is why CI never saw it and it had to be found by reading. So the cases below
    are the ones a walk cannot be given -- a file that is in the tree and is not
    in the repository -- plus the invariant that makes the split safe, which is
    that a root with no work tree is still census-able and says that it fell
    back rather than reading identically to a committed run.

    Two of them are about *named* directories rather than dotted ones. `/tmp/`,
    `/out/` and `/scratch/` are all listed in this repository's `.gitignore` and
    none of them is a dot-directory, so a rule that pruned dot-directories would
    have passed the dot-directory case and failed the named one. That is the
    whole reason the reading is `git ls-files` and not a longer `PRUNED`.
    """

    def figures(self, root):
        """(markdown read, test files read, pins found) as one run reports them."""
        _read, files = census.suites(root)
        records, _files = census.census(root)
        return len(census.markdown(root)), len(files), len(records)

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

    def kept(self, rel):
        """Whether the population carries `rel` at all, the prune applied here.

        The test's own component check rather than the tool's, so an
        expectation computed from git and one computed by the same function
        cannot agree because they are the same function.
        """
        return not any(part in census.PRUNED for part in rel.split("/"))

    def test_an_untracked_markdown_does_not_move_either_denominator(self):
        # The case the walk could not be given, and the one the reproduction is:
        # drop any markdown carrying a pin into a directory the walk does not
        # prune, and the markdown figure the write-up quotes moves, with no
        # commit anywhere. One of the two denominators, not both -- each counts
        # files of its own kind, so a dropped `.md` cannot move the test-file
        # one either way. The assertion is over all three figures because the
        # point is what the committed reading leaves alone, and the record count
        # is in there because the dropped file carries a resolvable citation.
        root = work_tree({"a.md": "`test_a.py:1`\n",
                          "ec/tools/test_a.py": "one\ntwo\n"})
        before = self.figures(root)
        drop(root, ".claude-pr/CLAUDE.md", "`ec/tools/test_a.py:2`\n")
        self.assertEqual(self.figures(root), before)

    def test_an_untracked_file_in_a_named_gitignored_directory_does_not_either(self):
        # The same thing under a directory `.gitignore` *names*, which is the
        # half a dot-prune would have missed and the reason the reading is git's
        # rather than a longer exclusion list.
        root = work_tree({".gitignore": "/scratch/\n", "a.md": "`test_a.py:1`\n",
                          "ec/tools/test_a.py": "one\ntwo\n"})
        before = self.figures(root)
        drop(root, "scratch/notes.md", "`ec/tools/test_a.py:2`\n")
        self.assertEqual(self.figures(root), before)

    def test_a_file_that_is_committed_stays_in_the_population_even_if_ignored(self):
        # What the rule does *not* claim, and the boundary of it. `git ls-files`
        # is the index, not the working directory, so a file that is tracked but
        # listed in `.gitignore` is in the population; one that is ignored and
        # never added is not, which is the case above. Stating the first without
        # the second would leave "the committed tree" reading as "the clean
        # tree".
        root = work_tree({".gitignore": "/scratch/\n", "a.md": "`test_a.py:1`\n",
                          "ec/tools/test_a.py": "one\ntwo\n"})
        drop(root, "scratch/notes.md", "`ec/tools/test_a.py:2`\n")
        git(root, "add", "-f", "scratch/notes.md")
        read, _source = census.population(root, ".md")
        self.assertIn("scratch/notes.md", read)

    def test_a_root_that_is_not_a_work_tree_is_still_censusable(self):
        # The invariant the split has to keep, and it is what the classes above
        # depend on: every fixture in this suite is a bare tempdir, and a
        # committed-only reading would have made all of them read nothing. The
        # second half is the part a reader needs -- a fallback run has to say it
        # fell back, or its figures are indistinguishable from the repository's.
        root = tree({"a.md": "`test_a.py:1`\n", "ec/tools/test_a.py": "one\n"})
        records, _files = census.census(root)
        self.assertEqual([r[3] for r in records], [census.RESOLVES])
        _read, source = census.population(root, ".md")
        self.assertIn("not the top of a work tree", source)

    def test_a_root_inside_a_work_tree_that_is_not_its_top_falls_back(self):
        # The subdirectory edge. `git -C ec/tools rev-parse --show-toplevel`
        # succeeds and answers with the repository's top, so a check that only
        # asked whether it succeeded would census the whole repository from a
        # subdirectory -- and report the result as that subdirectory's, which is
        # the same defect one level up. `top.md` is the file that must *not*
        # come along.
        root = work_tree({"top.md": "`test_a.py:1`\n",
                          "ec/tools/a.md": "`test_a.py:1`\n",
                          "ec/tools/test_a.py": "one\n"})
        inner = os.path.join(root, "ec", "tools")
        self.assertEqual(census.markdown(inner), ["a.md"])
        _read, source = census.population(inner, ".md")
        self.assertIn("not the top of a work tree", source)

    def test_the_run_names_the_reading_its_figures_came_from(self):
        # A figure that cannot be traced to a reading is a figure that cannot
        # be checked, and the fallback's numbers are that tree's rather than
        # this repository's -- so the run says which on every invocation, in
        # both readings, rather than leaving a reader to infer it.
        pinned = work_tree({"a.md": "`test_a.py:1`\n",
                            "ec/tools/test_a.py": "one\n"})
        bare = tree({"a.md": "`test_a.py:1`\n", "ec/tools/test_a.py": "one\n"})
        for root, wanted in ((pinned, "the committed tree"),
                             (bare, "not the top of a work tree")):
            with self.subTest(reading=wanted):
                _rc, out, _err = self.run_main(root)
                self.assertIn(wanted, out)
                self.assertIn(census.SELF_DOC, out)

    def test_each_denominator_is_the_set_git_reports_and_not_a_stored_number(self):
        # The two denominators, held as claims rather than as numerals. The
        # expected set is computed from `git ls-files` *here*, so the comparison
        # is against git and not against a figure somebody wrote down: a
        # literal is a value every merge that lands a write-up has to edit, and
        # it would redden on the next one, reading as drift (CLAUDE.md, "No
        # totals of the repository's own text"). On a clean checkout the walk
        # answers this identically -- which is the whole reason the defect this
        # change fixes was never caught here -- so this case holds the
        # denominator rather than guarding the split; the cases above are what
        # guard the split, on trees the walk gets wrong.
        listed = sorted(
            os.fsdecode(name) for name in subprocess.run(
                ["git", "-C", census.REPO, "ls-files", "-z"], check=True,
                stdout=subprocess.PIPE).stdout.split(b"\0") if name)
        self.assertEqual(census.markdown(census.REPO),
                         sorted(rel for rel in listed
                                if rel.endswith(".md") and rel != census.SELF_DOC
                                and self.kept(rel)))
        files, _index = census.suites(census.REPO)
        self.assertEqual(sorted(files),
                         sorted(rel for rel in listed
                                if rel.endswith(".py")
                                and os.path.basename(rel).startswith("test_")
                                and self.kept(rel)))


if __name__ == "__main__":
    unittest.main()
