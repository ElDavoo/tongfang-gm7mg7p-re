#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

ctgp_dben_probe.py imports ecrw, which binds kernel32 at import time and so
only loads on Windows -- windows/tools/ecrw_fake.py stands in for the whole
module, installed by assignment the way the probe, ec_watch and GPU-block
suites do, and FakeEc below scripts the two arms on top of it.

The byte-script checks only know what the tool writes. They would pass
unchanged against a rewrite that drove bit 0 instead of bit 1, because a
reworded constant still writes a byte. So CitationPinTests is the half that
matters: it reads `evidence/acpi/dsdt.dsl`,
`ec/annotations/ghidra-functions.csv` and `ec/annotations/registers.yaml`, the
committed inputs the arm arithmetic and the watch table transcribe, and
asserts that the bits this tool sets are the bits those files name -- DBEN at
bit 3 in the ECMG field list, bit 1 of 0x0743 as the value `0x96AD` hands
`0x94C0`, bit 0 as the gate on the routine that makes bit 3 follow bit 4.
ProcedureChainTests then holds the procedure's own copy of that chain to the
tool, which is the drift #266 cost the GPU-block procedure the other way
round.

Like test_gpu_block_watch.py, it therefore has to run from inside the
repository, which `tools/run-tests.sh` guarantees (it cds to the repo root).
"""
import contextlib
import csv
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

TOOLS = Path(__file__).parent
REPO = TOOLS.parent.parent
DSDT = REPO / "evidence" / "acpi" / "dsdt.dsl"
FUNCTIONS = REPO / "ec" / "annotations" / "ghidra-functions.csv"
REGISTERS = REPO / "ec" / "annotations" / "registers.yaml"
PROCEDURE = REPO / "docs" / "hardware-tests" / "ctgp-dben-07c4-bit3.md"

sys.path.insert(0, str(TOOLS))

import ecrw_fake  # noqa: E402  (needs the sys.path entry above)
ecrw_fake.install()

import ctgp_dben_probe as probe  # noqa: E402  (needs the fake ecrw above)

# The vendor's own AC value for 0x0743 (registers.yaml, CTGP_DB_CTRL), so the
# fixture state traces to a committed observation rather than being invented
# here. Bit 2 (cTGP enable) is set with it, because "bits 2-7 are preserved"
# has to have something to preserve for that claim to mean anything.
ORIG = 0x07

# ctgp_dben_probe.py builds this list inside main(), so it cannot be imported
# and checked against itself. The copy here is the assertion.
COLS = ["ts", "mark", "t_s", "ctrl_written", "ctrl_read", "dben_byte",
        "dben_b3", "cpua", "dbap"]

# 0x09EA/0x09EB are what CPUA/DBAP are copied from, so a value that differs
# from both is a 0x83FF block that copied. 0x07C4 carries bit 3 and bit 5, so
# the bit under test starts set and DBST is set in both arms.
CPUA_FROM, DBAP_FROM = 0x40, 0x90
DBEN_HOLDS = 0x28

# A run that gets all the way through: both arms, one sample each, restore.
# --seconds 0 ends each arm on its first pass, so the write history is
# exactly the two arms and the restore.
BASE = ("--seconds", "0", "--interval", "0", "--i-mean-it")


def ecmg_group(text, addr):
    """The ECMG field-list group that starts at `Offset (addr)`.

    Translated out of the ASL rather than transcribed, and the unnamed bits
    are kept as "" instead of being dropped, because the whole of the bit-3
    claim is that three of them come first -- a parser that skipped them would
    "confirm" DBEN at bit 0. An `Offset (0xNNN)` restarts the bit count at
    that byte and every `Name, width` (or unnamed `, width`) takes the next
    `width` bits of it. Returns [(name, lo, hi)]; an empty group raises
    StopIteration, which is the non-vacuity guard: a group that is not there
    cannot pass for a field list that agrees.
    """
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines)
                 if l.strip().startswith("Field (ECMG"))
    out, here, bit = [], False, 0
    for line in lines[start + 1:]:
        line = line.split("//")[0].strip()
        if line == "}":
            break
        m = re.fullmatch(r"Offset \((0x[0-9A-Fa-f]+)\),\s*", line)
        if m:
            if here:
                break
            here = int(m.group(1), 16) == addr
            bit = 0
            continue
        m = re.fullmatch(r"([A-Za-z0-9_]*)\s*,\s*(\d+),\s*", line)
        if m and here:
            out.append((m.group(1), bit, bit + int(m.group(2)) - 1))
            bit += int(m.group(2))
    if not out:
        raise StopIteration(f"no ECMG field group at 0x{addr:04X}")
    return out


def function_row(text, addr, name):
    """One `ghidra-functions.csv` row, by address *and* by name.

    The address alone would let a renamed or re-pointed row satisfy a check
    keyed on the old name; a rename is exactly what this suite exists to
    notice. StopIteration is the non-vacuity guard again.
    """
    rows = [r for r in csv.DictReader(text.splitlines())
            if r["addr"].lower() == addr.lower()]
    row = next((r for r in rows if r["name"] == name), None)
    if row is None:
        raise StopIteration(f"no ghidra-functions.csv row {addr}={name}")
    return row


def read_registers():
    """registers.yaml as {addr: status}, keyed by address.

    A row's `addr:` is a list when it covers a block, so both shapes are
    handled once here rather than in each class that wants the mapping.
    """
    statuses = {}
    for r in yaml.safe_load(REGISTERS.read_text())["registers"]:
        addrs = r["addr"] if isinstance(r["addr"], list) else [r["addr"]]
        for a in addrs:
            if isinstance(a, int):
                statuses.setdefault(a, r["status"])
    return statuses


def _match(text, pattern):
    m = re.search(pattern, text)
    if m is None:
        raise StopIteration(f"no match for {pattern!r}")
    return m


def bit_numbers(text, pattern):
    """The bit indices a pattern captures in a row's comment, as ints.

    The three masks in this tool are `1 << n` for three n's, and each n is a
    number in a sentence in the CSV. Deriving the masks from the sentence
    rather than restating the number is what keeps this a pin and not a second
    copy of the claim: reword `bit 0` to `bit 2` in the CSV and the tool's
    GATE_BIT fails here rather than quietly driving the wrong bit. A pattern
    that no longer matches raises rather than returning zeroes.
    """
    return tuple(int(g) for g in _match(text, pattern).groups())


def mask_numbers(text, pattern):
    """The byte masks a pattern captures in a row's comment, base 16.

    `0x94C0`'s two halves are spelled as byte masks rather than bit indices in
    its comment, so they are read as the numbers they are written as.
    """
    return tuple(int(g, 16) for g in _match(text, pattern).groups())


def procedure_section(text, heading):
    """One `## n.` section of the procedure, found by heading.

    A missing heading raises rather than returning an empty section: an empty
    span makes every check that reads it pass vacuously.
    """
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(heading))
    body = lines[start + 1:]
    for i, l in enumerate(body):
        if l.startswith("## "):
            return "\n".join(body[:i])
    return "\n".join(body)


def procedure_chain(section):
    """§1's bit table as {(addr, bit): role}, keyed on the first two cells.

    Hand-rolled in the house idiom rather than taken from a markdown library,
    because project-setup installs none and one table does not need one. The
    role is a whole cell of its own rather than a word hunted for in prose, so
    a cell that describes the gate without saying "gate" fails instead of
    quietly matching on some other sentence's wording.
    """
    out = {}
    for line in section.splitlines():
        m = re.match(r"\|\s*`(0x[0-9A-Fa-f]{4})` bit (\d)\s*\|\s*(\w+)\s*\|", line)
        if m:
            out[(int(m.group(1), 16), int(m.group(2)))] = m.group(3)
    return out


class FakeEc:
    """A byte map, so the tool's own read/write pair is the one under test.

    Every read and write goes through the map rather than a scripted table,
    because 0x0743 is the register this tool changes: a write has to land
    where a later read can see it, or the restore's readback asserts nothing.
    `boom_read_at` and `boom_write_at` raise on a chosen read or write, so a
    failure can be put genuinely partway -- a read inside the second arm's
    sample, or the second arm's write itself -- rather than merely early. The
    context manager is here because the tool opens the device with `with Ec()
    as ec:`, and __exit__ returns None so a failure partway through still
    reaches the finally that restores.
    """

    def __init__(self, orig=ORIG, dben=None, boom_read_at=None,
                 boom_write_at=None, exc=None):
        self.regs = {probe.CTRL: orig, probe.DBEN: DBEN_HOLDS,
                     probe.CPUA: CPUA_FROM, probe.DBAP: DBAP_FROM}
        self.writes = []    # (addr, value), in the order the tool wrote them
        self.reads = 0
        self.dben = dben    # None: 0x07C4 holds its fixture value throughout
        self.boom_read_at = boom_read_at
        self.boom_write_at = boom_write_at
        self._boomed = False
        self.exc = exc

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        index = self.reads
        self.reads += 1
        if index == self.boom_read_at:
            raise self.exc
        if addr == probe.DBEN and self.dben is not None:
            return self.dben
        return self.regs.get(addr, 0x00)

    def write(self, addr, val):
        # The boom fires once, before the write is recorded, so the assertion
        # is about what the tool had actually put by the time it failed -- and
        # so the restore's own write, which lands at the same list index, is
        # not the thing that raises.
        if len(self.writes) == self.boom_write_at and not self._boomed:
            self._boomed = True
            raise self.exc
        self.writes.append((addr, val))
        self.regs[addr] = val


class Clock:
    """A counter for time.time, so --seconds 0 buys exactly one pass a arm.

    The tool takes t0 at the first call, an arm's deadline at the second and
    that arm's exit check at the third, so a step of any size ends each arm
    after one sample. `slept` records what the run asked to sleep for, which
    is how "one pass and no interval" is asserted rather than counted out.
    """

    def __init__(self, step=0.1):
        self.t = 0.0
        self.step = step
        self.slept = []

    def time(self):
        self.t += self.step
        return self.t

    def sleep(self, s):
        self.slept.append(s)


def run_probe(argv, ec=None, clock=None):
    ec = ec if ec is not None else FakeEc()
    clock = clock if clock is not None else Clock()
    out, err = io.StringIO(), io.StringIO()
    with patch.object(probe, 'Ec', lambda: ec), \
         patch.object(probe.time, 'time', clock.time), \
         patch.object(probe.time, 'sleep', clock.sleep), \
         contextlib.redirect_stdout(out), \
         contextlib.redirect_stderr(err):
        rc = probe.main(list(argv))
    return rc, ec, clock, out.getvalue(), err.getvalue()


def capture(*extra, **kw):
    """A full run into a temporary CSV: (rc, ec, clock, stdout, rows)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'run.csv'
        rc, ec, clock, out, _ = run_probe([*BASE, "--csv", str(path), *extra],
                                          **kw)
        rows = list(csv.reader(path.read_text().splitlines()))
        return rc, ec, clock, out, rows


class RefusalTests(unittest.TestCase):
    """Nothing is opened and nothing is written to disk before the writing.

    The house `lambda: self.fail(...)` idiom rather than a flag on the fake:
    a run that constructed an Ec at all is a failure, and there is no state
    left to inspect if it did.
    """

    def test_a_run_without_i_mean_it_prints_the_plan_and_opens_no_ec(self):
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            # --csv is given so the run *could* have recorded itself; the
            # refusal is about the write, and the plan is the useful part of
            # what a run with no machine can still produce.
            path = Path(tmp) / 'plan.csv'
            with patch.object(probe, 'Ec',
                              lambda: self.fail("opened an EC")), \
                 contextlib.redirect_stdout(out), \
                 contextlib.redirect_stderr(err):
                rc = probe.main(["--csv", str(path)])
            self.assertFalse(path.exists())
        text = out.getvalue()
        self.assertEqual(rc, 2)
        self.assertEqual(err.getvalue().strip(),
                         "refusing to write without --i-mean-it")
        # The watch set and the two arms print before the refusal, so a run
        # with no machine is still a plan and not only an error.
        self.assertIn("planned byte script", text)
        self.assertIn("arm A   orig | 0x03", text)
        self.assertIn("arm B   (orig | 0x01) & ~0x02", text)
        for addr, name, _, _ in probe.WATCH:
            self.assertIn(f"0x{addr:04X}", text)
            self.assertIn(name, text)

    def test_the_plan_resolves_the_arms_when_the_original_is_supplied(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(probe, 'Ec', lambda: self.fail("opened an EC")), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = probe.main(["--orig", "0x00"])
        text = out.getvalue()
        self.assertEqual(rc, 2)
        arm_a, arm_b = probe.arm_bytes(0x00)
        self.assertIn(f"-> 0x{arm_a:02X}", text)
        self.assertIn(f"-> 0x{arm_b:02X}", text)
        # On a byte with bit 0 clear -- what the vendor writes on battery --
        # the plan says arm A forces the bit on rather than leaving the
        # operator to work that out from the arithmetic.
        self.assertIn("bit 0 in orig: CLEAR", text)
        self.assertIn("forces `DB function control` on", text)

    def test_a_run_without_csv_is_refused_and_writes_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(probe, 'Ec', lambda: self.fail("opened an EC")), \
                 contextlib.redirect_stderr(io.StringIO()):
                rc, _, _, _, err = run_probe([*BASE])
            self.assertEqual(rc, 2)
            # The message is the claim, not the bare rc: a mistyped flag exits
            # 2 too, and so does an --i-mean-it refusal the reader is meant to
            # be told about.
            self.assertIn("--csv is required", err)
            self.assertNotIn("--i-mean-it", err)
            # Nothing at all was created, which is the stronger form of "no
            # --csv, no capture": the run had a directory to write into and
            # did not write into it.
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_a_planning_value_is_refused_alongside_i_mean_it(self):
        # --orig exists so a plan can resolve the arms, and a real run reads
        # the byte for itself. Allowing both would put a value a human typed
        # earlier in front of the restore, which is the one write in this tool
        # that has to be exactly what the machine held.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            with patch.object(probe, 'Ec', lambda: self.fail("opened an EC")), \
                 contextlib.redirect_stderr(io.StringIO()):
                rc, _, _, _, err = run_probe(
                    [*BASE, "--csv", str(path), "--orig", "0x03"])
            self.assertEqual(rc, 2)
            self.assertIn("--orig is a planning value", err)
            self.assertFalse(path.exists())

    def test_a_mistyped_flag_is_a_usage_error_not_a_refusal(self):
        with patch.object(probe, 'Ec', lambda: self.fail("opened an EC")), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                probe.main(["--intervl", "0.5"])
        self.assertEqual(cm.exception.code, 2)


class ByteScriptTests(unittest.TestCase):
    """The three writes, in order, and what the two of them are."""

    def expected_arms(self, orig):
        """The arm bytes, computed from `orig` and the bit each arm drives.

        Deliberately not literal constants: recomputing them here means a
        reworded mask in the tool fails these checks rather than passing as a
        byte that happens to be right for one starting value.
        """
        arm_a = orig | probe.GATE_BIT | probe.VALUE_BIT
        arm_b = (orig | probe.GATE_BIT) & ~probe.VALUE_BIT & 0xFF
        return arm_a, arm_b

    def test_the_byte_script_is_the_two_arms_and_the_restore(self):
        arm_a, arm_b = self.expected_arms(ORIG)
        rc, ec, clock, _, _ = capture()
        self.assertEqual(rc, 0)
        self.assertEqual(ec.writes,
                         [(probe.CTRL, arm_a), (probe.CTRL, arm_b),
                          (probe.CTRL, ORIG)])
        # Breaks on the arm's deadline before the interval is ever slept,
        # which is the "exactly one pass a arm" the fake clock buys.
        self.assertEqual(clock.slept, [])

    def test_the_arms_differ_only_in_the_bit_they_drive(self):
        for orig in (0x00, 0x01, 0x02, 0x07, 0xFF):
            arm_a, arm_b = self.expected_arms(orig)
            self.assertEqual(arm_a ^ arm_b, probe.VALUE_BIT, f"0x{orig:02X}")
            for arm in (arm_a, arm_b):
                # bit 0 is the gate on the 0x83FF block, and it has to be set
                # in both arms or the routine under test never runs.
                self.assertTrue(arm & probe.GATE_BIT, f"0x{orig:02X}")
                # bits 2-7 are cTGP enable and the rest of the vendor's byte;
                # neither arm is allowed to move them.
                self.assertEqual(arm & ~0x03, orig & ~0x03, f"0x{orig:02X}")
            self.assertTrue(arm_a & probe.VALUE_BIT, f"0x{orig:02X}")
            self.assertFalse(arm_b & probe.VALUE_BIT, f"0x{orig:02X}")

    def test_a_byte_with_bit_zero_clear_has_it_forced_on_in_both_arms(self):
        # The vendor writes 0x0743=0x00 on battery, and forcing the gate on is
        # the difference between the two power states, so the banner says so
        # where the operator reads it.
        rc, _, _, out, _ = capture(ec=FakeEc(orig=0x00))
        self.assertEqual(rc, 0)
        self.assertIn("both arms FORCE", out)

    def test_the_baseline_line_names_the_original_and_the_gate_state(self):
        _, _, _, out, _ = capture(ec=FakeEc(orig=0x00))
        self.assertIn("baseline: 0x0743 = 0x00 (bit 0 CLEAR, bit 1 clear), "
                      f"0x07C4 = 0x{DBEN_HOLDS:02X}", out)

    # The restore is a finally rather than an except clause, and these are the
    # two cases that show it: one EcError, which an `except` clause could
    # have handled, and one KeyboardInterrupt, which it could not.
    def test_an_ec_error_partway_still_restores_the_byte(self):
        arm_a, arm_b = self.expected_arms(ORIG)
        # Read 8 is arm B's third of four reads, so both arms had been written
        # and the restore is the only thing that can put the byte back. The
        # raise has to be the fake module's own EcError, because the tool binds
        # that name at import and a plain RuntimeError would go out of main()
        # instead of becoming a return code.
        ec = FakeEc(boom_read_at=8, exc=ecrw_fake.EcError("ECRR failed"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, _, out, err = run_probe([*BASE, "--csv", str(path)], ec=ec)
            rows = list(csv.reader(path.read_text().splitlines()))
        self.assertEqual(rc, 1)
        self.assertEqual(err.strip(), "error: ECRR failed")
        self.assertEqual(ec.writes,
                         [(probe.CTRL, arm_a), (probe.CTRL, arm_b),
                          (probe.CTRL, ORIG)])
        self.assertIn(f"restored 0x0743 -> 0x{ORIG:02X}", out)
        # An errored run still leaves a CSV a reader can parse: the header and
        # arm A's one completed sample, and no half-written row for the arm
        # that was cut off mid-sweep.
        self.assertEqual(rows[0], COLS)
        self.assertEqual([r[COLS.index("mark")] for r in rows[1:]],
                         [probe.ARMS[0]])

    def test_ctrl_c_partway_still_restores_the_byte(self):
        arm_a, _ = self.expected_arms(ORIG)
        # Raised on arm B's write, so the failure is between the two arms and
        # arm A is the only write the tool had made.
        ec = FakeEc(boom_write_at=1, exc=KeyboardInterrupt())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            with self.assertRaises(KeyboardInterrupt):
                run_probe([*BASE, "--csv", str(path)], ec=ec)
        # KeyboardInterrupt is a BaseException, so `except EcError` cannot
        # catch it and it leaves main() uncaught. What puts the byte back is
        # the finally, which is why that arm is a finally.
        self.assertEqual(ec.writes, [(probe.CTRL, arm_a), (probe.CTRL, ORIG)])


class CsvTests(unittest.TestCase):
    def test_the_header_is_the_pinned_column_set_and_every_row_fills_it(self):
        rc, _, _, _, rows = capture()
        self.assertEqual(rc, 0)
        self.assertEqual(rows[0], COLS)
        # --seconds 0 buys one sample an arm: header, arm A, arm B.
        self.assertEqual(len(rows), 3)
        for row in rows[1:]:
            self.assertEqual(len(row), len(COLS))

    def test_every_sample_carries_its_arm_and_the_byte_its_arm_wrote(self):
        _, ec, _, _, rows = capture()
        self.assertEqual([r[COLS.index("mark")] for r in rows[1:]],
                         list(probe.ARMS))
        self.assertEqual([r[COLS.index("ctrl_written")] for r in rows[1:]],
                         [f"0x{v:02X}" for _, v in ec.writes[:2]])

    def test_the_bit_under_test_is_its_own_column(self):
        # 0x28 carries bit 3 and bit 5, so dben_b3 is 1 in both arms and the
        # column is not a restatement of a zero; a byte carrying bit 4 only
        # has to read 0 there.
        _, _, _, _, rows = capture()
        self.assertEqual({r[COLS.index("dben_b3")] for r in rows[1:]}, {"1"})
        _, _, _, _, rows = capture(ec=FakeEc(dben=0x10))
        self.assertEqual({r[COLS.index("dben_byte")] for r in rows[1:]}, {"0x10"})
        self.assertEqual({r[COLS.index("dben_b3")] for r in rows[1:]}, {"0"})

    def test_the_07d4_and_07d5_columns_are_watched_every_sweep(self):
        # The two bytes 0x83FF writes one instruction from the bit-3 write are
        # what tells "the routine ran and set bit 3" from "the routine ran",
        # so a capture carrying a value for them has to exist.
        _, _, _, _, rows = capture()
        self.assertEqual({r[COLS.index("cpua")] for r in rows[1:]},
                         {f"0x{CPUA_FROM:02X}"})
        self.assertEqual({r[COLS.index("dbap")] for r in rows[1:]},
                         {f"0x{DBAP_FROM:02X}"})

    def test_a_second_run_into_the_same_file_appends_without_a_second_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            for _ in range(2):
                run_probe([*BASE, "--csv", str(path)])
            rows = list(csv.reader(path.read_text().splitlines()))
        self.assertEqual(rows.count(COLS), 1)
        self.assertEqual(len(rows), 5)

    def test_a_sweep_is_four_reads(self):
        # The #94 exposure is the read count, and the docstring claims four a
        # sweep against 24 and 206 for the two tools that carry the warning.
        # Eleven reads for a two-arm --seconds 0 run: two in the baseline
        # banner, four a sweep, one in the restore's readback.
        _, ec, _, _, _ = capture()
        self.assertEqual(ec.reads, 11)

    def test_the_tool_states_a_measurement_and_not_a_verdict(self):
        # The watch table carries registers.yaml's own status words, so the
        # check is scoped to the run body: a value that holds across an arm is
        # not a result, and #168 owns grading a capture.
        _, _, _, out, _ = capture()
        body = out[out.index("baseline:"):].lower()
        for word in ("confirmed", "inert", "absent", "unreferenced", "verdict"):
            self.assertNotIn(word, body)
        self.assertIn("restored 0x0743", out)

    def test_the_cadence_caveat_is_where_the_operator_decides(self):
        _, _, _, out, _ = capture()
        self.assertIn("no interval here is validated", out)
        self.assertIn("fans audibly", out)

    # The procedure and the tool each say they are the reference the other
    # follows, and the two defaults are where that claim is checkable: a run
    # of §3's length that the tool silently holds for a different time is the
    # drift #146 was.
    def test_the_defaults_are_the_procedures_thirty_seconds_and_half_second(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, _, _, out, _ = run_probe(["--csv", str(path), "--i-mean-it"])
        # Read off the banner rather than counted out of fake sweeps: the
        # default is a number the operator reads before pressing anything, so
        # that is where it has to be right. The fake clock makes the 60 s of
        # default holding cost 600 iterations and nothing else.
        self.assertEqual(rc, 0)
        self.assertIn("holding 30s an arm, sweeping every 0.5s", out)

    def test_the_interval_flag_reaches_the_sweep(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            _, _, clock, out, _ = run_probe(
                ["--seconds", "0.3", "--interval", "1.25", "--csv", str(path),
                 "--i-mean-it"])
        # --seconds 0.3 buys two samples an arm against the fake clock's 0.1
        # step, so exactly one interval is slept per arm and its value is
        # visible.
        self.assertIn("sweeping every 1.25s", out)
        self.assertEqual(clock.slept, [1.25, 1.25])


class CitationPinTests(unittest.TestCase):
    """The bits the tool writes, checked against the files they come from.

    Every helper here reads a committed input and raises rather than returning
    an empty match, so a pin that finds nothing cannot pass for an agreement.
    """

    @classmethod
    def setUpClass(cls):
        cls.dsdt = DSDT.read_text(encoding="utf-8", errors="replace")
        cls.functions = FUNCTIONS.read_text(encoding="utf-8")
        cls.statuses = read_registers()
        cls.apply = function_row(cls.functions, "0x96AD",
                                 "apply_oem_overrides_then_fill_08xx")
        cls.set_b4 = function_row(cls.functions, "0x94C0",
                                  "set_07c4_bit4_from_r7")
        cls.sync = function_row(cls.functions, "0x83FF",
                                "sync_0788_and_07d4_from_09e9")

    def test_the_dsdt_field_list_the_tool_depends_on_was_parsed(self):
        # 0x7C4's group with its unnamed bits intact: the bit-3 claim is a
        # claim about three unnamed bits coming first, so a parser that
        # dropped them would "confirm" DBEN at bit 0.
        self.assertEqual(ecmg_group(self.dsdt, 0x07C4),
                         [("", 0, 2), ("DBEN", 3, 3), ("", 4, 4), ("DBST", 5, 5)])

    def test_the_observed_bit_is_the_dsdt_bit(self):
        # 0x07C4 bit 3 in the ASL, 0x07C4 bit 3 in the tool -- derived from
        # the parsed field list rather than restated, so the two can only
        # disagree if the ASL or the tool did.
        bit = next(lo for name, lo, _ in ecmg_group(self.dsdt, 0x07C4)
                   if name == "DBEN")
        self.assertEqual(probe.OBSERVED_BIT, 1 << bit)

    def test_the_gate_bit_is_the_bit_the_sync_row_gates_on(self):
        # 0x83FF's own comment carries the gate bit as a number, and the
        # tool's GATE_BIT has to be 1 << that number. This is what stops a
        # rewrite that drives bit 0 alone -- §9's original instruction, which
        # opens a gate onto a bit 4 that never moves -- from passing every
        # byte-script test above.
        (gate,) = bit_numbers(self.sync["comment"],
                              r"only when bit (\d) of 0x0743")
        self.assertEqual(probe.GATE_BIT, 1 << gate)

    def test_the_value_bit_is_the_bit_the_apply_row_passes(self):
        (value,) = bit_numbers(self.apply["comment"],
                               r"calls 0x94C0 with 0x0743 bit (\d)")
        self.assertEqual(probe.VALUE_BIT, 1 << value)

    def test_the_value_bit_lands_on_07c4_bit_four(self):
        # 0x94C0 is what turns the value into a bit of 0x07C4, and the two
        # masks in its comment are the halves of that: OR 0x10 in, AND 0xEF
        # out. Checked as numbers, so a routine that started driving bit 3
        # directly would fail here instead of quietly collapsing the two hops.
        out_mask, and_mask = mask_numbers(
            self.set_b4["comment"],
            r"a non-zero R7 ORs 0x([0-9A-Fa-f]{2}) into the byte, a zero R7 "
            r"ANDs it with 0x([0-9A-Fa-f]{2})")
        self.assertEqual(out_mask, probe.OBSERVED_BIT << 1,
                         "0x94C0 sets the bit one above the bit under test; "
                         "0x83FF is what does the second hop")
        self.assertEqual(out_mask & and_mask, 0,
                         "the AND half has to clear the bit the OR sets")
        self.assertEqual(out_mask | and_mask, 0xFF,
                         "and must not clear any other bit")

    def test_the_observed_bit_follows_the_bit_94c0_sets(self):
        (observed, followed) = bit_numbers(
            self.sync["comment"],
            r"sets or clears bit (\d) of 0x07C4 to follow bit (\d)")
        (out_mask,) = mask_numbers(
            self.set_b4["comment"],
            r"a non-zero R7 ORs 0x([0-9A-Fa-f]{2}) into the byte")
        self.assertEqual(probe.OBSERVED_BIT, 1 << observed)
        self.assertEqual(followed, out_mask.bit_length() - 1)

    def test_the_two_copied_bytes_are_the_two_the_tool_watches(self):
        # The bytes 0x83FF copies in the same block are the tool's other two
        # read addresses, so "the routine ran" is readable from the same
        # capture as "and it set bit 3".
        self.assertIn("copies 0x09EA and 0x09EB into 0x07D4 and 0x07D5",
                      self.sync["comment"])
        self.assertEqual((0x07D4, 0x07D5), (probe.CPUA, probe.DBAP))

    def test_the_watch_set_is_those_four_addresses_and_nothing_else(self):
        self.assertEqual([a for a, *_ in probe.WATCH],
                         [probe.CTRL, probe.DBEN, probe.CPUA, probe.DBAP])
        self.assertEqual(len(probe.WATCH), 4)

    def test_every_registers_yaml_status_in_the_watch_set_is_verbatim(self):
        for addr, _, status, _ in probe.WATCH:
            self.assertEqual(status, self.statuses[addr], f"0x{addr:04X}")

    def test_every_watch_set_citation_names_the_file_it_comes_from(self):
        for addr, _, _, cite in probe.WATCH:
            self.assertIn("dsdt.dsl:", cite, f"0x{addr:04X}")
            self.assertIn("registers.yaml", cite, f"0x{addr:04X}")

    def test_no_watch_set_cell_is_spelled_as_absence(self):
        # Every cell carries registers.yaml's own vocabulary, quoted. A cell
        # saying "unused" or "no row" would be the §4c retraction in table
        # form, and a sweep table is where that phrasing comes back from.
        for addr, _, status, _ in probe.WATCH:
            for word in ("absent", "unused", "unreferenced", "no row"):
                self.assertNotIn(word, status, f"0x{addr:04X}")
            self.assertIn(status, self.statuses[addr], f"0x{addr:04X}")


class ProcedureChainTests(unittest.TestCase):
    """The procedure's own copy of the chain, against the tool.

    #266 is what duplicating a table costs: the GPU-block tool's copy was held
    by its suite and the door doc's copy went stale for a whole merge cycle.
    Here the doc is the copy that can drift, so it is checked against the
    tool -- every bit number in §1's table has to be the bit the tool drives.
    """

    @classmethod
    def setUpClass(cls):
        cls.section = procedure_section(PROCEDURE.read_text(encoding="utf-8"),
                                         "## 1. The question")
        cls.chain = procedure_chain(cls.section)
        cls.text = PROCEDURE.read_text(encoding="utf-8")

    def test_the_chain_table_was_parsed(self):
        # The non-vacuity guard: a table that is missing, renamed or
        # reformatted finds nothing, and three checks against an empty dict
        # pass on a procedure that says nothing about which bit is which.
        self.assertEqual(set(self.chain),
                         {(probe.CTRL, 0), (probe.CTRL, 1), (probe.DBEN, 3)})

    def test_every_bit_in_the_doc_is_the_bit_the_tool_drives(self):
        roles = {(probe.CTRL, probe.GATE_BIT): "gate",
                 (probe.CTRL, probe.VALUE_BIT): "value",
                 (probe.DBEN, probe.OBSERVED_BIT): "watched"}
        for (addr, bit), role in self.chain.items():
            self.assertEqual(role, roles[(addr, 1 << bit)],
                             f"0x{addr:04X} bit {bit}")

    def test_the_procedure_answers_the_readback_question_rather_than_leaving_it(self):
        # §7 is where a capture is read, so it is where a clean readback would
        # be turned into a conclusion. The whole document is checked, because
        # the answer has to be where a reader is, not in a footnote.
        self.assertIn("is not evidence the EC acts on it", self.text)
        self.assertIn("**Status: not run (issue #284).**", self.text)

    def test_the_procedure_names_the_tool_it_drives(self):
        self.assertIn("../../windows/tools/ctgp_dben_probe.py", self.text)

    def test_the_procedure_says_the_attribution_is_a_separate_question(self):
        # §8 of the sites doc is a different question this run cannot reach:
        # it drives a byte from the host, so nothing it captures can say who
        # wrote 0x07C4 on 2026-09-23. §5 has to say so by name.
        section = procedure_section(self.text, "## 5. What this cannot settle")
        self.assertIn("ec-07c4-07d5-sites.md", section)
        self.assertIn("§8", section)


if __name__ == '__main__':
    unittest.main()
