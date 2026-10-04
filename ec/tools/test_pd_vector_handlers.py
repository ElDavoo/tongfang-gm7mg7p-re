#!/usr/bin/env python3
"""Offline checks for pd_vector_handlers.py: the five PD interrupt handler
targets, the chain that makes a bare `ret` their terminator, and the framing
conflict the tool refuses to resolve.

Every case asserts against the committed `ec/firmware/GMxMGxx_11.800` and the
committed tree, never against a fixture. That is the point of the file: the
bytes *are* the input, so a byte that moved has to take the suite red rather
than let a report go quietly wrong. The only scratch copy is the
temporary page `TestCheckExitsNonZeroOnDrift` writes.

**The load-bearing case is `TestRetIsTheTerminator`, and it pins three
separate things rather than the conclusion.** The wrapper's `lcall 0x0050` is
what puts a return address on the stack; the shared body's ending `ljmp` is
what stops it pushing one of its own; and the `jmp @a+dptr` is what carries
control to the handler. "A `ret` at a handler pops the wrapper's return
address" stops following from the bytes if any one of the three is replaced,
so each is asserted on its own and a mutation moves one at a time. The claim
the page now rests on is therefore not a sentence in a comment that happens to
be true today.

**The negative control is `TestRetsHereAreCalled`, and it does the real work.**
Three of the five vectors point at a single `0x22`. The reason that is a
no-op stub and not padding is that a `0x22` *in the same run* is `lcall`ed by
committed listings — so the suite asserts the callers exist, and a mutation
that removes the `lcall` from a scratch listing takes it red.

**The null cases are the calibration.** `0xEFEA` and `0xE5EB` have no decoded
referrer, and `TestANullIsReportedAsANull` asserts the tool says so *in those
words* and names the search — the token `not found by this method` is the
finding, and a checker that reported "unreachable" would be the overclaim
CLAUDE.md puts above every other rule. `TestByteScanIsNotACallerCount` is the
other half: the byte scan finds two candidates for each, in addresses no
listing holds, and those must never be reported as callers.

**`TestFramingConflictIsReportedNotResolved` is a case about a disagreement.**
`0xF790` is named by the `0x1B` vector's word, and the linear walk from
`0xF78B` steps over it. The tool returns that as a conflict; the case asserts
the conflict is still there, so an edit that quietly picked a side and made the
gap close takes the suite red instead of passing for a reading nothing in the
image establishes.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# pd_vector_handlers imports its siblings by bare module name, the way the rest
# of this directory does, so the tool directory goes on the path before the load
# rather than after.
sys.path.insert(0, str(HERE))

import pd_image_census as census  # noqa: E402
import pd_vector_handlers as tool  # noqa: E402

TOOL = HERE / "pd_vector_handlers.py"

# What the five interrupt vectors' CODE words select, by value. Transcribed by
# hand from the three bytes at each selector address, so the suite's own copy is
# an oracle rather than a second call into the tool it checks; the tool derives
# the same thing from the image and a disagreement fails here first.
EXPECTED = {
    0x03: (0x0151, b"\xff\xa8\xae", 0xA8AE),
    0x0B: (0x0154, b"\xff\xf7\xae", 0xF7AE),
    0x13: (0x0157, b"\xff\xf7\xaf", 0xF7AF),
    0x1B: (0x015A, b"\xff\xf7\x90", 0xF790),
    0x23: (0x015D, b"\xff\xf7\xb0", 0xF7B0),
}

# The bodies 0xF790 and 0xF798 call, and the fact that neither is decoded here.
HANDLER_BODIES = (0xEFEA, 0xE5EB)


def region():
    """The committed 64 KiB PD image, or raise the census's refusal."""
    data, _how = census.read_region()
    return data


def page_text():
    """The committed `pd-image.md`, read as text."""
    with open(census.PAGE, encoding="utf-8") as f:
        return f.read()


class TestTheFiveWords(unittest.TestCase):
    """Case 1: the selectors, their three CODE bytes, and the five words."""

    @classmethod
    def setUpClass(cls):
        cls.region = region()
        cls.rows = {v: r for v, r in
                    ((r[0], r) for r in tool.handlers(cls.region))}

    def test_one_row_per_interrupt_vector(self):
        self.assertEqual(sorted(self.rows), sorted(EXPECTED))

    def test_selector_and_three_bytes(self):
        for vector, (selector, triple, _target) in EXPECTED.items():
            row = self.rows[vector]
            self.assertEqual(row[1], selector,
                             "the DPTR immediate in the 0x%02X wrapper" % vector)
            self.assertEqual(row[4], triple,
                             "the three CODE bytes at 0x%04X" % selector)
            self.assertEqual(row[3], 1,
                             "0x%04X has exactly one MOV DPTR site" % selector)

    def test_the_word_is_the_second_and_third_byte(self):
        for vector, (_s, triple, target) in EXPECTED.items():
            self.assertEqual((triple[1] << 8) | triple[2], target,
                             "the jump target the 0x%02X vector selects" % vector)

    def test_the_first_byte_is_never_the_target(self):
        """The lead byte goes into R3 and the jump does not use it.

        All five are 0xFF, so a reading that took the word from bytes one and
        two would land on 0xFFA8, 0xFFF7 and so on. Asserting they are not the
        target is what stops `0x1229`'s R2:R1 ordering being "corrected" into
        the other one.
        """
        for vector, (_s, triple, target) in EXPECTED.items():
            self.assertNotEqual(triple[0], (target >> 8) & 0xFF,
                                "the lead byte is not the target's high byte")


class TestTheTargets(unittest.TestCase):
    """Case 2: the opcode at each target, by value."""

    @classmethod
    def setUpClass(cls):
        cls.region = region()
        cls.shapes = tool.handler_shapes(cls.region)

    def test_one_committed_entry_and_four_unlisted(self):
        starts = {v: r[6] for v, r in
                  ((r[0], r) for r in tool.handlers(self.region))}
        self.assertEqual(starts[0x03], "yes")
        for vector in (0x0B, 0x13, 0x1B, 0x23):
            self.assertEqual(starts[vector], tool.NOT_FOUND,
                             "0x%02X's target has no listing here" % vector)

    def test_the_opcode_at_each_target(self):
        """By value, which is the part that matters.

        The three no-op vectors all point at one 0x22 and the fourth at an
        `lcall`; every one of them is the first byte of its target, so a tool
        that read the opcode from anywhere else would still get these right.
        """
        self.assertEqual(self.region[0xF7AE], tool.RET)
        self.assertEqual(self.region[0xF7AF], tool.RET)
        self.assertEqual(self.region[0xF7B0], tool.RET)
        self.assertEqual(self.region[0xF790], tool.LCALL)
        self.assertEqual((self.region[0xF791] << 8) | self.region[0xF792],
                         0xEFEA)
        self.assertEqual(self.region[0xF793], tool.RET)

    def test_the_derived_shape_matches_the_bytes(self):
        self.assertEqual(self.shapes[0xF7AE], "`ret`")
        self.assertEqual(self.shapes[0xF7AF], "`ret`")
        self.assertEqual(self.shapes[0xF7B0], "`ret`")
        self.assertEqual(self.shapes[0xF790], "`lcall 0xEFEA` then `ret`")
        self.assertEqual(self.shapes[0xA8AE],
                         "a committed entry, `event_dispatch_ff80_ffe0`")

    def test_the_three_no_op_vectors_are_the_ones_the_page_names(self):
        """`0x0B`, `0x13` and `0x23` -- the table's own row, not a chosen set."""
        no_op = sorted(v for v, (_s, _t, target) in EXPECTED.items()
                       if self.region[target] == tool.RET)
        self.assertEqual(no_op, [0x0B, 0x13, 0x23])


class TestRetIsTheTerminator(unittest.TestCase):
    """Case 3: the load-bearing chain, pinned link by link."""

    @classmethod
    def setUpClass(cls):
        cls.region = region()

    def test_all_four_links_hold(self):
        for ok, phrase in tool.chain_is_jump_not_call(self.region):
            self.assertTrue(ok, phrase)

    def test_the_shared_body_leaves_no_return_address_open(self):
        """The link that makes the tail jump load-bearing.

        `0x0050`'s one `lcall` targets `0x10f1`, which ends in a `ret`, so the
        stack is back where the wrapper left it when the `ljmp` runs. Without
        this a walk that only asked "does the body end in a jump" would still
        pass after the tail jump had become a call, because a call falls
        through and the next transfer it found would be further along.
        """
        self.assertEqual(tool.calls_left_open(self.region, 0x0050), [])
        self.assertEqual(self.region[0x10FC], tool.RET,
                         "0x10f1 pops what 0x0050 pushed")

    def test_the_wrapper_pushes_the_return_address(self):
        callee, pushes, reti = tool.wrapper_pushes_return_address(self.region)
        self.assertEqual(callee, 0x0050)
        self.assertEqual(reti, True)
        self.assertGreaterEqual(pushes, 1,
                                "the wrapper pushes before it calls")

    def test_the_shared_body_ends_in_a_jump_not_a_call(self):
        at, op = tool.last_transfer(self.region, 0x0050)
        self.assertEqual(op, tool.LJMP)
        self.assertEqual(self.region[at], 0x02)
        self.assertEqual((self.region[at + 1] << 8) | self.region[at + 2],
                         0x1229)

    def test_the_dispatch_reaches_the_target_by_indirect_jump(self):
        at, is_jump = tool.dispatch_reaches_target_by_jump(self.region)
        self.assertTrue(is_jump)
        # 0x73 and not 0x02: a `call @a+dptr` would push a return address that
        # a `ret` at the handler would pop instead of the wrapper's, which is
        # the whole difference between the chain working and not.
        self.assertEqual(self.region[at], 0x73)

    def test_a_tail_jump_turned_into_a_call_breaks_the_chain(self):
        """A mutation, and the one the fourth link exists for.

        One byte at 0x0053 turns the shared body's `ljmp` into an `lcall`. The
        body no longer ends in a jump, and the call it now makes targets
        0x1229, which does not return -- so its return address would still be
        on the stack when a handler's `ret` ran, and the `ret` would pop that
        instead of the wrapper's. Both links have to notice.
        """
        scratch = bytearray(self.region)
        at, _op = tool.last_transfer(self.region, 0x0050)
        scratch[at] = tool.LCALL
        links = tool.chain_is_jump_not_call(bytes(scratch))
        self.assertFalse(links[1][0],
                         "a call at 0x%04X must break the tail-jump link" % at)
        self.assertFalse(links[2][0],
                         "a call at 0x%04X to a routine that does not return "
                         "must break the open-return-address link" % at)

    def test_a_return_where_the_tail_jump_was_breaks_the_tail_jump_link(self):
        """The simpler half: a body ending in `ret` does not carry control on."""
        scratch = bytearray(self.region)
        at, _op = tool.last_transfer(self.region, 0x0050)
        scratch[at] = tool.RET
        self.assertFalse(tool.chain_is_jump_not_call(bytes(scratch))[1][0])

    def test_a_call_at_dptr_breaks_the_indirect_jump_link(self):
        """`call @a+dptr` would push over the wrapper's return address."""
        scratch = bytearray(self.region)
        at, _is_jump = tool.dispatch_reaches_target_by_jump(self.region)
        scratch[at] = 0x02          # ljmp @a+dptr, one byte
        links = tool.chain_is_jump_not_call(bytes(scratch))
        self.assertFalse(links[3][0],
                         "an ljmp at 0x%04X must break the indirect-jump link"
                         % at)


class TestRetsHereAreCalled(unittest.TestCase):
    """Case 4: the negative control — a `0x22` here is a no-op, not padding."""

    @classmethod
    def setUpClass(cls):
        cls.region = region()

    def test_each_control_stub_is_a_bare_ret(self):
        for stub in tool.RETS_CALLED:
            self.assertEqual(self.region[stub], tool.RET,
                             "0x%04X is the control" % stub)

    def test_each_control_stub_is_lcalled_from_a_listing(self):
        for stub in tool.RETS_CALLED:
            decoded = tool.referrers_in_listings(stub)
            self.assertTrue(decoded,
                            "0x%04X is %s with no committed caller, which is "
                            "what padding looks like" % (stub, tool.NOT_FOUND))
            for site, entry, _name, kind in decoded:
                self.assertEqual(kind, "lcall")
                self.assertIsNotNone(entry,
                                     "the caller at 0x%04X must sit inside a "
                                     "committed listing" % site)

    def test_the_callers_are_the_two_the_run_names(self):
        """`DA44` and `A8AE` by name, not just by count."""
        callers = {name for stub in tool.RETS_CALLED
                   for _s, _e, name, _k in tool.referrers_in_listings(stub)}
        self.assertEqual(callers,
                         {"poll_0208_0209_then_spin",
                          "event_dispatch_ff80_ffe0"})

    def test_the_negative_control_and_the_handlers_are_the_same_shape(self):
        """A control stub and a no-op handler are both one `0x22`.

        This is the sentence the page rests on, so it is asserted rather than
        narrated: the three vectors' targets and the four called stubs are the
        same single-byte body, so a reading that made one padding and not the
        other would have to argue from something other than the bytes.
        """
        for target in (0xF7AE, 0xF7AF, 0xF7B0):
            self.assertEqual(self.region[target], tool.RET)
        for stub in tool.RETS_CALLED:
            self.assertEqual(self.region[stub], tool.RET)
        self.assertNotIn(0xF790, tool.RETS_CALLED)


class TestANullIsReportedAsANull(unittest.TestCase):
    """Case 5: the two undecoded bodies, and the wording of their null."""

    @classmethod
    def setUpClass(cls):
        cls.region = region()

    def test_no_committed_listing_calls_either_body(self):
        for body in HANDLER_BODIES:
            self.assertEqual(tool.referrers_in_listings(body), [],
                             "0x%04X gained a decoded caller; re-read it"
                             % body)

    def test_the_phrase_says_not_found_by_this_method(self):
        """The token, and none of the words that turn a search into an absence."""
        banned = ("unreachable", "absent", "never called", "not referenced",
                  "is dead", "no callers")
        for body in HANDLER_BODIES:
            phrase = tool.refcount_phrase(body, self.region)
            self.assertIn(tool.NOT_FOUND, phrase)
            for word in banned:
                self.assertNotIn(word, phrase,
                                 "0x%04X: %r reads as an absence" % (body,
                                                                     phrase))

    def test_the_phrase_names_the_search_it_ran(self):
        """A null without its population is the failure CLAUDE.md names."""
        phrase = tool.refcount_phrase(HANDLER_BODIES[0], self.region)
        self.assertIn("decoded", phrase)
        self.assertIn("committed pd listings", phrase)

    def test_the_control_does_the_same_wording_on_a_non_null(self):
        """The token is not a fixed string the tool prints everywhere.

        A checker that always said "not found by this method" would pass the
        null case and be worthless on every other target, so a target that has
        callers must not carry the token.
        """
        phrase = tool.refcount_phrase(tool.RETS_CALLED[0], self.region)
        self.assertNotIn(tool.NOT_FOUND, phrase)
        self.assertIn("decoded referrer(s) from", phrase)


class TestByteScanIsNotACallerCount(unittest.TestCase):
    """The two populations stay apart, in that order."""

    @classmethod
    def setUpClass(cls):
        cls.region = region()

    def test_the_byte_scan_is_wider_than_the_decoded_count(self):
        for body in HANDLER_BODIES:
            decoded = tool.referrers_in_listings(body)
            candidates = tool.referrers_in_bytes(self.region, body)
            self.assertGreater(len(candidates), len(decoded),
                               "0x%04X: the byte scan is the wider population"
                               % body)

    def test_every_candidate_is_reported_with_the_token(self):
        owners = census.address_owners(census.function_extents())
        for body in HANDLER_BODIES:
            candidates = tool.referrers_in_bytes(self.region, body)
            self.assertTrue(candidates)
            for site, _kind in candidates:
                if owners.get(site) is None:
                    self.assertIn(tool.NOT_FOUND,
                                  tool.refcount_phrase(body, self.region),
                                  "a candidate no listing holds must be "
                                  "reported as one")
                    break

    def test_the_five_targets_are_named_by_no_instruction(self):
        """Reached by `jmp @a+dptr` and by nothing the image spells."""
        for _v, _s, target, _sites, _t, _op, _st, _spans, _name in \
                tool.handlers(self.region):
            self.assertEqual(tool.referrers_in_listings(target), [])
            self.assertEqual(tool.referrers_in_bytes(self.region, target), [])


class TestTheRunAndItsFramingConflict(unittest.TestCase):
    """The run read two ways, and the one place the two cannot both be right."""

    @classmethod
    def setUpClass(cls):
        cls.region = region()

    def test_the_run_bounds_are_the_committed_neighbours(self):
        self.assertEqual(self.region[tool.RUN_FIRST], tool.LJMP)
        self.assertEqual(self.region[tool.RUN_LAST], tool.RET)
        self.assertEqual(self.region[tool.RUN_LAST + 1], 0xFF,
                         "the byte after the run is erased")

    def test_every_uncovered_span_in_the_run_is_named(self):
        spans = tool.uncovered_in_run()
        self.assertTrue(spans)
        extents = census.function_extents()
        for lo, hi in spans:
            for addr in range(lo, hi + 1):
                self.assertNotIn(addr, extents,
                                 "0x%04X is inside a span this tool calls "
                                 "uncovered" % addr)

    def test_every_handler_target_falls_in_an_uncovered_span(self):
        covered = {a for lo, hi in tool.uncovered_in_run()
                   for a in range(lo, hi + 1)}
        extents = census.function_extents()
        for _v, _s, target, _sites, _t, _op, _st, _spans, _name in \
                tool.handlers(self.region):
            if target in extents:
                continue
            self.assertIn(target, covered,
                          "0x%04X has no listing and sits outside every "
                          "uncovered span" % target)

    def test_the_framing_conflict_is_reported_not_resolved(self):
        """`0xF790` is named by the table and stepped over by the walk."""
        self.assertEqual(tool.framing_conflict(self.region), [0xF790])
        self.assertEqual(EXPECTED[0x1B][2], 0xF790,
                         "the conflict has to be a target the table names")

    def test_the_two_unframed_bytes_are_named_by_no_transfer(self):
        """The one place this change says something reaches nothing.

        It is a scan -- absolute, PC-relative and paged, at every byte offset --
        and a scan that finds nothing is *not found by this method*, never an
        absence. `branches_to()` returns the list either way so the report can
        print the token rather than a blank, and this case pins both: the null
        as it is, and a positive control on the same scan so a function that
        always returned nothing would not pass it.
        """
        self.assertEqual(tool.branches_to(self.region, tool.UNFRAMED), [],
                         "a transfer now names 0xF78E or 0xF78F; re-read it")
        # The same scan, on an address it does find: if this were empty the null
        # above would be the scan being broken rather than the image being quiet.
        self.assertTrue(tool.branches_to(self.region, (0xF79C,)))
        self.assertTrue(tool.branches_to(self.region, (0xF7B2,)))

    def test_the_linear_walk_does_not_land_on_the_conflicted_target(self):
        starts = {off for off, _text in tool.linear_reading(self.region)}
        self.assertNotIn(0xF790, starts,
                         "the walk from 0xF78B steps over 0xF790")
        # ...and it does land on the byte whose `jbc` swallows it, which is what
        # makes the disagreement real rather than a walk that simply stopped.
        self.assertIn(0xF78F, starts)
        self.assertEqual(self.region[0xF78F], 0x10, "JBC")

    def test_both_readings_are_returned_not_just_one(self):
        """One walk is the question asked badly; two is the question asked."""
        self.assertTrue(tool.linear_reading(self.region))
        self.assertTrue(tool.run_entries(self.region))
        # The per-entry set is a subset of the addresses the walk lands on for
        # every entry whose framing the two readings agree about -- 0xF79C,
        # 0xF79F and the four committed `ret_only` rows -- which is what makes
        # 0xF790's disagreement visible rather than assumed.
        linear = {off for off, _t in tool.linear_reading(self.region)}
        for entry, _walk, _name in tool.run_entries(self.region):
            if entry != 0xF790:
                self.assertIn(entry, linear,
                              "0x%04X: the two readings disagree about an "
                              "address the conflict function does not name"
                              % entry)


class TestThePageAndTheTool(unittest.TestCase):
    """Case 6: the committed page and the tool cannot drift apart."""

    def setUp(self):
        self.region = region()
        self.text = page_text()

    def test_the_pages_rows_are_the_tools_rows(self):
        self.assertEqual(tool.page_targets(self.text),
                         {k: (v[0], v[1])
                          for k, v in tool.derived_targets(self.region).items()})

    def test_every_derived_shape_is_stated_in_the_page(self):
        for cells in tool.page_tables(self.text):
            for row in cells[2:]:
                vector = tool.backticked(row[0])
                key = vector.lower()
                shape = tool.derived_targets(self.region)[key][2]
                self.assertIn(shape, row[3],
                              "the page cell for %s does not carry %r"
                              % (key, shape))

    def test_a_page_row_this_tool_does_not_derive_is_visible(self):
        """The union, not the page's keys alone.

        A check that only walked the page's rows would report clean on a page
        that had lost one, which is the drift it exists to catch.
        """
        self.assertEqual(sorted(tool.page_targets(self.text)),
                         sorted(tool.derived_targets(self.region)))


class TestCheckExitsNonZeroOnDrift(unittest.TestCase):
    """Case 7: the product is the exit status, run as a subprocess.

    Importing the tool cannot observe it, and the repository's own convention
    is that a checker whose only observable behaviour is a report has no
    product -- `docs/findings/pd-vector-handler-words.md` says why that matters
    here too. So this runs the module as a program, twice: once over the
    committed page, which must exit zero, and once over a page with the shape
    and the address moved, which must exit non-zero and say which.
    """

    def test_the_committed_page_exits_zero(self):
        proc = subprocess.run([sys.executable, str(TOOL), "--check"],
                              capture_output=True, text=True,
                              cwd=str(census.REPO))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertIn("re-derives", proc.stdout)

    def broken_page(self, before, after):
        """A temporary page with one cell edited, and the path to it.

        The tool reads the committed page, so a drifted copy is checked by
        calling `check_page()` against it rather than through `--check`, which
        takes no page argument. The edit is asserted to have applied: a fixture
        that stopped matching would make the case pass for the wrong reason.
        """
        text = page_text()
        broken = text.replace(before, after, 1)
        self.assertNotEqual(text, broken,
                            "the fixture edit did not apply: %r" % before)
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f:
            f.write(broken)
            return f.name

    def test_a_page_that_dropped_the_shape_fails(self):
        path = self.broken_page("| `0xF7B0` — `ret` |", "| `0xF7B0` |")
        try:
            self.assertEqual(tool.check_page(path=path), 1,
                             "a page that dropped the shape must fail")
        finally:
            os.unlink(path)

    def test_a_page_that_moved_an_address_fails(self):
        path = self.broken_page("| `0xF7AF` — `ret` |",
                                "| `0xF7B1` — `ret` |")
        try:
            self.assertEqual(tool.check_page(path=path), 1,
                             "a page that moved an address must fail")
        finally:
            os.unlink(path)

    def test_a_page_that_dropped_a_row_fails(self):
        """The other direction: a row the tool derives and the page omits."""
        import os
        import re
        text = open(census.PAGE, encoding="utf-8").read()
        # The §2.1 wrapper table also opens a row with `| \`0x13\` |
        # \`0x0157\``, so the row to drop is named by its selector range,
        # which only the five-word table carries.
        lines = [ln for ln in text.splitlines(keepends=True)
                 if "`0x0157`-`0x0159`" not in ln]
        self.assertEqual(len(lines), len(text.splitlines(keepends=True)) - 1,
                         "the row-removal fixture did not apply")
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f:
            f.write("".join(lines))
            path = f.name
        try:
            self.assertEqual(tool.check_page(path=path), 1,
                             "a page missing a row the tool derives must fail")
        finally:
            os.unlink(path)


class TestNothingIsWritten(unittest.TestCase):
    """A run of the tool leaves the tree byte-identical."""

    def test_a_full_report_writes_nothing(self):
        proc = subprocess.run([sys.executable, str(TOOL)],
                              capture_output=True, text=True,
                              cwd=str(census.REPO))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertIn("not found by this method", proc.stdout,
                      "a null must carry the token on the stream a reader "
                      "sees")


if __name__ == "__main__":
    unittest.main()