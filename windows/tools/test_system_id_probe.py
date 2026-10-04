#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

system_id_probe.py imports ecrw -- the fake below stands in for the whole module,
which is what lets the sweeps be scripted byte by byte. What the fake is for
now is that scriptability: `ecrw` imports anywhere
(`windows/tools/test_import_off_windows.py`).

The script is keyed on the sweep, not on a timestamp, so what a sample is
labelled is an assertion about the arithmetic -- which arm reproduces the
0x0449, and which divisor it implies against bit 6 -- and not about how many
sweeps a given hold happens to buy. Every value here is reachable: the
`unexplained` rows are the ones the model cannot place, which is the state the
committed capture is entirely in.
"""
import ast
import contextlib
import importlib.util
import inspect
import io
from pathlib import Path
import re
import sys
import tempfile
import textwrap
import threading
import unittest
from unittest.mock import patch

# One dict per sweep, in run order. Each is built so that a specific arm
# reproduces its 0x0449, and the quotient behind each is worked out in the
# comment so a reader can check a fixture without running anything:
#
#   0  current  0x07F8 = 2040 mA, the value BAT_CURRENT_MA was established
#               live at; / 100 = 20 = 0x0014, low byte 0x14. The high byte is
#               0x00, so this fixture is what a high-byte reading cannot
#               reproduce.
#   1  060c     masked pair 0x03F0 * 10 = 10080; / 0x22 = 296 = 0x0128 (low
#               byte 0x28) and / 0x44 = 148 = 0x0094 (low byte 0x94), so it
#               places under 0x22 alone -- and 0x0456 bit 6 is clear here,
#               which is the contradiction the implied divisor exists to catch
#   2  060c     an all-zero pair places under both divisors; bit 6 is set here
#   3  neither  one above the 0x22 arm's 0x28, and the current arm lands on
#               0x00 -- the near-miss that must not be snapped to the nearer arm
#   4  both     an all-zero current reading and an all-zero pair both produce
#               0x00. Under the swapped reading this bucket was trivially
#               reachable at every input, which is why the fixture below it is
#               built rather than searched for; see BothArmsFixtureTests.
SWEEPS = [
    {0x0456: 0x40, 0x060C: 0x00, 0x060D: 0x00, 0x0449: 0x14,
     0x0434: 0xF8, 0x0435: 0x07},
    {0x0456: 0x00, 0x060C: 0xF0, 0x060D: 0x03, 0x0449: 0x28,
     0x0434: 0x00, 0x0435: 0x07},
    {0x0456: 0x40, 0x060C: 0x00, 0x060D: 0x00, 0x0449: 0x00,
     0x0434: 0x00, 0x0435: 0x07},
    {0x0456: 0x80, 0x060C: 0xF0, 0x060D: 0x03, 0x0449: 0x29,
     0x0434: 0x00, 0x0435: 0x64},
    {0x0456: 0x40, 0x060C: 0x00, 0x060D: 0x00, 0x0449: 0x00,
     0x0434: 0x00, 0x0435: 0x00},
]


class FakeEc:
    """Returns SWEEPS[n] for sweep n, and stops the run after the last one.

    The sweep index is counted per address rather than per read, so a run
    with `--start` and its extra context range still lines up -- a read count
    would drift the moment the watch set was not six bytes long.

    The read gate pins the interleaving the mark test needs: on the first read
    of the last sweep the mark is allowed in, so it lands after the previous
    sample's row and before this one's. Without it "did the MARK row land
    between two sample rows" would be a race against the sweep timer.

    `write` is here so that a write path in the tool shows up as a failed
    assertion rather than an AttributeError.
    """

    def __init__(self, sweeps=SWEEPS):
        self.sweeps = sweeps
        self.seen = {}        # addr -> how many times it has been read
        self.read_addrs = []  # every address, in order, across all sweeps
        self.writes = []
        self.at_last = threading.Event()
        self.marked = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        sweep = self.seen.get(addr, 0)
        self.seen[addr] = sweep + 1
        if sweep == len(self.sweeps) - 1:
            self.at_last.set()
            self.marked.wait(5)
        if sweep >= len(self.sweeps):
            raise KeyboardInterrupt
        self.read_addrs.append(addr)
        # A `--start` range sweeps addresses the script does not cover, and
        # the arithmetic never looks at them; the six that matter are all
        # present, so a missing one shows up as a wrong label, not a 0x00.
        return self.sweeps[sweep].get(addr, 0x00)

    def write(self, addr, val):
        self.writes.append((addr, val))


class FakeStdin:
    """One mark, stamped once the sweep loop reaches the last sweep.

    The second readline() is the proof the mark is fully committed -- Marker
    only asks for another line after writing the previous one -- so that is
    where the sweep loop is released.
    """

    def __init__(self, ec, label):
        self._ec = ec
        self._label = label
        self._sent = False

    def readline(self):
        self._ec.at_last.wait(5)
        if not self._sent:
            self._sent = True
            return self._label + "\n"
        self._ec.marked.set()
        return ""


# The tool's own `from ecrw import ...` has to resolve, and the directory is the
# import root whether or not the runner was started from here.
sys.path.insert(0, str(Path(__file__).parent))

# The shared offline stand-in for `ecrw` (windows/tools/ecrw_fake.py), installed
# by assignment like the other suites in this directory do. It supplies the names
# the tool binds at import; `FakeEc` above, the one that scripts the sweeps, is
# patched over the probe's own `Ec` in each test below.
import ecrw_fake  # noqa: E402  (needs the sys.path entry above)
ecrw_fake.install()

spec = importlib.util.spec_from_file_location(
    'system_id_probe', Path(__file__).with_name('system_id_probe.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

# The reader a `ts,MARK,,label` row is written for, loaded by path the way
# `ec_watch.py`'s own `load_label_vocab` loads it, so the mark row this probe
# writes is asked of the reader that has to place it rather than of a split
# this file makes itself. The grader imports nothing outside the standard
# library and registers no `sys.modules` entry, so loading it here cannot
# change what the shared `ecrw` above resolves to for any other suite in this
# directory.
grader_path = Path(__file__).resolve().parents[2] / 'ec/tools' \
    / 'grade_0751_isolation.py'
grader_spec = importlib.util.spec_from_file_location('grade_0751_isolation',
                                                     grader_path)
grader = importlib.util.module_from_spec(grader_spec)
grader_spec.loader.exec_module(grader)


class ArithmeticTests(unittest.TestCase):
    """The model, checked against the listings it is read from."""

    def test_the_pair_is_little_endian_with_the_lower_address_in_the_low_byte(self):
        # 0x8886 puts [DPTR] in R1 and [DPTR+1] in R2, so 0x0434 is the low
        # byte. 2040 mA is 0x07F8, and read the other way round it would be
        # 0xF807 -- a different current entirely, and one that divides to a
        # different stored byte.
        self.assertEqual(probe.arm_current(0xF8 | 0x07 << 8), 0x14)
        self.assertNotEqual(probe.arm_current(0x07 | 0xF8 << 8), 0x14)

    def test_what_is_stored_is_the_quotients_low_byte(self):
        # 0xA5E6 returns the quotient low byte in R1 and 0xF3D7 stores R1, so
        # the stored byte is the low one. 2040 mA -- the value BAT_CURRENT_MA
        # was established live at -- divides to 20, and 20 is 0x14 rather than
        # the 0x00 a high-byte reading gives it. ec/tools/a5e6_quotient.py
        # establishes the direction by executing the listing.
        self.assertEqual(probe.arm_current(2040), 0x14)

    def test_the_stored_byte_is_the_low_one_wherever_the_bytes_differ(self):
        # The property behind the case above, over inputs whose quotient has
        # two different bytes: the stored byte is the low one. A high-byte
        # reading disagrees on every one of these, so the case cannot pass by
        # accident on an input where the two bytes happen to be equal.
        for current_ma in (25600, 51200, 65535, 100000):
            with self.subTest(current_ma=current_ma):
                full = current_ma // probe.CURRENT_DIV
                self.assertEqual(probe.arm_current(current_ma), full & 0xFF)
                self.assertNotEqual(probe.arm_current(current_ma), full >> 8)

    def test_the_high_byte_of_the_060c_pair_is_masked_to_0x03(self):
        # F3FB `anl 0x02,#0x3`, a direct address, so it is R2 -- the high byte.
        self.assertEqual(probe.arm_060c(0xF0, 0x83, 0x22),
                         probe.arm_060c(0xF0, 0x03, 0x22))
        self.assertEqual(probe.arm_060c(0xF0, 0x04, 0x22),
                         probe.arm_060c(0xF0, 0x00, 0x22))

    def test_the_mask_bounds_the_060c_dividend_the_way_the_listing_does(self):
        # The point of the mask, stated as a bound. F3FB's `anl 0x02,#0x3`
        # caps the high byte at 3, so the product cannot exceed 0x03FF * 10
        # and the stored byte is bounded by that quotient's low byte. Drop the
        # mask and an unmasked high byte reaches 0xFFFF * 10, whose quotient
        # mod 256 differs -- which is what this case is here to notice. The
        # bound was {0, 1} under the swapped reading and is not a bound now,
        # because the low byte of a quotient this size is not confined to two
        # values; asserting a numeral here rather than the property is what
        # made the old case wrong.
        for lo in (0x00, 0x7F, 0xF0, 0xFF):
            for hi in range(0x100):
                masked = probe.arm_060c(lo, hi, 0x22)
                # Whatever the input, the result is the low byte of a
                # division, so it is always a byte.
                self.assertTrue(0x00 <= masked <= 0xFF)
        # And with the high byte pinned at its mask ceiling the quotient is
        # the largest the arm can produce.
        self.assertEqual(probe.arm_060c(0xFF, 0xFF, 0x22),
                         probe.arm_060c(0xFF, 0x03, 0x22))
        self.assertNotEqual(probe.arm_060c(0xFF, 0x03, 0x22), 0x00)

    def test_the_two_divisors_separate_wherever_the_byte_can_move(self):
        # The corrected model makes the implied divisor discriminating, which
        # is the point of reporting it per sample rather than folding it into
        # one pass/fail. Under the swapped reading the two divisors returned
        # 0x00 for almost every input and could not be told apart at all.
        # Asserted as near-non-overlap over the masked input space rather than
        # as a count: a handful of near-zero inputs still agree, and that is
        # a property of the arithmetic rather than something to pin.
        self.assertEqual(probe.arm_060c(0xF0, 0x03, 0x22), 0x28)
        self.assertEqual(probe.arm_060c(0xF0, 0x03, 0x44), 0x94)
        agree = [(lo, hi)
                 for lo in range(0x100)
                 for hi in range(0x04)
                 if probe.arm_060c(lo, hi, 0x22) == probe.arm_060c(lo, hi, 0x44)]
        self.assertTrue(agree, "the divisors never agree at all")
        # Where they do agree it is the degenerate near-zero region, where
        # both quotients are below the divisor and the stored byte is 0.
        for lo, hi in agree:
            self.assertEqual(probe.arm_060c(lo, hi, 0x22), 0x00)
        # And they are told apart across the bulk of the space.
        differ = sum(1 for lo in range(0x100) for hi in range(0x04)
                     if probe.arm_060c(lo, hi, 0x22) != probe.arm_060c(lo, hi, 0x44))
        self.assertGreater(differ, 0x100 * 0x04 // 2)

    def test_bit6_picks_the_divisor_the_way_f3c9_does(self):
        self.assertEqual(probe.divisor_from_bit6(0x40), 0x22)
        self.assertEqual(probe.divisor_from_bit6(0x00), 0x44)
        # Only bit 6 is looked at: bit 7 (the HAS_GPU candidate) and bit 5
        # must not move it.
        self.assertEqual(probe.divisor_from_bit6(0xE0), 0x22)
        self.assertEqual(probe.divisor_from_bit6(0x80), 0x44)


class ClassifyTests(unittest.TestCase):
    """One sweep's six bytes to a label, with no run involved."""

    def test_a_sample_the_current_arm_reproduces_is_current_branch(self):
        self.assertEqual(probe.classify(SWEEPS[0]), ("current-branch", []))

    def test_a_sample_the_060c_arm_reproduces_is_060c_branch_with_its_divisor(self):
        self.assertEqual(probe.classify(SWEEPS[1]), ("060c-branch", [0x22]))

    def test_a_sample_060c_reproduces_under_both_divisors_names_both(self):
        self.assertEqual(probe.classify(SWEEPS[2]), ("060c-branch",
                                                     [0x22, 0x44]))

    def test_a_sample_neither_arm_reproduces_is_unexplained(self):
        self.assertEqual(probe.classify(SWEEPS[3]), ("unexplained", []))

    def test_a_near_miss_is_not_snapped_to_the_nearer_arm(self):
        # Sweep 3 sits one above what the 0x22 arm predicts (0x28 -> 0x29),
        # and the current arm lands at 0x00, nowhere near it. Snapping to the
        # closer of the two would be the "closest fit" the procedure rules
        # out, and it would manufacture a match out of a sample that neither
        # arm reproduces.
        snap = SWEEPS[3]
        self.assertEqual(probe.arm_060c(snap[0x060C], snap[0x060D], 0x22),
                         snap[0x0449] - 1)
        self.assertNotEqual(probe.arm_current(snap[0x0434] | snap[0x0435] << 8),
                            snap[0x0449] - 1)
        self.assertEqual(probe.classify(snap)[0], "unexplained")

    def test_both_arms_reproducing_the_same_byte_is_its_own_bucket(self):
        self.assertEqual(probe.classify(SWEEPS[4]), ("both-arms", [0x22, 0x44]))


class BothArmsFixtureTests(unittest.TestCase):
    """A genuine both-arms collision, built rather than found in SWEEPS.

    Under the swapped reading both arms returned the same byte for almost
    every input, so the fixture table collided by construction and a sweep
    could be found for it. Under the corrected reading a real collision is
    rare -- both arms return the low byte of a small quotient, so they agree
    only near zero -- and the table above cannot be guaranteed to contain one.
    It does, on an all-zero reading, but that is the degenerate case, and a
    test that only ever exercises the degenerate case is not evidence the
    bucket works.

    So this builds a collision away from zero and checks the label directly.
    Building the snapshot here rather than widening the fixture table is the
    point: it keeps SWEEPS a set of *sweeps* rather than a search space, and
    the alternative -- weakening an arm until the two collide -- would
    manufacture the collision out of the thing under test.
    """

    def test_a_nonzero_collision_is_still_labelled_both_arms(self):
        found = None
        for current_ma in range(0x0100, 0x2000):
            byte = probe.arm_current(current_ma)
            for lo, hi in ((0xF0, 0x03), (0x10, 0x00), (0x64, 0x01)):
                if byte and probe.arm_060c(lo, hi, 0x22) == byte:
                    found = (current_ma, lo, hi, byte)
                    break
            if found:
                break
        self.assertIsNotNone(found,
                             "no non-zero both-arms collision exists to test")
        current_ma, lo, hi, byte = found
        snap = {0x0456: 0x40, 0x060C: lo, 0x060D: hi, 0x0449: byte,
                0x0434: current_ma & 0xFF, 0x0435: (current_ma >> 8) & 0xFF}
        self.assertNotEqual(byte, 0x00)
        label, implied = probe.classify(snap)
        # `both-arms` is about the two *current/060c* arms agreeing, not about
        # both divisors doing so: the implied list carries whichever divisors
        # also reproduce the byte, and near zero that is not always both.
        self.assertEqual(label, "both-arms")
        self.assertIn(probe.DIV_BIT6_SET, implied)
        self.assertTrue(set(implied) <= {probe.DIV_BIT6_SET, probe.DIV_BIT6_CLEAR})


class RunTests(unittest.TestCase):
    def run_probe(self, *extra, ec=None, label=None, want_csv=True):
        ec = ec if ec is not None else FakeEc()
        # Without a mark there is nothing to wait for, and the gate would sit
        # out its full timeout on every read of the last sweep.
        if label is None:
            ec.marked.set()
        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(probe, 'Ec', lambda: ec))
            if label is not None:
                stack.enter_context(
                    patch.object(probe.sys, 'stdin', FakeStdin(ec, label)))
            stack.enter_context(contextlib.redirect_stdout(out))
            with tempfile.TemporaryDirectory() as tmp:
                csv = Path(tmp) / 'capture.csv'
                argv = ['--interval', '0']
                if want_csv:
                    argv += ['--csv', str(csv)]
                argv += list(extra)
                rc = probe.main(argv)
                rows = csv.read_text().splitlines() if want_csv else []
        return rc, ec, out.getvalue(), rows

    def test_the_run_reports_every_arm_and_the_implied_divisor_against_bit6(self):
        rc, _, out, _ = self.run_probe()
        self.assertEqual(rc, 0)
        for label, n in (("current-branch", 1), ("060c-branch", 2),
                         ("both-arms", 1), ("unexplained", 1)):
            self.assertIn(f"{label:<16} {n:>5} of 5", out)
        # Sweep 1 places under 0x22 with bit 6 clear, and sweep 2 places under
        # both with bit 6 set. 0x22 is implied by three samples and agreed with
        # by two of them -- the one disagreement is sweep 1, and it is the
        # whole reason the divisor is reported per sample.
        self.assertIn("implied 0x22", out)
        self.assertIn("3 sample(s)  bit 6 agreed on 2, disagreed on 1", out)
        self.assertIn("implied 0x44", out)
        self.assertIn("2 sample(s)  bit 6 agreed on 0, disagreed on 2", out)

    def test_a_disagreeing_sample_is_printed_with_its_raw_six_bytes(self):
        _, _, out, _ = self.run_probe()
        line = [l for l in out.splitlines() if "unexplained" in l][0]
        self.assertIn("0x0456=0x80", line)
        self.assertIn("0x060C=0xF0", line)
        self.assertIn("0x060D=0x03", line)
        self.assertIn("0x0449=0x29", line)
        self.assertIn("0x0434=0x00", line)
        self.assertIn("0x0435=0x64", line)

    def test_the_bit7_trajectory_is_reported_against_the_samples(self):
        _, _, out, _ = self.run_probe()
        self.assertEqual(out.count("0x0456 bit 7 0 -> 1"), 1)
        self.assertEqual(out.count("0x0456 bit 7 1 -> 0"), 1)
        self.assertIn("0x0456 bit 7: set on 1 of 5 samples, changed 2 times",
                      out)

    def test_the_run_states_a_measurement_rather_than_a_verdict(self):
        _, _, out, _ = self.run_probe()
        for status in ("confirmed-working", "confirmed-inert",
                       "present-untested"):
            self.assertNotIn(status, out)
        self.assertIn("No status and no verdict", out)

    def test_every_sample_reaches_the_csv_with_its_branch_and_divisor(self):
        _, _, _, rows = self.run_probe()
        self.assertEqual(rows[0], ",".join(probe.CSV_HEADER))
        # Read the last two columns by position, not by a literal index, so a
        # column added to the header does not silently shift this assertion.
        tail = len(probe.CSV_HEADER) - 2
        self.assertEqual([r.split(",")[tail:] for r in rows[1:]],
                         [["current-branch", ""],
                          ["060c-branch", "0x22"],
                          ["060c-branch", "0x22|0x44"],
                          ["unexplained", ""],
                          ["both-arms", "0x22|0x44"]])

    def test_a_mark_lands_in_the_csv_between_two_sample_rows(self):
        _, _, _, rows = self.run_probe('--mark', label='GPU mode -> dGPU')
        at = [i for i, r in enumerate(rows) if ',MARK,' in r]
        self.assertEqual(len(at), 1)
        i = at[0]
        # The fifth field is `ec_watch.Marker`'s provenance column, empty
        # because this process has no `--label-vocab` to record: a mark row is
        # the 0751 capture shape whatever wrote it, and `CSV_HEADER` above is
        # this tool's own schema and is a different one.
        self.assertEqual(rows[i].split(',', 1)[1], 'MARK,,GPU mode -> dGPU,')
        self.assertEqual(rows[i - 1].split(",")[1], "4")
        self.assertEqual(rows[i + 1].split(",")[1], "5")

    def grader_marks(self, rows):
        """The marks `grader.read_capture` reads out of `rows`.

        The reader takes a path and these cases hold the capture as text, so
        it is written back out and read through it. Every row goes to it --
        the sample rows are this tool's own `CSV_HEADER` and hex-parse as
        addresses -- and the mark row is the only one the assertions name.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'capture.csv'
            path.write_text(''.join(row + '\n' for row in rows))
            return grader.read_capture(str(path))[0]

    def test_the_grader_places_no_role_in_this_runs_free_form_label(self):
        _, _, _, rows = self.run_probe('--mark', label='GPU mode -> dGPU')
        marks = self.grader_marks(rows)
        self.assertEqual(len(marks), 1)
        self.assertEqual(marks[0].label, 'GPU mode -> dGPU')
        # (None, None), and that is the run's design rather than a defect: the
        # probe is started without `--label-vocab`, so the label is free-form
        # and no §3 form leads it. `ec_watch.py`'s own `RefusedLabelTests`
        # refuses an unplaceable label only while a vocabulary is held, which
        # is this same distinction read from the other side. Asserting a role
        # here instead would claim a placement this run never made. The
        # century is not read off the return -- `parse_ts` is `fromisoformat`
        # and takes a 1999 stamp -- so it is asked of the `datetime` instead.
        self.assertEqual(grader.parse_mark(marks[0].label), (None, None))
        self.assertEqual(marks[0].ts.year // 100, 20)

    def test_without_a_csv_nothing_is_written_to_disk(self):
        rc, _, out, _ = self.run_probe(want_csv=False)
        self.assertEqual(rc, 0)
        self.assertIn("=== 5 samples", out)

    def test_a_run_stopped_before_its_first_sample_still_reports(self):
        # Ctrl-C during the first sleep, or --seconds the loop never reaches:
        # the denominators are all zero and the bit-7 line has no last value to
        # print. It is a report, not a crash.
        rc, _, out, _ = self.run_probe(ec=FakeEc(sweeps=[]))
        self.assertEqual(rc, 0)
        self.assertIn("=== 0 samples", out)
        self.assertIn("0 of 0", out)
        self.assertNotIn("last value", out)


class GuardTests(unittest.TestCase):
    """The allow-list, and where it is enforced."""

    def refused(self, argv):
        opened = []
        with patch.object(probe, 'Ec', lambda: opened.append(1)), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                probe.main(argv)
        # The refusal itself, not any SystemExit: argparse exits 2 on a
        # mistyped flag, so the bare assertion would pass for a run that never
        # looked at the address. `sys.exit(msg)` carries the message as the
        # exception's code.
        self.assertIsInstance(cm.exception.code, str)
        self.assertEqual(opened, [], "the EC was opened before the refusal")
        return cm.exception.code

    def test_a_range_walking_into_the_fan_tach_page_is_refused(self):
        msg = self.refused(['--start', '0x045E', '--len', '0x10'])
        self.assertIn("0x0460", msg)
        self.assertIn("fan-tach", msg)
        self.assertIn("#94", msg)

    def test_an_address_outside_the_allowed_set_is_refused(self):
        msg = self.refused(['--start', '0x0700', '--len', '0x10'])
        self.assertIn("0x0700", msg)
        self.assertIn("refusing to read outside", msg)

    def test_an_off_page_address_that_is_not_060c_or_060d_is_refused(self):
        # 0x060B is one below the pair and 0x060E one above it; both are
        # refused even though the range also covers an allowed byte.
        self.assertIn("0x060B", self.refused(['--start', '0x060B',
                                              '--len', '0x02']))
        self.assertIn("0x060E", self.refused(['--start', '0x060E',
                                              '--len', '0x01']))

    def test_the_default_watch_set_is_inside_the_allow_list(self):
        self.assertTrue(set(probe.WATCH) <= probe.ALLOWED)
        self.assertEqual(set(probe.WATCH) & set(probe.FAN_TACH), set())
        # 0x0456 is the highest address read inside the page, and 0x0460 is
        # the first byte after it.
        self.assertLess(max(a for a in probe.WATCH if a in probe.PAGE), 0x0460)

    def test_a_range_inside_the_page_is_accepted(self):
        ec = FakeEc()
        ec.marked.set()
        out = io.StringIO()
        with patch.object(probe, 'Ec', lambda: ec), \
             contextlib.redirect_stdout(out):
            rc = probe.main(['--start', '0x0400', '--len', '0x60',
                             '--interval', '0'])
        self.assertEqual(rc, 0)
        # The whole page, and not one byte of the next one.
        self.assertIn(0x045F, ec.read_addrs)
        self.assertNotIn(0x0460, ec.read_addrs)
        self.assertNotIn("0x0460", out.getvalue())

    def test_len_without_start_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                probe.main(['--len', '0x10'])
        self.assertEqual(cm.exception.code, 2)

    def test_a_mistyped_flag_is_a_usage_error_not_a_guard_refusal(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                probe.main(['--intervl', '0.5'])
        self.assertEqual(cm.exception.code, 2)

    def test_a_start_that_is_not_a_number_is_a_usage_error(self):
        # The guard's refusal is a string code and a traceback is neither, so
        # "0x04Z0" has to land on argparse's exit 2 rather than either.
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                probe.main(['--start', '0x04Z0'])
        self.assertEqual(cm.exception.code, 2)


class NoWriteTests(unittest.TestCase):
    """There is nothing to gate, because there is no write."""

    def test_the_run_never_writes_to_the_ec(self):
        ec = FakeEc()
        ec.marked.set()
        with patch.object(probe, 'Ec', lambda: ec), \
             contextlib.redirect_stdout(io.StringIO()):
            probe.main(['--interval', '0'])
        self.assertEqual(ec.writes, [])

    def test_there_is_no_write_subcommand(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                probe.main(['write'])
        self.assertEqual(cm.exception.code, 2)

    def test_the_module_exposes_no_write_helper(self):
        # `write` is the name ecrw.py's and manual_fan_ctrl_probe.py's
        # tool-level helpers would take if this tool had one.
        self.assertFalse(hasattr(probe, 'write'))
        self.assertFalse(hasattr(probe, 'do_write'))


class LinesStdin:
    """Several labels in a row, rather than `FakeStdin`'s one.

    `FakeStdin` waits on `at_last`, hands over its single line, and releases
    the sweep loop on the read after that -- one mark, and the read that proves
    it was committed. The blank-press cases need a *sequence*, because what is
    being asked is what a rejected press does to the presses beside it: a
    rejected press records nothing, and the mark after it still takes the
    number it would have taken. One line cannot ask that.

    The read that finds the list empty is what sets `marked`, so the sweep
    loop is released only once every line has been consumed and committed --
    the same ordering guarantee `FakeStdin` gives, held back until the last
    line rather than the second read.
    """

    def __init__(self, ec, lines):
        self._ec = ec
        self._lines = list(lines)
        self._at_last = threading.Event()

    def readline(self):
        self._at_last.set()
        self._ec.at_last.wait(5)
        if not self._lines:
            self._ec.marked.set()
            return ""
        return self._lines.pop(0)


# `LinesStdin` sits here rather than beside `FakeStdin` because
# `docs/findings/test-line-pin-census.md` carries pins that cite lines *into*
# this file (`0751-mark-provenance-column.md` and `0751-mark-provenance-shapes.md`
# both do), and inserting a class between `FakeStdin` and `RunTests` would put
# every one of them below the edit and re-register them for a shift of a few
# hundred lines rather than a few. Same for the two classes below.
#
# Placing them at the end is not the same as the pins not moving, and an earlier
# version of this comment said it was. The imports the new cases need are
# module-level, so they went to the top of this file and shifted everything below
# them by that many lines: the targets the table registers no longer land where
# it records them. Those rows are left stale deliberately, by the same rule that
# already leaves pins stale on `origin/main` -- see the "No totals of the
# repository's own text" bullet in `CLAUDE.md`, and
# `docs/findings/test-line-pin-census.md`'s own statement that it records the tree
# it was measured on. So: the placement keeps the shift small and keeps it below
# the code that is being extended, not at zero.


class BlankMarkTests(unittest.TestCase):
    """A blank press is not a mark, and the prompt says so rather than naming it.

    The prompt used to substitute `mark N` for an empty label, which wrote a
    `ts,MARK,,mark N` row -- the 0751 capture shape -- describing nothing, and
    read at the console as a mark somebody meant to place. It was also a mark
    nobody described, which is the one kind no reader can recover. Same
    substitution, same row shape and same cost as `ec_watch.py`'s, which
    stopped on 2026-09-25 (#474); the cases below mirror `test_ec_watch.py`'s
    `BlankMarkTests` one for one. The reasoning is
    `docs/findings/system-id-probe-mark-labels.md`.

    `FakeEc`'s read gate is what keeps the interleaving fixed, so the marks
    still land between the same two sample rows `RunTests` puts them between
    and "did the MARK row land between two samples" is not a race.
    """

    def run_probe(self, lines):
        ec = FakeEc()
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / 'capture.csv'
            out = io.StringIO()
            with patch.object(probe, 'Ec', lambda: ec), \
                 patch.object(probe.sys, 'stdin', LinesStdin(ec, lines)), \
                 contextlib.redirect_stdout(out):
                rc = probe.main(['--interval', '0', '--mark',
                                 '--csv', str(csv)])
                rows = csv.read_text().splitlines()
        return rc, rows, out.getvalue()

    def marks_summary(self, text):
        """The probe's own closing marks list, which is what §3 reads.

        The runbook's completeness check is "the last label in the list the
        probe printed is the last mark the capture has", so the summary is
        asserted directly rather than inferred from the CSV: a substitute in
        one and not the other would be the confusion the guard exists to stop.
        """
        if '\nmarks:\n' not in text:
            return []
        out = []
        for line in text.split('\nmarks:\n', 1)[1].splitlines():
            if not line:
                break
            out.append(line)
        return out

    def test_a_blank_press_writes_no_row_and_leaves_the_real_mark_alone(self):
        rc, rows, _ = self.run_probe(['\n', 'block start\n'])
        self.assertEqual(rc, 0)
        # The whole capture rather than the row counted above: the shape the
        # 0751 grader refuses is a substituted mark anywhere in the file, and
        # that is a property of the file rather than of where the press fell.
        self.assertNotIn(',MARK,,mark', '\n'.join(rows))
        self.assertEqual([r.split(',', 1)[1] for r in rows if ',MARK,' in r],
                         ['MARK,,block start,'])
        # And it still landed between two samples, so the blank press did not
        # push the real mark out of the capture.
        at = [i for i, r in enumerate(rows) if ',MARK,' in r]
        self.assertEqual(rows[at[0] - 1].split(",")[1], "4")
        self.assertEqual(rows[at[0] + 1].split(",")[1], "5")

    def test_the_console_says_the_press_was_not_recorded(self):
        _, _, text = self.run_probe(['\n', 'block start\n'])
        notices = [ln for ln in text.splitlines() if 'nothing recorded' in ln]
        self.assertEqual(len(notices), 1)
        # Not framed as a mark: a notice that reads like one is the same
        # confusion the substitution existed to create, and it would read the
        # same way at a console where the CSV is not in view.
        self.assertNotIn('MARK:', notices[0])
        # And the run's own count agrees with the file -- one mark, and no
        # substitute standing in for the press.
        summary = self.marks_summary(text)
        self.assertEqual(len(summary), 1)
        self.assertIn('block start', summary[0])

    def test_a_whitespace_only_press_is_the_same_as_an_empty_one(self):
        rc, rows, _ = self.run_probe(['   \n', 'block start\n'])
        self.assertEqual(rc, 0)
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['block start'])

    def test_a_padded_real_label_is_still_taken_and_stripped(self):
        # The other half of the guard: refuse the blank press, not the
        # whitespace. A label typed with a stray leading space is a label,
        # and §3's labels are prose an operator types by hand.
        rc, rows, text = self.run_probe(['  block start  \n'])
        self.assertEqual(rc, 0)
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['block start'])
        self.assertNotIn('nothing recorded', text)

    def test_a_rejected_press_does_not_take_a_mark_number(self):
        _, rows, text = self.run_probe(['\n', 'block start\n', '\n'])
        # Each notice names the number the press would have taken, and `_n`
        # counts marks recorded: the first blank would have been mark 1 and
        # was not, so the typed mark took 1 and the second blank would have
        # been mark 2. With the counter incremented first, the first notice
        # would have read "mark 2" and the capture would have held a `mark 2`
        # row sitting between two real labels.
        self.assertEqual(text.count('nothing recorded, no mark 1 taken'), 1)
        self.assertEqual(text.count('nothing recorded, no mark 2 taken'), 1)
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['block start'])

    def test_the_substitution_cannot_come_back(self):
        # The guard against a re-introduction in a form the cases above would
        # miss. Those hold for whatever the prompt does with a blank line;
        # this one holds the shape of the line itself, which is the thing that
        # was there before and could be pasted back. It has to be asserted on
        # the source, because an output assertion cannot see a default these
        # inputs never reach.
        #
        # On the AST rather than on the text, for a reason worth writing down
        # because the obvious version of this case silently cannot fire. An
        # f-string parses as a `JoinedStr` whose constant parts are only the
        # fragments between the holes, so re-inserting the exact deleted line
        # (`label = label.strip() or f"mark {self._n}"`) puts `'mark '` in
        # the literal list and never the substring `'mark {'` -- the check
        # would go on passing against the substitution itself. Matching the
        # source text instead does not work either: the blank-press notice
        # ends `no mark {self._n + 1}`, so `'mark {'` is in the unparsed
        # source of *correct* code too. Hence the node test, and hence the
        # liveness check below it.
        #
        # What it asserts is the structural form rather than the old
        # spelling: the loop has no `or` fallback, so there is no default to
        # substitute. That catches every spelling rather than the one that was
        # deleted. It is also blind to the comment above the guard, which
        # quotes the old line -- `ast.parse` drops comments -- so the record
        # of what this used to do is free to stay.
        loop = textwrap.dedent(inspect.getsource(probe.Marker._loop))
        self.assertEqual(self.or_fallbacks(loop), [],
                         'Marker._loop has an `or` fallback again, so a blank '
                         'label can be substituted for once more')
        # And this case is required to be able to fail. A guard that cannot is
        # worse than no guard: it tells the next reader a re-introduction
        # would be caught, and it would not be. Run the same check against the
        # two spellings of the line that was there.
        for gone in ('label = label.strip() or f"mark {self._n}"\n',
                     "label = label.strip() or 'mark ' + str(self._n)\n"):
            with self.subTest(spelling=gone):
                self.assertTrue(self.or_fallbacks(gone),
                                'this guard no longer detects the substitution '
                                'it is here to detect')

    @staticmethod
    def or_fallbacks(source):
        """The `x or y` expressions in `source`, by node rather than by text."""
        tree = ast.parse(textwrap.dedent(source))
        return [n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or)]


class FreeFormLabelTests(unittest.TestCase):
    """The mark labels are free-form prose by design, and there is no vocabulary.

    `ec_watch.py` takes `--label-vocab 0751` and refuses a label the 0751
    grader's `parse_mark` cannot read. This probe deliberately does not, and
    the case that makes the decision testable rather than a comment is the one
    below: every label the procedure tells the operator to type is one that
    check would refuse.

    **This class is a tripwire that goes red in the useful direction**, and the
    case that fires is `test_there_is_no_vocabulary_to_hold`: it asks the parser
    for `--label-vocab` and expects argparse's exit 2, so a flag added here
    fails it outright. That is the change re-opening this decision, not a defect
    in the probe, and the next reader should read the red as the question this
    file already answers.

    **CORRECTION (#1329 fix round 1, 2026-10-04), beside the paragraph above
    rather than under it.** "Fails it outright" was wrong about what a reader
    would see. That case invoked `main`, and with the flag added `main` does not
    fail: it parses, opens the EC and sweeps the six addresses until it is
    killed, so the case hung until the suite timed out -- which names no
    assertion and says nothing about which one mattered. It now asks
    `probe.build_parser()` to parse the flag instead, which has no side effect
    in either direction, so the flag makes the assertion fail at once and by
    name. `test_that_case_can_go_red` exists for the same reason as
    `BlankMarkTests`' liveness check above: the paragraph above is a claim
    about the future, and a claim about the future that cannot fire is worse
    than no claim, so that case arms the flag on a fresh copy of the real
    parser and fails if the detector above stays green with it.

    The other cases are *not* that tripwire, and the distinction is worth
    keeping straight rather than rounding off into "the class detects it". They
    read the runbook and the grader, and none of them touches this probe's
    parser: adding `--label-vocab` here would not change `parse_mark`, so they
    stay green. What they hold is the *consequence* the decision rests on --
    every label the procedure mandates is one that check would refuse -- which is
    why they are worth having, and why a flag added alongside them would be
    refusing the procedure's own labels at the first mark. That is an argument,
    not a detector; the detector is the parser case.

    What none of it establishes is that an operator's marks are *good*.
    `parse_mark` returning `(None, None)` for a runbook label is the design,
    and it says nothing about whether a capture is usable; §4 of the procedure
    is read by a person against the `0x0456` bit-7 trajectory.
    """

    # The labels §3 and §3b mandate, read out of the procedure rather than
    # copied from it, so a procedure that stopped asking for one of them makes
    # this case fail instead of quietly passing over a smaller set. The
    # extraction is deliberately narrow: a backticked label after the word
    # `mark`, plus the last column of §3b's "mark label if you do it" table.
    def mandated_labels(self):
        text = (Path(__file__).resolve().parents[2] / 'docs' / 'hardware-tests'
                / 'system-id-0456-bit6-divisor.md').read_text()
        try:
            body = text.split('### 3a.', 1)[1].split('### 3c.', 1)[0]
        except IndexError:
            self.fail('the procedure no longer has the 3a/3b blocks this '
                      'reads its labels out of')
        labels = []
        for m in re.finditer(r'mark `([^`]+)`', body, re.IGNORECASE):
            if m.group(1) not in labels:
                labels.append(m.group(1))
        for line in body.splitlines():
            m = re.match(r'^\|[^|]*\|[^|]*\|\s*`([^`]+)`\s*\|\s*$', line)
            if m and m.group(1) not in labels:
                labels.append(m.group(1))
        return labels

    def test_every_label_the_procedure_mandates_is_free_form_deliberately(self):
        labels = self.mandated_labels()
        # A vacuous pass is the failure mode here: a regex that stopped
        # matching would leave `labels` empty and assert nothing. So the
        # labels the decision rests on are named and required to be among
        # what the extraction found -- which fails loudly and by name if §3
        # stops asking for one, where a floor on the count would only say
        # that some number of them went.
        for named in ('block start', 'control arm end', 'steady window end',
                      'block end', 'GPU mode -> discrete', 'suspend/resume',
                      'driver reload', 'power mode -> N'):
            with self.subTest(label=named):
                self.assertIn(named, labels)
        for label in labels:
            with self.subTest(label=label):
                # (None, None) is the design and is correct for this run: no
                # §3 form leads any of these, so a `--label-vocab 0751` here
                # would refuse every label the procedure tells the operator to
                # type, at the first mark. Asserting a role for one instead
                # would be the calibration error in the other direction --
                # claiming a placement this run never makes.
                self.assertEqual(grader.parse_mark(label), (None, None))

    def test_a_0751_label_is_still_read_by_the_same_reader(self):
        # The other side of the case above, so `parse_mark` returning
        # (None, None) cannot be a broken reader being asserted into
        # agreement: a §3 form the *other* procedure mandates does place, by
        # the same call, in the same suite.
        self.assertEqual(grader.parse_mark('wrote 0x0751=0xA0'),
                         ('write', 0xA0))

    def test_there_is_no_vocabulary_to_hold(self):
        # `main`'s parser, asked for the flag rather than the module's
        # attributes: an operator reaching for `--label-vocab` on this tool
        # gets argparse's exit 2, which is the shape of the answer. That is the
        # parser `build_parser` hands `main`, unchanged.
        #
        # `build_parser().parse_args`, and not `main`, because asking `main`
        # is only a bounded question while the answer is no. With the flag
        # present `main` parses it, opens the EC and sweeps the six addresses
        # until it is killed, so a case meant to catch that would hang to the
        # suite timeout instead of failing -- a red that names no assertion.
        # Parsing has no side effect in either direction, so asking it the
        # question costs nothing and answers it in microseconds.
        self.assertTrue(self.refuses_vocabulary(probe.build_parser()),
                        'this tool now takes --label-vocab, so the free-form '
                        'decision its labels rest on needs reopening')
        # And nothing on the class either, so the vocabulary cannot be passed
        # in by a caller that did not go through the parser.
        self.assertFalse(hasattr(probe.Marker(sink=None), '_check'))
        self.assertFalse(hasattr(probe.Marker(sink=None), '_forms'))

    def test_that_case_can_go_red(self):
        # And this case is required to be able to fail, for the reason
        # `BlankMarkTests` gives for its own: a guard that cannot is worse than
        # no guard, because it tells the next reader that a flag added here
        # would be caught when it would not. Run the same check against a
        # parser that has the flag -- a fresh copy of *this* tool's own, so
        # what is exercised is its set of options and not a synthetic one.
        armed = probe.build_parser()
        if self.refuses_vocabulary(armed):
            # Not there yet, so arm a copy the way adding it would. Once the
            # flag does land this stops adding it -- argparse would raise on a
            # duplicate, and an error naming the conflict rather than the guard
            # is the same weak signal this case exists to rule out.
            armed.add_argument("--label-vocab", default=None)
        self.assertFalse(self.refuses_vocabulary(armed),
                         'this guard no longer detects the flag it is here to '
                         'detect')

    @staticmethod
    def refuses_vocabulary(ap):
        """Whether `ap` refuses `--label-vocab` with argparse's exit 2.

        A function of the parser so the case above and the liveness check
        below can ask the same question of two parsers, and so the question
        never reaches `main`'s EC handle or its sweep.
        """
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                ap.parse_args(['--label-vocab', '0751'])
            except SystemExit as e:
                return e.code == 2
        return False


if __name__ == '__main__':
    unittest.main()
