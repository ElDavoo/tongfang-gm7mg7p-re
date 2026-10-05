#!/usr/bin/env python3
"""Offline checks for the sentence boundary inside a blockquote, both ways round.

`line.strip()` takes a blockquote's indentation but not its `>`, so before
`TERMINATOR` carried `>` in its lookahead a boundary inside a quoted paragraph
was recognised only where the marker did not fall between the period and the
next capital. The same text therefore read as one unit or two on the strength
of where an author had wrapped it, with no change in the words -- and a walk
whose population moves with a reflow is not one whose verdicts mean anything.
Measured here by accident, when a reworded pair quoted as a blockquote passed
with the period mid-line and went red on the next wrap.

`TERMINATOR` now carries `>`, so a wrap point landing on the marker is a
boundary like any other. The alternative -- strip the marker before the join --
also makes the wrap irrelevant and was **not** adopted: `TheStripWouldCostACoverage`
holds why, and `docs/findings/blockquote-terminator-wrap.md` records the
measurement. Both readings report no disagreement over the committed corpus,
which is exactly why the verdicts could not decide between them and coverage
did.

**Both directions are pinned, and the second is the load-bearing one.**
`TheWrapDoesNotDecideTheUnit` holds that the pair's two wrappings agree;
`TheFixIsNotALoosening` holds that the re-packed one-sentence form still reports
`0x0800`, which is the control `test_check_cluster_citations.py`'s
`OneAttributionPerUnit` already holds and that a change admitting it would be a
corpus-wide loosening made against one sentence. A fix that passes only the
first class has stopped checking.

**No case asserts a count of the committed tree.** Every fixture is written
inline against a scratch census, so nothing here moves when a write-up lands.
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

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'check_cluster_citations', HERE / 'check_cluster_citations.py')
ccc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccc)

# Two clusters that share no address, which is the property that makes an
# address in the wrong one a real disagreement rather than "close enough".
# `main-ec-081` holds the three bytes the `0xD96C` clear steps over and
# `main-ec-100` holds `0x0800`, which is the second bound the `setb c` makes --
# the pair §26's summary sentence runs together.
#
# A scratch census under fixture names, copied rather than imported from the
# main suite so a case here reads without a second file open, and deliberately
# *not* the committed cluster ids: this suite is about a sentence boundary, and
# a fixture pinned to `xdata-clusters.csv` would go red when a routine is seeded
# without any of that touching the wrapping. One consequence is load-bearing:
# `main-ec-081` also matches the legacy rank form, so every case runs `check()`
# at its default `ranks=True` rather than the committed tree's `ranks=False`.
# Under that switch the walk would pass each fixture below over as `RANK_ONLY`,
# and a case that passes for the wrong reason checks nothing.
CLEAR_MEMBERS = {
    'main-ec-081': {'0x07FD', '0x07FE', '0x07FF'},
    'main-ec-100': {'0x0630', '0x06C4', '0x0800'},
}
# The registers CSV's `known` set, narrowed to what these sentences name. The
# clear's own bounds (`0x0100`, `0x0FFF`) have no registers row, and
# `0xD89F`/`0xD96C`/`0xD982` are code addresses rather than XDATA ones.
CLEAR_KNOWN = {'0x07FD', '0x07FE', '0x07FF', '0x0800', '0x0630', '0x06C4'}

# The pair, in the two wrappings. Identical words; the only difference is where
# the line ends. `MID_LINE` puts the period and the next capital on one line and
# wraps later, at `0xD982`; `AT_WRAP` wraps *between* them, which is the case
# the old lookahead could not see.
MID_LINE = ('> Those three are the whole of the `main-ec-081` cluster. The setb c '
            'at 0xD982\n'
            '> makes the second bound 0x0800.\n')
AT_WRAP = ('> Those three are the whole of the `main-ec-081` cluster.\n'
           '> The setb c at 0xD982 makes the second bound 0x0800.\n')

# The pre-#617 lookahead, spelled out rather than derived from the live pattern.
# A case that reconstructs the old regex from the new one cannot fail when the
# fix is reverted -- deriving `>` out of what is there tests nothing about the
# defect. This is the shape the walk had, so a case can be shown to be red
# against it.
BEFORE = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*_|-])")

# A blockquote marker as it heads a line, which is what the rejected reading
# would have to take off before the join. Never applied to the live walk: it is
# here so `TheStripWouldCostACoverage` can run that reading over the committed
# tree without reaching into the tool to do it.
MARKER = re.compile(r"(?m)^[ \t]*(?:>[ \t]?)+")


def units_of(text, terminator=None):
    """The units `units()` reads under `terminator`, as text."""
    saved = ccc.TERMINATOR
    if terminator is not None:
        ccc.TERMINATOR = terminator
    try:
        return [unit for _, unit in ccc.units(text)]
    finally:
        ccc.TERMINATOR = saved


def cited(text):
    """(count, first address) the checker reports for one piece of prose."""
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
        f.write(text)
        path = f.name
    try:
        problems, _, _ = ccc.check(path, CLEAR_MEMBERS, {}, CLEAR_KNOWN)
    finally:
        os.unlink(path)
    return len(problems), problems[0][3] if problems else None


def held_claims(text, strip_markers=False, census=None):
    """{(address, cluster)} for each attribution the walk holds over `text`.

    Keyed on the attribution rather than on the unit, because a split moves
    which *line* a claim is reported against without changing whether it is held
    at all. Keying on `(path, line, ...)` would call the two readings different
    on every wrapped quote in the corpus and measure nothing: the question is
    coverage, not where the report points.

    `census` is passed in rather than read per call because the corpus
    comparison asks this of every file that cites a cluster, and re-reading both
    CSVs that many times is the difference between a case and a slow one. It
    defaults at call time, not at def time, for the reason
    `census_citation_exemptions.census_of()` gives: a def-time default binds at
    import and silently defeats a caller that patches the base.
    """
    if strip_markers:
        text = MARKER.sub('', text)
    members, known, counts, by_key, by_name = census or ccc.census()
    names = ccc.name_re(by_name)
    transcripts = ccc.transcript_lines(text)
    held = set()
    for lineno, unit in ccc.units(text):
        ids = ccc.cited_clusters(unit, by_key, by_name, names)
        if not ids:
            continue
        addresses = sorted({"0x" + a.upper() for a in ccc.ADDRESS.findall(unit)
                            if "0x" + a.upper() in known})
        if not addresses:
            continue
        reason = ccc.skip_reason(lineno, unit, transcripts)
        if not reason and ccc.RANK.search(unit):
            reason = ccc.RANK_ONLY
        if reason:
            continue
        pairs = ccc.pairings(unit, addresses) if len(ids) > 1 else {}
        for address in addresses:
            expected = [pairs[address]] if address in pairs else ids
            if any(address in members.get(cid, ()) for cid in expected):
                held.add((address, tuple(expected)))
    return held


class TheWrapDoesNotDecideTheUnit(unittest.TestCase):
    """The pair, in both wrappings: the same units, whatever the wrap did.

    The defect in one line is that `AT_WRAP` was a single unit and `MID_LINE`
    two, so the population depended on where the author put the newline. Both
    wrappings have to give the *same* answer and not merely the same count: a
    count alone is satisfied by two different splits.
    """

    def test_both_wrappings_yield_the_same_membership_unit(self):
        # The load-bearing case, and the unit that matters: the one carrying the
        # cluster id, which is what `cited_clusters()` reads and what every rule
        # downstream is asked about. Before the fix this was two units in one
        # wrapping and one in the other, so the walk's population moved with the
        # wrap.
        #
        # It is this unit and not the whole list, because the two wrappings put
        # the marker at different offsets in the joined text -- `MID_LINE` wraps
        # mid-sentence, so its trailing unit carries `> ` between `0xD982` and
        # `makes`. That is where the author wrapped, not something the split
        # chose, and a case demanding the trailing unit match too would be
        # asserting a property of the fixture rather than of the fix.
        def carrying(text):
            return [u for u in units_of(text) if "main-ec-081" in u]

        self.assertEqual(carrying(AT_WRAP), carrying(MID_LINE))
        self.assertEqual(len(carrying(AT_WRAP)), 1,
                         "the membership sentence did not come out as one unit")

    def test_the_pair_is_two_units_either_way(self):
        # Two units is the same claim in the quoting shape: the membership
        # sentence names the cluster, and the `setb c` sentence names none, so
        # it is not read as a citation at all.
        self.assertEqual(len(units_of(MID_LINE)), 2)
        self.assertEqual(len(units_of(AT_WRAP)), 2)

    def test_the_fix_is_what_makes_them_agree(self):
        # Shown from the other side, so the case above is not merely asserting
        # today's behaviour. Against the old lookahead the two wrappings really
        # do disagree, and by exactly the amount the issue reported.
        self.assertEqual(len(units_of(MID_LINE, terminator=BEFORE)), 2)
        self.assertEqual(len(units_of(AT_WRAP, terminator=BEFORE)), 1)

    def test_the_marker_survives_the_join(self):
        # What the fix is *not*: it does not strip the quote. The marker is
        # still in the unit text, which is what keeps a quoted correction
        # readable as a quotation to whoever reads the `--verbose` line, and is
        # the property that tells this reading apart from the rejected one.
        self.assertTrue(all(u.lstrip().startswith('>') for u in units_of(AT_WRAP)),
                        "the fix removed the marker rather than splitting on it")

    def test_a_quote_wrapped_at_a_comma_is_still_one_unit(self):
        # The fix is one character of a lookahead, so it must not have become
        # "split a quote somewhere". A wrap between two clauses of one sentence
        # is still one unit, which is the ordinary wrap the walk exists to
        # handle: an attribution straddling a line break has to stay readable.
        text = ('> The `0x08A8` listing is a member of `main-ec-003`,\n'
                '> and of no other cluster.\n')
        units = units_of(text)
        self.assertEqual(len(units), 1)
        self.assertIn("0x08A8", units[0])
        self.assertIn("main-ec-003", units[0])


class TheFixIsNotALoosening(unittest.TestCase):
    """The other direction, and the one a corpus-wide loosening would fail.

    Making the wrap irrelevant is only a fix if the unit is still sized to one
    attribution. These are the re-packed shapes: one sentence carrying both the
    claim and the operand, which is the form `0x0800` is reported on and which
    the fix must keep reporting. A change that admitted them would be a
    loosening made against a single sentence, and no other case here would see
    it.
    """

    # `main-ec-100` holds `0x0800` and the sentence names `main-ec-081`, so the
    # any-of fallback has nothing to satisfy the operand with.
    REPACKED = ('> **The `0xD96C` clear steps over `0x07FD`, `0x07FE` and '
                '`0x07FF`** — 3,837 of 3,840 bytes, the `setb c` at `0xD982` '
                'making the second bound `0x0800` — and those three are the '
                'whole of the `main-ec-081` cluster.\n')

    def test_the_re_packed_quote_still_reports_the_operand(self):
        # Expected to report, like its unquoted twin in `OneAttributionPerUnit`:
        # it says the unit was too wide, and a quote marker does not make a
        # unit narrower.
        self.assertEqual(cited(self.REPACKED), (1, '0x0800'))

    def test_the_split_quote_is_silent(self):
        # The same claim with the bound in a sentence of its own, which names no
        # cluster and so is not a citation. This is what the pair is *for*, and
        # it is the half of the fix a loosening would take with it.
        self.assertEqual(cited(MID_LINE), (0, None))
        self.assertEqual(cited(AT_WRAP), (0, None))

    def test_drift_inside_a_quote_is_still_reported(self):
        # A wrong id in a quoted correction is a wrong id, and the marker is
        # not a reason to pass it over. Without this the fix could have been
        # "ignore quotes", and every other case here would still pass.
        self.assertEqual(
            cited('> The `0x07FD` listing is a member of `main-ec-100`.\n'),
            (1, '0x07FD'))


class TheStripWouldCostACoverage(unittest.TestCase):
    """Why the rejected reading was rejected, as a property of the corpus.

    Stripping `>` before the join makes the wrap irrelevant too, and is the
    change that reads best. It loses an attribution, and not for the reason one
    would guess: with the marker gone `LIST_ITEM` can see the `-` of a quoted
    tight list, so a blockquote that was one paragraph becomes one unit per
    item. That is the *second* rule switched on for a body of prose it was never
    applied to, and it separates a cluster id from the addresses it governs, so
    the address item — which claims no membership of its own — is passed over.
    A claim nothing checks reads exactly like a claim that is not there, which is
    why this is a case and not a note.

    The comparison is a *relation* over the committed tree and never a figure:
    what is asserted is that the strip drops something the current walk holds,
    which stays true whatever the corpus grows to be. A count of either set
    would be a total of this repository's own prose, and the line carrying it is
    one every merge has to touch.
    """

    @classmethod
    def setUpClass(cls):
        cls.held, cls.stripped = cls._over_committed_tree()

    @staticmethod
    def _over_committed_tree():
        """({path: held}, {path: held}) for every committed `.md` that cites one.

        Both sides come from the checker's own walk and its own functions, in
        the committed-tree mode `main()` uses (`ranks=False`), so this
        population *is* the checker's by construction rather than by a
        comparison some later merge could invalidate.
        """
        census = ccc.census()
        names = ccc.name_re(census[4])
        held, stripped = {}, {}
        for root in ccc.ROOTS:
            for dirpath, dirnames, filenames in os.walk(
                    os.path.join(ccc.REPO, root)):
                dirnames[:] = [d for d in dirnames if not d.startswith('.')]
                for name in sorted(filenames):
                    if not name.endswith('.md'):
                        continue
                    path = os.path.join(dirpath, name)
                    with open(path, encoding='utf-8') as f:
                        text = f.read()
                    if ("main-ec-" not in text and not ccc.CLUSTER_KEY.search(text)
                            and not (names and names.search(text))):
                        continue
                    rel = os.path.relpath(path, ccc.REPO)
                    if rel not in held:
                        held[rel] = held_claims(text, census=census)
                    stripped[rel] = held_claims(text, strip_markers=True,
                                                census=census)
        return held, stripped


class TheStripLosesAClaim(unittest.TestCase):
    """The two directions of that comparison, on the committed tree."""

    @classmethod
    def setUpClass(cls):
        cls.held, cls.stripped = TheStripWouldCostACoverage._over_committed_tree()

    def test_the_committed_walk_holds_something_to_compare(self):
        # Without this, the case below would pass by both sides being empty, so
        # the relation is only worth anything once there is a population.
        self.assertTrue(self.held,
                        "no committed file holds a membership claim at all")

    def test_the_strip_drops_a_claim_the_walk_holds_today(self):
        lost = {path: sorted(held - self.stripped.get(path, set()))
                for path, held in self.held.items()
                if held - self.stripped.get(path, set())}
        self.assertTrue(
            lost,
            "stripping the marker held every claim the current walk holds; if "
            "that is now true, the rejection recorded in "
            "docs/findings/blockquote-terminator-wrap.md is stale and the "
            "decision should be re-opened on its evidence")

    def test_the_current_walk_holds_nothing_the_strip_does_not(self):
        # The other direction, and the one that would say the strip is not
        # simply a narrower reading of the same thing. A strip that lost a claim
        # *and* gained one would be a different rule rather than a stricter one,
        # and the write-up's "coverage-preserving" would be half-true.
        for path, held in self.stripped.items():
            self.assertFalse(
                held - self.held.get(path, set()),
                f"the strip holds a claim in {path} that the current walk does "
                "not")


class AQuoteInsideAFence(unittest.TestCase):
    """The fix splits `>`-prefixed lines inside a fence too, and that is inert.

    A fenced block is still cut into sentences inside itself and `>` is in the
    lookahead now, so a `diff` transcript's `>` lines become units where they
    were one. `docs/findings/testdata-row-claims-no-addr-column.md` carries such
    a transcript, so this is a shape the corpus reaches rather than a
    hypothetical. The units it makes name no cluster and no XDATA address, so
    they are outside every rule and the walk reports nothing new -- pinned here
    because "nothing is reported" and "nothing was examined" print the same, and
    only a reason tells them apart.
    """

    TRANSCRIPT = ('```\n'
                  '2c2\n'
                  '< ... 25 passed over under the five shapes, ...\n'
                  '> ... 25 passed over under the five shapes and the three '
                  'dated refusals, ...\n'
                  '```\n')

    def test_a_diff_transcript_reports_nothing(self):
        self.assertEqual(cited(self.TRANSCRIPT), (0, None))

    def test_the_transcript_lines_are_units_now(self):
        # What the fix actually did here, asserted so the case above cannot pass
        # for the uninteresting reason that nothing changed: the `>` line is its
        # own unit where it used to be part of the block's.
        self.assertGreater(len(units_of(self.TRANSCRIPT)),
                           len(units_of(self.TRANSCRIPT, terminator=BEFORE)))

    def test_a_quoted_claim_inside_a_fence_is_still_a_claim(self):
        # The fence scopes a *regeneration transcript* and nothing else. A
        # quoted membership claim inside an ordinary fenced block is an ordinary
        # citation, so a `>`-prefixed line has to stay reachable: the split must
        # not turn a checked claim into an unread one.
        text = ('```\n'
                '> The `0x07FD` listing is a member of `main-ec-081`.\n'
                '> The `0x0630` listing is a member of `main-ec-081`.\n'
                '```\n')
        self.assertEqual(cited(text), (1, '0x0630'))

    def test_a_quoted_line_in_a_regeneration_transcript_is_still_passed_over(self):
        # And the fence that *is* scoped still is. The transcript reason is
        # reached by line number inside the block, so a split that moved the
        # claim to a unit the block does not cover would let it through; the
        # reason is asserted rather than only the silence, because the two read
        # the same at the exit code.
        text = ('```\n'
                '$ python3 ec/tools/xdata_register_map.py --no-eq-guard\n'
                '> The `0x0630` listing is a member of `main-ec-081`.\n'
                '```\n')
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
            f.write(text)
            path = f.name
        try:
            problems, _, reasons = ccc.check(path, CLEAR_MEMBERS, {}, CLEAR_KNOWN)
        finally:
            os.unlink(path)
        self.assertEqual(problems, [])
        self.assertIn("census-regeneration transcript", reasons)


class AQuotedListIsNotTheStrip(unittest.TestCase):
    """A quoted list keeps reading as one unit, which is what tells the two apart.

    The strip would take the marker off and let `LIST_ITEM` match the item that
    was behind it, so a quoted tight list would become one unit per item where
    today it is one unit. `TERMINATOR`'s `>` does not do that: it splits a
    quoted paragraph at a *sentence* boundary and leaves a quoted list alone.
    The case holds the difference, because the two readings are otherwise easy
    to confuse and the confusion is what would let the strip back in unnoticed.
    """

    QUOTED_LIST = ('> - the `0x07FD` listing is a member of `main-ec-081`, and '
                   'no other\n'
                   '> - the `0x07FE` block is a member of `main-ec-081` too\n')

    def test_a_quoted_tight_list_stays_one_unit(self):
        self.assertEqual(len(units_of(self.QUOTED_LIST)), 1)

    def test_the_strip_would_have_split_it(self):
        # The observable difference between the readings on the same text. The
        # marker is what `LIST_ITEM` cannot see past, so removing it is what
        # makes the list readable as a list -- which is the coverage the strip
        # costs, in a shape this suite can show without the corpus.
        self.assertEqual(len(units_of(MARKER.sub('', self.QUOTED_LIST))), 2)

    def test_the_fix_did_not_change_here(self):
        # The other half: `>` in the lookahead is a sentence rule, and this list
        # has no sentence boundary in it to find.
        self.assertEqual(units_of(self.QUOTED_LIST),
                         units_of(self.QUOTED_LIST, terminator=BEFORE))


class TheCommittedTreeIsStillGreen(unittest.TestCase):
    """The run itself, after the change: exit 0, and every reason still named.

    The lookahead is a change to how the corpus is read, so the committed run
    is the assertion that it is read the same way as far as any verdict goes.
    `SKIPS` is compared in the direction that matters here -- the fix adds no
    reason, so a unit passed over under one nobody wrote down would arrive as a
    summary line that does not describe the run.
    """

    def test_the_run_exits_zero_and_names_every_reason_it_produced(self):
        err, out = io.StringIO(), io.StringIO()
        argv = sys.argv
        sys.argv = ['check_cluster_citations.py']
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = ccc.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, err.getvalue())
        self.assertIn('every checked', out.getvalue())
        printed = out.getvalue().split('skipped: ', 1)[-1].split('\n', 1)[0]
        seen = {part.rsplit(' ', 1)[0] for part in printed.split(', ') if part}
        self.assertTrue(seen, "the walk reached no unit to skip at all")
        self.assertEqual(seen - set(ccc.SKIPS), set(),
                         "the run produced these reasons and SKIPS does not "
                         f"name them: {sorted(seen - set(ccc.SKIPS))}")


if __name__ == '__main__':
    unittest.main()
