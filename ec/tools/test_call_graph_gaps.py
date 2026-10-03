#!/usr/bin/env python3
"""Offline checks for call_graph_gaps.py: committed files only.

`call_graph_gaps.py` writes two committed CSVs that carry the per-target
`cause` and per-row `entry` the call-graph census used to reduce to an integer
each, and `--check` recomputes both. A classifier that quietly stops
classifying does not crash and does not raise: it keeps writing a file, the
file keeps its shape, and the only thing that notices is a reader who has
already been misled by a `no-index-row` they read as "no function here". So
what is pinned below is the line between what the tool places and what it
leaves open.

Four properties, in the order a reader meets them.

**The two artifacts describe `call_graph.scan()`'s two populations.** The tool
does its own walk rather than reading `scan()`'s `Counter`, because it needs
the per-site detail the Counter does not carry -- which makes "the same
population" a claim rather than a tautology, and it is checked in one process
against `scan()` itself. A tool that re-derived a near-neighbour of the census
would satisfy every other case here and still be wrong about the thing it is
for.

**The four causes are a partition, decided in the documented precedence.** Each
target carries exactly one, the four sets are disjoint, and the winning value
is the head of `all_causes()` rather than a restatement of the same `if` chain.
The overlap count matters on its own: a precedence that quietly decides targets
is a rule no reader can see, so it is printed and asserted rather than assumed
away.

**The weak negatives stay weak.** `no-index-row` and `not-adjacent` mean this
method placed the row nowhere. Nothing here may let them be read as claims about
the firmware, so the artifact's own header comment is asserted to carry that
caveat, and the worked addresses are the ones where reading them the strong way
would be wrong -- a neighbour that ends in a `ret` or an `ljmp` is adjacent but
is not entered by falling into it.

**What the report prints is what the tool computed.** Every figure is read back
out of the rendered lines rather than recomputed beside them, and the
distinct-caller figure is held to the union of `(scope, listing)` pairs over
the site map rather than to the sum of a per-target `callers` column. A number
labelled *distinct* that was computed as a sum is the same mistake one level
down as reporting a per-target cause as a per-population one, and it prints
plausibly either way.

**`--check` still rejects a table that drifted.** Asserted with a table one
cell different, one with a row dropped, and one with CRLF endings, because a
check that has quietly started accepting everything looks exactly like a check
that is working.

Nothing here reads a capture, an EC, or a laptop. Every input is a committed
listing, `index.csv` or `registers.yaml` under this repository.
"""
import collections
import contextlib
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import build_ec_decompile
import call_graph
import call_graph_gaps

FIXTURE = HERE / "testdata" / "call-graph-gaps"


def predecessor_last_mnemonic(row):
    """The mnemonic of the predecessor listing's last instruction, read back off
    the committed `.asm` rather than taken from the classifier's own label.

    Asserting a class against the set the tool used to build it would only
    check that the tool agrees with itself. Reading the listing is what turns
    "`fall-through` really falls through" into a claim about bytes, and it is
    the only thing that catches a predicate narrowed back to something too
    small -- a `ret`-only rule satisfies every `ret`-terminated row and
    mislabels every `ljmp`-terminated one.
    """
    path = os.path.join(call_graph.DECOMPILED, row["pred_scope"],
                        row["pred_addr"] + ".asm")
    last = None
    for parts in call_graph.citation_callers.iter_instructions(path):
        last = parts
    if last is None:
        return None
    return last[4]


def load_committed():
    """`(index, xdata, edges, unresolved_counter, sites, rows, unreached)` for
    the committed tree.

    One walk of the real listings for every case below, because `scan()` over
    `ec/decompiled/` is the expensive half and a suite that pays it per test is
    a suite nobody runs. The values are read-only, so sharing them across cases
    cannot let one case's mutation leak into another's.
    """
    index = call_graph.load_index()
    edges, unresolved, _orphans, _total, _listings = call_graph.scan(index)
    xdata = build_ec_decompile.registered_addresses()
    sites = call_graph_gaps.unresolved_sites(index)
    rows = call_graph_gaps.unresolved_rows(index, sites, xdata)
    unreached = call_graph_gaps.unreached_rows(index, edges)
    return index, xdata, edges, unresolved, sites, rows, unreached


class CommittedPopulationTests(unittest.TestCase):
    """The two artifacts against `call_graph.scan()`, in one process."""

    @classmethod
    def setUpClass(cls):
        (cls.index, cls.xdata, cls.edges, cls.unresolved, cls.sites,
         cls.rows, cls.unreached) = load_committed()

    def test_discovery_reached_something(self):
        # The vacuous-check guard the runner also has: a comparison against an
        # empty population would pass every other case in this class.
        self.assertTrue(self.rows, "no unresolved targets classified")
        self.assertTrue(self.unreached, "no unreached rows classified")

    def test_the_unresolved_targets_are_scan_s_own(self):
        """Same keys, same per-key site counts.

        The equality is the claim the whole tool rests on. It is checked both
        ways because a tool that classified a *superset* and a tool that
        classified a *subset* each fail one direction only, and each would still
        print a plausible table.
        """
        self.assertEqual(set(self.sites), set(self.unresolved))
        for addr, count in self.unresolved.items():
            self.assertEqual(len(self.sites[addr]), count,
                             "site count for %s" % addr)

    def test_the_unresolved_site_total_is_scan_s_own(self):
        self.assertEqual(sum(int(r["sites"]) for r in self.rows),
                         sum(self.unresolved.values()))

    def test_the_unreached_population_is_the_one_report_prints(self):
        """Exactly the anonymous rows `report()`'s `unreached` counts.

        `report()` computes it as `len(anon_rows)` less the anonymous rows
        carrying an inbound edge, which is *not* the same as "anonymous rows the
        table carries no row for" -- a cited row the scan cannot reach is in
        that table now and is still a row no transfer reaches. Recomputing
        `report()`'s expression here rather than asserting a figure is what
        makes this a property of the tree rather than a number that goes stale.
        """
        anon = [r for r in self.index.rows if r["name"].startswith("FUN_")]
        reached = [r for r in anon if (r["program"], r["_addr"]) in self.edges]
        self.assertEqual(len(self.unreached), len(anon) - len(reached))
        self.assertEqual(
            {(r["scope"], r["addr"]) for r in self.unreached},
            {(r["program"], r["_addr"]) for r in anon} - set(self.edges))

    def test_no_row_the_artifact_calls_unreached_is_one_a_transfer_reaches(self):
        keys = {(r["scope"], r["addr"]) for r in self.unreached}
        self.assertFalse(keys & set(self.edges))


class CauseVocabularyTests(CommittedPopulationTests):
    """The closed vocabulary, the partition, and the precedence."""

    def test_every_cause_is_in_the_vocabulary(self):
        outside = {r["cause"] for r in self.rows} - set(call_graph_gaps.CAUSES)
        self.assertFalse(outside, "causes outside the vocabulary: %s"
                         % sorted(outside))

    def test_the_causes_partition_the_population(self):
        """One cause per row, and the four sets disjoint.

        Not a count. A cause that overlaps another would double-count the
        populations the artifact reports side by side, and the overlap is what
        the precedence exists to settle.
        """
        counts = collections.Counter(r["cause"] for r in self.rows)
        self.assertEqual(sum(counts.values()), len(self.rows))
        by_cause = collections.defaultdict(set)
        for r in self.rows:
            self.assertNotIn(
                r["target"], by_cause[r["cause"]],
                "%s carries more than one cause" % r["target"])
            by_cause[r["cause"]].add(r["target"])

    def test_the_winning_cause_is_the_head_of_all_causes(self):
        """The artifact's value is `all_causes()`'s first, not a restatement.

        `classify()` and `all_causes()` are two functions over one set of
        predicates, which is the only reason a disagreement between them is a
        bug rather than a copy. This is what catches the copy drifting.
        """
        spans = call_graph_gaps.spans(self.index)
        for r in self.rows:
            addr = r["target"]
            fired = call_graph_gaps.all_causes(
                addr, {s[0] for s in self.sites[addr]},
                list(self.index.by_addr.get(addr, ())),
                call_graph_gaps.hosts(addr, spans), self.xdata)
            self.assertEqual(r["cause"], fired[0],
                             "cause for %s is not all_causes()'s head" % addr)

    def test_multi_scope_is_resolve_s_own_decline(self):
        """The `multi-scope` set is exactly where `resolve()` declines on scope.

        Computed from the rule rather than transcribed, so an annotation tranche
        that adds or removes a second-scope row moves the set and the assertion
        follows it.
        """
        expected = set()
        for addr in self.sites:
            rows = list(self.index.by_addr.get(addr, ()))
            scopes = {s[0] for s in self.sites[addr]}
            if (len(rows) >= 2
                    and not ({r["program"] for r in rows} & scopes)):
                expected.add(addr)
        got = {r["target"] for r in self.rows if r["cause"] == "multi-scope"}
        self.assertEqual(got, expected)

    def test_interior_entry_targets_have_no_index_row_of_their_own(self):
        """Rule 3's own precondition, read off the index rather than the tool.

        An `interior-entry` row that also had an index row would mean the
        resolver declined it for a different reason than the one reported, and
        that is the difference between "a branch into a routine that exists" and
        "a function we could not place".
        """
        for r in self.rows:
            if r["cause"] == "interior-entry":
                self.assertNotIn(r["target"], self.index.by_addr,
                                 "%s has an index row" % r["target"])
                self.assertTrue(r["host_addr"],
                                "%s names no host row" % r["target"])

    def test_xdata_or_data_targets_are_in_registers_yaml(self):
        for r in self.rows:
            if r["cause"] == "xdata-or-data":
                self.assertIn(int(r["target"], 16), self.xdata)

    def test_a_host_is_never_invented_for_a_row_the_index_placed_nowhere(self):
        """`no-index-row` carries no host, and its address is in no span.

        The weak negative is only honest while it stays empty. A host on such a
        row would be the classifier quietly promoting "I placed this nowhere"
        into "and here is what it is", which is the claim it must not make.
        """
        spans = call_graph_gaps.spans(self.index)
        for r in self.rows:
            if r["cause"] == "no-index-row":
                self.assertFalse(r["host_addr"],
                                 "%s has a host" % r["target"])
                self.assertFalse(
                    call_graph_gaps.hosts(r["target"], spans),
                    "%s is inside a span" % r["target"])

    def test_the_precedence_is_visible_in_what_the_tool_prints(self):
        """The overlap count is printed, so a precedence that decides is seen.

        Computed here rather than read off the report so the assertion is about
        the tool's rule; `ReportPrintingTests` holds the report to printing the
        same figure.
        """
        spans = call_graph_gaps.spans(self.index)
        overlap = sum(
            1 for addr in self.sites
            if len(call_graph_gaps.all_causes(
                addr, {s[0] for s in self.sites[addr]},
                list(self.index.by_addr.get(addr, ())),
                call_graph_gaps.hosts(addr, spans), self.xdata)) > 1)
        self.assertGreater(overlap, 0,
                           "the fixture tree is expected to exercise the "
                           "overlap; on the committed tree a zero would mean "
                           "the precedence is untested")


class CalibrationTests(CommittedPopulationTests):
    """The weak negatives, in the artifact and in the tool's own report."""

    def test_the_committed_tables_carry_the_caveat_in_their_own_header(self):
        """The header comment a reader sees says what the value does not mean.

        The tool's docstring is what a maintainer reads; this file is what
        someone opening the CSV in an editor reads. Neither is a substitute for
        the other, and the header is the one that travels with the data.
        """
        for path, weak in ((call_graph_gaps.UNRESOLVED, "no-index-row"),
                           (call_graph_gaps.UNREACHED, "not-adjacent")):
            head = Path(path).read_text(encoding="utf-8").splitlines()
            self.assertTrue(head[0].startswith("#"), "%s has no header" % path)
            block = "\n".join(head[:len(call_graph_gaps.HEADER_NOTE)])
            self.assertIn("WEAK NEGATIVE", block)
            self.assertIn("`%s`" % weak, block)
            self.assertIn("not a claim about the firmware", block)

    def test_a_boundary_neighbour_is_not_reported_as_a_fall_through(self):
        """The `adjacent-no-fallthrough` class exists, and is not
        `fall-through`.

        A row one past a `ret` is adjacent by arithmetic and not entered by it;
        a row one past an `ljmp` is *jumped over*, which is the same conclusion
        for the opposite reason and the larger half of the class. Reporting
        either as a fall-through would credit an entry the bytes do not make --
        the exact overclaim `CLAUDE.md` puts above every other rule. The class
        is asserted to be non-empty so a tool that dropped it would fail here
        rather than quietly merging it into `fall-through`.
        """
        adjacent = [r for r in self.unreached
                    if r["entry"] == "adjacent-no-fallthrough"]
        self.assertTrue(adjacent,
                        "no adjacent-no-fallthrough rows; the class is gone")
        for r in adjacent:
            self.assertTrue(r["pred_addr"], "%s has no predecessor" % r["addr"])
            self.assertIn(predecessor_last_mnemonic(r),
                          call_graph_gaps.NO_FALLTHROUGH,
                          "%s's predecessor is not one NO_FALLTHROUGH covers"
                          % r["addr"])

    def test_the_no_fall_through_class_is_wider_than_the_returns(self):
        """The set is asked of more than the returns, and that is asserted.

        `ret`/`reti` are the obvious boundary set and they are not the right
        one: an `ljmp` is three bytes of unconditional jump, so the row one
        past it is jumped over. A predicate narrowed back to the returns
        satisfies every `ret`-terminated row and mislabels every
        `ljmp`-terminated one, which is why a non-returning boundary has to be
        in the population this case looks for rather than only in the rule.
        """
        adjacent = [r for r in self.unreached
                    if r["entry"] == "adjacent-no-fallthrough"]
        non_return = [r for r in adjacent
                      if predecessor_last_mnemonic(r) not in ("ret", "reti")]
        self.assertTrue(
            non_return,
            "every adjacent-no-fallthrough row is preceded by a return, so "
            "the class cannot distinguish a return from an unconditional "
            "transfer and the rule is a returns-only one wearing a wider name")
        self.assertLess(
            {"ret", "reti"}, set(call_graph_gaps.NO_FALLTHROUGH),
            "NO_FALLTHROUGH no longer carries the returns it was widened from")

    def test_a_fall_through_row_is_preceded_by_an_instruction_control_passes(self):
        """The other side of the same split, so the two classes cannot merge.

        Asserted over every row rather than a sample, because the class is the
        one an overclaim lives in and a sample is only as good as the rows it
        happens to reach.
        """
        rows = [r for r in self.unreached if r["entry"] == "fall-through"]
        self.assertTrue(rows, "no fall-through rows")
        for r in rows:
            self.assertNotIn(predecessor_last_mnemonic(r),
                             call_graph_gaps.NO_FALLTHROUGH,
                             "%s is preceded by %s, which control does not "
                             "continue past"
                             % (r["addr"], r["pred_addr"]))

    def test_not_adjacent_rows_carry_no_predecessor(self):
        """The empty `pred_*` cells are asserted, not merely left empty.

        A row this method placed nowhere must not acquire a predecessor by
        accident -- that would be the tool guessing a caller, which is the one
        thing the classification is not allowed to do.
        """
        for r in self.unreached:
            if r["entry"] == "not-adjacent":
                self.assertFalse(r["pred_addr"], "%s names a predecessor"
                                 % r["addr"])
                self.assertFalse(r["pred_name"])
                self.assertFalse(r["pred_named"])

    def test_the_forms_column_records_the_paged_signal_without_widening_the_vocabulary(self):
        """`ajmp`/`acall` reach a target; they are not a fifth cause.

        The paged forms put the page in the opcode and only the low byte in the
        operand, so three addresses can be three entry points into one body.
        That is a property of how a target is reached, recorded in `forms`,
        while `cause` stays at four values.
        """
        paged = {"ajmp", "acall"}
        for r in self.rows:
            forms = set(r["forms"].split())
            if forms and forms <= paged:
                self.assertNotEqual(r["cause"], "paged")
        self.assertTrue(
            any(set(r["forms"].split()) <= paged for r in self.rows),
            "no paged-only target on the committed tree")

    def test_every_listing_cell_names_a_listing_that_exists(self):
        """`listings` reads back to a listing that is on disk.

        A `scope/stem@site` cell is only useful if the stem is a real listing.
        This walks it rather than checking the shape, because a stem that names
        nothing is exactly the drift a reader would hit when following the row.
        """
        for r in self.rows:
            for token in r["listings"].split():
                scope, rest = token.split("/")
                stem, _at_site = rest.split("@")
                self.assertTrue(
                    os.path.exists(os.path.join(call_graph.DECOMPILED, scope,
                                                stem + ".asm")),
                    "%s names no listing" % token)


class CheckRejectsDriftTests(unittest.TestCase):
    """`--check`'s pass condition, driven against the shipped functions.

    A check that has quietly started accepting everything looks exactly like a
    check that is working, and the failure is silent: the tool keeps writing a
    table and the table keeps its shape. So each rejection is asserted with the
    same function `--check` runs, not a re-implementation of it -- asserting
    against a re-implementation would prove the re-implementation works.
    """

    def setUp(self):
        index = call_graph.load_index()
        self.rows = call_graph_gaps.unresolved_rows(
            index, call_graph_gaps.unresolved_sites(index),
            build_ec_decompile.registered_addresses())
        self.rendered = call_graph_gaps.render(
            self.rows, call_graph_gaps.UNRESOLVED_COLUMNS,
            call_graph_gaps.HEADER_NOTE)

    def test_a_table_against_itself_passes(self):
        self.assertEqual(
            call_graph_gaps.check_table(self.rendered, self.rendered,
                                        call_graph_gaps.UNRESOLVED_COLUMNS),
            (0, []))

    def test_one_altered_cell_is_rejected_naming_that_row_and_column(self):
        rows = [dict(r) for r in self.rows]
        rows[0]["cause"] = "edited-by-the-suite"
        lines = call_graph_gaps.diff_table(
            call_graph_gaps.render(rows, call_graph_gaps.UNRESOLVED_COLUMNS,
                                   call_graph_gaps.HEADER_NOTE),
            self.rendered, call_graph_gaps.UNRESOLVED_COLUMNS)
        self.assertTrue(
            any(line == "  %s:" % self.rows[0]["target"] for line in lines),
            "the diff named no row: %r" % lines)
        self.assertTrue(
            any("cause" in line and "recomputed" in line for line in lines),
            "the diff named no column: %r" % lines)

    def test_a_dropped_last_row_is_rejected_on_the_row_count(self):
        """A drift no cell-by-cell comparison can see."""
        dropped = call_graph_gaps.render(
            self.rows[:-1], call_graph_gaps.UNRESOLVED_COLUMNS,
            call_graph_gaps.HEADER_NOTE)
        self.assertEqual(
            call_graph_gaps.diff_table(dropped, self.rendered,
                                       call_graph_gaps.UNRESOLVED_COLUMNS),
            ["  row count: committed %d, recomputed %d"
             % (len(self.rows) - 1, len(self.rows))])

    def test_crlf_line_endings_are_rejected_on_their_bytes(self):
        """Every row parses equal and the bytes do not match.

        `.gitattributes` marks the decompiled `.c` trees `-text` for this hazard
        and does not cover `ec/annotations/*.csv`, so the case is reachable
        rather than hypothetical. Gating the verdict on parsed rows would call
        this table clean with the check green, which is the quiet drift the
        check exists to close.
        """
        crlf = self.rendered.replace("\n", "\r\n")
        rc, lines = call_graph_gaps.check_table(
            crlf, self.rendered, call_graph_gaps.UNRESOLVED_COLUMNS)
        self.assertEqual(rc, 1)
        self.assertTrue(lines, "a byte-only difference reported no lines")
        self.assertEqual(
            call_graph_gaps.diff_table(crlf, self.rendered,
                                       call_graph_gaps.UNRESOLVED_COLUMNS), [],
            "the row diff alone cannot see this case, which is why the pass "
            "condition is the byte comparison")

    def test_the_committed_table_matches_a_recomputation(self):
        """The reproducibility claim, byte for byte.

        The whole value of committing these two CSVs is that they cannot drift
        from the listings they were derived from, and this is the assertion that
        says so. It is the same comparison `--check` runs, in process.
        """
        for path, columns in ((call_graph_gaps.UNRESOLVED,
                               call_graph_gaps.UNRESOLVED_COLUMNS),
                              (call_graph_gaps.UNREACHED,
                               call_graph_gaps.UNREACHED_COLUMNS)):
            have = Path(path).read_text(encoding="utf-8")
            index = call_graph.load_index()
            edges, _unresolved, _orphans, _total, _listings = call_graph.scan(
                index)
            if columns is call_graph_gaps.UNRESOLVED_COLUMNS:
                rows = call_graph_gaps.unresolved_rows(
                    index, call_graph_gaps.unresolved_sites(index),
                    build_ec_decompile.registered_addresses())
            else:
                rows = call_graph_gaps.unreached_rows(index, edges)
            want = call_graph_gaps.render(rows, columns,
                                          call_graph_gaps.HEADER_NOTE)
            rc, lines = call_graph_gaps.check_table(have, want, columns)
            self.assertEqual(rc, 0, "%s differs:\n%s"
                             % (os.path.basename(path), "\n".join(lines)))


class SelfTestAndFixtureTests(unittest.TestCase):
    """The shipped `--self-test`, and the fixture it runs on."""

    def test_the_shipped_self_test_passes(self):
        """`--self-test` as a subprocess, so what CI runs is what is asserted.

        Driven as a process rather than by calling `self_test()` because the
        arm that matters is the one that returns an exit code, and calling the
        function would not exercise the argument handling that reaches it.
        """
        proc = subprocess.run(
            [sys.executable, str(HERE / "call_graph_gaps.py"), "--self-test"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("all assertions passed", proc.stdout)

    def test_the_fixture_indexes_itself(self):
        """The fixture directory carries its own README, which is what
        `check_testdata_index.py` reads rather than the shared index.

        Structural rather than an exemption list: the next self-indexed
        directory needs no edit to that tool either.
        """
        self.assertTrue((FIXTURE / "README.md").exists())
        for name in ("index.csv", "registers.yaml"):
            self.assertTrue((FIXTURE / name).exists(), name)

    def test_the_fixture_exercises_every_cause_and_every_entry(self):
        """Coverage of the vocabularies, on the fixture's own classification.

        A fixture that stopped exercising a value would let a rule that no
        longer fires pass its own test, which is the failure the fixture is
        there to prevent.
        """
        index = call_graph.load_index(str(FIXTURE / "index.csv"))
        xdata = build_ec_decompile.registered_addresses(
            str(FIXTURE / "registers.yaml"))
        decompiled = str(FIXTURE / "decompiled")
        edges, _unresolved, _orphans, _total, _listings = call_graph.scan(
            index, decompiled)
        rows = call_graph_gaps.unresolved_rows(
            index, call_graph_gaps.unresolved_sites(index, decompiled), xdata)
        unreached = call_graph_gaps.unreached_rows(index, edges, decompiled)
        self.assertEqual({r["cause"] for r in rows},
                         set(call_graph_gaps.CAUSES))
        self.assertEqual({r["entry"] for r in unreached},
                         set(call_graph_gaps.ENTRIES))

    def test_the_fixture_and_the_committed_tree_agree_on_what_scan_counts(self):
        """`scan()` is the same function on both, and the tool's walk agrees.

        The cross-tool check the fixture also carries, run against the committed
        tree: if `unresolved_sites()` ever stopped agreeing with `scan()`'s own
        `Counter`, this is where it would show.
        """
        index = call_graph.load_index()
        _edges, unresolved, _orphans, _total, _listings = call_graph.scan(index)
        sites = call_graph_gaps.unresolved_sites(index)
        self.assertEqual(set(sites), set(unresolved))
        self.assertEqual(sum(len(v) for v in sites.values()),
                         sum(unresolved.values()))


class ReportPrintingTests(unittest.TestCase):
    """What the report prints, read back out of its lines.

    Read from the rendered output rather than recomputed, so the assertion is
    about what a reader is shown and not about this file agreeing with itself.
    A label whose wording moved reads as `None` and fails the case that wanted
    it, rather than raising out of the middle of a passing run.
    """

    @classmethod
    def setUpClass(cls):
        # Rendered once for the class: `figure()` is a lookup in these lines,
        # and re-walking `ec/decompiled/` per lookup would make the two cases
        # that call it the slowest in the suite for no extra coverage.
        cls.index = index = call_graph.load_index()
        edges, _unresolved, _orphans, _total, _listings = call_graph.scan(index)
        cls.xdata = xdata = build_ec_decompile.registered_addresses()
        cls.sites = sites = call_graph_gaps.unresolved_sites(index)
        rows = call_graph_gaps.unresolved_rows(index, sites, xdata)
        cls.rows = rows
        unreached = call_graph_gaps.unreached_rows(index, edges)
        spans = call_graph_gaps.spans(index)
        overlap = sum(
            1 for addr in sites
            if len(call_graph_gaps.all_causes(
                addr, {s[0] for s in sites[addr]},
                list(index.by_addr.get(addr, ())),
                call_graph_gaps.hosts(addr, spans), xdata)) > 1)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            call_graph_gaps.report(sites, rows, unreached, overlap, xdata)
        cls.lines = buf.getvalue().splitlines()

    def figure(self, label):
        for line in self.lines:
            body = line.strip()
            if body.startswith(label):
                tail = body[len(label):].split()
                return int(tail[-1]) if tail and tail[-1].isdigit() else None
        self.fail("no line starting %r in:\n%s"
                  % (label, "\n".join(self.lines)))

    def test_the_two_headline_figures_are_what_the_census_prints(self):
        """`call_graph.py` and this tool report the same two populations.

        Run in one process against the same index, so a drift between the
        census and the artifact shows as a failing number rather than as prose
        that has quietly gone out of date. Both figures are asserted against
        `scan()`'s own return values, not against each other.
        """
        index = call_graph.load_index()
        _edges, unresolved, _orphans, _total, _listings = call_graph.scan(index)
        self.assertEqual(self.figure("unresolved transfer targets"),
                         len(unresolved))
        self.assertEqual(self.figure("sites reaching them"),
                         sum(unresolved.values()))

    def test_the_entry_split_sums_to_the_unreached_total(self):
        self.assertEqual(
            self.figure("fall-through")
            + self.figure("adjacent-no-fallthrough")
            + self.figure("not-adjacent"),
            self.figure("anonymous rows no transfer reaches"))

    def test_the_distinct_caller_figure_is_the_union_not_a_sum(self):
        """The number labelled *distinct* is the union over the site map.

        The `callers` column counts distinct callers **per target**, so a
        listing that reaches two unresolved targets appears in two rows and a
        sum over the column counts it twice. The union is computed here from the
        same `sites` map `report()` was handed, so a report that summed the
        column under this label fails instead of printing a plausible figure.
        """
        union = call_graph_gaps.distinct_listings(self.sites)
        self.assertEqual(self.figure("distinct caller listings reaching them"),
                         union)
        # And the two readings really are different, so this case cannot pass
        # on a tree where they coincide by accident.
        summed = sum(int(r["callers"]) for r in self.rows)
        self.assertNotEqual(union, summed,
                            "the union and the per-target sum are equal here, "
                            "so this case would not catch a report that sums")

    def test_the_report_states_the_weak_negative_in_words(self):
        """The caveat is printed, not only in the docstring.

        A report read once in a terminal is where a weak negative gets promoted
        into a finding, and the terminal is not carrying the docstring.
        """
        text = "\n".join(self.lines)
        self.assertIn("not found by this method", text)
        self.assertIn("placed the target nowhere", text)


if __name__ == "__main__":
    unittest.main()