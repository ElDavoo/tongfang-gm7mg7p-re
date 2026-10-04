#!/usr/bin/env python3
"""§3c's named-versus-spelled counts, held against the census that derives them.

Stands in for [issue
#1162](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1162), whose point
is that `docs/findings.md` §3c carried figures the census no longer produced and
that no checker could see. `check_doc_figure_pins.py` reads figures out of
tables carrying a `verdict` column and §3c has none, so it reports nothing for
the section -- which is why the section drifted twice under a tool built to hold
it. This suite is the missing hold, and the write-up is
`docs/findings/3c-named-versus-spelled.md`.

**It asserts relations, not copied constants.** No expected figure is written
here, deliberately: CLAUDE.md's rule is that a test holds a property of the tree
and never a census of it, and a figure typed into an assertion is a value every
branch that legitimately moves the register file has to edit. So each case
derives what the census says now and checks that §3c's prose says the same
thing. When the census moves, a sentence goes red and the failure names the
sentence -- which is the whole failure this issue is about.

The second class is the other half. It holds §4a-4d: the superseded figures stay
visible in §3c beside the correction, the correction stays a blockquote rather
than an edit, and the frozen section count is unmoved. A tidy-up that deletes a
retracted number would leave every case in the first class green.

Between them, one case holds the `CPU_TEMP` count the correction introduces --
the one figure in §3c that does *not* re-derive. It is held as the relation the
correction argues for (the comment-stripped token count equals the census's
`refs` cell for `0x043E`) rather than as a number, for the same reason as
everything else here.
"""
import argparse
import csv
import importlib.util
import re
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

# Loaded by path the way test_xdata_register_map.py loads it, rather than off
# `sys.path`: the tool is a script beside this suite, not an installed module,
# and the existing suite's loader is the idiom here.
_spec = importlib.util.spec_from_file_location(
    "xdata_register_map", HERE / "xdata_register_map.py")
X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(X)

FINDINGS = ROOT / "docs" / "findings.md"

# The census's own flags at their defaults, because §3c's table is the run
# `--check` reproduces. `census_and_groups` takes `not args.no_eq_guard` as the
# equality guard, so the default is the guard ON -- and getting this backwards
# silently re-derives a different census rather than failing, which is why it is
# spelled out here rather than left to a caller.
ARGS = argparse.Namespace(no_eq_guard=False, export_ownership=False)


def census_counts():
    """Every figure §3c's named/spelled paragraph is about, derived now.

    (named_in_tree, named_main, named_pd_only, symbol_main) -- the three
    distinct questions the paragraph has to keep apart:

      named_in_tree  addresses the generated symbol table names that the
                     census reaches at all, across both programs
      named_main     of those, the ones the main EC's programs touch
      named_pd_only  of those, the ones only the PD image touches
      symbol_main    main-EC addresses the committed `.c` spells *by symbol*,
                     which is a different question from all three

    The census is read once per process rather than per case: it is the whole
    tree, and a case that re-read it would dominate the suite's runtime.
    """
    funcs, by_file = X.load_index()
    names = X.load_names(funcs)
    symbols = X.load_symbols()
    census, _calls, _groups, _raw = X.census_and_groups(
        ARGS, funcs, by_file, names, symbols)
    groups = {g: X.merge_group(census, X.PROGRAM_COL[g]) for g in X.GROUPS}

    everywhere = set(groups["main-ec"]) | set(groups["pd"])
    named = {a for a in everywhere if a in symbols}
    spelled = {a for a, e in groups["main-ec"].items() if "symbol" in e["spellings"]}
    return (len(named),
            len(named & set(groups["main-ec"])),
            len(named - set(groups["main-ec"])),
            len(spelled))


def section_3c():
    """§3c's body, from its heading to the next `### ` heading."""
    text = FINDINGS.read_text(encoding="utf-8")
    start = text.index("### 3c. ")
    rest = text[start + 4:]
    end = rest.find("\n### ")
    return rest if end == -1 else rest[:end]


class ThreeCountsAgainstTheCensus(unittest.TestCase):
    """Each figure in §3c, checked against what the census derives now."""

    # This issue's own correction block. Named rather than matched loosely so a
    # case cannot pass against a different correction's figures.
    CORRECTION = "Corrected 2026-10-04, issue #1162."

    @classmethod
    def setUpClass(cls):
        cls.named, cls.main, cls.pd_only, cls.spelled = census_counts()
        cls.body = section_3c()

    def correction_block(self):
        """This issue's correction block, unquoted, and not the whole of §3c.

        Scoped to *this* block rather than to the section, because the section
        keeps three dated corrections side by side and the two older ones quote
        these same sentences with figures that are now wrong. Asserting against
        the section as a whole would let a superseded 172 satisfy a claim about
        the current 180, which is the opposite of what these cases are for.

        The `>` markers come off so the patterns below read the block as prose
        rather than as markdown source; the block is a blockquote because
        `check_citation_lines.py` passes quoted material over rather than
        checking a retracted figure as if it were current.
        """
        start = self.body.find(self.CORRECTION)
        self.assertNotEqual(start, -1,
                            "§3c no longer carries this issue's correction block")
        block = self.body[start:]
        return "\n".join(line.lstrip("> ").rstrip() for line in block.splitlines())

    def assert_claims_hold(self, derived, patterns, claim):
        """Every figure the block states for this count equals what we derived.

        Every *mention*, not one: the block states the symbol-spelled count
        twice, and a check that only asked whether the right number appeared
        somewhere would pass with one mention stale and the other current. Each
        pattern captures the figure the sentence attributes to this count, and
        every capture has to be the derived one, so a partial edit goes red
        rather than being satisfied by the sentence that was not touched.
        """
        block = self.correction_block()
        seen = False
        for pattern in patterns:
            for match in re.finditer(pattern, block, re.S):
                seen = True
                self.assertEqual(
                    int(match.group(1)), derived,
                    f"{claim} is stated as {match.group(1)} in the sentence "
                    f"{block[max(0, match.start() - 40):match.end() + 40]!r}, "
                    f"and the census derives {derived}")
        self.assertTrue(seen, f"the correction block no longer states {claim}")

    def test_the_named_and_reached_count_is_what_the_section_says(self):
        """The "named addresses the census reaches" figure."""
        self.assert_claims_hold(
            self.named,
            [r"\*\*(\d+)\*\* named addresses appear in the decompiled tree"],
            "the named addresses appearing in the tree")

    def test_the_named_population_they_are_drawn_from(self):
        """The `xdata-symbols.csv` row count, and the `NOT_IN_TREE` remainder.

        The block's own warning is that the named population is the address
        *union* rather than `registers.yaml`'s row count, so both figures are
        stated and their difference is the named-and-reached count the case above
        checks -- which is what makes the sentence re-derivable rather than just
        asserted.
        """
        block = self.correction_block()
        total = re.search(r"of\s+the\s+\*\*(\d+)\*\*\s+addresses `xdata-symbols\.csv`",
                          block, re.S)
        absent = re.search(r"the\s+other\s+\*\*(\d+)\*\*\s+being", block, re.S)
        self.assertIsNotNone(total, "the correction block no longer states the "
                                    "named population")
        self.assertIsNotNone(absent, "the correction block no longer states "
                                     "the NOT_IN_TREE count")
        self.assertEqual(int(total.group(1)), len(X.load_symbols()))
        self.assertEqual(int(absent.group(1)), len(X.NOT_IN_TREE))

    def test_the_main_ec_half_of_that_split_is_what_the_section_says(self):
        """The main-EC-touched half, which is not the symbol-spelled figure.

        Asserted as its own claim rather than as a bare number, because the
        mistake this section exists to correct is reading one count for the
        other.
        """
        self.assert_claims_hold(
            self.main,
            [r"\*\*(\d+)\*\* of the \d+ are touched by the main EC",
             r"\*\*(\d+) and \d+ are two questions"],
            "the main-EC-touched share of that split")

    def test_the_pd_only_half_is_what_the_section_says(self):
        """The PD-image-only half, the third of the split."""
        self.assert_claims_hold(
            self.pd_only,
            [r"and\s+\*\*(\d+)\*\*\s+only by the\s+PD image"],
            "the PD-image-only share of that split")

    def test_the_symbol_spelled_count_is_what_the_section_says(self):
        """The "spells by symbol" figure, which §3c's correction is about.

        `ORACLE["symbol_main_distinct"]` is the pin the section's own correction
        names, so this is the figure that drifted under it.
        """
        self.assert_claims_hold(
            self.spelled,
            [r"`?symbol_main_distinct`?\"?\]`?\s+reads\s+\*\*(\d+)\*\*",
             r"\*\*\d+ and (\d+) are two questions"],
            "the decompile spells by symbol")

    def test_the_named_count_is_the_difference_the_tool_derives(self):
        """`named_in_tree` is `len(symbols) - len(NOT_IN_TREE)`.

        The identity `xdata_register_map.py`'s own self-test holds, restated here
        against the figure §3c prints, so the section's number cannot drift from
        the arithmetic without one of the two going red.
        """
        self.assertEqual(self.named, len(X.load_symbols()) - len(X.NOT_IN_TREE))

    def test_the_two_program_halves_sum_to_the_whole(self):
        """`named_in_tree == named_main + named_pd_only`.

        Held as an identity rather than as two literals: a register added for
        the PD image moves one half and not the other, and only the sum is a
        claim about the tree that stays true across that.
        """
        self.assertEqual(self.named, self.main + self.pd_only)

    def test_the_symbol_spelled_count_is_not_the_named_and_reached_count(self):
        """The three counts are three questions, and the gap is the evidence.

        Being *in* the symbol table and being *spelled* by it in the committed
        `.c` are separate facts. A future edit that collapses them into one
        number would restate the mistake §3c was written to correct, so this
        asserts the ordering holds and that a gap exists to explain.
        """
        self.assertLessEqual(self.spelled, self.main,
                             "more addresses spelled by symbol than named and "
                             "reached is not a state the census can produce")
        self.assertLess(self.spelled, self.main,
                        "the named and the symbol-spelled counts have collapsed "
                        "into one number; §3c's correction is about the gap")


class TheCorrectedCpuTempCountIsHeldToo(unittest.TestCase):
    """The `CPU_TEMP` correction, held against the census the same way.

    The block's own concession is that this is the one figure in §3c that does
    not re-derive, which makes it the one most likely to drift again unnoticed:
    a corrected figure with nothing watching it repeats the gap this issue
    exists to stop, in miniature. So the relation the correction rests on is
    asserted here rather than left as prose.

    The relation, not a constant: the count of `CPU_TEMP` tokens left after
    `xdata_register_map.py`'s own `strip_comments()` removes this repository's
    annotation prose equals the `refs` cell `xdata-registers.csv` carries for
    `0x043E`. The raw, unstripped count is deliberately *not* compared to
    anything -- it is the outlier the correction names, and it moves whenever an
    annotation is reworded, which is not a drift worth a red test.
    """

    ADDRESS = "0x043E"

    def census_refs(self):
        """The `refs` cell the census carries for `CPU_TEMP`'s address."""
        path = ROOT / "ec" / "annotations" / "xdata-registers.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = [r for r in csv.DictReader(handle)
                    if r["addr"].upper() == self.ADDRESS.upper()]
        self.assertEqual(len(rows), 1,
                         f"{self.ADDRESS} is not carried exactly once by "
                         f"xdata-registers.csv, so this relation has no meaning")
        return int(rows[0]["refs"])

    def stripped_token_count(self, token):
        """Occurrences of `token` in the decompiled C, comments blanked out.

        `strip_comments()` is the tool's own, so the count here is the same one
        the correction quotes rather than a re-implementation of it that could
        disagree with the prose.
        """
        count = 0
        for path in sorted((ROOT / "ec" / "decompiled").rglob("*.c")):
            text = path.read_text(encoding="utf-8", errors="replace")
            count += len(re.findall(token, X.strip_comments(text)))
        return count

    def test_the_stripped_token_count_is_the_census_refs_cell(self):
        """Comments out, the token count and the census agree.

        This is the claim the correction makes and the reason it calls the raw
        count the outlier: the annotations quoting the decompile back at itself
        are the whole of the difference between the two numbers.
        """
        stripped = self.stripped_token_count(r"CPU_TEMP")
        self.assertEqual(
            stripped, self.census_refs(),
            "the comment-stripped CPU_TEMP count no longer matches the census's "
            "refs cell for 0x043E, so §3c's corrected count no longer re-derives")


class TheSupersededFiguresStayVisible(unittest.TestCase):
    """§4a-4d, held as a property of the file this change edits.

    The correction is a blockquote beside the wrong version rather than an edit
    of it. Every case above would stay green if someone deleted a retracted
    number, because the retraction is what makes the prose correct.
    """

    @classmethod
    def setUpClass(cls):
        cls.body = section_3c()

    def test_the_superseded_census_rows_are_still_in_the_section(self):
        """The table's own superseded first two rows, quoted by the #342 block.

        Matched as the quoted row rather than as loose digits: these figures
        appear elsewhere in the section too, so a bare `assertIn` would be
        satisfied by an unrelated sentence and would not notice this one going.
        """
        for row in ("1,063 | 157 |\n1,172", "13,937 | 864 | 14,801"):
            with self.subTest(row=row):
                self.assertIn(row.replace("\n", " "),
                              self.body.replace("\n", " "),
                              f"§3c no longer quotes the superseded row {row!r}; "
                              f"a retraction must leave the wrong version visible")

    def test_the_superseded_named_and_spelled_figures_are_still_in_the_section(self):
        """The counts this correction replaces, kept readable beside it.

        Each is matched inside the sentence that states it, for the same reason
        as the rows above: three of the four figures also occur elsewhere in the
        section, so matching the number alone would not notice the sentence that
        carries the retraction being rewritten.
        """
        superseded = (
            "79 of `registers.yaml`'s 101 addresses appear",
            "72 of them touched by the main EC",
            "the 41 main-EC addresses the decompile spells by symbol",
        )
        for sentence in superseded:
            with self.subTest(sentence=sentence):
                self.assertIn(sentence, self.body,
                              f"§3c no longer carries {sentence!r}; a retraction "
                              f"must leave the wrong version visible")

    def test_the_correction_is_a_blockquote_not_an_edit(self):
        """The correction is quoted material, which the citation checks skip.

        `check_citation_lines.py` passes over a paragraph whose raw lines open
        with `>`, so a block full of deliberately superseded figures is not read
        as current prose. That is the property that makes a blockquote the right
        shape here rather than a parenthetical.

        Checked on *this issue's* opening line rather than on the section, since
        §3c already carries two older corrections that are blockquoted for their
        own reasons and would satisfy a section-wide check on their own.
        """
        self.assertRegex(
            self.body,
            r"(?m)^> \*\*Corrected 2026-10-04, issue #1162\.\*\*",
            "this issue's correction is no longer a blockquote, so the citation "
            "checks will read its superseded figures as current prose")

    def test_the_file_carries_no_new_section(self):
        """`docs/findings.md` is frozen: this change corrects one section in place.

        The count is asserted against the freeze tool's own constant rather than
        written out, so there is one number in the tree and not two.
        """
        import check_findings_frozen as frozen
        text = FINDINGS.read_text(encoding="utf-8")
        headings = re.findall(r"(?m)^## (\d+)\. ", text)
        self.assertEqual(len(headings), frozen.FROZEN_SECTIONS)
        self.assertEqual(headings, sorted(headings, key=int),
                         "§3c's correction must not renumber or reorder")


if __name__ == "__main__":
    unittest.main()