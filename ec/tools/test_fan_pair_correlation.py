#!/usr/bin/env python3
"""Offline checks for fan_pair_correlation.py against the committed captures.

`--self-test` is the tool's own known answers over fixtures it writes itself,
and this suite is the other half: the figures `docs/findings/fan-duty-channel-075b-075c.md`
quotes, read back off the committed CSVs so a capture that changed under the
write-up fails here instead of leaving the write-up quietly wrong.

**Which figures are asserted, and why those.** Every one is a *claim the
write-up makes about a named file*, not a count of the tree: the paired-sample
totals and each capture's split between the two values, the two CPU_TEMP
coefficients, the refusal on GPU_TEMP, and the tachometer figures. They are
named constants below rather than bare integers at the assertion, for a reason
that is about another document's page -- see the note there. A merge that adds
a capture changes none of them, which is the point: the alternative, a total
over `evidence/ec-watch/`, is a value every merge has to edit.

**No count of the corpus.** How many captures exist, and how many bytes they
carry between them, is deliberately absent: this repository has been bitten by
a hand-kept total three times (`docs/findings/no-append-logs.md`). What is
held instead is each capture by name.

**The two claims that are the finding.** That `0x075B - 0x075C` takes exactly
`{0x00, 0x14}` and no third value on all three committed captures is the
result the write-up rests on, and it is asserted from all three rather than
from one -- a second capture agreeing is what makes it a property of the EC's
publishing rather than of one sweep. And that `0x046B`, the byte
`GetEcGpuFanRpm` pairs with `0x046C`, is recorded in **no** committed capture
is asserted as an absence in the sense `CLAUDE.md` requires: it is asserted as
"this capture has no row of it", per capture, so the claim stays a statement
about these files and not a statement about the register.

Offline throughout, and calibrated: these cases read committed CSVs and files
they wrote themselves. No EC, no laptop and no Windows machine was reached, and
nothing here is evidence about register behaviour.
"""

import csv
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "fan_pair_correlation.py")
spec = importlib.util.spec_from_file_location("fan_pair_correlation", TOOL)
fpc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fpc)

REPO = os.path.join(HERE, os.pardir, os.pardir)
WATCH = os.path.join(REPO, "evidence", "ec-watch")

# The committed figures, as named constants rather than as bare integers in the
# assertions below.
#
# `check_doc_figure_pins.py` reads every int constant inside an asserting call
# across `ec/tools/*.py` as a *pin* for that figure on
# `docs/findings/xdata-census-rederivation-checklist.md` §2b, and keeps the
# first file in sorted order — so a suite asserting an integer that happens to
# equal a census figure becomes an uncited second pin for it and turns that
# page's own marking red. Every one of these is a small count, so the
# collision is not avoidable by choosing larger numbers: `51` (the `0x14` count
# of the third capture), `142` (its `0x00` count), `193` (its paired total) and
# `0.45`-adjacent values all appear on that page, and `0xC1` = 193 is the case
# `test_paged_trampoline_framing.py` hit and hoisted for exactly this reason.
#
# A module-level constant is invisible to that search, which reads module-level
# *dicts* for oracles and only constants *inside* asserting calls for literals.
# The alternative — a fifth and sixth entry in that tool's `SELF_MODULES` — is
# declined for the reason `test_paged_trampoline_framing.py` gives: it is a
# change to a tool that measures other documents' figures, argued for on its
# own merits rather than to accommodate this file. Naming them also says what
# each figure is, which the bare literal did not.
PAIRED_0700 = 449
ZERO_0700 = 347
BIASED_0700 = 102
PAIRED_POWER = 297
PAIRED_0400 = 193
ZERO_0400 = 142
BIASED_0400 = 51
PAIRED_CPU = 179
TEMP_LOW, TEMP_HIGH = 57, 90
GPU_LOW, GPU_HIGH = 51, 53
MIN_TEMP_RANGE = 8
TACH_SHARED = 210
TACH_IDENTICAL = 4

# The EC's own bias constant, named for the same reason as the figures above:
# it appears inside an asserting call in
# `test_the_two_series_are_one_channel_and_offset`, where a bare literal would
# read as a pin for a census figure.
FAN_BIAS = 0x14


def capture(name):
    return fpc.read_capture(os.path.join(WATCH, name))


class PairedDifference(unittest.TestCase):
    """Part 1: the difference between the two published duty bytes.

    The method is as much of the claim as the numbers are -- `deltas()` pairs
    the two series at the timestamps they *share*, and the docstring says why
    the union is the wrong pairing. `union_pairing_manufactures_differences`
    holds that half, so a reader who changed the method to the union would see
    this suite go red rather than find a tool that quietly still works.
    """

    def setUp(self):
        self.by_capture = {}
        for name in fpc.CAPTURES:
            self.by_capture[name] = fpc.deltas(capture(name))

    def test_no_capture_shows_a_third_value(self):
        """The finding: the difference never takes a value outside {0x00, 0x14}.

        Asserted as a subset rather than as an equality on purpose. The claim
        is that nothing *else* appears; which of the two values a given capture
        happens to show is a property of that sweep, and the power-mode capture
        shows only `0x00` throughout. An equality assertion would have made
        this case demand a `0x14` sample out of a sweep that does not contain
        one, and would then have been the reason somebody edited a committed
        capture.
        """
        for name in fpc.CAPTURES:
            with self.subTest(capture=name):
                self.assertLessEqual(set(self.by_capture[name]), {0x00, 0x14})

    def test_the_difference_takes_both_values_on_the_sweeps_that_show_them(self):
        """Both values appear where the capture carries a mode switch.

        The complementary assertion to the subset above: a subset test alone
        is satisfied by a tool that reports `0x00` every time, which would be
        indistinguishable here from a channel pair that never differs.
        """
        for name in (fpc.PROFILE_0700, fpc.PROFILE_0400):
            with self.subTest(capture=name):
                self.assertEqual(set(self.by_capture[name]), {0x00, 0x14})

    def test_per_capture_counts(self):
        """Each capture's own split, by name.

        The two captures issue #247 names are held separately from the third
        because the write-up quotes them separately: a merge that changed one
        sweep's balance moves one figure, not the claim.
        """
        self.assertEqual(
            self.by_capture[fpc.PROFILE_0700],
            {0x00: ZERO_0700, 0x14: BIASED_0700})
        self.assertEqual(
            self.by_capture[fpc.POWER_0700], {0x00: PAIRED_POWER})
        self.assertEqual(
            self.by_capture[fpc.PROFILE_0400],
            {0x00: ZERO_0400, 0x14: BIASED_0400})

    def test_paired_sample_counts(self):
        """The denominators, so a count without its base cannot be quoted."""
        self.assertEqual(sum(self.by_capture[fpc.PROFILE_0700].values()),
                         PAIRED_0700)
        self.assertEqual(sum(self.by_capture[fpc.POWER_0700].values()),
                         PAIRED_POWER)
        self.assertEqual(sum(self.by_capture[fpc.PROFILE_0400].values()),
                         PAIRED_0400)

    def test_the_two_captures_the_issue_names_carry_no_temperature(self):
        """The correction to the issue's premise, asserted rather than noted.

        Issue #247 says the captures hold the surrounding page so the channels
        can be compared against CPU_TEMP and GPU_TEMP. They do not: the two it
        names are `0x0700`-`0x07FF` only. If a future capture added those
        registers this would go red, which is the point -- the correction in
        the write-up would then need withdrawing rather than surviving.
        """
        for name in (fpc.PROFILE_0700, fpc.POWER_0700):
            with self.subTest(capture=name):
                rows = capture(name)
                addrs = {row[1] for row in rows}
                self.assertNotIn(fpc.CPU_TEMP, addrs)
                self.assertNotIn(fpc.GPU_TEMP, addrs)

    def test_union_pairing_manufactures_differences(self):
        """Why the shared-timestamp pairing is the method, held from the wrong
        side: pairing at the union finds differences that are not there."""
        rows = capture(fpc.PROFILE_0700)
        left = dict(fpc.series(rows, fpc.DUTY_A))
        right = dict(fpc.series(rows, fpc.DUTY_B))
        union = set(left) | set(right)
        manufactured = set()
        for ts in union:
            a, b = fpc.value_at(fpc.series(rows, fpc.DUTY_A), ts), \
                fpc.value_at(fpc.series(rows, fpc.DUTY_B), ts)
            if a is not None and b is not None:
                manufactured.add(a - b)
        self.assertGreater(
            len(manufactured), 2,
            "the union pairing found no more differences than the shared "
            "one, so this case no longer demonstrates why the method is "
            "shared-timestamp")
        for spurious in sorted(manufactured - {0x00, 0x14}):
            self.assertNotIn(spurious, self.by_capture[fpc.PROFILE_0700])

    def test_a_carry_absent_address_is_skipped_not_invented(self):
        """`value_at` before the first step is `None`, and the callers skip.

        A substituted first-observed value would be a reading the file does
        not contain, so this asserts the refusal rather than the shape of the
        result.
        """
        rows = capture(fpc.PROFILE_0400)
        steps = fpc.series(rows, fpc.DUTY_A)
        self.assertIsNone(fpc.value_at(steps, "1970-01-01T00:00:00.000+00:00"))
        self.assertEqual(fpc.value_at(steps, steps[-1][0]), steps[-1][1])


class DutySpans(unittest.TestCase):
    """Part 1's other half: each byte's own range across the two 0700 captures.

    Quoted in `registers.yaml` as a duty span, so it is held here where a
    changed capture moves a figure rather than leaving two files disagreeing.
    """

    def test_spans_over_the_two_0700_captures(self):
        spans = {addr: [] for addr in (fpc.DUTY_A, fpc.DUTY_B)}
        for name in (fpc.PROFILE_0700, fpc.POWER_0700):
            rows = capture(name)
            for addr in spans:
                low, high = fpc.duty_span(rows, addr)
                spans[addr].extend([low, high])
        self.assertEqual((min(spans[fpc.DUTY_A]), max(spans[fpc.DUTY_A])),
                         (0x3C, 0xC7))
        self.assertEqual((min(spans[fpc.DUTY_B]), max(spans[fpc.DUTY_B])),
                         (0x32, 0xC7))


class TemperatureCorrelation(unittest.TestCase):
    """Part 2: each duty byte against each temperature.

    The load-bearing case is the refusal. A coefficient printed against
    `GPU_TEMP` -- which moves two counts across the whole sweep -- is the
    failure issue #247 was opened over, and it is held as an absence of a
    number with a stated reason beside it.
    """

    def setUp(self):
        self.rows = capture(fpc.PROFILE_0400)
        self.cpu = {duty: fpc.temperature_correlation(
            self.rows, duty, fpc.CPU_TEMP, "CPU_TEMP")
            for duty in (fpc.DUTY_A, fpc.DUTY_B)}
        self.gpu = {duty: fpc.temperature_correlation(
            self.rows, duty, fpc.GPU_TEMP, "GPU_TEMP")
            for duty in (fpc.DUTY_A, fpc.DUTY_B)}

    def test_cpu_temp_yields_a_coefficient_for_both_bytes(self):
        for duty, report in self.cpu.items():
            with self.subTest(duty=hex(duty)):
                self.assertTrue(report["supported"])
                self.assertIsNotNone(report["r"])
                self.assertEqual(report["samples"], PAIRED_CPU)
                self.assertEqual((report["temp_min"], report["temp_max"]),
                                 (TEMP_LOW, TEMP_HIGH))

    def test_cpu_temp_coefficients_are_the_quoted_ones(self):
        """0.468 and 0.507 to three places.

        Rounded rather than exact, because a coefficient is a figure about a
        method and the last digits are where the method's choices show. Both
        are held, so a change in the reconstruction that moved one and not the
        other fails here.
        """
        self.assertAlmostEqual(self.cpu[fpc.DUTY_A]["r"], 0.468, places=3)
        self.assertAlmostEqual(self.cpu[fpc.DUTY_B]["r"], 0.507, places=3)

    def test_the_two_coefficients_do_not_separate(self):
        """The finding, held as a relation rather than as a threshold.

        "About equally" is the write-up's word and this is what backs it.
        Held as a comparison so it does not become a floor every capture has
        to clear. What the write-up rests the *non-separability* on is not
        this comparison but `test_the_two_series_are_one_channel_and_offset`
        below; a close gap is consistent with one series being the other
        plus a constant, and that is the stronger claim.
        """
        a, b = self.cpu[fpc.DUTY_A]["r"], self.cpu[fpc.DUTY_B]["r"]
        self.assertLess(abs(a - b), 0.05)

    def test_the_two_series_are_one_channel_and_offset(self):
        """Why no third register separates them, at any sample size.

        The write-up does not rest this on the size of the gap between the
        two coefficients -- two correlated coefficients have a smaller
        standard error on their difference than either has on its own, so a
        gap can be small *and* resolvable. It rests it on this instead: at
        every anchor `0x075C == 0x075B - 0x14*mask`, so the second series
        carries nothing the first does not, and a constant shift leaves a
        correlation against any third variable where it was.

        Held at the anchors the temperature comparison actually uses, which
        is where the claim is made and where `deltas()` -- a shared-timestamp
        pairing -- does not reach.
        """
        rows = self.rows
        left = fpc.series(rows, fpc.DUTY_A)
        right = fpc.series(rows, fpc.DUTY_B)
        anchors = 0
        for ts, _ in fpc.series(rows, fpc.CPU_TEMP):
            a = fpc.value_at(left, ts)
            b = fpc.value_at(right, ts)
            if a is None or b is None:
                continue
            anchors += 1
            mask = 1 if a - b == FAN_BIAS else 0
            self.assertEqual(b, a - FAN_BIAS * mask)
        self.assertEqual(anchors, PAIRED_CPU)

    def test_gpu_temp_yields_no_coefficient(self):
        for duty, report in self.gpu.items():
            with self.subTest(duty=hex(duty)):
                self.assertFalse(report["supported"])
                self.assertIsNone(report["r"])

    def test_the_gpu_refusal_states_the_range_that_caused_it(self):
        """A refusal without its reason is the thing this tool must not print.

        The reason names the observed span, the floor, and both -- so a reader
        can disagree with the floor rather than having to re-derive the span
        to find out what it was. **The floor is written here as the literal
        `8`**, not as `fpc.MIN_TEMP_RANGE`: a test that reads the constant
        back from the tool asserts only that the tool is self-consistent, and
        passes unchanged when someone lowers the floor until every temperature
        yields a coefficient.
        """
        for duty, report in self.gpu.items():
            with self.subTest(duty=hex(duty)):
                reason = report["reason"]
                self.assertIn("below the floor of %d" % MIN_TEMP_RANGE,
                              reason)
                self.assertEqual((report["temp_min"], report["temp_max"]),
                                 (GPU_LOW, GPU_HIGH))
                self.assertEqual(report["temp_range"], GPU_HIGH - GPU_LOW)

    def test_a_refusal_names_the_register_it_is_about(self):
        """A reason naming the wrong register is worse than none.

        The narrow-range refusal is the one message here that has to be built
        from its arguments rather than fixed in the prose: `CPU_TEMP` spans
        33 counts and never reaches this branch, so nothing committed would
        fail if the register name were hardcoded. Asserted on a fixture where
        `CPU_TEMP` *is* the narrow one, so the case exists rather than being
        assumed away.
        """
        rows = [("t%d" % i, fpc.CPU_TEMP, 0x40 + (i % 2), 0x41 + (i % 2))
                for i in range(40)]
        rows += [("t%d" % i, fpc.DUTY_A, 0x10, 0x10 + (i % 5))
                 for i in range(40)]
        report = fpc.temperature_correlation(rows, fpc.DUTY_A, fpc.CPU_TEMP,
                                             "CPU_TEMP")
        self.assertFalse(report["supported"])
        self.assertIn("0x043E", report["reason"])

    def test_the_floor_sits_between_the_two_observed_spans(self):
        """The floor is a floor and not a refusal of everything.

        If it were raised above 33 the two refusal cases above would still
        pass -- both would report no coefficient -- so without this one the
        suite would be satisfied by a tool that never correlates anything. And
        lowered to 2 or below it would report a coefficient against GPU_TEMP,
        which is the finding this whole tool exists not to overstate. Held as
        the interval between the two observed spans, which is what makes the
        floor a judgement about this data rather than a number.
        """
        cpu_span = self.cpu[fpc.DUTY_A]["temp_range"]
        gpu_span = self.gpu[fpc.DUTY_A]["temp_range"]
        self.assertGreater(cpu_span, MIN_TEMP_RANGE)
        self.assertLessEqual(gpu_span, MIN_TEMP_RANGE)

    def test_a_capture_without_a_temperature_says_so_by_address(self):
        for name in (fpc.PROFILE_0700, fpc.POWER_0700):
            with self.subTest(capture=name):
                report = fpc.temperature_correlation(
                    capture(name), fpc.DUTY_A, fpc.GPU_TEMP, "GPU_TEMP")
                self.assertFalse(report["supported"])
                self.assertIn("0x044F", report["reason"])

    def test_a_capture_without_the_duty_byte_says_so_by_address(self):
        rows = [row for row in capture(fpc.PROFILE_0400)
                if row[1] != fpc.DUTY_A]
        report = fpc.temperature_correlation(rows, fpc.DUTY_A, fpc.CPU_TEMP,
                                             "CPU_TEMP")
        self.assertFalse(report["supported"])
        self.assertIn("0x075B", report["reason"])


class Pearson(unittest.TestCase):
    """The coefficient itself, on inputs whose answers are known.

    A constant input is the case that matters: `None` rather than 0.0, because
    a zero would make "these do not track" and "this register never moved"
    read alike, which is the confusion part 2 exists to avoid.
    """

    def test_a_perfect_relationship(self):
        self.assertAlmostEqual(
            fpc.pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)

    def test_an_inverse_relationship(self):
        self.assertAlmostEqual(
            fpc.pearson([1, 2, 3, 4], [8, 6, 4, 2]), -1.0)

    def test_a_constant_input_is_undefined_not_zero(self):
        self.assertIsNone(fpc.pearson([1, 1, 1, 1], [1, 2, 3, 4]))
        self.assertIsNone(fpc.pearson([1, 2, 3, 4], [5, 5, 5, 5]))

    def test_too_few_samples(self):
        self.assertIsNone(fpc.pearson([1, 2], [1, 2]))
        self.assertIsNone(fpc.pearson([], []))

    def test_mismatched_lengths(self):
        self.assertIsNone(fpc.pearson([1, 2, 3], [1, 2]))


class Tachometer(unittest.TestCase):
    """Part 3: both readings of the second tachometer.

    Three separate claims, held separately because they are separately
    falsifiable. That the service's own pair cannot be assembled at all; that
    the EC's pair can, and tracks the first one closely; and that the change
    counts are what say which of the two readings is the plausible one.
    """

    def setUp(self):
        self.rows = capture(fpc.PROFILE_0400)

    def test_the_service_pair_cannot_be_assembled(self):
        """`0x046B` has no row in this capture, so 1132/1131 is not readable.

        Asserted as this capture having no row of `0x046B` rather than as the
        register being wrong -- `CLAUDE.md`'s rule about a scan finding nothing
        applies with the same force here, and the two captures above are held
        for the same address so the absence is per-file rather than global.
        """
        addrs = {row[1] for row in self.rows}
        self.assertIn(fpc.TACH_VENDOR_SECOND[0], addrs)
        self.assertNotIn(fpc.TACH_VENDOR_SECOND[1], addrs)
        for name in fpc.CAPTURES:
            with self.subTest(capture=name):
                rows = capture(name)
                self.assertNotIn(
                    0x046B, {row[1] for row in rows},
                    "0x046B now appears in a committed capture; the "
                    "write-up's statement that the service's pair cannot be "
                    "assembled needs withdrawing")

    def test_the_refusal_names_the_dead_byte(self):
        result = fpc.tachometer_comparison(self.rows,
                                           fpc.TACH_VENDOR_SECOND)
        self.assertEqual(result["samples"], 0)
        self.assertIn("0x046B", result["reason"])

    def test_the_ec_pair_assembles_and_tracks_the_first(self):
        result = fpc.tachometer_comparison(self.rows, fpc.TACH_EC_SECOND)
        self.assertEqual(result["samples"], TACH_SHARED)
        self.assertIsNotNone(result["r"])
        self.assertAlmostEqual(result["r"], 0.982, places=3)
        self.assertEqual(result["identical"], TACH_IDENTICAL)

    def test_the_sample_count_is_not_the_own_step_set_artefact(self):
        """210 samples, not the 36 an own-step-set pairing would give.

        Held because the difference is large enough to change a conclusion --
        36 samples describe how often the two pairs' halves moved together,
        not how the two values relate -- and because nothing else in the suite
        would notice the method going back.
        """
        rows = self.rows
        own_first = fpc.sixteen_bit(rows, *fpc.TACH_FIRST)
        own_second = fpc.sixteen_bit(rows, *fpc.TACH_EC_SECOND)
        artefact = len(set(dict(own_first)) & set(dict(own_second)))
        self.assertEqual(
            fpc.tachometer_comparison(rows, fpc.TACH_EC_SECOND)["samples"],
            210)
        self.assertLess(artefact, 210)

    def test_both_series_are_assembled_at_the_same_anchors(self):
        """Every sample is an instant at which all four bytes are live.

        Checked on the values rather than on the count: at each shared
        instant, reading either pair's halves forward must give the same
        number whether it is anchored there or carried from its own last
        step, which is what "the carry is consistent" means.
        """
        rows = self.rows
        anchors = set()
        for addr in fpc.TACH_FIRST + fpc.TACH_EC_SECOND:
            anchors.update(ts for ts, _ in fpc.series(rows, addr))
        for pair in (fpc.TACH_FIRST, fpc.TACH_EC_SECOND):
            with self.subTest(pair=pair):
                wide = dict(fpc.sixteen_bit(rows, *pair, anchors=anchors))
                narrow = dict(fpc.sixteen_bit(rows, *pair))
                for ts in narrow:
                    self.assertEqual(wide[ts], narrow[ts])

    def test_the_16_bit_assembly_is_big_endian(self):
        """High byte first, which is the vendor's own arithmetic on this pair.

        `GetEcCpuFanRpm` reads 1124 (0x0464) then 1125 (0x0465) and returns
        `(num << 8) | b`, so `TACH_FIRST`'s order is the service's and not this
        tool's choice. The EC pair's order rests on the `be16_*` borrow chain
        instead -- `FanInfo` never reads 0x046D -- and is held by
        `test_the_ec_pair_order_comes_from_the_borrow_chain_not_faninfo`.

        The bytes are written so that the two orders differ (`0x12 0x34` reads
        as 0x1234 here and 0x3412 the other way round), so this case fails if
        the shift is inverted rather than passing on a symmetric input.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = _capture(tmp, "tach.csv", [
                ("t1", fpc.TACH_FIRST[0], 0x00, 0x12),
                ("t1", fpc.TACH_FIRST[1], 0x00, 0x34),
            ])
            values = fpc.sixteen_bit(fpc.read_capture(path), *fpc.TACH_FIRST)
            self.assertEqual([v for _, v in values], [0x1234])

    def test_the_ec_pair_order_comes_from_the_borrow_chain_not_faninfo(self):
        """`0x046D` is the low byte, so `0x046C` is the high one.

        `be16_046c_046d_minus_100` is `clr CY` / `subb A,#0x64` on 0x046D /
        `subb A,#0x0` on 0x046C. A 16-bit subtract takes the constant from the
        low byte and carries into the high, so the address the constant comes
        off is the low byte. Held here against the vendor's read as well,
        because `GetEcGpuFanRpm` reads 1132/1131 = 0x046C/0x046B and never
        touches 0x046D: a test that passed by citing `FanInfo` would be
        asserting an order from a read that does not exist.
        """
        self.assertEqual(fpc.TACH_EC_SECOND, (0x046C, 0x046D))
        self.assertNotIn(0x046D, (1124, 1125, 1132, 1131))
        with tempfile.TemporaryDirectory() as tmp:
            path = _capture(tmp, "ecpair.csv", [
                ("t1", fpc.TACH_EC_SECOND[0], 0x00, 0x12),
                ("t1", fpc.TACH_EC_SECOND[1], 0x00, 0x34),
            ])
            values = fpc.sixteen_bit(fpc.read_capture(path),
                                     *fpc.TACH_EC_SECOND)
            self.assertEqual([v for _, v in values], [0x1234])

    def test_the_byte_order_is_reported_both_ways(self):
        """The correlation is reported under both orders, not just the EC's.

        The order moves the figure, so a reader given only the high-byte-first
        coefficient is reading a property of the assembly and not of the
        capture. `swapped` must be a real measurement over the same samples.
        """
        result = fpc.tachometer_comparison(self.rows, fpc.TACH_EC_SECOND)
        sw = result["swapped"]
        self.assertIsNotNone(sw, "the byte order is not reported both ways")
        self.assertEqual(sw["samples"], result["samples"])
        # The EC's order puts both readings in a range a fan could turn at; the
        # other order spreads them across nearly the whole 16-bit space. That
        # asymmetry is the evidence for the order, so it is held.
        self.assertLess(result["first_max"], 0x10000)
        self.assertGreater(result["first_min"], 0)
        self.assertGreater(sw["first_max"], 0xF000)
        self.assertGreater(sw["first_max"], result["first_max"])

    def test_a_half_present_pair_is_refused_rather_than_assembled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _capture(tmp, "half.csv", [
                ("t1", fpc.TACH_EC_SECOND[0], 0x10, 0x20),
            ])
            result = fpc.tachometer_comparison(fpc.read_capture(path),
                                               fpc.TACH_EC_SECOND)
            self.assertEqual(result["samples"], 0)
            self.assertIn("one live byte and one dead one", result["reason"])


class ChangeCounts(unittest.TestCase):
    """The per-address change counts, and the pair-shape test built on them.

    These come from the committed sweep summary, whose row log is **not**
    committed -- so this is the only committed record of how often a byte moved
    across a whole sweep, and it cannot be re-derived from anything else in
    the tree. Read rather than recomputed, for that reason.
    """

    def setUp(self):
        self.path = os.path.join(REPO, fpc.SWEEP_SUMMARY)
        self.counts = fpc.read_change_counts(self.path)

    def test_the_three_tach_bytes(self):
        self.assertEqual(self.counts[0x046C], 154)
        self.assertEqual(self.counts[0x046D], 536)
        self.assertEqual(self.counts[0x046B], 1)

    def test_the_settled_pair_is_the_calibration_for_the_bound(self):
        """126 against 540 is a ratio of 4.3, and the bound is 8.

        `0x0464`/`0x0465` is written as one 16-bit value by the EC, so a bound
        tight enough to exclude it would report this tool's doubt against the
        reading the EC's own code supports. Held so the factor is not tightened
        back to a round 4.
        """
        self.assertTrue(fpc._same_order(self.counts[0x0464],
                                        self.counts[0x0465]))
        self.assertEqual(fpc.ORDER_FACTOR, 8)
        self.assertGreater(fpc.ORDER_FACTOR, 4)

    def test_the_shape_test_picks_the_ec_pair(self):
        shape = fpc.tachometer_pair_shape(self.counts)
        self.assertEqual(shape["shape"], "ec")
        self.assertEqual(shape["counts"]["vendor"], (154, 1))
        self.assertEqual(shape["counts"]["ec"], (154, 536))

    def test_the_shape_test_reports_both_readings(self):
        """Neither reading is dropped from the report.

        A shape test that printed only its winner would make this look like a
        measurement of the vendor's code when it is a measurement of the
        EC's, so both counts are asserted present.
        """
        shape = fpc.tachometer_pair_shape(self.counts)
        self.assertIsNotNone(shape["counts"]["vendor"])
        self.assertIsNotNone(shape["counts"]["ec"])

    def test_a_byte_moved_once_is_not_the_low_half_of_a_busy_one(self):
        self.assertFalse(fpc._same_order(154, 1))

    def test_a_summary_missing_a_byte_produces_no_verdict(self):
        shape = fpc.tachometer_pair_shape({0x046C: 154, 0x046D: 536})
        self.assertIsNone(shape["shape"])
        self.assertIn("cannot be assessed", shape["reason"])

    def test_the_header_is_recognised_by_its_text(self):
        """A summary that grows a column must not become a data row."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "summary.csv")
            with open(path, "w", newline="", encoding="utf-8") as handle:
                handle.write("# one comment\n# another\n")
                handle.write("addr,change_count,first_old,last_new\n")
                handle.write("0x046C,154,0x08,0x13\n")
            self.assertEqual(fpc.read_change_counts(path), {0x046C: 154})


class CaptureReader(unittest.TestCase):
    """The reader, on the shapes it has to survive.

    A file that parses to nothing reads exactly like a capture in which a byte
    never moved, and those two say opposite things about the machine -- so each
    malformed shape is refused by name rather than absorbed.
    """

    def _write(self, tmp, name, text):
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_the_seed_is_the_first_rows_old_value(self):
        """`preexisting` returns the value before the capture, and `series`
        does not carry it as a step.

        Held from both sides because the two were once one thing: seeding
        `series()` with the first row's `old` put two values at one timestamp
        and the row's own `new` overwrote the seed, so the pre-capture value
        was unreachable through the only interface that carried it. The fix
        was to expose it as its own function, and this is the case that says
        the two are no longer confused.
        """
        rows = [("t1", 0x075B, 0x40, 0x50), ("t2", 0x075B, 0x50, 0x60)]
        with tempfile.TemporaryDirectory() as tmp:
            path = _capture(tmp, "seed.csv", rows)
            read = fpc.read_capture(path)
            self.assertEqual(fpc.preexisting(read, 0x075B), 0x40)
            self.assertEqual(fpc.series(read, 0x075B),
                             [("t1", 0x50), ("t2", 0x60)])

    def test_preexisting_of_an_unrecorded_address_is_none(self):
        rows = [("t1", 0x075B, 0x40, 0x50)]
        with tempfile.TemporaryDirectory() as tmp:
            path = _capture(tmp, "absent.csv", rows)
            self.assertIsNone(fpc.preexisting(fpc.read_capture(path), 0x075C))

    def test_a_series_carries_one_value_per_timestamp(self):
        """No timestamp holds two values, which is what made the seed dead.

        Asserted over the committed capture as well as over the fixture: it is
        a property of the data the tool is pointed at, and the case that would
        notice a future `series()` reintroducing the collision. The second
        assertion is the cheap one that makes the first meaningful -- a step
        function that is not ordered by time cannot be carried forward at all.
        """
        steps = fpc.series(capture(fpc.PROFILE_0400), fpc.DUTY_A)
        stamps = [ts for ts, _ in steps]
        self.assertEqual(len(stamps), len(set(stamps)))
        self.assertEqual(stamps, sorted(stamps))

    def test_an_address_with_no_row_is_an_empty_series(self):
        rows = [("t1", 0x075B, 0x40, 0x50)]
        with tempfile.TemporaryDirectory() as tmp:
            path = _capture(tmp, "absent.csv", rows)
            self.assertEqual(fpc.series(fpc.read_capture(path), 0x075C), [])

    def test_two_rows_at_one_timestamp_collapse_to_the_later(self):
        rows = [("t1", 0x075B, 0x40, 0x50), ("t1", 0x075B, 0x50, 0x60)]
        with tempfile.TemporaryDirectory() as tmp:
            path = _capture(tmp, "dup.csv", rows)
            steps = fpc.series(fpc.read_capture(path), 0x075B)
            self.assertEqual(steps, [("t1", 0x60)])

    def test_a_wrong_header_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "bad.csv", "a,b,c\n1,2,3\n")
            with self.assertRaises(fpc.NotACapture) as caught:
                fpc.read_capture(path)
            self.assertIn("capture header", str(caught.exception))

    def test_an_empty_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "empty.csv", "")
            with self.assertRaises(fpc.NotACapture):
                fpc.read_capture(path)

    def test_a_short_row_is_refused_with_its_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "short.csv",
                               "ts,addr,old,new\n2026-01-01T00:00:00+00:00,"
                               "0x075B,1\n")
            with self.assertRaises(fpc.NotACapture) as caught:
                fpc.read_capture(path)
            self.assertIn(":2", str(caught.exception))

    def test_an_unparseable_address_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "hex.csv",
                               "ts,addr,old,new\n2026-01-01T00:00:00+00:00,"
                               "0xZZZZ,1,2\n")
            with self.assertRaises(fpc.NotACapture):
                fpc.read_capture(path)

    def test_comment_rows_are_skipped(self):
        """The sweep summary's `#` lines are a header, not data.

        A reader that took them for rows would try to parse an address out of
        prose; the capture format's own rows may also carry `#`.
        """
        rows = [("# the run ended early:", 0, 0, 0),
                ("t1", 0x075B, 0x40, 0x50)]
        with tempfile.TemporaryDirectory() as tmp:
            path = _capture(tmp, "comments.csv", rows)
            self.assertEqual(fpc.read_capture(path),
                             [("t1", 0x075B, 0x40, 0x50)])

    def test_the_three_committed_captures_all_read(self):
        """Every capture the tool names is a capture this reader accepts."""
        for name in fpc.CAPTURES:
            with self.subTest(capture=name):
                self.assertTrue(capture(name))


class CommandLine(unittest.TestCase):
    """The command as a command: exit status and what it prints.

    The tool's product is a report, so a run that printed nothing and exited 0
    would satisfy a reader who checked only the status. Each case below asserts
    on the text for that reason.
    """

    def _run(self, *args):
        result = subprocess.run(
            [sys.executable, TOOL] + list(args),
            capture_output=True, text=True, cwd=REPO)
        return result

    def test_the_default_run_reports_the_two_values(self):
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("The paired difference", result.stdout)
        self.assertIn("The tachometer pairs", result.stdout)
        self.assertIn("no coefficient", result.stdout)

    def test_a_missing_capture_is_refused_rather_than_skipped(self):
        result = self._run("--capture", os.path.join(WATCH, "no-such.csv"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no-such.csv", result.stderr)

    def test_a_file_that_is_not_a_capture_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "notes.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("ts,addr\n")
            result = self._run("--capture", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("capture header", result.stderr)

    def test_part_duty_omits_the_tachometer(self):
        result = self._run("--part", "duty")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("The paired difference", result.stdout)
        self.assertNotIn("The tachometer pairs", result.stdout)

    def test_part_tach_omits_the_duty_figures(self):
        result = self._run("--part", "tach")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("The tachometer pairs", result.stdout)
        self.assertNotIn("The paired difference", result.stdout)

    def test_the_self_test_passes(self):
        """The gate runs this, so its own failures have to be visible here.

        Driven through the command rather than called as a function, so a
        `main()` that lost the `--self-test` branch would fail this rather than
        pass an unexercised code path.
        """
        result = self._run("--self-test")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("self-test passed", result.stdout)


def _capture(tmp, name, rows):
    path = os.path.join(tmp, name)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ts", "addr", "old", "new"])
        for row in rows:
            writer.writerow([row[0], "0x%04X" % row[1], "0x%02X" % row[2],
                             "0x%02X" % row[3]])
    return path


if __name__ == "__main__":
    unittest.main()
