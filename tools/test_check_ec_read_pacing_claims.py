#!/usr/bin/env python3
"""Checks on the checker that holds the prose around `ec_watch.py`'s defaults.

`tools/check_ec_read_pacing_claims.py` exists because the class of committed
prose a change to these two tools makes stale has no natural end: six review
rounds on this issue each fixed the sites a review named and each surfaced
more, and the seventh would have cost a CI run to learn the same thing. It
settles the class with two properties derived from the tools -- a rate claim
has to be one their argparse defaults produce, and a `#94` attribution has to
name a tool that is still unpaced.

Both are heuristics over prose, which is exactly where a rule that has quietly
stopped firing looks like a rule that is working: a regex that stops matching
because the wording moved, a `#94` that matches `#940` and nothing else, a
file that a third edit has made unresolvable. So this suite pins the refusals
and the *non*-refusals, each against a string the checker reads on its own, so
a rule that has stopped working fails here rather than on somebody's next edit
to a runbook.

Two things this deliberately does not do. It does not assert a count of the
files or sentences the checker sweeps -- that number moves on every landing
edit, which is the merge-conflict trap `CLAUDE.md` records four times over --
so the green run here says nothing about how many sites exist. And it does not
assert anything about the machine: the checker's subject is what committed
prose says, and no scan of this repository can say whether reading a fan-tach
register stalls a fan.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_ec_read_pacing_claims as checker  # noqa: E402

FIGURES = checker.computed()

# Stands in for a `#94` attribution. The wording matters less than the shape:
# what is under test is that the rule keys on there being a tool behind the
# claim, not on the exact words.
OPEN = "issue #94 is the open work that would make these tools safe by default"

# A tool that paces and one that does not, as `paced`/`unpaced` name them. The
# dictionaries are the checker's own shape -- {name: path} -- with the paths
# unused, because the self-test takes the *names* and asks whether one of them
# is paced.
PACED = {"ec_watch.py": "paced", "slow_probe.py": "unpaced"}


def paced(names):
    return {n: n for n in names if PACED[n] == "paced"}


def unpaced(names):
    return {n: n for n in names if PACED[n] == "unpaced"}


def said(figure):
    return (f"`windows/tools/ec_watch.py` sweeps 2 KiB of EC space in about "
            f"{figure}.")


class DerivedFiguresTests(unittest.TestCase):
    """Property 1's subject: the figures, read out of the tools.

    Asserted as the relation between them rather than as literals, because
    every one of them moves when a default moves and a literal here would be a
    value every change to `ec_watch.py` has to edit.
    """

    def test_the_sweep_cost_is_one_gap_per_address(self):
        self.assertAlmostEqual(FIGURES["sweep_s"],
                               FIGURES["addresses"] * FIGURES["gap_s"])

    def test_a_sweep_a_second_is_the_interval_plus_the_sweep(self):
        self.assertAlmostEqual(
            FIGURES["sweeps_per_s"],
            1.0 / (FIGURES["interval"] + FIGURES["sweep_s"]))

    def test_the_address_count_is_the_range_less_the_page(self):
        path = os.path.join(checker.REPO, checker.TOOLS, checker.WATCH)
        defaults = checker.declared_defaults(path)
        page = checker.declared_range(path)
        start = int(str(defaults["--start"]), 0)
        length = int(str(defaults["--len"]), 0)
        self.assertEqual(FIGURES["addresses"], length - len(page & set(
            range(start, start + length))))
        # The page this exclusion is about is the one the tool declares, so a
        # rename of FAN_TACH goes uncovered here rather than silently
        # checking the wrong range.
        self.assertEqual(page, set(range(0x0460, 0x0470)))


class RateRuleTests(unittest.TestCase):
    """Property 1: a rate claim, and the three things that are not one."""

    def refused(self, body):
        """The refusal one string draws, if any."""
        said = checker.rate_disagreement(body, FIGURES)
        return [] if said is None else [said]

    def test_a_rate_the_defaults_produce_is_not_refused(self):
        self.assertEqual(self.refused(
            f"`ec_watch.py` sweeps its default range in about "
            f"{FIGURES['sweep_s']:.1f}."), [])

    def test_the_interval_default_is_not_a_disagreement(self):
        # `--interval` is one of the computed durations, so a sentence that
        # quotes it is quoting the tool and not describing a retired default.
        self.assertEqual(self.refused(
            "`ec_watch.py` sweeps on a 0.25 s default sweep interval."), [])

    def test_a_retired_rate_is_refused(self):
        self.assertEqual(len(self.refused(
            "`ec_watch.py` sweeps 2 KiB of EC space in about 150 ms.")), 1)

    def test_a_retired_frequency_is_refused(self):
        self.assertEqual(len(self.refused(
            "`ec_watch.py` sweeps 2 KiB about 2.5 times a second, fast "
            "enough to catch a settings write as it lands.")), 1)

    def test_a_figure_in_the_wrong_unit_is_refused(self):
        # The one that made the first version of this shape refuse `--seconds
        # 20` and a 500 ms timeout: a duration claim has to carry a read or a
        # sweep next to its figure, or it is not about the tool's read rate.
        self.assertEqual(self.refused(
            "Run it for 20 s and wait 500 ms between windows, watching "
            "`ec_watch.py` output."), [])

    def test_a_dated_record_of_a_past_run_is_left_alone(self):
        self.assertEqual(self.refused(
            "`ec_watch.py` took those two windows at 0.2 s sweeps on "
            "2026-09-23, into evidence/ec-watch/."), [])

    def test_a_figure_the_defaults_round_to_is_admitted(self):
        # Prose rounds, and a runbook that writes "about 12 s" is making the
        # same claim as a banner that writes 12.2.
        coarse = FIGURES["sweep_s"] * 100 // 100
        self.assertEqual(self.refused(
            f"`ec_watch.py` sweeps its default range in about {coarse:g} s."),
            [])

    def test_the_tool_s_own_docstring_is_held_to_the_same_figure(self):
        # The tools describe themselves in prose, so the rule's own subject is
        # in scope for it -- which is why `ec_watch.py`'s opening paragraph
        # carries the figure as digits rather than as "a little over twelve
        # seconds". A scan that reads digits cannot read an adjective, and a
        # docstring that leaned on one would be the sentence the rule could
        # not reach.
        path = os.path.join(checker.REPO, checker.TOOLS, checker.WATCH)
        opening = checker.blocks(path)[0][1]
        self.assertEqual(self.refused(opening), [])
        # And the shape that one would have, with a figure the defaults do
        # not produce, is refused from the same file and the same paragraph.
        self.assertEqual(len(self.refused(
            "`ecrw.py` gives a sweep in about 150 ms, fast enough to catch a "
            "settings write as it lands.")), 1)


class AttributionRuleTests(unittest.TestCase):
    """Property 2: an attribution, and what it has to have behind it."""

    def refused(self, body, also_unpaced=()):
        """The paced tools one string's attribution rests on, if any.

        The two maps handed to the rule are the *resolved* set -- what
        `attribution_problems` builds, the tools a block names unioned with
        the unpaced ones its file is about -- so the helper resolves them the
        same way rather than passing a fixed pair no string could produce.
        `also_unpaced` stands in for the file half.
        """
        names = {n for n in checker.TOOL_NAME.findall(body) if n in PACED}
        names |= set(also_unpaced)
        named = checker.attribution_disagreement(
            body, paced(names), unpaced(names))
        return [] if named is None else [named]

    def test_an_attribution_naming_only_paced_tools_is_refused(self):
        # The shape this whole tool exists for. `ec_watch.py` is paced, so an
        # attribution resting on it alone names no open work at all.
        self.assertEqual(len(self.refused(
            OPEN + " `ec_watch.py` is the tool it is about.")), 1)

    def test_an_unpaced_tool_the_file_is_about_carries_the_attribution(self):
        # A paragraph that names a paced tool is not the whole of what it
        # rests on: this is a runbook whose subject tool has no gap of its
        # own, and the work behind "the open work" is still open. Reading the
        # paragraph's own names alone refused it.
        self.assertEqual(self.refused(
            "`ecrw.py` is the reader here; " + OPEN,
            also_unpaced=("slow_probe.py",)), [])

    def test_an_attribution_naming_an_unpaced_tool_is_not_refused(self):
        self.assertEqual(self.refused(OPEN + " `slow_probe.py` still is."), [])

    def test_an_unpaced_tool_anywhere_in_the_attribution_carries_it(self):
        self.assertEqual(self.refused(
            "ec_watch.py now paces; slow_probe.py does not. " + OPEN), [])

    def test_a_tool_named_twice_is_reported_once(self):
        # The message names what the claim rests on, and it used to list one
        # tool once per mention of it in the sentence -- so the same tool read
        # as two.
        self.assertEqual(self.refused(
            OPEN + " `ec_watch.py` paces now; `ec_watch.py` did not."),
            ["ec_watch.py"])

    def test_a_hazard_sentence_is_not_an_attribution(self):
        # #94 also owns an access shape and a watch set. A sentence that says
        # what the hazard *is* has no open work behind it and is not this
        # rule's subject.
        self.assertEqual(self.refused(
            "an unaligned four-byte read over 0x0460-0x046F is issue #94's "
            "access."), [])

    def test_another_issue_number_is_not_this_issue(self):
        # `#940`, `#941` and the rest are cross-referenced by number in running
        # prose here, and a substring match reads them all as this one.
        self.assertEqual(self.refused(
            "follow-up 2 asks whether [#940](x) still holds."), [])


class TreeTests(unittest.TestCase):
    """The check against the tree as it is, which is what a gate would run."""

    def test_the_committed_tree_has_no_disagreement(self):
        # The property under test is "the class terminates", and that is only
        # demonstrable on the tree: the sweep over `docs/` and the tool
        # sources is what enumerated the class in the first place.
        problems = []
        tools = checker.ec_tools()
        for rel in checker.prose_files():
            problems.extend(checker.rate_problems(rel, FIGURES))
            problems.extend(checker.attribution_problems(rel, tools))
        self.assertEqual(problems, [], "\n".join(
            f"{p['file']}:{p['line']} {p.get('said', '')}" for p in problems))

    def test_the_tools_that_read_the_ec_are_derived_not_listed(self):
        tools = checker.ec_tools()
        self.assertIn("ec_watch.py", tools)
        # `ecrw.py` is here because it defines `Ec` rather than because it
        # imports it: it is one of the two tools this rule is written about,
        # and a subject set that dropped it left an attribution resting on
        # `ecrw.py dump` invisible -- a hole in the stopping rule exactly
        # where a contributor would hit it.
        self.assertIn("ecrw.py", tools)
        # The shared fixture defines an `Ec` too, and is not a tool: it opens
        # no driver, and reading it as an unpaced one would offer a test
        # double as an open question.
        self.assertNotIn("ecrw_fake.py", tools)
        self.assertFalse([n for n in tools if n.startswith("test_")])

    def test_both_tools_this_change_paced_are_read_as_paced(self):
        # The convergence argument is that the two tools drop out of every
        # attribution on their own. That is only true if both are in the set
        # the argument is about.
        paced = checker.paced_tools()
        for name in (checker.WATCH, checker.DUMP):
            self.assertIn(name, paced)

    def test_an_attribution_resting_on_the_dump_tool_alone_is_refused(self):
        # The case the subject set used to miss. Held against the real sets
        # rather than invented ones, because what is under test is that
        # `ecrw.py` is *in* them.
        tools = checker.ec_tools()
        for name in (checker.WATCH, checker.DUMP):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "attribution.md"
                path.write_text(
                    f"`{name}` walks the fan page with no delay; {OPEN}\n")
                problems = checker.attribution_problems(str(path), tools)
                self.assertEqual([p["named"] for p in problems], [name])

    def test_a_paced_tool_is_read_as_paced_from_its_own_source(self):
        path = os.path.join(checker.REPO, checker.TOOLS, "ec_watch.py")
        self.assertTrue(checker.paces_reads(path))
        other = os.path.join(checker.REPO, checker.TOOLS,
                             "manual_fan_ctrl_probe.py")
        self.assertFalse(checker.paces_reads(other))


if __name__ == '__main__':
    unittest.main()