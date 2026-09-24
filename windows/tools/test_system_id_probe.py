#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

system_id_probe.py imports ecrw, which binds kernel32 at import time and so
only loads on Windows -- the fake below stands in for the whole module, which
is also what lets the sweeps be scripted byte by byte.

The script is keyed on the sweep, not on a timestamp, so what a sample is
labelled is an assertion about the arithmetic -- which arm reproduces the
0x0449, and which divisor it implies against bit 6 -- and not about how many
sweeps a given hold happens to buy. Every value here is reachable: the
`unexplained` rows are the ones the model cannot place, which is the state the
committed capture is entirely in.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

# One dict per sweep, in run order. Each is built so that a specific arm
# reproduces its 0x0449:
#
#   0  current  0xC800 mA / 100 = 0x0200, high byte 0x02
#   1  060c     masked pair 0x03F0 * 10 = 10224; /34 -> 300 (0x01), /68 -> 150 (0x00),
#               so it places under 0x22 alone -- and 0x0456 bit 6 is clear here,
#               which is the contradiction the implied divisor exists to catch
#   2  060c     an all-zero pair places under both divisors; bit 6 is set here
#   3  neither  one above what the 0x22 arm predicts, and the current arm
#               lands on 0x01 rather than 0x02 -- the near-miss that must not
#               be snapped to the nearer arm
#   4  both     the current arm and both divisors produce 0x00
SWEEPS = [
    {0x0456: 0x40, 0x060C: 0x00, 0x060D: 0x00, 0x0449: 0x02,
     0x0434: 0x00, 0x0435: 0xC8},
    {0x0456: 0x00, 0x060C: 0xF0, 0x060D: 0x83, 0x0449: 0x01,
     0x0434: 0x00, 0x0435: 0xC8},
    {0x0456: 0x40, 0x060C: 0x00, 0x060D: 0x00, 0x0449: 0x00,
     0x0434: 0x00, 0x0435: 0xC8},
    {0x0456: 0x80, 0x060C: 0xF0, 0x060D: 0x83, 0x0449: 0x02,
     0x0434: 0x00, 0x0435: 0x64},
    {0x0456: 0x40, 0x060C: 0x00, 0x060D: 0x00, 0x0449: 0x00,
     0x0434: 0x00, 0x0435: 0x00},
]


class FakeEcError(RuntimeError):
    pass


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


fake_ecrw = types.ModuleType('ecrw')
fake_ecrw.Ec = FakeEc
fake_ecrw.EcError = FakeEcError
sys.modules.setdefault('ecrw', fake_ecrw)

spec = importlib.util.spec_from_file_location(
    'system_id_probe', Path(__file__).with_name('system_id_probe.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ArithmeticTests(unittest.TestCase):
    """The model, checked against the listings it is read from."""

    def test_the_pair_is_little_endian_with_the_lower_address_in_the_low_byte(self):
        # 0x8886 puts [DPTR] in R1 and [DPTR+1] in R2, so 0x0434 is the low
        # byte. Read the pair the other way round, 0xC800 becomes 0x00C8 and
        # the stored byte collapses to zero.
        self.assertEqual(probe.arm_current(0x00 | 0xC8 << 8), 0x02)
        self.assertEqual(probe.arm_current(0xC8 | 0x00 << 8), 0x00)

    def test_what_is_stored_is_the_quotients_high_byte(self):
        # 0xA5E6 leaves the quotient in R1:R2 and 0xF3D7 stores R1, so 512
        # reads back as 0x02 and 511 -- the same top byte, one short -- as 0x01.
        self.assertEqual(probe.arm_current(51200), 0x02)
        self.assertEqual(probe.arm_current(51199), 0x01)

    def test_the_high_byte_of_the_060c_pair_is_masked_to_0x03(self):
        # F3FB `anl 0x02,#0x3`, a direct address, so it is R2 -- the high byte.
        self.assertEqual(probe.arm_060c(0xF0, 0x83, 0x22),
                         probe.arm_060c(0xF0, 0x03, 0x22))
        self.assertEqual(probe.arm_060c(0xF0, 0x04, 0x22),
                         probe.arm_060c(0xF0, 0x00, 0x22))

    def test_the_mask_keeps_the_060c_arm_inside_one_byte(self):
        # The point of the mask, stated as a bound: with it, the largest
        # product is 0x03F0 * 10 and the stored byte never leaves {0, 1}. Drop
        # it and 0xFFFF would reach 0x01A0 * 10, which stores 0x07 -- so this
        # is the assertion that fails if the `hi &= 0x03` ever goes missing.
        for lo in (0x00, 0x7F, 0xF0, 0xFF):
            for hi in range(0x100):
                self.assertIn(probe.arm_060c(lo, hi, 0x22), (0x00, 0x01))

    def test_the_two_divisors_separate_only_where_the_byte_can_move(self):
        # The masked pair caps the product at 0x27FF, and 0x27FF / 0x44 is 150
        # -- never 0x100. So under 0x44 the stored byte is always 0x00, and
        # every sample that places under 0x44 places under 0x22 too. That is
        # why the implied divisor is reported next to bit 6 rather than
        # folded into one pass/fail: the disagreement is only ever visible in
        # the 0x22 direction, and only per sample.
        self.assertEqual(probe.arm_060c(0xF0, 0x03, 0x22), 0x01)
        self.assertEqual(probe.arm_060c(0xF0, 0x03, 0x44), 0x00)
        for lo in (0x00, 0x7F, 0xF0, 0xFF):
            for hi in (0x00, 0x01, 0x02, 0x03):
                self.assertEqual(probe.arm_060c(lo, hi, 0x44), 0x00)

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
        # Sweep 3 sits one above the 0x22 arm's 0x01 and one above the current
        # arm's 0x01. Picking the closer of the two would be the "closest fit"
        # the procedure rules out, and it would manufacture a match.
        snap = SWEEPS[3]
        self.assertEqual(probe.arm_060c(snap[0x060C], snap[0x060D], 0x22),
                         snap[0x0449] - 1)
        self.assertEqual(probe.arm_current(snap[0x0434] | snap[0x0435] << 8),
                         snap[0x0449] - 1)
        self.assertEqual(probe.classify(snap)[0], "unexplained")

    def test_both_arms_reproducing_the_same_byte_is_its_own_bucket(self):
        self.assertEqual(probe.classify(SWEEPS[4]), ("both-arms", [0x22, 0x44]))


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
        self.assertIn("0x060D=0x83", line)
        self.assertIn("0x0449=0x02", line)
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
        self.assertEqual(rows[i].split(',', 1)[1], 'MARK,,GPU mode -> dGPU')
        self.assertEqual(rows[i - 1].split(",")[1], "4")
        self.assertEqual(rows[i + 1].split(",")[1], "5")

    def test_a_mark_row_parses_as_the_grader_expects(self):
        _, _, _, rows = self.run_probe('--mark', label='GPU mode -> dGPU')
        mark = [r for r in rows if ',MARK,' in r][0]
        ts, addr, old, label = mark.split(',')
        self.assertEqual((addr, old, label), ('MARK', '', 'GPU mode -> dGPU'))
        self.assertTrue(ts.startswith('20'))

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


if __name__ == '__main__':
    unittest.main()
