#!/usr/bin/env python3
"""Offline checks for trampoline_target_reading.py: no hardware, no capture, no
Ghidra, and nothing but the committed firmware and the committed CSVs.

**What is asserted here is a relationship or a cited fact, never a count of the
tree.** CLAUDE.md's rule, arrived at the same way as in
`test_trampoline_target_census.py`: a figure that every merge has to edit is a
value that goes stale the moment anything lands, so what these assert is that
the table is *of* the image -- one row per entry, every byte read in the row's
own bank, every run really a run -- and the figures move without the suite
moving with them.

**The committed table is read against the image, not against a re-run of the
scan that wrote it.** A regenerated table compared with itself would pass even
if the scan had drifted from the firmware, so `target_byte` here is the byte at
the file offset the row's own `selects_bank` and `dptr_target` name, and
`ret_run` is recomputed from the image rather than trusted.

**The two committed tables that overlap are cross-checked against each other.**
`trampoline_target_census.csv` carries the same entries with the same stub, bank
and target byte; this table adds the run and the callers. Asserting agreement
catches a drift in either, where asserting one against a literal written here
would only say this file had not changed.

**Where the numbers *are* the finding**, they are transcribed from the
write-up rather than recomputed, and each is an address or a property of the
image that no change to this repository can move: the two targets issue #559
read by hand, and the stub's own bytes, which are what make the `ret` reading a
mechanism rather than a guess.

**What is deliberately not here.** No case asserts that any target is or is not
code, that any trampoline is called, or that any register behaves in any way.
`in_ret_run` says a target sits in a run of identical bytes and nothing more;
`call_sites` is a byte-scan upper bound; nothing here was observed on hardware.
"""
import csv
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    "trampoline_target_reading", HERE / "trampoline_target_reading.py")
ttr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ttr)

import audit_call_targets as act
import trampoline_target_census as ttc

FIRMWARE = str(HERE.parent / "firmware" / "GMxMGxx_11.800")
COMMITTED_CSV = HERE.parent / "annotations" / "trampoline-target-reading.csv"
CENSUS_CSV = HERE.parent / "annotations" / "trampoline-target-census.csv"
CALL_TARGETS_CSV = HERE.parent / "annotations" / "bank-call-targets.csv"
TOOL = str(HERE / "trampoline_target_reading.py")

# The two targets `docs/findings/reset-vector-dptr-targets.md` read by hand
# (issue #559), as (entry, target, byte). Both are named there, so a run whose
# table disagreed with them would be disagreeing with a reading another
# write-up already published -- which is what makes them the transcription to
# use rather than a figure off this tool's own output.
RESET_VECTOR_TARGETS = ((0x158E, 0xD89F, 0x22), (0x1594, 0xD96C, 0x90))

# The bank-select stub's own bytes, which are the premise the whole `ret`
# reading rests on: it pushes DPL and DPH, switches the bank through the
# P1.0-P1.2 port bits, and `ret`s -- so the `ret` consumes the two DPTR bytes it
# pushed and control reaches the *target*.
# `docs/findings/scheduler-run-8518-entries.md` section 2 derives this from the
# same bytes and `run_entry_map.py --self-test` re-derives it, so it is
# transcribed rather than re-decoded here: if the stub ever stopped having this
# shape, the reading below would be a guess.
#
# `push direct` and `clr`/`setb direct` are each two bytes and `ret` is one.
# Checked as a subsequence of the stub's own extent rather than at fixed
# offsets, because what the claim needs is that these forms are present and that
# the stub ends in a `ret` -- not that they sit at particular offsets, which the
# four stubs' differing bank-select tails would move anyway.
STUB_PUSHES_DPTR = (b"\xc0\x82", b"\xc0\x83")

# The stub's bit writes are the bank-select port bits P1.0-P1.2, named as
# direct addresses and not as an opcode: `clr` on one of them and `setb` on
# another is how `find_banks.find_stubs()` derives each stub's bank number, and
# the three differ across the four stubs while a DPTR clear would not. Reading
# them as one opcode would only hold for the bank-0 stub.
STUB_BANK_SELECT_BITS = (0x90, 0x91, 0x92)

# DPL, DPH and DPS. The premise is that the stub writes none of them after
# pushing the first two, so the `ret` still has a target to consume.
DPTR_BYTES = (0x82, 0x83, 0x86)

# How long a bank-select stub is. `find_banks.py` finds the four 20 bytes
# apart, and reading one instruction-count's worth would run into the next
# stub -- so the extent is named here rather than derived from a stride that
# belongs to a different structure entirely.
STUB_LENGTH = 20


def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


class CommittedTableTests(unittest.TestCase):
    """The committed CSV, read against the image rather than against the tool."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        cls.rows = read_csv(COMMITTED_CSV)
        cls.by_offset = {int(r["file_offset"], 16): r for r in cls.rows}
        cls.census = {int(r["file_offset"], 16): r for r in read_csv(CENSUS_CSV)}

    def target_offset(self, row):
        """The file offset the row's own cells say its target byte was read at.

        Derived from `selects_bank` and `dptr_target` rather than read from a
        column, so this re-derives the arithmetic instead of trusting it.
        """
        bank = int(row["selects_bank"])
        lo = act.region_bounds("bank%d" % bank)[0]
        return lo + int(row["dptr_target"], 16) - 0x8000

    def test_one_row_per_entry_the_census_scoped_to(self):
        entries = {e for e, _, _ in ttc.block_entries(self.d)}
        self.assertEqual(set(self.by_offset), entries,
                         "the table carries one row per block entry, and "
                         "neither a row the block does not have nor a missing "
                         "one -- a count of the block would go stale on the "
                         "next framing correction, so this is a set equality")

    def test_the_target_byte_is_the_byte_in_the_rows_own_bank(self):
        for row in self.rows:
            off = self.target_offset(row)
            self.assertEqual(int(row["target_byte"], 16), self.d[off],
                             f"entry {row['file_offset']} names "
                             f"{row['dptr_target']} in bank {row['selects_bank']}"
                             f" and the byte there is {self.d[off]:02x}, not "
                             f"{row['target_byte']}")

    def test_the_class_is_the_census_own_and_not_recomputed(self):
        for row in self.rows:
            other = self.census[int(row["file_offset"], 16)]
            self.assertEqual(row["target_class"], other["target_class"])
            self.assertEqual(row["stub"], other["stub"])
            self.assertEqual(row["dptr_target"], other["target"])
            self.assertEqual(row["target_byte"], other["target_byte"])

    def test_the_reset_vector_targets_are_the_rows_that_write_up_read(self):
        for entry, target, byte in RESET_VECTOR_TARGETS:
            row = self.by_offset.get(entry)
            self.assertIsNotNone(row, f"entry 0x{entry:04X} has a row")
            self.assertEqual(int(row["dptr_target"], 16), target)
            self.assertEqual(int(row["target_byte"], 16), byte)


class RetRunTests(unittest.TestCase):
    """`ret_run` and `in_ret_run`, against the image and against the rule."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        cls.rows = ttr.reading(cls.d)

    def test_a_reported_run_is_all_ret_and_a_row_without_one_is_not_ret(self):
        for r in self.rows:
            if r["ret_run"] is None:
                self.assertNotEqual(r["target_byte"], ttc.RET,
                                    f"entry 0x{r['file_offset']:04X} carries no "
                                    "run, so its target byte must not be `ret`")
            else:
                lo, hi = r["ret_run"]
                self.assertTrue(all(self.d[i] == ttc.RET for i in range(lo, hi + 1)),
                                "every byte of a reported run is `ret`, which "
                                "is what makes the extent a run and not a span")

    def test_a_run_extent_is_inclusive_at_both_ends(self):
        """`0xBF54`-`0xBFDD` is 138 bytes, not 137.

        Built from the image rather than asserted as a figure: the extent is
        `(last - first + 1)`, and a half-open reading would name one byte
        fewer than the run holds without any other check noticing.
        """
        for r in self.rows:
            if r["ret_run"] is not None:
                lo, hi = r["ret_run"]
                self.assertEqual(self.d[lo], ttc.RET)
                self.assertEqual(self.d[hi], ttc.RET)

    def test_in_ret_run_is_the_threshold_and_nothing_else(self):
        for r in self.rows:
            run = r["ret_run"]
            want = run is not None and run[1] - run[0] + 1 >= ttr.MIN_RET_RUN
            self.assertEqual(r["in_ret_run"], want,
                             "the verdict is the run's length against the "
                             "threshold and nothing else -- a row in a run too "
                             "short keeps the run and drops only the verdict")

    def test_the_threshold_sits_inside_a_flat_band(self):
        """The population does not depend on where in the band the cutoff is.

        Recomputed across every threshold, so this is a property of the image.
        If the count moved anywhere inside the band, `in_ret_run` would be a
        reading of the cutoff and the column would not mean what the write-up
        says it means.
        """
        def counted(n):
            return sum(1 for r in self.rows
                       if r["ret_run"] is not None
                       and r["ret_run"][1] - r["ret_run"][0] + 1 >= n)

        chosen = counted(ttr.MIN_RET_RUN)
        lo = hi = ttr.MIN_RET_RUN
        lengths = [r["ret_run"][1] - r["ret_run"][0] + 1
                   for r in self.rows if r["ret_run"] is not None]
        while lo - 1 >= min(lengths) and counted(lo - 1) == chosen:
            lo -= 1
        while hi + 1 <= max(lengths) and counted(hi + 1) == chosen:
            hi += 1
        self.assertLess(lo, ttr.MIN_RET_RUN,
                        "the band extends below the chosen threshold, so the "
                        "cutoff is not sitting on the edge where one step "
                        "would change the population")
        self.assertGreater(hi, ttr.MIN_RET_RUN,
                           "and above it, for the same reason")
        self.assertNotEqual(counted(lo - 1), chosen,
                            "the band is bounded below by a real change in the "
                            "count, not by where the walk stopped")
        self.assertNotEqual(counted(hi + 1), chosen,
                            "and bounded above by one")

    def test_one_byte_is_not_enough_because_the_tree_has_named_one_ins(self):
        """The rule needs a run, and here is why: a one-byte `ret` is code.

        The census's own docstring gives the precedents -- `bank0,0xD9DB`
        `ret_stub` and `bank0,0xD2BE` `return_trampoline_d091_0860_guard_fail`
        -- and the suite asserts the property rather than the names: a
        threshold of 1 would sweep in rows that are a whole `ret` run long, and
        the table keeps them, with `in_ret_run` false, precisely because a lone
        `ret` is a routine.
        """
        alone = [r for r in self.rows
                 if r["ret_run"] is not None
                 and r["ret_run"][1] - r["ret_run"][0] + 1 == 1]
        self.assertTrue(alone, "this image does have targets in a one-byte "
                              "`ret` run, which is what makes the threshold a "
                              "decision rather than a formality")
        self.assertTrue(all(not r["in_ret_run"] for r in alone),
                        "and none of them is counted, because a lone `ret` is "
                        "a one-instruction routine and not a fill")


class CallerJoinTests(unittest.TestCase):
    """The join's two ends, and its upper-bound framing."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        cls.rows = ttr.reading(cls.d)
        cls.calls = ttr.call_sites_by_entry(CALL_TARGETS_CSV)

    def test_every_committed_call_site_resolves_to_an_entry(self):
        known = {r["file_offset"] for r in self.rows}
        unresolved = sorted(t for t in self.calls if t not in known)
        self.assertEqual(unresolved, [],
                         "every call site naming a trampoline resolves to an "
                         "entry in this table -- a site resolving to nothing "
                         "is a caller attributed to no thunk, and would be "
                         "dropped from the count without anything noticing")

    def test_an_entrys_count_is_the_number_of_sites_naming_it(self):
        for r in self.rows:
            self.assertEqual(r["call_sites"], len(self.calls.get(r["file_offset"], [])),
                             "the count is read from the committed file, not "
                             "accumulated across calls")

    def test_the_opcode_mix_sums_to_the_count(self):
        for r in self.rows:
            self.assertEqual(sum(r["caller_ops"].values()), r["call_sites"],
                             "the opcode mix is a split of one count, not a "
                             "second count that could disagree with it")

    def test_a_row_with_no_sites_says_zero_rather_than_blank(self):
        """The empty cell would read as "not applicable" and as "zero".

        Which is the same defect `trampoline_target_census` records for its
        own `listing` column, so the same answer: an explicit 0, and a `-` in
        the CSV only for the opcode mix, where there is genuinely no opcode.
        """
        table = list(csv.reader(io.StringIO(ttr.csv_text(self.d))))
        head = table[0]
        for row in table[1:]:
            cells = dict(zip(head, row))
            self.assertTrue(cells["call_sites"].isdigit(),
                            "an entry with no call site carries 0, never an "
                            "empty cell")
            self.assertEqual(cells["caller_ops"] == "-",
                             cells["call_sites"] == "0",
                             "the opcode mix is `-` exactly when there are no "
                             "sites to mix")

    def test_rows_without_calls_are_reported_not_filtered(self):
        """A dropped row would silently shrink the contrast the write-up reads.

        The write-up's claim is a comparison -- entries inside a `ret` run
        against the rest -- so an entry with zero callers has to survive into
        the table for the comparison to mean anything. Asserted as a
        relationship to the census rather than as a count.
        """
        census = {int(r["file_offset"], 16) for r in read_csv(CENSUS_CSV)}
        self.assertEqual({r["file_offset"] for r in self.rows}, census,
                         "no row is dropped for having no caller; the table is "
                         "one row per entry whatever the call count")


class RefusalTests(unittest.TestCase):
    """The planted-entry fixtures, and what each is for."""

    def setUp(self):
        self.d = Path(FIRMWARE).read_bytes()

    def test_a_planted_entry_outside_the_block_is_not_absorbed(self):
        for name, off, raw in ttr.PLANTED:
            if name != "OUTSIDE":
                continue
            buf = bytearray(self.d)
            buf[off:off + len(raw)] = raw
            entries = [e for e, _, _ in ttc.block_entries(bytes(buf))]
            self.assertNotIn(off, entries,
                             "a well-formed entry past the block's end is "
                             "excluded by the range restriction, which is the "
                             "only thing excluding it -- `trampolines()` "
                             "accepts the shape")
            self.assertEqual(len(entries), len(ttc.block_entries(self.d)),
                             "and the population is unchanged, so the fixture "
                             "is testing the refusal rather than the count")

    def test_a_planted_entry_inside_the_block_breaks_the_stride(self):
        for name, off, raw in ttr.PLANTED:
            if name != "INSIDE":
                continue
            buf = bytearray(self.d)
            buf[off:off + len(raw)] = raw
            entries = [e for e, _, _ in ttc.block_entries(bytes(buf))]
            strides = sorted({b - a for a, b in zip(entries, entries[1:])})
            self.assertNotEqual(strides, [act.TRAMP_STRIDE],
                                "a well-formed entry planted inside the block "
                                "is taken by the scan and the stride is no "
                                "longer one run -- so a census that absorbed it "
                                "would fail its own framing check rather than "
                                "quietly reporting a larger block")

    def test_the_stub_belongs_to_a_far_call_over_a_bank_select_tail(self):
        """The route the `ret` reading rests on, read off the stub's bytes.

        The stub pushes DPL and DPH, switches the bank through P1.0-P1.2, then
        `ret`s. That `ret` consumes the two bytes it pushed as a **jump
        target**, so control reaches the far routine; what the far routine's own
        `ret` pops is the marker above it, landing at `0x11XX` inside the stub
        window, and that landing is the stub's own bank-select tail whose `ret`
        pops the caller's return address from below the marker. Asserted as the
        byte shape so a stub that stopped having it is caught here rather than
        leaving the write-up's reading resting on nothing. Which route the
        caller took to reach the pointer is not something these bytes decide,
        and nothing here asserts that it did not.
        """
        stub = act.STUB_SITES[0][0]
        window = bytes(self.d[stub:stub + STUB_LENGTH])
        self.assertEqual(len(window), STUB_LENGTH,
                         "the stub's extent is inside the image, so the bytes "
                         "checked below are the stub's and not the next one's")

        def offset_of(form):
            at = window.find(form)
            self.assertNotEqual(at, -1,
                                f"the stub still carries {form.hex(' ')}, so "
                                "the `ret` reading's premise holds in these "
                                "bytes")
            return at

        # Every `clr direct` / `setb direct` in the stub, as (offset, address).
        bits = [(at, window[at + 1]) for at in range(len(window) - 1)
                if window[at] in (0xC2, 0xD2)]
        writes = [direct for _, direct in bits]

        pushed = [offset_of(f) for f in STUB_PUSHES_DPTR]
        self.assertEqual(window[-1], ttc.RET,
                         "and the stub ends in a `ret`, which is what consumes "
                         "the pushed DPTR")
        self.assertEqual(writes, list(STUB_BANK_SELECT_BITS),
                         "the stub's bit writes are the bank-select port bits "
                         "P1.0-P1.2 and nothing else, which is the reading "
                         "`find_banks.find_stubs()` derives the bank number "
                         "from")
        self.assertEqual([direct for direct in writes if direct in DPTR_BYTES],
                         [],
                         "and none of them is DPL, DPH or DPS, so the bank "
                         "switch does not overwrite the target")
        self.assertLess(max(pushed), min(at for at, _ in bits),
                        "the DPTR bytes are pushed before the bank-select "
                        "tail, so the `ret` has something left to consume: "
                        "write over DPTR first and the far call would have no "
                        "target")


class ToolTests(unittest.TestCase):
    """The tool's own modes, driven the way a reader would drive them."""

    def run_tool(self, *args):
        return subprocess.run([sys.executable, TOOL, FIRMWARE, *args],
                              capture_output=True, text=True)

    def test_check_passes_against_the_committed_table(self):
        got = self.run_tool("--check")
        self.assertEqual(got.returncode, 0,
                         f"--check must reproduce the committed table\n{got.stdout}"
                         f"{got.stderr}")

    def test_csv_on_stdout_is_the_committed_table(self):
        got = self.run_tool("--csv")
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(got.stdout, Path(COMMITTED_CSV).read_text(),
                         "--csv and the committed file are the same bytes, so "
                         "the reproduction in the write-up is a `| diff -` "
                         "against a file this repository holds")

    def test_self_test_passes(self):
        got = self.run_tool("--self-test")
        self.assertEqual(got.returncode, 0,
                         f"--self-test must pass\n{got.stdout}{got.stderr}")
        self.assertIn("self-test passed", got.stdout)

    def test_check_refuses_a_missing_table_rather_than_creating_it(self):
        """A missing file is a red run, not a table written on the spot.

        `--check` deciding what the committed table is would make the mode
        that verifies it the mode that produces it; `bucket_c_codemap.py` and
        `trampoline_target_census.py` both refuse, and this is that refusal.
        """
        with tempfile.TemporaryDirectory() as tmp:
            absent = os.path.join(tmp, "absent.csv")
            got = self.run_tool("--check", "--csv-path", absent)
            self.assertEqual(got.returncode, 1)
            self.assertFalse(os.path.exists(absent),
                             "--check compares; it never creates the file it "
                             "compares against")

    def test_check_reds_on_a_doctored_table(self):
        """The guard has to be able to go red, or it is not a guard."""
        committed = Path(COMMITTED_CSV).read_text()
        with tempfile.TemporaryDirectory() as tmp:
            doctored = os.path.join(tmp, "doctored.csv")
            # Flip one verdict rather than a byte: a table that disagreed
            # about the run is the drift this mode exists to catch, and it is
            # the one a byte-level check would not notice.
            doctored_txt = committed.replace(
                next(line for line in committed.splitlines(True)
                     if line.endswith(",yes,no,1,ljmp=1\n")),
                next(line for line in committed.splitlines(True)
                     if line.endswith(",yes,no,1,ljmp=1\n"))
                .replace(",yes,no,", ",no,no,"), 1)
            self.assertNotEqual(doctored_txt, committed,
                                "the fixture has to change something, or the "
                                "case is vacuous")
            Path(doctored).write_text(doctored_txt)
            got = self.run_tool("--check", "--csv-path", doctored)
            self.assertEqual(got.returncode, 1,
                             "a table whose verdicts were edited is not what "
                             "the image derives, and --check says so")


if __name__ == "__main__":
    unittest.main()
