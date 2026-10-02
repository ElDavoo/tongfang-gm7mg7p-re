#!/usr/bin/env python3
"""Do the `--export-ownership` refusal's figures come from the pins?

Issue #833 opened on three numerals in that refusal's comment -- 1,171 register
rows, 430 clusters, 10 hand names -- that the tree had moved under, and on a
fourth (the 228 addresses `moved`) that was stale by the same mechanism. The
prose is now re-derived rather than corrected, and this is what holds it there.

**Every case here asserts a relation and never a figure.** The figures the
prose quotes are read from `OWNERSHIP` and from the two committed census CSVs at
run time, and the expected value is *computed* from them -- `39` is
`len(committed cluster_keys) - OWNERSHIP["cluster_keys_kept"]`, not a literal
this file would have to edit when the next re-derivation lands. Writing
`39 of the 439` into an assertion would make this suite red for a change that
is not a defect, which is the failure `test_xdata_guard_off_row_join.py` names
in its own docstring and the reason `CLAUDE.md` asks for the claim rather than
the census. The one number this file does write out is a comment's *line count*,
and that is not a count of the tree: it is the shape of a block the tool's
refusal anchors are resolved out of, exactly as
`test_the_comment_block_keeps_its_six_lines` holds its sibling.

**Why the prose cannot simply interpolate, and what it does instead.** Only an
f-string can read a pin, so only `--help` could have quoted `OWNERSHIP` directly
and it does not either: the argument is long enough that a second interpolated
figure would have pushed the block past the line count
`check_eq_guard_citations.py` resolves `../tools/xdata_register_map.py:5250`
against. The other six sites are comments and docstrings, which cannot
interpolate at all. So the fix is a citation -- `annotations/xdata-export-
ownership.md` §5 for the measurement, `OWNERSHIP` for the pins -- and this file
is what stops a citation quietly going stale the way a literal did: it derives
the figures and holds the one site that has to keep a figure to them.

**The refusal has to keep a figure, and that is not a preference.** Its sibling
guard's own suite holds the comment above this refusal to
`FIGURE_IN_PROSE` ("a figure as prose spells it rather than as a report cell"),
so the citation cannot simply replace the numbers here. The figure survives for
that reason; what changes is that it is now *checked against the pins* rather
than trusted, and the check is a subtraction of two things this repository can
re-derive.

**No hardware, no Ghidra, no network, and no census run.** The two committed
CSVs and the tool's own module-level pins are all this reads; the one
subprocess is `--help`, which argparse answers from the source without touching
an image. Nothing here is evidence about the EC, and nothing here could
overwrite a committed file.
"""
import ast
import csv
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

HERE = Path(__file__).parent
EC = HERE.parent
TOOL = HERE / "xdata_register_map.py"
SIBLING = HERE / "export_ownership.py"
SUITE = HERE / "test_xdata_register_map.py"
README = EC / "README.md"
CLUSTERS = EC / "annotations" / "xdata-clusters.csv"
REGISTERS = EC / "annotations" / "xdata-registers.csv"
NAMES = EC / "annotations" / "xdata-cluster-names.csv"

spec = importlib.util.spec_from_file_location("xdata_register_map", TOOL)
xrm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xrm)

# The refusal this file is about, and the one above it whose comment
# `test_xdata_guard_off_row_join.py` holds to a line count. Both are named as
# the code spells them rather than by line, because a line number in this file
# would be a pin every edit above it moves -- which is the mistake the guard-off
# suite's own `comment_above` exists to avoid.
EXPORT_OWNERSHIP_REFUSAL = "if args.export_ownership and (args.check or args.self_test):"

# A figure as the prose spells it: a numerator, the article, and a
# denominator of at least three digits. Imported from the suite that defines the
# rule rather than re-spelled, because two copies of this regex are two rules
# the next edit has to keep in step, and a disagreement between them would show
# up as one suite going red for the other's reason.
sys.path.insert(0, str(HERE))
from test_xdata_guard_off_row_join import FIGURE_IN_PROSE  # noqa: E402


def rows_of(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def comment_above(source, anchor):
    """The run of `#` lines immediately above `anchor`, and the file's lines.

    Copied in shape from the guard-off suite's method of the same name rather
    than imported: that one is a `TestCase` method reaching for its own `self`,
    and reaching into another suite's instance for a helper is a worse
    dependency than a six-line function written twice."""
    lines = source.splitlines()
    at = next(i for i, line in enumerate(lines) if line.strip() == anchor)
    above = []
    for line in reversed(lines[:at]):
        if not line.strip().startswith("#"):
            break
        above.append(line)
    return list(reversed(above)), lines


def paragraph_holding(text, needle):
    """The blank-line-delimited paragraph of `text` that names `needle`.

    Paragraph granularity, not docstring and not file. A docstring is the wrong
    unit twice over on this tool: the module docstring is a hundred paragraphs
    of census prose and its direction-split paragraph carries figures this
    issue has no business holding, and a whole-file search found `0 of the 108`
    in a bucket table on the first run of this suite. The paragraph is the unit
    the file itself writes in, and it is the unit each of the six sites is."""
    for para in re.split(r"\n\s*\n", text):
        if needle in para:
            return para
    raise AssertionError(f"no paragraph names {needle!r}")


def docstring_holding(source, needle):
    """The one module, class or function docstring in `source` naming `needle`.

    Read out of the parse rather than sliced by offset, so a docstring that
    moves is still found and a slice cannot quietly start mid-sentence."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef,
                                ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        head = body[0]
        if (isinstance(head, ast.Expr)
                and isinstance(head.value, ast.Constant)
                and isinstance(head.value.value, str)
                and needle in head.value.value):
            return head.value.value
    raise AssertionError(f"no docstring names {needle!r}")


def option_block(help_text, flag):
    """The `--flag` entry of argparse's own option list, indentation collapsed.

    Found by the option list's shape rather than by the first mention of the
    flag, because the usage line names every flag before any of them is
    described -- a split on the flag name would hand this case the usage line
    and the whole description with it."""
    lines = help_text.splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.lstrip().startswith(flag))
    block = [lines[start].strip()]
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith(" " * 24):
            break
        block.append(line.strip())
    return " ".join(block)


def figure_of(text, what, after):
    """The `N of the M` pair `text` quotes for `what`, searched after `after`.

    Each of the three figures is looked for by the noun that follows it rather
    than by position, so a re-wrap of the comment moves nothing and a *changed*
    figure is what turns a case red."""
    tail = text.split(after, 1)[-1]
    match = re.search(r"(\d[\d,]*) of the (\d[\d,]*)\s+" + what, tail)
    if not match:
        raise AssertionError(
            f"no {what!r} figure after {after!r} in:\n{text}")
    return tuple(int(g.replace(",", "")) for g in match.groups())


class TheDerivedFigures(unittest.TestCase):
    """The refusal's numbers, checked against what the tool pins.

    The measurement itself is `annotations/xdata-export-ownership.md` §5 and
    `OWNERSHIP`; this is the third reader of it, added because the other two are
    a page and a pin table and neither of them fails when the prose beside them
    stops agreeing."""

    @classmethod
    def setUpClass(cls):
        cls.source = TOOL.read_text(encoding="utf-8")
        cls.comment, cls.lines = comment_above(cls.source, EXPORT_OWNERSHIP_REFUSAL)
        cls.text = "\n".join(cls.comment)
        cls.committed = {r["cluster_key"] for r in rows_of(CLUSTERS)
                         if r["cluster_key"]}
        cls.names = [r for r in rows_of(NAMES) if r["cluster_key"].strip()]
        cls.own = xrm.OWNERSHIP

    def test_the_cluster_figure_is_the_committed_count_less_what_survives(self):
        # The numerator is not a pin of its own: nothing counts "how many keys
        # move", because that is `len(committed) - cluster_keys_kept` and
        # pinning it would be pinning the same measurement twice, from two
        # sides that could then disagree.
        got = figure_of(self.text, "clusters", "the reference count of")
        self.assertEqual(
            got, (len(self.committed) - self.own["cluster_keys_kept"],
                  len(self.committed)),
            "the refusal's cluster figure is no longer the committed census "
            "less the keys OWNERSHIP says survive")

    def test_the_hand_name_figure_is_the_names_file_less_what_survives(self):
        got = figure_of(self.text, "hand", "the reference count of")
        self.assertEqual(
            got, (len(self.names) - self.own["hand_names_kept"], len(self.names)),
            "the refusal's hand-name figure is no longer the committed names "
            "file less the names OWNERSHIP says survive")

    def test_the_row_figure_is_the_pinned_distinct_count(self):
        # `distinct` rather than a row count of its own: the registers CSV is
        # what `--check` holds to a fresh generation, and `OWNERSHIP` is what
        # the census-wide oracle asserts, so the two ends of the same claim are
        # read from one of them rather than counted twice here.
        rows = figure_of(self.text, "register rows", "the reference count of")
        self.assertEqual(rows[1], self.own["distinct"],
                         "the refusal's register-row total is not OWNERSHIP's "
                         "`distinct`")
        self.assertEqual(
            len(rows_of(REGISTERS)), self.own["distinct"],
            "the registers CSV and OWNERSHIP's `distinct` disagree, so either "
            "figure would be quoting a population the other does not")

    def test_the_moved_figure_is_the_pinned_moved_count(self):
        moved = figure_of(self.text, "register rows", "the reference count of")[0]
        self.assertEqual(
            moved, self.own["moved"],
            "the refusal quotes a `moved` width that is not OWNERSHIP's; that "
            "is the one figure here with a pin of its own and it was the one "
            "that drifted furthest")

    def test_the_comment_still_quotes_a_figure_in_prose(self):
        # Held by the sibling suite too, and for the same reason: the comment
        # is the refusal's argument, and an argument with no number in it is one
        # a later change can weaken without anything going red.
        self.assertRegex(self.text, FIGURE_IN_PROSE)


class TheSitesCiteRatherThanRestate(unittest.TestCase):
    """The other six sites, which cannot interpolate and so must point.

    Each of these is a comment or a docstring: there is no f-string in a
    comment, so "read the pin" is not available and the only shape that cannot
    go stale is a citation of where the figure lives. The case below is on the
    *absence of a figure*, which is the claim -- a site that grows a numeral
    back is the defect this issue opened on, and it is a spelling to hold rather
    than a number of the tree to re-derive."""

    # (label, path, needle). Each is one *paragraph*, reached by the sentence
    # that identifies it, so the case is on the site rather than on the file or
    # the docstring it lives in -- both of which are far too coarse here, and
    # both of which the first run of this suite proved it by failing on a
    # bucket table's `0 of the 108` and on a direction-split paragraph's own
    # figures, neither of which this issue is about.
    CITED = (
        ("the module docstring", TOOL, "The default stays off"),
        ("the --export-ownership docstring", TOOL,
         "`export_ownership` reads each routine once"),
        ("the sibling tool's docstring", SIBLING, "The default stays off for the"),
    )

    # A census figure as prose spells it. Deliberately the same shape as
    # FIGURE_IN_PROSE and deliberately not imported: that one is a *floor* the
    # refusal has to clear, and this is the absence everywhere else wants. One
    # rule per direction, so neither can be loosened to pass the other.
    FIGURE = re.compile(r"\d[\d,]* of (?:the )?[\d,]{3,}")

    def sites(self):
        for label, path, needle in self.CITED:
            doc = docstring_holding(path.read_text(encoding="utf-8"), needle)
            yield label, paragraph_holding(doc, needle)

    def test_the_tool_prose_cites_the_page_and_the_pins(self):
        for label, text in self.sites():
            with self.subTest(site=label):
                self.assertIn(
                    "xdata-export-ownership.md", text,
                    f"{label} names neither the page that records the "
                    "measurement nor a pin table to read it from")
        # `OWNERSHIP` is the pin table the tool itself carries; the sibling
        # module cannot import it without a cycle, which is why site six is
        # checked for the page alone.
        self.assertIn("OWNERSHIP", TOOL.read_text(encoding="utf-8"))

    def test_no_prose_site_carries_a_census_figure_any_more(self):
        for label, text in self.sites():
            with self.subTest(site=label):
                found = self.FIGURE.search(text)
                self.assertIsNone(
                    found,
                    f"{label} quotes {found.group(0) if found else ''!r}; the "
                    "measurement belongs to annotations/xdata-export-ownership.md "
                    "§5 and the pins to OWNERSHIP, and a figure typed beside "
                    "them is the thing #833 opened on")

    def test_the_readme_cites_the_section_rather_than_a_figure(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn(
            "`xdata-export-ownership.md` §5", text,
            "the README's export-ownership bullet is the one place a reader "
            "meets this before the tool, and it must send them to §5")
        bullet = text.split("- **`tools/export_ownership.py`**", 1)[-1]
        bullet = bullet.split("\n- **`", 1)[0]
        found = self.FIGURE.search(bullet)
        self.assertIsNone(
            found, f"the README bullet quotes {found.group(0) if found else ''!r}")

    def test_the_test_comment_points_at_the_suite_that_holds_it(self):
        text = SUITE.read_text(encoding="utf-8")
        self.assertIn(
            "test_export_ownership_refusal_figures.py", text,
            "the refusal's test comment quotes what the flag would do to the "
            "census; without the pointer a reader has no way to find what "
            "checks it")

    def test_the_stale_spellings_are_gone_from_every_site(self):
        # A spelling check, not a census: each of these is the pre-#833 way of
        # writing a figure that is now derived, and none of them is a number
        # that could legitimately come back.
        gone = ("35 of the 430", "35 of 430", "5 of the 10", "1,171",
                "228 of the", "Ten of the 427")
        for label, text in self.sites():
            with self.subTest(site=label):
                for spelling in gone:
                    self.assertNotIn(
                        spelling, text,
                        f"{label} still spells the refusal's cost {spelling!r}")


class TheHelpIsReadForWhatItSays(unittest.TestCase):
    """`--help`, which is the surface a reader reaches before running anything.

    The help string changed shape with the rest, and a case that read the source
    would pass on a string argparse never renders. So this asks the parser."""

    @classmethod
    def setUpClass(cls):
        proc = subprocess.run(
            [sys.executable, str(TOOL), "--help"],
            capture_output=True, text=True, check=True)
        cls.help = proc.stdout

    def test_the_flag_still_says_why_it_is_off_and_where_to_read_the_cost(self):
        block = option_block(self.help, "--export-ownership")
        self.assertIn("renumbering", block)
        # argparse re-wraps the help text to the console width and `textwrap`
        # breaks on hyphens, so the cited path renders split at whichever
        # hyphen the width lands on -- `annotations/xdata-export-` /
        # `ownership.md` at one re-wrap and `annotations/xdata-` /
        # `export-ownership.md` at the next. Rejoining `- <space>` undoes
        # exactly that and nothing else: the help text has no spaced hyphen in
        # it to confuse the pair. Asserting the raw substring would pin which
        # hyphen happened to break, which is the renderer's choice and not the
        # string's -- the first run of this case failed for that reason alone.
        self.assertIn(
            "annotations/xdata-export-ownership.md",
            re.sub(r"-\s+", "-", block),
            "--help must still send the reader to the measurement, or the "
            "flag's cost is stated nowhere they will look")

    def test_the_help_carries_no_census_figure_to_go_stale(self):
        block = option_block(self.help, "--export-ownership")
        self.assertIsNone(
            TheSitesCiteRatherThanRestate.FIGURE.search(block),
            "--help quotes a census figure; it is built at parse time and could "
            "read a pin, but the block's line count is what "
            "check_eq_gate_citations resolves a committed citation against, so "
            "it cites §5 instead")

    def test_the_module_docstring_is_part_of_help_and_is_clean_of_figures(self):
        # The docstring is the parser's description, so site one is not private
        # to a reader of the source -- it is on the same surface, and this is
        # the case that says so rather than leaving it to be discovered.
        self.assertIn("The default stays off", self.help)
        tail = self.help.split("The default stays off", 1)[-1]
        described = tail.split("\nusage:", 1)[0]
        self.assertIsNone(
            TheSitesCiteRatherThanRestate.FIGURE.search(described),
            "the module docstring reaches `--help` as the description and must "
            "cite rather than restate")


class TheRefusalBlocksKeepTheirShape(unittest.TestCase):
    """Line counts, because the anchors under them are resolved by position.

    `check_eq_guard_citations.py` reads `committed_output_refusal` out of
    `xdata_register_map.py` by the line it is on, and the guard-off suite reads
    its own anchors as offsets from the `ap.error` call. Both are satisfied only
    while the blocks above them keep their length, so a re-wrap that reads
    better and gains a line turns four other suites red for a change that
    altered no claim. That is the cost the sibling suite's docstring records,
    and the reason this edit is a substitution rather than a rewrite."""

    def setUp(self):
        self.source = TOOL.read_text(encoding="utf-8")

    def test_the_refusal_comment_keeps_its_eleven_lines(self):
        comment, _lines = comment_above(self.source, EXPORT_OWNERSHIP_REFUSAL)
        self.assertEqual(
            len(comment), 11,
            "the --export-ownership refusal comment changed length; the "
            "committed_output_refusal anchor below it moves with it")

    def test_the_ap_error_call_keeps_its_four_lines(self):
        _comment, lines = comment_above(self.source, EXPORT_OWNERSHIP_REFUSAL)
        call = next(i for i, line in enumerate(lines)
                    if line.lstrip().startswith("ap.error("))
        self.assertNotIn(
            "ap.error", lines[call + 4],
            "the refusal grew a line, and the refusal below it moves with it")


class TheRefusalStillFires(unittest.TestCase):
    """The contract is unchanged; a figure fix that moved a guard is not a fix.

    Cheap, and here rather than left to `test_xdata_register_map.py` because
    that suite answers a different question -- whether the two flags are
    refused, yes, but not whether *this* file's edit left the refusal where the
    comment above it still describes the same `if`. The run is bare and stops at
    the guard, so it writes nothing; the whole point of the case is that it
    still cannot."""

    def test_the_flag_is_still_refused_against_the_committed_paths(self):
        proc = subprocess.run(
            [sys.executable, str(TOOL), "--export-ownership"],
            capture_output=True, text=True, cwd=str(EC))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("overwrite the committed census", proc.stderr)


if __name__ == "__main__":
    unittest.main()
