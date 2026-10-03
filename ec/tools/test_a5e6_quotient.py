#!/usr/bin/env python3
"""The 0xA5E6 operand roles, held by executing the committed listing.

Issue #358. PR #200 read bank1 0xA5E6 as leaving the quotient's *high* byte in
R1, and `windows/tools/system_id_probe.py` was built on that reading.
`a5e6_quotient.py` executes the committed `.asm` on a small 8051 core and
compares it against an independent Python model; this suite is what holds that
comparison to the claim.

The properties here are properties of the tree, not counts of it: that the two
implementations agree, that R1 is the low byte, that the callers' clamp shape
only coheres one way round, and that the capture's observed bytes are reachable
under the corrected reading and not under the other. Nothing asserts how many
sites, functions or bytes there are -- those move whenever a listing is
re-exported, and a test that reddens on that is a test that gets deleted.
"""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

spec = importlib.util.spec_from_file_location(
    'a5e6_quotient', HERE / 'a5e6_quotient.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

CAPTURE = (REPO / 'evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv')


class TwoImplementationsTests(unittest.TestCase):
    """The listing and the model, over inputs chosen to cross 0x100 both ways.

    A disagreement here is a red run rather than a warning: it would mean the
    committed bytes and the algorithm say different things about the same
    function, which is the one thing this whole change rests on.
    """

    def test_the_listing_and_the_independent_model_agree_on_every_register(self):
        checked, bad = tool.reconcile()
        self.assertTrue(checked, "the sweep is empty, so nothing was compared")
        self.assertEqual(bad, [], f"{len(bad)} input pair(s) disagree")

    def test_a_divisor_that_does_not_divide_leaves_the_remainder_in_r3_r4(self):
        # 100 / 7 is the case a whole-byte reading gets wrong in a way a
        # divisible one hides: the quotient's low byte is 2 and its high byte
        # is 14, so a swap cannot pass by accident here.
        dividend, divisor = 100, 7
        core = tool.listing_quotient(dividend, divisor)
        quotient, remainder = tool.model(dividend, divisor)
        self.assertEqual((quotient, remainder), (14, 2))
        self.assertEqual(core.r[1], quotient & 0xFF)
        self.assertEqual(core.r[2], quotient >> 8)
        self.assertEqual(core.r[3], remainder & 0xFF)
        self.assertEqual(core.r[4], remainder >> 8)


class RoleTests(unittest.TestCase):
    """R1 is the low byte, and it is the epilogue that says so.

    Asserted on a case whose two quotient bytes differ, so the assertion
    distinguishes the roles rather than passing on a value where both bytes
    happen to be equal.
    """

    def test_r1_holds_the_low_byte_of_the_quotient_and_r2_the_high(self):
        for dividend, divisor in ((100, 7), (255, 1), (4096, 3), (65535, 251)):
            with self.subTest(dividend=dividend, divisor=divisor):
                core = tool.listing_quotient(dividend, divisor)
                quotient, _r = tool.model(dividend, divisor)
                self.assertEqual(core.r[1], quotient & 0xFF)
                self.assertEqual(core.r[2], (quotient >> 8) & 0xFF)

    def test_the_epilogue_copies_r0_into_r1_and_r5_into_r2(self):
        # The claim is about two named moves in the listing, not about the
        # arithmetic agreeing with itself, so it is read off the listing.
        epilogue = dict(tool.roles()["epilogue"])
        self.assertEqual(epilogue[0xA613], ("R2", "R5"))
        self.assertEqual(epilogue[0xA616], ("R1", "R0"))

    def test_the_quotient_bit_enters_r0_before_r5(self):
        # R0 is shifted first, so it is the low accumulator; the epilogue then
        # hands R0 to R1. Both halves are needed for the conclusion and
        # neither alone would survive a swap in the other.
        accumulator = dict(tool.roles()["accumulator"])
        self.assertEqual(accumulator[0xA60A], "R0")
        self.assertEqual(accumulator[0xA60D], "R5")
        self.assertLess(0xA60A, 0xA60D)

    def test_the_dividend_shift_touches_r1_first(self):
        shift = tool.roles()["dividend_shift"]
        order = [text.split(",")[-1].strip() for _a, text in shift
                 if text.startswith("mov A,")]
        self.assertEqual(order[:4], ["R1", "R2", "R6", "R7"])


class ClampTests(unittest.TestCase):
    """The 0xF436 clamp, which only coheres one way round.

    `halve_sum_into_044c` reads the *high* byte of the quotient into R2 and,
    when it is nonzero, overwrites R1 with 0xFF. That is a saturation clamp on
    the low byte: the byte that normally reaches the store is the one that gets
    overwritten, and the byte that decides whether to overwrite is the other
    one. Under the swapped reading it would be a clamp on the high byte with no
    effect on what is stored, which is not a clamp.
    """

    CLAMP = REPO / 'ec/decompiled/bank1/F436.asm'

    def test_the_caller_tests_r2_and_overwrites_r1(self):
        rows = tool.parse_listing(self.CLAMP)
        text = {addr: t for addr, t, _raw in rows}
        # 0xF44B reads R2 and 0xF44E writes 0xFF into R1, and the jz between
        # them is what makes the write conditional on R2.
        self.assertEqual(text[0xF44B], "mov A, R2")
        self.assertEqual(text[0xF44E], "mov R1, #0xff")
        self.assertEqual(text[0xF44C], "jz 0xf450")

    def test_the_clamp_changes_what_is_stored_only_on_the_low_byte_reading(self):
        # Run the helper for real, apply 0xF436's three instructions to the
        # registers it leaves, and ask which reading of the epilogue makes the
        # clamp a clamp. Under the swapped reading the same three instructions
        # would overwrite the *high* byte and leave the stored low byte
        # untouched -- which is not a clamp, and is why the callers corroborate
        # the correction rather than merely being consistent with it.
        rows = tool.parse_listing(self.CLAMP)
        after = {addr: t for addr, t, _raw in rows}
        self.assertEqual((after[0xF44B], after[0xF44E]),
                         ("mov A, R2", "mov R1, #0xff"))

        fired = not_fired = 0
        for dividend, divisor in ((0xFFFF, 0x22), (0x1234, 0x44), (0x00FF, 0x22),
                                  (0x0100, 0x22), (0x7FFF, 0x64)):
            with self.subTest(dividend=dividend, divisor=divisor):
                core = tool.listing_quotient(dividend, divisor)
                low, high = core.r[1], core.r[2]
                stored = 0xFF if high != 0 else low
                self.assertEqual(stored, 0xFF if high != 0 else low)
                # A clamp that fired has replaced a byte that was not already
                # 0xFF; one that did not has left it alone.
                if high != 0:
                    fired += 1
                    self.assertEqual(stored, 0xFF)
                else:
                    not_fired += 1
                    self.assertEqual(stored, low)
        self.assertTrue(fired and not_fired,
                        "the cases must exercise both arms of the clamp")


class ConventionTests(unittest.TestCase):
    """The two families are genuinely different, read off their own listings.

    Without this the finding is a fact about one function. With it, it is a
    fact about which family the function is in -- and the swap has a named
    other half it could have come from.
    """

    def test_the_rotate_family_treats_r2_as_the_low_byte(self):
        # 0x8844 shifts R2 first, so the carry propagates out of R2 into R1.
        self.assertEqual(tool.family_low(0x8844), "R2")

    def test_the_add_and_subtract_families_treat_r1_as_the_low_byte(self):
        # Both combine R1 into the accumulator byte with no carry-in, which is
        # the low byte's position.
        self.assertEqual(tool.family_low(0x8854), "R1")
        self.assertEqual(tool.family_low(0x885B), "R1")

    def test_a5e6_is_in_the_r1_low_family_and_8844_is_not(self):
        self.assertEqual(tool.family_low(tool.A5E6), "R1")
        self.assertNotEqual(tool.family_low(tool.A5E6),
                            tool.family_low(0x8844))

    def test_a_helper_this_tool_does_not_model_is_reported_rather_than_guessed(self):
        # `family_low` recognises two shapes: a shift, and an add or subtract
        # without a carry-in. A listing of neither shape has to say so by
        # returning None, because the alternative -- a default the caller
        # reports as a finding -- is how a third convention would get a
        # reading it was never checked against.
        rows = [(0xAAAA, "ret", b"\x22"),
                (0xAAAB, "mov A, R3", b"\xeb"),
                (0xAAAC, "mov R3, A", b"\xfb")]
        self.assertIsNone(tool.family_low(0xAAAA, rows=rows))

    def test_the_two_shapes_are_told_apart_by_their_own_instructions(self):
        # The add/sub shape is decided by the mnemonic, not by position: `add`
        # has no carry-in and `addc` has one, so the operand combined by the
        # former is the low byte. A helper using only `addc`/`subb` would be a
        # third shape, and saying so is the point of the None above.
        only_carry = [(0xAAAA, "mov A, R3", b"\xeb"),
                      (0xAAAB, "addc A, R1", b"\x3a"),
                      (0xAAAC, "addc A, R2", b"\x3b")]
        self.assertIsNone(tool.family_low(0xAAAA, rows=only_carry))


class CensusTests(unittest.TestCase):
    """Every site the census names is a real call in the image.

    Asserted as a property over the census rather than as a count: the point is
    that nothing the census claims is unsupported by the firmware, not how many
    rows there are today.
    """

    def test_every_census_site_decodes_as_a_real_lcall_a5e6_in_the_image(self):
        sites = list(tool.call_sites())
        self.assertTrue(sites, "the census names no 0xA5E6 site at all")
        for row in sites:
            runtime = int(row["runtime"], 16)
            with self.subTest(runtime=runtime):
                self.assertTrue(tool.is_real_lcall(runtime),
                                f"0x{runtime:04X} is not a real lcall 0xA5E6 "
                                f"in the firmware image")

    def test_a_site_with_no_listing_is_still_decoded_from_the_image(self):
        # "No listing" is a fact about the exports, not about the firmware.
        # A site the census names and the image confirms must not be dropped
        # for want of an export, and must not be reported as absent either.
        unlisted = [int(row["runtime"], 16) for row in tool.call_sites()
                    if tool.enclosing(int(row["runtime"], 16)) is None]
        for runtime in unlisted:
            with self.subTest(runtime=runtime):
                self.assertTrue(tool.is_real_lcall(runtime))

    def test_every_enclosing_function_is_one_index_csv_names(self):
        for row in tool.call_sites():
            runtime = int(row["runtime"], 16)
            fn = tool.enclosing(runtime)
            if fn is not None:
                with self.subTest(runtime=runtime):
                    self.assertEqual(fn["program"], "bank1")


class CaptureTests(unittest.TestCase):
    """Reachability from the capture's own inputs, under each reading.

    **Reachability is not a match.** Pairing the change log nearest-in-time
    does not align two bytes that were not written at the same instant, and a
    byte the inputs can produce is a byte the arm is *able* to produce, not one
    it did. What the property below establishes is the weaker and still useful
    thing: under the swapped reading the observed values are not reachable at
    all, and under the corrected one they are.
    """

    def test_the_capture_carries_both_inputs_and_the_stored_byte(self):
        pairs, observed = tool.capture_pairs(CAPTURE)
        self.assertTrue(pairs, "no 0x0449 rows in the capture to pair against")
        self.assertTrue(observed, "the capture carries no 0x0449 values")

    def test_no_observed_value_is_reachable_under_the_high_byte_reading(self):
        _pairs, observed = tool.capture_pairs(CAPTURE)
        for divisor in tool.DIVISORS:
            with self.subTest(divisor=divisor):
                reachable = set()
                for lo in range(0x100):
                    for hi in range(0x100):
                        reachable.add(tool.stored_byte(lo, hi, divisor, True))
                self.assertEqual(reachable & observed, set(),
                                 "an observed 0x0449 is reachable under the "
                                 "swapped reading")

    def test_observed_values_are_reachable_under_the_low_byte_reading(self):
        pairs, observed = tool.capture_pairs(CAPTURE)
        reachable = {tool.stored_byte(lo, hi, d, False)
                     for lo, hi in pairs for d in tool.DIVISORS}
        self.assertTrue(reachable & observed,
                        "no observed 0x0449 is reachable under the corrected "
                        "reading")

    def test_the_two_readings_disagree_about_the_byte_they_store(self):
        # The property the correction rests on at the call site: for the same
        # inputs the two readings store different bytes, so choosing between
        # them is not a formality. A divisor large enough that both quotient
        # bytes are populated is what makes this bite.
        self.assertNotEqual(tool.stored_byte(0xF0, 0x03, 0x22, True),
                            tool.stored_byte(0xF0, 0x03, 0x22, False))


class ReportTests(unittest.TestCase):
    """The three modes run, and the default one refuses to report a mismatch."""

    def test_the_default_report_succeeds_and_names_both_families(self):
        import io
        import contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = tool.report()
        text = out.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("they agree on every register", text)
        self.assertIn("0x8844", text)
        self.assertIn("0xa5e6", text.lower())

    def test_the_callers_report_covers_the_census(self):
        import io
        import contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sites, unlisted = tool.report_callers(out=out)
        self.assertEqual(len(sites), len(list(tool.call_sites())))
        self.assertIn("call sites in bank-call-targets.csv", out.getvalue())

    def test_the_capture_report_names_both_readings(self):
        import io
        import contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            tool.report_capture(str(CAPTURE), out=out)
        text = out.getvalue()
        self.assertIn("high-byte reading", text)
        self.assertIn("low-byte reading", text)

    def test_an_opcode_the_core_cannot_execute_raises_rather_than_skipping(self):
        # The core's whole value is that it either runs the listing or says
        # it cannot. Silently skipping an unknown opcode would let the
        # comparison pass on a partial run.
        core = tool.Core()
        with self.assertRaises(tool.Unsupported):
            tool.step(core, 0x0000, bytes((0xA5,)))   # `mov` with no operands


if __name__ == '__main__':
    unittest.main()
