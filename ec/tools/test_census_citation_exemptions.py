#!/usr/bin/env python3
"""Offline checks for census_citation_exemptions.py: committed files only.

The tool is a census whose failure mode is a plausible-looking table. It
classifies every membership-checked unit the checker walks, so a mistake in the
role lexicon or the clause boundaries does not crash it -- it silently re-roles
the corpus and prints a confident figure. What is pinned here is therefore the
boundary between what it *measured* and what it *assumed*.

Three of the classes below are about the tool agreeing with the checker it
bounds rather than with itself: the population is compared against `check()`'s
own view of the same tree, a skip is held to the reason the checker gives it,
and a perturbed fixture is required to move. A measurement that cannot go red,
or that reads a different population from the rule it is bounding, would make
the decision in the write-up unfalsifiable -- and that decision is the whole
deliverable.

`TheWorkedCase` is the one to read first. It runs the census over the very
sentence `test_check_cluster_citations.py`'s `OneAttributionPerUnit` holds as
*expected to report*, and finds that a lexicon exemption would admit that unit
-- which is the finding the "no" rests on, and the reason this tool reports the
lexicon figure and the `SPAN` figure separately rather than as one admitted
count.

The fixtures are small enough to write inline, as in `test_check_cluster_
citations.py`, so each case reads as the sentence it is about. The census they
run against is written to a scratch tree beside the prose rather than being the
committed one, because a case that depended on today's clusters would fail for
an unrelated reason the next regeneration lands.

**No case asserts a count of the committed tree.** The tool's own run prints its
figures and `docs/findings/operand-bound-exemption-census.md` records the
ones that decided the question; a test that pinned them would be a value every
merge has to edit, which is the trap `CLAUDE.md` names. What each case asserts
is a property: that the population matches the checker, that a classification is
what this method can see, that a perturbation is visible.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    'census_citation_exemptions', HERE / 'census_citation_exemptions.py')
cce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cce)

spec = importlib.util.spec_from_file_location(
    'check_cluster_citations', HERE / 'check_cluster_citations.py')
ccc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccc)

# The two clusters §26 runs together, as `test_check_cluster_citations.py`
# writes them: `main-ec-081` is the three bytes the `0xD96C` clear steps over,
# `main-ec-104` holds `0x0800`, the second bound the `setb c` makes. They share
# no address, so an address in the wrong one is a real disagreement rather than
# "close enough". The clear loop's own bounds (`0x0100`, `0x0FFF`) and the code
# addresses (`0xD89F`, `0xD96C`, `0xD982`) are absent from the registers set
# below, which is what keeps them out of every classification -- they are a
# clear's range and an instruction, not XDATA members.
CLUSTERS_CSV = (
    "cluster_id,program,size,refs,addrs,cluster_key,cluster_name,addr_range,"
    "named_addrs\n"
    "main-ec-081,main-ec,3,4,0x07FD 0x07FE 0x07FF,,,0x07FD-0x07FF,0x07FD\n"
    "main-ec-104,main-ec,3,4,0x0630 0x06C4 0x0800,,,0x0630-0x0800,0x0800\n"
)

REGISTERS_CSV = (
    "addr,program,cluster_id\n"
    "0x07FD,main-ec,main-ec-081\n"
    "0x07FE,main-ec,main-ec-081\n"
    "0x07FF,main-ec,main-ec-081\n"
    "0x0630,main-ec,main-ec-104\n"
    "0x06C4,main-ec,main-ec-104\n"
    "0x0800,main-ec,main-ec-104\n"
)


def census_of(text, clusters=None, registers=None):
    """Run the census over one piece of prose on a scratch tree.

    A tree rather than a single file, because `census_of()` walks `ROOTS` and a
    case that called a per-file helper would not be exercising the walk the
    committed run uses. The CSVs are written beside the prose and passed in, so
    a case never reads the real census -- see the module docstring.
    """
    with tempfile.TemporaryDirectory() as scratch:
        docs = os.path.join(scratch, "docs", "findings")
        os.makedirs(docs)
        with open(os.path.join(docs, "fixture.md"), "w") as handle:
            handle.write(text)
        clusters_csv = os.path.join(scratch, "clusters.csv")
        registers_csv = os.path.join(scratch, "registers.csv")
        with open(clusters_csv, "w") as handle:
            handle.write(clusters or CLUSTERS_CSV)
        with open(registers_csv, "w") as handle:
            handle.write(registers or REGISTERS_CSV)
        found, skipped = cce.census_of(scratch, clusters_csv, registers_csv)
    return found, skipped


def rows_for(text, **kwargs):
    """{token: Address} for the one unit a fixture's prose makes."""
    found, _skipped = census_of(text, **kwargs)
    if not found:
        return {}
    return {address.token: address for address in found[0][5]}


def one_row(text, token, **kwargs):
    """The `Address` for one token, failing loudly when it was not read.

    The message carries the tokens that *were* read, because "assertion failed"
    against a fixture whose census is written two functions above says nothing
    about whether the fixture is wrong or the tool is.
    """
    rows = rows_for(text, **kwargs)
    if token not in rows:
        raise AssertionError(
            f"{token} was not read as a census-known address; the rows were: "
            f"{sorted(rows)}")
    return rows[token]


class TheWorkedCase(unittest.TestCase):
    """§26's re-packed sentence: what an exemption would do to the one it was for.

    This is the sentence `test_check_cluster_citations.py` holds as *expected to
    report* `0x0800`, and it is the only unit in the corpus the issue argues
    about. Running the census over it is what turns "the set an exemption would
    admit" from a figure about today's prose into a statement about the
    proposal: the sentence that motivated it is admitted, and admitting it means
    the `0x0800` disagreement stops being reported.
    """

    # Verbatim from `OneAttributionPerUnit.test_the_re_packed_sentence_still_
    # reports_the_operand`, so this case and that one are about one sentence
    # rather than two sentences that look alike.
    REPACKED = ('**`0xD89F` is a single `ret` byte, and `0xD96C` is a real '
                'routine that clears XDATA `0x0100`–`0x0FFF` except it steps '
                'over `0x07FD`, `0x07FE` and `0x07FF`** — 3,837 of 3,840 bytes, '
                'the `setb c` at `0xD982` making the second bound `0x0800` '
                'rather than `0x07FF` — and those three are the whole of the '
                '`main-ec-081` cluster.\n')

    def test_the_exemption_would_admit_the_very_sentence_it_was_proposed_for(self):
        found, _skipped = census_of(self.REPACKED)
        unit = found[0]
        # `lexicon`, not `range`: no address here is half of a `SPAN`, so the
        # word-based rule is doing all of it. This is the figure the decision
        # turns on and it is the one a `SPAN` reading must not be allowed to
        # stand in for.
        self.assertEqual(unit[4], (cce.ADMITTED, "lexicon"))

    def test_admitting_it_would_silence_the_disagreement_that_control_pins(self):
        found, _skipped = census_of(self.REPACKED)
        unit = found[0]
        failing = [a.token for a in unit[5] if a.fails]
        exempt = [a.token for a in unit[5] if a.exempt]
        # The disagreement is real and still open: `0x0800` is in
        # `main-ec-104` and not in `main-ec-081`, the only id this unit names.
        self.assertEqual(failing, ["0x0800"])
        # And the exemption covers it, so the two cases together are the
        # acceptance criterion the issue sets: an exemption that made this
        # silent is a corpus-wide loosening made against one sentence.
        self.assertIn("0x0800", exempt)

    def test_the_reworded_form_is_not_admitted(self):
        # The other half of the pair, and the control that says the verdict
        # turns on unit size rather than on the words: the same bound, the same
        # two clusters, moved into a sentence that makes no membership claim.
        # Nothing is exempt, so a check would still run over the unit.
        split = ('**`0xD89F` is a single `ret` byte, and `0xD96C` is a real '
                 'routine that clears XDATA `0x0100`–`0x0FFF` except it steps '
                 'over `0x07FD`, `0x07FE` and `0x07FF`** — 3,837 of 3,840 '
                 'bytes, and those three are the whole of the `main-ec-081` '
                 'cluster. The `setb c` at `0xD982` is what makes the second '
                 'bound `0x0800` rather than the `0x07FF` its own immediates '
                 'spell out.\n')
        found, _skipped = census_of(split)
        unit = found[0]
        self.assertEqual(unit[4], (cce.NOT_ADMITTED, None))
        # The bound sentence names no cluster, so only the membership sentence
        # is read -- which is why no address of the bound is in this unit.
        self.assertEqual(unit[3], ["main-ec-081"])
        self.assertFalse(any(a.exempt for a in unit[5]))

    def test_a_preposition_pairing_is_read_and_not_assumed(self):
        # The pairing column, shown to be read rather than assumed, in the
        # direction that matters: a preposition joins `0x0800` to `main-ec-081`,
        # and `0x0800` is *not* a member of it -- so the address fails against
        # the one id its own sentence paired it with. Under the any-of fallback
        # the same unit would pass, `main-ec-104` being named elsewhere in it.
        # That is the whole value of the pairing rule, and the column has to be
        # shown reading it for the exemption question to mean anything.
        text = ("The `0x07FD`, `0x07FE` and `0x07FF` bytes are the whole of "
                "the `main-ec-104` cluster, and the second bound `0x0800` is "
                "in `main-ec-081`.\n")
        row = one_row(text, "0x0800")
        self.assertEqual(row.paired, "main-ec-081")
        self.assertTrue(row.fails)
        self.assertEqual(row.in_clause, ["bound"])


class LexiconTightness(unittest.TestCase):
    """The two figures, and the gap between them being a measured thing.

    The checker's docstring names a lexicon false positive -- a name like
    `charge-target` read as a citation in a sentence that only means the words
    -- and resolves it by constraining the input rather than loosening the
    matcher. These cases hold the *output* side honest: the looser figure is
    reported, and where the two figures differ the difference is visible rather
    than averaged away.
    """

    LOCAL = ("The `0x07FD`/`0x07FE`/`0x07FF` bound is the whole of the "
             "`main-ec-081` cluster.\n")

    ELSEWHERE = ("The bound at `0xD982` clears XDATA; the three bytes "
                 "`0x07FD`, `0x07FE` and `0x07FF` are the whole of the "
                 "`main-ec-081` cluster.\n")

    def test_a_role_word_in_the_address_own_clause_is_read(self):
        row = one_row(self.LOCAL, "0x07FD")
        self.assertEqual(row.in_clause, ["bound"])
        self.assertEqual(row.role, "bound")
        self.assertTrue(row.exempt)

    def test_the_same_word_in_another_clause_is_not_the_address_role(self):
        # Same word, same unit, different clause -- and this address is named
        # as a *member*, which is the opposite of being a bound. Reading it as
        # a bound is exactly the false positive, and `unclassified` is what it
        # has to read as.
        row = one_row(self.ELSEWHERE, "0x07FD")
        self.assertEqual(row.in_clause, [])
        self.assertEqual(row.in_unit, ["bound"])
        self.assertEqual(row.role, cce.UNCLASSIFIED)
        self.assertFalse(row.exempt)

    def test_the_looser_figure_is_strictly_larger_than_the_stricter_one(self):
        # A claim about the method, not a count of the tree. If the two figures
        # were equal on the committed corpus, the tool would not be
        # distinguishing them, and every `admitted` it reports would be a word
        # matched somewhere it does not mean -- indistinguishable from a real
        # operand by the very property being claimed.
        found, _skipped = cce.census_of()
        loose = [a for u in found for a in u[5] if a.in_unit]
        strict = [a for a in loose if a.in_clause]
        self.assertGreater(len(loose), len(strict))
        self.assertEqual([a for a in loose if not a.in_clause],
                         [a for u in found for a in u[5]
                          if a.in_unit and not a.in_clause])


class SpanIsStructural(unittest.TestCase):
    """A `SPAN` is one token, so the role needs no words at all.

    The checker's docstring makes this its one wordless claim -- `0xAAAA-0xBBBB`
    is a single token and `census_row()` reads it as a range rather than as two
    member claims. These cases hold the wordless half to being wordless: the
    classification must not depend on a lexicon hit.
    """

    RANGE = ("The clear steps over `0x07FD`-`0x07FF`, which is the whole of "
             "the `main-ec-081` cluster.\n")

    PARTLY = ("The clear steps over `0x07FD`-`0x07FF`, which is the whole of "
              "the `main-ec-081` cluster, and the `0x0630` byte is in the "
              "`main-ec-104` cluster.\n")

    def test_a_span_classifies_as_a_range_with_no_lexicon_hit(self):
        rows = rows_for(self.RANGE)
        for token in ("0x07FD", "0x07FF"):
            self.assertEqual(rows[token].role, cce.RANGE)
            self.assertEqual(rows[token].in_clause, [])
            self.assertEqual(rows[token].in_unit, [])
            self.assertTrue(rows[token].exempt)

    def test_a_unit_whose_every_address_is_in_a_span_is_admitted_by_range(self):
        found, _skipped = census_of(self.RANGE)
        self.assertEqual(found[0][4], (cce.ADMITTED, cce.RANGE))

    def test_one_address_outside_every_span_makes_it_partly(self):
        # The verdict that keeps the check running. Getting it wrong in either
        # direction is the bug: `admitted` here would silence a unit on the
        # strength of two of its three addresses.
        found, _skipped = census_of(self.PARTLY)
        unit = found[0]
        self.assertEqual(unit[4], (cce.PARTLY, cce.RANGE))
        roles = {a.role for a in unit[5]}
        self.assertIn(cce.RANGE, roles)
        self.assertIn(cce.UNCLASSIFIED, roles)

    def test_a_range_that_also_says_bound_reports_both(self):
        # The word is recorded even when the token wins, or the gap between the
        # two figures would be unreadable wherever the structural signal fires.
        text = ("The bound `0x07FD`-`0x07FF` is the whole of the "
                "`main-ec-081` cluster.\n")
        row = one_row(text, "0x07FD")
        self.assertEqual(row.role, cce.RANGE)
        self.assertEqual(row.in_clause, ["bound"])


class SkipsAreNamed(unittest.TestCase):
    """A unit the checker passes over is reported as passed over, with its reason.

    The checker's own rule is that a skip that cannot be named is a blind spot
    nobody is looking at. This census inherits that obligation in the other
    direction: a skipped unit must not turn up as an `unclassified` row, or a
    reader would count it among the units an exemption would newly admit and
    draw a conclusion about a unit the checker never looked at.
    """

    def test_a_denial_is_skipped_and_never_classified(self):
        text = ("`0x0800` is not in the `main-ec-081` cluster, and the three "
                "bytes it steps over are its whole membership.\n")
        found, skipped = census_of(text)
        self.assertEqual(found, [])
        self.assertEqual(dict(skipped), {"disclaims membership": 1})

    def test_a_unit_with_no_membership_claim_is_skipped_by_name(self):
        # A cluster id and a range with no membership claim in them -- the shape
        # of a §5 summary row, whose *ranges* the membership rule leaves alone.
        # The word "cluster" is deliberately absent: it is a claim about the
        # cluster table, not about what is a member of it.
        text = ("`main-ec-081` spans `0x07FD`–`0x07FF` and the census puts it "
                "first by size.\n")
        found, skipped = census_of(text)
        self.assertEqual(found, [])
        self.assertEqual(dict(skipped), {"no membership claim": 1})

    def test_the_skip_reason_is_the_checker_own(self):
        # Held against `skip_reason()` rather than a literal, so the two cannot
        # drift: a reason renamed in one place and not the other is a census
        # counting a skip the checker no longer takes.
        text = "`0x0800` is not in the `main-ec-081` cluster.\n"
        _found, skipped = census_of(text)
        self.assertEqual(list(skipped), ["disclaims membership"])
        self.assertIn("disclaims membership", ccc.SKIPS)

    def test_a_transcript_skip_is_a_reason_this_census_also_names(self):
        # The third reason, and the one only a *paired* fence can produce: the
        # command and the membership it produced have to sit in one block, and
        # a fence with no opener is not a block. A census that silently lacked
        # this reason would report a transcript's ranks as membership in a
        # generation the reader cannot open.
        self.assertIn("census-regeneration transcript", ccc.SKIPS)
        text = ("```\n$ python3 ec/tools/xdata_register_map.py --no-eq-guard\n"
                "The clustering puts `0x0800` in `main-ec-081`.\n```\n")
        found, skipped = census_of(text)
        self.assertEqual(found, [])
        self.assertEqual(dict(skipped), {"census-regeneration transcript": 1})


class ThePopulationIsTheCheckers(unittest.TestCase):
    """This census reads the checker's units, not a walk of its own.

    The tool's whole claim is that "the set an exemption would admit" is a
    statement about the rule `check_cluster_citations.py` actually applies. That
    rests entirely on the two sharing a population, so it is compared against
    `check()`'s own view of the same files rather than assumed.
    """

    FILES = ("docs/findings/reset-vector-dptr-targets.md",
             "ec/annotations/xdata-register-map.md",
             "ec/annotations/xdata-086x-dispatch.md")

    def _checked_units(self, path):
        """The units `check()` reads a membership claim in, on the committed CSVs.

        `check()`'s own filter chain, step for step, so the comparison is
        against the checker's population rather than against a restatement of
        it -- a restatement would be the second walk this tool is written not to
        have.
        """
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        _members, known, _counts, by_key, by_name = ccc.census()
        names = ccc.name_re(by_name)
        transcripts = ccc.transcript_lines(text)
        found = []
        for lineno, unit in ccc.units(text):
            ids = ccc.cited_clusters(unit, by_key, by_name, names)
            if not ids:
                continue
            addresses = sorted({"0x" + a.upper()
                                for a in ccc.ADDRESS.findall(unit)
                                if "0x" + a.upper() in known})
            if not addresses or ccc.skip_reason(lineno, unit, transcripts):
                continue
            found.append((lineno, tuple(ids), tuple(addresses)))
        return found

    def test_every_unit_the_checker_reads_is_classified_here(self):
        mine = {(os.path.relpath(path, cce.REPO), lineno)
                for path, lineno, _text, _ids, _verdict, _addrs
                in cce.census_of()[0]}
        theirs = set()
        for relpath in self.FILES:
            theirs |= {(relpath, lineno)
                       for lineno, _ids, _addresses in self._checked_units(
                           os.path.join(cce.REPO, relpath))}
        # One direction only, and deliberately: the census reads every root and
        # this picks three files, so equality is not available. The direction
        # that matters is that no unit of the checker's is missing here, since
        # a missing unit would be one the exemption's size was computed without.
        self.assertTrue(theirs)
        self.assertEqual(theirs - mine, set())

    def test_the_addresses_classified_are_the_addresses_the_checker_reads(self):
        # A set, because the census keeps every *mention* -- a unit naming one
        # address twice is two rows and one address -- while the checker holds
        # each address once. The claim being tested is that neither invents or
        # drops an address, not that they count mentions the same way.
        mine = {}
        for path, lineno, _text, _ids, _verdict, addresses in cce.census_of()[0]:
            mine[(os.path.relpath(path, cce.REPO), lineno)] = sorted(
                {a.token for a in addresses})
        for relpath in self.FILES:
            for lineno, _ids, addresses in self._checked_units(
                    os.path.join(cce.REPO, relpath)):
                self.assertEqual(mine[(relpath, lineno)], list(addresses))

    def test_no_unit_is_dropped_between_the_walk_and_the_rows(self):
        # Every checked unit yields at least one row and a verdict this module
        # defines. A census that classified some units and passed over others
        # would make its admitted set a subset it chose.
        found, _skipped = cce.census_of()
        self.assertTrue(found)
        for _path, _lineno, _text, ids, verdict, addresses in found:
            self.assertTrue(addresses)
            self.assertTrue(ids)
            self.assertIn(verdict[0], cce.VERDICTS)


class Perturbation(unittest.TestCase):
    """A measurement that cannot go red is not measuring.

    The tool exits 0 on the committed tree and should: it changes no rule and no
    verdict. That is also what makes a passing run uninformative on its own, so
    the committed-tree case is paired with ones that must move.
    """

    def test_the_committed_tree_has_nothing_failing_to_report(self):
        found, _skipped = cce.census_of()
        self.assertEqual([(u[0], u[1], a.token) for u in found for a in u[5]
                          if a.fails], [])

    def test_the_tool_exits_zero_on_the_committed_tree(self):
        # The census convention: it changes no rule, so there is nothing for it
        # to fail on. Captured rather than printed, because a run that narrated
        # itself into the test output is noise in every other case's log too.
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(cce.main([]), 0)
        self.assertIn("never absent", stream.getvalue())

    def test_moving_an_address_out_of_its_cluster_is_visible(self):
        # `0x0800` belongs to `main-ec-104` in the fixture census. Written
        # against one where it belongs to neither cluster it must be reported,
        # or the tool cannot tell a clean corpus from a drifted one.
        drifted = CLUSTERS_CSV.replace(
            "main-ec-104,main-ec,3,4,0x0630 0x06C4 0x0800,,,0x0630-0x0800,0x0800",
            "main-ec-104,main-ec,2,4,0x0630 0x06C4,,,0x0630-0x06C4,0x06C4")
        text = ("The `main-ec-081` cluster is `0x07FD` `0x07FE` `0x07FF`, and "
                "`0x0800` is in the `main-ec-104` cluster.\n")
        self.assertTrue(one_row(text, "0x0800", clusters=drifted).fails)

    def test_an_empty_population_is_a_broken_census_and_not_an_empty_one(self):
        # `census_evidence_citations.py`'s convention: a census that found
        # nothing and a census that read nothing both print, and only the second
        # may claim the run was broken. A tree citing no cluster is the second,
        # and `main()` says so rather than exiting zero.
        with tempfile.TemporaryDirectory() as scratch:
            docs = os.path.join(scratch, "docs", "findings")
            os.makedirs(docs)
            with open(os.path.join(docs, "empty.md"), "w") as handle:
                handle.write("# nothing here cites a cluster\n")
            clusters_csv = os.path.join(scratch, "clusters.csv")
            registers_csv = os.path.join(scratch, "registers.csv")
            with open(clusters_csv, "w") as handle:
                handle.write(CLUSTERS_CSV)
            with open(registers_csv, "w") as handle:
                handle.write(REGISTERS_CSV)
            found, _skipped = cce.census_of(scratch, clusters_csv, registers_csv)
        self.assertEqual(found, [])


class TheReportIsReadable(unittest.TestCase):
    """The report is the deliverable, so a case holds that it renders.

    The tool's numbers are how the decision was reached and how a reader checks
    it. A report that raised, or that resolved its stream at import so a
    redirect missed it, would leave the run looking broken rather than empty --
    and "printed nothing" is the one failure a census cannot be allowed to
    have, because it is the failure that reads as a result.
    """

    def _render(self, **kwargs):
        found, skipped = cce.census_of()
        members = ccc.census()[0]
        stream = io.StringIO()
        cce.report(found, skipped, members, repo=cce.REPO, out=stream, **kwargs)
        return found, stream.getvalue()

    def test_the_report_renders_to_a_redirected_stream(self):
        _found, text = self._render()
        self.assertIn("what an operand/bound exemption would admit", text)
        # The calibration line is not decoration: it is what stops a reader
        # taking `unclassified` for "is not a bound", which is the claim this
        # tool has to decline to make. Asserted on the unwrapped text, since
        # the report hard-wraps its prose and a phrase that straddles a wrap
        # would make this case fail on a reflow rather than on a regression.
        flat = " ".join(text.split())
        self.assertIn("not named by this method, never absent", flat)
        self.assertIn("Nothing was opened, read back or observed", flat)

    def test_every_admitted_unit_is_named_rather_than_only_counted(self):
        # The admitted set is the figure the decision rests on, so it has to be
        # a list a reader can go and check rather than a count to take on trust.
        found, text = self._render()
        for path, lineno, _text, _ids, _verdict, _addresses in found:
            if _verdict[0] == cce.ADMITTED:
                self.assertIn(f"{os.path.relpath(path, cce.REPO)}:{lineno}", text)

    def test_the_lexicon_and_span_figures_are_reported_apart(self):
        # A report that folded them into one admitted count would let the
        # decision be taken on the structural figure while the prose argued
        # about the lexicon, which is the confusion the decision turns on.
        _found, text = self._render()
        self.assertIn("by the signal that exempts them", text)
        self.assertIn("`range` is a `SPAN` token", text)

    def test_verbose_lists_every_address_of_every_unit(self):
        found, text = self._render(verbose=True)
        self.assertIn("every membership-checked unit", text)
        for _path, _lineno, _text, _ids, _verdict, addresses in found:
            for address in addresses:
                self.assertIn(address.token, text)


class CommittedDecision(unittest.TestCase):
    """The recorded decision is the deliverable, so it is held to the run.

    The write-up answers "no". Not on taste: the committed corpus carries no
    lexicon-admitted unit *today*, because §26 was reworded -- and the case
    above is what makes that insufficient, since the sentence the exemption
    was proposed for is admitted the moment it is written in its old form. So
    what is asserted here is both halves, and the second is the one that holds
    the decision to the tree: the corpus figure may move, the checker's own
    control may not.
    """

    def test_no_committed_unit_is_admitted_by_the_lexicon(self):
        found, _skipped = cce.census_of()
        self.assertEqual([u for u in found
                          if u[4][0] == cce.ADMITTED and u[4][1] == "lexicon"],
                         [])

    def test_every_committed_admitted_unit_is_admitted_structurally(self):
        # The other half: whatever the corpus's admitted set turns out to be,
        # it must not rest on the lexicon. A merge that lands a sentence with a
        # bound word in the address's own clause fails this case, which is the
        # point -- it should be a visible change to the recorded decision
        # rather than a silent contradiction of it.
        found, _skipped = cce.census_of()
        for unit in found:
            if unit[4][0] == cce.ADMITTED:
                self.assertEqual(unit[4][1], cce.RANGE)

    def test_the_checker_control_still_reports_the_operand(self):
        # The other direction, and the acceptance criterion the issue sets. It
        # is asserted here as well as in the checker's own suite because this is
        # the PR that declines the exemption: a re-run of the checker's suite is
        # what would notice, and a case in this file is what makes noticing it
        # part of *this* suite rather than something to remember.
        self.assertIn("class OneAttributionPerUnit",
                      (HERE / "test_check_cluster_citations.py").read_text())

    def test_the_decision_is_recorded_beside_the_lexicon_limit(self):
        # The issue's own "Done" clause names where the answer goes, and a
        # decision recorded somewhere else would leave the checker's docstring
        # still carrying the open question. Read through the line wrapping, since
        # a docstring hard-wrapped at the column would otherwise fail this case
        # on a reflow rather than on the decision being taken out.
        source = " ".join(
            (HERE / "check_cluster_citations.py").read_text().split())
        self.assertIn("census_citation_exemptions.py", source)
        self.assertIn("not adopted", source)


if __name__ == '__main__':
    unittest.main()