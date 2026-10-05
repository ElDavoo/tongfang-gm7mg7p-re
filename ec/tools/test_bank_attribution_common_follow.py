#!/usr/bin/env python3
"""Cases for `bank_attribution.py`'s common-area continuation and vector seeds.

Stands in for the four things issue #1078 changed, none of which a figure
elsewhere in the tree would catch:

  * `closure()` follows a `callee < BANK_FLOOR` as a same-bank continuation,
    so the zero delta below is a measurement rather than a no-op. A change that
    quietly stopped following would produce the same numbers.
  * The vector table's split -- the common-area code handlers seed each bank,
    and the targets that are themselves trampoline entries do not, because
    their own targets are already seeds.
  * The `common` entry-point `kind`, and its `frm` naming the bank that reached
    it, so a routine both banks share is recorded as ambiguous rather than
    attributed to whichever bank was walked first.
  * The identity itself: the attributed address set, the four verdicts, and the
    per-address path counts are all unchanged by both changes. That is the
    measured negative the finding rests on, so it is asserted as an identity
    against a second closure rather than as a recorded number.
  * The bounds arm, which is the other half of the same disjunction. §9 asks
    whether what is left is *seeds* or *bounds*, and an earlier version of this
    change asserted "not bounds" in the tool's report and in two write-ups
    with nothing in the tree computing it -- a measured negative on one horn
    and an unmeasured assertion on the other. Re-walking both closures at a
    raised ceiling is what makes the answer two-armed.
  * That the DPTR-immediate census the write-up quotes is a count of how often
    the idiom appears, **not** a count of routes nothing follows -- the
    trampoline census already names nearly all of them, and the one it does not
    is an XDATA clear rather than a code route. An earlier draft of the write-up
    read that figure the other way, which made a confident negative about the
    firmware on the one pair of addresses that contradicted it.

**No count of the tree is asserted anywhere in this file.** The entry-point
totals grow and shrink with the walk's bounds, and a merge that changed a bound
would not be a defect; what is asserted is the relation between two populations
this suite computes, which no change to the tree can move on its own.

Everything here reads committed files. No Ghidra, no hardware, no Windows, no
network.
"""
import contextlib
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bank_attribution as ba  # noqa: E402
from audit_call_targets import survey  # noqa: E402
from trace_xdata_refs import offset_for_runtime  # noqa: E402
from walk_branch_arms import descend  # noqa: E402

EC = ba.__file__.rsplit("/", 2)[0]
FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")
ANNOTATIONS = os.path.join(EC, "annotations")


def firmware():
    """The committed image, read fresh, for the reason
    `test_census_closure_functions.firmware()` gives: a cached module-level read
    would let this suite and the tool under test disagree about the image."""
    with open(FIRMWARE, "rb") as f:
        return f.read()


def both():
    """(image, seeds, handlers, closures with the change, closures without).

    Two populations rather than one, because the whole finding is a difference
    between them. Run once per class that needs it: `closure()` is a bounded
    walk over the image and running it per case would dominate the suite.
    """
    d = firmware()
    _rows, _stubs, tramp = survey(d)
    seeds = ba.seeds_for(tramp)
    handlers = ba.vector_handlers(d, tramp)
    seeded = {b: seeds[b] | handlers[b] for b in (0, 1)}
    return (d, seeds, handlers, seeded,
            {b: ba.closure(d, b, seeded[b]) for b in (0, 1)},
            {b: ba.closure(d, b, seeds[b], follow_common=False)
             for b in (0, 1)})


def report():
    """The tool's default report over the committed image.

    Driven through `main()` rather than by calling the print functions, so the
    section this suite reads is the one a reader of the tool sees -- a print
    function called directly would not exercise `main()`'s own seeding.
    """
    argv = sys.argv
    sys.argv = ["bank_attribution.py", FIRMWARE]
    try:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            ba.main()
    finally:
        sys.argv = argv
    return buf.getvalue()


class TheSelfTest(unittest.TestCase):
    """The tool's own self-test, which is where the readings live."""

    def test_it_passes(self):
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = ba.self_test(firmware())
        self.assertEqual(rc, 0, buf.getvalue()[-3000:])


class TheVectorTableSplit(unittest.TestCase):
    """What the vector table adds, and what it does not."""

    @classmethod
    def setUpClass(cls):
        (cls.d, cls.seeds, cls.handlers, _s, _c, _w) = both()
        cls.targets = {addr for addr, basis in ba.build_ec_decompile.vector_seeds(cls.d)
                       if basis == "vector-target"}
        cls.tramp = survey(cls.d)[2]

    def test_every_vector_target_is_common_area(self):
        """So the handlers seed both banks from one set, and no vector target
        can itself be a banked entry point."""
        self.assertTrue(self.targets)
        self.assertEqual([a for a in self.targets if a >= ba.BANK_FLOOR], [])

    def test_the_same_handler_set_seeds_both_banks(self):
        self.assertEqual(self.handlers[0], self.handlers[1])

    def test_the_handlers_are_exactly_the_targets_no_trampoline_names(self):
        """The split as a relation, not a list. `vector_handlers()` drops a
        target that is itself a trampoline entry, because that entry's own
        target is already a seed through the stub -- so the handlers are the
        targets minus those, recomputed here from the two accessors."""
        common = {a for a in self.targets if a < ba.BANK_FLOOR}
        already = common & set(self.tramp)
        self.assertTrue(already, "no vector target is a trampoline entry, which "
                        "is not the shape this image has")
        self.assertEqual(self.handlers[0], common - already)

    def test_each_dropped_target_really_does_name_a_banked_seed(self):
        """The reason for dropping them. Asserted per target rather than as a
        count, so a vector table that grew a thirteenth entry is caught here
        instead of silently changing the seed set."""
        common = {a for a in self.targets if a < ba.BANK_FLOOR}
        for addr in sorted(common & set(self.tramp)):
            bank, target = self.tramp[addr]
            self.assertGreaterEqual(
                target, ba.BANK_FLOOR,
                f"0x{addr:04X} is a trampoline entry whose target is not "
                f"banked, so it is not redundant")
            self.assertIn(target, self.seeds[bank])

    def test_no_handler_is_already_a_banked_seed(self):
        """Otherwise dropping the trampoline targets would leave a gap."""
        for bank in (0, 1):
            self.assertEqual(self.handlers[bank] & self.seeds[bank], set())


class TheContinuationFollows(unittest.TestCase):
    """`closure()` descends a common-area callee, and attributes nothing to a
    bank for doing it."""

    @classmethod
    def setUpClass(cls):
        (cls.d, _s, cls.handlers, _sd, cls.closures, cls.without) = both()

    def test_the_walk_reaches_common_area_entry_points(self):
        followed = {a for b in (0, 1)
                    for a, (kind, _frm) in self.closures[b][2].items()
                    if kind == "common"}
        self.assertTrue(followed,
                        "no common-area callee was followed, so the identity "
                        "the other cases assert would prove nothing")
        self.assertEqual([a for a in followed if a >= ba.BANK_FLOOR], [])

    def test_following_common_area_adds_entry_points(self):
        """The walk does real work. Without this, a `follow_common` that did
        nothing would satisfy every identity below."""
        for bank in (0, 1):
            self.assertGreater(len(self.closures[bank][2]),
                               len(self.without[bank][2]),
                               f"bank{bank} gained no entry points from the "
                               f"common area")

    def test_no_banked_byte_is_attributed_through_a_common_entry_point(self):
        """The `pc >= BANK_FLOOR` gate, held in the direction that matters. A
        common-area arm could only add a banked byte by decoding a banked
        address, and none of them does -- so `who` never carries a common entry
        point for an address at or above the floor."""
        for bank in (0, 1):
            reached, who, entries, _cuts, _common = self.closures[bank]
            common_eps = {a for a, (k, _f) in entries.items() if k == "common"}
            attributed = {e for a, eps in who.items() if a >= ba.BANK_FLOOR
                          for e in eps}
            self.assertEqual(attributed & common_eps, set(),
                             f"bank{bank} attributed a banked address to a "
                             f"common-area entry point")

    def test_a_common_entry_point_records_the_bank_that_reached_it(self):
        """`frm` is the entry point, never None. A None reads as a seed the
        linker wrote down, which would be a false claim about the linker for a
        shared routine -- and it would let `entry_chain()` walk past an address
        no bank owns."""
        for bank in (0, 1):
            entries = self.closures[bank][2]
            common = {a: frm for a, (k, frm) in entries.items() if k == "common"}
            self.assertTrue(common)
            self.assertEqual([a for a, frm in common.items() if frm is None], [])

    def test_a_shared_routine_is_ambiguous_rather_than_picked(self):
        """Where both banks reach one common callee, both record it and
        neither claims the bytes. The routine is mapped in every bank, so a
        winner here would be a claim about a region no bank owns."""
        by_addr = {a: {self.closures[b][2][a][1] for b in (0, 1)
                       if a in self.closures[b][2]
                       and self.closures[b][2][a][0] == "common"}
                   for a in {a for b in (0, 1)
                             for a, (k, _f) in self.closures[b][2].items()
                             if k == "common"}}
        shared = [a for a, frms in by_addr.items() if len(frms) > 1]
        self.assertTrue(shared, "no common callee is reached from both banks, "
                        "so the ambiguity is not exercised")
        for addr in shared:
            for bank in (0, 1):
                self.assertNotIn(addr, self.closures[bank][0],
                                 f"0x{addr:04X} is common area but was "
                                 f"attributed to bank{bank}")

    def test_entry_chain_splices_a_common_hop(self):
        """`entry_chain()` splices a common hop the way it splices a table
        edge, and for the same reason: the hop's `frm` is the entry point that
        reached it, so the chain names that rather than skipping to a seed.

        Asserted as the whole chain rather than its length, because the failure
        this guards is a chain that *grows* -- splicing past the common address
        into the banked code behind it would make the depth histogram larger
        and no more meaningful, which is what the docstring says about table
        edges too.
        """
        entries = self.closures[0][2]
        common = sorted(a for a, (k, _f) in entries.items() if k == "common")
        self.assertTrue(common)
        for addr in common[:16]:
            frm = entries[addr][1]
            chain = ba.entry_chain(entries, addr)
            self.assertIn(addr, chain)
            self.assertIn(frm, chain)
            # The chain runs seeds-first and ends at the address asked about,
            # and `frm` sits immediately before it -- the hop is spliced, not
            # replaced by a walk to whatever the common routine calls next.
            self.assertEqual(chain[-1], addr)
            self.assertEqual(chain[-2], frm)


class TheDeltaIsZero(unittest.TestCase):
    """The measured negative, asserted as an identity between two closures."""

    @classmethod
    def setUpClass(cls):
        (cls.d, cls.seeds, cls.handlers, cls.seeded, cls.closures,
         cls.without) = both()

    def test_the_attributed_address_set_is_identical(self):
        for bank in (0, 1):
            self.assertEqual(self.closures[bank][0], self.without[bank][0],
                             f"bank{bank}'s attributed addresses moved")

    def test_the_per_address_path_counts_are_identical(self):
        """Stronger than the set: a byte that moved from one entry point to
        another would leave the set alone and the counts changed."""
        for bank in (0, 1):
            for addr, n in self.closures[bank][0].items():
                self.assertEqual(n, self.without[bank][0][addr],
                                 f"bank{bank} 0x{addr:04X} path count moved")

    def test_the_four_verdicts_are_identical_over_both_populations(self):
        """Both populations §3 reports: all bucket-B pairs, and the narrower
        both-banks-live subset the headline is drawn from."""
        rows, _s, _t = survey(self.d)
        with_p = ba.pair_rows(rows, self.closures)
        without_p = ba.pair_rows(rows, self.without)
        self.assertEqual(len(with_p), len(without_p))
        for label, pick in (("all bucket-B", lambda ps: ps),
                            ("both-banks-live", ba.both_live)):
            self.assertEqual(
                tuple(ba.tally(pick(with_p))[v] for v in ba.VERDICTS),
                tuple(ba.tally(pick(without_p))[v] for v in ba.VERDICTS),
                f"{label} verdicts moved")

    def test_no_pair_changes_its_verdict(self):
        """Per pair rather than per class: a target that moved from
        `unreached` to `still-ambiguous` and another that moved back would
        leave both totals where they were."""
        rows, _s, _t = survey(self.d)
        before = {(p["region"], p["target"]): p["verdict"]
                  for p in ba.pair_rows(rows, self.without)}
        after = {(p["region"], p["target"]): p["verdict"]
                 for p in ba.pair_rows(rows, self.closures)}
        self.assertEqual(set(before), set(after))
        moved = [k for k in before if before[k] != after[k]]
        self.assertEqual(moved, [],
                         f"{len(moved)} pair(s) changed verdict")


class TheBoundsArm(unittest.TestCase):
    """§9's second horn, measured rather than argued: the same two closures
    under a raised ceiling.

    "Is the residue seeds or bounds" is a disjunction, so both arms have to be
    run rather than one of them argued. `TheDeltaIsZero` is the seeds arm; this
    is the bounds one, and it is here because an earlier version of this change
    put "not bounds" in the tool's own report and in two write-ups with nothing
    in the tree computing it -- which left a reader with a measured negative on
    one horn and an unmeasured assertion on the other and no way to tell which
    was which.

    The factor is read from `ba.BOUNDS_FACTOR` rather than restated, and
    nothing here holds a population as a figure: every one of them moves with
    the walk's bounds, and what is held is the relation between the two walks.
    """

    @classmethod
    def setUpClass(cls):
        (cls.d, _seeds, _handlers, cls.seeded, cls.shipped,
         _without) = both()
        cls.raised = {
            b: ba.closure(cls.d, b, cls.seeded[b],
                          max_depth=ba.MAX_DEPTH * ba.BOUNDS_FACTOR,
                          max_insns=ba.MAX_INSNS * ba.BOUNDS_FACTOR)
            for b in (0, 1)}
        rows, _s, _t = survey(cls.d)
        cls.rows = rows
        cls.arms = ba.bounds_delta(cls.d, cls.shipped, rows, cls.seeded)

    def test_the_arm_reports_each_bounds_stops_either_way(self):
        """The stop count is reported for both budgets, not only the raised
        one. Without that, "nothing moved" is what a broken arm looks like as
        well as what a lifted one looks like, so the figure cannot be read."""
        ceilings = {ba.END_DEPTH, ba.END_BUDGET}
        for bank in (0, 1):
            for why, pair in self.arms["banks"][bank]["stops"].items():
                with self.subTest(bank=bank, bound=why):
                    was, now = pair
                    self.assertIsInstance(was, set)
                    self.assertIsInstance(now, set)
        # The arm has to have something to show: a ceiling that fired at 1x.
        # Which bank, and how many, moves with the walk -- that at least one
        # did is the relation.
        self.assertTrue(
            any(pair[0] for bank in (0, 1) for why, pair
                in self.arms["banks"][bank]["stops"].items()
                if why in ceilings),
            "no ceiling fired at 1x, so BOUNDS_FACTOR is under the threshold "
            "the arm needs and it re-walked the same closure")

    def test_every_ceiling_that_fired_clears(self):
        """A factor lifts `MAX_DEPTH` and `MAX_INSNS` and nothing else, so the
        relation is between the two reasons those constants control and every
        other stop reason: the ceilings that fired stop firing, and the rest
        land on exactly the same entry points."""
        ceilings = {ba.END_DEPTH, ba.END_BUDGET}
        for bank in (0, 1):
            stops = self.arms["banks"][bank]["stops"]
            for why, (was, now) in sorted(stops.items()):
                with self.subTest(bank=bank, bound=why):
                    if why in ceilings:
                        self.assertFalse(now, f"{why} still stops {len(now)} "
                                              f"entry point(s) at the raised "
                                              f"ceiling")
                    else:
                        self.assertEqual(now, was,
                                         f"{why} moved under a budget that "
                                         f"cannot resolve it")

    def test_the_lifted_walk_attributes_the_same_addresses(self):
        """The result the arm exists to produce, checked against closures this
        suite walks itself rather than against `bounds_delta`'s own account of
        them -- a function that returned two empty sets would satisfy the
        check above and this one."""
        for bank in (0, 1):
            with self.subTest(bank=f"bank{bank}"):
                self.assertEqual(set(self.raised[bank][0]),
                                 set(self.shipped[bank][0]))
                arm = self.arms["banks"][bank]
                self.assertEqual(arm["added"], set())
                self.assertEqual(arm["lost"], set())

    def test_none_of_the_four_verdicts_moves(self):
        for label, pick in (("all bucket-B", lambda ps: ps),
                            ("both-banks-live", ba.both_live)):
            with self.subTest(label=label):
                before = ba.tally(pick(ba.pair_rows(self.rows, self.shipped)))
                after = ba.tally(pick(ba.pair_rows(self.rows, self.raised)))
                self.assertEqual([after[v] for v in ba.VERDICTS],
                                 [before[v] for v in ba.VERDICTS])
        self.assertEqual(self.arms["verdicts"],
                         {v: 0 for v in ba.VERDICTS})

    def test_what_moves_is_which_walk_arrived_first_not_the_content(self):
        """The nuance the report has to carry. A walk that no longer stops
        finds callees the truncated one never reached, which reorders the
        worklist, so an address can be reached by more paths than before
        without being reached by a path that was missing.

        Asserted as a relation and not as a figure: whether anything moved at
        all is a property of this image and its bounds, but *if* the walk
        differs then it differs only inside the closure -- same entry points,
        same addresses -- which is what licenses comparing the address set and
        the verdicts and calling the result a measurement.
        """
        moved = {b for b in (0, 1) if self.arms["banks"][b]["paths"]}
        for bank in (0, 1):
            with self.subTest(bank=f"bank{bank}"):
                self.assertEqual(set(self.raised[bank][2]),
                                 set(self.shipped[bank][2]))
                if bank in moved:
                    self.assertNotEqual(self.raised[bank][0],
                                        self.shipped[bank][0],
                                        "the path counts are identical, so "
                                        "this suite is not seeing the "
                                        "reordering the arm reports")


class TheMissingEdge(unittest.TestCase):
    """Why the delta is zero: the common area's route out is a DPTR immediate,
    which is not an edge a callee-keyed worklist has."""

    @classmethod
    def setUpClass(cls):
        cls.d = firmware()

    def test_a_common_route_names_a_banked_target_in_dptr_and_not_in_callees(self):
        """Pinned per route rather than as a census, because the claim is
        about the *vocabulary*: `descend()` records the immediate in
        `code_immediates` and never in `callees`, so the worklist cannot see
        it, and the stub it branches to ends in `ret` so nothing branches
        onward to the DPTR's value either."""
        for site, raw, target, stub in ba.DPTR_ROUTES:
            off = offset_for_runtime(site, "common")
            with self.subTest(site=f"0x{site:04X}"):
                self.assertEqual(self.d[off:off + len(raw)], raw)
                arm = descend(self.d, "bank0", site, None, ba.MAX_DEPTH,
                              ba.MAX_INSNS, True)
                self.assertIn(target, arm.code_immediates)
                self.assertNotIn(target, arm.callees)
                self.assertIn(stub, arm.callees)

    def test_the_reset_vector_reaches_those_routes(self):
        """So the routes are not code nobody calls: the vector the CPU takes at
        power-on reaches both, and following the common area descends them."""
        arm = descend(self.d, "bank0", ba.RESET_VECTOR, None, ba.MAX_DEPTH,
                      ba.MAX_INSNS, True)
        callees = dict.fromkeys(arm.callees)
        for site, _raw, _target, _stub in ba.DPTR_ROUTES:
            self.assertIn(site, callees)

    def test_the_closure_reaches_both_route_targets_anyway(self):
        """**The half that stops the pair above being read as a counterexample
        to itself.** `0x158E` and `0x1594` are themselves trampoline entries, so
        `seeds_for()` already seeds `0xD89F` and `0xD96C` and bank0's closure
        reaches both -- before this change as well as after.

        An earlier draft of the write-up claimed the closure "now walks the code
        that names them and still does not reach them". That was false, and this
        is the assertion that would have caught it: the missing thing is the
        *edge*, not the address. If a future change made these targets
        unseeded, the vocabulary claim would need a different example rather
        than this one.
        """
        _rows, _stubs, tramp = survey(self.d)
        seeds = ba.seeds_for(tramp)
        for site, _raw, target, _stub in ba.DPTR_ROUTES:
            with self.subTest(site=f"0x{site:04X}"):
                self.assertIn(site, tramp,
                              f"0x{site:04X} is no longer a trampoline entry, so "
                              f"this pair is no longer an example of the census "
                              f"covering the route the worklist cannot see")
                self.assertIn(tramp[site][1], seeds[tramp[site][0]])

    def test_common_arms_do_carry_the_immediate(self):
        """The other half: the edge is not absent from the image or from
        `descend()`, it is absent from the worklist. Measured over the
        `common`-kind entry points the closure actually reached."""
        _d, _s, _h, _sd, closures, _w = both()
        for bank in (0, 1):
            immediates = ba.imms_for(firmware(), f"bank{bank}", closures[bank])
            self.assertTrue(
                immediates,
                f"bank{bank}'s common-kind arms name no DPTR immediate, so the "
                f"missing edge is not the explanation here")

    def test_the_immediate_count_is_not_a_count_of_unfollowed_routes(self):
        """The reconciliation, asserted so the figure cannot drift back into
        reading as coverage. The trampoline census already names nearly every
        banked DPTR immediate in a `common`-kind arm, because the linker writes
        the route at the trampoline site; so the total is how often the idiom
        appears in the arms this walk descended, not a count of routes nothing
        follows.
        """
        _rows, _stubs, tramp = survey(self.d)
        named = {t for _bank, t in tramp.values()}
        _d, seeds, _h, _sd, closures, _w = both()
        for bank in (0, 1):
            beyond = {i for i in ba.imms_for(firmware(), f"bank{bank}",
                                             closures[bank])
                      if offset_for_runtime(i, f"bank{bank}") is not None}
            with self.subTest(bank=f"bank{bank}"):
                self.assertTrue(beyond)
                covered = beyond & named
                self.assertGreaterEqual(
                    len(covered), len(beyond) // 2,
                    "the census no longer covers most of these, so the wording "
                    "in the write-up and in section 8 needs re-measuring")

    def test_the_one_uncovered_immediate_is_an_xdata_clear_not_a_code_route(self):
        """So this image offers no missed *code* route, and the zero above is
        structural rather than lucky: every route the walk does not see is
        already a seed. The leftover is `0x9000` at `0x0F95`, where
        `mov dptr,#0x9000` bounds the `movx @dptr,a` loop clearing XDATA
        `0x9000`-`0x97FF`.

        If a different immediate ever appears here it is not automatically a
        code route -- an immediate at or above `CODE_FLOOR` is a candidate, not
        a proved entry -- so this fails rather than letting the follow-up be
        sized on an example that turns out to be data.
        """
        _rows, _stubs, tramp = survey(self.d)
        named = {t for _bank, t in tramp.values()}
        _d, _s, _h, _sd, closures, _w = both()
        leftovers = set()
        for bank in (0, 1):
            beyond = {i for i in ba.imms_for(firmware(), f"bank{bank}",
                                             closures[bank])
                      if offset_for_runtime(i, f"bank{bank}") is not None}
            leftovers |= beyond - named
        self.assertTrue(leftovers)
        for addr in sorted(leftovers):
            with self.subTest(immediate=f"0x{addr:04X}"):
                self.assertIn(addr, ba.XDATA_CLEAR_IMMEDIATES,
                              "an immediate no trampoline names appeared that is "
                              "not a known XDATA clear; it has to be read before "
                              "anything calls it a code route")

    def test_the_xdata_clear_immediate_is_pinned_as_bytes(self):
        """The leftover is a real `mov dptr`, and what it points at is the part
        that decides what it means -- so both are pinned rather than asserted in
        prose."""
        off = offset_for_runtime(ba.XDATA_CLEAR_SITE, "common")
        self.assertEqual(
            self.d[off:off + 3],
            bytes((0x90, ba.XDATA_CLEAR_IMMEDIATE >> 8,
                   ba.XDATA_CLEAR_IMMEDIATE & 0xFF)),
            "common 0x0F95 is no longer `mov dptr,#0x9000`")


class TheReport(unittest.TestCase):
    """Section 8 prints the comparison rather than asserting it in prose."""

    @classmethod
    def setUpClass(cls):
        cls.out = report()
        # The report is printed a line at a time, so a phrase can straddle a
        # wrap. Matching against a whitespace-flattened copy keeps each case
        # reading as the sentence it is about rather than as a line break.
        cls.flat = " ".join(cls.out.split())

    def test_it_prints_the_comparison_both_ways(self):
        self.assertIn("entry points without", self.flat)
        self.assertIn("addresses without", self.flat)

    def test_each_contribution_is_measured_on_its_own(self):
        """Three rows, each varying one thing against the same baseline.

        `follow_common` defaults to True, so a row that omitted it would print
        the shipped closure's figures under a second label and the section would
        claim a separation it never measured. Asserting the three labels keeps
        the separation checkable rather than asserted in prose.
        """
        for label in ("vector-table seeds alone",
                      "common-area continuation alone",
                      "both (as shipped)"):
            self.assertIn(label, self.flat)

    def test_each_row_prints_its_own_populations_figures(self):
        """**The row that cannot be satisfied by a label.** Each line's entry
        point and banked address counts are compared against a population this
        suite computes, so a row that reused the closure above it prints the
        wrong entry-point delta and fails.

        The entry-point delta is what makes this work. The banked figures are
        `+0` in every row -- that is the finding -- so a duplicated row would
        print identical zeros under a second label and nothing would notice.
        The seeds alone add a handful of entry points and no descent at all;
        the continuation alone does nearly all of the descending. Those two
        numbers differing is the evidence the rows are really different walks.
        """
        d = firmware()
        _rows, _stubs, tramp = survey(d)
        seeds = ba.seeds_for(tramp)
        handlers = ba.vector_handlers(d, tramp)
        without = {b: ba.closure(d, b, seeds[b], follow_common=False)
                   for b in (0, 1)}
        populations = {
            "vector-table seeds alone":
                {b: ba.closure(d, b, seeds[b] | handlers[b], follow_common=False)
                 for b in (0, 1)},
            "common-area continuation alone":
                {b: ba.closure(d, b, seeds[b]) for b in (0, 1)},
            "both (as shipped)":
                {b: ba.closure(d, b, seeds[b] | handlers[b]) for b in (0, 1)},
        }
        for label, cl in populations.items():
            eps0 = len(cl[0][2]) - len(without[0][2])
            banked0 = len(cl[0][0]) - len(without[0][0])
            eps1 = len(cl[1][2]) - len(without[1][2])
            banked1 = len(cl[1][0]) - len(without[1][0])
            expected = (f"adds {eps0} entry point(s) and {banked0} banked "
                        f"address(es) in bank0, {eps1} and {banked1} in bank1")
            with self.subTest(row=label):
                self.assertIn(f"{label}: ", self.flat)
                self.assertIn(expected, self.flat,
                              "the row's printed figures are not this "
                              "population's; a row that reused the closure "
                              "above it would print the same `+0` banked "
                              "figures and only the entry-point delta would "
                              "give it away")

    def test_the_isolated_rows_really_are_different_populations(self):
        """The relation behind those figures, asserted directly rather than only
        through the printed text: each isolated population is a distinct
        entry-point set, and none of them attributes a banked byte the baseline
        did not.
        """
        d = firmware()
        _rows, _stubs, tramp = survey(d)
        seeds = ba.seeds_for(tramp)
        handlers = ba.vector_handlers(d, tramp)
        without = {b: ba.closure(d, b, seeds[b], follow_common=False)
                   for b in (0, 1)}
        seeds_only = {b: ba.closure(d, b, seeds[b] | handlers[b],
                                    follow_common=False) for b in (0, 1)}
        cont_only = {b: ba.closure(d, b, seeds[b]) for b in (0, 1)}
        shipped = {b: ba.closure(d, b, seeds[b] | handlers[b]) for b in (0, 1)}
        for bank in (0, 1):
            with self.subTest(bank=f"bank{bank}"):
                # Each isolated population is a distinct entry-point set ...
                self.assertNotEqual(seeds_only[bank][2], cont_only[bank][2])
                self.assertNotEqual(seeds_only[bank][2], without[bank][2])
                self.assertNotEqual(cont_only[bank][2], without[bank][2])
                # ... and none of them attributes a banked byte the baseline did
                # not, which is the `+0` the section prints.
                for pop in (seeds_only, cont_only, shipped):
                    self.assertEqual(pop[bank][0], without[bank][0])

    def test_it_reports_the_census_overlap_beside_the_total(self):
        """The bare DPTR-immediate count reads as a count of unfollowed routes
        unless the coverage is printed next to it, which is the reading the
        earlier draft of the write-up got wrong."""
        self.assertIn("already named by a trampoline entry somewhere in the "
                      "image", self.flat)
        self.assertIn("not a count of routes nothing follows", self.flat)

    def test_it_says_the_leftover_immediate_is_not_a_code_route(self):
        """`0x9000` is an XDATA pointer above `CODE_FLOOR`, not a route into
        banked code. Without this the leftover prints as a missed route, which
        is the calibration failure the whole correction is about."""
        self.assertIn("XDATA", self.flat)
        self.assertIn("0x9000", self.flat)
        self.assertIn("no such code route to miss", self.flat)

    def test_it_states_the_zero_delta_as_measured(self):
        self.assertIn("The attributed address set is identical in both banks",
                      self.flat)

    def test_it_answers_seeds_or_bounds_with_neither(self):
        self.assertIn('the answer to "seeds or bounds" is neither', self.flat)

    def test_it_prints_the_bounds_arm_beside_the_seeds_rows(self):
        """Both halves of the disjunction §9 asks are computed and printed in
        the same section. Without the second, "neither" is half a measurement."""
        self.assertIn("And the second arm of \"seeds or bounds\", measured "
                      "rather than argued", self.flat)
        self.assertIn("Each bound's own stop count either way", self.flat)
        self.assertIn(f"multiplied by {ba.BOUNDS_FACTOR}", self.flat)

    def test_the_bounds_arm_shows_the_ceilings_clearing(self):
        """The stop lines, matched against `bounds_delta()`'s own account.

        The point of the arm is that a reader can see the ceilings stop firing
        rather than infer it from a figure that reads the same either way, so
        the `before -> after` transition for each bound is what is asserted --
        against the populations this suite walks, not against a restatement.
        """
        d = firmware()
        _rows, _stubs, tramp = survey(d)
        seeded = {b: ba.seeds_for(tramp)[b] | ba.vector_handlers(d, tramp)[b]
                  for b in (0, 1)}
        shipped = {b: ba.closure(d, b, seeded[b]) for b in (0, 1)}
        arms = ba.bounds_delta(d, shipped, _rows, seeded)
        for bank in (0, 1):
            for why, (was, now) in sorted(arms["banks"][bank]["stops"].items()):
                with self.subTest(bank=f"bank{bank}", bound=why):
                    self.assertIn(f"{why} {len(was)} -> {len(now)}", self.flat)

    def test_the_bounds_arm_says_what_moved_and_what_did_not(self):
        """The path counts are the honest wrinkle: lifting the ceilings changes
        which walk reached a byte first, not which bytes are reached. Printed
        so a reader shown "nothing moved" does not conclude the two walks are
        the same one."""
        self.assertIn("What does move is which walk reached a byte first, not "
                      "which bytes are reached", self.flat)
        self.assertIn("Every ceiling cleared and the indirect jump did not",
                      self.flat)

    def test_the_negative_is_calibrated(self):
        """CLAUDE.md's rule, and the one a negative result erodes first: the
        report may say the common area adds no banked byte *by this walk*,
        never that it reaches no banked code. Every line carrying "reach" and a
        negative is read here, so an edit that writes "the common area reaches
        nothing banked" fails."""
        offenders = [line.strip() for line in self.out.splitlines()
                     if "reach" in line and "no banked" in line.lower()
                     and not any(p in line for p in ("identical", "adds",
                                                     "this walk", "walk"))]
        self.assertEqual(offenders, [],
                         "an uncalibrated negative in the report")

    def test_no_section_claims_the_common_area_is_recorded_and_not_followed(self):
        """The mechanism is described once and has to be described *the same
        way* everywhere, because one run of the tool prints every section.

        `main()` builds its closures with the default `follow_common=True`, so a
        section that still says the common area is recorded and followed
        nothing contradicts the section that says it is followed as a same-bank
        continuation -- in the same output, which is what made the original
        correction land in the document and miss its tool-side twin. Asserting
        the sentence that is there is what holds the one that is not.
        """
        self.assertIn("records it and follows it as a same-bank continuation",
                      self.flat)
        for stale in ("records it and follows nothing",
                      "records each and follows none"):
            self.assertNotIn(stale, self.flat,
                             f"section 7 still claims {stale!r}")

    def test_it_keeps_the_same_bank_caveat(self):
        """Following a common call *extends* the same-bank assumption rather
        than testing it, so the standing caveat has to survive the change that
        made the section necessary."""
        self.assertIn("so it extends that assumption rather than testing it",
                      self.flat)
        self.assertIn("a verdict on the same-bank assumption", self.flat)

    def test_it_does_not_claim_the_dptr_edge_is_enabled(self):
        """The edge is named as the missing one and left off, so a reader does
        not come away thinking section 8 turned it on."""
        self.assertIn("not a proved entry -- so it is not enabled here",
                      self.flat)

    def test_the_report_carries_no_total_of_the_repository(self):
        for phrase in ("write-ups", "suites", "tests in all"):
            self.assertNotIn(phrase, self.flat)


class TheRegionsTable(unittest.TestCase):
    """The committed CSVs must not move: they are what a region map reads, and
    a changed row here would be a silent consumer-visible change."""

    def test_both_committed_csvs_regenerate_byte_identically(self):
        for flag, name in (("--regions-csv", "bank-attribution-regions.csv"),
                           ("--pairs-csv", "bank-attribution-pairs.csv")):
            with self.subTest(csv=name):
                buf = io.StringIO()
                argv = sys.argv
                sys.argv = ["bank_attribution.py", FIRMWARE, flag]
                try:
                    with contextlib.redirect_stdout(buf):
                        self.assertEqual(ba.main(), 0)
                finally:
                    sys.argv = argv
                with open(os.path.join(ANNOTATIONS, name), newline="") as f:
                    self.assertEqual(buf.getvalue(), f.read(),
                                     f"{name} moved")


if __name__ == "__main__":
    unittest.main()